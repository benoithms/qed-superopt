"""Re-check everything with the reference toolchain, from the files only:
    PYTHONPATH=. python scripts/verify_all.py            # corpus + every recorded proof
    PYTHONPATH=. python scripts/verify_all.py --corpus   # corpus only

Corpus: each entry against the CLAUDE.md rules (meta, size, category), and every expected.ll
proven by Alive2 and faster than clang -O3 in llvm-mca cycles. Results: every attempt
recorded as proven in results/*/*.json is proven again by Alive2, and the stored hashes must
match the stored files. Lists every problem found and exits with 1 if there is any."""

import argparse
import json
import sys
from pathlib import Path

from qed.cost import cost, ir_instructions
from qed.extract import extract, function, splice
from qed.verify import Status, sha256, verify


def check_corpus() -> list[str]:
    problems = []
    for e in sorted(Path("bench").glob("*/*")):
        cat = e.parent.name
        meta = json.loads((e / "meta.json").read_text())
        if meta.get("category") != cat or meta.get("id") != e.name:
            problems.append(f"{e}: meta id/category mismatch")
        if not meta.get("source"):
            problems.append(f"{e}: no source")
        src = extract(e / "src.c")
        n = ir_instructions(function(src))
        if n > 30 or (cat == "C" and n < 5):
            problems.append(f"{e}: {n} IR instructions")
        exp = e / "expected.ll"
        if exp.exists() and cat != "B":
            problems.append(f"{e}: expected.ll outside B")
        if exp.exists():
            tgt = splice(src, exp.read_text())
            r = verify(src, tgt)
            if r.status is not Status.PROVEN:
                problems.append(f"{e}: expected.ll {r.status.value}")
            elif cost(tgt).mca_cycles >= cost(src).mca_cycles:
                problems.append(f"{e}: expected.ll not faster")
    return problems


def recorded_proofs():
    for p in sorted(Path("results").glob("*/*.json")):
        if p.name == "run.json":
            continue
        res = json.loads(p.read_text())
        for run in [res] + ([res["fallback"]] if res.get("fallback") else []):
            for a in run["attempts"]:
                if a.get("check") == "proven":
                    yield f"{p} ({run['model']} attempt {a['n']})", run, a


def check_results() -> tuple[int, list[str]]:
    problems, n = [], 0
    for where, run, a in recorded_proofs():
        n += 1
        if sha256(run["src_ll"]) != run["src_sha256"] or sha256(a["tgt_ll"]) != a["tgt_sha256"]:
            problems.append(f"{where}: hash mismatch")
            continue
        r = verify(run["src_ll"], a["tgt_ll"])
        if r.status is not Status.PROVEN:
            problems.append(f"{where}: {r.status.value}")
    return n, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", action="store_true", help="corpus only")
    args = ap.parse_args()
    problems = check_corpus()
    print(f"corpus: {len(list(Path('bench').glob('*/*')))} entries, {len(problems)} problems")
    if not args.corpus:
        n, more = check_results()
        print(f"results: {n} recorded proofs, {len(more)} problems")
        problems += more
    if problems:
        print("\n".join(problems))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
