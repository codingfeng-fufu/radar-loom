# Viewer Navigation Performance Design

## Goal

Make desktop knowledge-page navigation feel immediate without requiring taxonomy, graph, or page-quality data to be current before the target article appears.

The performance budgets are:

- Show navigation feedback within 100 ms of activation.
- Complete a same-section page switch within 300 ms under normal local conditions.
- Complete a cross-section switch within 500 ms under normal local conditions.
- Keep the last readable article visible when the target page cannot be loaded.

These budgets apply after the Viewer application has loaded. Full browser startup is measured separately because it includes loading the local rendering libraries.

## Current Bottleneck

`navigateTo()` fetches the section index before every page request. Generated-artifact routes in `scripts/serve_kb.py` call `KnowledgeBuilder.refresh()` before returning `_index.md`, `_interview_index.md`, graph JSON, or `/api/catalog`. Once the periodic taxonomy check is active, that refresh holds one global lock while running both taxonomy profiles and, when stale, the index and graph generators.

The Viewer also waits for `renderPageQuality()` before inserting the article. A slow catalog request therefore leaves the content area unchanged even after the Markdown page has arrived. The taxonomy summary fetch is started on every navigation and competes for the same server refresh lock.

Observed behavior on 2026-08-01:

- Clean-server initial article: about 700-740 ms.
- Same-section page switch: 36-58 ms.
- Mermaid interview switch: 104-208 ms.
- Long-running server `_index.md` first byte: 21.75 seconds.
- Long-running server logs show refresh-triggered waits of roughly 19-33 seconds.

## Chosen Approach

Use phased decoupling:

1. Keep parsed section indexes in Viewer memory and reuse them for navigation.
2. Serve indexes and graph JSON as static artifacts without running generators in the request path.
3. Render the target Markdown as soon as it is fetched and parsed.
4. Load page quality and taxonomy summary asynchronously after the article is visible.
5. Keep explicit refresh as the operation that rebuilds taxonomy, indexes, and graphs, then invalidate Viewer caches.

This preserves the existing file-based architecture and refresh workflow while removing expensive maintenance work from ordinary reads.

## Architecture

### Static Read Path

Ordinary GET requests for these paths only read the existing artifact:

- `/_index.md`
- `/_interview_index.md`
- `/graph-data.json`
- `/interview-graph-data.json`
- `/api/catalog`

They do not call taxonomy, index, or graph generators. `/api/catalog` builds its JSON response from the current graph artifacts in memory or from a direct file read; failure returns an API error without delaying static Markdown.

### Explicit Maintenance Path

`POST /api/refresh` remains the authoritative full refresh operation. It may run taxonomy synchronization, index generation, and graph generation under the existing lock. A successful response returns the new revision and graph statistics.

`POST /api/taxonomy/rebuild` retains its existing explicit global-rebuild behavior. No periodic taxonomy process is started by a Viewer read request.

### Viewer Index Cache

Each section state owns a parsed-index cache with:

- the parsed groups and entries;
- an in-flight promise used to coalesce concurrent first loads;
- a generation or invalidation marker.

The first visit to a section fetches and parses its index. Later navigation in that section reuses the parsed value. Crossing into a section that has not been loaded fetches that section once. A failed first load clears the in-flight promise so retry remains possible.

After a successful explicit refresh, both section caches are invalidated. The active section is fetched again before the refresh operation is reported as fully recovered.

### Navigation Pipeline

The navigation sequence is:

1. Increment the existing navigation generation token.
2. Show a restrained navigation-progress state within the current document shell.
3. Resolve the requested section from cached index data when available.
4. Fetch the target Markdown.
5. Verify the generation token and detected section.
6. Commit section/navigation state and render sanitized Markdown immediately.
7. Render math, code, and Mermaid only when the article contains the corresponding syntax.
8. Clear navigation progress and publish active-page context.
9. Start page-quality and taxonomy-summary enrichment without awaiting them.

The existing generation token continues to ensure that an older request cannot replace the result of a newer click.

### Progressive Enrichment

Page quality and taxonomy summary are secondary information:

- Article rendering never awaits `/api/catalog`.
- The quality panel shows a neutral loading state while catalog data is pending.
- If catalog loading fails, the quality panel uses body/frontmatter facts that can be computed locally and marks graph-dependent facts as unavailable.
- Taxonomy summary failure changes only the summary status.
- A stale enrichment response checks both its own generation and the active file/section before updating the DOM.

### Conditional Rendering Work

The initial HTML continues using the existing local libraries to avoid introducing a bundler in this change. Per-page work is conditional:

- Run KaTeX auto-render only when extracted math regions exist.
- Run Highlight.js only when non-Mermaid fenced code exists.
- Convert and render Mermaid only when Mermaid blocks exist.

Lazy-loading the 2.5 MB Mermaid browser bundle is deferred from this plan because it changes runtime dependency loading and error states. It can be evaluated independently after the blocking request path is removed.

## Loading And Error States

Navigation feedback must not erase the current article. While a target is loading:

- Keep the current article readable.
- Mark the content surface as busy with `aria-busy="true"`.
- Show a compact status indicating that the requested page is opening.
- Disable no unrelated controls.

On success, replace the article atomically and clear the busy state. On failure, preserve the prior article, clear the busy state, and expose the existing retry action with the intended file and section.

Rapid repeated navigation uses last-intent-wins behavior. Earlier fetches may finish, but generation checks prevent them from committing content, history, quality, or taxonomy state.

## Consistency Model

The Viewer is allowed to show the latest generated index and graph artifacts even when Markdown files are newer. This is the explicit product choice behind fast navigation.

- Direct links to a valid Markdown path remain loadable even if the cached index does not list the page yet.
- Newly created pages become discoverable in navigation after explicit refresh.
- Existing page edits are visible on direct navigation because page Markdown is fetched with `no-store`.
- Graph, taxonomy, incoming-link, and broken-link facts may remain at the previous generated revision until refresh.
- The workbench refresh result remains the point at which all active generated surfaces are expected to agree.

## Scope

In scope:

- Desktop Viewer page navigation.
- Knowledge and engineering-interview section indexes.
- Static/generated artifact request behavior in `serve_kb.py`.
- Async page-quality and taxonomy enrichment.
- Conditional per-page math, code, and Mermaid work.
- Loading, failure, rapid-click, cache-invalidation, and performance regression tests.

Out of scope:

- Graph-view rendering performance.
- Claude conversation UI or history.
- Mobile layout changes.
- Knowledge-page content changes.
- Taxonomy algorithms, clustering thresholds, or category design.
- Replacing the current browser libraries or adding a frontend build system.

## Testing Strategy

### Python Contracts

- Static artifact GETs must not call `KnowledgeBuilder.refresh()` or any generator.
- `/api/catalog` must return current artifact data without maintenance work.
- Explicit refresh must still run maintenance and return revision/stats.
- Existing upload, origin, taxonomy rebuild, and refresh security contracts must remain unchanged.

### Viewer Contracts

- A loaded section index is reused for subsequent navigation.
- Concurrent first loads share one in-flight index request.
- Failed index loads can be retried.
- Successful refresh invalidates both section caches.
- `renderPageData()` does not await page quality before article insertion.
- Math, highlighting, and Mermaid work is conditional.
- Loading and error states preserve the current article.

### Browser Regressions

- Delay `/api/catalog` and graph JSON while asserting that the target article becomes visible.
- Delay taxonomy-related endpoints while switching pages in the same section.
- Assert one index request across repeated same-section navigation.
- Assert one first-load request per section during cross-section navigation.
- Click multiple pages rapidly and verify that only the final target commits.
- Run explicit refresh and verify that the active index is fetched again.
- Verify navigation feedback appears within 100 ms.
- Measure same-section completion below 300 ms and cross-section completion below 500 ms using controlled local fixtures without intentional network delay.

Performance tests report measured duration in failure output. They use a clean local server and project Playwright configuration to avoid conflating long-running external process state with the navigation implementation.

## Acceptance Criteria

- Ordinary page reads never run taxonomy, index, or graph generators.
- Same-section navigation does not fetch the section index again.
- Article visibility does not depend on catalog or taxonomy completion.
- Explicit refresh remains functional and invalidates cached indexes.
- Slow or failed enrichment never removes or delays readable article content.
- Last-intent-wins navigation remains correct under rapid clicks.
- The 100 ms feedback, 300 ms same-section, and 500 ms cross-section budgets pass in controlled desktop tests.
- Existing Python and Playwright suites pass, and `scripts/check_health.py` reports `ERROR 0 / WARN 0`.
