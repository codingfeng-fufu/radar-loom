from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "Web操作台使用与维护说明书.md"
README = ROOT / "README.md"


class WebConsoleManualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")

    def test_manual_has_complete_structure(self):
        for heading in (
            "项目定位与系统组成",
            "快速开始",
            "一体化操作台",
            "Viewer、数学公式与交互式图谱",
            "Claude Code 对话区",
            "知识库工作流",
            "火山 Coding Plan 专用配置",
            "目录、进程、端口与数据流",
            "日常维护与验证",
            "常见故障与恢复",
            "安全边界与已知限制",
            "关键文件索引",
        ):
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", self.manual)

    def test_commands_and_urls_are_current(self):
        for command in (
            "/home/u2023312337/webui/webui-control start",
            "/home/u2023312337/webui/webui-control stop",
            "/home/u2023312337/webui/webui-control restart",
            "/home/u2023312337/webui/webui-control status",
            "/home/u2023312337/webui/webui-control logs",
            "/home/u2023312337/webui/kbserve-control start",
            "/home/u2023312337/webui/kbserve-control restart",
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.manual)
        for url in (
            "http://127.0.0.1:18080/",
            "http://127.0.0.1:18081/viewer.html",
            "http://127.0.0.1:18081/graph-view.html",
        ):
            self.assertIn(url, self.manual)

    def test_skill_permissions_and_config_are_documented(self):
        for phrase in (
            "$create-knowledge-page",
            "创建知识页",
            "/home/u2023312337/webui/claude-config",
            "/home/u2023312337/webui/runtime.env",
            "https://ark.cn-beijing.volces.com/api/coding",
            "normal",
            "plan",
            "accept edits",
            "dangerously skip permissions",
        ):
            self.assertIn(phrase, self.manual)
        self.assertNotRegex(self.manual, r"ANTHROPIC_AUTH_TOKEN\s*=\s*[A-Za-z0-9_-]{20,}")

    def test_maintenance_security_and_troubleshooting_are_actionable(self):
        for phrase in (
            "python3 scripts/build_index.py",
            "python3 scripts/render_graph.py",
            "python3 scripts/check_health.py",
            "test-integrated-workbench.mjs",
            "test-dangerous-mode.mjs",
            "127.0.0.1",
            "HTTP 401",
            "HTTP 429",
            "CDN",
            "tmux",
            "CLAUDE_CONFIG_DIR",
        ):
            self.assertIn(phrase, self.manual)

    def test_readme_links_to_manual(self):
        self.assertIn("[Web 操作台使用与维护说明书](Web操作台使用与维护说明书.md)", self.readme)


if __name__ == "__main__":
    unittest.main()
