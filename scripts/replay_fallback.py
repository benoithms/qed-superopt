"""Replay fallback policies offline, at no cost, from two complete runs on the same functions:
    python scripts/replay_fallback.py --primary results/<spark> --fallback results/<wonder>
    python scripts/replay_fallback.py --cascade results/<run with --fallback-when always>

The fallback run must have used at least as many attempts as the largest cap replayed. Its first
k attempts are exactly what a k-attempt run would have produced (attempts are sequential), so
each policy x cap pair can be evaluated without calling the model again.

A real gain is a fallback win where the primary model had none, or a fallback version at least
GAIN_MARGIN faster (fewer llvm-mca cycles) than the primary's best."""

import argparse
import json
from pathlib import Path

from qed.loop import FALLBACK_POLICIES, wants_fallback

GAIN_MARGIN = 0.02
CAPS = (1, 2, 3, 5)


def load(dirs: list[Path]) -> dict[str, dict]:
    runs = {}
    for d in dirs:
        runs |= {p.stem: json.loads(p.read_text()) for p in d.glob("*.json") if p.stem != "run"}
    return runs


def split(dirs: list[Path]) -> tuple[dict[str, dict], dict[str, dict]]:
    """Primary and fallback results of a cascade run (loop.py --fallback-model)."""
    primary, fallback = {}, {}
    for i, res in load(dirs).items():
        fb = res["fallback"]
        spent = res["cost_usd"] - (fb["cost_usd"] if fb else 0.0)
        primary[i] = {**res, "best": res["primary_best"], "cost_usd": spent}
        if fb:
            fallback[i] = fb
    return primary, fallback


def truncated(res: dict, cap: int) -> tuple[float | None, float]:
    """Best cycles and cost of the fallback run had it stopped after `cap` attempts."""
    kept = [a for a in res["attempts"] if a["n"] <= cap]
    wins = [a["cost"]["mca_cycles"] for a in kept if a.get("faster")]
    return (min(wins) if wins else None), sum(a.get("cost_usd", 0.0) for a in kept)


def gain(primary: dict, cycles: float | None) -> bool:
    if cycles is None:
        return False
    if primary["best"] is None:
        return True
    return cycles <= primary["best"]["mca_cycles"] * (1 - GAIN_MARGIN)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--primary", nargs="+", type=Path)
    ap.add_argument("--fallback", nargs="+", type=Path)
    ap.add_argument("--cascade", nargs="+", type=Path)
    args = ap.parse_args(argv)
    if args.cascade:
        primary, fallback = split(args.cascade)
    elif args.primary and args.fallback:
        primary, fallback = load(args.primary), load(args.fallback)
    else:
        ap.error("give --cascade, or both --primary and --fallback")
    ids = sorted(primary.keys() & fallback.keys())
    missing = sorted(primary.keys() ^ fallback.keys())
    print(f"{len(ids)} functions in both runs" + (f", ignored: {missing}" if missing else ""))

    gains_at = {}
    for i in ids:
        for n in range(1, max(CAPS) + 1):
            if gain(primary[i], truncated(fallback[i], n)[0]):
                gains_at[i] = n
                break
    print("attempt of the first real gain:", gains_at)

    print(f"\n{'policy':20}{'cap':>4}{'called':>8}{'gains':>7}{'fallback $':>12}{'$/gain':>9}")
    for policy in FALLBACK_POLICIES:
        called = [i for i in ids if wants_fallback(primary[i], policy)]
        for cap in CAPS:
            replays = [truncated(fallback[i], cap) for i in called]
            gains = sum(gain(primary[i], c) for i, (c, _) in zip(called, replays, strict=True))
            usd = sum(u for _, u in replays)
            per = f"{usd / gains:.2f}" if gains else "-"
            print(f"{policy:20}{cap:>4}{len(called):>8}{gains:>7}{usd:>12.2f}{per:>9}")
    print(f"\nprimary cost (always paid): ${sum(primary[i]['cost_usd'] for i in ids):.2f}")


if __name__ == "__main__":
    main()
