"""Time the kept wins on the real CPU (i7-9700K first, then the i7-12700H):
    PYTHONPATH=. python scripts/bench_cpu.py results/<run-id> --machine "<conditions>" \
        [--all-kept] [--ids a b] [--out results/bench-<cpu>/<run-id>.json]

llvm-mca reads a function as one straight line, both sides of a branch included, so wins with a
branch need a real measure. For each win, clang -O3's function and the rewrite (after opt -O3,
as in fold_back.py) go through the reference llc into one binary with a generated C driver.

Inputs: 64 distinct argument tuples, drawn per argument from a mix of edge values (0, 1, -1,
small and small negative numbers, powers of two, signed min and max) and random ones, so that
every branch goes both ways. Inputs on which either version traps (division by zero) are
dropped. Both modes call the functions on the same 16384 inputs, only the order differs:
- predictable: each tuple repeated 256 times in a row, the predictor learns every branch;
- random: the same calls shuffled, branches go both ways unpredictably.
Any gap between the two modes is the cost of mispredicted branches.

Timing: the time-stamp counter around 16384 calls, the clang version, the rewrite and an empty
function in turn, repeated --reps times; the median per call is kept. The empty function gives
the loop and call overhead. A chain of dependent adds (one cycle each) gives the actual core
frequency at the start and at the end of each launch, which shows whether turbo was on or the
CPU slowed down. Each launch is a separate process pinned with taskset; the spread between
launches tells whether the measure is stable (under WSL2, taskset pins a virtual CPU only).
A win holds in a mode when every launch is faster by more than --min-speedup."""

import argparse
import json
import platform
import random
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from fold_back import check, opt_o3, winning_attempt

from qed import config
from qed.extract import function

DISTINCT = 64
CALLS = 16384
_PARAM = re.compile(r"(i\d+)([^,)]*)")


def c_type(ir_type: str, attrs: str) -> str:
    bits = int(ir_type[1:])
    if bits == 1:
        return "bool"
    return f"{'u' if 'zeroext' in attrs else ''}int{bits}_t"


def signature(ll: str) -> tuple[str, list[str], list[int]]:
    """C return type, C parameter types and parameter widths of the function in `ll`."""
    header = function(ll).split("\n", 1)[0]
    m = re.match(r"define (.*?)\s(i\d+) @[-\w.$]+\((.*)\)", header)
    ret = c_type(m.group(2), m.group(1))
    params = _PARAM.findall(m.group(3))
    return ret, [c_type(t, a) for t, a in params], [int(t[1:]) for t, _ in params]


def candidates(widths: list[int], rng: random.Random, count: int) -> list[list[int]]:
    """`count` argument tuples, each argument masked to its width."""

    def value(w: int) -> int:
        mask = (1 << w) - 1
        kind = rng.randrange(8)
        if kind == 0:
            v = rng.choice([0, 1, -1])
        elif kind == 1:
            v = rng.randrange(2 * w + 2)
        elif kind == 2:
            v = -rng.randrange(2 * w + 2)
        elif kind == 3:
            v = (1 << rng.randrange(w)) + rng.choice([-1, 0, 1])
        elif kind == 4:
            v = rng.choice([1 << (w - 1), (1 << (w - 1)) - 1])
        else:
            v = rng.getrandbits(w)
        return v & mask

    return [[value(w) for w in widths] for _ in range(count)]


DRIVER = r"""
#include <setjmp.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <x86intrin.h>

#define NARGS @NARGS@
#define DISTINCT @DISTINCT@
#define CANDIDATES @CANDIDATES@
#define CALLS @CALLS@
#define REPS @REPS@

@RET@ f_src(@PARAMS@);
@RET@ f_tgt(@PARAMS@);
@RET@ f_nop(@PARAMS@);

static const uint64_t cand[CANDIDATES][NARGS] = {@CANDS@};
static uint64_t keep[DISTINCT][NARGS];
static uint64_t in[NARGS][CALLS];
static uint64_t sink;

#define CALL(fn, a, i) fn(@ARGS@)

static sigjmp_buf trap;
static void on_trap(int sig) { (void)sig; siglongjmp(trap, 1); }

static uint64_t tsc(void) {
    _mm_lfence();
    uint64_t t = __rdtsc();
    _mm_lfence();
    return t;
}

/* TSC ticks per core cycle: 10 dependent adds per iteration, one cycle each. */
static double ticks_per_cycle(void) {
    uint64_t n = 20000000, x = 0, t0 = tsc();
    __asm__ volatile("1:\n"
                     "add $1, %0\n add $1, %0\n add $1, %0\n add $1, %0\n add $1, %0\n"
                     "add $1, %0\n add $1, %0\n add $1, %0\n add $1, %0\n add $1, %0\n"
                     "dec %1\n jnz 1b"
                     : "+r"(x), "+r"(n));
    return (double)(tsc() - t0) / (20000000.0 * 10);
}

static double tsc_ghz(void) {
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    uint64_t t0 = tsc();
    do clock_gettime(CLOCK_MONOTONIC, &b);
    while ((b.tv_sec - a.tv_sec) * 1000000000L + (b.tv_nsec - a.tv_nsec) < 200000000L);
    uint64_t t1 = tsc();
    return (double)(t1 - t0) / ((b.tv_sec - a.tv_sec) * 1e9 + (b.tv_nsec - a.tv_nsec));
}

#define TIME(fn, out)                                                         \
    do {                                                                      \
        uint64_t s = 0, t0 = tsc();                                           \
        for (int i = 0; i < CALLS; i++) s ^= (uint64_t)CALL(fn, in, i);       \
        out = (double)(tsc() - t0) / CALLS;                                   \
        sink ^= s;                                                            \
    } while (0)

static int cmp(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static void stats(const char *name, double *v, double tpc, int last) {
    qsort(v, REPS, sizeof *v, cmp);
    printf("\"%s\": {\"median\": %.4f, \"q1\": %.4f, \"q3\": %.4f, \"min\": %.4f}%s", name,
           v[REPS / 2] / tpc, v[REPS / 4] / tpc, v[3 * REPS / 4] / tpc, v[0] / tpc,
           last ? "" : ", ");
}

static void measure(const char *mode, double tpc, int last) {
    static double src[REPS], tgt[REPS], nop[REPS];
    for (int r = 0; r < REPS; r++) {
        for (int k = 0; k < 3; k++) {
            switch ((r + k) % 3) {
            case 0: TIME(f_src, src[r]); break;
            case 1: TIME(f_tgt, tgt[r]); break;
            case 2: TIME(f_nop, nop[r]); break;
            }
        }
    }
    printf("\"%s\": {", mode);
    stats("src", src, tpc, 0);
    stats("tgt", tgt, tpc, 0);
    stats("nop", nop, tpc, 1);
    printf("}%s", last ? "" : ", ");
}

int main(void) {
    signal(SIGFPE, on_trap);
    int kept = 0, dropped = 0, differ = 0;
    uint64_t a[NARGS][1];
    for (int c = 0; c < CANDIDATES && kept < DISTINCT; c++) {
        for (int j = 0; j < NARGS; j++) a[j][0] = cand[c][j];
        if (sigsetjmp(trap, 1)) { dropped++; continue; }
        uint64_t s = (uint64_t)CALL(f_src, a, 0), t = (uint64_t)CALL(f_tgt, a, 0);
        differ += (@RET@)s != (@RET@)t;
        for (int j = 0; j < NARGS; j++) keep[kept][j] = cand[c][j];
        kept++;
    }
    signal(SIGFPE, SIG_DFL);
    if (kept < DISTINCT) { fprintf(stderr, "only %d inputs without a trap\n", kept); return 1; }

    double ghz = tsc_ghz(), tpc_start = ticks_per_cycle();
    printf("{\"tsc_ghz\": %.4f, \"core_ghz_start\": %.4f, \"dropped\": %d, \"differ\": %d, ",
           ghz, ghz / tpc_start, dropped, differ);

    /* predictable: each input repeated CALLS / DISTINCT times in a row */
    for (int i = 0; i < CALLS; i++)
        for (int j = 0; j < NARGS; j++) in[j][i] = keep[i / (CALLS / DISTINCT)][j];
    measure("predictable", tpc_start, 0);

    /* random: the same calls, shuffled (fixed seed) */
    uint64_t x = 0x9e3779b97f4a7c15u;
    for (int i = CALLS - 1; i > 0; i--) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        int k = (int)(x % (uint64_t)(i + 1));
        for (int j = 0; j < NARGS; j++) {
            uint64_t t = in[j][i]; in[j][i] = in[j][k]; in[j][k] = t;
        }
    }
    measure("random", tpc_start, 1);

    printf(", \"core_ghz_end\": %.4f, \"sink\": %llu}\n", ghz / ticks_per_cycle(),
           (unsigned long long)(sink & 1));
    return 0;
}
"""

NOP = """\t.text
\t.globl\tf_nop
\t.type\tf_nop,@function
f_nop:
\txorl\t%eax, %eax
\tretq
\t.size\tf_nop, .-f_nop
\t.section\t".note.GNU-stack","",@progbits
"""


def driver(ll: str, reps: int, seed: int) -> str:
    ret, params, widths = signature(ll)
    cands = candidates(widths, random.Random(seed), 4 * DISTINCT)
    subs = {
        "NARGS": str(len(params)),
        "DISTINCT": str(DISTINCT),
        "CANDIDATES": str(len(cands)),
        "CALLS": str(CALLS),
        "REPS": str(reps),
        "RET": ret,
        "PARAMS": ", ".join(params),
        "CANDS": ",".join("{" + ",".join(f"{v}u" for v in c) + "}" for c in cands),
        "ARGS": ", ".join(f"({t})a[{j}][i]" for j, t in enumerate(params)),
    }
    return re.sub(r"@([A-Z]+)@", lambda m: subs[m.group(1)], DRIVER)


def renamed(ll: str, name: str) -> str:
    fn = function(ll)
    header, rest = fn.split("\n", 1)
    return ll.replace(fn, re.sub(r"@[-\w.$]+\(", f"@{name}(", header, count=1) + "\n" + rest)


def _run(cmd: list) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"{Path(str(cmd[0])).name}: {p.stderr.strip()}")
    return p.stdout


def build(src_ll: str, tgt_ll: str, d: Path, reps: int, seed: int) -> Path:
    objs = []
    for name, ll in (("f_src", src_ll), ("f_tgt", tgt_ll)):
        (d / f"{name}.ll").write_text(renamed(ll, name))
        _run([config.LLC, *config.LLC_FLAGS, d / f"{name}.ll", "-o", d / f"{name}.s"])
        objs.append(d / f"{name}.s")
    (d / "nop.s").write_text(NOP)
    (d / "driver.c").write_text(driver(src_ll, reps, seed))
    exe = d / "bench"
    _run(
        [config.CLANG, "-O2", f"-march={config.CPU}", "-o", exe, d / "driver.c", *objs, d / "nop.s"]
    )
    return exe


def summarize(launches: list[dict], min_speedup: float) -> dict:
    out = {}
    for mode in ("predictable", "random"):
        med = {v: [r[mode][v]["median"] for r in launches] for v in ("src", "tgt", "nop")}
        speedups = [s / t for s, t in zip(med["src"], med["tgt"], strict=True)]
        triples = zip(med["src"], med["tgt"], med["nop"], strict=True)
        # a rewrite as cheap as the empty function leaves no net time to compare
        net = [(s - n) / (t - n) if t > n else None for s, t, n in triples]
        spread = {
            v: (max(med[v]) - min(med[v])) / statistics.median(med[v]) for v in ("src", "tgt")
        }
        if min(speedups) > min_speedup:
            verdict = "faster"
        elif max(speedups) < 1.0:
            verdict = "slower"
        else:
            verdict = "no clear gain"
        out[mode] = {
            "cycles": {v: statistics.median(med[v]) for v in med},
            "speedup": statistics.median(speedups),
            "speedup_range": [min(speedups), max(speedups)],
            "net_speedup": None if None in net else statistics.median(net),
            "spread": spread,
            "verdict": verdict,
        }
    return out


def conditions(args) -> dict:
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        platform.processor(),
    )
    return {
        "machine": args.machine,
        "cpu": cpu,
        "kernel": platform.release(),
        "wsl": "microsoft" in platform.release().lower(),
        "pinned_cpu": args.cpu,
        "launches": args.launches,
        "reps": args.reps,
        "calls_per_rep": CALLS,
        "distinct_inputs": DISTINCT,
        "seed": args.seed,
        "min_speedup": args.min_speedup,
        "statistic": "median over reps per launch, then median over launches",
        "llc_flags": config.LLC_FLAGS,
        "toolchain": str(config.TOOLCHAIN),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--machine", required=True, help="turbo on/off, power plan, what else runs")
    ap.add_argument("--ids", nargs="*", help="these functions (default: kept wins with a branch)")
    ap.add_argument("--all-kept", action="store_true", help="every kept win, branch or not")
    ap.add_argument("--launches", type=int, default=5)
    ap.add_argument("--reps", type=int, default=201)
    ap.add_argument("--cpu", type=int, default=2, help="CPU to pin with taskset")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-speedup", type=float, default=1.05)
    ap.add_argument("--out", type=Path, help="write the full results as JSON")
    args = ap.parse_args(argv)

    results = {}
    for p in sorted(args.run_dir.glob("*.json")):
        if p.name != "run.json":
            res = json.loads(p.read_text())
            if res["best"]:
                results[res["id"]] = res
    if args.ids:
        ids = args.ids
    else:
        rows = [check(r, args.min_speedup) for r in results.values()]
        ids = [r["id"] for r in rows if r["kept"] and (args.all_kept or r["branch"])]

    rows = []
    for fid in sorted(ids):
        res = results[fid]
        tgt = opt_o3(winning_attempt(res)["tgt_ll"])
        with tempfile.TemporaryDirectory() as d:
            exe = build(res["src_ll"], tgt, Path(d), args.reps, args.seed)
            launches = [
                json.loads(_run(["taskset", "-c", str(args.cpu), exe]))
                for _ in range(args.launches)
            ]
        rows.append(
            {
                "id": fid,
                "category": res["category"],
                "launches": launches,
                **summarize(launches, args.min_speedup),
            }
        )
        print(f"{fid}: done", file=sys.stderr)

    print(
        f"{'cat':4}{'function':30}{'mode':12}{'clang':>8}{'rewrite':>8}{'speedup':>9}"
        f"{'range':>14}{'spread':>8}  verdict"
    )
    for r in sorted(rows, key=lambda r: (r["category"], r["id"])):
        for mode in ("predictable", "random"):
            m = r[mode]
            lo, hi = m["speedup_range"]
            print(
                f"{r['category']:4}{r['id']:30}{mode:12}{m['cycles']['src']:>8.2f}"
                f"{m['cycles']['tgt']:>8.2f}{m['speedup']:>8.2f}x{lo:>7.2f}-{hi:.2f}x"
                f"{max(m['spread'].values()):>7.1%}  {m['verdict']}"
            )
    ghz = [(x["core_ghz_start"], x["core_ghz_end"]) for r in rows for x in r["launches"]]
    print(
        f"\ncycles per call, overhead included; core clock {min(min(g) for g in ghz):.2f}"
        f"-{max(max(g) for g in ghz):.2f} GHz"
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps({"conditions": conditions(args), "results": rows}, indent=1) + "\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
