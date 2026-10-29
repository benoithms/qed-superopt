# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LLVM IR superoptimizer for the Meta Global AI Developer Hackathon (submission Wed Nov 4, 21:00 ET). For a small C function, a Meta model proposes IR faster than `clang -O3`, and Alive2 formally proves the rewrite correct. This is a hackathon: favor simple code that works, with minimal abstractions. The MVP (full loop on 1 function) comes before everything else.

Planned modules: `extract.py` (C → `.ll`), `llm.py` (`generate(ir, history) -> str`, returns the function **body** only), `verify.py` (`alive-tv`), `cost.py` (`llc` + `llvm-mca`), `loop.py`, `report.py`. The `generate()`, `verify()`, `cost()` interfaces and the corpus entry format are frozen by Benoit: do not change their signatures without agreement.

## Rigor rules (non-negotiable)

- **A rewrite is valid only if Alive2 proves it.** Only `alive-tv`'s exact success message, with no approximation warning, counts as a proof. Timeout, unsupported, error or unexpected output = not proven. Never bypass, weaken or short-circuit verification, even for a test or a demo.
- Only `verify.py` may create a `ProvenResult`, and `report.py` accepts only that type.
- The verified source is exactly the `clang -O3` output, minus debug metadata. The candidate's signature is identical **by construction**: the model only provides the function body, which the tool places under the source's exact header (`define` line, parameter and return attributes, attribute group `#0`). The model never writes or changes the header.
- Alive2 proves **refinement**, not equivalence: write "proven correct (refinement)", never "equivalent". Two versions that differ on an input where the source has UB (signed `nsw` overflow, shift ≥ bit width, poison) are not a bug.
- Every result stores `src.ll`, `tgt.ll`, the Alive2 output and their hashes.
- The verifier regression suite (wrong rewrites that must be rejected, correct ones that must be accepted) must pass entirely. A single failure blocks everything.

## Toolchain

- **Do not use `/usr/bin/clang` (Apple clang) or a Homebrew LLVM** to produce reference IR, measure cost or validate the corpus. The whole chain (`clang`, `opt`, `llc`, `llvm-mca`, Alive2) comes from a single reference LLVM build pinned to one commit. If it is not available, say so instead of improvising with another compiler.
- **Single target for the whole chain**, from `clang -O3` to `llvm-mca`: `--target=x86_64-unknown-linux-gnu -march=skylake` (`-mcpu=skylake` for `llc` and `llvm-mca`). The target changes the IR produced by `-O3` (e.g. `ctpop` is only formed when `popcnt` is available), so extracting without `-march` would create fake "missed optimizations". Skylake code runs on both bench machines: the i7-9700K (Skylake microarchitecture, reference) and the i7-12700H (same `.s`, second measurement, `llvm-mca -mcpu=alderlake` for comparison).
- Gains are measured on the assembly after `llc`, not on the IR. Wording: "gain estimated by llvm-mca". No timing under emulation (Rosetta, x86 VM).
- Python: `uv` for environment and dependencies, `ruff` for lint and format, `pytest` for tests.

## Corpus (`bench/<A|B|C>/<id>/{src.c, meta.json, expected.ll?}`)

- A single non-`static` function, pure (no pointer, array, global or call), no loop or recursion, `int8_t`–`int64_t` or `bool` integers, no floating point. Builtins lowering to intrinsics are OK (`__builtin_popcount`, `clz`, `ctz`, `bswap`…), and so are `__builtin_assume` and `__builtin_unreachable`: they only state preconditions (UB when false), which Alive2 takes into account. Size, after `-O3 -march=skylake`: at most 30 IR instructions; the 5-instruction floor applies to category C only (A has no floor, B is kept whatever its size since a known miss proves there is a gain).
- One optimization pattern = one entry. A B entry needs a known solution that is **faster in llvm-mca cycles** on Skylake, not just shorter in IR: if a C entry has such a solution, it is a B entry; a known form that is shorter in IR but not faster keeps the entry in C (write the form in `meta.json` `notes`). An LLVM issue whose IR miss `llc` already recovers has no assembly gain: it is an A entry, with the known IR form in `notes` and no `expected.ll`.
- Every `expected.ll` is itself proven by Alive2 against its source; only its body matters, the header comes from the source.
- An issue that does not reproduce from C: if clang already optimizes it, it moves to A; if it was reported at IR level (e.g. from Rust) and the C does not produce the same IR, it is dropped for now.
- **Contamination**: `src.c` is sent as-is to the model. It must contain no trace of the known solution, in code or comments. `expected.ll` must never appear in a prompt, and the generator-side loader reads only `src.c`.
- A B case that clang trunk already optimizes moves to category A. Flag doubtful cases instead of deciding alone.

## Licenses and hackathon rules

- External tools (LLVM, Alive2, Z3, llama.cpp) are invoked, never vendored into the repo: our MIT license stays unconstrained. Do not copy third-party code into the repo.
- **LLM Compiler** (Meta LLM Compiler License): accept the license on the Hugging Face model page, including when using a third-party quantized GGUF; never commit the weights; the README must display "Built with LLM Compiler"; never use its outputs to train or improve another LLM.
- Muse Spark is used under the Meta Model API terms of service.
- Corpus: write each function yourself (a few lines, the idea is not protected) and always cite the source in `meta.json`. Never paste long excerpts from the Hacker's Delight book.
- Hackathon rule (disqualification risk): the README and the demo must clearly separate **what we built during the hackathon** (orchestration, loop, prompts, corpus, results) from **what we use** (LLVM, Alive2, Z3, Meta models).

## Team and repo

- No other AI (Claude, GPT…) **in the optimization loop**, not even for comparison: only Muse Spark (Meta API) and LLM Compiler (local, llama.cpp) generate candidates. Other AIs are only used to build the project.
- No AI as author or co-author (no `Co-Authored-By`, no "Generated with") in commits, PRs or the README.
- Branches: `dev` is the working base, `main` only receives merges of stable `dev`. One branch per topic, created from `dev` and merged into `dev` (`feat/verify`, `corpus/llvm-issues`, `feat/llm-compiler`…).
- Meta API keys live in `.env`, never committed. Budget is limited: log the cost of every call, cap spend per function, cache responses on disk.
- Never commit `*.gguf`, generated `*.ll`, `*.o`, `*.s`, or anything in `.orca/` (internal team plan).
