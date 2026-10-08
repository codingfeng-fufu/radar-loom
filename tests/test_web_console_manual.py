from __future__ import annotations

import re
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "Web操作台使用与维护说明书.md"
README = ROOT / "README.md"
KBSERVE_CONTROL = Path(os.environ["KB_SERVE_CONTROL"]) if os.environ.get("KB_SERVE_CONTROL") else None


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
            "<local-webui-root>/webui-control start",
            "<local-webui-root>/webui-control stop",
            "<local-webui-root>/webui-control restart",
            "<local-webui-root>/webui-control status",
            "<local-webui-root>/webui-control logs",
            "<local-webui-root>/kbserve-control start",
            "<local-webui-root>/kbserve-control restart",
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
            "<local-webui-root>/claude-config",
            "<local-webui-root>/runtime.env",
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

    def test_live_graph_refresh_is_documented_and_deployed(self):
        for phrase in (
            "POST /api/refresh",
            "GET /api/revision",
            "每 4 秒",
            "自动重建",
            "scripts/serve_kb.py",
        ):
            self.assertIn(phrase, self.manual)

        if KBSERVE_CONTROL is None or not KBSERVE_CONTROL.is_file():
            self.skipTest("本机 WebUI 控制脚本不属于公开仓库；设置 KB_SERVE_CONTROL 后运行部署联调检查")
        control = KBSERVE_CONTROL.read_text(encoding="utf-8")
        self.assertIn("scripts/serve_kb.py", control)
        self.assertNotIn("python3 -m http.server", control)

    def test_evolving_taxonomy_operation_is_documented(self):
        for phrase in (
            "taxonomy.json",
            ".cache/taxonomy/",
            "taxonomy_cli.py migrate",
            "taxonomy_cli.py sync",
            "taxonomy_cli.py global",
            "taxonomy_cli.py status",
            "taxonomy_cli.py validate",
            "累计新增或修改 5 个页面",
            "每周",
            "知识关系",
            "分类结构",
            "综合视图",
            "claude-taxonomy-namer",
            "global --no-llm",
            "intfloat/multilingual-e5-small",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.manual)
        self.assertIn("taxonomy.json", self.readme)
        self.assertIn("自动归属", self.readme)


if __name__ == "__main__":
    unittest.main()
