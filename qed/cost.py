"""Cost of an IR function on the target: llc -> assembly -> llvm-mca."""

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from qed import config
from qed.extract import body, function

_NAME = re.compile(r"@([-\w.$]+)\(")
_TOTAL = re.compile(r"^Total Cycles:\s+(\d+)", re.M)
_ITERS = re.compile(r"^Iterations:\s+(\d+)", re.M)


class CostError(Exception):
    pass


@dataclass(frozen=True)
class Cost:
    ir_insts: int
    asm_insts: int
    mca_cycles: float  # llvm-mca steady-state cycles per call (Total Cycles / Iterations)
    asm: str  # the function's assembly, kept for the record
    mca_output: str  # raw llvm-mca report, kept for the record


def cost(ll: str) -> Cost:
    """Lower `ll` with the reference llc for Skylake and score it with llvm-mca."""
    fn = function(ll)
    name = _NAME.search(fn.split("\n", 1)[0]).group(1)
    with tempfile.TemporaryDirectory() as d:
        src, asm_path = Path(d) / "f.ll", Path(d) / "f.s"
        src.write_text(ll)
        _run([config.LLC, *config.LLC_FLAGS, src, "-o", asm_path])
        asm = asm_path.read_text()
        mca = _run([config.LLVM_MCA, *config.MCA_FLAGS, asm_path])

    total, iters = _TOTAL.search(mca), _ITERS.search(mca)
    if not total or not iters:
        raise CostError("unexpected llvm-mca output")
    fn_asm = _function_asm(asm, name)
    return Cost(
        ir_insts=ir_instructions(fn),
        asm_insts=len(asm_instructions(fn_asm)),
        mca_cycles=int(total.group(1)) / int(iters.group(1)),
        asm=fn_asm,
        mca_output=mca,
    )


def ir_instructions(fn: str) -> int:
    """Instructions in an IR function body (labels and comments excluded)."""
    n = 0
    for line in body(fn).split("\n"):
        s = line.split(";", 1)[0].strip()
        if s and not s.endswith(":"):
            n += 1
    return n


def asm_instructions(fn_asm: str) -> list[str]:
    """Instruction lines of a function's assembly (directives, labels, comments excluded)."""
    out = []
    for line in fn_asm.split("\n"):
        s = line.split("#", 1)[0].strip()
        if s and not s.startswith(".") and not s.endswith(":"):
            out.append(s)
    return out


def _function_asm(asm: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}:.*?^\.Lfunc_end\d+:", asm, re.M | re.S)
    if not m:
        raise CostError(f"function {name} not found in llc output")
    return m.group(0)


def _run(cmd: list) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise CostError(f"{Path(cmd[0]).name}: {p.stderr.strip()}")
    return p.stdout
