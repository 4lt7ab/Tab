tab setup
─────────
1. Install / verify the CLI
     uv tool install tab           # or: pipx install tab
     tab --version

2. Configure provider keys (set what you'll use; pydantic-ai picks them up)
     export ANTHROPIC_API_KEY=...
     export OPENAI_API_KEY=...
     export GEMINI_API_KEY=...
     export GROQ_API_KEY=...
     # Ollama needs no key — point at OLLAMA_HOST if running remote.

3. (Optional) Wire `tab mcp` into Claude Code
     claude mcp add --scope user --transport stdio tab tab mcp
     # Then any Claude Code session can call ask_tab() and search_memory().

4. Want the Claude Code plugin instead of (or in addition to) the CLI?
     Run /hey-tab inside Claude Code, or:
     https://github.com/4lt7ab/Tab
