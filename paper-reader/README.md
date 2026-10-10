# paper-reader

跨机器、跨客户端(Cursor / Claude Code / Codex / Antigravity / Gemini CLI / WorkBuddy 等)的论文/博客阅读分析 skill。真身随 git 仓库分发；换机器时同步子模块、安装运行时，再按客户端注册即可。

## 架构: 脚本准备 + Agent 写笔记

| 角色 | 职责 |
|---|---|
| `scripts/*.py` | 拉元数据、下 PDF、MinerU/Marker 提取、拷贝 assets、浅克隆关联仓库、写 `bundle.json` |
| **Agent(当前会话模型)** | 读论文与仓库清单/源码，分类并生成笔记、落盘 |

默认**不**调用外部 LLM API, 因此在 Cursor 等 Agent 框架内使用时无需配置
京东云 / DeepSeek 等密钥; 笔记由调度本 skill 的同一个模型完成。

可选 `--with-llm`: 纯 CLI、无 Agent 时, 才用配置的 OpenAI 兼容 API 自动写笔记。

## 安装

### 1. 安装 Python 依赖和 MinerU

推荐使用 Python 3.11 的独立环境。`requirements.txt` 只包含准备论文所需的轻量依赖，MinerU 需要单独安装：

```bash
cd 90_Meta/Skills/paper-reader
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python mineru
```

安装后确认命令和模型管理入口，以实际版本的 `--help` 为准：

```bash
.venv/bin/mineru --help
.venv/bin/mineru-kit --help       # 若该版本提供 mineru-kit
.venv/bin/mineru-models-download --help  # 若该版本提供模型下载器
```

如果安装版本提供以下命令，下载并校验 basic 模型；命令不存在时按上面的 `--help` 选择对应入口：

```bash
.venv/bin/mineru-models-download --tier basic --source modelscope
.venv/bin/mineru-kit models verify --tier basic
```

深度解析没有可用 MinerU 时会降级为摘要模式；这只用于排查环境，不代表完整安装成功。Marker 可作为兼容后备，但不是 MinerU 的替代安装步骤。
论文正文或摘要明确给出 GitHub URL 时，脚本会用 `git clone --depth 1
--filter=blob:none --no-tags` 把公开仓库放到 `extracted/<paper>/code/`，记录固定
commit、README、关键文件、语言统计和文件树。它不会猜测仓库，也不会执行仓库
中的安装脚本或程序；克隆失败只记录到 bundle，不中断论文流程。

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

真身位置: 本仓库内的 `90_Meta/Skills/paper-reader/`。一键软链:

```bash
bash scripts/install_links.sh
```

| 客户端 | 发现机制 | 接入方式 |
|---|---|---|
| Cursor | `~/.cursor/skills/<name>/SKILL.md` 或 `~/.agents/skills/` | 软链 |
| Claude Code | `~/.claude/skills/<name>/SKILL.md` | 软链 |
| Gemini CLI | `gemini skills install <path>` | `gemini skills install <本目录> --scope user` |
| Codex | 读取 `AGENTS.md` 或已注册的 skills | 在 `~/.codex/AGENTS.md` 或项目内 `AGENTS.md` 中引用本目录 `SKILL.md`；若当前版本支持 `~/.codex/skills`，可使用软链 |
| Antigravity | 软链或规则文件引用 | 软链或在其 rules/skills 目录中引用本目录 |
| WorkBuddy | 以其当前版本的 Skills/Rules 配置为准 | 在 UI 或项目规则中引用本目录 `SKILL.md`；不要假设固定目录 |

详见 [references/clients.md](references/clients.md)。

## 换机器时怎么用

```bash
git pull --recurse-submodules
git submodule update --init --recursive
bash scripts/install_links.sh
```

安装 skill 和安装 MinerU 是两件事：skill 是 `SKILL.md` 与脚本，MinerU 是本机 Python 环境和模型。换电脑时两者都要重新准备；换 Agent 平台时通常只需重新注册同一份 `SKILL.md`。

## 排查

- Agent 场景下出现 `配置错误: 未找到有效的 LLM API Key` -> 误加了
  `--with-llm`; 去掉该参数即可, Agent 自己写笔记。
- 深度模式一直降级为"仅摘要" -> 先检查 MinerU CLI、模型和 Python 环境；再检查 `mineru_bin` 配置。不要只检查 `marker_single`。
- MinerU 命令参数报错 -> 运行 `mineru --help`、`mineru-kit --help`，确认当前版本入口；旧版 `magic-pdf` 参数不能直接套用到新版 CLI。
- marker 在公式识别阶段崩溃(进程被信号杀死, 常见于部分 torch + Apple
  Silicon 组合) -> `deep_paper.py` 已内置自动降级: 检测到崩溃后会自动禁用
  `EquationProcessor` 重试一次(仍保留文本/图片/表格提取), 无需手动处理;
  若仍失败才会最终降级为仅摘要模式。
- Vault 路径不对 -> 显式设置环境变量 `NOTES_VAULT`, 或在 `config.local.json`
  中填写 `obsidian_vault`。
- ArXiv HTML 链接未被识别 -> 请更新到支持 `/html/` 的版本; 或改用
  `https://arxiv.org/abs/<id>`。
