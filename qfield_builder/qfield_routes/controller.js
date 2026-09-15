// Production controller; external QField objects, transport and files are injected at the boundary.
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function create(deps) {
    var state = {message: "", busy: false, expanded: false, listed: [], candidate: null, snapshot: null,
        mapping: {layer: "site", id: "site_id", name: "site_name", completed: ""}, scope: "selected", startMode: "gps", mapStart: null, targetStart: "", roundtrip: true,
        settings: {server_url: "https://api.heigit.org/openrouteservice", optimizer_url: "https://api.heigit.org/vroom/v0", backend: "ors-vroom", profile: "driving-car", key: "", timeout_ms: 30000, max_road_offset_m: 1000, objective: "time"}};
    function notify() { if (deps.changed) deps.changed(); }
    function error(e) { state.message = String(e.message || e).split(state.settings.key || "\u0000").join("[숨김]"); notify(); }
    function active() { return state.snapshot.data.routes.find(function(r) { return r.route_id === state.snapshot.data.active_id; }) || null; }
    function commit(data) { state.snapshot = deps.repository.save(deps.io, deps.base, data, state.snapshot.revision); notify(); }
    function reload() {
        try {
            state.snapshot = deps.repository.load(deps.io, deps.base);
            Object.assign(state.settings, state.snapshot.data.settings);
            state.settings.server_url = String(state.settings.server_url || "").replace(/\/+$/, "");
            state.settings.optimizer_url = String(state.settings.optimizer_url || "").replace(/\/+$/, "");
            if (state.settings.server_url === "https://api.openrouteservice.org") state.settings.server_url = "https://api.heigit.org/openrouteservice";
            if (!state.settings.optimizer_url || state.settings.optimizer_url === "https://api.openrouteservice.org/optimization") state.settings.optimizer_url = "https://api.heigit.org/vroom/v0";
            state.settings.key = deps.projectKey ? String(deps.projectKey() || "").trim() : "";
            if(state.snapshot.data.settings.mapping) state.mapping=clone(state.snapshot.data.settings.mapping); if(active() && active().mapping) state.mapping=clone(active().mapping); state.message = state.snapshot.recovered ? "손상된 저장본을 발견하여 정상 사본을 불러왔습니다." : ""; notify();
        }
        catch(e) { error(e); throw e; }
    }
    function settings(values) {
        var merged = Object.assign({}, state.settings, values);
        merged.server_url = String(merged.server_url || "").replace(/\/+$/, "");
        merged.optimizer_url = String(merged.optimizer_url || "").replace(/\/+$/, "");
        if (merged.server_url === "https://api.openrouteservice.org") merged.server_url = "https://api.heigit.org/openrouteservice";
        if (!merged.optimizer_url || merged.optimizer_url === "https://api.openrouteservice.org/optimization") merged.optimizer_url = "https://api.heigit.org/vroom/v0";
        if (!/^https?:\/\//.test(merged.server_url) || !/^https?:\/\//.test(merged.optimizer_url) || !Number.isInteger(merged.timeout_ms) || merged.timeout_ms <= 0 || !isFinite(merged.max_road_offset_m) || merged.max_road_offset_m < 0) throw new Error("서버 주소, 제한시간, 도로 이격거리를 확인하세요.");
        state.settings = merged; notify();
    }
    function targets() {
        if (![state.mapping.layer, state.mapping.id, state.mapping.name].every(function(v) { return typeof v === "string" && v.trim(); }))
            throw new Error("대상 레이어, ID 필드, 이름 필드를 모두 명시하세요.");
        var records = deps.features(state.mapping, state.scope), seen = Object.create(null);
        var list = records.map(function(record) {
            var id = record.id;
            if (id === null || id === undefined || !String(id).trim() || seen[String(id)]) throw new Error("조사대상 ID가 비어 있거나 중복되었습니다.");
            id = String(id); seen[id] = true;
            return {site_id: id, source_layer: state.mapping.layer, name: String(record.name || id), coordinate: deps.geometry.coordinate(record.coordinate), completed: record.completed === true};
        });
        if (!state.mapping.completed && active()) list.forEach(function(t) {var saved=active().stops.find(function(s){return s.site_id===t.site_id && s.source_layer===t.source_layer;});if(saved)t.completed=saved.completed;});
        if (state.scope === "uncompleted") list = list.filter(function(t) { return !t.completed; });
        state.listed = list; notify(); return list;
    }
    function start(list, remaining) {
        if (remaining || state.startMode === "gps") return deps.geometry.coordinate(deps.gps());
        if (state.startMode === "map") return deps.geometry.coordinate(state.mapStart);
        if (state.startMode === "saved_default") return deps.geometry.coordinate(state.snapshot.data.settings.default_start);
        var target = list.find(function(t) { return t.site_id === state.targetStart; });
        if (!target) throw new Error("출발 조사대상을 지정하세요.");
        return target.coordinate;
    }
    function refresh() {
        var route = active();
        if (!route || !state.mapping.completed) return;
        var records = deps.features(state.mapping, "all"), data = clone(state.snapshot.data), changed = false;
        var updated = data.routes.find(function(r) { return r.route_id === route.route_id; });
        updated.stops.forEach(function(stop) {
            var f = stop.source_layer === state.mapping.layer && records.find(function(r) { return String(r.id) === stop.site_id; });
            if (f && (f.completed === true) !== stop.completed) { stop.completed = f.completed === true; changed = true; }
        });
        if (changed) { updated.revision++; commit(data); }
    }
    function calculate(remaining) {
        if (state.busy) return Promise.resolve(false);
        state.candidate = null; state.message = "";
        var list, origin, previous, baseRevision;
        try {
            refresh(); previous = remaining ? clone(active()) : null;
            list = remaining ? (previous ? previous.stops.filter(function(s) {return !s.completed;}) : []) : targets();
            if (!list.length) throw new Error(remaining ? "남은 조사대상이 없습니다." : "계산할 조사대상을 선택하세요.");
            origin = start(list, remaining); baseRevision = state.snapshot.revision;
            if (!state.settings.optimizer_url && state.settings.backend === "ors-vroom") throw new Error("VROOM 최적화 서버 주소를 설정하세요.");
            if (state.settings.backend === "ors-vroom" && !state.settings.key &&
                    state.settings.server_url === "https://api.heigit.org/openrouteservice" &&
                    state.settings.optimizer_url === "https://api.heigit.org/vroom/v0")
                throw new Error("HeiGIT 경로 계산에는 API 키가 필요합니다. 프로젝트 키 또는 이번 세션 키를 입력하세요.");
        } catch(e) {error(e); return Promise.resolve(false);}
        state.busy = true; notify();
        return deps.backend.calculate(state.settings, list, origin, state.roundtrip, deps.transport).then(function(result) {
            if (result.road_geometry) result.road_geometry.coordinates.forEach(deps.geometry.coordinate);
            var hasEta = result.eta !== null && result.eta !== undefined;
            var hasEtaBasis = result.eta_basis !== null && result.eta_basis !== undefined;
            if (hasEta !== hasEtaBasis) throw new Error("예상 도착시간과 기준 정보가 함께 제공되지 않았습니다.");
            if (hasEta && (!Array.isArray(result.eta) || result.eta.length !== list.length || result.eta.some(function(v) {return typeof v !== "number" || !isFinite(v) || v < 0;}))) throw new Error("예상 도착시간 값이 올바르지 않습니다.");
            if (hasEta && state.settings.backend === "ors-vroom" && result.eta_basis !== "relative_seconds") throw new Error("예상 도착시간 기준이 올바르지 않습니다.");
            var stops = result.stops.map(function(s,i) { return Object.assign({},s,{sequence:i+1}); });
            if (previous) {
                var done = previous.stops.filter(function(s) { return s.completed; }), reserved = {};
                done.forEach(function(s) { reserved[s.sequence] = true; });
                var seq = 1; stops.forEach(function(s) {while(reserved[seq]) seq++; s.sequence = seq++;});
                stops = done.concat(stops).sort(function(a,b){return a.sequence-b.sequence;});
            }
            state.candidateBaseRevision = baseRevision;
            var etaMatchesStoredStops = !previous || !previous.stops.some(function(s) {return s.completed;});
            state.candidate = {route_id: previous ? previous.route_id : deps.uuid(), name: previous ? previous.name : "새 조사 경로", created_at: previous ? previous.created_at : new Date().toISOString(), backend: state.settings.backend, status: "ready", mapping: clone(state.mapping), revision: previous ? previous.revision + 1 : 1, start: origin, end: state.roundtrip ? origin : result.stops[result.stops.length-1].coordinate, distance_m: result.distance_m, duration_s: result.duration_s, stops: stops, road_geometry: result.road_geometry, legs: result.legs, eta: etaMatchesStoredStops ? result.eta : null, eta_basis: etaMatchesStoredStops && result.eta ? result.eta_basis : null, optimality_guaranteed: false};
            state.message = "계산되었습니다. 저장 전에는 기존 경로가 유지됩니다. 최적해를 보장하지 않습니다.";
            return true;
        }).catch(function(e) {state.candidate = null; error(e); return false;}).then(function(ok) {state.busy = false; notify(); return ok;});
    }
    function save(name) {
        try {
            if (!state.candidate) throw new Error("먼저 경로를 계산하세요.");
            refresh();
            if (state.candidateBaseRevision !== state.snapshot.revision) throw new Error("저장 이후 상태가 변경되었습니다. 경로를 다시 계산하세요.");
            var data = clone(state.snapshot.data), candidate = clone(state.candidate);
            candidate.name = String(name || candidate.name).trim();
            var index = data.routes.findIndex(function(r) {return r.route_id === candidate.route_id;});
            if (index >= 0) data.routes[index] = candidate; else data.routes.push(candidate);
            data.active_id = candidate.route_id; commit(data); state.candidate = null; notify(); return true;
        } catch(e) {error(e); return false;}
    }
    function select(id) { try { var data=clone(state.snapshot.data); if (!data.routes.some(function(r){return r.route_id===id;})) throw new Error("저장 경로를 찾지 못했습니다."); data.active_id=id;commit(data);if(active().mapping)state.mapping=clone(active().mapping); refresh(); notify(); return true;} catch(e){error(e);return false;} }
    function complete(id, value) {
        try {
            if(state.mapping.completed) { deps.setCompleted(state.mapping,id,value); refresh(); }
            else {var data=clone(state.snapshot.data), route=data.routes.find(function(r){return r.route_id===data.active_id;}); if(!route) throw new Error("활성 경로가 없습니다."); var stop=route.stops.find(function(s){return s.site_id===id;}); if(!stop) throw new Error("대상을 찾지 못했습니다.");stop.completed=value===true;route.revision++;commit(data);}
            return true;
        } catch(e){error(e);return false;}
    }
    function saveDefault(point) {var data=clone(state.snapshot.data); data.settings.default_start=deps.geometry.coordinate(point);commit(data);}
    function saveSettings() {var data=clone(state.snapshot.data), s=clone(state.settings);delete s.key;delete s.objective;s.mapping=clone(state.mapping);data.settings=Object.assign(data.settings,s);var route=data.routes.find(function(r){return r.route_id===data.active_id;});if(route && route.mapping && route.mapping.layer===state.mapping.layer && JSON.stringify(route.mapping)!==JSON.stringify(state.mapping)){route.mapping=clone(state.mapping);route.revision++;}commit(data);}
    function navigate(stop) {try {deps.navigation.open(stop,deps.openUrl);state.message="네이버지도에 실행을 요청했습니다. 앱 내부의 목적지 수락 여부는 확인할 수 없습니다.";notify();return true;}catch(e){error(e);return false;}}
    reload();
    return {state: state, active: active, reload: reload, configure: settings, targets: targets, calculate: calculate, save: save, select: select, complete: complete, refresh: refresh, saveDefault: saveDefault, saveSettings: saveSettings, navigate: navigate,
        next: function(){var r=active();return r ? r.stops.filter(function(s){return !s.completed;}).sort(function(a,b){return a.sequence-b.sequence;})[0] || null : null;}, error:error};
}
