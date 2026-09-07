"""Project re-validation (FR-QPB-094, Section 17/18; HARNESS_CONTRACT.md's `validate_project`).

Re-opens an *existing* generated project and runs the integrity checks Section 12/18 requires
`VALIDATION_REPORT.json` to confirm. Used both for the moved-folder case (NFR-QPB-021,
AC-QPB-010/024) and for re-running manifest/missing-file detection against a deliberately mutated
folder (AC-QPB-027/031).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import schemas
from .gpkg_functions import register_gpkg_functions
from .manifest import MANIFEST_FILENAME
from .paths import is_malformed_attachment_path

VALIDATION_REPORT_FILENAME = "VALIDATION_REPORT.json"


def _open_gpkg_readonly(gpkg_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(gpkg_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    register_gpkg_functions(conn)
    return conn


def _read_manifest(project_dir: str) -> dict | None:
    manifest_path = Path(project_dir) / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _check_foreign_keys(conn: sqlite3.Connection) -> list[dict]:
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    return [
        {
            "code": "foreign_key_violation",
            "message": f"Foreign key violation in table {row[0]!r} (rowid {row[1]}): {row}",
        }
        for row in violations
    ]


def _check_cover_range(conn: sqlite3.Connection, survey_type: str) -> list[dict]:
    if survey_type not in ("temporary_plots", "permanent_plots"):
        return []
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='observation';"
    ).fetchall()
    if not tables:
        return []
    rows = conn.execute(
        "SELECT observation_id, cover FROM observation WHERE cover < 0 OR cover > 100;"
    ).fetchall()
    return [
        {
            "code": "cover_out_of_range",
            "message": f"observation {obs_id!r} has cover={cover!r}, outside 0-100.",
        }
        for obs_id, cover in rows
    ]


def _check_attachments(
    conn: sqlite3.Connection, project_dir: str, survey_type: str
) -> tuple[list[dict], list[str]]:
    """Returns (issues, all_currently_referenced_relative_paths).

    Covers both Type-1 inline photo-path columns and the Type 2/3 related photo tables, per
    DR-QPB-012/AC-QPB-009. A record with a NULL path is never examined (zero related photos is
    valid, per Decision Log D-23) — only existing, non-null path values are checked.
    """
    issues: list[dict] = []
    referenced: list[str] = []
    photo_fields = schemas.photo_path_fields_for(survey_type)

    for table_name, columns in photo_fields.items():
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;", (table_name,)
        ).fetchone()
        if not table_exists:
            continue
        uuid_col = schemas.get_schema(survey_type)[table_name].uuid_pk
        for col in columns:
            rows = conn.execute(
                f'SELECT "{uuid_col}", "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL;'
            ).fetchall()
            for record_id, raw_path in rows:
                is_bad, shape = is_malformed_attachment_path(raw_path, project_dir=project_dir)
                if is_bad:
                    issues.append(
                        {
                            "code": "invalid_attachment_path",
                            "message": (
                                f"{table_name}.{col} for {uuid_col}={record_id!r}: stored path "
                                f"{raw_path!r} is not a valid relative attachment path ({shape})."
                            ),
                        }
                    )
                    continue
                referenced.append(raw_path)
                target = Path(project_dir) / raw_path
                if not target.exists():
                    issues.append(
                        {
                            "code": "broken_attachment_reference",
                            "message": (
                                f"{table_name}.{col} for {uuid_col}={record_id!r}: referenced "
                                f"attachment file {raw_path!r} is missing from the project folder."
                            ),
                        }
                    )
    return issues, referenced


def _check_manifest_declared_files(
    project_dir: str, manifest: dict | None, gpkg_path: str
) -> list[dict]:
    issues: list[dict] = []
    root = Path(project_dir)
    if not Path(gpkg_path).exists():
        issues.append(
            {
                "code": "missing_manifest_file",
                "message": (
                    f"Required GeoPackage file is missing from the project folder: {gpkg_path!r}"
                ),
            }
        )
    if manifest is not None:
        for rel in manifest.get("required_files", {}).get("basemap", []) or []:
            if rel and not (root / rel).exists():
                issues.append(
                    {
                        "code": "missing_manifest_file",
                        "message": (
                            f"Required basemap file declared in MANIFEST.json is missing: {rel!r}"
                        ),
                    }
                )
        qgs_rel = manifest.get("required_files", {}).get("qgs_project")
        if qgs_rel and not (root / qgs_rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": (
                        "Required .qgs project file declared in MANIFEST.json is missing: "
                        f"{qgs_rel!r}"
                    ),
                }
            )
    return issues


def _check_missing_attachments_against_manifest(
    referenced_paths: list[str], project_dir: str
) -> list[dict]:
    """Dynamic, current-state manifest-level check (AC-QPB-027's "attachment" case): any
    currently-referenced attachment path missing from disk is reported as missing_manifest_file,
    independent of the (build-time-static) MANIFEST.json file list, since attachments are
    frequently added after delivery during field data collection."""
    issues = []
    root = Path(project_dir)
    for rel in referenced_paths:
        if not (root / rel).exists():
            issues.append(
                {
                    "code": "missing_manifest_file",
                    "message": f"Attachment file referenced by the project is missing: {rel!r}",
                }
            )
    return issues


_REQUIRED_LAYER_TREE_GROUPS = ("Survey data", "Reference", "Basemap")


def _visibility_is_checked(value) -> bool:
    """Return whether *value* is an actual QGIS/Qt checked value.

    QGIS normally returns a Python ``bool`` from ``itemVisibilityChecked``.  Some bindings expose
    the Qt checked enum instead.  Do not use truthiness here: strings such as ``"false"`` and
    arbitrary objects are not evidence that a layer is visible and must fail closed.
    """
    if type(value) is bool:
        return value is True

    try:
        from qgis.PyQt.QtCore import Qt
    except ImportError:
        return False

    checked = getattr(Qt, "Checked", None)
    if checked is None:
        check_state = getattr(Qt, "CheckState", None)
        checked = getattr(check_state, "Checked", None) if check_state is not None else None
    return checked is not None and type(value) is type(checked) and value == checked


def _layer_tree_visibility_issues(project) -> list[dict]:
    """Validate the generated project's required layer-tree visibility contract.

    This intentionally inspects the live, re-opened ``QgsProject`` rather than the XML text.  A
    layer can be valid and present in ``project.mapLayers()`` while its legend node is absent or
    unchecked; that is precisely the failure mode D-91/E-QPB-018 must catch before promotion.
    """
    issues: list[dict] = []
    try:
        map_layers = dict(project.mapLayers())
    except Exception as exc:  # noqa: BLE001 - inability to verify is a hard validation failure.
        return [
            {
                "code": "layer_tree_visibility_unverified",
                "message": f"Unable to inspect successfully-created map layers: {exc}",
            }
        ]
    # An empty map-layer collection is not a valid verification result.  In particular, do not
    # let a lightweight XML-only double bypass the required group checks: a real generated project
    # always has at least one layer, and an empty/uninspectable project must fail closed.
    if not map_layers:
        issues.append(
            {
                "code": "layer_tree_visibility_unverified",
                "message": "Generated project exposes no map layers to verify for visibility.",
            }
        )
    try:
        root = project.layerTreeRoot()
    except Exception as exc:  # noqa: BLE001 - inability to verify is a hard validation failure.
        return [
            {
                "code": "layer_tree_visibility_unverified",
                "message": f"Unable to inspect the generated layer tree: {exc}",
            }
        ]

    groups = {}
    for group_name in _REQUIRED_LAYER_TREE_GROUPS:
        finder = getattr(root, "findGroup", None)
        if not callable(finder):
            issues.append(
                {
                    "code": "layer_tree_visibility_unverified",
                    "message": "QGIS layer-tree root does not expose findGroup().",
                }
            )
            break
        try:
            group = finder(group_name)
        except Exception as exc:  # noqa: BLE001
            group = None
            issues.append(
                {
                    "code": "layer_tree_visibility_unverified",
                    "message": f"Unable to inspect layer-tree group {group_name!r}: {exc}",
                }
            )
        if group is None:
            issues.append(
                {
                    "code": "layer_tree_group_missing",
                    "message": f"Required layer-tree group {group_name!r} is missing.",
                }
            )
            continue
        groups[group_name] = group
        checked_getter = getattr(group, "itemVisibilityChecked", None)
        if not callable(checked_getter):
            issues.append(
                {
                    "code": "layer_tree_group_invalid",
                    "message": (
                        f"Required layer-tree group {group_name!r} cannot be checked for "
                        "visibility."
                    ),
                }
            )
        else:
            try:
                checked = checked_getter()
                if not _visibility_is_checked(checked):
                    issues.append(
                        {
                            "code": "layer_tree_group_unchecked",
                            "message": f"Required layer-tree group {group_name!r} is unchecked.",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                issues.append(
                    {
                        "code": "layer_tree_group_invalid",
                        "message": f"Unable to verify group {group_name!r} visibility: {exc}",
                    }
                )

    # Index every layer node under the required groups.  Recursion is deliberate: QGIS can add
    # intermediate sub-groups without changing the contract that each created layer belongs to
    # one of the three top-level groups.
    nodes_by_layer_id: dict[str, list[tuple[str, object]]] = {}

    def walk(node, group_name: str) -> None:
        children_getter = getattr(node, "children", None)
        if not callable(children_getter):
            issues.append(
                {
                    "code": "layer_tree_group_invalid",
                    "message": f"Layer-tree group {group_name!r} cannot expose its children.",
                }
            )
            return
        try:
            children = list(children_getter())
        except Exception as exc:  # noqa: BLE001
            issues.append(
                {
                    "code": "layer_tree_visibility_unverified",
                    "message": f"Unable to inspect children of group {group_name!r}: {exc}",
                }
            )
            return
        for node_child in children:
            layer_id_getter = getattr(node_child, "layerId", None)
            if callable(layer_id_getter):
                try:
                    layer_id = layer_id_getter()
                except Exception as exc:  # noqa: BLE001
                    issues.append(
                        {
                            "code": "layer_tree_node_invalid",
                            "message": f"Unable to read a layer-tree node in {group_name!r}: {exc}",
                        }
                    )
                    continue
                if not isinstance(layer_id, str) or not layer_id.strip():
                    issues.append(
                        {
                            "code": "layer_tree_node_invalid",
                            "message": f"Layer-tree node in {group_name!r} has no valid layer ID.",
                        }
                    )
                    continue
                nodes_by_layer_id.setdefault(layer_id, []).append((group_name, node_child))
                checked_getter = getattr(node_child, "itemVisibilityChecked", None)
                if not callable(checked_getter):
                    issues.append(
                        {
                            "code": "layer_tree_node_invalid",
                            "message": (
                                f"Layer-tree node {layer_id!r} in {group_name!r} cannot be "
                                "checked for visibility."
                            ),
                        }
                    )
                else:
                    try:
                        checked = checked_getter()
                    except Exception as exc:  # noqa: BLE001
                        issues.append(
                            {
                                "code": "layer_tree_node_invalid",
                                "message": f"Unable to verify layer {layer_id!r} visibility: {exc}",
                            }
                        )
                    else:
                        layer_getter = getattr(node_child, "layer", None)
                        layer = layer_getter() if callable(layer_getter) else None
                        is_hidden_lookup_raster = bool(
                            layer is not None
                            and layer.customProperty(
                                "fieldbuildkit/probability_raster", False
                            )
                        )
                        if not _visibility_is_checked(checked) and not is_hidden_lookup_raster:
                            issues.append(
                                {
                                    "code": "layer_tree_node_unchecked",
                                    "message": (
                                        f"Layer {layer_id!r} in {group_name!r} is unchecked/hidden."
                                    ),
                                }
                            )
            else:
                # A child without layerId may be a nested group.  Recurse when it has children;
                # otherwise it is an invalid node and cannot be associated with a created layer.
                if callable(getattr(node_child, "children", None)):
                    walk(node_child, group_name)
                else:
                    issues.append(
                        {
                            "code": "layer_tree_node_invalid",
                            "message": f"Invalid child node in layer-tree group {group_name!r}.",
                        }
                    )

    for group_name, group in groups.items():
        walk(group, group_name)

    for layer_id, layer in map_layers.items():
        if not isinstance(layer_id, str) or not layer_id.strip():
            issues.append(
                {
                    "code": "layer_tree_node_invalid",
                    "message": "A successfully-created map layer has no valid layer ID.",
                }
            )
            continue
        if not nodes_by_layer_id.get(layer_id):
            name_value = getattr(layer, "name", None)
            layer_name = name_value() if callable(name_value) else (name_value or layer_id)
            issues.append(
                {
                    "code": "layer_tree_node_missing",
                    "message": (
                        f"Successfully-created layer {layer_name!r} ({layer_id!r}) has no "
                        "layer-tree node under Survey data/Reference/Basemap."
                    ),
                }
            )
    return issues


def _open_with_pyqgis_direct(qgs_path: str) -> tuple[bool, bool, list[dict | str]] | None:
    """Real-QGIS open check, run in-process. Returns None if PyQGIS is not importable here."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None

    from .qgis_bridge import ensure_qgis_application

    ensure_qgis_application()

    project = QgsProject()
    opened = project.read(qgs_path)
    bad_layers = [lyr for lyr in project.mapLayers().values() if not lyr.isValid()]
    visibility_issues = _layer_tree_visibility_issues(project) if opened else []
    return (
        bool(opened) and not bad_layers and not visibility_issues,
        bool(bad_layers) or bool(visibility_issues),
        visibility_issues,
    )


def _open_with_pyqgis(qgs_path: str) -> tuple[bool, bool, list[dict | str]]:
    """Compatibility name for standalone structure validation; does not invoke QGIS."""
    from .template_project import inspect_project

    return inspect_project(qgs_path)


def validate_project(project_dir: str) -> dict:
    """Wraps re-opening/validating an existing generated project. See HARNESS_CONTRACT.md."""
    root = Path(project_dir)
    qgs_candidates = list(root.glob("*.qgs"))
    gpkg_candidates = list((root / "data").glob("*.gpkg")) or list(root.glob("*.gpkg"))
    manifest = _read_manifest(project_dir)

    issues: list[dict] = []

    gpkg_path = str(gpkg_candidates[0]) if gpkg_candidates else (
        str(root / manifest["required_files"]["geopackage"])
        if manifest and manifest.get("required_files", {}).get("geopackage")
        else ""
    )

    survey_type = manifest.get("survey_type") if manifest else None

    if gpkg_path and Path(gpkg_path).exists() and survey_type:
        conn = _open_gpkg_readonly(gpkg_path)
        try:
            issues += _check_foreign_keys(conn)
            issues += _check_cover_range(conn, survey_type)
            attachment_issues, referenced_paths = _check_attachments(conn, project_dir, survey_type)
            issues += attachment_issues
            issues += _check_missing_attachments_against_manifest(referenced_paths, project_dir)
        finally:
            conn.close()

    issues += _check_manifest_declared_files(
        project_dir, manifest, gpkg_path or "data/project.gpkg"
    )

    opens_ok, missing_layer, extra_warnings = (True, False, [])
    if qgs_candidates:
        opens_ok, missing_layer, extra_warnings = _open_with_pyqgis(str(qgs_candidates[0]))
    else:
        opens_ok, missing_layer = False, True
        extra_warnings = ["No .qgs project file was found in the project folder."]

    for warning in extra_warnings:
        if isinstance(warning, dict):
            issues.append(warning)
        else:
            issues.append({"code": "runtime_warning", "message": warning})

    # A pre-existing structural issue (broken FK, missing manifest file) also implies the project
    # should not be reported as opening cleanly, even if the PyQGIS-level open nominally succeeds.
    structural_blocking_codes = {
        "foreign_key_violation",
        "missing_manifest_file",
        "layer_tree_visibility_unverified",
        "layer_tree_group_missing",
        "layer_tree_group_invalid",
        "layer_tree_group_unchecked",
        "layer_tree_node_missing",
        "layer_tree_node_invalid",
        "layer_tree_node_unchecked",
    }
    if any(issue["code"] in structural_blocking_codes for issue in issues):
        opens_ok = False
    opens_ok = opens_ok and not issues

    return {
        "success": opens_ok,
        "validation_backend": "standalone",
        "structure_valid": opens_ok,
        "qgis_open_checked": False,
        "opens_without_repair_warning": None,
        "missing_layer_warning": missing_layer,
        "issues": issues,
    }


def write_validation_report(project_dir: str, report: dict) -> str:
    path = Path(project_dir) / VALIDATION_REPORT_FILENAME
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
