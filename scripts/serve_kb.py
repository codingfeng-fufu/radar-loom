#!/usr/bin/env python3
"""Serve the knowledge base and keep generated index/graph files fresh."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import subprocess
import shutil
import io
import zipfile
import sys
import tempfile
import threading
import time
from email import policy
from email.parser import BytesParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from search_service import search_payload
from catalog_service import catalog_payload, paper_notes_payload


def page_history_payload(root: Path, file: str, old: str = '', new: str = 'HEAD') -> dict[str, object]:
    if not file or file.startswith('/') or '..' in Path(file).parts or not file.endswith('.md'):
        raise ValueError('invalid page path')
    target = root / file
    if not target.is_file() or file not in {f'pages/{p.name}' for p in (root / 'pages').glob('*.md')}:
        raise FileNotFoundError(file)
    log = subprocess.run(['git', '-C', str(root), 'log', '--format=%H%x09%ad%x09%s', '--date=iso', '-20', '--', file], capture_output=True, text=True, check=False)
    commits = []
    for line in log.stdout.splitlines():
        parts = line.split('\t', 2)
        if len(parts) == 3:
            commits.append({'id': parts[0], 'date': parts[1], 'subject': parts[2]})
    diff = ''
    if old:
        completed = subprocess.run(['git', '-C', str(root), 'diff', '--no-ext-diff', '--unified=3', old, new, '--', file], capture_output=True, text=True, check=False)
        diff = completed.stdout
    return {'version': 1, 'file': file, 'commits': commits, 'old': old or None, 'new': new, 'diff': diff}


def duplicate_payload(root: Path, threshold: float = 0.86) -> dict[str, object]:
    pages = []
    for path in sorted((root / 'pages').glob('*.md')):
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        normalized = re.sub(r'\s+', ' ', text.lower())
        pages.append((path, normalized))
    pairs = []
    for index, (left, left_text) in enumerate(pages):
        for right, right_text in pages[index + 1:]:
            score = difflib.SequenceMatcher(None, left_text, right_text).ratio()
            title_score = difflib.SequenceMatcher(None, left.stem.lower(), right.stem.lower()).ratio()
            score = max(score, title_score * 0.92)
            if score >= threshold:
                pairs.append({'left': f'pages/{left.name}', 'right': f'pages/{right.name}', 'score': round(score, 3)})
    pairs.sort(key=lambda item: item['score'], reverse=True)
    return {'version': 1, 'threshold': threshold, 'pairs': pairs[:200]}


def merge_preview(root: Path, left: str, right: str) -> dict[str, object]:
    def read(file):
        if not file.startswith('pages/') or '..' in Path(file).parts:
            raise ValueError('invalid page path')
        return (root / file).read_text(encoding='utf-8').splitlines()
    import difflib as _difflib
    left_lines, right_lines = read(left), read(right)
    return {'version': 1, 'left': left, 'right': right, 'diff': ''.join(_difflib.unified_diff(left_lines, right_lines, fromfile=left, tofile=right, lineterm='\n')), 'manualReviewRequired': True}


def git_changes(root: Path, base: str = '') -> dict[str, object]:
    command = ['git', '-C', str(root), 'diff', '--stat', '--name-status']
    if base:
        command.insert(5, base)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    changes = []
    for line in completed.stdout.splitlines():
        parts = line.split('\t', 1)
        if len(parts) == 2:
            changes.append({'status': parts[0], 'file': parts[1]})
    return {'version': 1, 'base': base or None, 'changes': changes, 'count': len(changes)}


def export_archive(root: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for pattern in ('pages/*.md', '*.md', 'graph-data.json', 'community-data.json', 'interview-graph-data.json', 'config/*.json'):
            for path in root.glob(pattern):
                if path.is_file() and '.trash' not in path.parts:
                    archive.write(path, path.relative_to(root).as_posix())
        archive.writestr('manifest.json', json.dumps({'version': 1, 'createdAt': time.time()}, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def health_summary(root: Path, builder: 'KnowledgeBuilder') -> dict[str, object]:
    pages = list((root / 'pages').glob('*.md'))
    try:
        status = subprocess.run(['git', '-C', str(root), 'status', '--short'], capture_output=True, text=True, check=False)
        dirty = bool(status.stdout.strip())
    except OSError:
        dirty = None
    stats = builder.graph_stats()
    return {'version': 1, 'time': time.time(), 'pages': len(pages), 'nodes': stats['nodes'], 'edges': stats['edges'], 'revision': builder.revision(), 'gitDirty': dirty, 'stale': builder.is_stale()}


def quality_issues(root: Path) -> dict[str, object]:
    pages = sorted((root / 'pages').glob('*.md'))
    known = {path.stem for path in pages}
    issues = []
    referenced = set()
    for path in pages:
        text = path.read_text(encoding='utf-8', errors='replace')
        metadata = re.search(r'\A---\s*\n(.*?)\n---', text, re.DOTALL)
        front = metadata.group(1) if metadata else ''
        missing = [field for field, pattern in (('摘要', r'(?m)^(?:摘要|summary):\s*\S'), ('来源', r'(?m)^(?:来源|source):\s*\S'), ('信度', r'(?m)^(?:信度|confidence):\s*\S'), ('标签', r'(?m)^tags:\s*\S')) if not re.search(pattern, front)]
        links = [target.strip() for target in re.findall(r'\[\[([^\]|]+)', text)]
        referenced.update(links)
        broken = [target for target in links if target not in known]
        if missing or broken:
            issues.append({'file': f'pages/{path.name}', 'severity': 'error' if (missing or broken) else 'warning', 'missing': missing, 'broken': broken})
    excluded_orphans = {'首页.md'}
    orphaned = [f'pages/{path.name}' for path in pages if path.stem not in referenced and path.name not in excluded_orphans]
    issues.extend({'file': file, 'severity': 'warning', 'missing': [], 'broken': [], 'reason': '孤立节点'} for file in orphaned)
    return {'version': 2, 'issues': issues, 'orphaned': orphaned, 'counts': {'pages': len(pages), 'issues': len(issues), 'errors': sum(1 for i in issues if i.get('severity') == 'error'), 'warnings': sum(1 for i in issues if i.get('severity') == 'warning'), 'orphaned': len(orphaned)}}


ALLOWED_ORIGIN = "http://127.0.0.1:18080"
ALLOWED_ORIGINS = frozenset({ALLOWED_ORIGIN, "http://127.0.0.1:18081"})
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FILENAME_BYTES = 240
MAX_IDEA_REQUEST_BYTES = 64 * 1024
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
UPLOAD_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


MIME_TYPE_RE = re.compile(
    r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+/[!#$%&'*+.^_`|~0-9A-Za-z-]+(?:\s*;.*)?$"
)
MULTIPART_BOUNDARY_RE = re.compile(r"^[0-9A-Za-z'()+_,./:=?-]{1,70}$")


class RefreshError(RuntimeError):
    """Raised when a generated knowledge-base artifact cannot be refreshed."""


class KnowledgeBuilder:
    def __init__(self, root: Path | str, timeout: int = 30, clock=None):
        self.root = Path(root).resolve()
        self.timeout = timeout
        self._clock = clock or time.monotonic
        self._last_taxonomy_check = float("-inf")
        self._lock = threading.Lock()
        self._taxonomy_script = self.root / "scripts" / "taxonomy_cli.py"
        self._scripts = (
            self.root / "scripts" / "build_index.py",
            self.root / "scripts" / "render_graph.py",
        )
        self._outputs = (
            self.root / "_index.md",
            self.root / "_interview_index.md",
            self.root / "graph-data.json",
            self.root / "community-data.json",
            self.root / "interview-graph-data.json",
        )
        self.taxonomy_check_interval = 60
        self.taxonomy_timeout = 900
        config_path = self.root / "config" / "taxonomy.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                self.taxonomy_check_interval = int(config.get("due_check_seconds", 60))
                self.taxonomy_timeout = int(config.get("command_timeout_seconds", 900))
            except (OSError, ValueError, json.JSONDecodeError):
                pass

    def source_paths(self) -> list[Path]:
        pages = self.root / "pages"
        paths = [pages] if pages.exists() else []
        paths.extend(sorted(pages.glob("*.md")))
        home = self.root / "首页.md"
        if home.exists():
            paths.append(home)
        for path in (
            self.root / "config" / "taxonomy.json",
            self.root / "taxonomy.json",
            self.root / "config" / "interview-taxonomy.json",
            self.root / "interview-taxonomy.json",
        ):
            if path.exists():
                paths.append(path)
        return paths

    def is_stale(self) -> bool:
        if any(not output.exists() for output in self._outputs):
            return True
        sources = self.source_paths()
        if not sources:
            return False
        newest_source = max(path.stat().st_mtime_ns for path in sources)
        oldest_output = min(path.stat().st_mtime_ns for path in self._outputs)
        return newest_source > oldest_output

    def revision(self) -> str:
        graph_outputs = (
            self.root / "graph-data.json",
            self.root / "community-data.json",
            self.root / "interview-graph-data.json",
        )
        missing = [path.name for path in graph_outputs if not path.exists()]
        if missing:
            raise RefreshError(f"{', '.join(missing)} was not generated")
        digest = hashlib.sha256()
        for path in graph_outputs:
            digest.update(path.read_bytes())
        return digest.hexdigest()[:16]

    def graph_stats(self) -> dict[str, int]:
        try:
            payload = json.loads((self.root / "graph-data.json").read_text(encoding="utf-8"))
            stats = payload.get("stats", {})
            nodes = int(stats.get("nodes", 0))
            edges = int(stats.get("edges", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise RefreshError("graph-data.json stats are unavailable") from error
        if nodes < 0 or edges < 0:
            raise RefreshError("graph-data.json stats are invalid")
        return {"nodes": nodes, "edges": edges}

    def _run_script(self, script: Path, *args: str, timeout: int | None = None) -> str:
        if not script.exists():
            raise RefreshError(f"missing generator: {script.relative_to(self.root)}")
        try:
            completed = subprocess.run(
                [sys.executable, str(script), *args],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            limit = timeout or self.timeout
            raise RefreshError(f"{script.name} timed out after {limit}s") from error
        combined = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
        if completed.returncode != 0:
            detail = combined or f"exit status {completed.returncode}"
            raise RefreshError(f"{script.name}: {detail}")
        return combined

    def _run_generators(self) -> list[str]:
        output_lines = []
        for script in self._scripts:
            combined = self._run_script(script)
            if combined:
                output_lines.append(combined)
        return output_lines

    def refresh(self, force: bool = False) -> dict[str, object]:
        with self._lock:
            source_stale = self.is_stale()
            now = self._clock()
            # Avoid blocking the first revision request when generated artifacts are already fresh.
            # Source changes and subsequent periodic checks still trigger taxonomy synchronization.
            taxonomy_due = (
                force
                or source_stale
                or (
                    self._last_taxonomy_check != float("-inf")
                    and now - self._last_taxonomy_check >= self.taxonomy_check_interval
                )
            )
            output_lines = []
            if taxonomy_due:
                for args in (("sync",), ("--profile", "interview", "sync")):
                    try:
                        combined = self._run_script(
                            self._taxonomy_script, *args, timeout=self.taxonomy_timeout
                        )
                        if combined:
                            output_lines.append(combined)
                    except RefreshError as error:
                        output_lines.append(str(error))
                self._last_taxonomy_check = now

            if not force and not self.is_stale():
                return {
                    "rebuilt": False,
                    "revision": self.revision(),
                    "output": "\n".join(output_lines),
                }

            output_lines.extend(self._run_generators())
            return {
                "rebuilt": True,
                "revision": self.revision(),
                "output": "\n".join(output_lines),
            }

    def taxonomy_status(self) -> dict[str, object]:
        with self._lock:
            output = self._run_script(
                self._taxonomy_script, "status", "--json", timeout=self.taxonomy_timeout
            )
            try:
                payload = json.loads(output)
            except json.JSONDecodeError as error:
                raise RefreshError("taxonomy status returned invalid JSON") from error
            if not isinstance(payload, dict):
                raise RefreshError("taxonomy status must be a JSON object")
            return payload

    def taxonomy_rebuild(self) -> dict[str, object]:
        with self._lock:
            output_lines = [
                self._run_script(
                    self._taxonomy_script, "global", timeout=self.taxonomy_timeout
                )
            ]
            output_lines.extend(self._run_generators())
            self._last_taxonomy_check = self._clock()
            status_output = self._run_script(
                self._taxonomy_script, "status", "--json", timeout=self.taxonomy_timeout
            )
            try:
                status = json.loads(status_output)
            except json.JSONDecodeError as error:
                raise RefreshError("taxonomy status returned invalid JSON") from error
            outcome = status.get("last_run", {}).get("status", status.get("last_run", {}).get("outcome", "unknown"))
            reason = status.get("last_run", {}).get("reason", "")
            return {
                "mode": "global",
                "outcome": outcome,
                "reason": reason,
                "revision": self.revision(),
                "status": status,
                "output": "\n".join(line for line in output_lines if line),
            }


class KnowledgeRequestHandler(SimpleHTTPRequestHandler):
    builder: KnowledgeBuilder
    upload_lock = threading.Lock()
    idea_lock = threading.Lock()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        request_path = urlsplit(self.path).path
        if request_path.startswith("/api/") or request_path in {"/_index.md", "/_interview_index.md"}:
            origin = self.headers.get("Origin")
            self.send_header(
                "Access-Control-Allow-Origin",
                origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGIN,
            )
            self.send_header("Vary", "Origin")
        super().end_headers()

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, status: int, body: bytes, content_type: str, filename: str = '') -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def refresh_payload(self, force: bool) -> tuple[int, dict[str, object]]:
        try:
            result = self.builder.refresh(force=force)
        except RefreshError as error:
            payload = {"ok": False, "error": str(error)}
            if force:
                payload.update({"version": 1, "operation": "knowledge-refresh"})
            return 500, payload
        payload = {"ok": True, **result}
        if force:
            payload.update({"version": 1, "operation": "knowledge-refresh", "stats": self.builder.graph_stats()})
        return 200, payload

    def taxonomy_allowed(self, require_origin: bool = False) -> bool:
        try:
            loopback = ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            return False
        return not require_origin or self.headers.get("Origin") in ALLOWED_ORIGINS

    def content_length(self, default: int = -1) -> int:
        try:
            return int(self.headers.get("Content-Length", ""))
        except ValueError:
            return default

    def do_OPTIONS(self) -> None:
        if urlsplit(self.path).path not in {"/api/refresh", "/api/taxonomy/rebuild", "/api/uploads", "/api/ideas", "/api/pages/trash", "/api/pages/restore", "/api/import"}:
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/uploads":
            self.handle_upload()
            return
        if path == "/api/ideas":
            self.handle_idea_capture()
            return
        if path in {"/api/pages/trash", "/api/pages/restore"}:
            self.handle_page_lifecycle(path)
            return
        if path == "/api/import":
            self.handle_archive_import()
            return
        if path == "/api/taxonomy/rebuild":
            if not self.taxonomy_allowed(require_origin=True):
                self.send_json(403, {"ok": False, "error": "localhost origin required"})
                return
            try:
                result = self.builder.taxonomy_rebuild()
            except RefreshError:
                self.send_json(500, {"version": 1, "operation": "taxonomy-rebuild", "ok": False, "error": "taxonomy rebuild failed"})
                return
            self.send_json(200, {"version": 1, "operation": "taxonomy-rebuild", "ok": True, "stats": self.builder.graph_stats(), **result})
            return
        if path != "/api/refresh":
            self.send_error(404)
            return
        status, payload = self.refresh_payload(force=True)
        self.send_json(status, payload)

    def handle_idea_capture(self) -> None:
        if not self.taxonomy_allowed(require_origin=True):
            self.send_json(403, {"ok": False, "error": "localhost origin required"})
            return
        length = self.content_length()
        if length < 1:
            self.send_json(400, {"ok": False, "error": "valid Content-Length required"})
            return
        if length > MAX_IDEA_REQUEST_BYTES:
            self.send_json(413, {"ok": False, "error": "idea request exceeds 64 KiB"})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"ok": False, "error": "application/json required"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, {"ok": False, "error": "invalid JSON body"})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"ok": False, "error": "JSON object required"})
            return
        idea = payload.get("idea")
        title = payload.get("title", "")
        problem = payload.get("problem", "")
        domains = payload.get("domains", [])
        if not isinstance(idea, str) or not idea.strip() or len(idea) > 10000:
            self.send_json(400, {"ok": False, "error": "idea must be 1-10000 characters"})
            return
        if not isinstance(title, str) or len(title) > 120 or not isinstance(problem, str) or len(problem) > 2000:
            self.send_json(400, {"ok": False, "error": "invalid title or problem"})
            return
        if not isinstance(domains, list) or len(domains) > 20 or any(not isinstance(item, str) or not item.strip() or len(item) > 80 for item in domains):
            self.send_json(400, {"ok": False, "error": "domains must be a short string list"})
            return
        scripts = self.builder.root / "ideas" / "scripts"
        command = [sys.executable, str(scripts / "new_idea.py"), idea.strip()]
        if title.strip():
            command.extend(["--title", title.strip()])
        if problem.strip():
            command.extend(["--problem", problem.strip()])
        if domains:
            command.extend(["--domains", ",".join(item.strip() for item in domains)])
        try:
            with self.idea_lock:
                created = subprocess.run(command, cwd=self.builder.root, text=True, capture_output=True, timeout=10, check=True)
                for script in ("build_idea_index.py", "render_idea_graph.py"):
                    subprocess.run([sys.executable, str(scripts / script)], cwd=self.builder.root, text=True, capture_output=True, timeout=10, check=True)
        except (OSError, subprocess.SubprocessError) as error:
            detail = getattr(error, "stderr", "") or str(error)
            self.send_json(500, {"ok": False, "error": f"idea capture failed: {detail.strip()[:1000]}"})
            return
        match = re.search(r"已创建\s+(.+\.md)", created.stdout)
        relative = match.group(1) if match else ""
        self.send_json(201, {"ok": True, "file": relative, "message": "Idea 已保存"})

    def handle_upload(self) -> None:
        if not self.taxonomy_allowed(require_origin=True):
            self.send_json(403, {"ok": False, "error": "localhost origin required"})
            return
        length = self.content_length()
        if length < 0:
            self.send_json(400, {"ok": False, "error": "valid Content-Length required"})
            return
        if length > MAX_UPLOAD_BYTES:
            self.send_json(413, {"ok": False, "error": "request exceeds 20 MiB"})
            return
        content_type = self.headers.get("Content-Type", "")
        try:
            content_type_bytes = content_type.encode("ascii")
        except UnicodeEncodeError:
            self.send_json(400, {"ok": False, "error": "invalid multipart Content-Type"})
            return
        header_message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + content_type_bytes + b"\r\n\r\n"
        )
        content_type_header = header_message["Content-Type"]
        boundary = header_message.get_boundary()
        if (
            header_message.get_content_type() != "multipart/form-data"
            or content_type_header is None
            or getattr(content_type_header, "defects", ())
            or boundary is None
            or not MULTIPART_BOUNDARY_RE.fullmatch(boundary)
        ):
            self.send_json(400, {"ok": False, "error": "invalid multipart Content-Type"})
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self.send_json(400, {"ok": False, "error": "incomplete request body"})
            return
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + content_type_bytes + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
        )
        if not message.is_multipart() or message.defects:
            self.send_json(400, {"ok": False, "error": "malformed multipart body"})
            return

        validated = []
        destination = "inbox"
        for part in message.iter_parts():
            filename = part.get_filename()
            if filename is None:
                if part.get_param("name", header="Content-Disposition") == "destination":
                    value = part.get_content().strip()
                    if value not in {"inbox", "papers"}:
                        self.send_json(400, {"ok": False, "error": "invalid upload destination"})
                        return
                    destination = value
                continue
            if (
                not filename
                or Path(filename).name != filename
                or "/" in filename
                or "\\" in filename
                or any(ord(character) < 32 or ord(character) == 127 for character in filename)
            ):
                self.send_json(400, {"ok": False, "error": "invalid filename"})
                return
            try:
                filename_size = len(filename.encode("utf-8"))
            except UnicodeEncodeError:
                self.send_json(400, {"ok": False, "error": "invalid filename"})
                return
            if filename_size > MAX_FILENAME_BYTES:
                self.send_json(
                    400,
                    {"ok": False, "error": "filename exceeds 240 UTF-8 bytes"},
                )
                return
            extension = Path(filename).suffix.lower()
            expected_mime = UPLOAD_TYPES.get(extension)
            content_type_headers = part.get_all("Content-Type", [])
            content_type_header = content_type_headers[0] if len(content_type_headers) == 1 else None
            if (
                content_type_header is None
                or getattr(content_type_header, "defects", ())
                or not MIME_TYPE_RE.fullmatch(str(content_type_header).strip())
            ):
                self.send_json(415, {"ok": False, "error": "valid file Content-Type required"})
                return
            actual_mime = part.get_content_type().lower()
            if expected_mime is None or actual_mime != expected_mime:
                self.send_json(415, {"ok": False, "error": "unsupported file type"})
                return
            content = part.get_payload(decode=True)
            if content is None:
                self.send_json(400, {"ok": False, "error": "malformed file content"})
                return
            if not content:
                self.send_json(400, {"ok": False, "error": "empty files are not allowed"})
                return
            if len(content) > MAX_UPLOAD_BYTES:
                self.send_json(413, {"ok": False, "error": "file exceeds 20 MiB"})
                return
            validated.append((filename, content))
        if not validated:
            self.send_json(400, {"ok": False, "error": "at least one file is required"})
            return

        inbox = self.builder.root / ("papers" if destination == "papers" else "raw/inbox")
        relative_root = "papers" if destination == "papers" else "raw/inbox"
        stored = []
        temp_paths = []
        final_paths = []
        try:
            with self.upload_lock:
                inbox.mkdir(parents=True, exist_ok=True)
                reserved = {path.name for path in inbox.iterdir()}
                planned = []
                for filename, content in validated:
                    candidate = filename
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    number = 2
                    while candidate in reserved:
                        candidate = f"{stem}-{number}{suffix}"
                        number += 1
                    reserved.add(candidate)
                    planned.append((candidate, content))
                for candidate, content in planned:
                    descriptor, temp_name = tempfile.mkstemp(prefix=".upload-", dir=inbox)
                    temp_path = Path(temp_name)
                    temp_paths.append(temp_path)
                    with os.fdopen(descriptor, "wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                for (candidate, content), temp_path in zip(planned, temp_paths):
                    final_path = inbox / candidate
                    os.replace(temp_path, final_path)
                    final_paths.append(final_path)
                    stored.append({
                        "name": candidate,
                        "path": f"{relative_root}/{candidate}",
                        "size": len(content),
                    })
        except OSError as error:
            for path in temp_paths + final_paths:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            self.send_json(500, {"ok": False, "error": f"upload failed: {error}"})
            return
        self.send_json(200, {
            "ok": True,
            "paths": [item["path"] for item in stored],
            "files": stored,
        })

    def handle_page_lifecycle(self, path: str) -> None:
        if not self.taxonomy_allowed(require_origin=True):
            self.send_json(403, {"ok": False, "error": "localhost origin required"})
            return
        try:
            length = self.content_length(0)
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            file = payload.get("file", "")
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, {"ok": False, "error": "valid JSON body required"})
            return
        if not isinstance(file, str) or not file.startswith("pages/") or Path(file).name != file[6:] or ".." in Path(file).parts or not file.endswith(".md"):
            self.send_json(400, {"ok": False, "error": "only pages/*.md is supported"})
            return
        source = self.builder.root / file
        trash = self.builder.root / ".trash" / "pages" / Path(file).name
        metadata_path = self.builder.root / ".trash" / "manifest.json"
        try:
            manifest = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            manifest = {}
        try:
            if path.endswith("trash"):
                if not source.is_file():
                    self.send_json(404, {"ok": False, "error": "page not found"})
                    return
                trash.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(trash))
                manifest[file] = {"file": file, "deletedAt": time.time(), "trashPath": str(trash.relative_to(self.builder.root))}
            else:
                if not trash.is_file():
                    self.send_json(404, {"ok": False, "error": "page not found in recycle bin"})
                    return
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(trash), str(source)); manifest.pop(file, None)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as error:
            self.send_json(500, {"ok": False, "error": f"page lifecycle failed: {error}"})
            return
        self.send_json(200, {"ok": True, "file": file, "action": "trash" if path.endswith("trash") else "restore"})

    def handle_archive_import(self) -> None:
        if not self.taxonomy_allowed(require_origin=True):
            self.send_json(403, {"ok": False, "error": "localhost origin required"})
            return
        length = self.content_length(0)
        if length < 1 or length > MAX_ARCHIVE_BYTES:
            self.send_json(413, {"ok": False, "error": "archive must be between 1 byte and 100 MiB"})
            return
        if self.headers.get_content_type() != 'application/zip':
            self.send_json(415, {"ok": False, "error": "application/zip required"})
            return
        try:
            archive = zipfile.ZipFile(io.BytesIO(self.rfile.read(length)))
            allowed = ('.md', '.json', '.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.webp')
            members = [item for item in archive.infolist() if not item.is_dir()]
            forbidden = {'scripts', '.git', '.trash', 'node_modules'}
            if any(Path(item.filename).is_absolute() or '..' in Path(item.filename).parts or not item.filename.lower().endswith(allowed) or Path(item.filename).parts[0] in forbidden for item in members):
                raise ValueError('archive contains an unsafe file')
            staged = [(self.builder.root / item.filename, archive.read(item)) for item in members]
            originals = {target: target.read_bytes() for target, _ in staged if target.is_file()}
            created = []
            try:
                for target, content in staged:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp_name = tempfile.mkstemp(prefix='.restore-', dir=str(target.parent))
                    with os.fdopen(fd, 'wb') as handle:
                        handle.write(content); handle.flush(); os.fsync(handle.fileno())
                    os.replace(temp_name, target)
                    created.append(target)
            except OSError:
                for target in created:
                    if target in originals: target.write_bytes(originals[target])
                    else: target.unlink(missing_ok=True)
                raise
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            self.send_json(400, {"ok": False, "error": f"archive import failed: {error}"})
            return
        self.send_json(200, {"ok": True, "imported": len(members)})

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/paper-notes":
            try:
                self.send_json(200, paper_notes_payload(self.builder.root))
            except OSError as error:
                self.send_json(500, {"ok": False, "error": f"paper notes unavailable: {error}"})
            return
        if path == "/api/search":
            params = parse_qs(urlsplit(self.path).query)
            query = params.get("q", [""])[0]
            if not query.strip() or len(query) > 300:
                self.send_json(400, {"ok": False, "error": "q must contain 1-300 characters"})
                return
            try:
                payload = search_payload(self.builder.root, query, params.get("section", [""])[0], params.get("sort", ["relevance"])[0], int(params.get("page", ["1"])[0]), int(params.get("pageSize", ["20"])[0]))
            except (ValueError, OSError) as error:
                self.send_json(400, {"ok": False, "error": f"invalid search request: {error}"})
                return
            self.send_json(200, payload)
            return
        if path == "/api/page-history":
            params = parse_qs(urlsplit(self.path).query)
            try:
                payload = page_history_payload(self.builder.root, params.get("file", [""])[0], params.get("old", [""])[0], params.get("new", ["HEAD"])[0])
            except (ValueError, FileNotFoundError, OSError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return
            self.send_json(200, payload)
            return
        if path == "/api/pages/trash":
            manifest_path = self.builder.root / ".trash" / "manifest.json"
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                manifest = {}
            self.send_json(200, {"version": 1, "items": list(manifest.values())})
            return
        if path == "/api/duplicates":
            params = parse_qs(urlsplit(self.path).query)
            try:
                threshold = float(params.get("threshold", ["0.86"])[0])
                if not 0.5 <= threshold <= 1:
                    raise ValueError("threshold must be between 0.5 and 1")
                self.send_json(200, duplicate_payload(self.builder.root, threshold))
            except (ValueError, OSError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return
        if path == "/api/merge-preview":
            params = parse_qs(urlsplit(self.path).query)
            try:
                self.send_json(200, merge_preview(self.builder.root, params.get('left', [''])[0], params.get('right', [''])[0]))
            except (ValueError, OSError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            return
        if path == "/api/git/changes":
            params = parse_qs(urlsplit(self.path).query)
            base = params.get('base', [''])[0]
            if len(base) > 100 or any(char in base for char in '\r\n;|&'):
                self.send_json(400, {"ok": False, "error": "invalid base revision"})
                return
            self.send_json(200, git_changes(self.builder.root, base))
            return
        if path == "/api/export":
            self.send_bytes(200, export_archive(self.builder.root), 'application/zip', 'knowledge-base-export.zip')
            return
        if path == "/api/health/summary":
            try:
                self.send_json(200, health_summary(self.builder.root, self.builder))
            except (OSError, RefreshError) as error:
                self.send_json(500, {"ok": False, "error": str(error)})
            return
        if path == "/api/quality/issues":
            try:
                self.send_json(200, quality_issues(self.builder.root))
            except OSError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
            return
        if path == "/api/catalog":
            try:
                knowledge = json.loads((self.builder.root / "graph-data.json").read_text(encoding="utf-8"))
                interview = json.loads((self.builder.root / "interview-graph-data.json").read_text(encoding="utf-8"))
                self.send_json(200, catalog_payload(knowledge, interview, self.builder.root))
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(500, {"ok": False, "error": f"catalog unavailable: {error}"})
            return
        if path == "/api/revision":
            try:
                payload = {"ok": True, "revision": self.builder.revision(), "rebuilt": False}
            except RefreshError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
                return
            self.send_json(200, payload)
            return
        if path == "/api/taxonomy/status":
            if not self.taxonomy_allowed():
                self.send_json(403, {"ok": False, "error": "localhost client required"})
                return
            try:
                result = self.builder.taxonomy_status()
            except RefreshError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
                return
            self.send_json(200, {"ok": True, **result})
            return
        super().do_GET()


def create_server(
    host: str,
    port: int,
    directory: Path | str,
    builder: KnowledgeBuilder | None = None,
) -> ThreadingHTTPServer:
    root = Path(directory).resolve()
    active_builder = builder or KnowledgeBuilder(root)
    class BoundKnowledgeRequestHandler(KnowledgeRequestHandler):
        pass

    BoundKnowledgeRequestHandler.builder = active_builder
    handler = partial(BoundKnowledgeRequestHandler, directory=str(root))
    return ThreadingHTTPServer((host, port), handler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="提供知识库静态页面并自动刷新索引与图谱")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent.parent)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    server = create_server(args.host, args.port, args.directory)
    print(f"知识库服务已启动:http://{args.host}:{args.port}/viewer.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
