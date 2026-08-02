# Viewer Page Export Design

## Goal

Add page-scoped copy and download controls to the Viewer so a reader can reuse the current article without navigating to the source file or exporting the surrounding application shell.

The feature supports:

- Copy original Markdown, including frontmatter.
- Copy body-only Markdown, excluding frontmatter.
- Copy rendered rich text with a plain-text fallback.
- Download the original Markdown file.
- Download a self-contained HTML document of the rendered article.

## Scope

In scope:

- Knowledge pages, engineering interview pages, and supported root Markdown pages rendered by `viewer.html`.
- The standalone Viewer and the same Viewer embedded in the Web workbench.
- Desktop placement beside the rendered article title.
- Clipboard capability detection, download generation, filename normalization, feedback, and regression tests.

Out of scope:

- PDF generation. Readers may use the browser print dialog on the exported HTML.
- Batch export, section export, or full-knowledge-base archives.
- Editing or saving changes back to Markdown files.
- Server-side export endpoints.
- Export controls for graph views, Claude conversations, navigation, page quality, or taxonomy panels.
- Mobile-specific layout redesign. Existing responsive constraints still apply.

## Chosen Approach

Implement export entirely in `viewer.html`. The Viewer already receives the exact source Markdown, separates frontmatter from the body, renders sanitized HTML, and knows the active file and title. Reusing those values avoids a second page request and keeps the feature available in both standalone and embedded contexts.

No new endpoint is added to `scripts/serve_kb.py`. Export is a local browser operation and must not trigger knowledge refresh, taxonomy work, index generation, or graph generation.

## User Interface

The Viewer inserts a compact action group beside the rendered top-level `H1` after each successful page render. It contains two icon buttons:

- Copy: opens a menu with three formats.
- Download: opens a menu with two formats.

The buttons use familiar copy and download icons, accessible names, titles, and keyboard-operable menus. Only one menu may be open at a time. Clicking outside, pressing Escape, changing pages, or starting a new navigation closes the menu.

The action group belongs to the article header, not the global workbench toolbar. It therefore remains available when `viewer.html` is opened directly and when it is hosted inside the knowledge iframe.

The controls must not change the article width or cause the title to overlap. The title and action group share a responsive header row; a long title wraps while the actions retain stable dimensions. On narrow viewports, the actions may move below the title without changing button size.

## Export Formats

### Original Markdown

The original Markdown is the exact response body fetched for the active file, including frontmatter delimiters and original whitespace. It is used for:

- Copy original Markdown.
- Download original Markdown.

The Viewer must retain this complete source in the active-page state. Reconstructing frontmatter from parsed metadata is not allowed because it could change ordering, quoting, comments, or whitespace.

### Body-Only Markdown

Body-only Markdown is the `body` returned by the existing `splitFrontmatter()` function. No additional formatting, link rewriting, or whitespace normalization is applied. A page without frontmatter produces the same content for original and body-only copy.

### Rendered Rich Text

Rich-text copy writes two clipboard representations in one operation:

- `text/html`: a sanitized clone of the rendered article.
- `text/plain`: the article's readable text content.

The cloned HTML excludes the export action group and any transient loading or error UI. It preserves rendered headings, emphasis, lists, tables, code blocks, KaTeX output, images, and rendered Mermaid SVG when present.

The rich-text operation uses `ClipboardItem` and `navigator.clipboard.write()` when supported. If HTML clipboard writing is unavailable, the operation falls back to copying the plain-text representation and reports that fallback instead of claiming that rich text was copied.

### Self-Contained HTML

The HTML download is a complete UTF-8 document containing only the current article and document metadata needed for standalone reading:

- A document title derived from the rendered page title.
- A viewport declaration.
- Inline article layout, typography, table, code, interview-page, image, and Mermaid styles.
- Inline KaTeX CSS needed by the rendered formula markup.
- A sanitized clone of the rendered article with export controls removed.

Article assets are embedded so the file remains readable outside the knowledge server:

- Image `src` values are resolved with the browser `URL` API, fetched, and converted to `data:` URLs.
- Link `href` values are resolved to absolute URLs unless they are fragment-only links.
- Rendered Mermaid SVG is included directly in the cloned article.
- KaTeX font files referenced by the inlined stylesheet are fetched and converted to `data:` URLs.

The HTML contains no runtime asset dependency and remains readable without the knowledge service or JavaScript. If a required image, stylesheet, or font cannot be fetched, HTML generation fails with the unavailable asset named in the error. The Viewer does not silently produce a partially self-contained file.

## Filenames

The Markdown download prefers the basename of the active Markdown file. The HTML filename uses the rendered page title with an `.html` extension.

Filename normalization:

- Replace `/`, `\\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`, and ASCII control characters with `_`.
- Trim leading and trailing spaces and trailing periods.
- Use `knowledge-page` if normalization produces an empty name.
- Preserve Chinese characters and ordinary spaces.

## State And Data Flow

Each successful navigation stores an immutable active export snapshot containing:

- Navigation generation token.
- Active file and section.
- Rendered title.
- Exact original Markdown source.
- Body-only Markdown.

The existing page fetch result must therefore include both the complete source and the existing parsed fields. Export handlers read the current snapshot at activation time. They do not close over a snapshot created for an earlier page.

The render sequence is:

1. Fetch and parse the target Markdown.
2. Render and sanitize the article, including conditional KaTeX, highlighting, and Mermaid work.
3. Verify the navigation generation.
4. Commit title, active navigation, and workbench context.
5. Store the export snapshot.
6. Mount the article action group beside the rendered `H1`.
7. Complete navigation and start existing asynchronous enrichment.

Starting another navigation closes open export menus immediately. A stale render may not replace the current export snapshot or action group because both remain protected by the existing navigation generation checks.

## Clipboard And Download Behavior

Plain Markdown formats use `navigator.clipboard.writeText()`. Clipboard operations are allowed only from a direct user activation. The Viewer does not request clipboard read permission.

Downloads use a `Blob`, a temporary object URL, and a temporary anchor with the `download` attribute. The object URL is revoked after activation. No generated export is stored in the repository or sent to the server.

Menu commands expose a busy state while preparing their payload. Repeated activation of the same command while it is busy is ignored. Copying or downloading does not change the current page, URL, scroll position, navigation history, or workbench context.

## Feedback And Errors

Successful operations use the existing Viewer status region and name the exact result:

- Original Markdown copied.
- Body-only Markdown copied.
- Rich text copied.
- Plain text copied because rich-text clipboard is unavailable.
- Markdown downloaded.
- HTML downloaded.

Feedback is concise and disappears after a short interval only if no newer status has replaced it. It must not overwrite navigation failures or other error alerts.

Failures produce an alert with the failed action and a useful reason. Clipboard failure leaves the menu open for retry. Download generation failure also leaves the menu open. The current article and export snapshot remain unchanged.

If no successful page snapshot exists, export controls are not mounted. If the rendered page has no `H1`, the existing filename-derived page title is shown in a generated article header so the controls still have a stable location.

## Security

- Export HTML is built from the already sanitized article clone.
- The action group and transient UI are explicitly removed from the clone.
- No raw Markdown is injected into HTML without the existing Marked and DOMPurify pipeline.
- Generated HTML contains no application scripts or event-handler attributes.
- URL resolution uses the browser `URL` API. Exported links preserve only normal `http:`, `https:`, `mailto:`, and fragment references. Exported image sources contain only generated `data:` URLs. Unsafe schemes are removed from the export clone.
- Clipboard HTML and downloaded HTML use the same sanitized clone helper so their security behavior cannot drift.

## Accessibility

- Icon buttons have visible tooltips through `title` and explicit `aria-label` values.
- Menus use buttons for commands and expose their expanded state with `aria-expanded`.
- Opening a menu moves focus to its first command.
- Arrow keys move through commands; Home and End move to the first and last command.
- Escape closes the menu and returns focus to its trigger.
- Status and failure messages continue using the existing status/alert role behavior.

## Testing

### Viewer Contracts

- The page fetch result retains exact source Markdown.
- Export actions are mounted only after a successful current-generation render.
- Copy and download menus expose the five exact commands and accessible attributes.
- Export clones remove action UI and unsafe URLs.
- Filename normalization covers invalid characters and empty results.
- Page navigation closes menus and replaces the export snapshot.

### Browser Regressions

- Copy original Markdown preserves frontmatter and original source text.
- Copy body-only Markdown excludes frontmatter without rewriting Markdown.
- Rich-text copy provides both HTML and plain-text representations when supported.
- Rich-text fallback reports plain-text copy accurately.
- Markdown download uses the source basename and exact source bytes.
- HTML download contains the rendered title, article markup, inline styles, embedded image and KaTeX font data, KaTeX markup, and Mermaid SVG while excluding Viewer navigation and export controls.
- Exporting after rapid page navigation always uses the final active page.
- A long page title wraps without overlapping the two action buttons at desktop widths.
- Existing navigation, rendering, workbench context, and performance-budget tests remain green.

## Acceptance Criteria

- Every successfully rendered Markdown page exposes copy and download controls beside its title.
- All three copy formats and both download formats behave as specified.
- Export operations never trigger a server refresh or a second page fetch.
- Exported HTML contains only the article and remains readable without JavaScript.
- Stale navigation cannot export or label an earlier page as the active page.
- Clipboard and download failures are recoverable and do not remove the readable article.
- Existing Viewer and desktop browser regressions continue to pass.
