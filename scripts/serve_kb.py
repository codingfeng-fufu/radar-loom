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
import sys
import tempfile
import threading
import time
from email import policy
from email.parser import BytesParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ALLOWED_ORIGIN = "http://127.0.0.1:18080"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FILENAME_BYTES = 240
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
            self.root / "interview-graph-data.json",
        )
        missing = [path.name for path in graph_outputs if not path.exists()]
        if missing:
            raise RefreshError(f"{', '.join(missing)} was not generated")
        digest = hashlib.sha256()
        for path in graph_outputs:
            digest.update(path.read_bytes())
        return digest.hexdigest()[:16]

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
            taxonomy_due = force or source_stale or now - self._last_taxonomy_check >= self.taxonomy_check_interval
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
            return {
                "mode": "global",
                "revision": self.revision(),
                "output": "\n".join(line for line in output_lines if line),
                **status,
            }


class KnowledgeRequestHandler(SimpleHTTPRequestHandler):
    builder: KnowledgeBuilder
    upload_lock = threading.Lock()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        if urlsplit(self.path).path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
        super().end_headers()

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def refresh_payload(self, force: bool) -> tuple[int, dict[str, object]]:
        try:
            result = self.builder.refresh(force=force)
        except RefreshError as error:
            return 500, {"ok": False, "error": str(error)}
        return 200, {"ok": True, **result}

    def taxonomy_allowed(self, require_origin: bool = False) -> bool:
        try:
            loopback = ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            return False
        return not require_origin or self.headers.get("Origin") == ALLOWED_ORIGIN

    def do_OPTIONS(self) -> None:
        if urlsplit(self.path).path not in {"/api/refresh", "/api/taxonomy/rebuild", "/api/uploads"}:
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
        if path == "/api/taxonomy/rebuild":
            if not self.taxonomy_allowed(require_origin=True):
                self.send_json(403, {"ok": False, "error": "localhost origin required"})
                return
            try:
                result = self.builder.taxonomy_rebuild()
            except RefreshError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
                return
            self.send_json(200, {"ok": True, **result})
            return
        if path != "/api/refresh":
            self.send_error(404)
            return
        status, payload = self.refresh_payload(force=True)
        self.send_json(status, payload)

    def handle_upload(self) -> None:
        if not self.taxonomy_allowed(require_origin=True):
            self.send_json(403, {"ok": False, "error": "localhost origin required"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
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
        for part in message.iter_parts():
            filename = part.get_filename()
            if filename is None:
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

        inbox = self.builder.root / "raw" / "inbox"
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
                        "path": f"raw/inbox/{candidate}",
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
        self.send_json(200, {"ok": True, "files": stored})

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/revision":
            status, payload = self.refresh_payload(force=False)
            payload.pop("output", None)
            self.send_json(status, payload)
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
        if path in {"/_index.md", "/_interview_index.md", "/graph-data.json", "/interview-graph-data.json"}:
            status, payload = self.refresh_payload(force=False)
            if status != 200:
                self.send_json(status, payload)
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
