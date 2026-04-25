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
- **Same plugins-dir resolution as the registry / personality compiler.**
  Default is ``<repo>/plugins`` derived from this file's location. Tests
  pass a tmp dir to exercise loader edges; production code can omit.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tab_cli.personality import TabSettings, build_system_prompt

if TYPE_CHECKING:
    from pydantic_ai import Agent


class SkillNotFoundError(FileNotFoundError):
    """The named skill has no ``SKILL.md`` under the personality plugin.

    Distinct from a generic ``FileNotFoundError`` so callers (CLI
    wrappers, the chat dispatch) can surface a "skill not registered"
    message that is friendlier than the bare path.
    """


def _default_plugins_dir() -> Path:
    """Mirror :func:`tab_cli.personality._repo_root` for the plugins tree.

    Layout: ``<repo>/cli/src/tab_cli/skills.py`` → ``parents[3]`` is the
    repo root, plus ``plugins/``. Kept private and re-derived here rather
    than imported from ``personality`` so a future split of the modules
    doesn't entangle them.
    """
    return Path(__file__).resolve().parents[3] / "plugins"


def _skill_md_path(plugins_dir: Path, skill_name: str) -> Path:
    return plugins_dir / "tab" / "skills" / skill_name / "SKILL.md"


def _strip_frontmatter(text: str) -> str:
    """Drop a leading ``--- ... ---`` YAML frontmatter block.

    Mirrors :func:`tab_cli.personality._strip_frontmatter`. Kept local
    so this module doesn't reach into a private helper across the
    package — the rule is small enough that one duplicated copy is the
    cheaper trade than a third "shared frontmatter utility" module.
    """
    if not text.startswith("---"):
        return text

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text

    for idx in range(1, len(lines)):
        if lines[idx].rstrip("\r\n") == "---":
            body = "".join(lines[idx + 1 :])
            return body.lstrip("\n")

    # Unterminated fence — fall back to the whole text rather than
    # raising. The registry's strict frontmatter parser already validates
    # the YAML at startup; by the time we get here, the file is known
    # well-formed enough to register, and a raise on this codepath would
    # only fire on a torn write between startup and skill dispatch.
    return text


def read_skill_body(skill_name: str, plugins_dir: Path | None = None) -> str:
    """Return the SKILL.md body (sans frontmatter) for ``skill_name``.

    The body is what becomes the skill's system-prompt suffix in
    :func:`compile_skill_agent`. The acceptance criterion for the
    draw-dino port pins exactly this: behavior is driven by the markdown
    body of the SKILL.md, not by a Python-side copy.

    Raises:
        SkillNotFoundError: ``plugins/tab/skills/<skill_name>/SKILL.md``
            does not exist.
    """
    plugins_dir = plugins_dir if plugins_dir is not None else _default_plugins_dir()
    path = _skill_md_path(plugins_dir, skill_name)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SkillNotFoundError(
            f"no SKILL.md for skill {skill_name!r} at {path}",
        ) from exc
    return _strip_frontmatter(text)


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

    prompt = build_skill_system_prompt(
        skill_name, settings=settings, plugins_dir=plugins_dir
    )
    return Agent(
        model=model,
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

    Used by the per-skill Typer subcommands (``tab draw-dino``,
    ``tab listen``, ...). The chat REPL builds its own agent via
    :func:`compile_skill_agent` so it can stream and update history;
    this entry point is for one-shot CLI use where streaming would just
    add complexity to the shell-out contract.

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
