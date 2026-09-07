"""Negative probabilities become real zero values; missing data stays missing."""
import json
import subprocess

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from qfield_builder import qml_plugin, standalone_gis


@pytest.mark.parametrize("value", [-0.25, -0.00001, -12000, 0, 0.75, 1, -9999, 1.25,
                                  float("nan"), float("inf")])
def test_raster_sampler_clamps_only_finite_non_nodata_negatives(tmp_path, value):
    path = tmp_path / "probability.tif"
    with rasterio.open(path, "w", driver="GTiff", width=1, height=1, count=1,
                       dtype="float32", crs="EPSG:4326", nodata=-9999,
                       transform=from_origin(127, 38, 1, 1)) as dataset:
        dataset.write(np.array([[value]], dtype="float32"), 1)
    result = standalone_gis._sample_probability_gdal(str(path), 1, 127.5, 37.5)
    if not np.isfinite(value) or value == -9999 or value > 1:
        assert not result["ok"]
    else:
        assert result == {"ok": True, "value": pytest.approx(max(0, value))}


def test_generated_qfield_widget_displays_and_retains_clamped_probability():
    content = qml_plugin.render_identification_widget_qml("''")
    start = content.index("function qpbFormatProbability(")
    end = content.index("function qpbHandlePlantNetResponse(", start)
    script = """
const functions = process.argv[1];
let pending, qpbCandidatesModel;
function qpbLoadProbabilityBandIndex() { return {mapping:{leaf:1},band_count:1}; }
function qpbNormalizeProbabilityBandName(name) { return name; }
function qpbEscapeForExpressionLiteral(value) { return value; }
function qpbTraceRuntime() {}
function qpbSampleProbabilityRaster(expression, callback) { pending=callback; return '1'; }
eval(functions);
const values = [-0.25, -0.00001, -12000, 0, 0.75, 1, -9999, 1.25, null, NaN, Infinity];
const results = values.map(value => {
    qpbCandidatesModel = [{probability_request_id:'1'}];
    qpbFormatProbability('leaf', {lon:127,lat:37}, 0);
    pending({available:true,value:value});
    return qpbCandidatesModel[0];
});
process.stdout.write(JSON.stringify(results));
"""
    result = subprocess.run(["node", "-e", script, content[start:end]],
                            check=True, capture_output=True, text=True)
    rows = json.loads(result.stdout)
    assert [row["probability_value"] for row in rows] == [0, 0, 0, 0, 0.75, 1,
                                                        None, None, None, None, None]
    assert all(row["probability_text"] == "예측 출현 확률: 0%" for row in rows[:4])
    assert all(row["warning_text"] == "" for row in rows[:6])
