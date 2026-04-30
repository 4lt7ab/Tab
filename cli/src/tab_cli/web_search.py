"""WebSearch tool wired into the teach skill's pydantic-ai agent.

The teach skill is the first v0 personality port that needs a tool.
Its SKILL.md research phase wants Exa-shaped queries — title, URL,
snippet — to synthesise the landscape of thinking around a topic. The
tool here is the bridge: a plain Python callable (the shape pydantic-ai
prefers for trivial tools) that the teach agent can invoke.

Design choices that aren't obvious from the call site:

- **Callable, not :class:`pydantic_ai.Tool`.** pydantic-ai accepts a
  bare function in ``Agent(tools=...)`` and infers the schema from the
  signature + docstring. The Tool wrapper only earns its keep when the
  caller needs to override the inferred name, prepare hooks, or
  retries. We don't, so we keep the surface area narrow.
- **Direct HTTP, no MCP.** The CLI process has no MCP runtime. The KB
  decision (``01KQ2YKTWGXQKYZZS56Y29KT0C``) calls out exa as one option
  among several — picking the direct HTTP API skips the broker, fits
  pydantic-ai's tool model cleanly, and keeps deps zero (httpx is
  already a transitive). The MCP path can land as a follow-up if a
  caller wants pooled results across tools.
- **Graceful degrade when unconfigured.** The teach SKILL.md says the
  skill works without web search ("teaches only from existing
  knowledge"). Missing ``EXA_API_KEY`` is a configuration condition,
  not an error — the tool returns an empty list and a one-line
  explanatory snippet so the model can decide to fall through to its
  own knowledge instead of failing the turn.
- **Builder, not module-level state.** :func:`build_web_search_tool`
  takes the API key + http client as arguments so tests can pin a fake
  client without monkey-patching ``os.environ``. The default
  :func:`default_web_search` reads ``EXA_API_KEY`` at call time so the
  config picture is also "do nothing ahead of time."
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable


# Exa's REST endpoint for /search. Documented at https://docs.exa.ai/.
# Pinned here rather than parameterised — switching providers is a
# deliberate change, not a runtime knob, and a constant keeps the call
# site readable.
EXA_SEARCH_URL = "https://api.exa.ai/search"


class _HttpResponseLike(Protocol):
    """Minimal slice of ``httpx.Response`` the tool actually uses.

    Pinning the surface area as a Protocol keeps the test fakes honest
    — a regression that starts touching ``response.headers`` will fail
    to type-check rather than silently coupling to a wider API.
    """

    def json(self) -> Any: ...

    def raise_for_status(self) -> Any: ...


class _HttpClientLike(Protocol):
    """Minimal slice of ``httpx.Client`` the tool actually uses."""

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = ...,
        headers: dict[str, str] | None = ...,
        timeout: float | None = ...,
    ) -> _HttpResponseLike: ...


# Per-call timeout for the HTTP search. Long enough for a realistic
# upstream search round-trip on a flaky link, short enough that the
# teach agent's user-facing turn doesn't pause for an obvious eternity
# while one tool call hangs. Tuned by feel, not measurement — the cost
# of a wrong value is one model retry, not data loss.
_DEFAULT_TIMEOUT_SECONDS = 15.0


# Cap on results returned to the model. The teach SKILL.md research
# phase typically wants 3-5 best sources; ten is plenty for the
# synthesis to draw from without burning a tool-call's budget on
# noise.
_DEFAULT_NUM_RESULTS = 10


def _trim(text: str, *, limit: int = 480) -> str:
    """Trim a snippet to a sensible upper bound.

    Exa's text/highlight payloads can be hundreds of characters; the
    teaching-conversation context is the constrained resource, not the
    network call. Trimming on the way out keeps history light without
    losing the useful kernel of each result.
    """
    if len(text) <= limit:
        return text
    # Word-boundary trim if there's a space inside the last ~10% of the
    # window — keeps the snippet readable rather than ending mid-token.
    cut = text[:limit]
    last_space = cut.rfind(" ", limit - 60, limit)
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip() + "..."


def build_web_search_tool(
    *,
    api_key: str | None,
    http_client: _HttpClientLike | None = None,
    num_results: int = _DEFAULT_NUM_RESULTS,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> Callable[[str], list[dict[str, str]]]:
    """Return a ``web_search(query)`` callable wired with the given backend.

    The returned callable is what pydantic-ai registers as a tool. Its
    docstring and signature are what the model sees, so they describe
    the tool's *behaviour* and not the runner — "search the web" is
    what the teach agent decides to invoke.

    Behaviour:

    - When ``api_key`` is ``None`` or empty, the returned callable is a
      no-op that always returns a single explanatory entry. The teach
      SKILL.md treats web search as optional and tells the agent to
      fall through to existing knowledge when the tool is unavailable;
      this short-circuit is the wire-level expression of that
      fallback. The teach agent sees a concrete answer instead of a
      tool error and can adjust the conversation accordingly.
    - When ``api_key`` is set but ``http_client`` is ``None``, an
      :class:`httpx.Client` is constructed at call time. Tests inject a
      fake :class:`_HttpClientLike` to avoid the network.
    - HTTP errors are caught and surfaced as a single-entry result with
      ``snippet`` describing the failure. The teach agent should never
      see an unhandled exception — the model's recovery story is
      "search came back empty, fall back."
    """

    def web_search(query: str) -> list[dict[str, str]]:
        """Search the web for the given query.

        Returns a list of search results, each with ``title``, ``url``,
        and ``snippet`` keys. The list may be empty when the search
        backend is unavailable or returns no matches. Always check
        results before quoting them — this is a research tool, not
        ground truth.

        Args:
            query: A natural-language search phrase. Concrete and
                specific queries return better results than broad ones
                — "event sourcing trade-offs production" beats "event
                sourcing".
        """
        if not query.strip():
            return []

        if not api_key:
            return [
                {
                    "title": "[web_search unavailable]",
                    "url": "",
                    "snippet": (
                        "EXA_API_KEY is not set in the environment, so "
                        "web_search is running in no-op mode. Fall back to "
                        "existing knowledge for this turn; let the user know "
                        "the research pass was skipped."
                    ),
                }
            ]

        try:
            client = http_client
            close_after = False
            if client is None:
                # Local import: keeps ``httpx`` out of the import path
                # for tests that pass a stub client. The real
                # personality CLI ships httpx as a transitive of
                # pydantic-ai so the import is free at session warm-up
                # time, but skipping it keeps test isolation tidy.
                import httpx

                client = httpx.Client(timeout=timeout_seconds)
                close_after = True

            try:
                response = client.post(
                    EXA_SEARCH_URL,
                    json={
                        "query": query,
                        "numResults": num_results,
                        "contents": {
                            # ``text`` gives a long passage; we
                            # downscope on the way out so the model
                            # doesn't drown in raw HTML extracts.
                            "text": True,
                        },
                    },
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            finally:
                if close_after:
                    # ``httpx.Client`` exposes ``.close()`` but the
                    # Protocol doesn't, so fall back to ``getattr`` to
                    # keep the type contract narrow.
                    closer = getattr(client, "close", None)
                    if callable(closer):
                        closer()
        except Exception as exc:  # noqa: BLE001 — collapse to tool result
            # The model's recovery story — "fall back to existing
            # knowledge" — is better served by a structured "this
            # didn't work" entry than by a tool exception that would
            # blow the turn. The error type is recorded in the snippet
            # so debugging from a transcript is still possible.
            return [
                {
                    "title": "[web_search error]",
                    "url": "",
                    "snippet": f"web_search failed: {type(exc).__name__}: {exc}",
                }
            ]

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return []

        out: list[dict[str, str]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            # Exa puts the long-form passage on ``text``; some legacy
            # payloads use ``snippet`` or ``highlights``. Take whichever
            # is non-empty, prefer ``text`` for the meatiest sample.
            snippet = (
                item.get("text")
                or item.get("snippet")
                or _join_highlights(item.get("highlights"))
                or ""
            )
            snippet = _trim(str(snippet).strip())
            if not (title or url or snippet):
                continue
            out.append({"title": title, "url": url, "snippet": snippet})
        return out

    return web_search


def _join_highlights(highlights: Any) -> str:
    """Flatten Exa's ``highlights`` array into one snippet-shaped string."""
    if not isinstance(highlights, list):
        return ""
    parts = [str(h).strip() for h in highlights if str(h).strip()]
    return " ... ".join(parts)


def default_web_search() -> Callable[[str], list[dict[str, str]]]:
    """Build the tool with environment-driven configuration.

    Reads ``EXA_API_KEY`` at call time. When unset, the returned
    callable still works — it just returns the explanatory no-op
    entry. This is the form the chat REPL's grimoire-routed dispatch
    wraps when it routes to the ``teach`` skill.
    """
    return build_web_search_tool(api_key=os.environ.get("EXA_API_KEY"))
