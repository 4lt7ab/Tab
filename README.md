# Tab

A thinking partner defined entirely in markdown -- no compiled code, no dependencies, just text files that shape how Claude talks, thinks, and works with you.

## What is Tab?

Tab is a Claude Code plugin repository containing two packages:

- **tab** -- a sharp, warm thinking partner personality. It changes how Claude shows up: more direct, more collaborative, more opinionated when it matters. The entire persona is defined in markdown files (agents and skills) with zero runtime dependencies.

- **tab-for-projects** -- project workflow tracking through conversational agents. It provides a set of specialized agents (manager, planner, QA, documenter, coordinator, bugfixer, implementer) and skills that integrate with the Tab for Projects MCP server for capturing decisions, tracking tasks, and managing project context.

Both packages are distributed as Claude Code plugins through AltTab's marketplace.

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
| [tab](./tab) | 0.0.3 | A sharp, warm thinking partner who helps you make better decisions |
| [tab-for-projects](./tab-for-projects) | 0.0.1 | Project workflow tracking -- skills and agents for the Tab for Projects MCP |

## Documentation

| Document | Description |
| --- | --- |
| [CLAUDE.md](./CLAUDE.md) | Agent context and project conventions |
| [docs/architecture.md](./docs/architecture.md) | Repository structure and design decisions |
| [docs/tab-agent.md](./docs/tab-agent.md) | Tab personality package documentation |
| [docs/project-agents.md](./docs/project-agents.md) | Tab for Projects agents documentation |
| [docs/skills.md](./docs/skills.md) | Skills documentation |
| [docs/setup.md](./docs/setup.md) | Setup guide |
| [docs/walkthrough.md](./docs/walkthrough.md) | Walkthrough guide |

## Trademark

Tab™ is a trademark of Jacob Fjermestad (4lt7ab), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.

## License

This project is licensed under [Apache-2.0](./LICENSE).
