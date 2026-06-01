# WORKLOG.md

## 2026-06-01 - M2.T9: Confluence hierarchy restructure -- live write and verified (Shahaan)

**Context**: Restructuring the flat docs/itsai/ layout to mirror the Confluence page tree: AI@SU root, five generated section hubs (claude/, gemini/, clementine-platform/, copilot/, example-uses/), and all 29 real pages nested under their sections.

**Work Completed**:
- Extended PageDoc with 4 hierarchy fields (raw_ancestor_ids, ancestor_slugs, is_section_index, is_space_root); fixed url_path() to return directory URL for index.md pages
- Rewrote run_ingest.py orchestration: build_hierarchy maps phantom section IDs to slugs, generate_hub_pages synthesizes 5 section landing pages with relative .md child links, stale cleanup removes all old flat files
- Added EXCLUDED_PAGE_IDS to suppress two test pages (948797482, 965672963) by ID regardless of folder
- Path collision check keyed on str(rel_path()) instead of slug() -- correct for nested directories
- Dry run validated: 34 total (29 real + 5 hubs), 3 restricted, 2 excluded, 0 failures -- path map matched approved design exactly
- Live write: 34 files written to nested paths; 29 stale flat files removed
- mkdocs build --strict: clean pass
- gen_llms.py + mirror_markdown.py: 35 pages each
- Fixed gen_llms.py page_url() using sub.as_posix() to emit forward-slash URLs on Windows

**Impact**: ITSAI site now has a real hierarchy: claude/, gemini/, clementine-platform/, copilot/ section hubs with clickable landing pages; example-uses/ nested under claude/. All 34 paths confirmed in site/itsai/. llms.txt URLs corrected for Windows.

**Next Steps**: User review and push to GitHub Pages.

---

## 2026-06-01 - Checkpoint 4/5: live write executed and deployed (Shahaan)

**Context**: Completing the ITSAI live write after a context-window gap -- final pre-write verification, then write and deploy.

**Work Completed**:
- Verified enhanced dry-run output: restrictions check (34 pages, 0 ACLs all clear), sample stripped targets (all image attachments + 1 cross-space ref, 0 in-ITSAI bridge failures), macro breakdown (iframe: Clementine Class Search; view-file: Claude Code Setup)
- Executed live write (Checkpoint 4): 31 pages to docs/itsai/, 3 test pages held, ai-tools/ placeholders removed, post-write [[...]] guard passed
- Fixed dead-letter mkdir ordering bug -- directory was created in Step 4 but _append_links_record in Step 3 needed it first; moved mkdir to before the Step 3 loop
- Set site_url in mkdocs.yml; re-ran ingest to regenerate docs/itsai/ with correct internal link URLs (32 files updated)
- Checkpoint 5: mkdocs build --strict clean; gen_llms.py (32 pages) and mirror_markdown.py (32 twins) ran successfully
- Deployed to GitHub Pages

**Impact**: ITSAI space live on GitHub Pages with 31 real Confluence pages, llms.txt, and 32 per-page .md twins. All milestone 2 tasks complete except hierarchy restructure (M2.T9).

**Next Steps**: Preserve Confluence hierarchy in published paths (M2.T9); match clementine.syr.edu styling (M3.T1).

---

## 2026-05-29 - Pages Demo Build, Deploy, and ITSAI Ingest (Shahaan)

**Context**: Stand up the V4 publishing half as a standalone repo, get it live on
GitHub Pages, and wire the Confluence ingest for the ITSAI pilot space.

**Work Completed**:
- (Shahaan) Researched LLM-crawler-optimized static-site best practices; chose MkDocs Material over pure Python+Jinja2 for the built-in llms.txt / sitemap / parallel-md tooling
- (Shahaan) Built the publishing scaffold: MkDocs Material config, overrides/main.html for per-page robots meta + .md alternate link + TechArticle JSON-LD, clementine-inspired CSS stub, AI-bot allowlist robots.txt
- (Shahaan) Hand-rolled gen_llms.py (llms.txt + llms-full.txt) and mirror_markdown.py (per-page .md twins) so the build depends only on mkdocs-material
- (Shahaan) Wired GitHub Actions deploy workflow; site went live and green on GitHub Pages with sample content
- (Shahaan) Reviewed Julian's su-kb-pipeline; adopted dead-letter routing and attachment-verification patterns, rejected agent-corpus patterns (orientation files, wikilinks, raw/wiki split) for the public site
- (Shahaan) Built the converter-agnostic ingest core (PageDoc contract, write_doc, resolve_wikilinks, is_public, DeadLetter) and tested it end to end
- (Shahaan) Wired the Confluence ingest adapter over the su-kb-mcp converter via editable install; dry run validated ITSAI at 31 public / 3 restricted (the 3 intern test pages held by folder rule 1069121551) / 0 conversion failures / 0 Confluence ACLs
- (Shahaan) Caught and fixed baked EXAMPLE URLs in resolved wikilinks; set real site_url and re-ran ingest so internal links resolve to the correct domain

**Problems Identified**:
- (Shahaan) Ingest config failed at first because su-kb-mcp Settings looks for .env in the working directory, not across the editable-install path
- (Shahaan) Published paths flattened the Confluence hierarchy; all 31 pages landed flat under itsai/ instead of mirroring the AI > Claude/Copilot/Gemini/mentorAI tree

**Solution Implemented**:
- (Shahaan) Copied su-kb-mcp .env into the pages repo (gitignored) so pydantic-settings resolves credentials
- (Shahaan) Scoped a hierarchy-preserving restructure (parent pages as section index pages, redundant root collapsed) as the next Claude Code task

**Impact**: V4 publishing half is live and green with real ITSAI content validated.
The concrete docs.syr.edu/its-ai vision now exists as a working pilot.

**Next Steps**:
- Restructure published paths to preserve the Confluence hierarchy with section index pages
- Match clementine.syr.edu styling exactly (Phase 1)
- Resolve the SyracuseUniversity org-repo cutover path with Aaron

---
