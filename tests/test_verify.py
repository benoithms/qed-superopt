from qed.extract import splice
from qed.verify import Status, classify, sha256, verify

# x + 1 > x on a signed int: with nsw, overflow is UB, so `true` is a valid refinement.
SRC_NSW = """define i1 @f(i32 %0) {
  %2 = add nsw i32 %0, 1
  %3 = icmp sgt i32 %2, %0
  ret i1 %3
}
"""
SRC_WRAP = SRC_NSW.replace("add nsw", "add")


def test_proven_refinement():
    tgt = splice(SRC_NSW, "  ret i1 true")
    r = verify(SRC_NSW, tgt)
    assert r.status is Status.PROVEN
    assert r.proof is not None
    assert r.proof.tgt_ll == tgt
    assert r.proof.tgt_sha256 == sha256(tgt)


def test_counterexample_without_nsw():
    r = verify(SRC_WRAP, splice(SRC_WRAP, "  ret i1 true"))
    assert r.status is Status.COUNTEREXAMPLE
    assert r.proof is None
    assert "2147483647" in r.counterexample


def test_identical_candidate_is_unchanged():
    r = verify(SRC_NSW, SRC_NSW)
    assert r.status is Status.UNCHANGED
    assert r.proof is None


def test_invalid_ir_is_not_proven():
    r = verify(SRC_NSW, splice(SRC_NSW, "  ret i1 %nope"))
    assert r.status is Status.NOT_PROVEN
    assert r.proof is None


# The counter steps by 5 instead of 4: Alive2 alone prints its success message on this pair.
LOOP = """define void @f(i64 %0, ptr %1) {
  br label %3
3:
  %4 = phi i64 [ 0, %2 ], [ %6, %3 ]
  %5 = getelementptr i64, ptr %1, i64 %4
  store i64 %4, ptr %5, align 8
  %6 = add i64 %4, 4
  %7 = icmp eq i64 %6, %0
  br i1 %7, label %8, label %3
8:
  ret void
}
"""


def test_wrong_loop_is_not_proven():
    r = verify(LOOP, LOOP.replace("%4, 4", "%4, 5"))
    assert r.status is Status.NOT_PROVEN
    assert r.proof is None
    assert "loop" in r.output


def test_candidate_with_a_loop_is_not_proven():
    r = verify(SRC_NSW, splice(SRC_NSW, "  br label %2\n2:\n  br label %2"))
    assert r.status is Status.NOT_PROVEN
    assert r.proof is None


def test_unexpected_output_is_not_proven():
    assert classify("") is Status.NOT_PROVEN
    assert classify("Transformation seems to be correct!\n") is Status.NOT_PROVEN  # no summary
    approx = (
        "Transformation seems to be correct!\n\nSummary:\n  1 correct transformations\n"
        "  0 incorrect transformations\n  0 failed-to-prove transformations\n"
        "  0 Alive2 errors\nAlive2 approximated the semantics\n"
    )
    assert classify(approx) is Status.NOT_PROVEN
