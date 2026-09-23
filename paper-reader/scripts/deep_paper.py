#!/usr/bin/env python3
"""
paper-reader 深度论文解析流水线。

默认 (Agent 模式 / prepare-only):
  下载 ArXiv PDF -> (可用则) marker 提取文本与图片 -> 拷贝图片到 assets/<slug>/
  -> 写出 bundle.json, 由调用方 Agent 用当前会话模型按 prompts/analyze_paper.md
  生成笔记并落盘。脚本本身不调用任何外部 LLM API。

可选 (--with-llm):
  在 prepare 完成后额外用配置的 OpenAI 兼容 API 自动分类并生成笔记
  (仅适合纯 CLI / 无 Agent 场景)。

marker 未安装或提取失败时自动降级为"仅摘要"模式, 不会中断流程。
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import arxiv

import config_lib as cfg

ARXIV_ID_RE = re.compile(r'(\d{4}\.\d{4,5})(v\d+)?')
IMAGE_EXTS = {".jpeg", ".jpg", ".png"}

# marker 的默认处理器管线里, EquationProcessor / LLMEquationProcessor 在部分
# 环境(观测到于某些 torch + Apple Silicon MPS 组合)下会在公式 OCR 阶段稳定
# 触发 segfault。发生崩溃时自动降级为不含这两个处理器的安全管线重试一次,
# 代价是公式不会被单独识别渲染, 但正文、图片、表格等其余内容仍能正常提取。
SAFE_PROCESSORS = ",".join([
    "marker.processors.order.OrderProcessor",
    "marker.processors.block_relabel.BlockRelabelProcessor",
    "marker.processors.line_merge.LineMergeProcessor",
    "marker.processors.blockquote.BlockquoteProcessor",
    "marker.processors.code.CodeProcessor",
    "marker.processors.document_toc.DocumentTOCProcessor",
    "marker.processors.footnote.FootnoteProcessor",
    "marker.processors.ignoretext.IgnoreTextProcessor",
    "marker.processors.line_numbers.LineNumbersProcessor",
    "marker.processors.list.ListProcessor",
    "marker.processors.page_header.PageHeaderProcessor",
    "marker.processors.sectionheader.SectionHeaderProcessor",
    "marker.processors.table.TableProcessor",
    "marker.processors.llm.llm_table.LLMTableProcessor",
    "marker.processors.llm.llm_table_merge.LLMTableMergeProcessor",
    "marker.processors.llm.llm_form.LLMFormProcessor",
    "marker.processors.text.TextProcessor",
    "marker.processors.llm.llm_complex.LLMComplexRegionProcessor",
    "marker.processors.llm.llm_image_description.LLMImageDescriptionProcessor",
    "marker.processors.llm.llm_handwriting.LLMHandwritingProcessor",
    "marker.processors.llm.llm_mathblock.LLMMathBlockProcessor",
    "marker.processors.llm.llm_sectionheader.LLMSectionHeaderProcessor",
    "marker.processors.llm.llm_page_correction.LLMPageCorrectionProcessor",
    "marker.processors.reference.ReferenceProcessor",
    "marker.processors.blank_page.BlankPageProcessor",
])

PROMPTS_DIR = cfg.SKILL_DIR / "prompts"
ANALYZE_TEMPLATE_PATH = PROMPTS_DIR / "analyze_paper.md"


def parse_arxiv_id(url_or_id: str) -> str:
    match = ARXIV_ID_RE.search(url_or_id)
    if not match:
        raise ValueError(f"无法从输入中解析出 ArXiv ID: {url_or_id}")
    return match.group(1)


def fetch_arxiv_metadata(arxiv_id: str):
    search = arxiv.Search(id_list=[arxiv_id])
    try:
        if hasattr(arxiv, "Client"):
            client = arxiv.Client()
            paper = next(client.results(search))
        else:
            paper = next(search.results())
    except StopIteration:
        raise RuntimeError(f"在 ArXiv 上找不到论文: {arxiv_id}")
    return {
        "title": paper.title.strip().replace("\n", " "),
        "authors": ", ".join(a.name for a in paper.authors),
        "abstract": paper.summary.strip(),
        "published": paper.published.strftime("%Y-%m-%d") if paper.published else "",
        "pdf_url": paper.pdf_url,
        "entry_id": paper.entry_id,
    }


def download_pdf(pdf_url: str, arxiv_id: str, tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / f"{arxiv_id}.pdf"
    print(f"正在下载 PDF: {pdf_url}")
    import urllib.request
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    return dest


def _run_marker_once(marker_bin: str, pdf_path: Path, extracted_root: Path, processors: str = None) -> Path:
    extracted_root.mkdir(parents=True, exist_ok=True)
    cmd = [marker_bin, str(pdf_path), "--output_format", "markdown", "--output_dir", str(extracted_root)]
    if processors:
        cmd += ["--processors", processors]
    print(f"正在运行 marker 提取文本与图片: {' '.join(cmd)}")
    env = os.environ.copy()
    env["TORCH_DEVICE"] = "cpu"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"marker 执行失败(returncode={result.returncode}): {result.stderr[-500:]}", file=sys.stderr)
        return None

    stem = pdf_path.stem
    candidate_dir = extracted_root / stem
    md_candidates = list(candidate_dir.glob("*.md")) if candidate_dir.exists() else []
    if not md_candidates:
        md_candidates = list(extracted_root.rglob(f"{stem}*.md"))
    return md_candidates[0] if md_candidates else None


def run_mineru(mineru_bin: str, pdf_path: Path, extracted_root: Path) -> Path:
    """
    运行不同代际的 MinerU CLI, 返回生成的 markdown 文件路径。

    MinerU 的 CLI 在不同版本间从 magic-pdf 风格参数迁移到了 mineru-kit
    子命令。这里保留多个候选命令，避免安装成功后因为 CLI 代际不同而静默降级。
    """
    extracted_root.mkdir(parents=True, exist_ok=True)
    before = {p.resolve() for p in extracted_root.rglob("*.md")}
    binary_name = Path(mineru_bin).name
    modern_commands = [
        [mineru_bin, "parse", "PDF", str(pdf_path), "--output", str(extracted_root),
         "--format", "markdown", "--tier", "basic", "--ocr-mode", "auto"],
        [mineru_bin, "parse", str(pdf_path), "--output", str(extracted_root),
         "--format", "markdown", "--tier", "basic", "--ocr-mode", "auto"],
        [mineru_bin, "parse", "-p", str(pdf_path), "-o", str(extracted_root)],
    ]
    legacy_command = [mineru_bin, "-p", str(pdf_path), "-o", str(extracted_root), "-m", "auto"]
    commands = modern_commands + [legacy_command] if binary_name == "mineru-kit" else [legacy_command] + modern_commands

    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    last_error = ""
    for cmd in commands:
        print(f"正在运行 MinerU 提取高精文本、公式与图片: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            last_error = result.stderr[-500:] or result.stdout[-500:]
            continue

        candidate_mds = [p for p in extracted_root.rglob("*.md") if p.resolve() not in before]
        if not candidate_mds:
            candidate_mds = list(extracted_root.rglob(f"{pdf_path.stem}*.md"))
        if candidate_mds:
            return sorted(candidate_mds)[0]

    if last_error:
        print(f"MinerU 执行失败: {last_error}", file=sys.stderr)
    return None


def collect_mineru_images(mineru_md_path: Path) -> list:
    """
    收集 MinerU 提取的图片切片 (通常在 markdown 同级的 images/ 目录下)。
    """
    images_dir = mineru_md_path.parent / "images"
    if images_dir.exists() and images_dir.is_dir():
        return sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    return sorted(p for p in mineru_md_path.parent.iterdir() if p.suffix.lower() in IMAGE_EXTS)


def run_marker(marker_bin: str, pdf_path: Path, extracted_root: Path) -> Path:
    """
    运行 marker_single, 返回生成的 markdown 文件路径(彻底失败则返回 None)。
    优先使用 SAFE_PROCESSORS 安全管线(禁用 CPU/MPS 上极慢且易崩的 EquationProcessor),
    确保在 10~20 秒内高精提取正文、表格和全部 Figure/Picture 单图切片。
    """
    md_path = _run_marker_once(marker_bin, pdf_path, extracted_root, processors=SAFE_PROCESSORS)
    if md_path:
        return md_path

    print("SAFE_PROCESSORS 失败, 尝试默认管线重试一次...")
    return _run_marker_once(marker_bin, pdf_path, extracted_root)


def collect_images(marker_md_path: Path) -> list:
    return sorted(
        p for p in marker_md_path.parent.iterdir()
        if p.suffix.lower() in IMAGE_EXTS
    )


def copy_assets(image_paths: list, vault_path: Path, slug: str) -> list:
    if not image_paths:
        return []
    assets_dir = vault_path / "assets" / slug
    assets_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in image_paths:
        dest = assets_dir / src.name
        shutil.copyfile(src, dest)
        copied.append(src.name)
    return copied


def classify_category(client, model: str, title: str, abstract: str, categories: list) -> str:
    prompt = f"""请从下面的现有分类列表中选择最适合这篇论文的一个分类。
如果都不合适, 返回 "Inbox"。严格输出 JSON: {{"category": "选择结果"}}

现有分类列表: {', '.join(categories) if categories else '(空)'}

论文标题: {title}
论文摘要: {abstract[:800]}
"""
    content = client.chat(
        messages=[{"role": "user", "content": prompt}],
        json_mode=True,
        model=model,
    )
    try:
        data = json.loads(content)
        return data.get("category") or "Inbox"
    except (json.JSONDecodeError, TypeError):
        return "Inbox"


def build_generation_prompt(template_text: str, meta: dict, full_text: str, slug: str, image_files: list) -> str:
    if image_files:
        image_list_str = "\n".join(f"- {name}" for name in image_files)
        image_reminder = f"""
## 再次提醒: 关于插图(务必执行, 不要忽略)

本文可用的真实图片文件名如下, 请在通读上面的论文正文后, 找出每个文件名在
正文中紧邻的 "Figure N ..." 说明文字, 判断它对应哪个 Figure, 并把它嵌入到
生成笔记中讨论该 Figure 内容的章节里(用 `![Figure N: 说明](../../assets/{slug}/文件名)`)。
除非某个文件确实在正文中找不到任何说明文字, 否则都应该被使用, **不要整篇笔记
都不插图**:
{image_list_str}
"""
    else:
        image_reminder = "\n## 关于插图\n本文没有可用图片, 不需要插图。\n"

    context = f"""
## 运行时上下文

- 标题: {meta['title']}
- 作者: {meta['authors']}
- 来源 URL: {meta['entry_id']}
- 日期: {meta['published']}
- 资产目录名 slug: {slug}

## 论文正文(可能是全文或仅摘要, 视 marker 是否可用而定)

{full_text}
"""
    return template_text + "\n\n" + context + image_reminder


def generate_note(client, model: str, template_text: str, meta: dict, full_text: str, slug: str, image_files: list) -> str:
    prompt = build_generation_prompt(template_text, meta, full_text, slug, image_files)
    print("正在调用 LLM 生成深度学术笔记...")
    content = client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
    ).strip()
    content = re.sub(r'^```(?:markdown)?\n', '', content)
    content = re.sub(r'\n```$', '', content)
    content = content.replace("<model>", model)
    content = _ensure_frontmatter_closed(content)
    content = _quote_frontmatter_values(content)
    return content


def _ensure_frontmatter_closed(content: str) -> str:
    """
    模型偶尔会漏写 frontmatter 的第二个 `---` 分隔符, 导致 YAML 块与正文
    混在一起(Obsidian 无法正确解析)。这里做一次轻量修复: 若开头是 `---`
    但在正文第一个一级标题之前找不到闭合的 `---`, 就在该标题前补上一个。
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return content

    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return content  # 已有闭合分隔符

    for i in range(1, len(lines)):
        if lines[i].startswith('# '):
            insert_at = i
            while insert_at > 1 and lines[insert_at - 1].strip() == '':
                insert_at -= 1
            lines.insert(insert_at, '---')
            lines.insert(insert_at, '')
            return '\n'.join(lines)

    return content


_FRONTMATTER_KV_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):[ \t](.*)$')


def _quote_frontmatter_values(content: str) -> str:
    """
    模型偶尔会输出诸如 `title: DAPO: An Open-Source ...` 这类论文标题本身
    带冒号的字段, 未加引号时是非法 YAML(会被解析成一个新的 mapping),
    导致 Obsidian 整段 frontmatter 解析失败、原样显示为正文文本。这里对
    frontmatter 区块内明显需要加引号的字段值做一次保护性加引号。
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return content

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    if end_idx is None:
        return content

    for i in range(1, end_idx):
        match = _FRONTMATTER_KV_RE.match(lines[i])
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        value = value.strip()
        if not value or value[0] in '"\'[{':
            continue
        needs_quote = (': ' in value) or (value[0] in '*&!|>%@`#')
        if not needs_quote:
            continue
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        lines[i] = f'{key}: "{escaped}"'

    return '\n'.join(lines)


def save_note(
    vault_path: Path,
    category: str,
    title: str,
    content: str,
    papers_subdir: str = "20_Papers",
    filename_override: str = None,
) -> Path:
    folder = vault_path / papers_subdir / category
    folder.mkdir(parents=True, exist_ok=True)
    filename = filename_override or (cfg.sanitize_filename(title) + ".md")
    if not filename.endswith(".md"):
        filename += ".md"
    dest = folder / filename
    dest.write_text(content, encoding="utf-8")
    return dest


def write_bundle(bundle_dir: Path, bundle: dict) -> Path:
    """写出 bundle.json, 并在 stdout 打印供 Agent 解析的标记块。"""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / "bundle.json"
    bundle = dict(bundle)
    bundle["bundle_path"] = str(bundle_path)
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== PAPER_READER_BUNDLE_BEGIN ===")
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    print("=== PAPER_READER_BUNDLE_END ===")
    print(f"已写出准备包: {bundle_path}")
    print(
        "下一步(Agent): 读取 template_path 与 full_text_path, 用当前会话模型按 "
        "prompts/analyze_paper.md 的 Layout 生成中文学术笔记, 写入 "
        f"{bundle.get('papers_subdir', '20_Papers')}/<category>/<标题>.md "
        "(category 从 categories 中选, 或用 category_override; 无合适则 Inbox)。"
        "不要调用外部 LLM API。"
    )
    return bundle_path


def _ensure_text_file(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def prepare_arxiv(
    url_or_id: str,
    config: dict = None,
    slug_override: str = None,
    force_text: bool = False,
    category_override: str = None,
    papers_subdir: str = "20_Papers",
    keep_tmp: bool = False,
    filename_override: str = None,
) -> dict:
    """机械准备: 元数据 + PDF/marker/assets。不调用 LLM。返回 bundle dict。"""
    config = config or cfg.load_config()
    vault_path = cfg.get_vault_path(config)

    arxiv_id = parse_arxiv_id(url_or_id)
    meta = fetch_arxiv_metadata(arxiv_id)
    slug = slug_override or cfg.slugify(meta["title"])
    print(f"论文: {meta['title']}  (slug={slug})")

    extracted_root = vault_path / "extracted"
    bundle_dir = extracted_root / arxiv_id
    full_text = meta["abstract"]
    full_text_path = None
    image_files = []
    extractor_used = None

    mineru_bin = None if force_text else cfg.find_mineru_binary(config)
    marker_bin = None if force_text else cfg.find_marker_binary(config)
    tmp_dir = cfg.SKILL_DIR / "_tmp"

    if mineru_bin:
        pdf_path = download_pdf(meta["pdf_url"], arxiv_id, tmp_dir)
        md_path = run_mineru(mineru_bin, pdf_path, extracted_root)
        if md_path and md_path.exists():
            full_text = md_path.read_text(encoding="utf-8")
            full_text_path = md_path
            image_paths = collect_mineru_images(md_path)
            image_files = copy_assets(image_paths, vault_path, slug)
            extractor_used = "mineru"
            print(f"MinerU 提取成功: 正文 {len(full_text)} 字符, 图片 {len(image_files)} 张 -> assets/{slug}/")
        else:
            print("MinerU 执行未产出有效结果, 尝试降级至 marker...")

    if extractor_used is None and marker_bin:
        pdf_file = tmp_dir / f"{arxiv_id}.pdf"
        if not pdf_file.exists():
            pdf_path = download_pdf(meta["pdf_url"], arxiv_id, tmp_dir)
        else:
            pdf_path = pdf_file
        md_path = run_marker(marker_bin, pdf_path, extracted_root)
        if md_path and md_path.exists():
            full_text = md_path.read_text(encoding="utf-8")
            full_text_path = md_path
            image_paths = collect_images(md_path)
            image_files = copy_assets(image_paths, vault_path, slug)
            extractor_used = "marker"
            print(f"marker 提取成功: 正文 {len(full_text)} 字符, 图片 {len(image_files)} 张 -> assets/{slug}/")
        else:
            print("marker 未产出有效结果, 降级为仅摘要模式。")

    if not keep_tmp:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if extractor_used is None:
        print("未检测到有效 PDF 解析引擎 (或指定 --force-text), 降级为仅摘要模式。")

    if full_text_path is None:
        full_text_path = _ensure_text_file(bundle_dir / "abstract.md", full_text)

    categories = cfg.get_paper_categories(vault_path, papers_subdir)
    assets_dir = vault_path / "assets" / slug

    bundle = {
        "mode": "deep_paper",
        "status": "prepared",
        "source_type": "arxiv",
        "arxiv_id": arxiv_id,
        "meta": meta,
        "slug": slug,
        "vault_path": str(vault_path),
        "papers_subdir": papers_subdir,
        "categories": categories,
        "category_override": category_override,
        "filename_override": filename_override,
        "full_text_path": str(full_text_path),
        "full_text_chars": len(full_text),
        "image_files": image_files,
        "assets_dir": str(assets_dir),
        "assets_rel": f"assets/{slug}",
        "template_path": str(ANALYZE_TEMPLATE_PATH),
        "extractor_used": extractor_used,
        "marker_used": extractor_used == "marker",
        "mineru_used": extractor_used == "mineru",
        "note_hint": (
            f"目标路径: {{vault}}/{papers_subdir}/<category>/"
            f"{filename_override or (cfg.sanitize_filename(meta['title']) + '.md')}"
        ),
    }
    write_bundle(bundle_dir, bundle)
    print(f"深度模式引擎: {extractor_used or '无(降级仅摘要)'}")
    return bundle


def prepare_local_pdf(
    pdf_path: str,
    config: dict = None,
    slug_override: str = None,
    force_text: bool = False,
    category_override: str = None,
    papers_subdir: str = "20_Papers",
    filename_override: str = None,
) -> dict:
    """本地 PDF 机械准备。不调用 LLM。"""
    config = config or cfg.load_config()
    vault_path = cfg.get_vault_path(config)

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    title_guess = pdf_path.stem.replace('_', ' ').replace('-', ' ').strip() or "Untitled"
    slug = slug_override or cfg.slugify(title_guess)
    meta = {
        "title": title_guess,
        "authors": "",
        "abstract": "",
        "published": datetime.date.today().isoformat(),
        "pdf_url": None,
        "entry_id": str(pdf_path),
    }

    extracted_root = vault_path / "extracted"
    bundle_dir = extracted_root / slug
    full_text = ""
    full_text_path = None
    image_files = []
    extractor_used = None

    mineru_bin = None if force_text else cfg.find_mineru_binary(config)
    marker_bin = None if force_text else cfg.find_marker_binary(config)

    if mineru_bin:
        md_path = run_mineru(mineru_bin, pdf_path, extracted_root)
        if md_path and md_path.exists():
            full_text = md_path.read_text(encoding="utf-8")
            full_text_path = md_path
            image_paths = collect_mineru_images(md_path)
            image_files = copy_assets(image_paths, vault_path, slug)
            extractor_used = "mineru"
            first_heading = next(
                (line.lstrip('#').strip() for line in full_text.splitlines() if line.strip().startswith('#')),
                None,
            )
            if first_heading:
                meta["title"] = first_heading
            print(f"MinerU 提取成功: 正文 {len(full_text)} 字符, 图片 {len(image_files)} 张 -> assets/{slug}/")
        else:
            print("MinerU 执行未产出有效结果, 尝试降级至 marker...")

    if extractor_used is None and marker_bin:
        md_path = run_marker(marker_bin, pdf_path, extracted_root)
        if md_path and md_path.exists():
            full_text = md_path.read_text(encoding="utf-8")
            full_text_path = md_path
            image_paths = collect_images(md_path)
            image_files = copy_assets(image_paths, vault_path, slug)
            extractor_used = "marker"
            first_heading = next(
                (line.lstrip('#').strip() for line in full_text.splitlines() if line.strip().startswith('#')),
                None,
            )
            if first_heading:
                meta["title"] = first_heading
            print(f"marker 提取成功: 正文 {len(full_text)} 字符, 图片 {len(image_files)} 张 -> assets/{slug}/")
        else:
            print("marker 未产出有效结果, 本地 PDF 深度解析失败, 仅使用文件名作为标题。")

    if extractor_used is None:
        print("未检测到有效 PDF 解析引擎, 本地 PDF 无法提取正文, 仅使用文件名作为标题。")

    if not full_text:
        full_text = f"(未能提取正文, 仅有文件名: {pdf_path.name})"
    if full_text_path is None:
        full_text_path = _ensure_text_file(bundle_dir / "abstract.md", full_text)

    categories = cfg.get_paper_categories(vault_path, papers_subdir)
    assets_dir = vault_path / "assets" / slug

    bundle = {
        "mode": "deep_paper",
        "status": "prepared",
        "source_type": "local_pdf",
        "arxiv_id": None,
        "meta": meta,
        "slug": slug,
        "vault_path": str(vault_path),
        "papers_subdir": papers_subdir,
        "categories": categories,
        "category_override": category_override,
        "filename_override": filename_override,
        "full_text_path": str(full_text_path),
        "full_text_chars": len(full_text),
        "image_files": image_files,
        "assets_dir": str(assets_dir),
        "assets_rel": f"assets/{slug}",
        "template_path": str(ANALYZE_TEMPLATE_PATH),
        "extractor_used": extractor_used,
        "marker_used": extractor_used == "marker",
        "mineru_used": extractor_used == "mineru",
        "note_hint": (
            f"目标路径: {{vault}}/{papers_subdir}/<category>/"
            f"{filename_override or (cfg.sanitize_filename(meta['title']) + '.md')}"
        ),
    }
    write_bundle(bundle_dir, bundle)
    print(f"深度模式引擎: {extractor_used or '无(降级)'}")
    return bundle


def generate_note_from_bundle(
    bundle: dict,
    config: dict = None,
) -> Path:
    """可选: 用外部 LLM API 从 bundle 生成并保存笔记。"""
    config = config or cfg.load_config()
    client, model = cfg.get_openai_client(config)
    vault_path = Path(bundle["vault_path"])
    meta = bundle["meta"]
    slug = bundle["slug"]
    papers_subdir = bundle.get("papers_subdir") or "20_Papers"
    full_text = Path(bundle["full_text_path"]).read_text(encoding="utf-8")
    image_files = bundle.get("image_files") or []
    categories = bundle.get("categories") or []

    category = bundle.get("category_override") or classify_category(
        client, model, meta["title"], meta.get("abstract") or meta["title"], categories
    )
    print(f"分类: {category}")

    template_text = ANALYZE_TEMPLATE_PATH.read_text(encoding="utf-8")
    note_content = generate_note(client, model, template_text, meta, full_text, slug, image_files)
    dest = save_note(
        vault_path,
        category,
        meta["title"],
        note_content,
        papers_subdir,
        bundle.get("filename_override"),
    )
    print(f"已保存笔记: {dest}")
    return dest


def run(
    url_or_id: str,
    config: dict = None,
    slug_override: str = None,
    force_text: bool = False,
    category_override: str = None,
    papers_subdir: str = "20_Papers",
    keep_tmp: bool = False,
    filename_override: str = None,
    with_llm: bool = False,
):
    """默认只 prepare; with_llm=True 时再调外部 API 生成笔记。"""
    bundle = prepare_arxiv(
        url_or_id,
        config=config,
        slug_override=slug_override,
        force_text=force_text,
        category_override=category_override,
        papers_subdir=papers_subdir,
        keep_tmp=keep_tmp,
        filename_override=filename_override,
    )
    if with_llm:
        return generate_note_from_bundle(bundle, config=config)
    return bundle


def run_from_local_pdf(
    pdf_path: str,
    config: dict = None,
    slug_override: str = None,
    force_text: bool = False,
    category_override: str = None,
    papers_subdir: str = "20_Papers",
    filename_override: str = None,
    with_llm: bool = False,
):
    """本地 PDF: 默认只 prepare; with_llm=True 时再调外部 API 生成笔记。"""
    bundle = prepare_local_pdf(
        pdf_path,
        config=config,
        slug_override=slug_override,
        force_text=force_text,
        category_override=category_override,
        papers_subdir=papers_subdir,
        filename_override=filename_override,
    )
    if with_llm:
        return generate_note_from_bundle(bundle, config=config)
    return bundle


def main():
    parser = argparse.ArgumentParser(
        description="paper-reader 深度论文解析 (默认只准备材料, 由 Agent 写笔记)"
    )
    parser.add_argument("url_or_id", help="ArXiv URL 或 ID, 例如 2503.14476")
    parser.add_argument("--config", help="显式指定 config.json 路径")
    parser.add_argument("--slug", help="覆盖自动生成的资产目录名(assets/<slug>/)")
    parser.add_argument("--category", help="覆盖分类, 直接指定 20_Papers/ 下的子目录名")
    parser.add_argument("--filename", help="覆盖输出文件名(不含目录, 便于原地覆盖已有笔记)")
    parser.add_argument("--force-text", action="store_true", help="跳过 marker, 强制仅摘要模式")
    parser.add_argument("--papers-subdir", default="20_Papers", help="论文归档的顶层子目录, 默认 20_Papers")
    parser.add_argument("--keep-tmp", action="store_true", help="保留下载的临时 PDF, 便于调试")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="可选: 用配置的外部 LLM API 自动生成笔记(默认关闭; Agent 场景请勿使用)",
    )
    args = parser.parse_args()

    config = cfg.load_config(args.config)
    try:
        input_target = args.url_or_id.strip()
        if Path(input_target).exists() or input_target.lower().endswith(".pdf"):
            run_from_local_pdf(
                input_target,
                config=config,
                slug_override=args.slug,
                force_text=args.force_text,
                category_override=args.category,
                papers_subdir=args.papers_subdir,
                filename_override=args.filename,
                with_llm=args.with_llm,
            )
        else:
            run(
                input_target,
                config=config,
                slug_override=args.slug,
                force_text=args.force_text,
                category_override=args.category,
                papers_subdir=args.papers_subdir,
                keep_tmp=args.keep_tmp,
                filename_override=args.filename,
                with_llm=args.with_llm,
            )
    except cfg.ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"处理失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
