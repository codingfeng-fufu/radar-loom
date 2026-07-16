from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh"
SESSION = "kb-regression"


@unittest.skipUnless(os.environ.get("KB_E2E") == "1", "set KB_E2E=1 to run browser regression")
class WebWorkbenchE2ETests(unittest.TestCase):
    @classmethod
    def run_cli(cls, *args: str, timeout: int = 45) -> str:
        completed = subprocess.run(
            ["bash", str(CLI), f"-s={SESSION}", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0 or "### Error" in output:
            raise AssertionError(output)
        return output

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if os.environ.get("KB_E2E") != "1":
            return
        cls.run_cli("close", timeout=10)
        cls.run_cli("open", "http://127.0.0.1:18080/", timeout=30)
        cls.run_cli("resize", "1440", "900")

    @classmethod
    def tearDownClass(cls):
        if os.environ.get("KB_E2E") == "1":
            try:
                cls.run_cli("close", timeout=10)
            except Exception:
                pass
        super().tearDownClass()

    def assert_code(self, code: str, expected: str = "true", timeout: int = 45):
        output = self.run_cli("run-code", code, timeout=timeout)
        self.assertIn(expected, output, output)

    def test_complete_workbench_regression(self):
        self.assert_code("""async page => {
          const trigger=page.locator('#createKnowledge');
          await trigger.click(); await page.locator('#cancelCreateKnowledge').click();
          const cancelOk=!(await page.locator('#createKnowledgeDialog').evaluate(d=>d.open)) && await trigger.evaluate(e=>document.activeElement===e);
          await trigger.click(); await page.keyboard.press('Escape');
          const escapeOk=!(await page.locator('#createKnowledgeDialog').evaluate(d=>d.open));
          await trigger.click(); await page.locator('#createKnowledgeDialog').click({position:{x:2,y:2}});
          const backdropOk=!(await page.locator('#createKnowledgeDialog').evaluate(d=>d.open));
          return cancelOk&&escapeOk&&backdropOk;
        }""")

        self.assert_code("""async page => {
          const frame=page.frameLocator('#knowledgeFrame');
          await frame.locator('#navigationSearch').fill('扩散模型');
          await frame.locator('.search-card').filter({hasText:'扩散模型 Diffusion Models DDPM'}).waitFor();
          await page.keyboard.press('Control+K');
          return await frame.locator('#navigationSearch').evaluate(e=>document.activeElement===e);
        }""")

        self.assert_code("""async page => {
          const frame=page.frames().find(f=>f.url().includes('127.0.0.1:18081'));
          await frame.goto('http://127.0.0.1:18081/graph-view.html');
          await frame.locator('#search').fill('扩散模型');
          await frame.locator('.search-result').filter({hasText:'扩散模型'}).first().click();
          await page.locator('#askClaude').click();
          const kind=await page.locator('#dialogContextKind').textContent();
          const label=await page.locator('#dialogFile').textContent();
          await page.locator('#cancelAsk').click();
          return kind==='当前图谱' && label.includes('扩散模型');
        }""")

        self.assert_code("""async page => {
          const frame=page.frames().find(f=>f.url().includes('graph-view.html'));
          await frame.locator('[data-mode="combined"]').click();
          await frame.evaluate(()=>{window.cyForTest=undefined});
          await frame.reload();
          await frame.locator('[data-mode="combined"][aria-pressed="true"]').waitFor();
          const stored=await frame.evaluate(()=>JSON.parse(sessionStorage.getItem('radar-graph-state-v1')));
          return stored.mode==='combined' && typeof stored.zoom==='number' && Boolean(stored.pan);
        }""")

        self.assert_code("""async page => {
          await page.locator('[data-tab="claude"]').click();
          const frame=page.frameLocator('#claudeFrame');
          const input=frame.locator('textarea').first();
          await input.fill('未发送草稿');
          await input.dispatchEvent('input');
          await page.reload();
          await page.locator('[data-tab="claude"]').click();
          const restored=page.frameLocator('#claudeFrame').locator('textarea').first();
          await restored.waitFor();
          return (await restored.inputValue())==='未发送草稿';
        }""", timeout=60)

        self.assert_code("""async page => {
          await page.route(/^https?:\\/\\/(?!127\\.0\\.0\\.1|localhost)/,route=>route.abort());
          const frame=page.frames().find(f=>f.url().includes('127.0.0.1:18081'));
          await frame.goto('http://127.0.0.1:18081/viewer.html?f=pages%2F%E6%89%A9%E6%95%A3%E6%A8%A1%E5%9E%8B%20Diffusion%20Models%20DDPM.md');
          await frame.locator('.katex').first().waitFor();
          await frame.goto('http://127.0.0.1:18081/graph-view.html');
          await frame.locator('#graph canvas').first().waitFor();
          return true;
        }""", timeout=60)

        self.run_cli("resize", "390", "844")
        self.assert_code("""async page => {
          const topOk=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
          await page.locator('[data-tab="preview"]').click();
          const frame=page.frames().find(f=>f.url().includes('127.0.0.1:18081'));
          const frameOk=await frame.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
          return topOk&&frameOk;
        }""")

        console = self.run_cli("console", "error")
        self.assertIn("Errors: 0", console, console)


if __name__ == "__main__":
    unittest.main()
