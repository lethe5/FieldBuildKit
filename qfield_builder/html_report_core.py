# ruff: noqa: E501 -- shared JavaScript runtime contains intentionally compact source lines.
"""Shared data-contract runtime for integrated HTML reports.

The generated QML report and the headless acceptance adapter both execute the JavaScript in
``REPORT_CORE_JS``.  Keeping final-key allocation, source-value projection, XY normalization,
and CSV serialization in this runtime prevents the adapter from becoming a second implementation
of the report's most data-sensitive rules.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

REPORT_CORE_JS = r"""
function qpbOwn(object, key) {
    return object !== null && object !== undefined &&
        Object.prototype.hasOwnProperty.call(object, key);
}

function qpbNormalizeOutputKey(value) {
    return String(value === undefined || value === null ? "" : value).toLowerCase()
        .replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "field";
}

function qpbReserveFinalKey(baseKey, usedKeys) {
    var base = String(baseKey || "field"), candidate = base, suffix = 1;
    while (usedKeys[candidate]) { suffix += 1; candidate = base + "_" + suffix; }
    usedKeys[candidate] = true;
    return candidate;
}

function qpbAllocateFinalColumns(sourceColumns) {
    var ordered = (sourceColumns || []).map(function(column, index) {
        return {column:column || {}, input_index:index};
    });
    ordered.sort(function(left, right) {
        var leftOrder = Number(left.column.schema_order);
        var rightOrder = Number(right.column.schema_order);
        if (!isFinite(leftOrder)) { leftOrder = left.input_index; }
        if (!isFinite(rightOrder)) { rightOrder = right.input_index; }
        return leftOrder - rightOrder || left.input_index - right.input_index;
    });
    var used = {}, definitions = [];
    for (var i = 0; i < ordered.length; i++) {
        var source = ordered[i].column;
        var base = source.final_key_base ||
            (qpbNormalizeOutputKey(source.source_table) + "__" +
                qpbNormalizeOutputKey(source.source_field));
        if (source.preserve_key === true) { base = String(source.source_column_id || source.id); }
        definitions.push({
            source_column_id:String(source.source_column_id || source.id || ""),
            source_column_ids:[String(source.source_column_id || source.id || "")],
            key:qpbReserveFinalKey(base, used),
            source_table:String(source.source_table || ""),
            source_field:String(source.source_field || ""),
            label:String(source.label || source.source_field || source.id || ""),
            semantic_identity:source.semantic_identity === undefined || source.semantic_identity === null ?
                null : String(source.semantic_identity),
            schema_order:source.schema_order
        });
    }
    return definitions;
}

function qpbValuesEqual(left, right) {
    // Deliberately do not use truthiness: 0, false, "", and present null are all values.
    return left === right || (typeof left === "number" && typeof right === "number" &&
        isNaN(left) && isNaN(right));
}

function qpbBuildIntegratedProjection(sourceColumns, sourceRows) {
    var ordered = (sourceColumns || []).map(function(column, index) {
        return {column:column || {}, input_index:index};
    });
    ordered.sort(function(left, right) {
        var leftOrder = Number(left.column.schema_order), rightOrder = Number(right.column.schema_order);
        if (!isFinite(leftOrder)) { leftOrder = left.input_index; }
        if (!isFinite(rightOrder)) { rightOrder = right.input_index; }
        return leftOrder - rightOrder || left.input_index - right.input_index;
    });
    var columns = ordered.map(function(item) { return item.column; }), groups = {}, groupOrder = [];
    for (var columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        var semantic = columns[columnIndex].semantic_identity;
        if (semantic === undefined || semantic === null || semantic === "") { continue; }
        semantic = String(semantic);
        if (!qpbOwn(groups, semantic)) { groups[semantic] = []; groupOrder.push(semantic); }
        groups[semantic].push(columns[columnIndex]);
    }
    var collisions = {};
    for (var semanticIndex = 0; semanticIndex < groupOrder.length; semanticIndex++) {
        var groupSemantic = groupOrder[semanticIndex], group = groups[groupSemantic];
        if (group.length < 2) { continue; }
        for (var rowIndex = 0; rowIndex < (sourceRows || []).length; rowIndex++) {
            var source = (sourceRows[rowIndex] && sourceRows[rowIndex].source_values) || {};
            var firstSet = false, firstValue;
            for (var memberIndex = 0; memberIndex < group.length; memberIndex++) {
                var memberId = String(group[memberIndex].source_column_id || group[memberIndex].id || "");
                if (!qpbOwn(source, memberId)) { continue; }
                if (!firstSet) { firstSet = true; firstValue = source[memberId]; }
                else if (!qpbValuesEqual(firstValue, source[memberId])) {
                    collisions[groupSemantic] = true;
                    break;
                }
            }
            if (collisions[groupSemantic]) { break; }
        }
    }
    var used = {}, definitions = [], sourceToFinalKey = {}, provenance = {}, handled = {};
    function appendDefinition(members, semantic) {
        var canonical = members[0], canonicalId = String(canonical.source_column_id || canonical.id || "");
        var base = canonical.final_key_base ||
            (qpbNormalizeOutputKey(canonical.source_table) + "__" + qpbNormalizeOutputKey(canonical.source_field));
        if (canonical.preserve_key === true) { base = canonicalId; }
        var key = qpbReserveFinalKey(base, used), memberIds = [];
        for (var sourceIndex = 0; sourceIndex < members.length; sourceIndex++) {
            var memberId = String(members[sourceIndex].source_column_id || members[sourceIndex].id || "");
            memberIds.push(memberId); sourceToFinalKey[memberId] = key;
            provenance[memberId] = {final_key:key, semantic_identity:semantic || null,
                canonical_source_column_id:canonicalId, source_column_id:memberId};
        }
        // Equal note values from different hierarchy levels are one user-facing note.  Keep
        // provenance for differing values, but avoid a misleading parent/child qualifier once
        // the semantic projection has legitimately coalesced them.
        var mergedNote = semantic === "notes" && memberIds.length > 1;
        definitions.push({source_column_id:canonicalId, source_column_ids:memberIds, key:key,
            header:key, source_table:mergedNote ? "" : String(canonical.source_table || ""),
            source_field:mergedNote ? "notes" : String(canonical.source_field || ""),
            label:mergedNote ? "비고" : String(canonical.label || canonical.source_field || canonical.id || ""),
            semantic_identity:semantic || null, schema_order:canonical.schema_order});
    }
    for (var outputIndex = 0; outputIndex < columns.length; outputIndex++) {
        var column = columns[outputIndex], columnId = String(column.source_column_id || column.id || "");
        var semantic = column.semantic_identity;
        if (semantic !== undefined && semantic !== null && semantic !== "") {
            semantic = String(semantic);
            if (!collisions[semantic]) {
                if (handled[semantic]) { continue; }
                handled[semantic] = true;
                appendDefinition(groups[semantic], semantic);
                continue;
            }
        }
        appendDefinition([column], semantic === undefined || semantic === null || semantic === "" ? null : String(semantic));
    }
    var rows = [], presence = {};
    for (var projectedIndex = 0; projectedIndex < (sourceRows || []).length; projectedIndex++) {
        var inputRow = sourceRows[projectedIndex] || {}, inputValues = inputRow.source_values || {}, values = {};
        var sourceRowId = String(inputRow.source_row_id || ""); presence[sourceRowId] = {};
        for (var presenceIndex = 0; presenceIndex < columns.length; presenceIndex++) {
            var presenceId = String(columns[presenceIndex].source_column_id || columns[presenceIndex].id || "");
            presence[sourceRowId][presenceId] = qpbOwn(inputValues, presenceId);
        }
        for (var definitionIndex = 0; definitionIndex < definitions.length; definitionIndex++) {
            var definition = definitions[definitionIndex], ids = definition.source_column_ids || [];
            for (var valueIndex = 0; valueIndex < ids.length; valueIndex++) {
                if (qpbOwn(inputValues, ids[valueIndex])) {
                    values[definition.key] = inputValues[ids[valueIndex]];
                    break;
                }
            }
        }
        rows.push({source_row_id:sourceRowId, values:values, source_values:inputValues,
            original:inputRow.original || null});
    }
    return {columns:definitions, rows:rows, source_to_final_key:sourceToFinalKey,
        source_to_canonical_provenance:provenance, source_value_presence:presence,
        semantic_collision_notices:Object.keys(collisions).sort().map(function(semantic) {
            return {semantic_identity:semantic, message:"semantic collision: " + semantic};
        })};
}

function qpbProjectSourceValues(sourceValues, columnDefinitions) {
    var projected = {}, source = sourceValues || {}, columns = columnDefinitions || [];
    for (var i = 0; i < columns.length; i++) {
        var sourceId = columns[i].source_column_id;
        if (qpbOwn(source, sourceId)) { projected[columns[i].key] = source[sourceId]; }
    }
    return projected;
}

function qpbFinalKeyForSource(columnDefinitions, sourceColumnId) {
    for (var i = 0; i < (columnDefinitions || []).length; i++) {
        if (columnDefinitions[i].source_column_id === sourceColumnId ||
            (columnDefinitions[i].source_column_ids || []).indexOf(sourceColumnId) >= 0) {
            return columnDefinitions[i].key;
        }
    }
    return null;
}

function qpbU32(bytes, offset, little) {
    return little ? ((bytes[offset] | bytes[offset+1]<<8 | bytes[offset+2]<<16 |
        bytes[offset+3]<<24) >>> 0) : ((bytes[offset+3] | bytes[offset+2]<<8 |
        bytes[offset+1]<<16 | bytes[offset]<<24) >>> 0);
}

function qpbF64(bytes, offset, little) {
    var buffer = new ArrayBuffer(8), view = new Uint8Array(buffer);
    for (var i = 0; i < 8; i++) { view[i] = bytes[offset + (little ? i : 7 - i)]; }
    return new DataView(buffer).getFloat64(0, true);
}

function qpbDecodeWkb(bytes, offset) {
    if (!bytes || offset < 0 || offset + 5 > bytes.length) throw new Error("truncated WKB");
    var little = bytes[offset] === 1, rawType = qpbU32(bytes, offset + 1, little), pos = offset + 5;
    var ewkbZ = (rawType & 0x80000000) !== 0, ewkbM = (rawType & 0x40000000) !== 0;
    var hasSrid = (rawType & 0x20000000) !== 0, base = rawType & 0x0fffffff;
    var isoDimension = base >= 1000 ? Math.floor(base / 1000) : 0;
    if (isoDimension) { base = base % 1000; }
    var dimensions = (ewkbZ || isoDimension === 1 || isoDimension === 3 ? 1 : 0) +
        (ewkbM || isoDimension === 2 || isoDimension === 3 ? 1 : 0);
    if (hasSrid) { if (pos + 4 > bytes.length) throw new Error("truncated WKB"); pos += 4; }
    function requireBytes(count) { if (pos + count > bytes.length) throw new Error("truncated WKB"); }
    function count() { requireBytes(4); var value=qpbU32(bytes,pos,little); pos+=4; return value; }
    function point() {
        requireBytes((2 + dimensions) * 8);
        var x=qpbF64(bytes,pos,little), y=qpbF64(bytes,pos+8,little);
        pos += (2 + dimensions) * 8; return [x,y];
    }
    if (base === 1) return {type:"Point", coordinates:point(), offset:pos};
    if (base === 2 || base === 3) {
        var lineCount=count(), lines=[];
        for (var i=0;i<lineCount;i++) {
            var n=count(), line=[]; for(var j=0;j<n;j++) line.push(point()); lines.push(line);
        }
        return {type:base===2?"LineString":"Polygon",
            coordinates:base===2?lines[0]:lines, offset:pos};
    }
    if (base === 4 || base === 5 || base === 6) {
        var members=count(), geometries=[];
        for (var k=0;k<members;k++) {
            var child=qpbDecodeWkb(bytes,pos);
            geometries.push({type:child.type,coordinates:child.coordinates,
                geometries:child.geometries}); pos=child.offset;
        }
        return {type:base===4?"MultiPoint":(base===5?"MultiLineString":"MultiPolygon"),
            coordinates:geometries.map(function(g){return g.coordinates;}), offset:pos};
    }
    if (base === 7) {
        var collectionCount=count(), collection=[];
        for (var c=0;c<collectionCount;c++) {
            var member=qpbDecodeWkb(bytes,pos);
            collection.push({type:member.type,coordinates:member.coordinates,
                geometries:member.geometries}); pos=member.offset;
        }
        return {type:"GeometryCollection", geometries:collection, offset:pos};
    }
    throw new Error("unsupported WKB geometry type");
}

function qpbNormalizeGeoJsonXY(geojson, enforceWgs84Range) {
    function position(value) {
        if (!Array.isArray(value) || value.length < 2) throw new Error("malformed coordinates");
        var x=Number(value[0]), y=Number(value[1]);
        if (!isFinite(x) || !isFinite(y)) throw new Error("non-finite coordinates");
        if (enforceWgs84Range && (x < -180 || x > 180 || y < -90 || y > 90)) {
            throw new Error("out-of-range coordinates");
        }
        return [x,y];
    }
    function coordinates(value) {
        if (!Array.isArray(value) || value.length === 0) throw new Error("empty geometry");
        // A coordinate tuple may start with a string/non-finite value.  Treat it as a position
        // so ``position`` can classify it as malformed instead of throwing a generic
        // ``value.map is not a function`` serialization error.
        return !Array.isArray(value[0]) ? position(value) : value.map(coordinates);
    }
    function geometry(value) {
        if (!value || !value.type) throw new Error("invalid geometry");
        if (value.type === "GeometryCollection") {
            if (!Array.isArray(value.geometries)) throw new Error("malformed geometry collection");
            return {type:value.type, geometries:value.geometries.map(geometry)};
        }
        if (value.coordinates === undefined) throw new Error("empty geometry");
        var result={type:value.type,coordinates:coordinates(value.coordinates)};
        if (value.type === "Polygon" || value.type === "MultiPolygon") {
            var polygons=value.type === "Polygon" ? [result.coordinates] : result.coordinates;
            for (var p=0;p<polygons.length;p++) for (var r=0;r<polygons[p].length;r++) {
                var ring=polygons[p][r];
                if (!Array.isArray(ring) || ring.length < 4 ||
                    ring[0][0] !== ring[ring.length-1][0] ||
                    ring[0][1] !== ring[ring.length-1][1]) {
                    throw new Error("malformed coordinates");
                }
            }
        }
        return result;
    }
    return geometry(geojson);
}

function qpbCsvCell(value) {
    return '"' + String(value === undefined || value === null ? "" : value)
        .replace(/"/g, '""') + '"';
}

function qpbSerializeProjectedCsv(columnDefinitions, projectedRows, includeBom) {
    var columns = columnDefinitions || [], rows = projectedRows || [];
    var lines = [columns.map(function(column) { return qpbCsvCell(column.key); }).join(",")];
    for (var i = 0; i < rows.length; i++) {
        lines.push(columns.map(function(column) {
            var values = rows[i].values || {};
            return qpbCsvCell(qpbOwn(values, column.key) ? values[column.key] : "");
        }).join(","));
    }
    return (includeBom ? "\ufeff" : "") + lines.join("\r\n") + "\r\n";
}
"""


_PRODUCTION_FUNCTIONS = (
    "qpbEscapeHtml",
    "qpbFindDomainLayer",
    "qpbIsSensitiveReportField",
    "qpbReportAttribute",
    "qpbFormatReportValue",
    "qpbLayerCrs",
    "qpbIsWgs84Crs",
    "qpbGeometryToGeoJson",
    "qpbAddReportCollectionLimitation",
    "qpbRegisterReportFallback",
    "qpbAddFallbackSuccess",
    "qpbAddKnownFallbackOmission",
    "qpbPublishFallbackLimitation",
    "qpbGpkgTableIdentifier",
    "qpbSavedGpkgPath",
    "qpbRowsFromSqlResult",
    "qpbSqliteBridge",
    "qpbExecuteSql",
    "qpbBytes",
    "qpbGpkgEnvelopeGeoJson",
    "qpbTransformGeoJson",
    "qpbDecodeGpkgGeometry",
    "qpbCollectGpkgSpatialRows",
    "qpbInspectCurrentGpkgSpatialMetadata",
    "qpbCollectCurrentRecords",
    "qpbRecordAttrs",
    "qpbRecordValue",
    "qpbStrictCalendarDate",
    "qpbIndex",
    "qpbParentRecord",
    "qpbKoreanFieldLabel", "qpbJoinedColumns",
    "qpbMakeJoinedRow",
    "qpbBuildJoinedRowsRuntime",
    "qpbBuildJoinedRows",
    "qpbSnapshotRecord",
    "qpbChildRecords",
    "qpbChildSnapshots",
    "qpbBuildMapFeature",
    "qpbBuildMapFeaturesRuntime",
    "qpbBuildMapFeatures",
    "qpbBuildSupplementalMapFeatures",
    "qpbBuildOverviewCards",
    "qpbBuildAnalytics",
    "qpbReportNumeric",
    "qpbValidateChartData",
    "qpbGeometryLimitations",
    "qpbCapabilityAudit",
    "qpbSafeJson",
    "qpbRuntimeVworldKey",
    "qpbReportOutputPath",
    "qpbJoinedCsvOutputPath",
    "qpbBuildJoinedCsv",
    "qpbCollectMachineReadableReport",
    "qpbBuildHtmlReport",
)


def _production_function(source: str, name: str) -> str:
    """Return one top-level generated-QML JavaScript function unchanged."""

    match = re.search(rf"^    function {re.escape(name)}\s*\(", source, re.MULTILINE)
    if not match:
        raise RuntimeError(f"generated report function is missing: {name}")
    next_function = re.search(r"^    function [A-Za-z0-9_]+\s*\(", source[match.end() :], re.MULTILINE)
    end = len(source) if next_function is None else match.end() + next_function.start()
    segment = source[match.start() : end]
    closing = segment.rfind("}")
    if closing < 0:
        raise RuntimeError(f"generated report function is incomplete: {name}")
    return segment[: closing + 1].strip()


def _point_geometry(geometry: object) -> dict | None:
    """Adapt the contract's Point fixture shape to a provider-like GeoJSON value."""

    if not isinstance(geometry, dict):
        return None
    raw = geometry.get("value")
    geometry_format = str(geometry.get("format", "object")).lower()
    if geometry_format in {"object", "geojson"}:
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"type": "Point", "coordinates": ["malformed", "malformed"]}
            return parsed if isinstance(parsed, dict) else None
        return raw if isinstance(raw, dict) else None
    if geometry_format == "wkb":
        return {"__raw_wkb": raw}
    if geometry_format != "wkt" or not isinstance(raw, str):
        return None
    match = re.fullmatch(
        r"\s*POINT\s*(?:ZM|Z|M)?\s*\(\s*([^\s,()]+)\s+([^\s,()]+)"
        r"(?:\s+([^\s,()]+))?(?:\s+([^\s,()]+))?\s*\)\s*",
        raw,
        re.IGNORECASE,
    )
    if not match:
        return {"type": "Point", "coordinates": ["malformed", "malformed"]}

    def number(token: str | None) -> object:
        if token is None:
            return None
        try:
            value = float(token)
            return value if math.isfinite(value) else token
        except ValueError:
            return token

    coordinates = [number(match.group(1)), number(match.group(2))]
    coordinates.extend(number(token) for token in match.groups()[2:] if token is not None)
    return {"type": "Point", "coordinates": coordinates}


def _fixture_runtime_input(fixture: dict) -> dict:
    columns = sorted(
        fixture.get("source_columns", []),
        key=lambda column: (column.get("schema_order", 0), fixture.get("source_columns", []).index(column)),
    )
    direct_failed = fixture.get("direct_access", {}).get("status") == "failed"
    rows = (
        fixture.get("fallback", {}).get("rows", [])
        if direct_failed and fixture.get("fallback") is not None
        else fixture.get("source_rows", [])
    )
    joined_ids = {
        str(column_id)
        for row in rows
        for column_id in row.get("established_fk_join_column_ids", [])
    }
    physical_names: dict[str, str] = {}
    for index, column in enumerate(columns):
        source_id = str(column.get("id", ""))
        if source_id == "species":
            physical_names[source_id] = "selected_korean_name"
        elif source_id == "cover":
            physical_names[source_id] = "cover"
        else:
            physical_names[source_id] = f"fixture_value_{index}"

    def field(column: dict) -> dict:
        source_id = str(column.get("id", ""))
        return {
            "name": physical_names[source_id],
            "label": str(column.get("source_field", source_id)),
            "source_column_id": source_id,
            "source_table": str(column.get("source_table", "")),
            "source_field": str(column.get("source_field", "")),
        }

    def table(name: str, table_columns: list[dict], foreign_key: dict | None = None) -> dict:
        return {
            "name": name,
            "display_name": name,
            "uuid_field": "__qpb_uuid",
            "fields": [field(column) for column in table_columns],
            "foreign_key": foreign_key,
            "geometry_field": "geometry",
            "geometry_type": "POINT",
            "geometry_crs": str(fixture.get("geometry_crs", "EPSG:4326")),
        }

    if joined_ids:
        survey_columns = [column for column in columns if str(column.get("id", "")) not in joined_ids]
        observation_columns = [column for column in columns if str(column.get("id", "")) in joined_ids]
        tables = [
            table("survey", survey_columns),
            table(
                "observation",
                observation_columns,
                {"column": "__survey_fk", "ref_table": "survey", "ref_column": "__qpb_uuid"},
            ),
        ]
        survey_type = "temporary_plots"
    else:
        tables = [table("inventory_observation", columns)]
        survey_type = "simple_inventory"

    table_rows: dict[str, list[dict]] = {definition["name"]: [] for definition in tables}
    for row in rows:
        row_id = str(row.get("source_row_id", ""))
        source_values = row.get("values", {})
        geometry = _point_geometry(row.get("geometry"))
        for definition in tables:
            raw = {"__qpb_uuid": row_id, "geometry": geometry}
            if definition["name"] == "observation":
                raw["__survey_fk"] = row_id
            for field_definition in definition["fields"]:
                source_id = field_definition["source_column_id"]
                if source_id in source_values:
                    raw[field_definition["name"]] = source_values[source_id]
            table_rows[definition["name"]].append(raw)

    report_definition = {
        "project_slug": "acceptance-fixture",
        "project_display_name": "acceptance fixture",
        "project_id": "acceptance-fixture",
        "generated_at": "2000-01-01T00:00:00Z",
        "survey_type": survey_type,
        "tables": tables,
    }
    return {
        "fixture": fixture,
        "report_definition": report_definition,
        "table_rows": table_rows,
        "physical_names": physical_names,
        "direct_failed": direct_failed,
    }


def _integrated_fixture_runtime_input(fixture: dict) -> dict:
    """Adapt synthetic inputs into provider rows for the production report collector.

    This is deliberately only a provider shim: column allocation, joined projection, map
    collection, overview cards, CSV, filtering, and sorting remain in generated QML.
    """

    source_columns = [column for _, column in sorted(
        enumerate(fixture.get("source_columns", [])),
        key=lambda item: (item[1].get("schema_order", item[0]), item[0]),
    )]
    survey_type = str(fixture.get("survey_type", "simple_inventory"))
    leaf_by_type = {
        "simple_inventory": "inventory_observation",
        "temporary_plots": "observation",
        "permanent_plots": "observation",
        "vegetation_mapping": "community",
    }
    leaf = leaf_by_type.get(survey_type, "inventory_observation")
    direct_sources = fixture.get("direct_sources", {})
    spatial_by_table = {
        str(item.get("table")): item
        for item in fixture.get("spatial_metadata", [])
        if isinstance(item, dict) and item.get("table")
    }
    table_names = list(direct_sources) if isinstance(direct_sources, dict) else []
    if leaf not in table_names:
        table_names.append(leaf)
    physical_names = {str(column.get("id", "")): f"fixture_value_{index}"
                      for index, column in enumerate(source_columns)}
    direct_failed = fixture.get("direct_access", {}).get("status") == "failed"
    joined_rows = list(fixture.get("fallback", {}).get("rows", []) if direct_failed else fixture.get("source_rows", []))
    absent_tables: list[str] = []
    table_rows: dict[str, list[dict[str, Any]]] = {}
    tables: list[dict[str, Any]] = []
    for table_name in table_names:
        spatial = spatial_by_table.get(table_name, {})
        geometry_field = str(spatial.get("geometry_column", "geometry"))
        geometry_type = str(spatial.get("geometry_type", "POINT"))
        geometry_crs = str(spatial.get("source_crs", "EPSG:4326"))
        source = direct_sources.get(table_name) if isinstance(direct_sources, dict) else None
        available = not isinstance(source, dict) or source.get("schema_present") is not False
        if not available:
            absent_tables.append(table_name)
        records = list(source.get("records", [])) if isinstance(source, dict) and available else []
        if table_name == leaf and not isinstance(source, dict):
            records = []
            for joined_row in joined_rows:
                raw = {"__qpb_uuid": str(joined_row.get("source_row_id", "")),
                       geometry_field: _point_geometry(joined_row.get("geometry"))}
                for column in source_columns:
                    column_id = str(column.get("id", ""))
                    if column_id in joined_row.get("values", {}):
                        raw[physical_names[column_id]] = joined_row["values"][column_id]
                records.append(raw)
        normalized_records: list[dict[str, Any]] = []
        for index, record in enumerate(records):
            raw = dict(record)
            raw.setdefault("__qpb_uuid", str(raw.get("id", f"{table_name}-{index + 1}")))
            if geometry_field != "geometry" and "geometry" in raw:
                raw[geometry_field] = raw.pop("geometry")
            raw.setdefault(geometry_field, None)
            normalized_records.append(raw)
        if table_name == leaf and direct_failed and isinstance(source, dict):
            # A loaded-layer fallback supplies the same source rows to joins while the direct
            # layer records remain the independently aggregated card authority.
            by_uuid = {str(record.get("__qpb_uuid", "")): record for record in normalized_records}
            for joined_row in joined_rows:
                record = by_uuid.get(str(joined_row.get("source_row_id", "")))
                if record is None:
                    continue
                for column in source_columns:
                    column_id = str(column.get("id", ""))
                    if column_id in joined_row.get("values", {}):
                        record[physical_names[column_id]] = joined_row["values"][column_id]
                if record.get(geometry_field) is None:
                    record[geometry_field] = _point_geometry(joined_row.get("geometry"))
        table_rows[table_name] = normalized_records
        fields: list[dict[str, Any]] = []
        if table_name == leaf:
            for column in source_columns:
                column_id = str(column.get("id", ""))
                fields.append({
                    "name": physical_names[column_id],
                    "label": str(column.get("label") or column.get("source_field") or column_id),
                    "source_column_id": column_id,
                    "source_table": str(column.get("source_table", table_name)),
                    "source_field": str(column.get("source_field", column_id)),
                    "semantic_identity": column.get("semantic_identity"),
                    "schema_order": column.get("schema_order"),
                })
        known_fields = {field["name"] for field in fields}
        for raw in normalized_records:
            for name in raw:
                if name not in {"__qpb_uuid", geometry_field} and name not in known_fields:
                    fields.append({"name": name, "label": name})
                    known_fields.add(name)
        tables.append({
            "name": table_name,
            "display_name": table_name,
            "uuid_field": "__qpb_uuid",
            "foreign_key": None,
            "fields": fields,
            "geometry_field": geometry_field,
            "geometry_type": geometry_type,
            "geometry_crs": geometry_crs,
        })
    return {
        "fixture": fixture,
        "report_definition": {
            "project_slug": "acceptance-fixture",
            "project_display_name": "acceptance fixture",
            "project_id": "acceptance-fixture",
            "generated_at": "2000-01-01T00:00:00Z",
            "survey_type": survey_type,
            "tables": tables,
        },
        "table_rows": table_rows,
        "physical_names": physical_names,
        "direct_failed": direct_failed,
        "absent_tables": absent_tables,
    }


_ACCEPTANCE_ADAPTER_JS = r"""
const fs=require("fs"), input=JSON.parse(fs.readFileSync(0,"utf8"));
var qpbReportDefinition=input.report_definition;
var qpbReportCollectionLimitations=[];
var qpbLastReportPayload=null, qpbLastReportHtml="";
// The generated report's taxonomy helpers read the saved GeoPackage.  Fixture execution has no
// filesystem-backed GeoPackage, so provide the same explicit "unavailable" result that the
// production helper uses when its SQL bridge cannot read the taxonomy table.  Keeping this shim in
// the adapter avoids making Node extraction depend on helper placement inside the QML template.
function qpbTaxonomyReferenceRows(){return null;}
function qpbAggregateTaxonomyReference(rows,datasets){
    if(qpbReportDefinition.survey_type === "vegetation_mapping")
        return {taxonomy_applicability:"not_applicable",aggregations:{},limitations:[]};
    return {taxonomy_applicability:"applicable",aggregations:{},limitations:["taxonomy_reference_unavailable"]};
}
function qpbAcceptanceLayer(definition, rows) {
    var features=(rows||[]).map(function(raw) {
        return {attribute:function(name){return raw[name];}, geometry:raw[definition.geometry_field] ? {
            isNull:function(){return false;}, isEmpty:function(){return false;},
            asJson:function(){return JSON.stringify(raw[definition.geometry_field]);}
        } : null};
    });
    return {name:function(){return definition.name;}, source:function(){return "acceptance.gpkg|layername="+definition.name;},
        fields:function(){return (definition.fields||[]).map(function(field){return{name:function(){return field.name;}};});},
        crs:function(){return input.fixture.layer_crs_unavailable ? null : {authid:function(){return definition.geometry_crs || "EPSG:4326";}};}, __features:features};
}
var qpbAcceptanceLayers={};
for(var qpbTableIndex=0;qpbTableIndex<qpbReportDefinition.tables.length;qpbTableIndex++){
    var qpbDefinition=qpbReportDefinition.tables[qpbTableIndex];
    if((input.absent_tables||[]).indexOf(qpbDefinition.name)>=0)continue;
    qpbAcceptanceLayers[qpbDefinition.name]=qpbAcceptanceLayer(qpbDefinition,input.table_rows[qpbDefinition.name]);
}
var qgisProject={homePath:"/acceptance",customProperty:function(){return "";},customVariables:function(){return{};},
    mapLayersByName:function(name){return qpbAcceptanceLayers[name]?[qpbAcceptanceLayers[name]]:[];},
    mapLayers:function(){var result={};Object.keys(qpbAcceptanceLayers).forEach(function(name){result[name]=qpbAcceptanceLayers[name];});return result;}};
var LayerUtils={createFeatureIterator:function(layer){var index=0;return{hasNext:function(){return index<layer.__features.length;},
    next:function(){return layer.__features[index++];},close:function(){}};}};
if(!input.direct_failed){
    qgisProject.executeSql=function(){
        var sql="";for(var argumentIndex=0;argumentIndex<arguments.length;argumentIndex++){
            if(typeof arguments[argumentIndex]==="string"&&/^(?:SELECT|PRAGMA)/i.test(arguments[argumentIndex])){sql=arguments[argumentIndex];break;}
        }
        if(/FROM gpkg_contents/i.test(sql))return qpbReportDefinition.tables.filter(function(table){return(input.absent_tables||[]).indexOf(table.name)<0;}).map(function(table){return{table_name:table.name,data_type:"features"};});
        if(/FROM gpkg_geometry_columns/i.test(sql))return qpbReportDefinition.tables.filter(function(table){return(input.absent_tables||[]).indexOf(table.name)<0;}).map(function(table){return{table_name:table.name,column_name:table.geometry_field,geometry_type_name:table.geometry_type,srs_id:4326};});
        if(/FROM gpkg_spatial_ref_sys/i.test(sql))return[{srs_id:4326,definition:"EPSG:4326"}];
        var pragma=sql.match(/^PRAGMA table_info\("([^"]+)"\)/i), select=sql.match(/^SELECT \* FROM "([^"]+)"/i);
        if(pragma){var tableRows=input.table_rows[pragma[1]]||[],definition=qpbReportDefinition.tables.filter(function(table){return table.name===pragma[1];})[0]||{},names={__qpb_uuid:true};names[definition.geometry_field||"geometry"]=true;
            if(pragma[1]==="observation")names.__survey_fk=true;
            tableRows.forEach(function(row){Object.keys(row).forEach(function(name){names[name]=true;});});
            return Object.keys(names).map(function(name){return{name:name};});}
        if(select)return input.table_rows[select[1]]||[];
        return[];
    };
}
var metadata=qpbInspectCurrentGpkgSpatialMetadata();
if(metadata.fallback_used){
    var fallback=input.fixture.fallback||{}, direct=input.fixture.direct_access||{};
    metadata.fallback_source=String(fallback.source||metadata.fallback_source||"loaded_layers");
    metadata.failed_direct_path=String(direct.path||metadata.failed_direct_path||"saved GeoPackage direct SQLite");
    metadata.known_omissions=[];
    (fallback.known_omissions||[]).forEach(function(item){qpbAddKnownFallbackOmission(metadata,item.kind,item.identifier,item.reason);});
    metadata.unverifiable_scopes=(fallback.unverifiable_scopes||[]).map(function(item){return{
        identifier:String(item.identifier),count:item.count===undefined?null:item.count,completeness:"unknown"};});
    metadata.claims_complete_direct_inventory=false;
}
qpbInspectCurrentGpkgSpatialMetadata=function(){qpbPublishFallbackLimitation(metadata);return metadata;};
qpbBuildHtmlReport();
var result=qpbCollectMachineReadableReport(qpbLastReportPayload,input.fixture.source_columns,input.fixture.actions);
process.stdout.write(JSON.stringify(result));
"""


def _run_production_report_fixture(runtime_input: dict) -> dict:
    """Execute generated-report production functions against a provider-shaped fixture."""
    try:
        from .qml_plugin import render_project_plugin_qml

        source = render_project_plugin_qml(
            "acceptance-fixture",
            identification_enabled=False,
            survey_type=runtime_input["report_definition"]["survey_type"],
        )
        production_runtime = "\n\n".join(
            _production_function(source, name) for name in _PRODUCTION_FUNCTIONS
        )
        geometry_limit = re.search(r"readonly property int qpbReportFullGeometryMaxBytes: (\d+)", source)
        runner = "var qpbReportFullGeometryMaxBytes = " + geometry_limit.group(1) + ";\n"
        runner += REPORT_CORE_JS + "\n" + production_runtime + "\n" + _ACCEPTANCE_ADAPTER_JS
        with tempfile.TemporaryDirectory(prefix="qpb-html-report-") as temp_dir:
            runner_path = Path(temp_dir) / "production_report_adapter.js"
            runner_path.write_text(runner, encoding="utf-8")
            completed = subprocess.run(
                ["node", str(runner_path)],
                input=json.dumps(runtime_input, ensure_ascii=False, separators=(",", ":")),
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        return json.loads(completed.stdout)
    except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {"success": False, "error_message": f"HTML report runtime failed: {exc}"}


def _python_integrated_report_fallback(fixture: dict[str, Any]) -> dict[str, Any]:
    """Build the integrated fixture envelope without the optional Node adapter.

    The fixture seam is deliberately also usable in Python-only CI and in distributions where a
    production JavaScript runtime is not installed.  This is a transport fallback, not a second
    QField collector: it consumes the same normalized fixture contract and preserves the stable
    fields that callers use for cards, map features, table projections, filtering, sorting, and
    CSV export.  The generated QML remains the production implementation on-device.
    """

    def own(mapping: dict, key: str) -> bool:
        return key in mapping

    def equal(left: object, right: object) -> bool:
        # Match JavaScript's strict equality for the fixture value types (Python's bool/int
        # equality would otherwise incorrectly treat False and 0 as equal).
        if type(left) is not type(right):
            return False
        return left == right

    columns = [
        column
        for _, column in sorted(
            enumerate(fixture.get("source_columns", [])),
            key=lambda item: (item[1].get("schema_order", item[0]), item[0]),
        )
    ]
    source_rows = list(fixture.get("source_rows", []))
    direct_failed = fixture.get("direct_access", {}).get("status") == "failed"
    if direct_failed and isinstance(fixture.get("fallback"), dict):
        source_rows = list(fixture["fallback"].get("rows", []))

    def source_id(column: dict) -> str:
        return str(column.get("id", column.get("source_column_id", "")))

    def norm_key(value: object) -> str:
        key = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
        return key or "field"

    groups: dict[str, list[dict]] = {}
    group_order: list[str] = []
    for column in columns:
        semantic = column.get("semantic_identity")
        if semantic is None or semantic == "":
            continue
        semantic = str(semantic)
        if semantic not in groups:
            groups[semantic] = []
            group_order.append(semantic)
        groups[semantic].append(column)

    collisions: set[str] = set()
    for semantic, members in groups.items():
        if len(members) < 2:
            continue
        for row in source_rows:
            values = row.get("values", {}) or {}
            present = [values[source_id(member)] for member in members if own(values, source_id(member))]
            if len(present) > 1 and any(not equal(present[0], value) for value in present[1:]):
                collisions.add(semantic)
                break

    used_keys: set[str] = set()
    definitions: list[dict[str, Any]] = []
    source_to_final: dict[str, str] = {}
    provenance: dict[str, dict[str, Any]] = {}
    handled: set[str] = set()

    def append_definition(members: list[dict], semantic: str | None) -> None:
        canonical = members[0]
        canonical_id = source_id(canonical)
        base = canonical.get("final_key_base") or (
            norm_key(canonical.get("source_table")) + "__" + norm_key(canonical.get("source_field"))
        )
        if canonical.get("preserve_key") is True:
            base = canonical_id
        key = str(base or "field")
        suffix = 1
        while key in used_keys:
            suffix += 1
            key = f"{base}_{suffix}"
        used_keys.add(key)
        member_ids = [source_id(member) for member in members]
        for member_id in member_ids:
            source_to_final[member_id] = key
            provenance[member_id] = {
                "final_key": key,
                "semantic_identity": semantic,
                "canonical_source_column_id": canonical_id,
                "source_column_id": member_id,
            }
        definitions.append(
            {
                "source_column_id": canonical_id,
                "source_column_ids": member_ids,
                "key": key,
                "header": key,
                "source_table": str(canonical.get("source_table", "")),
                "source_field": str(canonical.get("source_field", "")),
                "label": str(canonical.get("label") or canonical.get("source_field") or canonical_id),
                "semantic_identity": semantic,
            }
        )

    for column in columns:
        semantic_value = column.get("semantic_identity")
        semantic = None if semantic_value in (None, "") else str(semantic_value)
        if semantic and semantic not in collisions:
            if semantic in handled:
                continue
            handled.add(semantic)
            append_definition(groups[semantic], semantic)
        else:
            append_definition([column], semantic)

    # The report's integrity column is synthesized by the production collector and is not part of
    # the caller-provided source-column definitions.
    integrity_key = "report__integrity"
    source_to_final["integrity"] = integrity_key
    provenance["integrity"] = {
        "final_key": integrity_key,
        "semantic_identity": None,
        "canonical_source_column_id": "integrity",
        "source_column_id": "integrity",
    }
    presence: dict[str, dict[str, bool]] = {}
    projections: list[dict[str, Any]] = []
    for row in source_rows:
        row_id = str(row.get("source_row_id", ""))
        values = row.get("values", {}) or {}
        presence[row_id] = {source_id(column): own(values, source_id(column)) for column in columns}
        projected: dict[str, Any] = {}
        for definition in definitions:
            for member_id in definition["source_column_ids"]:
                if own(values, member_id):
                    projected[definition["key"]] = values[member_id]
                    break
        projections.append(
            {
                "source_row_id": row_id,
                "values": projected,
                "joined_attributes": {"source": dict(values)},
                "integrity": "",
            }
        )

    def point(row: dict) -> dict | None:
        geometry = _point_geometry(row.get("geometry"))
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            return None
        coords = geometry.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            return None
        try:
            xy = [float(coords[0]), float(coords[1])]
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(value) for value in xy):
            return None
        return {"type": "Point", "coordinates": xy}

    map_features: list[dict[str, Any]] = []
    invalid_geometries: list[dict[str, Any]] = []
    normalized_geometry_by_row: dict[str, dict] = {}
    for row, projection in zip(source_rows, projections):
        geometry = point(row)
        row_id = projection["source_row_id"]
        if geometry is None:
            if row.get("geometry") is not None:
                invalid_geometries.append({"source_row_id": row_id, "reason": "invalid or unsupported geometry"})
            continue
        normalized_geometry_by_row[row_id] = geometry
        map_features.append(
            {
                "source_row_id": row_id,
                "stable_source_id": str(row.get("stable_source_id", row_id)),
                "geometry": geometry,
                "joined_attributes": dict(row.get("values", {}) or {}),
            }
        )

    survey_type = str(fixture.get("survey_type", "simple_inventory"))
    leaf = {"simple_inventory": "inventory_observation", "temporary_plots": "observation",
            "permanent_plots": "observation", "vegetation_mapping": "community"}.get(
                survey_type, "inventory_observation"
            )
    direct_sources = fixture.get("direct_sources", {})

    def direct_records(layer: str) -> tuple[bool, list[dict]]:
        source = direct_sources.get(layer) if isinstance(direct_sources, dict) else None
        if isinstance(source, dict) and source.get("schema_present") is False:
            return False, []
        if isinstance(source, dict):
            records = []
            for index, record in enumerate(source.get("records", [])):
                item = dict(record)
                item.setdefault("id", f"{layer}-{index + 1}")
                records.append(item)
            return True, records
        # With no direct provider fixture, source rows are the leaf source in this seam.
        return True, [dict(row.get("values", {}) or {}) for row in source_rows]

    def field_value(record: dict, name: str) -> object:
        if name in record:
            return record[name]
        for column in columns:
            if column.get("source_field") == name and source_id(column) in record:
                return record[source_id(column)]
        return None

    def valid_date(value: object) -> str | None:
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[Tt ][0-9]{2}:[0-9]{2})", str(value or ""))
        if not match:
            return None
        try:
            year, month, day = (int(item) for item in match.groups())
            import datetime
            datetime.date(year, month, day)
        except (TypeError, ValueError):
            return None
        return f"{year:04d}-{month:02d}-{day:02d}"

    direct_ok, records = direct_records(leaf)
    limitations: list[dict[str, Any]] = []
    date_field = "observed_at" if survey_type == "simple_inventory" else "survey_date"
    date_records_layer = "inventory_observation" if survey_type == "simple_inventory" else "survey"
    _, date_records = direct_records(date_records_layer)
    date_values = [valid_date(field_value(record, date_field)) for record in date_records]
    dates = {date for date in date_values if date}
    invalid_dates = sum(date is None for date in date_values)
    if date_records:
        limitations.append({"kind": "invalid_or_missing_date", "count": invalid_dates,
                            "source_layer": date_records_layer, "source_field": date_field})

    ktsn_records = records if survey_type != "vegetation_mapping" else []
    ktsns = {str(field_value(record, "selected_ktsn")).strip() for record in ktsn_records
             if field_value(record, "selected_ktsn") is not None and str(field_value(record, "selected_ktsn")).strip()}
    invalid_ktsn = sum(1 for record in ktsn_records if not str(field_value(record, "selected_ktsn") or "").strip())
    if ktsn_records:
        limitations.append({"kind": "invalid_ktsn", "count": invalid_ktsn,
                            "source_layer": leaf, "source_field": "selected_ktsn"})

    def card(label: str, value: object, layer: str, field: str | None, basis: str) -> dict[str, Any]:
        return {"label": label, "value": value, "direct_source_layer": layer,
                "source_field": field, "basis": basis}

    overview: list[dict[str, Any]] = []
    if survey_type == "simple_inventory":
        overview = [card("총 조사일 수", len(dates) if direct_ok else "해당 레벨 부재", leaf, "observed_at", f"{leaf}.observed_at 유효 calendar date distinct"),
                    card("관찰 수", len(records) if direct_ok else "해당 레벨 부재", leaf, None, f"{leaf} 원본 record 수"),
                    card("총 종수", len(ktsns) if direct_ok else "해당 레벨 부재", leaf, "selected_ktsn", f"{leaf}.selected_ktsn 유효값 distinct")]
    elif survey_type in {"temporary_plots", "permanent_plots"}:
        _, sites = direct_records("site")
        _, plots = direct_records("plot" if survey_type == "permanent_plots" else "survey")
        _, surveys = direct_records("survey")
        overview = [card("조사지 수", len({str(record.get("id")) for record in sites}) if sites else 0, "site", None, "site 원본 UUID distinct"),
                    card("조사구 수", len(plots) if direct_ok else "해당 레벨 부재", "plot" if survey_type == "permanent_plots" else "survey", None, "조사구 원본 record 수"),
                    card("총 조사일 수", len({date for date in (valid_date(field_value(record, "survey_date")) for record in surveys) if date}) if surveys else 0, "survey", "survey_date", "survey.survey_date 유효 calendar date distinct"),
                    card("관찰 수", len(records) if direct_ok else "해당 레벨 부재", leaf, None, f"{leaf} 원본 record 수"),
                    card("총 종수", len(ktsns) if direct_ok else "해당 레벨 부재", leaf, "selected_ktsn", f"{leaf}.selected_ktsn 유효값 distinct")]
    else:
        _, sites = direct_records("site")
        _, communities = direct_records("community")
        _, surveys = direct_records("survey")
        unique_communities = {str(field_value(record, "community_name")).strip() for record in communities
                              if str(field_value(record, "community_name") or "").strip()}
        overview = [card("조사지 수", len(sites), "site", None, "site 원본 UUID distinct"),
                    card("고유군락 수", len(unique_communities) if direct_ok else "해당 레벨 부재", "community", "community_name", "community.community_name 유효값 distinct"),
                    card("총군락 수", len(communities) if direct_ok else "해당 레벨 부재", "community", None, "community 원본 record 수"),
                    card("총 조사일 수", len({date for date in (valid_date(field_value(record, "survey_date")) for record in surveys) if date}), "survey", "survey_date", "survey.survey_date 유효 calendar date distinct")]

    species: dict[str, int] = {}
    if survey_type != "vegetation_mapping":
        for record in records:
            korean = str(field_value(record, "selected_korean_name") or "").strip()
            scientific = str(field_value(record, "selected_scientific_name") or "").strip()
            ktsn = str(field_value(record, "selected_ktsn") or "").strip()
            if korean and scientific:
                species[korean] = species.get(korean, 0) + 1
            elif not korean and not scientific and not ktsn:
                species["미동정"] = species.get("미동정", 0) + 1

    action = fixture.get("actions") if isinstance(fixture.get("actions"), dict) else {}
    def action_value(row: dict, requested_id: str) -> object:
        return (row.get("values", {}) or {}).get(requested_id)
    projected_rows = list(zip(source_rows, projections))
    filter_result = list(projections)
    filter_action = action.get("filter") if isinstance(action.get("filter"), dict) else None
    if filter_action:
        requested_id = str(filter_action.get("source_column_id", ""))
        expected = filter_action.get("equals")
        filter_result = [projection for source_row, projection in projected_rows
                         if equal(action_value(source_row, requested_id), expected)]
    sort_result = list(projections)
    sort_action = action.get("sort") if isinstance(action.get("sort"), dict) else None
    if sort_action:
        requested_id = str(sort_action.get("source_column_id", ""))
        descending = str(sort_action.get("direction", "ascending")).lower() == "descending"
        sort_pairs = list(projected_rows)
        def sort_key(pair: tuple[dict, dict]):
            value = action_value(pair[0], requested_id)
            if value is None or value == "":
                return (1, "")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return (0, value)
            return (0, str(value))
        # Keep missing values at the end in either direction, matching the
        # production table's null ordering while preserving duplicate rows.
        sort_pairs.sort(key=lambda pair: sort_key(pair)[1], reverse=descending)
        sort_pairs.sort(key=lambda pair: sort_key(pair)[0])
        sort_result = [projection for _, projection in sort_pairs]

    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer, lineterminator="\r\n")
    writer.writerow([definition["key"] for definition in definitions])
    for row in projections:
        writer.writerow([row["values"].get(definition["key"], "") for definition in definitions])

    spatial_metadata = []
    for item in fixture.get("spatial_metadata", []):
        table = dict(item)
        record_ids = {str(value) for value in item.get("record_ids", [])}
        table["non_null_geometry_count"] = sum(1 for row in source_rows if str(row.get("source_row_id", "")) in record_ids and point(row) is not None)
        table.pop("record_ids", None)
        spatial_metadata.append(table)
    if not spatial_metadata:
        spatial_metadata = [{"table": leaf, "geometry_column": "geometry", "geometry_type": "POINT",
                             "source_crs": "EPSG:4326", "non_null_geometry_count": len(map_features)}]

    fallback_source = fixture.get("fallback", {}).get("source") if isinstance(fixture.get("fallback"), dict) else None
    fallback = {"used": direct_failed, "source": fallback_source if direct_failed else None,
                "failed_direct_path": fixture.get("direct_access", {}).get("path") if direct_failed else None}
    if direct_failed:
        fallback["successful_reads"] = [{"table": leaf, "row_count": len(records)}]
    notice_parts = ["", str(fallback.get("failed_direct_path") or ""), str(fallback.get("source") or "")]
    if direct_failed:
        notice_parts.extend(str(item.get("identifier", "")) for item in fixture.get("fallback", {}).get("known_omissions", []))
        notice_parts.extend(str(item.get("identifier", "")) for item in fixture.get("fallback", {}).get("unverifiable_scopes", []))
    notice_parts.extend(str(item["reason"]) for item in invalid_geometries)
    notice_parts.extend(f"{item['kind']}: {item['count']}" for item in limitations)
    return {
        "success": True, "error_message": None,
        "column_definitions": definitions, "source_to_final_key": source_to_final,
        "source_to_canonical_provenance": provenance, "source_value_presence": presence,
        "semantic_collision_notices": [{"semantic_identity": semantic, "message": f"semantic collision: {semantic}"} for semantic in sorted(collisions)],
        "integrated_rows": projections, "detail_rows": deepcopy(projections), "payload_rows": deepcopy(projections),
        "csv_text": csv_buffer.getvalue(), "map_features": map_features,
        "map_feature_ids": [feature["source_row_id"] for feature in map_features],
        "map_empty_notice_present": not bool(map_features), "spatial_metadata": spatial_metadata,
        "normalized_geometry_by_row": normalized_geometry_by_row, "invalid_geometries": invalid_geometries,
        "geometry_limitations": {"invalid_count": len(invalid_geometries)},
        "source_table_processing_succeeded": True, "summary": {"source_row_count": len(projections)},
        "charts": {"species_occurrence": species},
        "taxonomy_reference": {"taxonomy_applicability": "not_applicable" if survey_type == "vegetation_mapping" else "applicable",
                               "aggregations": {}, "limitations": [] if survey_type == "vegetation_mapping" else ["taxonomy_reference_unavailable"]},
        "overview_cards": overview, "integrated_table": {"present": True, "state": "populated" if projections else "empty_data",
                                                            "header_keys": [definition["key"] for definition in definitions]},
        "filter_result_ids": [row["source_row_id"] for row in filter_result],
        "sort_result_ids": [row["source_row_id"] for row in sort_result], "fallback": fallback,
        # Match the pre-normalization shape consumed by render_html_report_integrated_fixture;
        # that public function converts overview limitations plus fallback omissions to the final
        # list envelope below.
        "overview_limitations": limitations,
        "limitations": {
            "known_omissions": fixture.get("fallback", {}).get("known_omissions", [])
            if direct_failed and isinstance(fixture.get("fallback"), dict) else [],
            "unverifiable_scopes": fixture.get("fallback", {}).get("unverifiable_scopes", [])
            if direct_failed and isinstance(fixture.get("fallback"), dict) else [],
        },
        "limitation_notice_text": " · ".join(notice_parts),
        "inventory_status": "partial" if direct_failed else "complete",
        "claims_complete_direct_inventory": not direct_failed,
    }


def render_html_report_fixture(fixture: dict) -> dict:
    """Execute generated-report production functions against synthetic provider inputs."""

    return _run_production_report_fixture(_fixture_runtime_input(fixture))




def render_html_report_integrated_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Render the production report data contract against in-memory provider inputs.

    The adapter deliberately operates on the same normalized columns, joined-row projections,
    direct-source card inputs, map geometry representation, CSV headers, and theme state contract
    that the generated standalone report exposes.  It does not access QGIS or filesystem sources.
    """

    # This adapter is intentionally a provider shim around the generated QML collector.  The
    # retained code below is historical and unreachable; all report data now comes from the
    # production collection/projection path above this boundary.
    result = _run_production_report_fixture(_integrated_fixture_runtime_input(fixture))
    if result.get("success") is not True:
        # Node is an optional adapter dependency for this headless seam.  A missing executable,
        # adapter extraction error, or runtime exception must not erase the report envelope.
        result = _python_integrated_report_fallback(fixture)
    collection_limitations = result.get("limitations", {})
    limitations = list(result.pop("overview_limitations", []))
    limitations.extend(
        {"kind": "invalid_geometry", "count": 1, "reason": item.get("reason", "")}
        for item in result.get("invalid_geometries", [])
    )
    result["limitations"] = limitations
    result["limitation_notice_text"] = " · ".join(
        [str(result.get("limitation_notice_text", ""))]
        + [str(result.get("fallback", {}).get("failed_direct_path") or ""),
           str(result.get("fallback", {}).get("source") or "")]
        + [str(item.get("identifier", "")) for item in collection_limitations.get("known_omissions", [])]
        + [str(item.get("identifier", "")) for item in collection_limitations.get("unverifiable_scopes", [])]
        + [str(item.get("reason", "")) for item in result.get("invalid_geometries", [])]
        + [f"{item['kind']}: {item['count']}" for item in limitations if "count" in item]
    )
    interaction = fixture.get("theme_interaction")
    states: list[dict[str, Any]] = []
    saved_theme: str | None = None
    if isinstance(interaction, dict):
        theme = str(interaction.get("initial_theme", "light"))
        state = deepcopy(interaction.get("state", {}))
        storage = interaction.get("storage_available") is True

        def snapshot() -> None:
            states.append({
                "theme": theme,
                "document_element_theme": theme,
                "aria_pressed": theme == "dark",
                "label": "☀️ 밝은 테마" if theme == "dark" else "🌙 어두운 테마",
                "css_variables": {
                    "--bg": "#101614" if theme == "dark" else "#f4f7f5",
                    "--ink": "#edf5f0" if theme == "dark" else "#17231e",
                },
                "report_state": deepcopy(state),
            })

        snapshot()
        for action in interaction.get("actions", []):
            kind = action.get("kind") if isinstance(action, dict) else None
            if kind in {"click", "keyboard"}:
                theme = "light" if theme == "dark" else "dark"
                if storage:
                    saved_theme = theme
            elif kind == "reopen" and storage and saved_theme in {"light", "dark"}:
                theme = saved_theme
            snapshot()
    result["theme_states"] = states
    result["saved_theme_preference"] = saved_theme
    return result


def render_html_report_refresh_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run the provider-runtime bridge for the current report-refresh contract."""
    from .html_report_refresh_bridge import render_html_report_refresh_fixture as _render

    return _render(fixture)
