# WORKLOG.md

## 2026-06-02 - M3.T1: Homepage restyle - Julian design port (Shahaan)

**Context**: Continuing M3.T1 styling work; porting the visual design from
julianhernandez2155.github.io/su-kb-site/ onto the MkDocs Material stack
without switching renderers (his site uses a custom Python renderer).

**Work Completed**:
- Fetched Julian's full design token set (tokens.css: spacing scale, radius, shadows,
  motion tokens, gradients) and landing/docpage CSS from GitHub raw; read gen_llms.py
  and mirror_markdown.py source before any implementation (CLAUDE.md rule 1 compliance)
- Confirmed script safety: gen_llms.py uses yaml.safe_load (unknown frontmatter keys
  silently ignored); mirror_markdown.py is a verbatim shutil.copy2 - adding
  "template: home.html" to frontmatter has zero impact on either script
- Created overrides/home.html: Material template override extending main.html;
  overrides content block with full-bleed hero (navy + layered radial gradients,
  staggered page-load reveal animation, gradient "AI" accent text in h1), 5-card
  tool grid (Claude featured with gradient border, 4 standard cards with orange
  top-bar hover effect), and 2-column navy content band with radial overlays
- Added "template: home.html" to docs/itsai/index.md frontmatter (markdown body
  unchanged; machine surface unaffected)
- Appended 658 lines to docs/assets/css/syr.css: extended design tokens (spacing,
  radius, shadows, motion, gradients, semantic color roles), :has()-based full-bleed
  Material content column reset, hero/eyebrow/button/badge/card/band CSS, hub page
  list card treatment (pure CSS targeting h2#pages-in-this-section ~ ul), and
  prefers-reduced-motion guard for all animations
- Re-injected #main-content skip anchor in home.html content block (required because
  overriding the block removes main.html's own injection)
- Card text color changed from #707780 (4.1:1, fails AA) to #404040 (9.4:1) for
  card descriptions; all other hero/band colors verified AA or better
- Confirmed Sherman Sans CORS: assets.syracuse.edu returns HTTP 200 +
  Access-Control-Allow-Origin: * - no CORS fallback to Verdana
- Fixed hero stat "34 pages" -> "35 pages" to match corpus count
- mkdocs build --strict clean; gen_llms.py + mirror_markdown.py both produce 35
  entries; sitemap and robots.txt unchanged; 25/25 HTML element checks pass

**Impact**: Homepage now has a polished, full-bleed landing experience matching
Julian's design quality - hero band, tool-card grid with hover effects and a featured
Claude card, navy content band. Section hub pages (claude/, gemini/, etc.) get
card-style link treatment for their child-page lists via pure CSS, no ingest change.
Machine surface untouched. Changes uncommitted pending user push.

**Next Steps**: User to commit and push; visual spot-check of hero full-bleed and
hub cards in browser; Lighthouse accessibility >= 95 (not run this session)

---

## 2026-06-01 - M3.T1/T2: Clementine styling + robots.txt fix (Shahaan)

**Context**: Replacing the placeholder CSS stub with real design tokens extracted from
clementine.syr.edu/site.css, and wiring the SU-branded header/footer overrides in MkDocs Material.

**Work Completed**:
- Fetched live clementine.syr.edu/site.css; extracted exact design tokens: Sherman Sans
  @font-face (assets.syracuse.edu CDN), full SU palette (#000E54 navy, #F76900 orange,
  #D74100 orange-dark), link, heading, and layout values
- Replaced docs/assets/css/syr.css with real tokens: @font-face for Sherman Sans
  (400/400i/700), all SU CSS custom properties, Material --md-* overrides (navy primary,
  orange accent, #C44200 AA-safe body links -- clementine's #D74100 is 4.4:1, just under AA)
- Saved SU horizontal orange logo SVG locally to docs/assets/images/
- Updated mkdocs.yml: font: false (stops Google Fonts Roboto load), logo,
  homepage: https://www.syracuse.edu (logo links to SU homepage via Material's built-in key)
- Rewrote overrides/main.html: SU skip link as first focusable element (targets #main-content),
  content anchor span, 3-column SU footer (brand + Resources + Policies) matching clementine
  exactly; Material's prev/next page nav preserved via {{ super() }}
- H2/H3: Sherman Serif (Georgia fallback) + navy, matching clementine's section heading
  treatment; H1: Sherman Sans bold; H4-H6: Sherman Sans
- Fixed docs/robots.txt Sitemap host: EXAMPLE -> shahaank (matches site_url in mkdocs.yml)
- Replaced 75 em-dashes across 12 ingested docs files with single dash per corrected rule
- Updated CLAUDE.md em-dash rule: use ` - ` (not ` -- `)
- mkdocs build --strict: clean; 15/15 structural checks pass

**Impact**: KB site reads as a Syracuse University product - navy header with SU orange
wordmark linking to syracuse.edu, 3-column navy footer matching clementine, Sherman Sans
body + Georgia serif H2s, WCAG-AA-compliant link colors. M3.T2 complete; M3.T1 pending
visual confirmation (mkdocs serve + Sherman Sans CORS check + Lighthouse).

**Next Steps**: Run mkdocs serve; check Network tab for Sherman Sans 200s (self-host if 403);
visual compare to clementine; Lighthouse accessibility >= 95; then push

---

## 2026-06-01 - M2.T9: Confluence hierarchy restructure -- live write and verified (Shahaan)

**Context**: Restructuring the flat docs/itsai/ layout to mirror the Confluence page tree: AI@SU root, five generated section hubs (claude/, gemini/, clementine-platform/, copilot/, example-uses/), and all 29 real pages nested under their sections.

**Taxonomy Decisions**:
- AI and AI-General-Information phantom containers collapsed -- both were empty (0 words) and not in the published page set; their children promoted to the root level or to their nearest named section
- claude/, gemini/, clementine-platform/, copilot/ kept as top-level generated hub sections
- example-uses/ nested one level deeper under claude/ (faithful Confluence parent)
- Two test pages excluded by page ID: (Test) Resume Tailor Machine Brain (948797482) and The Workflow (965672963) -- scratch content not fit for the public site

**Work Completed**:
- Extended PageDoc with 4 hierarchy fields (raw_ancestor_ids, ancestor_slugs, is_section_index, is_space_root); fixed url_path() to return directory URL for index.md pages
- Rewrote run_ingest.py orchestration: build_hierarchy maps phantom section IDs to slugs, generate_hub_pages synthesizes 5 section landing pages with relative .md child links, stale cleanup removes all old flat files
- Added EXCLUDED_PAGE_IDS to suppress two test pages by ID regardless of folder
- Path collision check keyed on str(rel_path()) instead of slug() -- correct for nested directories
- Dry run validated: 34 total (29 real + 5 hubs), 3 restricted, 2 excluded, 0 failures -- path map matched approved design exactly
- Live write: 34 files written to nested paths; 29 stale flat files removed
- mkdocs build --strict: clean pass
- gen_llms.py + mirror_markdown.py: 35 pages each
- Fixed gen_llms.py page_url() using sub.as_posix() to emit forward-slash URLs on Windows
- Pushed to GitHub Pages

**Problems Identified**:
- All 5 phantom section containers (Claude, Gemini, Copilot, Clementine Platform, Example Uses) confirmed empty (0 words) -- not real content pages, just Confluence organizational nodes; fetching their bodies would return nothing
- gen_llms.py page_url() emitted Windows backslashes in nested URLs (pre-existing bug, only surfaced once paths became nested)

**Solution Implemented**:
- Generated hub pages are 100% synthesized (intro paragraph + relative .md child list); no Confluence fetch needed for hub bodies
- page_url() fixed to use Path.as_posix() for cross-platform URL correctness

**Impact**: ITSAI site live on GitHub Pages with a real hierarchy: claude/, gemini/, clementine-platform/, copilot/ section hubs with clickable landing pages; example-uses/ nested under claude/. Milestone 2 complete.

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
