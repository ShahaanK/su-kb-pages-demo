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
    visibility_signal: str = "public"   # public | restricted | unknown
    robots: str = "index, follow"

    def slug(self) -> str:
        return slugify(self.title)

    def rel_path(self) -> Path:
        """docs-relative path, e.g. itsai/claude-at-syracuse.md"""
        return Path(slugify(self.space)) / f"{self.slug()}.md"

    def url_path(self, base_url: str) -> str:
        """Directory-style site URL for this page."""
        sub = self.rel_path().with_suffix("")
        return f"{base_url.rstrip('/')}/{sub}/"


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
