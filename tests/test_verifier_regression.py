"""Verifier regression suite: we test the tester.

Every WRONG rewrite must be rejected with a counterexample, every CORRECT one must be proven.
Wrong cases are subtle on purpose: they hold on almost every input and break on one
(INT_MIN, a zero divisor, a poison input, a shift past the bit width), which is exactly
what a random tester misses. A single failure here blocks everything."""

import pytest

from qed.extract import splice
from qed.verify import Status, classify, verify


def fn(params: str, ret: str, body: str) -> str:
    return f"define {ret} @f({params}) {{\n{body}\n}}\n"


# (name, source module, candidate body, why it is wrong)
WRONG = [
    (
        "abs-int-min",
        fn("i32 %0", "i32", "  %2 = call i32 @llvm.abs.i32(i32 %0, i1 false)\n  ret i32 %2"),
        "  %2 = icmp slt i32 %0, 0\n  %3 = sub nsw i32 0, %0\n"
        "  %4 = select i1 %2, i32 %3, i32 %0\n  ret i32 %4",
        "abs(INT_MIN) is defined in the source, but sub nsw 0, INT_MIN is poison",
    ),
    (
        "shift-past-width",
        fn("i32 %0, i32 %1", "i32", "  %3 = and i32 %1, 31\n  %4 = shl i32 %0, %3\n  ret i32 %4"),
        "  %3 = shl i32 %0, %1\n  ret i32 %3",
        "the source masks the shift amount; shl by 32 or more is poison",
    ),
    (
        "added-nsw",
        fn("i32 %0, i32 %1", "i32", "  %3 = add i32 %0, %1\n  ret i32 %3"),
        "  %3 = add nsw i32 %0, %1\n  ret i32 %3",
        "the source wraps on overflow; the candidate turns overflow into poison",
    ),
    (
        "introduced-division-by-zero",
        fn("i32 %0", "i32", "  ret i32 0"),
        "  %2 = udiv i32 %0, %0\n  %3 = sub i32 %2, 1\n  ret i32 %3",
        "x / x - 1 is 0 for x != 0, but dividing by zero is UB",
    ),
    (
        "off-by-one",
        fn("i32 %0", "i1", "  %2 = icmp ult i32 %0, 10\n  ret i1 %2"),
        "  %2 = icmp ule i32 %0, 10\n  ret i1 %2",
        "differs only at x = 10",
    ),
    (
        "logical-vs-arithmetic-shift",
        fn("i32 %0", "i32", "  %2 = lshr i32 %0, 1\n  ret i32 %2"),
        "  %2 = ashr i32 %0, 1\n  ret i32 %2",
        "differs on every negative input",
    ),
    (
        "sdiv-rounding",
        fn("i32 %0", "i32", "  %2 = sdiv i32 %0, 2\n  ret i32 %2"),
        "  %2 = ashr i32 %0, 1\n  ret i32 %2",
        "sdiv rounds toward zero, ashr toward minus infinity: wrong on negative odd inputs",
    ),
    (
        "wrong-mask",
        fn("i32 %0", "i32", "  %2 = trunc i32 %0 to i8\n  %3 = zext i8 %2 to i32\n  ret i32 %3"),
        "  %2 = and i32 %0, 127\n  ret i32 %2",
        "keeping 8 bits needs mask 255, not 127",
    ),
    (
        "select-to-and-poison",
        fn("i1 %0, i1 %1", "i1", "  %3 = select i1 %0, i1 %1, i1 false\n  ret i1 %3"),
        "  %3 = and i1 %0, %1\n  ret i1 %3",
        "when %0 is false the source ignores %1; `and` propagates a poison %1",
    ),
    (
        "model-written-header-is-ignored",
        fn("i32 %0", "i1", "  %2 = icmp ult i32 %0, 10\n  ret i1 %2"),
        "define i1 @f(i32 range(i32 0, 10) %0) {\n  ret i1 true\n}",
        "the model tries to add a range assumption; splice keeps the source header",
    ),
]

# (name, source module, candidate body)
CORRECT = [
    (
        "nsw-overflow-is-ub",
        fn("i32 %0", "i1", "  %2 = add nsw i32 %0, 1\n  %3 = icmp sgt i32 %2, %0\n  ret i1 %3"),
        "  ret i1 true",
    ),
    (
        # In i8: the same proof in i32 times out in Z3 (see test_timeout_is_not_proven).
        "sdiv-by-two",
        fn("i8 %0", "i8", "  %2 = sdiv i8 %0, 2\n  ret i8 %2"),
        "  %2 = lshr i8 %0, 7\n  %3 = add i8 %0, %2\n  %4 = ashr i8 %3, 1\n  ret i8 %4",
    ),
    (
        "right-mask",
        fn("i32 %0", "i32", "  %2 = trunc i32 %0 to i8\n  %3 = zext i8 %2 to i32\n  ret i32 %3"),
        "  %2 = and i32 %0, 255\n  ret i32 %2",
    ),
    (
        "select-to-and-with-freeze",
        fn("i1 %0, i1 %1", "i1", "  %3 = select i1 %0, i1 %1, i1 false\n  ret i1 %3"),
        "  %3 = freeze i1 %1\n  %4 = and i1 %0, %3\n  ret i1 %4",
    ),
    (
        "dropping-nsw",
        fn("i32 %0, i32 %1", "i32", "  %3 = add nsw i32 %0, %1\n  ret i32 %3"),
        "  %3 = add i32 %0, %1\n  ret i32 %3",
    ),
    (
        "masking-a-poison-shift",
        fn("i32 %0, i32 %1", "i32", "  %3 = shl i32 %0, %1\n  ret i32 %3"),
        "  %3 = and i32 %1, 31\n  %4 = shl i32 %0, %3\n  ret i32 %4",
    ),
    (
        "pow2-to-ctpop",
        fn(
            "i32 %0",
            "i1",
            "  %2 = add i32 %0, -1\n  %3 = and i32 %0, %2\n  %4 = icmp eq i32 %3, 0\n"
            "  %5 = icmp ne i32 %0, 0\n  %6 = and i1 %4, %5\n  ret i1 %6",
        ),
        "  %2 = call i32 @llvm.ctpop.i32(i32 %0)\n  %3 = icmp eq i32 %2, 1\n  ret i1 %3",
    ),
]


# Real alive-tv output for sdiv-by-two in i32 (Z3 times out on 32-bit division).
TIMEOUT_OUTPUT = """
define i32 @f(i32 %#0) {
#1:
  %#2 = lshr i32 %#0, 31
  %#3 = add i32 %#0, %#2
  %#4 = ashr i32 %#3, 1
  ret i32 %#4
}
ERROR: Timeout

Summary:
  0 correct transformations
  0 incorrect transformations
  1 failed-to-prove transformations
  0 Alive2 errors
"""


def test_timeout_is_not_proven():
    assert classify(TIMEOUT_OUTPUT) is Status.NOT_PROVEN


@pytest.mark.parametrize("name,src,body,why", WRONG, ids=[w[0] for w in WRONG])
def test_wrong_rewrite_is_rejected(name, src, body, why):
    r = verify(src, splice(src, body))
    assert r.status is Status.COUNTEREXAMPLE, f"{name} must be rejected: {why}\n{r.output}"
    assert r.proof is None
    assert r.counterexample


@pytest.mark.parametrize("name,src,body", CORRECT, ids=[c[0] for c in CORRECT])
def test_correct_rewrite_is_proven(name, src, body):
    r = verify(src, splice(src, body))
    assert r.status is Status.PROVEN, f"{name} must be proven\n{r.output}"
    assert r.proof is not None
