#!/usr/bin/env python3
"""Ingest contract: the target shape every Confluence page is converted into.

This module is deliberately converter-agnostic. It does NOT import or call the
su-kb converter. Instead it defines the interface that the converter must
produce (a `PageDoc`) and writes that PageDoc into the MkDocs `docs/` tree with
the frontmatter schema the publish pipeline expects.

Wiring the su-kb converter to emit PageDoc objects is the integration step
documented in INTEGRATION.md (the part that needs the converter source).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PageDoc:
    """One Confluence page, normalized for publication."""

    page_id: str
    space: str                      # Confluence space key, e.g. "ITSAI"
    title: str
    body_markdown: str              # converted body (wikilinks resolved upstream)

    description: str = ""           # human/search snippet, 140-160 chars
    ai_description: str = ""        # one-line factual summary for LLM context
    date: str = ""                  # ISO created date, e.g. "2026-04-10"
    lastmod: str = ""               # ISO modified date, drives sitemap lastmod
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    visibility_signal: str = "public"   # public | restricted | excluded | unknown
    robots: str = "index, follow"

    # Hierarchy fields -- set by run_ingest after the full page list is built.
    # Raw Confluence ancestor IDs (root-first), set by adapter._convert_page.
    raw_ancestor_ids: list[str] = field(default_factory=list)
    # Filtered path components (published phantom-section slugs only), root-first.
    # Set by run_ingest._build_hierarchy; used by rel_path().
    ancestor_slugs: list[str] = field(default_factory=list)
    # True if this page is written as <folder>/index.md (hub or space root).
    is_section_index: bool = False
    # True for the space root page (writes to itsai/index.md, not itsai/<slug>/index.md).
    is_space_root: bool = False

    def slug(self) -> str:
        return slugify(self.title)

    def rel_path(self) -> Path:
        """docs-relative path respecting hierarchy fields.

        Rules (applied in order):
          is_space_root                    -> itsai/index.md
          is_section_index, no ancestors   -> itsai/<slug>/index.md
          is_section_index, with ancestors -> itsai/<ancestors>/<slug>/index.md
          leaf, no ancestors               -> itsai/<slug>.md
          leaf, with ancestors             -> itsai/<ancestors>/<slug>.md
        """
        base = Path(slugify(self.space))
        if self.is_space_root:
            return base / "index.md"
        if not self.ancestor_slugs:
            if self.is_section_index:
                return base / self.slug() / "index.md"
            return base / f"{self.slug()}.md"
        parent = base.joinpath(*self.ancestor_slugs)
        if self.is_section_index:
            return parent / self.slug() / "index.md"
        return parent / f"{self.slug()}.md"

    def url_path(self, base_url: str) -> str:
        """Directory-style site URL for this page.

        MkDocs serves index.md files at the directory URL, not at .../index/.
        So itsai/claude/index.md -> .../itsai/claude/  (not .../itsai/claude/index/).
        """
        rel = self.rel_path()
        stem = rel.with_suffix("")
        sub = stem.parent if stem.name == "index" else stem
        sub_str = str(sub).replace("\\", "/")
        if sub_str == ".":
            return f"{base_url.rstrip('/')}/"
        return f"{base_url.rstrip('/')}/{sub_str}/"


_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    s = _SLUG_STRIP.sub("-", text.strip().lower())
    return s.strip("-") or "untitled"


def _frontmatter(doc: PageDoc) -> str:
    meta = {
        "title": doc.title,
        "description": doc.description,
        "ai_description": doc.ai_description,
        "date": doc.date,
        "lastmod": doc.lastmod,
        "confluence_id": doc.page_id,
        "confluence_space": doc.space,
        "confluence_parent_id": doc.raw_ancestor_ids[-1] if doc.raw_ancestor_ids else "",
        "authors": doc.authors,
        "tags": doc.tags,
        "robots": doc.robots,
        "sitemap_exclude": False,
    }
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True,
                            default_flow_style=False)
    return f"---\n{dumped}---\n\n"


def write_doc(doc: PageDoc, docs_dir: Path) -> Path:
    """Write a PageDoc into docs_dir. Returns the file path written."""
    target = docs_dir / doc.rel_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_frontmatter(doc) + doc.body_markdown.rstrip() + "\n",
                      encoding="utf-8")
    return target
