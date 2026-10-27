"""Reference toolchain and target. One LLVM build, one target, for the whole chain."""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

TOOLCHAIN = Path(os.environ.get("QED_TOOLCHAIN") or REPO.parent / "qed-toolchain").expanduser()
LLVM_BIN = TOOLCHAIN / "llvm-build" / "bin"

CLANG = LLVM_BIN / "clang"
OPT = LLVM_BIN / "opt"
LLC = LLVM_BIN / "llc"
LLVM_MCA = LLVM_BIN / "llvm-mca"
ALIVE_TV = TOOLCHAIN / "alive2" / "build" / "alive-tv"

TRIPLE = "x86_64-unknown-linux-gnu"
CPU = "skylake"
CLANG_FLAGS = ["-O3", f"--target={TRIPLE}", f"-march={CPU}", "-S", "-emit-llvm", "-g0"]
LLC_FLAGS = ["-O3", f"-mtriple={TRIPLE}", f"-mcpu={CPU}"]
MCA_FLAGS = [f"-mtriple={TRIPLE}", f"-mcpu={CPU}"]

ALIVE_TIMEOUT_MS = 60_000

META_API_KEY = os.environ.get("META_API_KEY", "")
META_API_BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")
META_MODEL = os.environ.get("META_MODEL", "muse-spark-1.3")


def check_toolchain() -> list[str]:
    """Return the missing tools; an empty list means the chain is ready."""
    return [str(p) for p in (CLANG, OPT, LLC, LLVM_MCA, ALIVE_TV) if not p.exists()]
