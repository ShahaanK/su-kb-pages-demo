# CLAUDE.md -- su-kb-pages-demo

Publish half of the SU AI Knowledge-Base pipeline. Takes Markdown mirrored from
Confluence and publishes it to GitHub Pages as human-readable HTML plus
machine-readable Markdown (llms.txt, llms-full.txt, per-page .md twins),
optimized for LLM and search crawlers. The Claude skill and the MCP fallback
both consume the published corpus.

## Architecture

```
Confluence (ITSAI)
   |  INGEST  -> PageDoc objects -> docs/<space>/<slug>.md
   v
docs/**/*.md   (frontmatter + body)
   |  PUBLISH (this repo)
   |    mkdocs build --strict
   |    scripts/gen_llms.py        -> site/llms.txt + site/llms-full.txt
   |    scripts/mirror_markdown.py -> site/**/index.md  (per-page twins)
   |    touch site/.nojekyll
   v
GitHub Pages (HTML for humans/Google; .md + llms*.txt for agents/skill)
```

The **ingest half** is wired via `scripts/ingest/`. The converter source lives in
a separate repo (`su-kb-mcp`); see `scripts/ingest/INTEGRATION.md`.

## Working rules (non-negotiable)

1. **View source before writing glue.** Read the actual su-kb converter source
   before adapting it. Do not assume method names, return types, or CLI
   signatures. Writing blind has caused real bugs here.
2. **Plan before execute.** Propose a plan and stop for approval before edits.
3. **Phase-gated.** Dry run with counts only before any live Confluence write.
4. **Only `visibility_signal == public` is published.** This is a public site.
   Restricted/unknown pages are held, never written to docs/.
5. **Never disable `--strict` to make a build pass.** A strict failure (usually
   an unresolved wikilink) is the gate working. Fix or dead-letter the page.
6. **Do not edit `site_url` in mkdocs.yml or the host in docs/robots.txt.** The
   maintainer sets those.
7. No em-dashes in docs or commits; use ` -- ` or restructure.

## Ingest setup (one-time, local only)

Ingest requires su-kb-mcp (the converter). Install it as an editable dependency
in the same virtualenv as this repo:

```bash
pip install -e ../su-kb-mcp   # covers httpx, tenacity, anthropic, bs4, etc.
pip install -r requirements.txt
```

Credentials are read from `../su-kb-mcp/.env` automatically via pydantic-settings.

## Build and verify

```bash
pip install -r requirements.txt
mkdocs serve                 # live preview

# Full build (what CI does):
mkdocs build --strict
python scripts/gen_llms.py --docs docs --site site --config mkdocs.yml
python scripts/mirror_markdown.py --docs docs --site site
touch site/.nojekyll
```

CI is `.github/workflows/deploy.yml` (build -> generate -> deploy via GitHub
Pages). Pushing to `main` deploys.

## Ingest contract

`scripts/ingest/page_doc.py` defines `PageDoc` and `write_doc()`.
`scripts/ingest/transforms.py` defines `resolve_wikilinks()`, `is_public()`,
and `DeadLetter`. The converter must produce `PageDoc` objects; the two-pass
flow (build id->url map from public pages, resolve links, dead-letter
unresolved, write) is in `scripts/ingest/INTEGRATION.md`.

## Layout

```
mkdocs.yml                       site config (plain YAML; scripts parse it)
requirements.txt
.github/workflows/deploy.yml
overrides/main.html              per-page robots meta, .md alt link, JSON-LD
scripts/
  gen_llms.py                    llms.txt + llms-full.txt
  mirror_markdown.py             per-page .md twins
  ingest/
    page_doc.py, transforms.py   converter-agnostic ingest core (tested)
    INTEGRATION.md               converter handoff spec
docs/
  index.md, robots.txt, llms*.txt (placeholders), assets/css/syr.css
  ai-tools/*.md                  sample pages (replace at first real ingest)
TODO.md                          clementine.syr.edu exact-match styling (Phase 1)
```

## Stub vs real

- `docs/*.md` content is sample/placeholder until the first ITSAI ingest.
- `docs/assets/css/syr.css` is a clementine-inspired placeholder; the exact
  match is the Phase 1 task in `TODO.md`.
- `docs/llms.txt` / `docs/llms-full.txt` are placeholders that the post-build
  scripts overwrite in `site/`. They exist so internal links resolve under
  `--strict`. Do not delete them.
- llms generation is hand-rolled in `scripts/`; the `mkdocs-llmstxt` plugin is a
  documented swap-in (see requirements.txt).
