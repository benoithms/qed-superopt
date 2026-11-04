"""Step 3 of the protocol: QED on the picked zones, with the usual loop, proofs and wallet:
    PYTHONPATH=. python real-projects/sqlite/search.py <picked.json> --max-total 10 [--dry-run]

Each zone becomes a corpus-like entry in work/entries. The loop reads its IR instead of compiling
C, and the prompt allows the loads and stores the zone already has: Alive2 checks them like the
rest. --dry-run only measures each zone, with no model call."""

import argparse
import json
from pathlib import Path

from qed import llm, loop
from qed.cost import cost

HERE = Path(__file__).parent
ENTRIES = HERE / "work" / "entries"
NO_MEMORY = "No memory access, no other function."
ZONE_RULES = (
    "No other function. Loads and stores are allowed, and every write must stay the same for "
    "every input, in the same order relative to other memory accesses unless they cannot alias."
)
NAMES = "Parameters keep their names (%0, %1, ...)."


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("picked", type=Path)
    ap.add_argument("--max-total", type=float, default=10)
    ap.add_argument("--run-id", default="real-projects/sqlite/spark")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.max_total > 10:
        raise SystemExit("the protocol caps this test at $10")
    entries = []
    for i, zone in enumerate(json.loads(args.picked.read_text())["zones"]):
        entry = ENTRIES / f"{i:02d}-{zone['function']}-{zone['block']}"
        entry.mkdir(parents=True, exist_ok=True)
        (entry / "src.ll").write_text(zone["src_ll"])
        (entry / "src.c").write_text("")
        entries.append(entry)
        if args.dry_run:
            c = cost(zone["src_ll"])
            print(entry.name, c.ir_insts, c.asm_insts, f"{c.mca_cycles:.2f}")
    if args.dry_run:
        return
    if NO_MEMORY not in llm.SYSTEM or NAMES not in llm.SYSTEM:
        raise SystemExit("the prompt changed: review this script")
    llm.SYSTEM = llm.SYSTEM.replace(NO_MEMORY, ZONE_RULES).replace(
        NAMES, "Parameters keep their names."
    )
    loop.extract = lambda path: (Path(path).parent / "src.ll").read_text()
    loop.main(
        [*map(str, entries), "--run-id", args.run_id, "--jobs", str(args.jobs)]
        + ["--max-total", str(args.max_total)]
    )


if __name__ == "__main__":
    main()
