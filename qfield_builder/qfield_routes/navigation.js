function canonicalNumber(value) {
    if (typeof value !== "number" || !isFinite(value)) throw new Error("유효한 WGS84 목적지 좌표가 아닙니다.");
    if (Object.is(value, -0)) value = 0;
    var text = value.toFixed(7).replace(/\.0+$|(?:(\.\d*?)0+)$/, "$1");
    return text === "-0" ? "0" : text;
}
function checkedCoordinate(stop) {
    var p = stop.coordinate;
    if (!Array.isArray(p) || p.length < 2 || typeof p[0] !== "number" || typeof p[1] !== "number" ||
        !isFinite(p[0]) || !isFinite(p[1]) ||
        p[0] < -180 || p[0] > 180 || p[1] < -90 || p[1] > 90)
        throw new Error("유효한 WGS84 목적지 좌표가 아닙니다.");
    return [canonicalNumber(p[0]), canonicalNumber(p[1])];
}
function nativeUrl(stop, callerId) {
    var p = checkedCoordinate(stop);
    return "nmap://navigation?dlat=" + encodeURIComponent(p[1]) + "&dlng=" + encodeURIComponent(p[0]) +
        "&dname=" + encodeURIComponent(stop.name || stop.site_id) +
        "&appname=" + encodeURIComponent(callerId || "ch.opengis.qfield");
}
function androidUrl(stop, callerId) {
    return nativeUrl(stop, callerId).replace(/^nmap:\/\//, "intent://") +
        "#Intent;scheme=nmap;action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;package=com.nhn.android.nmap;end";
}
function open(stop, opener, platform, callerId) {
    platform = String(platform || "").toLowerCase();
    if (platform !== "android" && platform !== "ios")
        throw new Error("네이버지도 안내는 Android 또는 iOS에서 사용할 수 있습니다. 지원 기기와 앱 설치를 확인해 주세요.");
    var p = checkedCoordinate(stop);
    var primary = platform === "android" ? androidUrl(stop, callerId) :
        "https://maps.apple.com/directions?destination=" + p[1] + "," + p[0] + "&mode=driving";
    var accepted = false;
    try { accepted = opener(primary) === true; }
    catch (error) {
        if (platform === "ios") throw new Error("Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요.");
        throw error;
    }
    if (accepted) return {
        message: "지도 앱에 길안내를 요청했습니다. 앱 실행·목적지 수락·안내 시작 여부는 확인할 수 없습니다.",
        os_request_accepted: true, fallback: false
    };
    if (platform === "ios")
        throw new Error("Apple 지도를 열 수 없습니다. 기기 설정과 네트워크 상태를 확인하세요.");
    var installUrl = platform === "android" ?
        "market://details?id=com.nhn.android.nmap" : "";
    if (!opener(installUrl))
        throw new Error("네이버지도와 설치 페이지를 열지 못했습니다. 앱 설치와 실행 권한을 확인해 주세요.");
    return {message: "네이버지도 설치 페이지를 열었습니다. 설치 후 다시 시도해 주세요.",
        os_request_accepted: false, fallback: true};
}
