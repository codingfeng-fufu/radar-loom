"""Shared request limits and syntax validators for the local HTTP service."""
from __future__ import annotations

import re

ALLOWED_ORIGIN = "http://127.0.0.1:18080"
ALLOWED_ORIGINS = frozenset({ALLOWED_ORIGIN, "http://127.0.0.1:18081", "http://127.0.0.1:49281"})
LOCAL_ORIGIN_RE = re.compile(r"^http://127\.0\.0\.1:49\d{3}$")


def is_allowed_origin(origin: str | None) -> bool:
    return bool(origin and (origin in ALLOWED_ORIGINS or LOCAL_ORIGIN_RE.fullmatch(origin)))
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


def valid_content_length(value: str | None, *, default: int = -1) -> int:
    """Parse Content-Length without allowing malformed or negative values."""
    try:
        length = int(value or "")
    except (TypeError, ValueError):
        return default
    return length if length >= 0 else default
