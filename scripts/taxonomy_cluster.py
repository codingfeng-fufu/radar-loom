#!/usr/bin/env python3
"""Global semantic/graph clustering and stable taxonomy reconciliation."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.cluster import HDBSCAN

from taxonomy_models import Category, Membership, Registry, TaxonomyEvent, new_category_id


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(left, right) / denominator)))


def _centroid(members: set[str], vectors: dict[str, np.ndarray]) -> np.ndarray:
    available = [np.asarray(vectors[name], dtype=np.float32) for name in sorted(members) if name in vectors]
    if not available:
        return np.zeros(1, dtype=np.float32)
    mean = np.asarray(available, dtype=np.float32).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return mean / norm if norm else mean


def _sorted_groups(groups) -> list[set[str]]:
    unique = {tuple(sorted(group)) for group in groups if group}
    return [set(group) for group in sorted(unique)]


def semantic_clusters(
    vectors: dict[str, np.ndarray],
    min_cluster_size: int = 3,
    min_samples: int = 2,
) -> list[set[str]]:
    names = sorted(vectors)
    if len(names) < min_cluster_size:
        return []
    matrix = np.asarray([vectors[name] for name in names], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("semantic clustering received a zero vector")
    matrix = matrix / norms
    labels = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        copy=True,
    ).fit_predict(matrix)
    groups: dict[int, set[str]] = defaultdict(set)
    for name, label in zip(names, labels, strict=True):
        if int(label) >= 0:
            groups[int(label)].add(name)
    return _sorted_groups(groups.values())


def graph_clusters(edges: list[tuple[str, str]], all_pages: set[str], seed: int) -> list[set[str]]:
    graph = nx.Graph()
    graph.add_nodes_from(sorted(all_pages))
    for source, target in edges:
        if source == target or source not in all_pages or target not in all_pages:
            continue
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += 1.0
        else:
            graph.add_edge(source, target, weight=1.0)
    communities = nx.algorithms.community.louvain_communities(graph, weight="weight", seed=seed)
    return _sorted_groups(communities)


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _cross_edge_density(left: set[str], right: set[str], edges: set[tuple[str, str]]) -> float:
    possible = len(left) * len(right)
    if possible == 0:
        return 0.0
    count = 0
    for source in left:
        for target in right:
            if source == target:
                continue
            pair = tuple(sorted((source, target)))
            if pair in edges:
                count += 1
    return count / possible


def fuse_clusters(
    semantic: list[set[str]],
    graph: list[set[str]],
    vectors: dict[str, np.ndarray],
    edges: list[tuple[str, str]],
    config: dict,
) -> list[set[str]]:
    candidates = [set(group) for group in semantic + graph if group]
    candidate_graph = nx.Graph()
    candidate_graph.add_nodes_from(range(len(candidates)))
    normalized_edges = {tuple(sorted(edge)) for edge in edges if edge[0] != edge[1]}
    centroids = [_centroid(group, vectors) for group in candidates]
    for left in range(len(candidates)):
        for right in range(left + 1, len(candidates)):
            overlap = _jaccard(candidates[left], candidates[right])
            semantic_score = _cosine(centroids[left], centroids[right])
            density = _cross_edge_density(candidates[left], candidates[right], normalized_edges)
            if overlap >= float(config["cluster_fusion_jaccard"]) or (
                semantic_score >= float(config["related_threshold"]) and density >= 0.15
            ):
                candidate_graph.add_edge(left, right)
    fused = []
    minimum = int(config["forming_min_pages"])
    for component in nx.connected_components(candidate_graph):
        members = set().union(*(candidates[index] for index in component))
        if len(members) >= minimum:
            fused.append(members)
    return _sorted_groups(fused)


def match_score(
    old_members: set[str],
    new_members: set[str],
    old_centroid: np.ndarray,
    new_centroid: np.ndarray,
    edge_score: float,
) -> float:
    return 0.50 * _jaccard(old_members, new_members) + 0.35 * _cosine(old_centroid, new_centroid) + 0.15 * edge_score


def _member_map(registry: Registry) -> dict[str, set[str]]:
    members: dict[str, set[str]] = defaultdict(set)
    for membership in registry.memberships:
        category = registry.categories.get(membership.category_id)
        if category is not None and category.status != "merged":
            members[membership.category_id].add(Path(membership.page).stem)
    return dict(members)


def _event(event_type: str, category_ids: list[str], reason: str, today: str) -> TaxonomyEvent:
    return TaxonomyEvent(event_type, sorted(set(category_ids)), reason, today)


def _lifecycle(category: Category, member_count: int, config: dict, today: str, events: list[TaxonomyEvent]) -> Category:
    updated = replace(category, updated_at=today, redirect_to=None)
    if updated.status == "forming":
        stable_runs = updated.stable_runs + 1
        if member_count >= int(config["stable_min_pages"]) or stable_runs >= int(config["stable_min_runs"]):
            events.append(_event("promote", [updated.id], "类别达到稳定条件", today))
            return replace(updated, status="stable", stable_runs=stable_runs, last_stable_at=today)
        return replace(updated, stable_runs=stable_runs)
    if updated.status == "stable" and member_count < int(config["forming_min_pages"]):
        events.append(_event("demote", [updated.id], "类别成员低于形成阈值", today))
        return replace(updated, status="forming", stable_runs=0)
    return updated


def reconcile_clusters(
    registry: Registry,
    clusters: list[set[str]],
    vectors: dict[str, np.ndarray],
    config: dict,
    today: str,
    page_paths: dict[str, str] | None = None,
) -> Registry:
    page_paths = page_paths or {}
    path_for = lambda name: page_paths.get(name, f"pages/{name}.md")
    result = Registry.from_dict(registry.to_dict())
    old_members = _member_map(registry)
    active_ids = sorted(old_members)
    clusters = _sorted_groups(clusters)
    old_centroids = {category_id: _centroid(old_members[category_id], vectors) for category_id in active_ids}
    new_centroids = [_centroid(cluster, vectors) for cluster in clusters]

    pairs = []
    for category_id in active_ids:
        for index, cluster in enumerate(clusters):
            score = match_score(
                old_members[category_id],
                cluster,
                old_centroids[category_id],
                new_centroids[index],
                0.0,
            )
            pairs.append((score, category_id, index))
    pairs.sort(key=lambda item: (-item[0], item[1], tuple(sorted(clusters[item[2]]))))

    matched_old: set[str] = set()
    matched_new: set[int] = set()
    new_ids: dict[int, str] = {}
    threshold = float(config["cluster_match_threshold"])
    for score, category_id, index in pairs:
        if score < threshold or category_id in matched_old or index in matched_new:
            continue
        matched_old.add(category_id)
        matched_new.add(index)
        new_ids[index] = category_id

    occupied = set(registry.categories)
    for index, cluster in enumerate(clusters):
        if index not in new_ids:
            category_id = new_category_id([path_for(name) for name in cluster], occupied)
            occupied.add(category_id)
            new_ids[index] = category_id

    categories: dict[str, Category] = {}
    events = list(result.events)
    for index, cluster in enumerate(clusters):
        category_id = new_ids[index]
        if category_id in registry.categories:
            category = _lifecycle(registry.categories[category_id], len(cluster), config, today, events)
        else:
            category = Category(
                id=category_id,
                name=f"待命名类别 {category_id.removeprefix('cat_')[:6]}",
                definition="由全局聚类自动形成，等待命名。",
                status="forming",
                naming_status="pending",
                created_at=today,
                updated_at=today,
            )
            events.append(_event("create", [category_id], "发现新的高内聚类别", today))
        categories[category_id] = category

    for old_id in active_ids:
        overlapping = [index for index, cluster in enumerate(clusters) if old_members[old_id] & cluster]
        if len(overlapping) > 1:
            events.append(
                _event(
                    "split",
                    [old_id] + [new_ids[index] for index in overlapping],
                    "原类别成员分布到多个新群组",
                    today,
                )
            )

    for old_id in sorted(set(registry.categories) - matched_old):
        old_category = registry.categories[old_id]
        if old_category.status == "merged":
            categories[old_id] = old_category
            continue
        candidates = [item for item in pairs if item[1] == old_id]
        best = candidates[0] if candidates else None
        if best and best[0] >= threshold:
            target_id = new_ids[best[2]]
            if target_id != old_id:
                categories[old_id] = replace(
                    old_category,
                    status="merged",
                    redirect_to=target_id,
                    parents=[],
                    related=[],
                    updated_at=today,
                )
                target = categories[target_id]
                categories[target_id] = replace(
                    target,
                    aliases=sorted(set(target.aliases + [old_category.name] + old_category.aliases)),
                )
                events.append(_event("merge", [old_id, target_id], "类别高度重叠并入主类别", today))
                continue
        events.append(_event("delete", [old_id], "类别未在本轮全局结构中保留", today))

    category_members = {new_ids[index]: set(cluster) for index, cluster in enumerate(clusters)}
    relation_centroids = {new_ids[index]: new_centroids[index] for index in range(len(clusters))}
    relations = infer_relations(category_members, relation_centroids, config)
    for category_id, relation in relations.items():
        categories[category_id] = replace(
            categories[category_id],
            parents=relation.parents,
            related=relation.related,
        )

    memberships = []
    for index, cluster in enumerate(clusters):
        category_id = new_ids[index]
        centroid = new_centroids[index]
        for name in sorted(cluster):
            score = _cosine(vectors[name], centroid)
            memberships.append(
                Membership(
                    page=path_for(name),
                    category_id=category_id,
                    score=score,
                    signals={"semantic": score, "links": 0.0, "tags": 0.0, "projects": 0.0},
                    reason=f"全局群组语义相似度 {score:.2f}",
                    first_assigned_at=today,
                    last_confirmed_at=today,
                )
            )

    result.categories = categories
    result.memberships = memberships
    result.events = events
    result.generated_at = today
    result.last_global_at = today
    result.changes_since_global = 0
    return result


def infer_relations(
    category_members: dict[str, set[str]],
    centroids: dict[str, np.ndarray],
    config: dict,
) -> dict[str, Category]:
    relations = {
        category_id: Category(category_id, category_id, "", "stable")
        for category_id in sorted(category_members)
    }
    containment = float(config["parent_containment_threshold"])
    candidates = []
    for child_id, child_members in category_members.items():
        for parent_id, parent_members in category_members.items():
            if child_id == parent_id or len(child_members) >= len(parent_members) or not child_members:
                continue
            score = len(child_members & parent_members) / len(child_members)
            if score >= containment:
                candidates.append((len(parent_members), parent_id, child_id))
    for _, parent_id, child_id in sorted(candidates):
        relations[child_id].parents.append(parent_id)

    parent_pairs = {
        (child_id, parent_id)
        for child_id, category in relations.items()
        for parent_id in category.parents
    }
    related_threshold = float(config["related_threshold"])
    ids = sorted(category_members)
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1:]:
            if (left_id, right_id) in parent_pairs or (right_id, left_id) in parent_pairs:
                continue
            if left_id not in centroids or right_id not in centroids:
                continue
            if _cosine(centroids[left_id], centroids[right_id]) >= related_threshold:
                relations[left_id].related.append(right_id)
                relations[right_id].related.append(left_id)
    for category in relations.values():
        category.parents = sorted(set(category.parents))
        category.related = sorted(set(category.related))
    return relations
