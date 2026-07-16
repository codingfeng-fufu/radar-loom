#!/usr/bin/env python3
"""Semantic page representation and fingerprinted local embedding cache."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

import radar_common as rc


FENCED_CODE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


class SentenceTransformerEncoder:
    def __init__(self, model_name: str):
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        model_path = snapshot_download(model_name, local_files_only=True)
        self.model = SentenceTransformer(model_path)
        max_tokens = int(getattr(self.model, "max_seq_length", 512) or 512)
        self.max_chars = max(512, max_tokens * 4)

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False),
            dtype=np.float32,
        )


def page_semantic_text(page: rc.PageInfo) -> str:
    body = FENCED_CODE_RE.sub("", page.body)
    headings = [match.strip() for match in HEADING_RE.findall(body)]
    summary = str(page.frontmatter.get("摘要", "")).strip()
    parts = [page.name, page.name, summary, "\n".join(headings), body]
    return "\n\n".join(part for part in parts if part.strip()).strip()


def content_fingerprint(text: str, model_name: str) -> str:
    digest = hashlib.sha256()
    digest.update(model_name.encode("utf-8"))
    digest.update(b"\0")
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def _normalized(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    if not np.isfinite(norm) or norm == 0.0:
        raise ValueError("embedding vector must have a finite non-zero norm")
    return value / norm


def _chunks(text: str, max_chars: int) -> list[str]:
    if max_chars < 1:
        raise ValueError("encoder max_chars must be positive")
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        pieces = [paragraph[index:index + max_chars] for index in range(0, len(paragraph), max_chars)]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip() if current else piece
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = piece
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


class EmbeddingCache:
    def __init__(self, root: Path, encoder):
        self.root = Path(root)
        self.encoder = encoder
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, dict[str, object]]:
        if not self.manifest_path.exists():
            return {}
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_manifest(self) -> None:
        encoded = (json.dumps(self.manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".manifest.",
                suffix=".tmp",
                dir=self.root,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.manifest_path)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _cache_key(self, page: rc.PageInfo) -> str:
        return page.path.as_posix()

    def _vector_path(self, key: str) -> Path:
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return self.root / f"{name}.npy"

    def _write_vector(self, path: Path, vector: np.ndarray) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=f".{path.stem}.",
                suffix=".tmp",
                dir=self.root,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                np.save(handle, vector, allow_pickle=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def vector_for(self, page: rc.PageInfo) -> np.ndarray:
        text = page_semantic_text(page)
        model_name = str(self.encoder.model_name)
        fingerprint = content_fingerprint(text, model_name)
        key = self._cache_key(page)
        path = self._vector_path(key)
        entry = self.manifest.get(key, {})
        if entry.get("fingerprint") == fingerprint and entry.get("model_name") == model_name and path.exists():
            try:
                return _normalized(np.load(path, allow_pickle=False))
            except (OSError, ValueError):
                pass

        chunks = _chunks(text, int(getattr(self.encoder, "max_chars", 8192)))
        encoded = np.asarray(self.encoder.encode(chunks), dtype=np.float32)
        if encoded.ndim != 2 or encoded.shape[0] != len(chunks):
            raise ValueError("encoder must return one vector per text chunk")
        vector = _normalized(encoded.mean(axis=0))
        self._write_vector(path, vector)
        self.manifest[key] = {
            "fingerprint": fingerprint,
            "model_name": model_name,
            "dimension": int(vector.shape[0]),
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self._write_manifest()
        return vector

    def vectors_for(self, pages: dict[str, rc.PageInfo]) -> dict[str, np.ndarray]:
        return {name: self.vector_for(pages[name]) for name in sorted(pages)}
