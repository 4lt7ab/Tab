# Skills

Skills are slash-command capabilities in the Claude Code plugin system. They are lighter than agents -- each skill is defined in a `SKILL.md` file and activated by typing its command in the chat. Skills give Tab (and its packages) specific, repeatable behaviors that users can invoke on demand.

A skill's `SKILL.md` declares its name, a description used for matching, and an argument hint showing what parameters it accepts. When a user types the corresponding slash command, Tab follows the instructions in that file.

---

## draw-dino

**Package:** tab
**Invocation:** `/draw-dino [species]`

Draws ASCII art dinosaurs. If the user names a specific species, Tab draws that one. If not, Tab picks one itself.

### How it works

1. Note the requested species or customization. If none is given, choose a classic dinosaur.
2. Freestyle draw the dinosaur as ASCII art inside a code block (so spacing is preserved).
3. After drawing, include a short fun fact related to the species.

### Customization

The species and style adapt to the user's request:

- **Cute / baby** -- draws a Baby Dino
- **Flying** -- draws a Pterodactyl
- **Scary / fierce** -- draws a T-Rex or Velociraptor
- **Big / gentle** -- draws a Brontosaurus

### Design principles

- Low stakes on purpose. The skill exists to be fun and lower the barrier to interaction.
- Always deliver. No clarifying questions, no refusals. Pick a dino and draw it.
- Personality over precision. A charming dinosaur with wobbly legs beats a technically perfect one with no character.

---

## listen

**Package:** tab
**Invocation:** `/listen [optional topic]`

A deliberate listening mode. Tab goes silent while the user thinks out loud -- dumping ideas, working through confusion, venting, brainstorming. When the user signals they are done, Tab synthesizes what it heard and hands back the structure that was hiding in the stream.

### Entering listen mode

When the user runs `/listen`:

1. Tab acknowledges with a single short line, something like: *"Listening. Say 'done' when you're ready for the synthesis."*
2. If a topic was passed (e.g. `/listen auth redesign`), Tab notes it internally as context but does not comment on it.
3. Tab goes silent.

### While listening

- **Say nothing.** No reactions, no clarifications, no encouragement, no emoji, no questions. Absolute silence.
- **Track everything.** Themes, contradictions, emotional weight, decisions made mid-thought, questions the user asked themselves, things they repeated (repetition signals importance).
- **Note what is unsaid.** If the user talks around something without naming it, that is signal too.

The only exception: if the user directly asks Tab a question (genuinely addressed to Tab, not rhetorical), Tab answers briefly and returns to silence.

### Ending listen mode

The user ends it by saying something like "done," "finished," "that's it," or any clear signal they are handing the floor back. If genuinely ambiguous whether they want synthesis or are just shifting topics, Tab asks.

### The synthesis

This is where Tab earns the silence. The synthesis covers:

1. **Structure.** Organize what the user said into coherent themes or threads. Show them the shape of their own thinking.
2. **Contradictions.** If the user said A early on and not-A later, name it without judgment.
3. **Energy.** What did they spend the most time on? What did they repeat? What made them change direction? That is where the real priority lives.
4. **Gaps.** If there is an obvious missing piece that their plan depends on, flag it.
5. **Mirror first, opinions second.** The synthesis reflects the user's thinking faithfully. If Tab has a strong reaction, it comes after the synthesis, clearly separated.

The synthesis is not a transcript, not a to-do list (unless the user was clearly listing tasks), and not advice. It is the user's thinking, organized.

After the synthesis, Tab returns to normal mode. The listening context stays available for the rest of the session.

---

## tab-for-projects

The tab-for-projects plugin does not currently provide any skills. The developer agent handles all project management and codebase work directly.

---

