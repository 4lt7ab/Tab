"""Compile `plugins/tab/agents/tab.md` into a pydantic-ai `Agent`.

The `tab.md` file ships the canonical Tab personality: identity, voice,
constraints, and a Settings table (Humor, Directness, Warmth, Autonomy,
Verbosity, each 0-100). This module reads that file, strips the YAML
frontmatter, and builds an `Agent` whose system prompt is the markdown
body prefixed with a short paragraph that names the current setting
values — so the model sees the levels actually in effect, not just the
defaults baked into the table.

`TabSettings` is a pydantic model with the five 0-100 ints. Defaults
match the Settings table in `tab.md`. Overrides happen at compile time:
to change a setting mid-session, recompile the agent.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from tab_cli.paths import plugins_dir, strip_frontmatter


class TabSettings(BaseModel):
    """Personality dials for the Tab agent.

    Each field is an int in [0, 100]. Defaults mirror the Settings
    table in `plugins/tab/agents/tab.md`.
    """

    humor: int = Field(default=65, ge=0, le=100)
    directness: int = Field(default=80, ge=0, le=100)
    warmth: int = Field(default=70, ge=0, le=100)
    autonomy: int = Field(default=50, ge=0, le=100)
    verbosity: int = Field(default=35, ge=0, le=100)


def _tab_md_path() -> Path:
    return plugins_dir() / "tab" / "agents" / "tab.md"


def _load_tab_md_body() -> str:
    """Read `plugins/tab/agents/tab.md` and return the body sans frontmatter."""
    return strip_frontmatter(_tab_md_path().read_text(encoding="utf-8"))


def _settings_preamble(settings: TabSettings) -> str:
    """Build the leading paragraph that injects current setting values."""
    return (
        "Your active personality settings (each on a 0-100 scale, where the "
        "Settings table below describes what each one controls) are: "
        f"Humor {settings.humor}%, Directness {settings.directness}%, "
        f"Warmth {settings.warmth}%, Autonomy {settings.autonomy}%, "
        f"Verbosity {settings.verbosity}%. "
        "These are the levels in effect right now — they override the "
        "defaults shown in the Settings table."
    )


def build_system_prompt(settings: TabSettings | None = None) -> str:
    """Compose the full system prompt: settings preamble + tab.md body.

    Exposed for tests and for callers that want the prompt string
    without instantiating an `Agent`.
    """
    s = settings if settings is not None else TabSettings()
    return f"{_settings_preamble(s)}\n\n{_load_tab_md_body()}"


def compile_tab_agent(
    settings: TabSettings | None = None,
    model: str | None = None,
) -> Agent:
    """Compile `tab.md` and the given settings into a pydantic-ai `Agent`.

    Args:
        settings: Personality dial values. ``None`` uses defaults from
            the Settings table in `tab.md`.
        model: Model identifier in ``<provider>:<name>`` form. The CLI
            drives only two providers: ``anthropic:<model>`` (handled by
            pydantic-ai's stock ``AnthropicModel``) and ``ollama:<model>``
            (handled by Tab's in-house :class:`OllamaNativeModel`, which
            talks to Ollama's ``/api/chat`` directly via ``ollama-python``
            rather than routing through the ``/v1`` OpenAI-compat layer).
            ``None`` defers model resolution; downstream callers wire it
            up before running the agent.

    Returns:
        A ready-to-run pydantic-ai `Agent`. Recompile to change settings.
    """
    prompt = build_system_prompt(settings)
    resolved_model = resolve_model(model)
    return Agent(
        model=resolved_model,
        system_prompt=prompt,
        defer_model_check=True,
    )


def resolve_model(model: str | None):
    """Dispatch a model string to the appropriate backend.

    The two prefixes Tab supports are:

    - ``ollama:<name>`` — peeled and passed to :class:`OllamaNativeModel`,
      which uses ``ollama-python``'s native ``/api/chat`` endpoint.
    - ``anthropic:<name>`` — passed through verbatim. pydantic-ai's
      ``Agent`` constructor parses the prefix and instantiates
      ``AnthropicModel`` itself, so we don't intercept.

    Anything else (``None``, ``openai:...``, etc.) is also passed through
    verbatim. pydantic-ai will reject unknown providers at run time, which
    is the right error surface — the CLI's documented contract is
    Anthropic + Ollama, but we don't pre-validate here so tests and
    advanced users keep a clean escape hatch.
    """
    if model is None:
        return None
    if model.startswith("ollama:"):
        # Lazy import: keeps callers that never use Ollama from paying
        # the ``ollama`` package's import cost.
        from tab_cli.models import OllamaNativeModel

        return OllamaNativeModel(model.removeprefix("ollama:"))
    return model
