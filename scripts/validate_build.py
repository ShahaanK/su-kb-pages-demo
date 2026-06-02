#!/usr/bin/env python3
"""validate_build.py - invariant checks for the su-kb-pages-demo machine surface.

The durable gate behind the crawler/LLM-surface cleanup. Encodes every
"definition of done" invariant so the frontmatter `---` bug and the llms.txt
quality can never silently regress.

Full mode (needs a built site/):
    python scripts/validate_build.py --docs docs --site site --config mkdocs.yml

Quick mode (source only, no build - used by git pre-commit and Claude Code Stop hook):
    python scripts/validate_build.py --docs docs --config mkdocs.yml --quick

Exit code 0 = all checks pass. 1 = one or more failures (each printed).

Notes
-----
- This script parses frontmatter with a robust, line-delimited fence parser
  (parse_frontmatter below). It deliberately does NOT reuse gen_llms.py's
  split_frontmatter, so it can judge whether that splitter and the build agree.
- Invariant 8 (home counts) is coupled to overrides/home.html structure. If the
  template is restructured, that check is the most likely to need updating; it
  fails loudly with the numbers it found vs computed rather than silently.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

# Frontmatter keys that must never appear in a rendered body. Used as sentinels
# to detect frontmatter bleeding into a page body (the llms-full.txt corruption
# caused by the split bug).
_FRONTMATTER_SENTINELS = (
    "sitemap_exclude:",
    "ai_description:",
    "confluence_id:",
    "confluence_space:",
)

_LLMS_ENTRY = re.compile(
    r"^-\s+\[(?P<title>.+?)\]\((?P<url>[^)]+)\)(?::\s*(?P<desc>.*\S))?\s*$"
)

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

_PAGES_BADGE = re.compile(r"(\d+)\s+pages?\b", re.IGNORECASE)

# Anchors on the structural "# Title\nSource: url\n\nbody" marker so that ---
# horizontal rules inside a page body do not create false block boundaries.
_FULL_BLOCK_RE = re.compile(
    r"^# (?P<title>[^\n]+)\nSource: (?P<url>[^\n]+)\n\n(?P<body>.*?)"
    r"(?=\n---\n\n# [^\n]+\nSource: |\Z)",
    re.DOTALL | re.MULTILINE,
)

# overrides/home.html tool-card href -> computed-section key.
# Keep in sync with PHANTOM_SECTIONS in run_ingest.py if sections change.
_CARD_HREF_TO_SECTION = {
    "claude/": "claude",
    "clementine-platform/": "clementine-platform",
    "gemini/": "gemini",
    "copilot/": "copilot",
    "approved-tools-for-use-with-university-data/": "ai-info",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Robust line-delimited frontmatter parse. Returns (meta, body).

    Unlike a bare text.split('---', 2), this anchors on the opening fence and
    the first closing fence that is alone on its line, so a `---` inside a
    frontmatter value (e.g. a description that starts with '---') does not
    break the parse.
    """
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[m.end():]


def is_excluded(meta: dict) -> bool:
    return str(meta.get("sitemap_exclude", "")).strip().lower() == "true"


def iter_docs(docs_dir: Path):
    """Yield (rel_path, meta, body) for every docs/**/*.md."""
    for md in sorted(docs_dir.rglob("*.md")):
        rel = md.relative_to(docs_dir)
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8"))
        yield rel, meta, body


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return s.strip("-") or "untitled"


def section_of(rel: Path) -> str | None:
    """Computed-section key for a leaf doc, or None if it is not a leaf under itsai/."""
    parts = rel.parts
    if parts[0] != "itsai" or rel.name == "index.md":
        return None
    rest = parts[1:]  # under itsai/
    if len(rest) == 1:  # flat file directly under itsai/ (e.g. approved-tools)
        return "ai-info"
    return rest[0]  # claude / gemini / clementine-platform / copilot (example-uses -> claude)


# ---------------------------------------------------------------------------
# Checks (each returns a list of failure strings)
# ---------------------------------------------------------------------------


def check_frontmatter_integrity(docs_dir: Path) -> list[str]:
    """Invariant 3: every source page parses with a non-empty title."""
    fails = []
    for rel, meta, _ in iter_docs(docs_dir):
        if not meta:
            fails.append(f"[frontmatter] {rel}: frontmatter did not parse (empty meta)")
        elif not str(meta.get("title", "")).strip():
            fails.append(f"[frontmatter] {rel}: empty or missing title")
    return fails


def check_gen_llms_agreement(docs_dir: Path) -> list[str]:
    """The splitter gen_llms.py ACTUALLY uses must yield a non-empty title for
    every page.

    This is the check that catches the frontmatter `---` degradation at its
    source, and it runs in quick mode too (so the pre-commit / Stop hook catch
    it before a build). It imports the real gen_llms.split_frontmatter rather
    than re-implementing it, so once Phase 2 fixes that splitter this check
    auto-passes with no edit here.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import gen_llms  # type: ignore
    except Exception as e:
        return [f"[gen-llms] could not import gen_llms.py to verify the splitter: {e}"]
    split = getattr(gen_llms, "split_frontmatter", None)
    if split is None:
        return ["[gen-llms] gen_llms.split_frontmatter not found"]
    fails = []
    for md in sorted(docs_dir.rglob("*.md")):
        try:
            meta, _ = split(md.read_text(encoding="utf-8"))
        except Exception as e:  # a raising splitter is also a failure
            fails.append(f"[gen-llms] {md.relative_to(docs_dir)}: splitter raised {e}")
            continue
        if not meta or not str((meta or {}).get("title", "")).strip():
            fails.append(
                f"[gen-llms] {md.relative_to(docs_dir)}: gen_llms splitter yields "
                f"no title - this page will degrade in llms.txt / llms-full.txt"
            )
    return fails


def check_robots_host(docs_dir: Path, config: dict) -> list[str]:
    """Invariant 7: robots.txt Sitemap host matches site_url host."""
    robots = docs_dir / "robots.txt"
    if not robots.exists():
        return ["[robots] docs/robots.txt not found"]
    site_url = str(config.get("site_url", ""))
    site_host = urlparse(site_url).netloc
    fails = []
    for line in robots.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("sitemap:"):
            sm_url = line.split(":", 1)[1].strip()
            sm_host = urlparse(sm_url).netloc
            if sm_host != site_host:
                fails.append(
                    f"[robots] Sitemap host {sm_host!r} != site_url host {site_host!r}"
                )
    return fails


def check_home_counts(docs_dir: Path, home_html: Path, n_pub: int) -> list[str]:
    """Invariant 8: home.html per-card counts and hero total match reality.

    Coupled to overrides/home.html. Fails loudly with found vs computed numbers.
    """
    if not home_html.exists():
        return [f"[home-counts] {home_html} not found"]
    html = home_html.read_text(encoding="utf-8")

    # Computed per-section leaf counts.
    computed: dict[str, int] = {}
    for rel, meta, _ in iter_docs(docs_dir):
        if is_excluded(meta):
            continue
        sec = section_of(rel)
        if sec:
            computed[sec] = computed.get(sec, 0) + 1

    fails = []

    # Per-card badge: first "N pages" badge inside each tool-card anchor.
    for href, sec in _CARD_HREF_TO_SECTION.items():
        m = re.search(
            r'<a\s+href="' + re.escape(href) + r'"\s+class="su-tool-card.*?</a>',
            html, re.DOTALL,
        )
        if not m:
            fails.append(f"[home-counts] could not locate tool card for href {href!r}")
            continue
        badge = _PAGES_BADGE.search(m.group(0))
        if not badge:
            fails.append(f"[home-counts] no 'N pages' badge in card {href!r}")
            continue
        stated = int(badge.group(1))
        actual = computed.get(sec, 0)
        if stated != actual:
            fails.append(
                f"[home-counts] card {href!r}: states {stated} pages, actual {actual}"
            )

    # Hero total: the "N pages" inside su-hero-meta.
    hero = re.search(r'class="su-hero-meta".*?</div>', html, re.DOTALL)
    if hero:
        badge = _PAGES_BADGE.search(hero.group(0))
        if badge and int(badge.group(1)) != n_pub:
            fails.append(
                f"[home-counts] hero states {badge.group(1)} pages, "
                f"actual published {n_pub}"
            )
    return fails


def check_llms_txt(site_dir: Path, n_pub: int) -> list[str]:
    """Invariants 1 (entry count) and 2 (no degraded entry) for llms.txt."""
    llms = site_dir / "llms.txt"
    if not llms.exists():
        return ["[llms] site/llms.txt not found (run gen_llms.py after build)"]
    entries = []
    for line in llms.read_text(encoding="utf-8").splitlines():
        m = _LLMS_ENTRY.match(line)
        if m:
            entries.append(m.groupdict())
    fails = []
    if len(entries) != n_pub:
        fails.append(
            f"[llms] entry count {len(entries)} != published page count {n_pub}"
        )
    for e in entries:
        if not (e.get("desc") or "").strip():
            fails.append(
                f"[llms] degraded entry (empty description): "
                f"{e['title']!r} -> {e['url']}"
            )
    return fails


def check_llms_full(site_dir: Path, n_pub: int) -> list[str]:
    """Invariants 1 (block count) and 4 (body integrity) for llms-full.txt."""
    full = site_dir / "llms-full.txt"
    if not full.exists():
        return ["[llms-full] site/llms-full.txt not found"]
    text = full.read_text(encoding="utf-8")
    page_blocks = list(_FULL_BLOCK_RE.finditer(text))
    fails = []
    if len(page_blocks) != n_pub:
        fails.append(
            f"[llms-full] page block count {len(page_blocks)} != published {n_pub}"
        )
    for m in page_blocks:
        body = m.group("body")
        if not body.strip():
            fails.append(f"[llms-full] empty body in block: {m.group('title')!r}")
        for sentinel in _FRONTMATTER_SENTINELS:
            if sentinel in body:
                fails.append(
                    f"[llms-full] frontmatter leaked into body "
                    f"(found {sentinel!r}): {m.group('title')!r}"
                )
                break
    return fails


def check_twins(site_dir: Path, n_docs_all: int) -> list[str]:
    """Invariant 1: per-page .md twin count == total source docs."""
    twins = list(site_dir.rglob("*.md"))
    fails = []
    if len(twins) != n_docs_all:
        fails.append(
            f"[twins] site .md twin count {len(twins)} != source doc count {n_docs_all}"
        )
    return fails


def check_root(site_dir: Path) -> list[str]:
    """Invariant 6: site root is not the placeholder."""
    root = site_dir / "index.html"
    if not root.exists():
        return ["[root] site/index.html not found"]
    if "Sample/placeholder content" in root.read_text(encoding="utf-8"):
        return ["[root] site root still contains 'Sample/placeholder content'"]
    return []


def check_wikilink_leak(site_dir: Path) -> list[str]:
    """Invariant 5: no [[ wikilink leakage in built HTML or .md twins."""
    fails = []
    for f in list(site_dir.rglob("*.html")) + list(site_dir.rglob("*.md")):
        if "[[" in f.read_text(encoding="utf-8", errors="ignore"):
            fails.append(f"[wikilink] '[[' found in {f.relative_to(site_dir)}")
    return fails


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_config(config_path: Path) -> dict:
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--site", default="site")
    ap.add_argument("--config", default="mkdocs.yml")
    ap.add_argument(
        "--quick", action="store_true",
        help="Source-only checks (no built site/ required).",
    )
    args = ap.parse_args()

    docs_dir = Path(args.docs)
    config = load_config(Path(args.config))
    repo_root = docs_dir.resolve().parent
    home_html = repo_root / "overrides" / "home.html"

    if not docs_dir.is_dir():
        print(f"ERROR: docs dir not found: {docs_dir}", file=sys.stderr)
        return 2

    # Published vs total counts (computed once, shared by several checks).
    all_docs = list(iter_docs(docs_dir))
    n_docs_all = len(all_docs)
    n_pub = sum(1 for _, meta, _ in all_docs if not is_excluded(meta))

    failures: list[str] = []

    # Source-only checks (run in both modes).
    failures += check_frontmatter_integrity(docs_dir)
    failures += check_gen_llms_agreement(docs_dir)
    failures += check_robots_host(docs_dir, config)
    failures += check_home_counts(docs_dir, home_html, n_pub)

    if not args.quick:
        site_dir = Path(args.site)
        if not site_dir.is_dir():
            print(
                f"ERROR: site dir not found: {site_dir} "
                f"(run mkdocs build + gen_llms.py + mirror_markdown.py first, "
                f"or use --quick)",
                file=sys.stderr,
            )
            return 2
        failures += check_llms_txt(site_dir, n_pub)
        failures += check_llms_full(site_dir, n_pub)
        failures += check_twins(site_dir, n_docs_all)
        failures += check_root(site_dir)
        failures += check_wikilink_leak(site_dir)

    mode = "quick" if args.quick else "full"
    if failures:
        print(f"VALIDATION FAILED ({mode} mode, {len(failures)} issue(s)):")
        for f in failures:
            print(f"  {f}")
        return 1

    print(
        f"VALIDATION PASSED ({mode} mode): "
        f"{n_pub} published pages, {n_docs_all} total docs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
