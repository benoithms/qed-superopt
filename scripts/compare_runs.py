"""Compare loop runs side by side:
    python scripts/compare_runs.py results/<run-a> results/<run-b> ...

Per run: functions won (proven and fewer llvm-mca cycles than clang -O3), speedups, attempts to
the first win, improvements after a first win, verdict counts, tokens and cost."""

import json
import math
import sys
from collections import Counter
from pathlib import Path


def load(run_dir: Path) -> dict[str, dict]:
    return {
        p.stem: json.loads(p.read_text()) for p in sorted(run_dir.glob("*.json")) if p.stem != "run"
    }


def first_win(res: dict) -> int | None:
    for a in res["attempts"]:
        if a.get("faster"):
            return a["n"]
    return None


def summary(name: str, runs: dict[str, dict]) -> dict:
    wins = [r for r in runs.values() if r["best"]]
    speedups = [r["best"]["speedup"] for r in wins]
    firsts = [first_win(r) for r in wins]
    improved = sum(1 for r, f in zip(wins, firsts, strict=True) if r["best"]["n"] > f)
    checks = Counter(a["check"] for r in runs.values() for a in r["attempts"])
    attempts = [a for r in runs.values() for a in r["attempts"]]
    paid = [a for a in attempts if not a.get("cached")]
    return {
        "run": name,
        "functions": len(runs),
        "won": len(wins),
        "geomean_speedup_on_wins": math.exp(sum(map(math.log, speedups)) / len(speedups))
        if speedups
        else None,
        "mean_attempts_to_first_win": sum(firsts) / len(firsts) if firsts else None,
        "improved_after_first_win": improved,
        "attempts": len(attempts),
        "checks": dict(checks),
        "reasoning_tokens": sum(a.get("tokens_reasoning", 0) for a in attempts),
        "cost_usd": sum(r["cost_usd"] for r in runs.values()),
        "paid_usd": sum(a.get("cost_usd", 0) for a in paid),
    }


def main(dirs: list[str]) -> None:
    runs = {Path(d).name: load(Path(d)) for d in dirs}
    for name, r in runs.items():
        s = summary(name, r)
        print(f"\n== {name}")
        for k, v in s.items():
            if k != "run":
                print(f"  {k:28} {round(v, 3) if isinstance(v, float) else v}")

    ids = sorted(set().union(*runs.values()))
    print("\nbest speedup per function (- = no win)")
    print(f"{'function':28}" + "".join(f"{n[-14:]:>16}" for n in runs))
    for i in ids:
        row = ""
        for r in runs.values():
            best = r.get(i, {}).get("best")
            cell = f"x{best['speedup']:.2f} (try {best['n']})" if best else "-"
            row += f"{cell:>16}"
        print(f"{i:28}{row}")


if __name__ == "__main__":
    main(sys.argv[1:])
