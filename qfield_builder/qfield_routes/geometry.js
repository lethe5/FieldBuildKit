// All external coordinates use [longitude, latitude] in EPSG:4326.
function coordinate(value) {
    if (!Array.isArray(value) || value.length < 2 ||
        typeof value[0] !== "number" || typeof value[1] !== "number" ||
        !isFinite(value[0]) || !isFinite(value[1]) ||
        Math.abs(value[0]) > 180 || Math.abs(value[1]) > 90)
        throw new Error("유효한 WGS84 좌표가 아닙니다.");
    return [value[0], value[1]];
}
function literal(value) { return "'" + String(value).replace(/'/g, "''") + "'"; }
// Candidate source-CRS centroid policy (O-SRP-003); never modify source geometry.
function representative(shape) {
    if (!shape || !shape.coordinates) throw new Error("비어 있는 조사지 도형입니다.");
    var weighted = [], coords = shape.coordinates;
    function point(p) {
        if (!Array.isArray(p) || p.length < 2 || !isFinite(p[0]) || !isFinite(p[1])) throw new Error("잘못된 조사지 좌표입니다.");
        return p;
    }
    function line(points) {
        if (!points || points.length < 2) throw new Error("선의 좌표가 부족합니다.");
        for(var i=1;i<points.length;i++) {var a=point(points[i-1]), b=point(points[i]), w=Math.hypot(b[0]-a[0],b[1]-a[1]); if(w) weighted.push([(a[0]+b[0])/2,(a[1]+b[1])/2,w]);}
    }
    function polygon(rings) {
        if(!rings || !rings.length) throw new Error("면의 고리가 없습니다.");
        rings.forEach(function(ring,index) {
            if(ring.length<4 || ring[0][0]!==ring[ring.length-1][0] || ring[0][1]!==ring[ring.length-1][1]) throw new Error("면의 고리가 닫혀 있지 않습니다.");
            var area=0,x=0,y=0;
            for(var i=1;i<ring.length;i++) {var a=point(ring[i-1]),b=point(ring[i]), c=a[0]*b[1]-b[0]*a[1];area+=c;x+=(a[0]+b[0])*c;y+=(a[1]+b[1])*c;}
            if(!area) throw new Error("면적이 없는 도형입니다.");
            weighted.push([x/(3*area),y/(3*area),Math.abs(area)*(index===0?1:-1)]);
        });
    }
    if(shape.type==="Point") return point(coords).slice(0,2);
    if(shape.type==="MultiPoint") coords.forEach(function(p){p=point(p);weighted.push([p[0],p[1],1]);});
    else if(shape.type==="LineString") line(coords);
    else if(shape.type==="MultiLineString") coords.forEach(line);
    else if(shape.type==="Polygon") polygon(coords);
    else if(shape.type==="MultiPolygon") coords.forEach(polygon);
    else throw new Error("지원하지 않는 조사지 도형입니다.");
    var x=0,y=0,total=0;weighted.forEach(function(p){x+=p[0]*p[2];y+=p[1]*p[2];total+=p[2];});
    if(total<=0) throw new Error("대표점을 계산할 수 없습니다.");
    return [x/total,y/total];
}
function featurePoint(evaluator, layer, feature) {
    try {
        evaluator.layer = layer;
        evaluator.feature = feature;
        if (!evaluator.evaluate("is_valid($geometry)")) throw new Error("조사지 도형이 유효하지 않습니다.");
        var longitude = evaluator.evaluate("attribute($currentfeature,'_fb_route_lon')");
        var latitude = evaluator.evaluate("attribute($currentfeature,'_fb_route_lat')");
        function present(value) { return value !== null && value !== undefined && String(value).trim() !== "" && String(value).toUpperCase() !== "NULL"; }
        var kind = String(evaluator.evaluate("geometry_type($geometry)"));
        var multipart = Boolean(evaluator.evaluate("is_multipart($geometry)"));
        var point = kind === "Point" && !multipart ? "$geometry" : "centroid($geometry)";
        var transformed = "transform(" + point + ", @layer_crs, 'EPSG:4326')";
        var current = coordinate([
            Number(evaluator.evaluate("x(" + transformed + ")")),
            Number(evaluator.evaluate("y(" + transformed + ")"))
        ]);
        // Validate the loaded geometry and its declared CRS before using an
        // original-CRS representative retained by the project's reprojection.
        return present(longitude) && present(latitude) ? coordinate([Number(longitude), Number(latitude)]) : current;
    } catch (error) {
        if (String(error.message || error).indexOf("조사지") >= 0) throw error;
        throw new Error("조사지 원본 CRS와 WGS84 좌표 변환을 확인하세요.");
    }
}
function lineWkt(points) {
    if (!Array.isArray(points) || points.length < 2) throw new Error("도로 경로 도형이 없습니다.");
    return "LINESTRING(" + points.map(function(p) { return coordinate(p).join(" "); }).join(",") + ")";
}
function geometryWkt(shape) {
    if (!shape || !shape.type || !Array.isArray(shape.coordinates)) throw new Error("완료 표시 도형이 없습니다.");
    function point(value) { return coordinate(value).join(" "); }
    function list(values, encode) { return "(" + values.map(encode).join(",") + ")"; }
    var c = shape.coordinates;
    if (shape.type === "Point") return "POINT(" + point(c) + ")";
    if (shape.type === "LineString") return "LINESTRING" + list(c, point);
    if (shape.type === "Polygon") return "POLYGON" + list(c, function(ring) { return list(ring, point); });
    if (shape.type === "MultiPoint") return "MULTIPOINT" + list(c, function(p) { return "(" + point(p) + ")"; });
    if (shape.type === "MultiLineString") return "MULTILINESTRING" + list(c, function(line) { return list(line, point); });
    if (shape.type === "MultiPolygon") return "MULTIPOLYGON" + list(c, function(poly) { return list(poly, function(ring) { return list(ring, point); }); });
    throw new Error("지원하지 않는 완료 표시 도형입니다.");
}
