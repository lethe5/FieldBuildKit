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
        if name == "esc":  # Quote-matching regexes confuse the lightweight brace scanner.
            functions.append(next(line for line in runtime.splitlines()
                                  if line.startswith("function esc(")))
            continue
        start, end = _js_function_span(runtime, 0, name)
        functions.append(runtime[start:end])
    result = subprocess.run(
        ["node", "-"], input="\n".join(functions) + "\n" + script,
        text=True, encoding="utf-8", capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_chart_axes_and_korean_labels_keep_distinct_species(runtime):
    result = run(runtime, ["qpbSpeciesChartLabel", "qpbCoverChartValues", "qpbDrawBarChart"], r'''
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


@pytest.mark.parametrize("anchor", ["survey", "plot"])
def test_plot_popup_separates_many_records_into_escaped_table_rows(runtime, anchor):
    result = run(runtime, ["esc", "qpbPopupRead", "qpbPopupAppend",
                           "qpbPopupObservation", "qpbMapFeatureDetail"], r'''
var data={tables:[]};
var observations=Array.from({length:120},function(_,i){return {
    attrs:{selected_korean_name:i===0?"<script>국명</script>":"국명 "+i,
        selected_scientific_name:"Scientific "+i,selected_ktsn:"hidden-id"},
    survey_context:{uuid:"survey-"+(i%2),attrs:{survey_date:"2026-09-0"+(i%2+1),
        surveyor:"조사자 "+(i%2+1)}}};});
observations[1].attrs.selected_scientific_name=null;
var feature={anchor_table:"ANCHOR",source:{site:{attrs:{site_name:"조사지 & 이름"}},
    plot:{attrs:{plot_name:"방형구 A"}},survey:{attrs:{survey_date:"wrong-date"}}},
    related_observations:observations};
var before=JSON.stringify(feature),html=qpbMapFeatureDetail(feature);
process.stdout.write(JSON.stringify({html:html,unchanged:before===JSON.stringify(feature)}));
'''.replace("ANCHOR", anchor))
    html = result["html"]
    assert result["unchanged"]
    assert html.count("<tr>") == 121 and html.count("scope='row'") == 120
    assert "관찰 목록 (120건)" in html and "방형구 A" in html
    assert "조사지 &amp; 이름" in html and "&lt;script&gt;국명&lt;/script&gt;" in html
    assert "<script>" not in html and "hidden-id" not in html and "wrong-date" not in html
    rows = html.split("<tbody>")[1].split("</tbody>")[0].split("</tr>")
    assert "2026-09-01" in rows[0] and "조사자 1" in rows[0]
    assert "2026-09-02" in rows[1] and "조사자 2" in rows[1] and "<td>—</td>" in rows[1]
    assert "tabindex='0'" in html and "scope='col'" in html
    assert "qpb-popup-scroll" in html


def test_plot_popup_empty_state_and_other_anchor_popups_are_preserved(runtime):
    result = run(runtime, ["esc", "qpbPopupRead", "qpbPopupAppend",
                           "qpbPopupObservation", "qpbMapFeatureDetail"], r'''
var data={tables:[]};
process.stdout.write(JSON.stringify([
    qpbMapFeatureDetail({anchor_table:"plot",related_observations:[]}),
    qpbMapFeatureDetail({anchor_table:"site",source:{site:{attrs:{site_name:"<조사지>"}}}}),
    qpbMapFeatureDetail({anchor_table:"inventory_observation",source:{inventory_observation:{
        attrs:{selected_korean_name:"소나무",observed_at:"2026-09-08"}}}})
]));
''')
    assert "등록된 관찰 기록이 없습니다" in result[0]
    assert result[1] == "&lt;조사지&gt;"
    assert "소나무" in result[2] and "2026-09-08" in result[2] and "<table>" not in result[2]


@pytest.mark.parametrize("width", [240, 900])
def test_plot_popup_dimensions_fit_the_map(runtime, width):
    result = run(runtime, ["renderMap"], r'''
var options=null,host={clientWidth:WIDTH,clientHeight:300,innerHTML:"",querySelector:()=>null};
var document={getElementById:()=>host},map={setView:function(){return this;},fitBounds:()=>{}};
var window={L:{map:()=>map,geoJSON:function(feature,settings){
    settings.onEachFeature(feature,{bindPopup:function(html,value){options=value;},on:()=>{}});
    return {addTo:()=>{}};}}};
function qpbSelectBackground(){}function qpbMapFeatureDetail(){return "popup";}
function qpbCollectionStatus(){return "collected";}
var data={map_features:[{anchor_table:"plot",geometry:{valid:true,
    geojson:{type:"Point",coordinates:[127,37]}}}]};
renderMap();process.stdout.write(JSON.stringify(options));
'''.replace("WIDTH", str(width)))
    assert result["maxWidth"] == min(640, width - 64)
    assert result["maxHeight"] == 220


def test_popup_styles_override_wide_report_tables_and_keep_scroll_headers():
    source = render_project_plugin_qml("popup", survey_type="permanent_plots")
    assert ".qpb-popup-scroll table{min-width:560px;" in source
    assert "max-height:230px;overflow:auto" in source
    assert ".qpb-popup-scroll thead th{position:sticky;top:0;" in source
    assert ".qpb-popup-scroll tbody tr:nth-child(even)" in source


def test_species_charts_and_value_tables_fall_back_to_scientific_names(runtime):
    result = run(runtime, ["esc", "qpbSpeciesChartLabel", "qpbCoverChartValues",
                           "renderCharts", "qpbRenderAnalyticsCards"], r'''
var species=[{korean:" 소나무 ",scientific:"Pinus densiflora",key:"private-1",count:2},
    {korean:null,scientific:" Quercus acutissima ",key:"private-2",count:1},
    {korean:"   ",scientific:"Ipomoea nil",key:"private-3",count:1},
    {scientific:" ",key:"private-4",count:1}];
var cover=species.map(function(s,i){return {name:" · "+(s.scientific||"")+" · private-"+i,
    korean:s.korean,scientific:s.scientific,value:i};});
var data={definition:{survey_type:"temporary_plots"},summary_stats:{species:species,
    chart_stats:{cover:cover}}},hosts={};
var document={getElementById:function(id){return hosts[id]||(hosts[id]={innerHTML:""});},
    querySelector:()=>({})};
function qpbValidateChartInitialization(){return true;}
function qpbDrawBarChart(){}function qpbDrawPieChart(){}
var before=JSON.stringify(data),charts=renderCharts();qpbRenderAnalyticsCards();
var unchanged=before===JSON.stringify(data);
data.summary_stats.chart_stats.cover=[{name:" · Legacy species · 123",
    korean:"국명 미입력",value:5}];
process.stdout.write(JSON.stringify({charts:charts,html:hosts.charts.innerHTML,
    legacy:qpbCoverChartValues(),originalCover:cover,unchanged:unchanged}));
''')
    expected = ["소나무", "Quercus acutissima", "Ipomoea nil", "미동정"]
    assert result["unchanged"]
    assert [s["name"] for s in result["charts"]["occurrence"]] == expected
    assert [s["name"] for s in result["charts"]["cover"]] == expected
    assert all(name in result["html"] for name in expected)
    assert "private-" not in result["html"]
    assert result["legacy"][0]["name"] == "Legacy species"
    assert result["originalCover"][2]["korean"] == "   "  # Display-only fallback.
