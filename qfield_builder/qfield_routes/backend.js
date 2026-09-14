// ORS v2 matrix/directions and VROOM v1.14 custom matrices. No straight-line fallback.
function number(value, label) {
    if (typeof value !== "number" || !isFinite(value) || value < 0) throw new Error(label + " 값이 올바르지 않습니다.");
    return value;
}
function matrix(value, n) {
    if (!Array.isArray(value) || value.length !== n) throw new Error("도로 행렬이 누락되었습니다.");
    return value.map(function(row) {
        if (!Array.isArray(row) || row.length !== n) throw new Error("도로 행렬 크기가 다릅니다.");
        return row.map(function(v) { return number(v, "도로 연결 비용"); });
    });
}
function calculate(settings, targets, start, roundtrip, transport) {
    if (settings.backend !== "ors-vroom") return Promise.reject(new Error("지원하지 않는 경로 backend입니다."));
    if (!targets.length) return Promise.reject(new Error("계산할 조사대상을 선택하세요."));
    var locations = [start].concat(targets.map(function(t) { return t.coordinate; }));
    var base = settings.server_url.replace(/\/$/, "");
    function post(url, body) { return transport({url: url, method: "POST", body: body, headers: {Authorization: settings.key || "", "Content-Type": "application/json"}, timeout_ms: settings.timeout_ms}); }
    return post(base + "/v2/matrix/" + encodeURIComponent(settings.profile), {locations: locations, metrics: ["duration", "distance"], resolve_locations: true}).then(function(response) {
        var times = matrix(response.durations, locations.length), distances = matrix(response.distances, locations.length);
        if (!Array.isArray(response.sources) || response.sources.length !== locations.length) throw new Error("도로 연결 위치가 누락되었습니다.");
        response.sources.forEach(function(s) {
            if (!s || number(s.snapped_distance, "도로 이격거리") > settings.max_road_offset_m) throw new Error("도로에서 너무 먼 조사대상이 있습니다. 이격거리 설정을 확인하세요.");
        });
        var costs = settings.objective === "distance" ? distances : times;
        var vehicle = {id: 1, profile: "car", start_index: 0};
        if (roundtrip) vehicle.end_index = 0;
        var request = {jobs: targets.map(function(t, i) { return {id: i, location_index: i + 1, description: t.site_id}; }), vehicles: [vehicle], matrices: {car: {durations: times.map(function(r){return r.map(Math.round);}), distances: distances.map(function(r){return r.map(Math.round);}), costs: costs.map(function(r){return r.map(Math.round);})}}};
        return post(settings.optimizer_url, request).then(function(result) {
            if (result.code !== 0 || !Array.isArray(result.unassigned) || result.unassigned.length || !Array.isArray(result.routes) || result.routes.length !== 1) throw new Error("모든 조사대상에 연결되는 도로 경로를 찾지 못했습니다.");
            var route = result.routes[0], steps = (route.steps || []).filter(function(s) { return s.type === "job"; });
            var seen = {}, ordered = steps.map(function(s) {
                if (!Number.isInteger(s.id) || s.id < 0 || s.id >= targets.length || seen[s.id]) throw new Error("방문 순서에 중복 또는 잘못된 대상이 있습니다.");
                seen[s.id] = true; return targets[s.id];
            });
            if (ordered.length !== targets.length) throw new Error("방문 목록에서 조사대상이 누락되었습니다.");
            number(route.distance, "거리"); number(route.duration, "시간");
            var timed = steps.filter(function(s) { return s.arrival !== undefined; });
            if (timed.length && timed.length !== steps.length) throw new Error("예상 도착시간이 일부 조사대상에만 제공되었습니다.");
            var eta = timed.length ? steps.map(function(s){return number(s.arrival, "예상 도착시간");}) : null;
            var coords = [start].concat(ordered.map(function(t) { return t.coordinate; }));
            if (roundtrip) coords.push(start);
            return post(base + "/v2/directions/" + encodeURIComponent(settings.profile) + "/geojson", {coordinates: coords}).then(function(directions) {
                var f = directions.features && directions.features[0];
                var geometry = f ? f.geometry : null;
                var legs = f && f.properties && f.properties.segments || null;
                if (legs && legs.length !== coords.length - 1) throw new Error("도로 구간 수가 방문 순서와 다릅니다.");
                if (legs) legs = legs.map(function(l) { return {distance_m: number(l.distance, "구간 거리"), duration_s: number(l.duration, "구간 시간")}; });
                if (geometry && (geometry.type !== "LineString" || !Array.isArray(geometry.coordinates) || geometry.coordinates.length < 2)) throw new Error("도로선 응답이 올바르지 않습니다.");
                return {stops: ordered, distance_m: route.distance, duration_s: route.duration, road_geometry: geometry, eta: eta, eta_basis: eta ? "relative_seconds" : null, legs: legs};
            });
        });
    });
}
