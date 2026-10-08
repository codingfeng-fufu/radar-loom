# Knowledge Base API

The local service runs on `http://127.0.0.1:18081`.

## Read APIs

| Endpoint | Purpose |
| --- | --- |
| `GET /api/catalog` | Combined knowledge/interview nodes and edges |
| `GET /api/search?q=...&section=knowledge&page=1&pageSize=20&sort=relevance` | Full-text search with snippets and pagination |
| `GET /api/page-history?file=pages/...` | Git history for a page |
| `GET /api/page-history?file=pages/...&old=<commit>&new=<commit>` | Unified diff between versions |
| `GET /api/duplicates?threshold=0.86` | Duplicate-page candidates |
| `GET /api/pages/trash` | Recycle-bin manifest |
| `GET /api/health/summary` | Page, graph, revision and working-tree status |
| `GET /api/quality/issues` | Missing fields, broken links and orphaned pages |
| `GET /api/git/changes?base=<commit>` | File-level Git change summary |
| `GET /api/merge-preview?left=pages/...&right=pages/...` | Manual merge preview |
| `GET /api/export` | Download a ZIP backup |

The optional stdio MCP adapter is `python3 scripts/mcp_server.py`. It exposes `kb_search`, `kb_catalog`, `kb_health`, and `kb_page_history` through `initialize`, `tools/list`, and `tools/call` JSON-RPC messages.

## Mutating APIs

Mutating requests require a loopback client and an allowed local `Origin` header.

- `POST /api/pages/trash` with `{"file":"pages/example.md"}`
- `POST /api/pages/restore` with `{"file":"pages/example.md"}`
- `POST /api/refresh`
- `POST /api/taxonomy/rebuild`
- `POST /api/import` with `Content-Type: application/zip` (validated local backup restore)

## External links

Viewer links use `viewer.html?section=knowledge&f=pages%2F...`. The workbench accepts the same URL and keeps Claude context associated with the selected file.
