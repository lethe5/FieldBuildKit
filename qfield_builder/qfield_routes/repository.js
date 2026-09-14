// Portable two-slot snapshots. Never overwrite the newest validated snapshot.
// FileUtils uses QFile (not QSaveFile); a torn write therefore needs a second slot.
function empty() { return {schema: 1, active_id: "", routes: [], settings: {}}; }
function checksum(text) {
    var hash = 2166136261;
    for (var i = 0; i < text.length; ++i) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16);
}
function validate(data) {
    if (!data || data.schema !== 1 || !Array.isArray(data.routes) ||
        typeof data.active_id !== "string" || !data.settings || typeof data.settings !== "object")
        throw new Error("저장된 경로 형식이 올바르지 않습니다.");
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
                typeof s.completed !== "boolean" || !Array.isArray(s.coordinate))
                throw new Error("저장된 방문 목록이 손상되었습니다.");
            stops[s.site_id] = true;
        });
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
        return {revision: envelope.revision, data: validate(JSON.parse(envelope.payload))};
    } catch (error) { return null; }
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
