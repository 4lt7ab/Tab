"""Tests for the ``teach`` skill's chat-mode wiring.

The ``teach`` skill ships only as a chat-routed skill — there is no
one-shot ``tab teach`` Typer verb. The two tests here pin the contract
that matters:

- ``test_teach_agent_can_invoke_web_search_and_incorporate_results``
  drops below the chat REPL into :func:`compile_skill_agent` and proves
  the registered ``web_search`` tool is callable from inside a teach
  agent and that its results round-trip into the agent's output.

- ``test_chat_routes_teach_match_through_grimoire_to_skill_agent_with_tool``
  exercises the full chat path: a teach-style prompt clears grimoire,
  ``compile_skill_agent`` is called with ``skill_name="teach"`` *and* a
  ``web_search`` tool in its ``tools=`` list. Mocked WebSearch — no
  network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


def test_teach_agent_can_invoke_web_search_and_incorporate_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registered ``web_search`` tool is callable from inside a teach agent.

    Build a teach agent against a stubbed pydantic-ai ``Agent`` that
    simulates a tool invocation by calling the registered ``web_search``
    callable directly with a query, then composing the model's reply
    from the search snippet. The test confirms two things:

    1. The registered tool is callable and produces the documented
       ``[{title, url, snippet}]`` shape.
    2. The agent's "synthesis" pathway has access to the result — the
       text that comes back to ``run_sync`` includes the snippet, so
       a teach session would teach from research, not just memory.
    """
    from tab_cli.skills import compile_skill_agent
    from tab_cli.web_search import build_web_search_tool

    exa_payload = {
        "results": [
            {
                "title": "Event Sourcing — Martin Fowler",
                "url": "https://martinfowler.com/eaaDev/EventSourcing.html",
                "text": "Sequence of events as the source of truth.",
            }
        ]
    }

    class _FakeResponse:
        def json(self) -> Any:
            return exa_payload

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def post(self, url: str, **_: Any) -> _FakeResponse:
            return _FakeResponse()

    web_search = build_web_search_tool(
        api_key="exa-key", http_client=_FakeClient()
    )

    captured_tools: list[Any] = []

    class _StubPydanticAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured_tools.extend(kwargs.get("tools") or ())

        def run_sync(self, user_prompt: str) -> Any:
            tool = next(
                (t for t in captured_tools if getattr(t, "__name__", "") == "web_search"),
                None,
            )
            assert tool is not None, "web_search tool must be registered on the agent"
            results = tool(user_prompt)
            assert isinstance(results, list)
            assert results and "Sequence of events" in results[0]["snippet"]

            class _Result:
                output = (
                    f"Researched {user_prompt}; one source frames it as "
                    f"'{results[0]['snippet']}'"
                )

            return _Result()

    monkeypatch.setattr("pydantic_ai.Agent", _StubPydanticAgent)

    agent = compile_skill_agent("teach", tools=[web_search])
    result = agent.run_sync("event sourcing")

    assert "Sequence of events" in result.output


def test_chat_routes_teach_match_through_grimoire_to_skill_agent_with_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A teach-style prompt in chat reaches the teach skill with web_search wired.

    Stub the agents and the registry; assert the skill compile saw
    ``skill_name="teach"`` *and* received a ``web_search`` callable in
    its tools sequence.
    """
    import io
    from contextlib import contextmanager
    from typing import Iterator
    from unittest.mock import patch

    @dataclass
    class _StubStreamResult:
        chunks: list[str]
        messages: list[Any]

        def __enter__(self) -> "_StubStreamResult":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def stream_text(self, *, delta: bool = False) -> Any:
            yield from self.chunks

        def all_messages(self) -> list[Any]:
            return list(self.messages)

    @dataclass
    class _StubAgent:
        response_stream: list[tuple[list[str], list[Any]]] = field(
            default_factory=list
        )
        runs: list[dict[str, Any]] = field(default_factory=list)

        def run_stream_sync(
            self,
            user_prompt: str,
            *,
            message_history: list[Any] | None = None,
        ) -> _StubStreamResult:
            self.runs.append(
                {
                    "user_prompt": user_prompt,
                    "message_history": list(message_history)
                    if message_history is not None
                    else None,
                }
            )
            if self.response_stream:
                chunks, messages = self.response_stream.pop(0)
            else:
                chunks, messages = (["ok"], [object()])
            return _StubStreamResult(chunks=chunks, messages=messages)

    @dataclass
    class _StubHit:
        name: str
        passed: bool
        similarity: float = 0.0
        threshold: float = 0.55

    @dataclass
    class _StubRegistry:
        responder: Any = None

        def match(self, query: str) -> _StubHit | None:
            if self.responder is None:
                return None
            return self.responder(query)

    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[(["What's your starting point?"], [object()])]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="teach", passed=True)
        if "teach" in q
        else None
    )

    skill_compile_calls: list[dict[str, Any]] = []
    tab_compile_calls: list[dict[str, Any]] = []

    def _tab_factory(**kwargs: Any) -> _StubAgent:
        tab_compile_calls.append(kwargs)
        return persona_agent

    def _skill_factory(skill_name: str, **kwargs: Any) -> _StubAgent:
        skill_compile_calls.append({"skill_name": skill_name, **kwargs})
        return skill_agent

    @contextmanager
    def _patches() -> Iterator[None]:
        with (
            patch("tab_cli.personality.compile_tab_agent", _tab_factory),
            patch("tab_cli.chat.compile_tab_agent", _tab_factory),
            patch("tab_cli.skills.compile_skill_agent", _skill_factory),
            patch("tab_cli.chat.compile_skill_agent", _skill_factory, create=True),
        ):
            yield

    from tab_cli.chat import run_chat

    stdin = io.StringIO("teach me about agent loops\n/exit\n")
    stdout = io.StringIO()
    with _patches():
        run_chat(registry=registry, stdin=stdin, stdout=stdout)

    out = stdout.getvalue()

    assert persona_agent.runs == []
    assert len(skill_agent.runs) == 1

    assert skill_compile_calls
    teach_call = next(
        (c for c in skill_compile_calls if c["skill_name"] == "teach"), None
    )
    assert teach_call is not None
    tools = teach_call.get("tools") or ()
    assert len(tools) >= 1
    names = {getattr(t, "__name__", str(t)) for t in tools}
    assert "web_search" in names

    assert "starting point" in out
