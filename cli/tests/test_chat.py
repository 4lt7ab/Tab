"""Tests for the ``tab chat`` REPL.

The REPL has four moving parts and the tests pin each one:

- I/O loop: read a line, react, repeat. ``/exit``, ``/quit``, and EOF
  all end the session; empty input is a no-op.
- Routing: an above-threshold registry hit is reported as a skill
  match (no agent call); a miss falls through to the agent.
- Streaming + history: ``run_stream_sync`` chunks reach stdout; the
  conversation history carries forward across turns.
- Settings adjustment: "set humor to 90%" mutates the active
  :class:`TabSettings`, recompiles the agent, and continues the loop
  with history intact.

Both the agent and the registry are stubbed — no LLM provider, no
grimoire runtime. The Typer-level dispatch (bare ``tab`` → ``tab
chat``) gets its own integration-shaped test using
``CliRunner`` and a patched ``run_chat``.
"""

from __future__ import annotations

import io
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app


# --------------------------------------------------------------- fakes


@dataclass
class _StubStreamResult:
    """Stand-in for ``StreamedRunResultSync``.

    Acts as a context manager (the REPL uses ``with`` around
    ``run_stream_sync``) and exposes ``stream_text(delta=True)`` plus
    ``all_messages()``. The chunks/messages are taken from the
    constructor so tests can assert exactly what reached stdout and
    what got threaded into the next turn's history.
    """

    chunks: list[str]
    messages: list[Any]

    def __enter__(self) -> _StubStreamResult:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def stream_text(self, *, delta: bool = False) -> Iterator[str]:
        # The REPL calls ``stream_text(delta=True)`` — pinning that
        # keyword keeps a future regression honest.
        assert delta is True, "REPL must request deltas, not cumulative text"
        yield from self.chunks

    def all_messages(self) -> list[Any]:
        return list(self.messages)


@dataclass
class _StubAgent:
    """Stand-in for ``pydantic_ai.Agent`` for the REPL's needs.

    Records each ``run_stream_sync`` call so tests can assert that the
    user prompt and the previous turn's history rounded-trip into the
    streaming call. Each call returns the next entry from
    ``response_stream`` — a list of ``(chunks, all_messages)`` tuples
    — so a test can simulate multi-turn conversations.
    """

    response_stream: list[tuple[list[str], list[Any]]] = field(default_factory=list)
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
        # If a test set up multiple turns, pop the next planned response;
        # otherwise default to a single empty-ish response so a single
        # call without setup still works.
        if self.response_stream:
            chunks, messages = self.response_stream.pop(0)
        else:
            chunks, messages = (["ok"], [object()])
        return _StubStreamResult(chunks=chunks, messages=messages)


@dataclass
class _StubHit:
    """Stand-in for ``grimoire.Hit``.

    The REPL only reads ``name`` and ``passed`` (similarity/threshold
    are diagnostic-only at this layer), so that's all the stub needs.
    """

    name: str
    passed: bool
    similarity: float = 0.0
    threshold: float = 0.55


@dataclass
class _StubRegistry:
    """Stand-in for ``SkillRegistry``.

    Per-query behavior is plugged in via ``responder`` — a callable
    that receives the query string and returns a ``_StubHit`` or
    ``None``. Default is "no match for anything," which is the right
    behaviour for tests that aren't exercising the routing edge.
    """

    responder: Any = None

    def match(self, query: str) -> _StubHit | None:
        if self.responder is None:
            return None
        return self.responder(query)


# --------------------------------------------------------------- helpers


@contextmanager
def _patched_compile(stub_agent: _StubAgent) -> Iterator[list[dict[str, Any]]]:
    """Patch ``compile_tab_agent`` to return ``stub_agent`` and record kwargs.

    Two patches: the source module (where the REPL imports from) and
    ``tab_cli.chat`` (in case the REPL imports it at module level in a
    future refactor). Yields the kwargs-list so tests can assert what
    was passed in.
    """
    calls: list[dict[str, Any]] = []

    def _factory(**kwargs: Any) -> _StubAgent:
        calls.append(kwargs)
        return stub_agent

    with (
        patch("tab_cli.personality.compile_tab_agent", _factory),
        patch("tab_cli.chat.compile_tab_agent", _factory),
    ):
        yield calls


def _run_chat_with_input(
    text: str,
    *,
    agent: _StubAgent,
    registry: _StubRegistry | None = None,
    model: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Drive the REPL with stdin=``text`` and return (stdout, compile_calls)."""
    from tab_cli.chat import run_chat

    stdin = io.StringIO(text)
    stdout = io.StringIO()
    with _patched_compile(agent) as compile_calls:
        run_chat(
            model=model,
            registry=registry if registry is not None else _StubRegistry(),
            stdin=stdin,
            stdout=stdout,
        )
    return stdout.getvalue(), compile_calls


# -------------------------------------------------------------------- tests


def test_eof_exits_cleanly() -> None:
    agent = _StubAgent()
    out, _ = _run_chat_with_input("", agent=agent)
    # Greeting was printed.
    assert "tab" in out.lower()
    # No agent call — EOF on the first prompt.
    assert agent.runs == []


def test_slash_exit_ends_loop_without_calling_agent() -> None:
    agent = _StubAgent()
    out, _ = _run_chat_with_input("/exit\n", agent=agent)
    assert agent.runs == []
    # Greeting and prompt rendered, no traceback.
    assert "tab" in out.lower()


def test_slash_quit_also_exits() -> None:
    agent = _StubAgent()
    _, _ = _run_chat_with_input("/quit\n", agent=agent)
    assert agent.runs == []


def test_unmatched_input_routes_to_agent_and_streams_output() -> None:
    """Acceptance signal #1: no skill match → agent handles the turn."""
    agent = _StubAgent(
        response_stream=[(["hel", "lo ", "there"], [object(), object()])]
    )
    out, _ = _run_chat_with_input("hi tab\n/exit\n", agent=agent)
    # Stream chunks all reached stdout in order.
    assert "hello there" in out
    # Agent was called exactly once with the user's prompt.
    assert len(agent.runs) == 1
    assert agent.runs[0]["user_prompt"] == "hi tab"


def test_skill_match_bypasses_agent_and_names_the_skill() -> None:
    """Acceptance signal #2: registry hit dispatches the skill, not the agent."""
    agent = _StubAgent()
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="draw-dino", passed=True)
        if "dinosaur" in q
        else None
    )
    out, _ = _run_chat_with_input(
        "draw me a dinosaur\n/exit\n", agent=agent, registry=registry
    )
    assert "draw-dino" in out, out
    # Agent was NOT called for the skill turn.
    assert agent.runs == []


def test_below_threshold_hit_falls_through_to_agent() -> None:
    """``hit.passed=False`` is silence — the agent must still see the input."""
    agent = _StubAgent(response_stream=[(["fallback"], [object()])])
    registry = _StubRegistry(
        responder=lambda _q: _StubHit(name="draw-dino", passed=False)
    )
    out, _ = _run_chat_with_input(
        "ambient draw something\n/exit\n", agent=agent, registry=registry
    )
    assert "fallback" in out
    assert len(agent.runs) == 1


def test_history_persists_across_turns() -> None:
    """Acceptance signal #3: the second turn must see turn-1 messages."""
    turn1 = (["one"], ["msg-from-turn-1"])
    turn2 = (["two"], ["msg-from-turn-1", "msg-from-turn-2"])
    agent = _StubAgent(response_stream=[turn1, turn2])

    out, _ = _run_chat_with_input("first\nsecond\n/exit\n", agent=agent)

    assert "one" in out
    assert "two" in out
    assert len(agent.runs) == 2
    # Turn 1 had no prior history.
    assert agent.runs[0]["message_history"] == []
    # Turn 2 received turn 1's full message list as history.
    assert agent.runs[1]["message_history"] == ["msg-from-turn-1"]


def test_set_humor_command_recompiles_agent_with_new_setting() -> None:
    """Acceptance signal #4: numeric set commands mutate the active settings."""
    agent = _StubAgent(response_stream=[(["after"], [object()])])

    out, calls = _run_chat_with_input(
        "set humor to 90%\nhello\n/exit\n", agent=agent
    )

    # First compile is the session start (default settings).
    # Second compile is after the settings change.
    assert len(calls) >= 2
    initial_settings = calls[0]["settings"]
    post_change = calls[1]["settings"]
    assert initial_settings.humor == 65  # tab.md default
    assert post_change.humor == 90
    # Other settings carry over unchanged.
    assert post_change.directness == initial_settings.directness
    # The acknowledgement appeared on stdout.
    assert "humor 90%" in out.lower()


def test_comparative_phrase_falls_through_to_agent() -> None:
    """v0 only handles ``set <name> to <value>``; "be more direct" goes to chat.

    The adjective→dial mapping is the deferred settings-UX ticket's
    job. Until that lands, the agent fields these phrases as free-form
    chat — and the test pins the contract that the chat layer doesn't
    accidentally swallow them as no-op settings nudges.
    """
    agent = _StubAgent(response_stream=[(["agent fielded it"], [object()])])

    out, calls = _run_chat_with_input("be more direct\n/exit\n", agent=agent)

    # Only the session-start compile — no settings change happened.
    assert len(calls) == 1
    assert "agent fielded it" in out
    assert agent.runs[0]["user_prompt"] == "be more direct"


def test_set_command_clamps_out_of_range_value() -> None:
    """Out-of-range numeric values clamp to [0, 100] rather than reject."""
    agent = _StubAgent()

    _, calls = _run_chat_with_input("set humor to 250\n/exit\n", agent=agent)

    assert calls[1]["settings"].humor == 100


def test_setting_change_does_not_reset_history() -> None:
    """Recompilation on a settings change must keep the conversation going."""
    turn1 = (["first"], ["msg-1"])
    turn2 = (["second"], ["msg-1", "msg-2"])
    agent = _StubAgent(response_stream=[turn1, turn2])

    _, _ = _run_chat_with_input(
        "hello\nset humor to 20%\nhi again\n/exit\n", agent=agent
    )

    # The post-settings agent turn must see turn-1 history.
    assert agent.runs[1]["message_history"] == ["msg-1"]


def test_model_kwarg_is_passed_through_to_compile() -> None:
    """``--model`` must round-trip into ``compile_tab_agent``."""
    agent = _StubAgent()
    _, calls = _run_chat_with_input(
        "/exit\n", agent=agent, model="anthropic:claude-sonnet-4-7"
    )
    assert calls[0]["model"] == "anthropic:claude-sonnet-4-7"


def test_empty_lines_are_skipped() -> None:
    """Whitespace-only input shouldn't trigger an agent call."""
    agent = _StubAgent(response_stream=[(["actual response"], [object()])])
    out, _ = _run_chat_with_input("\n   \nhello\n/exit\n", agent=agent)
    assert "actual response" in out
    # Only the non-blank line reached the agent.
    assert len(agent.runs) == 1
    assert agent.runs[0]["user_prompt"] == "hello"


# ----------------------------------------------------- Typer-level dispatch


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_bare_tab_invokes_chat(runner: CliRunner) -> None:
    """``tab`` with no subcommand must default to ``tab chat``."""
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, [])

    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    assert captured[0]["model"] is None


def test_bare_tab_passes_model_flag(runner: CliRunner) -> None:
    """``tab --model X`` must route the model into the chat run."""
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["--model", "openai:gpt-5"])

    assert result.exit_code == 0, result.output
    assert captured[0]["model"] == "openai:gpt-5"


def test_tab_chat_subcommand_invokes_chat(runner: CliRunner) -> None:
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["chat", "--model", "anthropic:claude-sonnet-4"])

    assert result.exit_code == 0, result.output
    assert captured[0]["model"] == "anthropic:claude-sonnet-4"


def test_chat_help_lists_command_and_flags(runner: CliRunner) -> None:
    top = runner.invoke(app, ["--help"])
    assert top.exit_code == 0
    assert "chat" in top.stdout
    assert "ask" in top.stdout

    sub = runner.invoke(app, ["chat", "--help"])
    assert sub.exit_code == 0
    assert "--model" in sub.stdout


def test_tab_chat_surfaces_runtime_errors_as_readable_message(
    runner: CliRunner,
) -> None:
    """Errors loading the agent or registry collapse to ``tab: <reason>``."""

    def _boom(**_: Any) -> None:
        raise RuntimeError("API key missing")

    with patch("tab_cli.chat.run_chat", _boom):
        result = runner.invoke(app, ["chat"])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "API key missing" in result.stderr


def test_bare_tab_surfaces_runtime_errors(runner: CliRunner) -> None:
    """Same readable-error contract on the bare-tab path."""

    def _boom(**_: Any) -> None:
        raise RuntimeError("registry unreachable")

    with patch("tab_cli.chat.run_chat", _boom):
        result = runner.invoke(app, [])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "registry unreachable" in result.stderr


# ---- Personality dial flags (Typer-level) ---------------------------------
#
# `tab chat` and the bare-`tab` shortcut both expose the five
# `--<dial> INT` flags. The values they parse must round-trip into
# `run_chat(settings=...)`. Range errors emit the same one-line stderr
# message as `tab ask`.


@pytest.fixture
def isolated_xdg(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Empty ``XDG_CONFIG_HOME`` so the resolver doesn't read real config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    tab_dir = tmp_path / "tab"
    tab_dir.mkdir()
    return tab_dir


def test_tab_chat_humor_flag_routes_to_run_chat(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """``tab chat --humor 90`` must reach ``run_chat`` with humor=90."""
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["chat", "--humor", "90"])

    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    settings = captured[0].get("settings")
    assert settings is not None, "run_chat must receive a TabSettings"
    assert settings.humor == 90
    # Other dials default.
    assert settings.directness == 80


def test_tab_chat_all_five_dial_flags_round_trip(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(
            app,
            [
                "chat",
                "--humor", "5",
                "--directness", "15",
                "--warmth", "25",
                "--autonomy", "35",
                "--verbosity", "45",
            ],
        )

    assert result.exit_code == 0, result.output
    settings = captured[0]["settings"]
    assert settings.humor == 5
    assert settings.directness == 15
    assert settings.warmth == 25
    assert settings.autonomy == 35
    assert settings.verbosity == 45


def test_tab_chat_out_of_range_dial_exits_non_zero(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """``tab chat --humor 150`` must surface the readable range error."""

    def _stub(**_: Any) -> None:
        # Should never be called — validation happens before run_chat.
        raise AssertionError("run_chat should not run on out-of-range input")

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["chat", "--humor", "150"])

    assert result.exit_code != 0
    assert "humor must be 0-100, got 150" in result.stderr


def test_bare_tab_humor_flag_routes_to_run_chat(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """The bare-``tab``-defaults-to-chat path must accept dial flags too."""
    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["--humor", "12", "--verbosity", "88"])

    assert result.exit_code == 0, result.output
    settings = captured[0]["settings"]
    assert settings.humor == 12
    assert settings.verbosity == 88


def test_bare_tab_out_of_range_dial_exits_non_zero(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Same range error on the bare-``tab`` path."""

    def _stub(**_: Any) -> None:
        raise AssertionError("run_chat should not run on out-of-range input")

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["--directness", "200"])

    assert result.exit_code != 0
    assert "directness must be 0-100, got 200" in result.stderr


def test_tab_chat_unset_flags_fall_through_to_config_then_defaults(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """flag > config file > tab.md defaults — same precedence on chat."""
    (isolated_xdg / "config.toml").write_text("[settings]\nautonomy = 99\n")

    captured: list[dict[str, Any]] = []

    def _stub(**kwargs: Any) -> None:
        captured.append(kwargs)

    with patch("tab_cli.chat.run_chat", _stub):
        result = runner.invoke(app, ["chat", "--humor", "10"])

    assert result.exit_code == 0, result.output
    settings = captured[0]["settings"]
    assert settings.humor == 10        # flag wins
    assert settings.autonomy == 99     # config-file fallthrough
    assert settings.directness == 80   # tab.md default fallthrough


def test_tab_chat_help_lists_dial_flags(runner: CliRunner) -> None:
    sub = runner.invoke(app, ["chat", "--help"])
    assert sub.exit_code == 0
    for dial in ("--humor", "--directness", "--warmth", "--autonomy", "--verbosity"):
        assert dial in sub.stdout, f"{dial} missing from `tab chat --help`"
