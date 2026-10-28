"""Propose -> prove -> repair loop. Writes every attempt, failures included, to
results/<run-id>/<id>.json, and the run settings to results/<run-id>/run.json."""

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from qed import config, llm, llm_compiler
from qed.cost import cost
from qed.extract import ExtractError, body, extract, function, splice
from qed.verify import Status, sha256, verify

FEEDBACK_TAIL = 25  # lines of an Alive2 error shown to the model


def run_function(
    entry: Path,
    backend: str = "muse",
    settings: llm.Settings = llm.DEFAULT,
    attempts: int = 5,
    budget_usd: float = 0.35,
) -> dict:
    """Up to `attempts` proposals for one corpus entry; keeps the fastest proven one.
    Only src.c is read: never expected.ll or meta.json (contamination rule)."""
    c_source = (entry / "src.c").read_text()
    src_ll = extract(entry / "src.c")
    base = cost(src_ll)
    history, log, best, spent, stop = [], [], None, 0.0, "attempts"

    for n in range(1, attempts + 1):
        call = (
            settings
            if best is None
            else replace(settings, max_tokens=settings.max_tokens_after_win)
        )
        if (
            backend == "muse"
            and spent + _worst_case_usd(src_ll, history, c_source, base, call) > budget_usd
        ):
            stop = "budget"
            break
        if backend == "muse":
            response = llm.generate(
                src_ll, history, c_source=c_source, baseline=base, settings=call
            )
            stats = {k: v for k, v in llm.last_call.items() if k != "messages"}
        else:
            response = llm_compiler.generate(src_ll, history)
            stats = dict(llm_compiler.last_call, cost_usd=0.0)
        spent += stats.get("cost_usd", 0.0)
        att = {"n": n, **stats, "response": response}

        if stats.get("finish_reason") == "length":
            # The model hit the token limit while reasoning and gave no usable answer.
            att["check"] = "truncated"
            if best is not None:
                # After a win, a truncation means no quick improvement: stop here. Without
                # this rule the model burned 4 capped calls in a row on optimal code (smoke-3).
                log.append(att)
                stop = "truncated_after_win"
                break
            feedback = (
                "You ran out of tokens before answering. Answer directly: a faster body, "
                f"or {llm.NO_IMPROVEMENT} if you believe the best version so far is optimal."
            )
        elif response.strip().startswith(llm.NO_IMPROVEMENT):
            if n > 1:
                att["check"] = "no_improvement"
                log.append(att)
                stop = "no_improvement"
                break
            att["check"] = "no_improvement_refused"
            feedback = "You must propose at least one rewrite before concluding. Try anyway."
        else:
            feedback, best = _check(att, src_ll, base, best, settings, first=(n == 1))
        history.append(
            {"response": response, "body": att.get("body", response), "feedback": feedback}
        )
        att["feedback"] = feedback
        log.append(att)

    return {
        "id": entry.name,
        "category": entry.parent.name,
        "backend": backend,
        "model": config.META_MODEL if backend == "muse" else "llm-compiler-7b",
        "settings": asdict(settings),
        "src_ll": src_ll,
        "src_sha256": sha256(src_ll),
        "baseline": _cost_record(base),
        "attempts": log,
        "best": best,
        "stop": stop,
        "cost_usd": spent,
        "verified_by": "alive-tv, reference toolchain",
    }


def _worst_case_usd(src_ll, history, c_source, base, settings) -> float:
    """Upper bound on the next call's cost: input estimated at ~3 characters per token,
    output at the token limit. The loop only calls the model if this fits the budget."""
    msgs = llm.messages(src_ll, history, c_source, base, settings)
    tokens_in = sum(len(m["content"]) for m in msgs) / 3
    return (tokens_in * config.META_PRICE_IN + settings.max_tokens * config.META_PRICE_OUT) / 1e6


def _check(att, src_ll, base, best, settings, first):
    """Splice, prove and measure one candidate; return the feedback for the model."""
    show_asm = settings.show_asm in ("always", "feedback")
    intro = ""
    if first and settings.show_asm == "feedback":
        intro = f"For reference, clang's x86-64 assembly:\n```asm\n{base.asm.strip()}\n```\n\n"
    try:
        tgt = splice(src_ll, att["response"])
    except ExtractError as e:
        att["check"] = "invalid"
        return (
            intro + f"Your answer could not be used: {e}. Answer with the function body only.",
            best,
        )

    att["body"] = body(function(tgt))
    att["tgt_ll"] = tgt
    att["tgt_sha256"] = sha256(tgt)
    r = verify(src_ll, tgt)
    att["check"] = r.status.value
    att["alive2_output"] = r.output
    att["alive2_seconds"] = r.time

    if r.status is Status.COUNTEREXAMPLE:
        if settings.feedback == "verdict":
            return (
                intro + "Rejected by Alive2: this rewrite is not a refinement of the source.",
                best,
            )
        return intro + f"Rejected by Alive2. Counterexample:\n{r.counterexample}", best
    if r.status is Status.UNCHANGED:
        return intro + "This is identical to the source. Propose a different, faster body.", best
    if r.status is Status.NOT_PROVEN:
        tail = "\n".join(r.output.strip().splitlines()[-FEEDBACK_TAIL:])
        return intro + f"Alive2 could not prove it (invalid IR, timeout or error):\n{tail}", best

    c = cost(tgt)
    att["cost"] = _cost_record(c)
    faster = c.mca_cycles < base.mca_cycles
    att["faster"] = faster
    if faster and (best is None or c.mca_cycles < best["mca_cycles"]):
        best = {"n": att["n"], **_cost_record(c), "speedup": base.mca_cycles / c.mca_cycles}
    msg = f"Proven correct. Cost: {c.mca_cycles:.2f} cycles per call, clang: {base.mca_cycles:.2f}."
    if show_asm:
        msg += f"\nYour x86-64 assembly:\n```asm\n{c.asm.strip()}\n```"
    if faster:
        msg += (
            "\nCan you make it even faster? If you believe this version is optimal, "
            f"answer {llm.NO_IMPROVEMENT} and one sentence why."
        )
    else:
        msg += "\nNot faster: find a faster version."
    return intro + msg, best


def _cost_record(c) -> dict:
    return {
        "ir_insts": c.ir_insts,
        "asm_insts": c.asm_insts,
        "mca_cycles": c.mca_cycles,
        "asm": c.asm,
        "mca_output": c.mca_output,
    }


def _git_head(path: Path) -> str:
    p = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() or "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the propose-prove-repair loop on corpus entries")
    ap.add_argument("entries", nargs="+", type=Path, help="bench/<cat>/<id> directories")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--backend", choices=["muse", "llmc"], default="muse")
    ap.add_argument("--show-asm", choices=["never", "always", "feedback"], default="never")
    ap.add_argument("--feedback", choices=["independent", "verdict", "full"], default="full")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument(
        "--budget", type=float, default=0.35, help="USD cap per function (5 x 16k tokens)"
    )
    args = ap.parse_args(argv)

    settings = llm.Settings(show_asm=args.show_asm, feedback=args.feedback)
    out = config.RESULTS_DIR / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    run = {
        "run_id": args.run_id,
        "started": datetime.now(UTC).isoformat(),
        "backend": args.backend,
        "model": config.META_MODEL if args.backend == "muse" else "llm-compiler-7b",
        "settings": asdict(settings),
        "attempts": args.attempts,
        "budget_usd_per_function": args.budget,
        "system_prompt": llm.SYSTEM if args.backend == "muse" else llm_compiler.PROMPT,
        "toolchain": {
            "llvm": _git_head(config.TOOLCHAIN / "llvm-project"),
            "alive2": _git_head(config.TOOLCHAIN / "alive2"),
            "clang_flags": config.CLANG_FLAGS,
            "llc_flags": config.LLC_FLAGS,
            "mca_flags": config.MCA_FLAGS,
        },
        "entries": [str(e) for e in args.entries],
    }
    total = 0.0
    for e in args.entries:
        res = run_function(e, args.backend, settings, args.attempts, args.budget)
        (out / f"{e.name}.json").write_text(json.dumps(res, indent=1))
        total += res["cost_usd"]
        best = res["best"]
        verdict = f"x{best['speedup']:.2f} (try {best['n']})" if best else "-"
        checks = " ".join(a["check"] for a in res["attempts"])
        print(f"{e.name:28} {verdict:16} {checks}  ${res['cost_usd']:.4f}", flush=True)
    run["finished"] = datetime.now(UTC).isoformat()
    run["cost_usd"] = total
    (out / "run.json").write_text(json.dumps(run, indent=1))
    print(f"total ${total:.4f} -> {out}")


if __name__ == "__main__":
    sys.exit(main())
