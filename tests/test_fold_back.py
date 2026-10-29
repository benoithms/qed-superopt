import sys
from pathlib import Path

from qed.cost import cost
from qed.extract import extract, splice

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fold_back  # noqa: E402

CMP3 = (
    "#include <stdint.h>\n"
    "int32_t f(int64_t a, int64_t b) { if (a < b) return -1; if (a > b) return 1; return 0; }\n"
)
# Proven and faster in llvm-mca cycles than clang's llvm.scmp, but opt -O3 re-forms scmp.
CMP3_REWRITE = """  %3 = icmp slt i64 %0, %1
  %4 = icmp sgt i64 %0, %1
  %5 = zext i1 %4 to i32
  %6 = select i1 %3, i32 -1, i32 %5
  ret i32 %6"""


def _result(tmp_path, c_src, rewrite):
    (tmp_path / "src.c").write_text(c_src)
    src = extract(tmp_path / "src.c")
    tgt = splice(src, rewrite)
    base, c = cost(src).mca_cycles, cost(tgt).mca_cycles
    return {
        "id": "t",
        "category": "A",
        "src_ll": src,
        "baseline": {"mca_cycles": base},
        "attempts": [{"n": 1, "check": "proven", "tgt_ll": tgt}],
        "best": {"n": 1, "mca_cycles": c, "speedup": base / c},
    }


def test_a_rewrite_that_opt_folds_back_is_not_kept(tmp_path):
    res = _result(tmp_path, CMP3, CMP3_REWRITE)
    assert res["best"]["speedup"] > 1.1  # the win the loop recorded
    r = fold_back.check(res, 1.0)
    assert r["back_to_clang"] and not r["kept"]
    assert r["chained"] == 1.0 and r["one_call"] == 1.0


def test_branches_are_detected_in_the_assembly():
    assert fold_back.has_branch("f:\n\ttestl %edi, %edi\n\tje .LBB0_2\n\tretq\n.Lfunc_end0:")
    assert not fold_back.has_branch("f:\n\tcmpq %rsi, %rdi\n\tcmovgel %ecx, %eax\n\tretq\n")
