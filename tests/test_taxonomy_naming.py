from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import taxonomy_naming as tn  # noqa: E402
except ModuleNotFoundError:
    tn = None


def request(category_id="cat_new"):
    return tn.NamingRequest(
        category_id=category_id,
        representative_pages=[{"title": "图检索推理", "summary": "结构化检索与推理"}],
        keywords=["图检索", "结构化推理", "知识增强"],
        neighbor_definitions=["检索增强生成"],
    )


class TaxonomyNamingModuleTests(unittest.TestCase):
    def test_taxonomy_naming_module_exists(self):
        self.assertIsNotNone(tn, "scripts/taxonomy_naming.py must exist")


@unittest.skipUnless(tn is not None, "taxonomy_naming is not implemented yet")
class TaxonomyNamingTests(unittest.TestCase):
    def test_keyword_fallback_is_deterministic_and_marks_pending(self):
        first = tn.KeywordNamer().name(request())
        second = tn.KeywordNamer().name(request())
        self.assertEqual(first, second)
        self.assertEqual(first.naming_status, "pending")
        self.assertEqual(first.name, "图检索 结构化推理")

    def test_command_namer_accepts_valid_json_and_respects_budget(self):
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdin.read(); print('{\"name\":\"图结构推理\",\"definition\":\"融合图检索与结构化推理。\"}')",
        ]
        namer = tn.CommandNamer(command, timeout=5)
        results = tn.name_changed_categories(
            [request("one"), request("two")], namer, max_calls=1
        )
        self.assertEqual(results[0].naming_status, "ready")
        self.assertEqual(results[0].name, "图结构推理")
        self.assertEqual(results[1].naming_status, "pending")

    def test_invalid_command_output_falls_back_without_losing_category(self):
        invalid_outputs = [
            "not json",
            '{"name":"<b>危险</b>","definition":"定义"}',
            '{"name":"名字","definition":""}',
        ]
        for output in invalid_outputs:
            with self.subTest(output=output):
                command = [
                    sys.executable,
                    "-c",
                    f"import sys; sys.stdin.read(); print({output!r})",
                ]
                result = tn.CommandNamer(command, timeout=5).name(request())
                self.assertEqual(result.naming_status, "pending")
                self.assertTrue(result.name)
                self.assertTrue(result.definition)


if __name__ == "__main__":
    unittest.main()
