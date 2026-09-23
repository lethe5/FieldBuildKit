// Portable two-slot snapshots. Never overwrite the newest validated snapshot.
// FileUtils uses QFile (not QSaveFile); a torn write therefore needs a second slot.
function empty() { return {schema: 2, active_id: "", routes: [], settings: {show_route_line: true}}; }
function checksum(text) {
    var hash = 2166136261;
    for (var i = 0; i < text.length; ++i) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16);
}
function number(value) { return typeof value === "number" && isFinite(value) && value >= 0; }
function coordinate(value) {
    return Array.isArray(value) && value.length >= 2 &&
        typeof value[0] === "number" && isFinite(value[0]) && value[0] >= -180 && value[0] <= 180 &&
        typeof value[1] === "number" && isFinite(value[1]) && value[1] >= -90 && value[1] <= 90;
}
function line(value) {
    return value && value.type === "LineString" && Array.isArray(value.coordinates) &&
        value.coordinates.length >= 2 && value.coordinates.every(coordinate);
}
function endpoint(value) {
    return value === "start" || (value && typeof value.layer_id === "string" && value.layer_id &&
        typeof value.site_id === "string" && value.site_id);
}
function nonblank(value) { return typeof value === "string" && value.trim().length > 0; }
function sameCoordinate(a, b) { return coordinate(a) && coordinate(b) && a[0] === b[0] && a[1] === b[1]; }
function reverseCoordinates(a, b) {
    return a.length === b.length && a.every(function(point, i) {
        var other = b[b.length - i - 1];
        return sameCoordinate(point, other);
    });
}
function haversine(a, b) {
    var rad=Math.PI/180, dlat=(b[1]-a[1])*rad, dlon=(b[0]-a[0])*rad;
    var h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(a[1]*rad)*Math.cos(b[1]*rad)*Math.sin(dlon/2)*Math.sin(dlon/2);
    return 6371008.8*2*Math.asin(Math.sqrt(h));
}
function near(a, b) { return Math.abs(a-b) <= 0.01; }
function validate(data) {
    if (!data || !Number.isInteger(data.schema) || data.schema < 1 || data.schema > 3)
        throw new Error(data && data.schema > 3 ?
            "이 프로젝트의 저장 경로는 더 최신 형식입니다. 파일을 보존하고 FieldBuild Kit를 업데이트하세요." :
            "저장된 경로 형식이 올바르지 않습니다.");
    var activeId = data.active_id === undefined ? data.active_route_id : data.active_id;
    if (!Array.isArray(data.routes) || typeof activeId !== "string" ||
        (data.settings !== undefined && (!data.settings || typeof data.settings !== "object")))
        throw new Error("저장된 경로 형식이 올바르지 않습니다.");
    if (data.active_id === undefined) data.active_id = activeId;
    if (!data.settings) data.settings = {};
    var ids = {};
    var untaggedMixed = data.schema === 3 && data.routes.length && data.routes.every(function(route) {
        return route && route.route_schema === undefined && Array.isArray(route.visits);
    });
    data.routes.forEach(function(route) {
        if (!route || typeof route.route_id !== "string" || !route.route_id ||
            ids[route.route_id] || !Array.isArray(route.stops) || !route.stops.length ||
            typeof route.name !== "string" || !Number.isInteger(route.revision) || route.revision < 1)
            throw new Error("저장된 경로가 손상되었습니다.");
        ids[route.route_id] = true;
        var hasEta = route.eta !== null && route.eta !== undefined;
        var hasEtaBasis = route.eta_basis !== null && route.eta_basis !== undefined;
        if (hasEta !== hasEtaBasis || (hasEta && (route.eta_basis !== "relative_seconds" ||
            !Array.isArray(route.eta) || route.eta.length !== route.stops.length ||
            route.eta.some(function(v) { return typeof v !== "number" || !isFinite(v) || v < 0; }))))
            throw new Error("저장된 예상 도착시간이 손상되었습니다.");
        var stops = {};
        route.stops.forEach(function(s, i) {
            if (!s.site_id || stops[s.site_id] || s.sequence !== i + 1 ||
                typeof s.completed !== "boolean" || (s.coordinate !== undefined && !coordinate(s.coordinate)))
                throw new Error("저장된 방문 목록이 손상되었습니다.");
            stops[s.site_id] = true;
        });
        var mixedFields = ["vehicle_legs","visits","vehicle_totals","walking_totals","combined_totals"];
        var hasMixed = mixedFields.some(function(field){return Object.prototype.hasOwnProperty.call(route,field);});
        var variant = route.route_schema === undefined ? (untaggedMixed ? 3 :
            (data.schema === 2 && !Array.isArray(route.legs) ? 1 : data.schema)) : route.route_schema;
        if (![1,2,3].includes(variant) || (variant === 1 && Array.isArray(route.legs)) ||
            (variant === 3 && !hasMixed) || (variant !== 3 && hasMixed) ||
            (data.schema < 3 && route.route_schema !== undefined))
            throw new Error("저장된 경로 버전 표식이 손상되었습니다.");
        if (Array.isArray(route.legs)) {
            var roundtrip = route.end && route.start && JSON.stringify(route.end) === JSON.stringify(route.start);
            var expected = route.stops.length + (roundtrip ? 1 : 0);
            if (!Array.isArray(route.legs) || route.legs.length !== expected ||
                !number(route.distance_m) || !number(route.duration_s) || !line(route.road_geometry))
                throw new Error("저장된 전체 경로 구간이 손상되었습니다.");
            var distance = 0, duration = 0;
            route.legs.forEach(function(leg, i) {
                var expectedFrom = i === 0 ? "start" : {layer_id: route.stops[i - 1].source_layer, site_id: route.stops[i - 1].site_id};
                var expectedTo = i < route.stops.length ? {layer_id: route.stops[i].source_layer, site_id: route.stops[i].site_id} : "start";
                if (!leg || leg.sequence !== i + 1 || !endpoint(leg.from) || !endpoint(leg.to) ||
                    JSON.stringify(leg.from) !== JSON.stringify(expectedFrom) ||
                    JSON.stringify(leg.to) !== JSON.stringify(expectedTo) ||
                    !number(leg.distance_m) || !number(leg.duration_s) || !line(leg.geometry))
                    throw new Error("저장된 전체 경로 구간이 손상되었습니다.");
                distance += leg.distance_m; duration += leg.duration_s;
            });
            if (Math.abs(distance - route.distance_m) > 1e-6 || Math.abs(duration - route.duration_s) > 1e-6)
                throw new Error("저장된 전체 경로 합계가 손상되었습니다.");
        } else if (variant >= 2) {
            throw new Error("저장된 전체 경로 구간이 손상되었습니다.");
        }
        if (variant === 3) {
            ["vehicle_legs","visits","vehicle_totals","walking_totals","combined_totals"].forEach(function(field){
                if(!Object.prototype.hasOwnProperty.call(route,field)){
                    var missing=new Error("schema 3 경로 필수 필드가 누락되었습니다: "+field);missing.schema3_required_field=field;throw missing;
                }
            });
            if (!Array.isArray(route.vehicle_legs) || !Array.isArray(route.visits) || route.visits.length!==route.stops.length ||
                JSON.stringify(route.vehicle_legs)!==JSON.stringify(route.legs) ||
                !route.vehicle_totals || !number(route.vehicle_totals.distance_m) || !number(route.vehicle_totals.duration_s) ||
                !route.walking_totals || !number(route.walking_totals.mapped_distance_m) || !number(route.walking_totals.lower_bound_distance_m) ||
                !Number.isInteger(route.walking_totals.unavailable_duration_count) || route.walking_totals.unavailable_duration_count<0 ||
                (route.walking_totals.duration_s!==null&&!number(route.walking_totals.duration_s))) throw new Error("저장된 혼합 경로가 손상되었습니다.");
            if (route.vehicle_totals.distance_m!==route.distance_m || route.vehicle_totals.duration_s!==route.duration_s)
                throw new Error("저장된 차량 경로 합계가 손상되었습니다.");
            var mappedDistance=0,lowerDistance=0,walkingDuration=0,unavailableCount=0;
            route.visits.forEach(function(visit,i){
                var stop=route.stops[i], pair=visit&&visit.walking_mode+"|"+visit.metric_source;
                if(!visit||!nonblank(stop.source_layer)||!nonblank(stop.site_id)||!nonblank(visit.layer_id)||!nonblank(visit.site_id)||!nonblank(visit.metric_source)||
                    visit.layer_id!==stop.source_layer||visit.site_id!==stop.site_id||
                    (route.mapping&&nonblank(route.mapping.layer)&&visit.layer_id!==route.mapping.layer)||
                    !coordinate(visit.source_coordinate)||!sameCoordinate(visit.source_coordinate,stop.coordinate)||!coordinate(visit.access_coordinate)||
                    !number(visit.access_offset_m)||!["mapped|ors-foot-hiking","exact_zero|exact_zero","unmapped_estimate|straight_line_lower_bound_m"].includes(pair)||visit.trip_multiplier!==2||
                    !Array.isArray(visit.walking_legs)||visit.walking_legs.length!==2)throw new Error("저장된 도보 방문이 손상되었습니다.");
                visit.walking_legs.forEach(function(leg,j){if(!leg||leg.direction!==(j?"return":"outbound")||!number(leg.distance_m)||
                    (leg.duration_s!==null&&!number(leg.duration_s))||(leg.geometry!==null&&!line(leg.geometry)))throw new Error("저장된 도보 구간이 손상되었습니다.");});
                var outbound=visit.walking_legs[0], inbound=visit.walking_legs[1], lowerBound=haversine(visit.source_coordinate,visit.access_coordinate);
                if(outbound.distance_m!==inbound.distance_m||outbound.duration_s!==inbound.duration_s)
                    throw new Error("저장된 도보 왕복 구간이 손상되었습니다.");
                if(visit.walking_mode==="exact_zero") {
                    if(lowerBound>1||!near(visit.access_offset_m,lowerBound)||outbound.distance_m!==0||outbound.duration_s!==0||outbound.geometry!==null||inbound.geometry!==null)
                        throw new Error("저장된 도보 0거리 구간이 손상되었습니다.");
                } else if(visit.walking_mode==="mapped") {
                    if(lowerBound<=1||!near(visit.access_offset_m,lowerBound)||outbound.duration_s===null||!line(outbound.geometry)||!line(inbound.geometry)||
                        !reverseCoordinates(outbound.geometry.coordinates,inbound.geometry.coordinates))
                        throw new Error("저장된 지도 도보 구간이 손상되었습니다.");
                } else if(lowerBound<=1||!near(visit.access_offset_m,lowerBound)||!near(outbound.distance_m,lowerBound)||outbound.duration_s!==null||!line(outbound.geometry)||!line(inbound.geometry)||
                    !sameCoordinate(outbound.geometry.coordinates[0],visit.access_coordinate)||
                    !sameCoordinate(outbound.geometry.coordinates[outbound.geometry.coordinates.length-1],visit.source_coordinate)||
                    !reverseCoordinates(outbound.geometry.coordinates,inbound.geometry.coordinates)) {
                    throw new Error("저장된 직선거리 하한 구간이 손상되었습니다.");
                }
                visit.walking_legs.forEach(function(leg){
                    if(visit.walking_mode==="unmapped_estimate")lowerDistance+=leg.distance_m;else mappedDistance+=leg.distance_m;
                    if(leg.duration_s===null)unavailableCount++;else walkingDuration+=leg.duration_s;
                });
            });
            if(route.walking_totals.mapped_distance_m!==mappedDistance||route.walking_totals.lower_bound_distance_m!==lowerDistance||
                route.walking_totals.unavailable_duration_count!==unavailableCount||
                route.walking_totals.duration_s!==(unavailableCount?null:walkingDuration))throw new Error("저장된 도보 경로 합계가 손상되었습니다.");
            if(route.walking_totals.unavailable_duration_count?(route.combined_totals!==null||route.walking_totals.duration_s!==null):
                (!route.combined_totals||!number(route.combined_totals.distance_m)||!number(route.combined_totals.duration_s)||
                 Math.abs(route.combined_totals.distance_m-(route.vehicle_totals.distance_m+route.walking_totals.mapped_distance_m))>1e-6||
                 Math.abs(route.combined_totals.duration_s-(route.vehicle_totals.duration_s+route.walking_totals.duration_s))>1e-6))throw new Error("저장된 혼합 경로 합계가 손상되었습니다.");
        }
    });
    if (data.active_id && !ids[data.active_id]) throw new Error("활성 경로가 없습니다.");
    return data;
}
function readSlot(io, path) {
    if (!io.exists(path)) return null;
    var parsed = null;
    try {
        var envelope = JSON.parse(String(io.read(path)));
        if (!Number.isInteger(envelope.revision) || envelope.revision < 1 ||
            typeof envelope.payload !== "string" || checksum(envelope.payload) !== envelope.checksum)
            return null;
        parsed = JSON.parse(envelope.payload);
        if (parsed && Number.isInteger(parsed.schema) && parsed.schema > 3)
            throw new Error("이 프로젝트의 저장 경로는 더 최신 형식입니다. 파일을 보존하고 FieldBuild Kit를 업데이트하세요.");
        return {revision: envelope.revision, data: validate(parsed)};
    } catch (error) {
        if (String(error && error.message || error).indexOf("더 최신 형식") >= 0) throw error;
        return null;
    }
}
function load(io, base) {
    var a = readSlot(io, base + ".a.json"), b = readSlot(io, base + ".b.json");
    if (!a && !b) {
        if (io.exists(base + ".a.json") || io.exists(base + ".b.json"))
            throw new Error("저장 경로의 두 사본이 손상되어 읽지 못했습니다. 파일을 보존하고 백업을 확인해 주세요.");
        return {data: empty(), revision: 0, slot: ""};
    }
    var useA = a && (!b || a.revision >= b.revision);
    var latest = useA ? a : b;
    return {data: latest.data, revision: latest.revision, slot: useA ? "a" : "b",
        recovered: (io.exists(base + ".a.json") && !a) || (io.exists(base + ".b.json") && !b)};
}
function recoverLastGood(io, base, rejectedSlot) {
    if (rejectedSlot !== "a" && rejectedSlot !== "b") throw new Error("복구할 저장본을 지정하세요.");
    var slot = rejectedSlot === "a" ? "b" : "a", snapshot = readSlot(io, base + "." + slot + ".json");
    if (!snapshot) throw new Error("이전 정상 저장본을 읽지 못했습니다. 손상된 파일은 보존됩니다.");
    return {data:snapshot.data,revision:snapshot.revision,slot:slot,recovered:true};
}
function save(io, base, data, expectedRevision) {
    validate(data);
    var latest = load(io, base);
    if (expectedRevision !== undefined && latest.revision !== expectedRevision)
        throw new Error("다른 창에서 저장한 변경이 있습니다. 경로를 다시 불러와 주세요.");
    var payload = JSON.stringify(data), revision = latest.revision + 1;
    var slot = latest.slot === "a" ? "b" : "a", path = base + "." + slot + ".json";
    var text = JSON.stringify({revision: revision, checksum: checksum(payload), payload: payload});
    var previousText = io.exists(path) ? String(io.read(path)) : null;
    if (io.write(path, text) !== true) {
        var currentText = io.exists(path) ? String(io.read(path)) : null;
        throw new Error(currentText !== previousText ?
            "경로 저장 확인 실패: 이전 저장본은 보존됩니다." :
            "경로 저장 실패: 이전 저장본은 보존됩니다.");
    }
    var readback = readSlot(io, path);
    if (!readback || readback.revision !== revision || JSON.stringify(readback.data) !== payload)
        throw new Error("경로 저장 확인 실패: 이전 저장본은 보존됩니다.");
    return {data: data, revision: revision, slot: slot};
}
