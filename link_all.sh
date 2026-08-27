#!/usr/bin/env bash
# 把本目录 (Skills/) 下所有含 SKILL.md 的 skill 同步软链到 Cursor 读取目录 ~/.agents/skills/
# 用法: bash Skills/link_all.sh
set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${TARGET_DIR:-$HOME/.agents/skills}"
mkdir -p "$TARGET_DIR"

linked=0
for d in "$SKILLS_DIR"/*/; do
  name="$(basename "$d")"
  if [[ ! -f "$d/SKILL.md" ]]; then
    echo "跳过 $name (无 SKILL.md)"
    continue
  fi
  ln -sfn "$SKILLS_DIR/$name" "$TARGET_DIR/$name"
  echo "已链接 $TARGET_DIR/$name -> $SKILLS_DIR/$name"
  linked=$((linked+1))
done

echo "完成: 共同步 $linked 个 skill 到 $TARGET_DIR"
echo "提示: 在 Cursor 中 Reload Window 后即可在 Skills 面板看到。"
