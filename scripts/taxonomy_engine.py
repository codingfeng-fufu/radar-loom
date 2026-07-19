#!/usr/bin/env python3
"""Orchestrate migration, incremental classification, and global restructuring."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shlex
from dataclasses import replace
from pathlib import Path

import numpy as np

import radar_common as rc
import taxonomy_cluster as tc
import taxonomy_candidates as tcan
import taxonomy_signals as ts
from taxonomy_embeddings import (
    EmbeddingCache,
    SentenceTransformerEncoder,
    content_fingerprint,
    page_semantic_text,
)
from taxonomy_models import (
    Category,
    Candidate,
    Membership,
    Registry,
    TaxonomyRun,
    TaxonomyEvent,
    load_registry,
    new_category_id,
    parameters_hash,
    validate_registry,
    write_registry,
)
from taxonomy_naming import CommandNamer, KeywordNamer, NamingRequest, name_changed_categories


def _date(value: str | None) -> dt.date:
    if not value:
        return dt.date.today()
    return dt.date.fromisoformat(value[:10])


def global_due(registry: Registry, config: dict, now: str | dt.date) -> bool:
    if registry.changes_since_global >= int(config["global_after_changes"]):
        return True
    current = now if isinstance(now, dt.date) else _date(str(now))
    baseline = _date(registry.last_global_at or registry.generated_at)
    return (current - baseline).days >= int(config["global_after_days"])


def pathological_global_collapse(before: Registry, after: Registry) -> bool:
    before_count = sum(category.status != "merged" for category in before.categories.values())
    after_count = sum(category.status != "merged" for category in after.categories.values())
    return before_count >= 4 and after_count < max(2, (before_count + 1) // 2)


def _page_summary(page: rc.PageInfo) -> str:
    summary = str(page.frontmatter.get("summary", "")).strip()
    return summary or str(page.frontmatter.get("摘要", "")).strip()


class DeterministicTestEncoder:
    model_name = "taxonomy-test-deterministic"
    max_chars = 8192

    def encode(self, texts: list[str]) -> np.ndarray:
        import hashlib

        vectors = []
        for text in texts:
            vector = np.zeros(64, dtype=np.float32)
            tokens = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", text.casefold())
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vector[int.from_bytes(digest[:2], "big") % len(vector)] += 1.0
            if not vector.any():
                vector[0] = 1.0
            vectors.append(vector)
        return np.asarray(vectors, dtype=np.float32)


class TaxonomyEngine:
    def __init__(self, root: Path | str, config: dict, encoder=None, namer=None, profile: str = "knowledge"):
        if profile not in {"knowledge", "interview"}:
            raise ValueError("profile must be knowledge or interview")
        self.root = Path(root).resolve()
        self.config = dict(config)
        self.profile = profile
        self.registry_path = self.root / ("taxonomy.json" if profile == "knowledge" else "interview-taxonomy.json")
        self.cache_root = self.root / ".cache" / ("taxonomy" if profile == "knowledge" else "interview-taxonomy")
        self._provided_encoder = encoder
        self._provided_namer = namer

    def _scan_pages(self) -> dict[str, rc.PageInfo]:
        pages_dir = self.root / "pages"
        if not pages_dir.exists():
            raise FileNotFoundError(f"pages directory does not exist: {pages_dir}")
        paths = sorted(pages_dir.glob("*.md"))
        home = self.root / "首页.md"
        if home.exists():
            paths.append(home)
        pages = {}
        for path in paths:
            text = path.read_text(encoding="utf-8")
            frontmatter, body = rc.parse_frontmatter(text)
            kind = rc.page_type(frontmatter)
            if (self.profile == "knowledge" and kind != rc.KNOWLEDGE_PAGE_TYPE) or (self.profile == "interview" and kind != rc.INTERVIEW_PAGE_TYPE):
                continue
            pages[path.stem] = rc.PageInfo(
                name=path.stem,
                path=path,
                frontmatter=frontmatter,
                body=body,
                links=[match.strip() for match in rc.WIKILINK_RE.findall(body)],
            )
        return pages

    def _stable_path(self, page: rc.PageInfo) -> str:
        return page.path.relative_to(self.root).as_posix()

    def _existing_paths(self, pages: dict[str, rc.PageInfo]) -> set[str]:
        return {self._stable_path(page) for page in pages.values()}

    def _fingerprints(self, pages: dict[str, rc.PageInfo]) -> dict[str, str]:
        model_name = str(self.config["embedding_model"])
        return {
            self._stable_path(page): content_fingerprint(page_semantic_text(page), model_name)
            for page in pages.values()
        }

    def _encoder(self):
        if self._provided_encoder is not None:
            return self._provided_encoder
        if os.environ.get("TAXONOMY_TEST_ENCODER") == "deterministic":
            return DeterministicTestEncoder()
        return SentenceTransformerEncoder(str(self.config["embedding_model"]))

    def _namer(self, allow_llm: bool):
        if self._provided_namer is not None:
            return self._provided_namer
        command = os.environ.get("TAXONOMY_NAMER_COMMAND", "").strip()
        if allow_llm and command:
            return CommandNamer(shlex.split(command))
        return KeywordNamer()

    def migrate(self, today: str | None = None, dry_run: bool = False) -> Registry:
        timestamp = today or dt.date.today().isoformat()
        pages = self._scan_pages()
        registry = Registry.empty(parameters_hash(self.config), timestamp)
        for tag, category_id in (sorted(ts.LEGACY_TAG_TO_SEED_ID.items()) if self.profile == "knowledge" else []):
            moc_name = rc.TAG_TO_CATEGORY_PAGE[tag]
            moc = pages.get(moc_name)
            definition = str(moc.frontmatter.get("摘要", "")).strip() if moc else ""
            registry.categories[category_id] = Category(
                id=category_id,
                name=moc_name,
                definition=definition or f"历史分类标签 {tag} 的初始种子类别。",
                status="stable",
                created_at=timestamp,
                updated_at=timestamp,
                last_stable_at=timestamp,
                stable_runs=int(self.config["stable_min_runs"]),
            )
            registry.events.append(TaxonomyEvent("create", [category_id], "从历史分类标签迁移", timestamp))

        for page in pages.values():
            tags = page.frontmatter.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]
            for tag in (sorted(set(str(item) for item in tags) & set(ts.LEGACY_TAG_TO_SEED_ID)) if self.profile == "knowledge" else []):
                registry.memberships.append(
                    Membership(
                        page=self._stable_path(page),
                        category_id=ts.LEGACY_TAG_TO_SEED_ID[tag],
                        score=1.0,
                        signals={"semantic": 0.0, "links": 0.0, "tags": 1.0, "projects": 0.0},
                        reason=f"历史人工标签 {tag}",
                        first_assigned_at=timestamp,
                        last_confirmed_at=timestamp,
                    )
                )
        registry.page_fingerprints = self._fingerprints(pages)
        registry.last_global_at = timestamp
        validate_registry(registry, self._existing_paths(pages))
        if not dry_run:
            write_registry(self.registry_path, registry, self._existing_paths(pages))
        return registry

    def _vectors(self, pages: dict[str, rc.PageInfo]) -> tuple[dict[str, np.ndarray], dict[str, Exception]]:
        cache = EmbeddingCache(self.cache_root / "embeddings", self._encoder())
        vectors = {}
        failures = {}
        for name in sorted(pages):
            try:
                vectors[name] = cache.vector_for(pages[name])
            except Exception as error:  # Page-level isolation is intentional.
                failures[name] = error
        return vectors, failures

    def _category_centroids(self, registry, vectors, pages):
        grouped = {}
        for item in registry.memberships:
            name = Path(item.page).stem
            if name in vectors:
                grouped.setdefault(item.category_id, []).append(vectors[name])
        return {cid: np.mean(values, axis=0) for cid, values in grouped.items() if values}

    def _refresh_candidates(self, result, pages, vectors, timestamp):
        groups = tcan.discover_groups(
            vectors, {name: self._stable_path(page) for name, page in pages.items()},
            result.memberships, result.categories, self._category_centroids(result, vectors, pages), self.config, timestamp,
        )
        self._promote_novel_groups(result, groups, vectors, timestamp)
        result.candidates = tcan.snapshot_candidates(groups, result.candidates, self.config, timestamp)

    def _promote_novel_groups(self, result, groups, vectors, timestamp):
        minimum = int(self.config.get("forming_min_pages", 3))
        for group in groups:
            if len(group.members) < minimum:
                continue
            member_set = set(group.members)
            existing = next((cid for cid, category in result.categories.items()
                             if category.status != "merged" and {m.page for m in result.memberships if m.category_id == cid} == member_set), None)
            if existing:
                continue
            category_id = new_category_id(group.members, set(result.categories))
            result.categories[category_id] = Category(
                id=category_id, name=tcan.temporary_name(group.members),
                definition="由候选页面形成的高内聚新主题。", status="forming",
                naming_status="pending", created_at=timestamp, updated_at=timestamp,
            )
            for path in group.members:
                name = Path(path).stem
                score = float(group.cohesion_score)
                result.memberships.append(Membership(path, category_id, score, dict(group.signals),
                    f"候选群组语义内聚度 {score:.2f}", timestamp, timestamp))
            result.events.append(TaxonomyEvent("create", [category_id], "候选群组达到形成阈值", timestamp))

    def sync(
        self,
        page_paths: list[str] | None = None,
        today: str | None = None,
        allow_global: bool = True,
    ) -> Registry:
        if not self.registry_path.exists():
            return self.migrate(today=today)
        timestamp = today or dt.date.today().isoformat()
        pages = self._scan_pages()
        path_to_name = {self._stable_path(page): name for name, page in pages.items()}
        current_fingerprints = self._fingerprints(pages)
        registry = load_registry(self.registry_path)
        targets = set(path_to_name)
        if page_paths:
            targets &= {Path(path).as_posix() for path in page_paths}
        changed = sorted(
            path for path in targets
            if registry.page_fingerprints.get(path) != current_fingerprints[path]
        )
        deleted = sorted(set(registry.page_fingerprints) - set(current_fingerprints))
        if not changed and not deleted:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            if raw.get("schema_version") == 1:
                upgraded = Registry.from_dict(raw)
                upgraded.schema_version = 2
                write_registry(self.registry_path, upgraded, self._existing_paths(pages))
                return upgraded
            return registry

        result = Registry.from_dict(registry.to_dict())
        affected = set(changed) | set(deleted)
        result.memberships = [item for item in result.memberships if item.page not in affected]
        result.pending_pages = [path for path in result.pending_pages if path not in affected]
        for path in deleted:
            result.page_fingerprints.pop(path, None)
        result.changes_since_global += len(changed) + len(deleted)

        vectors: dict[str, np.ndarray] = {}
        failures: dict[str, Exception] = {}
        if changed:
            vectors, failures = self._vectors(pages)
        first_assignment = {
            (item.page, item.category_id): item.first_assigned_at
            for item in registry.memberships
        }
        for path in changed:
            name = path_to_name[path]
            result.page_fingerprints[path] = current_fingerprints[path]
            if name in failures or name not in vectors:
                result.pending_pages.append(path)
                continue
            try:
                assignments = ts.classify_page(name, vectors, result, pages, self.config)
                for assignment in assignments:
                    result.memberships.append(
                        Membership(
                            page=path,
                            category_id=assignment.category_id,
                            score=assignment.score,
                            signals=assignment.signals,
                            reason=assignment.reason,
                            first_assigned_at=first_assignment.get((path, assignment.category_id), timestamp),
                            last_confirmed_at=timestamp,
                        )
                    )
                if not assignments:
                    forming = ts.detect_forming_group(name, vectors, result, self.config)
                    if forming is not None:
                        member_paths = [self._stable_path(pages[member]) for member in forming.members]
                        category_id = new_category_id(member_paths, set(result.categories))
                        if category_id not in result.categories:
                            result.categories[category_id] = Category(
                                id=category_id,
                                name=" ".join(forming.members[:2]),
                                definition="由增量分类发现的高内聚新主题。",
                                status="forming",
                                naming_status="pending",
                                created_at=timestamp,
                                updated_at=timestamp,
                            )
                            result.events.append(
                                TaxonomyEvent("create", [category_id], "至少三个新颖页面形成高内聚群组", timestamp)
                            )
                        result.memberships = [
                            item for item in result.memberships
                            if not (item.category_id == category_id and item.page in set(member_paths))
                        ]
                        for member, member_path in zip(forming.members, member_paths, strict=True):
                            score = max(0.0, min(1.0, float(np.dot(vectors[member], vectors[name]))))
                            result.memberships.append(
                                Membership(
                                    member_path, category_id, score,
                                    {"semantic": score, "links": 0.0, "tags": 0.0, "projects": 0.0},
                                    f"与新主题代表页语义相似度 {score:.2f}", timestamp, timestamp,
                                )
                            )
                result.pending_pages = [item for item in result.pending_pages if item != path]
            except Exception:
                result.pending_pages.append(path)

        member_counts = {}
        for membership in result.memberships:
            member_counts[membership.category_id] = member_counts.get(membership.category_id, 0) + 1
        for category_id, category in list(result.categories.items()):
            if category.status == "forming" and member_counts.get(category_id, 0) == 0:
                del result.categories[category_id]
                result.events.append(TaxonomyEvent("delete", [category_id], "类别成员已为空", timestamp))

        result.pending_pages = sorted(set(result.pending_pages))
        if failures:
            result.last_run = TaxonomyRun("sync", "failed", timestamp, timestamp, "embedding failure")
        else:
            try:
                all_vectors, candidate_failures = self._vectors(pages)
                if candidate_failures:
                    raise RuntimeError("candidate embedding failure")
                old_category_ids = set(result.categories)
                self._refresh_candidates(result, pages, all_vectors, timestamp)
                outcome = "adopted" if set(result.categories) != old_category_ids else "unchanged"
                result.last_run = TaxonomyRun("sync", outcome, timestamp, timestamp, "")
            except Exception as error:
                result.last_run = TaxonomyRun("sync", "failed", timestamp, timestamp, type(error).__name__)
        result.generated_at = timestamp
        existing_paths = self._existing_paths(pages)
        write_registry(self.registry_path, result, existing_paths)
        if allow_global and global_due(result, self.config, timestamp):
            return self.global_rebuild(today=timestamp)
        return result

    def global_rebuild(self, today: str | None = None, allow_llm: bool = True) -> Registry:
        timestamp = today or dt.date.today().isoformat()
        pages = self._scan_pages()
        registry = load_registry(self.registry_path) if self.registry_path.exists() else self.migrate(timestamp)
        vectors, failures = self._vectors(pages)
        if failures:
            failed = ", ".join(sorted(failures))
            result = Registry.from_dict(registry.to_dict())
            result.last_run = TaxonomyRun("global", "failed", timestamp, timestamp, "分类数据未更新: RuntimeError")
            write_registry(self.registry_path, result, self._existing_paths(pages))
            raise RuntimeError(f"global embedding failed for: {failed}")
        edges = []
        for source, page in pages.items():
            for target in page.links:
                resolved = rc.resolve_link(target, pages)
                if resolved is not None:
                    edges.append((source, resolved))
        semantic = tc.semantic_clusters(vectors, min_cluster_size=int(self.config["forming_min_pages"]), min_samples=2)
        graph = tc.graph_clusters(edges, set(pages), seed=int(self.config["random_seed"]))
        clusters = tc.fuse_clusters(semantic, graph, vectors, edges, self.config)
        if not clusters:
            result = Registry.from_dict(registry.to_dict())
            result.generated_at = timestamp
            result.last_global_at = timestamp
            result.changes_since_global = 0
        else:
            result = tc.reconcile_clusters(
                registry,
                clusters,
                vectors,
                self.config,
                timestamp,
                page_paths={name: self._stable_path(page) for name, page in pages.items()},
            )

        if pathological_global_collapse(registry, result):
            result = Registry.from_dict(registry.to_dict())
            result.generated_at = timestamp
            result.last_global_at = timestamp
            result.changes_since_global = 0
            result.events.append(TaxonomyEvent(
                "reject",
                sorted(result.categories),
                "拒绝全局重组：候选结构丢失超过一半有效类别",
                timestamp,
            ))
            existing_paths = self._existing_paths(pages)
            try:
                self._refresh_candidates(result, pages, vectors, timestamp)
            except Exception as error:
                result.candidates = list(registry.candidates)
                result.last_run = TaxonomyRun("global", "failed", timestamp, timestamp, type(error).__name__)
            else:
                result.last_run = TaxonomyRun(
                    "global", "rejected", timestamp, timestamp,
                    "拒绝全局重组：候选结构丢失超过一半有效类别",
                )
            validate_registry(result, existing_paths)
            write_registry(self.registry_path, result, existing_paths)
            return result

        old_members = {}
        for item in registry.memberships:
            old_members.setdefault(item.category_id, set()).add(Path(item.page).stem)
        new_members = {}
        for item in result.memberships:
            new_members.setdefault(item.category_id, set()).add(Path(item.page).stem)
        requests = []
        request_ids = []
        for category_id, category in sorted(result.categories.items()):
            if category.status == "merged":
                continue
            old_category = registry.categories.get(category_id)
            before = old_members.get(category_id, set())
            after = new_members.get(category_id, set())
            union = before | after
            overlap = len(before & after) / len(union) if union else 1.0
            relations_changed = old_category is not None and (
                old_category.parents != category.parents or old_category.related != category.related
            )
            if old_category is None or overlap < float(self.config["naming_change_jaccard"]) or relations_changed:
                titles = sorted(after)[:5]
                requests.append(
                    NamingRequest(
                        category_id=category_id,
                        representative_pages=[
                            {"title": title, "summary": _page_summary(pages[title])}
                            for title in titles if title in pages
                        ],
                        keywords=titles[:3],
                        neighbor_definitions=[
                            result.categories[parent].definition
                            for parent in category.parents if parent in result.categories
                        ],
                    )
                )
                request_ids.append(category_id)
        naming_results = name_changed_categories(
            requests,
            self._namer(allow_llm),
            int(self.config["max_naming_calls"]) if allow_llm else 0,
        )
        for category_id, naming in zip(request_ids, naming_results, strict=True):
            category = result.categories[category_id]
            old_name = category.name
            result.categories[category_id] = replace(
                category,
                name=naming.name,
                definition=naming.definition,
                naming_status=naming.naming_status,
                aliases=sorted(set(category.aliases + ([old_name] if old_name != naming.name else []))),
                updated_at=timestamp,
            )
            if old_name != naming.name:
                result.events.append(TaxonomyEvent("rename", [category_id], f"{old_name} -> {naming.name}", timestamp))

        existing_paths = self._existing_paths(pages)
        try:
            self._refresh_candidates(result, pages, vectors, timestamp)
        except Exception as error:
            result.last_run = TaxonomyRun("global", "failed", timestamp, timestamp, type(error).__name__)
        validate_registry(result, existing_paths)
        write_registry(self.registry_path, result, existing_paths)
        return result

    def status(self) -> dict[str, object]:
        registry = load_registry(self.registry_path)
        seed_categories = sum(category.id.startswith("cat_seed_") and category.status != "merged" for category in registry.categories.values())
        automatic_categories = sum(not category.id.startswith("cat_seed_") and category.status != "merged" for category in registry.categories.values())
        return {
            "schema_version": registry.schema_version,
            "generated_at": registry.generated_at,
            "last_global_at": registry.last_global_at,
            "categories": len(registry.categories),
            "active_categories": sum(category.status != "merged" for category in registry.categories.values()),
            "memberships": len(registry.memberships),
            "pending_pages": len(registry.pending_pages),
            "changes_since_global": registry.changes_since_global,
            "global_due": global_due(registry, self.config, dt.date.today()),
            "seed_categories": seed_categories,
            "automatic_categories": automatic_categories,
            "candidates": len(registry.candidates),
            "candidate_updated_at": max((item.last_confirmed_at for item in registry.candidates), default=""),
            "last_run": registry.last_run.to_dict(),
        }

    def validate(self) -> None:
        pages = self._scan_pages()
        validate_registry(load_registry(self.registry_path), self._existing_paths(pages))


def load_config(root: Path | str, profile: str = "knowledge") -> dict:
    if profile not in {"knowledge", "interview"}:
        raise ValueError("profile must be knowledge or interview")
    filename = "taxonomy.json" if profile == "knowledge" else "interview-taxonomy.json"
    return json.loads((Path(root) / "config" / filename).read_text(encoding="utf-8"))
