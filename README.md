# Self-Skills: Universal AI Agent Skills Repository

一套跨平台、多客户端通用的 AI Agent 技能库。技能源码只维护一份，换电脑时重新同步仓库，再按目标客户端注册即可。

---

## 📦 技能矩阵 (Skills Catalog)

| 技能名称 (Skill) | 定位与核心功能 | 依赖环境 / 工具 | 典型触发场景 |
| :--- | :--- | :--- | :--- |
| **[`paper-reader`](./paper-reader)** | **深度学术论文/博客研读与知识库沉淀**<br>• 首选 **MinerU**：版面检测、公式识别、表格和图片提取<br>• Marker 作为可选兼容后备<br>• 自动按分类归档至 Obsidian 知识库 (`20_Papers/`) 并同步资产 (`assets/<slug>/`) | Python 3.10+<br>MinerU 运行时<br>`trafilatura`、`requests`、`arxiv` | 提供 arXiv URL、本地 PDF 或学术博客，要求“深度解读”、“整理笔记” |
| **[`auto-research-llm`](./auto-research-llm)** | **LLM 全流程自动化科研与训练套件**<br>• 数据清洗、Prompt 构造、Tokenization 预处理<br>• 训练全管线：SFT、LoRA/QLoRA、知识蒸馏、DPO、GRPO 等<br>• 评测与权重导出追踪 | PyTorch<br>Transformers<br>TRL / Deepspeed | 需要进行微调实验、强化学习对齐、蒸馏与基准评测 |
| **[`dataset-to-s3`](./dataset-to-s3)** | **大规模数据集/模型权重 S3 归档工具**<br>• 断点续传、MD5 完整性校验、分片并行上传<br>• 自动生成数据版本元信息 | AWS CLI / MinIO<br>Boto3 | 上传清洗后的数据集、Checkpoint 归档至云端对象存储 |
| **[`obsidian-clipper`](./obsidian-clipper)** | **通用网页智能剪藏与格式清洗**<br>• 去除网页噪点广告，提取主体正文与高清图片<br>• 规范化 YAML Frontmatter 与 Markdown 标签 | Readability<br>BeautifulSoup4 | 浏览技术文章、研报网页，需要一键剪藏至 Obsidian |

---

## ⚡ 快速开始 (Quick Start)

### 1. 同步源码

新电脑推荐直接克隆主仓库和子模块：

```bash
git clone --recurse-submodules git@github.com:Eveosev/obsidian_notes.git
cd obsidian_notes
git submodule update --init --recursive
```

已有工作区更新：

```bash
git pull --recurse-submodules
git submodule update --init --recursive
```

`git submodule update --remote --merge` 会升级子模块指针，属于主动升级操作，不是普通初始化步骤。

### 2. 安装 paper-reader 运行时

深度论文解析要求 MinerU。建议使用独立 Python 3.11 环境，避免污染 Agent 或系统 Python：

```bash
cd 90_Meta/Skills/paper-reader
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python mineru
```

不同 MinerU 版本的命令名和模型管理命令可能不同，安装后先确认实际 CLI：

```bash
.venv/bin/mineru --help
.venv/bin/mineru-kit --help       # 若该版本提供 mineru-kit
.venv/bin/mineru-models-download --help  # 若该版本提供模型下载器
```

如果安装版本提供以下命令，下载并校验 basic 模型；命令不存在时按 `--help` 选择对应入口：

```bash
.venv/bin/mineru-models-download --tier basic --source modelscope
.venv/bin/mineru-kit models verify --tier basic
```

不要把 `magic-pdf` 的旧参数直接复制给新版 `mineru-kit`。

### 3. 注册到 Agent 客户端

运行 paper-reader 的接入脚本。脚本只处理已存在的客户端目录，默认不会覆盖已有文件或软链接：

```bash
bash 90_Meta/Skills/paper-reader/scripts/install_links.sh
```

需要替换错误链接时显式使用 `--force`。Codex 的 `AGENTS.md` 不会被脚本覆盖，请按 [客户端说明](./paper-reader/references/clients.md) 手动追加引用。

**自动分发的目标目录映射表：**

| 客户端 / Agent 框架 | 软链目标路径 |
| :--- | :--- |
| **Cursor IDE** | `~/.cursor/skills/<skill-name>` |
| **Google Antigravity** | `~/.gemini/config/skills/<skill-name>` |
| **Gemini CLI** | `~/.gemini/skills/<skill-name>` |
| **Anthropic Claude Code** | `~/.claude/skills/<skill-name>` |
| **OpenAI Codex CLI** | 在 `AGENTS.md` 中引用 skill；脚本不会覆盖已有规则 |

---

## 🔧 重点技能配置与使用说明

### 📖 `paper-reader` 深度论文研读引擎

#### 常用执行命令

```bash
# 方式 A: 准备 arXiv 论文材料，由当前 Agent 生成 Obsidian 笔记
90_Meta/Skills/paper-reader/.venv/bin/python 90_Meta/Skills/paper-reader/scripts/read.py "https://arxiv.org/abs/2601.07372"

# 方式 B: 解析本地 PDF 文件
90_Meta/Skills/paper-reader/.venv/bin/python 90_Meta/Skills/paper-reader/scripts/read.py "/path/to/paper.pdf"

# 方式 C: 极速降级模式 (跳过深度图表提取，仅拉取摘要与纯文本)
90_Meta/Skills/paper-reader/.venv/bin/python 90_Meta/Skills/paper-reader/scripts/read.py "https://arxiv.org/abs/2501.12948" --light
```

---

## 🔄 Git Submodule 协作与维护指南

当本仓库作为主项目（如 Obsidian 笔记库）的 **Git Submodule** 时：

### 1. 新机器克隆主仓库（含 Submodule）
```bash
git clone --recurse-submodules git@github.com:Eveosev/obsidian_notes.git
```

### 2. 已有主仓库拉取与同步 Submodule 最新代码
```bash
# 初始化并同步子模块
git submodule update --init --recursive

# 拉取子模块的远程最新更新
git submodule update --remote --merge
```

### 3. 在 Submodule 中开发与提交
```bash
cd 90_Meta/Skills  # 进入子模块目录
git checkout main
# 进行技能修改或新增技能...
git add .
git commit -m "feat: add new skill"
git push origin main

# 返回父仓库更新指针
cd ../..
git add 90_Meta/Skills
git commit -m "chore: update skills submodule reference"
git push origin main
```

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 授权。
