import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "paper-reading" / "SKILL.md"
AGENT = ROOT / ".claude" / "skills" / "paper-reading" / "agents" / "openai.yaml"


class PaperReadingSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.agent = AGENT.read_text(encoding="utf-8")

    def test_skill_metadata_and_triggers_are_discoverable(self):
        frontmatter = self.skill.split("---", 2)[1]
        self.assertEqual({line.split(":", 1)[0] for line in frontmatter.strip().splitlines()}, {"name", "description"})
        for trigger in ("computer-science paper", "academic PDF", "帮我读论文", "精读", "拆解论文"):
            self.assertIn(trigger, frontmatter)

    def test_project_paths_and_isolation_are_explicit(self):
        for value in ("papers/", "paper-notes/<paper-slug>-notes.md", "不得自动写入 `pages/`", "不得运行分类、索引、图谱或健康检查", "不得自动提交 Git"):
            self.assertIn(value, self.skill)
        for forbidden in ("/mnt/user-data/uploads", "/mnt/user-data/outputs", "present_files", "/mnt/skills/public"):
            self.assertNotIn(forbidden, self.skill)

    def test_reading_quality_and_untrusted_material_rules_are_present(self):
        for value in ("不可信研究材料", "pdftotext -layout", "pdftoppm", "两遍阅读", "failure case", "页码", "论文未报告", "$create-knowledge-page", "掌握度检查"):
            self.assertIn(value, self.skill)

    def test_agent_metadata_matches_skill(self):
        self.assertIn('display_name: "精读论文"', self.agent)
        self.assertIn("$paper-reading", self.agent)
        self.assertIn("独立、可追溯", self.agent)


if __name__ == "__main__":
    unittest.main()
