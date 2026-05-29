#!/usr/bin/env python3
"""Generate llms.txt and llms-full.txt from the docs/ Markdown corpus.

Run AFTER `mkdocs build`, writing into the built site/ directory:

    python scripts/gen_llms.py --docs docs --site site --config mkdocs.yml

Design notes
------------
- This is the hand-rolled alternative to the mkdocs-llmstxt plugin. It exists
  so the build depends only on mkdocs-material. To switch to the plugin later,
  delete this script from the workflow and add a `- llmstxt:` block to mkdocs.yml.
- "Aggressive inlining": llms-full.txt contains the full body of every page so
  an agent can grab the whole corpus in one fetch. Fine at 34 pages. At ~4,338
  pages this must be sharded per-space (see WORKPLAN M14 Phase 2).
- Pages with `sitemap_exclude: true` in frontmatter are also excluded here.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def split_frontmatter(text: str):
    """Return (meta: dict, body: str). Tolerates files with no frontmatter."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), parts[2].lstrip("\n")
    return {}, text


def page_url(base_url: str, rel: Path) -> str:
    """Map a docs-relative .md path to its directory-style site URL."""
    stem = rel.with_suffix("")
    if stem.name == "index":
        sub = stem.parent
    else:
        sub = stem
    sub_str = "" if str(sub) == "." else f"{sub}/"
    return f"{base_url.rstrip('/')}/{sub_str}"


def load_site_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return {
        "name": cfg.get("site_name", "Knowledge Base"),
        "description": (cfg.get("site_description") or "").strip(),
        "url": cfg.get("site_url", "/"),
    }


def collect_pages(docs_dir: Path):
    pages = []
    for md in sorted(docs_dir.rglob("*.md")):
        rel = md.relative_to(docs_dir)
        meta, body = split_frontmatter(md.read_text(encoding="utf-8"))
        if str(meta.get("sitemap_exclude", "")).lower() == "true":
            continue
        pages.append({"rel": rel, "meta": meta, "body": body})
    return pages


def section_for(page) -> str:
    meta = page["meta"]
    if meta.get("section"):
        return str(meta["section"])
    parts = page["rel"].parts
    if len(parts) == 1:  # top-level file
        return "Overview"
    return parts[0].replace("-", " ").replace("_", " ").title()


def section_sort_key(name: str):
    # Overview always first, then alphabetical
    return (0, "") if name == "Overview" else (1, name.lower())


def build_llms_txt(site, pages, base_url) -> str:
    out = [f"# {site['name']}", ""]
    if site["description"]:
        out += [f"> {site['description']}", ""]

    by_section: dict[str, list] = {}
    for p in pages:
        by_section.setdefault(section_for(p), []).append(p)

    for sec in sorted(by_section, key=section_sort_key):
        out.append(f"## {sec}")
        out.append("")
        for p in sorted(by_section[sec], key=lambda x: str(x["rel"])):
            meta = p["meta"]
            title = str(meta.get("title", p["rel"].stem))
            desc = str(meta.get("ai_description") or meta.get("description") or "").strip()
            url = page_url(base_url, p["rel"])
            out.append(f"- [{title}]({url}): {desc}" if desc else f"- [{title}]({url})")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def build_llms_full_txt(site, pages, base_url) -> str:
    out = [f"# {site['name']}", ""]
    if site["description"]:
        out += [f"> {site['description']}", ""]
    out += ["<!-- Full corpus inlined for LLM consumption. -->", ""]

    for p in sorted(pages, key=lambda x: str(x["rel"])):
        meta = p["meta"]
        title = str(meta.get("title", p["rel"].stem))
        url = page_url(base_url, p["rel"])
        out.append("---")
        out.append("")
        out.append(f"# {title}")
        out.append(f"Source: {url}")
        out.append("")
        out.append(p["body"].rstrip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--site", default="site")
    ap.add_argument("--config", default="mkdocs.yml")
    args = ap.parse_args()

    docs_dir = Path(args.docs)
    site_dir = Path(args.site)
    if not docs_dir.is_dir():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1
    site_dir.mkdir(parents=True, exist_ok=True)

    site = load_site_config(Path(args.config))
    base_url = site["url"]
    pages = collect_pages(docs_dir)

    (site_dir / "llms.txt").write_text(
        build_llms_txt(site, pages, base_url), encoding="utf-8"
    )
    (site_dir / "llms-full.txt").write_text(
        build_llms_full_txt(site, pages, base_url), encoding="utf-8"
    )
    print(f"Wrote llms.txt and llms-full.txt for {len(pages)} pages -> {site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
