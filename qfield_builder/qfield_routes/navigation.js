function nativeUrl(stop, callerId) {
    var p = stop.coordinate;
    if (!p || !isFinite(p[0]) || !isFinite(p[1]) ||
        p[0] < -180 || p[0] > 180 || p[1] < -90 || p[1] > 90)
        throw new Error("유효한 WGS84 목적지 좌표가 아닙니다.");
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
    var primary = platform === "android" ? androidUrl(stop, callerId) : nativeUrl(stop, callerId);
    if (opener(primary)) return {
        message: "운영체제에 네이버지도 실행을 요청했습니다. 앱 실행·목적지 수락·안내 시작 여부는 확인할 수 없습니다.",
        os_request_accepted: true, fallback: false
    };
    var installUrl = platform === "android" ?
        "market://details?id=com.nhn.android.nmap" : "http://itunes.apple.com/app/id311867728?mt=8";
    if (!opener(installUrl))
        throw new Error("네이버지도와 설치 페이지를 열지 못했습니다. 앱 설치와 실행 권한을 확인해 주세요.");
    return {message: "네이버지도 설치 페이지를 열었습니다. 설치 후 다시 시도해 주세요.",
        os_request_accepted: false, fallback: true};
}
