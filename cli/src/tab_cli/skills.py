"""Generic personality-skill runner.

The first port (``draw-dino``) and the three that follow (``listen``,
``teach``, ``think``) all share the same shape: read
``plugins/tab/skills/<name>/SKILL.md``, take the body as instructions,
run a turn against the configured model, print the result. This module
holds the shared machinery so each port ticket only adds a thin wrapper
(a Typer subcommand, a chat-dispatch line) instead of duplicating the
"open the file, strip the fence, build an agent" plumbing.

Design choices that aren't obvious from the call sites:

- **Persona delta, not replacement.** The skill's system prompt is the
  Tab persona (settings preamble + ``tab.md`` body) plus the skill body
  appended underneath. That keeps personality dials live during a skill
  turn — a 5%-warmth dino is still a Tab dino — and matches what the
  task body calls "a delta on top of the Tab persona prompt."
- **No prompt cache in source.** The body is read off disk on every
  ``run_skill`` / ``compile_skill_agent`` call. Skill prompts change as
  the personality plugin evolves and a stale cached copy would silently
  drift. The cost is one ``read_text`` per invocation, which is a
  rounding error next to the model call.
- **Shared plugins-dir resolution.** Default comes from
  :func:`tab_cli.paths.plugins_dir` — one resolver, used here, in the
  registry loader, in the chat default-load branch, and in the
  personality compiler. Tests pass a tmp dir to exercise loader edges;
  production code can omit.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tab_cli.paths import cli_skills_dir as _cli_skills_dir
from tab_cli.paths import plugins_dir as _plugins_dir
from tab_cli.paths import strip_frontmatter
from tab_cli.personality import TabSettings, build_system_prompt

if TYPE_CHECKING:
    from pydantic_ai import Agent


class SkillNotFoundError(FileNotFoundError):
    """The named skill has no ``SKILL.md`` under the personality plugin.

    Distinct from a generic ``FileNotFoundError`` so callers (CLI
    wrappers, the chat dispatch) can surface a "skill not registered"
    message that is friendlier than the bare path.
    """


def _skill_md_path(plugins_dir: Path, skill_name: str) -> Path:
    """Return the canonical plugin-tree path for ``skill_name``'s SKILL.md.

    Used by the test seam ``read_skill_body(plugins_dir=...)`` and the
    error path of the multi-source resolver. The CLI-local skill home
    has its own layout (``<cli_skills>/<name>/SKILL.md``, no ``tab/``
    intermediate) and is resolved through :func:`_resolve_skill_md_path`,
    not this helper.
    """
    return plugins_dir / "tab" / "skills" / skill_name / "SKILL.md"


def _resolve_skill_md_path(skill_name: str) -> Path:
    """Find ``skill_name``'s SKILL.md across both skill homes.

    Plugin tree first, CLI-local second — matches the order
    :func:`tab_cli.registry.load_skill_registry` walks, so a
    duplicate-name conflict the registry rejects at load time would
    also surface here as the plugin copy winning. Returns the canonical
    plugin path when neither file exists, so the resulting
    :class:`SkillNotFoundError` points at the most likely missing
    location rather than the CLI-local fallback.
    """
    candidates = (
        _skill_md_path(_plugins_dir(), skill_name),
        _cli_skills_dir() / skill_name / "SKILL.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def read_skill_body(skill_name: str, plugins_dir: Path | None = None) -> str:
    """Return the SKILL.md body (sans frontmatter) for ``skill_name``.

    The body is what becomes the skill's system-prompt suffix in
    :func:`compile_skill_agent`. The acceptance criterion for the
    draw-dino port pins exactly this: behavior is driven by the markdown
    body of the SKILL.md, not by a Python-side copy.

    When ``plugins_dir`` is omitted, the resolver searches both skill
    homes (plugin tree, then CLI-local). When it is provided — the
    test seam — only the plugin-tree layout is consulted, preserving
    the existing test contract.

    Raises:
        SkillNotFoundError: ``SKILL.md`` not present in either home (or,
            with the test seam, at the explicit plugins_dir path).
    """
    if plugins_dir is not None:
        path = _skill_md_path(plugins_dir, skill_name)
    else:
        path = _resolve_skill_md_path(skill_name)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SkillNotFoundError(
            f"no SKILL.md for skill {skill_name!r} at {path}",
        ) from exc
    return strip_frontmatter(text)


def build_skill_system_prompt(
    skill_name: str,
    *,
    settings: TabSettings | None = None,
    plugins_dir: Path | None = None,
) -> str:
    """Compose Tab's persona prompt + the skill body as one string.

    Exposed for tests and for callers that want to inspect the prompt
    without building an :class:`Agent`. The skill body is appended after
    a blank-line separator so the model parses the two halves cleanly.
    """
    base = build_system_prompt(settings)
    body = read_skill_body(skill_name, plugins_dir=plugins_dir)
    return f"{base}\n\n{body}"


def compile_skill_agent(
    skill_name: str,
    *,
    settings: TabSettings | None = None,
    model: str | None = None,
    plugins_dir: Path | None = None,
    tools: Sequence[Any] | None = None,
) -> Agent:
    """Build a pydantic-ai :class:`Agent` for the named personality skill.

    The system prompt is :func:`build_skill_system_prompt`'s output —
    Tab's persona (with the active settings preamble) plus the skill
    body. ``defer_model_check=True`` mirrors :func:`compile_tab_agent`
    so the same env-driven model resolution applies.

    ``tools`` is a per-skill registration hook. Most personality skills
    don't take any (the runner stays generic on purpose); the teach
    skill is the first that needs one — ``web_search`` is wired in by
    its caller. Anything pydantic-ai accepts in ``Agent(tools=...)``
    works: a plain function, a :class:`pydantic_ai.Tool`, or a list
    mixing both. ``None`` and ``()`` are equivalent — no tools.

    Raises:
        SkillNotFoundError: when the skill has no SKILL.md on disk.
    """
    # Lazy import: keeps modules that import :mod:`tab_cli.skills` for
    # type hints alone (e.g. the chat module's TYPE_CHECKING block) from
    # paying for pydantic_ai at import time. Same pattern the rest of
    # the package follows.
    from pydantic_ai import Agent

    from tab_cli.personality import resolve_model

    prompt = build_skill_system_prompt(
        skill_name, settings=settings, plugins_dir=plugins_dir
    )
    # Dispatch the model string the same way ``compile_tab_agent`` does:
    # ``ollama:<name>`` routes to the in-house ``OllamaNativeModel``,
    # ``anthropic:<name>`` and everything else passes through to
    # pydantic-ai. Without this, ``ollama:`` strings reach pydantic-ai's
    # ``Agent`` constructor which constructs ``OllamaProvider()`` and
    # raises about a missing ``OLLAMA_BASE_URL`` env var.
    resolved_model = resolve_model(model)
    return Agent(
        model=resolved_model,
        system_prompt=prompt,
        defer_model_check=True,
        tools=tuple(tools) if tools else (),
    )


def run_skill(
    skill_name: str,
    user_input: str,
    *,
    settings: TabSettings | None = None,
    model: str | None = None,
    plugins_dir: Path | None = None,
    tools: Sequence[Any] | None = None,
) -> str:
    """Run one synchronous turn against the named skill and return text.

    Used by the per-skill Typer subcommands (today: ``tab draw-dino``).
    The chat REPL builds its own agent via :func:`compile_skill_agent`
    so it can stream and update history; this entry point is for
    one-shot CLI use where streaming would just add complexity to the
    shell-out contract.

    ``user_input`` may be empty — every personality skill's SKILL.md
    handles a "no specific request" turn (draw-dino picks a dino,
    listen waits for the next line, etc.). The caller doesn't have to
    fabricate a default prompt.

    ``tools`` is forwarded to :func:`compile_skill_agent` for skills
    that need a tool registered (today: only ``teach`` with
    ``web_search``).
    """
    agent = compile_skill_agent(
        skill_name,
        settings=settings,
        model=model,
        plugins_dir=plugins_dir,
        tools=tools,
    )
    result = agent.run_sync(user_input)
    return result.output
