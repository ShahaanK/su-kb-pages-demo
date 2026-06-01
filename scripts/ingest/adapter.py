#!/usr/bin/env python3
"""Bridge su-kb-mcp converter -> PageDoc objects for the publish pipeline.

Requires su-kb-mcp installed in the same virtualenv:
    pip install -e ../su-kb-mcp

Reads credentials from ../su-kb-mcp/.env via pydantic-settings (load_settings).
"""
from __future__ import annotations

import asyncio
import logging
import re
import textwrap
from collections import defaultdict
from pathlib import Path

from anthropic import AsyncAnthropic

# su-kb-mcp imports -- requires: pip install -e ../su-kb-mcp
from su_kb_mcp.client import ConfluenceClient
from su_kb_mcp.config import load_settings
from su_kb_mcp.converter import convert_storage_to_markdown

# Ingest contract (same package)
from page_doc import PageDoc

log = logging.getLogger(__name__)

# Confluence folder whose children are held from the public site.
# M13 recon confirmed: all ITSAI pages are unrestricted at the ACL level;
# the 3 held pages are test pages that live under this folder.
RESTRICTED_FOLDER_ID = "1069121551"

# Individual pages excluded from publication regardless of folder.
# These are scratch/test pages confirmed not for the public site.
EXCLUDED_PAGE_IDS: frozenset[str] = frozenset({
    "948797482",  # (Test) Resume Tailor Machine Brain
    "965672963",  # The Workflow (how you actually use it)
})

_AI_SEM = asyncio.Semaphore(3)

# Matches Obsidian-style wikilinks produced by convert_storage_to_markdown:
#   [[Title]]  or  [[Title|Display]]
# Groups: (1) title, (2) optional display after '|'
_OBSIDIAN_WIKILINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")

# Matches any [[...]] form -- used for stripping after bridge+resolve.
_ANY_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")

# Distinguishes bridged [[id - Display]] (digits then ' - ')
_NUMERIC_DASH = re.compile(r"^(\d+)\s+-\s+(.+)$", re.DOTALL)


async def build_pagedocs_from_su_kb(
    space: str = "ITSAI",
    *,
    dry_run: bool = False,
) -> list[PageDoc]:
    """Walk the Confluence space and convert every page to a PageDoc.

    Returns ALL pages including restricted ones. Callers apply is_public()
    before writing.

    In dry_run mode, body conversion runs (so the caller can count failures and
    unresolved links) but ai_description Haiku calls are skipped. No files are
    written -- that is the caller's responsibility.
    """
    settings = load_settings()

    async with ConfluenceClient(settings) as client:
        # ── Walk: collect page summaries with ancestors + restrictions ──────
        log.info("Walking space %s ...", space)
        raw_pages: list[dict] = []
        acl_violations: list[str] = []

        walk_expand = (
            "version,space,ancestors,metadata.labels,"
            "restrictions.read.restrictions.user,"
            "restrictions.read.restrictions.group"
        )
        async for page in client.list_pages_in_space(space, expand=walk_expand):
            raw_pages.append(page)
            _check_restrictions(page, acl_violations)

        log.info("Space %s: %d pages discovered", space, len(raw_pages))

        # Per-page ACL report -- log every page so the count is auditable
        pid_to_title = {str(p.get("id", "")): p.get("title", "?") for p in raw_pages}
        acl_counts: dict[str, tuple[int, int]] = {}  # page_id -> (users, groups)
        for page in raw_pages:
            rest = page.get("restrictions", {}).get("read", {}).get("restrictions", {})
            u = len(rest.get("user", {}).get("results", []))
            g = len(rest.get("group", {}).get("results", []))
            acl_counts[str(page.get("id", ""))] = (u, g)

        nonzero = [(pid, u, g) for pid, (u, g) in acl_counts.items() if u > 0 or g > 0]
        log.info(
            "Restrictions check: %d pages -- user ACLs: %d, group ACLs: %d%s",
            len(acl_counts),
            sum(u for u, _ in acl_counts.values()),
            sum(g for _, g in acl_counts.values()),
            " (all clear)" if not nonzero else "",
        )
        if nonzero:
            for pid, u, g in nonzero:
                log.warning(
                    "  ACL on %s %r: %d user(s), %d group(s)",
                    pid, pid_to_title.get(pid, "?"), u, g,
                )

        if acl_violations:
            raise RuntimeError(
                "STOP -- unexpected Confluence ACLs found on ITSAI pages. "
                "An access restriction was added since last recon. "
                "Review before publishing:\n  " + "\n  ".join(acl_violations)
            )

        # ── Build title->id map (collision-safe) ────────────────────────────
        title_to_id = _build_title_to_id(raw_pages)

        # ── Haiku client -- None in dry_run (skips ai_description calls) ────
        anthropic_client: AsyncAnthropic | None = None
        if not dry_run:
            if not settings.has_anthropic_key():
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set in .env. "
                    "Required for ai_description generation."
                )
            anthropic_client = AsyncAnthropic(
                api_key=settings.anthropic_api_key.get_secret_value()  # type: ignore[union-attr]
            )

        # ── Convert each page ────────────────────────────────────────────────
        page_docs: list[PageDoc] = []
        converter_warnings: list[str] = []  # aggregated across all pages

        for raw in raw_pages:
            page_id = str(raw.get("id", ""))
            title = raw.get("title", "")
            visibility = _get_visibility(raw)

            if page_id in EXCLUDED_PAGE_IDS:
                page_docs.append(PageDoc(
                    page_id=page_id,
                    space=space,
                    title=title,
                    body_markdown="",
                    visibility_signal="excluded",
                ))
                continue

            if visibility != "public":
                # Restricted pages: return stub (no body fetch needed)
                page_docs.append(PageDoc(
                    page_id=page_id,
                    space=space,
                    title=title,
                    body_markdown="",
                    visibility_signal=visibility,
                ))
                continue

            try:
                doc = await _convert_page(
                    client=client,
                    raw_summary=raw,
                    title_to_id=title_to_id,
                    space=space,
                    anthropic_client=anthropic_client,
                    converter_warnings=converter_warnings,
                )
                page_docs.append(doc)
            except Exception:
                log.exception("Failed to convert page %s %r", page_id, title)
                page_docs.append(PageDoc(
                    page_id=page_id,
                    space=space,
                    title=title,
                    body_markdown="",
                    visibility_signal="unknown",
                ))

        if converter_warnings:
            unique = sorted({w.split(":", 1)[-1] for w in converter_warnings})
            log.info(
                "Converter: %d warning(s) across pages (%d unique types): %s",
                len(converter_warnings), len(unique), ", ".join(unique),
            )
            # Per-macro breakdown: which pages triggered each warning type
            by_warning: dict[str, list[str]] = defaultdict(list)
            for entry in converter_warnings:
                pid, _, wtype = entry.partition(":")
                label = pid_to_title.get(pid, pid)
                by_warning[wtype].append(label)
            for wtype, titles in sorted(by_warning.items()):
                log.info("  %s: %s", wtype, "; ".join(titles[:5]))

    return page_docs


# ── Private helpers ───────────────────────────────────────────────────────────


def _check_restrictions(page: dict, violations: list[str]) -> None:
    rest = page.get("restrictions", {}).get("read", {}).get("restrictions", {})
    users = rest.get("user", {}).get("results", [])
    groups = rest.get("group", {}).get("results", [])
    if users or groups:
        violations.append(
            f"page {page['id']} ({page.get('title', '?')!r}): "
            f"{len(users)} user ACL(s), {len(groups)} group ACL(s)"
        )


def _build_title_to_id(raw_pages: list[dict]) -> dict[str, str]:
    """Build title->page_id map. On collision, keep both as title_<id>."""
    title_to_id: dict[str, str] = {}
    for p in raw_pages:
        title = p.get("title", "")
        pid = str(p.get("id", ""))
        if not title or not pid:
            continue
        if title in title_to_id:
            existing_id = title_to_id[title]
            disambig_existing = f"{title}_{existing_id}"
            if disambig_existing not in title_to_id:
                title_to_id[disambig_existing] = existing_id
            title_to_id[f"{title}_{pid}"] = pid
            log.warning(
                "Title collision: %r (IDs %s, %s). "
                "Wikilinks to this title are ambiguous; bridge uses first match.",
                title, existing_id, pid,
            )
        else:
            title_to_id[title] = pid
    return title_to_id


def _get_visibility(page: dict) -> str:
    """Determine visibility by checking whether RESTRICTED_FOLDER_ID is an ancestor."""
    for ancestor in page.get("ancestors", []):
        if str(ancestor.get("id", "")) == RESTRICTED_FOLDER_ID:
            return "restricted"
    return "public"


async def _convert_page(
    *,
    client: ConfluenceClient,
    raw_summary: dict,
    title_to_id: dict[str, str],
    space: str,
    anthropic_client: AsyncAnthropic | None,
    converter_warnings: list[str],
) -> PageDoc:
    page_id = str(raw_summary["id"])
    title = raw_summary.get("title", "")

    # Full fetch: body + history for dates/authors
    page = await client.get_page(
        page_id,
        expand=(
            "body.storage,version,space,ancestors,metadata.labels,"
            "history,history.contributors.publishers.users"
        ),
    )

    # Convert Confluence XHTML -> Markdown
    storage_xhtml = page.get("body", {}).get("storage", {}).get("value", "")
    result = convert_storage_to_markdown(storage_xhtml)
    for w in result.warnings:
        converter_warnings.append(f"{page_id}:{w}")

    # Bridge [[Title]] / [[Title|Display]] -> [[id]] / [[id - Display]]
    body, unmapped_titles = _bridge_wikilinks(result.markdown, title_to_id)
    if unmapped_titles:
        unique = sorted(set(unmapped_titles))
        log.debug(
            "Page %s %r: %d unmapped title(s) (cross-space/deleted): %s%s",
            page_id, title, len(unique),
            ", ".join(repr(t) for t in unique[:5]),
            f" ... (+{len(unique)-5} more)" if len(unique) > 5 else "",
        )

    # Generate ai_description via Haiku 4.5 (skipped in dry_run: client is None)
    ai_desc = ""
    if anthropic_client:
        try:
            ai_desc = await _generate_ai_description(
                anthropic_client, title=title, body=body[:800]
            )
        except Exception as e:
            log.warning("ai_description failed for %s %r: %s", page_id, title, e)

    # Extract metadata
    version_obj = page.get("version", {})
    history_obj = page.get("history", {})
    date_str = _parse_iso_date(history_obj.get("createdDate") or version_obj.get("when", ""))
    lastmod_str = _parse_iso_date(version_obj.get("when", ""))

    publishers_users = (
        history_obj.get("contributors", {})
                   .get("publishers", {})
                   .get("users", [])
    )
    authors = [u["displayName"] for u in publishers_users if u.get("displayName")]

    labels = [
        lbl["name"]
        for lbl in page.get("metadata", {}).get("labels", {}).get("results", [])
        if lbl.get("name")
    ]

    # Ancestor chain from the walk summary (already fetched in walk_expand).
    # Root-first: e.g. [AI@SU_id, AI_id, Claude_id] for a Claude page.
    raw_ancestor_ids = [
        str(a.get("id", ""))
        for a in raw_summary.get("ancestors", [])
        if a.get("id")
    ]

    return PageDoc(
        page_id=page_id,
        space=space,
        title=title,
        body_markdown=body,
        description=_make_description(body),
        ai_description=ai_desc,
        date=date_str,
        lastmod=lastmod_str,
        authors=authors,
        tags=labels,
        visibility_signal="public",
        raw_ancestor_ids=raw_ancestor_ids,
    )


def _bridge_wikilinks(
    body: str, title_to_id: dict[str, str]
) -> tuple[str, list[str]]:
    """Convert [[Title]] / [[Title|Display]] -> [[id]] / [[id - Display]].

    Titles not found in title_to_id are left as [[Title]] / [[Title|Display]]
    for strip_remaining_wikilinks to handle later. Returns (body, unmapped_titles).
    """
    unmapped: list[str] = []

    def repl(m: re.Match) -> str:
        title = m.group(1).strip()
        display = (m.group(2) or "").strip()
        pid = title_to_id.get(title)
        if not pid:
            unmapped.append(title)
            return m.group(0)
        return f"[[{pid}]]" if not display else f"[[{pid} - {display}]]"

    return _OBSIDIAN_WIKILINK.sub(repl, body), unmapped


def strip_remaining_wikilinks(
    body: str, id_to_title: dict[str, str] | None = None
) -> str:
    """Strip any [[...]] remaining after resolve_wikilinks to plain text.

    Handles:
      [[id - Display]]     -> Display
      [[id]]               -> page title from id_to_title (if known) else ""
      [[Title|Display]]    -> Display
      [[Title]]            -> Title

    After this call the body must contain no '[['. The caller should verify.
    """
    id_to_title = id_to_title or {}

    def repl(m: re.Match) -> str:
        content = m.group(1).strip()
        # [[id - Display]] (numeric id + display text, from bridge step)
        nd = _NUMERIC_DASH.match(content)
        if nd:
            return nd.group(2).strip()
        # [[id]] (bare numeric, bridged without display)
        if re.match(r"^\d+$", content):
            return id_to_title.get(content, "")
        # [[Title|Display]] (unmapped Obsidian link with display text)
        if "|" in content:
            return content.split("|", 1)[1].strip()
        # [[Title]] (unmapped plain title)
        return content

    return _ANY_WIKILINK.sub(repl, body)


def _make_description(body: str) -> str:
    """Extract first ~150 chars of plain text from Markdown body.

    Strips headings, Markdown links, wikilinks (all forms), and inline
    formatting. Trims at a word boundary.
    """
    text = re.sub(r"^#+\s+.+$", "", body, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url)
    # Strip wikilinks to their display label (or empty for bare numeric IDs)
    text = re.sub(r"\[\[([^\]]+)\]\]", _wikilink_to_plain, text)
    text = re.sub(r"[*_`~>|]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return textwrap.shorten(text, width=150, placeholder="...")


def _wikilink_to_plain(m: re.Match) -> str:
    """Collapse a [[...]] match to its human-readable label."""
    content = m.group(1).strip()
    nd = _NUMERIC_DASH.match(content)
    if nd:
        return nd.group(2).strip()
    if re.match(r"^\d+$", content):
        return ""  # bare id has no useful display text
    if "|" in content:
        return content.split("|", 1)[1].strip()
    return content


def _parse_iso_date(s: str) -> str:
    """Return YYYY-MM-DD from an ISO datetime string."""
    return s[:10] if s else ""


async def _generate_ai_description(
    client: AsyncAnthropic, *, title: str, body: str
) -> str:
    async with _AI_SEM:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "Write one factual sentence (under 120 characters) "
                    "summarizing this Syracuse University IT knowledge-base "
                    "page for use as search metadata. "
                    "Return only the sentence, no quotes.\n\n"
                    f"Title: {title}\n\n---\n{body}\n---"
                ),
            }],
        )
    text = resp.content[0].text.strip() if resp.content else ""
    if len(text) > 160:
        trimmed = text[:160]
        last_period = trimmed.rfind(".")
        text = trimmed[: last_period + 1] if last_period > 80 else trimmed + "..."
    return text
