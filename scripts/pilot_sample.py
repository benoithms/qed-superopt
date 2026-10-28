"""Draw pilot entries with a fixed seed, reproducibly.

    PYTHONPATH=. python scripts/pilot_sample.py          # anchoring pilot: 10 B entries
    PYTHONPATH=. python scripts/pilot_sample.py --category C --n 5 --min-insts 10

Excluded: entries where llc already recovers the optimization (no asm gain on Skylake), and
C entries Jules moved to B (their solution is known)."""

import argparse
import random
from pathlib import Path

from qed.cost import ir_instructions
from qed.extract import extract, function

SEED = 20261028
EXCLUDED = {"llvm-issue-230022", "llvm-issue-230719", "clp2-u32", "nlz-binsearch-u32"}

ap = argparse.ArgumentParser()
ap.add_argument("--category", default="B")
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--min-insts", type=int, default=0)
args = ap.parse_args()

pool = []
for p in sorted(Path("bench", args.category).iterdir()):
    if p.is_dir() and p.name not in EXCLUDED:
        if ir_instructions(function(extract(p / "src.c"))) >= args.min_insts:
            pool.append(p)
for entry in random.Random(SEED).sample(pool, args.n):
    print(entry)
