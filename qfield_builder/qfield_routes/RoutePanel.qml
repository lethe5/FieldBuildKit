import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.qgis
import org.qfield
import "qrc:/qml" as QFieldItems
import "controller.js" as Controller
import "geometry.js" as Geometry
import "repository.js" as Repository
import "backend.js" as Backend
import "navigation.js" as Navigation

Rectangle {
    id: panel
    objectName: "qpbSurveyRoutePanel"
    SystemPalette { id: hostPalette; colorGroup: SystemPalette.Active }
    property var controller: null
    property var routingBackend: Backend
    property var routingBackends: ({"ors-vroom": routingBackend})
    property var urlLauncher: Qt.openUrlExternally
    property var route: null
    property var candidate: null
    property var stops: []
    property var savedRoutes: []
    property string message: ""
    property bool expanded: false
    property bool busy: false
    property int completedCount: 0
    property int selectedCount: 0
    property var layerOptions: []
    property var fieldOptions: []
    property var targetOptions: []
    signal targetOptionsRefreshed()
    signal startValidationStarted()
    ListModel { id: targetOptionsModel; objectName: "targetOptionsModel" }
    property var routeProgress: ({available:true,remaining_distance_m:0,remaining_duration_s:0})
    property string mappingValidation: ""
    property string startValidation: ""
    property string remainingDistanceText: routeProgress.available ? formatDistance(routeProgress.remaining_distance_m) : "사용 불가"
    property string remainingDurationText: routeProgress.available ? formatDuration(routeProgress.remaining_duration_s) : "사용 불가"
    property string remainingGeometryText: routeProgress.available ? "사용 가능" : "사용 불가"
    property bool showRouteLine: true
    property string platformName: String(Qt.platform.os||"").toLowerCase()
    property string callerId: "ch.opengis.qfield"
    property var canvas: null
    property string surveyType: ""
    property string defaultLayer: surveyType === "simple_inventory" ? "" : "site"
    property var layerAliases: ({site:"조사지"})
    property string defaultId: surveyType === "simple_inventory" ? "" : "site_id"
    property string defaultName: surveyType === "simple_inventory" ? "" : "site_name"
    property bool settingsExpanded: false
    readonly property color hostSurfaceColor: hostPalette.window
    readonly property bool darkAppearance: hostSurfaceColor.r * 0.2126 + hostSurfaceColor.g * 0.7152 + hostSurfaceColor.b * 0.0722 < 0.5
    readonly property color surfaceColor: darkAppearance ? "#111827" : "#f8fafc"
    readonly property color foregroundColor: darkAppearance ? "#f9fafb" : "#111827"
    readonly property color mutedColor: darkAppearance ? "#cbd5e1" : "#334155"
    readonly property color outlineColor: darkAppearance ? "#94a3b8" : "#64748b"
    readonly property color focusColor: darkAppearance ? "#60a5fa" : "#1769e0"
    readonly property color errorColor: darkAppearance ? "#fca5a5" : "#b91c1c"
    property int displayedCandidateGeneration: 0
    property string displayedRouteIdentity: ""
    property var activeTransports: []
    property int transportGeneration: 0
    property bool lifecycleActive: true
    color: surfaceColor
    border.color: outlineColor
    palette.window: surfaceColor
    palette.base: surfaceColor
    palette.button: darkAppearance ? "#1f2937" : "#e2e8f0"
    palette.text: foregroundColor
    palette.windowText: foregroundColor
    palette.buttonText: foregroundColor
    palette.placeholderText: mutedColor
    palette.disabled.text: darkAppearance ? "#e2e8f0" : "#334155"
    palette.disabled.buttonText: darkAppearance ? "#e2e8f0" : "#334155"
    height: expanded ? Math.min(parent.height * 0.72, 640) : 44
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    z: 100

    component FloatingOutline: Rectangle {
        required property var owner
        objectName: owner.objectName + "Outline"
        color: "transparent"
        radius: 4
        border.width: owner.activeFocus ? 2 : 1
        border.color: owner.hasError ? panel.errorColor : (owner.activeFocus ? panel.focusColor : panel.outlineColor)
    }
    component FloatingLabel: Label {
        required property var owner
        readonly property string componentSource: Qt.resolvedUrl("RoutePanel.qml") + "#FloatingLabel"
        text: owner.floatingLabel
        x: 10
        height: 18
        y: -height / 2
        padding: owner.notchPadding
        color: owner.hasError ? panel.errorColor : (owner.activeFocus ? panel.focusColor : panel.mutedColor)
        font.pixelSize: 10
        background: Rectangle { color: panel.surfaceColor }
        enabled: false
        z: 2
    }
    component FloatingComboBox: ComboBox {
        required property string floatingLabel
        property bool hasError: false
        readonly property real outlineWidth: activeFocus ? 2 : 1
        readonly property real notchPadding: 3
        Accessible.name: floatingLabel
        palette.text: panel.foregroundColor
        palette.buttonText: panel.foregroundColor
        opacity: 1
        topPadding: 20
        bottomPadding: 4
        implicitHeight: 48
        Layout.bottomMargin: hasError ? 15 : 0
        background: FloatingOutline { owner: parent }
        FloatingLabel {
            objectName: parent.objectName + "FloatingLabel"
            owner: parent
        }
        Label {
            objectName: parent.objectName + "ValidationMessage"
            text: "입력 확인 필요"
            visible: parent.hasError
            enabled: false
            color: panel.errorColor
            y: parent.height + 2
            width: parent.width
            font.pixelSize: 10
        }
    }
    component FloatingTextField: TextField {
        required property string floatingLabel
        property bool hasError: false
        readonly property real outlineWidth: activeFocus ? 2 : 1
        readonly property real notchPadding: 3
        Accessible.name: floatingLabel
        color: panel.foregroundColor
        placeholderTextColor: panel.mutedColor
        opacity: 1
        activeFocusOnPress: true
        activeFocusOnTab: true
        focusPolicy: Qt.StrongFocus
        readOnly: false
        selectByMouse: true
        onPressed: forceActiveFocus(Qt.MouseFocusReason)
        topPadding: 20
        bottomPadding: 4
        implicitHeight: 48
        Layout.bottomMargin: hasError || readOnly || !enabled ? 15 : 0
        background: FloatingOutline { owner: parent }
        FloatingLabel {
            objectName: parent.objectName + "FloatingLabel"
            owner: parent
        }
        Label {
            objectName: parent.objectName + "ValidationMessage"
            text: "입력 확인 필요"
            visible: parent.hasError
            enabled: false
            color: panel.errorColor
            y: parent.height + 2
            width: parent.width
            font.pixelSize: 10
        }
        Label {
            objectName: parent.objectName + "StateReason"
            text: parent.readOnly ? "읽기 전용" : "사용 불가"
            visible: !parent.hasError && (parent.readOnly || !parent.enabled)
            enabled: false
            color: panel.mutedColor
            y: parent.height + 2
            width: parent.width
            font.pixelSize: 10
        }
    }

    ExpressionEvaluator { id: evaluator; project: qgisProject }
    FeatureModel { id: completionFeature; project: qgisProject }
    AttributeFormModel { id: completionForm; featureModel: completionFeature }
    Component { id: timeoutFactory; Timer {} }
    Component {
        id: roadFactory
        QFieldItems.GeometryRenderer {
            property var storedGeometry: null
            property string linePattern: "solid"
            property string semanticClass: "vehicle"
            property bool contrastingCasing: true
            property string semanticName: "차량 경로 실선"
            property string legendLabel: "차량 경로"
            property string nonColorCue: semanticName
            Accessible.name: semanticName
            mapSettings: panel.canvas.mapSettings
            color: panel.darkAppearance ? "#f8fafc" : "#111827"
            lineWidth: 7
            Component.onCompleted: {
                geometryWrapper.qgsGeometry=storedGeometry;
                geometryWrapper.crs=CoordinateReferenceSystemUtils.wgs84Crs();
            }
            QFieldItems.GeometryRenderer {
                mapSettings: panel.canvas.mapSettings
                color: "#1769e0"
                lineWidth: 4
                Component.onCompleted: { geometryWrapper.qgsGeometry=parent.storedGeometry; geometryWrapper.crs=CoordinateReferenceSystemUtils.wgs84Crs(); }
            }
        }
    }
    Component {
        id: walkingFactory
        Item {
            id: walkingRoot
            anchors.fill: parent
            property var coordinates: []
            property string linePattern: "dashed"
            property string semanticClass: linePattern === "dotted" ? "unmapped_walking" : "mapped_walking"
            property bool lineVisible: true
            visible: lineVisible
            property bool contrastingCasing: true
            property bool warningMarker: linePattern === "dotted"
            property string semanticName: linePattern === "dotted" ? "지도 경로 없음 점선 경고" : "도보 경로 파선"
            property string legendLabel: linePattern === "dotted" ? "지도 경로 없음" : "도보 경로"
            property string nonColorCue: semanticName
            Accessible.name: semanticName
            Repeater {
                id: walkingPoints
                model: walkingRoot.coordinates
                MapToScreen {
                    mapSettings: panel.canvas.mapSettings
                    mapPoint: GeometryUtils.reprojectPoint(GeometryUtils.point(modelData[0],modelData[1]),CoordinateReferenceSystemUtils.wgs84Crs(),panel.canvas.mapSettings.destinationCrs)
                    onScreenPointChanged: walkingCanvas.requestPaint()
                }
            }
            Canvas {
                id: walkingCanvas
                anchors.fill: parent
                onPaint: {
                    var ctx=getContext("2d");ctx.clearRect(0,0,width,height);if(walkingPoints.count<2)return;
                    function stroke(color,width,dash){ctx.beginPath();var first=walkingPoints.itemAt(0).screenPoint;ctx.moveTo(first.x,first.y);for(var i=1;i<walkingPoints.count;i++){var p=walkingPoints.itemAt(i).screenPoint;ctx.lineTo(p.x,p.y);}ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.stroke();}
                    if(walkingRoot.lineVisible){stroke(panel.darkAppearance?"#f8fafc":"#111827",7,[]);stroke(walkingRoot.linePattern==="dotted"?"#c026d3":"#7e22ce",4,walkingRoot.linePattern==="dotted"?[2,5]:[10,7]);}
                    if(walkingRoot.warningMarker){var p=walkingPoints.itemAt(Math.floor(walkingPoints.count/2)).screenPoint;ctx.setLineDash([]);ctx.fillStyle="#facc15";ctx.strokeStyle="#111827";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(p.x,p.y-9);ctx.lineTo(p.x-8,p.y+7);ctx.lineTo(p.x+8,p.y+7);ctx.closePath();ctx.fill();ctx.stroke();}
                }
            }
        }
    }
    Component {
        id: accessMarkerFactory
        QFieldItems.GeometryRenderer {
            property var accessCoordinate: null
            Accessible.name: "차량 접근점"
            mapSettings: panel.canvas.mapSettings
            color: "#7e22ce"
            pointSize: 12
            borderSize: 3
            Component.onCompleted: { geometryWrapper.qgsGeometry=GeometryUtils.createGeometryFromWkt("POINT("+accessCoordinate[0]+" "+accessCoordinate[1]+")"); geometryWrapper.crs=CoordinateReferenceSystemUtils.wgs84Crs(); }
        }
    }
    Component {
        id: completedFactory
        QFieldItems.GeometryRenderer {
            property var storedGeometry: null
            property var storedCrs: CoordinateReferenceSystemUtils.wgs84Crs()
            property string geometryType: ""
            readonly property string overlayColor: "#1565C0"
            readonly property real fillOpacity: geometryType === "Polygon" ? 0.35 : 1
            readonly property real outlineOpacity: 1
            readonly property bool persistent: false
            readonly property real polygonFillBoostOpacity: 8/15
            mapSettings: panel.canvas.mapSettings
            color: "#1565C0"
            lineWidth: 5
            pointSize: 18
            borderSize: 3
            Component.onCompleted: {
                geometryWrapper.qgsGeometry=storedGeometry;
                geometryWrapper.crs=storedCrs;
            }
            QFieldItems.GeometryRenderer {
                objectName: "completedFillBoost"
                visible: parent.geometryType === "Polygon"
                opacity: parent.polygonFillBoostOpacity
                mapSettings: panel.canvas.mapSettings
                color: "#1565C0"
                lineWidth: 5
                Component.onCompleted: {
                    geometryWrapper.qgsGeometry=parent.storedGeometry;
                    geometryWrapper.crs=parent.storedCrs;
                }
            }
        }
    }
    Component {
        id: startMarkerFactory
        Item {
            id: startMarkerRoot
            objectName: "startMarkerItem"
            anchors.fill: parent
            property var coordinate: null
            readonly property string markerLabel: "출발지"
            readonly property string semanticRole: "start_marker"
            Accessible.name: markerLabel
            Accessible.role: Accessible.StaticText
            QFieldItems.GeometryRenderer {
                id: startPoint
                objectName: "startMarkerPoint"
                anchors.fill: parent
                mapSettings: panel.canvas.mapSettings
                color: "#ff7a00"
                pointSize: 24
                borderSize: 5
                Component.onCompleted: {
                    if(startMarkerRoot.coordinate)geometryWrapper.qgsGeometry=GeometryUtils.createGeometryFromWkt("POINT("+startMarkerRoot.coordinate[0]+" "+startMarkerRoot.coordinate[1]+")");
                    geometryWrapper.crs=CoordinateReferenceSystemUtils.wgs84Crs();
                }
            }
            onCoordinateChanged: {
                if (coordinate && startPoint) startPoint.geometryWrapper.qgsGeometry=GeometryUtils.createGeometryFromWkt("POINT("+coordinate[0]+" "+coordinate[1]+")");
            }
            MapToScreen {
                id: markerPosition
                objectName: "startMarkerPosition"
                mapSettings: panel.canvas.mapSettings
                mapPoint: startMarkerRoot.coordinate ? GeometryUtils.reprojectPoint(GeometryUtils.point(startMarkerRoot.coordinate[0], startMarkerRoot.coordinate[1]), CoordinateReferenceSystemUtils.wgs84Crs(), panel.canvas.mapSettings.destinationCrs) : GeometryUtils.point(0, 0)
            }
            Rectangle {
                objectName: "startMarkerLabelBackground"
                x: markerPosition.screenPoint.x - width / 2
                y: markerPosition.screenPoint.y - height - 18
                width: markerText.implicitWidth + 12
                height: markerText.implicitHeight + 6
                color: "#111827"
                border.color: "white"
                border.width: 2
                radius: 3
                Label { id: markerText; objectName: "startMarkerText"; anchors.centerIn: parent; text: "출발지"; color: "white"; font.bold: true }
            }
        }
    }
    property var roadItem: null
    property var completedItems: []
    property var walkingItems: []
    property var startMarkerItem: null
    function formatDistance(meters) { return (Number(meters||0)/1000).toFixed(2)+" km"; }
    function formatDuration(seconds) {
        var minutes=Math.ceil(Number(seconds||0)/60),hours=Math.floor(minutes/60),rest=minutes%60;
        var text=rest<10?"0"+rest:String(rest);
        return hours>0 ? hours+"시간 "+text+"분" : text+"분";
    }
    function mappedWalkingDuration(activeRoute, remainingWalking) {
        if(activeRoute===candidate)return (activeRoute.visits||[]).reduce(function(total,visit){return total+(visit.walking_mode==="unmapped_estimate"?0:visit.walking_legs.reduce(function(sum,leg){return sum+Number(leg.duration_s||0);},0));},0);
        return Number(remainingWalking&&remainingWalking.mapped_duration_s||0);
    }
    function mixedSummary(activeRoute, remaining) {
        if(!activeRoute)return "조사 경로 · 0/0 · 남은 0.00 km · 0시간 00분";
        var vehicle=activeRoute===candidate?activeRoute.vehicle_totals:{distance_m:remaining.remaining_distance_m,duration_s:remaining.remaining_duration_s};
        var counts=completedCount+"/"+activeRoute.stops.length;
        if(!activeRoute.vehicle_totals)return activeRoute.name+" · "+counts+" · 남은 "+formatDistance(vehicle.distance_m)+" · "+formatDuration(vehicle.duration_s);
        var walking=activeRoute===candidate?activeRoute.walking_totals:remaining.remaining_walking;
        return activeRoute.name+" · "+counts+" · 남은 차량 "+formatDistance(vehicle.distance_m)+" · "+formatDuration(vehicle.duration_s)+
            " / 지도 도보 거리 "+formatDistance(walking.mapped_distance_m)+" · 지도 도보 시간 "+formatDuration(mappedWalkingDuration(activeRoute,walking))+
            (walking.lower_bound_distance_m?" / 직선거리 하한 "+formatDistance(walking.lower_bound_distance_m)+" · 시간 사용 불가":"");
    }
    function visitAccessibilityValue(index) {var r=candidate||route,v=r&&r.visits&&r.visits[index];if(!v)return null;var distance=0,duration=0,unknown=false;(v.walking_legs||[]).forEach(function(leg){distance+=Number(leg.distance_m||0);if(leg.duration_s===null)unknown=true;else duration+=Number(leg.duration_s||0);});return {site_id:v.site_id,site_name:v.site_name||v.site_id,walking_mode:v.walking_mode,metric_source:v.metric_source,roundtrip:true,distance_m:distance,duration_s:unknown?null:duration};}
    function visitAccessibilityNumber(value) {return Number(value)%1===0?Number(value).toFixed(1):String(value);}
    function visitAccessibilityText(index) {var v=visitAccessibilityValue(index);return v?v.site_name+" "+v.walking_mode+" "+v.metric_source+" 왕복 "+visitAccessibilityNumber(v.distance_m)+" m "+(v.duration_s===null?"시간 사용 불가":visitAccessibilityNumber(v.duration_s)+" s"):"";}
    function hasMappedWalking(activeRoute) {return Boolean(activeRoute&&activeRoute.visits&&activeRoute.visits.some(function(visit){return visit.walking_mode==="mapped";}));}
    function presentationFields(activeRoute, remaining) {
        if(!activeRoute)return {vehicle_distance:"",vehicle_duration:"",mapped_walking_distance:"",mapped_walking_duration:"",straight_line_lower_bound_m:"",roundtrip:"",metric_source:"",unavailable_reason:""};
        var vehicle=activeRoute===candidate?activeRoute.vehicle_totals:{distance_m:remaining.remaining_distance_m,duration_s:remaining.remaining_duration_s};
        var walking=activeRoute===candidate?activeRoute.walking_totals:remaining.remaining_walking;
        var sources=(activeRoute.visits||[]).map(function(visit){return visit.metric_source;}).filter(function(value,index,values){return value&&values.indexOf(value)===index;});
        return {vehicle_distance:formatDistance(vehicle.distance_m),vehicle_duration:formatDuration(vehicle.duration_s),
            mapped_walking_distance:walking?formatDistance(walking.mapped_distance_m):"",
            mapped_walking_duration:walking?formatDuration(mappedWalkingDuration(activeRoute,walking)):"",
            straight_line_lower_bound_m:walking?formatDistance(walking.lower_bound_distance_m):"",
            roundtrip:activeRoute.roundtrip?"왕복":"편도",metric_source:sources.join(", "),
            unavailable_reason:walking&&walking.unavailable_duration_count?"직선거리 하한 · 경로/시간 사용 불가":""};
    }
    function layerId(layer) {
        if(!layer)return "";
        if(typeof layer.id === "function")return String(layer.id());
        return String(layer.id||layer.layerId||layer.name||"");
    }
    function layerName(layer) {
        if(!layer)return "";
        if(typeof layer.sourceName === "function")return String(layer.sourceName());
        if(layer.sourceName)return String(layer.sourceName);
        if(typeof layer.name === "function")return String(layer.name());
        return String(layer.name||"");
    }
    function layerLabel(layer) {
        if(!layer)return "";
        if(typeof layer.name === "function")return String(layer.name());
        return String(layer.alias||layer.name||layerName(layer));
    }
    function supportedVectorLayer(layer) {
        if(!layer)return false;
        try {
            var fields=typeof layer.fields === "function"?layer.fields():layer.fields;
            if(!fields)return false;
            var geometryType=typeof layer.geometryType === "function"?layer.geometryType():layer.geometryType;
            return geometryType===undefined||geometryType===null||Number(geometryType)>=0&&Number(geometryType)<=2;
        } catch(e) {return false;}
    }
    function nodeValue(node,name) {
        if(!node)return null;
        var value=node[name];
        return typeof value === "function" ? value.call(node) : value;
    }
    function layerTreePath(node) {
        var parts=[],current=node;
        while(current) {
            var name=nodeValue(current,"name");
            if(name)parts.unshift(String(name));
            current=nodeValue(current,"parent");
        }
        return parts.join(" / ");
    }
    function projectLayers() {
        try {
            var mapCanvas=canvas||((iface&&typeof iface.mapCanvas==="function")?iface.mapCanvas():null);
            var canvasLayers=mapCanvas&&mapCanvas.mapSettings?mapCanvas.mapSettings.layers:null,canvasOrdered=[];
            if(typeof canvasLayers==="function")canvasLayers=canvasLayers();
            if(canvasLayers)for(var c=0;c<canvasLayers.length;c++)if(supportedVectorLayer(canvasLayers[c]))canvasOrdered.push({layer:canvasLayers[c],tree_path:""});
            if(canvasOrdered.length)return canvasOrdered;
        } catch(e) {}
        try {
            if(qgisProject&&typeof qgisProject.layerTreeRoot==="function") {
                var root=qgisProject.layerTreeRoot();
                if(root&&typeof root.findLayers==="function") {
                    var nodes=root.findLayers(),ordered=[];
                    for(var i=0;i<nodes.length;i++) {
                        var treeLayer=nodeValue(nodes[i],"layer");
                        if(supportedVectorLayer(treeLayer))ordered.push({layer:treeLayer,tree_path:layerTreePath(nodes[i])});
                    }
                    return ordered;
                }
            }
        } catch(e) {}
        var values=[];
        try {
            var raw=typeof qgisProject.mapLayers === "function" ? qgisProject.mapLayers() : qgisProject.mapLayers;
            if(Array.isArray(raw))values=raw.slice().sort(function(a,b){return layerId(a).localeCompare(layerId(b));});
            else if(raw)Object.keys(raw).sort().forEach(function(key){values.push(raw[key]);});
        } catch(e) {}
        if(!values.length)Object.keys(layerAliases).sort().forEach(function(name){
            var matches=typeof qgisProject.mapLayersByName === "function" ? qgisProject.mapLayersByName(layerAliases[name]||name) : [];
            if(matches&&matches.length)values.push(matches[0]);
        });
        return values.filter(supportedVectorLayer).map(function(layer){return {layer:layer,tree_path:""};});
    }
    function fieldsFor(layer) {
        var names=[],fields=null;
        try {
            fields=layer?(typeof layer.fields==="function"?layer.fields():layer.fields):null;
            var rawNames=fields?(typeof fields.names==="function"?fields.names():fields.names):null;
            if(rawNames!==undefined&&rawNames!==null)for(var n=0;n<rawNames.length;n++)names.push(String(rawNames[n]));
            else if(fields&&typeof fields.count === "function")for(var i=0;i<fields.count();i++)names.push(String(fields.at(i).name()));
            else if(Array.isArray(fields))names=fields.map(function(field){return String(typeof field.name==="function"?field.name():field.name||field);});
        } catch(e) { names=[]; }
        return names;
    }
    function refreshProjectSelectors(preserveLayer) {
        var raw=projectLayers(),counts={},options=[];
        raw.forEach(function(entry){var layer=entry.layer,source=layerName(layer),aliasSource=Object.keys(layerAliases).find(function(name){return layerAliases[name]===source;});if(aliasSource)source=aliasSource;var label=source==="site"?"조사지":String(layerLabel(layer)||layerAliases[source]||source);counts[label]=(counts[label]||0)+1;options.push({label:label,layer_id:layerId(layer),source_name:source,tree_path:entry.tree_path,layer:layer});});
        options.forEach(function(option){if(counts[option.label]>1)option.label=option.label+" · "+(option.tree_path||option.layer_id)+" · "+option.layer_id;});
        layerOptions=options;
        var wanted=preserveLayer||layerEdit.text,match=options.find(function(option){return option.layer_id===wanted;});
        if(!match&&wanted)match=options.find(function(option){return option.source_name===wanted;});
        if(!match&&!wanted)match=options.find(function(option){return option.source_name==="site";});
        layerEdit.text=match?match.layer_id:"";layerEdit.currentIndex=match?options.indexOf(match):-1;
        refreshFields(match?match.layer:null);
    }
    function refreshFields(layer) {
        var resolved=layer;
        if(!resolved)try{resolved=layerFor({layer:layerEdit.text});}catch(e){resolved=null;}
        var names=fieldsFor(resolved),oldId=idEdit.text,oldName=nameEdit.text,oldCompleted=completionEdit.text;
        fieldOptions=names;
        idEdit.text=names.indexOf(oldId)>=0?oldId:(names.find(function(name){return /_id$/i.test(name);})||"");
        nameEdit.text=names.indexOf(oldName)>=0?oldName:(names.find(function(name){return /_name$/i.test(name);})||"");
        completionEdit.text=names.indexOf(oldCompleted)>=0?oldCompleted:"";
        idEdit.currentIndex=names.indexOf(idEdit.text);nameEdit.currentIndex=names.indexOf(nameEdit.text);completionEdit.currentIndex=names.indexOf(completionEdit.text)+1;
        mappingValidation=layerEdit.text&&idEdit.text&&nameEdit.text?"":"조사지 레이어와 조사지 ID/이름 필드를 선택하세요.";
    }
    function validateStart() {
        startValidationStarted();
        if(startCombo.currentIndex===2&&targetEdit.text===""){startValidation="출발 조사지를 선택하세요.";return;}
        if(startCombo.currentIndex===1)try{Geometry.coordinate(controller.state.mapStart);}catch(e){clearStartMarker();startValidation="지도 중심을 출발지로 지정하세요.";return;}
        startValidation="";
    }
    function syncControlState() {
        controller.state.mapping={layer:layerEdit.text,id:idEdit.text,name:nameEdit.text,completed:completionEdit.text};
        controller.state.scope=["selected","all","uncompleted"][scopeCombo.currentIndex];
        controller.state.startMode=["gps","map","target","saved_default"][startCombo.currentIndex];
        controller.state.targetStart=targetEdit.text;
        controller.state.roundtrip=roundtripBox.checked;
    }
    function refreshTargets() {
        if(!controller)return;
        try {syncControlState();var rows=controller.targets();targetOptions=rows.map(function(row){return {label:row.name+" · "+row.site_id,value:row.site_id};});targetOptionsModel.clear();targetOptions.forEach(function(option){targetOptionsModel.append(option);});
            if(!targetOptions.some(function(option){return option.value===targetEdit.text;}))targetEdit.text="";
            targetEdit.currentIndex=targetOptions.findIndex(function(option){return option.value===targetEdit.text;});
            controller.state.targetStart=targetEdit.text;
            targetOptionsRefreshed();
            validateStart();
        } catch(e) {targetOptions=[];targetOptionsModel.clear();targetEdit.text="";targetEdit.currentIndex=-1;validateStart();}
    }
    function clearStartMarker() { if(startMarkerItem){startMarkerItem.visible=false;startMarkerItem.destroy();startMarkerItem=null;} }
    function showStartMarker(coordinate) {
        if(startMarkerItem){startMarkerItem.coordinate=coordinate;return;}
        var next=startMarkerFactory.createObject(canvas,{coordinate:coordinate});
        if(!next)throw new Error("출발지 marker를 표시할 수 없습니다.");
        startMarkerItem=next;
    }
    function clearCompletedOverlays() {
        completedItems.forEach(function(item){item.destroy();});completedItems=[];
        walkingItems.forEach(function(item){item.destroy();});walkingItems=[];
    }
    function refreshWalkingOverlays(activeRoute) {
        walkingItems.forEach(function(item){item.destroy();});walkingItems=[];
        if(!activeRoute||!activeRoute.visits||!canvas)return;
        activeRoute.visits.slice(activeRoute===route?routeProgress.prefix_length:0).forEach(function(visit){walkingItems.push(accessMarkerFactory.createObject(canvas,{accessCoordinate:visit.access_coordinate}));visit.walking_legs.slice(0,1).forEach(function(leg){if(!leg.geometry)return;walkingItems.push(walkingFactory.createObject(canvas,{coordinates:leg.geometry.coordinates,linePattern:visit.walking_mode==="unmapped_estimate"?"dotted":"dashed",lineVisible:showRouteLine}));});});
    }
    function refreshCompletedOverlays(activeRoute) {
        clearCompletedOverlays();
        if(!activeRoute||!canvas)return;
        var mapping=activeRoute.mapping||controller.state.mapping,layer;
        try{layer=layerFor(mapping);}catch(e){return;}
        var wanted={};activeRoute.stops.forEach(function(stop){if(stop.completed)wanted[stop.site_id]=true;});
        if(!Object.keys(wanted).length)return;
        var iterator=LayerUtils.createFeatureIterator(layer);
        try{while(iterator.hasNext()){
            var feature=iterator.next();evaluator.layer=layer;evaluator.feature=feature;
            var id=String(evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.id)+")"));
            if(!wanted[id])continue;
            var qgs=feature.geometry;
            var kind=String(evaluator.evaluate("geometry_type($geometry)"));
            var crs=typeof layer.crs==="function"?layer.crs():(layer.crs||CoordinateReferenceSystemUtils.wgs84Crs());
            completedItems.push(completedFactory.createObject(canvas,{storedGeometry:qgs,storedCrs:crs,geometryType:kind}));
        }}finally{iterator.close();}
    }
    function updateView() {
        if (!controller) return;
        var state=controller.state;
        route=controller.active(); candidate=state.candidate; stops=(candidate||route) ? (candidate||route).stops : state.listed;
        savedRoutes=state.snapshot ? state.snapshot.data.routes : [];
        message=state.message;busy=state.busy;
        completedCount=route ? route.stops.filter(function(s){return s.completed;}).length : 0;
        routeProgress=route?controller.progress(route):({available:true,remaining_distance_m:candidate?candidate.distance_m:0,remaining_duration_s:candidate?candidate.duration_s:0,remaining_geometry:candidate?candidate.road_geometry:null});
        showRouteLine=state.showRouteLine;
        if(candidate && state.candidateGeneration!==displayedCandidateGeneration) {
            displayedCandidateGeneration=state.candidateGeneration;
            routeName.text=candidate.name;
            unmappedAck.checked=false;
        } else if(!candidate && route) {
            var routeIdentity=route.route_id+":"+route.revision;
            if(routeIdentity!==displayedRouteIdentity) {
                displayedRouteIdentity=routeIdentity;
                routeName.text=route.name;
            }
        }
        var road=candidate?candidate.road_geometry:(routeProgress.available?routeProgress.remaining_geometry:(route&&route.road_geometry));
        if(roadItem) {roadItem.destroy();roadItem=null;}
        if(road && canvas) {
            var wkt=Geometry.lineWkt(road.coordinates);
            var geom=GeometryUtils.createGeometryFromWkt(wkt);
            roadItem=roadFactory.createObject(canvas,{storedGeometry:geom,visible:showRouteLine});
        }
        refreshCompletedOverlays(route);
        refreshWalkingOverlays(candidate||route);
    }
    function layerFor(mapping) {
        var layer=typeof qgisProject.mapLayer === "function" ? qgisProject.mapLayer(mapping.layer) : null;
        if(layer) return layer;
        var name=layerAliases[mapping.layer] || mapping.layer;
        var matches=typeof qgisProject.mapLayersByName === "function" ? qgisProject.mapLayersByName(name) : [];
        if(matches.length===1) return matches[0];
        throw new Error("조사지 레이어를 찾지 못했습니다. 조사지 레이어 이름 또는 ID를 설정하세요.");
    }
    function selectedFeatures(mapping) {
        if(!mapping || !mapping.layer) return [];
        var layer=layerFor(mapping);
        var host=iface.findItemByObjectName("featureForm"), model=host && host.model;
        return model && model.selectedLayer===layer ? (model.selectedFeatures || []) : [];
    }
    function refreshSelectedCount() {
        try {
            selectedCount=selectedFeatures({layer:layerEdit.text}).length;
        } catch(e) {
            selectedCount=0;
        }
    }
    function records(mapping,scope) {
        var layer=layerFor(mapping), features=[];
        if(scope==="selected") {
            features=selectedFeatures(mapping);
            selectedCount=features.length;
        } else {
            var iterator=LayerUtils.createFeatureIterator(layer);
            try {while(iterator.hasNext()) features.push(iterator.next());} finally {iterator.close();}
        }
        return features.map(function(feature) {
            evaluator.layer=layer;evaluator.feature=feature;
            var id=evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.id)+")");
            var name=evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.name)+")");
            var done=mapping.completed ? evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.completed)+")") : false;
            return {id:id,name:name,completed:done,coordinate:Geometry.featurePoint(evaluator,layer,feature)};
        });
    }
    function setCompleted(mapping,id,value) {
        var layer=layerFor(mapping), iterator=LayerUtils.createFeatureIterator(layer), found=null;
        try {while(iterator.hasNext()) {var feature=iterator.next();evaluator.layer=layer;evaluator.feature=feature;if(String(evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.id)+")"))===id) {found=feature;break;}}} finally {iterator.close();}
        if(!found) throw new Error("완료 상태를 변경할 대상을 찾지 못했습니다.");
        completionFeature.currentLayer=layer;completionFeature.feature=found;
        completionForm.applyFeatureModel();
        if(!completionForm.changeAttribute(mapping.completed,value) || !completionForm.save()) throw new Error("완료 필드를 저장하지 못했습니다. 편집 권한과 필드 형식을 확인하세요.");
    }
    function transport(request) {
        return new Promise(function(resolve,reject) {
            var generation=transportGeneration;
            if(!lifecycleActive){var stopped=new Error("경로 계산이 취소되었습니다.");stopped.cancelled=true;reject(stopped);return;}
            var xhr=new XMLHttpRequest(), finished=false;
            activeTransports=activeTransports.concat([xhr]);
            var timer=timeoutFactory.createObject(panel,{interval:request.timeout_ms,repeat:false});
            function end(error,value) {if(finished)return;finished=true;timer.stop();timer.destroy();activeTransports=activeTransports.filter(function(item){return item!==xhr;});if(error)reject(error);else resolve(value);}
            timer.triggered.connect(function(){end(new Error("도로 서버 응답 시간이 초과되었습니다."));xhr.abort();});
            xhr.onreadystatechange=function() {
                if(xhr.readyState!==XMLHttpRequest.DONE || finished)return;
                if(generation!==transportGeneration||!lifecycleActive){var stopped=new Error("경로 계산이 취소되었습니다.");stopped.cancelled=true;end(stopped);return;}
                if(xhr.status<200 || xhr.status>=300) {end(Backend.httpError(request.stage,xhr.status,xhr.responseText,xhr.getResponseHeader("Content-Type"),controller?controller.state.settings.key:""));return;}
                try {end(null,JSON.parse(xhr.responseText));}catch(e){var failure=new Error("도로 서버 응답을 해석할 수 없습니다: JSON");failure.category="provider_response";failure.reference="JSON";end(failure);}
            };
            xhr.open(request.method,request.url);
            Object.keys(request.headers).forEach(function(k){xhr.setRequestHeader(k,request.headers[k]);});
            timer.start();xhr.send(JSON.stringify(request.body));
        });
    }
    function cancelTransports(){transportGeneration++;var rows=activeTransports.slice();activeTransports=[];rows.forEach(function(xhr){try{xhr.abort();}catch(_){}});}
    function applyControls(refreshBefore) {
        if(refreshBefore!==false)refreshProjectSelectors(layerEdit.text);
        syncControlState();
        validateStart();
        if(mappingValidation||startValidation)throw new Error(mappingValidation||startValidation);
        controller.configure({server_url:serverEdit.text,optimizer_url:optimizerEdit.text,backend:backendEdit.text,profile:profileEdit.text,key:keyEdit.text,timeout_ms:Number(timeoutEdit.text),max_road_offset_m:Number(offsetEdit.text),max_access_distance_m:Number(accessEdit.text),objective:objectiveCombo.currentIndex===0?"time":"distance"});
    }
    function syncMapping() {
        var m=controller.state.mapping;
        layerEdit.text=m.layer;idEdit.text=m.id;nameEdit.text=m.name;completionEdit.text=m.completed;
        refreshProjectSelectors(m.layer);
    }
    function selectRoute(id) {if(controller.select(id)) syncMapping();}
    function pickMapStart() {
        if(!canvas || !canvas.mapSettings) throw new Error("지도 중심 위치를 확인할 수 없습니다.");
        var p=canvas.mapSettings.getCenter(true);
        var transformed="transform(make_point("+p.x+","+p.y+"), @project_crs, 'EPSG:4326')";
        var coordinate=Geometry.coordinate([Number(evaluator.evaluate("x("+transformed+")")),Number(evaluator.evaluate("y("+transformed+")"))]);
        showStartMarker(coordinate);
        controller.state.mapStart=coordinate;
        startCombo.currentIndex=1;message="지도 중심을 출발지로 지정했습니다.";
    }
    function calculate() {try {lifecycleActive=true;applyControls(true);refreshTargets();controller.calculate(route!==null&&!Array.isArray(route.visits));}catch(e){controller.error(e);}}
    function completionEnabled(stop,index) {return !candidate && route!==null && (stop.completed===true || index===routeProgress.prefix_length);}
    function completionState(stop,index) {return stop.completed===true && index>=routeProgress.prefix_length ? "순서 밖 완료" : (stop.completed===true ? "완료" : "미완료");}
    Component.onCompleted: {
        canvas=iface&&typeof iface.mapCanvas==="function"?iface.mapCanvas():iface.findItemByObjectName("mapCanvas");
        try {
            var directory=String(evaluator.evaluate("@project_folder"));
            controller=Controller.create({geometry:Geometry,repository:Repository,backend:{calculate:function(s,t,o,r,x){var provider=panel.routingBackends[s.backend];return provider ? provider.calculate(s,t,o,r,x) : Promise.reject(new Error("지원하지 않는 경로 backend입니다."));}},navigation:Navigation,
                base:directory+"/survey-routes",io:{exists:FileUtils.fileExists,read:FileUtils.readFileContent,write:FileUtils.writeFileContent},cancelTransport:cancelTransports,
                features:records,setCompleted:setCompleted,transport:transport,openUrl:function(url){return panel.urlLauncher(url);},
                platform:function(){return panel.platformName;},callerId:function(){return panel.callerId;},
                projectKey:function(){return evaluator.evaluate("@fieldbuild_route_api_key");},
                gps:function(){var p=iface.findItemByObjectName("positionSource"), info=p && p.positionInformation;if(!p || !p.active || !info || !info.latitudeValid || !info.longitudeValid)throw new Error("GPS 위치가 없습니다. 위치 수신 후 다시 계산하세요.");return [info.longitude,info.latitude];},
                uuid:function(){return String(evaluator.evaluate("uuid('WithoutBraces')"));},changed:updateView});
            if(!controller.active() && !controller.state.snapshot.data.settings.mapping) controller.state.mapping={layer:defaultLayer,id:defaultId,name:defaultName,completed:""};
            syncMapping();
            var s=controller.state.settings;serverEdit.text=s.server_url;optimizerEdit.text=s.optimizer_url;backendEdit.text=s.backend;profileEdit.text=s.profile;keyEdit.text=s.key;timeoutEdit.text=String(s.timeout_ms);offsetEdit.text=String(s.max_road_offset_m);accessEdit.text=String(s.max_access_distance_m);
            updateView();refreshSelectedCount();refreshTargets();
        } catch(e) {message=String(e.message||e);}
    }
    onExpandedChanged: {if(expanded){refreshProjectSelectors(layerEdit.text);refreshSelectedCount();refreshTargets();}}
    Component.onDestruction: {lifecycleActive=false;if(controller)controller.cancel("project-close");cancelTransports();if(roadItem)roadItem.destroy();clearCompletedOverlays();clearStartMarker();}
    Timer {objectName:"candidateRefreshTimer";interval:500;repeat:true;running:controller!==null && expanded;onTriggered:{refreshSelectedCount();refreshProjectSelectors(layerEdit.text);refreshTargets();}}
    Timer {interval:1500;repeat:true;running:controller!==null && expanded && !busy;onTriggered:{try{controller.refresh();}catch(e){controller.error(e);}}}
    ColumnLayout {
        anchors.fill:parent;spacing:4
        Button {objectName:"routeSummaryButton";property var presentationFields:panel.presentationFields(panel.candidate||panel.route,panel.routeProgress);Layout.fillWidth:true;Layout.preferredHeight:40;text:(panel.expanded?"▾ ":"▸ ")+panel.mixedSummary(panel.candidate||panel.route,panel.routeProgress);Accessible.name:text;onClicked:panel.expanded=!panel.expanded}
        ScrollView {
            id:routeScroll;objectName:"routeScroll";visible:panel.expanded;Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            contentWidth:availableWidth
            topPadding:20
            ScrollBar.horizontal.policy:ScrollBar.AlwaysOff
            ColumnLayout {
                objectName:"routeContent";width:Math.max(0,routeScroll.availableWidth-24);x:12;spacing:6
                FloatingComboBox {id:layerEdit;objectName:"layerEdit";floatingLabel:"조사지";property string text:panel.defaultLayer;property string placeholderText:"레이어 선택";hasError:panel.mappingValidation!==""&&!text;Layout.fillWidth:true;Layout.topMargin:18;model:panel.layerOptions;textRole:"label";onActivated:function(index){text=panel.layerOptions[index].layer_id;panel.refreshFields(panel.layerOptions[index].layer);panel.refreshSelectedCount();panel.refreshTargets();}}
                RowLayout {Layout.fillWidth:true;spacing:6;FloatingComboBox{id:idEdit;objectName:"idEdit";floatingLabel:"조사지 ID 필드";property string text:panel.defaultId;Layout.fillWidth:true;Layout.minimumWidth:0;model:panel.fieldOptions;onActivated:function(index){text=panel.fieldOptions[index];panel.refreshTargets();}} FloatingComboBox{id:nameEdit;objectName:"nameEdit";floatingLabel:"조사지 이름 필드";property string text:panel.defaultName;Layout.fillWidth:true;Layout.minimumWidth:0;model:panel.fieldOptions;onActivated:function(index){text=panel.fieldOptions[index];panel.refreshTargets();}}}
                FloatingComboBox {id:completionEdit;objectName:"completionEdit";floatingLabel:"조사 완료 필드";property string text:"";Layout.fillWidth:true;model:[""].concat(panel.fieldOptions);onActivated:function(index){text=model[index];panel.refreshTargets();}}
                Label {objectName:"mappingValidationLabel";visible:panel.mappingValidation!=="";text:panel.mappingValidation;color:panel.errorColor;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"completionHelpLabel";text:"완료 필드는 source layer의 Boolean 필드 이름입니다. 값이 true일 때만 완료이며 false/NULL/missing은 미완료입니다. 비우면 이 저장 경로 안에서만 완료 상태를 관리합니다.";wrapMode:Text.Wrap;Layout.fillWidth:true}
                FloatingComboBox {id:scopeCombo;objectName:"scopeCombo";floatingLabel:"계산 대상";model:["선택 대상","전체 대상","미조사 대상"];Layout.fillWidth:true;onActivated:panel.refreshTargets()}
                Label {objectName:"scopeHelpLabel";text:"선택 대상은 QField에서 체크한 피처만, 전체 대상은 선택과 무관한 모든 유효 피처, 미조사 대상은 전체 중 완료되지 않은 피처를 사용합니다.";wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"selectionHelpLabel";visible:scopeCombo.currentIndex===0;text:"조사지 레이어를 열고 피처 선택/체크 도구로 계산할 조사지를 선택한 뒤 이 패널로 돌아오세요. 현재 선택한 조사지: "+panel.selectedCount+"개";wrapMode:Text.Wrap;Layout.fillWidth:true}
                FloatingComboBox {id:startCombo;objectName:"startCombo";floatingLabel:"출발지";model:["현재 GPS 출발","지도 위치 출발","조사지 출발","저장 기본 출발지"];Layout.fillWidth:true;onCurrentIndexChanged:{if(currentIndex!==1)panel.clearStartMarker();}onActivated:{panel.refreshTargets();panel.validateStart();}}
                Button {objectName:"mapCenterButton";visible:startCombo.currentIndex===1;text:"지도 중심을 출발지로 지정";onClicked:{try{pickMapStart();}catch(e){controller.error(e);}}}
                ComboBox {id:targetEdit;objectName:"targetEdit";property string text:"";visible:startCombo.currentIndex===2;Layout.fillWidth:true;model:targetOptionsModel;textRole:"label";onActivated:function(index){text=panel.targetOptions[index].value;panel.validateStart();}}
                Label {objectName:"startValidationLabel";visible:panel.startValidation!=="";text:panel.startValidation;color:panel.errorColor;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Button {visible:startCombo.currentIndex===1;text:"지정 위치를 기본 출발지로 저장";onClicked:controller.saveDefault(controller.state.mapStart)}
                CheckBox {id:roundtripBox;objectName:"roundtripBox";text:"출발지로 복귀";checked:true}
                Button {id:settingsDisclosure;objectName:"settingsDisclosure";text:(panel.settingsExpanded?"▾ ":"▸ ")+"API URL/키 설정";Layout.fillWidth:true;Accessible.name:"API URL/키 설정";Accessible.description:panel.settingsExpanded?"expanded":"collapsed";onClicked:panel.settingsExpanded=!panel.settingsExpanded}
                ColumnLayout {
                    objectName:"settingsContent";visible:panel.settingsExpanded;Layout.fillWidth:true;spacing:6
                    FloatingTextField {id:serverEdit;objectName:"serverEdit";floatingLabel:"ORS 서버 URL";Layout.fillWidth:true}
                    FloatingTextField {id:optimizerEdit;objectName:"optimizerEdit";floatingLabel:"VROOM 서버 URL";Layout.fillWidth:true}
                    TextField {id:backendEdit;objectName:"backendEdit";Layout.fillWidth:true;placeholderText:"경로 backend ID";Accessible.name:"경로 backend ID"}
                    TextField {id:profileEdit;objectName:"profileEdit";Layout.fillWidth:true;placeholderText:"ORS profile";Accessible.name:"ORS profile"}
                    TextField {id:keyEdit;objectName:"keyEdit";Layout.fillWidth:true;placeholderText:"API 키 (저장하지 않음)";Accessible.name:"API 키";echoMode:TextInput.Password}
                    Label {objectName:"keySourceLabel";text:controller&&controller.state.keySource==="project"&&keyEdit.text===controller.state.settings.key?"프로젝트 파일의 평문 키 사용 중":"이번 세션만 사용";wrapMode:Text.Wrap;Layout.fillWidth:true}
                    Label {objectName:"projectKeyWarningLabel";visible:controller&&controller.state.keySource==="project"&&keyEdit.text===controller.state.settings.key;text:"프로젝트 파일(.qgs)에 평문 키가 포함되어 있습니다.";wrapMode:Text.Wrap;Layout.fillWidth:true;color:panel.darkAppearance?"#fde68a":"#78350f"}
                    RowLayout {Layout.fillWidth:true;spacing:6;TextField{id:timeoutEdit;objectName:"timeoutEdit";Layout.fillWidth:true;Layout.minimumWidth:0;placeholderText:"제한시간(ms)"} TextField{id:offsetEdit;objectName:"offsetEdit";Layout.fillWidth:true;Layout.minimumWidth:0;placeholderText:"도로 이격거리(m)"}}
                    FloatingTextField {id:accessEdit;objectName:"accessEdit";floatingLabel:"차량 최대 접근 거리 (m)";Layout.fillWidth:true;Accessible.description:"기본 2.00 km, 허용 0.35–5.00 km"}
                    Label {objectName:"accessDistanceHelp";text:"기본 2.00 km · 허용 범위 0.35–5.00 km";wrapMode:Text.Wrap;Layout.fillWidth:true}
                    ComboBox {id:objectiveCombo;objectName:"objectiveCombo";model:["시간 최소화","거리 최소화"];Layout.fillWidth:true}
                    Button {objectName:"settingsSaveButton";text:"서버 설정 저장 (키 제외)";onClicked:{try{applyControls();controller.saveSettings();}catch(e){controller.error(e);}}}
                }
                Label {objectName:"coordinateSharingNotice";text:"계산하면 원본 조사 좌표, 반환된 차량 접근 좌표와 경로 geometry 요청이 ORS에 전송됩니다.";Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Button {objectName:"calculateButton";text:"새 경로 계산";Accessible.name:text;Accessible.role:Accessible.Button;enabled:controller!==null&&!busy&&panel.mappingValidation===""&&panel.startValidation==="";onClicked:calculate()}
                Label {id:messageLabel;objectName:"messageLabel";text:panel.message;Layout.fillWidth:true;wrapMode:Text.Wrap}
                Label {objectName:"remainingLabel";text:(candidate||route)?"남은 "+panel.remainingDistanceText+" · "+panel.remainingDurationText:"결과 없음";Layout.fillWidth:true;wrapMode:Text.Wrap}
                Label {objectName:"availabilityLabel";text:routeProgress.available?(((candidate||route)&&(candidate||route).road_geometry?"도로선 제공":"도로선 없음")+" · "+((candidate||route)&&(candidate||route).eta?"ETA 제공 (출발 기준 초)":"ETA 미제공")+" · "+((candidate||route)&&(candidate||route).legs?"전체 구간 제공":"구간 값 미제공")):routeProgress.message;Layout.fillWidth:true;wrapMode:Text.Wrap}
                CheckBox {id:routeLineToggle;objectName:"routeLineToggle";text:"경로선 표시";checked:panel.showRouteLine;onClicked:controller.toggleRouteLine(checked)}
                Label {objectName:"mixedRouteLegend";text:"━ 차량 경로   ┄ 도보 경로   ··· 지도 경로 없음";Accessible.name:"차량 경로 실선, 도보 경로 파선, 지도 경로 없음 점선";wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"endpointGapCalculationDisclosure";visible:candidate!==null&&panel.hasMappedWalking(candidate);text:"ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함";Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"endpointGapSavedDisclosure";visible:candidate===null&&panel.hasMappedWalking(route);text:"ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함";Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"endpointGapLegendAccessibility";visible:panel.hasMappedWalking(candidate||route);text:"ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함";Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"mixedTotalsLabel";property var presentationFields:panel.presentationFields(candidate||route,routeProgress);property var screenReaderFields:presentationFields;visible:(candidate||route)&&Boolean((candidate||route).vehicle_totals);text:{var r=candidate||route;if(!r||!r.vehicle_totals)return "";var v=candidate?r.vehicle_totals:{distance_m:routeProgress.remaining_distance_m,duration_s:routeProgress.remaining_duration_s};return "차량 거리 "+panel.formatDistance(v.distance_m)+" · 차량 시간 "+panel.formatDuration(v.duration_s)+" · 왕복";} Accessible.name:text;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"mappedMetricSourceAccessibility";property string metricSourceValue:{var r=candidate||route;return r&&r.visits&&r.visits.length?String(r.visits[0].metric_source||""):"";} visible:metricSourceValue!=="";text:"도보 metric source "+metricSourceValue;Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Repeater {
                    id:visitAccessibilityRepeater
                    objectName:"visitAccessibilityRepeater"
                    model:{var r=candidate||route;return r&&r.visits?r.visits.length:0;}
                    delegate:Label {
                        required property int index
                        objectName:"visitAccessibilityDelegate-"+index
                        property var visitValue:panel.visitAccessibilityValue(index)
                        visible:text!==""
                        text:panel.visitAccessibilityText(index)
                        Accessible.name:text
                        Accessible.role:Accessible.StaticText
                        wrapMode:Text.Wrap
                        Layout.fillWidth:true
                    }
                }
                Label {objectName:"walkingTotalsAccessibility";property real metricValue:{var r=candidate||route,w=candidate?r.walking_totals:routeProgress.remaining_walking;return w?Number(w.mapped_distance_m):0;} visible:(candidate||route)&&Boolean((candidate||route).walking_totals);text:"지도 도보 거리 "+panel.formatDistance(metricValue);Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"mappedWalkingDurationAccessibility";property real metricValue:{var r=candidate||route,w=candidate?r.walking_totals:routeProgress.remaining_walking;return w?panel.mappedWalkingDuration(r,w):0;} visible:(candidate||route)&&Boolean((candidate||route).walking_totals);text:"지도 도보 시간 "+panel.formatDuration(metricValue);Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {objectName:"straightLineLowerBoundAccessibility";property real metricValue:{var r=candidate||route,w=candidate?r.walking_totals:routeProgress.remaining_walking;return w?Number(w.lower_bound_distance_m):0;} visible:metricValue>0;text:"직선거리 하한 "+panel.formatDistance(metricValue)+" · 도보 시간 사용 불가";Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                Label {id:mixedFallbackLabel;objectName:"mixedFallbackLabel";visible:(candidate||route)&&Boolean((candidate||route).visits&&((candidate||route).visits.some(function(v){return v.walking_mode==="unmapped_estimate";})));text:{var r=candidate||route;if(!r||!r.visits)return "";var visits=r.visits.filter(function(v){return v.walking_mode==="unmapped_estimate";});return "직선거리 하한 · 경로/시간 사용 불가 · 영향 조사지: "+visits.map(function(v){var stop=r.stops.find(function(s){return s.site_id===v.site_id;});return (stop&&stop.name)||v.site_id;}).join(", ")+" · metric source "+visits.map(function(v){return v.metric_source;}).filter(function(value,index,values){return values.indexOf(value)===index;}).join(", ");} Accessible.name:text;Accessible.role:Accessible.StaticText;wrapMode:Text.Wrap;Layout.fillWidth:true}
                CheckBox {id:unmappedAck;objectName:"unmappedAcknowledgement";visible:(candidate||route)&&Boolean((candidate||route).visits&&((candidate||route).visits.some(function(v){return v.walking_mode==="unmapped_estimate";})));text:"지도에 없는 도보 구간 포함";onClicked:controller.acknowledgeUnmapped(checked)}
                FloatingTextField {id:routeName;objectName:"routeName";floatingLabel:"저장할 경로 이름";placeholderText:"경로 이름";Layout.fillWidth:true}
                Button {objectName:"saveRouteButton";text:"계산 결과 저장";enabled:candidate!==null&&panel.mappingValidation===""&&(!unmappedAck.visible||unmappedAck.checked);onClicked:{try{applyControls(true);if(controller.save(routeName.text)){var point=messageLabel.mapToItem(routeScroll.contentItem,Qt.point(0,0));routeScroll.contentItem.contentY=Math.max(0,point.y-routeScroll.contentItem.height/2+messageLabel.height/2);}}catch(e){controller.error(e);}}}
                FloatingComboBox {id:savedCombo;objectName:"savedCombo";floatingLabel:"저장 경로 불러오기";Layout.fillWidth:true;model:panel.savedRoutes;textRole:"name"}
                Button {objectName:"loadRouteButton";text:"저장 경로 불러오기";enabled:savedCombo.currentIndex>=0;onClicked:selectRoute(panel.savedRoutes[savedCombo.currentIndex].route_id)}
                Button {objectName:"navigateButton";text:"다음 지점 지도 안내";enabled:controller!==null&&route!==null;onClicked:{var stop=controller.next();if(stop)controller.navigate(stop);else message="남은 조사지가 없습니다.";}}
                Label {objectName:"visitGuidanceLabel";text:"방문 순서대로 이동하고, 조사를 마친 지점을 체크하세요.";wrapMode:Text.Wrap;Layout.fillWidth:true}
                Repeater {
                    model:panel.stops
                    delegate:RowLayout {
                        required property var modelData
                        required property int index
                        CheckBox {id:completionBox;text:(modelData.sequence||"")+". "+modelData.name+" · "+panel.completionState(modelData,index);checked:modelData.completed;enabled:panel.completionEnabled(modelData,index);Accessible.description:enabled?"":"다음 방문 지점부터 순서대로 완료하세요.";onClicked:controller.complete(modelData.site_id,checked)}
                        Button {objectName:"blockedCompletionAction";property string siteId:String(modelData.site_id);visible:panel.candidate===null&&panel.route!==null&&!panel.completionEnabled(modelData,index)&&!modelData.completed;text:"다음 방문 지점부터 순서대로 완료하세요.";flat:true;Layout.fillWidth:true;Accessible.name:completionBox.text+". "+text;contentItem:Label{text:parent.text;wrapMode:Text.Wrap;horizontalAlignment:Text.AlignLeft} onClicked:controller.complete(modelData.site_id,true)}
                    }
                }
            }
        }
    }
}
