from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from search_service import search_payload  # noqa: E402


class SearchServiceTests(unittest.TestCase):
    def test_search_filters_phrases_negatives_and_sections(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pages = root / "pages"
            pages.mkdir()
            (pages / "Knowledge.md").write_text("摘要: knowledge\nRAG evidence retrieval\n", encoding="utf-8")
            (pages / "Interview.md").write_text("page_type: interview\nRAG interview answer\n", encoding="utf-8")

            result = search_payload(root, '"evidence retrieval" -noise', section="knowledge")

            self.assertEqual(result["total"], 1)
            self.assertEqual(result["results"][0]["title"], "Knowledge")

    def test_search_supports_or_and_updated_sort(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pages = root / "pages"
            pages.mkdir()
            (pages / "A.md").write_text("alpha\n", encoding="utf-8")
            (pages / "B.md").write_text("beta\n", encoding="utf-8")

            result = search_payload(root, "alpha OR beta", sort="updated")

            self.assertEqual(result["total"], 2)
            self.assertEqual({item["title"] for item in result["results"]}, {"A", "B"})


if __name__ == "__main__":
    unittest.main()
