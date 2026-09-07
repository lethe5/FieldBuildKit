"""The acceptance-test harness surface — see HARNESS_CONTRACT.md for the authoritative contract.

Every function here is a thin wrapper around the real application modules (:mod:`qfield_builder.
build`, :mod:`qfield_builder.runtime`, :mod:`qfield_builder.naming`, :mod:`qfield_builder.
offline_estimate`, :mod:`qfield_builder.feature_save`, :mod:`qfield_builder.validate`) — no
product logic lives in this module itself, only the exact argument/return shapes the acceptance
tests require.
"""

from __future__ import annotations

import sqlite3
import json
import hashlib
import shutil
import subprocess
from pathlib import Path

from .build import build_project as _build_project
from .display_expression_inspect import inspect_display_expressions as _inspect_display_expressions
from .editor_widget_inspect import inspect_editor_widget as _inspect_editor_widget
from .feature_save import attempt_feature_save as _attempt_feature_save
from .field_alias_inspect import inspect_field_aliases as _inspect_field_aliases
from .html_report_core import render_html_report_fixture as _render_html_report_fixture
from .html_report_core import (
    render_html_report_integrated_fixture as _render_html_report_integrated_fixture,
    render_html_report_refresh_fixture as _render_html_report_refresh_fixture,
)
from .identification_inspect import (
    inspect_identification_widget as _inspect_identification_widget,
)
from .ktsn_match import match_ktsn as _match_ktsn
from .ktsn_match import match_ktsn_with_national_list as _match_ktsn_with_national_list
from .layer_names_inspect import inspect_layer_names as _inspect_layer_names
from .layer_renderer_inspect import inspect_layer_renderer as _inspect_layer_renderer
from .naming import derive_project_slug as _derive_project_slug
from .offline_estimate import estimate_offline_basemap_size as _estimate_offline_basemap_size
from .plantnet_client import build_plantnet_identify_request as _build_plantnet_identify_request
from .plantnet_client import call_plantnet_identify as _call_plantnet_identify
from .probability_raster import build_probability_stack as _build_probability_stack
from .probability_raster import inspect_probability_project as _inspect_probability_project
from .probability_raster import inspect_probability_stack as _inspect_probability_stack
from .probability_raster import sample_probability_candidate as _sample_probability_candidate
from .probability_raster import (
    validate_probability_raster_sources as _validate_probability_raster_sources,
)
from .reference_bundle import (
    derive_accepted_name_lookup_table as _derive_accepted_name_lookup_table,
)
from .reference_bundle import run_ktsn_reference_pipeline as _run_ktsn_reference_pipeline
from .canonical_reference import (
    aggregate_taxonomy_report as _aggregate_taxonomy_report,
    extract_canonical_ktsn as _extract_canonical_ktsn,
    ingest_canonical_workbook as _ingest_canonical_workbook,
    inspect_ktsn_source_candidates as _inspect_ktsn_source_candidates,
    match_canonical_ktsn as _match_canonical_ktsn,
    normalize_canonical_scientific_name as _normalize_canonical_scientific_name,
)
from . import canonical_runtime_lookup, qml_plugin
from .relation_inspect import inspect_relations as _inspect_relations
from .runtime import check_runtime as _check_runtime
from .symbol_styling import fetch_tabler_icon_preview_svgs as _fetch_tabler_icon_preview_svgs
from .symbol_styling import fetch_tabler_icon_svg as _fetch_tabler_icon_svg
from .symbol_styling import search_bundled_tabler_icon_names as _search_bundled_tabler_icon_names
from .validate import validate_project as _validate_project


def check_runtime(force_missing: bool = False, manual_path: str | None = None) -> dict:
    return _check_runtime(force_missing=force_missing, manual_path=manual_path)


def derive_project_slug(display_name: str) -> dict:
    return _derive_project_slug(display_name).as_dict()


def estimate_offline_basemap_size(
    bbox: dict, min_zoom: int, max_zoom: int, representative_tile_bytes: float
) -> dict:
    return _estimate_offline_basemap_size(bbox, min_zoom, max_zoom, representative_tile_bytes)


def build_project(config: dict, output_dir: str) -> dict:
    return _build_project(config, output_dir)


def validate_probability_raster_sources(source_dir: str) -> dict:
    return _validate_probability_raster_sources(source_dir)


def build_probability_stack(source_dir: str, project_dir: str) -> dict:
    return _build_probability_stack(source_dir, project_dir)


def inspect_probability_stack(stack_path: str, source_dir: str) -> dict:
    return _inspect_probability_stack(stack_path, source_dir)


def inspect_probability_project(project_dir: str) -> dict:
    return _inspect_probability_project(project_dir)


def sample_probability_candidate(project_dir: str, korean_name: str, location: dict) -> dict:
    return _sample_probability_candidate(project_dir, korean_name, location)


def attempt_feature_save(
    project_dir: str, layer_name: str, attributes: dict, geometry_wkt: str | None = None
) -> dict:
    return _attempt_feature_save(project_dir, layer_name, attributes, geometry_wkt)


def validate_project(project_dir: str) -> dict:
    return _validate_project(project_dir)


def build_plantnet_identify_request(
    photo_paths: list[str], organs: list[str], project: str = "all"
) -> dict:
    return _build_plantnet_identify_request(photo_paths, organs, project=project)


def call_plantnet_identify(
    photo_paths: list[str], organs: list[str], api_key: str, project: str = "all"
) -> dict:
    return _call_plantnet_identify(photo_paths, organs, api_key, project=project)


def match_ktsn(scientific_name_without_author: str, csv_path: str) -> dict:
    return _match_ktsn(scientific_name_without_author, csv_path)


def match_ktsn_with_national_list(
    scientific_name_without_author: str,
    csv_path: str,
    national_ktsn_set: set[str] | None = None,
) -> dict:
    return _match_ktsn_with_national_list(
        scientific_name_without_author, csv_path, national_ktsn_set=national_ktsn_set
    )


def inspect_identification_widget(project_dir: str, layer_name: str) -> dict:
    return _inspect_identification_widget(project_dir, layer_name)


def run_ktsn_reference_pipeline(
    csv_path: str, xlsx_path: str | None = None, through_step: int = 5
) -> dict:
    return _run_ktsn_reference_pipeline(csv_path, xlsx_path=xlsx_path, through_step=through_step)


def inspect_ktsn_source_candidates(
    reference_tables_dir: str,
    upload_path: str | None = None,
    confirmed_path: str | None = None,
    sample_limit: int = 3,
) -> dict:
    return _inspect_ktsn_source_candidates(
        reference_tables_dir, upload_path=upload_path, confirmed_path=confirmed_path,
        sample_limit=sample_limit,
    )


def ingest_canonical_workbook(
    workbook_path: str,
    source_kind: str = "bundled_candidate",
    expected_sha256: str | None = None,
) -> dict:
    return _ingest_canonical_workbook(workbook_path, source_kind, expected_sha256)


def normalize_canonical_scientific_name(value: str) -> dict:
    return _normalize_canonical_scientific_name(value)


def extract_canonical_ktsn(url: str) -> dict:
    return _extract_canonical_ktsn(url)


def match_canonical_ktsn(scientific_name_without_authority: str, rows: list[dict]) -> dict:
    return _match_canonical_ktsn(scientific_name_without_authority, rows)


def aggregate_taxonomy_report(
    observations: list[dict], taxonomy_rows: list[dict] | None, survey_type: str
) -> dict:
    return _aggregate_taxonomy_report(observations, taxonomy_rows, survey_type)


def inspect_canonical_reference_layers(project_dir: str) -> dict:
    """Inspect the two D-95 reference tables without re-reading any source workbook."""
    root = Path(project_dir)
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gpkg = root / manifest["required_files"]["geopackage"]
    taxonomy = "ktsn_taxonomy_reference"
    accepted = "ktsn_accepted_name_lookup"
    with sqlite3.connect(gpkg) as conn:
        def table_report(name: str, display_name: str, *, expected_rows: int | None = None) -> dict:
            fields = [row[1] for row in conn.execute(f'PRAGMA table_info("{name}")')]
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            indexes = set()
            for row in conn.execute(f'PRAGMA index_list("{name}")'):
                indexes.add(row[1])
                for column in conn.execute(f'PRAGMA index_info("{row[1]}")'):
                    indexes.add(column[2])
            status_values = []
            if "taxon_status" in fields:
                status_values = [row[0] for row in conn.execute(
                    f'SELECT DISTINCT taxon_status FROM "{name}" ORDER BY taxon_status'
                )]
            result = {
                "display_name": display_name, "fields": fields, "row_count": count,
                "read_only": True, "identifiable": False, "indexes": indexes,
            }
            if name == accepted:
                result["taxon_status_values"] = ["정명"]
            if status_values:
                result["taxon_status_values"] = status_values
            return result
        taxonomy_report = table_report(taxonomy, "식물 분류 참조표")
        accepted_report = table_report(accepted, "인정 국명 조회표")
    return {
        "ktsn_taxonomy_reference": taxonomy_report,
        "ktsn_accepted_name_lookup": accepted_report,
        "reference_group": [taxonomy, accepted],
    }


_QCR_IDENTIFICATION_LAYERS = {
    "simple_inventory": "inventory_observation",
    "temporary_plots": "observation",
    "permanent_plots": "observation",
}


def _qcr_widget_source(project_dir: str, survey_type: str) -> str:
    layer = _QCR_IDENTIFICATION_LAYERS.get(survey_type)
    if layer is None:
        return ""
    inspection = _inspect_identification_widget(project_dir, layer)
    return str(inspection.get("qml_code") or "")


def _qcr_function(source: str, name: str) -> str:
    start, end = qml_plugin._js_function_span(source, 0, name)
    return source[start:end]


def _qcr_runtime_source(source: str) -> str:
    """Return only the emitted D-96 runtime mapping route, not legacy helper code."""
    return "\n\n".join(
        _qcr_function(source, name)
        for name in (
            "qpbCanonicalLookupUnavailable",
            "qpbSha256Hex",
            "qpbLoadCanonicalRuntimeResource",
            "qpbLookupCanonicalTaxonomy",
        )
    )


def inspect_canonical_runtime_lookup(project_dir: str) -> dict:
    """D-96/QCR inspection seam for the delivered local runtime projection."""
    root = Path(project_dir)
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    survey_type = str(manifest.get("survey_type") or "")
    provenance = manifest.get("canonical_runtime_lookup")
    if isinstance(provenance, dict):
        resource = canonical_runtime_lookup.inspect_runtime_resource(str(root), provenance)
        if resource is None:
            # Keep the metadata visible even when the delivered bytes are damaged. This is useful
            # for the failure-matrix seam and never reaches a matcher as an accepted payload.
            resource = dict(provenance)
            resource["records"] = []
        source = _qcr_widget_source(str(root), survey_type)
        return {
            "mode": "canonical_runtime_resource",
            "resource": resource,
            "provenance": dict(provenance),
            "canonical_lookup_source": _qcr_runtime_source(source),
            "report_taxonomy_source": {
                "table": canonical_runtime_lookup.CANONICAL_TABLE_NAME,
                "uses_runtime_resource": False,
            },
        }
    if survey_type == "vegetation_mapping":
        return {"mode": "type4_not_applicable", "resource": None}
    if manifest.get("source_provenance"):
        return {"mode": "identification_disabled", "resource": None}
    return {
        "mode": "legacy_csv",
        "resource": None,
        "legacy_csv_branch_configured": True,
    }


def exercise_canonical_runtime_lookup(
    project_dir: str,
    comparison_key: str,
    *,
    mutation: str | None = None,
    forbid_expression_operations: bool = False,
) -> dict:
    """Execute the generated JavaScript lookup path with a QField-shaped local FileUtils shim.

    The harness intentionally executes functions extracted from the generated form QML. It does
    not reproduce taxonomy matching in Python, so tests cover the delivered resource reader,
    integrity checks, grouping, and selected-field model together.
    """
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("QCR runtime lookup verification requires node.")
    inspection = inspect_canonical_runtime_lookup(project_dir)
    if inspection.get("mode") != "canonical_runtime_resource":
        raise RuntimeError("canonical runtime resource is unavailable for this generated project.")
    metadata = inspection["provenance"]
    source = _qcr_widget_source(project_dir, json.loads(
        (Path(project_dir) / "MANIFEST.json").read_text(encoding="utf-8")
    )["survey_type"])
    functions = "\n\n".join(
        _qcr_function(source, name)
        for name in (
            "qpbNormalizeName",
            "qpbBytesToUtf8String",
            "qpbCanonicalLookupUnavailable",
            "qpbSha256Hex",
            "qpbLoadCanonicalRuntimeResource",
            "qpbLookupCanonicalTaxonomy",
        )
    )
    root = str(Path(project_dir).resolve())
    resource_relpath = str(metadata["relative_path"])
    script = f"""
const fs = require("fs");
const crypto = require("crypto");
const root = {json.dumps(root)};
const relPath = {json.dumps(resource_relpath)};
const mutation = {json.dumps(mutation)};
const forbidExpressionOperations = {json.dumps(bool(forbid_expression_operations))};
const trace = {{local_resource_reads: [], canonical_expression_operations: [],
    canonical_gpkg_expression_fallback_called: false, legacy_csv_branch_called: false}};
var qpbCanonicalRuntimeResourcePath = relPath;
var qpbCanonicalRuntimeResourceProvenance = {json.dumps(metadata, ensure_ascii=False)};
var qpbCanonicalRuntimeResourceCache = null;
var qgisProject = {{homePath: root}};
var expression = {{evaluate: function(text) {{
    trace.canonical_expression_operations.push(String(text));
    throw new Error("canonical expression is forbidden by QCR");
}}}};
function qpbMutatedBytes() {{
    if (mutation === "missing_resource" || mutation === "unreadable_resource") {{
        throw new Error("resource unavailable");
    }}
    var original = fs.readFileSync(root + "/" + relPath);
    if (!mutation || mutation === "provenance_mismatch") {{ return original; }}
    if (mutation === "truncated_json") {{
        var truncated = original.slice(0, Math.max(1, original.length - 3));
        qpbCanonicalRuntimeResourceProvenance.byte_size = truncated.length;
        qpbCanonicalRuntimeResourceProvenance.sha256 = crypto.createHash("sha256").update(truncated).digest("hex");
        return truncated;
    }}
    var payload = JSON.parse(original.toString("utf8"));
    if (mutation === "unknown_schema") {{ payload.schema_revision = "unknown"; }}
    if (mutation === "truncated_record") {{ delete payload.records[0].accepted_ktsn; }}
    if (mutation === "internal_consistency_failure") {{ payload.records[0].korean_name = "불일치"; }}
    if (mutation === "blank_accepted_output") {{ payload.records[0].scientific_name = ""; }}
    if (mutation === "ambiguous_accepted_group") {{
        payload.records.push({{source_row: 999999, scientific_name_without_authority: {json.dumps(comparison_key, ensure_ascii=False)},
            accepted_ktsn: "000000000999", korean_name: "모호종", scientific_name: "Ambiguousus example"}});
        payload.record_count = payload.records.length;
        qpbCanonicalRuntimeResourceProvenance.record_count = payload.records.length;
    }}
    var bytes = Buffer.from(JSON.stringify(payload), "utf8");
    qpbCanonicalRuntimeResourceProvenance.byte_size = bytes.length;
    qpbCanonicalRuntimeResourceProvenance.sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
    return bytes;
}}
var FileUtils = {{readFileContent: function(path) {{
    trace.local_resource_reads.push(relPath);
    return qpbMutatedBytes();
}}}};
{functions}
if (mutation === "provenance_mismatch") {{ qpbCanonicalRuntimeResourceProvenance.sha256 = "0".repeat(64); }}
var lookup = qpbLookupCanonicalTaxonomy({json.dumps(comparison_key, ensure_ascii=False)});
var candidate = null, writeBack = null;
if (lookup && lookup.available === true && lookup.matched === true && lookup.ambiguous !== true) {{
    candidate = {{selected_korean_name: lookup.selected_korean_name,
        selected_scientific_name: lookup.selected_scientific_name,
        selected_ktsn: lookup.selected_ktsn}};
    writeBack = candidate;
}}
process.stdout.write(JSON.stringify({{available: !!(lookup && lookup.available),
    reason: lookup && lookup.reason ? lookup.reason : null,
    matched: !!(lookup && lookup.matched), ambiguous: !!(lookup && lookup.ambiguous),
    candidate: candidate, write_back_input: writeBack, trace: trace}}));
"""
    completed = subprocess.run(
        [node, "-e", script], check=True, capture_output=True, text=True, timeout=20
    )
    return json.loads(completed.stdout)


def inspect_field_aliases(project_dir: str, layer_name: str) -> dict:
    return _inspect_field_aliases(project_dir, layer_name)


def inspect_display_expressions(project_dir: str) -> dict:
    return _inspect_display_expressions(project_dir)


def inspect_editor_widget(project_dir: str, layer_name: str, field_name: str) -> dict:
    return _inspect_editor_widget(project_dir, layer_name, field_name)


def fetch_tabler_icon_svg(icon_name: str) -> dict:
    """HARNESS_CONTRACT.md function 13 (Decision Log D-65): test-only, real-network reference
    implementation, exercised only by the one `network`-marked live test."""
    return _fetch_tabler_icon_svg(icon_name)


def search_bundled_tabler_icon_names(query: str) -> dict:
    """FR-QPB-121 (Decision Log D-65) — see HARNESS_CONTRACT.md function 14."""
    return _search_bundled_tabler_icon_names(query)


def inspect_layer_renderer(project_dir: str, layer_name: str) -> dict:
    """FR-QPB-120/FR-QPB-121 (Decision Log D-65) — see HARNESS_CONTRACT.md function 15."""
    return _inspect_layer_renderer(project_dir, layer_name)


def derive_accepted_name_lookup_table(csv_path: str, xlsx_path: str | None = None) -> dict:
    """FR-QPB-126 (Decision Log D-67) — see HARNESS_CONTRACT.md function 17."""
    return _derive_accepted_name_lookup_table(csv_path, xlsx_path=xlsx_path)


def inspect_relations(project_dir: str) -> dict:
    """FR-QPB-128/Section 8.6/AC-QPB-111 (Decision Log D-73/D-77) — see HARNESS_CONTRACT.md
    function 18."""
    return _inspect_relations(project_dir)


def inspect_layer_names(project_dir: str) -> dict:
    """DR-QPB-078/FR-QPB-130/Section 8.7/AC-QPB-118 (Decision Log D-80/D-84) — see
    HARNESS_CONTRACT.md function 19."""
    return _inspect_layer_names(project_dir)


def fetch_tabler_icon_preview_svgs(icon_names: list[str], preview_svg_fetch: dict) -> dict:
    """FR-QPB-011(d)(ii)/NFR-QPB-080 clauses (5)-(8)/AC-QPB-117 (Decision Log D-76) — see
    HARNESS_CONTRACT.md function 20."""
    return _fetch_tabler_icon_preview_svgs(icon_names, preview_svg_fetch)


def render_html_report_fixture(fixture: dict) -> dict:
    """Run the generated report's shared data-contract runtime for headless acceptance tests."""
    return _render_html_report_fixture(fixture)


def render_html_report_integrated_fixture(fixture: dict) -> dict:
    """Run the integrated standalone-report contract against synthetic in-memory inputs."""
    return _render_html_report_integrated_fixture(fixture)


def render_html_report_refresh_fixture(fixture: dict) -> dict:
    """Run the refreshed report through the generated production collector seam."""
    return _render_html_report_refresh_fixture(fixture)
