# Setup and Installation Guide

## Prerequisites

- **Claude Code** must be installed and working. These plugins run inside the Claude Code harness — they have no standalone runtime.
- **For tab-for-projects only:** The Tab for Projects MCP server must be running and configured in your Claude Code environment. The plugin's agents communicate with this MCP to manage projects, tasks, and documents.

## Installing the tab plugin

The `tab` plugin provides:
- **Tab agent** — a thinking partner defined in markdown. Sharp, warm, opinionated. Helps you pressure-test ideas and make better decisions.
- **Skills** — `draw-dino`, `listen`.

### Steps

1. Add the plugin from the AltTab marketplace. In Claude Code, install from the marketplace source at this repository:

   ```
   /Users/alttab/4lt7ab/Tab
   ```

   The marketplace manifest (`.claude-plugin/marketplace.json`) registers `tab` as an available plugin.

2. Once installed, the plugin sets `tab:Tab` as the default agent (configured in `tab/settings.json`).

### Verification

After installation, confirm the Tab agent is active:
- Start a new Claude Code session. The agent should identify itself through its characteristic style — direct, opinionated, conversational.
- Check that the `tab:Tab` agent is listed among available agents.

## Installing the tab-for-projects plugin

The `tab-for-projects` plugin provides:
- **Agent** — `developer` (codebase owner, implementation, analysis, in-code docs).

### Additional prerequisite

The Tab for Projects MCP server must be connected before the plugin can do anything useful. The developer agent checks MCP connectivity on startup by calling `list_projects` with `limit: 1`. If the MCP is not available, it will tell you and stop -- it does not improvise alternatives.

### Steps

1. Ensure the Tab for Projects MCP server is running and configured in your Claude Code MCP settings.

2. Add the plugin from the AltTab marketplace, same as above. The marketplace manifest registers `tab-for-projects` alongside `tab`.

3. Once installed, the plugin sets `tab-for-projects:developer` as the default agent (configured in `tab-for-projects/settings.json`).

### Verification

1. Start a new Claude Code session with the `tab-for-projects:developer` agent active.
2. The developer agent will call `list_projects` on startup. If you see a project list (or an empty list with no errors), the MCP connection is working.
3. Try asking the agent to list projects or create a test project. If it responds with structured project data from the MCP, everything is connected.

## Configuration

### Default agent

Each plugin declares a default agent in its `settings.json`:

| Plugin | File | Default agent |
|--------|------|---------------|
| `tab` | `tab/settings.json` | `tab:Tab` |
| `tab-for-projects` | `tab-for-projects/settings.json` | `tab-for-projects:developer` |

The `agent` field uses the format `plugin-name:agent-name`. To switch which agent loads by default, update the `agent` value in the relevant `settings.json`.

### Sandbox and permissions

Claude Code uses `.claude/settings.local.json` for local sandbox and permission overrides. This file controls which directories and network hosts commands may access. If a plugin's agents or skills need to reach specific paths or hosts, configure the sandbox allowlist there.

### Plugin structure

Both plugins are defined entirely in text files — no compiled code, no dependencies:

- **Agents** are markdown files in `<plugin>/agents/`. They define the agent's identity, behavior, and instructions.
- **Skills** are directories in `<plugin>/skills/`. They provide specialized capabilities invoked via slash commands.
- **Plugin manifest** is `<plugin>/.claude-plugin/plugin.json`. It declares the plugin's name, version, agents, and skills directory.

## Troubleshooting

### MCP not connected (tab-for-projects)

**Symptom:** The developer agent says "the Tab for Projects MCP isn't connected" on startup, or `list_projects` fails.

**What to check:**
- Verify the MCP server process is running.
- Check your Claude Code MCP configuration to ensure the Tab for Projects server is registered.
- Confirm the server's connection details (host, port, transport) match what Claude Code expects.
- Restart Claude Code after making MCP configuration changes.

### Plugin not loading

**Symptom:** The agent doesn't activate, skills aren't available, or Claude Code behaves as if no plugin is installed.

**What to check:**
- Verify the marketplace source path is correct and points to the repository root containing `.claude-plugin/marketplace.json`.
- Check that `marketplace.json` lists the plugin you expect (both `tab` and `tab-for-projects` should appear in the `plugins` array).
- Confirm the plugin's `plugin.json` is valid JSON. Look for the plugin name in `<plugin>/.claude-plugin/plugin.json`.
- Check that agent markdown files referenced in `plugin.json` exist at the declared paths (e.g., `./agents/tab.md` for the tab plugin).
- Restart Claude Code to pick up any plugin changes.

### Wrong agent loading

**Symptom:** You expected one agent but got another (e.g., Tab instead of the developer).

**What to check:**
- Each plugin has its own `settings.json` with an `agent` field. Verify the correct plugin is active and its `settings.json` points to the agent you want.
- If both plugins are installed, check which one is set as the active plugin in your session.
