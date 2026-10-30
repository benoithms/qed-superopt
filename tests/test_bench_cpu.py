import platform
import random
import sys
from pathlib import Path

import pytest

from qed import config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import bench_cpu  # noqa: E402

LL = (
    "define dso_local noundef zeroext i1 @f(i1 noundef zeroext %0, i64 noundef %1, "
    "i8 noundef signext %2) local_unnamed_addr #0 {\n  ret i1 %0\n}\n"
)


def test_signature_maps_ir_types_to_c():
    assert bench_cpu.signature(LL) == ("bool", ["bool", "int64_t", "int8_t"], [1, 64, 8])


def test_candidates_fit_their_width():
    for args in bench_cpu.candidates([1, 8, 64], random.Random(0), 500):
        assert args[0] < 2 and args[1] < 2**8 and args[2] < 2**64


def test_renamed_changes_only_the_definition():
    out = bench_cpu.renamed(LL, "f_src")
    assert "@f_src(i1" in out and "@f(" not in out


ASM = """\t.text
\t.globl\tf_src
\t.type\tf_src,@function
f_src:                                  # @f_src
\t.cfi_startproc
# %bb.0:
\ttestl\t%edi, %edi
\tje\t.LBB0_2
\tmovl\t$1, %eax
\tretq
.LBB0_2:
\txorl\t%eax, %eax
\tretq
.Lfunc_end0:
\t.size\tf_src, .Lfunc_end0-f_src
\t.cfi_endproc
"""


def test_inline_loop_turns_rets_into_jumps_and_loads_the_arguments():
    out = bench_cpu.inline_loop(ASM, "f_src", 2)
    assert "loop_f_src:" in out and "retq" not in out.split("loop_f_src:")[1].split("popq")[0]
    assert out.count("jmp\t.Lnext_f_src") == 1  # the last ret falls through
    assert "131072(%r12,%rbx,8), %rsi" in out  # 2nd argument: CALLS * 8 bytes further
    assert ".cfi_" not in out and "\tf_src," not in out


def test_summarize_needs_every_launch_above_the_threshold():
    def launch(src, tgt):
        m = {"src": {"median": src}, "tgt": {"median": tgt}, "nop": {"median": 1.0}}
        return {"predictable": m, "random": m}

    assert bench_cpu.summarize([launch(10.3, 10), launch(12, 10)], 1.05)["random"]["verdict"] == (
        "no clear gain"
    )
    assert bench_cpu.summarize([launch(12, 10), launch(13, 10)], 1.05)["random"]["verdict"] == (
        "faster"
    )
    assert bench_cpu.summarize([launch(9, 10)], 1.05)["random"]["verdict"] == "slower"


def test_summarize_survives_a_rewrite_as_cheap_as_the_empty_function():
    m = {"src": {"median": 3.0}, "tgt": {"median": 1.0}, "nop": {"median": 1.0}}
    out = bench_cpu.summarize([{"predictable": m, "random": m}], 1.05)
    assert out["random"]["net_speedup"] is None and out["random"]["verdict"] == "faster"


@pytest.mark.skipif(
    platform.system() != "Linux" or platform.machine() != "x86_64" or config.check_toolchain(),
    reason="runs x86-64 Linux code built by the reference toolchain",
)
def test_driver_runs_and_traps_are_dropped(tmp_path):
    src = (
        "define dso_local noundef i8 @f(i8 noundef zeroext %0, i8 noundef zeroext %1) "
        "local_unnamed_addr #0 {\n  %3 = udiv i8 %0, %1\n  ret i8 %3\n}\n"
    )
    exe = bench_cpu.build(src, src, tmp_path, 3, 1)
    out = bench_cpu.json.loads(bench_cpu._run([exe]))
    assert out["dropped"] > 0 and out["differ"] == 0
    assert out["random"]["src"]["median"] > 0 and out["random"]["inline_tgt"]["median"] > 0


def test_overall_needs_one_faster_and_no_slower_number():
    def row(*verdicts):
        modes = ("predictable", "random", "predictable_inline", "random_inline")
        return {m: {"verdict": v} for m, v in zip(modes, verdicts, strict=True)} | {"id": "f"}

    assert (
        bench_cpu.overall(row("no clear gain", "no clear gain", "faster", "faster")) == "confirmed"
    )
    assert bench_cpu.overall(row("slower", "faster", "slower", "faster")) == "depends on context"
    assert bench_cpu.overall(row("slower", "slower", "no clear gain", "no clear gain")) == "slower"
    assert bench_cpu.overall(row(*["no clear gain"] * 4)) == "no gain"


def test_slower_needs_every_launch_below_098():
    def launch(src, tgt):
        m = {"src": {"median": src}, "tgt": {"median": tgt}, "nop": {"median": 1.0}}
        return {"predictable": m, "random": m}

    assert bench_cpu.summarize([launch(9.9, 10)], 1.05)["random"]["verdict"] == "no clear gain"
    assert bench_cpu.summarize([launch(9.7, 10)], 1.05)["random"]["verdict"] == "slower"
