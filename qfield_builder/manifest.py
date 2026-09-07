"""`MANIFEST.json` generation (FR-QPB-090/092, NFR-QPB-017/071, AC-QPB-027/057/081).

`MANIFEST.json` identifies every required file so a missing attachment, plugin (post-MVP),
database, or basemap can be detected before transfer (FR-QPB-092). Per NFR-QPB-017, when the
online-layer VWorld key-embedding exception (FR-QPB-073/076-079) was used, the manifest may
record only a boolean `security_warning` flag — never the key itself. Per NFR-QPB-071 (Decision
Log D-45), the same treatment applies, independently, to the Pl@ntNet key-embedding exception
(FR-QPB-114-116): a second, independent boolean flag, never the key itself.
"""

from __future__ import annotations

import json
from pathlib import Path

from .vworld import ATTRIBUTION_TEXT_EN, ATTRIBUTION_TEXT_KO

MANIFEST_FILENAME = "MANIFEST.json"


def build_manifest(
    project_dir: str,
    project_id: str,
    project_slug: str,
    survey_type: str,
    qgs_relpath: str,
    gpkg_relpath: str,
    attachment_relpaths: list[str],
    basemap_relpaths: list[str],
    online_key_embedded: bool,
    identification_plugin_relpath: str | None = None,
    reference_relpaths: list[str] | None = None,
    plantnet_key_embedded: bool = False,
    probability_band_count: int | None = None,
    source_provenance: dict | None = None,
    canonical_runtime_lookup: dict | None = None,
) -> dict:
    """``identification_plugin_relpath`` names the shared project-plugin sidecar.

    The manifest key's historical name is retained for compatibility, but D-87 makes this file
    unconditional because it also owns the identification-independent HTML-report action.
    ``reference_relpaths`` remains identification-gated (FR-QPB-112/113). All paths are project-
    relative, per FR-QPB-091/DR-QPB-012's no-absolute-paths discipline.

    `plantnet_key_embedded` (NFR-QPB-071, Decision Log D-45): whether the Pl@ntNet key-embedding
    consent-gated exception (FR-QPB-114-116) was used for this build -- independent of, and
    additional to, `online_key_embedded`'s pre-existing VWorld flag."""
    manifest = {
        "manifest_version": "1.0",
        "project_id": project_id,
        "project_slug": project_slug,
        "survey_type": survey_type,
        "required_files": {
            "qgs_project": qgs_relpath,
            "geopackage": gpkg_relpath,
            "attachments": attachment_relpaths,
            "basemap": basemap_relpaths,
            "identification_plugin": identification_plugin_relpath,
            "reference": reference_relpaths or [],
        },
        "security": {
            # NFR-QPB-017: a boolean flag only — never the key itself.
            "online_layer_key_embedded_warning": bool(online_key_embedded),
            # NFR-QPB-071 (Decision Log D-45): a second, independent boolean flag only — never
            # the key itself. May be true/false independently of the VWorld flag above.
            "plantnet_api_key_embedded_warning": bool(plantnet_key_embedded),
        },
        "attribution": {
            "vworld_molit_en": ATTRIBUTION_TEXT_EN,
            "vworld_molit_ko": ATTRIBUTION_TEXT_KO,
        },
    }
    if probability_band_count is not None:
        manifest["probability_raster"] = {
            "stack_path": "reference/rasters/occurrence_probability_multiband.tif",
            "index_path": "reference/rasters/occurrence_probability_bands.json",
            "band_count": int(probability_band_count),
        }
    if source_provenance is not None:
        # This is metadata only; the workbook bytes and rows never enter a generated project.
        manifest["source_provenance"] = dict(source_provenance)
    if canonical_runtime_lookup is not None:
        # D-96/QCR: the QField-only projection is independently auditable from the canonical
        # workbook provenance.  It contains only the project-relative resource identity, never
        # source-workbook rows or paths.
        manifest["canonical_runtime_lookup"] = dict(canonical_runtime_lookup)
    return manifest


def write_manifest(project_dir: str, manifest: dict) -> str:
    path = Path(project_dir) / MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def find_missing_required_files(project_dir: str, manifest: dict) -> list[dict]:
    """AC-QPB-027: detect a manifest-declared file that is absent from the project folder."""
    root = Path(project_dir)
    issues: list[dict] = []
    required = manifest.get("required_files", {})

    for key in ("qgs_project", "geopackage"):
        rel = required.get(key)
        if rel and not (root / rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": (
                        f"Required file '{rel}' ({key}) declared in MANIFEST.json is missing."
                    ),
                }
            )

    for rel in required.get("attachments", []) or []:
        if rel and not (root / rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": f"Attachment '{rel}' declared in MANIFEST.json is missing.",
                }
            )

    for rel in required.get("basemap", []) or []:
        if rel and not (root / rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": f"Basemap file '{rel}' declared in MANIFEST.json is missing.",
                }
            )

    plugin_rel = required.get("identification_plugin")
    if plugin_rel and not (root / plugin_rel).exists():
        issues.append(
            {
                "code": "missing_manifest_file",
                "message": (
                    f"Project plugin file '{plugin_rel}' declared in MANIFEST.json is missing."
                ),
            }
        )

    for rel in required.get("reference", []) or []:
        if rel and not (root / rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": f"Reference asset '{rel}' declared in MANIFEST.json is missing.",
                }
            )

    return issues
