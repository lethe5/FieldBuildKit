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
    if (!value || value.type !== "LineString") throw new Error("type이 LineString이 아닙니다");
    if (!Array.isArray(value.coordinates)) throw new Error("coordinates가 배열이 아닙니다");
    if (value.coordinates.length < 2) throw new Error("coordinates 점 개수가 2개보다 적습니다");
    for (var i=0;i<value.coordinates.length;i++) {
        var point=value.coordinates[i];
        if (!Array.isArray(point)||point.length<2) throw new Error("coordinates["+i+"]가 좌표 배열이 아닙니다");
        if (typeof point[0]!=="number"||!isFinite(point[0])||typeof point[1]!=="number"||!isFinite(point[1]))
            throw new Error("coordinates["+i+"]에 유한한 숫자가 아닌 값이 있습니다");
        if (point[0]<-180||point[0]>180||point[1]<-90||point[1]>90)
            throw new Error("coordinates["+i+"]가 WGS84 범위를 벗어났습니다");
    }
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
function snappedDistance(row, stage, maximum) {
    if (!Object.prototype.hasOwnProperty.call(row, "snapped_distance")) return;
    var distance;
    try { distance = providerNumber(row.snapped_distance, "도로 이격거리", "snapped_distance"); }
    catch (error) { throw staged(error, stage); }
    if (maximum !== undefined && distance > maximum)
        throw staged(providerError("도로에서 너무 먼 조사지가 있습니다. snapped_distance 이격거리 설정을 확인하세요.", "snapped_distance"), stage);
}
function providerLine(value, reference) {
    try { return line(value); }
    catch (error) { throw providerError("도로 구간 geometry가 올바른 WGS84 LineString이 아닙니다 ("+error.message+"): " + reference, reference); }
}
function requestHeaders(settings) {
    var headers = {"Content-Type": "application/json"};
    if (settings.key) headers.Authorization = settings.key;
    return headers;
}
function routingParts(base) {
    base=String(base||"");
    var marker=base.search(/[?#]/), suffix=marker<0?"":base.slice(marker);
    if(marker>=0)base=base.slice(0,marker);
    return {base:base.replace(/\/+$/,""),suffix:suffix};
}
function calculateLegacy(settings, targets, start, roundtrip, transport) {
    if (settings.backend !== "ors-vroom") return Promise.reject(new Error("지원하지 않는 경로 backend입니다."));
    if (!targets.length) return Promise.reject(new Error("계산할 조사지를 선택하세요."));
    var locations = [start].concat(targets.map(function(t) { return t.coordinate; }));
    var routing=routingParts(settings.server_url),base=routing.base,routingSuffix=routing.suffix;
    function post(url, body) {
        var headers = requestHeaders(settings);
        var stage = url.indexOf("/matrix/") >= 0 ? "matrix" : (url.indexOf("/directions/") >= 0 ? "directions" : "optimizer");
        return transport({stage:stage,url: url.replace(/\/+$/, ""), method: "POST", body: body, headers: headers, timeout_ms: settings.timeout_ms})
            .catch(function(error){ throw staged(error,stage); });
    }
    return post(base + "/v2/matrix/" + encodeURIComponent(settings.profile) + routingSuffix, {locations: locations, metrics: ["duration", "distance"], resolve_locations: true}).then(function(response) {
        var times, distances;
        try {
            providerDocument(response, "matrix");
            times = matrix(response.durations, locations.length, "durations");
            distances = matrix(response.distances, locations.length, "distances");
            if (!Array.isArray(response.sources) || response.sources.length !== locations.length || response.sources.some(function(s){return !s || typeof s !== "object" || Array.isArray(s);}))
                throw providerError("도로 연결 위치가 누락되었습니다: sources", "sources");
            response.sources.forEach(function(s) { snappedDistance(s, "matrix", settings.max_road_offset_m); });
        } catch (error) { throw staged(error, "matrix"); }
        var costs = settings.objective === "distance" ? distances : times;
        var vehicle = {id: 1, profile: "car", start_index: 0};
        if (roundtrip) vehicle.end_index = 0;
        var request = {jobs: targets.map(function(_, i) { return {id: i, location_index: i + 1}; }), vehicles: [vehicle], matrices: {car: {durations: times.map(function(r){return r.map(Math.round);}), distances: distances.map(function(r){return r.map(Math.round);}), costs: costs.map(function(r){return r.map(Math.round);})}}};
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
            return post(base + "/v2/directions/" + encodeURIComponent(settings.profile) + "/geojson" + routingSuffix, {coordinates: coords}).then(function(directions) {
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

var stageLabels = {"origin-validation":"출발지 차량 경로 확인(origin-validation)","matrix":"행렬(matrix)","optimizer":"방문 순서 최적화(optimizer)",
    "directions":"도로 경로(directions)","access-snap":"차량 접근점(access-snap)",
    "walking-directions":"도보 경로(walking-directions)"};
function safeScalar(value, limit, key) {
    if (typeof value !== "string" && typeof value !== "number") return null;
    var text = String(value).replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/g, " ").replace(/\s+/g, " ").trim();
    if (!text || text.length > 100000 || /<[^>]*>|authorization|bearer\s|(?:token|key|secret)\s*[=:]|https?:\/\/\S*[?&][^\s=]+=/i.test(text)) return null;
    if (key && text.indexOf(String(key)) >= 0) return null;
    return text.slice(0, limit);
}
function httpError(stage, status, body, contentType, key) {
    var record = {stage:stage,http_status:Number.isInteger(status)&&status>0?status:null,provider_code:null,provider_message:null,safe_text:null};
    var type = String(contentType || "").toLowerCase(), parsed = null;
    if (body && typeof body === "object") parsed = body;
    else if (typeof body === "string" && body.length <= 100000) {
        try { parsed = JSON.parse(body); } catch (_) {}
    }
    if (parsed && !Array.isArray(parsed)) {
        var source = parsed.error && typeof parsed.error === "object" ? parsed.error : parsed;
        record.provider_code = safeScalar(source.code, 64, key);
        record.provider_message = safeScalar(source.message, 320, key);
        if ((source.code !== undefined && !record.provider_code) || (source.message !== undefined && !record.provider_message)) {
            record.provider_code = null; record.provider_message = null;
        }
    } else if (typeof body === "string" && body.length <= 100000 && type.indexOf("html") < 0 && type.indexOf("json") < 0) {
        record.safe_text = safeScalar(body, 320, key);
    }
    var parts = [(stageLabels[stage] || stage) + " 요청 실패"];
    if (record.http_status !== null) parts.push("HTTP " + record.http_status);
    if (record.provider_code || record.provider_message) parts.push((record.provider_code ? record.provider_code + (record.provider_message ? ": " : "") : "") + (record.provider_message || ""));
    else if (record.safe_text) parts.push(record.safe_text);
    var error = new Error(parts.join(" · ").slice(0, 512));
    error.category = "provider_http"; error.stage = stage; error.http_status = record.http_status; error.safe_record = record;
    var detail=((record.provider_code||"")+" "+(record.provider_message||"")+" "+(record.safe_text||"")).toLowerCase();
    error.classification=/endpoint.*unavailable/.test(detail)?"endpoint-unavailable-explicit":
        (/no (?:route|result)|경로.*없/.test(detail)?"no-result-explicit":"generic-http");
    error.suggested_actions=[];
    if(record.http_status===null){
        error.message=((stageLabels[stage]||stage)+" 요청 실패 · 네트워크 연결 상태를 확인하세요.").slice(0,512);
        error.classification="network";
        error.suggested_actions.push("connection");
    }
    if(record.http_status===401)error.suggested_actions.push("key");
    if(record.http_status===403)error.suggested_actions.push("permission");
    if(record.http_status===404)error.suggested_actions.push("endpoint");
    if(record.http_status===429)error.suggested_actions.push("wait");
    if(record.http_status>=500)error.suggested_actions.push("retry-provider");
    if(stage==="access-snap"&&/radius|cap|반경/.test(detail))error.suggested_actions.push("max_access_distance_m");
    return error;
}
function staged(error, stage) {
    if (!error.stage) {
        error.stage = stage;
        error.message = ((stageLabels[stage] || stage) + " 요청 실패 · " + String(error.message || error)).slice(0,512);
    }
    if(/time|timeout|시간.*초과/i.test(String(error.message||error)))error.suggested_actions=["timeout"];
    return error;
}
function haversine(a, b) {
    var rad=Math.PI/180, dlat=(b[1]-a[1])*rad, dlon=(b[0]-a[0])*rad;
    var h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(a[1]*rad)*Math.cos(b[1]*rad)*Math.sin(dlon/2)*Math.sin(dlon/2);
    return 6371008.8*2*Math.asin(Math.sqrt(h));
}
function reverseLine(value) { return {type:"LineString",coordinates:value.coordinates.slice().reverse()}; }
function walkingVisit(target, access, raw) {
    var source = target.coordinate, offset = haversine(access, source), legs;
    if (offset <= 1) { legs=[{direction:"outbound",distance_m:0,duration_s:0,geometry:null},{direction:"return",distance_m:0,duration_s:0,geometry:null}]; }
    else if (raw && raw.explicit_no_path) {
        var out={type:"LineString",coordinates:[access,source]};
        legs=[{direction:"outbound",distance_m:offset,duration_s:null,geometry:out},{direction:"return",distance_m:offset,duration_s:null,geometry:reverseLine(out)}];
    } else {
        var distance=providerNumber(raw && raw.distance_m,"도보 거리",target.site_id), duration=providerNumber(raw && raw.duration_s,"도보 시간",target.site_id);
        var geometry=providerLine(raw && raw.geometry,target.site_id);
        legs=[{direction:"outbound",distance_m:distance,duration_s:duration,geometry:geometry},{direction:"return",distance_m:distance,duration_s:duration,geometry:reverseLine(geometry)}];
    }
    return {layer_id:String(target.source_layer),site_id:String(target.site_id),site_name:String(target.name||target.site_id),source_coordinate:source.slice(),access_coordinate:access.slice(),access_offset_m:offset,
        walking_mode:raw&&raw.explicit_no_path?"unmapped_estimate":(offset<=1?"exact_zero":"mapped"),walking_legs:legs,trip_multiplier:2,
        metric_source:raw&&raw.explicit_no_path?"straight_line_lower_bound_m":(offset<=1?"exact_zero":"ors-foot-hiking")};
}
function walkingPayload(document, target, access) {
    if (document && document.explicit_no_path) return document;
    var feature=document&&document.type==="FeatureCollection"&&Array.isArray(document.features)&&document.features.length===1&&document.features[0], properties=feature&&feature.type==="Feature"&&feature.properties, summary=properties&&properties.summary;
    if (!feature || !summary) throw providerError("도보 경로 응답이 올바르지 않습니다: "+target.site_id,target.site_id);
    var rawGeometry=feature.geometry,segments=properties.segments,wayPoints=properties.way_points;
    if(rawGeometry&&rawGeometry.type==="LineString"&&Array.isArray(rawGeometry.coordinates)&&rawGeometry.coordinates.length===1&&coordinate(rawGeometry.coordinates[0])&&
            Array.isArray(segments)&&segments.length===1&&Array.isArray(wayPoints)&&wayPoints.length===2&&wayPoints[0]===0&&wayPoints[1]===0&&
            summary.distance===0&&summary.duration===0&&segments[0]&&segments[0].distance===0&&segments[0].duration===0)
        return {explicit_no_path:true};
    var geometry=providerLine(rawGeometry,target.site_id),distance=providerNumber(summary.distance,"도보 거리",target.site_id),duration=providerNumber(summary.duration,"도보 시간",target.site_id);
    var last=geometry.coordinates.length-1;
    if(!Array.isArray(segments)||segments.length!==1||!Array.isArray(wayPoints)||wayPoints.length!==2||
            !Number.isInteger(wayPoints[0])||!Number.isInteger(wayPoints[1])||wayPoints[0]!==0||wayPoints[1]!==last)
        throw providerError("도보 경로 segment 또는 route-level way_points가 올바르지 않습니다: "+target.site_id,target.site_id);
    var segmentDistance=providerNumber(segments[0]&&segments[0].distance,"도보 구간 거리",target.site_id),segmentDuration=providerNumber(segments[0]&&segments[0].duration,"도보 구간 시간",target.site_id);
    if(!close(distance,segmentDistance,1)||!close(duration,segmentDuration,1))throw providerError("도보 경로 summary와 segment metric이 일치하지 않습니다: "+target.site_id,target.site_id);
    return {distance_m:distance,duration_s:duration,geometry:geometry};
}
function explicitNoFootPath(error) {
    var record=error&&error.safe_record;if(!record)return false;
    var code=String(record.provider_code||"").toLowerCase(),message=String(record.provider_message||record.safe_text||"").toLowerCase();
    return /^(no_foot_route|no_foot_path)$/.test(code)||
        (code==="2010"&&/could not find routable point\b.*\bspecified coordinate\b/.test(message))||
        /no foot (?:route|path) (?:found|available)|도보.*경로.*없/.test(message);
}
function calculateMixed(settings, targets, start, roundtrip, transport) {
    if (settings.backend !== "ors-vroom") return Promise.reject(new Error("지원하지 않는 경로 backend입니다."));
    if (!targets.length) return Promise.reject(new Error("계산할 조사지를 선택하세요."));
    if (targets.length > (settings.snap_batch_limit || 3500)) return Promise.reject(new Error("차량 접근점 일괄 요청 한도를 초과했습니다. 대상을 나누어 계산하세요."));
    var radius=settings.max_access_distance_m;
    if (!isFinite(radius)||radius<350||radius>5000) return Promise.reject(new Error("차량 최대 접근 거리는 0.35~5.00 km여야 합니다."));
    var routing=routingParts(settings.server_url),base=routing.base,routingSuffix=routing.suffix,headers=requestHeaders(settings);
    function post(stage,url,body){return transport({stage:stage,url:url,method:"POST",body:body,headers:headers,timeout_ms:settings.timeout_ms}).catch(function(e){throw staged(e,stage);});}
    var sourceTargets=targets.map(function(t){
        return Object.assign({},t,{coordinate:t.coordinate.slice(),source_coordinate:t.coordinate.slice()});
    });
    return post("origin-validation",base+"/v2/matrix/driving-car"+routingSuffix,{locations:[start.slice(),start.slice()],sources:[0],destinations:[1],metrics:["duration"],resolve_locations:true}).then(function(origin){
        providerDocument(origin,"origin-validation");
        var source=Array.isArray(origin.sources)&&origin.sources.length===1&&origin.sources[0],destination=Array.isArray(origin.destinations)&&origin.destinations.length===1&&origin.destinations[0];
        var routable=Array.isArray(origin.durations)&&origin.durations.length===1&&Array.isArray(origin.durations[0])&&origin.durations[0].length===1&&typeof origin.durations[0][0]==="number"&&isFinite(origin.durations[0][0])&&origin.durations[0][0]>=0&&
            source&&typeof source==="object"&&!Array.isArray(source)&&coordinate(source.location)&&
            destination&&typeof destination==="object"&&!Array.isArray(destination)&&coordinate(destination.location);
        if(!routable){var failure=new Error("출발지를 driving-car 도로에서 확인할 수 없습니다. 도로 위의 지도 위치 출발 또는 저장 기본 출발지를 사용하세요.");failure.stage="origin-validation";failure.suggested_actions=["map_start","saved_start"];throw failure;}
        snappedDistance(source,"origin-validation");snappedDistance(destination,"origin-validation");
        return post("access-snap",base+"/v2/snap/driving-car/json"+routingSuffix,{locations:sourceTargets.map(function(t){return t.source_coordinate;}),radius:radius});
    }).then(function(snap){
        providerDocument(snap,"access-snap");if(!Array.isArray(snap.locations)||snap.locations.length!==sourceTargets.length)throw providerError("차량 접근점 응답 수가 올바르지 않습니다.","access-snap");
        var access=snap.locations.map(function(row,i){var p=row&&row.location;if(!coordinate(p)){var e=new Error(sourceTargets[i].name+" ("+sourceTargets[i].site_id+") 차량 접근점을 "+(radius/1000).toFixed(2)+" km 안에서 찾지 못했습니다. 좌표, OSM coverage와 차량 최대 접근 거리를 확인하세요.");e.stage="access-snap";e.suggested_actions=["coordinates","osm_coverage","max_access_distance_m"];throw e;}return p.slice();});
        var visits=[],chain=Promise.resolve();
        sourceTargets.forEach(function(target,i){chain=chain.then(function(){
            if(haversine(access[i],target.source_coordinate)<=1){visits.push(walkingVisit(target,access[i],null));return;}
            return post("walking-directions",base+"/v2/directions/foot-hiking/geojson"+routingSuffix,{coordinates:[access[i],target.source_coordinate]}).then(function(raw){visits.push(walkingVisit(target,access[i],walkingPayload(raw,target,access[i])));}).catch(function(error){if(explicitNoFootPath(error)){visits.push(walkingVisit(target,access[i],{explicit_no_path:true}));return;}throw error;});
        });});
        return chain.then(function(){var vehicleTargets=sourceTargets.map(function(t,i){return Object.assign({},t,{coordinate:access[i],access_coordinate:access[i]});});
            return calculateLegacy(settings,vehicleTargets,start,roundtrip,transport).then(function(vehicle){
                var mapped=0,lower=0,duration=0,unavailable=0;visits.forEach(function(v){v.walking_legs.forEach(function(l){if(v.walking_mode==="unmapped_estimate")lower+=l.distance_m;else mapped+=l.distance_m;if(l.duration_s===null)unavailable++;else duration+=l.duration_s;});});
                var vehicleTotals={distance_m:vehicle.distance_m,duration_s:vehicle.duration_s};
                var walkingTotals={mapped_distance_m:mapped,lower_bound_distance_m:lower,duration_s:unavailable?null:duration,unavailable_duration_count:unavailable};
                var orderedVisits=vehicle.stops.map(function(t){return visits.find(function(v){return v.site_id===t.site_id&&v.layer_id===String(t.source_layer);});});
                return Object.assign(vehicle,{stops:vehicle.stops.map(function(t){var original=sourceTargets.find(function(s){return s.site_id===t.site_id;});return Object.assign({},original,{access_coordinate:t.coordinate.slice(),coordinate:original.source_coordinate.slice()});}),vehicle_legs:vehicle.legs,visits:orderedVisits,vehicle_totals:vehicleTotals,walking_totals:walkingTotals,combined_totals:unavailable?null:{distance_m:vehicle.distance_m+mapped,duration_s:vehicle.duration_s+duration}});
            });});
    });
}
function calculate(settings, targets, start, roundtrip, transport) {
    return settings.max_access_distance_m === undefined ? calculateLegacy(settings,targets,start,roundtrip,transport) : calculateMixed(settings,targets,start,roundtrip,transport);
}
