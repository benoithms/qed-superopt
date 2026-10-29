"""Draw pilot entries with a fixed seed, reproducibly.

    PYTHONPATH=. python scripts/pilot_sample.py          # anchoring pilot: 10 B entries
    PYTHONPATH=. python scripts/pilot_sample.py --category C --n 5 --min-insts 10
    PYTHONPATH=. python scripts/pilot_sample.py --seed 20261029 --exclude-run results/pilot-wonder

Excluded: C entries Jules moved to B (their solution is known).
The draw depends on the corpus at the time: the exact entries of a past run are in its run.json."""

import argparse
import random
from pathlib import Path

from qed.cost import ir_instructions
from qed.extract import extract, function

SEED = 20261028
EXCLUDED = {"clp2-u32", "nlz-binsearch-u32"}

ap = argparse.ArgumentParser()
ap.add_argument("--category", default="B")
ap.add_argument("--n", type=int, default=10)
ap.add_argument("--min-insts", type=int, default=0)
ap.add_argument("--seed", type=int, default=SEED)
ap.add_argument(
    "--exclude-run", type=Path, action="append", default=[], help="skip entries of this run"
)
args = ap.parse_args()
seen = {p.stem for d in args.exclude_run for p in d.glob("*.json")}

pool = []
for p in sorted(Path("bench", args.category).iterdir()):
    if p.is_dir() and p.name not in EXCLUDED | seen:
        if ir_instructions(function(extract(p / "src.c"))) >= args.min_insts:
            pool.append(p)
for entry in random.Random(args.seed).sample(pool, args.n):
    print(entry)
