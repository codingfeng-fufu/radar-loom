from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("KB_E2E") == "1", "set KB_E2E=1 to run browser regression")
class WebWorkbenchE2ETests(unittest.TestCase):
    SCREENSHOTS = (
        "engineering-interview-list.png",
        "engineering-interview-sample-page.png",
        "engineering-interview-graph.png",
        "engineering-interview-upload-dialog.png",
        "engineering-interview-mobile.png",
    )

    def test_sample_page_is_only_exercised_against_the_worktree_server(self):
        self.assertEqual(
            os.environ.get("KB_VIEWER_URL", "http://127.0.0.1:18081"),
            "http://127.0.0.1:18081",
        )

    def test_playwright_spec(self):
        artifact_dir = Path(os.environ.get("E2E_ARTIFACT_DIR", "/tmp/engineering-interview-e2e"))
        environment = os.environ.copy()
        environment.setdefault("KB_VIEWER_URL", "http://127.0.0.1:18081")
        environment["E2E_ARTIFACT_DIR"] = str(artifact_dir)
        completed = subprocess.run(
            [
                "npm", "run", "test:e2e", "--",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=240,
            check=False,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        self.assertEqual(completed.returncode, 0, output)
        for name in self.SCREENSHOTS:
            screenshot = artifact_dir / name
            self.assertTrue(screenshot.is_file(), f"missing screenshot {screenshot}\n{output}")
            self.assertGreater(screenshot.stat().st_size, 5_000, f"blank screenshot {screenshot}")


if __name__ == "__main__":
    unittest.main()
