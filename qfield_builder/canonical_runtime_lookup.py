"""Minimal project-local canonical taxonomy lookup resource for QField.

The canonical GeoPackage table remains the source of truth for desktop inspection and reports.
This module derives a compact, deterministic projection from that *already materialized* table
for QField's attribute-form JavaScript runtime.  It intentionally never copies the source
workbook or its URL/rank columns into a delivered project.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


RUNTIME_RESOURCE_RELPATH = "reference/canonical_taxonomy_runtime_lookup.json"
RUNTIME_RESOURCE_SCHEMA_REVISION = "QCR-1"
RUNTIME_RESOURCE_PIPELINE_REVISION = "D-96-canonical-runtime-lookup-1"
CANONICAL_TABLE_NAME = "ktsn_taxonomy_reference"


class CanonicalRuntimeLookupBuildError(RuntimeError):
    """A resource generation or validation error that must prevent project promotion."""


def _required_text(value: object, field: str) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        raise CanonicalRuntimeLookupBuildError(
            f"canonical runtime lookup의 필수 값이 비어 있습니다: {field}"
        )
    return text


def _projection_rows(gpkg_path: str) -> list[dict]:
    """Read and verify the minimal mapping from the newly built canonical GPKG table."""
    try:
        with closing(sqlite3.connect(gpkg_path)) as connection:
            rows = connection.execute(
                f"SELECT source_row, ktsn, taxon_status, scientific_name_without_authority, "
                f"accepted_ktsn, korean_name, scientific_name FROM {CANONICAL_TABLE_NAME} "
                "ORDER BY source_row"
            ).fetchall()
    except sqlite3.Error as exc:
        raise CanonicalRuntimeLookupBuildError(
            "canonical GeoPackage 참조표에서 QField 조회 데이터를 읽을 수 없습니다."
        ) from exc

    if not rows:
        raise CanonicalRuntimeLookupBuildError("canonical GeoPackage 참조표가 비어 있습니다.")

    accepted: dict[str, tuple[str, str]] = {}
    normalized_rows: list[dict] = []
    for source_row, ktsn, status, comparison_key, accepted_ktsn, korean_name, scientific_name in rows:
        source_row_value = int(source_row)
        ktsn_value = _required_text(ktsn, "ktsn")
        group = _required_text(accepted_ktsn, "accepted_ktsn")
        key = _required_text(comparison_key, "scientific_name_without_authority")
        normalized_rows.append(
            {
                "source_row": source_row_value,
                "ktsn": ktsn_value,
                "taxon_status": _required_text(status, "taxon_status"),
                "scientific_name_without_authority": key,
                "accepted_ktsn": group,
                "korean_name": "" if korean_name is None else str(korean_name).strip(),
                "scientific_name": "" if scientific_name is None else str(scientific_name).strip(),
            }
        )
        if ktsn_value == group:
            if status != "정명":
                raise CanonicalRuntimeLookupBuildError(
                    "canonical GeoPackage 참조표의 인정 KTSN 행이 정명이 아닙니다."
                )
            value = (
                _required_text(korean_name, "accepted korean_name"),
                _required_text(scientific_name, "accepted scientific_name"),
            )
            previous = accepted.get(group)
            if previous is not None and previous != value:
                raise CanonicalRuntimeLookupBuildError(
                    "canonical GeoPackage 참조표의 인정 결과가 내부적으로 일치하지 않습니다."
                )
            accepted[group] = value

    records: list[dict] = []
    for row in normalized_rows:
        output = accepted.get(row["accepted_ktsn"])
        if output is None:
            raise CanonicalRuntimeLookupBuildError(
                "canonical GeoPackage 참조표에서 이명에 대응하는 정명을 찾을 수 없습니다."
            )
        records.append(
            {
                "source_row": row["source_row"],
                "scientific_name_without_authority": row["scientific_name_without_authority"],
                "accepted_ktsn": row["accepted_ktsn"],
                "korean_name": output[0],
                "scientific_name": output[1],
            }
        )
    return records


def _payload(records: list[dict]) -> dict:
    return {
        "schema_revision": RUNTIME_RESOURCE_SCHEMA_REVISION,
        "pipeline_revision": RUNTIME_RESOURCE_PIPELINE_REVISION,
        "record_count": len(records),
        "records": records,
    }


def _serialize(records: list[dict]) -> bytes:
    return (json.dumps(_payload(records), ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _validated_payload(raw: bytes, expected: dict | None = None) -> dict:
    """Parse the on-device format using the same fail-closed structural contract as QML."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 형식이 올바르지 않습니다.") from exc
    if not isinstance(payload, dict):
        raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 형식이 올바르지 않습니다.")
    if payload.get("schema_revision") != RUNTIME_RESOURCE_SCHEMA_REVISION:
        raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 schema가 일치하지 않습니다.")
    if payload.get("pipeline_revision") != RUNTIME_RESOURCE_PIPELINE_REVISION:
        raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 pipeline이 일치하지 않습니다.")
    records = payload.get("records")
    if not isinstance(records, list) or not records or payload.get("record_count") != len(records):
        raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 레코드가 올바르지 않습니다.")

    outputs_by_accepted: dict[str, tuple[str, str]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 레코드가 올바르지 않습니다.")
        key = _required_text(record.get("scientific_name_without_authority"), "comparison key")
        accepted_ktsn = _required_text(record.get("accepted_ktsn"), "accepted_ktsn")
        korean_name = _required_text(record.get("korean_name"), "korean_name")
        scientific_name = _required_text(record.get("scientific_name"), "scientific_name")
        source_row = record.get("source_row")
        if not isinstance(source_row, int) or source_row < 1:
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 source_row가 올바르지 않습니다.")
        if key != str(record.get("scientific_name_without_authority")).strip():
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup 리소스 비교 키가 올바르지 않습니다.")
        output = (korean_name, scientific_name)
        previous = outputs_by_accepted.get(accepted_ktsn)
        if previous is not None and previous != output:
            raise CanonicalRuntimeLookupBuildError(
                "canonical runtime lookup 리소스의 인정 결과가 내부적으로 일치하지 않습니다."
            )
        outputs_by_accepted[accepted_ktsn] = output

    if expected is not None:
        for field in ("schema_revision", "pipeline_revision", "record_count", "byte_size", "sha256"):
            if field not in expected:
                raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance가 올바르지 않습니다.")
        if expected["schema_revision"] != payload["schema_revision"]:
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance schema가 일치하지 않습니다.")
        if expected["pipeline_revision"] != payload["pipeline_revision"]:
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance pipeline이 일치하지 않습니다.")
        if expected["record_count"] != len(records):
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance count가 일치하지 않습니다.")
        if expected["byte_size"] != len(raw):
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance size가 일치하지 않습니다.")
        if expected["sha256"] != hashlib.sha256(raw).hexdigest():
            raise CanonicalRuntimeLookupBuildError("canonical runtime lookup provenance hash가 일치하지 않습니다.")
    return payload


def materialize_runtime_resource(
    gpkg_path: str,
    project_dir: str,
    *,
    force_failure_stage: str | None = None,
) -> dict:
    """Create and validate the project-relative canonical runtime projection atomically."""
    if force_failure_stage == "materialization":
        raise CanonicalRuntimeLookupBuildError("테스트 주입: canonical runtime resource materialization 실패")
    records = _projection_rows(gpkg_path)
    raw = _serialize(records)
    destination = Path(project_dir) / RUNTIME_RESOURCE_RELPATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor, staging_name = tempfile.mkstemp(
            prefix=".qpb-canonical-runtime-", suffix=".json", dir=destination.parent
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
        staging = Path(staging_name)
        os.replace(staging, destination)
    except OSError as exc:
        raise CanonicalRuntimeLookupBuildError(
            "canonical runtime lookup 리소스를 프로젝트에 저장할 수 없습니다."
        ) from exc
    finally:
        try:
            if "staging" in locals() and staging.exists():
                staging.unlink()
        except OSError:
            pass

    metadata = {
        "relative_path": RUNTIME_RESOURCE_RELPATH,
        "schema_revision": RUNTIME_RESOURCE_SCHEMA_REVISION,
        "pipeline_revision": RUNTIME_RESOURCE_PIPELINE_REVISION,
        "record_count": len(records),
        "byte_size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if force_failure_stage == "schema_validation":
        raise CanonicalRuntimeLookupBuildError("테스트 주입: canonical runtime resource schema validation 실패")
    _validated_payload(destination.read_bytes(), metadata)
    if force_failure_stage == "provenance_write":
        raise CanonicalRuntimeLookupBuildError("테스트 주입: canonical runtime resource provenance write 실패")
    return metadata


def inspect_runtime_resource(project_dir: str, provenance: dict | None) -> dict | None:
    """Inspect a delivered resource without consulting a workbook or the legacy CSV branch."""
    if not isinstance(provenance, dict):
        return None
    relative_path = provenance.get("relative_path")
    if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute():
        return None
    root = Path(project_dir).resolve()
    resource_path = (root / relative_path).resolve()
    if root not in resource_path.parents or not resource_path.is_file():
        return None
    try:
        raw = resource_path.read_bytes()
        payload = _validated_payload(raw, provenance)
    except (OSError, CanonicalRuntimeLookupBuildError):
        return None
    return {**provenance, "records": payload["records"]}
