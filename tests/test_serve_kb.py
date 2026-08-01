import json
import os
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import serve_kb  # noqa: E402


BUILD_INDEX = """from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / '_index.md').write_text('fresh index\\n', encoding='utf-8')
(root / '_interview_index.md').write_text('fresh interview index\\n', encoding='utf-8')
with (root / 'runs.log').open('a', encoding='utf-8') as handle:
    handle.write('index\\n')
print('index rebuilt')
"""

RENDER_GRAPH = """import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
(root / 'graph-data.json').write_text(json.dumps({'stats': {'nodes': 1, 'edges': 0}}), encoding='utf-8')
(root / 'interview-graph-data.json').write_text(json.dumps({'stats': {'nodes': 2, 'edges': 1}}), encoding='utf-8')
(root / 'graph.md').write_text('fresh graph\\n', encoding='utf-8')
with (root / 'runs.log').open('a', encoding='utf-8') as handle:
    handle.write('graph\\n')
print('graph rebuilt')
"""

TAXONOMY_CLI = """import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
args = sys.argv[1:]
command = args[0]
if command == 'status':
    print(json.dumps({'categories': 2, 'pending_pages': 0, 'changes_since_global': 0}))
elif command == 'validate':
    print('valid')
else:
    with (root / 'runs.log').open('a', encoding='utf-8') as handle:
        handle.write(('global' if command == 'global' else 'interview-taxonomy' if args[:2] == ['--profile', 'interview'] else 'taxonomy') + '\\n')
    print(command + ' complete')
"""


class KnowledgeBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pages").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "pages" / "Example.md").write_text("# Example\n", encoding="utf-8")
        (self.root / "首页.md").write_text("# Home\n", encoding="utf-8")
        (self.root / "config" ).mkdir()
        (self.root / "config" / "interview-taxonomy.json").write_text("{}\n", encoding="utf-8")
        (self.root / "interview-taxonomy.json").write_text("{}\n", encoding="utf-8")
        (self.root / "scripts" / "build_index.py").write_text(BUILD_INDEX, encoding="utf-8")
        (self.root / "scripts" / "render_graph.py").write_text(RENDER_GRAPH, encoding="utf-8")
        (self.root / "scripts" / "taxonomy_cli.py").write_text(TAXONOMY_CLI, encoding="utf-8")
        self.now = [0.0]
        self.builder = serve_kb.KnowledgeBuilder(self.root, timeout=5, clock=lambda: self.now[0])

    def tearDown(self):
        self.temp.cleanup()

    def test_catalog_payload_combines_separate_graph_profiles(self):
        knowledge = {"nodes": [{"id": "A", "label": "Alpha", "href": "viewer.html?f=pages%2FA.md", "tags": ["KG"], "summary": "alpha"}], "edges": [{"source": "A", "target": "B"}]}
        interview = {"nodes": [{"id": "Q", "label": "Question", "href": "viewer.html?section=interview&f=pages%2FQ.md", "tags": ["LLM"]}], "edges": []}
        payload = serve_kb.catalog_payload(knowledge, interview)
        self.assertEqual([(item["section"], item["file"]) for item in payload["entries"]], [("knowledge", "pages/A.md"), ("interview", "pages/Q.md")])
        self.assertEqual(payload["edges"], [{"section": "knowledge", "source": "A", "target": "B"}])

    def make_outputs_older_than_sources(self):
        (self.root / "_index.md").write_text("old index\n", encoding="utf-8")
        (self.root / "graph-data.json").write_text("{}\n", encoding="utf-8")
        (self.root / "_interview_index.md").write_text("old interview index\n", encoding="utf-8")
        (self.root / "interview-graph-data.json").write_text("{}\n", encoding="utf-8")
        old = time.time_ns() - 2_000_000_000
        for output in self.builder._outputs:
            output.touch()
            output.chmod(0o644)
            os.utime(output, ns=(old, old))

    def test_stale_sources_rebuild_once_and_revision_is_stable_when_fresh(self):
        self.make_outputs_older_than_sources()

        first = self.builder.refresh()
        second = self.builder.refresh()

        self.assertTrue(first["rebuilt"])
        self.assertFalse(second["rebuilt"])
        self.assertEqual(second["revision"], first["revision"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8"), "taxonomy\ninterview-taxonomy\nindex\ngraph\n")
        self.assertIn("index rebuilt", first["output"])
        self.assertIn("graph rebuilt", first["output"])

    def test_fresh_outputs_skip_expensive_initial_taxonomy_check(self):
        self.builder.refresh(force=True)
        (self.root / "runs.log").write_text("", encoding="utf-8")
        result = self.builder.refresh()
        self.assertFalse(result["rebuilt"])
        self.assertEqual(result["output"], "")
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8"), "")

    def test_force_refresh_rebuilds_even_when_outputs_are_fresh(self):
        first = self.builder.refresh(force=True)
        second = self.builder.refresh(force=True)

        self.assertTrue(first["rebuilt"])
        self.assertTrue(second["rebuilt"])
        runs = (self.root / "runs.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(runs.count("taxonomy"), 2)
        self.assertEqual(runs.count("interview-taxonomy"), 2)
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("index"), 2)
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("graph"), 2)

    def test_deleting_a_page_marks_generated_outputs_as_stale(self):
        self.builder.refresh(force=True)

        (self.root / "pages" / "Example.md").unlink()
        refreshed = self.builder.refresh()

        self.assertTrue(refreshed["rebuilt"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").splitlines().count("taxonomy"), 2)
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("index"), 2)
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").count("graph"), 2)

    def test_failed_generator_raises_refresh_error_without_false_success(self):
        (self.root / "scripts" / "render_graph.py").write_text(
            "import sys\nprint('render failed', file=sys.stderr)\nsys.exit(3)\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(serve_kb.RefreshError, "render failed"):
            self.builder.refresh(force=True)

    def test_weekly_due_check_runs_even_when_pages_and_outputs_are_fresh(self):
        self.builder.refresh(force=True)
        self.now[0] = 61.0

        refreshed = self.builder.refresh(force=False)

        self.assertFalse(refreshed["rebuilt"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8").splitlines().count("taxonomy"), 2)

    def test_taxonomy_failure_keeps_last_static_outputs_available(self):
        self.builder.refresh(force=True)
        (self.root / "scripts" / "taxonomy_cli.py").write_text(
            "import sys\nprint('taxonomy failed', file=sys.stderr)\nsys.exit(5)\n",
            encoding="utf-8",
        )
        (self.root / "pages" / "Example.md").write_text("# Changed\n", encoding="utf-8")

        refreshed = self.builder.refresh()

        self.assertTrue(refreshed["rebuilt"])
        self.assertIn("taxonomy failed", refreshed["output"])
        self.assertTrue((self.root / "graph-data.json").exists())

    def test_source_paths_include_interview_config_and_registry(self):
        sources = self.builder.source_paths()

        self.assertIn(self.root / "config" / "interview-taxonomy.json", sources)
        self.assertIn(self.root / "interview-taxonomy.json", sources)

    def test_refresh_runs_both_taxonomy_profiles_with_exact_cli_order(self):
        calls = []
        original = self.builder._run_script

        def recording_run(script, *args, **kwargs):
            calls.append((script.name, args))
            return original(script, *args, **kwargs)

        self.builder._run_script = recording_run
        self.builder.refresh(force=True)

        self.assertEqual(calls[:2], [
            ("taxonomy_cli.py", ("sync",)),
            ("taxonomy_cli.py", ("--profile", "interview", "sync")),
        ])

    def test_revision_hashes_both_graph_outputs_in_fixed_order(self):
        self.builder.refresh(force=True)
        expected = __import__("hashlib").sha256(
            (self.root / "graph-data.json").read_bytes()
            + (self.root / "interview-graph-data.json").read_bytes()
        ).hexdigest()[:16]

        self.assertEqual(self.builder.revision(), expected)

    def test_one_taxonomy_profile_failure_does_not_skip_other_or_generators(self):
        (self.root / "scripts" / "taxonomy_cli.py").write_text(
            """import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
with (root / 'runs.log').open('a', encoding='utf-8') as handle:
    handle.write(('interview-taxonomy' if sys.argv[1:3] == ['--profile', 'interview'] else 'taxonomy') + '\\n')
if sys.argv[1:3] == ['--profile', 'interview']:
    print('interview failed', file=sys.stderr)
    sys.exit(7)
""",
            encoding="utf-8",
        )

        result = self.builder.refresh(force=True)

        self.assertIn("interview failed", result["output"])
        self.assertEqual((self.root / "runs.log").read_text(encoding="utf-8"), "taxonomy\ninterview-taxonomy\nindex\ngraph\n")


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
        (self.root / "scripts" / "taxonomy_cli.py").write_text(TAXONOMY_CLI, encoding="utf-8")
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

    def upload(self, files, origin="http://127.0.0.1:18080", destination=None):
        boundary = "----kb-" + uuid.uuid4().hex
        body = bytearray()
        if destination is not None:
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(b'Content-Disposition: form-data; name="destination"\r\n\r\n')
            body.extend(destination.encode())
            body.extend(b"\r\n")
        for name, mime, content in files:
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="files"; filename="{name}"\r\n'.encode())
            if mime is not None:
                body.extend(f"Content-Type: {mime}\r\n".encode())
            body.extend(b"\r\n")
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if origin is not None:
            headers["Origin"] = origin
        request = Request(self.base + "/api/uploads", data=bytes(body), method="POST", headers=headers)
        with urlopen(request, timeout=10) as response:
            return response, json.loads(response.read().decode("utf-8"))

    def upload_error(self, files, origin="http://127.0.0.1:18080", destination=None):
        with self.assertRaises(HTTPError) as caught:
            self.upload(files, origin=origin, destination=destination)
        return caught.exception, json.loads(caught.exception.read().decode("utf-8"))

    def test_explicit_refresh_rebuilds_and_revision_is_read_only(self):
        response, refreshed = self.request_json("/api/refresh", method="POST")
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("revision triggered refresh")):
            _, revision = self.request_json("/api/revision")

        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:18080")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(refreshed["ok"])
        self.assertTrue(refreshed["rebuilt"])
        self.assertEqual(refreshed["version"], 1)
        self.assertEqual(refreshed["operation"], "knowledge-refresh")
        self.assertEqual(refreshed["stats"], {"nodes": 1, "edges": 0})
        self.assertEqual(revision, {"ok": True, "revision": refreshed["revision"], "rebuilt": False})

    def test_taxonomy_rebuild_accepts_the_standalone_viewer_origin(self):
        request = Request(
            self.base + "/api/taxonomy/rebuild",
            data=b"{}",
            method="POST",
            headers={"Origin": "http://127.0.0.1:18081", "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:18081")
        self.assertTrue(payload["ok"])

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
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["operation"], "knowledge-refresh")
        self.assertIn("render failed", payload["error"])

    def test_static_responses_disable_cache_for_live_knowledge_files(self):
        with urlopen(self.base + "/viewer.html", timeout=5) as response:
            self.assertEqual(response.read(), b"viewer")
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_upload_accepts_all_allowed_formats_and_multiple_files(self):
        files = [
            ("paper.pdf", "application/pdf", b"%PDF-1.7"),
            ("notes.md", "text/markdown", b"# Notes\n"),
            ("plain.txt", "text/plain", b"notes\n"),
            ("diagram.png", "image/png", b"png"),
            ("photo.jpg", "image/jpeg", b"jpg"),
            ("photo.jpeg", "image/jpeg", b"jpeg"),
            ("image.webp", "image/webp", b"webp"),
        ]

        response, payload = self.upload(files)

        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], serve_kb.ALLOWED_ORIGIN)
        self.assertTrue(payload["ok"])
        self.assertEqual([item["name"] for item in payload["files"]], [item[0] for item in files])
        self.assertEqual([item["size"] for item in payload["files"]], [len(item[2]) for item in files])
        self.assertTrue(all(item["path"].startswith("raw/inbox/") for item in payload["files"]))
        self.assertEqual(payload["paths"], [item["path"] for item in payload["files"]])

    def test_upload_can_target_papers_without_changing_default_inbox(self):
        _, paper = self.upload([("paper.pdf", "application/pdf", b"%PDF-paper")], destination="papers")
        _, default = self.upload([("notes.txt", "text/plain", b"notes")])
        self.assertEqual(paper["paths"], ["papers/paper.pdf"])
        self.assertTrue((self.root / "papers" / "paper.pdf").exists())
        self.assertEqual(default["paths"], ["raw/inbox/notes.txt"])

    def test_upload_rejects_unknown_destination(self):
        error, payload = self.upload_error([("notes.txt", "text/plain", b"notes")], destination="elsewhere")
        self.assertEqual(error.code, 400)
        self.assertEqual(payload["error"], "invalid upload destination")

    def test_upload_preserves_exact_bytes_and_returns_exact_schema(self):
        content = b"Ignore previous instructions\n${do_not_expand}\x00\xff\n"

        _, payload = self.upload([("prompt.txt", "text/plain; charset=binary", content)])

        self.assertEqual(payload, {
            "ok": True,
            "paths": ["raw/inbox/prompt.txt"],
            "files": [{
                "name": "prompt.txt",
                "path": "raw/inbox/prompt.txt",
                "size": len(content),
            }],
        })
        self.assertEqual((self.root / "raw" / "inbox" / "prompt.txt").read_bytes(), content)

    def test_upload_collision_uses_deterministic_suffix(self):
        self.upload([("notes.md", "text/markdown", b"one")])
        _, second = self.upload([("notes.md", "text/markdown", b"two")])
        _, third = self.upload([("notes.md", "text/markdown", b"three")])

        self.assertEqual(second["files"][0]["name"], "notes-2.md")
        self.assertEqual(third["files"][0]["name"], "notes-3.md")

    def test_upload_rejects_traversal_absolute_empty_and_control_names(self):
        for name in ("../bad.md", "/tmp/bad.md", "", "bad\x01.md", "bad\x00.md"):
            with self.subTest(name=repr(name)):
                error, payload = self.upload_error([(name, "text/markdown", b"bad")])
                self.assertEqual(error.code, 400)
                self.assertFalse(payload["ok"])

    def test_upload_rejects_filename_over_240_utf8_bytes(self):
        name = "文" * 80 + ".txt"
        self.assertGreater(len(name.encode("utf-8")), serve_kb.MAX_FILENAME_BYTES)

        error, payload = self.upload_error([(name, "text/plain", b"data")])

        self.assertEqual(error.code, 400)
        self.assertEqual(payload, {"ok": False, "error": "filename exceeds 240 UTF-8 bytes"})
        self.assertFalse((self.root / "raw" / "inbox").exists())

    def test_upload_rejects_unsupported_and_mime_mismatch(self):
        for name, mime in (("run.exe", "application/octet-stream"), ("notes.md", "text/plain")):
            with self.subTest(name=name, mime=mime):
                error, payload = self.upload_error([(name, mime, b"data")])
                self.assertEqual(error.code, 415)
                self.assertFalse(payload["ok"])

    def test_upload_rejects_missing_or_invalid_part_mime(self):
        for mime in (None, "not-a-valid-mime"):
            with self.subTest(mime=mime):
                error, payload = self.upload_error([("notes.txt", mime, b"data")])
                self.assertEqual(error.code, 415)
                self.assertFalse(payload["ok"])

    def test_upload_rejects_empty_files_and_declares_20_mib_file_limit(self):
        error, _ = self.upload_error([("empty.txt", "text/plain", b"")])
        self.assertEqual(error.code, 400)
        self.assertEqual(serve_kb.MAX_UPLOAD_BYTES, 20 * 1024 * 1024)

    def test_upload_requires_exact_localhost_origin(self):
        for origin in (None, "http://localhost:18080", "http://127.0.0.1:9999"):
            with self.subTest(origin=origin):
                error, payload = self.upload_error([("notes.md", "text/markdown", b"ok")], origin=origin)
                self.assertEqual(error.code, 403)
                self.assertFalse(payload["ok"])

    def test_invalid_batch_persists_no_partial_files(self):
        error, _ = self.upload_error([
            ("good.md", "text/markdown", b"good"),
            ("bad.md", "text/plain", b"bad"),
        ])

        self.assertEqual(error.code, 415)
        inbox = self.root / "raw" / "inbox"
        self.assertFalse(inbox.exists() and any(inbox.iterdir()))

    def test_replace_failure_cleans_temps_and_rolls_back_entire_batch(self):
        real_replace = serve_kb.os.replace
        calls = [0]

        def fail_second_replace(source, destination):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError("injected replace failure")
            return real_replace(source, destination)

        with mock.patch.object(serve_kb.os, "replace", side_effect=fail_second_replace):
            error, payload = self.upload_error([
                ("one.txt", "text/plain", b"one"),
                ("two.txt", "text/plain", b"two"),
            ])

        self.assertEqual(error.code, 500)
        self.assertIn("injected replace failure", payload["error"])
        inbox = self.root / "raw" / "inbox"
        self.assertEqual(list(inbox.iterdir()), [])

    def test_upload_rejects_request_over_20_mib_before_parsing(self):
        request = Request(
            self.base + "/api/uploads",
            data=b"x",
            method="POST",
            headers={
                "Origin": serve_kb.ALLOWED_ORIGIN,
                "Content-Type": "multipart/form-data; boundary=x",
                "Content-Length": str(serve_kb.MAX_UPLOAD_BYTES + 1),
            },
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 413)

    def test_upload_rejects_non_ascii_request_content_type_as_json(self):
        request = Request(
            self.base + "/api/uploads",
            data=b"body",
            method="POST",
            headers={
                "Origin": serve_kb.ALLOWED_ORIGIN,
                "Content-Type": "multipart/form-data; boundary=é",
            },
        )

        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)

        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(
            json.loads(caught.exception.read().decode("utf-8")),
            {"ok": False, "error": "invalid multipart Content-Type"},
        )

    def test_generated_artifact_gets_do_not_run_refresh(self):
        self.builder.refresh(force=True)
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("read triggered refresh")):
            for path in (
                "/_index.md", "/_interview_index.md",
                "/graph-data.json", "/interview-graph-data.json",
            ):
                with self.subTest(path=path):
                    with urlopen(self.base + path, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_catalog_reads_current_graphs_without_running_refresh(self):
        self.builder.refresh(force=True)
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("catalog triggered refresh")):
            response, payload = self.request_json("/api/catalog")

        self.assertEqual(response.status, 200)
        self.assertEqual(
            [(entry["section"], entry["file"]) for entry in payload["entries"]],
            [],
        )
        self.assertEqual(payload["edges"], [])

    def test_taxonomy_status_and_rebuild_endpoints_return_json(self):
        _, status = self.request_json("/api/taxonomy/status")
        _, rebuilt = self.request_json("/api/taxonomy/rebuild", method="POST")

        self.assertTrue(status["ok"])
        self.assertEqual(status["categories"], 2)
        self.assertTrue(rebuilt["ok"])
        self.assertEqual(rebuilt["mode"], "global")
        self.assertEqual(rebuilt["version"], 1)
        self.assertEqual(rebuilt["operation"], "taxonomy-rebuild")
        self.assertEqual(rebuilt["stats"], {"nodes": 1, "edges": 0})

    def test_taxonomy_rebuild_failure_keeps_static_service_available(self):
        (self.root / "scripts" / "taxonomy_cli.py").write_text(
            "import sys\nprint('global failed', file=sys.stderr)\nsys.exit(6)\n",
            encoding="utf-8",
        )
        with self.assertRaises(HTTPError) as caught:
            self.request_json("/api/taxonomy/rebuild", method="POST")
        self.assertEqual(caught.exception.code, 500)

        with urlopen(self.base + "/viewer.html", timeout=5) as response:
            self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
