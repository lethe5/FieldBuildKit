// Production controller; external QField objects, transport and files are injected at the boundary.
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function create(deps) {
    var state = {message: "", busy: false, expanded: false, listed: [], candidate: null, candidateGeneration: 0, snapshot: null, lastError: null,
        mapping: {layer: "site", id: "site_id", name: "site_name", completed: ""}, scope: "selected", startMode: "gps", mapStart: null, targetStart: "", roundtrip: true, showRouteLine: true,
        calculationGeneration:0, settings: {server_url: "https://api.heigit.org/openrouteservice", optimizer_url: "https://api.heigit.org/vroom/v0", backend: "ors-vroom", profile: "driving-car", key: "", timeout_ms: 30000, max_road_offset_m: 1000, max_access_distance_m:2000, objective: "time"}};
    function calculationInputs() {
        return JSON.stringify({mapping:state.mapping,scope:state.scope,startMode:state.startMode,mapStart:state.mapStart,
            targetStart:state.targetStart,roundtrip:state.roundtrip,settings:state.settings});
    }
    function targetInputs(list) {
        return JSON.stringify(list.map(function(target){return {site_id:target.site_id,source_layer:target.source_layer,
            name:target.name,coordinate:target.coordinate,completed:target.completed};}));
    }
    function localSurveyName(value) {
        var now = value === undefined ? (deps.now ? deps.now() : new Date()) : value;
        if (!(now instanceof Date)) now = new Date(now);
        function two(value) { return value < 10 ? "0" + value : String(value); }
        return now.getFullYear() + "-" + two(now.getMonth() + 1) + "-" + two(now.getDate()) + " 조사";
    }
    function notify() { if (deps.changed) deps.changed(); }
    function error(e) {
        state.lastError=e.safe_record||{category:e.category||"client_processing",reference:e.reference===undefined?null:String(e.reference),stage:e.stage||null,http_status:e.http_status||null};
        state.lastErrorClassification=e.classification||null;
        state.suggestedActions=Array.isArray(e.suggested_actions)?e.suggested_actions.slice():[];
        state.message = String(e.message || e).split(state.settings.key || "\u0000").join("[숨김]"); notify();
    }
    function active() { return state.snapshot.data.routes.find(function(r) { return r.route_id === state.snapshot.data.active_id; }) || null; }
    function storedPath() {
        var base = String(deps.base || "survey-routes").replace(/\\/g, "/").split("/").pop();
        return base + "." + state.snapshot.slot + ".json";
    }
    function commit(data) {
        state.snapshot = deps.repository.save(deps.io, deps.base, data, state.snapshot.revision);
        notify(); return storedPath();
    }
    function providerUrl(value) {
        var url = String(value || "").trim();
        if (!/^https?:\/\/[^/?#]+(?:\/[^?#]*)?(?:\?[^#]*)?(?:#.*)?$/.test(url))
            throw new Error("서버 주소, 제한시간, 도로 이격거리와 차량 최대 접근 거리를 확인하세요.");
        var suffix=url.match(/([?#].*)$/), base=suffix ? url.slice(0,suffix.index) : url;
        return base.replace(/\/+$/, "")+(suffix?suffix[1]:"");
    }
    function persistedProviderUrl(value) {
        return providerUrl(value).split(/[?#]/,1)[0].replace(/\/+$/, "");
    }
    function reload() {
        try {
            state.snapshot = deps.repository.load(deps.io, deps.base);
            Object.assign(state.settings, state.snapshot.data.settings);
            state.settings.server_url = persistedProviderUrl(state.settings.server_url);
            state.settings.optimizer_url = persistedProviderUrl(state.settings.optimizer_url || "https://api.heigit.org/vroom/v0");
            if (state.settings.server_url === "https://api.openrouteservice.org") state.settings.server_url = "https://api.heigit.org/openrouteservice";
            if (!state.settings.optimizer_url || state.settings.optimizer_url === "https://api.openrouteservice.org/optimization") state.settings.optimizer_url = "https://api.heigit.org/vroom/v0";
            state.settings.key = deps.projectKey ? String(deps.projectKey() || "").trim() : "";
            state.keySource = state.settings.key ? "project" : "manual";
            state.showRouteLine = state.snapshot.data.settings.show_route_line !== false;
            if(state.snapshot.data.settings.mapping) state.mapping=clone(state.snapshot.data.settings.mapping); if(active() && active().mapping) state.mapping=clone(active().mapping); state.message = state.snapshot.recovered ? "손상된 저장본을 발견하여 정상 사본을 불러왔습니다." : ""; refresh(); notify();
        }
        catch(e) { error(e); throw e; }
    }
    function settings(values) {
        var merged = Object.assign({}, state.settings, values);
        merged.server_url = providerUrl(merged.server_url);
        merged.optimizer_url = providerUrl(merged.optimizer_url || "https://api.heigit.org/vroom/v0");
        if (merged.server_url === "https://api.openrouteservice.org") merged.server_url = "https://api.heigit.org/openrouteservice";
        if (!merged.optimizer_url || merged.optimizer_url === "https://api.openrouteservice.org/optimization") merged.optimizer_url = "https://api.heigit.org/vroom/v0";
        if (!/^https?:\/\//.test(merged.server_url) || !/^https?:\/\//.test(merged.optimizer_url) || !Number.isInteger(merged.timeout_ms) || merged.timeout_ms <= 0 || !isFinite(merged.max_road_offset_m) || merged.max_road_offset_m < 0 || !isFinite(merged.max_access_distance_m) || merged.max_access_distance_m<350 || merged.max_access_distance_m>5000) throw new Error("서버 주소, 제한시간, 도로 이격거리와 차량 최대 접근 거리를 확인하세요.");
        state.settings = merged;
        state.keySource = merged.key && deps.projectKey && merged.key === String(deps.projectKey() || "").trim() ? "project" : "manual";
        notify();
    }
    function targets() {
        if (![state.mapping.layer, state.mapping.id, state.mapping.name].every(function(v) { return typeof v === "string" && v.trim(); }))
            throw new Error("조사지 레이어, 조사지 ID 필드, 조사지 이름 필드를 모두 선택하세요.");
        var records = deps.features(state.mapping, state.scope), seen = Object.create(null);
        var list = records.map(function(record) {
            var id = record.id;
            if (id === null || id === undefined || !String(id).trim() || seen[String(id)]) throw new Error("조사지 ID가 비어 있거나 중복되었습니다.");
            id = String(id); seen[id] = true;
            return {site_id: id, source_layer: state.mapping.layer, name: String(record.name || id), coordinate: deps.geometry.coordinate(record.coordinate), completed: record.completed === true};
        });
        if (!state.mapping.completed && active()) list.forEach(function(t) {var saved=active().stops.find(function(s){return s.site_id===t.site_id && s.source_layer===t.source_layer;});if(saved)t.completed=saved.completed;});
        if (state.scope === "uncompleted") list = list.filter(function(t) { return !t.completed; });
        state.listed = list; notify(); return list;
    }
    function preflight() { refresh(); return targets(); }
    function start(list) {
        if (state.startMode === "gps") return deps.geometry.coordinate(deps.gps());
        if (state.startMode === "map") return deps.geometry.coordinate(state.mapStart);
        if (state.startMode === "saved_default") return deps.geometry.coordinate(state.snapshot.data.settings.default_start);
        var target = list.find(function(t) { return t.site_id === state.targetStart; });
        if (!target) throw new Error("출발 조사지를 지정하세요.");
        return target.coordinate;
    }
    function refresh() {
        var route = active();
        if (!route || !state.mapping.completed) return;
        var records = deps.features(state.mapping, "all");
        route.stops.forEach(function(stop) {
            var f = stop.source_layer === state.mapping.layer && records.find(function(r) { return String(r.id) === stop.site_id; });
            if (f) stop.completed = f.completed === true;
        });
    }
    function calculate(replaceActive) {
        if (state.busy) return Promise.resolve(false);
        var list, origin, previous, baseRevision, previousCandidate = state.candidate, generation=++state.calculationGeneration;
        state.message = ""; state.lastError = null; state.lastErrorClassification=null; state.suggestedActions=[];
        try {
            previous = replaceActive ? clone(active()) : null;
            list = preflight();
            if (!list.length) throw new Error("계산할 조사지를 선택하세요.");
            origin = start(list); baseRevision = state.snapshot.revision;
            if (!state.settings.optimizer_url && state.settings.backend === "ors-vroom") throw new Error("VROOM 최적화 서버 주소를 설정하세요.");
            if (state.settings.backend === "ors-vroom" && !state.settings.key &&
                    state.settings.server_url === "https://api.heigit.org/openrouteservice" &&
                    state.settings.optimizer_url === "https://api.heigit.org/vroom/v0")
                throw new Error("HeiGIT 경로 계산에는 API 키가 필요합니다. 프로젝트 키 또는 이번 세션 키를 입력하세요.");
        } catch(e) {error(e); return Promise.resolve(false);}
        state.busy = true; notify();
        return deps.backend.calculate(state.settings, list, origin, state.roundtrip, deps.transport).then(function(result) {
            if(generation!==state.calculationGeneration)return false;
            if (!result.road_geometry) throw new Error("완전한 도로선이 제공되지 않았습니다.");
            result.road_geometry.coordinates.forEach(deps.geometry.coordinate);
            var hasEta = result.eta !== null && result.eta !== undefined;
            var hasEtaBasis = result.eta_basis !== null && result.eta_basis !== undefined;
            if (hasEta !== hasEtaBasis) throw new Error("예상 도착시간과 기준 정보가 함께 제공되지 않았습니다.");
            if (hasEta && (!Array.isArray(result.eta) || result.eta.length !== list.length || result.eta.some(function(v) {return typeof v !== "number" || !isFinite(v) || v < 0;}))) throw new Error("예상 도착시간 값이 올바르지 않습니다.");
            if (hasEta && state.settings.backend === "ors-vroom" && result.eta_basis !== "relative_seconds") throw new Error("예상 도착시간 기준이 올바르지 않습니다.");
            if (!Array.isArray(result.legs) || result.legs.length !== list.length + (state.roundtrip ? 1 : 0))
                throw new Error("완전한 도로 구간이 제공되지 않았습니다.");
            var stops = result.stops.map(function(s,i) { return Object.assign({},s,{sequence:i+1}); });
            state.candidateBaseRevision = baseRevision;
            state.candidateInputSignature = calculationInputs();
            state.candidateTargetSignature = targetInputs(list);
            var now = deps.now ? deps.now() : new Date();
            if (!(now instanceof Date)) now = new Date(now);
            state.candidate = {route_id: previous ? previous.route_id : deps.uuid(), name: localSurveyName(now), created_at: previous ? previous.created_at : now.toISOString(), backend: state.settings.backend, status: "ready", mapping: clone(state.mapping), revision: previous ? previous.revision + 1 : 1, start: origin, end: state.roundtrip ? origin : result.stops[result.stops.length-1].coordinate, roundtrip: state.roundtrip, distance_m: result.distance_m, duration_s: result.duration_s, stops: stops, road_geometry: result.road_geometry, legs: result.legs, eta: result.eta, eta_basis: result.eta ? result.eta_basis : null, optimality_guaranteed: false};
            if(result.visits){state.candidate.route_schema=3;state.candidate.vehicle_legs=clone(result.vehicle_legs);state.candidate.visits=clone(result.visits);state.candidate.vehicle_totals=clone(result.vehicle_totals);state.candidate.walking_totals=clone(result.walking_totals);state.candidate.combined_totals=clone(result.combined_totals);}
            state.candidateGeneration++;
            state.lastError = null; state.message = "계산되었습니다. 저장 전에는 기존 경로가 유지됩니다. 최적해를 보장하지 않습니다.";
            return true;
        }).catch(function(e) {state.candidate = previousCandidate;if(e&&e.cancelled!==true)error(e);return false;}).then(function(ok) {if(generation===state.calculationGeneration)state.busy=false;notify();return ok;});
    }
    function cancel(reason){
        if(!state.busy)return false;
        state.calculationGeneration++;
        if(deps.cancelTransport)deps.cancelTransport();
        state.busy=false;state.message=reason==="project-close"?"프로젝트 종료로 경로 계산을 취소했습니다.":"경로 계산을 취소했습니다.";notify();return true;
    }
    function save(name) {
        try {
            if (!state.candidate) throw new Error("먼저 경로를 계산하세요.");
            refresh();
            if (state.candidateInputSignature !== calculationInputs()) throw new Error("calculation_input 변경으로 계산 결과가 오래되었습니다. 새 경로를 계산하세요.");
            if (state.candidateTargetSignature !== targetInputs(targets())) throw new Error("calculation_input 대상이 변경되어 계산 결과가 오래되었습니다. 새 경로를 계산하세요.");
            if (state.candidateBaseRevision !== state.snapshot.revision) throw new Error("snapshot_revision 변경으로 계산 결과가 오래되었습니다. 새 경로를 계산하세요.");
            var data = clone(state.snapshot.data), candidate = clone(state.candidate);
            var persistedSettings = clone(state.settings); delete persistedSettings.key; delete persistedSettings.objective;
            persistedSettings.server_url=persistedProviderUrl(persistedSettings.server_url);
            persistedSettings.optimizer_url=persistedProviderUrl(persistedSettings.optimizer_url);
            data.settings = Object.assign(data.settings, persistedSettings);
            candidate.name = String(name === undefined ? candidate.name : (name === null ? "" : name)).trim();
            if (!candidate.name) throw new Error("저장 경로 이름을 입력하세요.");
            var index = data.routes.findIndex(function(r) {return r.route_id === candidate.route_id;});
            if (index >= 0) data.routes[index] = candidate; else data.routes.push(candidate);
            if(Array.isArray(candidate.visits)){
                var legacySchema=data.schema;
                data.routes.forEach(function(route){
                    if(route.route_schema===undefined)route.route_schema=Array.isArray(route.visits)?3:(Array.isArray(route.legs)?legacySchema:1);
                });
                data.schema=3;
            } else data.schema = data.routes.every(function(r) {return Array.isArray(r.legs);}) ? 2 : 1;
            data.active_id = candidate.route_id; var path=commit(data); state.candidate = null;
            state.message="‘"+candidate.name+"’ 경로를 저장했습니다: "+path; notify(); return true;
        } catch(e) {error(e); return false;}
    }
    function select(id) { try { var data=clone(state.snapshot.data); if (!data.routes.some(function(r){return r.route_id===id;})) throw new Error("저장 경로를 찾지 못했습니다."); data.active_id=id;commit(data);state.candidate=null;if(active().mapping)state.mapping=clone(active().mapping); refresh(); notify(); return true;} catch(e){error(e);return false;} }
    function complete(id, value) {
        try {
            refresh();
            var current=active();
            if(!current) throw new Error("활성 경로가 없습니다.");
            var currentStop=current.stops.find(function(s){return s.site_id===id;});
            if(!currentStop) throw new Error("대상을 찾지 못했습니다.");
            var nextStop=current.stops.filter(function(s){return !s.completed;}).sort(function(a,b){return a.sequence-b.sequence;})[0]||null;
            if(value===true && !currentStop.completed && (!nextStop || nextStop.site_id!==id)) {
                state.message="다음 방문 지점부터 순서대로 완료하세요. 다음 지점: "+(nextStop ? nextStop.sequence+". "+nextStop.name : "없음");notify();return false;
            }
            if(state.mapping.completed) { deps.setCompleted(state.mapping,id,value); refresh(); notify(); }
            else {var data=clone(state.snapshot.data), route=data.routes.find(function(r){return r.route_id===data.active_id;}); if(!route) throw new Error("활성 경로가 없습니다."); var stop=route.stops.find(function(s){return s.site_id===id;}); if(!stop) throw new Error("대상을 찾지 못했습니다.");stop.completed=value===true;commit(data);}
            return true;
        } catch(e){error(e);return false;}
    }
    function saveDefault(point) {try{var data=clone(state.snapshot.data),p=deps.geometry.coordinate(point);data.schema=Math.max(2,data.schema);data.settings.default_start=p;tagMixedRoutes(data);var path=commit(data);state.message="기본 출발지 "+p[0]+", "+p[1]+" 저장: "+path;notify();return true;}catch(e){error(e);return false;}}
    function saveSettings() {try{var data=clone(state.snapshot.data), s=clone(state.settings);delete s.key;delete s.objective;s.server_url=persistedProviderUrl(s.server_url);s.optimizer_url=persistedProviderUrl(s.optimizer_url);s.mapping=clone(state.mapping);s.show_route_line=state.showRouteLine;data.schema=Math.max(2,data.schema);tagMixedRoutes(data);data.settings=Object.assign(data.settings,s);var route=data.routes.find(function(r){return r.route_id===data.active_id;});if(route && route.mapping && route.mapping.layer===state.mapping.layer && JSON.stringify(route.mapping)!==JSON.stringify(state.mapping)){route.mapping=clone(state.mapping);route.revision++;}var path=commit(data);state.message="현재 프로젝트 서버 설정 저장: "+path+" · 키 제외";notify();return path;}catch(e){error(e);return false;}}
    function tagMixedRoutes(data) {
        if(data.schema===3)data.routes.forEach(function(route){if(route.route_schema===undefined)route.route_schema=Array.isArray(route.visits)?3:2;});
    }
    function toggleRouteLine(value) {
        var previous=state.showRouteLine, requested=value!==false;
        try {var data=clone(state.snapshot.data);data.settings.show_route_line=requested;tagMixedRoutes(data);commit(data);if(state.candidate)state.candidateBaseRevision=state.snapshot.revision;state.showRouteLine=requested;notify();return true;}
        catch(e){state.showRouteLine=previous;error(e);return false;}
    }
    function progress(route) {
        route=route||active();
        if(!route)return {available:true,prefix_length:0,remaining_distance_m:0,remaining_duration_s:0,remaining_geometry:null,remaining_leg_sequences:[],visit_context_ids:[]};
        if(!Array.isArray(route.legs))return {available:false,message:"향상된 남은 경로를 보려면 새 전체 경로를 계산하고 저장하세요."};
        var prefix=0;while(prefix<route.stops.length&&route.stops[prefix].completed===true)prefix++;
        var remaining=(route.vehicle_legs||route.legs).slice(prefix),coordinates=[];
        remaining.forEach(function(leg){leg.geometry.coordinates.forEach(function(point,i){if(!coordinates.length||i||JSON.stringify(coordinates[coordinates.length-1])!==JSON.stringify(point))coordinates.push(point);});});
        var visits=(route.visits||[]).slice(prefix),mapped=0,lower=0,walkingDuration=0,unavailable=0;
        visits.forEach(function(visit){visit.walking_legs.forEach(function(leg){if(visit.walking_mode==="unmapped_estimate")lower+=leg.distance_m;else mapped+=leg.distance_m;if(leg.duration_s===null)unavailable++;else walkingDuration+=leg.duration_s;});});
        return {available:true,prefix_length:prefix,remaining_leg_sequences:remaining.map(function(leg){return leg.sequence;}),remaining_distance_m:remaining.reduce(function(sum,leg){return sum+leg.distance_m;},0),remaining_duration_s:remaining.reduce(function(sum,leg){return sum+leg.duration_s;},0),remaining_geometry:coordinates.length>1?{type:"LineString",coordinates:coordinates}:null,visit_context_ids:route.stops.slice(prefix).map(function(stop){return stop.site_id;}),walking_visit_count:visits.length,remaining_walking:{mapped_distance_m:mapped,lower_bound_distance_m:lower,mapped_duration_s:walkingDuration,duration_s:unavailable?null:walkingDuration,unavailable_duration_count:unavailable},remaining_note:prefix===route.stops.length&&route.roundtrip&&remaining.length?"복귀 포함":""};
    }
    function navigate(stop) {try{var result=deps.navigation.open(stop,deps.openUrl,deps.platform?deps.platform():"",deps.callerId?deps.callerId():"");state.message=result&&result.message?result.message:"지도 앱에 길안내를 요청했습니다. 앱 실행·목적지 수락·안내 시작 여부는 확인할 수 없습니다.";notify();return true;}catch(e){error(e);return false;}}
    reload();
    return {state: state, active: active, reload: reload, configure: settings, targets: targets, preflight: preflight, calculate: calculate, cancel:cancel, save: save, select: select, complete: complete, refresh: refresh, saveDefault: saveDefault, saveSettings: saveSettings, toggleRouteLine: toggleRouteLine, progress: progress, navigate: navigate,
        // Compatibility for older generated test/project callers; fallback is no longer gated state.
        acknowledgeUnmapped:function(){}, next: function(){var r=active();return r ? r.stops.filter(function(s){return !s.completed;}).sort(function(a,b){return a.sequence-b.sequence;})[0] || null : null;}, error:error};
}
