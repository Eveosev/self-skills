#!/usr/bin/env python3
"""
paper-reader 统一入口。

自动判别输入类型:
- ArXiv 链接/ID、本地 .pdf 文件 -> 视为"论文", 默认走深度准备(marker 提图),
  由 Agent 按 prompts/analyze_paper.md 写笔记; --light 可强制退化为快速摘要准备。
- 其他网页/博客 URL -> 轻量抓取准备(不涉及 marker), 由 Agent 按
  prompts/summarize_web.md 写笔记。

默认不调用外部 LLM API。仅在显式传入 --with-llm 时用配置的 API 自动写笔记
(适合纯 CLI / 无 Agent 场景)。
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import trafilatura

import config_lib as cfg
import deep_paper

# 兼容 abs / pdf / html / 纯 ID
ARXIV_PATTERN = re.compile(
    r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?'
    r'|^\d{4}\.\d{4,5}(?:v\d+)?$',
    re.IGNORECASE,
)
SUMMARIZE_TEMPLATE_PATH = cfg.SKILL_DIR / "prompts" / "summarize_web.md"


def detect_type(source: str) -> str:
    if ARXIV_PATTERN.search(source.strip()):
        return "arxiv"
    if source.lower().endswith(".pdf") and Path(source).exists():
        return "local_pdf"
    return "web"


def fetch_web_content(url: str) -> dict:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise RuntimeError("无法下载网页内容")
    text = trafilatura.extract(downloaded)
    title_json = trafilatura.extract(downloaded, output_format="json")
    title = json.loads(title_json).get("title", "Untitled") if title_json else "Untitled"
    return {"title": title, "content": (text or "")[:8000], "url": url}


def summarize_light(client, model: str, title: str, content: str, categories: list) -> dict:
    template = SUMMARIZE_TEMPLATE_PATH.read_text(encoding="utf-8")
    prompt = f"""{template}

## 运行时上下文
现有分类列表: {', '.join(categories) if categories else '(空)'}
内容标题: {title}
内容正文(节选): {content[:3000]}
"""
    content = client.chat(
        messages=[{"role": "user", "content": prompt}],
        json_mode=True,
        model=model,
    )
    return json.loads(content)


def save_light_note(base_dir: Path, category: str, title: str, url: str, content: str, analysis: dict) -> Path:
    folder = base_dir / (category or "Inbox")
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{cfg.sanitize_filename(title)}.md"

    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags = analysis.get("tags", [])
    tags_str = ("\n  - " + "\n  - ".join(tags)) if tags else " []"
    points_str = "\n".join(f"- {p}" for p in analysis.get("key_points", []))

    md = f"""---
title: "{title}"
source: {url}
date: {date_str}
tags:{tags_str}
type: article
---

# {title}

来源链接: [点击访问]({url})

## AI 总结
> {analysis.get('summary', '')}

## 核心要点
{points_str}

---
## 原文备份(节选)
{content[:2000]}
"""
    dest.write_text(md, encoding="utf-8")
    return dest


def prepare_light_web(url: str, config: dict) -> dict:
    """抓取网页正文并写出 bundle, 不调用 LLM。"""
    vault_path = cfg.get_vault_path(config)
    data = fetch_web_content(url)
    categories = cfg.get_general_categories(vault_path)

    slug = cfg.slugify(data["title"] or "web")
    bundle_dir = vault_path / "extracted" / f"web_{slug}"
    content_path = deep_paper._ensure_text_file(bundle_dir / "content.md", data["content"])

    bundle = {
        "mode": "web_light",
        "status": "prepared",
        "source_type": "web",
        "meta": {
            "title": data["title"],
            "authors": "",
            "abstract": "",
            "published": datetime.date.today().isoformat(),
            "pdf_url": None,
            "entry_id": data["url"],
        },
        "url": data["url"],
        "slug": slug,
        "vault_path": str(vault_path),
        "papers_subdir": None,
        "categories": categories,
        "category_override": None,
        "content_path": str(content_path),
        "content_chars": len(data["content"]),
        "template_path": str(SUMMARIZE_TEMPLATE_PATH),
        "note_layout": "light_article",
        "note_hint": "目标路径: {vault}/<category>/<标题>.md (category 从 categories 选, 或 Inbox)",
    }
    deep_paper.write_bundle(bundle_dir, bundle)
    return bundle


def prepare_light_arxiv(source: str, config: dict, papers_subdir: str) -> dict:
    """仅用 ArXiv 摘要准备轻量 bundle, 不跑 marker、不调用 LLM。"""
    vault_path = cfg.get_vault_path(config)
    arxiv_id = deep_paper.parse_arxiv_id(source)
    meta = deep_paper.fetch_arxiv_metadata(arxiv_id)
    categories = cfg.get_paper_categories(vault_path, papers_subdir)

    bundle_dir = vault_path / "extracted" / arxiv_id
    content_path = deep_paper._ensure_text_file(bundle_dir / "abstract.md", meta["abstract"])

    bundle = {
        "mode": "arxiv_light",
        "status": "prepared",
        "source_type": "arxiv",
        "arxiv_id": arxiv_id,
        "meta": meta,
        "url": meta["entry_id"],
        "slug": cfg.slugify(meta["title"]),
        "vault_path": str(vault_path),
        "papers_subdir": papers_subdir,
        "categories": categories,
        "category_override": None,
        "content_path": str(content_path),
        "content_chars": len(meta["abstract"]),
        "template_path": str(SUMMARIZE_TEMPLATE_PATH),
        "note_layout": "light_article",
        "note_hint": (
            f"目标路径: {{vault}}/{papers_subdir}/<category>/"
            f"{cfg.sanitize_filename(meta['title'])}.md"
        ),
    }
    deep_paper.write_bundle(bundle_dir, bundle)
    return bundle


def run_light_web(url: str, config: dict, with_llm: bool = False):
    bundle = prepare_light_web(url, config)
    if not with_llm:
        return bundle
    client, model = cfg.get_openai_client(config)
    vault_path = Path(bundle["vault_path"])
    content = Path(bundle["content_path"]).read_text(encoding="utf-8")
    analysis = summarize_light(client, model, bundle["meta"]["title"], content, bundle["categories"])
    dest = save_light_note(
        vault_path,
        analysis.get("category", "Inbox"),
        bundle["meta"]["title"],
        bundle["url"],
        content,
        analysis,
    )
    print(f"已保存: {dest}")
    return dest


def run_light_arxiv(source: str, config: dict, papers_subdir: str, with_llm: bool = False):
    bundle = prepare_light_arxiv(source, config, papers_subdir)
    if not with_llm:
        return bundle
    client, model = cfg.get_openai_client(config)
    vault_path = Path(bundle["vault_path"])
    content = Path(bundle["content_path"]).read_text(encoding="utf-8")
    analysis = summarize_light(client, model, bundle["meta"]["title"], content, bundle["categories"])
    dest = save_light_note(
        vault_path / papers_subdir,
        analysis.get("category", "Inbox"),
        bundle["meta"]["title"],
        bundle["url"],
        content,
        analysis,
    )
    print(f"已保存(轻量, 仅摘要): {dest}")
    return dest


def main():
    parser = argparse.ArgumentParser(
        description="paper-reader 统一入口: 默认只准备材料, 由 Agent 用当前模型写笔记"
    )
    parser.add_argument("source", help="URL(网页 / ArXiv) 或本地 PDF 路径")
    parser.add_argument("--config", help="显式指定 config.json 路径")
    parser.add_argument("--light", action="store_true", help="强制轻量模式(论文也只做摘要级准备, 跳过 marker)")
    parser.add_argument("--force-text", action="store_true", help="深度模式下跳过 marker, 仅用摘要/文本")
    parser.add_argument("--slug", help="覆盖资产目录名(仅深度模式)")
    parser.add_argument("--category", help="覆盖分类(写入 bundle.category_override)")
    parser.add_argument("--filename", help="覆盖输出文件名(仅深度模式, 便于原地覆盖已有笔记)")
    parser.add_argument("--papers-subdir", default="20_Papers", help="论文归档的顶层子目录, 默认 20_Papers")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="可选: 用配置的外部 LLM API 自动生成笔记(默认关闭; Agent 场景请勿使用)",
    )
    args = parser.parse_args()

    config = cfg.load_config(args.config)
    source_type = detect_type(args.source)

    try:
        if source_type == "arxiv":
            if args.light:
                run_light_arxiv(args.source, config, args.papers_subdir, with_llm=args.with_llm)
            else:
                deep_paper.run(
                    args.source,
                    config=config,
                    slug_override=args.slug,
                    force_text=args.force_text,
                    category_override=args.category,
                    papers_subdir=args.papers_subdir,
                    filename_override=args.filename,
                    with_llm=args.with_llm,
                )
        elif source_type == "local_pdf":
            deep_paper.run_from_local_pdf(
                args.source,
                config=config,
                slug_override=args.slug,
                force_text=args.force_text or args.light,
                category_override=args.category,
                papers_subdir=args.papers_subdir,
                filename_override=args.filename,
                with_llm=args.with_llm,
            )
        else:
            run_light_web(args.source, config, with_llm=args.with_llm)
    except cfg.ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"处理失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
