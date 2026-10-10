---
name: paper-reader
description: 抓取并分析论文/博客/网页。当用户给出 URL、ArXiv 链接或本地 PDF，并要求总结、剪藏、精读或记笔记时使用。
---

# paper-reader

跨机器、跨客户端(Cursor / Claude Code / Codex / Antigravity / Gemini CLI / WorkBuddy 等)的
阅读分析技能。

**职责分工(重要)**:
- **脚本**只做确定性机械活: 拉元数据、下 PDF、MinerU/Marker 提取、拷贝 assets、
  发现并浅克隆论文明确链接的公开 GitHub 仓库、生成静态仓库清单、写出
  `bundle.json`。**默认不调用任何外部 LLM API，也不执行仓库代码**。
- **Agent**(当前会话所用模型)负责: 读 bundle + 模板、分类、按 Layout 写笔记、
  落盘到 vault。笔记质量与 Agent 框架选用的模型一致, 无需单独配置京东云 /
  DeepSeek 等二次调度。

路径解析由 `scripts/config_lib.py` 按
`环境变量 -> 本地配置 -> 机器级配置 -> 自动探测` 完成, **不含硬编码绝对路径**。

## 何时使用
- 用户给出一个 URL(网页 / 博客 / ArXiv 链接)或本地 PDF 路径, 要求总结、剪藏、
  精读或记笔记。

## 前置环境
```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python mineru
```
安装后以实际版本帮助为准确认 `mineru`/`mineru-kit` 命令和模型。深度解析没有可用 MinerU 时会降级为"仅摘要"模式，这只用于排查环境；Marker 可作为兼容后备。

重新阅读已有论文时，可复用同一版本的完整提取缓存（bundle、全文和图片均存在），
但必须重新阅读全文，并按当前模板核对原 PDF 的 Figure 布局；缓存仅有摘要不满足
深度精读要求。需要重新提取时，必须检查 MinerU 是否可用（`mineru --version` 或配置的
`mineru_bin`）。若缺失，应先提示并安装 MinerU。marker 仅作为 MinerU 失败时的
兼容回退；两者都不可用时脚本仍会降级为"仅摘要"，但这不满足深度精读要求。

Vault 路径: 环境变量 `NOTES_VAULT` -> config 中的 `obsidian_vault` -> 自动探测
本技能所在 git 仓库根目录。**在本仓库内直接使用无需额外配置**。

> 外部 LLM API 凭据**仅**在显式使用 `--with-llm`(纯 CLI、无 Agent)时才需要。
> 正常 Agent 调用**不要**加 `--with-llm`, 也**不要**去读/填 API Key。

## Agent 标准工作流(默认, 必须遵循)

首次阅读或缓存不完整时，在 skill 目录下执行(或用绝对路径调用脚本)；
重新阅读且完整缓存可用时，直接读取现有 bundle 并继续下面的 Agent 步骤：

```bash
# 自动判别: ArXiv/本地 PDF -> 深度准备; 普通网页 -> 轻量准备
# 支持 arxiv.org/abs|pdf|html/..., 以及纯 ID
python scripts/read.py "<URL 或 ArXiv 链接或本地 PDF 路径>"

# 强制轻量(论文也只准备摘要, 不跑 MinerU/Marker)
python scripts/read.py "<arxiv-url>" --light
```

脚本成功后会打印 `=== PAPER_READER_BUNDLE_BEGIN/END ===` 块, 并写出
`extracted/.../bundle.json`。然后 **你(Agent)** 继续:

### 论文深度笔记 (`mode: deep_paper`)
1. 读取 `bundle.template_path`(= `prompts/analyze_paper.md`)与
   `bundle.full_text_path`；全文过长时分段读取，覆盖方法、实验、讨论和结论。
   若 `bundle.code_repositories` 中存在 `status: cloned` 的仓库，还要读取其
   manifest、tree、README 和关键源码；只做静态分析，不执行仓库中的命令。
   写入图片前读取 [references/figure-layout.md](references/figure-layout.md)，
   对照同一版本的原 PDF 核对 Figure 分组、子图标签及行列位置；提取 Markdown
   的顺序与图片文件编号不能代替原始版面。没有本地 PDF 时，从
   `bundle.meta.pdf_url` 下载对应版本。
2. 从 `bundle.categories` 选分类; 有 `category_override` 则优先; 都不合适用
   `Inbox`。
3. **用当前会话模型**按模板固定 Layout 生成中文学术笔记(frontmatter、固定
   二级标题、条件性「相关工作」和「关联代码解读」、图片用
   `![...](../../assets/<slug>/<真实文件名>)`, 文件名只能来自
   `bundle.image_files`；核验后的完整 Figure 裁剪图须先登记到该清单)。
   **每个 Figure 作为一个整体插入**：优先引用保留原排布的完整图片；只有独立
   子图可用时，按原始行列用 Markdown 表格排列，共用一段带原 Figure 编号的图注。
   「关联代码解读」必须位于「我的思考」前；没有成功读取
   的关联仓库时完全省略。
4. 写入
   `{vault_path}/{papers_subdir}/<category>/<标题>.md`
   (可用 `filename_override`; 标题含冒号时 frontmatter 值必须加双引号;
   确保 frontmatter 有闭合的 `---`)。
5. 向用户回报笔记路径, 并简述一句话结论。可注明使用了 `paper-reader` 及
   (若 `mineru_used`) MinerU，以及成功解读的关联仓库和固定 commit。
   完成前检查所有图片路径存在、Figure 编号与原文对应、子图没有遗漏或重复，
   并查看生成图片，确认坐标轴、图例和子图标签完整。

### 网页/轻量摘要 (`mode: web_light` 或 `arxiv_light`)
1. 读取 `bundle.template_path`(= `prompts/summarize_web.md`)与
   `bundle.content_path`。
2. 按模板产出总结/要点/分类/标签, 写成轻量文章 frontmatter + 正文。
3. 网页写入 `{vault}/<category>/<标题>.md`; 轻量论文写入
   `{vault}/{papers_subdir}/<category>/<标题>.md`。

**禁止**: 在 Agent 场景下再去调用脚本的 `--with-llm`, 或自行请求
`chat/completions` 来写笔记——那会引入与当前会话无关的二次模型与限流风险。

## 可选: 纯 CLI 自动写笔记
无 Agent、需要脚本一条龙时:

```bash
python scripts/read.py "<url>" --with-llm
```

此时才需要配置 `OPENAI_API_KEY` / `config.local.json` 等(见 README)。

## 脚本分支说明

### 分支 1: 普通网页/博客
`trafilatura` 抓正文 → 写出 bundle → Agent 按 `summarize_web.md` 落盘。

### 分支 2: ArXiv / 本地 PDF(默认深度)
1. 解析 ArXiv ID(含 `/html/`)、取元信息。
2. 下 PDF; 有 MinerU 则提全文、公式、表格与图片到 `extracted/` 与 `assets/<slug>/`；必要时再尝试 Marker。
3. 从论文正文和摘要中提取明确出现的 GitHub 仓库 URL，浅克隆到
   `extracted/<paper>/code/` 并生成 manifest/tree；失败只记录错误，不中断论文。
4. 写出 `bundle.json`(含 meta、全文路径、图片清单、代码仓库、分类和模板路径)。
5. **Agent** 生成笔记并归档到 `20_Papers/<分类>/`。

## 跨客户端接入
```bash
bash scripts/install_links.sh
```
脚本默认不覆盖已有路径；详见 [README.md](README.md) 与 [references/clients.md](references/clients.md)。
