import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import serve_kb  # noqa: E402


BUILD_INDEX = """from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / '_index.md').write_text('fresh index\\n', encoding='utf-8')
with (root / 'runs.log').open('a', encoding='utf-8') as handle:
    handle.write('index\\n')
print('index rebuilt')
"""

RENDER_GRAPH = """import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / 'graph-data.json').write_text(json.dumps({'stats': {'nodes': 1, 'edges': 0}}), encoding='utf-8')
(root / 'graph.md').write_text('fresh graph\\n', encoding='utf-8')
with (root / 'runs.log').open('a', encoding='utf-8') as handle:
    handle.write('graph\\n')
print('graph rebuilt')
"""


class KnowledgeBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pages").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "pages" / "Example.md").write_text("# Example\n", encoding="utf-8")
        (self.root / "首页.md").write_text("# Home\n", encoding="utf-8")
        (self.root / "scripts" / "build_index.py").write_text(BUILD_INDEX, encoding="utf-8")
        (self.root / "scripts" / "render_graph.py").write_text(RENDER_GRAPH, encoding="utf-8")
        self.builder = serve_kb.KnowledgeBuilder(self.root, timeout=5)

    def tearDown(self):
        self.temp.cleanup()

    def make_outputs_older_than_sources(self):
        (self.root / "_index.md").write_text("old index\n", encoding="utf-8")
        (self.root / "graph-data.json").write_text("{}\n", encoding="utf-8")
        old = time.time_ns() - 2_000_000_000
        for output in (self.root / "_index.md", self.root / "graph-data.json"):
            output.touch()
            output.chmod(0o644)
            import os
            os.utime(output, ns=(old, old))

    def test_stale_sources_rebuild_once_and_revision_is_stable_when_fresh(self):
        self.make_outputs_older_than_sources()

        first = self.builder.refresh()
        second = self.builder.refresh()

        self.assertTrue(first["rebuilt"])
        self.assertFalse(second["rebuilt"])
        self.assertEqual(second["revision"], first["revision"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8"), "index\ngraph\n")
        self.assertIn("index rebuilt", first["output"])
        self.assertIn("graph rebuilt", first["output"])

    def test_force_refresh_rebuilds_even_when_outputs_are_fresh(self):
        first = self.builder.refresh(force=True)
        second = self.builder.refresh(force=True)

        self.assertTrue(first["rebuilt"])
        self.assertTrue(second["rebuilt"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("index"), 2)
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("graph"), 2)

    def test_failed_generator_raises_refresh_error_without_false_success(self):
        (self.root / "scripts" / "render_graph.py").write_text(
            "import sys\nprint('render failed', file=sys.stderr)\nsys.exit(3)\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(serve_kb.RefreshError, "render failed"):
            self.builder.refresh(force=True)


class KnowledgeServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pages").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "pages" / "Example.md").write_text("# Example\n", encoding="utf-8")
        (self.root / "viewer.html").write_text("viewer", encoding="utf-8")
        (self.root / "scripts" / "build_index.py").write_text(BUILD_INDEX, encoding="utf-8")
        (self.root / "scripts" / "render_graph.py").write_text(RENDER_GRAPH, encoding="utf-8")
        self.builder = serve_kb.KnowledgeBuilder(self.root, timeout=5)
        self.server = serve_kb.create_server("127.0.0.1", 0, self.root, self.builder)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request_json(self, path, method="GET"):
        request = Request(
            self.base + path,
            method=method,
            headers={"Origin": "http://127.0.0.1:18080"},
        )
        with urlopen(request, timeout=5) as response:
            return response, json.loads(response.read().decode("utf-8"))

    def test_refresh_and_revision_endpoints_rebuild_and_set_localhost_cors(self):
        response, refreshed = self.request_json("/api/refresh", method="POST")
        _, revision = self.request_json("/api/revision")

        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:18080")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(refreshed["ok"])
        self.assertTrue(refreshed["rebuilt"])
        self.assertEqual(revision, {"ok": True, "revision": refreshed["revision"], "rebuilt": False})

    def test_refresh_endpoint_returns_json_error_when_generation_fails(self):
        (self.root / "scripts" / "render_graph.py").write_text(
            "import sys\nprint('render failed', file=sys.stderr)\nsys.exit(4)\n",
            encoding="utf-8",
        )

        with self.assertRaises(HTTPError) as caught:
            self.request_json("/api/refresh", method="POST")

        self.assertEqual(caught.exception.code, 500)
        payload = json.loads(caught.exception.read().decode("utf-8"))
        self.assertEqual(payload["ok"], False)
        self.assertIn("render failed", payload["error"])

    def test_static_responses_disable_cache_for_live_knowledge_files(self):
        with urlopen(self.base + "/viewer.html", timeout=5) as response:
            self.assertEqual(response.read(), b"viewer")
            self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
