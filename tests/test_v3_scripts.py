from __future__ import annotations

import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import radar_common as rc  # noqa: E402
import check_health  # noqa: E402
import taxonomy_models as tm  # noqa: E402


class CommonV3Tests(unittest.TestCase):
    def test_v3_tags_and_graph_paths(self):
        self.assertEqual(
            rc.CATEGORY_TAGS,
            {"KG", "RAG", "LLM机制", "可信度", "多智能体", "前沿", "基础", "评测"},
        )
        self.assertIn("CoMaGRAG", rc.PROJECT_TAGS)
        self.assertEqual(rc.INDEX_FILE, ROOT / "_index.md")
        self.assertEqual(rc.GRAPH_DATA_FILE, ROOT / "graph-data.json")
        self.assertEqual(set(rc.GRAPH_DIR_FILES), rc.CATEGORY_TAGS)

    def test_parse_source_types_and_local_path(self):
        self.assertEqual(rc.parse_source("https://example.com/a"), ("url", None))
        self.assertEqual(rc.parse_source("对话记录 2026-07-12"), ("chat", None))
        self.assertEqual(
            rc.parse_source("papers/example.pdf p.3-5"),
            ("local", "papers/example.pdf"),
        )
        self.assertEqual(
            rc.parse_source("raw/processed/note.md"),
            ("local", "raw/processed/note.md"),
        )
        self.assertEqual(rc.parse_source("somewhere"), ("unknown", None))


class HealthMathTests(unittest.TestCase):
    def test_undelimited_math_flags_ddpm_style_equations(self):
        body = """普通说明。\n前向过程 q(x_t | x_{t-1}) 加噪。\nL_simple = E_{t, x_0} [ ‖ ε - ε_θ(x_t, t) ‖² ]\n裸命令 \\frac{a}{b}\n"""
        self.assertEqual(check_health.undelimited_math_lines(body), [2, 3, 4])

    def test_undelimited_math_ignores_delimited_math_and_code(self):
        body = r"""行内 $q(x_t | x_{t-1})$ 正常。
$$
L_{simple} = \mathbb{E}[\epsilon^2]
$$
代码 `x_t = 1` 与 https://example.com/a_b。
文件 MASTER_knowledge_base.md 与长度≤阈值不是公式。
```python
x_t = epsilon_theta(x_t)
```
括号公式 \(x_t = x_0\) 正常。
"""
        self.assertEqual(check_health.undelimited_math_lines(body), [])


class IndexV3Tests(unittest.TestCase):
    def test_index_module_exposes_deterministic_renderer(self):
        try:
            module = importlib.import_module("build_index")
        except ModuleNotFoundError:
            self.fail("scripts/build_index.py is missing")
        rendered, concept_count, project_count, missing = module.render_index(rc.scan_pages())
        self.assertTrue(rendered.startswith("# 索引(机器生成,勿手工编辑)\n"))
        self.assertIn("## 基础\n", rendered)
        self.assertIn("## 评测\n", rendered)
        self.assertIn("## 项目\n", rendered)
        self.assertGreaterEqual(concept_count, 88)
        self.assertEqual(project_count, 5)
        self.assertGreaterEqual(missing, 0)

    def test_current_index_exactly_matches_pages(self):
        module = importlib.import_module("build_index")
        rendered, concept_count, project_count, missing = module.render_index(rc.scan_pages())
        self.assertEqual(rc.INDEX_FILE.read_text(encoding="utf-8"), rendered)
        self.assertGreaterEqual(concept_count, 88)
        self.assertEqual((project_count, missing), (5, 0))

    def test_all_concept_metadata_is_v3_healthy(self):
        for page in rc.scan_pages().values():
            tags = page.frontmatter.get("tags", [])
            if page.name == "首页" or "MOC" in tags or "项目" in tags:
                continue
            with self.subTest(page=page.name):
                summary = str(page.frontmatter.get("摘要", "")).strip()
                self.assertTrue(summary)
                self.assertLessEqual(len(summary), 60)
                source_type, local_path = rc.parse_source(str(page.frontmatter.get("来源", "")))
                self.assertIn(source_type, {"local", "url", "chat"})
                if source_type == "local":
                    self.assertTrue((ROOT / local_path).exists(), local_path)


class GraphV3Tests(unittest.TestCase):
    def test_graph_data_json_is_complete_and_deterministic(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        edges, broken, degree = graph.graph_data(pages)
        first = graph.render_graph_data(pages, edges, broken, degree)
        second = graph.render_graph_data(pages, edges, broken, degree)
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["stats"]["nodes"], len(pages))
        self.assertEqual(payload["stats"]["edges"], len(edges))
        self.assertEqual(len(payload["nodes"]), len(pages))
        self.assertEqual(len(payload["edges"]), len(edges))
        node_ids = [node["id"] for node in payload["nodes"]]
        self.assertEqual(node_ids, sorted(node_ids))
        self.assertEqual([edge["id"] for edge in payload["edges"]], sorted(edge["id"] for edge in payload["edges"]))
        self.assertEqual({edge["source"] for edge in payload["edges"]} | {edge["target"] for edge in payload["edges"]}, set(node_ids))

    def test_graph_data_json_exposes_workspace_metadata(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        edges, broken, degree = graph.graph_data(pages)
        payload = json.loads(graph.render_graph_data(pages, edges, broken, degree))
        by_id = {node["id"]: node for node in payload["nodes"]}
        self.assertEqual(by_id["首页"]["kind"], "moc")
        self.assertEqual(by_id["EvidenceFirst"]["kind"], "project")
        self.assertEqual(by_id["GraphRAG 架构"]["kind"], "concept")
        self.assertEqual(by_id["GraphRAG 架构"]["category"], "RAG")
        for node in payload["nodes"]:
            self.assertEqual(
                set(node),
                {"id", "label", "kind", "tags", "category", "confidence", "summary", "degree", "href"},
            )
            self.assertTrue(node["href"].startswith("viewer.html?f="))
        self.assertEqual(set(payload["categories"]), rc.CATEGORY_TAGS)

    def test_graph_data_contains_taxonomy_nodes_memberships_and_relations(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        edges, broken, degree = graph.graph_data(pages)
        registry = tm.load_registry(ROOT / "taxonomy.json")
        payload = json.loads(graph.render_graph_data(pages, edges, broken, degree, registry))

        self.assertEqual(payload["taxonomy"]["schemaVersion"], 1)
        self.assertTrue(payload["taxonomy"]["categories"])
        self.assertTrue(payload["taxonomy"]["memberships"])
        self.assertIn("status", payload["taxonomy"]["categories"][0])
        self.assertIn("signals", payload["taxonomy"]["memberships"][0])

    def test_graph_data_taxonomy_references_existing_pages_and_categories(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        edges, broken, degree = graph.graph_data(pages)
        registry = tm.load_registry(ROOT / "taxonomy.json")
        payload = json.loads(graph.render_graph_data(pages, edges, broken, degree, registry))
        category_ids = {item["id"] for item in payload["taxonomy"]["categories"]}
        page_ids = {item["id"] for item in payload["nodes"]}
        for membership in payload["taxonomy"]["memberships"]:
            self.assertIn(membership["category"], category_ids)
            self.assertIn(membership["page"], page_ids)

    def test_overview_contains_both_statistics_and_broken_links(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        pages["首页"].links.append("不存在的测试页面")
        edges, broken, degree = graph.graph_data(pages)
        rendered = graph.render_overview(pages, edges, broken, degree)
        self.assertIn("> 全库:节点", rendered)
        self.assertIn("> 概览:节点", rendered)
        self.assertIn("## 断链", rendered)
        self.assertIn("首页 → 不存在的测试页面", rendered)

    def test_rag_graph_includes_external_gray_neighbor_for_gnn_rag(self):
        graph = importlib.import_module("render_graph")
        pages = rc.scan_pages()
        edges, _, _ = graph.graph_data(pages)
        rendered, _, _ = graph.render_category("RAG", pages, edges)
        self.assertIn('GNN-RAG 图神经网络检索增强', rendered)
        self.assertIn('图神经网络 GNN', rendered)
        self.assertIn('classDef ext fill:#eee,stroke:#999;', rendered)


class CliV3Tests(unittest.TestCase):
    def run_script(self, script: str, *args: str):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_all_executables_help_without_business_output(self):
        for script in ("build_index.py", "render_graph.py", "new_page.py", "check_health.py"):
            with self.subTest(script=script):
                result = self.run_script(script, "--help")
                self.assertEqual(result.returncode, 0)
                self.assertIn("usage:", result.stdout)
                self.assertNotIn("已生成", result.stdout)
                self.assertNotIn("健康检查完成", result.stdout)

    def test_argumentless_scripts_reject_unknown_arguments(self):
        for script in ("build_index.py", "render_graph.py", "check_health.py"):
            with self.subTest(script=script):
                result = self.run_script(script, "--unknown")
                self.assertEqual(result.returncode, 2)

    def test_new_page_help_lists_v3_arguments(self):
        result = self.run_script("new_page.py", "--help")
        self.assertIn("--summary", result.stdout)
        self.assertIn("--force-source", result.stdout)


if __name__ == "__main__":
    unittest.main()
