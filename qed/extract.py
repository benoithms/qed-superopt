"""C source -> reference IR (clang -O3, Skylake), and splicing a body under the source header."""

from pathlib import Path


def extract(c_path: Path) -> str:
    """Compile `c_path` with the reference clang and return the IR of its single function,
    exactly as produced by -O3, minus debug metadata."""
    raise NotImplementedError


def splice(src_ir: str, body: str) -> str:
    """Place a candidate function body under the exact header of `src_ir`
    (`define` line, parameter and return attributes, attribute groups).
    The model never writes the header: the signature is identical by construction."""
    raise NotImplementedError
