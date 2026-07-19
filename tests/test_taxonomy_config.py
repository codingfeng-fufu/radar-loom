from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TaxonomyConfigTests(unittest.TestCase):
    def test_runtime_dependencies_and_config_are_explicit(self):
        requirements_path = ROOT / "requirements-taxonomy.txt"
        config_path = ROOT / "config" / "taxonomy.json"
        self.assertTrue(requirements_path.exists(), "requirements-taxonomy.txt must exist")
        self.assertTrue(config_path.exists(), "config/taxonomy.json must exist")

        requirements = requirements_path.read_text(encoding="utf-8")
        for package in ("numpy", "scipy", "scikit-learn", "sentence-transformers", "networkx"):
            self.assertIn(package, requirements)

        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["schema_version"], 1)
        self.assertEqual(config["embedding_model"], "intfloat/multilingual-e5-small")
        self.assertEqual(config["forming_min_pages"], 3)
        self.assertEqual(config["global_after_changes"], 5)
        self.assertEqual(config["due_check_seconds"], 60)
        self.assertEqual(config.get("command_timeout_seconds"), 900)
        for key, value in {"candidate_min_pages": 2, "candidate_neighborhood_k": 12, "candidate_cohesion_threshold": 0.78, "candidate_related_threshold": 0.70, "representative_page_limit": 5}.items():
            self.assertEqual(config[key], value)
        self.assertEqual(sum(config["signal_weights"].values()), 1.0)
        self.assertIn(".cache/taxonomy/", (ROOT / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
