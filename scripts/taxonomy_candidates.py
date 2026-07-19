#!/usr/bin/env python3
"""Discover small, local taxonomy candidates without changing the taxonomy."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from taxonomy_models import Candidate


@dataclass(frozen=True)
class NovelGroup:
    members: list[str]
    cohesion_score: float
    signals: dict[str, float]
    related_category_ids: list[str]


def candidate_id(member_paths: list[str]) -> str:
    canonical = "\n".join(sorted(set(member_paths))).encode("utf-8")
    return "candidate_" + hashlib.sha256(canonical).hexdigest()[:12]


def temporary_name(page_names: list[str]) -> str:
    tokens = set()
    for name in page_names:
        tokens.update(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(name)))
    label = " ".join(sorted(tokens)[:3]) if tokens else "新主题"
    return label if len(label) <= 12 else label[:11] + "…"


def _cosine(a, b):
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def discover_groups(vectors, page_paths, memberships, categories, category_centroids, config, today):
    names = sorted(vectors)
    k = int(config.get("candidate_neighborhood_k", 12))
    threshold = float(config.get("candidate_cohesion_threshold", .78))
    minimum = int(config.get("candidate_min_pages", 2))
    adjacency = {name: set() for name in names}
    for name in names:
        neighbors = sorted(((
            _cosine(vectors[name], vectors[other]), other
        ) for other in names if other != name), reverse=True)[:k]
        for score, other in neighbors:
            if score >= threshold:
                adjacency[name].add(other)
                adjacency[other].add(name)
    groups, seen = [], set()
    for name in names:
        if name in seen:
            continue
        stack, component = [name], set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current); seen.add(current); stack.extend(adjacency[current] - component)
        if len(component) < minimum:
            continue
        paths = sorted(page_paths.get(item, item) for item in component)
        scores = [_cosine(vectors[a], vectors[b]) for a, b in combinations(sorted(component), 2)]
        cohesion = sum(scores) / len(scores) if scores else 1.0
        member_set = set(paths)
        explained = False
        by_category = {}
        for membership in memberships:
            if membership.page in member_set:
                by_category.setdefault(membership.category_id, set()).add(membership.page)
        for category_id, pages in by_category.items():
            category = categories.get(category_id)
            if category and not category_id.startswith("cat_seed_") and category.status != "merged" and pages == member_set:
                explained = True
                break
        if explained:
            continue
        centroid = np.mean([vectors[item] for item in sorted(component)], axis=0)
        related = [cid for cid, cvec in category_centroids.items() if _cosine(centroid, cvec) >= float(config.get("candidate_related_threshold", .70))]
        groups.append(NovelGroup(paths, cohesion, {"semantic_cohesion": cohesion}, sorted(related)))
    return sorted(groups, key=lambda group: candidate_id(group.members))


def snapshot_candidates(groups, previous, config, today):
    minimum = int(config.get("forming_min_pages", 3))
    old = {item.id: item for item in previous}
    result = []
    for group in groups:
        if len(group.members) >= minimum:
            continue
        cid = candidate_id(group.members)
        prior = old.get(cid)
        result.append(Candidate(cid, temporary_name(group.members), sorted(group.members), group.cohesion_score, minimum, dict(group.signals), group.related_category_ids, prior.first_seen_at if prior else today, today))
    return sorted(result, key=lambda item: item.id)
