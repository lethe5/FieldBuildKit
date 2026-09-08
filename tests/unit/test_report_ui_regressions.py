"""Execute the actual embedded report renderers, without network or a browser."""

import json
import re
import subprocess

import pytest

from qfield_builder.qml_plugin import _js_function_span, render_project_plugin_qml


@pytest.fixture(scope="module")
def runtime():
    source = render_project_plugin_qml("ui", survey_type="temporary_plots")
    scripts = [json.loads(m.group(1)) for m in
               re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source)]
    return "\n".join(s for s in scripts if s.startswith("<script>"))


def run(runtime, names, script):
    functions = []
    for name in names:
        start, end = _js_function_span(runtime, 0, name)
        functions.append(runtime[start:end])
    result = subprocess.run(
        ["node", "-"], input="\n".join(functions) + "\n" + script,
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=20,
    )
    return json.loads(result.stdout)


def test_chart_axes_and_korean_labels_keep_distinct_species(runtime):
    result = run(runtime, ["qpbCoverChartValues", "qpbDrawBarChart"], r'''
var data={summary_stats:{chart_stats:{cover:[
    {name:"나팔꽃 · Ipomoea nil · 120000083551",value:5},
    {name:"나팔꽃 · another species · 2",korean:"나팔꽃",value:11}]}}};
var nodes=[], host={innerHTML:""}, document={querySelector:()=>host,getElementById:()=>host};
function selection(tag){var n={tag:tag,attrs:{},setAttribute:function(k,v){this.attrs[k]=v;},
    addEventListener:function(){}};nodes.push(n);return {
    append:selection,attr:function(k,v){n.attrs[k]=v;return this;},
    text:function(v){n.text=v;return this;},node:()=>n};}
function scale(band){var domain=[],range=[];var s=function(v){return band?
    range[0]+domain.indexOf(v)*100:range[0]+v/domain[1]*(range[1]-range[0]);};
    s.domain=function(v){domain=v;return s;};s.range=function(v){range=v;return s;};
    s.padding=s.nice=function(){return s;};s.bandwidth=()=>60;return s;}
var d3={select:()=>selection("host"),scaleBand:()=>scale(true),scaleLinear:()=>scale(false)};
var cover=qpbCoverChartValues();
qpbDrawBarChart("#cover",cover,"평균 피도");
qpbDrawBarChart("#occurrence",[{name:"나팔꽃",value:1}],"종별 출현");
process.stdout.write(JSON.stringify({cover:cover,nodes:nodes}));
''')
    assert [v["name"] for v in result["cover"]] == ["나팔꽃", "나팔꽃"]
    assert result["cover"][0]["key"] != result["cover"][1]["key"]
    texts = [n.get("text") for n in result["nodes"] if n["tag"] == "text"]
    assert "평균 피도 (%)" in texts and "출현 횟수 (회)" in texts
    assert not any(" · " in str(t) for t in texts)
    bars = [n for n in result["nodes"] if n["tag"] == "rect"]
    assert bars[0]["attrs"]["x"] != bars[1]["attrs"]["x"]


def test_expanded_summaries_have_escaped_records_or_explicit_empty_state(runtime):
    result = run(runtime, ["renderSummaries", "qpbNormalColumn", "qpbKoreanFieldLabel"], r'''
var host={innerHTML:""},document={getElementById:()=>host};
function esc(v){return String(v).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
var data={tables:[{name:"site",fields:[{name:"site_id"},{name:"site_name"}],
    records:[{attrs:{site_id:"hidden-id",site_name:"<서울>"}}]},
    {name:"survey",fields:[{name:"survey_date"}],records:[{attrs:{survey_date:"2026-09-08"}}]},
    {name:"plot",fields:[],records:[]}]};
renderSummaries();process.stdout.write(JSON.stringify(host.innerHTML));
''')
    assert "&lt;서울&gt;" in result and "2026-09-08" in result
    assert "hidden-id" not in result
    assert "등록된 조사구 기록이 없습니다" in result
    assert result.count("<tbody>") == 2 and result.count("<details>") == 3


@pytest.mark.parametrize("count", [0, 18])
def test_map_finishes_loading_even_when_no_geometry_is_available(runtime, count):
    result = run(runtime, ["renderMap"], r'''
var removed=false,added=0,placeholder={parentNode:{removeChild:()=>{removed=true;}}};
var host={innerHTML:"",querySelector:()=>placeholder,
    insertAdjacentHTML:function(position,text){this.innerHTML+=text;}};
var status={},document={getElementById:id=>id==="map"?host:status};
var map={setView:function(){return this;},fitBounds:function(){}};
var window={L:{map:()=>map,geoJSON:()=>({addTo:()=>{added++;}})}};
function qpbSelectBackground(){}function qpbMapFeatureDetail(){return "";}
function qpbCollectionStatus(){return "collected";}
var data={map_features:Array.from({length:COUNT},()=>({geometry:{valid:true,
    geojson:{type:"Point",coordinates:[127,37]}}}))};
renderMap();process.stdout.write(JSON.stringify({removed:removed,added:added,html:host.innerHTML}));
'''.replace("COUNT", str(count)))
    assert result["removed"] and result["added"] == count
    assert ("표시 가능한 도형이 없습니다" in result["html"]) == (count == 0)
