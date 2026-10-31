"""Fill the LLVM issue template with the recorded data of one win:
    PYTHONPATH=.:scripts python scripts/issue_draft.py <function-id> [--reduced case.ll]

Refuses a win that our rule does not keep or that is not confirmed on both CPUs. The IR shown
has a shorter header than the recorded one, so that exact text is proven again by Alive2 before
anything is written, and so is a reduced case. Numbers come from the files only and always
describe the full function. The text that explains the miss is left as TODO for the person
filing. Writes .orca/issues/generated/<id>.md: no API call, nothing filed."""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from string import Template

from fold_back import check, opt_o3, winning_attempt

from qed.cost import cost
from qed.extract import function
from qed.verify import Status, verify

REPO = "https://github.com/benoithms/qed-superopt"
LLVM_COMMIT = "b974545"
ALIVE2_COMMIT = "adacbd5"
CPUS = {"i7-9700K": "results/bench-9700k", "i7-12700H": "results/bench-12700h"}
MODES = ["predictable", "random", "predictable_inline", "random_inline"]


class Refused(Exception):
    pass


def readable(fn: str) -> str:
    """The function without the header noise an issue reader does not need."""
    header, rest = fn.split("\n", 1)
    header = re.sub(r"\b(dso_local|local_unnamed_addr) ", "", header)
    header = re.sub(r" #\d+(?= \{)", "", header)
    return f"{header}\n{rest}"


def proven_pair(src_ll: str, tgt_ll: str) -> tuple[str, str]:
    """The (src, tgt) text to show, after proving that exact text."""
    src_fn, tgt_fn = function(src_ll), function(tgt_ll)
    src_short, tgt_short = readable(src_fn), readable(tgt_fn)
    r = verify(src_ll.replace(src_fn, src_short), tgt_ll.replace(tgt_fn, tgt_short))
    if r.status is not Status.PROVEN:
        raise Refused(f"the text to show is not proven: {r.status.value}")
    declares = re.findall(r"^declare .*$", tgt_ll, re.M)
    shown_src = src_short.replace("@f(", "@src(", 1).rstrip()
    shown_tgt = tgt_short.replace("@f(", "@tgt(", 1).rstrip()
    return shown_src, "\n".join([shown_tgt, *declares])


def cpu_row(cpu: str, entry: dict) -> str:
    cells = []
    for mode in MODES:
        low, high = entry[mode]["speedup_range"]
        cells.append(f"{low:.2f}x-{high:.2f}x")
    return f"| {cpu} | " + " | ".join(cells) + " |"


def asm_diff(src_asm: str, tgt_asm: str) -> str:
    def lines(asm):
        return [x.split("#")[0].rstrip() for x in asm.splitlines() if x.split("#")[0].strip()]

    diff = difflib.unified_diff(lines(src_asm), lines(tgt_asm), "clang -O3", "rewrite", lineterm="")
    return "\n".join(diff)


def reduced_pair(path: Path, src_ll: str) -> tuple[str, str]:
    """The @src and @tgt of a hand-reduced file, after proving them as written."""
    text = path.read_text()
    prefix = "".join(x + "\n" for x in re.findall(r"^target .*$", src_ll, re.M))
    declares = "".join(x + "\n" for x in re.findall(r"^declare .*$", text, re.M))
    fns = {
        m[1]: m[0].rstrip()
        for m in re.findall(r"(^define .*?@(src|tgt)\(.*?^\}$)", text, re.M | re.S)
    }
    if set(fns) != {"src", "tgt"}:
        raise Refused(f"{path}: expected one @src and one @tgt")
    src, tgt = (
        prefix + declares + fns[n].replace(f"@{n}(", "@f(", 1) + "\n" for n in ("src", "tgt")
    )
    r = verify(src, tgt)
    if r.status is not Status.PROVEN:
        raise Refused(f"the reduced case is not proven: {r.status.value}")
    return fns["src"], fns["tgt"] + ("\n\n" + declares.rstrip() if declares else "")


def draft(fid: str, run: str = "spark-full-v1", reduced: Path | None = None) -> str:
    res = json.loads(Path(f"results/{run}/{fid}.json").read_text())
    if not res["best"]:
        raise Refused("no win recorded")
    kept = check(res, 1.05)
    if not kept["kept"]:
        raise Refused("our rule does not keep this win")
    rows, launches = [], set()
    for cpu, folder in CPUS.items():
        bench = json.loads(Path(folder, f"{run}.json").read_text())
        entry = next((e for e in bench["results"] if e["id"] == fid), None)
        if entry is None or entry["overall"] != "confirmed":
            raise Refused(f"not confirmed on the {cpu}")
        rows.append(cpu_row(cpu, entry))
        launches.add(bench["conditions"]["launches"])

    attempt = winning_attempt(res)
    full_src, full_tgt = proven_pair(res["src_ll"], attempt["tgt_ll"])
    src_fn, tgt_fn = reduced_pair(reduced, res["src_ll"]) if reduced else (full_src, full_tgt)
    meta = json.loads(next(Path("bench").glob(f"*/{fid}/meta.json")).read_text())
    c_source = Path("bench", meta["category"], fid, "src.c").read_text().strip()
    base, new = cost(res["src_ll"]), cost(opt_o3(attempt["tgt_ll"]))
    gain_scope, full_case = "Measured on the function above.", f"```c\n{c_source}\n```\n"
    if reduced:
        gain_scope = (
            "Measured on the full function and its proven rewrite, in the details below: "
            "not on the reduced case, and not on the fix it suggests."
        )
        full_case += f"\n```llvm\n{full_src}\n\n{full_tgt}\n```\n"
    template = Template(Path("scripts/issue_template.md").read_text())
    return template.substitute(
        llvm_commit=LLVM_COMMIT,
        alive2_commit=ALIVE2_COMMIT,
        src_fn=src_fn,
        tgt_fn=tgt_fn,
        gain_scope=gain_scope,
        mca_summary=(
            f"{base.asm_insts} to {new.asm_insts} instructions, "
            f"Block RThroughput {kept['throughput']:.2f}x, one-call latency {kept['latency']:.2f}x."
        ),
        full_case=full_case,
        asm_diff=asm_diff(base.asm, new.asm),
        launches="/".join(str(n) for n in sorted(launches)),
        cpu_rows="\n".join(rows),
        description=meta["description"],
        source=meta["source"],
        repo=REPO,
        model=attempt["model"],
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("id")
    ap.add_argument("--run", default="spark-full-v1")
    ap.add_argument("--reduced", type=Path, help="hand-reduced file with @src and @tgt")
    args = ap.parse_args()
    try:
        text = draft(args.id, args.run, args.reduced)
    except Refused as e:
        sys.exit(f"{args.id}: refused: {e}")
    out = Path(".orca/issues/generated", f"{args.id}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(out)


if __name__ == "__main__":
    main()
