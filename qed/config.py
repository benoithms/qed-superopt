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
# -fdiscard-value-names: our clang is an assertions build and would otherwise keep
# source names (%x, %entry); numbered values match what the models produce.
CLANG_FLAGS = [
    "-O3",
    f"--target={TRIPLE}",
    f"-march={CPU}",
    "-S",
    "-emit-llvm",
    "-g0",
    "-fdiscard-value-names",
]
LLC_FLAGS = ["-O3", f"-mtriple={TRIPLE}", f"-mcpu={CPU}"]
MCA_FLAGS = [f"-mtriple={TRIPLE}", f"-mcpu={CPU}"]

ALIVE_TIMEOUT_MS = 60_000  # per SMT query
ALIVE_WALL_TIMEOUT_S = 300  # whole alive-tv run

META_API_KEY = os.environ.get("META_API_KEY", "")
META_API_BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")
META_MODEL = os.environ.get("META_MODEL", "muse-spark-1.3")
# USD per million tokens (input, output), from the Models page of the Meta Model API
# dashboard (Oct 28, 2026). Cached input is cheaper; ignoring it slightly overestimates costs.
PRICES = {
    "muse-spark-1.3": (1.25, 4.25),
    "muse-wonder-1.0": (4.00, 20.00),
}


def price(model: str) -> tuple[float, float]:
    if model not in PRICES:
        raise KeyError(f"no price for {model}: add it to config.PRICES")
    return PRICES[model]


# Model answers are cached on disk: the same request is never paid twice.
CACHE_DIR = REPO / ".cache" / "llm"
RESULTS_DIR = REPO / "results"

# LLM Compiler, served locally by llama.cpp (llama-server -m llm-compiler-7b.Q8_0.gguf).
LLMC_URL = os.environ.get("LLMC_URL", "http://127.0.0.1:8089")
# What the server cannot report about itself, recorded in run.json: the GGUF's sha256 and the
# machine (GPU, driver, backend), e.g. "az4, RTX 4070 Ti, driver 616.92, CUDA 13.4".
LLMC_MODEL_SHA256 = os.environ.get("LLMC_MODEL_SHA256")
LLMC_MACHINE = os.environ.get("LLMC_MACHINE")


def check_toolchain() -> list[str]:
    """Return the missing tools; an empty list means the chain is ready."""
    return [str(p) for p in (CLANG, OPT, LLC, LLVM_MCA, ALIVE_TV) if not p.exists()]
