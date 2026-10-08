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
    parent_category_ids: list[str] = None

    def __post_init__(self):
        object.__setattr__(self, "parent_category_ids", sorted(set(self.parent_category_ids or [])))


def candidate_id(member_paths: list[str]) -> str:
    canonical = "\n".join(sorted(set(member_paths))).encode("utf-8")
    return "candidate_" + hashlib.sha256(canonical).hexdigest()[:12]


def temporary_name(page_names: list[str]) -> str:
    stems = [re.sub(r"^pages/|\.md$", "", str(name)) for name in page_names]
    cjk_parts = [re.findall(r"[\u4e00-\u9fff]+", name) for name in stems]
    frequencies = {}
    for parts in cjk_parts:
        seen = set()
        for part in parts:
            for width in range(2, min(6, len(part)) + 1):
                seen.update(part[index:index + width] for index in range(len(part) - width + 1))
        for token in seen:
            frequencies[token] = frequencies.get(token, 0) + 1
    if frequencies:
        token, count = max(frequencies.items(), key=lambda item: (item[1] * len(item[0]), item[1], len(item[0]), item[0]))
        if count >= max(2, (len(stems) + 2) // 3):
            return token
    tokens = set()
    for name in page_names:
        tokens.update(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", str(name)))
    label = " ".join(sorted(tokens)[:3]) if tokens else "新主题"
    return label if len(label) <= 12 else label[:11] + "…"


def _cosine(a, b):
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def _title_topic_overlap(left: str, right: str) -> bool:
    """Treat an explicit repeated Chinese title phrase as local evidence."""
    left_parts = re.findall(r"[\u4e00-\u9fff]{3,}", left)
    right_parts = re.findall(r"[\u4e00-\u9fff]{3,}", right)
    return any(len(part) >= 3 and part in other for part in left_parts for other in right_parts)


def discover_groups(vectors, page_paths, memberships, categories, category_centroids, config, today):
    names = sorted(vectors)
    threshold = float(config.get("candidate_cohesion_threshold", .78))
    compact_threshold = float(config.get("candidate_compact_threshold", threshold))
    minimum = int(config.get("candidate_min_pages", 2))
    maximum = int(config.get("candidate_max_pages", 15))
    path_to_name = {path: name for name, path in page_paths.items()}
    seed_members = {}
    for membership in memberships:
        if (membership.category_id.startswith("cat_seed_") and membership.page in path_to_name
                and float(membership.signals.get("tags", 0.0)) >= 0.5):
            seed_members.setdefault(membership.category_id, set()).add(path_to_name[membership.page])

    # Complete-link agglomeration prevents a chain of merely adjacent pages from
    # swallowing an entire seed category. A page may occur in several seed pools.
    raw_groups = []
    for parent_id, pool in sorted(seed_members.items()):
        clusters = [{name} for name in sorted(pool & set(names))]
        while True:
            choices = []
            for left, right in combinations(range(len(clusters)), 2):
                merged = clusters[left] | clusters[right]
                if len(merged) > maximum:
                    continue
                pair_scores = [_cosine(vectors[a], vectors[b]) for a in clusters[left] for b in clusters[right]]
                lexical = any(_title_topic_overlap(a, b) for a in clusters[left] for b in clusters[right])
                if pair_scores and (min(pair_scores) >= compact_threshold or lexical):
                    choices.append((sum(pair_scores) / len(pair_scores), left, right))
            if not choices:
                break
            _, left, right = max(choices, key=lambda item: (item[0], -item[1], -item[2]))
            clusters[left] |= clusters[right]
            del clusters[right]
        raw_groups.extend((cluster, parent_id) for cluster in clusters if len(cluster) >= minimum)

    groups = []
    for component, parent_id in raw_groups:
        paths = sorted(page_paths.get(item, item) for item in component)
        scores = [_cosine(vectors[a], vectors[b]) for a, b in combinations(sorted(component), 2)]
        cohesion = sum(scores) / len(scores) if scores else 1.0
        if cohesion < threshold:
            continue
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
        groups.append(NovelGroup(paths, cohesion, {"semantic_cohesion": cohesion}, [], [parent_id]))
    unique = {}
    for group in groups:
        key = (tuple(group.members), tuple(group.parent_category_ids))
        unique[key] = group
    return sorted(unique.values(), key=lambda group: (candidate_id(group.members), group.parent_category_ids))


def snapshot_candidates(groups, previous, config, today):
    minimum = int(config.get("forming_min_pages", 3))
    old = {item.id: item for item in previous}
    result = []
    seen_ids = set()
    for group in groups:
        if len(group.members) >= minimum:
            continue
        cid = candidate_id(group.members)
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        prior = old.get(cid)
        result.append(Candidate(cid, temporary_name(group.members), sorted(group.members), group.cohesion_score, minimum, dict(group.signals), group.related_category_ids, prior.first_seen_at if prior else today, today))
    return sorted(result, key=lambda item: item.id)
