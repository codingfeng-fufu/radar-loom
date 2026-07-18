from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("KB_E2E") == "1", "set KB_E2E=1 to run browser regression")
class WebWorkbenchE2ETests(unittest.TestCase):
    def test_sample_page_is_only_exercised_against_the_worktree_server(self):
        self.assertEqual(
            os.environ.get("KB_VIEWER_URL", "http://127.0.0.1:18081"),
            "http://127.0.0.1:18081",
        )

    def test_playwright_spec(self):
        completed = subprocess.run(
            [
                "npm", "run", "test:e2e", "--",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=240,
            check=False,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        self.assertEqual(completed.returncode, 0, output)


if __name__ == "__main__":
    unittest.main()
