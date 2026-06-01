# TODO

## Match clementine.syr.edu exactly (styling)

We are extending clementine.syr.edu, so this docs site should read as the same
product. The Phase 0 `docs/assets/css/syr.css` is a placeholder (SU-orange
guess). Replace it with the real clementine design, applied through MkDocs
Material's `overrides/` + `extra_css`.

### Known from the live site (2026-05)

| Element | Detail |
|---|---|
| Logo | SU horizontal one-line orange wordmark: `https://assets.cdn.syr.edu/logos/syr_horizontal_1Line_orange.svg`, links to `https://www.syracuse.edu` |
| Accessibility | "Skip to main content" link to `#main-content` as the first focusable element |
| Footer | Two columns. **Resources**: Syracuse University, Information Technology Services, Answers (SU Help). **Policies**: AI Data & Privacy FAQ, Accessibility, Privacy Policy, IT Policies. Logo repeated above a one-line tagline |
| Brand color | Syracuse Orange (approx `#F76900`); confirm exact value from CSS |
| CDN | Shared SU assets live under `assets.cdn.syr.edu` |

### Extraction steps for an exact match (needs devtools, cannot be guessed)

1. Open clementine.syr.edu, devtools -> Network/Sources. Find the linked
   stylesheet(s) (`<link rel="stylesheet">`) and any `@font-face` / Google Fonts.
2. Capture exact values:
   - [ ] Primary + secondary hex (orange, navy/any accent), from computed styles
   - [ ] Font families for headings vs body (SU brand typeface), with fallbacks
   - [ ] Base font size, line-height, heading scale
   - [ ] Link color + hover/underline behavior
   - [ ] Header height, background, logo placement/padding
   - [ ] Footer background, column layout, link styling, tagline type
   - [ ] Max content width / container gutters
   - [ ] Border-radius, shadow, button styling conventions
3. Note whether a shared SU design-system CSS exists on `assets.cdn.syr.edu`
   that we can link directly rather than re-deriving.

### Apply in MkDocs

- [ ] Put exact tokens in `docs/assets/css/syr.css` as CSS custom properties,
      overriding Material's `--md-*` variables (primary, accent, typeset).
- [ ] Load the SU brand font via `extra_css` or an `@font-face` (or the SU CDN
      font URL if one exists).
- [ ] Override `overrides/main.html` (and partials) to render the SU horizontal
      orange logo in the header linking to syracuse.edu, plus the skip-to-main
      link.
- [ ] Add a footer partial override matching the Resources / Policies two-column
      layout and the repeated-logo + tagline block. Adapt the tagline for the KB
      (e.g. "Syracuse University ITS AI Knowledge Base -- built by Syracuse, for you.").
- [ ] Keep WCAG: visible focus states, color contrast >= AA, working skip link.

### Acceptance criteria

- [ ] Side-by-side, header + footer + type + color read as the same product as
      clementine.syr.edu.
- [ ] Lighthouse accessibility >= 95.
- [ ] `mkdocs build --strict` still clean.

> Note: this is a Phase 1 task per the plan. Do it after live ITSAI ingest so we
> are styling real content, not the placeholder samples.
