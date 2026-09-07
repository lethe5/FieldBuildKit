"""Offline basemap assembly must not invent a source identity."""
from __future__ import annotations

import pytest

from qfield_builder import qgis_worker


def test_offline_basemap_rejects_missing_source_identity_before_layer_creation():
    with pytest.raises(ValueError, match="source identity is required"):
        qgis_worker._add_offline_basemap_layer(
            {
                "QgsRasterLayer": object,
                "QgsCoordinateReferenceSystem": object,
            },
            project=object(),
            mbtiles_relative_path="./basemap/offline.mbtiles",
        )


def test_offline_basemap_rejects_incomplete_source_identity_before_layer_creation():
    with pytest.raises(ValueError, match="source identity is incomplete"):
        qgis_worker._add_offline_basemap_layer(
            {
                "QgsRasterLayer": object,
                "QgsCoordinateReferenceSystem": object,
            },
            project=object(),
            mbtiles_relative_path="./basemap/offline.mbtiles",
            offline_source_identity={"provider": "VWorld", "layer": ""},
        )
