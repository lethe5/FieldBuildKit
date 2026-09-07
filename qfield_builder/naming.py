"""Project naming: project_display_name / project_slug / project_id (Section 6.1).

Implements FR-QPB-020/021/021a/022/022a per Decision Log D-22:

- ``project_display_name``: free-form Unicode, user-facing (never sanitized/rejected here).
- ``project_slug``: ASCII letters/digits/hyphens/underscores only, 1-64 characters, derived from
  the display name, used for generated folder/file names. Rejects blank input, path-traversal
  components/general separators, and Windows-reserved device names.
- ``project_id``: a UUID v4, independent of both names (see :func:`new_project_id`).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass

MAX_SLUG_LENGTH = 64

# Windows-reserved device names (case-insensitive), per FR-QPB-021.
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_NON_SLUG_CHARS_RE = re.compile(r"[^A-Za-z0-9]+")
_SLUG_CHARSET_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class SlugResult:
    ok: bool
    slug: str | None = None
    error_code: str | None = None
    message: str | None = None

    def as_dict(self) -> dict:
        if self.ok:
            return {"ok": True, "slug": self.slug}
        return {"ok": False, "error_code": self.error_code, "message": self.message}


def _is_path_traversal_or_separator(raw: str) -> bool:
    """True if `raw` contains a path separator or is purely composed of dots.

    FR-QPB-021 requires rejecting path-traversal components (``..``) and separators
    (``/``, ``\\``) generally — not merely full traversal sequences.
    """
    if "/" in raw or "\\" in raw:
        return True
    if raw and set(raw) <= {"."}:
        return True
    return False


def _transliterate_to_ascii(text: str) -> str:
    """Best-effort Unicode -> ASCII transliteration (strip diacritics, drop the rest)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_bytes = normalized.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii")


def _fallback_slug_for(display_name: str) -> str:
    """Deterministic ASCII fallback for names that transliterate to nothing (e.g. pure CJK)."""
    digest = hashlib.sha256(display_name.encode("utf-8")).hexdigest()[:10]
    return f"project-{digest}"


def _is_reserved(candidate: str) -> bool:
    return candidate.upper() in _WINDOWS_RESERVED_NAMES


def derive_project_slug(display_name: str) -> SlugResult:
    """Derive and validate a filesystem-safe ``project_slug`` from ``project_display_name``.

    Wraps FR-QPB-021/FR-QPB-021a. See HARNESS_CONTRACT.md's ``derive_project_slug`` contract.
    """
    if not isinstance(display_name, str):
        return SlugResult(
            ok=False, error_code="blank", message="프로젝트 이름은 텍스트여야 합니다."
        )

    trimmed = display_name.strip()
    if not trimmed:
        return SlugResult(
            ok=False,
            error_code="blank",
            message="프로젝트 이름을 비워 둘 수 없습니다. 프로젝트 이름을 입력해 주세요.",
        )

    if _is_path_traversal_or_separator(trimmed):
        return SlugResult(
            ok=False,
            error_code="path_traversal",
            message=(
                "프로젝트 이름에는 경로 구분 기호(/ 또는 \\)를 포함하거나 점(.)으로만 이루어질 수 "
                "없습니다."
            ),
        )

    ascii_text = _transliterate_to_ascii(trimmed)
    slug_candidate = _NON_SLUG_CHARS_RE.sub("-", ascii_text).strip("-")
    slug_candidate = re.sub(r"-{2,}", "-", slug_candidate)

    if not slug_candidate:
        slug_candidate = _fallback_slug_for(trimmed)

    slug_candidate = slug_candidate.lower()[:MAX_SLUG_LENGTH].strip("-")
    if not slug_candidate:
        # Extremely unlikely (fallback is already ASCII/hyphen-safe), but guard regardless.
        slug_candidate = _fallback_slug_for(trimmed)[:MAX_SLUG_LENGTH]

    if _is_reserved(slug_candidate):
        return SlugResult(
            ok=False,
            error_code="reserved_filename",
            message=(
                f"'{slug_candidate}'은(는) Windows에서 예약된 파일 이름이므로 프로젝트 이름으로 "
                "사용할 수 없습니다."
            ),
        )

    if not _SLUG_CHARSET_RE.match(slug_candidate):
        # Defensive: should not happen given the derivation above.
        return SlugResult(
            ok=False,
            error_code="invalid_characters",
            message="입력한 텍스트로부터 안전한 프로젝트 이름을 만들 수 없습니다.",
        )

    if len(slug_candidate) > MAX_SLUG_LENGTH:
        return SlugResult(
            ok=False,
            error_code="too_long",
            message=f"프로젝트 슬러그는 {MAX_SLUG_LENGTH}자를 초과할 수 없습니다.",
        )

    return SlugResult(ok=True, slug=slug_candidate)


def derive_project_slug_dict(display_name: str) -> dict:
    """Dict-returning convenience wrapper matching HARNESS_CONTRACT.md's literal return shape."""
    return derive_project_slug(display_name).as_dict()


def new_project_id() -> str:
    """A UUID v4 project_id, independent of project_display_name/project_slug (FR-QPB-021a)."""
    return str(uuid.uuid4())
