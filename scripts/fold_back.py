"""Which wins hold? For every function a run won:
    PYTHONPATH=. python scripts/fold_back.py results/<run-id> [--min-speedup 1.05]

A proven rewrite only counts if the normal pipeline keeps it: clang runs `opt -O3` on the IR
before `llc`, so a rewrite that `opt -O3` turns back into clang's form is no gain in practice
(e.g. cmp3-i64: InstCombine re-forms llvm.scmp). Each winning tgt.ll goes through the reference
`opt -O3`, then llc + llvm-mca again, in two measures that must both beat clang -O3 by more than
--min-speedup (5%, the threshold fixed for both models):
- chained: llvm-mca's default, 100 calls back to back (what cost() reports). A register reused
  as a temporary then delays the next call's argument, a dependency no real caller has;
- one call: llvm-mca -iterations=1, independent of the next call.
llvm-mca reads a function as one straight line, both sides of a branch included, which favors
branch-free code: a win with a branch in clang's or the rewrite's assembly is marked "confirm on
CPU" (i7-9700K, predictable and random inputs). Read-only: prints a table and writes nothing."""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from qed import config
from qed.cost import asm_instructions, cost
from qed.extract import body, function

OPT_FLAGS = ["-O3", f"-mtriple={config.TRIPLE}", f"-mcpu={config.CPU}", "-S"]


def opt_o3(ll: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "f.ll"
        path.write_text(ll)
        p = subprocess.run(
            [config.OPT, *OPT_FLAGS, path, "-o", "-"], capture_output=True, text=True
        )
    if p.returncode:
        raise RuntimeError(f"opt: {p.stderr.strip()}")
    return p.stdout


def one_call_cycles(ll: str) -> int:
    """llvm-mca Total Cycles for a single call (-iterations=1)."""
    with tempfile.TemporaryDirectory() as d:
        src, asm = Path(d) / "f.ll", Path(d) / "f.s"
        src.write_text(ll)
        for cmd in (
            [config.LLC, *config.LLC_FLAGS, src, "-o", asm],
            [config.LLVM_MCA, *config.MCA_FLAGS, "-iterations=1", asm, "-o", Path(d) / "mca"],
        ):
            p = subprocess.run(cmd, capture_output=True, text=True)
            if p.returncode:
                raise RuntimeError(f"{Path(cmd[0]).name}: {p.stderr.strip()}")
        mca = (Path(d) / "mca").read_text()
    return int(re.search(r"^Total Cycles:\s+(\d+)", mca, re.M).group(1))


def has_branch(fn_asm: str) -> bool:
    return any(i.split()[0].startswith("j") for i in asm_instructions(fn_asm))


def _norm(ll: str) -> str:
    return "\n".join(line.strip() for line in body(function(ll)).splitlines() if line.strip())


def winning_attempt(res: dict) -> dict:
    """The proven attempt behind res["best"] (from the fallback model when it won)."""
    best, fb = res["best"], res.get("fallback")
    run = fb if fb and best.get("model") == fb["model"] else res
    return next(a for a in run["attempts"] if a["n"] == best["n"] and a["check"] == "proven")


def check(res: dict, min_speedup: float) -> dict:
    src, tgt = res["src_ll"], winning_attempt(res)["tgt_ll"]
    base = res["baseline"]["mca_cycles"]
    folded = opt_o3(tgt)
    c = cost(folded)
    back_to_src = _norm(folded) == _norm(opt_o3(src))
    chained, one_call = base / c.mca_cycles, one_call_cycles(src) / one_call_cycles(folded)
    return {
        "id": res["id"],
        "category": res["category"],
        "speedup": res["best"]["speedup"],
        "chained": chained,
        "one_call": one_call,
        "back_to_clang": back_to_src,
        "kept": not back_to_src and chained > min_speedup and one_call > min_speedup,
        "branch": has_branch(res["baseline"]["asm"]) or has_branch(c.asm),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument(
        "--min-speedup", type=float, default=1.05, help="kept only above this (default: 5%%)"
    )
    args = ap.parse_args(argv)
    rows = []
    for p in sorted(args.run_dir.glob("*.json")):
        if p.name == "run.json":
            continue
        res = json.loads(p.read_text())
        if res["best"]:
            rows.append(check(res, args.min_speedup))

    print(f"{'cat':4}{'function':30}{'loop':>8}{'chained':>9}{'one call':>10}  verdict")
    for r in sorted(rows, key=lambda r: (r["category"], r["id"])):
        if r["back_to_clang"]:
            verdict = "folded back to clang"
        elif not r["kept"]:
            verdict = "below threshold"
        else:
            verdict = "kept, confirm on CPU (branch)" if r["branch"] else "kept"
        print(
            f"{r['category']:4}{r['id']:30}{r['speedup']:>7.2f}x{r['chained']:>8.2f}x"
            f"{r['one_call']:>9.2f}x  {verdict}"
        )
    kept = [r for r in rows if r["kept"]]
    solid = [r for r in kept if not r["branch"]]
    by_cat = {c: sum(r["category"] == c for r in kept) for c in "ABC"}
    print(f"\n{len(kept)} of {len(rows)} wins kept in both measures {by_cat}")
    print(f"{len(solid)} without any branch; {len(kept) - len(solid)} to confirm on the i7-9700K")
    return 0


if __name__ == "__main__":
    sys.exit(main())
