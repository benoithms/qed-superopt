import pytest

from qed import config
from qed.verify import ProvenResult


def test_toolchain_is_complete():
    assert config.check_toolchain() == []


def test_proven_result_cannot_be_forged():
    with pytest.raises(TypeError):
        ProvenResult("src", "tgt", "out", "h1", "h2", object())
