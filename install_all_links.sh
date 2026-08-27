#!/usr/bin/env bash
set -euo pipefail

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

  # Link to Cursor
  ln -sfh "$src_dir" "$HOME/.cursor/skills/$skill"
  echo "  -> Linked to Cursor: $HOME/.cursor/skills/$skill"

  # Link to Antigravity / Gemini
  ln -sfh "$src_dir" "$HOME/.gemini/config/skills/$skill"
  echo "  -> Linked to Antigravity: $HOME/.gemini/config/skills/$skill"
  ln -sfh "$src_dir" "$HOME/.gemini/skills/$skill"
  echo "  -> Linked to Gemini: $HOME/.gemini/skills/$skill"

  # Link to Claude Code
  ln -sfh "$src_dir" "$HOME/.claude/skills/$skill"
  echo "  -> Linked to Claude Code: $HOME/.claude/skills/$skill"

  # Link to Codex
  ln -sfh "$src_dir" "$HOME/.codex/skills/$skill"
  echo "  -> Linked to Codex: $HOME/.codex/skills/$skill"
done

# 2. Update ~/.codex/AGENTS.md
CODEX_AGENTS_FILE="$HOME/.codex/AGENTS.md"
mkdir -p "$(dirname "$CODEX_AGENTS_FILE")"

cat << INNER_EOF > "$CODEX_AGENTS_FILE"
# Codex Global Agent Rules & Skills

Here are the custom skills linked for Codex:

- **paper-reader**: 跨机器、跨客户端的论文/博客阅读分析与网页轻量总结。
  参见技能说明: $WORKSPACE_SKILLS_DIR/paper-reader/SKILL.md
- **auto-research-llm**: Automated LLM Research framework for dataset preparation, training (SFT, LoRA, Distillation, DPO, GRPO), evaluation, and tracking.
  参见技能说明: $WORKSPACE_SKILLS_DIR/auto-research-llm/SKILL.md
- **dataset-to-s3**: Tool for uploading and archiving datasets to S3.
  参见技能说明: $WORKSPACE_SKILLS_DIR/dataset-to-s3/SKILL.md
- **obsidian-clipper**: Tool for clipping web content and saving to Obsidian.
  参见技能说明: $WORKSPACE_SKILLS_DIR/obsidian-clipper/SKILL.md
INNER_EOF

echo "  -> Updated Codex configuration: $CODEX_AGENTS_FILE"
echo "All Skills symlinked successfully!"
