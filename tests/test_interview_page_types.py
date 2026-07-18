from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import radar_common as rc  # noqa: E402


class InterviewPageTypeTests(unittest.TestCase):
    def test_page_type_defaults_legacy_pages_to_knowledge(self):
        self.assertEqual(rc.page_type({}), rc.KNOWLEDGE_PAGE_TYPE)
        self.assertEqual(rc.page_type({"page_type": "  "}), rc.KNOWLEDGE_PAGE_TYPE)

    def test_page_type_recognizes_interview_and_rejects_other_explicit_values(self):
        self.assertEqual(rc.page_type({"page_type": "interview"}), rc.INTERVIEW_PAGE_TYPE)
        self.assertEqual(rc.page_type({"page_type": " interview "}), "invalid")
        self.assertEqual(rc.page_type({"page_type": "project"}), "invalid")

    def test_partition_pages_excludes_invalid_pages(self):
        pages = {
            "legacy": rc.PageInfo("legacy", Path("legacy.md"), {}, ""),
            "interview": rc.PageInfo("interview", Path("interview.md"), {"page_type": "interview"}, ""),
            "invalid": rc.PageInfo("invalid", Path("invalid.md"), {"page_type": "other"}, ""),
        }
        knowledge, interviews = rc.partition_pages(pages)
        self.assertEqual(set(knowledge), {"legacy"})
        self.assertEqual(set(interviews), {"interview"})

    def test_interview_output_paths_are_rooted_at_vault(self):
        self.assertEqual(rc.INTERVIEW_INDEX_FILE, rc.VAULT_ROOT / "_interview_index.md")
        self.assertEqual(rc.INTERVIEW_GRAPH_FILE, rc.VAULT_ROOT / "interview-graph.md")
        self.assertEqual(rc.INTERVIEW_GRAPH_DATA_FILE, rc.VAULT_ROOT / "interview-graph-data.json")


class FrontmatterBlockListTests(unittest.TestCase):
    def test_inline_lists_and_scalar_values_remain_supported(self):
        fm, body = rc.parse_frontmatter("---\ntags: [one, \"two\"]\nsource: note.md\n---\nBody\n")
        self.assertEqual(fm["tags"], ["one", "two"])
        self.assertEqual(fm["source"], "note.md")
        self.assertEqual(body, "Body\n")

    def test_indented_block_lists_parse_for_metadata_fields(self):
        text = "---\nsource:\n  - \"papers/a.pdf\"\n  - 'papers/b.pdf'\ntags:\n  - [RAG]\nroles:\n  - interviewer\nrelated_concepts:\n  - \"Graph RAG\"\nignored:\n  nested: value\n---\n# Body\n"
        fm, body = rc.parse_frontmatter(text)
        self.assertEqual(fm["source"], ["papers/a.pdf", "papers/b.pdf"])
        self.assertEqual(fm["tags"], ["[RAG]"])
        self.assertEqual(fm["roles"], ["interviewer"])
        self.assertEqual(fm["related_concepts"], ["Graph RAG"])
        self.assertNotIn("nested", fm)
        self.assertEqual(body, "# Body\n")


if __name__ == "__main__":
    unittest.main()
