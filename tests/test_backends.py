"""Tests for the Claude/Gemini chat backends with stand-in clients (no keys, no network).

Run with:  python -m pytest tests/test_backends.py -v
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from pitchiq import backends
from pitchiq.backends import AnthropicChat, GeminiChat, available_backend, error_message
from pitchiq.config import GEMINI_MODEL


# --- Gemini --------------------------------------------------------------------------------

def _gemini_events(interaction_id, texts, status="completed", total_tokens=1234):
    yield NS(event_type="interaction.created", interaction=NS(id=interaction_id))
    yield NS(event_type="step.delta", delta=NS(type="thought_summary", text="(thinking)"))  # not shown
    for t in texts:
        yield NS(event_type="step.delta", delta=NS(type="text", text=t))
    yield NS(event_type="interaction.completed",
             interaction=NS(id=interaction_id, status=status, usage=NS(total_tokens=total_tokens)))


class FakeGemini:
    def __init__(self, scripted):
        self.calls, self.scripted = [], list(scripted)
        self.interactions = NS(create=self.create)

    def create(self, **params):
        self.calls.append(params)
        return self.scripted.pop(0)


def _gemini(scripted) -> GeminiChat:
    chat = GeminiChat(api_key="test-not-real")
    chat.client = FakeGemini(scripted)
    return chat


def test_gemini_streams_text_and_continues_the_conversation():
    chat = _gemini([_gemini_events("int-1", ["Start ", "him away."]),
                    _gemini_events("int-2", ["Same plan."])])
    assert "".join(chat.stream("SYSTEM", "Dodgers?")) == "Start him away."
    first = chat.client.calls[0]
    assert first["model"] == GEMINI_MODEL and first["stream"] is True
    assert first["system_instruction"] == "SYSTEM" and first["input"] == "Dodgers?"
    assert "previous_interaction_id" not in first
    assert chat.result.status == "ok" and chat.result.tokens == 1234 and chat.result.cost == 0.0

    assert "".join(chat.stream("SYSTEM", "And Freeman?")) == "Same plan."
    assert chat.client.calls[1]["previous_interaction_id"] == "int-1"
    assert chat.previous_id == "int-2"


def test_gemini_failed_turn_does_not_advance_the_conversation():
    chat = _gemini([_gemini_events("int-1", ["ok"]), _gemini_events("int-2", [], status="failed")])
    list(chat.stream("S", "q1"))
    list(chat.stream("S", "q2"))
    assert chat.result.status == "refused"
    assert chat.previous_id == "int-1"


def test_gemini_error_event_raises_and_keeps_state():
    def broken():
        yield NS(event_type="interaction.created", interaction=NS(id="int-9"))
        yield NS(event_type="error", error=NS(code="RESOURCE_EXHAUSTED", message="quota"))
    chat = _gemini([broken()])
    with pytest.raises(RuntimeError, match="quota"):
        list(chat.stream("S", "q"))
    assert chat.previous_id is None


def test_gemini_incomplete_is_truncated():
    chat = _gemini([_gemini_events("int-1", ["partial"], status="incomplete")])
    list(chat.stream("S", "q"))
    assert chat.result.status == "truncated" and chat.previous_id == "int-1"


# --- Claude ---------------------------------------------------------------------------------

class _Stream:
    def __init__(self, texts, final, fail=False):
        self.texts, self.final, self.fail = texts, final, fail

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        yield from self.texts
        if self.fail:
            raise ConnectionError("dropped")

    def get_final_message(self):
        return self.final


def _claude(streams) -> AnthropicChat:
    chat = AnthropicChat(api_key="sk-ant-test-not-real")
    queue = list(streams)
    chat.client = NS(beta=NS(messages=NS(stream=lambda **kw: queue.pop(0))))
    return chat


def _final(stop="end_turn"):
    return NS(stop_reason=stop, content=["assistant blocks"],
              usage=NS(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=0,
                       cache_read_input_tokens=0))


def test_claude_keeps_alternating_history():
    chat = _claude([_Stream(["A"], _final()), _Stream(["B"], _final())])
    assert "".join(chat.stream("S", "q1")) == "A"
    assert "".join(chat.stream("S", "q2")) == "B"
    assert [m["role"] for m in chat.messages] == ["user", "assistant", "user", "assistant"]
    assert chat.result.cost == pytest.approx((1000 * 4 + 500 * 20) / 1e6)


def test_claude_error_or_refusal_leaves_history_valid():
    chat = _claude([_Stream(["A"], _final()), _Stream(["par"], None, fail=True), _Stream([], _final("refusal"))])
    list(chat.stream("S", "q1"))
    with pytest.raises(ConnectionError):
        list(chat.stream("S", "q2"))
    list(chat.stream("S", "q3"))
    assert chat.result.status == "refused"
    assert [m["role"] for m in chat.messages] == ["user", "assistant"]


# --- choosing a backend, errors -----------------------------------------------------------------

def test_auto_prefers_claude_then_gemini(monkeypatch):
    monkeypatch.setattr(backends, "CHAT_PROVIDER", "auto")
    assert available_backend(None, None) is None
    assert available_backend(None, "g-key").provider == "gemini"
    assert available_backend("sk-ant-x", "g-key").provider == "anthropic"
    monkeypatch.setattr(backends, "CHAT_PROVIDER", "gemini")
    assert available_backend("sk-ant-x", "g-key").provider == "gemini"
    assert available_backend("sk-ant-x", None) is None


@pytest.mark.parametrize("exc,expected", [
    (NS(status_code=429), "Rate limit"),
    (NS(status_code=403), "rejected"),
    (NS(status_code=503), "server error"),
])
def test_error_messages(exc, expected):
    class Err(Exception):
        pass
    e = Err("boom")
    e.status_code = exc.status_code
    assert expected in error_message(e)


# --- Gemini model fallback ----------------------------------------------------------------------

class _Overloaded(Exception):
    def __init__(self, status=503):
        super().__init__("high demand")
        self.status_code = status


def _by_model(behaviour):
    """create(**params) that fails or streams depending on the requested model."""
    calls = []

    def create(**params):
        calls.append(params["model"])
        outcome = behaviour[params["model"]]
        if isinstance(outcome, Exception):
            raise outcome
        return _gemini_events(f"int-{params['model']}", outcome)
    return create, calls


def test_overloaded_model_falls_back_and_conversation_stays_there():
    from pitchiq.config import GEMINI_MODELS
    first, second = GEMINI_MODELS[0], GEMINI_MODELS[1]
    chat = GeminiChat(api_key="test-not-real")
    create, calls = _by_model({first: _Overloaded(503), second: ["from fallback"]})
    chat.client = NS(interactions=NS(create=create))
    assert "".join(chat.stream("S", "q1")) == "from fallback"
    assert calls == [first, second]
    assert chat.model == second and second in chat.label
    list(chat.stream("S", "q2"))
    assert calls[-1] == second  # next turn starts on the model that answered


def test_quota_exhausted_also_falls_back():
    from pitchiq.config import GEMINI_MODELS
    chat = GeminiChat(api_key="test-not-real")
    create, calls = _by_model({GEMINI_MODELS[0]: _Overloaded(429), GEMINI_MODELS[1]: ["ok"]})
    chat.client = NS(interactions=NS(create=create))
    assert "".join(chat.stream("S", "q")) == "ok"


def test_other_errors_do_not_fall_back():
    from pitchiq.config import GEMINI_MODELS
    chat = GeminiChat(api_key="test-not-real")
    create, calls = _by_model({GEMINI_MODELS[0]: _Overloaded(403), GEMINI_MODELS[1]: ["ok"]})
    chat.client = NS(interactions=NS(create=create))
    with pytest.raises(_Overloaded):
        list(chat.stream("S", "q"))
    assert calls == [GEMINI_MODELS[0]]


def test_all_models_overloaded_reports_the_error():
    from pitchiq.config import GEMINI_MODELS
    chat = GeminiChat(api_key="test-not-real")
    create, calls = _by_model({m: _Overloaded(503) for m in GEMINI_MODELS})
    chat.client = NS(interactions=NS(create=create))
    with pytest.raises(_Overloaded):
        list(chat.stream("S", "q"))
    assert calls == list(GEMINI_MODELS)
    assert "server error" in error_message(_Overloaded(503))


# --- empty answers ----------------------------------------------------------------------------

def test_empty_answer_is_retried_and_not_kept_in_the_conversation():
    from pitchiq.config import GEMINI_MODELS
    first = GEMINI_MODELS[0]
    chat = GeminiChat(api_key="test-not-real")
    scripted = [_gemini_events("int-empty", []), _gemini_events("int-ok", ["Plan."])]
    calls = []

    def create(**params):
        calls.append((params["model"], params.get("previous_interaction_id")))
        return scripted.pop(0)
    chat.client = NS(interactions=NS(create=create))
    assert "".join(chat.stream("S", "Dodgers?")) == "Plan."
    assert calls == [(first, None), (first, None)]   # retried on the same model, fresh
    assert chat.previous_id == "int-ok" and chat.result.status == "ok"


def test_all_attempts_empty_reports_empty():
    from pitchiq.config import GEMINI_MODELS
    chat = GeminiChat(api_key="test-not-real")
    n = 1 + len(GEMINI_MODELS)  # current model twice, then each other model once
    scripted = [_gemini_events(f"int-{i}", []) for i in range(n)]
    chat.client = NS(interactions=NS(create=lambda **p: scripted.pop(0)))
    assert "".join(chat.stream("S", "q")) == ""
    assert chat.result.status == "empty" and chat.previous_id is None and scripted == []


# --- stream closed early -------------------------------------------------------------------------

def test_stream_closed_early_is_completed_from_the_finished_interaction(monkeypatch):
    monkeypatch.setattr(backends, "RECOVER_POLL_S", 0)
    chat = GeminiChat(api_key="test-not-real")
    cut = [NS(event_type="interaction.created", interaction=NS(id="int-1")),
           NS(event_type="step.delta", delta=NS(type="text", text="Start him "))]   # no "completed"
    polls = iter([NS(status="in_progress"),
                  NS(status="completed", output_text="Start him with the changeup.", usage=NS(total_tokens=900))])
    gets = []

    def get(interaction_id):
        gets.append(interaction_id)
        return next(polls)
    chat.client = NS(interactions=NS(create=lambda **p: iter(cut), get=get))
    assert "".join(chat.stream("S", "q")) == "Start him with the changeup."
    assert gets == ["int-1", "int-1"]                      # polled until it finished
    assert chat.result.status == "ok" and chat.result.tokens == 900 and chat.previous_id == "int-1"


def test_stream_that_never_finishes_is_marked_cut_off(monkeypatch):
    monkeypatch.setattr(backends, "RECOVER_POLL_S", 0)
    monkeypatch.setattr(backends, "RECOVER_WAIT_S", 0)
    chat = GeminiChat(api_key="test-not-real")
    cut = [NS(event_type="interaction.created", interaction=NS(id="int-1")),
           NS(event_type="step.delta", delta=NS(type="text", text="Start him"))]
    chat.client = NS(interactions=NS(create=lambda **p: iter(cut), get=lambda i: NS(status="in_progress")))
    assert "".join(chat.stream("S", "q")) == "Start him"
    assert chat.result.status == "truncated"


# --- our own deadlines ---------------------------------------------------------------------------

def test_iterate_with_deadline_passes_items_and_errors_through():
    from pitchiq.backends import iterate_with_deadline
    assert list(iterate_with_deadline(lambda: iter([1, 2, 3]), 1, 1)) == [1, 2, 3]

    def broken():
        yield 1
        raise ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        list(iterate_with_deadline(broken, 1, 1))


def test_iterate_with_deadline_gives_up_on_a_stalled_request():
    import threading as th
    from pitchiq.backends import ModelTimeout, iterate_with_deadline
    release = th.Event()

    def stalled():
        release.wait(5)  # like a request Google never answers
        yield "too late"
    with pytest.raises(ModelTimeout):
        list(iterate_with_deadline(stalled, 0.2, 0.2))
    release.set()


def test_stalled_model_falls_back_to_the_next(monkeypatch):
    import threading as th
    from pitchiq.config import GEMINI_MODELS
    monkeypatch.setattr(backends, "FIRST_EVENT_S", 0.2)
    release = th.Event()

    def create(**params):
        if params["model"] == GEMINI_MODELS[0]:
            release.wait(5)          # first model never responds
        return _gemini_events("int-2", ["from backup"])
    chat = GeminiChat(api_key="test-not-real")
    chat.client = NS(interactions=NS(create=create))
    assert "".join(chat.stream("S", "q")) == "from backup"
    assert chat.model == GEMINI_MODELS[1]
    release.set()
