from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import radar_common as rc  # noqa: E402

try:
    import taxonomy_embeddings as te  # noqa: E402
except ModuleNotFoundError:
    te = None


class FakeEncoder:
    model_name = "fake-v1"
    max_chars = 10_000

    def __init__(self):
        self.calls = 0

    def encode(self, texts):
        self.calls += len(texts)
        return np.asarray(
            [[len(text), text.count("graph") + 1] for text in texts],
            dtype=np.float32,
        )


def page_info(title="Graph RAG", summary="摘要", body="## Mechanism\ngraph retrieval"):
    return rc.PageInfo(
        name=title,
        path=Path("pages") / f"{title}.md",
        frontmatter={"摘要": summary},
        body=body,
        links=[],
    )


class TaxonomyEmbeddingModuleTests(unittest.TestCase):
    def test_taxonomy_embeddings_module_exists(self):
        self.assertIsNotNone(te, "scripts/taxonomy_embeddings.py must exist")


@unittest.skipUnless(te is not None, "taxonomy_embeddings is not implemented yet")
class TaxonomyEmbeddingTests(unittest.TestCase):
    def test_sentence_transformer_loads_from_local_cache_only(self):
        calls = {}
        sentence_module = types.ModuleType("sentence_transformers")
        hub_module = types.ModuleType("huggingface_hub")

        class FakeModel:
            max_seq_length = 512

        def snapshot_download(model_name, **kwargs):
            calls["snapshot"] = (model_name, kwargs)
            return "/cache/multilingual-e5-small"

        def make_model(model_path):
            calls["model_path"] = model_path
            return FakeModel()

        sentence_module.SentenceTransformer = make_model
        hub_module.snapshot_download = snapshot_download
        with mock.patch.dict(sys.modules, {
            "sentence_transformers": sentence_module,
            "huggingface_hub": hub_module,
        }):
            te.SentenceTransformerEncoder("intfloat/multilingual-e5-small")

        self.assertEqual(calls["snapshot"], (
            "intfloat/multilingual-e5-small",
            {"local_files_only": True},
        ))
        self.assertEqual(calls["model_path"], "/cache/multilingual-e5-small")

    def test_unchanged_page_reuses_normalized_cached_vector(self):
        with tempfile.TemporaryDirectory() as directory:
            encoder = FakeEncoder()
            cache = te.EmbeddingCache(Path(directory), encoder)
            page = page_info()

            first = cache.vector_for(page)
            second = cache.vector_for(page)

            self.assertEqual(encoder.calls, 1)
            np.testing.assert_allclose(first, second)
            self.assertAlmostEqual(float(np.linalg.norm(first)), 1.0, places=6)

    def test_title_summary_headings_and_body_affect_fingerprint(self):
        page = page_info(body="## Mechanism\ntext\n```python\nsecret_code()\n```\nbody graph")
        text = te.page_semantic_text(page)

        self.assertGreaterEqual(text.count("Graph RAG"), 2)
        self.assertIn("摘要", text)
        self.assertIn("Mechanism", text)
        self.assertIn("body graph", text)
        self.assertNotIn("secret_code", text)
        self.assertNotEqual(
            te.content_fingerprint(text, "model-a"),
            te.content_fingerprint(text, "model-b"),
        )
        changed = te.page_semantic_text(page_info(summary="不同摘要"))
        self.assertNotEqual(
            te.content_fingerprint(text, "model-a"),
            te.content_fingerprint(changed, "model-a"),
        )

    def test_long_text_is_chunked_and_mean_vector_is_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            encoder = FakeEncoder()
            encoder.max_chars = 40
            cache = te.EmbeddingCache(Path(directory), encoder)
            vector = cache.vector_for(page_info(body="graph paragraph\n\n" * 20))

            self.assertGreater(encoder.calls, 1)
            self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
