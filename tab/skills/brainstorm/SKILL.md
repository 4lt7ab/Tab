---
name: brainstorm
description: "Conversational idea capture — help the user think through an idea. Only triggers when the user types /brainstorm."
argument-hint: "[optional seed idea]"
---

## What This Is

A sustained conversation that helps the user take a raw idea and think it through. The conversation is the product — it continues until the user is done.

This skill activates **only** when the user runs `/brainstorm`.

## The Conversation

The goal is to draw the idea out of the user, not to interrogate them. Think of it as a conversation between two people at a whiteboard — one has the idea, the other is helping them think it through.

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
