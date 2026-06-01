#!/usr/bin/env python3
"""Ingest transforms that operate on data, not on the converter internals.

- resolve_wikilinks: turn [[page-id]] / [[page-id - Title]] into real links
- is_public: visibility gate for the public site
- DeadLetter: quarantine pages/links that can't be published cleanly

All converter-agnostic and safe to write without the su-kb source.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Matches [[123456]] or [[123456 - Some Title]]
_WIKILINK = re.compile(r"\[\[\s*(\d+)\s*(?:-\s*(.*?))?\s*\]\]")


def resolve_wikilinks(body: str, id_to_url: dict[str, str],
                      id_to_title: dict[str, str] | None = None):
    """Replace wikilinks with Markdown links.

    Returns (resolved_body, unresolved_ids). Unresolved ids are left as a
    visible [[id]] marker AND reported so the caller can dead-letter the page;
    we never silently drop a broken link.
    """
    id_to_title = id_to_title or {}
    unresolved: list[str] = []

    def repl(m: re.Match) -> str:
        pid = m.group(1)
        inline_title = (m.group(2) or "").strip()
        url = id_to_url.get(pid)
        if not url:
            unresolved.append(pid)
            return m.group(0)  # leave [[id ...]] intact for the dead-letter check
        label = inline_title or id_to_title.get(pid) or pid
        return f"[{label}]({url})"

    return _WIKILINK.sub(repl, body), unresolved


def is_public(visibility_signal: str) -> bool:
    """Only `public` is published. Anything else (restricted/unknown) is held."""
    return str(visibility_signal).strip().lower() == "public"


class DeadLetter:
    """Quarantine pages that cannot be published cleanly.

    Writes a JSON record plus the offending body to dead-letter/ so failures
    are inspectable, never silently lost. dead-letter/ is gitignored.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def record(self, page_id: str, reason: str, *, title: str = "",
               body: str = "", extra: dict | None = None) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rec = {
            "page_id": page_id,
            "title": title,
            "reason": reason,
            "quarantined_at": stamp,
            **(extra or {}),
        }
        out = self.root / f"{page_id}-{stamp}.json"
        out.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        if body:
            (self.root / f"{page_id}-{stamp}.md").write_text(body, encoding="utf-8")
        return out
