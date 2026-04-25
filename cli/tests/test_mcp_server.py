"""Tests for ``tab mcp`` — the MCP server mode.

Two layers of coverage:

- Server level: build the FastMCP server with a stubbed
  ``compile_tab_agent`` and drive it through FastMCP's in-memory
  ``Client`` transport. Both registered tools (``ask_tab`` and
  ``search_memory``) have to be callable end-to-end and return what
  the contract pins.
- Typer level: ``tab mcp --help`` lists the command and the dial flags,
  and ``tab mcp`` patched at ``run_server`` validates dial inputs the
  same way ``tab ask`` does — out-of-range values exit non-zero with
  the contract'd one-line error.

The in-memory client transport is the linchpin of the end-to-end test.
FastMCP's ``Client`` accepts a ``FastMCP`` instance directly, runs the
JSON-RPC handshake in process, and returns ``CallToolResult`` objects
with the tool's structured output on ``.data``. No subprocess, no
stdio plumbing, no flaky timing — just a real MCP round-trip the test
can assert on.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from typer.testing import CliRunner

from tab_cli.cli import app
from tab_cli.mcp_server import build_server, run_server
from tab_cli.personality import TabSettings


# --------------------------------------------------------------- fakes


@dataclass
class _StubResult:
    """Stand-in for ``pydantic_ai.AgentRunResult``. Only ``.output`` is read."""

    output: str


@dataclass
class _StubAgent:
    """Stand-in for ``pydantic_ai.Agent`` for the MCP server's needs.

    Records each ``run_sync`` call so tests can assert that the prompt
    arrived intact and the per-call ``model`` override (if any) made it
    into the compile call. ``response`` is what ``run_sync`` returns;
    ``raise_on_run`` lets a test exercise the error-surface path.
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


# --------------------------------------------------------------- helpers


def _run(coro: Any) -> Any:
    """Run an async coroutine to completion in a fresh event loop.

    pytest-asyncio isn't on the dev deps and the rest of the suite is
    sync — keeping a tiny ``asyncio.run`` helper avoids pulling in a
    new test plugin just to exercise FastMCP's async client.
    """
    return asyncio.run(coro)


# ------------------------------------------------------- server-level tests


def test_build_server_registers_both_tools() -> None:
    """The two contracted tools must be exposed by name on the server."""
    agent = _StubAgent()
    recorder = _CompileRecorder(agent=agent)
    server = build_server(compile_agent=recorder)

    async def _list() -> list[str]:
        from fastmcp import Client

        async with Client(server) as client:
            tools = await client.list_tools()
            return [t.name for t in tools]

    names = _run(_list())
    assert "ask_tab" in names
    assert "search_memory" in names


def test_ask_tab_round_trips_prompt_and_uses_compile_tab_agent() -> None:
    """A client call to ``ask_tab`` reaches the agent and returns ``output``."""
    agent = _StubAgent(response="hi there")
    recorder = _CompileRecorder(agent=agent)
    server = build_server(compile_agent=recorder)

    async def _call() -> Any:
        from fastmcp import Client

        async with Client(server) as client:
            return await client.call_tool("ask_tab", {"prompt": "hello"})

    result = _run(_call())
    # FastMCP unmarshals the tool's typed return into ``.data`` for
    # primitive return types — a string in our case.
    assert result.data == "hi there"
    # The compile-and-run path actually fired.
    assert len(recorder.calls) == 1
    assert len(agent.runs) == 1
    args, _ = agent.runs[0]
    assert args[0] == "hello"


def test_ask_tab_passes_settings_through_to_compile() -> None:
    """The server's resolved settings reach every compile call.

    Acceptance criterion: the server reuses ``compile_tab_agent``
    rather than duplicating personality logic. Asserting the settings
    object lands in ``compile_tab_agent`` pins that wiring.
    """
    agent = _StubAgent()
    recorder = _CompileRecorder(agent=agent)
    settings = TabSettings(humor=90, directness=20)
    server = build_server(settings=settings, compile_agent=recorder)

    async def _call() -> None:
        from fastmcp import Client

        async with Client(server) as client:
            await client.call_tool("ask_tab", {"prompt": "x"})

    _run(_call())
    passed = recorder.calls[0]["settings"]
    assert passed.humor == 90
    assert passed.directness == 20
    # Other dials fall through to TabSettings defaults.
    assert passed.warmth == 70


def test_ask_tab_uses_server_default_model_when_call_omits_it() -> None:
    """The ``--model`` flag at server start becomes the default per-call model."""
    agent = _StubAgent()
    recorder = _CompileRecorder(agent=agent)
    server = build_server(model="anthropic:claude-sonnet-4", compile_agent=recorder)

    async def _call() -> None:
        from fastmcp import Client

        async with Client(server) as client:
            await client.call_tool("ask_tab", {"prompt": "x"})

    _run(_call())
    assert recorder.calls[0].get("model") == "anthropic:claude-sonnet-4"


def test_ask_tab_per_call_model_overrides_server_default() -> None:
    """A ``model`` argument on the tool call wins over the server default."""
    agent = _StubAgent()
    recorder = _CompileRecorder(agent=agent)
    server = build_server(model="anthropic:claude-sonnet-4", compile_agent=recorder)

    async def _call() -> None:
        from fastmcp import Client

        async with Client(server) as client:
            await client.call_tool(
                "ask_tab",
                {"prompt": "x", "model": "openai:gpt-4o"},
            )

    _run(_call())
    assert recorder.calls[0].get("model") == "openai:gpt-4o"


def test_ask_tab_default_model_is_none() -> None:
    """Without a server default and no per-call override, model is None."""
    agent = _StubAgent()
    recorder = _CompileRecorder(agent=agent)
    server = build_server(compile_agent=recorder)

    async def _call() -> None:
        from fastmcp import Client

        async with Client(server) as client:
            await client.call_tool("ask_tab", {"prompt": "x"})

    _run(_call())
    assert recorder.calls[0].get("model") is None


def test_search_memory_returns_v0_stub() -> None:
    """``search_memory`` returns the documented v0 placeholder."""
    server = build_server(compile_agent=_CompileRecorder(agent=_StubAgent()))

    async def _call() -> Any:
        from fastmcp import Client

        async with Client(server) as client:
            return await client.call_tool(
                "search_memory", {"query": "anything"}
            )

    result = _run(_call())
    # ``data`` is the typed return — list[str] in our case.
    assert isinstance(result.data, list)
    assert len(result.data) == 1
    assert "v0 placeholder" in result.data[0]


def test_ask_tab_propagates_agent_errors() -> None:
    """A failure inside ``run_sync`` becomes a tool-call error.

    FastMCP marshals exceptions raised inside a tool into the
    ``CallToolResult.is_error`` flag — the client doesn't see a Python
    traceback, but the error state is observable.
    """
    boom = RuntimeError("API key missing")
    agent = _StubAgent(raise_on_run=boom)
    recorder = _CompileRecorder(agent=agent)
    server = build_server(compile_agent=recorder)

    async def _call() -> Any:
        from fastmcp import Client
        from fastmcp.exceptions import ToolError

        async with Client(server) as client:
            try:
                return await client.call_tool("ask_tab", {"prompt": "hello"})
            except ToolError as exc:
                return exc

    result = _run(_call())
    # Either the result carries an error flag, or the client raised a
    # ToolError — both are acceptable shapes for "the tool failed."
    if hasattr(result, "is_error"):
        assert result.is_error is True
    else:
        assert "API key missing" in str(result) or "tab" in str(result).lower()


# -------------------------------------------------------- typer-level tests


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_mcp_help_lists_command(runner: CliRunner) -> None:
    """The top-level help must list ``mcp`` so users can discover it."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "mcp" in result.stdout


def test_mcp_subcommand_help_lists_dial_flags(runner: CliRunner) -> None:
    """``tab mcp --help`` must expose the dial flags + ``--model``."""
    result = runner.invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0
    for dial in ("--humor", "--directness", "--warmth", "--autonomy", "--verbosity"):
        assert dial in result.stdout, f"{dial} missing from `tab mcp --help`"
    assert "--model" in result.stdout


def test_mcp_out_of_range_dial_exits_non_zero(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same dial-validation contract as ``tab ask``."""
    # Patch run_server so a passing case wouldn't try to bind stdio in
    # the test process. The out-of-range path must fail before even
    # getting there, but the patch keeps a regression honest.
    monkeypatch.setattr(
        "tab_cli.mcp_server.run_server", lambda **_: None, raising=True
    )

    result = runner.invoke(app, ["mcp", "--humor", "150"])
    assert result.exit_code != 0
    assert "humor must be 0-100, got 150" in result.stderr


def test_mcp_invokes_run_server_with_resolved_settings(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """The Typer wrapper resolves settings + model and hands them to the server."""
    # Isolate XDG so a real user config can't leak into the assertion.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "tab").mkdir()

    captured: dict[str, Any] = {}

    def _fake_run_server(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        "tab_cli.mcp_server.run_server", _fake_run_server, raising=True
    )

    result = runner.invoke(
        app,
        [
            "mcp",
            "--model",
            "anthropic:claude-sonnet-4",
            "--humor",
            "10",
        ],
    )
    assert result.exit_code == 0, result.stderr
    assert captured.get("model") == "anthropic:claude-sonnet-4"
    settings = captured.get("settings")
    assert settings is not None
    assert settings.humor == 10
    # Untouched dials use TabSettings defaults.
    assert settings.directness == 80


def test_mcp_collapses_runtime_errors_to_readable_stderr(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failures from the server start path collapse to ``tab: <reason>``."""

    def _boom(**_: Any) -> None:
        raise RuntimeError("port already in use")

    monkeypatch.setattr("tab_cli.mcp_server.run_server", _boom, raising=True)

    result = runner.invoke(app, ["mcp"])
    assert result.exit_code != 0
    assert "tab:" in result.stderr
    assert "port already in use" in result.stderr


# ------------------------------------------------------- run_server smoke


def test_run_server_calls_fastmcp_run_with_stdio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``run_server`` builds a server and runs it with the stdio transport.

    We can't bind real stdio in a unit test, so we patch the FastMCP
    instance's ``run`` to record the call. Asserting ``transport='stdio'``
    pins the contract — Claude Code et al. spawn ``tab mcp`` and talk
    JSON-RPC over the subprocess's std streams.
    """
    captured: dict[str, Any] = {}

    real_build = build_server

    def _fake_build(**kwargs: Any) -> Any:
        server = real_build(**kwargs)

        def _fake_run(*args: Any, **run_kwargs: Any) -> None:
            captured["args"] = args
            captured["kwargs"] = run_kwargs

        server.run = _fake_run  # type: ignore[method-assign]
        return server

    monkeypatch.setattr("tab_cli.mcp_server.build_server", _fake_build, raising=True)

    run_server(settings=TabSettings(humor=42))

    # ``transport`` is passed positionally or as a kwarg depending on
    # the FastMCP version — accept either shape.
    assert (
        ("stdio" in captured.get("args", ()))
        or captured.get("kwargs", {}).get("transport") == "stdio"
    )
