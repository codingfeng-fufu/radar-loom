from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import radar_common as rc
import taxonomy_cli
from taxonomy_cli import parse_args
from taxonomy_embeddings import page_semantic_text
from taxonomy_engine import TaxonomyEngine, _page_summary, load_config
from taxonomy_models import Registry, parameters_hash, write_registry


class InterviewTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pages").mkdir()
        (self.root / "config").mkdir()
        config = json.loads((ROOT / "config" / "taxonomy.json").read_text())
        (self.root / "config" / "taxonomy.json").write_text(json.dumps(config))
        interview = json.loads((ROOT / "config" / "interview-taxonomy.json").read_text())
        (self.root / "config" / "interview-taxonomy.json").write_text(json.dumps(interview))

    def tearDown(self):
        self.tmp.cleanup()

    def page(self, name, frontmatter):
        lines = ["---"] + [f"{k}: {v}" for k, v in frontmatter.items()] + ["---", f"# {name}"]
        (self.root / "pages" / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")

    def test_scan_isolation_and_paths(self):
        self.page("K", {"tags": "[KG]"})
        self.page("I", {"page_type": "interview", "summary": "s"})
        self.page("X", {"page_type": "project"})
        knowledge = TaxonomyEngine(self.root, load_config(self.root))._scan_pages()
        interview = TaxonomyEngine(self.root, load_config(self.root, "interview"), profile="interview")
        self.assertEqual(set(knowledge), {"K"})
        self.assertEqual(set(interview._scan_pages()), {"I"})
        self.assertEqual(interview.registry_path.name, "interview-taxonomy.json")
        self.assertTrue(str(interview.cache_root).endswith(".cache/interview-taxonomy"))

    def test_invalid_profile_and_config_weights(self):
        with self.assertRaises(ValueError):
            TaxonomyEngine(self.root, {}, profile="invalid")
        config = load_config(self.root, "interview")
        self.assertAlmostEqual(sum(config["signal_weights"].values()), 1.0)
        self.assertEqual(config["signal_weights"]["projects"], 0.0)

    def test_interview_migration_starts_empty(self):
        self.page("I", {"page_type": "interview", "tags": "[KG]", "summary": "s"})
        registry = TaxonomyEngine(self.root, load_config(self.root, "interview"), profile="interview").migrate(today="2026-01-01")
        self.assertEqual(registry.categories, {})
        self.assertEqual(registry.memberships, [])
        self.assertEqual(set(registry.page_fingerprints), {"pages/I.md"})

    def test_cli_profile_help_and_parsing(self):
        args = parse_args(["--profile", "interview", "status", "--json"])
        self.assertEqual(args.profile, "interview")
        self.assertEqual(args.command, "status")
        old_root = taxonomy_cli.ROOT
        try:
            taxonomy_cli.ROOT = self.root
            registry = Registry.empty(parameters_hash(load_config(self.root, "interview")), "2026-01-01")
            write_registry(self.root / "interview-taxonomy.json", registry, set())
            from io import StringIO
            from contextlib import redirect_stdout
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(taxonomy_cli.main(["--profile", "interview", "status", "--json"]), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["memberships"], 0)
        finally:
            taxonomy_cli.ROOT = old_root
        self.assertTrue((self.root / "interview-taxonomy.json").exists())
        self.assertFalse((self.root / ".cache").exists())

    def test_summary_precedence_and_fallback(self):
        both = rc.PageInfo("P", Path("P.md"), {"summary": "English", "摘要": "中文"}, "body")
        fallback = rc.PageInfo("P", Path("P.md"), {"摘要": "中文"}, "body")
        self.assertIn("English", page_semantic_text(both))
        self.assertNotIn("中文", page_semantic_text(both))
        self.assertIn("中文", page_semantic_text(fallback))
        for value in ("", "   "):
            page = rc.PageInfo("P", Path("P.md"), {"summary": value, "摘要": "中文"}, "body")
            self.assertIn("中文", page_semantic_text(page))

    def test_naming_summary_uses_interview_summary(self):
        page = rc.PageInfo("I", Path("I.md"), {"page_type": "interview", "summary": "English", "摘要": "中文"}, "")
        self.assertEqual(_page_summary(page), "English")


if __name__ == "__main__":
    unittest.main()
