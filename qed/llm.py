"""Candidate generators. Only Meta models: Muse Spark (API, here) and LLM Compiler (local,
qed/llm_compiler.py). Both expose generate(ir, history) -> body."""

import hashlib
import json
import threading
import time
from dataclasses import dataclass

from openai import OpenAI

from qed import config
from qed.extract import function

NO_IMPROVEMENT = "NO_IMPROVEMENT"

SYSTEM = f"""You are a superoptimizer for LLVM IR. You receive one function compiled by \
clang -O3 for x86-64 (Skylake) and propose a faster version of it.

Your rewrite is checked by Alive2, a formal verifier: it must be a refinement of the source.
- For every input where the source has defined behavior, return the same value.
- You may exploit undefined behavior that is already in the source (nsw, nuw, exact flags, \
poison, shifts past the bit width, division by zero): on those inputs, any result is allowed.
- Never introduce undefined behavior the source does not have (no new nsw/nuw/exact flag, \
no possible division by zero, no new poison).
- Only LLVM intrinsics may be called (llvm.ctpop, llvm.ctlz, llvm.cttz, llvm.abs, \
llvm.smin/smax/umin/umax, llvm.fshl/fshr, llvm.bswap, llvm.bitreverse, llvm.uadd.sat, ...). \
No memory access, no other function.

Speed is measured by llvm-mca on the x86-64 assembly that llc produces for your IR, in \
cycles per call. Fewer IR instructions is not the goal: a division or a branch can cost far \
more than several simple instructions.

Answer format:
- Write only the function BODY in a ```llvm block: no `define` line, no closing brace. \
The original header (name, parameters, attributes) is kept as is.
- Parameters keep their names (%0, %1, ...). Give your own values names (%t1, %t2, ...), \
never new numbers.
- If, after at least one attempt, you believe the source is already optimal, answer \
{NO_IMPROVEMENT} followed by one sentence explaining why."""


@dataclass(frozen=True)
class Settings:
    model: str = config.META_MODEL
    # When clang's asm is shown: "never" | "always" | "feedback". "never" was frozen after the
    # anchoring pilot (results/pilot-anchor-*): same wins, cheapest, no anchoring risk.
    show_asm: str = "never"
    feedback: str = "full"  # "independent" | "verdict" | "full": what the model sees of history
    # One high cap for every call. Earlier caps (16k/10k after a win, 32k/20k for large
    # functions) wasted 75% of the spend on truncated answers, and a retry restarts the same
    # search from scratch since the API returns no reasoning. At 64k (results/highcap-cascade)
    # muse-spark-1.3 was never truncated, answered in up to 44k tokens and matched or beat the
    # old muse-wonder-1.0 results. The four fields stay separate to reproduce earlier runs.
    max_tokens: int = 64_000  # until a first proven win
    max_tokens_after_win: int = 64_000
    large_insts: int = 10  # functions with at least this many IR instructions are "large"
    max_tokens_large: int = 64_000
    max_tokens_after_win_large: int = 64_000
    # A truncated answer loses all its reasoning, so a retry restarts the same search from
    # scratch: with a high cap, a truncation means the model is going in circles. Stop.
    stop_on_truncation: bool = True


DEFAULT = Settings()


class _PerThread:
    """A dict per thread: with --jobs, functions run in parallel threads, and a shared dict
    would let one call overwrite another call's tokens and cost."""

    def __init__(self):
        self._local = threading.local()

    def _d(self) -> dict:
        if not hasattr(self._local, "d"):
            self._local.d = {}
        return self._local.d

    def clear(self):
        self._d().clear()

    def update(self, *args, **kw):
        self._d().update(*args, **kw)

    def items(self):
        return self._d().items()

    def get(self, key, default=None):
        return self._d().get(key, default)

    def __getitem__(self, key):
        return self._d()[key]

    def __setitem__(self, key, value):
        self._d()[key] = value


# Tokens, cost and time of the last generate() call in the current thread.
last_call = _PerThread()


def cost_usd(model: str, tokens_in: float, tokens_out: float) -> float:
    price_in, price_out = config.price(model)
    return (tokens_in * price_in + tokens_out * price_out) / 1e6


def client() -> OpenAI:
    if not config.META_API_KEY:
        raise RuntimeError("META_API_KEY is missing: copy .env.example to .env and fill it in")
    # The Meta Model API speaks the OpenAI wire format: this is only the HTTP client, every request
    # goes to META_API_BASE. While the model reasons, a stream sends nothing: muse-wonder-1.0 was
    # silent for more than the default 10 minutes at 60k tokens, hence 30. No automatic retry: a
    # hidden retry could be billed twice without going through the run's spending cap.
    return OpenAI(
        api_key=config.META_API_KEY, base_url=config.META_API_BASE, timeout=1800, max_retries=0
    )


def first_message(ir: str, c_source: str | None, baseline=None, show_asm: bool = False) -> str:
    parts = []
    if c_source:
        parts.append(f"C source:\n```c\n{c_source.strip()}\n```")
    parts.append(f"LLVM IR produced by clang -O3:\n```llvm\n{function(ir).strip()}\n```")
    if baseline is not None:
        cost = f"{baseline.asm_insts} instructions, {baseline.mca_cycles:.2f} cycles per call"
        if show_asm:
            parts.append(f"x86-64 assembly (llc, Skylake):\n```asm\n{baseline.asm.strip()}\n```")
        parts.append(f"Cost to beat (llvm-mca): {cost}.")
    parts.append("Propose a faster body.")
    return "\n\n".join(parts)


def messages(ir, history, c_source=None, baseline=None, settings=DEFAULT) -> list[dict]:
    """The conversation sent to the model. `history` entries are dicts with "response"
    (the model's raw answer), "body" and "feedback" (what the loop tells the model)."""
    show = settings.show_asm == "always"
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": first_message(ir, c_source, baseline, show)},
    ]
    if settings.feedback == "independent":
        return msgs
    for h in history:
        msgs.append({"role": "assistant", "content": h["response"]})
        msgs.append({"role": "user", "content": h["feedback"]})
    return msgs


def _stream(request: dict):
    """Streamed call: a non-streamed request is cut by the server (504) when the model reasons
    for several minutes (muse-wonder-1.0 at 50k tokens). Same answer, received in pieces.
    Returns (model, response, finish_reason, usage)."""
    start = last = time.monotonic()
    model, parts, finish_reason, usage = request["model"], [], None, None

    def where() -> str:
        # Why streams get cut is unknown: record when, and how long the stream had been silent.
        now = time.monotonic()
        return (
            f"after {now - start:.0f} s, {len(parts)} content chunks, "
            f"last chunk {now - last:.0f} s before, finish_reason {finish_reason}"
        )

    try:
        chunks = client().chat.completions.create(
            **request, stream=True, stream_options={"include_usage": True}
        )
        for c in chunks:
            last = time.monotonic()
            model = c.model or model
            if c.choices:
                if c.choices[0].delta and c.choices[0].delta.content:
                    parts.append(c.choices[0].delta.content)
                finish_reason = c.choices[0].finish_reason or finish_reason
            usage = c.usage or usage
    except Exception as exc:
        exc.add_note(f"stream failed {where()}")
        raise
    if usage is None:
        raise RuntimeError(
            f"streamed response without token usage: cost cannot be recorded ({where()})"
        )
    return model, "".join(parts), finish_reason, usage


def generate(ir: str, history: list, *, c_source=None, baseline=None, settings=DEFAULT) -> str:
    """Propose a faster version of the function in `ir`.

    `history` holds the previous attempts and the loop's feedback (Alive2 counterexamples,
    costs). Returns the model's answer: a function BODY (possibly in a ```llvm block), which
    the caller splices under the source header, or a NO_IMPROVEMENT sentence."""
    msgs = messages(ir, history, c_source, baseline, settings)
    request = {"model": settings.model, "messages": msgs, "max_tokens": settings.max_tokens}
    if settings.feedback == "independent":
        request["n_attempt"] = len(history)  # distinct cache key per independent sample
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    path = config.CACHE_DIR / f"{key}.json"

    if path.exists():
        record = json.loads(path.read_text())
        record["cached"] = True
    else:
        request.pop("n_attempt", None)
        start = time.monotonic()
        model, response, finish_reason, u = _stream(request)
        details = u.completion_tokens_details
        record = {
            "model": model,
            "response": response,
            "finish_reason": finish_reason,
            "tokens_in": u.prompt_tokens,
            "tokens_out": u.completion_tokens,
            "tokens_reasoning": (details.reasoning_tokens or 0) if details else 0,
            "cost_usd": cost_usd(settings.model, u.prompt_tokens, u.completion_tokens),
            "seconds": time.monotonic() - start,
            "cached": False,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1))

    last_call.clear()
    last_call.update(record, messages=msgs)
    return record["response"]
