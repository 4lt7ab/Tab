"""Tests for the ``tab ask`` one-shot subcommand.

The wiring under test is small but load-bearing: the CLI argument and
``--model`` option must round-trip through ``compile_tab_agent``, the
agent's ``run_sync`` output must reach stdout, and any exception from
either step must collapse to a readable stderr line plus a non-zero
exit code (no traceback dump — this command is the shell-out / CI
entry point and tracebacks make it hostile to scripting).

We mock ``compile_tab_agent`` so the test never reaches a real model
provider. The stub records each call so the prompt round-trip
assertion is precise — the test fails if either the positional prompt
argument or the ``--model`` option is dropped on the floor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app


@dataclass
class _StubResult:
    """Stand-in for ``pydantic_ai.AgentRunResult``.

    Only ``.output`` is read by the CLI; the rest of the result shape
    isn't part of the contract this test pins.
    """

    output: str


@dataclass
class _StubAgent:
    """Stand-in for ``pydantic_ai.Agent``.

    Records every ``run_sync`` invocation so tests can assert the
    prompt argument arrived intact. ``response`` is what ``run_sync``
    returns; ``raise_on_run`` lets a test swap in an exception path.
    """

    response: str = "hello from tab"
    raise_on_run: BaseException | None = None
    runs: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)

    def run_sync(self, *args: Any, **kwargs: Any) -> _StubResult:
        self.runs.append((args, kwargs))
        if self.raise_on_run is not None:
            raise self.raise_on_run
        return _StubResult(output=self.response)


@dataclass
class _CompileRecorder:
    """Wrap a stub agent and capture the kwargs passed to compile."""

    agent: _StubAgent
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **kwargs: Any) -> _StubAgent:
        self.calls.append(kwargs)
        return self.agent


@pytest.fixture
def runner() -> CliRunner:
    # Click 8.3+ keeps stderr separate from stdout by default — the
    # legacy ``mix_stderr=False`` toggle is gone. ``result.stderr`` and
    # ``result.stdout`` are independent buffers, which is exactly what
    # the readable-error tests need.
    return CliRunner()


def _patch_compile(
    monkeypatch: pytest.MonkeyPatch, agent: _StubAgent
) -> _CompileRecorder:
    """Replace ``compile_tab_agent`` everywhere ``tab ask`` will look it up."""
    recorder = _CompileRecorder(agent=agent)
    # The CLI imports ``compile_tab_agent`` lazily inside the command
    # body, so patching the source module is the binding the import
    # actually resolves. Patching ``tab_cli.cli.compile_tab_agent``
    # would miss because the name doesn't live there until the command
    # runs.
    monkeypatch.setattr(
        "tab_cli.personality.compile_tab_agent", recorder, raising=True
    )
    return recorder


def test_ask_prints_response_and_exits_zero(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _StubAgent(response="hi there")
    _patch_compile(monkeypatch, agent)

    result = runner.invoke(app, ["ask", "hello"])

    assert result.exit_code == 0, result.stderr
    assert "hi there" in result.stdout
    # The prompt must have round-tripped through `run_sync`.
    assert agent.runs, "agent.run_sync was never called"
    first_call_args, _ = agent.runs[0]
    assert first_call_args[0] == "hello"


def test_ask_round_trips_prompt_through_compile_tab_agent(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The acceptance test the task spells out: prompt must reach the agent.

    We assert both halves: ``compile_tab_agent`` was called exactly
    once (one-shot, not a loop), and the prompt that came back out of
    ``run_sync`` is the same string the user typed.
    """
    agent = _StubAgent(response="ok")
    recorder = _patch_compile(monkeypatch, agent)

    result = runner.invoke(app, ["ask", "what is 2 + 2?"])

    assert result.exit_code == 0, result.stderr
    assert len(recorder.calls) == 1, "compile_tab_agent should be called once per ask"
    assert len(agent.runs) == 1, "agent.run_sync should be called once per ask"
    args, _ = agent.runs[0]
    assert args[0] == "what is 2 + 2?"


def test_ask_passes_model_option_through_to_compile(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _StubAgent()
    recorder = _patch_compile(monkeypatch, agent)

    result = runner.invoke(
        app, ["ask", "--model", "anthropic:claude-sonnet-4", "hello"]
    )

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0].get("model") == "anthropic:claude-sonnet-4"


def test_ask_default_model_is_none(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --model, the CLI must pass ``model=None`` to the compiler.

    ``None`` defers model resolution to pydantic-ai, mirroring
    ``compile_tab_agent``'s default. A bare ``tab ask`` should not
    silently inject a different default and surprise the caller.
    """
    agent = _StubAgent()
    recorder = _patch_compile(monkeypatch, agent)

    result = runner.invoke(app, ["ask", "hello"])

    assert result.exit_code == 0, result.stderr
    assert recorder.calls[0].get("model") is None


def test_ask_surfaces_runtime_errors_as_readable_message(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Network/API failures must collapse to one stderr line plus exit 1.

    The CLI is a shell-out target; tracebacks would make `tab ask ...
    || fallback` ugly. The contract: stderr contains a `tab: <reason>`
    line, exit code is non-zero, stdout is empty (no half-printed
    response).
    """
    boom = RuntimeError("API key missing")
    agent = _StubAgent(raise_on_run=boom)
    _patch_compile(monkeypatch, agent)

    result = runner.invoke(app, ["ask", "hello"])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "API key missing" in result.stderr
    assert result.stdout.strip() == ""


def test_ask_surfaces_compile_failures(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure inside ``compile_tab_agent`` must also collapse cleanly.

    Same shape as a runtime failure: the user shouldn't have to read a
    traceback to learn that the personality file is missing or
    malformed.
    """

    def _boom(**_: Any) -> Any:
        raise FileNotFoundError("plugins/tab/agents/tab.md is missing")

    monkeypatch.setattr("tab_cli.personality.compile_tab_agent", _boom, raising=True)

    result = runner.invoke(app, ["ask", "hello"])

    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "tab.md is missing" in result.stderr


def test_ask_help_lists_command_and_model_flag(runner: CliRunner) -> None:
    """The `--help` surface is part of the contract for shell-out users."""
    top = runner.invoke(app, ["--help"])
    assert top.exit_code == 0
    assert "ask" in top.stdout

    sub = runner.invoke(app, ["ask", "--help"])
    assert sub.exit_code == 0
    assert "--model" in sub.stdout
    assert "PROMPT" in sub.stdout.upper()
