"""Build orchestration: the headless equivalent of completing the seven-step wizard (Section 6)
and clicking "Build" (FR-QPB-041).

Implements the atomicity/rollback rules (FR-QPB-032, E-QPB-008/009/010): all generation happens
in a temporary build directory; the final output directory is only ever created by an atomic
rename on success, and is never partially populated on failure or cancellation.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import zipfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from . import (
    canonical_reference,
    canonical_runtime_lookup,
    gpkg,
    gpkg_upload_reader,
    naming,
    probability_raster,
    qgis_worker,
    qml_plugin,
    reference_bundle,
    runtime,
    schemas,
    site_upload,
    symbol_styling,
    transfer_readme,
    validate,
    vworld,
)
from . import manifest as manifest_mod
from .credential_store import apply_plantnet_retention_policy, apply_retention_policy
from .errors import (
    BuildCancelledError,
    BuildError,
    InvalidGeometryBuildError,
    InvalidNameError,
    OfflineSizeExceededError,
    ReferenceDataInvalidError,
    ReferenceDataMissingError,
    RuntimeMissingError,
    VWorldApiKeyMissingError,
)
from .offline_estimate import DEFAULT_REPRESENTATIVE_TILE_BYTES, estimate_offline_basemap_size
from .resource_paths import repo_or_bundle_root
from .vworld_tiles import resolve_tile_fetcher
from .wkt import InvalidGeometryError, validate_geometry

REQUIRED_TOP_LEVEL_KEYS = ("project_display_name", "survey_type")
SITE_GEOMETRY_TYPE = "MULTIPOLYGON"
PLOT_GEOMETRY_TYPE = "POINT"
# The only supported source for a normal Type 1-3 build is the D-95 workbook.  This explicit
# compatibility value is deliberately not part of the wizard's normal config: it exists only for
# the legacy fixture/source harness. Existing generated projects are read by validation/report
# paths and do not need to pass through this build-time source compatibility branch.
LEGACY_REFERENCE_COMPATIBILITY_MODE = "legacy_reference_compatibility"

# E-QPB-008/FR-QPB-022a: an existing output folder must never be silently overwritten. The
# application has no built-in "replace with backup" operation, so the message must not imply
# one exists -- it must only instruct the user to choose a different project name or a
# different output folder.
_OUTPUT_DIR_EXISTS_MESSAGE = (
    "출력 폴더 '{output_dir}'가 이미 존재합니다. 다른 프로젝트 이름이나 다른 출력 폴더를 "
    "선택한 뒤 다시 시도해 주세요."
)


def _empty_result(**overrides) -> dict:
    result = {
        "success": False,
        "cancelled": False,
        "project_dir": None,
        "project_id": None,
        "project_slug": None,
        "qgs_path": None,
        "gpkg_path": None,
        "attachments_dir": None,
        "basemap_dir": None,
        "basemap_provider": None,
        "basemap_layer": None,
        "manifest_security_warning": None,
        "symbols_dir": None,
        "ktsn_lookup_table_name": None,
        "probability_raster_registration_count": 0,
        "stage_timings": [],
        "validation_report_path": None,
        "validation_report": None,
        "failed_stage": None,
        "error_code": None,
        "error_message": None,
    }
    result.update(overrides)
    return result


def _validate_config(config: dict) -> None:
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if not config.get(key):
            raise InvalidNameError(f"필수 설정 항목이 누락되었습니다: {key!r}", "missing_config")
    if config["survey_type"] not in schemas.SURVEY_TYPES:
        raise InvalidNameError(
            f"알 수 없는 survey_type입니다: {config['survey_type']!r}", "invalid_survey_type"
        )


def _epsg_code(crs: str | None) -> int | None:
    value = (crs or "").strip().upper()
    if not value.startswith("EPSG:"):
        return None
    try:
        return int(value.removeprefix("EPSG:"))
    except ValueError:
        return None


def _resolve_seed_sites(config: dict, work_dir: Path | None = None) -> list[dict]:
    if config.get("sites"):
        sites = config["sites"]
        for site in sites:
            try:
                validate_geometry(site["geom_wkt"], SITE_GEOMETRY_TYPE)
            except InvalidGeometryError as exc:
                # NOTE: the "invalid geometry" phrase below is deliberately kept in English --
                # tests/acceptance/qfield_project_builder/test_error_handling.py's
                # test_invalid_geometry_is_reported_not_silently_repaired (an approved acceptance
                # test this implementer must not modify) asserts this exact substring appears in
                # the reported error_message.
                raise InvalidGeometryBuildError(
                    f"사이트 '{site.get('site_name')}'의 geometry가 유효하지 않습니다 "
                    f"(invalid geometry): {exc}"
                ) from exc
        return sites
    upload = config.get("sites_upload")
    if upload:
        return _resolve_sites_from_upload(
            upload, storage_crs=config.get("storage_crs", "EPSG:4326"), work_dir=work_dir
        )
    return []


def _resolve_sites_from_upload(
    upload: dict, *, storage_crs: str = "EPSG:4326", work_dir: Path | None = None
) -> list[dict]:
    fmt = upload.get("format")
    encoding = upload.get("encoding", "cp949")
    site_name_field = (upload.get("attribute_mapping") or {}).get("site_name")
    if fmt not in ("zipped_shapefile", "shapefile", "gpkg"):
        raise BuildError("unsupported_upload_format", f"지원되지 않는 업로드 형식입니다: {fmt!r}")
    features_are_raw = fmt == "gpkg"

    # Keep GeoPackage geometries in binary form during the build.  Converting large boundary
    # layers to WKT (then parsing them back while writing) needlessly duplicates hundreds of
    # megabytes of coordinate text and was the source of the apparent infinite loading state.
    if fmt == "gpkg":
        source_path = upload["path"]
        source_info = gpkg_upload_reader.first_feature_layer_info(source_path)
        source_srs_id = source_info["srs_id"]
        target_srs_id = _epsg_code(storage_crs)
        if target_srs_id is not None and source_srs_id != target_srs_id:
            if work_dir is None:
                raise BuildError(
                    "crs_transform_required",
                    "업로드한 GeoPackage의 좌표계가 저장 좌표계와 달라 변환이 필요합니다. "
                    "프로젝트 생성 경로에서 다시 시도해 주세요.",
                )
            transformed_path = Path(work_dir) / "reprojected_upload.gpkg"
            qgis_worker.reproject_uploaded_gpkg_layer(
                source_path=source_path,
                source_layer_name=source_info["table_name"],
                destination_path=str(transformed_path),
                target_crs=storage_crs,
            )
            source_path = str(transformed_path)
        features = gpkg_upload_reader.read_first_feature_layer_raw(source_path)
    else:
        source_path = upload["path"]
        has_prj = site_upload.shapefile_has_prj(fmt, source_path)
        source_crs = upload.get("source_crs")
        if not has_prj and not source_crs:
            raise BuildError(
                "missing_upload_crs",
                "업로드한 SHP에 .prj 파일이 없습니다. 원본 좌표계의 EPSG 코드를 입력해 주세요.",
            )
        if source_crs:
            source_crs = site_upload.normalize_epsg_code(source_crs)
        normalized_storage_crs = (
            site_upload.normalize_epsg_code(storage_crs)
            if str(storage_crs).strip().upper().startswith("EPSG:")
            else storage_crs
        )
        # A source without .prj can stay on the dependency-free reader when the user explicitly
        # confirmed that it is already in the generated GeoPackage's storage CRS. Every other
        # case goes through QGIS so a projected SHP cannot be copied as mislabeled lon/lat.
        if not has_prj and source_crs == normalized_storage_crs:
            features = site_upload.read_upload_features(fmt, source_path, encoding)
        else:
            if work_dir is None:
                raise BuildError(
                    "crs_transform_required",
                    "업로드한 SHP의 좌표계를 저장 좌표계로 변환하려면 프로젝트 생성 경로에서 "
                    "다시 시도해 주세요.",
                )
            qgis_source_path = _materialize_shapefile_upload(source_path, fmt, work_dir)
            transformed_path = Path(work_dir) / "reprojected_shapefile_upload.gpkg"
            qgis_worker.reproject_uploaded_shapefile(
                source_path=qgis_source_path,
                destination_path=str(transformed_path),
                target_crs=storage_crs,
                source_crs=source_crs,
            )
            features = gpkg_upload_reader.read_first_feature_layer_raw(str(transformed_path))
            features_are_raw = True
    sites = []
    for feature in features:
        if features_are_raw:
            name = feature["attributes"].get(site_name_field) if site_name_field else None
            sites.append(
                {
                    "site_name": name or "가져온 사이트",
                    "geom_wkb": feature["geom_wkb"],
                    "geom_envelope": feature.get("envelope"),
                }
            )
        else:
            name = feature.attributes.get(site_name_field) if site_name_field else None
            sites.append({"site_name": name or "가져온 사이트", "geom_wkt": feature.geom_wkt})
    return sites


def _materialize_shapefile_upload(source_path: str, fmt: str, work_dir: Path) -> str:
    """Return a filesystem SHP path suitable for QGIS, unpacking a ZIP upload safely."""
    if fmt == "shapefile":
        return source_path
    if fmt != "zipped_shapefile":
        raise BuildError("unsupported_upload_format", f"지원되지 않는 SHP 형식입니다: {fmt!r}")

    try:
        with zipfile.ZipFile(source_path) as archive:
            names = archive.namelist()
            shp_name = next((name for name in names if name.lower().endswith(".shp")), None)
            if shp_name is None:
                raise BuildError(
                    "malformed_upload",
                    "업로드한 압축 Shapefile에 필수 구성 요소인 .shp 파일이 없습니다.",
                )
            stem = Path(shp_name).stem.lower()
            component_names = {
                Path(name).suffix.lower(): name
                for name in names
                if Path(name).stem.lower() == stem
                and Path(name).suffix.lower() in {".shp", ".shx", ".dbf", ".prj", ".cpg"}
            }
            extract_dir = Path(work_dir) / "uploaded_shapefile"
            extract_dir.mkdir(parents=True, exist_ok=True)
            output_stem = extract_dir / "uploaded"
            for suffix, member_name in component_names.items():
                (output_stem.with_suffix(suffix)).write_bytes(archive.read(member_name))
    except (OSError, zipfile.BadZipFile) as exc:
        raise BuildError(
            "malformed_upload", "업로드한 파일이 올바른 zip 압축 파일이 아닙니다."
        ) from exc

    return str(output_stem.with_suffix(".shp"))


def _resolve_seed_plots(config: dict) -> list[dict]:
    plots = config.get("plots") or []
    for plot in plots:
        try:
            validate_geometry(plot["geom_wkt"], PLOT_GEOMETRY_TYPE)
        except InvalidGeometryError as exc:
            raise InvalidGeometryBuildError(
                f"조사구 '{plot.get('plot_name')}'의 geometry가 유효하지 않습니다 "
                f"(invalid geometry): {exc}"
            ) from exc
    return plots


def _resolve_online_basemap(basemap_config: dict) -> dict:
    consent_accepted = bool(basemap_config.get("consent_accepted"))
    if not consent_accepted:
        return {"mode": "online", "consent_accepted": False}
    # Finding 1 fix (reviewer round, D-53/D-55): this call is only load-bearing for the *direct*,
    # in-process build_project() call the acceptance-test harness/unit tests use. In the real
    # desktop application, build_project() always runs inside a freshly spawned, separate OS
    # worker process (qfield_builder.worker_process.run_job_in_subprocess), whose own
    # credential_store copy was never unlocked there -- so this call always finds the store
    # locked and no-ops there, by design. The real persistence for "Remember this key" happens
    # earlier, in the UI process, via ReviewAndBuildPage._persist_remembered_keys() -- see
    # qfield_builder.credential_store's module docstring for the full explanation.
    apply_retention_policy(
        basemap_config.get("vworld_api_key", ""), bool(basemap_config.get("remember_key"))
    )
    return basemap_config


def _resolve_plantnet_config(plantnet_config: dict) -> dict:
    """FR-QPB-114-116/NFR-QPB-072 (Decision Log D-45): mirrors `_resolve_online_basemap`'s VWorld
    consent gate/retention-policy application, but for the Pl@ntNet key. When consent is
    declined, returns a config carrying only `consent_accepted: False` -- never the key -- so
    nothing downstream can accidentally embed it (FR-QPB-116); the retention policy (session-only,
    or the encrypted local `credentials.enc` file if "remember this key" was selected -- see
    Decision Log D-53) is only applied when consent is accepted, exactly mirroring the VWorld
    behavior above. See `_resolve_online_basemap`'s own comment (Finding 1 fix, reviewer round)
    for why this call is a real-subprocess-boundary no-op in the real desktop application.
    """
    consent_accepted = bool(plantnet_config.get("consent_accepted"))
    if not consent_accepted:
        return {"consent_accepted": False}
    apply_plantnet_retention_policy(
        plantnet_config.get("api_key", ""), bool(plantnet_config.get("remember_key"))
    )
    return plantnet_config


def _resolve_reference_data_dir(config: dict) -> str:
    """Section 13.3 (FR-QPB-105/112/113): resolves the reference-data source directory.

    `_test_reference_data_dir` (HARNESS_CONTRACT.md test seam) takes precedence; otherwise the
    `REFERENCE_DATA_DIR` environment variable (per `.env.example`); otherwise the default,
    version-controlled-scaffold location `storage/reference` relative to the repo/bundle root.
    """
    override = config.get("_test_reference_data_dir")
    if override:
        return str(override)
    env_value = os.environ.get("REFERENCE_DATA_DIR")
    if env_value:
        return env_value
    return str(repo_or_bundle_root() / "storage" / "reference")


def _legacy_reference_compatibility_requested(config: dict) -> bool:
    """Return whether this call explicitly opted into the pre-D-95 source contract.

    A legacy CSV/XLSX source is never inferred from a missing canonical workbook.  Keeping the
    check in a named predicate makes the compatibility boundary auditable and prevents the
    production wizard's ordinary config from reaching the old pipeline accidentally.
    """
    return config.get("reference_compatibility_mode") == LEGACY_REFERENCE_COMPATIBILITY_MODE


def _representative_tile_bytes(basemap_config: dict) -> float:
    tile_source = basemap_config.get("tile_source", "vworld")
    if isinstance(tile_source, dict) and "fake" in tile_source:
        return float(tile_source["fake"].get("tile_bytes", 5000))
    return DEFAULT_REPRESENTATIVE_TILE_BYTES


#: FR-QPB-121/AC-QPB-101 (Decision Log D-61/D-65): the project-relative folder a successfully
#: fetched Tabler icon SVG is embedded into (FR-QPB-121's own example: "a new `symbols/`
#: subfolder of the project root").
SYMBOLS_DIR_RELPATH = "symbols"


def _resolve_symbol_styling(config: dict, temp_project_dir: Path) -> str | None:
    """FR-QPB-120/FR-QPB-121 (Decision Log D-61/D-65): resolves this build's own, per-project,
    fresh symbol-styling choice (Step 6, FR-QPB-123) -- never persisted or reused from any other
    build (AC-QPB-104).

    Returns the project-relative path (POSIX-style, relative to `temp_project_dir`, e.g.
    ``"symbols/map-pin.svg"``) of an embedded SVG file once a Tabler icon was successfully
    fetched, or `None` when: the config omits `symbol_styling` entirely (the minimalist default,
    FR-QPB-120), `symbol_styling.mode` is `"minimalist"`, no `tabler_icon_name` was actually
    selected, or the single permitted SVG-fetch request (FR-QPB-011(d)) failed for any reason
    (no network, non-200 response, timeout) -- in every one of those cases, generation continues
    unblocked with the minimalist default (FR-QPB-121's own explicit fallback rule).
    """
    symbol_styling_config = config.get("symbol_styling") or {"mode": "minimalist"}
    if symbol_styling_config.get("mode") != "tabler_icon":
        return None

    icon_name = symbol_styling_config.get("tabler_icon_name") or ""
    if not symbol_styling.is_valid_icon_name_shape(icon_name):
        # No (or malformed) icon selected -- FR-QPB-121: "the user does not select an icon" ->
        # the minimalist default remains in use; never a build failure.
        return None

    fetch_result = symbol_styling.resolve_svg_fetch(symbol_styling_config, icon_name)
    if not fetch_result.get("success"):
        # FR-QPB-121: a failed fetch (no network, non-200, timeout) must not block generation --
        # the minimalist default remains the point-marker symbol.
        return None

    symbols_dir = temp_project_dir / SYMBOLS_DIR_RELPATH
    symbols_dir.mkdir(parents=True, exist_ok=True)
    svg_path = symbols_dir / f"{icon_name}.svg"
    svg_path.write_text(fetch_result.get("svg_content") or "", encoding="utf-8")
    return f"{SYMBOLS_DIR_RELPATH}/{icon_name}.svg"


def build_project(
    config: dict,
    output_dir: str,
    should_cancel: Callable[[], bool] | None = None,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    build_started = time.monotonic()
    stage_timings: list[dict[str, float | str]] = []

    def report_stage(stage: str) -> None:
        elapsed = round(time.monotonic() - build_started, 1)
        stage_timings.append({"stage": stage, "elapsed_seconds": elapsed})
        if progress_callback is not None:
            progress_callback({"stage": stage, "elapsed_seconds": elapsed})

    report_stage("생성 준비")
    if should_cancel is not None and should_cancel():
        return _empty_result(
            cancelled=True,
            error_code="cancelled",
            error_message="빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요.",
        )

    try:
        _validate_config(config)
    except BuildError as exc:
        return _empty_result(error_code=exc.error_code, error_message=exc.message)

    slug_result = naming.derive_project_slug(config["project_display_name"])
    if not slug_result.ok:
        return _empty_result(error_code=slug_result.error_code, error_message=slug_result.message)

    force_missing = bool(config.get("_test_force_missing_runtime", False))
    # FR-QPB-008 (manual QGIS-install-path override): threaded through from the wizard's own
    # session-local state (`ReviewAndBuildPage._manual_qgis_path`, set once a manual path has
    # already been verified via `runtime.check_runtime(manual_path=...)`), mirroring
    # `_test_force_missing_runtime`'s existing internal-config-key convention. This build actually
    # runs in a separate worker process (see `qfield_builder.worker_process`/`ui.build_worker`),
    # so automatic detection must be re-attempted there too -- the manual override has to travel
    # with the config for the build to actually succeed after a manual override, not just the
    # earlier UI-process-only `check_runtime()` gate in `ReviewAndBuildPage._start_build`.
    manual_qgis_path = config.get("_manual_qgis_path")
    runtime_info = runtime.check_runtime(force_missing=force_missing, manual_path=manual_qgis_path)
    if not runtime_info["available"]:
        return _empty_result(error_code="runtime_missing", error_message=runtime_info["message"])
    report_stage("내장 실행 환경 확인")

    output_path = Path(output_dir)
    if output_path.exists():
        return _empty_result(
            error_code="output_dir_exists",
            error_message=_OUTPUT_DIR_EXISTS_MESSAGE.format(output_dir=output_dir),
        )

    project_id = naming.new_project_id()
    project_slug = slug_result.slug
    survey_type = config["survey_type"]

    temp_root = Path(tempfile.mkdtemp(prefix=f"qpb-build-{project_slug}-"))
    temp_project_dir = temp_root / project_slug
    validation_report: dict | None = None
    validation_report_path: str | None = None

    try:
        if should_cancel is not None and should_cancel():
            raise BuildCancelledError(
                "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
            )
        report_stage("사이트 경계 읽기 및 좌표 변환")
        seed_sites = _resolve_seed_sites(config, work_dir=temp_root)
        seed_plots = _resolve_seed_plots(config) if survey_type == "permanent_plots" else []
        seed_temp_points = (
            config.get("temporary_plot_seed_points") or []
            if survey_type == "temporary_plots"
            else []
        )
        report_stage("입력 자료 확인")
        for point in seed_temp_points:
            try:
                validate_geometry(point["geom_wkt"], PLOT_GEOMETRY_TYPE)
            except InvalidGeometryError as exc:
                raise InvalidGeometryBuildError(
                    f"초기 조사 지점의 geometry가 유효하지 않습니다 (invalid geometry): {exc}"
                ) from exc

        temp_project_dir.mkdir(parents=True)
        attachments_dir = temp_project_dir / "attachments"
        attachments_dir.mkdir(parents=True)

        identification_enabled = bool(config.get("identification_enabled", False))
        # The accepted-name lookup table is bundled for every survey type.  Type 4 reuses the
        # same Korean-name picker for Type 4's dominant/subdominant species fields. Its widget
        # remains display-only, but samples probability at the community polygon centroid.
        is_types_1_to_3 = survey_type != "vegetation_mapping"
        identification_probability_enabled = identification_enabled
        requires_accepted_name_lookup = True
        plantnet_config: dict | None = None
        reference_data_dir: str | None = None
        canonical_ingest: dict | None = None
        canonical_source_path: Path | None = None
        probability_band_count: int | None = None
        canonical_runtime_resource: dict | None = None
        # FR-QPB-105 (further revised; Decision Log D-70): fail early, with a clear message,
        # before any heavier generation work, when the reference CSV is missing or lacks required
        # columns -- whenever *either* the identification subsystem is enabled (the original
        # trigger) *or* a project needs its accepted-name lookup table.
        if identification_enabled or requires_accepted_name_lookup:
            reference_data_dir = _resolve_reference_data_dir(config)
            reference_root = Path(reference_data_dir)
            configured_canonical = (
                config.get("canonical_reference_path")
                or config.get("_canonical_reference_path")
                or config.get("reference_workbook_path")
            )
            canonical_path_was_configured = bool(configured_canonical)
            canonical_source_path = Path(configured_canonical) if configured_canonical else (
                reference_root / "tables" / canonical_reference.CANONICAL_FILENAME
            )
            canonical_source_kind = str(
                config.get("canonical_source_kind") or "bundled_candidate"
            )
            if canonical_source_kind not in canonical_reference.ALLOWED_SOURCE_KINDS:
                allowed = ", ".join(sorted(canonical_reference.ALLOWED_SOURCE_KINDS))
                raise ReferenceDataInvalidError(
                    "canonical 참조 source_kind가 허용되지 않습니다: "
                    f"{canonical_source_kind!r}. 허용값은 {allowed}뿐입니다."
                )
            if canonical_path_was_configured and not canonical_source_path.is_file():
                raise ReferenceDataMissingError(
                    "확정한 canonical 참조 엑셀을 찾을 수 없습니다: "
                    f"{canonical_source_path}. 파일을 다시 선택하고 확인해 주세요."
                )
            if canonical_source_path.is_file():
                canonical_ingest = canonical_reference.ingest_canonical_workbook(
                    str(canonical_source_path),
                    source_kind=canonical_source_kind,
                    expected_sha256=config.get("canonical_reference_sha256"),
                )
                if not canonical_ingest.get("success"):
                    raise ReferenceDataInvalidError(
                        canonical_ingest.get("error_message")
                        or "canonical 참조 엑셀 검증에 실패했습니다."
                    )
                if is_types_1_to_3 or identification_enabled:
                    try:
                        reference_bundle._validate_raster_dir(
                            reference_root / reference_bundle.RASTER_DIR_RELATIVE_SUBPATH
                        )
                    except BuildError:
                        raise
            elif _legacy_reference_compatibility_requested(config):
                # This is an explicit pre-D-95 compatibility path only.  It is never reached by
                # the normal wizard config, and a configured-but-missing canonical candidate was
                # rejected above instead of being silently downgraded to this path.
                if not config.get("_test_reference_data_dir"):
                    raise ReferenceDataInvalidError(
                        "legacy reference compatibility에는 명시적인 reference-data directory가 "
                        "필요합니다. 새 프로젝트는 canonical .xlsx를 사용하세요."
                    )
                if reference_bundle.is_filtered_reference_data(reference_data_dir):
                    reference_bundle.validate_filtered_reference_data(reference_data_dir)
                elif not (reference_root / reference_bundle.KTSN_CSV_RELATIVE_SUBPATH).is_file():
                    raise ReferenceDataMissingError(
                        "canonical 참조 엑셀을 찾을 수 없습니다. storage/reference/tables/에 "
                        f"{canonical_reference.CANONICAL_FILENAME}을 두거나 올바른 .xlsx를 "
                        "업로드해 주세요."
                    )
                reference_bundle.validate_reference_data(reference_data_dir)
            else:
                raise ReferenceDataMissingError(
                    "canonical 참조 엑셀을 찾을 수 없습니다. 새 프로젝트는 legacy CSV/구형 "
                    "workbook으로 대체하지 않습니다. wizard에서 .xlsx 파일을 선택하고 "
                    "미리보기를 확인한 뒤 다시 시도해 주세요."
                )
        if identification_enabled:
            # FR-QPB-114-116/NFR-QPB-072 (Decision Log D-45): resolve the Pl@ntNet key's
            # consent-gated retention/embedding config, mirroring the VWorld online-basemap
            # handling below.
            plantnet_config = _resolve_plantnet_config(config.get("plantnet") or {})
        report_stage("참조 자료 확인")

        gpkg_relpath = f"data/{project_slug}.gpkg"
        gpkg_path = temp_project_dir / gpkg_relpath
        gpkg.build_geopackage(
            str(gpkg_path),
            survey_type,
            project_id,
            seed_sites=seed_sites,
            seed_plots=seed_plots,
            seed_temporary_plot_points=seed_temp_points,
        )
        report_stage("GeoPackage 생성")

        if should_cancel is not None and should_cancel():
            raise BuildCancelledError(
                "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
            )

        ktsn_lookup_table_name: str | None = None
        ktsn_taxonomy_table_name: str | None = None
        if requires_accepted_name_lookup:
            # Derive and bundle the accepted-name lookup table as a real, indexed table inside the
            # same .gpkg file. It powers Type 1–3 Korean-name selection and Type 4 dominant-species
            # selection, independently of photo identification.
            assert reference_data_dir is not None  # guaranteed by the dual trigger above
            if canonical_ingest is not None:
                if is_types_1_to_3 or identification_enabled:
                    gpkg.add_ktsn_taxonomy_reference_table(
                        str(gpkg_path), "ktsn_taxonomy_reference", canonical_ingest["rows"]
                    )
                accepted_name_lookup = {
                    "rows": [
                        {
                            "ktsn": row["ktsn"],
                            "taxon_kor_nm": row.get("korean_name") or "",
                            "taxon_full_nm": row["scientific_name"],
                        }
                        for row in canonical_ingest["rows"]
                        if row["taxon_status"] == "정명"
                    ]
                }
                ktsn_taxonomy_table_name = (
                    "ktsn_taxonomy_reference" if is_types_1_to_3 or identification_enabled else None
                )
                # QCR/D-96: QField cannot reliably evaluate the cross-layer canonical lookup
                # expression on iOS.  Derive a small local projection *from the table just
                # validated and inserted above*, never from the workbook directly.
                if identification_enabled:
                    canonical_runtime_resource = (
                        canonical_runtime_lookup.materialize_runtime_resource(
                            str(gpkg_path),
                            str(temp_project_dir),
                            force_failure_stage=config.get(
                                "_test_force_canonical_runtime_resource_failure"
                            ),
                        )
                    )
            elif reference_bundle.is_filtered_reference_data(reference_data_dir):
                # D-89 filtered-only packaged applications contain no raw CSV/XLSX.  The
                # accepted-only artifact was already derived and validated at packaging time.
                accepted_name_lookup = reference_bundle.load_filtered_accepted_name_lookup(
                    reference_data_dir
                )
            else:
                ktsn_source_csv = (
                    Path(reference_data_dir) / reference_bundle.KTSN_CSV_RELATIVE_SUBPATH
                )
                ktsn_source_xlsx = (
                    Path(reference_data_dir) / reference_bundle.NATIONAL_LIST_XLSX_RELATIVE_SUBPATH
                )
                accepted_name_lookup = reference_bundle.derive_accepted_name_lookup_table(
                    str(ktsn_source_csv), str(ktsn_source_xlsx)
                )
            gpkg.add_ktsn_lookup_table(
                str(gpkg_path),
                reference_bundle.KTSN_LOOKUP_TABLE_NAME,
                accepted_name_lookup["rows"],
            )
            ktsn_lookup_table_name = reference_bundle.KTSN_LOOKUP_TABLE_NAME

        basemap_config = config.get("basemap") or {"mode": "none"}
        mode = basemap_config.get("mode", "none")
        basemap_dir_path: Path | None = None
        mbtiles_relpath: str | None = None

        if mode == "online":
            basemap_config = _resolve_online_basemap(basemap_config)
            if not basemap_config.get("consent_accepted"):
                # FR-QPB-077: no consent -> proceed, but no online layer/key anywhere.
                pass
        elif mode == "offline":
            if should_cancel is not None and should_cancel():
                raise BuildCancelledError(
                    "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
                )

            # Bug 1 fix (E-QPB-003/FR-QPB-078/NFR-QPB-058): offline MBTiles generation genuinely
            # needs a VWorld API key during tile retrieval -- fail fast, here, with a clear,
            # non-technical, actionable message, before any other offline-mode work (the size
            # estimate, tile download) is attempted, rather than letting a missing/blank key
            # surface later as `vworld_tiles.resolve_tile_fetcher()`'s own raw `KeyError`.
            api_key = basemap_config.get("vworld_api_key")
            if not isinstance(api_key, str) or not api_key.strip():
                raise VWorldApiKeyMissingError(
                    "오프라인 배경지도를 생성하려면 VWorld API 키가 필요합니다. 마법사의 4단계"
                    "(연결 상태 및 배경지도)에서 API 키를 입력한 뒤 다시 시도해 주세요."
                )

            # Test-only cancellation remains a phase hook, but key validation must win over it:
            # a missing/blank key is required to fail before estimate, acquisition, cancellation,
            # or any MBTiles write is attempted.
            if config.get("_test_cancel_after_phase") == "basemap_download":
                raise BuildCancelledError()

            # Reviewer-round fix (compounding issue, FR-QPB-076 finding): offline mode's own
            # "remember this key" checkbox must actually have an effect, exactly like the online
            # branch's `_resolve_online_basemap` does above -- unconditionally here (unlike the
            # online branch, offline mode has no `consent_accepted` gate to check: FR-QPB-078/
            # NFR-QPB-058's transient, never-embedded use of the key needs no consent step). See
            # `apply_retention_policy`'s own docstring for why this call is load-bearing only for
            # the direct, in-process `build_project()` call this harness/these tests use -- the
            # real desktop application's actual persistence happens earlier, in the UI process,
            # via `ReviewAndBuildPage._persist_remembered_keys()`.
            apply_retention_policy(
                basemap_config.get("vworld_api_key", ""), bool(basemap_config.get("remember_key"))
            )

            selected_layer = str(basemap_config.get("layer") or "").strip()
            advertised_layers = basemap_config.get("known_vworld_layers")
            allowed_layers = (
                list(advertised_layers)
                if advertised_layers is not None
                else vworld.supported_layers()
            )
            if not selected_layer or selected_layer not in allowed_layers:
                raise BuildError(
                    "offline_layer_unavailable",
                    "선택한 VWorld 오프라인 레이어를 현재 사용할 수 없습니다. 레이어 목록을 "
                    "새로고침하고 지원되는 레이어를 하나 선택한 뒤 다시 시도해 주세요.",
                )

            bbox = basemap_config["bbox"]
            min_zoom = basemap_config["min_zoom"]
            max_zoom = basemap_config["max_zoom"]
            representative_bytes = _representative_tile_bytes(basemap_config)
            estimate = estimate_offline_basemap_size(bbox, min_zoom, max_zoom, representative_bytes)
            if estimate["exceeds_pregeneration_threshold"]:
                raise OfflineSizeExceededError(
                    "예상되는 오프라인 배경지도 크기가 900 MiB 사전 생성 한도를 초과합니다. "
                    "선택한 영역, 줌 범위, 또는 해상도를 줄인 뒤 다시 시도해 주세요."
                )

            basemap_dir_path = temp_project_dir / "basemap"
            mbtiles_relpath = "basemap/offline.mbtiles"
            mbtiles_path = temp_project_dir / mbtiles_relpath
            tile_fetcher = resolve_tile_fetcher(basemap_config)
            from .mbtiles import build_mbtiles

            build_mbtiles(
                str(mbtiles_path),
                bbox,
                min_zoom,
                max_zoom,
                tile_fetcher,
                should_cancel=should_cancel,
                provider="VWorld",
                layer=selected_layer,
                on_progress=progress_callback,
            )
            # Carry only non-secret source identity into the project-builder config. This keeps
            # compatibility with lightweight build seams while ensuring the native QGIS path and
            # the MBTiles metadata receive the same selected layer.
            basemap_config["offline_source_identity"] = {
                "provider": "VWorld",
                "layer": selected_layer,
            }

        if identification_enabled:
            # FR-QPB-112 (revised; Decision Log D-47): bundle the build-time-extracted, 5-column
            # KTSN lookup file (FR-QPB-118) and the complete, unmodified probability-raster set
            # into this project's own reference/ folder.
            if canonical_ingest is None:
                reference_bundle.bundle_reference_data(
                    reference_data_dir,
                    str(temp_project_dir),
                    include_probability_rasters=False,
                )
            # FR-QPB-113 (Decision Log D-41): best-effort extraction of the NIBR accepted-taxon
            # KTSN lookup list; silently skipped if the source xlsx is not present at
            # reference_data_dir (e.g. a minimal test-seam override), never a hard build failure.
            if canonical_ingest is None:
                reference_bundle.extract_and_bundle_national_ktsn_list(
                    reference_data_dir, str(temp_project_dir)
                )
            if identification_probability_enabled:
                probability_source_override = config.get("_test_probability_raster_source_dir")
                if probability_source_override:
                    probability_source_dir = str(probability_source_override)
                elif canonical_ingest is not None:
                    probability_source_dir = str(
                        Path(reference_data_dir) / reference_bundle.RASTER_DIR_RELATIVE_SUBPATH
                    )
                else:
                    _csv_path, resolved_raster_dir = reference_bundle.validate_reference_data(
                        reference_data_dir
                    )
                    probability_source_dir = str(resolved_raster_dir)
                probability_result = probability_raster.build_probability_stack(
                    probability_source_dir,
                    str(temp_project_dir),
                    cache_dir=str(Path(reference_data_dir) / "probability_cache"),
                )
                if not probability_result.get("success"):
                    raise BuildError(
                        probability_result.get("error_code") or "probability_stack_build_failed",
                        probability_result.get("error_message")
                        or "다중밴드 출현확률 래스터를 생성하지 못했습니다.",
                    )
                probability_band_count = int(probability_result["discovered_species_count"])
        report_stage("식별 참조 자료 준비")

        # FR-QPB-090/100/133 (Decision Log D-83/D-85/D-87): the shared project-plugin sidecar
        # and its HTML-report action are unconditional. FR-QPB-143 (Decision Log D-97): write
        # portable, self-contained toolbar SVGs into this project before its adjacent sidecar
        # references them. Identification-only assets and members remain gated by
        # `identification_enabled`.
        for relative_path, svg_content in qml_plugin.project_toolbar_svg_assets(
            identification_enabled=identification_enabled
        ).items():
            asset_path = temp_project_dir / relative_path
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_text(svg_content, encoding="utf-8")

        plugin_qml_path = temp_project_dir / f"{project_slug}.qml"
        plugin_qml_path.write_text(
            qml_plugin.render_project_plugin_qml(
                project_slug,
                identification_enabled=identification_enabled,
                project_display_name=config["project_display_name"],
                project_id=project_id,
                survey_type=survey_type,
                generated_at=datetime.now(timezone.utc).isoformat(),
                canonical_reference_enabled=canonical_ingest is not None,
            ),
            encoding="utf-8",
        )

        # FR-QPB-120/FR-QPB-121 (Decision Log D-61/D-65): this build's own, fresh symbol-styling
        # choice (Step 6, FR-QPB-123) -- never persisted or reused from any other build
        # (AC-QPB-104). A failed/offline Tabler SVG fetch, or no icon selected, silently falls
        # back to the minimalist default (FR-QPB-121) without blocking generation.
        svg_relative_path = (
            _resolve_symbol_styling(config, temp_project_dir)
            if survey_type != "vegetation_mapping"
            else None
        )

        qgs_relpath = f"{project_slug}.qgs"
        qgs_path = temp_project_dir / qgs_relpath
        try:
            if should_cancel is not None and should_cancel():
                raise BuildCancelledError(
                    "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
                )
            qgis_kwargs = dict(
                gpkg_path=str(gpkg_path),
                qgs_path=str(qgs_path),
                survey_type=survey_type,
                project_crs=config.get("project_crs", "EPSG:5186"),
                basemap_config=basemap_config if mode != "none" else None,
                mbtiles_relative_path=mbtiles_relpath,
                identification_enabled=identification_enabled,
                plantnet_config=plantnet_config,
                svg_relative_path=svg_relative_path,
                ktsn_lookup_table_name=ktsn_lookup_table_name,
            )
            if ktsn_taxonomy_table_name:
                qgis_kwargs["ktsn_taxonomy_table_name"] = ktsn_taxonomy_table_name
            if canonical_runtime_resource is not None:
                qgis_kwargs["canonical_runtime_lookup_resource"] = canonical_runtime_resource
            # Keep the legacy call shape unchanged for projects without photo identification;
            # existing lightweight QGIS test doubles and integrations do not accept the optional
            # probability-layer argument. New identification-enabled projects explicitly pass
            # the shared multiband layer path.
            if identification_probability_enabled:
                qgis_kwargs["probability_raster_relative_path"] = probability_raster.STACK_RELPATH
            qgis_result = qgis_worker.build_qgis_project(**qgis_kwargs)
        except ImportError as exc:
            raise RuntimeMissingError(
                f"내장 프로젝트 생성 모듈을 사용할 수 없습니다: {exc}"
            ) from exc
        report_stage("템플릿 프로젝트 구성")

        online_key_embedded = qgis_result.get("online_key_embedded", False)
        plantnet_key_embedded = qgis_result.get("plantnet_key_embedded", False)

        basemap_relpaths = [mbtiles_relpath] if mbtiles_relpath else []
        if should_cancel is not None and should_cancel():
            raise BuildCancelledError(
                "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
            )
        # The historical manifest key retains its stable name for compatibility, but now points
        # to the unconditional shared sidecar (D-87), not an identification-only artifact.
        identification_plugin_relpath = f"{project_slug}.qml"
        reference_relpaths: list[str] = []
        if identification_enabled and canonical_ingest is None:
            reference_relpaths.append(reference_bundle.PROJECT_KTSN_LOOKUP_RELPATH)
            if identification_probability_enabled:
                reference_relpaths.extend(
                    [probability_raster.STACK_RELPATH, probability_raster.INDEX_RELPATH]
                )
            national_list_path = temp_project_dir / reference_bundle.PROJECT_NATIONAL_LIST_RELPATH
            if national_list_path.is_file():
                reference_relpaths.append(reference_bundle.PROJECT_NATIONAL_LIST_RELPATH)
        elif canonical_runtime_resource is not None:
            reference_relpaths.append(canonical_runtime_resource["relative_path"])
            if identification_probability_enabled:
                reference_relpaths.extend(
                    [probability_raster.STACK_RELPATH, probability_raster.INDEX_RELPATH]
                )

        manifest = manifest_mod.build_manifest(
            project_dir=str(temp_project_dir),
            project_id=project_id,
            project_slug=project_slug,
            survey_type=survey_type,
            qgs_relpath=qgs_relpath,
            gpkg_relpath=gpkg_relpath,
            attachment_relpaths=[],
            basemap_relpaths=basemap_relpaths,
            online_key_embedded=online_key_embedded,
            identification_plugin_relpath=identification_plugin_relpath,
            reference_relpaths=reference_relpaths,
            plantnet_key_embedded=plantnet_key_embedded,
            probability_band_count=(
                probability_band_count if identification_probability_enabled else None
            ),
            source_provenance=(canonical_ingest or {}).get("provenance")
            if canonical_ingest
            else None,
            canonical_runtime_lookup=canonical_runtime_resource,
        )
        manifest_mod.write_manifest(str(temp_project_dir), manifest)

        transfer_readme.write_readme_transfer_ko(
            str(temp_project_dir), config["project_display_name"]
        )

        validation_report = validate.validate_project(str(temp_project_dir))
        temp_validation_report_path = validate.write_validation_report(
            str(temp_project_dir), validation_report
        )
        report_stage("프로젝트 검증")
        visibility_failure_codes = {
            "layer_tree_visibility_unverified",
            "layer_tree_group_missing",
            "layer_tree_group_invalid",
            "layer_tree_group_unchecked",
            "layer_tree_node_missing",
            "layer_tree_node_invalid",
            "layer_tree_node_unchecked",
        }
        visibility_failures = [
            issue
            for issue in validation_report.get("issues", [])
            if isinstance(issue, dict) and issue.get("code") in visibility_failure_codes
        ]
        if visibility_failures or not validation_report.get("success"):
            # Keep a failed validation report outside the temporary build root.  The temporary
            # project is intentionally removed on every failed build, so without this copy the
            # only actionable diagnostics would disappear along with the rollback artifacts. A
            # unique suffix avoids overwriting an earlier report when the same output name is
            # retried. Successful builds retain the report inside the promoted project, but must
            # not create this durable sidecar next to the requested output folder.
            output_path.parent.mkdir(parents=True, exist_ok=True)
            durable_report = output_path.parent / f"{output_path.name}.VALIDATION_REPORT.json"
            if durable_report.exists():
                durable_report = output_path.parent / (
                    f"{output_path.name}.VALIDATION_REPORT-{project_id}.json"
                )
            try:
                shutil.copy2(temp_validation_report_path, durable_report)
            except OSError as exc:
                # Returning the complete report below still preserves diagnostics if the requested
                # parent cannot accept a sidecar file; never turn a validation failure into a
                # success.
                validation_report_path = None
                report_copy_error = f" 검증 보고서 sidecar 저장 실패: {exc}"
            else:
                validation_report_path = str(durable_report)
                report_copy_error = ""
            issue_messages = [
                str(issue.get("message", ""))
                for issue in validation_report.get("issues", [])
                if isinstance(issue, dict) and issue.get("message")
            ]
            detail = " ".join(issue_messages)
            raise BuildError(
                "project_validation_failed",
                "생성된 프로젝트 검증에 실패하여 결과를 저장하지 않았습니다."
                + (f" {detail}" if detail else "")
                + (
                    f" 검증 보고서: {validation_report_path}."
                    if validation_report_path
                    else (
                        " 검증 보고서는 build 결과의 validation_report 필드에서 확인할 수 있습니다."
                    )
                )
                + report_copy_error,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if should_cancel is not None and should_cancel():
            raise BuildCancelledError(
                "빌드가 취소되었습니다. 다시 생성하려면 '생성'을 눌러 주세요."
            )
        if output_path.exists():
            # A destination directory has appeared after the initial existence check above
            # (e.g. a race with another process/thread). E-QPB-008/FR-QPB-022a require that an
            # existing output folder is never silently overwritten -- so this build must abort
            # cleanly here, leave that destination completely untouched (never delete or move
            # into it), and report the same structured error as the initial check. This build's
            # own temp artifacts (temp_root) are still cleaned up via the enclosing `finally`.
            return _empty_result(
                error_code="output_dir_exists",
                error_message=_OUTPUT_DIR_EXISTS_MESSAGE.format(output_dir=output_dir),
            )
        shutil.move(str(temp_project_dir), str(output_path))
        report_stage("프로젝트 저장")

        return _empty_result(
            success=True,
            cancelled=False,
            project_dir=str(output_path),
            project_id=project_id,
            project_slug=project_slug,
            qgs_path=str(output_path / qgs_relpath),
            gpkg_path=str(output_path / gpkg_relpath),
            attachments_dir=str(output_path / "attachments"),
            basemap_dir=str(output_path / "basemap") if basemap_dir_path else None,
            basemap_provider="VWorld" if mode == "offline" else None,
            basemap_layer=(selected_layer if mode == "offline" else None),
            manifest_security_warning=online_key_embedded,
            symbols_dir=str(output_path / SYMBOLS_DIR_RELPATH) if svg_relative_path else None,
            ktsn_lookup_table_name=ktsn_lookup_table_name,
            probability_raster_registration_count=qgis_result.get(
                "probability_raster_registration_count", 0
            ),
            stage_timings=stage_timings,
        )
    except BuildCancelledError as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        return _empty_result(cancelled=True, error_code=exc.error_code, error_message=exc.message)
    except canonical_runtime_lookup.CanonicalRuntimeLookupBuildError as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        return _empty_result(
            error_code="canonical_runtime_lookup_resource_failed",
            error_message=str(exc),
            failed_stage="canonical_runtime_lookup_resource",
        )
    except BuildError as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        return _empty_result(
            error_code=exc.error_code,
            error_message=exc.message,
            validation_report_path=validation_report_path,
            validation_report=validation_report,
        )
    except Exception as exc:  # noqa: BLE001 - never raise an uncaught exception to the caller.
        shutil.rmtree(temp_root, ignore_errors=True)
        return _empty_result(
            error_code="unexpected_error",
            error_message=str(exc),
            validation_report_path=validation_report_path,
            validation_report=validation_report,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
