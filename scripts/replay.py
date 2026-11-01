"""Replay a recorded win or rejection: no API call, Alive2 really runs again.
PYTHONPATH=. uv run python scripts/replay.py win
PYTHONPATH=. uv run python scripts/replay.py rejected"""

import json
import sys

from qed.verify import verify

name, check = {
    "win": ("libcxx-days-from-civil", "proven"),
    "rejected": ("linux-mult-frac", "counterexample"),
}[sys.argv[1]]
r = json.load(open(f"results/spark-full-v1/{name}.json"))
a = next(x for x in r["attempts"] if x["check"] == check)
print(f"--- {name}: recorded Muse Spark attempt {a['n']}\n{a['body']}\n")
v = verify(r["src_ll"], a["tgt_ll"])
o = a["alive2_output"]
print(f"--- Alive2, run now: {v.status.value.upper()}")
if check == "counterexample":
    print(o[o.find("Example:") : o.find("Source:")].strip())
    print(o[o.find("Source value") : o.find("Summary:")].strip())
else:
    c, b = a["cost"], r["baseline"]
    print(f"--- clang -O3: {b['asm_insts']} instructions, {b['mca_cycles']} cycles")
    print(
        f"--- rewrite:   {c['asm_insts']} instructions, {c['mca_cycles']} cycles (estimated by llvm-mca)"
    )
