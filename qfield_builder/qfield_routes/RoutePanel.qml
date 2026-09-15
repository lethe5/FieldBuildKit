import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.qgis
import org.qfield
import org.qfield.core
import org.qfield.gui
import "controller.js" as Controller
import "geometry.js" as Geometry
import "repository.js" as Repository
import "backend.js" as Backend
import "navigation.js" as Navigation

Rectangle {
    id: panel
    objectName: "qpbSurveyRoutePanel"
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
    property var canvas: null
    property string defaultLayer: "site"
    property var layerAliases: ({site:"조사지"})
    property string defaultId: "site_id"
    property string defaultName: "site_name"
    color: "#f8fafc"
    border.color: "#94a3b8"
    height: expanded ? Math.min(parent.height * 0.72, 640) : 44
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    z: 100

    QfExpressionEvaluator { id: evaluator; project: qgisProject }
    QfFeatureModel { id: completionFeature; project: qgisProject }
    QfAttributeFormModel { id: completionForm; featureModel: completionFeature }
    Component { id: timeoutFactory; Timer {} }
    Component {
        id: roadFactory
        QfLinePolygon {
            property var storedGeometry: null
            mapSettings: panel.canvas.mapSettings
            geometry: QfGeometryWrapper { qgsGeometry: storedGeometry; crs: panel.canvas.mapSettings.destinationCrs }
            color: "#1769e0"
            lineWidth: 4
        }
    }
    property var roadItem: null
    function updateView() {
        if (!controller) return;
        var state=controller.state;
        route=controller.active(); candidate=state.candidate; stops=(candidate||route) ? (candidate||route).stops : state.listed;
        savedRoutes=state.snapshot ? state.snapshot.data.routes : [];
        message=state.message;busy=state.busy;
        completedCount=route ? route.stops.filter(function(s){return s.completed;}).length : 0;
        var road=(candidate||route) && (candidate||route).road_geometry;
        if(roadItem) {roadItem.destroy();roadItem=null;}
        if(road && canvas) {
            var wkt=Geometry.lineWkt(road.coordinates);
            var geom=evaluator.evaluate("transform(geom_from_wkt("+Geometry.literal(wkt)+"), 'EPSG:4326', @project_crs)");
            roadItem=roadFactory.createObject(canvas,{storedGeometry:geom});
        }
    }
    function layerFor(mapping) {
        var layer=typeof qgisProject.mapLayer === "function" ? qgisProject.mapLayer(mapping.layer) : null;
        if(layer) return layer;
        var name=layerAliases[mapping.layer] || mapping.layer;
        var matches=typeof qgisProject.mapLayersByName === "function" ? qgisProject.mapLayersByName(name) : [];
        if(matches.length===1) return matches[0];
        throw new Error("대상 레이어를 찾지 못했습니다. 레이어 이름 또는 ID를 설정하세요.");
    }
    function records(mapping,scope) {
        var layer=layerFor(mapping), features=[];
        if(scope==="selected") {
            var host=iface.findItemByObjectName("featureForm"), model=host && host.model;
            if(model && model.selectedLayer===layer) features=model.selectedFeatures || [];
        } else {
            var iterator=QfLayerUtils.createFeatureIterator(layer);
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
        var layer=layerFor(mapping), iterator=QfLayerUtils.createFeatureIterator(layer), found=null;
        try {while(iterator.hasNext()) {var feature=iterator.next();evaluator.layer=layer;evaluator.feature=feature;if(String(evaluator.evaluate("attribute($currentfeature,"+Geometry.literal(mapping.id)+")"))===id) {found=feature;break;}}} finally {iterator.close();}
        if(!found) throw new Error("완료 상태를 변경할 대상을 찾지 못했습니다.");
        completionFeature.currentLayer=layer;completionFeature.feature=found;
        completionForm.applyFeatureModel();
        if(!completionForm.changeAttribute(mapping.completed,value) || !completionForm.save()) throw new Error("완료 필드를 저장하지 못했습니다. 편집 권한과 필드 형식을 확인하세요.");
    }
    function transport(request) {
        return new Promise(function(resolve,reject) {
            var xhr=new XMLHttpRequest(), finished=false;
            var timer=timeoutFactory.createObject(panel,{interval:request.timeout_ms,repeat:false});
            function end(error,value) {if(finished)return;finished=true;timer.stop();timer.destroy();if(error)reject(error);else resolve(value);}
            timer.triggered.connect(function(){end(new Error("도로 서버 응답 시간이 초과되었습니다."));xhr.abort();});
            xhr.onreadystatechange=function() {
                if(xhr.readyState!==XMLHttpRequest.DONE || finished)return;
                if(xhr.status<200 || xhr.status>=300) {end(new Error("도로 서버 요청 실패 (HTTP "+xhr.status+"). 연결 및 인증 설정을 확인하세요."));return;}
                try {end(null,JSON.parse(xhr.responseText));}catch(e){end(new Error("도로 서버 응답을 해석할 수 없습니다."));}
            };
            xhr.open(request.method,request.url);
            Object.keys(request.headers).forEach(function(k){xhr.setRequestHeader(k,request.headers[k]);});
            timer.start();xhr.send(JSON.stringify(request.body));
        });
    }
    function applyControls() {
        controller.state.mapping={layer:layerEdit.text,id:idEdit.text,name:nameEdit.text,completed:completionEdit.text};
        controller.state.scope=["selected","all","uncompleted"][scopeCombo.currentIndex];
        controller.state.startMode=["gps","map","target","saved_default"][startCombo.currentIndex];
        controller.state.targetStart=targetEdit.text;controller.state.roundtrip=roundtripBox.checked;
        controller.configure({server_url:serverEdit.text,optimizer_url:optimizerEdit.text,backend:backendEdit.text,profile:profileEdit.text,key:keyEdit.text,timeout_ms:Number(timeoutEdit.text),max_road_offset_m:Number(offsetEdit.text),objective:objectiveCombo.currentIndex===0?"time":"distance"});
    }
    function syncMapping() {
        var m=controller.state.mapping;
        layerEdit.text=m.layer;idEdit.text=m.id;nameEdit.text=m.name;completionEdit.text=m.completed;
    }
    function selectRoute(id) {if(controller.select(id)) syncMapping();}
    function pickMapStart() {
        if(!canvas || !canvas.mapSettings) throw new Error("지도 중심 위치를 확인할 수 없습니다.");
        var p=canvas.mapSettings.getCenter(true);
        var point=JSON.parse(evaluator.evaluate("geom_to_geojson(transform(make_point("+p.x+","+p.y+"), @project_crs, 'EPSG:4326'),17)"));
        controller.state.mapStart=Geometry.coordinate(point.coordinates);
        startCombo.currentIndex=1;message="지도 중심을 출발지로 지정했습니다.";
    }
    function calculate(remaining) {try {applyControls();controller.calculate(remaining);}catch(e){controller.error(e);}}
    Component.onCompleted: {
        canvas=iface.findItemByObjectName("mapCanvas");
        try {
            var directory=String(evaluator.evaluate("@project_folder"));
            controller=Controller.create({geometry:Geometry,repository:Repository,backend:{calculate:function(s,t,o,r,x){var provider=panel.routingBackends[s.backend];return provider ? provider.calculate(s,t,o,r,x) : Promise.reject(new Error("지원하지 않는 경로 backend입니다."));}},navigation:Navigation,
                base:directory+"/survey-routes",io:{exists:QfFileUtils.fileExists,read:QfFileUtils.readFileContent,write:QfFileUtils.writeFileContent},
                features:records,setCompleted:setCompleted,transport:transport,openUrl:function(url){return panel.urlLauncher(url);},
                gps:function(){var p=iface.findItemByObjectName("positionSource"), info=p && p.positionInformation;if(!p || !p.active || !info || !info.latitudeValid || !info.longitudeValid)throw new Error("GPS 위치가 없습니다. 위치 수신 후 다시 계산하세요.");return [info.longitude,info.latitude];},
                uuid:function(){return String(evaluator.evaluate("uuid('WithoutBraces')"));},changed:updateView});
            if(!controller.active() && !controller.state.snapshot.data.settings.mapping) controller.state.mapping={layer:defaultLayer,id:defaultId,name:defaultName,completed:""};
            syncMapping();
            var s=controller.state.settings;serverEdit.text=s.server_url;optimizerEdit.text=s.optimizer_url;backendEdit.text=s.backend;profileEdit.text=s.profile;timeoutEdit.text=String(s.timeout_ms);offsetEdit.text=String(s.max_road_offset_m);
            updateView();
        } catch(e) {message=String(e.message||e);}
    }
    Component.onDestruction: {if(roadItem)roadItem.destroy();}
    Timer {interval:1500;repeat:true;running:controller!==null && expanded && !busy;onTriggered:{try{controller.refresh();}catch(e){controller.error(e);}}}
    ColumnLayout {
        anchors.fill:parent;spacing:4
        Button {Layout.fillWidth:true;Layout.preferredHeight:40;text:(panel.expanded?"▾ ":"▸ ")+(panel.route?panel.route.name:"조사 경로")+" · "+panel.completedCount+"/"+(panel.route?panel.route.stops.length:0);onClicked:panel.expanded=!panel.expanded}
        ScrollView {
            visible:panel.expanded;Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            ColumnLayout {
                width:parent.width;spacing:6
                Label {text:"대상 · 선택은 QField 목록의 체크된 피처를 사용합니다";wrapMode:Text.Wrap;Layout.fillWidth:true}
                TextField {id:layerEdit;objectName:"layerEdit";Layout.fillWidth:true;placeholderText:"대상 레이어 이름 / ID";text:panel.defaultLayer}
                RowLayout {TextField{id:idEdit;objectName:"idEdit";Layout.fillWidth:true;placeholderText:"ID 필드";text:panel.defaultId} TextField{id:nameEdit;objectName:"nameEdit";Layout.fillWidth:true;placeholderText:"이름 필드";text:panel.defaultName}}
                TextField {id:completionEdit;objectName:"completionEdit";Layout.fillWidth:true;placeholderText:"완료 Boolean 필드 (비우면 경로별 완료)"}
                ComboBox {id:scopeCombo;objectName:"scopeCombo";model:["선택 대상","전체 대상","미조사 대상"];Layout.fillWidth:true}
                ComboBox {id:startCombo;objectName:"startCombo";model:["현재 GPS 출발","지도 위치 출발","조사대상 출발","저장 기본 출발지"];Layout.fillWidth:true}
                Button {text:"지도 중심을 출발지로 지정";onClicked:{try{pickMapStart();}catch(e){controller.error(e);}}}
                TextField {id:targetEdit;objectName:"targetEdit";Layout.fillWidth:true;placeholderText:"출발 조사대상 ID"}
                Button {text:"지정 위치를 기본 출발지로 저장";onClicked:{try{controller.saveDefault(controller.state.mapStart);}catch(e){controller.error(e);}}}
                CheckBox {id:roundtripBox;objectName:"roundtripBox";text:"출발지로 복귀";checked:true}
                Label {text:"도로 서버 설정 · 키는 이번 세션에서만 사용"}
                TextField {id:serverEdit;objectName:"serverEdit";Layout.fillWidth:true;placeholderText:"ORS 서버 URL"}
                TextField {id:optimizerEdit;objectName:"optimizerEdit";Layout.fillWidth:true;placeholderText:"VROOM v1.14 서버 URL"}
                TextField {id:backendEdit;objectName:"backendEdit";Layout.fillWidth:true;placeholderText:"경로 backend ID"}
                TextField {id:profileEdit;objectName:"profileEdit";Layout.fillWidth:true;placeholderText:"ORS profile"}
                TextField {id:keyEdit;objectName:"keyEdit";Layout.fillWidth:true;placeholderText:"API 키 (저장하지 않음)";echoMode:TextInput.Password}
                RowLayout {TextField{id:timeoutEdit;objectName:"timeoutEdit";Layout.fillWidth:true;placeholderText:"제한시간(ms)"} TextField{id:offsetEdit;objectName:"offsetEdit";Layout.fillWidth:true;placeholderText:"도로 이격거리(m)"}}
                ComboBox {id:objectiveCombo;objectName:"objectiveCombo";model:["시간 최소화","거리 최소화"]}
                Button {text:"서버 설정 저장 (키 제외)";onClicked:{try{applyControls();controller.saveSettings();}catch(e){controller.error(e);}}}
                RowLayout {Button{text:"새 경로 계산";enabled:controller!==null&&!busy;onClicked:calculate(false)} Button{text:"남은 지점 계산";enabled:controller!==null&&!busy&&route!==null;onClicked:calculate(true)}}
                Label {text:panel.message;Layout.fillWidth:true;wrapMode:Text.Wrap}
                Label {text:(candidate||route)?"거리 "+(candidate||route).distance_m+" m / 시간 "+(candidate||route).duration_s+" s":"결과 없음"}
                Label {objectName:"availabilityLabel";text:((candidate||route)&&(candidate||route).road_geometry?"도로선 제공":"도로선 없음")+" · "+((candidate||route)&&(candidate||route).eta?"ETA 제공 (출발 기준 초)":"ETA 미제공")+" · "+((candidate||route)&&(candidate||route).legs?"구간 값 제공":"구간 값 미제공");Layout.fillWidth:true;wrapMode:Text.Wrap}
                TextField {id:routeName;objectName:"routeName";Layout.fillWidth:true;placeholderText:"저장할 경로 이름"}
                Button {text:"계산 결과 저장";enabled:candidate!==null;onClicked:controller.save(routeName.text)}
                ComboBox {id:savedCombo;objectName:"savedCombo";Layout.fillWidth:true;model:panel.savedRoutes;textRole:"name"}
                Button {text:"저장 경로 불러오기";enabled:savedCombo.currentIndex>=0;onClicked:selectRoute(panel.savedRoutes[savedCombo.currentIndex].route_id)}
                Button {text:"다음 지점 네이버지도 안내";enabled:controller!==null&&route!==null;onClicked:{var stop=controller.next();if(stop)controller.navigate(stop);else message="남은 조사대상이 없습니다.";}}
                Repeater {
                    model:panel.stops
                    delegate:RowLayout {
                        required property var modelData
                        CheckBox {text:(modelData.sequence||"")+". "+modelData.name;checked:modelData.completed;enabled:!panel.candidate&&panel.route!==null;onClicked:controller.complete(modelData.site_id,checked)}
                    }
                }
            }
        }
    }
}
