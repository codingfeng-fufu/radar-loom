"""Fast, read-only duplicate suggestions for Markdown pages.

The scores are screening signals, not permission to merge pages.  Candidate
generation uses character shingles so Chinese and English content work without
an external tokenizer.  Results are cached until page file metadata changes.
"""
from __future__ import annotations

import difflib
import hashlib
import re
import threading
from collections import Counter, defaultdict
from pathlib import Path


_lock = threading.Lock()
_cached_key: tuple | None = None
_cached_pairs: list[dict[str, object]] = []
_FRONTMATTER = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL)


def _normalized_body(text: str) -> str:
    body = _FRONTMATTER.sub("", text)
    return re.sub(r"\s+", " ", body.casefold()).strip()


def _shingles(text: str, width: int = 5) -> set[str]:
    compact = re.sub(r"\s+", "", text)
    if len(compact) < width:
        return {compact} if compact else set()
    return {compact[index:index + width] for index in range(len(compact) - width + 1)}


def _signature(paths: list[Path]) -> tuple:
    return tuple((path.name, path.stat().st_mtime_ns, path.stat().st_size) for path in paths)


def _rank_pairs(paths: list[Path]) -> list[dict[str, object]]:
    pages = []
    postings: dict[str, list[int]] = defaultdict(list)
    exact: dict[str, list[int]] = defaultdict(list)
    for path in paths:
        try:
            body = _normalized_body(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        shingles = _shingles(body)
        index = len(pages)
        pages.append((path, shingles))
        if body:
            exact[hashlib.sha256(body.encode("utf-8")).hexdigest()].append(index)
        for shingle in shingles:
            postings[shingle].append(index)

    overlap: Counter[tuple[int, int]] = Counter()
    # Very common fragments usually come from page templates rather than the
    # concept itself; comparing them creates noise and quadratic work.
    for members in postings.values():
        if len(members) > 40:
            continue
        for offset, left in enumerate(members):
            for right in members[offset + 1:]:
                overlap[left, right] += 1
    exact_pairs = set()
    for members in exact.values():
        for offset, left in enumerate(members):
            exact_pairs.update((left, right) for right in members[offset + 1:])

    pairs = []
    for left, right in set(overlap) | exact_pairs:
        left_path, left_set = pages[left]
        right_path, right_set = pages[right]
        content_score = 1.0 if (left, right) in exact_pairs else (2 * len(left_set & right_set) / max(1, len(left_set) + len(right_set)))
        title_score = difflib.SequenceMatcher(None, left_path.stem.casefold(), right_path.stem.casefold()).ratio() * .92
        score = max(content_score, title_score)
        if score >= .5:
            pairs.append({"left": f"pages/{left_path.name}", "right": f"pages/{right_path.name}", "score": round(score, 3), "method": "content" if content_score >= title_score else "title"})
    # Title-only candidates can have no shared content shingles.
    known = set(overlap) | exact_pairs
    for left, (left_path, _) in enumerate(pages):
        for right in range(left + 1, len(pages)):
            if (left, right) in known:
                continue
            right_path = pages[right][0]
            score = difflib.SequenceMatcher(None, left_path.stem.casefold(), right_path.stem.casefold()).ratio() * .92
            if score >= .5:
                pairs.append({"left": f"pages/{left_path.name}", "right": f"pages/{right_path.name}", "score": round(score, 3), "method": "title"})
    pairs.sort(key=lambda item: (-item["score"], item["left"], item["right"]))
    return pairs


def duplicate_payload(root: Path, threshold: float = .86) -> dict[str, object]:
    global _cached_key, _cached_pairs
    paths = sorted((root / "pages").glob("*.md"))
    key = (str(root.resolve()), _signature(paths))
    with _lock:
        if key != _cached_key:
            _cached_pairs = _rank_pairs(paths)
            _cached_key = key
        matches = [pair for pair in _cached_pairs if pair["score"] >= threshold][:200]
    return {"version": 1, "threshold": threshold, "pairs": matches, "manualReviewRequired": True}
