"""Tests for :mod:`tab_cli.web_search` — the teach skill's web tool.

The contract pinned here is narrow but load-bearing. The teach SKILL
body trusts the tool to either return Exa-shaped results
(``[{title, url, snippet}]``) or to degrade quietly when search isn't
configured. A regression in either direction breaks the SKILL's
research phase silently — the model would either drop the result
shape it expects to consume, or surface a transport exception that
the SKILL doesn't know how to recover from.

The HTTP path is exercised via a fake :class:`_HttpClientLike` rather
than ``responses``/``vcr`` because the surface area is tiny (one
``post``) and a stub keeps the suite hermetic and dep-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from tab_cli.web_search import (
    EXA_SEARCH_URL,
    build_web_search_tool,
    default_web_search,
)


@dataclass
class _FakeResponse:
    """Stand-in for ``httpx.Response``."""

    payload: Any
    status: int = 200

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


@dataclass
class _FakeClient:
    """Records every ``post`` and returns canned responses."""

    response: _FakeResponse | Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    closed: bool = False

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> _FakeResponse:
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is None:
            return _FakeResponse(payload={"results": []})
        return self.response

    def close(self) -> None:
        self.closed = True


# ----------------------------------------------------- happy-path search


def test_web_search_returns_results_with_expected_shape() -> None:
    """A real-shaped Exa payload must round-trip into title/url/snippet rows."""
    payload = {
        "results": [
            {
                "title": "Event Sourcing — Martin Fowler",
                "url": "https://martinfowler.com/eaaDev/EventSourcing.html",
                "text": "Capture all changes to an application state as a sequence of events.",
            },
            {
                "title": "Versioning in an event-sourced system",
                "url": "https://leanpub.com/esversioning",
                "text": "Schema evolution under append-only events is a real concern...",
            },
        ]
    }
    client = _FakeClient(response=_FakeResponse(payload=payload))

    web_search = build_web_search_tool(api_key="exa-test-key", http_client=client)
    out = web_search("event sourcing trade-offs production")

    assert isinstance(out, list)
    assert len(out) == 2
    first = out[0]
    assert set(first.keys()) == {"title", "url", "snippet"}
    assert "Martin Fowler" in first["title"]
    assert first["url"].startswith("https://")
    assert "sequence of events" in first["snippet"]


def test_web_search_calls_exa_endpoint_with_api_key_header() -> None:
    """Acceptance signal: the request goes to Exa with the key in headers."""
    client = _FakeClient(response=_FakeResponse(payload={"results": []}))

    web_search = build_web_search_tool(api_key="exa-test-key", http_client=client)
    web_search("agent loops")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["url"] == EXA_SEARCH_URL
    # API key in the header — never in the URL or body, so a leak via
    # transcripts can't surface it from a logged URL string.
    assert call["headers"]["x-api-key"] == "exa-test-key"
    assert call["json"]["query"] == "agent loops"
    # We default to a reasonable result cap; the body must include it.
    assert isinstance(call["json"]["numResults"], int)
    assert call["json"]["numResults"] > 0


def test_web_search_falls_back_to_highlights_when_text_missing() -> None:
    """Legacy Exa payloads without ``text`` should still produce a snippet."""
    payload = {
        "results": [
            {
                "title": "RAG patterns",
                "url": "https://example.com/rag",
                "highlights": ["Retrieval-Augmented Generation", "vector search"],
            }
        ]
    }
    client = _FakeClient(response=_FakeResponse(payload=payload))

    web_search = build_web_search_tool(api_key="exa-key", http_client=client)
    out = web_search("RAG")

    assert len(out) == 1
    assert "Retrieval-Augmented" in out[0]["snippet"]
    assert "vector search" in out[0]["snippet"]


def test_web_search_trims_long_snippets() -> None:
    """Very long ``text`` payloads get trimmed so history stays light."""
    long_text = "alpha beta gamma " * 200  # well over the trim window
    payload = {
        "results": [
            {
                "title": "Long article",
                "url": "https://example.com/long",
                "text": long_text,
            }
        ]
    }
    client = _FakeClient(response=_FakeResponse(payload=payload))

    web_search = build_web_search_tool(api_key="key", http_client=client)
    out = web_search("topic")

    assert len(out) == 1
    snippet = out[0]["snippet"]
    assert snippet.endswith("...")
    assert len(snippet) < len(long_text)


# ----------------------------------------------------- degrade paths


def test_web_search_no_api_key_returns_explanatory_no_op() -> None:
    """SKILL.md says the skill works without web search — the tool reflects that.

    The model should see one ``[web_search unavailable]`` entry rather
    than an exception. The teach SKILL body's "fall back to existing
    knowledge" branch can read the entry and behave accordingly.
    """
    web_search = build_web_search_tool(api_key=None)
    out = web_search("anything")

    assert len(out) == 1
    assert "unavailable" in out[0]["title"].lower()
    assert "EXA_API_KEY" in out[0]["snippet"]
    assert out[0]["url"] == ""


def test_web_search_empty_api_key_also_no_ops() -> None:
    """Empty-string API keys are treated as unset, not as authenticated."""
    web_search = build_web_search_tool(api_key="")
    out = web_search("anything")

    assert len(out) == 1
    assert "unavailable" in out[0]["title"].lower()


def test_web_search_blank_query_returns_empty_list() -> None:
    """A blank query is the model's bug; refuse it without burning a request."""
    client = _FakeClient(response=_FakeResponse(payload={"results": []}))

    web_search = build_web_search_tool(api_key="key", http_client=client)
    assert web_search("") == []
    assert web_search("   ") == []
    # No HTTP attempt for blank queries.
    assert client.calls == []


def test_web_search_http_error_is_caught_and_described() -> None:
    """Network errors collapse to a structured "this didn't work" entry."""
    client = _FakeClient(response=ConnectionError("connection refused"))

    web_search = build_web_search_tool(api_key="key", http_client=client)
    out = web_search("topic")

    assert len(out) == 1
    assert out[0]["title"] == "[web_search error]"
    assert "ConnectionError" in out[0]["snippet"]
    assert "connection refused" in out[0]["snippet"]


def test_web_search_drops_non_dict_result_items() -> None:
    """Defensive: non-dict items in ``results`` shouldn't break the tool."""
    payload = {
        "results": [
            "garbage",  # ignored
            {"title": "ok", "url": "https://ok", "text": "fine"},
            None,  # ignored
        ]
    }
    client = _FakeClient(response=_FakeResponse(payload=payload))

    web_search = build_web_search_tool(api_key="key", http_client=client)
    out = web_search("topic")

    assert len(out) == 1
    assert out[0]["title"] == "ok"


def test_web_search_handles_non_dict_payload() -> None:
    """If the upstream returns a list/string at the top level, we shrug."""
    client = _FakeClient(response=_FakeResponse(payload=["not", "a", "dict"]))

    web_search = build_web_search_tool(api_key="key", http_client=client)
    out = web_search("topic")

    assert out == []


# ----------------------------------------------------- env-driven default


def test_default_web_search_reads_exa_api_key_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``default_web_search`` resolves the key from the environment."""
    monkeypatch.setenv("EXA_API_KEY", "from-env-key")

    web_search = default_web_search()

    # Without a fake client we'd hit the real network — the easy
    # observation is that this path doesn't no-op on the missing-key
    # branch, which we already proved with explicit tests above.
    # Confirm the no-op snippet text is NOT present, instead of trying
    # to actually search.
    monkeypatch.delenv("EXA_API_KEY")
    no_key = default_web_search()("topic")
    assert "EXA_API_KEY" in no_key[0]["snippet"]

    # And reverse: with the env back in place, it resolves a tool that
    # would attempt the network rather than no-op.
    monkeypatch.setenv("EXA_API_KEY", "from-env-key")
    # Inspect via call: mock out httpx.Client to a faux client that
    # records its kwargs, prove the api_key reaches the request.
    captured: list[dict[str, Any]] = []

    class _Cap:
        def __init__(self, **kwargs: Any) -> None:
            captured.append({"init": kwargs})

        def post(self, url: str, **kwargs: Any) -> _FakeResponse:
            captured.append({"url": url, **kwargs})
            return _FakeResponse(payload={"results": []})

        def close(self) -> None:
            captured.append({"closed": True})

    monkeypatch.setattr("httpx.Client", _Cap)

    default_web_search()("a query")

    posts = [c for c in captured if "url" in c]
    assert posts, "expected a real HTTP attempt when EXA_API_KEY is set"
    assert posts[0]["headers"]["x-api-key"] == "from-env-key"
