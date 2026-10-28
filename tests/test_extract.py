import pytest

from qed.extract import ExtractError, extract, function, splice

POW2 = """#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x) { return x && !(x & (x - 1)); }
"""


@pytest.fixture
def pow2_ir(tmp_path):
    c = tmp_path / "src.c"
    c.write_text(POW2)
    return extract(c)


def test_extract_targets_skylake(pow2_ir):
    # Without -march=skylake, clang keeps a branch instead of forming ctpop.
    assert "@llvm.ctpop.i32" in function(pow2_ir)
    assert "br " not in function(pow2_ir)


def test_extract_numbers_values(pow2_ir):
    assert "%x" not in pow2_ir
    assert "i32 noundef %0" in function(pow2_ir)


def test_extract_rejects_two_functions(tmp_path):
    c = tmp_path / "src.c"
    c.write_text("int f(int x) { return x; }\nint g(int x) { return -x; }\n")
    with pytest.raises(ExtractError, match="exactly one function"):
        extract(c)


def test_splice_keeps_source_header(pow2_ir):
    out = splice(pow2_ir, "  ret i1 false")
    src_header = function(pow2_ir).split("\n", 1)[0]
    assert function(out) == f"{src_header}\n  ret i1 false\n}}\n"


def test_splice_discards_model_header(pow2_ir):
    candidate = "```llvm\ndefine i1 @f(i32 %0) nounwind {\n  ret i1 false\n}\n```"
    out = splice(pow2_ir, candidate)
    assert "nounwind {" not in function(out)
    assert function(out).endswith("\n  ret i1 false\n}\n")


def test_splice_allows_intrinsics(pow2_ir):
    out = splice(pow2_ir, "  %2 = call i32 @llvm.ctpop.i32(i32 %0)\n  ret i1 true")
    assert "@llvm.ctpop.i32" in function(out)


def test_splice_rejects_calls(pow2_ir):
    with pytest.raises(ExtractError, match="only LLVM intrinsics"):
        splice(pow2_ir, "  %2 = call i1 @g(i32 %0)\n  ret i1 %2")


def test_splice_rejects_empty(pow2_ir):
    with pytest.raises(ExtractError, match="empty"):
        splice(pow2_ir, "```\n```")
