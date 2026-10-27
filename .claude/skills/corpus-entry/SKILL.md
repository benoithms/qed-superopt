---
name: corpus-entry
description: Create or review a qed-superopt corpus entry bench/<A|B|C>/<id>/ (src.c, meta.json, expected.ll), enforcing the eligibility criteria and the contamination rule. Use when adding functions from LLVM missed-optimization issues, Hacker's Delight, Bit Twiddling Hacks or Souper, or when auditing existing entries.
---

# Corpus entry

Argument: a source (issue URL, bit hack name, function idea) or a `bench/...` path to review. $ARGUMENTS

## 1. Eligibility: every criterion is mandatory

Reject (and say why) any function that fails one of them:
- a single function, not `static`;
- pure: no pointer, array, global variable or call to another function;
- no `for`, `while`, backward `goto` or recursion;
- types `int8_t`–`int64_t`, `uint*_t` or `bool` (`<stdint.h>`, `<stdbool.h>`), no `float` or `double`;
- builtins are allowed if they lower to LLVM intrinsics: `__builtin_popcount*`, `__builtin_clz*`, `__builtin_ctz*`, `__builtin_bswap*`, `__builtin_*_overflow`;
- size after `-O3 -march=skylake`: at most 30 IR instructions; at least 5 for category C only (A has no floor, B is kept whatever its size). Estimate, then confirm once the reference toolchain is available.

## 2. Category

- **A, control**: clang already produces optimal code. A B case that clang trunk now optimizes moves here.
- **B, known miss**: the better version is known (LLVM issue, Souper). Add `expected.ll` if available: only its body matters (the header comes from the source), and it will itself be proven by Alive2 against the source.
- One optimization pattern = one entry: if a C entry's solution is known, it is a B entry (cite the issue in `notes`).
- An issue that does not reproduce from C: if clang already optimizes it, move it to A; if it was reported at IR level (e.g. from Rust) and the C does not produce the same IR, drop it for now.
- **C, unknown**: we don't know whether it can be improved. For a bit hack, write the **naive** version in C.

`id`: stable kebab-case, e.g. `llvm-issue-12345`, `hd-turn-off-rightmost-bit`, `bth-sign-extend`.

## 3. Contamination rule (critical)

`src.c` is sent **as-is** to the model. It must contain:
- no comment describing the expected optimization, the clever version, the issue or the word "missed";
- no function or variable name that gives away the solution (`f` rather than `x_and_neg_x`);
- no unnecessary `#include`.

The solution goes **only** into `expected.ll` and optionally `meta.json` (`description`, `notes`). When done, re-read every `src.c` you created specifically for this point.

## 4. Files

`bench/<cat>/<id>/src.c`: the function alone, with the needed includes. Write it yourself from the idea: never paste code from the source (especially long excerpts from the Hacker's Delight book). The source is always cited in `meta.json`.

`bench/<cat>/<id>/meta.json`:
```json
{
  "id": "llvm-issue-12345",
  "category": "B",
  "source": "https://github.com/llvm/llvm-project/issues/12345",
  "description": "Three-way comparison not simplified",
  "known_solution": true,
  "still_missed_on": "clang trunk (godbolt), YYYY-MM-DD",
  "notes": ""
}
```
- `still_missed_on`: state how it was checked. For now, "clang trunk (godbolt)" + date (Compiler Explorer, `x86-64 clang (trunk)`, `-O3 --target=x86_64-unknown-linux-gnu -march=skylake -emit-llvm -S`). Without `-march=skylake` the IR is wrong for our target (e.g. no `ctpop`), and the category may be wrong too. Never claim it was checked if it wasn't: use `"unverified"`.
- Do not use `/usr/bin/clang` (Apple clang) for this check: it is not the reference compiler.

## 5. Refinement

Two versions that differ only on inputs where the source has UB (signed overflow, shift ≥ bit width, division by zero, `INT_MIN / -1`) are not wrong: Alive2 accepts this refinement. Account for it before categorizing a case.

## 6. Doubtful cases

Don't decide alone: at the end, list doubtful entries (uncertain category, borderline size, subtle UB, unverified solution) with a one-line explanation each, for Benoit and Jules to decide.
