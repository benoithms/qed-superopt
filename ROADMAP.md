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
- [ ] Verifier regression suite: deliberately wrong rewrites that `verify.py` must reject *(can start now)*.
- [ ] Chart scripts and demo page reading `results/<run-id>/*.json`.

**After the submission**
- [ ] Paper: a precise, formal and reproducible write-up of the approach (refinement, the counterexample-guided loop, corpus, results, threats to validity).

## Open decisions (proposed by Jules, to settle with Benoit)

First signal (provisional: godbolt IR, online Alive2, IR instruction count, not llvm-mca): LLM Compiler alone, up to 5 attempts, on the 40 B entries: 23 proven, 15 shorter than `clang -O3`. Extra attempts added no win: the hard cases need a model that can read counterexamples.

1. **Headline: new wins, not a model race.** Aim for "N previously unreported missed optimizations in clang trunk, proven by Alive2, faster on real x86, filed upstream". B entries then calibrate the tool (known answers); new wins can only come from C. A Muse vs. LLM Compiler table stays secondary.
2. **Two-model pipeline as the core.** LLM Compiler proposes first (free, ~2 s per candidate); when Alive2 rejects, Muse Spark repairs from the counterexample. Report proven wins per dollar at a fixed budget for three arms: LLM Compiler alone, Muse alone, pipeline. Must not delay M1.
3. **Grow C to 60–100 entries** (Jules, with kiro): variants of known patterns (bit widths, signedness, operand order, combined idioms) and small functions from well-known projects.
4. **Second reference toolchain build: keep it, low priority.** M4 promises a reproduction on a second machine; `make verify-all` on one machine may be enough if time runs short.

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
