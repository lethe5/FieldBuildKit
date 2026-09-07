"""Standalone runtime checks plus developer-only legacy QGIS detection utilities.

The application calls check_runtime(), which never discovers or launches QGIS.
The older detect_qgis_installation() is retained only for development compatibility tools.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import qgis_bridge

MIN_QGIS_SERIES = "3.44"  # QGIS 3.44.0 is the minimum supported runtime version.

_NON_TECHNICAL_MISSING_MESSAGE = (
    "이 컴퓨터에서 호환되는 QGIS Desktop 설치를 찾을 수 없습니다 "
    f"(QGIS {MIN_QGIS_SERIES} 이상 버전이 필요합니다). "
    "QGIS Desktop을 설치하거나, 'QGIS 설치 위치 선택...' 옵션을 사용해 기존 설치 위치를 "
    "지정한 뒤 다시 시도해 주세요."
)


def _non_technical_manual_path_rejected_message(manual_path: str) -> str:
    """A distinct, non-technical failure message for a manually supplied QGIS install path that
    does not verify (missing entirely, or exists but is not a genuinely working QGIS/PyQGIS
    install) -- deliberately different wording from `_NON_TECHNICAL_MISSING_MESSAGE` (the message
    shown *before* the user has ever tried the manual option), so a user who just tried it does
    not see the exact same generic "nothing found anywhere" text again."""
    return (
        f"지정한 위치('{manual_path}')에서 QGIS Desktop 설치를 확인할 수 없습니다 "
        f"(QGIS {MIN_QGIS_SERIES} 이상 버전이 설치된 폴더가 맞는지 확인해 "
        "주세요). QGIS Desktop이 설치된 폴더(예: macOS의 'QGIS.app', Windows의 QGIS 설치 폴더)를 "
        "다시 선택한 뒤 시도해 주세요."
    )


@dataclass(frozen=True)
class RuntimeInfo:
    available: bool
    message: str
    qgis_version: str | None = None
    qgis_prefix_path: str | None = None

    def as_dict(self) -> dict:
        return {
            "available": self.available,
            "message": self.message,
            "qgis_prefix_path": self.qgis_prefix_path,
        }


def _try_import_pyqgis_in_current_process() -> tuple[bool, str | None]:
    """Attempt a real PyQGIS import in the *current* process.

    This only succeeds when the current interpreter already has PyQGIS on its path (e.g. this
    code is itself already running inside a QGIS-supplied Python, such as inside a
    :mod:`qfield_builder.qgis_bridge`-launched worker). The normal case — this application's own
    host interpreter (the PySide6 UI process, or this process's own Python during tests) — never
    has PyQGIS importable this way, which is exactly why :mod:`qfield_builder.qgis_bridge` exists.
    """
    import importlib

    try:
        qgis_core = importlib.import_module("qgis.core")
    except ImportError:
        return False, None
    version = getattr(qgis_core, "Qgis", None)
    version_string = None
    if version is not None:
        version_string = getattr(version, "QGIS_VERSION", None)
    return True, version_string


def _verify_manual_path(manual_path: str) -> RuntimeInfo:
    """FR-QPB-008's manual-override half: verifies `manual_path` via the same real,
    subprocess-based `qgis_bridge` mechanism automatic detection uses -- never a "directory looks
    plausible" heuristic. Never raises; always returns a structured `RuntimeInfo`."""
    target = qgis_bridge.get_bridge_target_for_path(manual_path)
    if target is not None:
        return RuntimeInfo(
            available=True,
            message=(
                "지정한 위치에서 정상적으로 작동하는 QGIS/PyQGIS 설치를 확인했습니다: "
                f"'{target.install_path}' (버전: {target.qgis_version or '알 수 없음'}). 해당 "
                "설치의 자체 Python/PyQGIS 환경을 통해 확인했습니다."
            ),
            qgis_version=target.qgis_version,
            qgis_prefix_path=target.install_path,
        )
    return RuntimeInfo(
        available=False, message=_non_technical_manual_path_rejected_message(manual_path)
    )


def detect_qgis_installation(manual_path: str | None = None) -> RuntimeInfo:
    """FR-QPB-008/009: detect a *verified-usable* QGIS installation; non-technical error if not.

    `manual_path` (FR-QPB-008's manual-override half) is consulted only once automatic detection
    (the current-process import, then the `qgis_bridge`-detected standard per-OS candidate roots)
    has already failed -- an already-succeeding automatic detection is never overridden by a
    supplied `manual_path`. An empty/blank `manual_path` is treated identically to `None`.
    """
    ok, version = _try_import_pyqgis_in_current_process()
    if ok and qgis_bridge.is_supported_qgis_version(version):
        return RuntimeInfo(
            available=True,
            message=(
                "정상적으로 작동하는 QGIS/PyQGIS 설치를 감지했습니다 "
                f"(버전: {version or '알 수 없음'})."
            ),
            qgis_version=version,
        )

    target = qgis_bridge.get_bridge_target()
    if target is not None:
        return RuntimeInfo(
            available=True,
            message=(
                "정상적으로 작동하는 QGIS/PyQGIS 설치를 감지했습니다: "
                f"'{target.install_path}' (버전: {target.qgis_version or '알 수 없음'}). 해당 "
                "설치의 자체 Python/PyQGIS 환경을 통해 확인했습니다."
            ),
            qgis_version=target.qgis_version,
            qgis_prefix_path=target.install_path,
        )

    normalized_manual_path = (manual_path or "").strip()
    if normalized_manual_path:
        return _verify_manual_path(normalized_manual_path)

    if qgis_bridge.any_plausible_install_dir_exists():
        return RuntimeInfo(
            available=False,
            message=(
                "QGIS 설치 폴더를 찾았지만, 해당 폴더의 PyQGIS 환경을 확인할 수 없습니다. QGIS "
                "3.44 이상 설치가 맞는지 확인하거나, 'QGIS 설치 위치 선택...' "
                "옵션을 사용한 뒤 다시 시도해 주세요."
            ),
        )

    return RuntimeInfo(available=False, message=_NON_TECHNICAL_MISSING_MESSAGE)


def check_runtime(force_missing: bool = False, manual_path: str | None = None) -> dict:
    """Check bundled dependencies and templates; never discover or launch QGIS."""
    import importlib

    from . import schemas

    missing = []
    for module in ("rasterio", "fiona"):
        try:
            package = importlib.import_module(module)
            if module == "rasterio":
                package.crs.CRS.from_epsg(5186)
            elif "GPKG" not in package.supported_drivers:
                missing.append("GeoPackage driver")
        except (ImportError, OSError, ValueError):
            missing.append(module)
    from pathlib import Path

    templates = Path(__file__).parent / "templates"
    for name in [
        *(f"{kind}.qgs" for kind in schemas.SURVEY_TYPES),
        "online.xml",
        "offline.xml",
        "probability.xml",
        "svg.xml",
    ]:
        if not (templates / name).is_file():
            missing.append(name)
    available = not missing and not force_missing
    return {
        "available": available,
        "qgis_prefix_path": None,
        "backend": "standalone",
        "message": "QGIS 설치 없이 실행할 준비가 되었습니다."
        if available
        else "내장 실행 환경이 불완전합니다. 앱을 다시 설치해 주세요. " + ", ".join(missing),
    }


def is_running_inside_pyqgis() -> bool:
    """True if the *current* interpreter already has a working PyQGIS import."""
    import sys

    return "qgis.core" in sys.modules or _try_import_pyqgis_in_current_process()[0]
