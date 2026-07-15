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
import taxonomy_signals as ts
from taxonomy_embeddings import (
    EmbeddingCache,
    SentenceTransformerEncoder,
    content_fingerprint,
    page_semantic_text,
)
from taxonomy_models import (
    Category,
    Membership,
    Registry,
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


class DeterministicTestEncoder:
    model_name = "taxonomy-test-deterministic"
    max_chars = 8192

    def encode(self, texts: list[str]) -> np.ndarray:
        import hashlib

        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([byte + 1 for byte in digest[:16]])
        return np.asarray(vectors, dtype=np.float32)


class TaxonomyEngine:
    def __init__(self, root: Path | str, config: dict, encoder=None, namer=None):
        self.root = Path(root).resolve()
        self.config = dict(config)
        self.registry_path = self.root / "taxonomy.json"
        self.cache_root = self.root / ".cache" / "taxonomy"
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
        for tag, category_id in sorted(ts.LEGACY_TAG_TO_SEED_ID.items()):
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
            for tag in sorted(set(str(item) for item in tags) & set(ts.LEGACY_TAG_TO_SEED_ID)):
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
            result = tc.reconcile_clusters(registry, clusters, vectors, self.config, timestamp)

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
                            {"title": title, "summary": str(pages[title].frontmatter.get("摘要", ""))}
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
        validate_registry(result, existing_paths)
        write_registry(self.registry_path, result, existing_paths)
        return result

    def status(self) -> dict[str, object]:
        registry = load_registry(self.registry_path)
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
        }

    def validate(self) -> None:
        pages = self._scan_pages()
        validate_registry(load_registry(self.registry_path), self._existing_paths(pages))


def load_config(root: Path | str) -> dict:
    return json.loads((Path(root) / "config" / "taxonomy.json").read_text(encoding="utf-8"))
