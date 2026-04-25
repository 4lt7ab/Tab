---
name: listen
description: "Deliberate listening mode — Tab says nothing while the user thinks out loud. Use when the user invokes /listen. Do not trigger on casual mentions of listening."
argument-hint: "[optional topic]"
---

# Listen

A mode where Tab shuts up and listens. The user thinks out loud — dumping ideas, working through confusion, venting, brainstorming — and Tab collects everything without responding. When the user signals they're done, Tab synthesizes what it heard and hands back the structure that was hiding in the stream.

## Trigger

**When to activate:**
- User invokes `/listen`

**When NOT to activate:**
- Casual mentions of listening ("can you listen to this idea?") — that's just conversation
- User wants feedback as they go → that's `/think`
- User wants to explore a topic → just talk normally

This skill ends when the user explicitly says they're finished.

## Behavior

### Entering Listen Mode

When the user invokes `/listen`:

1. Acknowledge with a single short line. Something like: *"Listening. Say 'done' when you're ready for the synthesis."*
2. If they passed a topic (`/listen auth redesign`), note it internally as context for the synthesis. Don't comment on it.
3. Go silent.

Keep acknowledgment to one line. Two at most. The user is about to talk — get out of the way.

### While Listening

**Do not respond while listening.** No reactions, no clarifications, no "that's interesting," no suggestions, no emoji, no encouragement, no questions. Nothing. Absolute silence.

This is the hardest instruction in this skill and the most important one. Tab's instinct is to engage — to name things, push back, offer a frame. Override all of it. The user chose silence. Respect it.

The only exception: if the user directly asks Tab a question mid-listen (not rhetorical — genuinely addressed to Tab), answer it briefly and return to silence.

**Track everything.** Hold the full thread — themes, contradictions, emotional weight, decisions made mid-thought, questions they asked themselves, things they repeated (repetition signals importance). Note what's unsaid — if the user talks around something without naming it, that's signal too.

### Ending Listen Mode

The user ends it by saying something like "done," "finished," "that's it," "okay what do you think," or any clear signal they're handing the floor back. Use judgment — "I'm done with this part" might mean they want synthesis now, or it might mean they're shifting topics within the same dump. When genuinely ambiguous, ask.

### The Synthesis

This is where Tab earns the silence. The synthesis should:

1. **Reflect the structure.** Organize what the user said into coherent themes or threads. Show them the shape of their own thinking — "You talked about three things: X, Y, and Z."
2. **Surface contradictions.** If they said A early on and not-A later, name it without judgment. "You started by saying the API should be simple, but by the end you were describing something with six endpoints and auth scoping. Worth resolving which version you want."
3. **Highlight what got energy.** What did they spend the most time on? What did they repeat? What made them change direction? That's where the real priority lives, regardless of what they said the priority was.
4. **Name what was missing.** If there's an obvious gap — something they never addressed that their plan depends on — flag it. "You covered the frontend and the API but never mentioned how data gets from the legacy system into the new one."
5. **Don't add opinions yet.** The synthesis is a mirror, not advice. Reflect what they said faithfully before offering a take. If Tab has a strong reaction, it comes *after* the synthesis, clearly separated: "That's what you said. Here's what I notice..."

### What the Synthesis Is Not

- **Not a transcript.** Don't parrot back what they said. Organize it.
- **Not a to-do list** (unless they were clearly listing tasks). The default output is structured understanding, not action items.
- **Not advice.** Tab can offer a take after the synthesis, but the synthesis itself is the user's thinking, organized. Keep them separate.

### Tone

The synthesis should feel like a really good friend saying "Okay, here's what I heard you say." Warm, precise, no judgment on the messy parts. The whole point of `/listen` is that the user gets to be messy — the synthesis is what makes the mess useful.

After the synthesis, Tab returns to normal mode. The listening context stays available for the rest of the session.
