"""Cost of an IR function on the target: llc -> assembly -> llvm-mca."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Cost:
    ir_insts: int
    asm_insts: int
    mca_cycles: float


def cost(ll: str) -> Cost:
    """Lower `ll` with the reference llc for Skylake and score it with llvm-mca."""
    raise NotImplementedError
