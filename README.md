# 🛠️ Self-Skills: Universal AI Agent Skills Repository

> 一套跨平台、多客户端通用的大模型与 AI Coding Agent 技能（Skills）库。支持在 **Cursor**、**Claude Code**、**Antigravity**、**OpenAI Codex CLI** 和 **Gemini** 之间无缝共用与即插即用。

---

## 📦 技能矩阵 (Skills Catalog)

| 技能名称 (Skill) | 定位与核心功能 | 依赖环境 / 工具 | 典型触发场景 |
| :--- | :--- | :--- | :--- |
| **[`paper-reader`](./paper-reader)** | **深度学术论文/博客研读与知识库沉淀**<br>• 首选 **MinerU (`magic-pdf`)**：DocLayout-YOLO 版面检测 + UniMERNet 神经网络公式转录 + 独立高精图表切片<br>• 后备 **Marker**：快速降级提取<br>• 自动按分类归档至 Obsidian 知识库 (`20_Papers/`) 并同步资产 (`assets/<slug>/`) | Python 3.10+<br>`magic-pdf[full]`<br>`doclayout-yolo`<br>`marker-pdf` (可选) | 提供 arXiv URL、本地 PDF 或学术博客，要求“深度解读”、“整理笔记” |
| **[`auto-research-llm`](./auto-research-llm)** | **LLM 全流程自动化科研与训练套件**<br>• 数据清洗、Prompt 构造、Tokenization 预处理<br>• 训练全管线：SFT、LoRA/QLoRA、知识蒸馏、DPO、GRPO 等<br>• 评测与权重导出追踪 | PyTorch<br>Transformers<br>TRL / Deepspeed | 需要进行微调实验、强化学习对齐、蒸馏与基准评测 |
| **[`dataset-to-s3`](./dataset-to-s3)** | **大规模数据集/模型权重 S3 归档工具**<br>• 断点续传、MD5 完整性校验、分片并行上传<br>• 自动生成数据版本元信息 | AWS CLI / MinIO<br>Boto3 | 上传清洗后的数据集、Checkpoint 归档至云端对象存储 |
| **[`obsidian-clipper`](./obsidian-clipper)** | **通用网页智能剪藏与格式清洗**<br>• 去除网页噪点广告，提取主体正文与高清图片<br>• 规范化 YAML Frontmatter 与 Markdown 标签 | Readability<br>BeautifulSoup4 | 浏览技术文章、研报网页，需要一键剪藏至 Obsidian |

---

## ⚡ 快速开始 (Quick Start)

### 1. 一键软链安装至全部 AI Agent 客户端

运行自带的软链安装脚本，会自动将本仓库中的全部 Skills 建立符号链接（Symlink）至各大主流 Agent 框架的技能目录：

```bash
chmod +x install_all_links.sh
./install_all_links.sh
```

**自动分发的目标目录映射表：**

| 客户端 / Agent 框架 | 软链目标路径 |
| :--- | :--- |
| **Cursor IDE** | `~/.cursor/skills/<skill-name>` |
| **Google Antigravity** | `~/.gemini/config/skills/<skill-name>` |
| **Gemini CLI** | `~/.gemini/skills/<skill-name>` |
| **Anthropic Claude Code** | `~/.claude/skills/<skill-name>` |
| **OpenAI Codex CLI** | `~/.codex/skills/<skill-name>` 并且自动同步规则至 `~/.codex/AGENTS.md` |

---

## 🔧 重点技能配置与使用说明

### 📖 `paper-reader` 深度论文研读引擎

#### 1. MinerU (magic-pdf) 环境配置（推荐）

MinerU 具备极高的版面检测与公式识别精度，推荐在独立的 Conda 环境中部署：

```bash
# 1. 创建并激活独立环境
conda create -n pdfparse python=3.11 -y
conda activate pdfparse

# 2. 安装核心依赖
pip install --upgrade "magic-pdf[full]" modelscope doclayout-yolo rapid-table "transformers==4.47.1"

# 3. 下载模型权重并配置 ~/magic-pdf.json
# (模型自动下载至 ~/.cache/magic-pdf/models，并在配置文件中指定本地路径与 device-mode)
```

#### 2. 常用执行命令

```bash
# 方式 A: 深度解析 arXiv 论文并生成 Obsidian 笔记
python paper-reader/scripts/deep_paper.py "https://arxiv.org/abs/2601.07372" --slug engram

# 方式 B: 解析本地 PDF 文件
python paper-reader/scripts/deep_paper.py "/path/to/paper.pdf" --slug my-paper --category "Model_Architecture"

# 方式 C: 极速降级模式 (跳过深度图表提取，仅拉取摘要与纯文本)
python paper-reader/scripts/deep_paper.py "https://arxiv.org/abs/2501.12948" --force-text
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
