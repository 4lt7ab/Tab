"""MCP server mode for the Tab CLI.

``tab mcp`` runs the CLI as an MCP server on stdio so MCP-aware hosts
(Claude Code, other agentic clients) can call into Tab as a long-lived
subprocess. The surface is two named tools — not the open-ended chat
REPL — per the Tab CLI decision (KB doc 01KQ2YKTWGXQKYZZS56Y29KT0C):

- ``ask_tab(prompt, model?)`` — one-shot wrap around the same agent
  the ``tab ask`` subcommand drives. Compile the personality, run a
  single turn, return the response string.
- ``search_memory(query)`` — v0 placeholder. The decision keeps the
  KB inside the tab-for-projects MCP and grimoire as a routing layer;
  CLI-side memory search isn't in scope yet, but the surface is
  reserved so future work can fill it without breaking clients.

The server is built around a factory (:func:`build_server`) so tests
can drive it through FastMCP's in-memory ``Client`` transport — no
subprocess plumbing, no real model provider, no flaky stdio. The
Typer-level ``tab mcp`` command calls :func:`run_server`, which is the
thin wrapper that takes settings + model and runs stdio to completion.

Personality settings layer the same way as every other Tab CLI surface
(flag > config > tab.md defaults) — that resolution happens upstream
in ``cli.py``; this module accepts the resolved :class:`TabSettings`
and reuses :func:`compile_tab_agent` so the personality story stays
single-sourced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from tab_cli.personality import TabSettings

if TYPE_CHECKING:  # pragma: no cover — typing-only imports
    from fastmcp import FastMCP


# The v0 memory-search stub message. Surfaced both as the tool's return
# value and as a sentinel callers can match on if they want to detect
# "this server doesn't actually search memory yet" without parsing prose.
_SEARCH_MEMORY_STUB = (
    "search_memory is a v0 placeholder. The Tab CLI does not yet expose "
    "memory search; the tab-for-projects MCP owns the project KB."
)


def _default_compile() -> Callable[..., Any]:
    """Return the real ``compile_tab_agent`` callable.

    Pulled behind a tiny indirection so :func:`build_server` can accept
    an injected compiler in tests without import-time coupling to the
    personality module's pydantic-ai pull-in.
    """
    from tab_cli.personality import compile_tab_agent

    return compile_tab_agent


def build_server(
    *,
    settings: TabSettings | None = None,
    model: str | None = None,
    compile_agent: Callable[..., Any] | None = None,
    name: str = "tab",
) -> FastMCP:
    """Build a FastMCP server with the two Tab tools registered.

    Args:
        settings: Personality dial values. ``None`` uses
            :class:`TabSettings`'s field defaults (which mirror the
            tab.md Settings table). The same settings are reused for
            every ``ask_tab`` call within a server lifetime — recompile
            by restarting the server.
        model: Default pydantic-ai model name in ``provider:name``
            form. Calls to ``ask_tab`` may override this per-call via
            their own ``model`` argument; otherwise this value is used.
        compile_agent: Test seam. Inject a stand-in for
            :func:`compile_tab_agent` to avoid touching real providers.
            Production callers leave this ``None``.
        name: Server name advertised over MCP. Defaults to ``"tab"`` —
            what Claude Code et al. will see in their MCP tool listing.

    Returns:
        A configured :class:`fastmcp.FastMCP` server with ``ask_tab``
        and ``search_memory`` registered. The caller is responsible
        for choosing a transport (``mcp.run("stdio")`` for the CLI).
    """
    # Lazy import: keeps ``tab --help`` and unrelated subcommands free
    # of FastMCP's import cost. Same instinct as the personality and
    # chat lazy imports in ``cli.py``.
    from fastmcp import FastMCP

    active_settings = settings if settings is not None else TabSettings()
    compile_fn = compile_agent if compile_agent is not None else _default_compile()
    # Captured under a distinct name so the per-call ``model`` argument
    # in ``ask_tab`` doesn't shadow it — the closure reads
    # ``model_default`` unambiguously.
    model_default = model

    mcp: FastMCP = FastMCP(name=name)

    @mcp.tool(
        name="ask_tab",
        description=(
            "Send a one-shot prompt to the Tab persona and return the "
            "response as a string. Optional ``model`` overrides the "
            "server's default pydantic-ai model name (e.g. "
            "``anthropic:claude-sonnet-4``)."
        ),
    )
    def ask_tab(prompt: str, model: str | None = None) -> str:
        """Run a single Tab turn and return the response text.

        Mirrors ``tab ask`` exactly: compile the personality, run one
        turn, return ``result.output``. Personality settings come from
        the server's resolved :class:`TabSettings`; per-call overrides
        of dials are deliberately not exposed — clients that want to
        change Tab's voice should restart the server with new flags
        (or use ``tab ask`` directly), keeping the MCP surface narrow.
        """
        effective_model = model if model is not None else model_default
        agent = compile_fn(settings=active_settings, model=effective_model)
        result = agent.run_sync(prompt)
        return result.output

    @mcp.tool(
        name="search_memory",
        description=(
            "v0 placeholder for Tab CLI memory search. Returns a stub "
            "message; the project KB lives in the tab-for-projects MCP."
        ),
    )
    def search_memory(query: str) -> list[str]:
        """Return the documented v0 stub.

        The decision pins this surface as reserved — clients can call
        it without erroring, and a future ticket can swap the body for
        a real memory implementation without breaking schemas. ``query``
        is accepted (and ignored) so the tool's signature is stable
        across the v0 → v1 transition.
        """
        # ``query`` is intentionally unused at v0. Reference it once so
        # static-analysis treats the parameter as live, which keeps the
        # MCP-advertised schema honest about what callers must send.
        del query
        return [_SEARCH_MEMORY_STUB]

    return mcp


def run_server(
    *,
    settings: TabSettings | None = None,
    model: str | None = None,
) -> None:
    """Run the Tab MCP server on stdio until the client disconnects.

    The standard transport for Claude Code subprocess MCPs is stdio —
    the client spawns ``tab mcp``, talks JSON-RPC over stdin/stdout,
    and reaps the process on shutdown. We don't expose HTTP or SSE at
    v0; that's a deferred surface decision.

    Errors during build or run propagate so the Typer wrapper in
    ``cli.py`` can collapse them to the standard ``tab: <reason>``
    one-line stderr message.
    """
    mcp = build_server(settings=settings, model=model)
    mcp.run(transport="stdio", show_banner=False)
