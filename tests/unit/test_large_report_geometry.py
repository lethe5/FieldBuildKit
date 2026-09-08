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
    assert result["geometry"]["outcome"] == "simplified_geometry"
    assert result["released"]
    assert "num_points(@g) > 16384" in result["expression"]
    assert "to_json(map(" in result["expression"]  # QField evaluate() returns a QString
    assert "simplify(@g, @t)" in result["expression"]
    assert "num_points(@s) <= 32768" in result["expression"]
    assert "transform(@s," in result["expression"]
    assert "bounds(@g)" not in result["expression"]


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


def test_native_vertex_limit_failure_never_falls_back_to_a_rectangle():
    result = _run(r"""
        var FeatureUtils={createBlankFeature:function(){return null;}};
        var qpbReportGeometryEvaluator={evaluate:function(){
            return JSON.stringify({empty:false,limited:true,wkt:null});}};
        var feature={get geometry(){throw new Error("must not expand native geometry");}};
        process.stdout.write(JSON.stringify(qpbGeometryToGeoJson(feature,{},
            {geometry_field:"geom"})));
    """)
    assert not result["valid"]
    assert result["reason"] == "경계 단순화 후에도 보고서 좌표 수 제한 초과"


def test_large_saved_row_uses_shared_native_simplification_without_loading_blob():
    source = render_project_plugin_qml("large-report", survey_type="temporary_plots")
    collector = _production_function(source, "qpbCollectGpkgSpatialRows")
    result = _run(collector + r"""
        var sql=[],expressionText="",qgisProject=null;
        function qpbGpkgTableIdentifier(s){return s;}
        function qpbSavedGpkgPath(){return "fixture.gpkg";}
        function qpbIsSensitiveReportField(){return false;}
        function qpbFormatReportValue(v){return v;}
        function qpbFindDomainLayer(){return {};}
        function qpbExecuteSql(s){sql.push(s);return s.indexOf("PRAGMA")===0?
            [{name:"site_id"},{name:"site_name"},{name:"geom"}]:
            [{site_id:"quote'id",site_name:"보존할 이름",__qpb_geometry_bytes:80000000,
                __qpb_geometry_prefix:[],__qpb_geometry_full:null}];}
        var FeatureUtils={createBlankFeature:function(){return null;}};
        var qpbReportGeometryEvaluator={evaluate:function(s){expressionText=s;
            return JSON.stringify({empty:false,simplified:1,
                wkt:"POLYGON((127 37,128 37,127.5 37.5,128 38,127 37))"});}};
        var result=qpbCollectGpkgSpatialRows("site","geom","POLYGON","EPSG:4326",
            {name:"site",uuid_field:"site_id"});
        var record=result.records[0];
        process.stdout.write(JSON.stringify({geometry:record._qpbGeometry,
            attrs:record._qpbAttrs,expression:expressionText,sql:sql}));
    """)
    assert result["geometry"]["outcome"] == "simplified_geometry"
    assert result["attrs"]["site_name"] == "보존할 이름"
    assert "geometry(get_feature(@layer, 'site_id', 'quote''id'))" in result["expression"]
    assert "CASE WHEN length(geom) <= 524288" in result["sql"][1]


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


def test_html_omits_redundant_geometry_copies_without_mutating_native_payload():
    source = render_project_plugin_qml("large-report", survey_type="temporary_plots")
    builder = _production_function(source, "qpbBuildHtmlReport")
    start = builder.index("qpbLastReportPayload = payload;")
    end = builder.index("var json = qpbSafeJson(htmlPayload);")
    serialization = builder[start:end] + "var json = qpbSafeJson(htmlPayload);"
    result = _run(_production_function(source, "qpbSafeJson") + r'''
var record={geometry:{valid:true,geojson:{type:"Point",coordinates:[127,37]}}};
var records=[record],gpkgMetadata={spatial_tables:[{table_name:"site",records:records}]};
var payload={datasets:{site:records},gpkg_metadata:gpkgMetadata,
    tables:[{name:"site",records:records}],map_features:[record]},qpbLastReportPayload=null;
''' + serialization + r'''
process.stdout.write(JSON.stringify({html:JSON.parse(json),
    nativeUnchanged:qpbLastReportPayload===payload && payload.datasets.site===records &&
        gpkgMetadata.spatial_tables[0].records===records}));
''')
    assert result["nativeUnchanged"]
    assert "datasets" not in result["html"]
    metadata = result["html"]["gpkg_metadata"]["spatial_tables"][0]
    assert "records" not in metadata and metadata["record_count"] == 1
    assert result["html"]["tables"][0]["records"] == result["html"]["map_features"]
