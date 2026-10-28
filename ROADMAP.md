# Roadmap

What is done, what comes next, and who is on it. Update this file whenever something is merged into `dev`.

Hackathon window: **Oct 26 – Nov 4, 2026**. Submission: **Wed Nov 4, 21:00 ET**.

## Done

- [x] Reference toolchain built and smoke-tested: LLVM `b974545` (clang 24.0.0git) and Alive2 `adacbd5` (Benoit)
- [x] Python project skeleton with the frozen interfaces `generate()`, `verify()`, `cost()` (Benoit)
- [x] Meta Model API access validated with `muse-spark-1.3` (Benoit)
- [x] Corpus: 73 entries (22 A, 40 B, 11 C); the 40 `expected.ll` are proven by Alive2 with the reference toolchain (Jules)
- [x] LLM Compiler 7B (Q8 GGUF) running locally with llama.cpp; first loop turn done by hand (Jules)

## M1: MVP, full loop on one function (Thu Oct 29)

**Benoit**
- [ ] `extract.py`: reference clang with `-fdiscard-value-names`, single-function extraction, `splice()` of a body under the source header
- [ ] `verify.py`: `alive-tv` wrapper, strict whitelist (exit code is always 0), `ProvenResult` with files and hashes
- [ ] Verifier regression suite: wrong rewrites that must be rejected, correct ones that must be accepted
- [ ] `cost.py`: `llc` + `llvm-mca` for Skylake
- [ ] `llm.py`: Muse Spark `generate()`, with token (including reasoning tokens) and cost logging
- [ ] `loop.py`: propose, prove, repair; results written as JSON in `results/<run-id>/`

**Jules**
- [ ] LLM Compiler behind `generate(ir, history) -> body` (training prompt format, prefilled module header)
- [ ] Reference toolchain built on a second machine, same commits (independent reproduction)
- [ ] Corpus: ~9 more C entries; `nlz-binsearch-u32` and `clp2-u32` to B once their `expected.ll` is proven; settle `next-same-popcount` with the reference clang; add issues 210131, 227280, 225655 and the `__builtin_assume` / `__builtin_unreachable` issues

## M2: First results (Fri Oct 30 – Sun Nov 1)

- [ ] Full corpus run with Muse Spark (Benoit)
- [ ] Full corpus run with LLM Compiler (Jules)
- [ ] Ablation: with vs. without counterexample feedback (Benoit)
- [ ] Muse Spark vs. LLM Compiler comparison: proven-candidate rate, gains, cost (together)
- [ ] Triage of real wins: gain on the final assembly, and `opt -O3` must not fold the rewrite back (Benoit)

## M3: Confirmation on real hardware (Mon Nov 2)

- [ ] x86 microbenchmark harness: separate object, no inlining, latency and throughput (Benoit)
- [ ] Measurements from the same `.s`: i7-9700K, reference (Jules); i7-12700H (Benoit)
- [ ] Stretch: generalize wins into peephole rules, re-proven by Alive2 (Benoit)

## M4: Submission (Tue Nov 3 – Wed Nov 4)

- [ ] Results in the README, demo page (together)
- [ ] `make verify-all`: re-runs Alive2 on every published result, reproduced on a second machine (together)
- [ ] Demo video (together)
- [ ] Submission (Benoit)

## Key decisions

- **One toolchain, one target.** Every step, from `clang -O3` to `llvm-mca`, uses the pinned reference build and `--target=x86_64-unknown-linux-gnu -march=skylake`. The target changes the IR produced by `-O3`, so mixing targets would create fake missed optimizations.
- **The model writes bodies, never headers.** The tool places the body under the source's exact header, so the signature and function attributes cannot change.
- **Refinement, not equivalence.** Alive2 proves that the rewrite refines the original, the criterion LLVM uses for its own optimizations.
- **Only Meta models generate candidates**: Muse Spark (API) and LLM Compiler (local).
