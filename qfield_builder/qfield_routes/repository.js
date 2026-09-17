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
function validate(data) {
    if (!data || !Number.isInteger(data.schema) || data.schema < 1 || data.schema > 2)
        throw new Error(data && data.schema > 2 ?
            "이 프로젝트의 저장 경로는 더 최신 형식입니다. 파일을 보존하고 FieldBuild Kit를 업데이트하세요." :
            "저장된 경로 형식이 올바르지 않습니다.");
    var activeId = data.active_id === undefined ? data.active_route_id : data.active_id;
    if (!Array.isArray(data.routes) || typeof activeId !== "string" ||
        (data.settings !== undefined && (!data.settings || typeof data.settings !== "object")))
        throw new Error("저장된 경로 형식이 올바르지 않습니다.");
    if (data.active_id === undefined) data.active_id = activeId;
    if (!data.settings) data.settings = {};
    var ids = {};
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
        } else if (data.schema === 2) {
            throw new Error("저장된 전체 경로 구간이 손상되었습니다.");
        }
    });
    if (data.active_id && !ids[data.active_id]) throw new Error("활성 경로가 없습니다.");
    return data;
}
function readSlot(io, path) {
    if (!io.exists(path)) return null;
    try {
        var envelope = JSON.parse(String(io.read(path)));
        if (!Number.isInteger(envelope.revision) || envelope.revision < 1 ||
            typeof envelope.payload !== "string" || checksum(envelope.payload) !== envelope.checksum)
            return null;
        var parsed = JSON.parse(envelope.payload);
        if (parsed && Number.isInteger(parsed.schema) && parsed.schema > 2)
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
            throw new Error("저장 경로의 두 사본을 읽지 못했습니다. 파일을 보존하고 백업을 확인해 주세요.");
        return {data: empty(), revision: 0, slot: ""};
    }
    var useA = a && (!b || a.revision >= b.revision);
    var latest = useA ? a : b;
    return {data: latest.data, revision: latest.revision, slot: useA ? "a" : "b",
        recovered: (io.exists(base + ".a.json") && !a) || (io.exists(base + ".b.json") && !b)};
}
function save(io, base, data, expectedRevision) {
    validate(data);
    var latest = load(io, base);
    if (expectedRevision !== undefined && latest.revision !== expectedRevision)
        throw new Error("다른 창에서 저장한 변경이 있습니다. 경로를 다시 불러와 주세요.");
    var payload = JSON.stringify(data), revision = latest.revision + 1;
    var slot = latest.slot === "a" ? "b" : "a", path = base + "." + slot + ".json";
    var text = JSON.stringify({revision: revision, checksum: checksum(payload), payload: payload});
    if (io.write(path, text) !== true) throw new Error("경로 저장 실패: 이전 저장본은 보존됩니다.");
    var readback = readSlot(io, path);
    if (!readback || readback.revision !== revision || JSON.stringify(readback.data) !== payload)
        throw new Error("경로 저장 확인 실패: 이전 저장본은 보존됩니다.");
    return {data: data, revision: revision, slot: slot};
}
