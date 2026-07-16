from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VendorAssetTests(unittest.TestCase):
    def test_required_assets_exist_and_are_nonempty(self):
        required = [
            "vendor/marked/marked.min.js",
            "vendor/dompurify/purify.min.js",
            "vendor/highlight/highlight.min.js",
            "vendor/highlight/github.min.css",
            "vendor/mermaid/mermaid.min.js",
            "vendor/katex/katex.min.js",
            "vendor/katex/auto-render.min.js",
            "vendor/katex/katex.min.css",
            "vendor/cytoscape/cytoscape.min.js",
            "vendor/cytoscape/layout-base.js",
            "vendor/cytoscape/cose-base.js",
            "vendor/cytoscape/cytoscape-fcose.js",
        ]
        for relative in required:
            path = ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file(), relative)
                self.assertGreater(path.stat().st_size, 100)

    def test_katex_fonts_are_present(self):
        fonts = list((ROOT / "vendor/katex/fonts").glob("*.woff2"))
        self.assertGreaterEqual(len(fonts), 20)


if __name__ == "__main__":
    unittest.main()
