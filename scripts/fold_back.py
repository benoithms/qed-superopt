"""Does a win survive `opt -O3`? For every function a run won:
    PYTHONPATH=. python scripts/fold_back.py results/<run-id> [--min-speedup 1.05]

A proven rewrite only counts if the normal pipeline keeps it: clang runs `opt -O3` on the IR
before `llc`, so a rewrite that `opt -O3` turns back into clang's form is no gain in practice
(e.g. cmp3-i64: InstCombine re-forms llvm.scmp). Each winning tgt.ll goes through the reference
`opt -O3`, then llc + llvm-mca again; the win is kept only if the result is still faster than
clang -O3 by at least --min-speedup. Read-only: prints a table and writes nothing."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from qed import config
from qed.cost import cost
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
    after = cost(folded).mca_cycles
    back_to_src = _norm(folded) == _norm(opt_o3(src))
    return {
        "id": res["id"],
        "category": res["category"],
        "speedup": res["best"]["speedup"],
        "speedup_after_opt": base / after,
        "back_to_clang": back_to_src,
        "kept": not back_to_src and base / after > min_speedup,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument(
        "--min-speedup", type=float, default=1.0, help="kept only above this (default: any gain)"
    )
    args = ap.parse_args(argv)
    rows = []
    for p in sorted(args.run_dir.glob("*.json")):
        if p.name == "run.json":
            continue
        res = json.loads(p.read_text())
        if res["best"]:
            rows.append(check(res, args.min_speedup))

    print(f"{'cat':4}{'function':30}{'speedup':>9}{'after opt':>11}  verdict")
    for r in sorted(rows, key=lambda r: (r["category"], r["id"])):
        verdict = (
            "kept"
            if r["kept"]
            else "folded back to clang"
            if r["back_to_clang"]
            else "below threshold"
        )
        print(
            f"{r['category']:4}{r['id']:30}{r['speedup']:>8.2f}x{r['speedup_after_opt']:>10.2f}x"
            f"  {verdict}"
        )
    kept = [r for r in rows if r["kept"]]
    by_cat = {c: sum(r["category"] == c for r in kept) for c in "ABC"}
    print(f"\n{len(kept)} of {len(rows)} wins kept after opt -O3 " + str(by_cat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
