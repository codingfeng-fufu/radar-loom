from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HomeWebFirstTests(unittest.TestCase):
    def test_home_leads_with_web_workbench(self):
        text = (ROOT / "首页.md").read_text(encoding="utf-8")
        first_screen = text[:900]
        for phrase in ("Web 操作台", "搜索", "交互图谱", "询问 Claude", "创建知识页"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, first_screen)
        self.assertIn("维护与排障", text)
        self.assertNotIn("要看全局图谱时运行", first_screen)


if __name__ == "__main__":
    unittest.main()
