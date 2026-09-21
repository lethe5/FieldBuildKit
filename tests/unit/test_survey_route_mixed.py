"""Focused production-JavaScript checks for mixed-access route boundaries."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROUTES = Path(__file__).parents[2] / "qfield_builder/qfield_routes"


def _node(source, *paths):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for route JavaScript tests")
    result = subprocess.run([node, "-e", source, *map(str, paths)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_provider_http_detail_is_bounded_redacted_and_stage_specific():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const safe=c.httpError('access-snap',404,{error:{code:'NO_ROUTE\u202e',message:' no  route '}},'application/json','secret');
const unsafe=c.httpError('directions',401,'Authorization: Bearer secret','text/plain','secret');
process.stdout.write(JSON.stringify({safe:safe.safe_record,message:safe.message,unsafe:unsafe.safe_record}));""", ROUTES / "backend.js")
    assert result["safe"]["provider_code"] == "NO_ROUTE"
    assert result["safe"]["provider_message"] == "no route"
    assert "차량 접근점(access-snap)" in result["message"]
    assert result["unsafe"]["safe_text"] is None


def test_origin_validation_requires_provider_location_before_any_later_request():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);(async()=>{let requests=[],message='';
const settings={backend:'ors-vroom',server_url:'https://routing.invalid',optimizer_url:'https://optimizer.invalid',profile:'driving-car',timeout_ms:1000,max_road_offset_m:1000,max_access_distance_m:2000};
const targets=[{source_layer:'site',site_id:'A',name:'A',coordinate:[127.1,37.1]}];
try{await c.calculateMixed(settings,targets,[127,37],true,request=>{requests.push(request);return Promise.resolve({durations:[[0]],sources:[{location:null,snapped_distance:12.5}]})})}catch(e){message=e.message}
process.stdout.write(JSON.stringify({stages:requests.map(r=>r.stage),message}));})().catch(e=>{console.error(e);process.exit(1)});""", ROUTES / "backend.js")
    assert result["stages"] == ["origin-validation"]
    assert "출발지" in result["message"]


def test_snapped_distance_is_optional_but_present_values_keep_stage_and_limit():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);let errors=[];
c.snappedDistance({},'origin-validation');c.snappedDistance({snapped_distance:1000},'matrix',1000);
for(const [row,stage,max] of [[{snapped_distance:'1'},'origin-validation',undefined],[{snapped_distance:1000.01},'matrix',1000]]){
  try{c.snappedDistance(row,stage,max)}catch(error){errors.push({category:error.category,stage:error.stage})}
}
process.stdout.write(JSON.stringify({errors}));""", ROUTES / "backend.js")
    assert result["errors"] == [
        {"category": "provider_response", "stage": "origin-validation"},
        {"category": "provider_response", "stage": "matrix"},
    ]


def test_ios_apple_maps_is_single_dispatch_and_android_fallback_remains():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);let ios=[],android=[];
let iosError='';try{c.open({coordinate:[127.123,37.456],name:'ignored'},u=>{ios.push(u);return false},'ios','id')}catch(e){iosError=e.message}
const androidResult=c.open({coordinate:[127.123,37.456],name:'한글 & #% '},u=>{android.push(u);return android.length===2},'android','org.example');
process.stdout.write(JSON.stringify({ios,iosError,android,androidResult}));""", ROUTES / "navigation.js")
    assert result["ios"] == ["https://maps.apple.com/directions?destination=37.456,127.123&mode=driving"]
    assert result["iosError"] == "Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요."
    assert result["android"][0].startswith("intent://navigation?")
    assert result["android"][1] == "market://details?id=com.nhn.android.nmap"


def test_repository_accepts_schema3_and_rejects_future_schema_without_write():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);let files={},writes=0;
const io={exists:p=>p in files,read:p=>files[p],write:(p,v)=>{writes++;files[p]=v;return true}};
const leg={sequence:1,from:'start',to:{layer_id:'site',site_id:'A'},distance_m:1,duration_s:2,geometry:{type:'LineString',coordinates:[[127,37],[127.1,37.1]]}};
const walking=[{direction:'outbound',distance_m:0,duration_s:0,geometry:null},{direction:'return',distance_m:0,duration_s:0,geometry:null}];
const route={route_id:'r',name:'r',revision:1,start:[127,37],end:[127.1,37.1],stops:[{source_layer:'site',site_id:'A',sequence:1,completed:false,coordinate:[127.1,37.1]}],distance_m:1,duration_s:2,road_geometry:leg.geometry,legs:[leg],vehicle_legs:[leg],visits:[{layer_id:'site',site_id:'A',source_coordinate:[127.1,37.1],access_coordinate:[127.1,37.1],access_offset_m:0,walking_mode:'exact_zero',walking_legs:walking,trip_multiplier:2,metric_source:'exact_zero'}],vehicle_totals:{distance_m:1,duration_s:2},walking_totals:{mapped_distance_m:0,lower_bound_distance_m:0,duration_s:0,unavailable_duration_count:0},combined_totals:{distance_m:1,duration_s:2}};
const inactive=JSON.parse(JSON.stringify(route));inactive.route_id='inactive';inactive.name='inactive';
const saved=c.save(io,'routes',{schema:3,active_id:'r',routes:[inactive,route],settings:{}},0);let future='',missing='',visit='';try{c.validate({schema:99})}catch(e){future=e.message}
const broken=JSON.parse(JSON.stringify(saved.data));delete broken.routes[0].combined_totals;try{c.validate(broken)}catch(e){missing=e.message}
const corrupt=JSON.parse(JSON.stringify(saved.data));corrupt.routes[1].visits[0].metric_source='guessed';try{c.validate(corrupt)}catch(e){visit=e.message}
const path='routes.a.json',before=files[path],envelope=JSON.parse(before),payload=JSON.parse(envelope.payload);delete payload.routes[1].visits[0].layer_id;envelope.payload=JSON.stringify(payload);envelope.checksum=c.checksum(envelope.payload);files[path]=JSON.stringify(envelope);const corrupted=files[path],writesBefore=writes;let load='';try{c.load(io,'routes')}catch(e){load=e.message}
process.stdout.write(JSON.stringify({schema:saved.data.schema,routeCount:saved.data.routes.length,writes,future,missing,visit,load,bytesPreserved:files[path]===corrupted,writesOnLoad:writes-writesBefore}));""", ROUTES / "repository.js")
    assert result["schema"] == 3 and result["routeCount"] == 2 and result["writes"] == 1
    assert "더 최신 형식" in result["future"]
    assert "combined_totals" in result["missing"]
    assert "손상" in result["visit"] and "손상" in result["load"]
    assert result["bytesPreserved"] is True and result["writesOnLoad"] == 0


def test_exact_zero_preserves_sub_meter_offset_and_rejects_mismatch():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),c);const source=[127.1,37.1],access=[127.100005,37.1];
const visit=c.walkingVisit({source_layer:'site',site_id:'A',coordinate:source},access,null);
const leg={sequence:1,from:'start',to:{layer_id:'site',site_id:'A'},distance_m:1,duration_s:2,geometry:{type:'LineString',coordinates:[[127,37],source]}};
const route={route_id:'r',name:'r',revision:1,start:[127,37],end:source,stops:[{source_layer:'site',site_id:'A',sequence:1,completed:false,coordinate:source}],distance_m:1,duration_s:2,road_geometry:leg.geometry,legs:[leg],vehicle_legs:[leg],visits:[visit],vehicle_totals:{distance_m:1,duration_s:2},walking_totals:{mapped_distance_m:0,lower_bound_distance_m:0,duration_s:0,unavailable_duration_count:0},combined_totals:{distance_m:1,duration_s:2}};
let accepted=false,rejected=false;try{c.validate({schema:3,active_id:'r',routes:[route],settings:{}});accepted=true}catch(e){}const preserved=JSON.parse(JSON.stringify(visit));
route.visits[0].access_offset_m+=0.1;try{c.validate({schema:3,active_id:'r',routes:[route],settings:{}})}catch(e){rejected=true}
process.stdout.write(JSON.stringify({visit:preserved,accepted,rejected,measured:c.haversine(access,source)}));""", ROUTES / "backend.js", ROUTES / "repository.js")
    visit = result["visit"]
    assert 0 < result["measured"] <= 1
    assert visit["access_offset_m"] == pytest.approx(result["measured"], abs=0.01)
    assert all(leg["distance_m"] == leg["duration_s"] == 0 and leg["geometry"] is None
               for leg in visit["walking_legs"])
    assert result["accepted"] is True and result["rejected"] is True


def test_schema1_settings_upgrade_preserves_legacy_variant_on_mixed_save():
    result = _node(r"""const fs=require('fs'),vm=require('vm'),c=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const legacy=id=>({route_id:id,name:id,revision:1,start:[127,37],end:[127.1,37.1],roundtrip:false,backend:'ors-vroom',stops:[{source_layer:'site',site_id:id,sequence:1,completed:false,coordinate:[127.1,37.1]}],eta:null,eta_basis:null});
let document={schema:1,active_id:'selected',routes:[legacy('selected'),legacy('unrelated')],settings:{}},revision=1;
const repository={load:()=>({data:JSON.parse(JSON.stringify(document)),revision,slot:'a'}),save:(_io,_base,data)=>{document=JSON.parse(JSON.stringify(data));return {data:document,revision:++revision,slot:'b'}}};
const line={type:'LineString',coordinates:[[127,37],[127.1,37.1]]};
const leg={sequence:1,from:'start',to:{layer_id:'site',site_id:'selected'},distance_m:1,duration_s:2,geometry:line};
const walking=[{direction:'outbound',distance_m:0,duration_s:0,geometry:null},{direction:'return',distance_m:0,duration_s:0,geometry:null}];
const mixed={stops:[{source_layer:'site',site_id:'selected',name:'selected',coordinate:[127.1,37.1],completed:false}],distance_m:1,duration_s:2,road_geometry:line,legs:[leg],eta:null,eta_basis:null,vehicle_legs:[leg],visits:[{layer_id:'site',site_id:'selected',source_coordinate:[127.1,37.1],access_coordinate:[127.1,37.1],access_offset_m:0,walking_mode:'exact_zero',walking_legs:walking,trip_multiplier:2,metric_source:'exact_zero'}],vehicle_totals:{distance_m:1,duration_s:2},walking_totals:{mapped_distance_m:0,lower_bound_distance_m:0,duration_s:0,unavailable_duration_count:0},combined_totals:{distance_m:1,duration_s:2}};
const deps={repository,io:{},base:'routes',features:()=>[{id:'selected',name:'selected',coordinate:[127.1,37.1],completed:false}],geometry:{coordinate:v=>v},gps:()=>[127,37],uuid:()=> 'new',now:()=>new Date('2026-09-21T00:00:00Z'),projectKey:()=>'',changed:()=>{},backend:{calculate:()=>Promise.resolve(mixed)}};
(async()=>{const first=c.create(deps);first.saveSettings();const upgraded=JSON.parse(JSON.stringify(document));const second=c.create(deps);second.configure({key:'test-key'});second.state.roundtrip=false;const calculated=await second.calculate(true),saved=second.save('mixed');process.stdout.write(JSON.stringify({upgraded,savedDocument:document,calculated,saved,message:second.state.message}));})().catch(error=>{console.error(error);process.exit(1)});
""", ROUTES / "controller.js")
    assert result["upgraded"]["schema"] == 2
    assert all("route_schema" not in route for route in result["upgraded"]["routes"])
    assert result["calculated"] is result["saved"] is True, result["message"]
    saved = result["savedDocument"]
    selected = next(route for route in saved["routes"]
                    if route["route_id"] == "selected")
    unrelated = next(route for route in saved["routes"]
                     if route["route_id"] == "unrelated")
    assert saved["schema"] == 3
    assert selected["route_schema"] == 3
    assert unrelated["route_schema"] == 1
    assert "legs" not in unrelated
