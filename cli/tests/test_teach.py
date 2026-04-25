"""Tests for the ``tab teach`` Typer subcommand.

The wiring under test mirrors ``test_listen`` / ``test_think``, with
one new assertion: the teach command must register a ``web_search``
tool with the pydantic-ai agent. Acceptance criterion #2 in the port
ticket pins exactly that.

Two layers of coverage live here:

- The CLI surface (positional args, dial flags, error contract). The
  ``run_skill`` recorder pattern from ``test_think`` carries over.
- The tool wiring. ``test_teach_registers_web_search_tool_on_skill_agent``
  drops down a level — into ``compile_skill_agent`` — to assert that
  the ``Agent`` gets a ``web_search``-shaped tool. This is the only
  assertion that actually touches pydantic-ai's tool surface, so a
  regression in tool registration fails specifically here rather than
  silently passing the higher-level recorder tests.

A second test exercises the tool path end-to-end: a stub agent
captures the registered tools, invokes one, and the test confirms the
result reaches the agent's behaviour. Mocked WebSearch — no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app


@dataclass
class _RunSkillRecorder:
    """Capture every ``run_skill`` call and return a fixed string."""

    response: str = "What would you like to learn about?"
    raise_on_call: BaseException | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(
        self, skill_name: str, user_input: str, **kwargs: Any
    ) -> str:
        self.calls.append(
            {"skill_name": skill_name, "user_input": user_input, **kwargs}
        )
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.response


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def isolated_xdg(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Empty ``XDG_CONFIG_HOME`` so config lookups don't read a real file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    tab_dir = tmp_path / "tab"
    tab_dir.mkdir()
    return tab_dir


# ---------------------------------------------------------- CLI surface


def test_teach_invokes_teach_skill_with_no_topic(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Acceptance criterion #1: ``tab teach`` runs the teach skill."""
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["teach"])

    assert result.exit_code == 0, result.stderr
    assert "learn about" in result.stdout
    assert recorder.calls[0]["skill_name"] == "teach"
    # No positional args -> empty user input.
    assert recorder.calls[0]["user_input"] == ""


def test_teach_joins_positional_args_into_topic(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """SKILL.md treats positional words as the topic to teach."""
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            ["teach", "event", "sourcing"],
        )

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0]["user_input"] == "event sourcing"


def test_teach_passes_model_flag_to_run_skill(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            ["teach", "--model", "anthropic:claude-sonnet-4-7", "agent loops"],
        )

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0]["model"] == "anthropic:claude-sonnet-4-7"


def test_teach_dial_flags_round_trip_to_run_skill(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(
            app,
            [
                "teach",
                "--humor", "10",
                "--directness", "20",
                "--warmth", "30",
                "--autonomy", "40",
                "--verbosity", "50",
            ],
        )

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.humor == 10
    assert settings.directness == 20
    assert settings.warmth == 30
    assert settings.autonomy == 40
    assert settings.verbosity == 50


def test_teach_out_of_range_dial_exits_non_zero(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Same readable-error contract as ``tab ask``."""

    def _boom(*_: Any, **__: Any) -> Any:
        raise AssertionError("run_skill should not run on out-of-range input")

    with patch("tab_cli.skills.run_skill", _boom):
        result = runner.invoke(app, ["teach", "--humor", "150"])

    assert result.exit_code != 0
    assert "humor must be 0-100, got 150" in result.stderr


def test_teach_surfaces_runtime_errors_as_readable_message(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Skill-runner exceptions collapse to ``tab: <reason>`` and exit non-zero."""
    recorder = _RunSkillRecorder(
        raise_on_call=RuntimeError("API key missing")
    )

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["teach", "a topic"])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "API key missing" in result.stderr
    # No half-printed shaping question.
    assert result.stdout.strip() == ""


def test_teach_help_lists_the_subcommand_and_flags(
    runner: CliRunner,
) -> None:
    top = runner.invoke(app, ["--help"])
    assert top.exit_code == 0
    assert "teach" in top.stdout

    sub = runner.invoke(app, ["teach", "--help"])
    assert sub.exit_code == 0
    for dial in ("--humor", "--directness", "--warmth", "--autonomy", "--verbosity"):
        assert dial in sub.stdout, f"{dial} missing from `tab teach --help`"
    assert "--model" in sub.stdout


def test_teach_unset_flags_fall_through_to_tab_md_defaults(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """No flags + no config → ``TabSettings`` defaults reach the runner."""
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["teach"])

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.humor == 65
    assert settings.directness == 80
    assert settings.warmth == 70
    assert settings.autonomy == 50
    assert settings.verbosity == 35


def test_teach_unset_flags_fall_through_to_config_file(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """flag > config file > tab.md defaults — same precedence as other commands."""
    (isolated_xdg / "config.toml").write_text("[settings]\nverbosity = 7\n")

    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["teach"])

    assert result.exit_code == 0, result.stderr
    settings = recorder.calls[0]["settings"]
    assert settings.verbosity == 7     # config-file fallthrough
    assert settings.directness == 80   # tab.md default fallthrough


# ---------------------------------------------------------- tool wiring


def test_teach_passes_a_web_search_tool_into_run_skill(
    runner: CliRunner, isolated_xdg: Any
) -> None:
    """Acceptance criterion #2: a ``web_search``-shaped tool reaches the runner.

    The CLI wrapper resolves a tool from :mod:`tab_cli.web_search` and
    forwards it via ``run_skill(tools=[...])``. The recorder grabs the
    tools list off the kwargs and we assert at least one callable
    named ``web_search`` is in it. Lower-level tool semantics are
    pinned in ``test_web_search.py``.
    """
    recorder = _RunSkillRecorder()

    with patch("tab_cli.skills.run_skill", recorder):
        result = runner.invoke(app, ["teach", "agent loops"])

    assert result.exit_code == 0, result.stderr
    tools = recorder.calls[0].get("tools")
    assert tools is not None and len(tools) >= 1
    names = {getattr(t, "__name__", str(t)) for t in tools}
    assert "web_search" in names, f"expected web_search in {names!r}"


def test_teach_registers_web_search_tool_on_skill_agent(
    runner: CliRunner, isolated_xdg: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drop a level: ``compile_skill_agent`` must hand the tool to ``Agent``.

    We don't run the agent — we capture the kwargs the constructor
    saw. The test fakes pydantic-ai's ``Agent`` so it never instantiates
    a real model and pins the contract that a non-empty ``tools=``
    sequence reached the constructor.
    """
    captured: list[dict[str, Any]] = []

    class _StubPydanticAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.append(kwargs)

        def run_sync(self, *_: Any, **__: Any) -> Any:
            class _Result:
                output = "ok"

            return _Result()

    monkeypatch.setattr("pydantic_ai.Agent", _StubPydanticAgent)

    result = runner.invoke(app, ["teach", "RAG"])
    assert result.exit_code == 0, result.stderr

    assert captured, "Agent should have been constructed at least once"
    # Find the construction that came from the teach skill — it's the
    # one whose system_prompt contains the SKILL body's voice.
    teach_inits = [c for c in captured if "Phase 1" in c.get("system_prompt", "")]
    assert teach_inits, "expected teach SKILL body in the skill agent prompt"

    init = teach_inits[-1]
    tools = init.get("tools") or ()
    assert len(tools) >= 1
    names = {getattr(t, "__name__", str(t)) for t in tools}
    assert "web_search" in names


def test_teach_agent_can_invoke_web_search_and_incorporate_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance criterion #4: the agent can call WebSearch and use the results.

    We don't go through Typer for this — the assertion is about the
    tool-call mechanics, not the CLI surface. Build a teach agent
    against a stubbed pydantic-ai ``Agent`` that simulates a tool
    invocation by calling the registered ``web_search`` callable
    directly with a query, then composing the model's reply from the
    search snippet. The test confirms two things:

    1. The registered tool is callable and produces the documented
       ``[{title, url, snippet}]`` shape.
    2. The agent's "synthesis" pathway has access to the result — the
       text that comes back to ``run_sync`` includes the snippet, so
       a teach session would teach from research, not just memory.
    """
    from tab_cli.skills import compile_skill_agent
    from tab_cli.web_search import build_web_search_tool

    # Fake Exa client returns a curated result. The teach agent's
    # research call should see this exact snippet.
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
            # Simulate the teach agent's research phase: pull the tool
            # off the registry and invoke it. A real agent loop does
            # this through the model; for the test we want to assert
            # the tool is *invocable from inside the agent* and the
            # results round-trip into the visible output.
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

    # Synthesis pulled in the snippet — proof the search result reached
    # the teaching turn rather than being silently dropped.
    assert "Sequence of events" in result.output


# ----------------------------------------------------- chat-mode routing


def test_chat_routes_teach_match_through_grimoire_to_skill_agent_with_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance criterion #3: a teach-style prompt in chat reaches the teach skill.

    Modeled on ``test_chat.test_think_match_routes_through_grimoire_to_skill_agent``,
    with the extra teeth that the teach dispatch must wire a
    ``web_search`` tool. Stub the agents and the registry; assert the
    skill compile saw ``skill_name="teach"`` *and* received a
    ``web_search`` callable in its tools sequence.
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

    # Persona agent stayed out — the teach turn went through the skill
    # agent.
    assert persona_agent.runs == []
    assert len(skill_agent.runs) == 1

    # Skill compile saw teach + web_search.
    assert skill_compile_calls
    teach_call = next(
        (c for c in skill_compile_calls if c["skill_name"] == "teach"), None
    )
    assert teach_call is not None
    tools = teach_call.get("tools") or ()
    assert len(tools) >= 1
    names = {getattr(t, "__name__", str(t)) for t in tools}
    assert "web_search" in names

    # Skill output reached stdout.
    assert "starting point" in out
