"""LLM Compiler candidate generator, served locally by llama.cpp (`llama-server`).

LLM Compiler is not instruction-tuned: it only knows its training task, "optimize this IR
with opt -O3". We use that exact prompt format, in two stages:
1. the model writes its usual first sentence, "The LLVM-IR will have instruction count N...";
   skipping it makes the model copy its input unchanged;
2. we prefill the module preamble and the source's `define` line, so the model writes only
   the body, and stop at the closing brace.

The model cannot read Alive2 counterexamples. To get a different candidate on later attempts,
we prefill the instruction counts between the model's own estimate and the source's count
(forcing a count below its estimate never helped), then fall back to sampling.

Answers are cached on disk, keyed by the request and the server that answered: a CUDA and a
Metal build can write different candidates for the same request.
"""

import hashlib
import json
import re
import time
from typing import NamedTuple
from urllib.request import urlopen

from openai import OpenAI

from qed import config
from qed.extract import body, function

PROMPT = (
    "[INST] Give the LLVM-IR for the following code when optimized using "
    "opt -p 'module(default<O3>)':\n\n<code>{fn}</code>\n\n"
    "The input code has instruction count {n}. [/INST]"
)
# Preamble the model itself writes for x86-64; prefilling it saves ~100 tokens per call.
# The model writes "minsize optsize" in the attributes line; we drop them because we
# optimize for cycles, not size (same results on bench/B, one more proven entry).
PREAMBLE = """<code>; ModuleID = '<stdin>'
source_filename = "-"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

; Function Attrs: mustprogress nofree norecurse nosync nounwind willreturn \
memory(none) uwtable
"""
# "sise" is the model's own spelling; it also keeps a forced " 3" from continuing as "30".
COUNT_PREFIX = "  The LLVM-IR will have instruction count {} and binary sise"
SENTENCE_TOKENS = 40
MAX_TOKENS = 1024
SAMPLES = 8  # temperature samples tried once the forced counts are used up
SAMPLE_TEMPERATURE = 0.8
# Recorded in run.json, with server(), so that a run can be replayed exactly.
GENERATION = {
    "first": "temperature 0",
    "then": "temperature 0, forced instruction counts from the model's estimate + 1 to the "
    "source's count - 1",
    "then_samples": SAMPLES,
    "sample_temperature": SAMPLE_TEMPERATURE,
    "sample_seeds": f"1..{SAMPLES}",
    "sentence_max_tokens": SENTENCE_TOKENS,
    "body_max_tokens": MAX_TOKENS,
}
# The model attaches metadata from its training modules (`, !tbaa !5, !range !6`) that does
# not exist in ours. Dropping attachments only removes promises, so the candidate stays valid.
_METADATA = re.compile(r"(,\s*![\w.]+\s+!(\d+|\{[^}]*\}))+(?=\s*$)", re.M)
_LABEL = re.compile(r"^[\w.$-]+:")
_ESTIMATE = re.compile(r"instruction count (\d+)")

# Tokens and time of the last generate() call (local model: no API cost).
last_call: dict = {}
# Generation is deterministic at temperature 0: never pay twice for the same request.
_cache: dict = {}
_server: dict = {}


def client() -> OpenAI:
    return OpenAI(api_key="none", base_url=f"{config.LLMC_URL}/v1")


def server() -> dict:
    """The llama-server and model that answer. The GGUF hash and the machine come from the
    environment, since the server reports neither."""
    if not _server:
        with urlopen(f"{config.LLMC_URL}/props", timeout=10) as r:
            props = json.load(r)
        _server.update(
            llama_cpp=props["build_info"],
            model_file=props["model_path"],
            quant=props.get("model_ftype"),
            n_ctx=props["default_generation_settings"]["n_ctx"],
            model_sha256=config.LLMC_MODEL_SHA256,
            machine=config.LLMC_MACHINE,
        )
    return _server


def instruction_count(fn: str) -> int:
    lines = (line.strip() for line in body(fn).splitlines())
    return sum(1 for s in lines if s and not s.startswith(";") and not _LABEL.match(s))


def generate(ir: str, history: list) -> str:
    """Propose a faster version of the function in `ir`.

    `history` holds the previous attempts (dicts with a "body" key, or plain strings);
    their counterexamples are not used, since this model cannot read them.
    Returns the function BODY only: the caller splices it under the source header.
    Never returns the source body or an earlier attempt, unless every option is used up."""
    fn = function(ir)
    n = instruction_count(fn)
    prompt = PROMPT.format(fn=fn, n=n)
    header = fn.split("\n", 1)[0]
    seen = {_norm(body(fn))} | {_norm(h["body"] if isinstance(h, dict) else h) for h in history}

    llm = client()
    stats = {"tokens": 0}
    start = time.monotonic()
    first = _candidate(llm, prompt, header, "", 0.0, 0, stats)
    m = _ESTIMATE.search(first.sentence)
    estimate = int(m.group(1)) if m else n
    steps = [("", 0.0, 0)]
    steps += [(COUNT_PREFIX.format(c), 0.0, 0) for c in range(estimate + 1, n)]
    steps += [("", SAMPLE_TEMPERATURE, seed) for seed in range(1, SAMPLES + 1)]

    candidate = first.body
    for forced, temperature, seed in steps:
        candidate = _candidate(llm, prompt, header, forced, temperature, seed, stats).body
        if _norm(candidate) not in seen:
            break

    last_call.clear()
    last_call.update(
        model="llm-compiler-7b",
        completion_tokens=stats["tokens"],
        seconds=time.monotonic() - start,
    )
    return candidate


class _Candidate(NamedTuple):
    sentence: str
    body: str


def _candidate(llm, prompt, header, forced, temperature, seed, stats) -> _Candidate:
    key = (prompt, forced, temperature, seed)
    if key not in _cache:
        sentence = forced + _complete(
            llm, prompt + forced, ["<code>"], SENTENCE_TOKENS, temperature, seed, stats
        )
        text = _complete(
            llm,
            prompt + sentence + PREAMBLE + header + "\n",
            ["\n}", "</code>"],
            MAX_TOKENS,
            temperature,
            seed,
            stats,
        )
        _cache[key] = _Candidate(sentence, _METADATA.sub("", text).rstrip())
    return _cache[key]


def _complete(llm, prompt, stop, max_tokens, temperature, seed, stats) -> str:
    request = {
        "prompt": prompt,
        "stop": stop,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "seed": seed,
    }
    key = json.dumps({**request, "server": server()}, sort_keys=True)
    path = config.CACHE_DIR / "llmc" / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text())["text"]
    r = llm.completions.create(model="llm-compiler", **request)
    tokens = r.usage.completion_tokens if r.usage else 0
    stats["tokens"] += tokens
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"server": server(), **request, "text": r.choices[0].text, "tokens": tokens}
    path.write_text(json.dumps(record, indent=1))
    return record["text"]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
