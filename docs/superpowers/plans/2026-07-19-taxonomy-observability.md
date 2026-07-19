# Dynamic Taxonomy Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make automatic taxonomy activity visible through persistent `2/3` candidates, truthful run outcomes, a compact Viewer entry, and a polished circular taxonomy graph with on-demand member expansion.

**Architecture:** Extend the validated taxonomy registry with candidate snapshots and explicit run state, calculate candidates in a focused local-only module, and publish both through the existing graph JSON pipeline. Keep the browser as a pure renderer: Viewer provides a compact deep link, while the existing taxonomy mode renders circular category/candidate nodes and expands representative pages locally from published memberships.

**Tech Stack:** Python 3 dataclasses, NumPy, existing sentence-transformer cache, NetworkX/scikit-learn taxonomy pipeline, unittest/pytest, vanilla HTML/CSS/JavaScript, Cytoscape.js with fCoSE, Playwright.

---

## File Map

- Create `scripts/taxonomy_candidates.py`: deterministic candidate discovery, stable IDs, temporary keyword names, and candidate-to-category proximity.
- Create `tests/test_taxonomy_candidates.py`: isolated candidate discovery and naming tests.
- Create `tests/taxonomy_observability.spec.cjs`: real-browser taxonomy interaction, geometry, refresh, and screenshot checks.
- Modify `scripts/taxonomy_models.py`: `Candidate` and `TaxonomyRun` records, schema-v2 compatibility, deterministic serialization, and validation.
- Modify `scripts/taxonomy_engine.py`: refresh candidate snapshots after sync/global operations and report explicit run outcomes.
- Modify `scripts/taxonomy_cli.py`: expose the richer status without changing command names.
- Modify `config/taxonomy.json` and `config/interview-taxonomy.json`: add candidate thresholds and representative-page limit.
- Modify `scripts/render_graph.py`: publish category origin, candidates, run state, and representative membership data.
- Modify `scripts/serve_kb.py`: return `adopted`, `rejected`, or `failed` for explicit rebuilds.
- Modify `viewer.html`: render one compact taxonomy status/deep-link row per active profile.
- Modify `graph-view.html`: honor `mode=taxonomy`, render circular source-aware nodes, local expansion, semantic edges, and truthful status UI.
- Modify relevant existing tests under `tests/`: lock registry, engine, service, JSON, Viewer, and graph contracts.
- Modify `README.md` and `Web操作台使用与维护说明书.md`: document candidates and observable rebuild outcomes without overwriting unrelated user edits.

### Task 1: Registry Schema for Candidates and Run State

**Files:**
- Modify: `scripts/taxonomy_models.py`
- Modify: `tests/test_taxonomy_models.py`

- [ ] **Step 1: Write failing schema-v2 round-trip and validation tests**

Add tests that construct these exact records and require old schema-v1 payloads to load with empty candidates and an idle run:

```python
def test_candidates_and_run_state_round_trip_deterministically(self):
    registry = self.make_registry()
    registry.candidates = [tm.Candidate(
        id="candidate_abc",
        name="缓存 替换",
        members=["pages/KV Cache.md", "pages/LRU.md"],
        cohesion_score=0.84,
        target_size=3,
        signals={"semantic": 0.84, "links": 0.5},
        related_category_ids=["a"],
        first_seen_at=NOW,
        last_confirmed_at=NOW,
    )]
    registry.last_run = tm.TaxonomyRun(
        operation="global", outcome="rejected", started_at=NOW,
        finished_at=NOW, reason="候选结构触发保护机制",
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "taxonomy.json"
        tm.write_registry(path, registry, {"pages/KV Cache.md", "pages/LRU.md"})
        loaded = tm.load_registry(path)
    self.assertEqual(loaded.candidates[0].members, ["pages/KV Cache.md", "pages/LRU.md"])
    self.assertEqual(loaded.last_run.outcome, "rejected")

def test_schema_v1_loads_with_empty_observability_state(self):
    payload = self.make_registry().to_dict()
    payload["schema_version"] = 1
    payload.pop("candidates", None)
    payload.pop("last_run", None)
    loaded = tm.Registry.from_dict(payload)
    self.assertEqual(loaded.candidates, [])
    self.assertEqual(loaded.last_run.outcome, "idle")

def test_validation_rejects_bad_candidate_members_scores_and_relations(self):
    registry = self.make_registry()
    registry.candidates = [tm.Candidate(
        "candidate_bad", "bad", ["pages/missing.md"], 1.4, 3, {}, ["missing"], NOW, NOW
    )]
    with self.assertRaisesRegex(tm.TaxonomyValidationError, "candidate"):
        tm.validate_registry(registry, set())
```

- [ ] **Step 2: Run the model tests and verify failure**

Run: `python3 -m unittest tests.test_taxonomy_models -v`

Expected: FAIL because `Candidate`, `TaxonomyRun`, `Registry.candidates`, and `Registry.last_run` do not exist.

- [ ] **Step 3: Implement schema-v2 records and backward-compatible loading**

Add focused dataclasses and constants:

```python
SCHEMA_VERSION = 2
RUN_OUTCOMES = {"idle", "adopted", "unchanged", "rejected", "failed"}

@dataclass
class Candidate:
    id: str
    name: str
    members: list[str]
    cohesion_score: float
    target_size: int
    signals: dict[str, float]
    related_category_ids: list[str]
    first_seen_at: str
    last_confirmed_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["members"] = sorted(set(self.members))
        payload["related_category_ids"] = sorted(set(self.related_category_ids))
        payload["signals"] = dict(sorted(self.signals.items()))
        return payload

@dataclass
class TaxonomyRun:
    operation: str = "none"
    outcome: str = "idle"
    started_at: str = ""
    finished_at: str = ""
    reason: str = ""
```

Extend `Registry.empty()`, `to_dict()`, and `from_dict()`. Accept input schema `1` or `2`, normalize loaded registries to schema `2`, and validate candidate IDs, unique members, existing page/category references, `target_size >= 3`, finite `[0,1]` scores, at least two members, and valid run outcomes. Keep serialization sorted by candidate ID.

- [ ] **Step 4: Run the model tests and verify pass**

Run: `python3 -m unittest tests.test_taxonomy_models -v`

Expected: all taxonomy model tests PASS.

- [ ] **Step 5: Commit the registry schema**

```bash
git add scripts/taxonomy_models.py tests/test_taxonomy_models.py
git commit -m "feat: model taxonomy candidates and run state"
```

### Task 2: Deterministic Local Candidate Discovery

**Files:**
- Create: `scripts/taxonomy_candidates.py`
- Create: `tests/test_taxonomy_candidates.py`
- Modify: `config/taxonomy.json`
- Modify: `config/interview-taxonomy.json`
- Modify: `tests/test_taxonomy_config.py`

- [ ] **Step 1: Write failing candidate discovery tests**

Use normalized vectors with two close pages and one unrelated page:

```python
def test_two_novel_close_pages_form_a_stable_candidate():
    config = {"candidate_min_pages": 2, "forming_min_pages": 3, "candidate_neighborhood_k": 12,
              "candidate_cohesion_threshold": 0.80, "candidate_related_threshold": 0.70}
    vectors = {
        "LRU": np.array([1.0, 0.0, 0.0], dtype=np.float32),
        "KV Cache": np.array([0.98, 0.02, 0.0], dtype=np.float32),
        "Unrelated": np.array([0.0, 1.0, 0.0], dtype=np.float32),
    }
    groups = tc.discover_groups(
        vectors=vectors,
        page_paths={name: f"pages/{name}.md" for name in vectors},
        memberships={"LRU": {"cat_seed_foundations"}, "KV Cache": {"cat_seed_llm"}},
        categories={
            "cat_seed_foundations": Category("cat_seed_foundations", "基础", "", "stable"),
            "cat_seed_llm": Category("cat_seed_llm", "LLM", "", "stable"),
            "cat_cache": Category("cat_cache", "缓存", "", "stable"),
        },
        category_centroids={"cat_cache": np.array([0.9, 0.1, 0.0])},
        config=config,
        today="2026-07-19",
    )
    candidates = tc.snapshot_candidates(groups, [], config, "2026-07-19")
    self.assertEqual(len(candidates), 1)
    self.assertEqual(candidates[0].members, ["pages/KV Cache.md", "pages/LRU.md"])
    self.assertEqual(candidates[0].target_size, 3)
    self.assertEqual(candidates[0].related_category_ids, ["cat_cache"])

def test_candidate_id_and_first_seen_survive_member_order():
    first = tc.candidate_id(["pages/B.md", "pages/A.md"])
    second = tc.candidate_id(["pages/A.md", "pages/B.md"])
    self.assertEqual(first, second)

def test_temporary_name_is_deterministic_and_does_not_use_command_namer():
    self.assertEqual(
        tc.temporary_name(["LRU 缓存替换", "KV Cache"]),
        tc.temporary_name(["KV Cache", "LRU 缓存替换"]),
    )
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m unittest tests.test_taxonomy_candidates tests.test_taxonomy_config -v`

Expected: FAIL because `taxonomy_candidates.py` and candidate config keys are absent.

- [ ] **Step 3: Implement candidate discovery**

Implement these public records and functions in `scripts/taxonomy_candidates.py`:

```python
@dataclass(frozen=True)
class NovelGroup:
    members: list[str]
    cohesion_score: float
    signals: dict[str, float]
    related_category_ids: list[str]

def candidate_id(member_paths: list[str]) -> str:
    canonical = "\n".join(sorted(set(member_paths))).encode("utf-8")
    return f"candidate_{hashlib.sha256(canonical).hexdigest()[:12]}"

def temporary_name(page_names: list[str]) -> str:
    tokens = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9+-]*|[\u3400-\u9fff]{2,}", " ".join(page_names))))
    value = " ".join(tokens[:3]) or "新主题"
    return value if len(value) <= 12 else f"{value[:11]}…"

def discover_groups(
    vectors: dict[str, np.ndarray], page_paths: dict[str, str],
    memberships: dict[str, set[str]], categories: dict[str, Category],
    category_centroids: dict[str, np.ndarray], config: dict, today: str,
) -> list[NovelGroup]:
    """Return sorted high-cohesion groups; implementation follows the k-NN rules below."""
    return _groups_from_knn(vectors, page_paths, memberships, categories, category_centroids, config)

def snapshot_candidates(
    groups: list[NovelGroup], previous: list[Candidate], config: dict, today: str
) -> list[Candidate]:
    prior = {item.id: item for item in previous}
    target = int(config["forming_min_pages"])
    snapshots = []
    for group in groups:
        if len(group.members) >= target:
            continue
        identifier = candidate_id(group.members)
        old = prior.get(identifier)
        snapshots.append(Candidate(
            id=identifier,
            name=temporary_name([Path(path).stem for path in group.members]),
            members=sorted(group.members),
            cohesion_score=group.cohesion_score,
            target_size=target,
            signals=group.signals,
            related_category_ids=group.related_category_ids,
            first_seen_at=old.first_seen_at if old else today,
            last_confirmed_at=today,
        ))
    return sorted(snapshots, key=lambda item: item.id)
```

Build a bounded cosine k-nearest-neighbor graph across all pages, including pages already assigned to broad seed categories. Connect pairs at or above `candidate_cohesion_threshold` and emit `NovelGroup` components of at least `candidate_min_pages`. Sharing a `cat_seed_*` membership must not suppress a group. Suppress only a group already fully explained by the same active non-seed automatic category. `snapshot_candidates()` persists groups smaller than `forming_min_pages`; the engine consumes groups at or above that threshold as new formal `forming` categories. Compute cohesion as the mean pairwise cosine, preserve `first_seen_at` by stable candidate ID, set `last_confirmed_at=today`, and attach categories whose centroid cosine meets `candidate_related_threshold`. Generate a temporary name from sorted title tokens, capped at 12 display characters plus an ellipsis.

Add these exact values to both profile configs:

```json
"candidate_min_pages": 2,
"candidate_neighborhood_k": 12,
"candidate_cohesion_threshold": 0.78,
"candidate_related_threshold": 0.70,
"representative_page_limit": 5
```

- [ ] **Step 4: Run candidate/config tests and verify pass**

Run: `python3 -m unittest tests.test_taxonomy_candidates tests.test_taxonomy_config -v`

Expected: all tests PASS with no network access.

- [ ] **Step 5: Commit candidate discovery**

```bash
git add scripts/taxonomy_candidates.py tests/test_taxonomy_candidates.py config/taxonomy.json config/interview-taxonomy.json tests/test_taxonomy_config.py
git commit -m "feat: discover local taxonomy candidates"
```

### Task 3: Candidate Lifecycle and Truthful Engine Outcomes

**Files:**
- Modify: `scripts/taxonomy_engine.py`
- Modify: `scripts/taxonomy_cli.py`
- Modify: `tests/test_taxonomy_engine.py`
- Modify: `tests/test_taxonomy_end_to_end.py`
- Modify: `tests/test_interview_taxonomy.py`

- [ ] **Step 1: Write failing lifecycle tests**

Extend the end-to-end fixture so two novel pages first create a candidate, then a third page promotes it:

```python
for name in ("Novel A", "Novel B"):
    (vault / "pages" / f"{name}.md").write_text(page(name, topic), encoding="utf-8")
registry = engine.sync(today="2026-07-16", allow_global=False)
self.assertEqual(len(registry.candidates), 1)
self.assertEqual(len(registry.candidates[0].members), 2)

(vault / "pages" / "Novel C.md").write_text(page("Novel C", topic), encoding="utf-8")
registry = engine.sync(today="2026-07-17", allow_global=False)
self.assertEqual(registry.candidates, [])
self.assertEqual(
    sum(category.status == "forming" for category in registry.categories.values()), 1
)
```

Add engine tests that require `status()` keys `seed_categories`, `automatic_categories`, `candidates`, and `last_run`, and verify a rejected global rebuild records `outcome == "rejected"` while an unchanged rebuild records `outcome == "unchanged"`.

Add a compatibility test that writes a schema-v1 registry with unchanged page fingerprints, runs `sync --no-global`, and asserts it is upgraded to schema 2 with a candidate snapshot. Run the same sync again and assert the schema-v2 bytes remain identical.

- [ ] **Step 2: Run lifecycle tests and verify failure**

Run: `python3 -m unittest tests.test_taxonomy_engine tests.test_taxonomy_end_to_end tests.test_interview_taxonomy -v`

Expected: FAIL because the engine never refreshes candidates or exposes explicit outcomes.

- [ ] **Step 3: Implement a single candidate refresh boundary**

Add helpers to `TaxonomyEngine`:

```python
def _run(self, operation, outcome, started_at, finished_at, reason="") -> TaxonomyRun:
    return TaxonomyRun(operation, outcome, started_at, finished_at, reason)

def _refresh_candidates(self, result, vectors, pages, timestamp):
    page_paths = {name: self._stable_path(page) for name, page in pages.items()}
    membership_map = {
        name: {item.category_id for item in result.memberships if item.page == page_paths[name]}
        for name in pages
    }
    centroids = self._category_centroids(result, vectors, pages)
    groups = taxonomy_candidates.discover_groups(
        vectors, page_paths, membership_map, result.categories, centroids, self.config, timestamp
    )
    self._promote_novel_groups(result, groups, vectors, pages, timestamp)
    result.candidates = taxonomy_candidates.snapshot_candidates(
        groups, result.candidates, self.config, timestamp
    )
```

Call `_refresh_candidates()` after changed-page assignments and after successful/rejected global reconciliation, before `write_registry()`. `_promote_novel_groups()` must create a formal `forming` category plus memberships for each novel group at or above `forming_min_pages`, even when those pages already belong to broad seed categories; smaller groups become candidate snapshots. Candidate refresh exceptions must not replace `result.candidates`; instead retain the previous snapshot and set `last_run=TaxonomyRun(operation, "failed", started_at, timestamp, f"候选数据未更新: {type(error).__name__}")`. Do not place secrets or page semantic text in the reason.

Mark migrated seed IDs using the existing `cat_seed_` prefix in status calculation. Compute automatic categories as active categories without that prefix. Return:

```python
{
    "seed_categories": 8,
    "automatic_categories": 0,
    "candidates": 1,
    "candidate_updated_at": "2026-07-19",
    "last_run": registry.last_run.to_dict(),
}
```

Preserve the current no-change byte-identical behavior after migration: a no-change schema-v2 `sync` returns without rewriting or recalculating candidates. A schema-v1 registry is an explicit observability migration case, so its first `sync` calculates candidates and atomically writes schema 2 even when page fingerprints are unchanged.

- [ ] **Step 4: Run lifecycle tests and verify pass**

Run: `python3 -m unittest tests.test_taxonomy_engine tests.test_taxonomy_end_to_end tests.test_interview_taxonomy -v`

Expected: all tests PASS; the two profiles remain isolated.

- [ ] **Step 5: Commit engine lifecycle**

```bash
git add scripts/taxonomy_engine.py scripts/taxonomy_cli.py tests/test_taxonomy_engine.py tests/test_taxonomy_end_to_end.py tests/test_interview_taxonomy.py
git commit -m "feat: persist taxonomy candidate lifecycle"
```

### Task 4: Publish Observability and Rebuild Outcomes

**Files:**
- Modify: `scripts/render_graph.py`
- Modify: `scripts/serve_kb.py`
- Modify: `tests/test_v3_scripts.py`
- Modify: `tests/test_interview_graph.py`
- Modify: `tests/test_serve_kb.py`

- [ ] **Step 1: Write failing graph and service contract tests**

Require the taxonomy payload to include source, candidates, run state, and representative memberships:

```python
taxonomy = payload["taxonomy"]
self.assertEqual(taxonomy["schemaVersion"], 2)
self.assertEqual(taxonomy["categories"][0]["source"], "seed")
self.assertIn("candidates", taxonomy)
self.assertIn("lastRun", taxonomy)
for candidate in taxonomy["candidates"]:
    self.assertLess(len(candidate["members"]), candidate["targetSize"])
    self.assertTrue(all(member in {node["id"] for node in payload["nodes"]}
                        for member in candidate["members"]))
```

Update the fake taxonomy CLI in `tests/test_serve_kb.py` so `global` writes status JSON with `last_run.outcome`. Assert POST `/api/taxonomy/rebuild` returns top-level `outcome` and `reason` for `adopted`, `rejected`, and a sanitized HTTP-500 `failed` response.

- [ ] **Step 2: Run graph/service tests and verify failure**

Run: `python3 -m unittest tests.test_v3_scripts tests.test_serve_kb -v && python3 -m pytest tests/test_interview_graph.py -q`

Expected: FAIL because the published payload lacks observability fields and the endpoint treats every zero exit as success.

- [ ] **Step 3: Extend the graph payload and endpoint response**

In `_taxonomy_payload()` publish:

```python
{
    "schemaVersion": registry.schema_version,
    "categories": [{**category_payload, "source":
                    "seed" if category.id.startswith("cat_seed_") else "automatic"}],
    "memberships": existing_memberships,
    "candidates": [candidate.to_dict() converted from paths to page IDs],
    "lastRun": registry.last_run.to_dict(),
    "stats": {**existing_stats,
              "seedCategories": sum(item.id.startswith("cat_seed_") and item.status != "merged" for item in registry.categories.values()),
              "automaticCategories": sum(not item.id.startswith("cat_seed_") and item.status != "merged" for item in registry.categories.values()),
              "candidates": len(registry.candidates)},
}
```

Include at most `representative_page_limit` highest-score memberships for each active category as `representatives`, sorted by score descending then page ID. In `taxonomy_rebuild()`, parse the post-run status and return `outcome`, `reason`, `revision`, and `status`; preserve the old registry/static files on command failure.

- [ ] **Step 4: Run graph/service tests and verify pass**

Run: `python3 -m unittest tests.test_v3_scripts tests.test_serve_kb -v && python3 -m pytest tests/test_interview_graph.py -q`

Expected: all tests PASS for both profiles.

- [ ] **Step 5: Commit published observability**

```bash
git add scripts/render_graph.py scripts/serve_kb.py tests/test_v3_scripts.py tests/test_interview_graph.py tests/test_serve_kb.py
git commit -m "feat: publish taxonomy observability state"
```

### Task 5: Compact Viewer Entry

**Files:**
- Modify: `viewer.html`
- Modify: `tests/test_viewer_contract.py`

- [ ] **Step 1: Write failing Viewer contract tests**

Require safe DOM rendering and the explicit taxonomy deep link:

```python
def test_viewer_exposes_compact_taxonomy_status_link(self):
    for token in ("taxonomySummary", "renderTaxonomySummary", "seedCategories",
                  "automaticCategories", "candidates", "mode=taxonomy"):
        self.assertIn(token, self.html)
    self.assertNotIn("taxonomySummary.innerHTML", self.html)
```

- [ ] **Step 2: Run Viewer tests and verify failure**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: FAIL because the compact summary does not exist.

- [ ] **Step 3: Implement the one-line summary**

Add an unframed `#taxonomySummary` row above navigation content. Fetch the profile-specific graph JSON already served statically, read `taxonomy.stats` and `taxonomy.lastRun`, and construct all labels with `textContent`/`createElement`. Link to:

```javascript
`graph-view.html?profile=${activeSection}&mode=taxonomy`
```

Render neutral, candidate, rejected, and failed states with a dot plus one concise phrase. On fetch/schema failure render `动态分类状态不可用` without blocking page navigation. Refresh the summary when the section changes and after the existing workbench refresh message.

- [ ] **Step 4: Run Viewer tests and verify pass**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: all Viewer contract tests PASS.

- [ ] **Step 5: Commit Viewer entry**

```bash
git add viewer.html tests/test_viewer_contract.py
git commit -m "feat: expose taxonomy status in viewer"
```

### Task 6: Circular Taxonomy Graph and On-Demand Expansion

**Files:**
- Modify: `graph-view.html`
- Modify: `tests/test_graph_view_contract.py`

- [ ] **Step 1: Write failing graph interaction contracts**

Require distinct node types, URL-mode precedence, expansion functions, and circular styles:

```python
def test_taxonomy_mode_supports_candidates_and_local_expansion(self):
    for token in ("candidateElements", "expandTaxonomyNode", "collapseExpandedMembers",
                  "candidate-member", "candidate-related", "representative"):
        self.assertIn(token, self.html)
    self.assertIn("searchParams.get('mode')", self.html)
    self.assertIn("shape': 'ellipse'", self.html)
    self.assertIn("width': 'data(size)'", self.html)
    self.assertIn("height': 'data(size)'", self.html)
```

Also require selectors for `source = "seed"`, `source = "automatic"`, candidate dashed borders, parent arrows, related curves, and member edges.

- [ ] **Step 2: Run graph contracts and verify failure**

Run: `python3 -m unittest tests.test_graph_view_contract -v`

Expected: FAIL because candidates and local expansion are absent and category sizing is not explicitly circular.

- [ ] **Step 3: Implement URL mode and truthful status strip**

Read `mode` from `location.search`; if it is one of the three supported modes, use it before session state. Add a single compact status element near `toolbarStats`. Map `lastRun.outcome` to neutral/adopted, amber/rejected, and red/failed presentation. Clicking the status renders the exact sanitized reason and timestamps in the existing detail panel.

- [ ] **Step 4: Implement category and candidate elements**

Make category data include `nodeType: 'category'`, `source`, member count, and fixed `size`. Add candidate nodes with `nodeType: 'candidate'`, `status: 'candidate'`, progress label, and proximity edges. Keep category parent/related edges and add unique IDs for every generated element.

Use Cytoscape selectors equivalent to:

```javascript
{ selector: 'node[nodeType = "category"], node[nodeType = "candidate"]', style: {
  'shape': 'ellipse', 'width': 'data(size)', 'height': 'data(size)',
  'text-wrap': 'wrap', 'text-max-width': 92, 'text-valign': 'center',
  'text-halign': 'center'
}},
{ selector: 'node[source = "seed"]', style: { 'border-color': '#d2a15f', 'border-style': 'solid' }},
{ selector: 'node[source = "automatic"]', style: { 'border-color': '#78a9d4', 'border-style': 'solid' }},
{ selector: 'node[nodeType = "candidate"]', style: { 'border-color': '#70bd8d', 'border-style': 'dashed' }},
{ selector: 'edge[edgeType = "parent"]', style: { 'target-arrow-shape': 'triangle' }},
{ selector: 'edge[edgeType = "related"]', style: { 'curve-style': 'unbundled-bezier', 'target-arrow-shape': 'none' }}
```

- [ ] **Step 5: Implement bounded local expansion**

`expandTaxonomyNode(node)` first calls `collapseExpandedMembers()`, then adds only published representative pages for a category or all members for a candidate. Use `nodeType: 'representative'`, a smaller fixed circular size, and `edgeType: 'membership'` or `'candidate-member'`. Position new nodes radially around the category before running an incremental `fcose` layout with existing category positions fixed. A second tap or background tap removes only temporary nodes/edges and clears the detail selection.

- [ ] **Step 6: Run graph contracts and verify pass**

Run: `python3 -m unittest tests.test_graph_view_contract -v`

Expected: all graph contract tests PASS.

- [ ] **Step 7: Commit graph behavior**

```bash
git add graph-view.html tests/test_graph_view_contract.py
git commit -m "feat: visualize evolving taxonomy candidates"
```

### Task 7: End-to-End, Visual Quality, Generated Data, and Documentation

**Files:**
- Create: `tests/taxonomy_observability.spec.cjs`
- Modify: `tests/playwright.config.cjs`
- Modify: `README.md`
- Modify: `Web操作台使用与维护说明书.md`
- Generate: `taxonomy.json`
- Generate: `interview-taxonomy.json`
- Generate: `graph-data.json`
- Generate: `interview-graph-data.json`

- [ ] **Step 1: Add Playwright behavior and geometry tests**

Create tests that open `viewer.html`, assert the compact status row, follow it to `mode=taxonomy`, and exercise candidate/category expansion. Add a geometry helper:

```javascript
async function graphGeometry(page) {
  return page.locator('#graph').evaluate(() => {
    const nodes = cy.nodes(':visible').map(node => ({ id: node.id(), box: node.renderedBoundingBox() }));
    const overlaps = [];
    for (let i = 0; i < nodes.length; i += 1) for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i].box, b = nodes[j].box;
      if (a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1) overlaps.push([nodes[i].id, nodes[j].id]);
    }
    return { nodes, overlaps, visibleEdges: cy.edges(':visible').length };
  });
}
```

Assert category/candidate rendered width and height differ by at most one pixel, no node overlaps after layout completion, all expanded nodes remain inside the visible graph extent, and the canvas pixel variance is nonzero. Capture desktop `1440x900` and mobile `390x844` screenshots to `E2E_ARTIFACT_DIR`.

- [ ] **Step 2: Run Playwright and verify the new tests fail before final integration**

Run: `KB_VIEWER_URL=http://127.0.0.1:18081 npx playwright test -c tests/playwright.config.cjs tests/taxonomy_observability.spec.cjs`

Expected: FAIL until generated schema-v2 data exists and any remaining layout defects are corrected.

- [ ] **Step 3: Regenerate registries and graph data with real local embeddings**

Run:

```bash
python3 scripts/taxonomy_cli.py sync --no-global
python3 scripts/taxonomy_cli.py --profile interview sync --no-global
python3 scripts/render_graph.py
python3 scripts/taxonomy_cli.py validate
python3 scripts/taxonomy_cli.py --profile interview validate
```

Expected: both registries validate; graph generation reports knowledge and interview outputs; status reports candidate counts without pending pages. If model loading fails, stop and fix the environment rather than publishing deterministic test embeddings into production registries.

- [ ] **Step 4: Run Playwright and inspect screenshots**

Run: `E2E_ARTIFACT_DIR=/tmp/taxonomy-observability KB_VIEWER_URL=http://127.0.0.1:18081 npx playwright test -c tests/playwright.config.cjs tests/taxonomy_observability.spec.cjs`

Expected: PASS. Inspect both screenshots and verify circular nodes, legible labels, meaningful connected edges, no overlap, no blank canvas, and usable mobile details. A passing DOM assertion alone is insufficient.

- [ ] **Step 5: Document observable classification behavior**

Update README and the maintenance manual to state: two pages create a local-only candidate; three pages enter `forming`; candidates are not formal categories or Claude naming inputs; Viewer links to taxonomy mode; rebuild outcomes distinguish adopted/rejected/failed; stale candidate snapshots remain visible with an error state. Preserve all unrelated existing edits in the manual.

- [ ] **Step 6: Run the complete verification suite**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m pytest tests -q
python3 scripts/taxonomy_cli.py validate
python3 scripts/taxonomy_cli.py --profile interview validate
python3 scripts/render_graph.py
python3 scripts/check_health.py
npx playwright test -c tests/playwright.config.cjs
git diff --check
```

Expected: all Python and Playwright tests PASS; both registries validate; health reports `ERROR 0` and `WARN 0`; no whitespace errors; regenerated files are stable on a second render.

- [ ] **Step 7: Commit acceptance, generated state, and documentation**

```bash
git add tests/taxonomy_observability.spec.cjs tests/playwright.config.cjs README.md \
  Web操作台使用与维护说明书.md taxonomy.json interview-taxonomy.json \
  graph-data.json interview-graph-data.json
git commit -m "test: accept observable taxonomy workflow"
```

Before committing, inspect `git diff -- Web操作台使用与维护说明书.md` and retain every pre-existing user edit; stage only the intended documentation additions if the file contains unrelated changes.
