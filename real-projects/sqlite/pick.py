"""Keep the zones Alive2 can work on, heaviest first, up to 20 (needs Alive2, no model call):
    PYTHONPATH=. python real-projects/sqlite/pick.py <zones.json> --out <picked.json>

The check is a correct change that does nothing, a dead instruction: a zone Alive2 cannot prove
with it has no chance with a real rewrite. This chooses zones only, it proves no rewrite."""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from qed.verify import Status, verify

LIMIT = 20


def provable(zone: dict) -> dict:
    src = zone["src_ll"]
    m = re.search(r"^  %[\w.\-]+ = (?!phi)", src, re.M)
    v = verify(src, src[: m.start()] + "  %dead = add i64 1, 1\n" + src[m.start() :])
    return {**zone, "check": v.status.value, "check_s": round(v.time, 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("zones", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=5)
    args = ap.parse_args()
    rec = json.loads(args.zones.read_text())
    with ThreadPoolExecutor(args.jobs) as e:
        checked = list(e.map(provable, rec["zones"]))
    kept = [z for z in checked if z["check"] == Status.PROVEN.value][:LIMIT]
    out = {
        "ir_sha256": rec["ir_sha256"],
        "smoke": rec["smoke"],
        "checked": [{k: v for k, v in z.items() if k != "src_ll"} for z in checked],
        "share": sum(z["share"] for z in kept),
        "zones": kept,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(
        f"{len(checked)} checked, {len(kept)} kept, {out['share']:.1%} of the executed instructions"
    )


if __name__ == "__main__":
    main()
