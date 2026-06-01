# VISION.md

## Current Vision

### Project: su-kb-pages-demo (SU AI KB Publishing Pipeline)

**Primary Stakeholder:** Syracuse University Enterprise Claude users and the Claude
skill that serves them. The skill and the broader LLM/search ecosystem are the
primary consumers of the published corpus; human readers browsing the site are the
co-equal second audience.

**Secondary Stakeholders:**
- Information Technology Services (eventual owner of the production site at docs.syr.edu/its-ai)
- Aaron Starr (steered the docs-first + skill direction; decision gate for the org-repo cutover)
- The parent su-kb-mcp project (this repo is the V4 publish half; the MCP is the fallback consumer)
- Confluence content authors (their pages become publicly discoverable without workflow change)

**Problem Statement:**
SU's IT documentation lives in Confluence, where native search ranks poorly and the
content is invisible to Google and to LLM crawlers. Students ask AI tools instead of
reading docs, and get generic non-SU answers. The V4 direction is to publish the
Confluence corpus as a public, crawlable site so it can be found by search engines,
pulled into LLM training and retrieval over time, and consumed by a Claude skill for
immediate grounded answers.

**Solution:**
A publishing pipeline that converts Confluence pages into a static site on GitHub Pages,
built for both audiences at once. Every page ships as human-readable HTML and
machine-readable Markdown, with llms.txt, llms-full.txt (aggressive inlining), per-page
.md twins, a sitemap, an AI-bot-friendly robots.txt, and per-page JSON-LD. Built on
MkDocs Material with hand-rolled llms generation. The Confluence ingest reuses the
su-kb-mcp converter via editable install, filters to public pages only
(visibility_signal), preserves the Confluence hierarchy as navigable structure, and
dead-letters anything that cannot publish cleanly. Pilot scope is the 34-page ITSAI
space; target scale is ~4,338 pages across 70 spaces.

---

## Version History

### Version 1.0 - Pages Demo Pilot (2026-05-29)

**Project: su-kb-pages-demo**

**Primary Stakeholder:** SU Enterprise Claude users, the Claude skill, and LLM/search crawlers.

**Problem Statement:** Confluence content is undiscoverable by search and LLMs; the V4
program needs a concrete publishing target. This repo is that target.

**Solution:** MkDocs Material publishing pipeline on GitHub Pages with the full
machine-reader surface (llms.txt, llms-full.txt, per-page .md, sitemap, JSON-LD) plus a
Confluence ingest adapter over the su-kb-mcp converter. Initialized as a standalone repo
on the maintainer's personal GitHub for pilot velocity; eventual production home is the
SyracuseUniversity org repo behind docs.syr.edu/its-ai.
