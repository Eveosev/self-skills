# 各客户端的 Skill 发现机制

paper-reader 真身只有一份，位于本 git 仓库的 `90_Meta/Skills/paper-reader/`。
换机器时先同步主仓库和子模块，再执行 `bash scripts/install_links.sh` 建立本机软链接。核心逻辑全部在 `scripts/*.py`，任何能执行 Python 的 Agent 框架都可以调用，不依赖某个客户端专有的插件格式。

## 安装顺序

1. 同步源码：`git clone --recurse-submodules ...`，或在已有工作区执行 `git pull --recurse-submodules` 与 `git submodule update --init --recursive`。
2. 创建 Python 3.11 环境，安装 `requirements.txt` 和 `mineru`，再按该版本 CLI 下载并校验模型。
3. 注册 `SKILL.md`。各客户端可以共享同一份源码，不需要复制 skill 目录。
4. 用一个本地 PDF 跑一次准备流程，确认 bundle 的 `extractor_used` 为 `mineru`。

安装 skill 不会自动安装 MinerU；换电脑时运行时和模型也需要重新安装。`--with-llm` 只适用于无 Agent 的纯 CLI 场景，正常 Agent 调用不要加。

## Cursor
- 发现路径: `~/.cursor/skills/<name>/SKILL.md`
- 接入: `ln -s <本目录> ~/.cursor/skills/paper-reader`
- `install_links.sh` 会自动检测 `~/.cursor/skills` 目录是否存在并建软链；默认不会覆盖已有文件或错误链接，确认后可用 `--force` 替换。

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
- Codex 通过 `~/.codex/AGENTS.md`、项目内 `AGENTS.md` 或已注册的 skills 目录读取说明。
- 推荐在 `AGENTS.md` 中引用本目录的 `SKILL.md` 绝对路径。脚本默认只准备 bundle，由 Agent 用当前会话模型写笔记；不要默认加 `--with-llm`。

## Antigravity
- 通常通过其规则/skills 配置目录引用外部文件或软链接。
- 做法与 Cursor/Claude Code 类似: 软链本目录, 或在其规则文件中显式引用
  `SKILL.md` 的路径。

## WorkBuddy

WorkBuddy 的 skill 目录和规则入口随版本、宿主系统变化，当前仓库不硬编码一个可能失效的路径。打开 WorkBuddy 的 Skills/Rules/项目指令配置，将本目录的 `SKILL.md` 加入引用；若只支持复制文本，复制该文件内容并保留脚本目录的相对关系。运行脚本时使用安装 MinerU 的同一个 Python 解释器。

## 通用兜底方案
如果某个客户端完全没有 skill 机制, 仍然可以把 `SKILL.md` 的内容粘贴进它的
系统提示词/项目说明文件中, 脚本调用方式(`python scripts/read.py ...`)不
依赖任何客户端特性, 在终端里能跑通即可被任意 Agent 调用。
