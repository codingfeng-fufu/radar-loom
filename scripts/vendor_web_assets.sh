#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBUI_VENDOR="${WEBUI_VENDOR:-$ROOT/.webui-vendor}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() {
  local url="$1"
  local target="$2"
  mkdir -p "$(dirname "$target")"
  curl --fail --location --retry 3 --silent --show-error "$url" --output "$target"
  test -s "$target"
}

fetch "https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js" "$TMP/marked/marked.min.js"
fetch "https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js" "$TMP/dompurify/purify.min.js"
fetch "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js" "$TMP/highlight/highlight.min.js"
fetch "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/github.min.css" "$TMP/highlight/github.min.css"
fetch "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js" "$TMP/mermaid/mermaid.min.js"
fetch "https://cdn.jsdelivr.net/npm/cytoscape@3.31.2/dist/cytoscape.min.js" "$TMP/cytoscape/cytoscape.min.js"
fetch "https://cdn.jsdelivr.net/npm/layout-base@2.0.1/layout-base.js" "$TMP/cytoscape/layout-base.js"
fetch "https://cdn.jsdelivr.net/npm/cose-base@2.2.0/cose-base.js" "$TMP/cytoscape/cose-base.js"
fetch "https://cdn.jsdelivr.net/npm/cytoscape-fcose@2.2.0/cytoscape-fcose.js" "$TMP/cytoscape/cytoscape-fcose.js"

fetch "https://registry.npmjs.org/katex/-/katex-0.16.22.tgz" "$TMP/katex.tgz"
mkdir -p "$TMP/katex-package"
tar -xzf "$TMP/katex.tgz" -C "$TMP/katex-package" --strip-components=2 package/dist
mkdir -p "$TMP/katex/fonts"
install -m 0644 "$TMP/katex-package/katex.min.js" "$TMP/katex/katex.min.js"
install -m 0644 "$TMP/katex-package/katex.min.css" "$TMP/katex/katex.min.css"
install -m 0644 "$TMP/katex-package/contrib/auto-render.min.js" "$TMP/katex/auto-render.min.js"
install -m 0644 "$TMP/katex-package/fonts/"*.woff2 "$TMP/katex/fonts/"

rm -rf "$ROOT/vendor"
mkdir -p "$ROOT/vendor"
cp -a "$TMP/marked" "$TMP/dompurify" "$TMP/highlight" "$TMP/mermaid" "$TMP/katex" "$TMP/cytoscape" "$ROOT/vendor/"

mkdir -p "$WEBUI_VENDOR"
install -m 0644 "$TMP/marked/marked.min.js" "$WEBUI_VENDOR/marked.min.js"
install -m 0644 "$TMP/dompurify/purify.min.js" "$WEBUI_VENDOR/purify.min.js"

printf 'Vendored browser assets into %s and %s\n' "$ROOT/vendor" "$WEBUI_VENDOR"
