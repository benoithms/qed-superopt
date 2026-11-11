"""Souper as a baseline on the corpus, judged by our chain only:
    PYTHONPATH=.:scripts uv run python scripts/souper_baseline.py --souper-dir <dir> \
        --run-id souper-v1 [--max-insts 2] [--timeout 600] [--jobs 4] [entries ...]

Souper (https://github.com/google/souper) runs as an opt pass, with its own LLVM 18. It reads
the clang -O3 IR of our reference toolchain after a downgrade to what LLVM 18 parses: the
poison-generating flags and attributes LLVM 18 does not know (`samesign`, `nuw`/`nsw` on
trunc, `range`, ...) are removed. Removing them makes the input more defined, so anything
that refines the downgraded IR also refines the original one. The body Souper returns is then
placed under the exact header of the original source, as for the models, proven by our Alive2
against the original source, measured by our llc and llvm-mca, and judged by the same rule
as fold_back.py. Souper's own verdict is never trusted."""

import argparse
import json
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fold_back import check

from qed import config
from qed.cost import cost
from qed.extract import ExtractError, body, extract, function, splice
from qed.verify import Status, sha256, verify

# LLVM 19+ syntax that LLVM 18 rejects; each removal only removes poison or UB from the source
DOWNGRADE = [
    (re.compile(r"\bicmp samesign "), "icmp "),
    (re.compile(r"\btrunc (?:nuw |nsw )+"), "trunc "),
    (re.compile(r"\brange\([^()]*\)\s*"), ""),
    (re.compile(r"\bcaptures\([^()]*\)\s*"), ""),
    (re.compile(r"\binitializes\([^()]*\)\s*"), ""),
    (re.compile(r"\bdead_on_unwind\s*"), ""),
    (re.compile(r"\bnocreateundeforpoison\s*"), ""),  # intrinsic declarations only
]
UNSUPPORTED = re.compile(r"@llvm\.[su]cmp\.")  # intrinsics added after LLVM 18


def downgrade(ll: str) -> str:
    for pat, rep in DOWNGRADE:
        ll = pat.sub(rep, ll)
    return ll


def run_souper(
    ll: str, souper_dir: Path, max_insts: int, timeout: int
) -> tuple[str | None, str, float]:
    opt = souper_dir / "third_party/llvm-Release-install/bin/opt"
    plugin = souper_dir / "build/libsouperPass.dylib"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "f.ll"
        f.write_text(ll)
        cmd = [
            opt,
            "-load-pass-plugin",
            plugin,
            "-passes=function(souper),dce",
            f"-souper-enumerative-synthesis-max-instructions={max_insts}",
            "-S",
            "-o",
            "-",
            f,
        ]
        start = time.monotonic()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "timeout", time.monotonic() - start
        sec = time.monotonic() - start
    if p.returncode:
        return None, "error: " + p.stderr.strip()[-500:], sec
    return p.stdout, "ok", sec


def one(entry: Path, args) -> dict:
    src = extract(entry / "src.c")
    rec = {
        "id": entry.name,
        "category": entry.parent.name,
        "src_ll": src,
        "src_sha256": sha256(src),
    }
    if UNSUPPORTED.search(src):
        return rec | {"status": "unsupported", "detail": "intrinsic unknown to LLVM 18"}
    low = downgrade(src)
    out, status, sec = run_souper(low, args.souper_dir, args.max_insts, args.timeout)
    rec |= {"souper_input": low, "souper_seconds": sec}
    if out is None:
        return rec | {"status": status}
    new = body(function(out))
    if new.strip() == body(function(low)).strip():
        return rec | {"status": "no_change"}
    try:
        tgt = splice(src, new)
    except ExtractError as e:
        return rec | {"status": "invalid", "detail": str(e)}
    r = verify(src, tgt)
    rec |= {
        "tgt_ll": tgt,
        "tgt_sha256": sha256(tgt),
        "check": r.status.value,
        "alive2_output": r.output,
    }
    if r.status is not Status.PROVEN:
        return rec | {"status": r.status.value}
    base, c = cost(src), cost(tgt)
    rec |= {
        "status": "proven",
        "baseline": {"asm_insts": base.asm_insts, "mca_cycles": base.mca_cycles},
        "cost": {"asm_insts": c.asm_insts, "mca_cycles": c.mca_cycles},
        "faster": c.mca_cycles < base.mca_cycles,
    }
    if rec["faster"]:
        fake = {
            "id": entry.name,
            "category": entry.parent.name,
            "src_ll": src,
            "baseline": {"mca_output": base.mca_output, "asm": base.asm},
            "best": {"n": 1, "speedup": base.mca_cycles / c.mca_cycles},
            "attempts": [{"n": 1, "tgt_ll": tgt, "check": "proven"}],
        }
        rec["fold_back"] = check(fake, 1.05)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("entries", nargs="*", type=Path)
    ap.add_argument("--souper-dir", type=Path, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--max-insts", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    entries = args.entries or sorted(p for p in Path("bench").glob("*/*") if p.is_dir())
    out = Path("results", args.run_id)
    out.mkdir(parents=True, exist_ok=True)

    def git(*a):
        return subprocess.run(
            ["git", "-C", str(args.souper_dir), *a], capture_output=True, text=True
        ).stdout.strip()  # noqa: E731

    (out / "run.json").write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "tool": "souper",
                "souper_commit": git("rev-parse", "HEAD"),
                "max_insts": args.max_insts,
                "timeout_s": args.timeout,
                "jobs": args.jobs,
                "passes": "function(souper),dce",
                "downgrade": [p.pattern for p, _ in DOWNGRADE],
                "judged_by": {
                    "alive2": "reference",
                    "llc": config.LLC_FLAGS,
                    "rule": "fold_back.check, 5%",
                },
                "entries": [str(e) for e in entries],
            },
            indent=1,
        )
    )
    with ThreadPoolExecutor(args.jobs) as ex:
        for rec in ex.map(lambda e: one(e, args), entries):
            (out / f"{rec['id']}.json").write_text(json.dumps(rec, indent=1))
            fb = rec.get("fold_back") or {}
            print(
                f"{rec['category']} {rec['id']:32} {rec['status']:12} kept={fb.get('kept')}",
                flush=True,
            )


if __name__ == "__main__":
    main()
