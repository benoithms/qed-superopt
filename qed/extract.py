"""C source -> reference IR (clang -O3, Skylake), and splicing a body under the source header."""

import re
import subprocess
from pathlib import Path

from qed import config

_DEFINE = re.compile(r"^define [^\n]*\{\n.*?^\}\n", re.M | re.S)
_GLOBAL_REF = re.compile(r"@([-\w.$]+)")
_FENCE = re.compile(r"```[\w-]*\n(.*?)```", re.S)


class ExtractError(Exception):
    pass


def extract(c_path: Path) -> str:
    """Compile `c_path` with the reference clang and return the module, exactly as produced
    by -O3 for the target (no debug metadata). It must contain a single function."""
    p = subprocess.run(
        [config.CLANG, *config.CLANG_FLAGS, str(c_path), "-o", "-"],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        raise ExtractError(p.stderr.strip())
    function(p.stdout)
    return p.stdout


def function(module: str) -> str:
    """The single `define ... { ... }` block of `module`."""
    defs = _DEFINE.findall(module)
    if len(defs) != 1:
        raise ExtractError(f"expected exactly one function, found {len(defs)}")
    return defs[0]


def body(fn: str) -> str:
    """The lines between a function's header and its closing brace."""
    return fn.split("\n", 1)[1].rstrip().removesuffix("}").rstrip("\n")


def splice(src_ir: str, candidate: str) -> str:
    """Place a candidate function body under the exact header of `src_ir`
    (`define` line, parameter and return attributes, attribute groups).
    The model never writes the header: the signature is identical by construction.
    If the model wrote a header anyway, it is discarded."""
    new_body = _clean(candidate)
    for ref in _GLOBAL_REF.findall(new_body):
        if not ref.startswith("llvm."):
            raise ExtractError(f"candidate references @{ref}: only LLVM intrinsics are allowed")
    fn = function(src_ir)
    header = fn.split("\n", 1)[0]
    return src_ir.replace(fn, f"{header}\n{new_body}\n}}\n", 1)


def _clean(text: str) -> str:
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    if re.search(r"^\s*define ", text, re.M):
        start = text.index("{", re.search(r"^\s*define ", text, re.M).start())
        text = text[start + 1 :]
        text = text[: text.rindex("}")] if "}" in text else text
    lines = [line.rstrip() for line in text.strip("\n").split("\n")]
    while lines and lines[-1].strip() in ("", "}"):
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        raise ExtractError("empty candidate body")
    return "\n".join(lines)
