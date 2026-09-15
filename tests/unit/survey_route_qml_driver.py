"""Execute generated RoutePanel in Qt; inject only QField, HTTP, file faults and OS boundaries."""
import json, os, sys, uuid, re, time, threading, shutil
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_CONTROLS_STYLE']='Basic'
os.environ['QT_QPA_FONTDIR']='C:/Windows/Fonts'
from PySide6.QtCore import QObject, Slot, QUrl, QMetaObject, Qt, QPointF, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent, QQmlNetworkAccessManagerFactory
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtQuick import QQuickWindow

payload=json.load(sys.stdin);case=payload['case'];folder=Path(payload['project_dir']);op=case['operation']
requests=[];provider_dispatches=[];transport_dispatches=[];logs=[];transitions=[];writes=[];expression_calls=[];evaluator_writes=[];fault='';geometry_fault='';completion_fault='';storage_fault='';launched=[];use_case_responses=False
features=case.get('features',[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(3)])
if op=='generated_geometry_calculate':features=[{'id':'generated','name':'생성 경로 대상','xy':[127,37]}]
gps=case.get('gps',[127,37]);map_center=[128,38];response=case.get('response',{})
def detached(x):return json.loads(json.dumps(x))
def case_shape():
    if op!='generated_geometry_calculate' or not case.get('wkt'):return None
    from qfield_builder.wkt import geometry_data
    kind,coordinates=geometry_data(case['wkt'])
    names={name.upper():name for name in ('Point','LineString','Polygon','MultiPoint','MultiLineString','MultiPolygon')}
    return {'type':names[kind], 'coordinates':coordinates}
generated_shape=case_shape()
def representative_xy(shape):
    coords=shape['coordinates'];weighted=[]
    def line(points):
        for a,b in zip(points,points[1:]):
            w=((b[0]-a[0])**2+(b[1]-a[1])**2)**.5
            if w:weighted.append(((a[0]+b[0])/2,(a[1]+b[1])/2,w))
    def polygon(rings):
        for index,ring in enumerate(rings):
            area=x=y=0
            for a,b in zip(ring,ring[1:]):
                cross=a[0]*b[1]-b[0]*a[1];area+=cross;x+=(a[0]+b[0])*cross;y+=(a[1]+b[1])*cross
            if not area:raise ValueError('degenerate polygon')
            weighted.append((x/(3*area),y/(3*area),abs(area)*(1 if index==0 else -1)))
    if shape['type']=='Point':return coords[:2]
    if shape['type']=='MultiPoint':weighted.extend((p[0],p[1],1) for p in coords)
    elif shape['type']=='LineString':line(coords)
    elif shape['type']=='MultiLineString':
        for points in coords:line(points)
    elif shape['type']=='Polygon':polygon(coords)
    elif shape['type']=='MultiPolygon':
        for rings in coords:polygon(rings)
    total=sum(v[2] for v in weighted)
    return [sum(v[0]*v[2] for v in weighted)/total,sum(v[1]*v[2] for v in weighted)/total]
class HTTP(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        url=self.headers['X-Original-Url']
        kind='matrix' if 'locations' in body else 'optimizer' if 'jobs' in body else 'directions'
        headers={'Content-Type':self.headers.get('Content-Type','')}
        if self.headers.get('Authorization') is not None:headers['Authorization']=self.headers['Authorization']
        req={'kind':kind,'url':url,'method':'POST','body':body,'headers':headers}
        requests.append(req);logs.append('HTTP '+req['url'])
        if fault in ('timeout','network','status_0') and (op!='remaining' or 'jobs' in body):
            if fault=='timeout':time.sleep(.15)
            self.close_connection=True;return
        if fault.startswith('http_'):
            self.send_response(int(fault[5:]));self.end_headers();self.wfile.write(('failure '+case.get('key','')).encode());return
        if fault=='truncated_json':out=b'{"durations":'
        else:
            if 'locations' in body:
                n=len(body['locations']);times=[[0 if i==j else 10+abs(i-j) for j in range(n)] for i in range(n)];distances=[[0 if i==j else 100+abs(i-j) for j in range(n)] for i in range(n)]
                value={'durations':detached(case.get('time_matrix',times)),'distances':detached(case.get('distance_matrix',distances)),'sources':[{'snapped_distance':0} for _ in range(n)]}
                if fault=='null_matrix':value['durations']=None
                if fault=='disconnected':value['durations'][0][1]=None
                if fault=='off_road':value['sources'][1]['snapped_distance']=10001
            elif 'jobs' in body:
                jobs=body['jobs']
                if use_case_responses and 'optimizer_response' in case:
                    value=detached(case['optimizer_response'])
                else:
                    order=response.get('order',case.get('backend_order',[j['description'] for j in jobs]))
                    steps=[{'type':'job','id':next((j['id'] for j in jobs if j['description']==id),999)} for id in order]
                    arrivals=response.get('arrivals')
                    if arrivals is not None:
                        for step,arrival in zip(steps,arrivals):step['arrival']=arrival
                    if fault=='duplicate_stop':steps[1]=steps[0]
                    if fault=='unknown_stop':steps[0]['id']=999
                    if fault=='missing_stop':steps.pop()
                    value={'code':0,'unassigned':[jobs[0]] if fault=='unassigned' else [],'routes':[{'steps':[{'type':'start','arrival':0}]+steps+[{'type':'end','arrival':response.get('duration_s',456)}],'distance':-1 if fault=='negative_distance' else response.get('distance_m',1234),'duration':None if fault=='nonfinite_time' else response.get('duration_s',456)}]}
            else:
                if use_case_responses and case.get('directions_response') is not None:
                    value=detached(case['directions_response'])
                else:
                    road=case.get('road_geometry',response.get('road_geometry'));legs=response.get('legs')
                    if fault=='leg_count':legs=[{'distance_m':10,'duration_s':10}]
                    value={'features':[{'geometry':road,'properties':{'segments':[{'distance':v['distance_m'],'duration':v['duration_s']} for v in legs] if legs else None}}] if road or legs else []}
            out=json.dumps(value).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        try:self.wfile.write(out)
        except (BrokenPipeError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),HTTP);threading.Thread(target=server.serve_forever,daemon=True).start()
class Network(QNetworkAccessManager):
    def createRequest(self,operation,request,outgoingData=None):
        if request.url().scheme() in ('http','https'):
            original=request.url().toString();request=QNetworkRequest(request);request.setRawHeader(b'X-Original-Url',original.encode());request.setUrl(QUrl('http://127.0.0.1:'+str(server.server_port)+'/'))
        return super().createRequest(operation,request,outgoingData)
class Factory(QQmlNetworkAccessManagerFactory):
    def create(self,parent):return Network(parent)
class Boundary(QObject):
    @Slot(str,'QVariant',result='QVariant')
    def evaluate(self,text,feature):
        expression_calls.append({'expression_text':text,'arity':1})
        if text=='@project_folder':return str(folder)
        if text=='@fieldbuild_route_api_key':
            import xml.etree.ElementTree as ET
            root=ET.parse(next(folder.glob('*.qgs'))).getroot()
            names=[v.text or '' for v in root.findall('./properties/Variables/variableNames/value')]
            values=[v.text or '' for v in root.findall('./properties/Variables/variableValues/value')]
            return dict(zip(names,values)).get('fieldbuild_route_api_key','')
        if text.startswith('uuid('):return str(uuid.uuid4())
        if hasattr(feature,'toVariant'):feature=feature.toVariant()
        if text=='is_valid($geometry)':return True
        if text=='geometry_type($geometry)':return feature['geometry']['type'].removeprefix('Multi').replace('LineString','Line')
        if text=='is_multipart($geometry)':return feature['geometry']['type'].startswith('Multi')
        if text=='geom_to_geojson($geometry,17)':return json.dumps(feature['geometry'])
        if text.startswith('attribute('):return feature['attributes'].get(re.search(r",'(.*)'\)",text)[1].replace("''","'"))
        if text.startswith(('x(transform(', 'y(transform(')):
            if geometry_fault:
                raise ValueError(geometry_fault)
            if 'make_point(' in text:
                m=re.search(r'make_point\(([^,]+),([^\)]+)\)',text);point=[float(m[1]),float(m[2])]
            else:point=representative_xy(feature['geometry'])
            source=case.get('crs','EPSG:4326') if '@layer_crs' in text else 'EPSG:4326'
            if source!='EPSG:4326':
                from rasterio.warp import transform
                xs,ys=transform(source,'EPSG:4326',[point[0]],[point[1]]);point=[xs[0],ys[0]]
            return point[0] if text.startswith('x(') else point[1]
        if 'geom_from_wkt(' in text:return {'type':'LineString','coordinates':[[float(v) for v in p.split()] for p in re.search(r'LINESTRING\(([^\)]+)\)',text)[1].split(',')]}
        raise ValueError(text)
    @Slot(str,result=bool)
    def exists(self,p):return Path(p).is_file()
    @Slot(str,result=str)
    def read(self,p):
        if not Path(p).exists():return ''
        logs.append('read '+Path(p).name);return Path(p).read_text(encoding='utf8')
    @Slot(str,str,result=bool)
    def write(self,p,text):
        target=Path(p)
        if not target.resolve().is_relative_to(folder.resolve()):raise ValueError('outside fixture')
        ok=storage_fault not in ('partial_write','storage_full')
        if storage_fault!='storage_full':target.write_text(text[:len(text)//2] if storage_fault=='partial_write' else text,encoding='utf8')
        writes.append({'path':str(target),'ok':ok,'bytes':target.read_text(encoding='utf8') if target.exists() else None});logs.append('write '+target.name+' '+str(ok));return ok
    @Slot(str,bool,result=bool)
    def complete(self,id,value):
        if completion_fault:return False
        field=state()['mapping']['completed'];mapping=state()['mapping']
        for f in features:
            if str(f.get(mapping['id'],f.get('id')))==id:f[field]=value;device_inputs();return True
        return False
    @Slot(str,result=bool)
    def launch(self,url):launched.append(url);return case.get('launch_result',True)
    @Slot(str,str)
    def providerEntry(self,provider,s):
        settings=json.loads(s)
        provider_dispatches.append({'backend':provider,'max_road_offset_m':settings.get('max_road_offset_m')})
    @Slot(str)
    def transportEntry(self,s):transport_dispatches.append(json.loads(s))
    @Slot(str)
    def changed(self,s):transitions.append(json.loads(s))
    @Slot(str)
    def evaluatorWrite(self,name):evaluator_writes.append(name)
app=QGuiApplication([]);engine=QQmlEngine();factory=Factory();engine.setNetworkAccessManagerFactory(factory)
window=QQuickWindow();window.resize(800,900);boundary=Boundary();engine.rootContext().setContextProperty('boundaryHost',boundary)
stubs=folder/'host-fixture'
def put(module,name,text):
    target=stubs/module.replace('.','/');target.mkdir(parents=True,exist_ok=True);(target/name).write_text(text,encoding='utf8')
put('org.qfield','qmldir','module org.qfield\nQfToolButton 1.0 QfToolButton.qml\n')
put('org.qfield','QfToolButton.qml','import QtQuick.Controls\nToolButton {}')
put('org.qfield.core','qmldir','module org.qfield.core\nQfFeatureModel 1.0 QfFeatureModel.qml\nQfLinePolygon 1.0 QfLinePolygon.qml\nQfGeometryWrapper 1.0 QfGeometryWrapper.qml\nsingleton QfLayerUtils 1.0 QfLayerUtils.qml\nsingleton QfFileUtils 1.0 QfFileUtils.qml\nsingleton QfFeatureUtils 1.0 QfFeatureUtils.qml\n')
put('org.qfield.core','QfFeatureModel.qml','import QtQml\nQtObject {property var project;property var currentLayer;property var feature}')
put('org.qfield.core','QfLinePolygon.qml','import QtQuick\nItem {property var mapSettings;property var geometry;property color color;property real lineWidth}')
put('org.qfield.core','QfGeometryWrapper.qml','import QtQml\nQtObject {property var qgsGeometry;property var crs}')
put('org.qfield.core','QfFileUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function fileExists(p){return boundaryHost.exists(p)} function readFileContent(p){return boundaryHost.read(p)} function writeFileContent(p,t){return boundaryHost.write(p,t)}}')
put('org.qfield.core','QfLayerUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createFeatureIterator(layer){var rows=fixtureFeatures, i=0;return {hasNext:function(){return i<rows.length},next:function(){return rows[i++]},close:function(){}}}}')
put('org.qfield.core','QfFeatureUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createBlankFeature(){return ({})} function attributeIsNull(value){return value===null || value===undefined}}')
put('org.qfield.gui','qmldir','module org.qfield.gui\nQfExpressionEvaluator 1.0 QfExpressionEvaluator.qml\nQfAttributeFormModel 1.0 QfAttributeFormModel.qml\n')
put('org.qfield.gui','QfExpressionEvaluator.qml','import QtQml\nQtObject {property var project;property var layer;property var feature:null;onProjectChanged:boundaryHost.evaluatorWrite("project");onLayerChanged:boundaryHost.evaluatorWrite("layer");onFeatureChanged:boundaryHost.evaluatorWrite("feature");function evaluate(text){return boundaryHost.evaluate(text,feature)}}')
put('org.qfield.gui','QfAttributeFormModel.qml','import QtQml\nQtObject {property var featureModel;property bool result:false;function applyFeatureModel(){} function save(){return result} function changeAttribute(field,value){result=boundaryHost.complete(String(featureModel.feature.attributes.site_id||featureModel.feature.attributes.custom_id),value);return result}}')
put('org.qgis','qmldir','module org.qgis\nDummy 1.0 Dummy.qml\n');put('org.qgis','Dummy.qml','import QtQml\nQtObject {}')
engine.addImportPath(str(stubs));engine.rootContext().setContextProperty('fixtureFeatures',[])
# IDs and display names come from the generated .qgs, never from the selected mapping.
import xml.etree.ElementTree as ET
layers=[{'id':l.findtext('id'),'name':l.findtext('layername')} for l in ET.parse(next(folder.glob('*.qgs'))).findall('./projectlayers/maplayer')]
route_defaults={'surveyType':case.get('survey_type','temporary_plots')}
layers.append({'id':'custom_7e04','name':'custom_targets'})
def js(code):
    v=engine.evaluate(code)
    if v.isError():raise RuntimeError(v.toString()+' '+v.property('stack').toString())
    return v
engine.globalObject().setProperty('boundaryHost',engine.newQObject(boundary))
js('var hostLayers='+json.dumps(layers)+';var qgisProject={mapLayer:function(id){return hostLayers.find(function(l){return l.id===id})||null},mapLayersByName:function(name){return hostLayers.filter(function(l){return l.name===name})}};var device={};')
engine.rootContext().setContextProperty('qgisProject',js('qgisProject'))
canvas_component=QQmlComponent(engine);canvas_component.setData(b'import QtQuick\nItem {property var mapSettings}',QUrl());host_canvas=canvas_component.create();host_canvas.setParentItem(window.contentItem());host_canvas.setWidth(640);host_canvas.setHeight(480);engine.globalObject().setProperty('hostCanvas',engine.newQObject(host_canvas))
class Iface(QObject):
    @Slot(str,result='QVariant')
    def findItemByObjectName(self,name):
        if name=='mapCanvas':return js('device.canvas')
        if name=='positionSource':return js('device.gps')
        if name=='coordinateLocator':return js('device.locator')
        if name=='featureForm':return js('device.form')
        return None
iface=Iface();engine.rootContext().setContextProperty('iface',iface)
qInstallMessageHandler(lambda typ,ctx,msg:logs.append(str(msg)))
component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));panel=None;components=[component]
def device_inputs():
    rows=[{'attributes':{'site_id':f.get('id'),'site_name':f.get('name'),'inventory_id':f.get('id'),'selected_korean_name':f.get('name'),**f},'geometry':generated_shape or {'type':'Point','coordinates':f['xy']}} for f in features]
    engine.rootContext().setContextProperty('fixtureFeatures',rows)
    selected=[r for r in rows if 'selected_ids' not in case or str(r['attributes'].get('id',r['attributes'].get('custom_id'))) in case['selected_ids']]
    js('device.canvas=hostCanvas;hostCanvas.mapSettings={destinationCrs:"EPSG:4326",getCenter:function(){return '+json.dumps({'x':map_center[0],'y':map_center[1]})+'}};device.gps='+json.dumps({'active':gps is not None,'positionInformation':{'latitudeValid':gps is not None,'longitudeValid':gps is not None,'longitude':gps[0] if gps else None,'latitude':gps[1] if gps else None}})+';device.locator={positionInformation:device.gps.positionInformation};device.form={model:{selectedLayer:qgisProject.mapLayersByName('+json.dumps('custom_targets' if case.get('mapping') else '조사지')+')[0],selectedFeatures:'+json.dumps(selected)+'}};')
def val(expr):return js('JSON.stringify('+expr+')').toString()
def state():return json.loads(val('p.controller.state'))
def active():return json.loads(val('p.controller.active()'))
def control(name,value,prop='text'):
    obj=panel.findChild(QObject,name)
    if obj is None:raise RuntimeError('missing control '+name)
    obj.setProperty(prop,value)
def click(text):
    candidates=[o for o in panel.findChildren(QObject) if o.property('text')==text]
    if not candidates:raise RuntimeError('missing button '+text)
    if not QMetaObject.invokeMethod(candidates[0],'clicked',Qt.DirectConnection):raise RuntimeError('click failed '+text)
    drain()
def drain():
    end=time.monotonic()+5
    while True:
        app.processEvents()
        if not panel or panel.property('controller') is None or not state()['busy']:
            app.processEvents();break
        if time.monotonic()>end:raise RuntimeError('QML action did not settle')
        time.sleep(.001)
def wait_for(predicate, timeout=2):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        app.processEvents()
        if predicate():return
        time.sleep(.005)
    raise RuntimeError('QML observation did not settle')
def open_panel():
    global panel
    device_inputs()
    if panel:panel.deleteLater();app.processEvents()
    panel=component.createWithInitialProperties({"parent":window.contentItem(),**route_defaults})
    if not panel:raise RuntimeError(str([e.toString() for e in component.errors()]))
    panel.setParentItem(window.contentItem());engine.globalObject().setProperty('p',engine.newQObject(panel));drain()
    if panel.property('controller') is None:return
    js('p.urlLauncher=function(url){return boundaryHost.launch(url)};var realProvider=p.routingBackends["ors-vroom"];p.routingBackends={"ors-vroom":{calculate:function(s,t,o,r,x){boundaryHost.providerEntry("ors-vroom",JSON.stringify(s));return realProvider.calculate(s,t,o,r,function(request){boundaryHost.transportEntry(JSON.stringify(request));return x(request)})}}};p.controller.state;')
    # Observe the selected provider and each request where production hands it to transport.
    panel.property('message')
    panel.messageChanged.connect(lambda:logs.append(str(panel.property('message'))))
    panel.routeChanged.connect(lambda:transitions.append(active()))
def settings(values=None, seed_defaults=True):
    defaults={'optimizer_url':'https://vroom.invalid'} if seed_defaults else {}
    if seed_defaults and not case.get('use_project_key'):defaults['key']=case.get('key','')
    values=defaults | (values or {})
    names={'server_url':'serverEdit','optimizer_url':'optimizerEdit','backend':'backendEdit','key':'keyEdit','profile':'profileEdit','timeout_ms':'timeoutEdit','max_road_offset_m':'offsetEdit'}
    for k,v in values.items():
        if k in names:control(names[k],str(v))
    if 'objective' in values:control('objectiveCombo',0 if values['objective']=='time' else 1,'currentIndex')
def calculate(remaining=False):
    device_inputs();click('남은 지점 계산' if remaining else '새 경로 계산');return state()['candidate'] is not None
def save(name='기존 경로'):
    control('routeName',name);js('var originalSave=p.controller.save;var saveResult=null;p.controller.save=function(name){saveResult=originalSave(name);return saveResult}')
    click('계산 결과 저장');js('p.controller.save=originalSave');return js('saveResult').toBool()

def stored():
    # Independent physical read: production readSlot validates every candidate file.
    js("var storeProbe=(function(){"+(folder/'qfield_routes/repository.js').read_text(encoding='utf8')+";return {readSlot:readSlot};})();")
    records=[]
    for f in folder.glob('survey-routes.*.json'):
        r=json.loads(val('storeProbe.readSlot({exists:function(p){return boundaryHost.exists(p)},read:function(p){return boundaryHost.read(p)}},'+json.dumps(str(f))+')'))
        if r:records.append(r)
    return max(records,key=lambda r:r['revision'])['data'] if records else None
def seed_inactive_saved_fixture():
    source=(folder/'qfield_routes/repository.js').read_text(encoding='utf8')
    js("var seedRepository=(function(){"+source+";return {save:save};})();")
    row=features[0];route={'route_id':'seeded-route','name':'기존 경로','created_at':'2026-09-15T00:00:00Z',
        'backend':'ors-vroom','status':'ready','revision':1,'start':[127,37],'end':[127,37],
        'distance_m':1,'duration_s':1,'stops':[{'site_id':str(row.get('id','seed')),'source_layer':'site',
        'name':str(row.get('name','기존 대상')),'sequence':1,'completed':False,'coordinate':row.get('xy',[127,37])}],
        'road_geometry':None,'legs':None,'eta':None,'eta_basis':None,'optimality_guaranteed':False}
    data={'schema':1,'active_id':'','routes':[route],'settings':{}}
    js("seedRepository.save({exists:function(p){return boundaryHost.exists(p)},read:function(p){return boundaryHost.read(p)},write:function(p,t){return boundaryHost.write(p,t)}},"+json.dumps(str(folder/'survey-routes'))+","+json.dumps(data)+",0)")
def saved():
    data=stored();return data['routes'] if data else []

def disk():
    records=[]
    for f in folder.glob('survey-routes.*.json'):
        try:
            data=json.loads(f.read_text(encoding='utf8'));records.append(data)
        except ValueError:pass
    return records

def load(index):control('savedCombo',index,'currentIndex');click('저장 경로 불러오기')
def visual_objects(root):
    yield root
    if hasattr(root,'childItems'):
        for child in root.childItems():yield from visual_objects(child)
def complete(id):
    # Repeater CheckBox is the actual panel delegate; user selects it via its displayed order/name.
    stop=next(s for s in active()['stops'] if s['site_id']==id)
    text=str(stop['sequence'])+'. '+stop['name'];obj=next(o for o in visual_objects(panel) if o.property('text')==text)
    obj.setProperty('checked',True);QMetaObject.invokeMethod(obj,'clicked',Qt.DirectConnection);drain();device_inputs()
def observation():
    return {'candidate':state()['candidate'],'route':active(),'message':panel.property('message')}
def decoded_transport_settings():
    if not provider_dispatches and not transport_dispatches and not requests:return {}
    if len(provider_dispatches)!=1 or len(transport_dispatches)!=len(requests):raise RuntimeError('provider/transport observation mismatch')
    for dispatched,received in zip(transport_dispatches,requests):
        if dispatched['url']!=received['url'] or dispatched['method']!=received['method'] or dispatched['body']!=received['body']:raise RuntimeError('HTTP request differs from provider dispatch')
        for name,value in dispatched['headers'].items():
            actual=received['headers'].get(name)
            if name.lower()=='content-type':
                actual_media=(actual or '').split(';',1)[0].strip().lower()
                dispatched_media=str(value).split(';',1)[0].strip().lower()
                if actual_media!='application/json':raise RuntimeError('HTTP Content-Type must be application/json')
                actual,value=actual_media,dispatched_media
            if actual!=value:raise RuntimeError('HTTP header differs from provider dispatch')
    matrix=next(r for r in transport_dispatches if 'locations' in r['body'])
    optimizer=next(r for r in transport_dispatches if 'jobs' in r['body'])
    marker='/v2/matrix/'
    if marker not in matrix['url']:raise RuntimeError('matrix provider URL missing')
    server_url,profile=matrix['url'].rsplit(marker,1)
    matrices=optimizer['body']['matrices']['car'];costs=matrices['costs']
    if costs==matrices['distances'] and costs!=matrices['durations']:objective='distance'
    elif costs==matrices['durations'] and costs!=matrices['distances']:objective='time'
    else:raise RuntimeError('optimizer objective cannot be decoded')
    return {'server_url':server_url,'optimizer_url':optimizer['url'],'backend':provider_dispatches[0]['backend'],'profile':unquote(profile),'timeout_ms':matrix['timeout_ms'],'max_road_offset_m':provider_dispatches[0]['max_road_offset_m'],'objective':objective,'key':requests[0]['headers'].get('Authorization','')}
def main():
    global features,gps,map_center,fault,geometry_fault,completion_fault,storage_fault,folder,component,response,use_case_responses
    original_response=response;response={};original_gps=gps;gps=[127,37]
    type1_without_mapping=case.get('survey_type')=='simple_inventory' and not case.get('mapping')
    if type1_without_mapping:seed_inactive_saved_fixture()
    open_panel();settings();original=features
    if op!='mapping_settings_restart_move' and not type1_without_mapping:
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(len(original))]
        if not panel.property('defaultLayer'):
            for name,value in [('layerEdit','custom_targets'),('idEdit','inventory_id'),('nameEdit','selected_korean_name')]:control(name,value)
        control('scopeCombo',1,'currentIndex');calculate();save();features=original;response=original_response;gps=original_gps;device_inputs();requests.clear();provider_dispatches.clear();transport_dispatches.clear()
    use_case_responses=True
    if op=='completion_write_failure':
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,{'layer':'site','id':'id','name':'name','completed':'done'}[key])
        click('서버 설정 저장 (키 제외)');features=[dict(f,done=False) for f in original];device_inputs()
    before=saved();result={'saved_before':before,'active_before':state()['snapshot']['data']['active_id'],'project_dir':str(folder),'ok':True}
    if op in ('calculate','start','road_cost','calculate_failure','configured_calculate','result_roundtrip','geometry_failure','generated_geometry_calculate'):
        if case.get('mapping'):
            for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,case['mapping'][key])
        control('scopeCombo',['selected','all','uncompleted'].index(case.get('scope','all')),'currentIndex')
        if op=='start':
            mode=case['mode'];control('startCombo',['gps','map','target','saved_default'].index(mode),'currentIndex')
            if mode=='gps':gps=case['coordinate']
            elif mode=='map':map_center=case['coordinate'];device_inputs();panel.setProperty('canvas',js('device.canvas'));click('지도 중심을 출발지로 지정')
            elif mode=='target':features[0]['xy']=case['coordinate'];control('targetEdit',str(features[0]['id']))
            else:
                map_center=case['coordinate'];device_inputs();panel.setProperty('canvas',js('device.canvas'));click('지도 중심을 출발지로 지정');click('지정 위치를 기본 출발지로 저장');open_panel();settings();control('scopeCombo',1,'currentIndex');control('startCombo',3,'currentIndex')
        if op=='road_cost':settings({'objective':case['objective']})
        if op=='configured_calculate':
            if case.get('fresh_project'):open_panel()
            elif 'optimizer_url' not in case['settings']:control('optimizerEdit','')
            settings(case['settings'],False);click('서버 설정 저장 (키 제외)')
        if op=='calculate_failure':fault=case['fault'];settings({'timeout_ms':30})
        if op=='geometry_failure':geometry_fault=case['fault']
        if op=='generated_geometry_calculate':geometry_fault=case.get('fault','')
        result['ok']=calculate()
        if op=='result_roundtrip':
            if result['ok']:save('왕복 경로');open_panel()
            result['reloaded']=active();disk_state=stored();result['saved']=next((r for r in disk_state['routes'] if r['route_id']==disk_state['active_id']),None);text=panel.findChild(QObject,'availabilityLabel').property('text');result['availability']={k:v in text for k,v in [('eta','ETA 제공'),('legs','구간 값 제공'),('road_geometry','도로선 제공')]}
        result['candidate']=state()['candidate'];result['listed_ids']=[s['site_id'] for s in state()['listed']]
        if op=='configured_calculate':
            result['transport_settings']=decoded_transport_settings();result['transport_headers']=detached([r['headers'] for r in requests]);result['persisted_settings']=detached(stored()['settings'])
        if op=='geometry_failure':
            result['published_features']=state()['candidate']['stops'] if state()['candidate'] else [];result['source_before']=detached(original);result['source_after']=detached(features)
        if op=='generated_geometry_calculate':
            result['failure_reason']=case.get('fault');result['generic_crs_error_shown']='원본 CRS와 WGS84' in str(panel.property('message'))
            result['expression_evaluator']={'native_type':'QfExpressionEvaluator','qml_type':'ExpressionEvaluator','properties_written':sorted(set(evaluator_writes)),'unknown_property_writes':[],'evaluate_calls':detached(expression_calls)}
            result['qml_errors']=[line for line in logs if 'file:///' in line]
    elif op=='save_two_restart_move':
        calculate();save('둘째 경로');result['selected_route_ids']=[]
        for i in range(len(saved())):load(i);result['selected_route_ids'].append(active()['route_id'])
        portable={**case['settings'],'key':case.get('key','')};settings(portable)
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,case['settings']['mapping'][key])
        map_center=case['settings']['default_start'];device_inputs();panel.setProperty('canvas',js('device.canvas'));click('지도 중심을 출발지로 지정');click('지정 위치를 기본 출발지로 저장');click('서버 설정 저장 (키 제외)')
        result['settings_before']=detached(stored()['settings']);result['saved_before']=saved();result['active_before']=active()['route_id'];result['old_dir']=str(folder);new=Path(str(folder)+'-moved');shutil.move(folder,new);folder=new;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));requests.clear();provider_dispatches.clear();transport_dispatches.clear();open_panel();result['project_dir']=str(folder);result['settings_after']=detached(stored()['settings']);result['session_key_present_after']=bool(state()['settings']['key'])
    elif op in ('complete','remaining','passive_action'):
        if op=='complete' and case.get('mapping'):
            mapping=case['mapping']
            for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,mapping.get(key,''))
            click('서버 설정 저장 (키 제외)')
        for id in case.get('completed_ids',[]):complete(id)
        if op=='complete':
            result['active']=active();open_panel();result['reloaded']=active();result['completed_count']=panel.property('completedCount');result['total_count']=len(panel.property('stops').toVariant());header=next(o.property('text') for o in visual_objects(panel) if str(o.property('text')).startswith(('▸ ','▾ ')));result['summary_counts']=[int(v) for v in header.rsplit(' · ',1)[1].split('/')]
            result['source_completion_after']={str(f.get('id')):True for f in features if f.get('done') is True} if case.get('source')=='field' else {}
        elif op=='remaining':
            result['saved_before']=active();result['completed_before']=[s for s in active()['stops'] if s['completed']]
            if case['outcome']=='failure':fault='timeout';settings({'timeout_ms':30})
            result['ok']=calculate(True)
            if case['outcome']=='save' and result['ok']:save();open_panel()
            result['saved_after']=active();result['completed_after']=[s for s in active()['stops'] if s['completed']]
        else:
            action=case['action']
            if action=='complete':complete('0')
            if action=='restart':open_panel()
            if action=='load':load(0)
            if action in ('expand','collapse'):
                button=next(o for o in panel.findChildren(QObject) if str(o.property('text')).startswith(('▸ ','▾ ')))
                if action=='collapse':QMetaObject.invokeMethod(button,'clicked',Qt.DirectConnection)
                QMetaObject.invokeMethod(button,'clicked',Qt.DirectConnection);drain()
            result['expanded']=panel.property('expanded')
        nxt=json.loads(val('p.controller.next()'));result['next_id']=nxt['site_id'] if nxt else None
    elif op=='completion_write_failure':
        result['source_completion_before']={str(f['id']):f['done'] for f in features}
        result['next_before']=json.loads(val('p.controller.next()'))['site_id'];completion_fault=case['fault'];complete(case['completed_id'])
        result['ok']=False;result['source_completion_after']={str(f['id']):f['done'] for f in features}
        result['next_after']=json.loads(val('p.controller.next()'))['site_id']
    elif op=='reopen_navigate':
        calculate();save('도로선');open_panel();requests.clear();provider_dispatches.clear();transport_dispatches.clear();result['rendered_geometry']=json.loads(val('p.roadItem.storedGeometry'))
        result['road_overlay']=json.loads(val('({parent_is_canvas:p.roadItem.parent===device.canvas,width:p.roadItem.width,height:p.roadItem.height,canvas_width:device.canvas.width,canvas_height:device.canvas.height,visible:p.roadItem.visible})'))
        # Navigation target is an external OS test input; production navigation remains intact.
        js('p.controller.navigate('+json.dumps({'coordinate':case['destination'],'name':case['name'],'site_id':'nav'})+')');drain();result['launched_url']=launched[-1];result['navigation_message']=str(panel.property('message'));result['destination_app_success_claimed']=bool(re.search(r'(목적지|안내|도착).*(성공|완료)',result['navigation_message']))
    elif op=='storage_fault':
        calculate();last=stored();result['last_good_before']=last;capture=folder.parent/('immutable-'+str(uuid.uuid4())+'.json');capture.write_text(json.dumps(last),encoding='utf8');transitions.clear()
        if case['fault'] in ('partial_write','storage_full'):
            storage_fault=case['fault'];result['ok']=save('수정');storage_fault='';result['outcome']='committed' if result['ok'] else 'rejected';result['last_good_after']=stored()
        elif case['fault']=='revision_conflict':
            # A second real panel commits while the first candidate remains pending.
            old=panel;_old_js=engine.newQObject(old);panel2=component.create();panel2.setParentItem(window.contentItem());engine.globalObject().setProperty('other',engine.newQObject(panel2));js('other.controller.complete("0",true)');newer=stored();result['last_good_before']=newer;result['ok']=save('충돌');result['outcome']='committed' if result['ok'] else 'rejected';result['last_good_after']=stored();panel2.deleteLater()
        else:
            if case['fault']=='corrupt_latest':save('추가');latest=state()['snapshot']['slot'];(folder/('survey-routes.'+latest+'.json')).write_text('broken')
            else:
                for f in folder.glob('survey-routes.*.json'):f.write_text('broken')
            transitions.clear();open_panel()
            if panel.property('controller') is None:result['outcome']='rejected';result['last_good_after']=json.loads(capture.read_text())
            else:result['outcome']='recovered';result['reloaded']=state()['snapshot']['data'];result['last_good_after']=result['reloaded']
        expected=next(r for r in result['last_good_before']['routes'] if r['route_id']==result['last_good_before']['active_id']);result['published_partial']=any(r and r!=expected for r in transitions);requests.clear();provider_dispatches.clear();transport_dispatches.clear()
    elif op=='mapping_reload':
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,{'layer':'site','id':'site_id','name':'site_name','completed':'doneA'}[key])
        calculate();save('A');a_index=len(saved())-1
        complete('0')
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,{'layer':'custom_targets','id':'site_id','name':'site_name','completed':'doneB'}[key])
        calculate();save('B');load(a_index)
        result['loaded_mapping']={k:panel.findChild(QObject,n).property('text') for k,n in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]}
        calculate();result['new_mapping']=state()['candidate']['mapping'];result['new_completed']=state()['candidate']['stops'][0]['completed']
        calculate(True);result['remaining_mapping']=state()['candidate']['mapping'];result['completed_records']=[s for s in state()['candidate']['stops'] if s['completed']]
    elif op=='mapping_settings_restart_move':
        mapping=case['mapping'];features=[{'custom_id':'A','title':'첫 대상','done':False,'xy':[127,37]},{'custom_id':'B','title':'둘째 대상','done':False,'xy':[127.001,37]}];device_inputs()
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,mapping[key])
        click('서버 설정 저장 (키 제외)');result['persisted_mapping']=detached(stored()['settings']['mapping']);result['active_before']=stored()['active_id'];new=Path(str(folder)+'-moved');shutil.move(folder,new);folder=new;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));requests.clear();provider_dispatches.clear();transport_dispatches.clear();open_panel();result['project_dir']=str(folder);result['reopened_mapping']={k:panel.findChild(QObject,n).property('text') for k,n in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]};control('scopeCombo',1,'currentIndex');result['ok']=calculate();result['calculated_mapping']=state()['candidate']['mapping'] if state()['candidate'] else None;result['active_after']=stored()['active_id']
    elif op=='panel_layout':
        window.resize(int(case['viewport_width']),900);window.show();panel.setProperty('expanded',True)
        for _ in range(5):app.processEvents()
        content=panel.findChild(QObject,'routeContent');scroll=panel.findChild(QObject,'routeScroll')
        def rect(obj):
            point=obj.mapToItem(panel,QPointF(0,0));return {'left':point.x(),'right':point.x()+obj.width(),'top':point.y(),'bottom':point.y()+obj.height()}
        field_names=['layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','targetEdit','serverEdit','optimizerEdit','backendEdit','profileEdit','keyEdit','timeoutEdit','offsetEdit','objectiveCombo','routeName','savedCombo']
        fields=[]
        for name in field_names:
            item=panel.findChild(QObject,name);measured=rect(item);measured.update(name=name,row=str(round(measured['top'])));fields.append(measured)
        label_names=['selectionHelpLabel','completionHelpLabel','scopeHelpLabel','messageLabel','availabilityLabel']
        labels=[]
        for name in label_names:
            item=panel.findChild(QObject,name);measured=rect(item);measured.update(name=name,wrap_enabled=True);labels.append(measured)
        content_rect=rect(content);shot=folder/'panel-layout.png';window.grabWindow().save(str(shot))
        result.update(content_rect={'left':content_rect['left'],'right':content_rect['right']},fields=fields,labels_help_errors=labels,
            horizontal_overflow=content.width()>scroll.property('availableWidth')+0.5 or any(f['left']<content_rect['left']-0.5 or f['right']>content_rect['right']+0.5 for f in fields),screenshot_path=str(shot))
    elif op=='selection_live':
        panel.setProperty('expanded',True);counts=[];all_ids=[str(f.get('id',f.get('custom_id'))) for f in features]
        for count in case.get('selection_counts',[0,1,len(features)]):
            case['selected_ids']=all_ids[:count];device_inputs()
            wait_for(lambda count=count:int(panel.property('selectedCount'))==count)
            text_value=str(panel.findChild(QObject,'selectionHelpLabel').property('text'))
            counts.append(int(re.search(r'(\d+)\s*$',text_value)[1]))
        result['recognized_counts_before_calculate']=counts
    elif op=='route_key_availability':
        pass
    else:raise RuntimeError('unsupported '+op)
    mat=next((r for r in requests if 'locations' in r['body']),None);opt=next((r for r in requests if 'jobs' in r['body']),None)
    objective=None
    if opt:
        matrices=opt['body']['matrices']['car'];objective='distance' if matrices['costs']==matrices['distances'] and matrices['costs']!=matrices['durations'] else 'time' if matrices['costs']==matrices['durations'] and matrices['costs']!=matrices['distances'] else None
    result.update(requests=detached(requests),provider_dispatches=detached(provider_dispatches),transport_dispatches=detached(transport_dispatches),submitted_ids=[j['description'] for j in opt['body']['jobs']] if opt else [],request_start=mat['body']['locations'][0] if mat else None,request_coordinate=mat['body']['locations'][1] if mat and len(mat['body']['locations']) > 1 else None,optimizer_request={'objective':objective,'cost_matrix':opt['body']['matrices']['car']['costs'],'return_to_start':opt['body']['vehicles'][0].get('end_index')==0} if opt else None)
    if case.get('restart_after_calculate'):
        open_panel();result['session_key_present_after_restart']=bool(state()['settings']['key'])
    result.setdefault('saved_after',saved() if panel.property('controller') is not None else [])
    result['active_after']=state()['snapshot']['data']['active_id'] if panel.property('controller') is not None else None
    controller_ready=panel.property('controller') is not None
    selection_text=str(panel.findChild(QObject,'selectionHelpLabel').property('text'))
    selection_count=re.search(r'(\d+)\s*$',selection_text)
    result['selection_help']={'recognized_count':int(selection_count[1]) if selection_count else None,
        'explains_layer_selection':all(word in selection_text for word in ('대상 레이어','선택','체크')),
        'focus_is_selection':controller_ready and case.get('focused_id') in [s['site_id'] for s in state()['listed']]}
    completion_text=str(panel.findChild(QObject,'completionHelpLabel').property('text'))
    result['completion_help']={'mapped_boolean_only':all(word in completion_text for word in ('Boolean','true','false','NULL','missing')),
        'blank_mapping_uses_route_local':all(word in completion_text for word in ('비우면','저장 경로'))}
    key_control=panel.findChild(QObject,'keyEdit')
    if key_control:engine.globalObject().setProperty('routeKeyControl',engine.newQObject(key_control))
    result['route_key_input']={'available':key_control is not None,'enabled':bool(key_control and key_control.property('enabled')),
        'password_echo':bool(key_control and js('routeKeyControl.echoMode!==0').toBool())}
    result['message']=panel.property('message');result['logs']='\n'.join(logs);result['transitions']=transitions;result['storage_writes']=writes;result['runtime']='Qt QML actual generated panel, injected QField host and HTTP transport; not native QField'
    return result
try:print(json.dumps(main(),ensure_ascii=True))
except Exception:
    import traceback;traceback.print_exc();print(json.dumps(logs,ensure_ascii=True),file=sys.stderr);sys.exit(1)
