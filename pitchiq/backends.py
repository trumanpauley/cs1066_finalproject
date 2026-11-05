"""Chat model providers behind one interface: Anthropic (Claude) and Google (Gemini).

Each backend keeps its own conversation state:
  - AnthropicChat holds the full message history (append-only) and resends it.
  - GeminiChat uses Gemini's server-side conversation state: each turn sends only
    the new message plus the previous interaction's id.

Usage:  for text in backend.stream(system_text, user_text): ...
        then backend.result  -> TurnResult(status, cost, tokens, label)
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from pitchiq.config import (
    CHAT_MODEL,
    CHAT_PROVIDER,
    GEMINI_FREE_TIER,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MODELS,
    GEMINI_THINKING,
    GEMINI_TIMEOUT_MS,
)

# Errors worth retrying on the next Gemini model: overloaded, or that model's free quota used up.
_RETRY_NEXT_MODEL = (429, 503)
RECOVER_WAIT_S = 60     # how long to wait for an interaction whose stream closed early
RECOVER_POLL_S = 2
FIRST_EVENT_S = 45      # give up on a request Google hasn't acknowledged in this long
EVENT_GAP_S = 60        # ...or on a stream that goes silent this long mid-answer


class ModelTimeout(TimeoutError):
    """The provider stopped responding; raised by our own clock, not the SDK's."""


def iterate_with_deadline(make_iter: Callable[[], Iterator], first_s: float, gap_s: float) -> Iterator:
    """Iterate `make_iter()` on a background thread, enforcing our own deadlines.

    The SDK's timeouts didn't reliably fire while Google held a request during
    "high demand", which froze the chat page. Here the caller never waits more
    than `first_s` for the first item or `gap_s` between items. A thread that
    is still blocked is abandoned (daemon) and dies with its connection.
    """
    items: queue.Queue = queue.Queue()

    def worker():
        try:
            for item in make_iter():
                items.put(("item", item))
            items.put(("done", None))
        except BaseException as exc:  # handed to the caller below
            items.put(("error", exc))

    threading.Thread(target=worker, daemon=True).start()
    wait = first_s
    while True:
        try:
            kind, value = items.get(timeout=wait)
        except queue.Empty:
            raise ModelTimeout(f"no response from the model for {wait:.0f} seconds") from None
        if kind == "item":
            yield value
            wait = gap_s
        elif kind == "done":
            return
        else:
            raise value


@dataclass
class TurnResult:
    status: str = "ok"           # ok | refused | truncated | empty (finished without writing)
    cost: float | None = None    # dollars; None when unknown, 0.0 on a free tier
    tokens: int | None = None


class AnthropicChat:
    provider, label = "anthropic", f"Claude · {CHAT_MODEL}"

    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.messages: list[dict] = []
        self.result = TurnResult()

    def stream(self, system_text: str, user_text: str) -> Iterator[str]:
        from pitchiq.assistant import AnswerStream, estimate_cost, system_blocks_from_text
        self.messages.append({"role": "user", "content": user_text})
        answer = AnswerStream(self.client, system_blocks_from_text(system_text), self.messages)
        try:
            yield from answer
        except BaseException:
            self.messages.pop()  # never leave an unanswered user turn in the history
            raise
        final = answer.message
        if final is None or final.stop_reason == "refusal":
            self.messages.pop()
            self.result = TurnResult(status="refused")
            return
        self.messages.append({"role": "assistant", "content": final.content})
        u = final.usage
        self.result = TurnResult(
            status="truncated" if final.stop_reason == "max_tokens" else "ok",
            cost=estimate_cost(u), tokens=(u.input_tokens or 0) + (u.output_tokens or 0))


class GeminiChat:
    provider = "gemini"

    def __init__(self, api_key: str):
        from google import genai
        # One SDK retry at most, plus a timeout: the SDK's default retries on a 503
        # "high demand" response kept the chat spinning for minutes.
        self.client = genai.Client(api_key=api_key, http_options={
            "timeout": GEMINI_TIMEOUT_MS, "retry_options": {"attempts": 1}})
        self.model = GEMINI_MODELS[0]   # the conversation stays on the model that answered
        self.previous_id: str | None = None
        self.result = TurnResult()

    @property
    def label(self) -> str:
        return f"Gemini · {self.model}" + (" (free tier)" if GEMINI_FREE_TIER else "")

    def stream(self, system_text: str, user_text: str) -> Iterator[str]:
        """Try the current model (twice), then the others, switching only before any text appears.

        A switch happens when a model is overloaded / out of quota, or when it
        finishes without writing any answer (it occasionally thinks, then stops).
        """
        models = [self.model] + [m for m in GEMINI_MODELS if m != self.model]
        for i, model in enumerate(models):
            attempts = 2 if i == 0 else 1   # an empty answer gets one retry on the same model
            for _ in range(attempts):
                started = False
                try:
                    for text in self._stream_one(model, system_text, user_text):
                        started = True
                        yield text
                except Exception as exc:
                    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                    retryable = status in _RETRY_NEXT_MODEL or isinstance(exc, ModelTimeout)
                    if started or not retryable or i == len(models) - 1:
                        raise
                    break  # overloaded / out of quota: go straight to the next model
                if started or self.result.status == "refused":
                    if started:
                        self.model = model
                    return
                # Finished with no answer text: nothing was shown, so try again.
        self.result = TurnResult(status="empty")

    def _stream_one(self, model: str, system_text: str, user_text: str) -> Iterator[str]:
        params = {
            "model": model,
            "input": user_text,
            "system_instruction": system_text,
            "generation_config": {"thinking_level": GEMINI_THINKING,
                                  "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS},
            "stream": True,
        }
        if self.previous_id:
            params["previous_interaction_id"] = self.previous_id

        interaction_id, status, usage = None, None, None
        streamed, completed = "", False
        events = iterate_with_deadline(lambda: self.client.interactions.create(**params),
                                       FIRST_EVENT_S, EVENT_GAP_S)
        for event in events:
            kind = getattr(event, "event_type", None)
            if kind == "interaction.created":
                interaction_id = event.interaction.id
            elif kind == "step.delta" and getattr(event.delta, "type", None) == "text":
                if event.delta.text:
                    streamed += event.delta.text
                    yield event.delta.text
            elif kind == "interaction.completed":
                completed = True
                interaction_id = event.interaction.id or interaction_id
                status, usage = event.interaction.status, event.interaction.usage
            elif kind == "error":
                err = event.error
                raise RuntimeError(f"Gemini error {getattr(err, 'code', '')}: {getattr(err, 'message', '')}")

        # The stream sometimes closes before the "completed" event, mid-answer. The
        # interaction keeps running on Google's side, so fetch the finished one and
        # add whatever didn't arrive. (Events carry no ids, so the stream can't be resumed.)
        if not completed and interaction_id:
            finished = self._wait_for(interaction_id)
            if finished is not None:
                completed = True
                status, usage = finished.status, getattr(finished, "usage", None)
                full = getattr(finished, "output_text", None) or ""
                if full.startswith(streamed) and len(full) > len(streamed):
                    rest = full[len(streamed):]
                    streamed += rest
                    yield rest
        wrote = bool(streamed)

        if status not in (None, "completed", "incomplete"):
            self.result = TurnResult(status="refused")
            return
        if not wrote:
            self.result = TurnResult(status="empty")  # don't continue the conversation from it
            return
        # Only continue the conversation from a turn that actually wrote an answer.
        self.previous_id = interaction_id or self.previous_id
        tokens = getattr(usage, "total_tokens", None) if usage else None
        cut_off = status == "incomplete" or not completed
        self.result = TurnResult(status="truncated" if cut_off else "ok",
                                 cost=0.0 if GEMINI_FREE_TIER else None, tokens=tokens)

    def _wait_for(self, interaction_id: str):
        """Poll a running interaction until it finishes (None if it doesn't in time)."""
        deadline = time.monotonic() + RECOVER_WAIT_S
        while True:
            try:
                interaction = next(iterate_with_deadline(
                    lambda: iter([self.client.interactions.get(interaction_id)]), EVENT_GAP_S, EVENT_GAP_S))
            except Exception:
                return None
            if getattr(interaction, "status", None) not in ("in_progress", "queued"):
                return interaction
            if time.monotonic() >= deadline:
                return None
            time.sleep(RECOVER_POLL_S)


def available_backend(anthropic_key: str | None, gemini_key: str | None):
    """The backend to use, from config and which API keys exist (None if no key)."""
    choice = CHAT_PROVIDER
    if choice == "auto":
        choice = "anthropic" if anthropic_key else "gemini" if gemini_key else None
    if choice == "anthropic" and anthropic_key:
        return AnthropicChat(anthropic_key)
    if choice == "gemini" and gemini_key:
        return GeminiChat(gemini_key)
    return None


def error_message(exc: Exception) -> str:
    """Friendly message for API errors from either SDK (matched by HTTP status)."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    name = type(exc).__name__
    if status in (401, 403) or name in ("AuthenticationError", "PermissionDeniedError"):
        return "The API key was rejected or doesn't have access to this model. Check `.streamlit/secrets.toml`."
    if status == 400 and "key" in str(exc).lower():
        return "The API key looks invalid. Check `.streamlit/secrets.toml`."
    if status == 429 or name == "RateLimitError":
        return ("Rate limit reached (free tiers allow only a few requests per minute and per day). "
                "Wait a minute and try again.")
    if name in ("APIConnectionError", "ConnectError", "ConnectTimeout") or "connect" in name.lower():
        return "Couldn't reach the model API — check your internet connection."
    if isinstance(exc, ModelTimeout):
        return ("The model stopped responding (the free Gemini tier is overloaded right now) and the "
                "backup model didn't answer either. Try again in a few minutes.")
    if status == 503:
        return ("The model provider is overloaded right now (503 \"high demand\") and the backup "
                "model was too — this is temporary, try again in a minute. (server error 503)")
    if isinstance(status, int) and status >= 500:
        return f"The model provider had a server error ({status}). Try again shortly."
    return f"Something went wrong: {exc}"
