#!/usr/bin/env python3
"""Ingest entry point: pull ITSAI from Confluence and write to docs/.

Phase-gated workflow -- always run --dry-run first:

    python scripts/ingest/run_ingest.py --space ITSAI --dry-run
    # confirm: 1 root + 28 leaves + 5 hubs = 34 files | 3 restricted + 2 excluded

    python scripts/ingest/run_ingest.py --space ITSAI
    # live write; followed by: mkdocs build --strict

Run from the repo root so that DOCS_DIR resolves correctly.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Add scripts/ingest/ to sys.path so sibling modules (page_doc, transforms,
# adapter) are importable without installing this package.
sys.path.insert(0, str(Path(__file__).parent))

from adapter import build_pagedocs_from_su_kb, strip_remaining_wikilinks
from page_doc import PageDoc, slugify, write_doc
from transforms import is_public, resolve_wikilinks

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
LINKS_DL = REPO_ROOT / "dead-letter" / "links-unresolved.jsonl"

# Space root page -- written as itsai/index.md.
ITSAI_ROOT_ID = "483525103"  # AI @ Syracuse University

# Phantom Confluence section IDs that ARE kept as published path components.
# Maps phantom page ID -> folder slug used in URLs.
# The remaining phantoms (AI: 488439881, AI-General-Info: 571670530) are collapsed.
PHANTOM_SECTIONS: dict[str, str] = {
    "488505501": "claude",
    "488603852": "gemini",
    "490045538": "clementine-platform",
    "488603851": "copilot",
    "544211038": "example-uses",
}

# Metadata for each generated section hub page.
_HUB_META: dict[str, dict] = {
    "claude": {
        "title": "Claude",
        "description": "Claude Enterprise at Syracuse University -- setup, connectors, and use cases.",
        "ancestor_slugs": [],
        "intro": (
            "Claude Enterprise at Syracuse University gives the SU community access to "
            "Anthropic's Claude AI assistant. This section covers setup, connectors, and "
            "hands-on workflow examples."
        ),
    },
    "gemini": {
        "title": "Gemini",
        "description": "Google Gemini tools at SU -- Gemini, NotebookLM, and AI study aids.",
        "ancestor_slugs": [],
        "intro": (
            "Google Gemini is available to the SU community through Google Workspace. "
            "This section covers Gemini, NotebookLM, and AI-assisted study tools."
        ),
    },
    "clementine-platform": {
        "title": "Clementine Platform",
        "description": (
            "The Clementine Platform -- SU's home-grown AI layer including "
            "mentorAI and Clementine Class Search."
        ),
        "ancestor_slugs": [],
        "intro": (
            "The Clementine Platform is SU's home-grown AI layer, including the mentorAI "
            "tutoring tool and the Clementine Class Search assistant."
        ),
    },
    "copilot": {
        "title": "Copilot",
        "description": "Microsoft Copilot for eligible SU Microsoft 365 users.",
        "ancestor_slugs": [],
        "intro": (
            "Microsoft Copilot is integrated into Microsoft 365 for eligible "
            "Syracuse University users."
        ),
    },
    "example-uses": {
        "title": "Example Uses",
        "description": "Practical Claude workflow examples for SU students and staff.",
        "ancestor_slugs": ["claude"],
        "intro": (
            "Practical examples of using Claude for academic and professional tasks "
            "at Syracuse University."
        ),
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest ITSAI Confluence pages into docs/."
    )
    parser.add_argument(
        "--space", default="ITSAI",
        help="Confluence space key (default: ITSAI).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help=(
            "Convert pages and report counts + resolved paths -- no writes, "
            "no Haiku calls. Always run this first."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
        stream=sys.stderr,
    )

    base_url = _load_base_url(MKDOCS_YML)
    return asyncio.run(_run(args.space, dry_run=args.dry_run, base_url=base_url))


def _load_base_url(mkdocs_yml: Path) -> str:
    """Read site_url from mkdocs.yml. Warns if it still says EXAMPLE."""
    try:
        cfg = yaml.safe_load(mkdocs_yml.read_text(encoding="utf-8")) or {}
        url = str(cfg.get("site_url", "")).rstrip("/")
    except Exception as e:
        log.warning("Could not read %s: %s -- using placeholder URL", mkdocs_yml, e)
        return "https://EXAMPLE.github.io/su-kb-pages-demo"
    if not url or "EXAMPLE" in url:
        log.warning(
            "site_url in mkdocs.yml still contains 'EXAMPLE'. "
            "Internal wikilinks will resolve to placeholder URLs. "
            "Set site_url in mkdocs.yml before the live write.",
        )
    return url or "https://EXAMPLE.github.io/su-kb-pages-demo"


async def _run(space: str, *, dry_run: bool, base_url: str) -> int:
    mode = "DRY RUN" if dry_run else "LIVE WRITE"
    log.info("=== Ingest [%s]  space=%s  base_url=%s ===", mode, space, base_url)

    # ── Step 0: Pull + convert all pages (dry_run skips Haiku only) ──────────
    all_pages = await build_pagedocs_from_su_kb(space, dry_run=dry_run)

    public = [p for p in all_pages if is_public(p.visibility_signal)]
    restricted = [p for p in all_pages if p.visibility_signal == "restricted"]
    excluded = [p for p in all_pages if p.visibility_signal == "excluded"]
    failures = [p for p in all_pages if p.visibility_signal == "unknown"]

    log.info(
        "Counts -- Total: %d | Public: %d | Restricted: %d | Excluded: %d | Failures: %d",
        len(all_pages), len(public), len(restricted), len(excluded), len(failures),
    )
    for p in restricted:
        log.info("  Held [restricted]  %s  %r", p.page_id, p.title)
    for p in excluded:
        log.info("  Held [excluded]    %s  %r", p.page_id, p.title)
    if failures:
        log.warning("  Conversion failures (visibility_signal=unknown):")
        for p in failures:
            log.warning("    %s  %r", p.page_id, p.title)

    # ── Step 0.5: Build hierarchy (ancestor_slugs, is_space_root) ────────────
    _build_hierarchy(public, PHANTOM_SECTIONS, ITSAI_ROOT_ID)

    # ── Step 0.6: Generate section hub pages ─────────────────────────────────
    hubs = _generate_hub_pages(public, space=space)
    public = public + hubs

    log.info(
        "Pages -- %d real (%d root + %d leaves) + %d generated hubs = %d total",
        len(public) - len(hubs),
        sum(1 for p in public if p.is_space_root),
        sum(1 for p in public if not p.is_space_root and not p.is_section_index),
        len(hubs),
        len(public),
    )

    # ── Step 1: Resolve path collisions BEFORE building id->url ──────────────
    # Key on full rel_path (not just slug) -- pages in different directories
    # with the same slug are NOT a collision.
    _resolve_path_collisions(public)

    # ── Step 2: Build id->url and id->title maps (real public pages only) ────
    # Hub pages get synthetic IDs ("hub-claude" etc.) -- exclude from the
    # wikilink resolution map since no real page content links to them.
    real_public = [p for p in public if not p.page_id.startswith("hub-")]
    id_to_url = {p.page_id: p.url_path(base_url) for p in real_public}
    id_to_title = {p.page_id: p.title for p in real_public}

    # ── Step 3: Resolve wikilinks (real pages only; hubs use direct links) ────
    if not dry_run:
        LINKS_DL.parent.mkdir(parents=True, exist_ok=True)

    unresolved_total = 0
    resolved_real: list[tuple[PageDoc, str]] = []
    stripped_samples: list[str] = []

    for p in real_public:
        if not p.body_markdown:
            log.warning("Skipping %s %r -- empty body (conversion failure)", p.page_id, p.title)
            continue

        resolved_body, unresolved_ids = resolve_wikilinks(
            p.body_markdown, id_to_url, id_to_title
        )

        remaining = re.findall(r"\[\[([^\]]+)\]\]", resolved_body)
        if unresolved_ids or remaining:
            unresolved_total += len(unresolved_ids) + len(remaining)
            if len(stripped_samples) < 15:
                stripped_samples.extend(remaining[: 15 - len(stripped_samples)])

        final_body = strip_remaining_wikilinks(resolved_body, id_to_title)

        if "[[" in final_body:
            log.error(
                "WIKILINK GUARD FAILED: %s %r still contains [[ after strip.",
                p.page_id, p.title,
            )
            return 1

        resolved_real.append((p, final_body))

        if not dry_run and (unresolved_ids or remaining):
            _append_links_record(LINKS_DL, p.page_id, p.title, unresolved_ids, remaining)

    log.info(
        "Wikilinks -- unresolved/stripped: %d "
        "(expected non-zero; only ITSAI is published)",
        unresolved_total,
    )
    if stripped_samples:
        log.info("  Sample stripped targets (confirm these are cross-space, not ITSAI):")
        for t in stripped_samples[:10]:
            log.info("    [[%s]]", t)

    if dry_run:
        log.info("Resolved paths (1 root + 28 leaves + 5 hubs = 34):")
        leaves = [p for p in public if not p.is_space_root and not p.is_section_index]
        hubs_list = [p for p in public if p.is_section_index]
        roots = [p for p in public if p.is_space_root]
        for p in sorted(roots + hubs_list + leaves, key=lambda x: str(x.rel_path())):
            role = "root" if p.is_space_root else ("hub" if p.is_section_index else "leaf")
            log.info(
                "  [%-4s]  %s",
                role,
                str(p.rel_path()).replace("\\", "/"),
            )
        log.info(
            "Summary: 1 root + %d leaves + %d hubs = %d | "
            "%d restricted + %d excluded",
            len(leaves), len(hubs_list), len(public),
            len(restricted), len(excluded),
        )
        log.info("DRY RUN complete -- no writes performed.")
        return 0

    # ── Step 4: Write (live mode only) ────────────────────────────────────────
    written_paths: set[Path] = set()

    # Write resolved real pages
    for p, final_body in resolved_real:
        p.body_markdown = final_body
        target = write_doc(p, DOCS_DIR)
        written_paths.add(target)
        log.info("Wrote %s", target.relative_to(DOCS_DIR))

    # Write generated hub pages (bodies are already final -- direct Markdown links)
    for hub in hubs:
        target = write_doc(hub, DOCS_DIR)
        written_paths.add(target)
        log.info("Wrote hub %s", target.relative_to(DOCS_DIR))

    # Write root page (AI @ SU) -- already in resolved_real if it has a body
    # (it was processed above), so no special handling needed here.

    # ── Step 5: Remove stale docs/itsai/ files ───────────────────────────────
    # This cleans up: old flat files from the pre-hierarchy run, excluded test
    # pages written in a prior run, and any other orphans.
    itsai_dir = DOCS_DIR / "itsai"
    if itsai_dir.exists():
        stale = 0
        for f in sorted(itsai_dir.rglob("*.md")):
            if f not in written_paths:
                f.unlink()
                log.info("Removed stale: %s", f.relative_to(DOCS_DIR))
                stale += 1
        # Remove directories left empty after stale cleanup
        for d in sorted(itsai_dir.rglob("*"), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except OSError:
                    pass
        if stale:
            log.info("Removed %d stale file(s) from docs/itsai/", stale)

    # ── Step 6: Post-write wikilink guard (all written files) ─────────────────
    guard_failures: list[str] = []
    for path in written_paths:
        content = path.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        body_to_check = parts[2] if len(parts) == 3 else content
        if "[[" in body_to_check:
            guard_failures.append(str(path.relative_to(DOCS_DIR)))

    if guard_failures:
        log.error(
            "WIKILINK GUARD: %d written file(s) still contain [[ in body:\n  %s",
            len(guard_failures), "\n  ".join(guard_failures),
        )
        return 1

    log.info(
        "=== Done -- wrote: %d | held: %d restricted + %d excluded | "
        "unresolved links stripped: %d | guard: OK ===",
        len(written_paths), len(restricted), len(excluded), unresolved_total,
    )
    return 0


# ── Hierarchy helpers ─────────────────────────────────────────────────────────


def _build_hierarchy(
    pages: list[PageDoc],
    phantom_sections: dict[str, str],
    root_page_id: str,
) -> None:
    """Set is_space_root and ancestor_slugs on each public page in-place.

    Only phantom section IDs listed in phantom_sections contribute to the path.
    Collapsed phantoms (AI, AI-General-Info) and AI@SU (root) are silently skipped.
    All real public pages are leaves (is_section_index stays False).
    """
    for p in pages:
        if p.page_id == root_page_id:
            p.is_space_root = True
            p.ancestor_slugs = []
        else:
            p.ancestor_slugs = [
                phantom_sections[aid]
                for aid in p.raw_ancestor_ids
                if aid in phantom_sections
            ]


def _generate_hub_pages(real_pages: list[PageDoc], *, space: str) -> list[PageDoc]:
    """Create 5 synthetic section hub PageDocs for phantom containers.

    Hub bodies use relative .md file links so --strict validates them.
    """
    # Create stubs first (rel_path needed to compute relative child links)
    hubs: list[PageDoc] = []
    for slug, meta in _HUB_META.items():
        hub = PageDoc(
            page_id=f"hub-{slug}",
            space=space,
            title=meta["title"],
            body_markdown="",
            description=meta["description"],
            ai_description="",
            visibility_signal="public",
            ancestor_slugs=list(meta["ancestor_slugs"]),
            is_section_index=True,
        )
        hubs.append(hub)

    all_candidates = real_pages + hubs

    # Fill hub bodies after all stubs exist (so sub-hubs appear in parent hub lists)
    for hub in hubs:
        hub_slug = hub.slug()
        target_ancestors = hub.ancestor_slugs + [hub_slug]
        children = sorted(
            [p for p in all_candidates if p.ancestor_slugs == target_ancestors],
            key=lambda p: p.title,
        )
        hub_dir = hub.rel_path().parent
        meta = _HUB_META[hub_slug]
        lines = [meta["intro"], "", "## Pages in this section", ""]
        for child in children:
            try:
                rel_link = str(
                    child.rel_path().relative_to(hub_dir)
                ).replace("\\", "/")
            except ValueError:
                rel_link = str(child.rel_path()).replace("\\", "/")
            lines.append(f"- [{child.title}]({rel_link})")
        hub.body_markdown = "\n".join(lines)

    return hubs


# ── Collision / dead-letter helpers ──────────────────────────────────────────


def _resolve_path_collisions(pages: list[PageDoc]) -> None:
    """Detect full-path collisions and amend page titles in-place.

    Two pages in different directories sharing a slug is NOT a collision.
    We key on str(rel_path()) so only genuine same-file conflicts are caught.
    Must run after _build_hierarchy (so ancestor_slugs are set) and before
    id_to_url is built (so the URL map matches the written paths).
    """
    by_path: dict[str, list[PageDoc]] = defaultdict(list)
    for p in pages:
        by_path[str(p.rel_path())].append(p)
    for path, group in by_path.items():
        if len(group) > 1:
            for p in group:
                original_title = p.title
                p.title = f"{p.title}-{p.page_id}"
                log.warning(
                    "Path collision on %r: page %s %r -- amended title to %r.",
                    path, p.page_id, original_title, p.title,
                )


def _append_links_record(
    path: Path,
    page_id: str,
    title: str,
    unresolved_ids: list[str],
    remaining_wikilinks: list[str],
) -> None:
    record = {
        "page_id": page_id,
        "title": title,
        "unresolved_ids": unresolved_ids,
        "remaining_wikilinks": remaining_wikilinks,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    sys.exit(main())
