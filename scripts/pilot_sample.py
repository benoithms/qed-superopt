"""Draw the anchoring pilot entries: 10 B entries, fixed seed, reproducible.
Excluded: entries where llc already recovers the optimization (no asm gain on Skylake)."""

import random
from pathlib import Path

SEED = 20261028
EXCLUDED = {"llvm-issue-230022", "llvm-issue-230719"}

pool = sorted(p for p in Path("bench/B").iterdir() if p.is_dir() and p.name not in EXCLUDED)
for entry in random.Random(SEED).sample(pool, 10):
    print(entry)
