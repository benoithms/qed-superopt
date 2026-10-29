"""Alive2 refinement check. The only module allowed to create a ProvenResult."""

import hashlib
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from qed import config

# Exact alive-tv verdict lines, taken from Alive2's source (llvm_util/compare.cpp).
# Its exit code is 0 whether or not the proof holds, so only the text counts.
PROOF_LINE = "Transformation seems to be correct!"
SAME_LINE = "Transformation seems to be correct! (syntactically equal)"
FAIL_LINE = "Transformation doesn't verify!"

_SUMMARY = re.compile(
    r"^Summary:\n"
    r"\s+(\d+) correct transformations\n"
    r"\s+(\d+) incorrect transformations\n"
    r"\s+(\d+) failed-to-prove transformations\n"
    r"\s+(\d+) Alive2 errors",
    re.M,
)

_TOKEN = object()


class Status(Enum):
    PROVEN = "proven"
    COUNTEREXAMPLE = "counterexample"
    UNCHANGED = "unchanged"  # candidate identical to the source: nothing gained
    NOT_PROVEN = "not_proven"  # timeout, unsupported, approximation, error, unexpected output


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


@dataclass(frozen=True)
class VerifyResult:
    status: Status
    counterexample: str | None
    time: float
    output: str
    proof: ProvenResult | None = None


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def verify(src_ll: str, tgt_ll: str) -> VerifyResult:
    """Ask Alive2 whether `tgt_ll` refines `src_ll` (two modules, same function name)."""
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as d:
        src, tgt = Path(d) / "src.ll", Path(d) / "tgt.ll"
        src.write_text(src_ll)
        tgt.write_text(tgt_ll)
        try:
            p = subprocess.run(
                [config.ALIVE_TV, f"--smt-to={config.ALIVE_TIMEOUT_MS}", src, tgt],
                capture_output=True,
                text=True,
                timeout=config.ALIVE_WALL_TIMEOUT_S,
            )
            output = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            output = "qed: alive-tv wall-clock timeout"
    elapsed = time.monotonic() - start

    status = classify(output)
    proof = None
    if status is Status.PROVEN:
        proof = ProvenResult(src_ll, tgt_ll, output, sha256(src_ll), sha256(tgt_ll), _TOKEN)
    cex = counterexample(output) if status is Status.COUNTEREXAMPLE else None
    return VerifyResult(status, cex, elapsed, output, proof)


def classify(output: str) -> Status:
    """Strict reading of alive-tv's output: anything unexpected is NOT_PROVEN."""
    lines = output.splitlines()
    m = _SUMMARY.search(output)
    summary = tuple(int(x) for x in m.groups()) if m else None
    # "ERROR" is case-sensitive: the summary always contains "Alive2 errors".
    clean = not (
        re.search(r"approximat", output, re.I) or "ERROR" in output or "Couldn't prove" in output
    )

    if summary == (1, 0, 0, 0) and clean and lines.count(PROOF_LINE) == 1:
        return Status.PROVEN
    if summary == (1, 0, 0, 0) and clean and lines.count(SAME_LINE) == 1:
        return Status.UNCHANGED
    if summary == (0, 1, 0, 0) and lines.count(FAIL_LINE) == 1 and "Example:" in output:
        return Status.COUNTEREXAMPLE
    return Status.NOT_PROVEN


def counterexample(output: str) -> str:
    """The part of alive-tv's report that explains the bug: error, inputs, values."""
    after = output.split(FAIL_LINE, 1)[1]
    return after.split("Summary:", 1)[0].strip()
