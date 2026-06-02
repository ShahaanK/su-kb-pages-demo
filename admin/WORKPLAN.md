# WORKPLAN.md

## Active Plan

### Milestone 1: Publishing Scaffold
- [✅] M1.T1 — Choose static site generator (MkDocs Material) after LLM-crawler research (Shahaan)
- [✅] M1.T2 — MkDocs Material config + overrides (robots meta, .md alt link, JSON-LD) (Shahaan)
- [✅] M1.T3 — gen_llms.py (llms.txt + llms-full.txt) (Shahaan)
- [✅] M1.T4 — mirror_markdown.py (per-page .md twins) (Shahaan)
- [✅] M1.T5 — robots.txt AI-bot allowlist + sitemap pointer (Shahaan)
- [✅] M1.T6 — clementine-inspired CSS stub (Shahaan)
- [✅] M1.T7 — GitHub Actions deploy workflow; live and green (Shahaan)

### Milestone 2: Confluence Ingest
- [✅] M2.T1 — Converter-agnostic ingest core (PageDoc, write_doc, transforms, DeadLetter), tested (Shahaan)
- [✅] M2.T2 — INTEGRATION.md handoff spec (Shahaan)
- [✅] M2.T3 — Adapter over su-kb-mcp converter via editable install (Shahaan)
- [✅] M2.T4 — Folder-based visibility (1069121551) + restrictions sanity check (Shahaan)
- [✅] M2.T5 — Wikilink bridge (Obsidian titles → numeric IDs) + dead-letter (Shahaan)
- [✅] M2.T6 — Haiku ai_description generation (Shahaan)
- [✅] M2.T7 — Dry run validated: 31 public / 3 held / 0 failures / 0 ACLs (Shahaan)
- [✅] M2.T8 — Fix baked EXAMPLE URLs; set site_url; re-ingest (Shahaan)
- [✅] M2.T9 — Preserve Confluence hierarchy in published paths; parent pages as section index pages; collapse redundant root (Shahaan)

### Milestone 3: Styling and Production
- [⏳] M3.T1 — Match clementine.syr.edu styling exactly (Shahaan)
- [✅] M3.T2 — Resolve site_url placeholder in robots.txt sitemap host (Shahaan)
- [ ] M3.T3 — Attachment/image handling in the ingest (Shahaan)
- [ ] M3.T4 — Cutover path to SyracuseUniversity org repo / docs.syr.edu (Shahaan + Aaron)
- [ ] M3.T5 — Fix sitemap lastmod to use frontmatter date, not build date (Shahaan)
- [✅] M3.T6 — validate_build.py: 9-invariant build gate (counts, degraded entries, frontmatter integrity, body integrity, wikilink leakage, root, robots host, home counts, gen_llms splitter agreement); full and --quick modes (Shahaan)
- [✅] M3.T7 — Fix split_frontmatter() in gen_llms.py: line-anchored regex; 4 degraded pages repaired (Shahaan)
- [✅] M3.T8 — Harden check_llms_full in validate_build.py: anchor on Source: not ---; body horizontal rules no longer create false block splits (Shahaan)
- [✅] M3.T9 — llms.txt quality: .md twin URLs + 6-section grouping (Overview / AI General Information / Claude / Clementine Platform / Copilot / Gemini) (Shahaan)
- [✅] M3.T10 — Visible "View raw .md" link on all content pages; rel=alternate head link preserved (Shahaan)
- [✅] M3.T11 — Root redirect (meta-refresh to /itsai/); hide: [toc] on itsai index; homepage count guard comment in home.html (Shahaan)
- [✅] M3.T12 — Gate wired: CI validation step in deploy.yml; pre-commit hook scripts/hooks/pre-commit (100755); Stop hook .claude/settings.json; --quick verified catching splitter bugs (Shahaan)

---

## Changelog

### 2026-06-02
- (Shahaan) ✅ M3.T6 -- validate_build.py written with 9 invariants and --quick mode
- (Shahaan) ✅ M3.T7 -- split_frontmatter() fixed; 4 degraded pages repaired in llms.txt (3 title loss + 1 wrong description field)
- (Shahaan) ✅ M3.T8 -- check_llms_full hardened to Source: anchor; immune to body --- horizontal rules
- (Shahaan) ✅ M3.T9 -- llms.txt now links to .md twins; 6-bucket per-tool section grouping
- (Shahaan) ✅ M3.T10 -- visible "View raw .md" link added to all content pages
- (Shahaan) ✅ M3.T11 -- root redirect, TOC hide on itsai index, homepage count guard comment
- (Shahaan) ✅ M3.T12 -- gate wired at CI + pre-commit (100755) + Stop hook; --quick verified catching splitter bugs in ~1s
- (Shahaan) ⏳ M3.T1 -- homepage restyle complete (home.html + 658-line CSS additions); Sherman Sans CORS confirmed; build --strict clean; machine surface verified 35 pages; push and Lighthouse pending

### 2026-06-01 (styling)
- (Shahaan) ⏳ M3.T1 -- clementine token extraction + full CSS/template implementation complete; pending mkdocs serve visual check + Lighthouse before push
- (Shahaan) ✅ M3.T2 -- robots.txt Sitemap host fixed: EXAMPLE -> shahaank (matches site_url)

### 2026-06-01
- (Shahaan) ✅ M2.T9 -- hierarchy restructure: 34 files (29 real + 5 hubs) written to nested paths; 29 stale flat files removed; mkdocs build --strict clean; gen_llms + mirror_markdown verified; gen_llms.py Windows URL bug fixed
- (Shahaan) ✅ Checkpoint 4 -- live write: 31 pages to docs/itsai/, guard passed, placeholders removed
- (Shahaan) ✅ Checkpoint 5 -- mkdocs build --strict clean; 32 pages in llms.txt and .md twins; deployed
- (Shahaan) ✅ M2.T8 -- site_url set and docs/itsai/ regenerated with correct internal URLs (confirmed via re-ingest)

### 2026-05-29
- (Shahaan) ✅ M1.T1–T7 — Publishing scaffold built and deployed live on GitHub Pages
- (Shahaan) ✅ M2.T1–T8 — Confluence ingest wired and validated on ITSAI (31/3, 0 failures, 0 ACLs)
- (Shahaan) 🔄 M1 — Switched generator from Python+Jinja2 to MkDocs Material after research
- (Shahaan) ⏳ M2.T9 — Hierarchy-preserving restructure in flight (Claude Code task)
- (Shahaan) 🆕 M3.T1–T5 — Styling and production milestone scoped
