# Whole-program test: stb_image

**Status: protocol fixed, not run.** QED has only been measured on isolated functions. This test asks whether it changes the speed of a real program, here PNG decoding in [stb_image](https://github.com/nothings/stb). This protocol is committed before any model call or timing on x86. If a rule changes later, the change gets its own commit and its reason.

Seen before fixing it: Paeth calls are 25.3% of the decoded bytes of these images (a count, not a time), and one smoke run on Apple silicon gave 6.4% of the time in Paeth rows. That second number is not on the target CPUs and does not count.

## What is fixed

- **Program:** `stb_image.h` v2.30, at the commit and hash in `project.json`. `STB_IMAGE_IMPLEMENTATION` and `STBI_ONLY_PNG`, otherwise its default settings.
- **Images:** the 24 images of the Kodak Image Suite, hashes in `project.json`. None is removed after the fact. How much they use Paeth depends on the encoder that wrote them, so they do not stand for all PNG files.
- **Toolchain and target:** the pinned reference LLVM, `-O3 --target=x86_64-unknown-linux-gnu -march=skylake`.
- **CPUs:** i7-9700K and i7-12700H, the same binary, 5 launches each, pinned.
- **Functions:** `functions/paeth-int` is `stbi__paeth` as written. `functions/paeth-u8` has byte arguments, which is what its call site passes. These are the only candidates: the other small pure functions of the file are not on the per-pixel path of PNG decoding.
- **Budget:** a hard cap of $2 on Muse Spark for this test.

## Steps

1. **Profile.** `profile.py` measures the share of decoding spent in Paeth rows. It includes the rest of the row, so it is an upper bound. We continue only if the median share is at least 5% on both CPUs.
2. **Search.** QED runs on both functions under the usual rules: a rewrite counts only if Alive2 proves it (refinement) and our function-level rule keeps it.
3. **Put back.** The proven rewrite replaces the body of `stbi__paeth` in the IR of the whole program, for `paeth-u8` behind a truncation of the arguments to bytes. Then the whole program goes through `opt -O3` and `llc`. The source of the comparison is the same program without this change.
4. **Measure.** Total decoding time of the 24 images, 5 launches per CPU, both binaries in turn.

## What counts as a result

**A win** is a whole-decoding speedup above 1.02x on every launch, on both CPUs. Anything else is reported as no win, with the numbers. The spread between launches is reported.

A stop at any step is a result too, and it is published here. Results go to `results/real-projects/stb-image/`, apart from the numbers of corpus-v1, which do not change.

## Run

```sh
python real-projects/stb-image/fetch.py
PYTHONPATH=. python real-projects/stb-image/profile.py --machine "<turbo, power plan, what else runs>" --out results/real-projects/stb-image/profile-<cpu>.json
```

stb_image is public domain or MIT, at the choice of the user. We do not commit it, and the two functions above are adapted from it with credit in their `meta.json`.
