# Whole-program test: SQLite

**Status: stopped at step 3, no win.** Rewriting one small function could not show a gain in [stb_image](../stb-image/README.md). This test rewrites many hot zones of a large program, SQLite, and asks whether the whole program gets faster. This protocol is committed before any model call or timing on x86. If a rule changes later, the change gets its own commit and its reason.

Seen before fixing it, on Apple silicon, so these numbers do not count: a block counter over the benchmark, then a proof check on the 100 heaviest candidates. The 20 kept zones hold 22.4% of the executed instructions, so a 3% win would need about 1.15x on all of them. They are small, 5 to 17 instructions. A win is far from certain.

## Result

**No win: the test stops before steps 4 and 5, because the gains found do not survive next to the code that uses each zone.** One real rewrite remains, too small to change the program.

- **Count and pick, on x86:** 100 candidates, 82 proven with a correct change that does nothing, 20 kept, holding 21.8% of the executed instructions. The 15% rule passes.
- **Search:** $4.05 of the $10 cap. Muse Spark found proven rewrites estimated faster by llvm-mca on 17 of the 20 zones, from 1.01x to 7.40x when each zone is measured alone.
- **These numbers are mostly an artifact of how we cut the zones.** A zone returns an exit code that the program branches on right away. Measured alone, a rewrite that turns the branch into a value looks faster, but the branch is still there in the program. Our function-level rule does not see this. The proofs are valid: the rewrites are correct, not faster.
- **Next to the code that uses them** (`in_caller.py`, assembly after `opt -O3` and `llc`):

| Result of the 17 rewrites | Zones |
|---:|:---|
| 8 | identical assembly |
| 3 | same instructions, other order |
| 2 | other instructions, same count |
| 1 | one instruction more |
| 2 | not settled: the exit code is not `i1`, so this check does not branch on it |
| 1 | shorter: a real rewrite |

- **The real rewrite** reads a signed big-endian 16-bit value, in `vdbeRecordCompareInt`. Clang forms `movbe` for the unsigned form of this code, and at our pinned commit not for the signed one, also from plain C. llvm-mca gives 1.46x for the zone alone. It holds 0.9% of the executed instructions, so it can give at most about 0.3%, far below the 3% threshold.
- **What we take from it:** a single block is too small a window, and its gain must be measured with its caller. Reading hot real code did lead to one lead for LLVM, which remains to be checked on trunk and against existing issues.
- **Changes from this protocol:** the stop before steps 4 and 5, and the `in_caller.py` check, were decided after seeing the search results, because the results looked too good. The two unsettled zones are dispatch switches: we expect no gain there since the program still branches on the value, but we did not measure it.

Raw data: `results/real-projects/sqlite/`.

## What is fixed

- **Program:** SQLite 3.50.4 amalgamation, 262,899 lines of C, at the hash in `project.json`, with the defines listed there.
- **Workload:** `speedtest1` from the same version, with the arguments in `project.json`, on an in-memory database. It stands for this benchmark, not for every use of SQLite.
- **Toolchain and target:** the pinned reference LLVM, `-O3 --target=x86_64-unknown-linux-gnu -march=skylake`.
- **CPUs:** i7-9700K and i7-12700H, the same binaries, 5 launches each, pinned.
- **Budget:** a hard cap of $10 on Muse Spark for this test.

## Steps

1. **Count.** `zones.py` counts every block of the IR of `sqlite3.c` over the workload. A block's weight is its runs times its instructions: an exact count, the same on any CPU, but only an estimate of time. Zones are blocks of 4 to 60 instructions with no loop, call or global, heaviest first, as functions that return the values the rest of the program uses.
2. **Pick.** `pick.py` keeps the first 20 of the 100 heaviest zones for which Alive2 proves a correct change that does nothing. We continue only if 20 zones are kept and they hold at least 15% of the executed instructions.
3. **Search.** QED runs on the 20 zones under the usual rules: Alive2 must prove the rewrite (refinement), with no loop, and the function-level rule of `scripts/fold_back.py` must keep it.
4. **Put back.** Every kept rewrite goes back into the program. The zones are cut out with LLVM's `extract-blocks`, then inlined. The baseline goes through the same steps with the zones unchanged, so the two builds differ only by the rewrites.
5. **Measure.** `speedtest1`, 5 launches per CPU, both binaries in turn, and the same output required before any timing.

## What counts as a result

**A win** is a whole-program speedup above 1.03x on every launch, on both CPUs. Anything else is reported as no win, with the numbers. The spread between launches is reported.

A stop at any step is a result too, and it is published here. Results go to `results/real-projects/sqlite/`, apart from the numbers of corpus-v1, which do not change.

## Limits of the proof

Alive2 proves each zone as its own function, which may read and write memory. Two things come from construction, not from a proof: returning the outputs instead of storing them through LLVM's fresh local pointers, and the fact that each zone goes back exactly where it was cut. Same output on the workload is a check, not a proof.

## Run

```sh
python real-projects/sqlite/fetch.py
PYTHONPATH=. python real-projects/sqlite/zones.py --out results/real-projects/sqlite/zones.json
PYTHONPATH=. python real-projects/sqlite/pick.py results/real-projects/sqlite/zones.json --out results/real-projects/sqlite/picked.json
PYTHONPATH=. python real-projects/sqlite/search.py results/real-projects/sqlite/picked.json --max-total 10
PYTHONPATH=. python real-projects/sqlite/in_caller.py results/real-projects/sqlite/spark
```

SQLite is in the public domain. We do not commit it. `pick.py` and `search.py` need Alive2, so they run on the Mac.
