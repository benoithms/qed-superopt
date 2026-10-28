import json

import pytest

from qed import llm, loop
from qed.llm import NO_IMPROVEMENT, Settings, messages

SRC_C = "#include <stdbool.h>\n#include <stdint.h>\nbool f(int64_t x) { return x % 250 != x; }\n"
WRONG = "```llvm\n  ret i1 true\n```"
RIGHT = "```llvm\n  %t1 = add i64 %0, -250\n  %t2 = icmp ult i64 %t1, -499\n  ret i1 %t2\n```"


@pytest.fixture
def entry(tmp_path):
    e = tmp_path / "B" / "srem-range"
    e.mkdir(parents=True)
    (e / "src.c").write_text(SRC_C)
    (e / "expected.ll").write_text("this must never be read")
    return e


@pytest.fixture
def fake_muse(monkeypatch):
    def install(*responses):
        queue, seen, max_tokens = list(responses), [], []

        def generate(ir, history, **kw):
            seen.append([dict(h) for h in history])
            max_tokens.append(kw["settings"].max_tokens)
            response = queue.pop(0)
            llm.last_call.clear()
            llm.last_call.update(cost_usd=0.01, tokens_in=100, tokens_out=50, finish_reason="stop")
            if response is None:  # the model hit the token limit
                llm.last_call["finish_reason"] = "length"
                response = ""
            return response

        monkeypatch.setattr(llm, "generate", generate)
        install.max_tokens = max_tokens
        return seen

    return install


def test_loop_repairs_from_counterexample_and_keeps_best(entry, fake_muse):
    seen = fake_muse(WRONG, RIGHT, f"{NO_IMPROVEMENT}: already a single range check.")
    res = loop.run_function(entry, attempts=5)

    checks = [a["check"] for a in res["attempts"]]
    assert checks == ["counterexample", "proven", "no_improvement"]
    assert "Counterexample" in seen[1][0]["feedback"]  # the model saw the counterexample
    assert res["best"]["n"] == 2
    assert res["best"]["mca_cycles"] < res["baseline"]["mca_cycles"]
    assert res["stop"] == "no_improvement"
    assert res["cost_usd"] == pytest.approx(0.03)
    assert all("this must never be read" not in str(a) for a in res["attempts"])


def test_no_improvement_on_first_attempt_is_refused(entry, fake_muse):
    fake_muse(f"{NO_IMPROVEMENT}: optimal.", RIGHT)
    res = loop.run_function(entry, attempts=2)
    assert [a["check"] for a in res["attempts"]] == ["no_improvement_refused", "proven"]


def test_budget_counts_the_worst_case_of_the_next_call(entry, fake_muse):
    fake_muse(WRONG, WRONG, WRONG)
    # Worst case of a call at max_tokens=1000: ~$0.004 output + ~$0.001 input. Each fake call
    # costs $0.01, so a second call (0.01 + ~0.005) would exceed the $0.012 budget.
    res = loop.run_function(entry, settings=Settings(max_tokens=1000), attempts=3, budget_usd=0.012)
    assert len(res["attempts"]) == 1
    assert res["stop"] == "budget"


def test_truncated_answer_is_recorded_and_the_model_is_told(entry, fake_muse):
    seen = fake_muse(None, RIGHT)
    res = loop.run_function(entry, attempts=2)
    assert [a["check"] for a in res["attempts"]] == ["truncated", "proven"]
    assert "ran out of tokens" in seen[1][0]["feedback"]


def test_a_win_offers_an_exit(entry, fake_muse):
    seen = fake_muse(RIGHT, f"{NO_IMPROVEMENT}: optimal.")
    loop.run_function(entry, attempts=2)
    assert NO_IMPROVEMENT in seen[1][0]["feedback"]


def test_verdict_feedback_hides_the_counterexample(entry, fake_muse):
    seen = fake_muse(WRONG, RIGHT)
    loop.run_function(entry, settings=Settings(feedback="verdict"), attempts=2)
    assert "Counterexample" not in seen[1][0]["feedback"]


def test_message_modes():
    ir = "define i1 @f(i64 %0) {\n  ret i1 false\n}\n"
    history = [{"response": "r1", "body": "b1", "feedback": "f1"}]
    full = messages(ir, history, settings=Settings(show_asm="never"))
    assert [m["role"] for m in full] == ["system", "user", "assistant", "user"]
    indep = messages(ir, history, settings=Settings(feedback="independent"))
    assert [m["role"] for m in indep] == ["system", "user"]


def test_lower_token_cap_after_a_win(entry, fake_muse):
    fake_muse(WRONG, RIGHT, f"{NO_IMPROVEMENT}: optimal.")
    loop.run_function(entry, attempts=3)
    s = Settings()
    assert fake_muse.max_tokens == [s.max_tokens, s.max_tokens, s.max_tokens_after_win]


def test_truncation_after_a_win_ends_the_search(entry, fake_muse):
    fake_muse(RIGHT, None, RIGHT)
    res = loop.run_function(entry, attempts=3)
    assert [a["check"] for a in res["attempts"]] == ["proven", "truncated"]
    assert res["stop"] == "truncated_after_win"
    assert res["best"]["n"] == 1


def test_truncation_before_a_win_keeps_searching(entry, fake_muse):
    fake_muse(None, RIGHT)
    res = loop.run_function(entry, attempts=2)
    assert [a["check"] for a in res["attempts"]] == ["truncated", "proven"]


def test_large_functions_get_twice_the_tokens_and_budget(entry, fake_muse):
    fake_muse(WRONG, RIGHT, f"{NO_IMPROVEMENT}: optimal.")
    s = Settings(large_insts=1)  # every function counts as large
    res = loop.run_function(entry, settings=s, attempts=3, budget_usd=0.35)
    assert fake_muse.max_tokens == [
        s.max_tokens_large,
        s.max_tokens_large,
        s.max_tokens_after_win_large,
    ]
    assert res["large"] and res["budget_usd"] == 0.70


def test_default_budget_gives_every_model_the_same_tokens(entry, fake_muse):
    fake_muse(RIGHT, f"{NO_IMPROVEMENT}: optimal.")
    res = loop.run_function(entry, settings=Settings(model="muse-wonder-1.0"), attempts=2)
    assert res["model"] == "muse-wonder-1.0"
    assert res["budget_usd"] == pytest.approx(0.35 * 20.00 / 4.25)


def test_last_call_is_per_thread():
    import threading

    seen = {}

    def worker(name):
        llm.last_call.clear()
        llm.last_call.update(cost_usd=name)
        threading.Event().wait(0.05)  # let the other thread write meanwhile
        seen[name] = llm.last_call.get("cost_usd")

    threads = [threading.Thread(target=worker, args=(n,)) for n in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert seen == {1: 1, 2: 2}


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    """Three corpus entries, results in tmp_path, and a thread-safe fake model that wins
    on the first attempt (each call costs $0.02) then answers NO_IMPROVEMENT."""
    entries = []
    for i in range(3):
        e = tmp_path / "B" / f"e{i}"
        e.mkdir(parents=True)
        (e / "src.c").write_text(SRC_C)
        entries.append(e)
    monkeypatch.setattr(loop.config, "RESULTS_DIR", tmp_path / "results")

    def generate(ir, history, **kw):
        llm.last_call.clear()
        llm.last_call.update(cost_usd=0.02, finish_reason="stop")
        return RIGHT if not history else f"{NO_IMPROVEMENT}: optimal."

    monkeypatch.setattr(llm, "generate", generate)
    return tmp_path, entries


def test_jobs_run_every_function(run_env):
    tmp, entries = run_env
    loop.main([*map(str, entries), "--run-id", "r", "--jobs", "2"])
    out = tmp / "results" / "r"
    assert sorted(p.name for p in out.glob("e*.json")) == ["e0.json", "e1.json", "e2.json"]
    run = json.loads((out / "run.json").read_text())
    assert run["cost_usd"] == pytest.approx(3 * 0.04) and run["jobs"] == 2


def test_max_total_stops_new_functions(run_env):
    tmp, entries = run_env
    loop.main([*map(str, entries), "--run-id", "r", "--max-total", "0.03"])
    run = json.loads((tmp / "results" / "r" / "run.json").read_text())
    assert len(run["skipped_by_max_total"]) == 2  # the first function spent $0.04
