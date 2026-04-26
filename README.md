# Tab

A thinking partner defined entirely in markdown -- no compiled code, no dependencies, just text files that shape how Claude talks, thinks, and works with you.

## What is Tab?

Tab is a markdown substrate for an AI thinking partner. The personality, skills, and workflows live in plain text files; runtimes load them. Two runtimes ship today:

- **Claude Code plugins** under `plugins/`: distributed through AltTab's marketplace.
- **Tab CLI** under `cli/`: a Python package that runs the same markdown outside Claude Code, exposable as an MCP server.

The repo contains:

- **tab** -- a sharp, warm thinking partner personality. It changes how Claude shows up: more direct, more collaborative, more opinionated when it matters. The entire persona is defined in markdown files (agents and skills) with zero runtime dependencies.

- **tab-for-projects** -- project workflow tools that integrate with the Tab for Projects MCP server for pair-programming, capturing decisions, and managing project context.

- **tab-cli** -- the Python runtime. Verb-shaped subcommands (`tab ask`, `tab chat`, `tab <skill>`, `tab mcp`, `tab setup`); pydantic-ai for the agent loop with Anthropic + Ollama backends; grimoire for semantic skill routing.

Both Claude Code plugins are distributed through AltTab's marketplace.

## Quick Start

Install either package using the Claude Code plugin system:

```
# Install Tab (the thinking partner personality)
claude plugin add --from "https://github.com/4lt7ab/Tab" tab

# Install Tab for Projects (project management agents)
claude plugin add --from "https://github.com/4lt7ab/Tab" tab-for-projects
```

The marketplace configuration at `.claude-plugin/marketplace.json` defines both plugins. Claude Code resolves them from this repository automatically.

## Packages

| Package | Version | Description |
| --- | --- | --- |
| [tab](./plugins/tab) | 0.3.2 | A sharp, warm thinking partner who helps you make better decisions |
| [tab-for-projects](./plugins/tab-for-projects) | 4.15.2 | Project workflow tracking -- skills and agents for the Tab for Projects MCP |
| [tab-cli](./cli) | 0.2.0 | Python runtime for the Tab markdown substrate -- verb-shaped subcommands, MCP server mode, Anthropic + Ollama backends |

## Trademark

Tab™ is a trademark of Jacob Fjermestad (4lt7ab), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.

## License

This project is licensed under [Apache-2.0](./LICENSE).
