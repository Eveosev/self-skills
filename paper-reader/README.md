# paper-reader

跨机器、跨客户端(Cursor / Claude Code / Codex / Antigravity / Gemini CLI 等)的
论文/博客阅读分析 skill。真身随本 git 仓库分发, 换机器只需 `git pull` +
跑一次软链脚本即可在该机器的所有客户端中使用。

## 架构: 脚本准备 + Agent 写笔记

| 角色 | 职责 |
|---|---|
| `scripts/*.py` | 拉元数据、下 PDF、marker 提图、拷贝 assets、写 `bundle.json` |
| **Agent(当前会话模型)** | 读 bundle + `prompts/*.md`, 分类并生成笔记、落盘 |

默认**不**调用外部 LLM API, 因此在 Cursor 等 Agent 框架内使用时无需配置
京东云 / DeepSeek 等密钥; 笔记由调度本 skill 的同一个模型完成。

可选 `--with-llm`: 纯 CLI、无 Agent 时, 才用配置的 OpenAI 兼容 API 自动写笔记。

## 安装

```bash
cd Skills/paper-reader
pip install -r requirements.txt            # trafilatura requests arxiv
```

深度解析(marker 提图)为可选增强: 安装
[datalab-to/marker](https://github.com/datalab-to/marker) 提供的
`marker_single` 命令后自动启用; 不安装也能正常工作, 只是降级为"仅摘要"。

Obsidian Vault 路径解析优先级: 环境变量 `NOTES_VAULT` > config 中的
`obsidian_vault` > 自动探测本仓库 git 根目录(在本仓库内直接用无需配置)。

### 仅 `--with-llm` 时才需要的 LLM 凭据

LLM 调用基于 `requests` 直连 `POST {base_url}/chat/completions`, 不依赖
`openai` SDK。配置方式(任选, 优先级从高到低):
1. 环境变量 `OPENAI_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`
   (兼容兜底: `DEFAULT_LLM_API_KEY` / `DEFAULT_LLM_BASE_URL` /
   `DEFAULT_LLM_MODEL_NAME`)
2. 本仓库内的 `config.local.json`(已 gitignore)
3. 机器级共享配置 `~/.config/paper-reader/config.json`

```bash
cp config.example.json config.local.json   # 仅 CLI --with-llm 需要
```

## 用法

```bash
# Agent 场景(默认): 只准备材料, 打印 bundle, 由 Agent 写笔记
python scripts/read.py "https://arxiv.org/abs/2503.14476"
python scripts/read.py "https://arxiv.org/html/2503.14476v1"   # /html/ 亦可
python scripts/read.py "https://arxiv.org/abs/2503.14476" --light
python scripts/read.py "https://example.com/some-blog-post"

# 纯 CLI 一条龙(才会打外部 LLM API)
python scripts/read.py "https://arxiv.org/abs/2503.14476" --with-llm
```

成功准备后 stdout 含:

```
=== PAPER_READER_BUNDLE_BEGIN ===
{ ... bundle.json ... }
=== PAPER_READER_BUNDLE_END ===
```

同时写入 `extracted/<arxiv_id|slug>/bundle.json`。

## 跨客户端接入矩阵

真身位置: 本仓库内的 `Skills/paper-reader/`。一键软链:

```bash
bash scripts/install_links.sh
```

| 客户端 | 发现机制 | 接入方式 |
|---|---|---|
| Cursor | `~/.cursor/skills/<name>/SKILL.md` 或 `~/.agents/skills/` | 软链 |
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | 软链 |
| Gemini CLI | `gemini skills install <path>` | `gemini skills install <本目录> --scope user` |
| Codex | 读取 `AGENTS.md` 引用的说明文件 | 在 `~/.codex/AGENTS.md` 中引用本目录 `SKILL.md` |
| Antigravity | 软链或规则文件引用 | 软链或在其 rules/skills 目录中引用本目录 |

详见 [references/clients.md](references/clients.md)。

## 换机器时怎么用

```bash
git pull                      # 真身随仓库同步
bash scripts/install_links.sh # 在这台新机器上重新建软链
```

## 排查

- Agent 场景下出现 `配置错误: 未找到有效的 LLM API Key` -> 误加了
  `--with-llm`; 去掉该参数即可, Agent 自己写笔记。
- 深度模式一直降级为"仅摘要" -> 检查 `marker_single` 是否在 `PATH` 中,
  或在 `config.local.json` 的 `marker_bin` 字段里显式指定其绝对路径。
- marker 在公式识别阶段崩溃(进程被信号杀死, 常见于部分 torch + Apple
  Silicon 组合) -> `deep_paper.py` 已内置自动降级: 检测到崩溃后会自动禁用
  `EquationProcessor` 重试一次(仍保留文本/图片/表格提取), 无需手动处理;
  若仍失败才会最终降级为仅摘要模式。
- Vault 路径不对 -> 显式设置环境变量 `NOTES_VAULT`, 或在 `config.local.json`
  中填写 `obsidian_vault`。
- ArXiv HTML 链接未被识别 -> 请更新到支持 `/html/` 的版本; 或改用
  `https://arxiv.org/abs/<id>`。
