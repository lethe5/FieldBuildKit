"""`build_plantnet_identify_request()` / `call_plantnet_identify()`
(HARNESS_CONTRACT.md functions 7/8; FR-QPB-104, revised; Decision Log D-37; further revised,
Decision Log D-54, to add the `include-related-images=true` request parameter).

`build_plantnet_identify_request` is a pure-Python reference implementation of FR-QPB-104's
client-side request-shape rules only -- it performs no network I/O. `call_plantnet_identify` is a
real-network-calling function used exclusively by the acceptance suite's `network`-marked live
test, mirroring the role `qfield_builder.vworld.fetch_supported_layers` plays for the existing live
VWorld test.

Neither function is the shipped mechanism -- Pl@ntNet is called from the embedded `QML Widget` via
QML's own native `XMLHttpRequest` (FR-QPB-101; see :mod:`qfield_builder.qml_plugin`). These exist
so the *request-shape rules* are verifiable offline/live against the real, confirmed API contract
(Decision Log D-37).
"""
from __future__ import annotations

import mimetypes
import os
import uuid
from urllib import error as urllib_error
from urllib import request as urllib_request

PLANTNET_ENDPOINT_TEMPLATE = "https://my-api.plantnet.org/v2/identify/{project}"
PLANTNET_DEFAULT_PROJECT = "all"
# D-98: no application-imposed candidate count; match the shipped QML request.
# FR-QPB-104 (further revised; Decision Log D-54; AC-QPB-094): causes Pl@ntNet to additionally
# return a per-candidate related-images list (organ/author/license/date/citation fields plus an
# o/m/s size-variant `url` object), consumed by FR-QPB-109's candidate-card image/attribution
# display (qfield_builder.qml_plugin).
PLANTNET_INCLUDE_RELATED_IMAGES = True
_MAX_PHOTOS = 5
_SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png")


def build_plantnet_identify_request(
    photo_paths: list[str], organs: list[str], project: str = "all"
) -> dict:
    """See HARNESS_CONTRACT.md function 7 for the exact, authoritative contract."""
    if len(organs) != len(photo_paths):
        return {
            "ok": False,
            "error_code": "organ_count_mismatch",
            "message": (
                f"organs count ({len(organs)}) must match photo_paths count "
                f"({len(photo_paths)})."
            ),
        }
    if len(photo_paths) > _MAX_PHOTOS:
        return {
            "ok": False,
            "error_code": "too_many_photos",
            "message": f"At most {_MAX_PHOTOS} photos may be submitted per request.",
        }
    for path in photo_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            return {
                "ok": False,
                "error_code": "unsupported_photo_format",
                "message": f"Unsupported photo format {ext!r} for {path!r}; JPEG/PNG only.",
            }

    project_name = project or PLANTNET_DEFAULT_PROJECT
    url = PLANTNET_ENDPOINT_TEMPLATE.format(project=project_name)
    return {
        "ok": True,
        "url": url,
        "method": "POST",
        "query": {
            "project": project_name,
            "include-related-images": PLANTNET_INCLUDE_RELATED_IMAGES,
        },
        "organs": list(organs),
        "photo_paths": list(photo_paths),
    }


def _build_multipart_body(photo_paths: list[str], organs: list[str]) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for organ, photo_path in zip(organs, photo_paths, strict=True):
        parts.append(
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="organs"\r\n\r\n'
                f"{organ}\r\n"
            ).encode()
        )
        content_type = mimetypes.guess_type(photo_path)[0] or "application/octet-stream"
        with open(photo_path, "rb") as fh:
            file_bytes = fh.read()
        filename = os.path.basename(photo_path)
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="images"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        parts.append(file_bytes)
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def call_plantnet_identify(
    photo_paths: list[str], organs: list[str], api_key: str, project: str = "all"
) -> dict:
    """See HARNESS_CONTRACT.md function 8 for the exact, authoritative contract.

    Never logs/prints `api_key` or raw photo bytes.
    """
    request_shape = build_plantnet_identify_request(photo_paths, organs, project=project)
    if not request_shape["ok"]:
        return {"http_status": 0, "body": None, "raw_text": request_shape["message"]}

    body, boundary = _build_multipart_body(photo_paths, organs)
    url = (
        f"{request_shape['url']}"
        f"?api-key={api_key}"
        "&include-related-images=true"
    )
    req = urllib_request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib_error.HTTPError as exc:
        raw_text = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except urllib_error.URLError as exc:
        return {"http_status": 0, "body": None, "raw_text": str(exc.reason)}

    import json

    try:
        body_json = json.loads(raw_text) if raw_text else None
    except json.JSONDecodeError:
        body_json = None

    return {"http_status": status, "body": body_json, "raw_text": raw_text}
