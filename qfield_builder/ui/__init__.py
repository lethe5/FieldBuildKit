"""PySide6 desktop UI (Section 5.1/5.3, Section 6 seven-step wizard).

This is the MVP-scope native desktop application shell. It never imports PyQGIS or
:mod:`qfield_builder.qgis_worker` directly (Section 5.3/FR-QPB-010) — all QGIS/PyQGIS/GDAL work
is dispatched to the separate GIS worker process via :mod:`qfield_builder.worker_process`.
"""
