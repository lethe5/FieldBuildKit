"""Execute the shipped report serializers, including the native pre-serialization guard."""

import json
import subprocess

from qfield_builder.html_report_core import REPORT_CORE_JS, _production_function
from qfield_builder.qml_plugin import render_project_plugin_qml


def _runtime():
    source = render_project_plugin_qml("large-report", survey_type="temporary_plots")
    names = ("qpbGeometryToGeoJson", "qpbWktToGeoJson", "qpbBytes", "qpbBinaryPrefix",
             "qpbGpkgEnvelopeGeoJson", "qpbTransformGeoJson", "qpbIsWgs84Crs", "qpbLayerCrs")
    return "var qpbReportFullGeometryMaxBytes=524288;\n" + REPORT_CORE_JS + "\n" + "\n".join(
        _production_function(source, name) for name in names)


def _run(script):
    result = subprocess.run(["node", "--max-old-space-size=128", "-"],
                            input=_runtime() + "\n" + script, text=True, encoding="utf-8",
                            capture_output=True, timeout=15, check=True)
    return json.loads(result.stdout)


def test_native_guard_runs_before_geometry_serialization_and_releases_feature():
    result = _run(r"""
        var expressionText="", FeatureUtils={createBlankFeature:function(){return null;}};
        var qpbReportGeometryEvaluator={evaluate:function(expression){
            expressionText=expression;
            return JSON.stringify({empty:false,simplified:1,
                wkt:"POLYGON((127 37,128 37,128 38,127 37))"});
        }};
        var feature={get geometry(){throw new Error("must not expand native geometry");}};
        var geometry=qpbGeometryToGeoJson(feature,{}, {geometry_field:"geom"});
        process.stdout.write(JSON.stringify({geometry:geometry,expression:expressionText,
            released:qpbReportGeometryEvaluator.feature===null&&qpbReportGeometryEvaluator.layer===null}));
    """)
    assert result["geometry"]["valid"]
    assert result["geometry"]["outcome"] == "simplified_envelope"
    assert result["released"]
    assert "num_points(@g) > 16384" in result["expression"]
    assert "to_json(map(" in result["expression"]  # QField evaluate() returns a QString
    assert "transform(if(@large, bounds(@g), @g)" in result["expression"]


def test_native_empty_failure_and_following_small_polygon_remain_distinct():
    result = _run(r"""
        var FeatureUtils={createBlankFeature:function(){return null;}};
        var responses=[{empty:true},null,{empty:false,simplified:false,
            wkt:"POLYGON((127 37,128 37,128 38,127 37),"+
                "(127.1 37.1,127.2 37.1,127.2 37.2,127.1 37.1))"}];
        var qpbReportGeometryEvaluator={evaluate:function(){
            return JSON.stringify(responses.shift());}};
        var results=[];
        for(var i=0;i<3;i++) results.push(qpbGeometryToGeoJson({}, {}, {geometry_field:"geom"}));
        process.stdout.write(JSON.stringify(results));
    """)
    assert [item["outcome"] for item in result] == [
        "actual_empty", "serialization_failure", "valid"]
    assert len(result[2]["geojson"]["coordinates"]) == 2  # small polygon's hole is retained


def test_legacy_wkt_size_is_checked_before_parsing():
    result = _run(r"""
        var geometry={asWkt:function(){return "POLYGON("+"0 0,".repeat(300000)+")";}};
        qpbWktToGeoJson=function(){throw new Error("unexpected parser call");};
        process.stdout.write(JSON.stringify(qpbGeometryToGeoJson({geometry:geometry},null,
            {geometry_field:"geom",geometry_crs:"EPSG:4326"})));
    """)
    assert not result["valid"]
    assert result["outcome"] == "serialization_failure"


def test_header_envelope_accepts_hex_and_array_without_expanding_payload():
    import struct

    prefix = b"GP\x00\x03" + struct.pack("<i4d", 4326, 127, 128, 37, 38)
    result = _run("var prefix=" + json.dumps(list(prefix)) + r""";
        var hex=prefix.map(function(b){return b.toString(16).padStart(2,"0");}).join("");
        var fromArray=qpbGpkgEnvelopeGeoJson(prefix,"EPSG:4326");
        var fromHex=qpbGpkgEnvelopeGeoJson(hex,"EPSG:4326");
        var fromPrefixed=qpbGpkgEnvelopeGeoJson("0x"+hex,"EPSG:4326");
        process.stdout.write(JSON.stringify([fromArray,fromHex,fromPrefixed,qpbBytes(hex)]));
    """)
    assert result[0] == result[1] == result[2]
    assert result[3] == list(prefix)
