"""Rank the zones QED may rewrite in SQLite by what the benchmark executes:
    PYTHONPATH=. python real-projects/sqlite/zones.py --out results/real-projects/sqlite/zones.json

A zone is one basic block of the clang -O3 IR of sqlite3.c, with no loop, call or global, as a
function that returns the values the rest of the program uses. Every block gets a counter, so its
weight (runs x instructions) is an exact count, the same on any CPU, but only an estimate of time.
--smoke builds for this machine to check the tool: its numbers do not count."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from qed import config

HERE = Path(__file__).parent
WORK = HERE / "work"
FUNC = re.compile(r"^(define[^\n]*@([\w.]+)\([^\n]*\{\n)(.*?)^\}", re.S | re.M)
BLOCK = re.compile(r"^([\w.\-]+):[^\n]*\n(.*?)(?=^[\w.\-]+:|\Z)", re.S | re.M)
LABEL = re.compile(r"label %([\w.\-]+)")
METADATA = re.compile(r",\s*!\w[\w.]*(?: !\d+| !\{[^}]*\})")
CANDIDATES, MIN_SIZE, MAX_SIZE = 100, 4, 60
DUMP = r"""
#include <stdio.h>
#include <stdlib.h>
unsigned long long qed_counts[QED_N];
static void qed_dump(void) {
    FILE *f = fopen(QED_OUT, "wb");
    fwrite(qed_counts, sizeof qed_counts, 1, f);
    fclose(f);
}
__attribute__((constructor)) static void qed_init(void) { atexit(qed_dump); }
"""


def project() -> dict:
    return json.loads((HERE / "project.json").read_text())


def named_ir(flags: list[str]) -> str:
    """clang -O3 IR of sqlite3.c, with stable names for its blocks."""
    defines = [f"-D{d}" for d in project()["defines"]]
    ll, named = WORK / "sqlite3.o3.ll", WORK / "sqlite3.named.ll"
    subprocess.run(
        [config.CLANG, *flags, *defines, "-S", "-emit-llvm", WORK / "sqlite3.c", "-o", ll],
        check=True,
    )
    subprocess.run([config.OPT, "-S", "-passes=instnamer", ll, "-o", named], check=True)
    return named.read_text()


def instructions(block: str) -> list[str]:
    return [x for x in block.splitlines() if x.startswith("  ") and not x.startswith("   ")]


def instrument(ir: str) -> tuple[str, list[dict]]:
    """Add one counter per block, after its phis. Returns the IR and what each counter counts."""
    table: list[dict] = []

    def in_function(f: re.Match) -> str:
        body, fn = f[3], f[2]

        def in_block(b: re.Match) -> str:
            lines = b[2].splitlines(keepends=True)
            i = 0
            while " = phi " in lines[i]:
                i += 1
            n = len(table)
            inst = instructions(b[2])
            table.append(
                {
                    "function": fn,
                    "block": b[1],
                    "instructions": len(inst),
                    "self_loop": b[1] in LABEL.findall(b[2]),
                }
            )
            gep = f"getelementptr inbounds nuw (i64, ptr @qed_counts, i64 {n})"
            add = (
                f"  %qc{n} = load i64, ptr {gep}\n  %qd{n} = add i64 %qc{n}, 1\n"
                f"  store i64 %qd{n}, ptr {gep}\n"
            )
            return f"{b[0][: b[0].index(chr(10)) + 1]}{''.join(lines[:i])}{add}{''.join(lines[i:])}"

        return f[1] + BLOCK.sub(in_block, body) + "}"

    out = FUNC.sub(in_function, ir)
    return out + "\n@qed_counts = external global [0 x i64]\n", table


def zone_ir(fn: str, block: str) -> tuple[str | None, str]:
    """The block as a function that returns its outputs, or None and the reason it is refused.
    llvm-extract passes outputs through pointers to fresh allocas, which Alive2 mostly cannot
    prove; they become part of the return value, and whole.py stores them back at the call."""
    p = subprocess.run(
        [
            config.LLVM_BIN / "llvm-extract",
            f"--bb={fn}:{block}",
            "-S",
            WORK / "sqlite3.named.ll",
            "-o",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        return None, "extract"
    s = METADATA.sub("", p.stdout)
    s = "\n".join(x for x in s.splitlines() if not x.startswith("!")) + "\n"
    m = re.search(r"^define (?:[a-z_]+ )*?(\S+) @([\w.]+)\((.*)\)( [^{]*)?\{$", s, re.M)
    if not m:
        return None, "header"
    body = s[m.end() :]
    if " call " in body or re.search(r"@(?!llvm\.)", body.split("\n}")[0]):
        return None, "call or global"
    ret, name, args = m[1], m[2], m[3]
    params = [a.strip() for a in re.split(r", (?=\w)", args)] if args else []
    outs = [a.split()[-1] for a in params if a.split()[-1].endswith(".out")]
    stored = {}
    for o in outs:
        st = re.search(rf"^  store (\S+) (\S+), ptr {re.escape(o)}\b[^\n]*\n", s, re.M)
        if not st:
            return None, "output"
        stored[o] = st[1], st[2]
        s = s.replace(st[0], "", 1)
    if any(re.search(rf"{re.escape(o)}\b", s[s.index("{") :]) for o in outs):
        return None, "output"
    base = [] if ret == "void" else [ret]
    if not base and not outs:
        return None, "no result"
    fields = base + [stored[o][0] for o in outs]
    rty = "{ " + ", ".join(fields) + " }"
    keep = [a for a in params if a.split()[-1] not in outs]
    n = 0

    def new_ret(r: re.Match) -> str:
        nonlocal n
        n += 1
        values = ([r[2]] if base else []) + [stored[o][1] for o in outs]
        cur, text = "poison", ""
        for i, (ty, v) in enumerate(zip(fields, values, strict=True)):
            text += f"  %ret{n}.{i} = insertvalue {rty} {cur}, {ty} {v}, {i}\n"
            cur = f"%ret{n}.{i}"
        return f"{text}  ret {rty} {cur}\n"

    s = re.sub(r"^  ret (?:void|(\S+) (\S+))\n", new_ret, s, flags=re.M)
    head = f"define {rty} @{name}({', '.join(keep)}) {{"
    s = re.sub(r"^define [^\n]*\{$", head, s, count=1, flags=re.M)
    s = re.sub(r"^attributes [^\n]*\n", "", s, flags=re.M)
    s = re.sub(r"^; Function Attrs[^\n]*\n", "", s, flags=re.M)
    return s, ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    flags = ["-O3", "-g0", "-fdiscard-value-names"]
    link: list[str] = ["-lm"]
    if args.smoke:
        sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True)
        flags += ["-isysroot", sdk.stdout.strip()]
    else:
        flags += [f"--target={config.TRIPLE}", f"-march={config.CPU}"]
        link += ["-no-pie"]
    ir = named_ir(flags)
    counted, table = instrument(ir)
    (WORK / "counted.ll").write_text(counted)
    obj = WORK / "counted.o"
    subprocess.run(
        [config.CLANG, *flags, "-O1", "-c", "-x", "ir", WORK / "counted.ll", "-o", obj], check=True
    )
    (WORK / "dump.c").write_text(DUMP)
    exe, dump = WORK / "counted", WORK / "counts.bin"
    subprocess.run(
        [
            config.CLANG, *flags, f"-DQED_N={len(table)}", f'-DQED_OUT="{dump}"', f"-I{WORK}",
            WORK / "dump.c", WORK / "speedtest1.c", obj, *link, "-o", exe,
        ],
        check=True,
    )  # fmt: skip
    subprocess.run([exe, *project()["workload"]], check=True, stdout=subprocess.DEVNULL)
    raw = dump.read_bytes()
    total = 0
    for i, row in enumerate(table):
        row["runs"] = int.from_bytes(raw[i * 8 : i * 8 + 8], "little")
        row["weight"] = row["runs"] * row["instructions"]
        total += row["weight"]
    table.sort(key=lambda r: -r["weight"])
    zones = []
    refused: dict[str, int] = {}
    for row in table:
        if len(zones) == CANDIDATES:
            break
        if row["self_loop"]:
            why = "loop"
        elif not MIN_SIZE <= row["instructions"] <= MAX_SIZE:
            why = "size"
        else:
            src, why = zone_ir(row["function"], row["block"])
            if src:
                zones.append({**row, "share": row["weight"] / total, "src_ll": src})
                continue
        refused[why] = refused.get(why, 0) + 1
    rec = {
        "ir_sha256": hashlib.sha256(ir.encode()).hexdigest(),
        "smoke": args.smoke,
        "blocks": len(table),
        "total_weight": total,
        "top20_all_share": sum(r["weight"] for r in table[:20]) / total,
        "refused_before_candidates": refused,
        "zones": zones,
        "top_blocks": table[:40],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{len(table)} blocks, {len(zones)} candidates, {sum(z['share'] for z in zones):.1%}")


if __name__ == "__main__":
    main()
