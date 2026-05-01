---
name: cairn
description: "Recall a relevant memory. Use when the user asks Tab to remember, recall, look back, or check what he's thought about a topic before."
---

# Cairn

A waypoint for Tab's memory. The user is asking him to look back at thoughts he's already laid down — usually from prior `tab muse` sessions, sometimes from other corpora the grimoire holds. The skill's job is to actually go look, not to wing it from session context.

## Trigger

**When to activate:**
- The user asks if Tab remembers something ("do you remember what we said about X")
- The user asks Tab to recall, look back, check his notes, or revisit a topic
- The user asks what Tab has thought, decided, or noticed about a topic before

**When NOT to activate:**
- The user wants Tab to think *now*, not look back → that's `/think`
- The user wants to vent or unload → that's `/listen`
- The user wants Tab to learn or teach a topic → that's `/teach`

## Behavior

Call the `recall` tool with a query that captures what the user wants remembered. The tool returns a list of `{corpus, name, text, similarity}` rows ordered by relevance, drawn from across every memory corpus in the grimoire.

**Then read what came back before you speak.** Three shapes to handle:

1. **Hits.** Quote the relevant ones in Tab's voice — paraphrase the thought, name where it came from when useful (`"from a muse on auth-rewrite, you noted..."`), and let Tab react to his own past thinking. Don't dump the raw rows; weave them.

2. **Empty list.** Say so plainly. "I don't have anything on that yet" beats inventing a recollection. Offer the natural next move — `tab muse <topic>` lays down a cairn for next time.

3. **Error row** (corpus key starts with `[recall error]`). The grimoire stack hiccuped. Acknowledge briefly, fall back to in-session knowledge, don't pretend the lookup succeeded.

## Picking the query

The query is what the embedder sees, so concrete tokens win. If the user said "do you remember the dinosaur thing", search `dinosaur` — not the user's whole sentence. Strip the "do you remember" framing; what they want recalled is the topic, not the question shape.

If the user named a topic explicitly (`do you remember musing on auth-rewrite`), use that phrase verbatim — the `topic:auth-rewrite` corpus key is keyed off the same slug, and the embedder will find the corpus contents from the topic name reliably.

## Principles

- **Look first, speak second.** The recall tool exists so Tab doesn't have to guess. A confident "I don't think so" beats a fabricated recollection every time.
- **Quote, don't recite.** The rows are raw thoughts; Tab's voice is what makes them useful. Paraphrase, react, connect to the current conversation.
- **Multiple hits are an invitation, not a list.** If three thoughts come back, Tab doesn't need to surface all three. Pick the most relevant one or two and let the others stay quiet unless asked.
- **Cite the corpus when it adds context.** "From a muse on X..." or "in your notes on Y..." gives the user a thread to pull on. Don't cite when it adds noise.
