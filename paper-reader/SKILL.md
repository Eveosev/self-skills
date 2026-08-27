---
name: paper-reader
description: 抓取并分析论文/博客/网页 (ArXiv 论文默认走 marker 提图 + 结构化深度学术笔记, 普通网页走轻量总结), 自动分类归档到 Obsidian/笔记库。当用户给出 URL、ArXiv 链接或本地 PDF, 并要求总结、剪藏、精读、记笔记时使用。
---

# paper-reader

跨机器、跨客户端(Cursor / Claude Code / Codex / Antigravity / Gemini CLI 等)的
阅读分析技能。

**职责分工(重要)**:
- **脚本**只做确定性机械活: 拉元数据、下 PDF、marker 提图、拷贝 assets、写出
  `bundle.json`。**默认不调用任何外部 LLM API**。
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
pip install -r requirements.txt        # trafilatura requests arxiv
```
可选: 安装 [marker](https://github.com/datalab-to/marker)(提供 `marker_single`
命令)用于深度提图。未安装时深度解析会自动降级为"仅摘要"模式, 不会报错中断。

Vault 路径: 环境变量 `NOTES_VAULT` -> config 中的 `obsidian_vault` -> 自动探测
本技能所在 git 仓库根目录。**在本仓库内直接使用无需额外配置**。

> 外部 LLM API 凭据**仅**在显式使用 `--with-llm`(纯 CLI、无 Agent)时才需要。
> 正常 Agent 调用**不要**加 `--with-llm`, 也**不要**去读/填 API Key。

## Agent 标准工作流(默认, 必须遵循)

在 skill 目录下执行(或用绝对路径调用脚本):

```bash
# 自动判别: ArXiv/本地 PDF -> 深度准备; 普通网页 -> 轻量准备
# 支持 arxiv.org/abs|pdf|html/..., 以及纯 ID
python scripts/read.py "<URL 或 ArXiv 链接或本地 PDF 路径>"

# 强制轻量(论文也只准备摘要, 不跑 marker)
python scripts/read.py "<arxiv-url>" --light
```

脚本成功后会打印 `=== PAPER_READER_BUNDLE_BEGIN/END ===` 块, 并写出
`extracted/.../bundle.json`。然后 **你(Agent)** 继续:

### 论文深度笔记 (`mode: deep_paper`)
1. 读取 `bundle.template_path`(= `prompts/analyze_paper.md`)与
   `bundle.full_text_path`(全文过长时可头尾截断, 保留方法/实验/结论)。
2. 从 `bundle.categories` 选分类; 有 `category_override` 则优先; 都不合适用
   `Inbox`。
3. **用当前会话模型**按模板固定 Layout 生成中文学术笔记(frontmatter、固定
   二级标题、条件性「相关工作」、图片用
   `![...](../../assets/<slug>/<真实文件名>)`, 文件名只能来自
   `bundle.image_files`)。
4. 写入
   `{vault_path}/{papers_subdir}/<category>/<标题>.md`
   (可用 `filename_override`; 标题含冒号时 frontmatter 值必须加双引号;
   确保 frontmatter 有闭合的 `---`)。
5. 向用户回报笔记路径, 并简述一句话结论。可注明使用了 `paper-reader` 及
   (若 `marker_used`) `marker_single`。

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
2. 下 PDF; 有 `marker_single` 则提全文+图到 `extracted/` 与 `assets/<slug>/`。
3. 写出 `bundle.json`(含 meta、全文路径、图片清单、分类列表、模板路径)。
4. **Agent** 生成笔记并归档到 `20_Papers/<分类>/`。

## 跨客户端接入
```bash
bash scripts/install_links.sh
```
详见 [README.md](README.md) 与 [references/clients.md](references/clients.md)。
