function url(stop) {
    var p = stop.coordinate;
    if (!p || !isFinite(p[0]) || !isFinite(p[1]) ||
        p[0] < -180 || p[0] > 180 || p[1] < -90 || p[1] > 90)
        throw new Error("유효한 WGS84 목적지 좌표가 아닙니다.");
    return "nmap://navigation?dlat=" + p[1] + "&dlng=" + p[0] +
        "&dname=" + encodeURIComponent(stop.name || stop.site_id) +
        "&appname=ch.opengis.qfield";
}
function open(stop, opener) {
    if (!opener(url(stop)))
        throw new Error("네이버지도를 열지 못했습니다. 앱 설치와 실행 권한을 확인해 주세요.");
}
