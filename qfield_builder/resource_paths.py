"""Resolves the on-disk location of this application's bundled, version-controlled resource
files (``resources/...``), correctly both when running from source and when running as a
PyInstaller-packaged application (``sys.frozen``/``sys._MEIPASS``).

Cross-platform and packaging-tool-agnostic: this module has no macOS-only assumption -- the same
``sys._MEIPASS`` convention is what PyInstaller sets on every platform it packages for (Windows,
macOS, Linux), and unlike an ``__file__``-relative path, it correctly points at wherever the
packaging tool actually put the bundled ``resources/`` directory, rather than assuming
``qfield_builder/``'s own parent directory is a real, readable directory on disk -- which is only
true when running from an unpacked source checkout. Once PyInstaller has bundled this package's
Python modules into its own archive format, ``__file__``-relative resolution (the previous
approach in :mod:`qfield_builder.vworld`) silently stops finding the real, packaged
``resources/config/vworld_layers.json`` and falls back to that module's hard-coded defaults --
technically non-crashing (a deliberate defensive fallback), but defeating FR-QPB-072's point that
the VWorld layer/URL configuration must be updatable "without a code change" in the *distributed*
application, not only when running from source.
"""
from __future__ import annotations

import sys
from pathlib import Path


def repo_or_bundle_root() -> Path:
    """The directory that contains this application's ``resources/`` folder.

    - When packaged by PyInstaller (``sys.frozen`` is True and ``sys._MEIPASS`` is set): the
      extraction root PyInstaller itself creates and populates from this project's own ``datas``
      configuration (see ``packaging/qfield_builder.spec``) -- true for both onefile and onedir
      builds, on every platform PyInstaller supports.
    - Otherwise (running from an unpacked source checkout, e.g. under pytest, ``python -m``, or
      the installed console-script entry point): this repository's own root directory, two levels
      above this file (``qfield_builder/resource_paths.py`` -> ``qfield_builder/`` -> repo root).
      A packaged QGIS bridge subprocess can instead import the loose source copy from
      ``<bundle>/qfield_builder_src/qfield_builder/``; in that layout the bundle root is the
      parent of the usual two-level result.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        return Path(meipass)
    source_root = Path(__file__).resolve().parent.parent
    if (
        source_root.name == "qfield_builder_src"
        and (source_root.parent / "resources").is_dir()
    ):
        return source_root.parent
    return source_root


def resource_path(*parts: str) -> Path:
    """A path under this application's bundled ``resources/`` directory, e.g.
    ``resource_path("config", "vworld_layers.json")``."""
    return repo_or_bundle_root().joinpath("resources", *parts)


def storage_path(*parts: str) -> Path:
    """Return a path under the source/package ``storage/`` tree.

    Reference data is packaged as application data at the bundle root (the same layout as the
    source checkout), not below ``resources/``. Keeping this resolver separate from
    :func:`resource_path` makes that packaging boundary explicit.
    """
    return repo_or_bundle_root().joinpath("storage", *parts)


def reference_path(*parts: str) -> Path:
    """Return a path under the canonical ``storage/reference/`` tree."""
    return storage_path("reference", *parts)
