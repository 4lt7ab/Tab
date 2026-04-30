#!/usr/bin/env bash
#
# validate-plugins.sh — lightweight consistency checks for the Tab plugin marketplace.
# Run from the repo root. Requires jq.
#
# Checks performed:
#   1. Agent paths — every path in plugin.json agents[] resolves to an existing file
#   2. Agent frontmatter — each agent has name + description
#   3. Skills directory — exists and contains at least one SKILL.md
#   3b. Skill frontmatter — each SKILL.md has name + description, and no
#       fields outside the convention (CLAUDE.md: name, description, optional
#       argument-hint). The forbidden keys mode / requires-mcp / agents /
#       inputs were considered and rejected; this check enforces it.
#   4. Version sync — marketplace version matches plugin.json version
#   5. Settings agent reference — settings.json agent ref points to a valid agent name

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKETPLACE="$REPO_ROOT/.claude-plugin/marketplace.json"
ERRORS=0

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required but not installed." >&2
  exit 1
fi

pass() { printf "  \033[32mPASS\033[0m  %s\n" "$1"; }
fail() { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; ERRORS=$((ERRORS + 1)); }
warn() { printf "  \033[33mWARN\033[0m  %s\n" "$1"; }

# Extract a YAML frontmatter field from a markdown file.
# Handles: name: value / name: "value" / name: 'value'
frontmatter_field() {
  local field="$1" file="$2"
  awk -v field="$field" '
    BEGIN { in_fm=0 }
    /^---$/ { if (!in_fm) { in_fm=1; next } else { exit } }
    in_fm && $0 ~ "^" field ":" {
      sub("^" field ":[[:space:]]*", "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$file"
}

# Check whether a YAML frontmatter field key exists at all (returns 0 if present, 1 if not).
frontmatter_field_exists() {
  local field="$1" file="$2"
  awk -v field="$field" '
    BEGIN { in_fm=0 }
    /^---$/ { if (!in_fm) { in_fm=1; next } else { exit } }
    in_fm && $0 ~ "^" field ":" { print "yes"; exit }
  ' "$file" | grep -q "yes"
}

echo ""
echo "Validating plugin structure..."
echo ""

PLUGIN_COUNT=$(jq '.plugins | length' "$MARKETPLACE")

for (( i=0; i<PLUGIN_COUNT; i++ )); do
  PLUGIN=$(jq -r ".plugins[$i].name" "$MARKETPLACE")
  SOURCE=$(jq -r ".plugins[$i].source" "$MARKETPLACE")
  MKT_VERSION=$(jq -r ".plugins[$i].version" "$MARKETPLACE")
  PLUGIN_DIR="$REPO_ROOT/$SOURCE"
  PLUGIN_JSON="$PLUGIN_DIR/.claude-plugin/plugin.json"

  echo "── $PLUGIN ──"

  if [[ ! -f "$PLUGIN_JSON" ]]; then
    fail "plugin.json not found at $PLUGIN_JSON"
    echo ""
    continue
  fi

  # ── 1. Agent paths exist ─────────────────────────────────────────────────
  AGENT_COUNT=$(jq '.agents | length' "$PLUGIN_JSON")
  ALL_AGENTS_OK=true
  AGENT_PATHS=()
  for (( j=0; j<AGENT_COUNT; j++ )); do
    agent_path=$(jq -r ".agents[$j]" "$PLUGIN_JSON")
    AGENT_PATHS+=("$agent_path")
    resolved="$PLUGIN_DIR/$agent_path"
    if [[ ! -f "$resolved" ]]; then
      fail "Agent file missing: $agent_path (expected at $resolved)"
      ALL_AGENTS_OK=false
    fi
  done
  if $ALL_AGENTS_OK; then
    pass "All agent paths exist ($AGENT_COUNT agents)"
  fi

  # ── 2. Agent frontmatter valid ───────────────────────────────────────────
  ALL_FM_OK=true
  for agent_path in "${AGENT_PATHS[@]}"; do
    resolved="$PLUGIN_DIR/$agent_path"
    [[ ! -f "$resolved" ]] && continue
    fm_name="$(frontmatter_field "name" "$resolved")"
    fm_desc="$(frontmatter_field "description" "$resolved")"
    if [[ -z "$fm_name" ]]; then
      fail "Agent $agent_path missing frontmatter 'name'"
      ALL_FM_OK=false
    fi
    if [[ -z "$fm_desc" ]]; then
      fail "Agent $agent_path missing frontmatter 'description'"
      ALL_FM_OK=false
    fi
  done
  if $ALL_FM_OK; then
    pass "All agent frontmatter valid"
  fi

  # ── 3. Skills directory valid ────────────────────────────────────────────
  SKILLS_DIR_REL=$(jq -r '.skills // empty' "$PLUGIN_JSON")
  if [[ -n "$SKILLS_DIR_REL" ]]; then
    SKILLS_DIR="$PLUGIN_DIR/$SKILLS_DIR_REL"
    if [[ ! -d "$SKILLS_DIR" ]]; then
      fail "Skills directory missing: $SKILLS_DIR_REL (expected at $SKILLS_DIR)"
    else
      SKILL_COUNT=$(find "$SKILLS_DIR" -name "SKILL.md" | wc -l | tr -d ' ')
      if [[ "$SKILL_COUNT" -eq 0 ]]; then
        fail "Skills directory $SKILLS_DIR_REL contains no SKILL.md files"
      else
        pass "Skills directory valid ($SKILL_COUNT skill(s))"

        # ── 3b. Skill frontmatter valid ────────────────────────────────────
        ALL_SKILL_FM_OK=true
        while IFS= read -r skill_file; do
          skill_rel="${skill_file#"$PLUGIN_DIR/"}"
          fm_name="$(frontmatter_field "name" "$skill_file")"
          fm_desc="$(frontmatter_field "description" "$skill_file")"
          if [[ -z "$fm_name" ]]; then
            fail "Skill $skill_rel missing frontmatter 'name'"
            ALL_SKILL_FM_OK=false
          fi
          if [[ -z "$fm_desc" ]]; then
            fail "Skill $skill_rel missing frontmatter 'description'"
            ALL_SKILL_FM_OK=false
          fi

          # ── Forbidden frontmatter keys ──
          # CLAUDE.md: skill frontmatter is name, description, optional
          # argument-hint. The keys below were considered and rejected
          # ("Decisions we rejected"), so their presence is a regression.
          for forbidden in mode requires-mcp agents inputs; do
            if frontmatter_field_exists "$forbidden" "$skill_file"; then
              fail "Skill $skill_rel has forbidden frontmatter '$forbidden' (CLAUDE.md: name/description/argument-hint only)"
              ALL_SKILL_FM_OK=false
            fi
          done

        done < <(find "$SKILLS_DIR" -name "SKILL.md")
        if $ALL_SKILL_FM_OK; then
          pass "All skill frontmatter valid"
        fi
      fi
    fi
  else
    pass "No skills directory declared (skipped)"
  fi

  # ── 4. Version sync ─────────────────────────────────────────────────────
  PKG_VERSION=$(jq -r '.version' "$PLUGIN_JSON")
  if [[ "$MKT_VERSION" == "$PKG_VERSION" ]]; then
    pass "Version in sync ($PKG_VERSION)"
  else
    fail "Version mismatch: marketplace=$MKT_VERSION, plugin.json=$PKG_VERSION"
  fi

  # ── 5. Settings agent reference valid ────────────────────────────────────
  SETTINGS_FILE="$PLUGIN_DIR/settings.json"
  if [[ -f "$SETTINGS_FILE" ]]; then
    AGENT_REF=$(jq -r '.agent' "$SETTINGS_FILE")
    REF_PLUGIN="${AGENT_REF%%:*}"
    REF_AGENT="${AGENT_REF#*:}"
    if [[ "$REF_PLUGIN" != "$PLUGIN" ]]; then
      fail "settings.json agent plugin prefix '$REF_PLUGIN' does not match plugin name '$PLUGIN'"
    else
      AGENT_FOUND=false
      for agent_path in "${AGENT_PATHS[@]}"; do
        resolved="$PLUGIN_DIR/$agent_path"
        [[ ! -f "$resolved" ]] && continue
        fm_name="$(frontmatter_field "name" "$resolved")"
        if [[ "$fm_name" == "$REF_AGENT" ]]; then
          AGENT_FOUND=true
          break
        fi
      done
      if $AGENT_FOUND; then
        pass "Settings agent reference valid ($AGENT_REF)"
      else
        fail "Settings agent '$AGENT_REF' — no agent has frontmatter name '$REF_AGENT'"
      fi
    fi
  else
    pass "No settings.json (skipped)"
  fi

  echo ""
done

# ── 6. CLAUDE.md structure tree matches filesystem ─────────────────────────

CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
if [[ -f "$CLAUDE_MD" ]]; then
  echo "── CLAUDE.md sync ──"
  TREE_OK=true

  # Check every skill directory on disk is mentioned in CLAUDE.md.
  # Files at the skills/ top level with a leading underscore are
  # reference / shared-substrate docs, not skills — they have no YAML
  # frontmatter, aren't named `SKILL.md`, and aren't registered, so the
  # structure tree skips them too. Same discipline applies to agents.
  for plugin_dir in "$REPO_ROOT"/plugins/tab; do
    plugin_name="$(basename "$plugin_dir")"
    skills_dir="$plugin_dir/skills"
    [[ ! -d "$skills_dir" ]] && continue

    for skill_path in "$skills_dir"/*/SKILL.md; do
      [[ ! -f "$skill_path" ]] && continue
      skill_name="$(basename "$(dirname "$skill_path")")"
      [[ "$skill_name" == _* ]] && continue
      expected="plugins/$plugin_name/skills/$skill_name/SKILL.md"
      # Use plain substring match — doesn't need to be the full line, just present
      # The tree uses path-like entries with spaces as indentation
      if ! grep -qF "skills/$skill_name/SKILL.md" "$CLAUDE_MD"; then
        fail "CLAUDE.md missing skill: $expected"
        TREE_OK=false
      fi
    done

    # Check every agent file on disk is mentioned. Files with a leading
    # underscore are reference / shared-substrate docs, not agents — they
    # have no YAML frontmatter and aren't registered in plugin.json, so
    # the structure tree skips them too.
    if [[ -d "$plugin_dir/agents" ]]; then
      for agent_file in "$plugin_dir"/agents/*.md; do
        [[ ! -f "$agent_file" ]] && continue
        agent_name="$(basename "$agent_file")"
        [[ "$agent_name" == _* ]] && continue
        if ! grep -qF "agents/$agent_name" "$CLAUDE_MD"; then
          fail "CLAUDE.md missing agent: plugins/$plugin_name/agents/$agent_name"
          TREE_OK=false
        fi
      done
    fi
  done

  if $TREE_OK; then
    pass "CLAUDE.md structure tree matches filesystem"
  fi
  echo ""
fi

# ── Summary ────────────────────────────────────────────────────────────────

if [[ "$ERRORS" -eq 0 ]]; then
  echo "All checks passed."
  exit 0
else
  echo "$ERRORS check(s) failed."
  exit 1
fi
