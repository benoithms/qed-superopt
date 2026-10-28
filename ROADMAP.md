# Roadmap

What is done, what comes next, and who is on it. Update this file whenever something is merged into `dev`.

Hackathon window: **Oct 26 – Nov 4, 2026**. Submission: **Wed Nov 4, 21:00 ET**.

## Done

- [x] Reference toolchain built and smoke-tested: LLVM `b974545` (clang 24.0.0git) and Alive2 `adacbd5` (Benoit)
- [x] Python project skeleton with the frozen interfaces `generate()`, `verify()`, `cost()` (Benoit)
- [x] Meta Model API access validated with `muse-spark-1.3` (Benoit)
- [x] Corpus: 103 entries (22 A, 66 B, 15 C). 40 `expected.ll` are proven by Alive2 with the reference toolchain; the 26 added on Oct 28 are proven on alive2.llvm.org and must be re-checked with it, and `absdiff-chain` is not proven yet (online timeout) (Jules)
- [x] LLM Compiler 7B (Q8 GGUF) running locally with llama.cpp; first loop turn done by hand (Jules)

## M1: MVP, full loop on one function (Thu Oct 29)

Reached on Oct 28: on `llvm-issue-215060`, Muse Spark's first attempt is proven by Alive2 and runs in 1.48 cycles per call instead of 3.40 for `clang -O3` (4 x86 instructions instead of 11, gain estimated by llvm-mca).

**Benoit**
- [x] `extract.py`: reference clang with `-fdiscard-value-names`, single-function extraction, `splice()` of a body under the source header
- [x] `verify.py`: `alive-tv` wrapper, strict whitelist (exit code is always 0), `ProvenResult` with files and hashes
- [x] Verifier regression suite: 10 wrong rewrites rejected, 7 correct ones proven (`tests/test_verifier_regression.py`)
- [x] `cost.py`: `llc` + `llvm-mca` for Skylake
- [x] `llm.py`: Muse Spark `generate()`, with token (including reasoning tokens) and cost logging
- [x] `loop.py`: propose, prove, repair; results written as JSON in `results/<run-id>/`; strict budget per function, and after a win the first truncated answer ends the search

**Jules**
- [x] LLM Compiler behind `generate(ir, history) -> body` (training prompt format, prefilled module header): `qed/llm_compiler.py`
- [ ] Reference toolchain built on a second machine, same commits (independent reproduction)
- [x] Corpus: more C entries; `nlz-binsearch-u32` and `clp2-u32` to B; issues 210131, 227280, 225655 and the `__builtin_assume` / `__builtin_unreachable` issues added; variants removed and C entries with a known solution moved to B after review
- [ ] Corpus: settle `next-same-popcount` with the reference clang (Jules)

## M2: First results (Fri Oct 30 – Sun Nov 1)

- [ ] Anchoring pilot: ~10 random B entries, clang's assembly shown never / from the start / only in feedback; then freeze the prompt and disclose the choice (Benoit)
- [ ] Full corpus run with Muse Spark (Benoit)
- [ ] Full corpus run with LLM Compiler (Jules)
- [ ] Ablation, three arms: independent samples, "rejected" only, full counterexample (Benoit)
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

## Ideas

Bonuses once the MVP works. Tasks marked *(can start now)* do not depend on the loop.

**To win**
- [ ] Report every proven, new win upstream as an LLVM issue (C, IR, Alive2 proof). Selective: only proven, previously unreported cases.
- [ ] Live demo page of the loop: proposal, Alive2 counterexample, repair, proof, measured gain.
- [ ] Charts: ablation with vs. without counterexamples, cost per proven optimization, proven rate vs. number of attempts.

**Usefulness: prove it, don't just claim it**

Why it matters: more and more code is written by AI models, and it can only be trusted if something checks it. This project shows the pattern on the harshest ground there is, compiler optimization: the model proposes, a formal proof decides. And a win in the compiler multiplies: one rule added to LLVM improves every program clang compiles.
- [ ] Count how often our winning patterns occur in real open-source code *(can start now for known B patterns)*.
- [ ] Test the hypothesis directly: does clang miss more optimizations on AI-written code than on human-written code? Build a corpus of functions written by AI models for common tasks (corpus building, not part of the optimization loop), run the tool on it, compare with human-written entries.

**Engine**
- [ ] Two-model pipeline: LLM Compiler (free, fast) proposes first, Muse Spark repairs from counterexamples.
- [ ] Memory of wins: rewrites proven on *other* functions as few-shot examples (never `expected.ll`).
- [ ] Corpus from real code: automatically extract small pure integer functions from open-source projects *(can start now)*.
- [ ] Peephole rules: generalize wins into rules with symbolic constants, re-proven by Alive2.

**Tooling**
- [x] Verifier regression suite: deliberately wrong rewrites that `verify.py` must reject (done in M1).
- [ ] Chart scripts and demo page reading `results/<run-id>/*.json`.

**After the submission**
- [ ] Paper: a precise, formal and reproducible write-up of the approach (refinement, the counterexample-guided loop, corpus, results, threats to validity).

## Decisions (Oct 28, Benoit and Jules)

First signal (provisional: godbolt IR, online Alive2, IR instruction count, not llvm-mca): LLM Compiler alone, up to 5 attempts, on the 40 B entries: 23 proven, 15 shorter than `clang -O3`. Extra attempts added no win: the hard cases need a model that can read counterexamples.

1. **Headline: new wins, not a model race.** Aim for "N previously unreported missed optimizations in clang trunk, proven by Alive2, faster on real x86, filed upstream". New wins come from C, and also from B entries where we beat `expected.ll`. A Muse vs. LLM Compiler table stays secondary.
2. **Two-model pipeline, after the MVP.** LLM Compiler proposes first (free, ~2 s per candidate); when Alive2 rejects, Muse Spark repairs from the counterexample. Report proven wins per dollar at a fixed budget for three arms: LLM Compiler alone, Muse alone, pipeline.
3. **Grow C to 60–100 entries with small functions from real projects** (Jules). No variants of known patterns: a known pattern is a B entry, and a variant breaks "one pattern = one entry".
4. **Second reference toolchain build: low priority.**

Evaluation rules that go with them:
- Freeze prompts and corpus before the official run; disclose that the LLM Compiler prompt was tuned while looking at B.
- "Faster" means fewer llvm-mca cycles, and `opt -O3` must not fold the rewrite back; run all N candidates and keep the best proven one instead of stopping at the first proof.
- Count comparable units across models: Alive2 checks, tokens, seconds, dollars.
- Contamination table: issue date vs. each model's training cutoff (LLM Compiler: mid-2024).
- Show zero false wins on A; give confidence intervals and per-entry paired comparisons (only 40 B entries).
- Ablation with three arms: independent samples, history with "rejected" only, history with the counterexample.
- Cut if time is short: paper, AI-written-code hypothesis, peephole generalization, automatic real-code extraction, live demo page (replay one recorded trace instead).

## Key decisions

- **One toolchain, one target.** Every step, from `clang -O3` to `llvm-mca`, uses the pinned reference build and `--target=x86_64-unknown-linux-gnu -march=skylake`. The target changes the IR produced by `-O3`, so mixing targets would create fake missed optimizations.
- **The model writes bodies, never headers.** The tool places the body under the source's exact header, so the signature and function attributes cannot change.
- **Refinement, not equivalence.** Alive2 proves that the rewrite refines the original, the criterion LLVM uses for its own optimizations.
- **Only Meta models generate candidates**: Muse Spark (API) and LLM Compiler (local).
