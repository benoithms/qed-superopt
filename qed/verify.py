"""Alive2 refinement check. The only module allowed to create a ProvenResult."""

from dataclasses import dataclass
from enum import Enum

# Exact alive-tv success line. Its exit code is 0 whether or not the proof holds,
# so only the text counts, and anything else is "not proven".
PROOF_LINE = "Transformation seems to be correct!"
FAIL_LINE = "Transformation doesn't verify!"

_TOKEN = object()


class Status(Enum):
    PROVEN = "proven"
    COUNTEREXAMPLE = "counterexample"
    NOT_PROVEN = "not_proven"  # timeout, unsupported, approximation, error, unexpected output


@dataclass(frozen=True)
class VerifyResult:
    status: Status
    counterexample: str | None
    time: float
    output: str


@dataclass(frozen=True)
class ProvenResult:
    """A rewrite proven correct (refinement) by Alive2, with the exact proven files."""

    src_ll: str
    tgt_ll: str
    alive_output: str
    src_sha256: str
    tgt_sha256: str
    _token: object

    def __post_init__(self):
        if self._token is not _TOKEN:
            raise TypeError("ProvenResult can only be created by qed.verify")


def verify(src_ll: str, tgt_ll: str) -> VerifyResult:
    """Ask Alive2 whether `tgt_ll` refines `src_ll`."""
    raise NotImplementedError
