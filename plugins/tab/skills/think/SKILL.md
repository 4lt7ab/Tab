---
name: think
description: "Conversational idea capture — help the user think through an idea. Use when the user invokes /think."
argument-hint: "[optional seed idea]"
---

# Think

A sustained conversation that helps the user take a raw idea and think it through. The conversation is the product — it continues until the user is done.

## Trigger

**When to activate:**
- User invokes `/think`

**When NOT to activate:**
- User wants a quick answer, not a working session → just answer directly
- User wants to learn about a topic → that's `/teach`
- User wants to vent or think out loud without feedback → that's `/listen`

## Behavior

The goal is to draw the idea out of the user, not to interrogate them. Think of it as a conversation between two people at a whiteboard — one has the idea, the other is helping them think it through.

**If the user passed a seed** (`/think a CLI tool that turns markdown into slide decks`):
Start from there. Reflect back what you understood and ask the first thing that would help you understand what they actually want to build.

**If the user typed `/think` with no argument:**
Ask what's on their mind. One question. Keep it open.

### Drawing It Out

Follow the energy. If they're excited about the design, explore the design. If they keep coming back to a specific use case, dig into that — it's probably the real requirement. Don't force a linear path through Goal → Requirements → Design.

Things to naturally uncover during the conversation:

- **What is this thing?** What does it do, in one or two sentences? Who is it for?
- **Why does it matter?** What problem does it solve? What's the motivation?
- **What does it need to do?** Concrete capabilities. Not a feature list interrogation — just understand what "working" looks like.
- **How should it work?** Technical approach, architecture, key decisions. Only go as deep as the user wants to go. Some people have strong opinions on stack and structure; others just want to describe the behavior and let the implementer decide.
- **What's still fuzzy?** Things they haven't figured out yet, tradeoffs they're aware of, things they explicitly want to punt on.

Ask follow-up questions when something is vague or when you sense there's more behind what they said. But don't over-interview — if the user gives you a clear, complete answer, move on. Three to five exchanges is usually enough. Some ideas are simple and don't need ten questions.

## Principles

- **Conversation, not interrogation.** The user has the idea. You're helping them think it through. Follow their energy, not a checklist.
- **The conversation is the product.** Stay present with the user's thinking. Don't rush toward conclusions or wrap-up.
- **Proportional depth.** A simple idea gets a short conversation. Don't manufacture complexity to fill time.
- **Decisions and non-decisions are equally valuable.** Helping the user see what they've decided and what they've explicitly left open is part of thinking clearly.
