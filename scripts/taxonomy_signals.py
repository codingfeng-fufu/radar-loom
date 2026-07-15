#!/usr/bin/env python3
"""Deterministic structural signals for incremental taxonomy assignment."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

import radar_common as rc
from taxonomy_models import Registry


LEGACY_TAG_TO_SEED_ID = {
    "KG": "cat_seed_kg",
    "RAG": "cat_seed_rag",
    "LLM机制": "cat_seed_llm",
    "可信度": "cat_seed_trust",
    "多智能体": "cat_seed_agents",
    "基础": "cat_seed_foundations",
    "评测": "cat_seed_evaluation",
    "前沿": "cat_seed_frontier",
}


@dataclass
class Assignment:
    category_id: str
    score: float
    signals: dict[str, float]
    reason: str


@dataclass
class FormingGroup:
    members: list[str]
    cohesion: float


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float32)
    right = np.asarray(right, dtype=np.float32)
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(left, right) / denominator)))


def _page_name(path: str) -> str:
    return Path(path).stem


def _active_members(registry: Registry) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {}
    for membership in registry.memberships:
        category = registry.categories.get(membership.category_id)
        if category is None or category.status == "merged":
            continue
        members.setdefault(membership.category_id, []).append(_page_name(membership.page))
    return members


def category_centroids(registry: Registry, vectors: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    centroids: dict[str, np.ndarray] = {}
    for category_id, member_names in sorted(_active_members(registry).items()):
        available = [vectors[name] for name in sorted(set(member_names)) if name in vectors]
        if not available:
            continue
        mean = np.asarray(available, dtype=np.float32).mean(axis=0)
        norm = float(np.linalg.norm(mean))
        if norm > 0.0:
            centroids[category_id] = mean / norm
    return centroids


def combine_signals(signals: dict[str, float], weights: dict[str, float]) -> float:
    return float(sum(float(weights.get(name, 0.0)) * float(signals.get(name, 0.0)) for name in weights))


def _link_signal(
    page: rc.PageInfo,
    category_id: str,
    registry: Registry,
    pages: dict[str, rc.PageInfo],
) -> float:
    neighbors = [rc.resolve_link(target, pages) for target in page.links]
    resolved = {name for name in neighbors if name is not None}
    if not resolved:
        return 0.0
    assigned = {
        _page_name(item.page)
        for item in registry.memberships
        if item.category_id == category_id
    }
    return len(resolved & assigned) / len(resolved)


def _tag_signal(page: rc.PageInfo, category_id: str) -> float:
    tags = page.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags]
    return 1.0 if any(LEGACY_TAG_TO_SEED_ID.get(str(tag)) == category_id for tag in tags) else 0.0


def _project_signal(
    page: rc.PageInfo,
    category_id: str,
    registry: Registry,
    pages: dict[str, rc.PageInfo],
) -> float:
    page_tags = page.frontmatter.get("tags", [])
    if not isinstance(page_tags, list):
        page_tags = [page_tags]
    projects = {str(tag) for tag in page_tags} & rc.PROJECT_TAGS
    if not projects:
        return 0.0
    members = [
        pages.get(_page_name(item.page))
        for item in registry.memberships
        if item.category_id == category_id
    ]
    members = [member for member in members if member is not None]
    if not members:
        return 0.0
    matching = 0
    for member in members:
        tags = member.frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags]
        if projects & {str(tag) for tag in tags}:
            matching += 1
    return matching / len(members)


def _reason(signals: dict[str, float]) -> str:
    labels = {"semantic": "语义", "links": "双链", "tags": "人工标签", "projects": "项目"}
    ranked = sorted(signals.items(), key=lambda item: (-item[1], item[0]))
    useful = [f"{labels.get(name, name)} {value:.2f}" for name, value in ranked if value > 0.0]
    return "，".join(useful[:2]) or "低强度综合信号"


def classify_page(
    page_name: str,
    vectors: dict[str, np.ndarray],
    registry: Registry,
    pages: dict[str, rc.PageInfo],
    config: dict,
) -> list[Assignment]:
    if page_name not in pages or page_name not in vectors:
        raise KeyError(f"missing page or vector: {page_name}")
    centroids = category_centroids(registry, vectors)
    assignments: list[Assignment] = []
    page = pages[page_name]
    for category_id, category in sorted(registry.categories.items()):
        if category.status == "merged" or category_id not in centroids:
            continue
        signals = {
            "semantic": _cosine(vectors[page_name], centroids[category_id]),
            "links": _link_signal(page, category_id, registry, pages),
            "tags": _tag_signal(page, category_id),
            "projects": _project_signal(page, category_id, registry, pages),
        }
        score = combine_signals(signals, config["signal_weights"])
        if score >= float(config["assignment_threshold"]):
            assignments.append(Assignment(category_id, score, signals, _reason(signals)))
    return sorted(assignments, key=lambda item: (-item.score, item.category_id))


def _best_existing_score(
    page_name: str,
    vectors: dict[str, np.ndarray],
    centroids: dict[str, np.ndarray],
) -> float:
    if page_name not in vectors or not centroids:
        return 0.0
    return max((_cosine(vectors[page_name], centroid) for centroid in centroids.values()), default=0.0)


def _mean_pairwise(names: list[str], vectors: dict[str, np.ndarray]) -> float:
    scores = [
        _cosine(vectors[left], vectors[right])
        for index, left in enumerate(names)
        for right in names[index + 1:]
    ]
    return float(sum(scores) / len(scores)) if scores else 0.0


def detect_forming_group(
    page_name: str,
    vectors: dict[str, np.ndarray],
    registry: Registry,
    config: dict,
) -> FormingGroup | None:
    if page_name not in vectors:
        return None
    centroids = category_centroids(registry, vectors)
    threshold = float(config["assignment_threshold"])
    novel = sorted(
        name
        for name in vectors
        if _best_existing_score(name, vectors, centroids) < threshold
    )
    if page_name not in novel:
        return None
    cohesion_threshold = float(config["forming_cohesion_threshold"])
    members = sorted(
        name
        for name in novel
        if name == page_name or _cosine(vectors[page_name], vectors[name]) >= cohesion_threshold
    )
    if len(members) < int(config["forming_min_pages"]):
        return None
    cohesion = _mean_pairwise(members, vectors)
    if cohesion < cohesion_threshold:
        return None
    return FormingGroup(members=members, cohesion=cohesion)
