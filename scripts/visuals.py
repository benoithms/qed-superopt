"""Draw the visuals meant for people who do not know LLVM, from the recorded JSON files only:
    PYTHONPATH=.:scripts uv run python scripts/visuals.py [--out charts]

skyline.png: every win confirmed on both CPUs, its worst and best timing against clang -O3.
saved.png: every win confirmed on both CPUs, the time it saves, median of its timings.
squares.png: the 134 functions, one square each, colored by the last check they passed.
Timings: the 8 of a win (4 measures on each of 2 CPUs). Prints what it draws."""

import argparse
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from charts import CPUS, LIGHT, RUNS, numbers  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

RUN = RUNS["Muse Spark"]
MEASURES = ["predictable", "random", "predictable_inline", "random_inline"]
INK, MUTED, SURFACE, ACCENT = LIGHT["ink"], LIGHT["muted"], LIGHT["surface"], LIGHT["series"][0]
STAGES = ["#ecebe6", "#d9d8d2", "#bdbcb5", "#96958e", ACCENT]
GROUPS = {
    "B": ("#2563eb", "with a known better solution"),
    "C": ("#d9730d", "with no known better solution"),
    "A": ("#7a7a7a", "controls clang already handles"),
}


def timings() -> dict[str, list[float]]:
    """The 8 timings (4 measures on each of 2 CPUs) of each win confirmed on both CPUs."""
    benches = []
    for folder in CPUS.values():
        results = json.loads(Path(folder, f"{RUN}.json").read_text())["results"]
        benches.append({e["id"]: e for e in results if e["overall"] == "confirmed"})
    return {
        fid: [b[fid][m]["speedup"] for b in benches for m in MEASURES]
        for fid in benches[0]
        if fid in benches[1]
    }


def columns(subtitle: str, note: str, figsize=(12, 6.75), bottom=0.12):
    fig, ax = plt.subplots(figsize=figsize, facecolor=SURFACE)
    fig.subplots_adjust(left=0.13 * 12 / figsize[0], right=0.985, top=0.9, bottom=bottom)
    ax.set_facecolor(SURFACE)
    ax.set_xticks([])
    ax.margins(x=0.01)
    ax.tick_params(colors=MUTED, length=0, labelsize=13)
    ax.grid(axis="y", color=MUTED, alpha=0.18)
    ax.set_axisbelow(True)
    for name, side in ax.spines.items():
        side.set_visible(name == "bottom")
        side.set_color(MUTED)
    fig.text(0.02, 0.945, subtitle, color=INK, fontsize=17, weight="bold")
    fig.text(0.02, 0.02, note, color=MUTED, fontsize=11, va="bottom")
    return fig, ax


def skyline(out: Path):
    """Every confirmed win, unnamed: its worst, median and best timing, with their numbers."""
    rows = sorted(timings().items(), key=lambda kv: -max(kv[1]))
    print("skyline", len(rows), [(f, round(min(t), 2), round(max(t), 2)) for f, t in rows[:3]])
    print("worst under 1x:", sum(min(t) < 1 for _, t in rows))
    funnel = numbers(RUN)["funnel"]
    fig, ax = columns(
        f"{len(rows)} of {funnel['Corpus']} small functions are confirmed faster after our rewrite "
        "than with clang -O3",
        "Small: at most 30 LLVM IR instructions after clang -O3, no loops. "
        "Every rewrite is formally proven correct (refinement). x86-64 Skylake target.\n"
        f"{funnel['Kept by our rule']} of the {funnel['Corpus']} reached CPU timing. "
        "Timed 8 ways: called or inlined, predictable or random inputs, on an i7-9700K and an "
        "i7-12700H; 5 launches each,\n"
        "loop overhead included. Confirmed: on each CPU, over 1.05x in every launch in at least "
        "one way, and under 0.98x in every launch in none.\n"
        "Bars start at 1x, the speed of clang -O3.",
        figsize=(17, 9),
        bottom=0.23,
    )
    xs = list(range(len(rows)))
    best = [max(t) for _, t in rows]
    worst = [min(t) for _, t in rows]
    groups = {d.name: d.parent.name for d in Path("bench").glob("*/*") if d.is_dir()}
    colors = [GROUPS[groups[fid]][0] for fid, _ in rows]
    ax.bar(xs, [v - 1 for v in best], 0.8, bottom=1, color=colors, alpha=0.28)
    ax.bar(xs, [max(v, 1) - 1 for v in worst], 0.8, bottom=1, color=colors)
    median = [statistics.median(t) for _, t in rows]
    ax.scatter(xs, median, s=30, color=INK, zorder=3)
    handles = []
    for group, (color, label) in GROUPS.items():
        won = sum(groups[fid] == group for fid, _ in rows)
        size = sum(g == group for g in groups.values())
        print("group", group, won, size)
        handles.append(Patch(color=color, label=f"{won} of {size} {label}"))
    handles += [
        Patch(color=MUTED, alpha=0.28, label="Light: best timing"),
        Patch(color=MUTED, label="Dark: worst timing"),
        Line2D([], [], marker="o", color=INK, ls="", label="Dot: median timing"),
    ]
    for x in xs:
        ax.text(
            x,
            best[x] + 0.08,
            f"{best[x]:.2f}",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=9,
            rotation=90,
        )
        ax.text(
            x, 0.93, f"{median[x]:.2f}", ha="center", va="top", color=INK, fontsize=9, rotation=90
        )
        ax.text(
            x,
            0.38,
            f"{worst[x]:.2f}",
            ha="center",
            va="top",
            color=colors[x],
            fontsize=9,
            rotation=90,
        )
    ax.text(-0.8, 0.72, "median", ha="right", va="center", color=INK, fontsize=10)
    ax.text(-0.8, 0.17, "worst", ha="right", va="center", color=MUTED, fontsize=10)
    ax.set_ylabel("Speedup over clang -O3 (times faster)", color=INK, fontsize=14, labelpad=10)
    ax.set_xlabel(
        f"The {len(rows)} functions, sorted by best timing", color=INK, fontsize=14, labelpad=62
    )
    ax.set_ylim(1, 10.8)
    ax.set_yticks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ["1x", *(f"{v}x" for v in range(2, 11))])
    ax.legend(handles=handles, frameon=False, fontsize=14, labelcolor=INK, loc="upper right")
    save(fig, out, "skyline")


def saved(out: Path):
    """Every confirmed win: how much less time the rewrite takes, median of the 8 timings."""
    rows = sorted((100 * (1 - 1 / statistics.median(t)) for t in timings().values()), reverse=True)
    print("saved", len(rows), round(rows[0]), round(statistics.median(rows)), round(rows[-1]))
    fig, ax = columns(
        f"{len(timings())} functions, proven correct: time saved over clang -O3",
        f"All {len(rows)} wins confirmed on 2 CPUs. Formally proven correct. Median of 8 timings.",
    )
    ax.bar(range(len(rows)), rows, 0.8, color=ACCENT)
    ax.set_ylim(0, 100)
    ax.set_yticks(
        [0, 25, 50, 75, 100], ["clang -O3", "25% less", "50% less", "75% less", "100% less"]
    )
    save(fig, out, "saved")


def squares(out: Path):
    f = numbers(RUN)["funnel"]
    counts = [
        ("No proven rewrite", f["Corpus"] - f["Proven rewrite"]),
        (
            "Proven correct, but not faster",
            f["Proven rewrite"] - f["Faster, estimated by llvm-mca"],
        ),
        (
            "Looked faster, failed our stricter rule",
            f["Faster, estimated by llvm-mca"] - f["Kept by our rule"],
        ),
        (
            "Passed our rule, not confirmed on both CPUs",
            f["Kept by our rule"] - f["Confirmed on both CPUs"],
        ),
        ("Proven correct and faster on both CPUs", f["Confirmed on both CPUs"]),
    ]
    print("squares", counts)
    colors = [STAGES[i] for i, (_, n) in enumerate(counts) for _ in range(n)]
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor=SURFACE)
    fig.subplots_adjust(left=0.04, right=0.55, top=0.8, bottom=0.06)
    ax.set_facecolor(SURFACE)
    ax.axis("off")
    per_row = 14
    for i, color in enumerate(reversed(colors)):
        ax.add_patch(Rectangle((i % per_row, -(i // per_row)), 0.86, 0.86, color=color))
    ax.set_xlim(0, per_row)
    ax.set_ylim(-(len(colors) // per_row) - 0.2, 1)
    ax.set_aspect("equal")
    fig.text(
        0.04, 0.88, f"{f['Corpus']} functions. {counts[-1][1]} real wins.", color=INK, fontsize=28
    )
    for i, (label, n) in enumerate(reversed(counts)):
        y = 0.72 - i * 0.12
        fig.patches.append(
            Rectangle(
                (0.58, y - 0.008), 0.022, 0.039, color=STAGES[4 - i], transform=fig.transFigure
            )
        )
        fig.text(0.612, y + 0.012, str(n), color=INK, fontsize=20, weight="bold", va="center")
        fig.text(
            0.665,
            y + 0.012,
            label.replace(", ", ",\n", 1),
            color=INK if i == 0 else MUTED,
            fontsize=13,
            va="center",
        )
    save(fig, out, "squares")


def save(fig, out: Path, name: str):
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"{name}.png", dpi=200)
    fig.savefig(out / f"{name}.svg")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path("charts"))
    args = ap.parse_args()
    skyline(args.out)
    saved(args.out)
    squares(args.out)


if __name__ == "__main__":
    main()
