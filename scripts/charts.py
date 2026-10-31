"""Draw the result charts from the recorded JSON files only:
    PYTHONPATH=.:scripts uv run python scripts/charts.py [--dark] [--out charts]

funnel.png: from the corpus to the wins confirmed on both CPUs, per model.
confirmed.png: the wins confirmed on both CPUs, per corpus group.
attempts.png: functions with a faster proven rewrite, by attempt.
mca_vs_cpu.png: each kept win, llvm-mca's estimate against the speedup timed on the i7-9700K.
cpu_vs_cpu.png: each kept win, the speedup timed on one CPU against the other.
Timings are inline with predictable inputs: no call floor, one fixed measure for every win.
Prints the numbers it draws."""

import argparse
import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fold_back import check  # noqa: E402

RUNS = {"Muse Spark": "spark-full-v1", "LLM Compiler": "llmc-full-az4"}
CPUS = {"i7-9700K": "results/bench-9700k", "i7-12700H": "results/bench-12700h"}
MEASURE = "predictable_inline"
GROUPS = {"B": "Known misses", "C": "Open functions", "A": "Controls"}
LIGHT = dict(surface="#fcfcfb", ink="#0b0b0b", muted="#52514e", series=["#2a78d6", "#eb6834"])
DARK = dict(surface="#1a1a19", ink="#f0efec", muted="#c3c2b7", series=["#3987e5", "#d95926"])


def confirmed(run: str, folder: str) -> dict[str, str]:
    bench = json.loads(Path(folder, f"{run}.json").read_text())
    return {e["id"]: e["category"] for e in bench["results"] if e["overall"] == "confirmed"}


def numbers(run: str) -> dict:
    paths = [p for p in Path("results", run).glob("*.json") if p.name != "run.json"]
    res = [json.loads(p.read_text()) for p in paths]
    proven = [r for r in res if any(a.get("check") == "proven" for a in r["attempts"])]
    bench = json.loads(Path(CPUS["i7-9700K"], f"{run}.json").read_text())
    a, b = (confirmed(run, folder) for folder in CPUS.values())
    both = [a[i] for i in a if i in b]
    return {
        "funnel": {
            "Corpus": len(list(Path("bench").glob("*/*"))),
            "Proven rewrite": len(proven),
            "Faster, estimated by llvm-mca": sum(1 for r in res if r["best"]),
            "Kept by our rule": len(bench["results"]),
            "Confirmed on both CPUs": len(both),
        },
        "groups": {g: both.count(g) for g in GROUPS},
    }


def grouped(ax, labels, series, theme):
    height = 0.36
    top = max(max(v) for v in series.values())
    for i, (name, values) in enumerate(series.items()):
        ys = [y + (i - 0.5) * (height + 0.03) for y in range(len(labels))]
        ax.barh(ys, values, height, color=theme["series"][i], label=name)
        for y, v in zip(ys, values, strict=True):
            ax.text(v + top * 0.008, y, str(v), va="center", color=theme["ink"], fontsize=13)
    ax.set_yticks(range(len(labels)), labels, color=theme["ink"], fontsize=13)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_xlim(0, top * 1.06)
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    legend = ax.legend(frameon=False, loc="lower right", fontsize=13)
    for text in legend.get_texts():
        text.set_color(theme["ink"])


def draw(name, title, note, labels, series, theme, out):
    fig, ax = plt.subplots(figsize=(11, 6), facecolor=theme["surface"], layout="constrained")
    ax.set_facecolor(theme["surface"])
    grouped(ax, labels, series, theme)
    ax.set_title(title, loc="left", color=theme["ink"], fontsize=18, pad=14)
    fig.supxlabel(note, x=0.01, ha="left", color=theme["muted"], fontsize=11)
    out.mkdir(exist_ok=True)
    fig.get_layout_engine().set(h_pad=0.15, w_pad=0.15)
    fig.savefig(out / f"{name}.png", dpi=200)
    fig.savefig(out / f"{name}.svg")


def attempts_by_function(run: str) -> list[int]:
    """Functions with a faster proven rewrite after attempts 1 to 5."""
    first = []
    for p in Path("results", run).glob("*.json"):
        if p.name != "run.json":
            res = json.loads(p.read_text())
            first.append(next((a["n"] for a in res["attempts"] if a.get("faster")), None))
    return [sum(1 for n in first if n and n <= k) for k in range(1, 6)]


def timed(run: str, folder: str) -> dict[str, float]:
    bench = json.loads(Path(folder, f"{run}.json").read_text())
    return {e["id"]: e[MEASURE]["speedup"] for e in bench["results"]}


def estimated(run: str, ids) -> dict[str, float]:
    """llvm-mca's speedup as our rule reads it: the better of throughput and one-call latency."""
    out = {}
    for fid in ids:
        r = check(json.loads(Path("results", run, f"{fid}.json").read_text()), 1.05)
        out[fid] = max(r["throughput"], r["latency"])
    return out


def axes(theme, title, xlabel, ylabel, note):
    fig, ax = plt.subplots(figsize=(8, 7), facecolor=theme["surface"], layout="constrained")
    ax.set_facecolor(theme["surface"])
    ax.set_title(title, loc="left", color=theme["ink"], fontsize=15, pad=12)
    ax.set_xlabel(xlabel, color=theme["ink"], fontsize=12)
    ax.set_ylabel(ylabel, color=theme["ink"], fontsize=12)
    ax.tick_params(colors=theme["muted"], which="both")
    ax.grid(color=theme["muted"], alpha=0.2, linewidth=0.8)
    for name, side in ax.spines.items():
        side.set_visible(name in ("left", "bottom"))
        side.set_color(theme["muted"])
    fig.supxlabel(note, x=0.01, ha="left", color=theme["muted"], fontsize=10)
    fig.get_layout_engine().set(h_pad=0.15, w_pad=0.15)
    return fig, ax


def finish(fig, ax, name, theme, out):
    legend = ax.legend(frameon=False, fontsize=11)
    for text in legend.get_texts():
        text.set_color(theme["ink"])
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"{name}.png", dpi=200)
    fig.savefig(out / f"{name}.svg")


def scatter(name, points, title, xlabel, ylabel, note, theme, out):
    fig, ax = axes(theme, title, xlabel, ylabel, note)
    values = [v for xs, ys in points.values() for v in xs + ys]
    low, high = min(values) * 0.95, max(values) * 1.05
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.plot([low, high], [low, high], color=theme["muted"], linewidth=1, label="Same speedup")
    ax.axhline(1, color=theme["muted"], linewidth=1, linestyle=":")
    ax.axvline(1, color=theme["muted"], linewidth=1, linestyle=":", label="No change (1x)")
    for i, (model, (xs, ys)) in enumerate(points.items()):
        ax.scatter(xs, ys, s=55, color=theme["series"][i], edgecolor=theme["surface"], label=model)
    ticks = [t for t in (0.7, 1, 1.5, 2, 3, 5, 7) if low <= t <= high]
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(matplotlib.ticker.FixedLocator(ticks))
        axis.set_major_formatter(lambda v, _: f"{v:g}x")
        axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_aspect("equal")
    finish(fig, ax, name, theme, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--out", type=Path, default=Path("charts"))
    args = ap.parse_args()
    theme = DARK if args.dark else LIGHT
    data = {model: numbers(run) for model, run in RUNS.items()}
    print(json.dumps(data, indent=2))

    draw(
        "funnel",
        "qed-superopt: what survives each check, by model",
        "Every win is proven correct (refinement) by Alive2. Up to 5 attempts per function.",
        list(data["Muse Spark"]["funnel"]),
        {m: list(d["funnel"].values()) for m, d in data.items()},
        theme,
        args.out,
    )
    draw(
        "confirmed",
        "Wins confirmed on both CPUs, by group",
        "Timed on an i7-9700K and an i7-12700H. Controls were expected to have nothing to gain.",
        list(GROUPS.values()),
        {m: [d["groups"][g] for g in GROUPS] for m, d in data.items()},
        theme,
        args.out,
    )

    fig, ax = axes(
        theme,
        "Functions with a faster proven rewrite, by attempt",
        "Attempt",
        "Functions (out of 134)",
        "Faster: estimated by llvm-mca, before our rule and the CPU timings.",
    )
    for i, (model, run) in enumerate(RUNS.items()):
        ys = attempts_by_function(run)
        print(model, "attempts", ys)
        ax.plot(range(1, 6), ys, marker="o", color=theme["series"][i], linewidth=2, label=model)
    ax.set_xticks(range(1, 6))
    ax.set_ylim(bottom=0)
    finish(fig, ax, "attempts", theme, args.out)

    mca, cpus = {}, {}
    for model, run in RUNS.items():
        a, b = (timed(run, folder) for folder in CPUS.values())
        est = estimated(run, a)
        mca[model] = ([est[i] for i in a], [a[i] for i in a])
        cpus[model] = ([a[i] for i in a], [b[i] for i in a])
        print(model, "points", len(a))
    note = "Each dot is a kept win. Timed inline with predictable inputs, one measure among four."
    scatter(
        "mca_vs_cpu",
        mca,
        "llvm-mca's estimate against the real CPU",
        "Speedup estimated by llvm-mca (better of throughput and latency)",
        "Speedup timed on the i7-9700K",
        note,
        theme,
        args.out,
    )
    scatter(
        "cpu_vs_cpu",
        cpus,
        "The same wins on two CPUs",
        "Speedup timed on the i7-9700K",
        "Speedup timed on the i7-12700H",
        note,
        theme,
        args.out,
    )


if __name__ == "__main__":
    main()
