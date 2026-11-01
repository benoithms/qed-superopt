# [TODO: component] Missed fold: TODO short pattern description

DRAFT, not filed. Reproduced at LLVM $llvm_commit. Trunk check and duplicate search: TODO.

TODO: one or two sentences, by the person filing: what LLVM misses and why it matters.

## Reproducer

```llvm
$src_fn
```

Expected:

```llvm
$tgt_fn
```

Alive2 proof of this case (proven locally with `alive-tv` at $alive2_commit): TODO link
Godbolt (clang trunk, `-O3 --target=x86_64-unknown-linux-gnu -march=skylake`): TODO link

## Codegen impact

$gain_scope

Gain estimated by llvm-mca (`-mcpu=skylake`): $mca_summary

<details><summary>Full function, assembly diff and timings</summary>

$full_case
```diff
$asm_diff
```

Speedup over clang -O3 on real CPUs, lowest to highest of $launches launches, loop overhead included:

| | Call, predictable | Call, random | Inline, predictable | Inline, random |
|---|---:|---:|---:|---:|
$cpu_rows

</details>

## Context

Found in: $description (source: $source).

The candidate rewrite was found by [qed-superopt]($repo), an LLM-guided superoptimizer using $model, and verified with Alive2. We checked the proof and reviewed this report, and we take responsibility for it. An AI assistant helped prepare the report template and the tooling that fills in the data.
