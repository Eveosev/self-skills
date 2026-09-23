#!/usr/bin/env bash
set -euo pipefail

FORCE=0
if [ "${1:-}" = "--force" ]; then
  FORCE=1
elif [ "$#" -gt 0 ]; then
  echo "Usage: $0 [--force]" >&2
  exit 2
fi

# Dynamically resolve script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_SKILLS_DIR="${WORKSPACE_SKILLS_DIR:-$SCRIPT_DIR}"

# 1. Ensure target folders exist
mkdir -p "$HOME/.cursor/skills"
mkdir -p "$HOME/.gemini/config/skills"
mkdir -p "$HOME/.gemini/skills"
mkdir -p "$HOME/.claude/skills"
mkdir -p "$HOME/.codex/skills"

# Skills list
SKILLS=("auto-research-llm" "dataset-to-s3" "obsidian-clipper" "paper-reader")

echo "Starting symlinking for Skills from $WORKSPACE_SKILLS_DIR..."

for skill in "${SKILLS[@]}"; do
  src_dir="$WORKSPACE_SKILLS_DIR/$skill"
  
  if [ ! -d "$src_dir" ]; then
    echo "Warning: Source skill directory $src_dir does not exist, skipping."
    continue
  fi

  echo "Linking skill: $skill"

  link_skill() {
    local target="$1"
    local label="$2"
    if [ -L "$target" ]; then
      if [ "$(readlink "$target")" = "$src_dir" ]; then
        echo "  -> Already linked to $label: $target"
        return
      fi
      if [ "$FORCE" -ne 1 ]; then
        echo "  !! Conflict at $target (use --force to replace)" >&2
        return 1
      fi
      rm "$target"
    elif [ -e "$target" ]; then
      if [ "$FORCE" -ne 1 ]; then
        echo "  !! Existing non-link at $target (use --force to replace)" >&2
        return 1
      fi
      rm -rf "$target"
    fi
    ln -s "$src_dir" "$target"
    echo "  -> Linked to $label: $target"
  }

  link_skill "$HOME/.cursor/skills/$skill" "Cursor"
  link_skill "$HOME/.gemini/config/skills/$skill" "Antigravity/Gemini config"
  link_skill "$HOME/.gemini/skills/$skill" "Gemini"
  link_skill "$HOME/.claude/skills/$skill" "Claude Code"
  link_skill "$HOME/.codex/skills/$skill" "Codex"
done

echo "Codex AGENTS.md 未被修改。请按各 skill 的客户端说明手动引用需要启用的 SKILL.md。"
echo "All Skills symlinked successfully!"
