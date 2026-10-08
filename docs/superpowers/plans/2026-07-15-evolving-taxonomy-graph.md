# Evolving Taxonomy Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable, automatically evolving multi-parent taxonomy that classifies pages incrementally, restructures categories globally, and exposes knowledge, taxonomy, and combined graph views.

**Architecture:** Keep algorithmic classification in a committed root-level `taxonomy.json` registry and cache embeddings under ignored `.cache/taxonomy/`. A Python engine combines multilingual embeddings, wikilink structure, project tags, HDBSCAN, and Louvain; the local knowledge server runs incremental sync and lazy scheduled global restructuring. `render_graph.py` publishes taxonomy data into `graph-data.json`, and the existing Cytoscape UI renders three switchable views.

**Tech Stack:** Python 3.11, NumPy, SciPy, scikit-learn `HDBSCAN`, sentence-transformers with `intfloat/multilingual-e5-small`, NetworkX Louvain, existing Python `unittest`, vanilla JavaScript, Cytoscape.js/fCoSE, Playwright CLI, Claude CLI for bounded category naming.

---

## File Map

- `config/taxonomy.json`: thresholds, weights, model name, schedule, random seed, and naming budget.
- `requirements-taxonomy.txt`: reproducible taxonomy runtime dependencies.
- `taxonomy.json`: committed schema-versioned categories, memberships, events, fingerprints, and run metadata.
- `scripts/taxonomy_models.py`: registry dataclasses, validation, stable IDs, deterministic JSON, and atomic writes.
- `scripts/taxonomy_embeddings.py`: semantic text construction, model adapter, normalized vectors, and fingerprint cache.
- `scripts/taxonomy_signals.py`: wikilink/project/tag features, category centroids, incremental scores, and forming-category detection.
- `scripts/taxonomy_cluster.py`: HDBSCAN, Louvain, cluster fusion, stable matching, merge/split, and taxonomy relations.
- `scripts/taxonomy_naming.py`: deterministic keyword fallback and bounded Claude CLI naming adapter.
- `scripts/taxonomy_engine.py`: migration, incremental sync, global restructuring, deletion handling, and run state.
- `scripts/taxonomy_cli.py`: `migrate`, `sync`, `global`, `status`, and `validate` commands.
- `scripts/serve_kb.py`: runs throttled taxonomy due checks independently of page staleness, invokes sync before generated artifacts, and exposes taxonomy APIs.
- `scripts/render_graph.py`: adds taxonomy nodes, membership edges, and category relations to graph data.
- `graph-view.html`: segmented graph modes, taxonomy navigation, taxonomy detail rendering, and manual global rebuild.
- `.claude/skills/create-knowledge-page/SKILL.md`: invokes taxonomy sync after the page is complete.
- `<local-webui-root>/claude-taxonomy-namer`: secret-isolating Claude CLI wrapper.
- `<local-webui-root>/kbserve-control`: points the taxonomy engine at the naming wrapper without exporting credentials into the server process.

## Milestone 1: Registry And Classification Engine

### Task 1: Dependency and configuration contract

**Files:**
- Create: `requirements-taxonomy.txt`
- Create: `config/taxonomy.json`
- Modify: `.gitignore`
- Create: `tests/test_taxonomy_config.py`

- [ ] **Step 1: Write the failing configuration test**

```python
class TaxonomyConfigTests(unittest.TestCase):
    def test_runtime_dependencies_and_config_are_explicit(self):
        requirements = (ROOT / "requirements-taxonomy.txt").read_text()
        for package in ("numpy", "scipy", "scikit-learn", "sentence-transformers", "networkx"):
            self.assertIn(package, requirements)
        config = json.loads((ROOT / "config/taxonomy.json").read_text())
        self.assertEqual(config["schema_version"], 1)
        self.assertEqual(config["embedding_model"], "intfloat/multilingual-e5-small")
        self.assertEqual(config["forming_min_pages"], 3)
        self.assertEqual(config["global_after_changes"], 5)
        self.assertEqual(config["due_check_seconds"], 60)
        self.assertEqual(sum(config["signal_weights"].values()), 1.0)
        self.assertIn(".cache/taxonomy/", (ROOT / ".gitignore").read_text())
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_config.py' -v`

Expected: FAIL because the requirements and config files do not exist.

- [ ] **Step 3: Add the exact dependency and configuration files**

`requirements-taxonomy.txt`:

```text
numpy==2.4.6
scipy>=1.14,<2
scikit-learn==1.8.0
sentence-transformers==2.7.0
networkx==3.6.1
```

`config/taxonomy.json`:

```json
{
  "schema_version": 1,
  "embedding_model": "intfloat/multilingual-e5-small",
  "random_seed": 20260715,
  "forming_min_pages": 3,
  "stable_min_pages": 5,
  "stable_min_runs": 2,
  "assignment_threshold": 0.62,
  "forming_cohesion_threshold": 0.78,
  "cluster_match_threshold": 0.55,
  "cluster_fusion_jaccard": 0.35,
  "related_threshold": 0.75,
  "parent_containment_threshold": 0.8,
  "global_after_changes": 5,
  "global_after_days": 7,
  "due_check_seconds": 60,
  "max_naming_calls": 8,
  "naming_change_jaccard": 0.8,
  "signal_weights": {"semantic": 0.6, "links": 0.25, "tags": 0.1, "projects": 0.05}
}
```

Append `.cache/taxonomy/` to `.gitignore`.

- [ ] **Step 4: Verify dependencies without installing or importing the model**

Run:

```bash
python3 -c "from sklearn.cluster import HDBSCAN; import networkx, numpy, scipy, sentence_transformers; print('taxonomy dependencies: OK')"
python3 -m unittest discover -s tests -p 'test_taxonomy_config.py' -v
```

Expected: dependency message and PASS. If a dependency is missing, run `python3 -m pip install --user -r requirements-taxonomy.txt`, then rerun both commands.

- [ ] **Step 5: Commit**

```bash
git add requirements-taxonomy.txt config/taxonomy.json .gitignore tests/test_taxonomy_config.py
git commit -m "build: define taxonomy runtime and configuration"
```

### Task 2: Registry model, validation, and atomic persistence

**Files:**
- Create: `scripts/taxonomy_models.py`
- Create: `tests/test_taxonomy_models.py`

- [ ] **Step 1: Write failing registry tests**

```python
class TaxonomyModelTests(unittest.TestCase):
    def make_registry(self):
        registry = tm.Registry.empty(parameters_hash="abc", now="2026-07-15T00:00:00+08:00")
        registry.categories = {
            "a": tm.Category(id="a", name="A", definition="A 类", status="stable"),
            "b": tm.Category(id="b", name="B", definition="B 类", status="stable"),
        }
        return registry

    def test_registry_round_trip_is_deterministic_and_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "taxonomy.json"
            registry = self.make_registry()
            registry.memberships.append(tm.Membership(
                page="pages/GNN.md", category_id="a", score=0.9,
                signals={"semantic": 0.9}, reason="语义",
            ))
            tm.write_registry(path, registry, existing_pages={"pages/GNN.md"})
            first = path.read_bytes()
            tm.write_registry(path, tm.load_registry(path), existing_pages={"pages/GNN.md"})
            self.assertEqual(path.read_bytes(), first)

    def test_validation_rejects_parent_cycles_and_dangling_memberships(self):
        registry = self.make_registry()
        registry.categories["a"].parents = ["b"]
        registry.categories["b"].parents = ["a"]
        registry.memberships.append(tm.Membership(
            page="pages/X.md", category_id="missing", score=.8,
            signals={}, reason="x",
        ))
        with self.assertRaises(tm.TaxonomyValidationError):
            tm.validate_registry(registry, existing_pages={"pages/X.md"})
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_models.py' -v`

Expected: FAIL with `ModuleNotFoundError: taxonomy_models`.

- [ ] **Step 3: Implement the registry API**

Create frozen-value dataclasses with `to_dict()`/`from_dict()` methods and these public signatures:

```python
SCHEMA_VERSION = 1

@dataclass
class Category:
    id: str
    name: str
    definition: str
    status: str
    naming_status: str = "ready"
    parents: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    redirect_to: str | None = None
    created_at: str = ""
    updated_at: str = ""
    last_stable_at: str | None = None
    stable_runs: int = 0
    algorithm_version: str = "taxonomy-v1"

@dataclass
class Membership:
    page: str
    category_id: str
    score: float
    signals: dict[str, float]
    reason: str
    first_assigned_at: str = ""
    last_confirmed_at: str = ""

@dataclass
class TaxonomyEvent:
    type: str
    category_ids: list[str]
    reason: str
    created_at: str

@dataclass
class Registry:
    schema_version: int
    generated_at: str
    algorithm_version: str
    parameters_hash: str
    categories: dict[str, Category]
    memberships: list[Membership]
    events: list[TaxonomyEvent]
    page_fingerprints: dict[str, str]
    pending_pages: list[str]
    changes_since_global: int
    last_global_at: str | None
```

Implement `Registry.empty(parameters_hash, now)`, `load_registry(path)`, `write_registry(path, registry, existing_pages)`, `validate_registry(registry, existing_pages)`, `new_category_id(member_paths, occupied_ids)`, and `parameters_hash(config)`. JSON output must use `ensure_ascii=False`, `indent=2`, `sort_keys=True`; lists must be sorted by stable keys before an atomic temp-file rename. Validate the temporary file after serializing it and before `os.replace`; reject parent cycles, dangling category/page references, asymmetric `related` edges, redirect cycles, invalid lifecycle states, duplicate memberships, non-finite scores, and scores outside `[0, 1]`.

- [ ] **Step 4: Run model tests and the existing suite**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_taxonomy_models.py' -v
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/taxonomy_models.py tests/test_taxonomy_models.py
git commit -m "feat: add auditable taxonomy registry"
```

### Task 3: Semantic text, local embeddings, and cache

**Files:**
- Create: `scripts/taxonomy_embeddings.py`
- Create: `tests/test_taxonomy_embeddings.py`

- [ ] **Step 1: Write failing cache tests with a fake encoder**

```python
class FakeEncoder:
    model_name = "fake-v1"
    calls = 0
    def encode(self, texts):
        self.calls += len(texts)
        return np.asarray([[len(text), text.count("graph") + 1] for text in texts], dtype=np.float32)

def test_unchanged_page_reuses_normalized_cached_vector():
    page = page_info("Graph RAG", "摘要", "## Mechanism\ngraph retrieval")
    encoder = FakeEncoder()
    cache = te.EmbeddingCache(cache_dir, encoder)
    first = cache.vector_for(page)
    second = cache.vector_for(page)
    self.assertEqual(encoder.calls, 1)
    np.testing.assert_allclose(first, second)
    self.assertAlmostEqual(float(np.linalg.norm(first)), 1.0, places=6)

def test_title_summary_headings_and_body_affect_fingerprint():
    first = te.page_semantic_text(page_info("A", "S", "## H\nB"))
    second = te.page_semantic_text(page_info("A", "S2", "## H\nB"))
    self.assertNotEqual(te.content_fingerprint(first), te.content_fingerprint(second))
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_embeddings.py' -v`

Expected: FAIL because `taxonomy_embeddings` does not exist.

- [ ] **Step 3: Implement the encoder boundary and cache**

Public API:

```python
class SentenceTransformerEncoder:
    def __init__(self, model_name: str): ...
    def encode(self, texts: list[str]) -> np.ndarray: ...

def page_semantic_text(page: rc.PageInfo) -> str: ...
def content_fingerprint(text: str, model_name: str) -> str: ...

class EmbeddingCache:
    def __init__(self, root: Path, encoder): ...
    def vector_for(self, page: rc.PageInfo) -> np.ndarray: ...
    def vectors_for(self, pages: dict[str, rc.PageInfo]) -> dict[str, np.ndarray]: ...
```

Construct semantic text in this order: title twice, frontmatter summary, Markdown headings, body with fenced code removed. Limit each body chunk to the encoder's supported token window; encode chunks and normalize their mean. Cache each vector as `.npy` plus one `manifest.json` entry containing fingerprint, model name, dimension, and update time. Write the manifest atomically.

- [ ] **Step 4: Verify cache behavior without downloading the real model**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_taxonomy_embeddings.py' -v
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS and no Hugging Face network request occurs.

- [ ] **Step 5: Commit**

```bash
git add scripts/taxonomy_embeddings.py tests/test_taxonomy_embeddings.py
git commit -m "feat: cache multilingual page embeddings"
```

### Task 4: Structural signals and incremental multi-label classification

**Files:**
- Create: `scripts/taxonomy_signals.py`
- Create: `tests/test_taxonomy_signals.py`

- [ ] **Step 1: Write failing scoring and forming-category tests**

```python
def test_incremental_score_combines_all_configured_signals():
    score = ts.combine_signals(
        {"semantic": .8, "links": .6, "tags": 1.0, "projects": .0},
        {"semantic": .6, "links": .25, "tags": .1, "projects": .05},
    )
    self.assertAlmostEqual(score, .73)

def test_page_can_join_multiple_categories_above_threshold():
    assignments = ts.classify_page(page, vectors, registry, pages, config)
    self.assertEqual({item.category_id for item in assignments}, {"cat_kg", "cat_rag"})

def test_three_novel_cohesive_pages_form_category_but_one_outlier_does_not():
    formed = ts.detect_forming_group("New C", vectors, registry, config)
    self.assertEqual(formed.members, ["New A", "New B", "New C"])
    self.assertIsNone(ts.detect_forming_group("Outlier", outlier_vectors, registry, config))
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_signals.py' -v`

Expected: FAIL because `taxonomy_signals` does not exist.

- [ ] **Step 3: Implement deterministic signal calculations**

Public API:

```python
@dataclass
class Assignment:
    category_id: str
    score: float
    signals: dict[str, float]
    reason: str

@dataclass
class FormingGroup:
    members: list[str]
    cohesion: float

LEGACY_TAG_TO_SEED_ID = {
    "KG": "cat_seed_kg", "RAG": "cat_seed_rag",
    "LLM机制": "cat_seed_llm", "可信度": "cat_seed_trust",
    "多智能体": "cat_seed_agents", "基础": "cat_seed_foundations",
    "评测": "cat_seed_evaluation", "前沿": "cat_seed_frontier",
}

def category_centroids(registry, vectors) -> dict[str, np.ndarray]: ...
def combine_signals(signals, weights) -> float: ...
def classify_page(page_name, vectors, registry, pages, config) -> list[Assignment]: ...
def detect_forming_group(page_name, vectors, registry, config) -> FormingGroup | None: ...
```

Semantic signal is cosine similarity to the category centroid. Link signal is the fraction of resolved neighbors assigned to the category. Tag signal maps the eight legacy tags through `LEGACY_TAG_TO_SEED_ID`. Project signal is the fraction of category members sharing at least one project tag. Sort assignments by descending score then category ID; retain every assignment at or above `assignment_threshold`.

For forming detection, select pages whose best existing-category score is below the assignment threshold, find the new page's nearest neighbors, require at least three total members, and require mean pairwise cosine similarity at or above `forming_cohesion_threshold`.

- [ ] **Step 4: Verify incremental classification**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_taxonomy_signals.py' -v
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/taxonomy_signals.py tests/test_taxonomy_signals.py
git commit -m "feat: classify pages into multiple taxonomy categories"
```

### Task 5: Global semantic and graph restructuring

**Files:**
- Create: `scripts/taxonomy_cluster.py`
- Create: `tests/test_taxonomy_cluster.py`

- [ ] **Step 1: Write failing global-structure tests**

```python
def test_semantic_clusters_use_normalized_hdbscan_and_minimum_size():
    groups = tc.semantic_clusters(vectors, min_cluster_size=3, min_samples=2)
    self.assertEqual(groups, [{"A", "B", "C"}, {"X", "Y", "Z"}])

def test_louvain_clusters_are_deterministic_for_fixed_seed():
    first = tc.graph_clusters(edges, all_pages, seed=20260715)
    second = tc.graph_clusters(edges, all_pages, seed=20260715)
    self.assertEqual(first, second)

def test_matching_preserves_main_id_across_split_and_redirects_merge():
    result = tc.reconcile_clusters(old_registry, new_clusters, vectors, config, today="2026-07-15")
    self.assertIn("cat_old", result.categories)
    self.assertEqual(result.categories["cat_merged"].status, "merged")
    self.assertEqual(result.categories["cat_merged"].redirect_to, "cat_old")
    self.assertTrue(any(event.type == "split" for event in result.events))

def test_parent_relations_are_acyclic_and_related_relations_are_symmetric():
    relations = tc.infer_relations(clusters, centroids, config)
    self.assertFalse(has_parent_cycle(relations))
    self.assertEqual(relations["a"].related, ["b"])
    self.assertEqual(relations["b"].related, ["a"])
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_cluster.py' -v`

Expected: FAIL because `taxonomy_cluster` does not exist.

- [ ] **Step 3: Implement the exact clustering pipeline**

Public API:

```python
def semantic_clusters(vectors, min_cluster_size=3, min_samples=2) -> list[set[str]]: ...
def graph_clusters(edges, all_pages, seed) -> list[set[str]]: ...
def fuse_clusters(semantic, graph, vectors, edges, config) -> list[set[str]]: ...
def match_score(old_members, new_members, old_centroid, new_centroid, edge_score) -> float: ...
def reconcile_clusters(registry, clusters, vectors, config, today) -> Registry: ...
def infer_relations(category_members, centroids, config) -> dict[str, Category]: ...
```

Normalize vectors, then run `sklearn.cluster.HDBSCAN(min_cluster_size=3, min_samples=2, metric="euclidean")`; cosine and Euclidean ordering are equivalent for normalized vectors. Build a NetworkX directed wikilink graph, convert it to undirected weighted edges, and call `louvain_communities(..., seed=config["random_seed"])`.

For fusion, represent every semantic and graph group as a node in a candidate graph. Connect candidates when Jaccard overlap is at least `cluster_fusion_jaccard`, or when centroid cosine is at least `related_threshold` and cross-edge density is at least `0.15`. Each connected component's member union is one fused candidate; discard candidates smaller than `forming_min_pages` and remove exact duplicates.

Match old and new categories with score `0.50 * Jaccard + 0.35 * centroid_cosine + 0.15 * edge_similarity`; sort pairs by score descending and IDs ascending, then greedily assign pairs at or above `cluster_match_threshold`. Apply the lifecycle rules from the spec and emit explicit create, merge, split, promote, demote, rename, parent-change, and material-member-change events. On merge, preserve the selected primary ID, append absorbed names to its aliases, and retain each absorbed ID as `status="merged"` with `redirect_to` pointing to the primary ID. Validate the result before returning it.

Infer parent `a -> b` only when `len(a) < len(b)` and `len(a & b) / len(a) >= parent_containment_threshold`; add candidates from most specific to broadest and skip any edge that creates a cycle. Add symmetric `related` when categories are not parent-related and centroid similarity exceeds `related_threshold`.

- [ ] **Step 4: Verify deterministic restructuring**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_taxonomy_cluster.py' -v
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS on two consecutive runs with byte-identical fixture output.

- [ ] **Step 5: Commit**

```bash
git add scripts/taxonomy_cluster.py tests/test_taxonomy_cluster.py
git commit -m "feat: evolve taxonomy with semantic and graph communities"
```

### Task 6: Bounded naming with deterministic fallback

**Files:**
- Create: `scripts/taxonomy_naming.py`
- Create: `tests/test_taxonomy_naming.py`
- Create: `<local-webui-root>/claude-taxonomy-namer`

- [ ] **Step 1: Write failing naming tests**

```python
def test_keyword_fallback_is_deterministic_and_marks_pending():
    result = tn.KeywordNamer().name(request)
    self.assertEqual(result.naming_status, "pending")
    self.assertEqual(result.name, "图检索 结构化推理")

def test_command_namer_accepts_only_valid_json_and_respects_budget():
    namer = tn.CommandNamer([sys.executable, fake_namer], timeout=5)
    results = tn.name_changed_categories(requests, namer, max_calls=1)
    self.assertEqual(results[0].naming_status, "ready")
    self.assertEqual(results[1].naming_status, "pending")

def test_invalid_command_output_falls_back_without_losing_category():
    result = tn.CommandNamer([sys.executable, invalid_namer], timeout=5).name(request)
    self.assertEqual(result.naming_status, "pending")
    self.assertTrue(result.name)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_naming.py' -v`

Expected: FAIL because `taxonomy_naming` does not exist.

- [ ] **Step 3: Implement naming adapters**

Public API:

```python
@dataclass
class NamingRequest:
    category_id: str
    representative_pages: list[dict[str, str]]
    keywords: list[str]
    neighbor_definitions: list[str]

@dataclass
class NamingResult:
    name: str
    definition: str
    naming_status: str

class KeywordNamer: ...
class CommandNamer:
    def __init__(self, command: list[str], timeout: int = 60): ...
    def name(self, request: NamingRequest) -> NamingResult: ...

def name_changed_categories(requests, namer, max_calls) -> list[NamingResult]: ...
```

The command receives one JSON request on stdin and must return exactly `{"name":"...","definition":"..."}`. Reject empty fields, HTML, names longer than 30 Chinese characters/60 ASCII characters, and definitions longer than 240 characters. On timeout, nonzero exit, malformed JSON, or budget exhaustion, use `KeywordNamer` and set `naming_status="pending"`.

- [ ] **Step 4: Create and statically validate the secret-isolating wrapper**

Create mode-700 `<local-webui-root>/claude-taxonomy-namer` that sources `<local-webui-root>/runtime.env`, exports the same non-secret model/config variables as `webui-control`, reads the JSON request from stdin, constructs a strict JSON-only prompt, and invokes:

```bash
exec <local-user-home>/.nvm/versions/node/v24.11.1/bin/claude \
  --print --output-format text --tools "" --permission-mode plan "$prompt"
```

The wrapper must never echo environment variables or the input prompt. Verify with:

```bash
bash -n <local-webui-root>/claude-taxonomy-namer
stat -c '%a' <local-webui-root>/claude-taxonomy-namer
python3 -m unittest discover -s tests -p 'test_taxonomy_naming.py' -v
```

Expected: shell syntax clean, mode `700`, tests PASS. Do not make a live API call in this task.

- [ ] **Step 5: Commit repository files**

```bash
git add scripts/taxonomy_naming.py tests/test_taxonomy_naming.py
git commit -m "feat: name taxonomy categories with bounded fallback"
```

The wrapper is deployment state outside the repository; document its checksum in Task 12 rather than adding it to Git.

### Task 7: Engine orchestration, CLI, and first migration

**Files:**
- Create: `scripts/taxonomy_engine.py`
- Create: `scripts/taxonomy_cli.py`
- Create: `tests/test_taxonomy_engine.py`
- Create after tests pass: `taxonomy.json`

- [ ] **Step 1: Write failing engine and CLI tests**

```python
def test_migration_preserves_all_legacy_category_memberships():
    registry = self.engine.migrate(today="2026-07-15")
    self.assertEqual(set(registry.categories), set(SEED_CATEGORY_IDS.values()))
    for page in self.pages.values():
        for tag in set(page.frontmatter.get("tags", [])) & rc.CATEGORY_TAGS:
            stable_path = page.path.relative_to(self.root).as_posix()
            self.assertIn((stable_path, SEED_CATEGORY_IDS[tag]), membership_pairs(registry))

def test_sync_handles_changed_and_deleted_pages_without_blocking_successful_pages():
    result = self.engine.sync(today="2026-07-15", allow_global=False)
    self.assertNotIn("pages/Deleted.md", {m.page for m in result.memberships})
    self.assertIn("pages/Failed.md", result.pending_pages)
    self.assertEqual(result.changes_since_global, 2)

def test_global_trigger_is_due_by_count_or_age_or_force():
    self.assertTrue(te.global_due(self.registry_with_changes(5), self.config, self.now))
    self.assertTrue(te.global_due(self.registry_from_eight_days_ago(), self.config, self.now))
    self.assertFalse(te.global_due(self.fresh_registry(), self.config, self.now))

def test_no_change_sync_does_not_rewrite_registry():
    before = (self.root / "taxonomy.json").read_bytes()
    self.engine.sync(today="2026-07-15", allow_global=False)
    self.assertEqual((self.root / "taxonomy.json").read_bytes(), before)

def test_deletion_shrinks_category_and_removes_empty_forming_category():
    result = self.engine.sync(today="2026-07-15", allow_global=False)
    self.assertEqual(self.member_count(result, "cat_survives"), 2)
    self.assertNotIn("cat_empty_forming", result.categories)
    self.assertTrue(any(event.type == "delete" for event in result.events))

def test_cli_help_and_validate_are_side_effect_free():
    completed = subprocess.run([sys.executable, "scripts/taxonomy_cli.py", "validate"], cwd=ROOT, capture_output=True, text=True)
    self.assertEqual(completed.returncode, 0)
    self.assertIn("分类注册表校验通过", completed.stdout)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy_engine.py' -v`

Expected: FAIL because engine and CLI modules do not exist.

- [ ] **Step 3: Implement the orchestration API**

```python
class TaxonomyEngine:
    def __init__(self, root, config, encoder=None, namer=None): ...
    def migrate(self, today=None) -> Registry: ...
    def sync(self, page_paths=None, today=None, allow_global=True) -> Registry: ...
    def global_rebuild(self, today=None) -> Registry: ...
    def status(self) -> dict[str, object]: ...
    def validate(self) -> None: ...

def global_due(registry, config, now) -> bool: ...
```

`migrate` creates the eight seeds with IDs from `taxonomy_signals.LEGACY_TAG_TO_SEED_ID`, display names from `radar_common.TAG_TO_CATEGORY_PAGE`, and definitions from the corresponding MOC page summaries. `sync` compares content fingerprints, processes new/changed pages independently, creates a `forming` category plus memberships when `detect_forming_group` succeeds, removes deleted-page memberships, shrinks affected categories, removes empty `forming` categories with a deletion event, increments `changes_since_global`, queues failures, and calls `global_rebuild` when count or age is due. If neither page content nor taxonomy state changed, return without touching `taxonomy.json`, so repeated runs are byte-identical and do not create Git noise. All mutations use stable vault-relative POSIX page paths such as `pages/GNN.md`. It must write only a fully validated registry and leave the previous file untouched on failure.

`global_rebuild` computes candidate clusters and relations into a detached registry, reconciles lifecycle changes, and sends naming requests only for newly created categories or categories whose member Jaccard is below `naming_change_jaccard` or whose relations changed. Apply at most `max_naming_calls`; retain keyword fallbacks with `naming_status="pending"`. Validate the complete detached registry before atomically replacing the previous file. On embedding, clustering, schema, or validation failure, preserve the previous registry; naming failures alone use the documented fallback and do not fail the rebuild.

CLI contract:

```text
taxonomy_cli.py migrate [--dry-run]
taxonomy_cli.py sync [--page pages/X.md] [--no-global]
taxonomy_cli.py global [--no-llm]
taxonomy_cli.py status [--json]
taxonomy_cli.py validate
```

All commands resolve the vault root from the script path. `status` and `validate` must not load the embedding model.

- [ ] **Step 4: Run unit tests and perform dry-run migration**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_taxonomy_engine.py' -v
python3 scripts/taxonomy_cli.py migrate --dry-run
python3 -m unittest discover -s tests -v
```

Expected: tests PASS; dry run reports current page count, eight seed categories, and legacy membership count without writing `taxonomy.json`.

- [ ] **Step 5: Create and validate the committed initial registry**

Run:

```bash
python3 scripts/taxonomy_cli.py migrate
python3 scripts/taxonomy_cli.py validate
python3 scripts/taxonomy_cli.py status --json
git diff --check
```

Expected: `taxonomy.json` exists, contains all current pages that carry legacy category tags, has no dangling IDs/cycles, and reports zero pending pages.

- [ ] **Step 6: Commit Milestone 1**

```bash
git add scripts/taxonomy_engine.py scripts/taxonomy_cli.py tests/test_taxonomy_engine.py taxonomy.json
git commit -m "feat: migrate knowledge base to evolving taxonomy"
```

## Milestone 2: Automatic Triggering And Graph Data

### Task 8: Knowledge server sync, status, and global rebuild APIs

**Files:**
- Modify: `scripts/serve_kb.py`
- Modify: `tests/test_serve_kb.py`
- Modify: `<local-webui-root>/kbserve-control`

- [ ] **Step 1: Add failing server tests**

```python
def test_refresh_runs_taxonomy_before_index_and_graph(self):
    refreshed = self.builder.refresh(force=True)
    self.assertEqual((self.root / "runs.log").read_text().splitlines(), ["taxonomy", "index", "graph"])

def test_weekly_due_check_runs_even_when_pages_and_generated_files_are_fresh(self):
    self.builder.refresh(force=True)
    self.mark_taxonomy_eight_days_old()
    self.builder.refresh(force=False, now_monotonic=61)
    self.assertEqual((self.root / "runs.log").read_text().splitlines().count("taxonomy"), 2)

def test_taxonomy_status_and_rebuild_endpoints_are_localhost_only_json(self):
    _, status = self.request_json("/api/taxonomy/status")
    _, rebuilt = self.request_json("/api/taxonomy/rebuild", method="POST")
    self.assertTrue(status["ok"])
    self.assertTrue(rebuilt["ok"])
    self.assertEqual(rebuilt["mode"], "global")

def test_taxonomy_failure_keeps_static_service_available_and_reports_error():
    with self.assertRaises(HTTPError) as caught:
        self.request_json("/api/taxonomy/rebuild", method="POST")
    self.assertEqual(caught.exception.code, 500)
    with urlopen(self.base + "/viewer.html") as response:
        self.assertEqual(response.status, 200)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_serve_kb.py' -v`

Expected: FAIL because taxonomy commands and endpoints are absent.

- [ ] **Step 3: Extend the builder and request handler**

Before the ordinary stale-output decision, run a cheap taxonomy due check at most once per `due_check_seconds`; this calls `taxonomy_cli.py sync` even when page mtimes and generated files are already fresh, so the weekly trigger does not depend on a new edit. After a page change, run `taxonomy_cli.py sync` before `build_index.py` and `render_graph.py`. Guard the entire check/build sequence with the existing builder lock. Add `GET /api/taxonomy/status` and `POST /api/taxonomy/rebuild`; the rebuild endpoint executes `taxonomy_cli.py global` with the configured naming wrapper and returns parsed status plus captured non-secret output. Reject non-loopback clients for both taxonomy endpoints and require the exact existing `ALLOWED_ORIGIN` on the POST request. Extend OPTIONS only for the fixed POST endpoint. Do not accept paths, commands, model names, or thresholds from HTTP requests.

If sync fails during ordinary static freshness refresh, log the taxonomy error, continue serving the last valid registry, and run index/graph from that registry. If the explicit rebuild endpoint fails, return HTTP 500 JSON and keep the old file.

- [ ] **Step 4: Point the deployed service at the wrapper safely**

Add one non-secret environment variable in `<local-webui-root>/kbserve-control`:

```bash
TAXONOMY_NAMER_COMMAND=<local-webui-root>/claude-taxonomy-namer
export TAXONOMY_NAMER_COMMAND
```

Do not source `runtime.env` in `kbserve-control`; only the mode-700 wrapper reads credentials.

- [ ] **Step 5: Verify service behavior**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_serve_kb.py' -v
bash -n <local-webui-root>/kbserve-control
python3 -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit repository changes**

```bash
git add scripts/serve_kb.py tests/test_serve_kb.py
git commit -m "feat: automate taxonomy sync in knowledge server"
```

### Task 9: Publish taxonomy through graph-data.json

**Files:**
- Modify: `scripts/render_graph.py`
- Modify: `tests/test_v3_scripts.py`
- Regenerate: `graph-data.json`

- [ ] **Step 1: Add failing graph-data assertions**

```python
def test_graph_data_contains_taxonomy_nodes_memberships_and_relations(self):
    payload = json.loads(render_graph.render_graph_data(pages, edges, broken, degree, registry))
    self.assertEqual(payload["taxonomy"]["schemaVersion"], 1)
    self.assertTrue(payload["taxonomy"]["categories"])
    self.assertTrue(payload["taxonomy"]["memberships"])
    self.assertIn("status", payload["taxonomy"]["categories"][0])
    self.assertIn("signals", payload["taxonomy"]["memberships"][0])

def test_graph_data_taxonomy_references_existing_pages_and_categories(self):
    category_ids = {item["id"] for item in payload["taxonomy"]["categories"]}
    page_ids = {item["id"] for item in payload["nodes"]}
    for membership in payload["taxonomy"]["memberships"]:
        self.assertIn(membership["category"], category_ids)
        self.assertIn(membership["page"], page_ids)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_v3_scripts.py' -v`

Expected: FAIL because graph data has no taxonomy payload.

- [ ] **Step 3: Extend deterministic rendering**

Load and validate `taxonomy.json` once in `main()`. Add a top-level `taxonomy` object containing `schemaVersion`, `generatedAt`, `categories`, `memberships`, `events` limited to the most recent 100, and `stats`. Convert stored page paths back to graph page IDs through `Path(page).stem`. Keep category and membership arrays sorted by ID/path and category ID.

- [ ] **Step 4: Regenerate and verify**

Run:

```bash
python3 scripts/render_graph.py
python3 -m unittest discover -s tests -p 'test_v3_scripts.py' -v
python3 scripts/check_health.py
git diff --check
```

Expected: render succeeds, tests PASS, health reports `ERROR 0` and `WARN 0`.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_graph.py tests/test_v3_scripts.py graph-data.json
git commit -m "feat: publish taxonomy in graph data"
```

### Task 10: Integrate classification with the knowledge-page Skill

**Files:**
- Modify: `.claude/skills/create-knowledge-page/SKILL.md`
- Modify: `tests/test_create_knowledge_page_skill.py`

- [ ] **Step 1: Add a failing Skill contract test**

```python
def test_completion_syncs_taxonomy_after_final_page_content(self):
    self.assertIn("python3 scripts/taxonomy_cli.py sync --page", self.body)
    sync = self.body.index("python3 scripts/taxonomy_cli.py sync --page")
    health = self.body.index("python3 scripts/check_health.py")
    self.assertLess(sync, health)
    self.assertIn("分类失败不回滚已完成的知识页", self.body)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_create_knowledge_page_skill.py' -v`

Expected: FAIL because taxonomy sync is not in the workflow.

- [ ] **Step 3: Update the completion workflow**

After the page body and frontmatter are final, invoke:

```bash
python3 scripts/taxonomy_cli.py sync --page "pages/<actual filename>.md"
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Require the final response to report category assignments or a forming category when sync succeeds. If sync fails, preserve the page, report the taxonomy error, and continue index/graph/health using the last valid registry.

- [ ] **Step 4: Verify and commit**

```bash
python3 -m unittest discover -s tests -p 'test_create_knowledge_page_skill.py' -v
python3 -m unittest discover -s tests -v
git add .claude/skills/create-knowledge-page/SKILL.md tests/test_create_knowledge_page_skill.py
git commit -m "feat: classify completed knowledge pages"
```

## Milestone 3: Taxonomy Graph Experience

### Task 11: Three graph modes and taxonomy details

**Files:**
- Modify: `graph-view.html`
- Modify: `tests/test_graph_view_contract.py`

- [ ] **Step 1: Add failing UI contract assertions**

```python
def test_graph_has_three_stable_modes_and_manual_rebuild(self):
    for value in ('data-mode="knowledge"', 'data-mode="taxonomy"', 'data-mode="combined"'):
        self.assertIn(value, self.html)
    self.assertIn('id="rebuildTaxonomy"', self.html)
    self.assertIn("/api/taxonomy/rebuild", self.html)

def test_taxonomy_elements_and_details_are_rendered_without_inner_html(self):
    for function in ("taxonomyElements", "combinedElements", "renderCategoryDetails", "renderMembershipDetails"):
        self.assertRegex(self.html, rf"function\s+{function}\s*\(")
    self.assertIn("data(status)", self.html)
    self.assertNotRegex(self.html, r"detailContent[^\n]*innerHTML")

def test_mode_switch_does_not_resize_the_workspace_or_duplicate_handlers(self):
    self.assertIn("state.mode", self.html)
    self.assertIn("replaceGraphElements", self.html)
    self.assertIn("aspect-ratio", self.html)
```

- [ ] **Step 2: Run and confirm RED**

Run: `python3 -m unittest discover -s tests -p 'test_graph_view_contract.py' -v`

Expected: FAIL because the mode controls and taxonomy rendering functions are absent.

- [ ] **Step 3: Implement the mode model before styling**

Add a three-option segmented control with buttons carrying `data-mode="knowledge|taxonomy|combined"`. Keep one Cytoscape instance and implement:

```javascript
function knowledgeElements(payload) { /* current pages and wikilink edges */ }
function taxonomyElements(payload) { /* category nodes and parent/related/redirect edges */ }
function combinedElements(payload) { /* pages, categories, wikilinks, memberships */ }
function replaceGraphElements(mode) {
  state.mode = mode;
  state.cy.batch(() => { state.cy.elements().remove(); state.cy.add(elementsFor(mode)); });
  bindModeIndependentHandlersOnce();
  runLayout(false);
}
```

Category nodes use stable IDs prefixed `category:`. Membership edges use `membership:<page>:<category>`. Parent, related, and redirect edges use distinct line styles and legend labels. Forming categories use a dashed border; stable categories use a solid border; merged categories are hidden by default but reachable through aliases/details.

- [ ] **Step 4: Implement taxonomy navigation and safe details**

Replace fixed category checkboxes with roots derived from categories that have no active parents. Because categories may have multiple parents, render the navigation as expandable references with a visited-ID guard rather than recursively duplicating subtrees without bounds. Category details must show definition, status, member count, timestamps, parents, children, related categories, aliases, and recent events. Page details must show all memberships sorted by score with signal contributions.

Use `textContent`, DOM creation, and existing accessible drawer patterns. Do not render algorithm explanations as permanent instructional text.

- [ ] **Step 5: Implement manual rebuild states**

The rebuild button POSTs `/api/taxonomy/rebuild`, disables itself with `aria-busy`, reports concise success/failure in the existing overlay/status surface, then reloads graph data only after a successful response. It must not send thresholds or commands.

- [ ] **Step 6: Run contract tests and commit**

```bash
python3 -m unittest discover -s tests -p 'test_graph_view_contract.py' -v
python3 -m unittest discover -s tests -v
git add graph-view.html tests/test_graph_view_contract.py
git commit -m "feat: add evolving taxonomy graph views"
```

### Task 12: Documentation, deployment tests, and end-to-end verification

**Files:**
- Modify: `README.md`
- Modify: `Web操作台使用与维护说明书.md`
- Modify: `tests/test_web_console_manual.py`
- Create: `tests/test_taxonomy_end_to_end.py`

- [ ] **Step 1: Write failing documentation and end-to-end tests**

Documentation assertions must require `taxonomy.json`, `.cache/taxonomy/`, all five CLI commands, three graph modes, automatic count/weekly triggers, the naming wrapper, failure behavior, and model cache setup.

End-to-end test fixture:

```python
def test_three_novel_pages_form_and_then_shrink_a_category(self):
    vault = copy_fixture_vault()
    run_cli(vault, "migrate")
    add_pages(vault, [novel_page("A"), novel_page("B"), novel_page("C")])
    run_cli(vault, "sync", "--no-global", env={"TAXONOMY_TEST_ENCODER": "deterministic"})
    registry = load(vault / "taxonomy.json")
    formed = [c for c in registry["categories"].values() if c["status"] == "forming"]
    self.assertEqual(len(formed), 1)
    delete_page(vault, "C")
    run_cli(vault, "sync", "--no-global", env={"TAXONOMY_TEST_ENCODER": "deterministic"})
    registry = load(vault / "taxonomy.json")
    self.assertEqual(member_count(registry, formed[0]["id"]), 2)
```

The deterministic test encoder is only selected through the explicit test environment variable and must never be the production default.

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_web_console_manual.py' -v
python3 -m unittest discover -s tests -p 'test_taxonomy_end_to_end.py' -v
```

Expected: FAIL because documentation and end-to-end fixture support are absent.

- [ ] **Step 3: Update the documentation**

Document installation, one-time model download, migration, normal automatic operation, CLI recovery, category lifecycle, three graph modes, local-only API boundaries, the external naming wrapper, and how to disable LLM naming with `global --no-llm`. State explicitly that original page tags remain historical/manual signals and automatic memberships live in `taxonomy.json`.

- [ ] **Step 4: Run all automated verification**

```bash
python3 -m unittest discover -s tests -v
python3 scripts/taxonomy_cli.py validate
python3 scripts/taxonomy_cli.py status --json
python3 scripts/check_health.py
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
bash <local-webui-root>/test-dedicated-claude-config.sh
node <local-webui-root>/patch-integrated-workbench.mjs --check
node <local-webui-root>/patch-dangerous-mode.mjs --check
bash -n <local-webui-root>/claude-taxonomy-namer
sha256sum <local-webui-root>/claude-taxonomy-namer
git diff --check
```

Expected: all tests PASS, taxonomy validates, health reports `ERROR 0` and `WARN 0`, and patch checks are idempotent.

- [ ] **Step 5: Restart localhost services and verify APIs**

```bash
<local-webui-root>/kbserve-control restart
<local-webui-root>/webui-control restart
curl -fsS http://127.0.0.1:18081/api/taxonomy/status
curl -fsS http://127.0.0.1:18081/api/revision
ss -ltnp '( sport = :18080 or sport = :18081 )'
```

Expected: both APIs return `ok: true`; only `127.0.0.1:18080` and `127.0.0.1:18081` listen.

- [ ] **Step 6: Perform Playwright desktop and mobile verification**

Use the Playwright CLI skill. At desktop `1440x900` and mobile `390x844`:

1. Open `http://127.0.0.1:18080/` and enter the graph.
2. Verify knowledge, taxonomy, and combined modes are nonblank and switch without layout overlap.
3. Inspect a category and a multi-category page; verify scores, signals, parents, and related categories fit their panels.
4. Trigger a no-LLM fixture global rebuild through a test server or temporary fixture, verify busy/success states, and confirm the graph refreshes.
5. Verify console errors and warnings are zero and canvas pixels are nonblank.
6. Capture screenshots outside tracked paths and remove `.playwright-cli/` afterward.

- [ ] **Step 7: Commit documentation and final test artifacts**

```bash
git add README.md Web操作台使用与维护说明书.md tests/test_web_console_manual.py tests/test_taxonomy_end_to_end.py
git commit -m "docs: document evolving taxonomy operations"
```

- [ ] **Step 8: Finish the branch**

Invoke `superpowers:verification-before-completion`, then `superpowers:finishing-a-development-branch`. Merge locally only after the complete suite passes on both the feature branch and merged `master`; restart both services from the main knowledge-base directory and leave the worktree clean.
