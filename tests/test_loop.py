import json

import pytest

from qed import llm, loop
from qed.llm import NO_IMPROVEMENT, Settings, messages

SRC_C = "#include <stdbool.h>\n#include <stdint.h>\nbool f(int64_t x) { return x % 250 != x; }\n"
WRONG = "```llvm\n  ret i1 true\n```"
RETRY = Settings(stop_on_truncation=False)  # the behavior of runs before results/highcap-cascade
RIGHT = "```llvm\n  %t1 = add i64 %0, -250\n  %t2 = icmp ult i64 %t1, -499\n  ret i1 %t2\n```"


@pytest.fixture(autouse=True)
def no_wallet(monkeypatch):
    monkeypatch.setattr(loop, "WALLET", None)  # main() sets it: never leak it between tests


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
    res = loop.run_function(entry, settings=RETRY, attempts=2)
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
    res = loop.run_function(entry, settings=RETRY, attempts=3)
    assert [a["check"] for a in res["attempts"]] == ["proven", "truncated"]
    assert res["stop"] == "truncated_after_win"
    assert res["best"]["n"] == 1


def test_truncation_before_a_win_keeps_searching(entry, fake_muse):
    fake_muse(None, RIGHT)
    res = loop.run_function(entry, settings=RETRY, attempts=2)
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
    assert res["budget_usd"] == pytest.approx(1.50 * 20.00 / 4.25)


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


def test_max_total_refuses_a_call_whose_worst_case_does_not_fit(run_env, monkeypatch):
    tmp, entries = run_env
    calls = []
    monkeypatch.setattr(llm, "generate", lambda *a, **kw: calls.append(1))
    # worst case of one 16k-token muse-spark call: ~$0.07 > $0.03
    loop.main([*map(str, entries), "--run-id", "r", "--max-total", "0.03"])
    run = json.loads((tmp / "results" / "r" / "run.json").read_text())
    assert calls == [] and run["paid_usd"] == 0
    res = json.loads((tmp / "results" / "r" / "e0.json").read_text())
    assert res["stop"] == "max_total"


def test_max_total_counts_real_costs_and_not_cached_answers(run_env, monkeypatch):
    tmp, entries = run_env

    def generate(ir, history, **kw):
        llm.last_call.clear()
        llm.last_call.update(cost_usd=0.02, finish_reason="stop", cached=bool(history))
        return RIGHT if not history else f"{NO_IMPROVEMENT}: optimal."

    monkeypatch.setattr(llm, "generate", generate)
    loop.main([*map(str, entries), "--run-id", "r", "--max-total", "5"])
    run = json.loads((tmp / "results" / "r" / "run.json").read_text())
    assert run["paid_usd"] == pytest.approx(3 * 0.02)  # the cached second answers are free


def test_wallet_reservations_never_exceed_the_cap():
    w = loop.Wallet(1.0)
    assert w.reserve(0.6) and not w.reserve(0.5)  # 0.6 in flight + 0.5 > 1.0
    w.settle(0.6, 0.1)
    assert w.reserve(0.5) and w.paid == pytest.approx(0.1)


def test_fallback_policies_use_only_the_primary_result():
    won = {"stop": "no_improvement", "best": {"n": 1}, "baseline": {"ir_insts": 3}}
    lost = {"stop": "attempts", "best": None, "baseline": {"ir_insts": 3}}
    big = {"stop": "truncated_after_win", "best": {"n": 1}, "baseline": {"ir_insts": 12}}
    assert [loop.wants_fallback(r, "not_no_improvement") for r in (won, lost, big)] == [
        False,
        True,
        True,
    ]
    assert [loop.wants_fallback(r, "no_win") for r in (won, lost, big)] == [False, True, False]
    assert [loop.wants_fallback(r, "large_or_no_win") for r in (won, lost, big)] == [
        False,
        True,
        True,
    ]


def test_cascade_skips_the_fallback_when_the_policy_says_so(entry, fake_muse):
    seen = fake_muse(RIGHT, f"{NO_IMPROVEMENT}: single range check.")
    wonder = Settings(model="muse-wonder-1.0")
    res = loop.run_cascade(entry, Settings(), 5, None, wonder, 3, "not_no_improvement")
    assert len(seen) == 2  # no fallback call
    assert res["fallback"] is None
    assert res["best"]["model"] == "muse-spark-1.3"


def test_cascade_keeps_the_fallback_win_and_adds_its_cost(entry, fake_muse):
    seen = fake_muse(WRONG, RIGHT, f"{NO_IMPROVEMENT}: single range check.")
    wonder = Settings(model="muse-wonder-1.0")
    res = loop.run_cascade(entry, Settings(), 1, None, wonder, 3, "no_win")
    assert len(seen) == 3
    assert res["primary_best"] is None
    assert res["best"]["model"] == "muse-wonder-1.0"
    assert res["fallback"]["model"] == "muse-wonder-1.0"
    assert res["cost_usd"] == pytest.approx(0.03)


def test_stop_on_truncation_does_not_retry(entry, fake_muse):
    seen = fake_muse(None, RIGHT)
    res = loop.run_function(entry, settings=Settings(stop_on_truncation=True), attempts=5)
    assert len(seen) == 1
    assert [a["check"] for a in res["attempts"]] == ["truncated"]
    assert res["stop"] == "truncated"


def test_max_tokens_option_sets_every_cap(entry, fake_muse, monkeypatch, tmp_path):
    fake_muse(RIGHT, f"{NO_IMPROVEMENT}: single range check.")
    monkeypatch.setattr(loop.config, "RESULTS_DIR", tmp_path)
    loop.main([str(entry), "--run-id", "t", "--max-tokens", "64000", "--stop-on-truncation"])
    assert fake_muse.max_tokens == [64000, 64000]
    run = json.loads((tmp_path / "t" / "run.json").read_text())
    assert run["settings"]["stop_on_truncation"] is True


def test_fallback_budget_scales_with_the_output_price(entry, fake_muse, monkeypatch, tmp_path):
    fake_muse(RIGHT, f"{NO_IMPROVEMENT}: a.", RIGHT, f"{NO_IMPROVEMENT}: b.")
    monkeypatch.setattr(loop.config, "RESULTS_DIR", tmp_path)
    loop.main(
        [str(entry), "--run-id", "t", "--budget", "1.5", "--fallback-model", "muse-wonder-1.0"]
    )
    res = json.loads((tmp_path / "t" / "srem-range.json").read_text())
    assert res["budget_usd"] == pytest.approx(1.5)
    assert res["fallback"]["budget_usd"] == pytest.approx(1.5 * 20.00 / 4.25)


def test_missing_entry_is_refused_before_any_call(entry, fake_muse, tmp_path):
    seen = fake_muse()
    with pytest.raises(SystemExit):
        loop.main([str(entry), str(tmp_path / "B" / "moved"), "--run-id", "t"])
    assert seen == []


def test_an_error_on_one_entry_does_not_stop_the_run(entry, fake_muse, monkeypatch, tmp_path):
    fake_muse(RIGHT, f"{NO_IMPROVEMENT}: single range check.")
    broken = tmp_path / "B" / "broken"
    broken.mkdir()
    (broken / "src.c").write_text("int f(int x) { return x; } int g(int x) { return x; }\n")
    monkeypatch.setattr(loop.config, "RESULTS_DIR", tmp_path / "results")
    loop.main([str(broken), str(entry), "--run-id", "t"])
    run = json.loads((tmp_path / "results" / "t" / "run.json").read_text())
    assert list(run["errors"]) == [str(broken)]
    assert (tmp_path / "results" / "t" / "srem-range.json").exists()
