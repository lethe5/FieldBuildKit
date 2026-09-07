"""Focused implementation regressions for the standalone report conformance defects."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from qfield_builder import qml_plugin
from qfield_builder.html_report_core import render_html_report_integrated_fixture


def _report_runtime(source: str) -> str:
    scripts = []
    for match in re.finditer(r'html\.push\(("(?:\\.|[^"\\])*")\);', source):
        script = json.loads(match.group(1))
        if script.startswith("<script>"):
            scripts.append(script)
    return "\n".join(scripts)


def test_standalone_runtime_has_one_renderer_and_type1_uses_only_approved_cards():
    runtime = _report_runtime(
        qml_plugin.render_project_plugin_qml(
            "demo", identification_enabled=False, survey_type="simple_inventory"
        )
    )

    for function_name in ("renderCards", "renderMap", "renderSummaries", "renderJoined", "saveCsv"):
        assert len(re.findall(rf"function {function_name}\s*\(", runtime)) == 1

    assert runtime.count("function qpbInitializeReport(") == 1
    cards = runtime[
        runtime.rindex("function renderCards") : runtime.index("function qpbRunRenderer")
    ]
    assert "data.summary_stats||{}" in cards
    assert "overview_cards||[]" in cards
    assert "qpbCard(\"site\"" not in cards
    assert "qpbCard(\"plot\"" not in cards


def test_chart_renderers_use_d3_node_method_before_joined_and_map_renderers():
    runtime = _report_runtime(
        qml_plugin.render_project_plugin_qml(
            "demo", identification_enabled=False, survey_type="simple_inventory"
        )
    )
    chart_runtime = runtime[
        runtime.index("function qpbDrawBarChart") : runtime.index(
            "function qpbValidateChartInitialization"
        )
    ]

    assert "bar.node().setAttribute(\"aria-label\"" in chart_runtime
    assert "bar.node().addEventListener(\"focus\"" in chart_runtime
    assert "path.node().setAttribute(\"aria-label\"" in chart_runtime
    assert "path.node().addEventListener(\"focus\"" in chart_runtime
    assert re.search(r"(?:bar|path)\.node\.(?:setAttribute|addEventListener)", chart_runtime) is None

    initialization = runtime[runtime.index("function qpbInitializeReport") :]
    assert initialization.index("renderCharts();") < initialization.index("renderJoined();")
    assert initialization.index("renderJoined();") < initialization.index("renderMap();")


def test_species_and_integrated_report_labels_use_korean_visible_names():
    runtime = _report_runtime(
        qml_plugin.render_project_plugin_qml(
            "labels", identification_enabled=False, survey_type="simple_inventory"
        )
    )

    species = runtime[
        runtime.index("function renderSpecies") : runtime.index("function strictDate")
    ]
    assert "<th>국명</th>" in species
    assert "esc(s.korean||s.key)" in species
    assert "<th>종 식별값</th>" not in species

    assert "function qpbKoreanFieldLabel" in runtime
    assert "selected_korean_name:\"국명\"" in runtime
    assert "selected_scientific_name:\"학명\"" in runtime
    assert "selected_ktsn:\"KTSN\"" in runtime
    assert "return /[가-힣]/.test(candidate)?candidate:\"필드\"" in runtime
    joined = runtime[
        runtime.index("function renderJoined") : runtime.index("function qpbFeatureAccessibleLabel")
    ]
    assert "qpbKoreanFieldLabel(cols[i].source_table||\"\",cols[i].source_field||cols[i].key,cols[i].label)" in joined
    assert "esc(visibleLabel)+\" 열 정렬" in joined


def test_map_popup_resolves_physical_field_name_through_source_field_alias():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the generated browser runtime")

    source = qml_plugin.render_project_plugin_qml(
        "popup-label-source-field", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _report_runtime(source)

    def function_source(name: str) -> str:
        start, end = qml_plugin._js_function_span(runtime, 0, name)
        return runtime[start:end]

    harness = f"""
var data={{tables:[{{name:"inventory_observation",display_name:"inventory_observation",fields:[{{
    name:"selected_korean_name__1",source_field:"selected_korean_name",
    source_column_id:"inventory_observation__selected_korean_name",label:"selected_korean_name"
}}]}},{{name:"site",display_name:"조사지",fields:[{{name:"site_name__1",source_field:"site_name",label:"site_name"}}]}}]}};
    function esc(value){{return String(value===undefined||value===null?'':value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\\"/g,'&quot;').replace(/'/g,'&#39;');}}
{function_source("qpbKoreanTableLabel")}
    {function_source("qpbKoreanFieldLabel")}
    {function_source("qpbVisibleLabel")}
    {function_source("qpbPopupRead")}
    {function_source("qpbPopupAppend")}
    {function_source("qpbPopupObservation")}
    {function_source("qpbMapFeatureDetail")}
var detail=qpbMapFeatureDetail({{properties:{{anchor_table:"inventory_observation",anchor_uuid:"row-1"}},source:{{
    inventory_observation:{{attrs:{{"selected_korean_name__1":"상사화"}}}}
}}}});
var siteDetail=qpbMapFeatureDetail({{properties:{{anchor_table:"site"}},source:{{site:{{attrs:{{"site_name__1":"한라산<script>alert(1)</script>"}}}}}}}});
process.stdout.write(JSON.stringify({{label:qpbVisibleLabel("inventory_observation","selected_korean_name__1"),detail:detail,siteDetail:siteDetail}}));
"""
    completed = subprocess.run(
        [node, "-e", harness], check=True, capture_output=True, text=True, timeout=10
    )
    result = json.loads(completed.stdout)

    assert result["label"] == "국명"
    assert "국명: 상사화" in result["detail"]
    assert "selected_korean_name" not in result["detail"]
    assert result["siteDetail"] == "한라산&lt;script&gt;alert(1)&lt;/script&gt;"


def test_map_feature_click_opens_only_the_leaflet_popup():
    runtime = _report_runtime(
        qml_plugin.render_project_plugin_qml(
            "map-popup", identification_enabled=False, survey_type="simple_inventory"
        )
    )
    render_map = runtime[
        runtime.index("function renderMap") : runtime.index("function renderSummaries")
    ]
    assert "l.bindPopup(detail)" in render_map
    assert "l.on(\"click\",function(){if(l.openPopup)l.openPopup();})" in render_map
    assert "qpbShowMapDetail" not in runtime
    assert "qpbMapPopup" not in runtime


def test_generated_report_popup_css_is_self_contained_above_layers_and_touch_interactive():
    source = qml_plugin.render_project_plugin_qml(
        "map-popup-css", identification_enabled=False, survey_type="simple_inventory"
    )

    # The generated report embeds Leaflet's presentation CSS because the Leaflet JavaScript
    # bundle alone does not style native popups in a standalone file:///Safari document.
    assert ".leaflet-popup-pane{z-index:1100;pointer-events:none}" in source
    assert ".leaflet-popup-content-wrapper{" in source
    assert ".leaflet-popup-content{" in source
    assert ".leaflet-popup-tip-container{" in source
    assert ".leaflet-popup-tip{" in source
    assert ".leaflet-popup-close-button{" in source
    assert ".leaflet-popup,.leaflet-popup-content-wrapper,.leaflet-popup-content,.leaflet-popup-close-button{pointer-events:auto}" in source

    # The superseded custom detail surface is absent; Leaflet's native popup remains styled.
    assert ".map-popup" not in source


def test_generated_report_svg_paths_are_interactive_with_popup_and_no_label_contracts():
    source = qml_plugin.render_project_plugin_qml(
        "map-svg-pointer-events", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _report_runtime(source)
    render_map = runtime[
        runtime.index("function renderMap") : runtime.index("function renderSummaries")
    ]

    assert ".leaflet-overlay-pane svg .leaflet-interactive{pointer-events:auto}" in source
    assert "l.bindPopup(detail)" in render_map
    assert "l.on(\"click\",function(){if(l.openPopup)l.openPopup();})" in render_map
    assert "qpbPopupRead" in runtime
    assert "bindTooltip" not in render_map
    assert "qpb-map-label" not in render_map


def test_map_features_do_not_bind_permanent_labels():
    runtime = _report_runtime(
        qml_plugin.render_project_plugin_qml(
            "map-popup", identification_enabled=False, survey_type="simple_inventory"
        )
    )
    render_map = runtime[
        runtime.index("function renderMap") : runtime.index("function renderSummaries")
    ]
    assert "l.bindPopup(detail)" in render_map
    assert "l.on(\"click\",function(){if(l.openPopup)l.openPopup();})" in render_map
    assert "bindTooltip" not in render_map
    assert "qpb-map-label" not in render_map
    assert "function qpbMapKoreanLabel(mapFeature)" not in runtime
    assert "qpbMapKoreanLabel(" not in runtime


def test_theme_binding_precedes_guarded_renderers_and_updates_visible_theme_state():
    source = qml_plugin.render_project_plugin_qml(
        "demo", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _report_runtime(
        source
    )

    assert "document.documentElement.setAttribute(\"data-theme\",selected)" in runtime
    assert "document.body.setAttribute(\"data-theme\",selected)" in runtime
    assert "document.documentElement.style.colorScheme=selected" in runtime
    assert "input.checked=isDark" in runtime
    assert "document.body.classList.remove(\"light-theme\",\"dark-theme\")" in runtime
    assert "document.body.classList.add(isDark?\"dark-theme\":\"light-theme\")" in runtime
    assert "input.addEventListener(\"change\",qpbToggleTheme)" in runtime
    init = runtime[runtime.index("function qpbInitializeReport") :]
    assert init.index("qpbBindThemeControl()") < init.index("qpbApplyTheme(qpbReadTheme())")
    assert init.index("qpbApplyTheme(qpbReadTheme())") < init.index(
        "renderCards();renderSummaries();renderSpecies();renderCharts();renderJoined();renderMap();"
    )
    assert "function qpbRunRenderer(renderer,label){try{renderer();}catch(error)" in runtime

    markup = source.replace(r'\"', '"')
    assert (
        '<label for="checkbox" class="toggle">'
        '<input type="checkbox" class="checkbox" id="checkbox" aria-label="테마 전환" tabindex="0" />'
        '<div class="slider"><div class="moon"></div><div class="sun"></div></div></label>'
        in markup
    )
    assert 'data-theme-toggle="true"' not in markup
    assert "themeToggle" not in markup
    assert 'class="theme-toggle"' not in markup
    assert "<button id='themeToggle'" not in markup
    assert "밝은 테마" not in markup
    assert "어두운 테마" not in markup
    assert "🌙" not in markup
    assert "☀️" not in markup
    assert ":root{--light:#d8c21e;--dark:#111111;--ball:20px;--top:8px;--margin:8px}" in markup
    assert (
        ".checkbox{display:block;position:absolute;top:0;left:0;z-index:1;-webkit-appearance:none;"
        "appearance:none;opacity:0;width:100%;height:100%;margin:0;padding:0;border:0;border-radius:0;"
        "background:transparent;cursor:pointer}"
        in markup
    )
    assert ".toggle{display:block;position:relative;width:70px;height:40px" in markup
    assert (
        ".slider{position:relative;top:0;left:0;right:0;bottom:0;width:100%;height:100%;"
        "background:var(--dark)" in markup
    )
    assert (
        ".checkbox:checked + .slider{background-color:var(--light);border:2px solid var(--dark)}"
        in markup
    )
    assert (
        ".checkbox:checked + .slider::after{right:calc(100% - var(--margin));"
        "transform:translateX(100%)}" in markup
    )
    assert "background-image:url('data:image/svg+xml;base64," in markup
    assert "@media (prefers-color-scheme:dark)" in markup


def test_final_theme_runtime_transitions_checkbox_and_persists_with_os_fallback():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to execute the generated browser runtime")

    source = qml_plugin.render_project_plugin_qml(
        "theme-runtime", identification_enabled=False, survey_type="simple_inventory"
    )
    runtime = _report_runtime(source)

    def function_source(name: str) -> str:
        start, end = qml_plugin._js_function_span(runtime, 0, name)
        return runtime[start:end]

    theme_runtime = "\n".join(
        [
            'var themeStorageKey="qpb-report-theme";',
            function_source("qpbReadTheme"),
            function_source("qpbApplyTheme"),
            function_source("qpbToggleTheme"),
            function_source("qpbBindThemeControl"),
        ]
    )
    harness = f"""
var storedTheme=null, osDark=false;
function element() {{
    return {{attrs:{{}},style:{{}},checked:false,textContent:"",__listeners:{{}},
        listenerCounts:{{}},classList:{{values:{{}},
            add:function(){{for(var i=0;i<arguments.length;i++)this.values[arguments[i]]=true;}},
            remove:function(){{
                for(var i=0;i<arguments.length;i++)delete this.values[arguments[i]];
            }},
            contains:function(name){{return !!this.values[name];}}}},
        setAttribute:function(name,value){{this.attrs[name]=String(value);}},
        getAttribute:function(name){{return this.attrs[name]===undefined?null:this.attrs[name];}},
        addEventListener:function(name,handler){{this.__listeners[name]=handler;this.listenerCounts[name]=(this.listenerCounts[name]||0)+1;}},
        emit:function(name){{if(this.__listeners[name])this.__listeners[name]();}}
    }};
}}
var root=element(), body=element(), input=element();
var document={{documentElement:root,body:body,getElementById:function(id){{
    return id==="checkbox"?input:null;
}}}};
var window={{matchMedia:function(){{return {{matches:osDark}};}}}};
var localStorage={{getItem:function(){{return storedTheme;}},
    setItem:function(_key,value){{storedTheme=value;}}}};
{theme_runtime}
function snapshot(){{return {{theme:root.attrs["data-theme"],body_theme:body.attrs["data-theme"],
    color_scheme:root.style.colorScheme,checked:input.checked,
    dark_class:body.classList.contains("dark-theme"),light_class:body.classList.contains("light-theme")}};}}
qpbBindThemeControl();qpbBindThemeControl();qpbApplyTheme(qpbReadTheme());
var states=[snapshot()];input.checked=true;input.emit("change");states.push(snapshot());
input.checked=false;input.emit("change");states.push(snapshot());
var persisted=storedTheme;storedTheme="dark";qpbApplyTheme(qpbReadTheme());var restored=snapshot();
storedTheme=null;osDark=true;qpbApplyTheme(qpbReadTheme());var osDefault=snapshot();
process.stdout.write(JSON.stringify({{states:states,persisted:persisted,restored:restored,os_default:osDefault,
    change_listeners:input.listenerCounts.change}}));
"""
    completed = subprocess.run(
        [node, "-e", harness], check=True, capture_output=True, text=True, timeout=10
    )
    result = json.loads(completed.stdout)

    assert [state["theme"] for state in result["states"]] == ["light", "dark", "light"]
    assert [state["body_theme"] for state in result["states"]] == ["light", "dark", "light"]
    assert [state["color_scheme"] for state in result["states"]] == ["light", "dark", "light"]
    assert [state["checked"] for state in result["states"]] == [False, True, False]
    assert [state["dark_class"] for state in result["states"]] == [False, True, False]
    assert [state["light_class"] for state in result["states"]] == [True, False, True]
    assert result["persisted"] == "light"
    assert result["restored"]["theme"] == "dark"
    assert result["restored"]["checked"] is True
    assert result["restored"]["dark_class"] is True
    assert result["os_default"]["theme"] == "dark"
    assert result["change_listeners"] == 1


def test_known_numeric_wgs84_geometry_maps_without_transform_api():
    result = render_html_report_integrated_fixture(
        {
            "survey_type": "simple_inventory",
            "source_columns": [
                {
                    "id": "id",
                    "source_table": "inventory_observation",
                    "source_field": "id",
                    "schema_order": 0,
                }
            ],
            "source_rows": [
                {
                    "source_row_id": "gpkg-row-1",
                    "values": {"id": "gpkg-row-1"},
                    "geometry": {"format": "wkt", "value": "POINT ZM (127 37 100 9)"},
                }
            ],
            "spatial_metadata": [
                {
                    "table": "inventory_observation",
                    "geometry_column": "geom",
                    "geometry_type": "POINT",
                    "source_crs": 4326,
                    "record_ids": ["gpkg-row-1"],
                }
            ],
            "coordinate_transform_available": False,
        }
    )

    assert result["map_features"][0]["geometry"] == {
        "type": "Point",
        "coordinates": [127.0, 37.0],
    }
    assert result["invalid_geometries"] == []
    assert result["map_empty_notice_present"] is False
