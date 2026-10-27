"""Candidate generators. Only Meta models: Muse Spark (API) and LLM Compiler (local)."""

from openai import OpenAI

from qed import config


def client() -> OpenAI:
    if not config.META_API_KEY:
        raise RuntimeError("META_API_KEY is missing: copy .env.example to .env and fill it in")
    return OpenAI(api_key=config.META_API_KEY, base_url=config.META_API_BASE)


def generate(ir: str, history: list) -> str:
    """Propose a faster version of the function in `ir`.

    `history` holds the previous attempts and Alive2's counterexamples.
    Returns the function BODY only: the caller splices it under the source header."""
    raise NotImplementedError
