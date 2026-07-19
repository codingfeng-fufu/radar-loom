#!/usr/bin/env python3
"""Discover small, local taxonomy candidates without changing the taxonomy."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from taxonomy_models import Candidate


@dataclass
class NovelGroup:
    members: list[str]
    cohesion_score: float
    related_category_ids: list[str]
    temporary_name: str
    first_seen_at: str


def candidate_id(member_paths: list[str]) -> str:
    canonical = "\n".join(sorted(set(member_paths))).encode("utf-8")
    return "cand_" + hashlib.sha256(canonical).hexdigest()[:12]


def temporary_name(page_names: list[str]) -> str:
    words = sorted({str(name).replace("_", " ").replace("-", " ").split()[0] for name in page_names if str(name).strip()})
    label = " / ".join(words) if words else "待命名候选"
    return label[:12]


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
        groups.append(NovelGroup(paths, cohesion, sorted(related), temporary_name(paths), today))
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
        result.append(Candidate(cid, group.temporary_name, sorted(group.members), group.cohesion_score, minimum, {"cohesion": group.cohesion_score}, group.related_category_ids, prior.first_seen_at if prior else group.first_seen_at, today))
    return sorted(result, key=lambda item: item.id)
