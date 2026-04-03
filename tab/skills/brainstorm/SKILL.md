---
name: brainstorm
description: "Conversational idea capture — interview the user about an idea and write a structured IDEA.md that gives a fresh LLM session everything it needs to start building. Only triggers when the user types /brainstorm."
argument-hint: "[optional seed idea]"
---

## What This Is

A conversational skill that helps the user take a raw idea — maybe just a sentence, maybe a half-formed vision — and turn it into a structured handoff document. The output is `.local/IDEA.md`, written so that a completely fresh LLM session can read it and start working without needing any of the original conversation.

This skill activates **only** when the user runs `/brainstorm`. It's designed for empty codebases — the starting point of something new.

## The Interview

The goal is to draw the idea out of the user, not to interrogate them. Think of it as a conversation between two people at a whiteboard — one has the idea, the other is helping them get it down clearly enough that someone else could pick it up tomorrow.

You're filling four sections: **Goal**, **Requirements**, **Design**, and **Open Questions**. But you're not walking through them like a form. You're having a conversation that naturally covers this ground.

### Starting

If the user passed a seed (`/brainstorm a CLI tool that turns markdown into slide decks`), start from there. Reflect back what you understood and ask the first thing that would help you understand what they actually want to build.

If they just typed `/brainstorm` with no argument, ask what's on their mind. One question. Keep it open.

### Drawing It Out

Follow the energy. If they're excited about the design, explore the design. If they keep coming back to a specific use case, dig into that — it's probably the real requirement. Don't force a linear path through Goal → Requirements → Design.

Things to naturally uncover during the conversation:

- **What is this thing?** What does it do, in one or two sentences? Who is it for?
- **Why does it matter?** What problem does it solve? What's the motivation?
- **What does it need to do?** Concrete capabilities. Not a feature list interrogation — just understand what "working" looks like.
- **How should it work?** Technical approach, architecture, key decisions. Only go as deep as the user wants to go. Some people have strong opinions on stack and structure; others just want to describe the behavior and let the implementer decide.
- **What's still fuzzy?** Things they haven't figured out yet, tradeoffs they're aware of, things they explicitly want to punt on.

Ask follow-up questions when something is vague or when you sense there's more behind what they said. But don't over-interview — if the user gives you a clear, complete answer, move on. Three to five exchanges is usually enough. Some ideas are simple and don't need ten questions.

### When to Stop

You'll feel it — the idea has shape, the key decisions are made or explicitly deferred, and you're starting to circle. When you think you have enough, say so: summarize what you've got and ask if they want to add anything before you write it up.

## Writing IDEA.md

### Before Writing

Check if `.local/IDEA.md` already exists. If it does, show the user the existing file's Goal section and ask what they'd like to do — replace it with the new idea, or bail out.

Create the `.local/` directory if it doesn't exist.

### The Document

Write `.local/IDEA.md` with this structure:

```markdown
# [Idea Title]

## Goal

[What this thing is and why it matters. Written as a clear, concise statement
that answers "what are we building and why?" A fresh reader should understand
the purpose and motivation in this section alone.]

## Requirements

[What the thing needs to do. Concrete capabilities, constraints, and
non-negotiables. Written as prose or a list — whichever fits the idea better.
Focus on behavior and outcomes, not implementation details.]

## Design

[How the thing should work. Architecture, technical approach, key decisions,
stack choices — whatever the user specified. If they left parts open, say so
explicitly ("the specific framework is open — choose whatever fits"). This
section bridges the gap between "what" and "how" so the implementer isn't
guessing.]

## Open Questions

[Things that are still fuzzy, explicitly deferred, or worth revisiting.
Tradeoffs the user is aware of but hasn't resolved. Anything marked "figure
this out later" during the conversation.]
```

### Writing Quality

The entire point of this document is that someone (or some LLM) reads it cold and starts building. Every sentence should serve that reader.

- **Be specific.** "A fast API" means nothing. "A REST API that handles ~100 concurrent users with sub-200ms response times" means something.
- **Preserve the user's decisions.** If they said "use SQLite, not Postgres," write that and capture their reasoning if they gave any. Don't editorialize.
- **Preserve the user's non-decisions.** If they explicitly said "I don't care about the frontend framework," say that. It's as useful as a decision — it tells the implementer they have freedom.
- **Keep it proportional.** A simple idea gets a short document. Don't pad sections to make them look thorough. An empty Open Questions section is fine if the user didn't have any.

### After Writing

Tell the user where the file is and that it's ready for a fresh session to pick up. Keep it brief — they just spent time on the idea, they don't need a ceremony.
