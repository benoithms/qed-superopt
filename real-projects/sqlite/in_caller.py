"""Does a zone's gain survive next to the code that uses it? Read-only, no model call:
    PYTHONPATH=. python real-projects/sqlite/in_caller.py <results/.../spark>

A zone returns an exit code that the program branches on right away. llvm-mca on the zone alone
misses that branch, so a rewrite that only moves the branch into the code looks faster. Here each
zone is inlined into a caller that uses all its outputs and branches on an i1 exit code, then goes
through opt -O3 and llc, for the source and for the rewrite. An exit code of another type is not
branched on, so those zones show nothing here."""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from qed import config

OPT = [config.OPT, "-O3", f"-mtriple={config.TRIPLE}", f"-mcpu={config.CPU}", "-S"]


def in_caller(ll: str) -> str:
    m = re.search(r"^define (\{[^}]*\}) @([\w.]+)\((.*?)\) \{", ll, re.M)
    rty, name, args = m[1], m[2], m[3]
    fields = rty[2:-2].split(", ")
    ll = ll.replace(f"define {rty}", f"define internal {rty}", 1).replace(
        ") {\n", ") alwaysinline {\n", 1
    )
    names = ", ".join(args.split(", "))
    s = f"declare void @use({', '.join(fields)})\ndeclare void @a()\ndeclare void @b()\n"
    s += f"define void @caller({args}) {{\n  %r = call {rty} @{name}({names})\n"
    for i in range(len(fields)):
        s += f"  %f{i} = extractvalue {rty} %r, {i}\n"
    used = ", ".join(f"{t} %f{i}" for i, t in enumerate(fields))
    s += f"  call void @use({used})\n"
    if fields[0] == "i1":
        s += "  br i1 %f0, label %x, label %y\nx:\n  call void @a()\n  ret void\n"
        s += "y:\n  call void @b()\n  ret void\n}\n"
    else:
        s += "  ret void\n}\n"
    return f"{ll}\n{s}"


def asm(ll: str) -> list[str]:
    with tempfile.TemporaryDirectory() as d:
        src, opt, out = Path(d) / "a.ll", Path(d) / "b.ll", Path(d) / "b.s"
        src.write_text(ll)
        opt.write_text(
            subprocess.run([*OPT, src], capture_output=True, text=True, check=True).stdout
        )
        subprocess.run([config.LLC, *config.LLC_FLAGS, opt, "-o", out], check=True)
        text = out.read_text()
    fn = text[text.index("caller:") : text.index(".Lfunc_end", text.index("caller:"))]
    return [
        x.strip()
        for x in fn.splitlines()
        if x.startswith("\t") and not x.startswith(("\t.", "\t#"))
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    args = ap.parse_args()
    for path in sorted(args.run.glob("*.json")):
        if path.name == "run.json":
            continue
        res = json.loads(path.read_text())
        if not res.get("best"):
            print(f"{path.stem}: no rewrite kept")
            continue
        tgt = next(a for a in res["attempts"] if a["n"] == res["best"]["n"])["tgt_ll"]
        a, b = asm(in_caller(res["src_ll"])), asm(in_caller(tgt))
        verdict = (
            "identical" if a == b else "same instructions" if sorted(a) == sorted(b) else "differs"
        )
        print(f"{path.stem}: alone x{res['best']['speedup']:.2f}, {len(a)} -> {len(b)}, {verdict}")


if __name__ == "__main__":
    main()
