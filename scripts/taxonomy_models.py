#!/usr/bin/env python3
"""Data model and deterministic persistence for the evolving taxonomy."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
ALGORITHM_VERSION = "taxonomy-v1"
CATEGORY_STATUSES = {"forming", "stable", "merged"}
NAMING_STATUSES = {"ready", "pending"}
RUN_OUTCOMES = {"idle", "adopted", "unchanged", "rejected", "failed"}


class TaxonomyValidationError(ValueError):
    """Raised when a taxonomy registry cannot be published safely."""


@dataclass
class Category:
    id: str
    name: str
    definition: str
    status: str
    naming_status: str = "ready"
    parents: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    redirect_to: str | None = None
    created_at: str = ""
    updated_at: str = ""
    last_stable_at: str | None = None
    stable_runs: int = 0
    algorithm_version: str = ALGORITHM_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("parents", "related", "aliases"):
            payload[key] = sorted(set(payload[key]))
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Category":
        return cls(**payload)


@dataclass
class Membership:
    page: str
    category_id: str
    score: float
    signals: dict[str, float]
    reason: str
    first_assigned_at: str = ""
    last_confirmed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["signals"] = dict(sorted(self.signals.items()))
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Membership":
        return cls(**payload)


@dataclass
class TaxonomyEvent:
    type: str
    category_ids: list[str]
    reason: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["category_ids"] = sorted(set(self.category_ids))
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaxonomyEvent":
        return cls(**payload)


@dataclass
class Candidate:
    id: str
    name: str
    members: list[str]
    cohesion_score: float
    target_size: int
    signals: dict[str, float]
    related_category_ids: list[str]
    first_seen_at: str = ""
    last_confirmed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["members"] = sorted(set(self.members))
        payload["signals"] = dict(sorted(self.signals.items()))
        payload["related_category_ids"] = sorted(set(self.related_category_ids))
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Candidate":
        return cls(**payload)


@dataclass
class TaxonomyRun:
    operation: str = "none"
    outcome: str = "idle"
    started_at: str = ""
    finished_at: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaxonomyRun":
        return cls(**payload)


@dataclass
class Registry:
    schema_version: int
    generated_at: str
    algorithm_version: str
    parameters_hash: str
    categories: dict[str, Category]
    memberships: list[Membership]
    events: list[TaxonomyEvent]
    page_fingerprints: dict[str, str]
    pending_pages: list[str]
    changes_since_global: int
    last_global_at: str | None
    candidates: list[Candidate] = field(default_factory=list)
    last_run: TaxonomyRun = field(default_factory=TaxonomyRun)

    @classmethod
    def empty(cls, parameters_hash: str, now: str) -> "Registry":
        return cls(
            schema_version=SCHEMA_VERSION,
            generated_at=now,
            algorithm_version=ALGORITHM_VERSION,
            parameters_hash=parameters_hash,
            categories={},
            memberships=[],
            events=[],
            page_fingerprints={},
            pending_pages=[],
            changes_since_global=0,
            last_global_at=None,
            candidates=[],
            last_run=TaxonomyRun(),
        )

    def to_dict(self) -> dict[str, Any]:
        categories = {
            category_id: self.categories[category_id].to_dict()
            for category_id in sorted(self.categories)
        }
        memberships = sorted(
            (item.to_dict() for item in self.memberships),
            key=lambda item: (item["page"], item["category_id"]),
        )
        events = sorted(
            (item.to_dict() for item in self.events),
            key=lambda item: (item["created_at"], item["type"], item["category_ids"]),
        )
        candidates = sorted(
            (item.to_dict() for item in self.candidates),
            key=lambda item: item["id"],
        )
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "algorithm_version": self.algorithm_version,
            "parameters_hash": self.parameters_hash,
            "categories": categories,
            "memberships": memberships,
            "events": events,
            "page_fingerprints": dict(sorted(self.page_fingerprints.items())),
            "pending_pages": sorted(set(self.pending_pages)),
            "changes_since_global": self.changes_since_global,
            "last_global_at": self.last_global_at,
            "candidates": candidates,
            "last_run": self.last_run.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Registry":
        schema_version = payload["schema_version"]
        if schema_version not in {1, SCHEMA_VERSION}:
            raise TaxonomyValidationError(f"unsupported schema_version: {schema_version}")
        return cls(
            schema_version=SCHEMA_VERSION,
            generated_at=payload["generated_at"],
            algorithm_version=payload["algorithm_version"],
            parameters_hash=payload["parameters_hash"],
            categories={
                key: Category.from_dict(value)
                for key, value in payload.get("categories", {}).items()
            },
            memberships=[Membership.from_dict(item) for item in payload.get("memberships", [])],
            events=[TaxonomyEvent.from_dict(item) for item in payload.get("events", [])],
            page_fingerprints=dict(payload.get("page_fingerprints", {})),
            pending_pages=list(payload.get("pending_pages", [])),
            changes_since_global=int(payload.get("changes_since_global", 0)),
            last_global_at=payload.get("last_global_at"),
            candidates=[Candidate.from_dict(item) for item in payload.get("candidates", [])],
            last_run=TaxonomyRun.from_dict(payload.get("last_run", {})),
        )


def parameters_hash(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def new_category_id(member_paths: list[str], occupied_ids: set[str]) -> str:
    canonical = "\n".join(sorted(set(member_paths))).encode("utf-8")
    base = f"cat_{hashlib.sha256(canonical).hexdigest()[:12]}"
    if base not in occupied_ids:
        return base
    suffix = 2
    while f"{base}_{suffix}" in occupied_ids:
        suffix += 1
    return f"{base}_{suffix}"


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        path.append(node)
        for neighbor in graph.get(node, []):
            cycle = visit(neighbor)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def validate_registry(registry: Registry, existing_pages: set[str]) -> None:
    errors: list[str] = []
    if registry.schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if registry.changes_since_global < 0:
        errors.append("changes_since_global must be non-negative")

    category_ids = set(registry.categories)
    for key, category in registry.categories.items():
        if category.id != key:
            errors.append(f"category key/id mismatch: {key}/{category.id}")
        if category.status not in CATEGORY_STATUSES:
            errors.append(f"invalid category status: {category.status}")
        if category.naming_status not in NAMING_STATUSES:
            errors.append(f"invalid naming status: {category.naming_status}")
        for relation_name, relation_ids in (("parent", category.parents), ("related", category.related)):
            for target in relation_ids:
                if target not in category_ids:
                    errors.append(f"dangling {relation_name}: {category.id} -> {target}")
                if target == category.id:
                    errors.append(f"self {relation_name}: {category.id}")
        for target in category.related:
            if target in registry.categories and category.id not in registry.categories[target].related:
                errors.append(f"related relation is not symmetric: {category.id} -> {target}")
        if category.redirect_to is not None:
            if category.redirect_to not in category_ids:
                errors.append(f"dangling redirect: {category.id} -> {category.redirect_to}")
            if category.redirect_to == category.id:
                errors.append(f"self redirect: {category.id}")
        if category.status == "merged" and not category.redirect_to:
            errors.append(f"merged category lacks redirect: {category.id}")
        if category.status != "merged" and category.redirect_to:
            errors.append(f"active category has redirect: {category.id}")

    parent_cycle = _find_cycle({key: list(value.parents) for key, value in registry.categories.items()})
    if parent_cycle:
        errors.append(f"parent cycle: {' -> '.join(parent_cycle)}")
    redirect_cycle = _find_cycle(
        {
            key: [value.redirect_to] if value.redirect_to else []
            for key, value in registry.categories.items()
        }
    )
    if redirect_cycle:
        errors.append(f"redirect cycle: {' -> '.join(redirect_cycle)}")

    membership_keys: set[tuple[str, str]] = set()
    for membership in registry.memberships:
        key = (membership.page, membership.category_id)
        if key in membership_keys:
            errors.append(f"duplicate membership: {membership.page} -> {membership.category_id}")
        membership_keys.add(key)
        if membership.page not in existing_pages:
            errors.append(f"dangling page membership: {membership.page}")
        if membership.category_id not in category_ids:
            errors.append(f"dangling category membership: {membership.category_id}")
        if not math.isfinite(membership.score) or not 0.0 <= membership.score <= 1.0:
            errors.append(f"invalid score: {membership.page} -> {membership.category_id}")
        for signal, score in membership.signals.items():
            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                errors.append(f"invalid signal score {signal}: {membership.page}")

    candidate_ids: set[str] = set()
    for candidate in registry.candidates:
        if not candidate.id:
            errors.append("candidate id must be nonempty")
        elif candidate.id in candidate_ids:
            errors.append(f"duplicate candidate id: {candidate.id}")
        candidate_ids.add(candidate.id)
        if len(candidate.members) != len(set(candidate.members)):
            errors.append(f"candidate has duplicate page members: {candidate.id}")
        if len(candidate.members) < 2:
            errors.append(f"candidate must have at least 2 page members: {candidate.id}")
        for page in candidate.members:
            if page not in existing_pages:
                errors.append(f"candidate has dangling page: {candidate.id} -> {page}")
        if candidate.target_size < 3:
            errors.append(f"candidate target_size must be at least 3: {candidate.id}")
        if not math.isfinite(candidate.cohesion_score) or not 0.0 <= candidate.cohesion_score <= 1.0:
            errors.append(f"candidate cohesion score is invalid: {candidate.id}")
        for signal, score in candidate.signals.items():
            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                errors.append(f"candidate signal score {signal} is invalid: {candidate.id}")
        if len(candidate.related_category_ids) != len(set(candidate.related_category_ids)):
            errors.append(f"candidate related categories must be unique: {candidate.id}")
        for category_id in candidate.related_category_ids:
            if category_id not in category_ids:
                errors.append(f"candidate related category is dangling: {candidate.id} -> {category_id}")

    if registry.last_run.outcome not in RUN_OUTCOMES:
        errors.append(f"invalid last_run outcome: {registry.last_run.outcome}")

    for page in registry.page_fingerprints:
        if page not in existing_pages:
            errors.append(f"dangling page fingerprint: {page}")
    for page in registry.pending_pages:
        if page not in existing_pages:
            errors.append(f"dangling pending page: {page}")
    if errors:
        raise TaxonomyValidationError("; ".join(errors))


def load_registry(path: Path | str) -> Registry:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return Registry.from_dict(payload)


def write_registry(path: Path | str, registry: Registry, existing_pages: set[str]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    validate_registry(registry, existing_pages)
    encoded = (json.dumps(registry.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        validate_registry(load_registry(temp_path), existing_pages)
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
