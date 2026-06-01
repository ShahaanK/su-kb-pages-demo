# Ingest integration brief

This is the one ingest step that needs the **su-kb converter source** and
**Confluence credentials**, so it is done locally (good Claude Code task),
not from a sandbox. The converter-agnostic core is already built and tested:

- `page_doc.py` -- the `PageDoc` contract + `write_doc()` (writes `docs/<space>/<slug>.md`)
- `transforms.py` -- `resolve_wikilinks()`, `is_public()`, `DeadLetter`

Your job is to make the su-kb converter produce `PageDoc` objects and run the
two-pass flow below. **View the su-kb converter source before writing any glue**
(`converter.py`, `sync_engine.py`, `walker.py`, `client.py`, frontmatter/
classifier modules). Do not guess method names or return types.

## Field mapping (su-kb -> PageDoc)

| PageDoc field | Source in su-kb |
|---|---|
| `page_id` | Confluence page id |
| `space` | space key (`ITSAI` for the pilot) |
| `title` | page title |
| `body_markdown` | converter output (storage XHTML -> Markdown) |
| `description` | first ~150 chars of body, or Confluence excerpt if present |
| `ai_description` | generate with Haiku 4.5 (locked decision); one factual line |
| `date` / `lastmod` | Confluence created / lastModified (ISO date) |
| `authors` | contributors/version-by |
| `tags` | Confluence labels (sparse; fine if empty) |
| `visibility_signal` | from Julian's classifier frontmatter (`public`/`restricted`/`unknown`) |

## Two-pass flow

```python
import sys; sys.path.insert(0, "scripts/ingest")
from page_doc import PageDoc, write_doc
from transforms import resolve_wikilinks, is_public, DeadLetter
from pathlib import Path

docs = Path("docs")
dl = DeadLetter("dead-letter")
BASE = "https://<you>.github.io/su-kb-pages-demo"   # match site_url

# 0. Pull + convert ITSAI via su-kb -> list[PageDoc]  (the part you wire up)
pages = build_pagedocs_from_su_kb(space="ITSAI")

# 1. Public-only, then build the id->url map (wikilinks can only target published pages)
public = [p for p in pages if is_public(p.visibility_signal)]
id_to_url   = {p.page_id: p.url_path(BASE) for p in public}
id_to_title = {p.page_id: p.title          for p in public}

# 2. Resolve links, dead-letter anything unresolved, write
for p in public:
    p.body_markdown, unresolved = resolve_wikilinks(p.body_markdown, id_to_url, id_to_title)
    if unresolved:
        dl.record(p.page_id, f"unresolved wikilinks: {unresolved}", title=p.title, body=p.body_markdown)
    write_doc(p, docs)
```

## Checkpoints (phase-gated)

1. **Dry run first.** Convert to `PageDoc`s and print counts (total, public, held,
   dead-lettered) BEFORE writing anything live. Confirm ~31 public / 3 restricted
   for ITSAI, matching the classifier.
2. **Delete the 3 sample pages** (`docs/index.md` stays as the hub; remove the
   `docs/ai-tools/*.md` samples) once real pages land, or fold them in.
3. **Local verify** before push:
   ```
   mkdocs build --strict
   python scripts/gen_llms.py --docs docs --site site --config mkdocs.yml
   python scripts/mirror_markdown.py --docs docs --site site
   ```
   `--strict` will fail on any unresolved wikilink that slipped past the dead-letter
   pass. That is the gate working; fix or quarantine the page, do not disable strict.
4. Push; confirm the Actions run is green and the live ITSAI pages render.

## Attachments (next iteration, not required for first pull)

Images/attachments are not handled by this core yet. When added: download +
verify, copy under `docs/assets/<page-id>/`, rewrite refs in `body_markdown`
before `write_doc`. Mirror su-kb's existing attachment verification.
