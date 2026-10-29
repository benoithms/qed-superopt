"""Propose -> prove -> repair loop. Writes every attempt, failures included, to
results/<run-id>/<id>.json, and the run settings to results/<run-id>/run.json."""

import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from qed import config, llm, llm_compiler
from qed.cost import cost
from qed.extract import ExtractError, body, extract, function, splice
from qed.verify import Status, sha256, verify

FEEDBACK_TAIL = 25  # lines of an Alive2 error shown to the model
BASE_MODEL, BASE_BUDGET_USD = "muse-spark-1.3", 0.35  # 5 attempts x 16k tokens

# When to call the fallback model, from the primary model's result only. Candidates of the
# fallback policy, compared offline by scripts/replay_fallback.py (see ROADMAP).
FALLBACK_POLICIES = {
    "always": lambda r: True,
    "not_no_improvement": lambda r: r["stop"] != "no_improvement",
    "no_win": lambda r: r["best"] is None,
    # from the baseline, which older results (before the "large" field) also have
    "large_or_no_win": lambda r: (
        r["baseline"]["ir_insts"] >= llm.DEFAULT.large_insts or r["best"] is None
    ),
}


def wants_fallback(primary: dict, policy: str) -> bool:
    return FALLBACK_POLICIES[policy](primary)


class Wallet:
    """Hard cap on the money actually paid by a run, shared by all parallel functions. Each
    call first reserves its worst case; the reservation is replaced by the real cost once the
    call returns (zero for a cached answer). So paid + reserved never exceeds the cap, even with
    calls in flight in several threads."""

    def __init__(self, cap_usd: float):
        self.cap, self.paid, self.reserved = cap_usd, 0.0, 0.0
        self._lock = threading.Lock()

    def reserve(self, usd: float) -> bool:
        with self._lock:
            if self.paid + self.reserved + usd > self.cap:
                return False
            self.reserved += usd
            return True

    def settle(self, reserved: float, paid: float) -> None:
        with self._lock:
            self.reserved -= reserved
            self.paid += paid


WALLET: Wallet | None = None  # set by main() from --max-total


def run_function(
    entry: Path,
    backend: str = "muse",
    settings: llm.Settings = llm.DEFAULT,
    attempts: int = 5,
    budget_usd: float | None = None,
) -> dict:
    """Up to `attempts` proposals for one corpus entry; keeps the fastest proven one.
    Only src.c is read: never expected.ll or meta.json (contamination rule).
    Default budget: $0.35 for muse-spark-1.3, scaled by the output price for other models, so
    every model gets the same number of tokens (a fair comparison)."""
    if budget_usd is None:
        budget_usd = BASE_BUDGET_USD * config.price(settings.model)[1] / config.price(BASE_MODEL)[1]
    c_source = (entry / "src.c").read_text()
    src_ll = extract(entry / "src.c")
    base = cost(src_ll)
    large = base.ir_insts >= settings.large_insts
    if large:
        budget_usd *= 2  # each attempt may cost twice as much
    first_cap = settings.max_tokens_large if large else settings.max_tokens
    win_cap = settings.max_tokens_after_win_large if large else settings.max_tokens_after_win
    history, log, best, spent, stop = [], [], None, 0.0, "attempts"

    for n in range(1, attempts + 1):
        call = replace(settings, max_tokens=first_cap if best is None else win_cap)
        worst = _worst_case_usd(src_ll, history, c_source, base, call) if backend == "muse" else 0
        if backend == "muse" and spent + worst > budget_usd:
            stop = "budget"
            break
        if backend == "muse":
            hard = _worst_case_usd(src_ll, history, c_source, base, call, chars_per_token=1)
            if WALLET is not None and not WALLET.reserve(hard):
                stop = "max_total"
                break
            try:
                response = llm.generate(
                    src_ll, history, c_source=c_source, baseline=base, settings=call
                )
            except BaseException:
                # a failed call may still have been billed: keep its worst case as paid
                if WALLET is not None:
                    WALLET.settle(hard, hard)
                raise
            stats = {k: v for k, v in llm.last_call.items() if k != "messages"}
            if WALLET is not None:
                WALLET.settle(hard, 0.0 if stats.get("cached") else stats["cost_usd"])
        else:
            response = llm_compiler.generate(src_ll, history)
            stats = dict(llm_compiler.last_call, cost_usd=0.0)
        spent += stats.get("cost_usd", 0.0)
        att = {"n": n, **stats, "response": response}

        if stats.get("finish_reason") == "length":
            # The model hit the token limit while reasoning and gave no usable answer.
            att["check"] = "truncated"
            if settings.stop_on_truncation:
                log.append(att)
                stop = "truncated"
                break
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
        "model": settings.model if backend == "muse" else "llm-compiler-7b",
        "settings": asdict(settings),
        "src_ll": src_ll,
        "src_sha256": sha256(src_ll),
        "baseline": _cost_record(base),
        "attempts": log,
        "best": best,
        "stop": stop,
        "cost_usd": spent,
        "large": large,
        "budget_usd": budget_usd,
        "verified_by": "alive-tv, reference toolchain",
    }


def run_cascade(
    entry: Path,
    settings: llm.Settings,
    attempts: int,
    budget_usd: float | None,
    fallback: llm.Settings,
    fallback_attempts: int,
    policy: str,
    fallback_budget_usd: float | None = None,
) -> dict:
    """Primary model first; the fallback model starts from scratch on the same entry when the
    policy asks for it. The result is the primary's, with the fallback run nested under
    "fallback" and "best" the fastest proven version of either."""
    res = run_function(entry, "muse", settings, attempts, budget_usd)
    res["primary_best"] = res["best"] and {**res["best"], "model": settings.model}
    res["best"] = res["primary_best"]
    res["fallback_policy"] = policy
    res["fallback"] = None
    if wants_fallback(res, policy):
        fb = run_function(entry, "muse", fallback, fallback_attempts, fallback_budget_usd)
        res["fallback"] = fb
        res["cost_usd"] += fb["cost_usd"]
        if fb["best"] and (
            res["best"] is None or fb["best"]["mca_cycles"] < res["best"]["mca_cycles"]
        ):
            res["best"] = {**fb["best"], "model": fallback.model}
    return res


def _worst_case_usd(src_ll, history, c_source, base, settings, chars_per_token=3) -> float:
    """Upper bound on the next call's cost: input estimated at ~3 characters per token,
    output at the token limit. The loop only calls the model if this fits the budget.
    The run-wide cap uses 1 character per token: a bound no tokenizer exceeds."""
    msgs = llm.messages(src_ll, history, c_source, base, settings)
    tokens_in = sum(len(m["content"]) for m in msgs) / chars_per_token
    return llm.cost_usd(settings.model, tokens_in, settings.max_tokens)


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
    ap.add_argument("--model", default=config.META_MODEL, choices=sorted(config.PRICES))
    ap.add_argument("--show-asm", choices=["never", "always", "feedback"], default="never")
    ap.add_argument("--feedback", choices=["independent", "verdict", "full"], default="full")
    ap.add_argument("--attempts", type=int, default=5)
    ap.add_argument(
        "--budget", type=float, help="USD cap per function (default: 5 x 16k tokens at the price)"
    )
    ap.add_argument("--jobs", type=int, default=1, help="functions run in parallel (API only)")
    ap.add_argument(
        "--max-total",
        type=float,
        help="USD: hard cap on the money paid by the whole run (cached answers are free); "
        "a call is made only if its worst case still fits",
    )
    ap.add_argument(
        "--fallback-model",
        choices=sorted(config.PRICES),
        help="second model, run from scratch on the functions selected by --fallback-when",
    )
    ap.add_argument("--fallback-when", choices=sorted(FALLBACK_POLICIES), default="always")
    ap.add_argument("--fallback-attempts", type=int, default=5)
    ap.add_argument(
        "--max-tokens",
        type=int,
        help="one token cap for every call (replaces the small/large and after-win caps)",
    )
    ap.add_argument(
        "--stop-on-truncation",
        action="store_true",
        help="stop a function at its first truncated answer instead of retrying",
    )
    args = ap.parse_args(argv)
    jobs = 1 if args.backend == "llmc" else args.jobs  # one local llama-server
    if args.fallback_model and args.backend != "muse":
        ap.error("--fallback-model needs --backend muse")

    settings = llm.Settings(
        model=args.model,
        show_asm=args.show_asm,
        feedback=args.feedback,
        stop_on_truncation=args.stop_on_truncation,
    )
    if args.max_tokens:
        settings = replace(
            settings,
            max_tokens=args.max_tokens,
            max_tokens_after_win=args.max_tokens,
            max_tokens_large=args.max_tokens,
            max_tokens_after_win_large=args.max_tokens,
        )
    fallback = args.fallback_model and replace(settings, model=args.fallback_model)

    # The fallback model gets the same number of tokens: --budget scaled by the output price.
    fallback_budget = (
        fallback
        and args.budget
        and args.budget * config.price(fallback.model)[1] / config.price(settings.model)[1]
    ) or None

    def work(e):
        if fallback:
            return run_cascade(
                e,
                settings,
                args.attempts,
                args.budget,
                fallback,
                args.fallback_attempts,
                args.fallback_when,
                fallback_budget,
            )
        return run_function(e, args.backend, settings, args.attempts, args.budget)

    out = config.RESULTS_DIR / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    run = {
        "run_id": args.run_id,
        "started": datetime.now(UTC).isoformat(),
        "backend": args.backend,
        "model": settings.model if args.backend == "muse" else "llm-compiler-7b",
        "settings": asdict(settings),
        "attempts": args.attempts,
        "budget_usd_per_function": args.budget,
        "jobs": jobs,
        "max_total_usd": args.max_total,
        "fallback": fallback
        and {
            "model": fallback.model,
            "when": args.fallback_when,
            "attempts": args.fallback_attempts,
            "budget_usd_per_function": fallback_budget,
        },
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

    missing = [str(e) for e in args.entries if not (e / "src.c").is_file()]
    if missing:  # checked before any call is paid
        ap.error(f"no src.c in: {', '.join(missing)}")
    global WALLET
    WALLET = Wallet(args.max_total) if args.max_total is not None else None
    total, todo, skipped, errors = 0.0, list(args.entries), [], {}
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        running = {}
        while todo or running:
            while todo and len(running) < jobs:
                if WALLET is not None and WALLET.paid >= WALLET.cap:
                    skipped, todo = todo, []
                    break
                e = todo.pop(0)
                running[pool.submit(work, e)] = e
            if not running:
                break
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            for fut in done:
                e = running.pop(fut)
                try:
                    res = fut.result()
                except Exception as exc:  # one broken entry must not stop the run
                    errors[str(e)] = repr(exc)
                    print(f"{e.name:28} ERROR {exc!r}", flush=True)
                    continue
                (out / f"{e.name}.json").write_text(json.dumps(res, indent=1))
                total += res["cost_usd"]
                best = res["best"]
                verdict = f"x{best['speedup']:.2f} (try {best['n']})" if best else "-"
                checks = " ".join(a["check"] for a in res["attempts"])
                if res.get("fallback"):
                    checks += " | " + " ".join(a["check"] for a in res["fallback"]["attempts"])
                print(f"{e.name:28} {verdict:16} {checks}  ${res['cost_usd']:.4f}", flush=True)

    run["finished"] = datetime.now(UTC).isoformat()
    run["cost_usd"] = total
    run["skipped_by_max_total"] = [str(e) for e in skipped]
    run["errors"] = errors
    run["paid_usd"] = WALLET.paid if WALLET is not None else None
    (out / "run.json").write_text(json.dumps(run, indent=1))
    print(f"total ${total:.4f} -> {out}" + (f" ({len(skipped)} skipped)" if skipped else ""))


if __name__ == "__main__":
    sys.exit(main())
