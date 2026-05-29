#!/usr/bin/env python3
"""Mirror source Markdown into the built site as per-page .md twins.

Run AFTER `mkdocs build` (which assumes use_directory_urls: true, the default):

    python scripts/mirror_markdown.py --docs docs --site site

Mapping (directory-URL style):
    docs/index.md            -> site/index.md
    docs/ai-tools/claude.md  -> site/ai-tools/claude/index.md
    docs/ai-tools/index.md   -> site/ai-tools/index.md

This gives every HTML page at /path/ a Markdown twin at /path/index.md, the
same convention used by Anthropic and Cloudflare docs. The twin includes
frontmatter, which is useful metadata for agent consumers.

Non-Markdown assets (images, robots.txt, css) are already copied by MkDocs and
are not touched here.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def target_for(rel: Path, site_dir: Path) -> Path:
    stem = rel.with_suffix("")
    if stem.name == "index":
        return site_dir / stem.parent / "index.md"
    return site_dir / stem / "index.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--site", default="site")
    args = ap.parse_args()

    docs_dir = Path(args.docs)
    site_dir = Path(args.site)
    if not docs_dir.is_dir():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 1
    if not site_dir.is_dir():
        print(f"ERROR: site dir not found (run mkdocs build first): {site_dir}",
              file=sys.stderr)
        return 1

    count = 0
    for md in sorted(docs_dir.rglob("*.md")):
        rel = md.relative_to(docs_dir)
        target = target_for(rel, site_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md, target)
        count += 1

    print(f"Mirrored {count} Markdown twins into {site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
