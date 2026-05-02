# Tab

A thinking partner defined entirely in markdown — no compiled code, no dependencies, just text files that shape how Claude talks, thinks, and works with you.

## What is Tab?

Tab is a markdown substrate for an AI thinking partner. The personality, skills, and workflows live in plain text files; runtimes load them. Two runtimes ship today:

- **Claude Code plugin** under `plugins/tab/`, distributed through AltTab's marketplace.
- **Tab CLI** under `cli/` — a Python package (PyPI: `tab`) that runs the same markdown outside Claude Code. Verb-shaped subcommands (`tab ask`, `tab chat`, `tab <skill>`, `tab setup`); pydantic-ai for the agent loop with Anthropic + Ollama backends; grimoire for semantic skill routing.

## Quick start

Install via the Claude Code plugin system:

```
claude plugin add --from "https://github.com/4lt7ab/Tab" tab
```

Or run the CLI from a clone:

```bash
cd cli
uv sync
uv run tab --help
```

Full setup, including provider keys and personality dials: [docs/setup.md](docs/setup.md).

## Documentation

- [Architecture](docs/architecture.md) — repo layout, the two skill homes, plugin registration
- [Setup](docs/setup.md) — local development and plugin install
- [Testing](docs/testing.md) — `just test`, `just validate`, pluggable test seams
- [Deployment](docs/deployment.md) — versions and release process
- [Conventions](docs/conventions.md) — frontmatter, error patterns, lazy imports
- [Decisions](docs/decisions.md) — choices we deliberately made and rejected

For agents: [CLAUDE.md](CLAUDE.md) and [.claude/rules/](.claude/rules/).

## Trademark

Tab™ is a trademark of Jacob Fjermestad (4lt7ab), used to identify the Tab AI persona, agent, and associated personality definition files. This trademark applies specifically to the use of "Tab" as the name of an AI assistant, AI agent, AI persona, or AI-powered software product.

The Apache 2.0 license grants permission to use, modify, and distribute the source files in this repository. It does not grant permission to use the Tab™ name, branding, or persona identity to market, distribute, or represent a derivative work as "Tab" or as affiliated with the Tab project.

If you fork or modify this project, please choose a different name for your derivative.

## License

Apache-2.0. See [LICENSE](LICENSE).
