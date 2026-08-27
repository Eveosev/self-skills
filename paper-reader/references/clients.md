# 各客户端的 Skill 发现机制

paper-reader 真身只有一份, 位于本 git 仓库的 `Skills/paper-reader/`。
换机器时先 `git pull` 拿到真身, 再执行 `bash scripts/install_links.sh`
建立本机的软链接。核心逻辑全部在 `scripts/*.py`(纯 Python), 任何能执行
`python` 命令的 Agent 框架都可以直接调用, 不依赖某个客户端专有的插件格式。

## Cursor
- 发现路径: `~/.cursor/skills/<name>/SKILL.md`
- 接入: `ln -s <本目录> ~/.cursor/skills/paper-reader`
- `install_links.sh` 会自动检测 `~/.cursor/skills` 目录是否存在并建软链。

## Claude Code
- 发现路径: `~/.claude/skills/<name>/SKILL.md`
- 接入: `ln -s <本目录> ~/.claude/skills/paper-reader`
- `install_links.sh` 同样会自动处理。

## Gemini CLI
- 通过命令安装, 不是简单软链:
  ```bash
  gemini skills install <本目录> --scope user
  ```
- 安装后需要 `/skills reload` 使其生效。
- 可参考本仓库 `GeminiSkills/Index.md` 中其它 skill 的登记方式。

## Codex
- Codex 没有独立的 skill 发现机制, 一般通过 `~/.codex/AGENTS.md`(或项目内
  的 `AGENTS.md`)引用说明文件来让 agent 知晓可用能力。
- 建议在 `AGENTS.md` 中加一行, 指向本目录的 `SKILL.md` 绝对路径, agent 读到
  后会按其中的说明调用 `python scripts/read.py ...`(默认只准备 bundle,
由 Agent 用当前会话模型写笔记; 勿默认加 `--with-llm`)。

## Antigravity
- 通常通过其规则/skills 配置目录引用外部文件或软链接。
- 做法与 Cursor/Claude Code 类似: 软链本目录, 或在其规则文件中显式引用
  `SKILL.md` 的路径。

## 通用兜底方案
如果某个客户端完全没有 skill 机制, 仍然可以把 `SKILL.md` 的内容粘贴进它的
系统提示词/项目说明文件中, 脚本调用方式(`python scripts/read.py ...`)不
依赖任何客户端特性, 在终端里能跑通即可被任意 Agent 调用。
