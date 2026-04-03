---
name: draw-dino
description: "Draw ASCII art dinosaurs — a fun, low-stakes creative skill."
argument-hint: "[species]"
---

## What This Skill Does

This skill draws ASCII art dinosaurs. It supports multiple species and styles.

## When to Trigger

Activate this skill when the user expresses **explicit intent to see or create a dinosaur drawing**. Look for requests like:

- "Draw me a dinosaur" / "draw a T-Rex" / "show me a dino"
- "Can you make an ASCII dinosaur?"
- "I want to see a brontosaurus"
- Any clear request to **draw, show, or create** a dinosaur or dino-related ASCII art

**Do NOT trigger on:**

- Incidental mentions of dinosaurs in conversation (e.g., "dinosaurs went extinct 66 million years ago")
- The word "rawr" used as an exclamation or greeting without drawing intent
- Discussions about dinosaur facts, movies, or paleontology unless the user asks for art
- Metaphorical dinosaur references (e.g., "this codebase is a dinosaur")

The bar is low — the user does not need to say `/draw-dino` or use precise language. But there must be a clear signal that they want to **see** a dinosaur, not just **talk about** one.

## Instructions

When invoked, pick an appropriate dinosaur based on the user's request. If no specific species is mentioned, pick one yourself. Always output the ASCII art inside a code block so spacing is preserved.

## Customization

- If the user asks for a **cute** or **baby** dino, use the Baby Dino.
- If the user asks for a **flying** dinosaur, use the Pterodactyl.
- If the user asks for something **scary** or **fierce**, use the T-Rex or Velociraptor.
- If the user asks for something **big** or **gentle**, use the Brontosaurus.

## Reference Templates

The following are quality anchors — use them as inspiration and starting points, but feel free to freestyle your own. Aim for **8-15 lines tall** so the art is substantial without overwhelming the chat.

### T-Rex

```
            __
           / _)
    _.----/ /
   /         \
__/ (  |  (  |
/__.-'|_|--|_|
```

### Brontosaurus

```
                  .       .
                 / `.   .' \
         .---.  <    > <    >  .---.
         |    \  \ - ~ ~ - /  /    |
          ~-..-~             ~-..-~
      \~~~\.'                    `./~~~/
       \__/                        \__/
        /                  .-    .  \
 _._ _.-    .-~ ~-.       /       }   \/~~~/
|     `\~~~`-.      `-.  |        }    \__/
 \    .'  `\   ~-._    `-|     ._ }
  `\.___.'   `-.__  ~--._}   .---'
                  `-._ _}--'
```

### Stegosaurus

```
                  .  .
                 / \/ \
                (  . .  )
               _/  ()  \_
              / /| .--. |\ \
             / / |/    \| \ \
            / /   \    /   \ \
        _.-'  /    \  /     \  '-._
    _.-'     /  /\  \/  /\   \     '-._
   {        / ./  \    /  \.\  \        }
    '-._   /    __/\  /\__  \   \ _.-'
        '-./   /    \/    \  \.-'
            '-'            '-'
```

These templates set a quality bar. You can modify, embellish, or draw entirely original dinosaurs — the point is that the output should feel **crafted**, not minimal.

## Workflow

1. Note the type of dinosaur and prompt customization, if one is given. Choose a classic if one is not.
2. Draw the dinosaur — use a reference template as a starting point or freestyle your own. Aim for 8-15 lines tall.
3. After drawing, add a short fun dinosaur fact related to the species you drew.

## Principles

- **Low stakes on purpose.** This skill exists to be fun. It lowers the barrier to interaction — if someone will ask for a dinosaur, they'll ask for anything. That's the point.
- **Always deliver.** No clarifying questions, no "I can't draw." Pick a dino and draw it. The user asked for a moment of delight, not a requirements gathering session.
- **Personality over precision.** A charming dinosaur with wobbly legs beats a technically perfect one with no soul. Have fun with it.
