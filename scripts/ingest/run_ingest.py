#!/usr/bin/env python3
"""Ingest entry point: pull ITSAI from Confluence and write to docs/.

Phase-gated workflow -- always run --dry-run first:

    python scripts/ingest/run_ingest.py --space ITSAI --dry-run
    # confirm counts: ~34 total | 31 public | 3 restricted | 0 failures
    #                 unresolved links stripped: <N> (expected to be non-zero)

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
from page_doc import PageDoc, write_doc
from transforms import is_public, resolve_wikilinks

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs"
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
LINKS_DL = REPO_ROOT / "dead-letter" / "links-unresolved.jsonl"


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
            "Convert pages and report counts (total, public, restricted, "
            "failures, unresolved links) -- no writes, no Haiku calls. "
            "Always run this first."
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
    held = [p for p in all_pages if not is_public(p.visibility_signal)]
    # visibility_signal == "unknown" means an exception during body conversion
    failures = [p for p in all_pages if p.visibility_signal == "unknown"]

    log.info(
        "Counts -- Total: %d | Public: %d | Restricted/held: %d | Conversion failures: %d",
        len(all_pages), len(public), len(held), len(failures),
    )
    for p in held:
        log.info("  Held [%s]  %s  %r", p.visibility_signal, p.page_id, p.title)
    if failures:
        log.warning("  Conversion failures (visibility_signal=unknown):")
        for p in failures:
            log.warning("    %s  %r", p.page_id, p.title)

    # ── Step 1: Resolve slug collisions BEFORE building id->url ──────────────
    # Slugs must be final before the URL map is built, so links resolve to the
    # correct written path.
    _resolve_slug_collisions(public)

    # ── Step 2: Build id->url and id->title maps (public pages only) ─────────
    id_to_url = {p.page_id: p.url_path(base_url) for p in public}
    id_to_title = {p.page_id: p.title for p in public}

    # ── Step 3: Resolve wikilinks and count unresolved (both modes) ───────────
    # The resolve pass runs in dry_run too so the count is available at
    # checkpoint-3 sign-off -- discovering a flood of failures here, before
    # any write, is the whole point of the phase gate.
    if not dry_run:
        LINKS_DL.parent.mkdir(parents=True, exist_ok=True)
    unresolved_total = 0
    resolved_pages: list[tuple[PageDoc, str]] = []  # (page, final_body)
    stripped_samples: list[str] = []  # first 15 stripped targets for review

    for p in public:
        if not p.body_markdown:
            log.warning("Skipping %s %r -- empty body (conversion failure)", p.page_id, p.title)
            continue

        # Resolve [[id]] / [[id - Display]] -> [label](url)
        resolved_body, unresolved_ids = resolve_wikilinks(
            p.body_markdown, id_to_url, id_to_title
        )

        # Collect remaining [[...]] before stripping (for dead-letter record)
        remaining = re.findall(r"\[\[([^\]]+)\]\]", resolved_body)
        if unresolved_ids or remaining:
            unresolved_total += len(unresolved_ids) + len(remaining)
            if len(stripped_samples) < 15:
                stripped_samples.extend(remaining[: 15 - len(stripped_samples)])

        # Strip leftover [[...]] to plain text (cross-space links are expected)
        final_body = strip_remaining_wikilinks(resolved_body, id_to_title)

        # Guard: strip_remaining_wikilinks must leave no [[ behind
        if "[[" in final_body:
            log.error(
                "WIKILINK GUARD FAILED: %s %r still contains [[ after strip. "
                "This is a bug in strip_remaining_wikilinks.",
                p.page_id, p.title,
            )
            return 1

        resolved_pages.append((p, final_body))

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
        log.info("DRY RUN complete -- no writes performed.")
        return 0

    # ── Step 4: Write (live mode only) ────────────────────────────────────────
    written_paths: set[Path] = set()

    for p, final_body in resolved_pages:
        p.body_markdown = final_body
        target = write_doc(p, DOCS_DIR)
        written_paths.add(target)
        log.info("Wrote %s", target.relative_to(DOCS_DIR))

    # ── Step 5: Remove placeholder sample pages ───────────────────────────────
    ai_tools_dir = DOCS_DIR / "ai-tools"
    if ai_tools_dir.exists():
        removed = 0
        for f in list(ai_tools_dir.glob("*.md")):
            if f not in written_paths:
                f.unlink()
                log.info("Removed placeholder: %s", f.relative_to(DOCS_DIR))
                removed += 1
        if removed:
            try:
                ai_tools_dir.rmdir()
                log.info("Removed empty dir: docs/ai-tools/")
            except OSError:
                pass  # Not empty -- a real page landed in ai-tools/; that is fine

    # ── Step 6: Post-write wikilink guard (all written files) ─────────────────
    guard_failures: list[str] = []
    for path in written_paths:
        content = path.read_text(encoding="utf-8")
        # Skip the YAML frontmatter block (between the two '---\n' delimiters)
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
        "=== Done -- wrote: %d | held: %d | unresolved links stripped: %d | guard: OK ===",
        len(written_paths), len(held), unresolved_total,
    )
    return 0


def _resolve_slug_collisions(pages: list[PageDoc]) -> None:
    """Detect slug collisions and amend page titles in-place before URL maps are built.

    Amending titles here keeps id_to_url and the written file paths in sync --
    if we amended after building id_to_url, pages linking to the colliding page
    would resolve to the old slug URL while the file was written at the new path.
    """
    by_slug: dict[str, list[PageDoc]] = defaultdict(list)
    for p in pages:
        by_slug[p.slug()].append(p)
    for slug, group in by_slug.items():
        if len(group) > 1:
            for p in group:
                original_title = p.title
                p.title = f"{p.title}-{p.page_id}"
                log.warning(
                    "Slug collision on %r: page %s %r -- amended title to %r.",
                    slug, p.page_id, original_title, p.title,
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
