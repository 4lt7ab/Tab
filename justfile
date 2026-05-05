_default:
    @just --list

# Run pytest from cli/ — the only blocking gate before commit.
test:
    cd cli && uv run pytest

# Validate plugin structure: frontmatter, version sync, CLAUDE.md tree.
validate:
    bash scripts/validate-plugins.sh

# Format Python sources with ruff (advisory).
fmt:
    uvx ruff format cli/src cli/tests

# Lint Python sources with ruff (advisory).
lint:
    uvx ruff check cli/src cli/tests

# Type-check the CLI with basedpyright (advisory).
typecheck:
    uvx basedpyright cli/src

# Run the CLI without installing — equivalent to `tab` after `uv sync`.
tab *args:
    cd cli && uv run tab {{args}}

# Sync the CLI venv from the lockfile.
sync:
    cd cli && uv sync

# Bump every version (defaults to patch; pass an explicit semver to override). Only blessed path — see CLAUDE.md "Versions".
bump VERSION="":
    #!/usr/bin/env bash
    set -euo pipefail
    new="{{VERSION}}"
    if [[ -z "$new" ]]; then
      cur=$(jq -r '.version' plugins/tab/.claude-plugin/plugin.json)
      new=$(echo "$cur" | awk -F. '{printf "%d.%d.%d", $1, $2, $3+1}')
    fi
    if ! [[ "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "tab: version must be semver x.y.z" >&2
      exit 1
    fi
    jq ".plugins[0].version = \"$new\"" .claude-plugin/marketplace.json > .claude-plugin/marketplace.json.tmp && mv .claude-plugin/marketplace.json.tmp .claude-plugin/marketplace.json
    jq ".version = \"$new\"" plugins/tab/.claude-plugin/plugin.json > plugins/tab/.claude-plugin/plugin.json.tmp && mv plugins/tab/.claude-plugin/plugin.json.tmp plugins/tab/.claude-plugin/plugin.json
    sed -i.bak -E "s/^version = .*/version = \"$new\"/" cli/pyproject.toml
    rm cli/pyproject.toml.bak
    (cd cli && uv sync)
    just validate
    just test
    echo "all → $new"
