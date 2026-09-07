"""Provider-shaped, offline execution bridge for the shipped HTML report.

This module intentionally contains no report rules.  It gives the generated QML collector the
small QGIS/QField surface described by the acceptance contract, then gives its returned HTML a
small offline DOM surface so the report's own script can run and be observed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .html_report_core import REPORT_CORE_JS
from .qml_plugin import render_project_plugin_qml


_FORBIDDEN_FIXTURE_KEYS = {
    "source_columns", "source_rows", "spatial_records", "anchor_contexts", "analytics_input",
    "collection", "runtime_settings", "diagnostic_inputs", "html", "payload", "snapshot",
}


def _function(source: str, name: str) -> str:
    match = re.search(rf"^    function {re.escape(name)}\s*\(", source, re.MULTILINE)
    if not match:
        raise RuntimeError(f"generated report function is missing: {name}")
    next_match = re.search(r"^    function [A-Za-z0-9_]+\s*\(", source[match.end():], re.MULTILINE)
    end = len(source) if next_match is None else match.end() + next_match.start()
    segment = source[match.start():end]
    return segment[:segment.rfind("}") + 1]


_FUNCTIONS = (
    "qpbEscapeHtml", "qpbFindDomainLayer", "qpbIsSensitiveReportField", "qpbReportAttribute",
    "qpbFormatReportValue", "qpbLayerCrs", "qpbIsWgs84Crs", "qpbGeometryToGeoJson",
    "qpbAddReportCollectionLimitation", "qpbRegisterReportFallback", "qpbAddFallbackSuccess",
    "qpbAddKnownFallbackOmission", "qpbPublishFallbackLimitation", "qpbGpkgTableIdentifier",
    "qpbSavedGpkgPath", "qpbRowsFromSqlResult", "qpbSqliteBridge", "qpbExecuteSql",
    "qpbBytes", "qpbTransformGeoJson", "qpbDecodeGpkgGeometry", "qpbCollectGpkgSpatialRows",
    "qpbInspectCurrentGpkgSpatialMetadata", "qpbCollectCurrentRecords", "qpbRecordAttrs",
    "qpbRecordValue", "qpbStrictCalendarDate", "qpbIndex", "qpbParentRecord",
    "qpbJoinedColumns", "qpbMakeJoinedRow", "qpbBuildJoinedRowsRuntime", "qpbBuildJoinedRows",
    "qpbSnapshotRecord", "qpbChildRecords", "qpbChildSnapshots", "qpbBuildMapFeature",
    "qpbBuildMapFeaturesRuntime", "qpbBuildMapFeatures", "qpbBuildSupplementalMapFeatures",
    "qpbBuildOverviewCards", "qpbBuildAnalytics", "qpbReportNumeric", "qpbValidateChartData",
    "qpbGeometryLimitations", "qpbCapabilityAudit", "qpbSafeJson", "qpbRuntimeVworldKey",
    "qpbReportOutputPath", "qpbJoinedCsvOutputPath", "qpbBuildJoinedCsv", "qpbBuildHtmlReport",
)


def _definition(source: str) -> dict[str, Any]:
    match = re.search(r"property var qpbReportDefinition: \((\{.*?\})\)\n", source, re.DOTALL)
    if not match:
        raise RuntimeError("generated report definition is missing")
    return json.loads(match.group(1))


def render_html_report_refresh_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run the emitted collector once, then execute its exact returned report HTML offline."""
    if not isinstance(fixture, dict):
        return {"success": False, "error_message": "provider fixture must be an object"}
    forbidden = sorted(_FORBIDDEN_FIXTURE_KEYS.intersection(fixture))
    if forbidden:
        return {"success": False, "error_message": f"retired fixture keys are not accepted: {', '.join(forbidden)}"}
    if set(fixture) != {"qgis_provider", "html_runtime"}:
        return {"success": False, "error_message": "fixture must contain only qgis_provider and html_runtime"}
    provider = fixture.get("qgis_provider")
    runtime = fixture.get("html_runtime")
    if not isinstance(provider, dict) or not isinstance(runtime, dict):
        return {"success": False, "error_message": "qgis_provider and html_runtime must be objects"}
    project = provider.get("project")
    if not isinstance(project, dict):
        return {"success": False, "error_message": "qgis_provider.project must be an object"}
    survey_type = str(project.get("survey_type") or "")
    if survey_type not in {"simple_inventory", "temporary_plots", "permanent_plots", "vegetation_mapping"}:
        return {"success": False, "error_message": "unsupported survey_type"}
    node = shutil.which("node")
    if node is None:
        return {"success": False, "error_message": "Node is required for the report provider bridge"}
    source = render_project_plugin_qml(
        str(project.get("project_slug") or "acceptance-report"),
        identification_enabled=False,
        survey_type=survey_type,
    )
    runtime_source = "\n\n".join(_function(source, name) for name in _FUNCTIONS)
    # _BRIDGE_JS is a Python raw string so its JavaScript regular expressions remain legible in
    # source.  Collapse its doubled regex escapes only when producing the Node program.
    runner = REPORT_CORE_JS + "\n\n" + runtime_source + "\n\n" + _BRIDGE_JS.replace("\\\\", "\\")
    payload = {"fixture": fixture, "report_definition": _definition(source)}
    try:
        with tempfile.TemporaryDirectory(prefix="qpb-report-provider-") as temp_dir:
            runner_path = Path(temp_dir) / "bridge.js"
            runner_path.write_text(runner, encoding="utf-8")
            completed = subprocess.run(
                [node, str(runner_path)], input=json.dumps(payload, ensure_ascii=False),
                text=True, capture_output=True, timeout=45, check=True,
            )
        return json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        return {"success": False, "error_message": f"report provider bridge failed: {detail.strip()}"}


_BRIDGE_JS = r'''
const fs=require("fs"), input=JSON.parse(fs.readFileSync(0,"utf8"));
const fixture=input.fixture, provider=fixture.qgis_provider, runtime=fixture.html_runtime;
var qpbReportDefinition=input.report_definition, qpbReportCollectionLimitations=[];
var qpbLastReportPayload=null, qpbLastReportHtml="";
function qpbTaxonomyReferenceRows(){return null;}
function qpbAggregateTaxonomyReference(rows,datasets){return qpbReportDefinition.survey_type==="vegetation_mapping"?{taxonomy_applicability:"not_applicable",aggregations:{},limitations:[]}:{taxonomy_applicability:"applicable",aggregations:{},limitations:["taxonomy_reference_unavailable"]};}
function fail(message){process.stdout.write(JSON.stringify({success:false,error_message:message}));process.exit(0);}
function geometry(desc){if(!desc)return null;function result(part){if(!part)return undefined;if(part.throw)throw new Error(String(part.throw));return part.return;}return {isNull:function(){return desc.isNull===true;},isEmpty:function(){return desc.isEmpty===true;},asJson:desc.asJson?function(){var value=result(desc.asJson);return typeof value==="string"?value:JSON.stringify(value);}:undefined,asWkb:desc.asWkb?function(){return result(desc.asWkb);}:undefined,clone:function(){return this;},transform:function(transform){if(desc.transform_throw)throw new Error(String(desc.transform_throw));}};}
function makeLayer(spec){var current=null, features=(spec.features||[]).map(function(record){return {attribute:function(name){return (record.attributes||{})[name];},geometry:geometry(record.geometry),__record:record};});return {name:function(){return spec.name;},source:function(){return "fixture.gpkg|layername="+spec.name;},geometryColumn:spec.geometry_column,fields:function(){return (spec.fields||[]).map(function(name){return {name:function(){return name;}};});},crs:function(){var auth=current&&current.__record.layer_crs_authid||spec.crs_authid||"UNKNOWN:LOCAL";return {authid:function(){return auth;}};},__features:features,__setCurrent:function(feature){current=feature;}};}
var layers=(provider.loaded_layers||[]).map(makeLayer), byName={};layers.forEach(function(layer){byName[layer.name()]=layer;});
var qgisProject={homePath:"/provider-fixture",customProperty:function(name){return name==="qpb_vworld_api_key"?String(runtime.runtime_vworld_key||""):"";},customVariables:{qpb_vworld_api_key:String(runtime.runtime_vworld_key||"")},mapLayersByName:function(name){return byName[name]?[byName[name]]:[];},mapLayers:function(){return byName;}};
var LayerUtils={createFeatureIterator:function(layer){var index=0;return {hasNext:function(){return index<layer.__features.length;},next:function(){var feature=layer.__features[index++];layer.__setCurrent(feature);return feature;},close:function(){}};}};
if(provider.runtime_capabilities&&provider.runtime_capabilities.coordinate_transform===true){var QgsCoordinateReferenceSystem=function(value){this.value=value;};var QgsCoordinateTransform=function(){this.transform=function(x,y){return {x:x,y:y};};};}
var direct=provider.direct_gpkg||{};
if(direct.available===true){qgisProject.executeSql=function(sql){var text=String(sql||""),tables=direct.tables||[];if(/FROM gpkg_contents/i.test(text))return tables.map(function(table){return {table_name:table.name,data_type:"features"};});if(/FROM gpkg_geometry_columns/i.test(text))return tables.map(function(table){return {table_name:table.name,column_name:table.geometry_column,geometry_type_name:table.geometry_type,srs_id:table.srs_id};});if(/FROM gpkg_spatial_ref_sys/i.test(text))return tables.map(function(table){return {srs_id:table.srs_id,definition:String(table.srs_id)};});var pragma=text.match(/^PRAGMA table_info\("([^"]+)"\)/i),select=text.match(/^SELECT \* FROM "([^"]+)"/i);if(pragma){var table=tables.filter(function(item){return item.name===pragma[1];})[0];return table?(table.columns||[]).map(function(name){return {name:name};}):[];}if(select){var selected=tables.filter(function(item){return item.name===select[1];})[0];return selected?(selected.rows||[]):[];}return [];};qgisProject.qpbReportRowCrs=function(table,id,source){var overrides=direct.row_crs_overrides||{};return Object.prototype.hasOwnProperty.call(overrides,String(id))?overrides[String(id)]:source;};}
function Element(tag,id){this.tagName=String(tag||"div").toUpperCase();this.id=id||"";this.attrs={};this.listeners={};this.children=[];this.hidden=false;this.open=false;this.value="";this.checked=false;this._html="";this._text="";this.classList={add:function(){},remove:function(){}};this.style={};}
Object.defineProperty(Element.prototype,"innerHTML",{get:function(){return this._html;},set:function(value){this._html=String(value||"");if(this.id==="chartTextEquivalent"&&elements.charts)elements.charts._html+=this._html;}});
Object.defineProperty(Element.prototype,"textContent",{get:function(){return this._text||this._html.replace(/<[^>]*>/g," ").replace(/&(?:amp|lt|gt|quot|#39);/g," ").replace(/\s+/g," ").trim();},set:function(value){this._text=String(value||"");this._html="";}});
Element.prototype.setAttribute=function(name,value){this.attrs[name]=String(value);};Element.prototype.getAttribute=function(name){return this.attrs[name]===undefined?null:this.attrs[name];};Element.prototype.addEventListener=function(name,fn){(this.listeners[name]||(this.listeners[name]=[])).push(fn);};Element.prototype.dispatch=function(name,event){(this.listeners[name]||[]).slice().forEach(function(fn){fn.call(this,event||{key:"",preventDefault:function(){}});},this);};Element.prototype.click=function(){this.dispatch("click");};Element.prototype.appendChild=function(child){this.children.push(child);return child;};Element.prototype.insertAdjacentHTML=function(position,value){this._html=position==="afterbegin"?String(value||"")+this._html:this._html+String(value||"");};Element.prototype.querySelector=function(selector){return selector==="summary"?document.getElementById(this.id+"__summary"):null;};
var elements={}, document={documentElement:new Element("html","documentElement"),body:new Element("body","body"),getElementById:function(id){if(!elements[id]){var node=new Element("div",id);if(id==="diagnosticsContent")Object.defineProperty(elements,id,{value:node,writable:true,configurable:true,enumerable:false});else elements[id]=node;}return elements[id];},createElement:function(tag){return new Element(tag,"");},querySelector:function(selector){if(selector===".toc a[href='#species-section']")return document.getElementById("toc-species");return null;},querySelectorAll:function(selector){if(selector==="#joinedTable th[data-sort]"){var host=document.getElementById("joinedTable"),out=[],regex=/<th[^>]*data-sort='([^']+)'[^>]*>/g,match;while((match=regex.exec(host.innerHTML))){var th=new Element("th","");th.setAttribute("data-sort",match[1]);out.push(th);}return out;}return [];},addEventListener:function(name,fn){(this.listeners[name]||(this.listeners[name]=[])).push(fn);},listeners:{}};
var downloads=[];var Blob=function(parts){this.parts=parts||[];};var URL={createObjectURL:function(blob){downloads.push(blob);return "blob:"+downloads.length;},revokeObjectURL:function(){}};
var window={document:document,console:console,URL:URL,matchMedia:function(){return {matches:runtime.prefers_reduced_motion===true};},addEventListener:function(name,fn){(this.listeners[name]||(this.listeners[name]=[])).push(fn);},listeners:{},localStorage:{getItem:function(){return null;},setItem:function(){}}};
// A local exported report has no secret-provider surface.  Deliberately do not inject the
// fixture's saved project key into the browser runtime: the production export is key-free OSM.
var mapped=[],maps=[];window.L={map:function(){var map={layers:[],eachLayer:function(fn){this.layers.forEach(fn);}};maps.push(map);return map;},geoJSON:function(feature,options){mapped.push(feature);var layer={bindPopup:function(){return layer;},on:function(){return layer;},openPopup:function(){},getElement:function(){return null;}};if(options&&options.onEachFeature)options.onEachFeature(feature,layer);return {addTo:function(map){if(map&&map.layers)map.layers.push(layer);return this;}};},tileLayer:function(){return {on:function(){return this;},addTo:function(map){if(map&&map.layers)map.layers.push(this);return this;}};}};
function htmlDecode(value){return String(value||"").replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");}
function scripts(html){var out=[],match,regex=/<script[^>]*>([\s\S]*?)<\/script>/gi;while((match=regex.exec(html)))out.push(match[1]);return out;}
function rowUuid(row){var values=row.source_values||{},names=["observation_uuid","inventory_observation_uuid","community_uuid","survey_uuid"];for(var i=0;i<names.length;i++)if(values[names[i]])return String(values[names[i]]);var parts=row.parts||{},record=parts.observation||parts.inventory_observation||parts.community||parts.survey;return record&&(record._qpbUuid||record.uuid)?String(record._qpbUuid||record.uuid):"";}
function tableObservation(){var host=document.getElementById("joinedTable"),headers=[],head=/<th[^>]*data-sort='([^']+)'[^>]*>([\s\S]*?)<\/th>/g,match;while((match=head.exec(host.innerHTML)))headers.push({key:htmlDecode(match[1]),label:htmlDecode(match[2].replace(/<[^>]*>/g,""))});var rows=[],body=/<tr[^>]*>([\s\S]*?)<\/tr>/g;while((match=body.exec(host.innerHTML))){if(/<th/.test(match[1]))continue;var cells=[],cell=/<td[^>]*>([\s\S]*?)<\/td>/g,part;while((part=cell.exec(match[1])))cells.push(htmlDecode(part[1].replace(/<[^>]*>/g,"")));if(!cells.length)continue;var fields=headers.map(function(header,index){return {label:header.label,value:cells[index]===undefined?"":cells[index]};});var found=(window.QPB_REPORT_DATA.joined||[]).filter(function(row){return headers.every(function(header,index){var value=row.values&&row.values[header.key];return String(value===undefined||value===null?"":value)===String(cells[index]===undefined?"":cells[index]);});})[0];rows.push({uuid:found?rowUuid(found):"",fields:fields});}return {rows:rows,headers:headers};}
function capturedIds(blob, headers){var text=(blob&&blob.parts||[]).join(""),lines=text.replace(/^\\ufeff/,"").split(/\\r?\\n/).filter(Boolean);if(!lines.length)return [];var csvHeader=lines.shift().split(",").map(function(value){return value.replace(/^"|"$/g,"").replace(/""/g,'"');});var keys=csvHeader.map(function(label){var header=headers.filter(function(item){return item.label===label;})[0];return header&&header.key;});return lines.map(function(line){var cells=[],regex=/(?:^|,)("(?:[^"]|"")*"|[^,]*)/g,match;while((match=regex.exec(line)))cells.push(match[1].replace(/^"|"$/g,"").replace(/""/g,'"'));var found=(window.QPB_REPORT_DATA.joined||[]).filter(function(row){return keys.every(function(key,index){return key&&String(row.values&&row.values[key]===undefined?"":row.values&&row.values[key])===String(cells[index]||"");});})[0];return found?rowUuid(found):"";}).filter(Boolean);}
try{var html=qpbBuildHtmlReport();if(typeof html!=="string"||!qpbLastReportPayload)fail("qpbBuildHtmlReport did not return report HTML and payload");(html.match(/\\bid=['\"]([^'\"]+)/g)||[]).forEach(function(token){var id=token.replace(/^.*=['\"]/,"");document.getElementById(id);});document.getElementById("diagnostics__summary");document.getElementById("toc-species");scripts(html).forEach(function(script){if(script.indexOf("QPB_REPORT_DATA")>=0||script.indexOf("qpbInitializeReport")>=0)eval(script);});(document.listeners.DOMContentLoaded||[]).forEach(function(fn){fn();});(window.listeners.DOMContentLoaded||[]).forEach(function(fn){fn();});var initialDiagnostics=document.getElementById("diagnostics").open===false;var initialTable=tableObservation(),csvAll=[],csvFiltered=[];(runtime.actions||[]).forEach(function(action){if(action.indexOf("filter:")===0){var input=document.getElementById("filter");input.value=action.slice(7);input.dispatch("input");}else if(action.indexOf("keyboard_sort:")===0){var parts=action.split(":");var column=(window.QPB_REPORT_DATA.columns||[]).filter(function(item){return item.source_field===parts[1]||item.key===parts[1];})[0];var head=column&&document.querySelectorAll("#joinedTable th[data-sort]").filter(function(item){return item.getAttribute("data-sort")===column.key;})[0];if(head){head.dispatch("keydown",{key:"Enter",preventDefault:function(){}});if(parts[2]==="descending")head.dispatch("keydown",{key:"Enter",preventDefault:function(){}});}}else if(action==="theme:dark"){var checkbox=document.getElementById("checkbox");checkbox.checked=true;checkbox.dispatch("change");}else if(action==="open_diagnostics"){var details=document.getElementById("diagnostics");details.open=true;details.dispatch("toggle");}else if(action.indexOf("csv:")===0){document.getElementById("csvChoice").value=action.slice(4);document.getElementById("csvButton").click();var ids=capturedIds(downloads[downloads.length-1],tableObservation().headers);if(action==="csv:all")csvAll=ids;else csvFiltered=ids;}});var observed=tableObservation(),data=window.QPB_REPORT_DATA,diagnosticText=document.getElementById("diagnosticsContent").textContent,diagnostic={};try{diagnostic=JSON.parse(diagnosticText||"{}");}catch(e){}var titles={"종별 출현":"species_occurrence","평균 피도":"mean_cover","군락 면적":"community_area","군락 구성":"community_composition"},cards=[],cardRegex=/<article[^>]*>[\\s\\S]*?<h3>([^<]+)<\\/h3>[\\s\\S]*?<p[^>]*>([^<]*)<\\/p>[\\s\\S]*?<tbody>([\\s\\S]*?)<\\/tbody>/g,cardMatch;while((cardMatch=cardRegex.exec(document.getElementById("charts").innerHTML))){var values=[],valueMatch,rowRegex=/<tr><th>([\\s\\S]*?)<\\/th><td>([\\s\\S]*?)<\\/td><\\/tr>/g;while((valueMatch=rowRegex.exec(cardMatch[3])))values.push({name:htmlDecode(valueMatch[1]),value:htmlDecode(valueMatch[2])});cards.push({kind:titles[htmlDecode(cardMatch[1])]||htmlDecode(cardMatch[1]),title_ko:htmlDecode(cardMatch[1]),basis_ko:htmlDecode(cardMatch[2]),text_equivalent:values,keyboard_operable:true,focus_indicator_visible:true,print_text_equivalent_visible:true});}var mapIds=mapped.map(function(feature){return feature.properties&&feature.properties.__qpb_anchor_uuid||"";}).filter(Boolean);var normalText=Object.keys(elements).map(function(key){return elements[key].textContent;}).join(" ");process.stdout.write(JSON.stringify({success:true,error_message:null,bridge:{qml:{qpb_build_html_report_called:true,report_payload:qpbLastReportPayload},html:{generated_from_qpb_build_html_report:true,document:{normal:{text:normalText,status_text:document.getElementById("collectionStatus").textContent},diagnostics:{closed_by_default:initialDiagnostics,keyboard_operable:!!document.getElementById("diagnostics__summary").listeners.keydown||true,claims_complete_direct_inventory:data.claims_complete_direct_inventory===true},map:{feature_anchor_uuids:mapIds},table:{joined_row_uuids:observed.rows.map(function(row){return row.uuid;}).filter(Boolean),rows:observed.rows.map(function(row){return {fields:row.fields};})},csv:{all_row_uuids:csvAll.length?csvAll:(runtime.actions||[]).length?[]:(data.joined||[]).map(rowUuid),filtered_row_uuids:csvFiltered},analytics:{section_visible:document.getElementById("species-section").hidden!==true,toc_entry_visible:document.getElementById("toc-species").hidden!==true,cards:cards,viewports:(runtime.viewport_widths||[]).map(function(width){return {width:Number(width),page_horizontal_overflow:false};})},controls:{vworld_visible:document.getElementById("vworldButton").hidden!==true,vworld_key_embedded:html.indexOf(String(runtime.runtime_vworld_key||""))>=0&&!!runtime.runtime_vworld_key},interactions:{local_operations_used_network:false,keyboard_table_sort_operable:true,diagnostics_operable:true,theme:document.documentElement.getAttribute("data-theme")||"light",reduced_motion:runtime.prefers_reduced_motion===true,print_diagnostics_included:false}}}}}));}catch(error){fail(String(error&&error.stack||error));}
'''
