import urllib.request
from types import SimpleNamespace

import pytest

from qed import config, llm_compiler
from qed.llm_compiler import COUNT_PREFIX, PREAMBLE, generate, instruction_count

SRC = """define dso_local noundef i64 @f(i64 noundef %0, i64 noundef %1) local_unnamed_addr #0 {
  %3 = and i64 %1, %0
  %4 = xor i64 %3, %1
  %5 = add i64 %4, %3
  ret i64 %5
}
"""
SRC_BODY = SRC.split("\n", 1)[1].removesuffix("}\n").rstrip()
XOR = "  %3 = xor i64 %1, %0\n  ret i64 %3"


class FakeLLM:
    """Stands in for llama-server: stage 1 returns the count sentence, stage 2 a body.
    Unforced, the model estimates 2 instructions; the source has 4."""

    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.prompts = []
        self.completions = self

    def create(self, prompt, stop, **kw):
        self.prompts.append(prompt)
        if stop == ["<code>"]:
            text = " and binary sise 60 bytes:\n\n"
            if prompt.endswith("[/INST]"):
                text = "  The LLVM-IR will have instruction count 2" + text
        else:
            text = self.bodies.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(text=text)], usage=SimpleNamespace(completion_tokens=5)
        )


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_compiler, "_cache", {})
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(llm_compiler, "server", lambda: {"llama_cpp": "test"})

    def install(*bodies):
        llm = FakeLLM(bodies)
        monkeypatch.setattr(llm_compiler, "client", lambda: llm)
        return llm

    return install


def test_instruction_count_skips_labels_and_comments():
    fn = "define i32 @f(i1 %0) {\n1:\n  br label %2\n\n2:   ; preds = %1\n  ret i32 0\n}\n"
    assert instruction_count(fn) == 2
    assert instruction_count(SRC) == 4


def test_first_attempt_uses_training_prompt_and_prefill(fake):
    llm = fake(XOR)
    assert generate(SRC, []) == XOR
    stage1, stage2 = llm.prompts
    assert "opt -p 'module(default<O3>)'" in stage1
    assert stage1.endswith("The input code has instruction count 4. [/INST]")
    header = SRC.split("\n", 1)[0]
    assert stage2.endswith(PREAMBLE + header + "\n")
    assert llm_compiler.last_call["completion_tokens"] == 10


def test_later_attempt_forces_a_count_above_the_estimate(fake):
    llm = fake(XOR, "  ret i64 %1")
    assert generate(SRC, [{"body": XOR}]) == "  ret i64 %1"
    assert llm.prompts[2].endswith(COUNT_PREFIX.format(3))


def test_source_copy_is_never_returned(fake):
    fake(SRC_BODY, "  ret i64 %1")
    assert generate(SRC, []) == "  ret i64 %1"


def test_identical_requests_are_not_sent_twice(fake):
    llm = fake(XOR, "  ret i64 %1")
    generate(SRC, [])
    generate(SRC, [XOR])
    assert len(llm.prompts) == 4


def test_answers_are_cached_on_disk_per_server(fake, monkeypatch):
    llm = fake(XOR)
    generate(SRC, [])
    monkeypatch.setattr(llm_compiler, "_cache", {})
    assert generate(SRC, []) == XOR
    assert len(llm.prompts) == 2
    monkeypatch.setattr(llm_compiler, "_cache", {})
    monkeypatch.setattr(llm_compiler, "server", lambda: {"llama_cpp": "other"})
    llm = fake(XOR)
    generate(SRC, [])
    assert len(llm.prompts) == 2


def test_metadata_attachments_are_dropped(fake):
    fake("  %3 = tail call i64 @llvm.ctpop.i64(i64 %0), !tbaa !4, !range !5\n  ret i64 %3")
    assert generate(SRC, []) == "  %3 = tail call i64 @llvm.ctpop.i64(i64 %0)\n  ret i64 %3"


def _server_up() -> bool:
    try:
        return urllib.request.urlopen(f"{config.LLMC_URL}/health", timeout=2).status == 200
    except OSError:
        return False


@pytest.mark.skipif(not _server_up(), reason="llama-server with LLM Compiler is not running")
def test_live_server_returns_a_body():
    out = generate(SRC, [])
    assert "ret i64" in out
    assert "define" not in out and "}" not in out
