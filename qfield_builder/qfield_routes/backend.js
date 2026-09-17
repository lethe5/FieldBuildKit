// ORS v2 matrix/directions and VROOM v1.14 custom matrices. No straight-line fallback.
function number(value, label) {
    if (typeof value !== "number" || !isFinite(value) || value < 0) throw new Error(label + " 값이 올바르지 않습니다.");
    return value;
}
function matrix(value, n, reference) {
    if (!Array.isArray(value) || value.length !== n) throw providerError("도로 행렬이 누락되었습니다: " + reference, reference);
    return value.map(function(row) {
        if (!Array.isArray(row) || row.length !== n) throw providerError("도로 행렬 크기가 다릅니다: " + reference, reference);
        return row.map(function(v) { return providerNumber(v, "도로 연결 비용", reference); });
    });
}
function coordinate(value) {
    return Array.isArray(value) && value.length >= 2 &&
        typeof value[0] === "number" && isFinite(value[0]) && value[0] >= -180 && value[0] <= 180 &&
        typeof value[1] === "number" && isFinite(value[1]) && value[1] >= -90 && value[1] <= 90;
}
function line(value) {
    if (!value || value.type !== "LineString" || !Array.isArray(value.coordinates) ||
            value.coordinates.length < 2 || !value.coordinates.every(coordinate))
        throw new Error("도로 구간 도형이 올바른 WGS84 LineString이 아닙니다.");
    return value;
}
function endpoint(target) {
    return {layer_id: String(target.source_layer), site_id: String(target.site_id)};
}
function close(total, sum, floor) {
    return Math.abs(total - sum) <= Math.max(floor, Math.abs(sum) * 0.005);
}
function providerError(message, reference) {
    var error = new Error(message);
    error.category = "provider_response";
    error.reference = String(reference);
    return error;
}
function providerDocument(value, stage) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        var error = providerError(stage + " 서버 응답 문서가 올바르지 않습니다. 서버 응답 형식을 확인한 뒤 다시 시도하세요.", stage);
        error.stage = stage;
        throw error;
    }
    return value;
}
function providerNumber(value, label, reference) {
    try { return number(value, label); }
    catch (error) { throw providerError(label + " provider 값이 올바르지 않습니다: " + reference, reference); }
}
function providerLine(value, reference) {
    try { return line(value); }
    catch (error) { throw providerError("도로 구간 geometry가 올바른 WGS84 LineString이 아닙니다: " + reference, reference); }
}
function calculate(settings, targets, start, roundtrip, transport) {
    if (settings.backend !== "ors-vroom") return Promise.reject(new Error("지원하지 않는 경로 backend입니다."));
    if (!targets.length) return Promise.reject(new Error("계산할 조사지를 선택하세요."));
    var locations = [start].concat(targets.map(function(t) { return t.coordinate; }));
    var base = settings.server_url.replace(/\/+$/, "");
    function post(url, body) {
        var headers = {"Content-Type": "application/json"};
        if (settings.key) headers.Authorization = settings.key;
        return transport({url: url.replace(/\/+$/, ""), method: "POST", body: body, headers: headers, timeout_ms: settings.timeout_ms});
    }
    return post(base + "/v2/matrix/" + encodeURIComponent(settings.profile), {locations: locations, metrics: ["duration", "distance"], resolve_locations: true}).then(function(response) {
        providerDocument(response, "matrix");
        var times = matrix(response.durations, locations.length, "durations"), distances = matrix(response.distances, locations.length, "distances");
        if (!Array.isArray(response.sources) || response.sources.length !== locations.length) throw providerError("도로 연결 위치가 누락되었습니다: sources", "sources");
        response.sources.forEach(function(s) {
            if (!s || providerNumber(s.snapped_distance, "도로 이격거리", "snapped_distance") > settings.max_road_offset_m) throw providerError("도로에서 너무 먼 조사지가 있습니다. snapped_distance 이격거리 설정을 확인하세요.", "snapped_distance");
        });
        var costs = settings.objective === "distance" ? distances : times;
        var vehicle = {id: 1, profile: "car", start_index: 0};
        if (roundtrip) vehicle.end_index = 0;
        var request = {jobs: targets.map(function(t, i) { return {id: i, location_index: i + 1, description: t.site_id}; }), vehicles: [vehicle], matrices: {car: {durations: times.map(function(r){return r.map(Math.round);}), distances: distances.map(function(r){return r.map(Math.round);}), costs: costs.map(function(r){return r.map(Math.round);})}}};
        return post(settings.optimizer_url, request).then(function(result) {
            providerDocument(result, "optimizer");
            if (result.code !== 0 || !Array.isArray(result.unassigned) || result.unassigned.length || !Array.isArray(result.routes) || result.routes.length !== 1)
                throw providerError("모든 조사지에 연결되는 도로 경로를 찾지 못했습니다. 미배정 대상: " + ((result.unassigned && result.unassigned[0] && result.unassigned[0].id) === undefined ? "unknown" : result.unassigned[0].id), (result.unassigned && result.unassigned[0] && result.unassigned[0].id) === undefined ? "unassigned" : result.unassigned[0].id);
            var route = result.routes[0];
            if (!route || !Array.isArray(route.steps)) throw providerError("방문 steps가 올바르지 않습니다: steps", "steps");
            var steps = route.steps.filter(function(s) { return s && s.type === "job"; });
            var seen = {}, ordered = steps.map(function(s) {
                if (!Number.isInteger(s.id) || s.id < 0 || s.id >= targets.length || seen[s.id]) throw providerError("방문 순서에 중복 또는 잘못된 대상 ID가 있습니다: " + s.id, s.id);
                seen[s.id] = true; return targets[s.id];
            });
            if (ordered.length !== targets.length) {
                var missing = targets.map(function(_, i) { return i; }).find(function(i) { return !seen[i]; });
                throw providerError("방문 목록에서 조사지 ID가 누락되었습니다: " + missing, missing);
            }
            providerNumber(route.distance, "거리", "route.distance"); providerNumber(route.duration, "시간", "route.duration");
            var timed = steps.filter(function(s) { return s.arrival !== undefined; });
            if (timed.length && timed.length !== steps.length) throw providerError("예상 도착시간이 일부 조사지에만 제공되었습니다: arrival", "arrival");
            var eta = timed.length ? steps.map(function(s){return providerNumber(s.arrival, "예상 도착시간", "arrival:" + s.id);}) : null;
            var coords = [start].concat(ordered.map(function(t) { return t.coordinate; }));
            if (roundtrip) coords.push(start);
            return post(base + "/v2/directions/" + encodeURIComponent(settings.profile) + "/geojson", {coordinates: coords}).then(function(directions) {
                providerDocument(directions, "directions");
                if (!Array.isArray(directions.features) || directions.features.length !== 1)
                    throw providerError("directions 도로 응답의 features를 확인하세요.", "features");
                var f = providerDocument(directions.features[0], "directions.features[0]");
                var geometry = providerLine(f && f.geometry, "geometry");
                var properties = f && f.properties;
                var rawLegs = properties && properties.segments;
                var wayPoints = properties && properties.way_points;
                if (!Array.isArray(rawLegs) || rawLegs.length !== coords.length - 1)
                    throw providerError("도로 구간 수가 방문 순서와 다릅니다: " + (coords.length - 1), coords.length - 1);
                if (!Array.isArray(wayPoints) || wayPoints.length !== rawLegs.length + 1)
                    throw providerError("route-level way_points 수가 올바르지 않습니다: way_points", "way_points");
                var legs = rawLegs.map(function(raw, i) {
                    var fromIndex = wayPoints[i], toIndex = wayPoints[i + 1];
                    if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex) || fromIndex < 0 ||
                            toIndex <= fromIndex || toIndex >= geometry.coordinates.length ||
                            (i === 0 && fromIndex !== 0) ||
                            (i === rawLegs.length - 1 && toIndex !== geometry.coordinates.length - 1))
                        throw providerError("도로 구간 " + (i + 1) + " way_points index가 올바르지 않습니다: " + toIndex, toIndex);
                    var legGeometry = {type: "LineString", coordinates: geometry.coordinates.slice(fromIndex, toIndex + 1)};
                    return {
                        sequence: i + 1,
                        from: i === 0 ? "start" : endpoint(ordered[i - 1]),
                        to: i < ordered.length ? endpoint(ordered[i]) : "start",
                        distance_m: providerNumber(raw && raw.distance, "구간 거리", i + 1),
                        duration_s: providerNumber(raw && raw.duration, "구간 시간", i + 1),
                        geometry: providerLine(legGeometry, i + 1)
                    };
                });
                var distance = legs.reduce(function(sum, leg) { return sum + leg.distance_m; }, 0);
                var duration = legs.reduce(function(sum, leg) { return sum + leg.duration_s; }, 0);
                var summary = f && f.properties && f.properties.summary || {};
                var providerDistance = providerNumber(summary.distance === undefined ? route.distance : summary.distance, "전체 거리", "distance");
                var providerDuration = providerNumber(summary.duration === undefined ? route.duration : summary.duration, "전체 시간", "duration");
                if (!close(providerDistance, distance, 1) || !close(providerDuration, duration, 1))
                    throw providerError("전체 distance 또는 duration이 저장 구간 합계와 일치하지 않습니다: distance", "distance");
                return {stops: ordered, distance_m: distance, duration_s: duration, road_geometry: geometry, eta: eta, eta_basis: eta ? "relative_seconds" : null, legs: legs};
            });
        });
    });
}
