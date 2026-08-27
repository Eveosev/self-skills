#!/usr/bin/env bash
# 把 paper-reader 真身软链到本机各 Agent 客户端的 skill 发现目录。
# 真身随本 git 仓库分发, 每台新机器只需跑一次本脚本即可在所有已安装的
# 客户端中使用同一份 skill, 无需重复复制文件。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

link_if_possible() {
  local target_dir="$1"
  local link_path="$2"
  local label="$3"

  if [ ! -d "$target_dir" ]; then
    echo "跳过 $label: 未检测到 $target_dir (客户端可能未安装)"
    return
  fi

  mkdir -p "$target_dir"
  if [ -L "$link_path" ] || [ -e "$link_path" ]; then
    echo "已存在, 跳过 $label: $link_path"
    return
  fi

  ln -s "$SKILL_DIR" "$link_path"
  echo "已接入 $label: $link_path -> $SKILL_DIR"
}

echo "paper-reader 真身: $SKILL_DIR"
echo "---"

link_if_possible "$HOME/.cursor/skills" "$HOME/.cursor/skills/paper-reader" "Cursor"
link_if_possible "$HOME/.claude/skills" "$HOME/.claude/skills/paper-reader" "Claude Code"

if command -v gemini >/dev/null 2>&1; then
  echo "检测到 gemini CLI, 可执行以下命令接入:"
  echo "  gemini skills install \"$SKILL_DIR\" --scope user"
else
  echo "跳过 Gemini CLI: 未检测到 gemini 命令"
fi

echo "---"
echo "Codex: 请在 ~/.codex/AGENTS.md 中添加一行引用本目录的 SKILL.md, 例如:"
echo "  参见技能说明: $SKILL_DIR/SKILL.md"
echo "Antigravity: 请在其 rules/skills 配置中软链或引用同一路径:"
echo "  $SKILL_DIR/SKILL.md"
echo "---"
echo "完成。详见 $SKILL_DIR/references/clients.md"
