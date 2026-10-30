# Roadmap

What is done, what comes next, and who is on it. Update this file whenever something is merged into `dev`.

Hackathon window: **Oct 26 – Nov 4, 2026**. Submission: **Wed Nov 4, 21:00 ET**.

## Done

- [x] Reference toolchain built and smoke-tested: LLVM `b974545` (clang 24.0.0git) and Alive2 `adacbd5` (Benoit)
- [x] Python project skeleton with the frozen interfaces `generate()`, `verify()`, `cost()` (Benoit)
- [x] Meta Model API access validated with `muse-spark-1.3` (Benoit)
- [x] Corpus: 134 entries (24 A, 61 B, 49 C, of which 31 from real projects); the 134 compile and the 61 `expected.ll` are proven by Alive2 with the reference toolchain (Jules, re-checked by Benoit)
- [x] LLM Compiler 7B (Q8 GGUF) running locally with llama.cpp; first loop turn done by hand (Jules)

## M1: MVP, full loop on one function (Thu Oct 29)

Reached on Oct 28: on `llvm-issue-215060`, Muse Spark's first attempt is proven by Alive2 and runs in 1.48 cycles per call instead of 3.40 for `clang -O3` (4 x86 instructions instead of 11, gain estimated by llvm-mca).

**Benoit**
- [x] `extract.py`: reference clang with `-fdiscard-value-names`, single-function extraction, `splice()` of a body under the source header
- [x] `verify.py`: `alive-tv` wrapper, strict whitelist (exit code is always 0), `ProvenResult` with files and hashes
- [x] Verifier regression suite: 10 wrong rewrites rejected, 7 correct ones proven (`tests/test_verifier_regression.py`)
- [x] `cost.py`: `llc` + `llvm-mca` for Skylake
- [x] `llm.py`: Muse Spark `generate()`, with token (including reasoning tokens) and cost logging
- [x] `loop.py`: propose, prove, repair; results written as JSON in `results/<run-id>/`; strict budget per function; one 64k token cap per call and a function stops at its first truncated answer (see M2)

**Jules**
- [x] LLM Compiler behind `generate(ir, history) -> body` (training prompt format, prefilled module header): `qed/llm_compiler.py`
- [x] Reference toolchain built on a second machine, same commits (independent reproduction): WSL2 Ubuntu 24.04, GCC, i7-9700K (Jules, Oct 29)
- [x] Corpus: more C entries; `nlz-binsearch-u32` and `clp2-u32` to B; issues 210131, 227280, 225655 and the `__builtin_assume` / `__builtin_unreachable` issues added; variants removed and C entries with a known solution moved to B after review
- [x] Corpus: settle `next-same-popcount` with the reference clang: stays C (Jules, Oct 29)
- [x] Corpus freeze: tag `corpus-v1` (134 entries); both full runs use it. Sources are frozen; only the category of a few B entries may change once the measurement is settled (Jules and Benoit, Oct 29)

## M2: First results (Fri Oct 30 – Sun Nov 1)

- [x] Anchoring pilot: 10 random B entries, clang's assembly shown never / from the start / only in feedback: same wins, "never" is cheapest and has no anchoring risk, so the prompt never shows it (Benoit, `results/pilot-anchor-*`)
- [x] Model choice (Benoit, Oct 28–29): Muse Spark vs. Muse Wonder on 15 entries (`results/pilot-wonder`); a Spark → Wonder fallback policy picked on that pilot did not hold on 14 unseen entries (1 real gain for $17, `results/validation-fallback`); 75% of all spend went to truncated answers, whose reasoning is lost. With one 64k cap and no retry after a truncation (`results/highcap-cascade`), Muse Spark matched or beat the old Muse Wonder results at a fraction of the cost, with a median of 9 s to its first proven win. **Decision: Muse Spark alone, 64k tokens, for the corpus.** Muse Wonder needs more than 64k tokens and 10 minutes per call on our largest functions: kept for a later experiment on truly large functions
- [x] Spending controls: hard cap per run checked before every call (worst case reserved, cached answers free), streamed calls, no hidden client retries (Benoit)
- [x] Full corpus run with Muse Spark (Benoit, Oct 29–30, `results/spark-full-v1`): 134 entries, 64k tokens, about $36.8 including failed calls (the server sometimes ends an answer empty, without token usage, after 5 to 8 minutes: such a call now ends the entry but keeps its paid attempts). After `scripts/fold_back.py`: 79 of 105 wins kept, 2 A, 52 B, 25 C; 53 without any branch, 26 to confirm on the i7-9700K. C wins without any branch: libcxx-days-from-civil, rgb565-to-rgb888, scale-u10-to-u8, fletcher16-update, bitfield-insert-u32, hamming74-encode, dos-time-to-seconds
  - [ ] **Report the 2 A wins, never hide or silently re-label them**: on 2 of the 24 A controls the model beat clang, and inspection shows real improvements, so their A label was wrong. `align-up-pow2`: `((x - 1) & -a) + a` instead of `(x + a - 1) & -a`, a missed IR simplification; `rot-lr-xor`: two variable rotates done as BMI2 shifts of `x` doubled to 64 bits, an x86 lowering gap (the IR is already optimal). Both branch-free; to measure on the i7-9700K and to search in LLVM issues (Benoit, Oct 30)
- [x] Full corpus run with LLM Compiler (Jules), on one machine: RTX 4070 Ti (CUDA, 56 tokens/s vs. 7 on the M1 Mac mini). On 40 B entries × 3 attempts, CUDA and Metal wrote the same candidate 85% of the time and found the same 13 faster proven rewrites; the gap is a limitation to state in the paper. `run.json` records the llama.cpp build, GGUF sha256, quantization, GPU and generation settings. Done Oct 29 (`results/llmc-full-az4`, 134 entries in 57 min, no error): 5 attempts, which are 5 independent samples since LLM Compiler cannot read counterexamples. Proven rewrite on 12 A, 39 B, 29 C; faster than clang -O3 on 1 A, 20 B, 9 C; after the fold-back check with a 5% threshold: 0 A, 19 B, 7 C. Its `run.json` still lists Muse settings (fixed since in `loop.py`): ignore them
- [ ] Ablation, three arms: independent samples, "rejected" only, full counterexample (Benoit)
- [ ] Muse Spark vs. LLM Compiler comparison: proven-candidate rate, gains, cost (together)
- [ ] Triage of real wins: gain on the final assembly, and `opt -O3` must not fold the rewrite back (Benoit)
  - [x] Fold-back check: `scripts/fold_back.py` runs `opt -O3` on every win and re-measures it (Jules). On `llmc-full-az4` it catches `cmp3-i64` (A, x1.17: `opt -O3` re-forms `llvm.scmp`, a backend lowering issue)
  - [x] Minimum gain: 5% (`--min-speedup 1.05`), fixed before the Muse Spark run and applied the same way to both models. llvm-mca is deterministic: 0.01 cycle per call is below its resolution (1 simulated cycle in 100 iterations), not noise (Jules and Benoit, Oct 29)
  - [x] Measurement rule (Benoit and Jules, Oct 29): a win counts when llvm-mca's Block RThroughput (no dependency between calls) or one call (`-iterations=1`, latency) is better by more than 5%, and the other is not worse; a real caller may need either. One call is a whole number of cycles (about 10), so one cycle is about 10%: a coarse measure, one more reason to confirm on the CPU (Benoit, Oct 29: the first version required throughput and rejected latency-only gains). The chained figure (100 calls back to back, what `cost()` reports) is kept for the record only: a register reused as a temporary there delays the next call's argument (zstd-fse-optimal-table-log x1.43 -> x1.00). llvm-mca reads both sides of a branch in a straight line, so a win with a branch in clang's or the rewrite's assembly is marked "confirm on CPU". `scripts/fold_back.py` applies all of it. On `llmc-full-az4`: 22 of 30 wins kept (16 B, 6 C); 12 B without any branch, 10 to confirm on the i7-9700K
  - [ ] Re-check every B `expected.ll` and earlier Muse Spark runs with the same rule (the B rule "faster in cycles" used the chained figure)
  - [ ] No numbers announced (README, demo, LLVM issues) before the measurement is settled
  - [ ] The 7 C wins kept on `llmc-full-az4` (zstd-fse-optimal-table-log x1.43, zstd-cparam-row-size x1.23, median3-i32 x1.21 after opt, opus-silk-rshift-round x1.17, lua-shiftl x1.14, linux-ewma-add x1.11, zstd-compress-bound x1.07): search existing LLVM issues before calling any of them new, then measure on the i7-9700K (Jules). Added from `spark-full-v1` (Benoit, Oct 30): the 7 C wins without any branch (libcxx-days-from-civil, rgb565-to-rgb888, scale-u10-to-u8, fletcher16-update, bitfield-insert-u32, hamming74-encode, dos-time-to-seconds), the 2 A wins (align-up-pow2, rot-lr-xor), and each C win with a branch once the i7-9700K confirms it

## M3: Confirmation on real hardware (Mon Nov 2)

- [ ] x86 microbenchmark harness: separate object, no inlining, latency and throughput (Benoit)
- [ ] Measurements from the same `.s`: i7-9700K, reference (Jules); i7-12700H (Benoit). Now the priority: no C win is confirmed without it. Every win with a branch is measured with predictable and with random inputs, and the report says in which case it holds
  - [x] i7-9700K (Jules, Oct 30, `results/bench-9700k/`, `scripts/bench_cpu.py --all-kept`): WSL2, Windows processor boost disabled, core clock measured 3.54-3.58 GHz (one Spark launch dipped to 3.01), median spread between launches 0.5-0.7%. Spark: of 79 kept wins, 35 faster in both modes (17 B, 18 C), 3 C only with random inputs, 39 no measurable gain, 2 slower. LLM Compiler: of 22, 9 faster in both modes, 2 C only with random inputs, 11 no measurable gain. Limits: a call through the timing loop costs about 5 cycles, and most branch-free B wins sit at that floor (clang, rewrite and empty function equal), so "no measurable gain" means not visible when called as a function, not disproven. `rot-lr-xor` (A) is slower on the CPU (0.88x in both modes), against llvm-mca; `align-up-pow2` (A) shows no gain. A first version had one timing loop per function, and loop placement made a constant function look 20% slower: fixed by one aligned loop for all
- [ ] Stretch: generalize wins into peephole rules, re-proven by Alive2 (Benoit)

## M4: Submission (Tue Nov 3 – Wed Nov 4)

- [ ] Results in the README, demo page (together)
- [x] `scripts/verify_all.py`: re-checks the corpus and re-runs Alive2 on every recorded proof, with hash checks (Benoit; Oct 29: 103 entries and 142 proofs, 0 problems)
- [x] The same check reproduced on a second machine: WSL2 Ubuntu 24.04 built with GCC, 103 entries and 142 proofs, then 134 entries with real-code, 0 problems (Jules, Oct 29)
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
- [ ] Muse Wonder on truly large functions: needs a corpus of large functions, splitting them into pieces Alive2 can prove, and more than 64k tokens per call.

**Tooling**
- [x] Verifier regression suite: deliberately wrong rewrites that `verify.py` must reject (done in M1).
- [ ] Chart scripts and demo page reading `results/<run-id>/*.json` (Jules: comparison and chart scripts first).

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
- **One high token cap, no blind retries.** The API returns no reasoning, so a truncated answer is lost and a retry starts over: Muse Spark gets 64k tokens per call and a function stops at its first truncation.
- **Hard spending cap.** Every paid run has a cap checked before each call; only free credits are spent.
