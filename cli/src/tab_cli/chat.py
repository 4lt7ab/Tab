"""Interactive REPL loop for ``tab chat`` (and bare ``tab``).

A turn is: read a line of user input, classify it, react.

- ``/exit`` / ``/quit`` / EOF (Ctrl-D) end the session cleanly.
- A "set <setting> to NN%" / "be more <adjective>" phrase mutates the
  active :class:`TabSettings`, recompiles the agent, prints a one-line
  acknowledgement, and continues.
- Anything else goes through the grimoire registry: an above-threshold
  hit dispatches the matched skill (Tab persona + SKILL.md body); a
  miss is routed to the agent and the response is streamed back.

The ``listen`` skill is sticky: matching it flips the session into
listen mode, where every subsequent line bypasses grimoire and
settings detection and routes straight to the listen skill agent. The
SKILL.md body keeps Tab silent during the dump and emits the synthesis
when the user signals done. ``/done`` is the explicit exit signal —
the line is forwarded so the skill agent produces the synthesis, then
the session returns to normal chat.

History persists across turns within the session by passing
:meth:`AgentRunResult.all_messages` (or its streamed equivalent) into
the next ``run_stream_sync`` call as ``message_history=``. Recompiling
the agent for a settings change does **not** reset history — the
conversation continues with the new system prompt in effect.

The chat module deliberately holds no provider state of its own; the
agent does. ``--model`` passes through to :func:`compile_tab_agent`,
and recompilation on a settings change re-uses whatever model name was
captured at session start.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import IO, TYPE_CHECKING, Any

from tab_cli.personality import TabSettings, compile_tab_agent

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.messages import ModelMessage

    from tab_cli.registry import SkillRegistry


# v0 greeting. Short, no banner art — the REPL is a tool, not a stage.
_GREETING = "tab — say something, or /exit to leave."


# Setting-adjustment patterns. tab.md documents two flavors:
#
#   1. "set humor to 90%"          — explicit numeric value
#   2. "be more direct" / "be terse" — adjective comparatives that map
#                                       onto a dial (direct ↔ directness,
#                                       terse ↔ low verbosity, etc.)
#
# v0 implements (1) only. The adjective→dial mapping is bigger than it
# looks — "terse" inverts onto verbosity, "blunt" maps to directness
# but not to humor, "warm" is itself the dial name — and the deferred
# settings-UX ticket (01KQ2YXEDHVD2YG1DPD9HEVR2S) is where that mapping
# gets defended. Catching adjective phrases here without that mapping
# would either over-route innocuous chat ("I want to be more careful")
# or quietly miss the half the user expects to work.
_SETTING_NAMES = ("humor", "directness", "warmth", "autonomy", "verbosity")

_NUMERIC_PATTERN = re.compile(
    rf"\bset\s+(?P<name>{'|'.join(_SETTING_NAMES)})\s+to\s+(?P<value>\d{{1,3}})%?\b",
    re.IGNORECASE,
)


@dataclass
class _Session:
    """Mutable per-session state for the REPL.

    Held as a dataclass rather than passed around as scalars so the
    settings-adjustment path has a single object to mutate — recompiling
    the agent in three different places would drift.

    ``active_skill`` carries the name of a sticky skill the session is
    currently running under (today only ``"listen"`` uses this). While
    set, the loop bypasses grimoire and settings detection and routes
    every line through that skill's agent. ``None`` means normal chat
    routing — grimoire-then-agent.
    """

    agent: Agent
    settings: TabSettings
    model: str | None
    registry: SkillRegistry | None
    history: list[ModelMessage] = field(default_factory=list)
    active_skill: str | None = None


# Skills that take over the session for multiple turns once they fire,
# rather than running one-shot like ``draw-dino``. Membership in this set
# is what makes a skill match flip the session's ``active_skill`` flag.
# Today only ``listen`` qualifies (and the SKILL.md's "Tab says nothing
# until you signal done" semantics literally require this — a one-shot
# dispatch would drop back to the regular agent on the user's next line
# and the silence promise breaks).
_STICKY_SKILLS = frozenset({"listen"})

# The line that ends a sticky-skill mode. We forward the literal token
# to the skill agent (so the SKILL.md body's "synthesise on done"
# branch fires) and only after that turn flip ``active_skill`` back to
# ``None``. Single-shape exit beats per-skill exit phrases — easy to
# document, easy to grep, and the SKILL.md body already recognises
# "done" as a synthesis trigger.
_STICKY_EXIT_COMMAND = "/done"


def _tools_for_skill(skill_name: str) -> list[Any]:
    """Return the per-skill tool list for ``skill_name`` dispatches.

    Most personality skills don't need tools — the runner stays
    generic on purpose. ``teach`` is the first that does: the SKILL.md
    body's research phase wants a ``web_search`` tool and grimoire
    routing inside ``tab chat`` is one of the two paths that need to
    wire it (the other being the one-shot ``tab teach`` Typer
    subcommand).

    Lazy import for the same reason ``compile_skill_agent`` is lazy:
    the chat module is loaded for every REPL turn and ``httpx`` /
    pydantic-ai cost only matters when a tool is actually attached.
    """
    if skill_name == "teach":
        from tab_cli.web_search import default_web_search

        return [default_web_search()]
    return []


def _detect_setting_change(text: str, current: TabSettings) -> TabSettings | None:
    """Return updated :class:`TabSettings` if ``text`` is a settings nudge.

    Matches "set <name> to <int>%?" against the five known dials. Out-of-range
    values (e.g. "set humor to 250") clamp to [0, 100] rather than reject —
    the user's intent is unambiguous and refusing the nudge would be pedantic
    for an interactive prompt.

    Returns ``None`` for everything else, including comparative phrases like
    "be more direct" — those need an adjective→dial mapping owned by the
    deferred settings-UX ticket. Until that lands, the agent fields them as
    free-form chat (which mostly does the right thing — the model knows
    what "be more direct" means; it just can't move the dial itself).
    """
    numeric = _NUMERIC_PATTERN.search(text)
    if numeric is None:
        return None

    name = numeric.group("name").lower()
    value = max(0, min(100, int(numeric.group("value"))))
    return current.model_copy(update={name: value})


def _read_input(stdin: IO[str], stdout: IO[str]) -> str | None:
    """Print the prompt and read one line, or return ``None`` on EOF.

    EOF (Ctrl-D on a terminal, end-of-stream in piped input) is the
    canonical "I'm done" signal for a Unix REPL — we collapse it to
    ``None`` so the caller's loop has a single sentinel to check
    alongside the textual ``/exit`` and ``/quit`` commands.
    """
    stdout.write("> ")
    stdout.flush()
    line = stdin.readline()
    if line == "":  # EOF — readline returns "" only at end-of-stream
        return None
    return line.rstrip("\n")


def _stream_agent_turn(session: _Session, prompt: str, stdout: IO[str]) -> None:
    """Run one agent turn with streaming and persist messages to history.

    We use ``run_stream_sync`` + ``stream_text(delta=True)`` so the
    response appears character-by-character as the model emits it. The
    final message list comes back via ``all_messages()`` once the
    stream is fully drained — appending those to the session's history
    preserves cross-turn context for the next call.
    """
    with session.agent.run_stream_sync(
        prompt,
        message_history=session.history,
    ) as result:
        for chunk in result.stream_text(delta=True):
            stdout.write(chunk)
            stdout.flush()
        stdout.write("\n")
        stdout.flush()
        # Replace history wholesale: ``all_messages()`` returns the
        # complete conversation including this turn's user prompt and
        # model response. Appending ``new_messages()`` to ``history``
        # would also work but ``all_messages`` is the documented "this
        # is the canonical history" accessor and matches what tests can
        # assert on.
        session.history = list(result.all_messages())


def _dispatch_skill(
    session: _Session, skill_name: str, user_prompt: str, stdout: IO[str]
) -> None:
    """Run one streamed skill turn and merge its messages into history.

    The grimoire registry tells us which personality skill fired; this
    function actually does the work — compile a skill-aware agent
    (:func:`tab_cli.skills.compile_skill_agent` adds the skill body
    underneath the regular Tab persona prompt), stream the response,
    and roll the resulting messages into the session's shared history
    so the next agent or skill turn sees the dino in context.

    Errors compiling the skill agent (missing SKILL.md, malformed
    skill name) propagate up the call stack — the REPL's outer wrapper
    in ``cli.py`` collapses them into the standard ``tab: <reason>`` /
    exit-1 line. We don't catch here because a per-turn skill failure
    inside the loop should kill the session, not silently fall through
    to the agent and confuse the user about what just happened.
    """
    # Lazy import: keeps `tab --help` and the agent-only chat path from
    # paying for the skill module's import cost when no skill ever fires.
    from tab_cli.skills import compile_skill_agent

    skill_agent = compile_skill_agent(
        skill_name,
        settings=session.settings,
        model=session.model,
        tools=_tools_for_skill(skill_name),
    )

    with skill_agent.run_stream_sync(
        user_prompt,
        message_history=session.history,
    ) as result:
        for chunk in result.stream_text(delta=True):
            stdout.write(chunk)
            stdout.flush()
        stdout.write("\n")
        stdout.flush()
        # Merge into the shared history. The skill agent's system prompt
        # differs from the regular Tab agent's, but pydantic-ai stores
        # only the user/model message exchange in `all_messages()` —
        # the system prompt is recomputed at each compile, so threading
        # these messages back into the regular agent for the next turn
        # works without prompt drift.
        session.history = list(result.all_messages())


def run_chat(
    *,
    model: str | None = None,
    settings: TabSettings | None = None,
    registry: SkillRegistry | None = None,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
) -> None:
    """Run the interactive REPL until EOF / ``/exit`` / ``/quit``.

    Args:
        model: pydantic-ai model name in ``provider:name`` form, or
            ``None`` to defer to pydantic-ai's env-driven default.
        settings: Initial :class:`TabSettings`; ``None`` uses tab.md's
            defaults.
        registry: Pre-built :class:`SkillRegistry`. ``None`` triggers
            a default load from ``plugins/`` next to the package — the
            production code path. Tests inject a stub to skip the
            grimoire/Ollama runtime requirement.
        stdin / stdout: Streams to read user input from and stream
            responses to. Default to ``sys.stdin`` / ``sys.stdout`` so
            tests can substitute :class:`io.StringIO`.

    Errors loading the agent or registry surface as ``RuntimeError``-shaped
    exceptions for the Typer wrapper to collapse into a readable
    one-liner — same contract as ``tab ask``.
    """
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    if registry is None:
        # Lazy-imported so importing ``tab_cli.chat`` doesn't pull in
        # grimoire's Postgres/Ollama runtime requirements; tests that
        # pass an injected registry never reach this branch.
        from pathlib import Path

        from tab_cli.registry import load_skill_registry

        plugins_dir = Path(__file__).resolve().parents[3] / "plugins"
        registry = load_skill_registry(plugins_dir)

    active_settings = settings if settings is not None else TabSettings()
    agent = compile_tab_agent(settings=active_settings, model=model)
    session = _Session(
        agent=agent,
        settings=active_settings,
        model=model,
        registry=registry,
    )

    stdout.write(f"{_GREETING}\n")
    stdout.flush()

    while True:
        line = _read_input(stdin, stdout)
        if line is None:
            stdout.write("\n")  # newline after the inline prompt for tidy exit
            stdout.flush()
            return

        stripped = line.strip()
        if not stripped:
            continue

        # ``/exit`` / ``/quit`` always end the session, even mid-listen-
        # mode. The user's escape hatch must be unconditional or
        # accidental sticky-mode lock-in becomes a real failure mode.
        if stripped in ("/exit", "/quit"):
            return

        # Sticky-skill mode (today: listen). Bypass grimoire and
        # settings detection and route every line through the active
        # skill agent. The SKILL.md body decides what to emit (silence
        # while listening, synthesis on done). ``/done`` is the
        # explicit exit signal — we forward it so the skill agent
        # produces the synthesis, then drop back to normal routing.
        if session.active_skill is not None:
            is_exit = stripped == _STICKY_EXIT_COMMAND
            _dispatch_skill(session, session.active_skill, stripped, stdout)
            if is_exit:
                session.active_skill = None
            continue

        # Settings nudge — handled before routing because phrases like
        # "be more direct" should never accidentally trip a skill match.
        updated = _detect_setting_change(stripped, session.settings)
        if updated is not None:
            session.settings = updated
            session.agent = compile_tab_agent(
                settings=session.settings, model=session.model
            )
            stdout.write(
                f"[settings: humor {session.settings.humor}%, "
                f"directness {session.settings.directness}%, "
                f"warmth {session.settings.warmth}%, "
                f"autonomy {session.settings.autonomy}%, "
                f"verbosity {session.settings.verbosity}%]\n"
            )
            stdout.flush()
            continue

        # Skill match check. The registry can be empty (no records seeded)
        # — in that case ``match`` returns ``None`` and we fall through.
        hit = session.registry.match(stripped) if session.registry else None
        if hit is not None and hit.passed:
            _dispatch_skill(session, hit.name, stripped, stdout)
            # Sticky skills (e.g. ``listen``) take over the session
            # until ``/done``. Set the flag *after* the dispatch so the
            # entry turn — the SKILL.md's "Listening..." acknowledgement
            # — runs through the same code path as a normal one-shot
            # dispatch.
            if hit.name in _STICKY_SKILLS:
                session.active_skill = hit.name
            continue

        # Default: route to the agent and stream the response back.
        _stream_agent_turn(session, stripped, stdout)
