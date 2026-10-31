import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from issue_draft import readable


def test_readable_keeps_what_the_proof_depends_on():
    fn = (
        "define dso_local range(i16 0, -257) i16 @f(i16 noundef zeroext %0) "
        "local_unnamed_addr #0 {\n  ret i16 %0\n}\n"
    )
    assert readable(fn) == (
        "define range(i16 0, -257) i16 @f(i16 noundef zeroext %0) {\n  ret i16 %0\n}\n"
    )
