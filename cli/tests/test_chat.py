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
def _patched_compile(
    stub_agent: _StubAgent,
    skill_agent: _StubAgent | None = None,
) -> Iterator[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Patch the agent factories used by the REPL.

    Two factories live in the call path: ``compile_tab_agent`` (the
    regular Tab persona agent — every chat turn that misses the skill
    registry) and ``compile_skill_agent`` (built per-skill-dispatch by
    the chat module's ``_dispatch_skill``). Yields ``(tab_calls,
    skill_calls)`` so tests can assert which factory ran and with which
    kwargs. ``skill_agent`` defaults to a fresh empty ``_StubAgent`` so
    a skill match in a test that didn't preload it gets sensible
    "ok"-stream behaviour from the agent stub instead of crashing.
    """
    tab_calls: list[dict[str, Any]] = []
    skill_calls: list[dict[str, Any]] = []
    skill_agent_to_return = skill_agent if skill_agent is not None else _StubAgent()

    def _tab_factory(**kwargs: Any) -> _StubAgent:
        tab_calls.append(kwargs)
        return stub_agent

    def _skill_factory(skill_name: str, **kwargs: Any) -> _StubAgent:
        # Skill name is the first positional arg in
        # `compile_skill_agent`; capture it alongside the kwargs so a
        # test can assert which skill was dispatched.
        skill_calls.append({"skill_name": skill_name, **kwargs})
        return skill_agent_to_return

    with (
        patch("tab_cli.personality.compile_tab_agent", _tab_factory),
        patch("tab_cli.chat.compile_tab_agent", _tab_factory),
        patch("tab_cli.skills.compile_skill_agent", _skill_factory),
        patch("tab_cli.chat.compile_skill_agent", _skill_factory, create=True),
    ):
        yield tab_calls, skill_calls


def _run_chat_with_input(
    text: str,
    *,
    agent: _StubAgent,
    registry: _StubRegistry | None = None,
    model: str | None = None,
    skill_agent: _StubAgent | None = None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Drive the REPL with stdin=``text`` and return ``(stdout, tab_calls, skill_calls)``."""
    from tab_cli.chat import run_chat

    stdin = io.StringIO(text)
    stdout = io.StringIO()
    with _patched_compile(agent, skill_agent=skill_agent) as (tab_calls, skill_calls):
        run_chat(
            model=model,
            registry=registry if registry is not None else _StubRegistry(),
            stdin=stdin,
            stdout=stdout,
        )
    return stdout.getvalue(), tab_calls, skill_calls


# -------------------------------------------------------------------- tests


def test_eof_exits_cleanly() -> None:
    agent = _StubAgent()
    out, _, _ = _run_chat_with_input("", agent=agent)
    # Greeting was printed.
    assert "tab" in out.lower()
    # No agent call — EOF on the first prompt.
    assert agent.runs == []


def test_slash_exit_ends_loop_without_calling_agent() -> None:
    agent = _StubAgent()
    out, _, _ = _run_chat_with_input("/exit\n", agent=agent)
    assert agent.runs == []
    # Greeting and prompt rendered, no traceback.
    assert "tab" in out.lower()


def test_slash_quit_also_exits() -> None:
    agent = _StubAgent()
    _, _, _ = _run_chat_with_input("/quit\n", agent=agent)
    assert agent.runs == []


def test_unmatched_input_routes_to_agent_and_streams_output() -> None:
    """Acceptance signal #1: no skill match → agent handles the turn."""
    agent = _StubAgent(
        response_stream=[(["hel", "lo ", "there"], [object(), object()])]
    )
    out, _, _ = _run_chat_with_input("hi tab\n/exit\n", agent=agent)
    # Stream chunks all reached stdout in order.
    assert "hello there" in out
    # Agent was called exactly once with the user's prompt.
    assert len(agent.runs) == 1
    assert agent.runs[0]["user_prompt"] == "hi tab"


def test_skill_match_dispatches_skill_agent_not_persona_agent() -> None:
    """Acceptance signal #2: registry hit routes to the skill agent.

    ``_dispatch_skill`` compiles a skill-aware agent (Tab persona +
    SKILL.md body) and runs *that* against the user prompt. The regular
    persona-agent factory must not see the turn — the test stubs both
    factories and asserts the routing edge.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[(["    /\\__/\\\n   ( o.o )"], [object(), object()])]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="draw-dino", passed=True)
        if "dinosaur" in q
        else None
    )
    out, tab_calls, skill_calls = _run_chat_with_input(
        "draw me a dinosaur\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Persona agent was bypassed; skill agent ran exactly once.
    assert persona_agent.runs == []
    assert len(skill_agent.runs) == 1
    assert skill_agent.runs[0]["user_prompt"] == "draw me a dinosaur"

    # The skill compile saw the matched skill name.
    assert len(skill_calls) == 1
    assert skill_calls[0]["skill_name"] == "draw-dino"

    # The skill's streamed output reached stdout.
    assert "/\\__/\\" in out

    # The persona-agent factory was still called once at session start
    # (that's how the REPL builds the default Tab agent), but never
    # for the skill turn.
    assert len(tab_calls) == 1


def test_skill_match_threads_messages_into_session_history() -> None:
    """Skill turn's ``all_messages()`` must roll into the session history.

    Otherwise the next agent turn loses context — the user's "what did
    you just draw?" follow-up wouldn't see the dino exchange.
    """
    persona_agent = _StubAgent(response_stream=[(["a brontosaurus"], [object()])])
    skill_agent = _StubAgent(response_stream=[(["dino-art"], ["skill-msg-1"])])
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="draw-dino", passed=True)
        if "dinosaur" in q
        else None
    )

    _, _, _ = _run_chat_with_input(
        "draw me a dinosaur\nwhat was that?\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Second turn (the persona agent) must see the skill turn's
    # messages threaded in as message_history.
    assert len(persona_agent.runs) == 1
    assert persona_agent.runs[0]["message_history"] == ["skill-msg-1"]


def test_below_threshold_hit_falls_through_to_agent() -> None:
    """``hit.passed=False`` is silence — the agent must still see the input."""
    agent = _StubAgent(response_stream=[(["fallback"], [object()])])
    registry = _StubRegistry(
        responder=lambda _q: _StubHit(name="draw-dino", passed=False)
    )
    out, _, _ = _run_chat_with_input(
        "ambient draw something\n/exit\n", agent=agent, registry=registry
    )
    assert "fallback" in out
    assert len(agent.runs) == 1


def test_history_persists_across_turns() -> None:
    """Acceptance signal #3: the second turn must see turn-1 messages."""
    turn1 = (["one"], ["msg-from-turn-1"])
    turn2 = (["two"], ["msg-from-turn-1", "msg-from-turn-2"])
    agent = _StubAgent(response_stream=[turn1, turn2])

    out, _, _ = _run_chat_with_input("first\nsecond\n/exit\n", agent=agent)

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

    out, calls, _ = _run_chat_with_input(
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

    out, calls, _ = _run_chat_with_input("be more direct\n/exit\n", agent=agent)

    # Only the session-start compile — no settings change happened.
    assert len(calls) == 1
    assert "agent fielded it" in out
    assert agent.runs[0]["user_prompt"] == "be more direct"


def test_set_command_clamps_out_of_range_value() -> None:
    """Out-of-range numeric values clamp to [0, 100] rather than reject."""
    agent = _StubAgent()

    _, calls, _ = _run_chat_with_input("set humor to 250\n/exit\n", agent=agent)

    assert calls[1]["settings"].humor == 100


def test_setting_change_does_not_reset_history() -> None:
    """Recompilation on a settings change must keep the conversation going."""
    turn1 = (["first"], ["msg-1"])
    turn2 = (["second"], ["msg-1", "msg-2"])
    agent = _StubAgent(response_stream=[turn1, turn2])

    _, _, _ = _run_chat_with_input(
        "hello\nset humor to 20%\nhi again\n/exit\n", agent=agent
    )

    # The post-settings agent turn must see turn-1 history.
    assert agent.runs[1]["message_history"] == ["msg-1"]


def test_model_kwarg_is_passed_through_to_compile() -> None:
    """``--model`` must round-trip into ``compile_tab_agent``."""
    agent = _StubAgent()
    _, calls, _ = _run_chat_with_input(
        "/exit\n", agent=agent, model="anthropic:claude-sonnet-4-7"
    )
    assert calls[0]["model"] == "anthropic:claude-sonnet-4-7"


def test_empty_lines_are_skipped() -> None:
    """Whitespace-only input shouldn't trigger an agent call."""
    agent = _StubAgent(response_stream=[(["actual response"], [object()])])
    out, _, _ = _run_chat_with_input("\n   \nhello\n/exit\n", agent=agent)
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


# ----------------------------------------------------- Sticky listen mode
#
# Once the grimoire registry fires ``listen``, the session enters a
# sticky mode where every subsequent line bypasses grimoire and
# settings detection and routes through the listen skill agent. The
# SKILL.md body keeps Tab silent during the dump and emits a synthesis
# when the user signals done. ``/done`` is the explicit exit signal:
# the line is forwarded so the skill agent produces the synthesis,
# then the session returns to normal chat.
#
# Acceptance criteria 2 + 3 from the porting task (the chat-mode
# behavior and the exit signal) live in this section.


def test_listen_match_sticks_subsequent_turns_to_skill_agent() -> None:
    """Acceptance criterion #2: ``listen`` is sticky inside ``tab chat``.

    After grimoire fires ``listen``, follow-up lines must continue to
    reach the listen skill agent — not the regular Tab agent. The SKILL
    body's "stay silent" promise breaks if the next line falls through
    to the default chat path.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[
            (["Listening. Say 'done' when ready."], [object()]),
            ([""], [object()]),  # silent listen turn
            ([""], [object()]),  # another silent listen turn
        ]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="listen", passed=True)
        if "listen" in q
        else None
    )

    out, _, skill_calls = _run_chat_with_input(
        "listen to me think\nfirst thought\nsecond thought\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Persona agent never ran — every turn went through the skill agent.
    assert persona_agent.runs == []
    # Three skill turns: the entry match plus two follow-on lines.
    assert len(skill_agent.runs) == 3
    assert skill_agent.runs[0]["user_prompt"] == "listen to me think"
    assert skill_agent.runs[1]["user_prompt"] == "first thought"
    assert skill_agent.runs[2]["user_prompt"] == "second thought"

    # The acknowledgement reached stdout from the entry turn.
    assert "Listening" in out
    # All three skill dispatches resolved the listen skill name.
    assert all(call["skill_name"] == "listen" for call in skill_calls)


def test_listen_mode_routes_done_through_skill_then_exits() -> None:
    """Acceptance criterion #3: ``/done`` exits listen mode.

    The user-typed ``/done`` line is forwarded so the SKILL body's
    synthesis branch fires, then the session drops back to normal
    routing — the next line goes to the regular Tab agent.
    """
    persona_agent = _StubAgent(
        response_stream=[(["back to normal"], [object()])]
    )
    skill_agent = _StubAgent(
        response_stream=[
            (["Listening."], [object()]),         # entry
            ([""], [object()]),                   # silent turn
            (["Synthesis: ..."], [object()]),     # /done -> synthesis
        ]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="listen", passed=True)
        if "listen" in q
        else None
    )

    out, _, _ = _run_chat_with_input(
        "listen to me think\nthought one\n/done\nhello again\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Three skill turns: entry, silent turn, /done with synthesis.
    assert len(skill_agent.runs) == 3
    # ``/done`` reached the skill agent so it could produce the synthesis.
    assert skill_agent.runs[2]["user_prompt"] == "/done"

    # After /done, the next line went to the persona agent.
    assert len(persona_agent.runs) == 1
    assert persona_agent.runs[0]["user_prompt"] == "hello again"

    # Synthesis text reached stdout.
    assert "Synthesis" in out
    # Post-exit chat output reached stdout too.
    assert "back to normal" in out


def test_exit_breaks_out_of_listen_mode() -> None:
    """``/exit`` ends the session even mid-listen-mode.

    Sticky-mode lock-in would be a real failure mode if ``/exit`` got
    swallowed by the listen branch. The escape hatch must be
    unconditional.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[(["Listening."], [object()])]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="listen", passed=True)
        if "listen" in q
        else None
    )

    out, _, _ = _run_chat_with_input(
        "listen to me think\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Only the entry turn fired through the skill; ``/exit`` ended the loop.
    assert len(skill_agent.runs) == 1
    assert "Listening" in out


def test_listen_mode_bypasses_grimoire_for_other_skills() -> None:
    """While listening, an apparent ``draw-dino`` match must not interrupt.

    The user is mid-dump; routing to a different skill mid-stream
    breaks the SKILL body's "track everything" promise. They have to
    ``/done`` (or ``/exit``) before another skill can fire.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[
            (["Listening."], [object()]),
            ([""], [object()]),
        ]
    )

    # The registry would happily match ``draw-dino`` on the second
    # query — but the listen-mode branch must short-circuit before the
    # registry is even consulted.
    def _responder(query: str) -> _StubHit | None:
        if "listen" in query:
            return _StubHit(name="listen", passed=True)
        if "dinosaur" in query:
            return _StubHit(name="draw-dino", passed=True)
        return None

    registry = _StubRegistry(responder=_responder)

    _, _, skill_calls = _run_chat_with_input(
        "listen to me think\ndraw me a dinosaur out loud\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Both skill dispatches resolved the listen skill — neither
    # routed to draw-dino.
    assert all(call["skill_name"] == "listen" for call in skill_calls)
    assert len(skill_calls) == 2


def test_think_match_routes_through_grimoire_to_skill_agent() -> None:
    """Acceptance criterion (think port #2): a think-style prompt in chat
    routes through grimoire to the think skill agent.

    Unlike ``listen``, ``think`` is not sticky — a single grimoire match
    is enough to pin the routing edge. Follow-on turns may either hit
    the registry again or fall through to the regular Tab agent with the
    think exchange already in history; either is fine for the SKILL
    body's "follow the energy" style.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[
            (
                ["So you're picturing markdown-to-slides. ",
                 "What's the smallest version that would feel useful?"],
                [object(), object()],
            )
        ]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="think", passed=True)
        if "think" in q
        else None
    )

    out, tab_calls, skill_calls = _run_chat_with_input(
        "/think a markdown-to-slides tool\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # Persona agent was bypassed for the think turn.
    assert persona_agent.runs == []
    assert len(skill_agent.runs) == 1
    assert skill_calls[0]["skill_name"] == "think"

    # The skill's streamed shaping question reached stdout.
    assert "smallest version" in out

    # Session-start compile only — no settings change happened.
    assert len(tab_calls) == 1


def test_listen_mode_bypasses_settings_nudge() -> None:
    """``set humor to 90%`` mid-listen reaches the skill agent, not settings.

    A settings ack ("[settings: humor 90%, ...]") would be Tab making
    noise during a deliberate-silence mode. The SKILL body decides what
    to do with the line; the chat layer doesn't intercept.
    """
    persona_agent = _StubAgent()
    skill_agent = _StubAgent(
        response_stream=[
            (["Listening."], [object()]),
            ([""], [object()]),
        ]
    )
    registry = _StubRegistry(
        responder=lambda q: _StubHit(name="listen", passed=True)
        if "listen" in q
        else None
    )

    out, calls, _ = _run_chat_with_input(
        "listen to me think\nset humor to 90%\n/exit\n",
        agent=persona_agent,
        skill_agent=skill_agent,
        registry=registry,
    )

    # No settings recompile happened — only the session-start compile.
    assert len(calls) == 1
    # The settings ack line did not appear.
    assert "humor 90%" not in out.lower()
    # The setting line went to the skill agent instead.
    assert skill_agent.runs[1]["user_prompt"] == "set humor to 90%"
