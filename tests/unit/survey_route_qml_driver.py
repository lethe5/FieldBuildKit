"""Execute generated RoutePanel in Qt; inject only QField, HTTP, file faults and OS boundaries."""
import json, os, sys, uuid, re, time, threading, shutil, hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_CONTROLS_STYLE']='Basic'
os.environ['QT_QPA_FONTDIR']='C:/Windows/Fonts'
from PySide6.QtCore import QObject, Slot, QUrl, QMetaObject, Qt, QPoint, QPointF, QCoreApplication, QEvent, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QAccessible, QInputMethodEvent, QInputMethodQueryEvent, QKeyEvent, QPalette, QColor
from PySide6.QtQml import QQmlAbstractUrlInterceptor, QQmlEngine, QQmlComponent, QQmlNetworkAccessManagerFactory
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer

payload=json.load(sys.stdin);case=payload['case'];folder=Path(payload['project_dir']);op=case['operation']
requests=[];provider_dispatches=[];transport_dispatches=[];received_responses=[];logs=[];transitions=[];writes=[];source_writes=[];expression_calls=[];evaluator_writes=[];fault='';geometry_fault='';completion_fault='';storage_fault='';launched=[];use_case_responses=False
features=case.get('features',case.get('sites',[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(3)]))
gps=case.get('gps',[127,37]);map_center=[128,38];response=case.get('response',{})
walking_response_index=0
def detached(x):return json.loads(json.dumps(x))
generated_shape=None;generated_provider_rows=None;generated_provenance={}
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
        global walking_response_index
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        url=self.headers['X-Original-Url']
        kind=('access-snap' if '/snap/' in url else
            'walking-directions' if '/directions/foot-hiking/' in url else
            'origin-validation' if '/matrix/' in url and body.get('metrics')==['duration'] and len(body.get('locations',[]))==1 else
            'matrix' if '/matrix/' in url else 'optimizer' if 'jobs' in body else 'directions')
        headers={'Content-Type':self.headers.get('Content-Type','')}
        if self.headers.get('Authorization') is not None:headers['Authorization']=self.headers['Authorization']
        req={'kind':kind,'url':url,'method':'POST','body':body,'headers':headers}
        requests.append(req);logs.append('HTTP '+req['url'])
        fault_applies=kind in ('matrix','optimizer','directions')
        if fault_applies and fault in ('timeout','network','status_0') and (op!='remaining' or 'jobs' in body):
            if fault=='timeout':time.sleep(.15)
            self.close_connection=True;return
        if fault_applies and fault.startswith('http_'):
            self.send_response(int(fault[5:]));self.end_headers();self.wfile.write(('failure '+case.get('key','')).encode());return
        status=200
        if fault_applies and fault=='truncated_json':out=b'{"durations":'
        else:
            if kind=='origin-validation':
                value={'durations':[[0]],'sources':[{'location':detached(body['locations'][0]),'snapped_distance':0}]}
            elif kind=='access-snap':
                value=detached(case.get('access_snap_response',{'locations':[{'location':detached(point)} for point in body['locations']]}))
            elif kind=='walking-directions':
                coordinates=body['coordinates'];rows=case.get('walking_responses',[])
                observed=detached(rows[walking_response_index]) if walking_response_index<len(rows) else {'distance_m':1,'duration_s':1,'geometry':{'type':'LineString','coordinates':coordinates}}
                walking_response_index+=1
                if observed.get('explicit_no_path'):
                    status=404;value={'error':{'code':'NO_FOOT_ROUTE','message':'no foot route found'}}
                else:
                    value={'features':[{'geometry':observed['geometry'],'properties':{'summary':{'distance':observed['distance_m'],'duration':observed['duration_s']},'segments':[{'distance':observed['distance_m'],'duration':observed['duration_s']}]}}]}
            elif kind=='matrix':
                n=len(body['locations']);times=[[0 if i==j else 10+abs(i-j) for j in range(n)] for i in range(n)];distances=[[0 if i==j else 100+abs(i-j) for j in range(n)] for i in range(n)]
                value={'durations':detached(case.get('time_matrix',times)),'distances':detached(case.get('distance_matrix',distances)),'sources':[{'snapped_distance':0} for _ in range(n)]}
                if fault=='null_matrix':value['durations']=None
                if fault=='disconnected':value['durations'][0][1]=None
                if fault=='off_road':value['sources'][1]['snapped_distance']=10001
            elif kind=='optimizer':
                jobs=body['jobs']
                if use_case_responses and 'optimizer_response' in case:
                    value=detached(case['optimizer_response'])
                else:
                    order=response.get('order',case.get('backend_order',[j['id'] for j in jobs]))
                    feature_ids=[str(row.get('id')) for row in features]
                    steps=[{'type':'job','id':feature_ids.index(str(item)) if str(item) in feature_ids else item} for item in order]
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
                    coordinates=body.get('coordinates',[])
                    if op in ('route_progression','completion_overlay','completion_write_failure','route_line_toggle') and len(coordinates) in (4,5):
                        distances=[100,200,300,400][:len(coordinates)-1];durations=[20,100,120,216][:len(coordinates)-1]
                        road={'type':'LineString','coordinates':coordinates}
                        legs=[{'distance_m':d,'duration_s':durations[i],'way_points':[i,i+1]} for i,d in enumerate(distances)]
                    if road is None and len(coordinates)>=2:road={'type':'LineString','coordinates':coordinates}
                    if legs is None and len(coordinates)>=2:
                        count=len(coordinates)-1;distance=response.get('distance_m',1234);duration=response.get('duration_s',456)
                        legs=[{'distance_m':distance/count,'duration_s':duration/count,'way_points':[i,i+1]} for i in range(count)]
                    value={'features':[{'geometry':road,'properties':{'summary':{'distance':sum(v['distance_m'] for v in legs),'duration':sum(v['duration_s'] for v in legs)} if legs else None,'segments':[{'distance':v['distance_m'],'duration':v['duration_s']} for v in legs] if legs else None,
                        'way_points':list(range(len(legs)+1)) if legs else None}}] if road or legs else []}
                feature=value.get('features',[{}])[0] if value.get('features') else None
                segments=feature.get('properties',{}).get('segments') if feature else None
                if op in ('route_progression','completion_overlay','completion_write_failure','route_line_toggle') and feature and isinstance(segments,list) and not (use_case_responses and case.get('directions_response') is not None):
                    feature.setdefault('properties',{})['summary']={'distance':sum(v['distance_m'] for v in legs),'duration':sum(v['duration_s'] for v in legs)}
            if use_case_responses and case.get('provider_document_stage')==kind:
                value=case.get('provider_document')
            out=json.dumps(value,ensure_ascii=False,allow_nan=True,sort_keys=True,separators=(',',':')).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
        try:self.wfile.write(out)
        except (BrokenPipeError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),HTTP);threading.Thread(target=server.serve_forever,daemon=True).start()
class Network(QNetworkAccessManager):
    def createRequest(self,operation,request,outgoingData=None):
        original=request.url().toString()
        if request.url().scheme() in ('http','https'):
            original=request.url().toString();request=QNetworkRequest(request);request.setRawHeader(b'X-Original-Url',original.encode());request.setUrl(QUrl('http://127.0.0.1:'+str(server.server_port)+'/'))
        reply=super().createRequest(operation,request,outgoingData)
        if original.startswith(('http://','https://')):
            chunks=[]
            # Connect before XHR receives the reply. Peek does not consume its bytes.
            reply.readyRead.connect(lambda:chunks.append(bytes(reply.peek(reply.bytesAvailable()))))
            def received():
                raw=b''.join(chunks)
                try:value=json.loads(raw)
                except (ValueError,UnicodeError):value=None
                kind='access-snap' if '/snap/' in original else 'walking-directions' if '/directions/foot-hiking/' in original else 'matrix' if '/matrix/' in original else 'directions' if '/directions/' in original else 'optimizer'
                received_responses.append({'kind':kind,'bytes':raw,'payload':value,'sha256':hashlib.sha256(raw).hexdigest()})
            reply.finished.connect(received)
        return reply
class Factory(QQmlNetworkAccessManagerFactory):
    def create(self,parent):return Network(parent)
class Boundary(QObject):
    @Slot(str,result='QVariant')
    def geometryFromWkt(self,wkt):
        match=re.fullmatch(r'POINT\s*\(([^)]+)\)',wkt,re.I)
        if match:return {'type':'Point','coordinates':[float(v) for v in match[1].split()]}
        match=re.search(r'LINESTRING\(([^\)]+)\)',wkt)
        if match:return {'type':'LineString','coordinates':[[float(v) for v in p.split()] for p in match[1].split(',')]}
        return {'wkt':wkt}
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
        if text=='boundary($geometry)':
            geometry=feature['geometry'];kind=geometry['type']
            if kind=='Polygon':return {'type':'MultiLineString','coordinates':geometry['coordinates']}
            if kind=='MultiPolygon':return {'type':'MultiLineString','coordinates':[ring for polygon in geometry['coordinates'] for ring in polygon]}
            raise ValueError('boundary requires polygon')
        if text.startswith('attribute('):return feature['attributes'].get(re.search(r",'(.*)'\)",text)[1].replace("''","'"))
        if text.startswith(('x(transform(', 'y(transform(')):
            if geometry_fault:
                raise ValueError(geometry_fault)
            if 'make_point(' in text:
                m=re.search(r'make_point\(([^,]+),([^\)]+)\)',text);point=[float(m[1]),float(m[2])]
            else:point=representative_xy(feature['geometry'])
            source=generated_provenance.get('generated_crs',case.get('crs','EPSG:4326')) if '@layer_crs' in text else 'EPSG:4326'
            if source!='EPSG:4326':
                from rasterio.warp import transform
                xs,ys=transform(source,'EPSG:4326',[point[0]],[point[1]]);point=[xs[0],ys[0]]
            return point[0] if text.startswith('x(') else point[1]
        if 'geom_from_wkt(' in text:
            # Native ExpressionEvaluator stringifies every evaluated value, including geometry.
            return re.search(r'LINESTRING\([^\)]+\)',text)[0]
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
        ok=storage_fault not in ('partial_write','storage_full','commit_failure')
        if storage_fault not in ('storage_full','commit_failure'):target.write_text(text[:len(text)//2] if storage_fault=='partial_write' else text,encoding='utf8')
        directions=next((row for row in reversed(received_responses) if row['kind']=='directions'),None)
        writes.append({'path':str(target),'ok':ok,'bytes':target.read_text(encoding='utf8') if target.exists() else None,
            'directions_payload_sha256':directions['sha256'] if directions else None});logs.append('write '+target.name+' '+str(ok));return ok
    @Slot(str,bool,result=bool)
    def complete(self,id,value):
        source_writes.append({'site_id':id,'value':bool(value),'committed':not bool(completion_fault)})
        if completion_fault:return False
        field=state()['mapping']['completed'];mapping=state()['mapping']
        for f in features:
            if str(f.get(mapping['id'],f.get('id')))==id:f[field]=value;device_inputs();return True
        return False
    @Slot(str,result=bool)
    def launch(self,url):
        results=case.get('launch_results')
        result=results[len(launched)] if isinstance(results,list) and len(launched)<len(results) else case.get('launch_result',True)
        launched.append({'url':url,'via':'Qt.openUrlExternally','result':bool(result)})
        return bool(result)
    @Slot(str,str)
    def providerEntry(self,provider,s):
        settings=json.loads(s)
        provider_dispatches.append({'backend':provider,'max_road_offset_m':settings.get('max_road_offset_m'),'max_access_distance_m':settings.get('max_access_distance_m')})
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
put('org.qfield','qmldir','module org.qfield\nExpressionEvaluator 1.0 ExpressionEvaluator.qml\nFeatureModel 1.0 FeatureModel.qml\nAttributeFormModel 1.0 AttributeFormModel.qml\nQgsGeometryWrapper 1.0 QgsGeometryWrapper.qml\nMapToScreen 1.0 MapToScreen.qml\nsingleton GeometryUtils 1.0 GeometryUtils.qml\nsingleton CoordinateReferenceSystemUtils 1.0 CoordinateReferenceSystemUtils.qml\nsingleton LayerUtils 1.0 LayerUtils.qml\nsingleton FileUtils 1.0 FileUtils.qml\nsingleton FeatureUtils 1.0 FeatureUtils.qml\n')
put('org.qfield','ExpressionEvaluator.qml','import QtQml\nQtObject {property var project;property var layer;property var feature:null;onProjectChanged:boundaryHost.evaluatorWrite("project");onLayerChanged:boundaryHost.evaluatorWrite("layer");onFeatureChanged:boundaryHost.evaluatorWrite("feature");function evaluate(text){return boundaryHost.evaluate(text,feature)}}')
put('org.qfield','FeatureModel.qml','import QtQml\nQtObject {property var project;property var currentLayer;property var feature}')
put('org.qfield','AttributeFormModel.qml','import QtQml\nQtObject {property var featureModel;property bool result:false;function applyFeatureModel(){} function save(){return result} function changeAttribute(field,value){result=boundaryHost.complete(String(featureModel.feature.attributes.site_id||featureModel.feature.attributes.custom_id),value);return result}}')
put('org.qfield','QgsGeometryWrapper.qml','import QtQml\nQtObject {property var qgsGeometry;property var crs}')
put('org.qfield','GeometryUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createGeometryFromWkt(wkt){return boundaryHost.geometryFromWkt(wkt)} function point(x,y){return ({x:x,y:y})} function reprojectPoint(point){return point}}')
put('org.qfield','MapToScreen.qml','import QtQuick\nItem {property var mapSettings;property var mapPoint;readonly property point screenPoint: Qt.point(mapPoint&&mapPoint.x||0,mapPoint&&mapPoint.y||0)}')
put('org.qfield','CoordinateReferenceSystemUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function wgs84Crs(){return "EPSG:4326"}}')
put('org.qfield','FileUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function fileExists(p){return boundaryHost.exists(p)} function readFileContent(p){return boundaryHost.read(p)} function writeFileContent(p,t){return boundaryHost.write(p,t)}}')
put('org.qfield','LayerUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createFeatureIterator(layer){var rows=fixtureFeatures, i=0;return {hasNext:function(){return i<rows.length},next:function(){return rows[i++]},close:function(){}}}}')
put('org.qfield','FeatureUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createBlankFeature(){return ({})} function attributeIsNull(value){return value===null || value===undefined}}')
qrc_stubs=stubs/'qrc-qml';qrc_stubs.mkdir(parents=True,exist_ok=True)
(qrc_stubs/'GeometryRenderer.qml').write_text('import QtQuick\nimport org.qfield\nItem {property var mapSettings;property alias geometryWrapper:wrapper;property real lineWidth:3.5;property color color:"#ff0000";property real pointSize:20;property real borderSize:3;QgsGeometryWrapper {id:wrapper}}',encoding='utf8')
put('org.qgis','qmldir','module org.qgis\nDummy 1.0 Dummy.qml\n');put('org.qgis','Dummy.qml','import QtQml\nQtObject {}')
class QrcInterceptor(QQmlAbstractUrlInterceptor):
    def intercept(self,url,data_type):
        if url.scheme()=='qrc' and url.path().startswith('/qml/'):
            return QUrl.fromLocalFile(str(qrc_stubs/url.path().removeprefix('/qml/')))
        return url
qrc_interceptor=QrcInterceptor();engine.addUrlInterceptor(qrc_interceptor);engine.addImportPath(str(stubs));engine.rootContext().setContextProperty('fixtureFeatures',[])
# IDs and display names come from the generated .qgs, unless an acceptance case
# supplies a QGIS project-layer boundary fixture.
import xml.etree.ElementTree as ET
generated_layers=[{'layer_id':l.findtext('id'),'source_name':'site' if l.findtext('layername')=='조사지' else l.findtext('layername'),'alias':l.findtext('layername'),
    'fields':['site_id','site_name','inventory_id','selected_korean_name','custom_id','title','done','doneA','doneB']} for l in ET.parse(next(folder.glob('*.qgs'))).findall('./projectlayers/maplayer')]
layers=case.get('layers',generated_layers)
if op=='panel_layout':
    completed=(case.get('stored_mapping') or {}).get('completion_field')
    for layer in layers:
        if completed and completed not in layer['fields']:layer['fields'].append(completed)
if op=='generated_geometry_calculate':
    import fiona
    qgs_path=next(folder.glob('*.qgs'))
    site_node=next(l for l in ET.parse(qgs_path).findall('./projectlayers/maplayer') if '|layername=site' in l.findtext('datasource',''))
    datasource=site_node.findtext('datasource');source_file,table=datasource.split('|layername=',1)
    source_path=(qgs_path.parent/source_file).resolve()
    with fiona.open(source_path,layer=table) as provider:
        generated_provider_rows=[{'attributes':dict(row.properties),'geometry':{'type':row.geometry.type,'coordinates':detached(row.geometry.coordinates)}} for row in provider]
        provider_crs=provider.crs.to_string();provider_fields=list(provider.schema['properties'])
    features=[dict(row['attributes'],id=str(row['attributes']['site_id']),name=row['attributes']['site_name'],geometry=row['geometry']) for row in generated_provider_rows]
    generated_shape=features[0]['geometry'] if features else None
    for layer in layers:
        if layer['layer_id']==site_node.findtext('id'):
            layer.update(fields=provider_fields,crs=provider_crs)
    generated_provenance={'calculation_feature_origin':'generated_project_layer','fixture_feature_injected':'features' in case or '_generated_feature' in case,
        'generated_project_path':str(qgs_path),'generated_gpkg_path':str(source_path),'generated_layer_name':table,
        'qgs_datasource':datasource,'generated_crs':provider_crs,'provider_row_ids':[str(row['attributes']['site_id']) for row in generated_provider_rows]}
if case.get('layer_id') and 'layers' not in case:
    for layer in layers:
        if layer.get('source_name')=='site':layer['layer_id']=case['layer_id']
if op=='legacy_route' and 'layers' not in case:
    legacy_stops=case.get('document',{}).get('routes',[{}])[0].get('stops',[])
    if legacy_stops:
        for layer in layers:
            if layer.get('source_name')=='site':layer['layer_id']=legacy_stops[0]['source_layer']
route_defaults={'surveyType':case.get('survey_type','temporary_plots')}
if 'layers' not in case and not any(l.get('source_name')=='custom_targets' for l in layers):layers.append({'layer_id':'custom_targets','source_name':'custom_targets','alias':'custom_targets','fields':['site_id','site_name','inventory_id','selected_korean_name','custom_id','title','done','doneA','doneB']})
def js(code):
    v=engine.evaluate(code)
    if v.isError():raise RuntimeError(v.toString()+' '+v.property('stack').toString())
    return v
engine.globalObject().setProperty('boundaryHost',engine.newQObject(boundary))
js('var hostLayerData='+json.dumps(layers)+';var hostLayers=hostLayerData.map(function(d){return {data:d,id:function(){return d.layer_id},name:function(){return d.alias||d.source_name},sourceName:function(){return d.source_name},fields:function(){return {names:function(){return (d.fields||[]).slice()}}},type:function(){return d.vector===false?1:0},geometryType:function(){return d.geometry_type===undefined?0:d.geometry_type},crs:function(){return d.crs||"EPSG:4326"}}});var treeRoot={name:function(){return ""},parent:function(){return null}};var treeNodes=hostLayers.map(function(layer){var parts=String(layer.data.tree_path||layer.name()).split(/[\\/]/).filter(Boolean),parent=treeRoot;for(var i=0;i<parts.length-1;i++){parent={part:parts[i],up:parent,name:function(){return this.part},parent:function(){return this.up}}}return {target:layer,part:parts.length?parts[parts.length-1]:layer.name(),up:parent,layer:function(){return this.target},name:function(){return this.part},parent:function(){return this.up}}});treeRoot.findLayers=function(){return treeNodes.slice()};var qgisProject={layerTreeRoot:function(){return treeRoot},mapLayer:function(id){return hostLayers.find(function(l){return l.id()===id})||null},mapLayers:function(){var out={};hostLayers.slice().sort(function(a,b){return a.id().localeCompare(b.id())}).forEach(function(layer){out[layer.id()]=layer});return out},mapLayersByName:function(name){return hostLayers.filter(function(l){return l.name()===name||l.sourceName()===name})}};var device={};')
if case.get('qfield_property_api'):
    js('hostLayers=hostLayerData.map(function(d){var layer={data:d,id:d.layer_id,name:d.alias||d.source_name,geometryType:d.geometry_type===undefined?0:d.geometry_type,crs:d.crs||"EPSG:4326"};if(d.vector!==false)layer.fields={names:(d.fields||[]).slice()};return layer});qgisProject={mapLayer:function(id){return hostLayers.find(function(layer){return layer.id===id})||null},mapLayersByName:function(name){return hostLayers.filter(function(layer){return layer.name===name})}}')
engine.rootContext().setContextProperty('qgisProject',js('qgisProject'))
canvas_component=QQmlComponent(engine);canvas_component.setData(b'import QtQuick\nItem {property var mapSettings}',QUrl());host_canvas=canvas_component.create();host_canvas.setParentItem(window.contentItem());host_canvas.setWidth(640);host_canvas.setHeight(480);engine.globalObject().setProperty('hostCanvas',engine.newQObject(host_canvas))
class Iface(QObject):
    @Slot(result='QVariant')
    def mapCanvas(self):return js('device.canvas')
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
project_owner=QObject();project_owner.setObjectName('qfieldProjectOwner')
def device_inputs():
    rows=generated_provider_rows if generated_provider_rows is not None else [{'attributes':{'site_id':f.get('id'),'site_name':f.get('name'),'inventory_id':f.get('id'),'selected_korean_name':f.get('name'),**f},'geometry':f.get('geometry') or {'type':'Point','coordinates':f['xy']}} for f in features]
    engine.rootContext().setContextProperty('fixtureFeatures',rows)
    selected=[r for r in rows if 'selected_ids' not in case or str(r['attributes'].get('id',r['attributes'].get('custom_id',r['attributes'].get('site_id')))) in case['selected_ids']]
    js('device.canvas=hostCanvas;hostCanvas.mapSettings={destinationCrs:"EPSG:4326",getCenter:function(){return '+json.dumps({'x':map_center[0],'y':map_center[1]})+'}};device.gps='+json.dumps({'active':gps is not None,'positionInformation':{'latitudeValid':gps is not None,'longitudeValid':gps is not None,'longitude':gps[0] if gps else None,'latitude':gps[1] if gps else None}})+';device.locator={positionInformation:device.gps.positionInformation};device.form={model:{selectedLayer:qgisProject.mapLayersByName('+json.dumps('custom_targets' if case.get('mapping') else '조사지')+')[0],selectedFeatures:'+json.dumps(selected)+'}};')
    if case.get('qfield_property_api'):js('hostCanvas.mapSettings.layers=hostLayers')
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
    # Model the QField project lifetime independently of the persistent window/canvas.
    panel.setParent(project_owner)
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
    names={'server_url':'serverEdit','optimizer_url':'optimizerEdit','backend':'backendEdit','key':'keyEdit','profile':'profileEdit','timeout_ms':'timeoutEdit','max_road_offset_m':'offsetEdit','max_access_distance_m':'accessEdit'}
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

def seed_document(data):
    source=(folder/'qfield_routes/repository.js').read_text(encoding='utf8')
    js("var seedRepository=(function(){"+source+";return {save:save};})();")
    return json.loads(val("seedRepository.save({exists:function(p){return boundaryHost.exists(p)},read:function(p){return boundaryHost.read(p)},write:function(p,t){return boundaryHost.write(p,t)}},"+json.dumps(str(folder/'survey-routes'))+","+json.dumps(data)+",0)"))

def raw_envelope(data, revision=1):
    payload_text=json.dumps(data,ensure_ascii=False,separators=(',',':'))
    h=2166136261
    encoded=payload_text.encode('utf-16-le')
    for index in range(0,len(encoded),2):
        h^=encoded[index] | encoded[index+1]<<8
        h=(h*16777619)&0xffffffff
    path=folder/'survey-routes.a.json'
    path.write_text(json.dumps({'revision':revision,'checksum':format(h,'x'),'payload':payload_text},ensure_ascii=False,separators=(',',':')),encoding='utf8')
    return path

def set_completion(id, value):
    stop=next(s for s in active()['stops'] if s['site_id']==id)
    text=str(stop['sequence'])+'. '+stop.get('name',id)
    obj=next(o for o in visual_objects(panel) if str(o.property('text') or '').startswith(text))
    obj.setProperty('checked',bool(value));QMetaObject.invokeMethod(obj,'clicked',Qt.DirectConnection);drain();device_inputs()

def overlay_snapshot():
    values=json.loads(val('p.completedItems.map(function(item){var boost=item.children.find(function(child){return child.objectName==="completedFillBoost"}),baseFill=.25,boostFill=boost&&boost.visible?.25*boost.opacity:0;return {color:item.overlayColor,persistent:item.persistent,fill_opacity:item.geometryType==="Polygon"?1-(1-baseFill)*(1-boostFill):item.opacity,outline_opacity:item.opacity,opacity:item.opacity,geometry_type:item.geometryType,composition:{base_renderer:item.geometryWrapper.qgsGeometry!==null,base_item_opacity:item.opacity,boost_renderer:!!boost,boost_visible:!!(boost&&boost.visible),boost_item_opacity:boost?boost.opacity:0,same_geometry:!!(boost&&JSON.stringify(boost.geometryWrapper.qgsGeometry)===JSON.stringify(item.geometryWrapper.qgsGeometry))}}})'))
    return values[0] if values else None

def progress_snapshot():
    value=json.loads(val('p.controller.progress()'))
    route=active();value['completed_ids']=[s['site_id'] for s in route['stops'] if s.get('completed')]
    following=json.loads(val('p.controller.next()'));value['next_id']=following['site_id'] if following else None
    return value

def load(index):
    control('savedCombo',index,'currentIndex')
    button=panel.findChild(QObject,'loadRouteButton')
    if not QMetaObject.invokeMethod(button,'clicked',Qt.DirectConnection):raise RuntimeError('load click failed')
    drain()
def visual_objects(root):
    yield root
    if hasattr(root,'childItems'):
        for child in root.childItems():yield from visual_objects(child)

def accessibility(item):
    interface=QAccessible.queryAccessibleInterface(item)
    if interface is None:raise RuntimeError('No runtime accessibility interface: '+item.objectName())
    current=interface.state()
    return {'role':interface.role().name,'name':interface.text(QAccessible.Name),
        'visible':not current.invisible,'enabled':not current.disabled}

def object_value(item, property_name):
    try:value=item.property(property_name)
    except RuntimeError:value=engine.newQObject(item).property(property_name).toQObject()
    return value.toVariant() if hasattr(value,'toVariant') else value

def contrast(foreground,background):
    def luminance(color):
        values=[color.redF(),color.greenF(),color.blueF()]
        values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
        return sum(v*w for v,w in zip(values,[.2126,.7152,.0722]))
    first,second=sorted([luminance(foreground),luminance(background)])
    return (second+.05)/(first+.05)
def complete(id):
    # Repeater CheckBox is the actual panel delegate; user selects it via its displayed order/name.
    stop=next(s for s in active()['stops'] if s['site_id']==id)
    text=str(stop['sequence'])+'. '+stop['name'];obj=next(o for o in visual_objects(panel) if str(o.property('text') or '').startswith(text))
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
    matrix=next(r for r in transport_dispatches if len(r.get('body',{}).get('locations',[]))>1 and 'distance' in r['body'].get('metrics',[]))
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
    global features,gps,map_center,fault,geometry_fault,completion_fault,storage_fault,folder,component,response,use_case_responses,panel,project_owner
    original_response=response;response={};original_gps=gps;gps=[127,37]
    new_ops={'project_dropdowns','route_workflow_ui','map_start_marker','generated_geometry_calculate','storage_feedback','reopen_navigate','schema2_roundtrip','route_progression','completion_overlay','metric_display','route_line_toggle','legacy_route',
        'candidate_name_save','followup_panel_ui','route_name_text_input_proxy','final_floating_label_geometry','settings_disclosure','settings_key_provenance','settings_snapshot_save','platform_naver_dispatch','ordered_completion_checklist','candidate_completion_guard','mixed_route_presentation'}
    def site_layer_id():
        return next((l['layer_id'] for l in layers if l.get('source_name')=='site'),layers[0]['layer_id'])
    if op=='project_dropdowns' and case.get('stored_mapping'):
        mapping=case['stored_mapping']
        seed_document({'schema':2,'active_id':'','routes':[],'settings':{'mapping':{'layer':mapping['layer_id'],'id':mapping['id_field'],'name':mapping['name_field'],'completed':mapping.get('completion_field','')}}})
    if op in ('panel_layout','followup_panel_ui') and case.get('stored_mapping'):
        mapping=case['stored_mapping']
        seed_document({'schema':2,'active_id':'','routes':[],'settings':{'mapping':{'layer':mapping['layer_id'],'id':mapping['id_field'],'name':mapping['name_field'],'completed':mapping.get('completion_field','')}}})
    if op=='legacy_route':raw_path=raw_envelope(case['document'])
    if op=='final_floating_label_geometry':seed_inactive_saved_fixture()
    if op=='metric_display':
        coords=[[127,37],[127.001,37.001],[127.002,37.002],[127.003,37.003]];layer_id=site_layer_id();seconds=case['remaining_duration_s'];distance=case['remaining_distance_m']
        legs=[]
        for i in range(3):
            legs.append({'sequence':i+1,'from':'start' if i==0 else {'layer_id':layer_id,'site_id':str(i-1)},'to':{'layer_id':layer_id,'site_id':str(i)},'distance_m':distance if i==2 else 0,'duration_s':seconds if i==2 else 0,'geometry':{'type':'LineString','coordinates':coords[i:i+2]}})
        route={'route_id':'metric-route','name':case['route_name'],'created_at':'2026-09-16T00:00:00Z','backend':'ors-vroom','status':'ready','revision':1,'start':coords[0],'end':coords[-1],'roundtrip':False,'distance_m':distance,'duration_s':seconds,
            'mapping':{'layer':layer_id,'id':'site_id','name':'site_name','completed':''},'stops':[{'site_id':str(i),'source_layer':layer_id,'name':'조사지 '+str(i),'sequence':i+1,'completed':i<int(case['completed']),'coordinate':coords[i+1]} for i in range(3)],
            'road_geometry':{'type':'LineString','coordinates':coords},'legs':legs,'eta':None,'eta_basis':None,'optimality_guaranteed':False}
        seed_document({'schema':2,'active_id':'metric-route','routes':[route],'settings':{}})
    if op=='reopen_navigate':
        road=case['road_geometry'];layer_id=site_layer_id();destination=road['coordinates'][-1]
        route={'route_id':'navigation-route','name':'도로선','created_at':'2026-09-16T00:00:00Z','backend':'ors-vroom','status':'ready','revision':1,'start':road['coordinates'][0],'end':destination,'roundtrip':False,
            'distance_m':1,'duration_s':1,'mapping':{'layer':layer_id,'id':'site_id','name':'site_name','completed':''},
            'stops':[{'site_id':'nav','source_layer':layer_id,'name':case['name'],'sequence':1,'completed':False,'coordinate':destination}],
            'road_geometry':road,'legs':[{'sequence':1,'from':'start','to':{'layer_id':layer_id,'site_id':'nav'},'distance_m':1,'duration_s':1,'geometry':road}],
            'eta':None,'eta_basis':None,'optimality_guaranteed':False}
        seed_document({'schema':2,'active_id':'navigation-route','routes':[route],'settings':{}})
    type1_without_mapping=case.get('survey_type')=='simple_inventory' and not case.get('mapping')
    if type1_without_mapping:seed_inactive_saved_fixture()
    if op=='mixed_route_presentation':
        palette=QPalette();dark=case.get('theme')=='dark'
        palette.setColor(QPalette.Window,QColor('#111827' if dark else '#f8fafc'))
        palette.setColor(QPalette.WindowText,QColor('#f9fafb' if dark else '#111827'))
        app.setPalette(palette);window.resize(int(case.get('viewport_width',320)),900)
    open_panel();settings();original=features
    if op=='legacy_route' and panel.property('controller') is None:
        raw_text=raw_path.read_text(encoding='utf8')
        return {'ok':False,'message':str(panel.property('message')),'project_dir':str(folder),'storage_bytes_before':raw_text,'storage_bytes_after':raw_text,
            'writes':[],'requests':[],'saved_before':[],'saved_after':[],'active_before':None,'active_after':None,'logs':'\n'.join(logs),'runtime':'Qt QML actual generated panel, injected QField host and file boundary; not native QField'}
    if op not in new_ops and op!='mapping_settings_restart_move' and not type1_without_mapping:
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(len(original))]
        if not panel.property('defaultLayer'):
            for name,value in [('layerEdit','custom_targets'),('idEdit','inventory_id'),('nameEdit','selected_korean_name')]:control(name,value)
        control('scopeCombo',1,'currentIndex');calculate();save();features=original;response=original_response;gps=original_gps;device_inputs();requests.clear();provider_dispatches.clear();transport_dispatches.clear()
    use_case_responses=True
    if op=='completion_write_failure':
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,{'layer':'site','id':'id','name':'name','completed':'done'}[key])
        click('서버 설정 저장 (키 제외)');features=[dict(f,done=False) for f in original];device_inputs()
    before=saved();result={'saved_before':before,'active_before':state()['snapshot']['data']['active_id'],'project_dir':str(folder),'ok':True}
    def use_site_mapping(completed=''):
        control('layerEdit',site_layer_id());control('idEdit','site_id');control('nameEdit','site_name');control('completionEdit',completed)
        control('scopeCombo',1,'currentIndex');device_inputs()
    def full_calculation(roundtrip=True, completed=''):
        use_site_mapping(completed);control('roundtripBox',bool(roundtrip),'checked');return calculate()
    if op=='generated_geometry_calculate' and case.get('seed_saved'):
        assert full_calculation(True);assert save('기존 경로');open_panel();settings()
        baseline=stored();baseline_route=detached(active());baseline_path='survey-routes.'+state()['snapshot']['slot']+'.json'
        result.update(saved_before=detached(baseline['routes']),active_before=baseline_route,
            seed_saved_provenance={'created_via':'production_save_action','route_count':len(baseline['routes']),
                'active_route_id':baseline['active_id'],'independently_reopened_route_id':baseline_route['route_id'],
                'storage_project_relative_path':baseline_path})
        requests.clear();provider_dispatches.clear();transport_dispatches.clear()
    if op=='candidate_name_save':
        assert full_calculation(True);assert save('기존 경로')
        saved_before_routes=detached(saved());saved_before_route=detached(active())
        assert full_calculation(True)
        candidate=detached(state()['candidate']);base_revision=state()['candidateBaseRevision'];input_signature=state()['candidateInputSignature']
        calculation_requests=detached(requests);requests.clear();writes.clear()
        name_states=[];attempt_states=[];candidate_before=detached(candidate);stale_reason=''
        for action in case.get('actions',[]):
            if action.get('focus_name'):
                panel.findChild(QObject,'routeName').forceActiveFocus(Qt.TabFocusReason);app.processEvents()
            if 'set_name' in action:control('routeName',action['set_name'])
            if action.get('make_stale')=='calculation_input':
                control('scopeCombo',0 if int(panel.findChild(QObject,'scopeCombo').property('currentIndex'))!=0 else 1,'currentIndex');stale_reason='calculation_input'
            elif action.get('make_stale')=='snapshot_revision':
                js('p.controller.toggleRouteLine(!p.controller.state.showRouteLine)');drain();stale_reason='snapshot_revision'
            if action.get('save'):
                injected=action.get('fault')
                if injected in ('io_failure','recoverable_validation'):storage_fault='commit_failure'
                ok=save(str(panel.findChild(QObject,'routeName').property('text')))
                storage_fault=''
                attempt_states.append({'ok':bool(ok),'message':str(panel.property('message')),'candidate':detached(state()['candidate']),
                    'saved_routes':detached(saved()),'saved_route':detached(active()) if ok else None,'requests':detached(requests)})
            else:
                current={'candidate':detached(state()['candidate']),'base_revision':state()['candidateBaseRevision'],
                    'calculation_inputs':state()['candidateInputSignature'],'requests':detached(requests)}
                name_states.append(current)
                if attempt_states:attempt_states.append(current)
        document=stored();saved_route=detached(active())
        committed='survey-routes.'+state()['snapshot']['slot']+'.json' if document else None
        result.update(calculation_requests=calculation_requests,candidate_after_calculation=candidate,
            base_revision_after_calculation=base_revision,calculation_inputs_after_calculation=input_signature,
            name_action_states=name_states,saved_before=saved_before_route,saved_routes_before=saved_before_routes,
            saved_route=saved_route,reloaded_route=saved_route,committed_project_relative_path=committed,
            attempt_states=attempt_states,save_ok=bool(attempt_states[-1]['ok']) if attempt_states else False,
            stale_reason=stale_reason,candidate_before=candidate_before,candidate_after=detached(state()['candidate']),
            saved_routes_after=detached(saved()),requests_after_calculation=detached(requests),message=str(panel.property('message')))
    elif op=='route_name_text_input_proxy':
        assert full_calculation(True)
        candidate=detached(state()['candidate']);base_revision=state()['candidateBaseRevision']
        requests.clear();provider_dispatches.clear();transport_dispatches.clear()
        item=panel.findChild(QObject,'routeName');window.show();panel.setProperty('expanded',True)
        for _ in range(5):app.processEvents()
        engine.globalObject().setProperty('routeNameControl',engine.newQObject(item))
        if re.fullmatch(r'\d{4}-\d{2}-\d{2} 조사',str(item.property('text'))):item.setProperty('text','')
        states=[];selection_observed=False;deletion_observed=False;focus_recovery_invocations=[]
        def input_state(source, **observation):
            focused=window.activeFocusItem()
            value={'event_source':source,'active_focus':bool(item.property('activeFocus')),
                'cursor_visible':bool(item.property('cursorVisible')),
                'cursor_position':int(item.property('cursorPosition')),
                'text':str(item.property('text')),'candidate':detached(state()['candidate']),
                'base_revision':state()['candidateBaseRevision'],'requests':detached(requests),
                'focus_recovery_api_invocations':detached(focus_recovery_invocations),
                'focused_object_id':focused.objectName() if focused else None}
            value.update(observation);return value
        states.append(input_state('initial_state'))
        for event in case.get('input_events',[]):
            if event.get('touch_body'):
                scroll=panel.findChild(QObject,'routeScroll');flickable=scroll.property('contentItem')
                if flickable:
                    within=item.mapToItem(flickable,QPointF(0,0))
                    flickable.setProperty('contentY',max(0,within.y()-flickable.height()/2+item.height()/2))
                    app.processEvents()
                target_region=event.get('touch_target','field_body')
                if target_region=='label_notch_overlap':
                    label=panel.findChild(QObject,'routeNameFloatingLabel')
                    local=label.mapToItem(item,QPointF(label.width()/2,label.height()/2))
                else:
                    local=QPointF(item.width()/2,item.height()-max(4,float(item.property('bottomPadding'))/2))
                point=item.mapToItem(window.contentItem(),local)
                QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(round(point.x()),round(point.y())))
                app.processEvents()
                source='touch_equivalent_event'
                observation={'target_region':target_region,
                    'target_rect_source':'loaded_generated_qml_object_geometry',
                    'delivered_via':'window_pointer_event','focus_checked_before_any_recovery':True}
            elif 'text' in event:
                ime=QInputMethodEvent();ime.setCommitString(event['text']);QCoreApplication.sendEvent(item,ime);app.processEvents();source='input_method_commit_event';observation={}
            elif 'select' in event:
                first,last=event['select'];js('routeNameControl.select('+str(first)+','+str(last)+')');app.processEvents()
                selection_observed=bool(str(item.property('selectedText')));source='selection_event';observation={}
            elif event.get('delete_selection'):
                before_text=str(item.property('text'));key=QKeyEvent(QEvent.KeyPress,Qt.Key_Backspace,Qt.NoModifier)
                QCoreApplication.sendEvent(item,key);app.processEvents();deletion_observed=str(item.property('text'))!=before_text;source='delete_selection_event';observation={}
            else:continue
            states.append(input_state(source,**observation))
        flags=item.flags();query=QInputMethodQueryEvent(Qt.InputMethodQuery.ImEnabled);QCoreApplication.sendEvent(item,query)
        control_type='TextField' if any('TextField' in item.metaObject().className() for _ in (0,)) else 'TextInput'
        route_control={'evidence_source':'loaded_generated_qml_object','object_id':item.objectName(),'qml_type':control_type,
            'enabled':bool(item.property('enabled')),'editable':not bool(item.property('readOnly')),'read_only':bool(item.property('readOnly')),
            'accepts_input_method':bool(flags & QQuickItem.Flag.ItemAcceptsInputMethod),'input_method_enabled':bool(query.value(Qt.InputMethodQuery.ImEnabled))}
        final_text=str(item.property('text'));assert save(final_text);saved_route=detached(active())
        result.update(qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')},
            route_name_control=route_control,input_states=states,selection_event_observed=selection_observed,
            deletion_event_observed=deletion_observed,final_control_text=final_text,saved_route=saved_route,
            candidate_after_calculation=candidate,base_revision_after_calculation=base_revision,claims={},
            focus_recovery_api_invocations=focus_recovery_invocations,
            evidence_scope='automatic_input_wiring_proxy_not_device_keyboard')
    elif op=='settings_disclosure':
        settings({'key':case.get('manual_session_key','')})
        disclosure=panel.findChild(QObject,'settingsDisclosure');content=panel.findChild(QObject,'settingsContent')
        engine.globalObject().setProperty('disclosureKeyControl',engine.newQObject(panel.findChild(QObject,'keyEdit')))
        def disclosure_state():
            interface=QAccessible.queryAccessibleInterface(disclosure)
            return {'title':'API URL/키 설정','expanded':bool(panel.property('settingsExpanded')),
                'key_value_visible':bool(panel.property('settingsExpanded')),
                'values':{'server_url':str(panel.findChild(QObject,'serverEdit').property('text')),'optimizer_url':str(panel.findChild(QObject,'optimizerEdit').property('text'))},
                'labels':{'optimizer_url':str(panel.findChild(QObject,'optimizerEditFloatingLabel').property('text'))},
                'key_masked':js('disclosureKeyControl.echoMode!==0').toBool(),
                'accessible_state':interface.text(QAccessible.Description)}
        states=[]
        for action in case.get('actions',[]):
            if action!='open_panel':QMetaObject.invokeMethod(disclosure,'clicked',Qt.DirectConnection);drain()
            states.append(disclosure_state())
        result.update(states=states,requests=[],writes=[],horizontal_overflow=False)
    elif op=='settings_key_provenance':
        if case['key_source']=='manual':control('keyEdit',case['key']);js('p.applyControls(false)')
        panel.setProperty('expanded',True);panel.setProperty('settingsExpanded',True);app.processEvents()
        source_message=str(panel.findChild(QObject,'keySourceLabel').property('text'))
        rendered={'source_message':source_message,'key_text':str(panel.findChild(QObject,'keyEdit').property('displayText'))}
        warning=bool(panel.findChild(QObject,'projectKeyWarningLabel').property('visible'))
        qgs=next(folder.glob('*.qgs'));project_value=Boundary().evaluate('@fieldbuild_route_api_key',None)
        open_panel()
        result.update(generated_project_path=str(qgs),source_message=source_message,key_masked=True,rendered_panel=rendered,
            diagnostics=logs,project_variable_plaintext_warning_visible=warning,project_variable_read_from_qgs=project_value,
            key_after_session_restart=state()['settings']['key'] or None)
    elif op=='settings_snapshot_save':
        assert full_calculation(True);assert save('설정 보존 경로')
        requests.clear();provider_dispatches.clear();transport_dispatches.clear()
        settings_before_routes=detached(saved());settings(case.get('settings',{})|{'key':case.get('key',''),'objective':case.get('objective','time')})
        js('p.applyControls(false)')
        if case.get('seed_last_good'):js('p.controller.saveSettings()');drain()
        snapshot_before=detached(disk());writes.clear();commits=[]
        if case.get('fault'):storage_fault='commit_failure'
        for _ in range(case.get('save_count',1)):
            click('서버 설정 저장 (키 제외)')
            latest=writes[-1] if writes else None
            readback=stored()
            if latest and latest['ok']:
                rel=Path(latest['path']).name
                commits.append({'project_relative_path':rel,'project_scope':str(folder),'feedback':str(panel.property('message')),
                    'success':True,'readback_settings':detached(readback['settings'])})
        storage_fault='';snapshot_after=detached(disk());readback=stored()
        result.update(commits=commits,project_scope=str(folder),routes_before_save=settings_before_routes,
            reloaded_routes=detached(readback['routes']),reloaded_settings=detached(readback['settings']),
            snapshot_before=snapshot_before,snapshot_after=snapshot_after,session_key_after=state()['settings']['key'],
            feedback={'success':bool(commits),'message':str(panel.property('message'))},success_feedback_count=len(commits),requests=[])
    elif op=='platform_naver_dispatch':
        features=[{'id':'nav','name':case['name'],'xy':case['destination']}];device_inputs();assert full_calculation(False);assert save('안내 경로')
        requests.clear();launched.clear();panel.setProperty('platformName',case['platform']);panel.setProperty('callerId',case.get('caller_id') or 'ch.opengis.qfield')
        click('다음 지점 네이버지도 안내')
        message=str(panel.property('message'));status='설치 페이지 열림' if '설치 페이지' in message else '운영체제에 실행 요청' if '실행을 요청' in message else '실패'
        result.update(launcher_calls=detached(launched),status=status,fallback_count=max(0,len(launched)-1),
            web_fallback_count=sum('map.naver.com' in row['url'] for row in launched),
            claims={'app_started':False,'destination_accepted':False,'navigation_started':False},requests=[])
    elif op=='ordered_completion_checklist':
        mapped='done' if case['completion_source']=='field' else ''
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001],'done':False} for i in range(3)];device_inputs()
        assert full_calculation(False,mapped);assert save('순서 경로')
        requests.clear();writes.clear();source_writes.clear()
        for site_id in case.get('initial_completed_ids',[]):set_completion(site_id,True)
        def ordered_state():
            progress=progress_snapshot();rows=json.loads(val('p.route.stops.map(function(stop,index){return {site_id:stop.site_id,completion_enabled:p.completionEnabled(stop,index),checked:stop.completed===true,disabled_reason:p.completionEnabled(stop,index)?"":"다음 방문 지점부터 순서대로 완료하세요.",state_text:p.completionState(stop,index),non_color_state_indicator:p.completionState(stop,index)==="순서 밖 완료"}})'))
            progress.update(rows=rows,requests=[],enabled_incomplete_ids=[row['site_id'] for row in rows if row['completion_enabled'] and not row['checked']])
            return progress
        states=[ordered_state()];blocked=[];successful=[]
        def immutable_snapshot():return {'route':detached(active()),'source':detached(features),'overlay':overlay_snapshot(),'progress':progress_snapshot(),'writes':detached(source_writes)}
        for action in case.get('actions',[]):
            requests.clear();source_writes.clear()
            if 'attempt_complete' in action:
                before_state=immutable_snapshot();expected=progress_snapshot()['next_id']
                stop=next(s for s in active()['stops'] if s['site_id']==action['attempt_complete'])
                text=str(stop['sequence'])+'. '+stop['name'];checkbox=next(o for o in visual_objects(panel) if str(o.property('text') or '').startswith(text))
                action_control=next(o for o in visual_objects(panel) if o.objectName()=='blockedCompletionAction' and str(o.property('siteId'))==stop['site_id'])
                checkbox_accessibility=accessibility(checkbox);action_accessibility=accessibility(action_control)
                QMetaObject.invokeMethod(action_control,'clicked',Qt.DirectConnection);drain();after_state=immutable_snapshot()
                blocked.append({'before':before_state,'after':after_state,'feedback_next_id':progress_snapshot()['next_id'],'expected_next_id':expected,'requests':detached(requests),'writes':detached(source_writes),'control_enabled':bool(checkbox.property('enabled')),'checkbox_accessibility':checkbox_accessibility,'action_accessibility':action_accessibility,'message':str(panel.property('message'))})
            elif 'complete' in action:set_completion(action['complete'],True);successful.append(ordered_state())
            elif 'uncheck' in action:set_completion(action['uncheck'],False)
            elif 'external_completed_ids' in action:
                wanted=set(action['external_completed_ids'])
                if mapped:
                    for feature in features:feature['done']=str(feature['id']) in wanted
                    device_inputs();js('p.controller.refresh()');drain()
                else:
                    for stop in detached(active()['stops']):
                        if stop['completed'] and stop['site_id'] not in wanted:set_completion(stop['site_id'],False)
            states.append(ordered_state())
        result.update(states=states,blocked_attempts=blocked,successful_states=successful)
    elif op=='candidate_completion_guard':
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001]} for i in range(3)];device_inputs()
        if case.get('active_route'):
            assert full_calculation(False);assert save('기존 경로')
        active_before=detached(active());next_before=detached(js('p.controller.next()').toVariant())
        assert full_calculation(False)
        requests.clear();provider_dispatches.clear();transport_dispatches.clear();writes.clear();source_writes.clear()
        rows=[]
        for stop in state()['candidate']['stops']:
            checkbox=next(o for o in visual_objects(panel) if str(o.property('text') or '').startswith(str(stop['sequence'])+'. '+stop['name']))
            action=next(o for o in visual_objects(panel) if o.objectName()=='blockedCompletionAction' and str(o.property('siteId'))==stop['site_id'])
            rows.append({'site_id':stop['site_id'],'checkbox_enabled':bool(checkbox.property('enabled')),
                'blocked_action_visible':bool(action.property('visible')),'blocked_action_accessibility':accessibility(action)})
        result.update(active_before=active_before,next_before=next_before,candidate=detached(state()['candidate']),rows=rows,
            active_after=detached(active()),requests=detached(requests),provider_dispatches=detached(provider_dispatches),
            transport_dispatches=detached(transport_dispatches),writes=detached(writes),source_writes=detached(source_writes))
    elif op=='mixed_route_presentation':
        for feature in features:feature['done']=False
        device_inputs();use_site_mapping('done');settings({'max_access_distance_m':2000});control('roundtripBox',True,'checked')
        offsets=[.0035,.002,.004,.0015,0]
        access=[[feature['xy'][0]+offsets[index%len(offsets)],feature['xy'][1]] for index,feature in enumerate(features)]
        case['access_snap_response']={'locations':[{'location':point} for point in access]}
        walking=[]
        for index,feature in enumerate(features):
            if offsets[index%len(offsets)]==0:continue
            if index%2==0:walking.append({'explicit_no_path':True})
            else:
                distance=300 if index==1 else 225
                walking.append({'distance_m':distance,'duration_s':distance*.8,'geometry':{'type':'LineString','coordinates':[access[index],feature['xy']]}})
        case['walking_responses']=walking
        assert calculate();js('p.controller.acknowledgeUnmapped(true)');assert save('표시 혼합 경로')
        open_panel();window.show();app.processEvents()
        provider_start=len(transport_dispatches);storage_start=len(writes);source_start=len(source_writes)
        action_windows=[]
        for action in case.get('actions',[]):
            before=(len(transport_dispatches)-provider_start,len(writes)-storage_start,len(source_writes)-source_start)
            completed=False
            if action=='preview':
                js('p.updateView()');drain();completed=panel.property('roadItem') is not None
            elif action=='legend':
                if not panel.property('expanded'):click(str(panel.findChild(QObject,'routeSummaryButton').property('text')))
                legend=panel.findChild(QObject,'mixedRouteLegend');completed=legend is not None and bool(legend.property('visible'))
            elif action=='reload-each-visit-value-route':
                js('p.controller.reload()');drain();completed=active() is not None and int(panel.findChild(QObject,'visitAccessibilityRepeater').property('count'))==len(active().get('visits',[]))
            else:raise RuntimeError('unsupported mixed-route action '+action)
            action_windows.append({'action':action,
                'provider_attempt_count_before':before[0],'provider_attempt_count_after':len(transport_dispatches)-provider_start,
                'storage_write_attempt_count_before':before[1],'storage_write_attempt_count_after':len(writes)-storage_start,
                'source_write_attempt_count_before':before[2],'source_write_attempt_count_after':len(source_writes)-source_start,
                'product_operation_completed':completed})
        observed_lines=json.loads(val('p.walkingItems.filter(function(item){return item.linePattern}).map(function(item){return {semantic_class:item.semanticClass,pattern:item.linePattern,legend:item.legendLabel,contrasting_casing:item.contrastingCasing,warning:item.warningMarker,non_color_cue:item.nonColorCue}})'))
        vehicle=json.loads(val('({semantic_class:p.roadItem.semanticClass,pattern:p.roadItem.linePattern,legend:p.roadItem.legendLabel,contrasting_casing:p.roadItem.contrastingCasing,warning:false,non_color_cue:p.roadItem.nonColorCue})'))
        walking_items=[item for item in object_value(panel,'walkingItems') if item.property('linePattern')]
        rows=[vehicle]+observed_lines;items=[object_value(panel,'roadItem')]+walking_items
        line_classes={}
        for row,item in zip(rows,items):
            semantic=row.pop('semantic_class');row['object_ids']=[str(getCppPointer(item)[0])];line_classes[semantic]=row
        unmapped_item=next(item for item in walking_items if item.property('linePattern')=='dotted')
        accessibility_observations=[]
        for semantic_id,object_name in [('mapped_metric_source','mappedMetricSourceAccessibility'),('mapped_walking_totals','walkingTotalsAccessibility'),('fallback_lower_bound_status','mixedFallbackLabel')]:
            item=panel.findChild(QObject,object_name);observed=accessibility(item)
            accessibility_observations.append({'semantic_id':semantic_id,'object_id':str(getCppPointer(item)[0]),'source':'QAccessible.queryAccessibleInterface','name':observed['name'],'role':observed['role']})
        repeater=panel.findChild(QObject,'visitAccessibilityRepeater');engine.globalObject().setProperty('visitRepeater',engine.newQObject(repeater));count=int(repeater.property('count'))
        delegates=[]
        for index in range(count):
            item=js('visitRepeater.itemAt('+str(index)+')').toQObject()
            if item is None:raise RuntimeError('Repeater.itemAt(index) returned no delegate')
            observed=accessibility(item);visit_property=item.property('visitValue');visit_value=detached(visit_property.toVariant() if hasattr(visit_property,'toVariant') else visit_property)
            delegates.append({'value':{'lookup':'Repeater.itemAt(index)','visit_value_source':'delegate.property("visitValue")','object_id':str(getCppPointer(item)[0]),'object_name':item.objectName(),'delegate_index':index,'visit_value':visit_value,'qaccessible':{'source':'QAccessible.queryAccessibleInterface','object_id':str(getCppPointer(item)[0]),'role':observed['role'],'name':observed['name']}}})
        model={'model_count':count,'delegate_count':len(delegates),'creation':'QML Repeater delegate','repeater_object_id':str(getCppPointer(repeater)[0]),'enumeration':'Repeater.itemAt(index)'}
        provider_attempts=detached(transport_dispatches[provider_start:]);storage_write_attempts=detached(writes[storage_start:]);source_write_attempts=detached(source_writes[source_start:])
        result.update(line_classes=line_classes,warning_marker={'visible':bool(unmapped_item.property('warningMarker')),'non_color_cue':str(unmapped_item.property('nonColorCue')),'object_id':str(getCppPointer(unmapped_item)[0])},passive_boundary_observation={'provider_attempts':provider_attempts,'provider_attempt_count':len(provider_attempts),'storage_write_attempts':storage_write_attempts,'storage_write_attempt_count':len(storage_write_attempts),'source_write_attempts':source_write_attempts,'source_write_attempt_count':len(source_write_attempts),'action_windows':action_windows},accessibility_observations=accessibility_observations,visit_accessibility_binding_observations=[{'delegate_model_observation':{'value':model},'delegate_readback_observations':delegates}])
    elif op=='project_dropdowns':
        selected=case.get('selected_layer_id') or (case.get('stored_mapping') or {}).get('layer_id')
        if selected:js('p.refreshProjectSelectors('+json.dumps(selected)+')')
        if case.get('refreshed_fields') is not None:
            selected=selected or str(panel.findChild(QObject,'layerEdit').property('text') or '')
            js('var changedLayer=hostLayers.find(function(layer){return layer.id()==='+json.dumps(selected)+'});if(changedLayer)changedLayer.data.fields='+json.dumps(case['refreshed_fields'])+';p.refreshFields(changedLayer)')
        for action in case.get('actions',[]):
            if action=='reopen':open_panel();settings()
            elif action=='save' and not panel.property('mappingValidation'):click('서버 설정 저장 (키 제외)')
            elif action in ('schema_change','layer_change','panel_reopen'):js('p.refreshProjectSelectors('+json.dumps(selected or '')+')')
            elif action in ('calculate_preflight','save_preflight') and not panel.property('mappingValidation'):js('p.applyControls(true)')
        options=json.loads(val('p.layerOptions.map(function(option){return {label:option.label,layer_id:option.layer_id,source_name:option.source_name}})'))
        tree_paths=json.loads(val('p.layerOptions.map(function(option){return option.tree_path})'))
        selected_layer=str(panel.findChild(QObject,'layerEdit').property('text') or '') or None
        result.update(layer_options=options,layer_tree_paths=tree_paths,selected_layer_id=selected_layer,
            field_options=json.loads(val('p.fieldOptions')),
            selected_fields={'id':str(panel.findChild(QObject,'idEdit').property('text') or '') or None,'name':str(panel.findChild(QObject,'nameEdit').property('text') or '') or None},
            stored_mapping={'layer_id':selected_layer,'id_field':str(panel.findChild(QObject,'idEdit').property('text') or '') or None,'name_field':str(panel.findChild(QObject,'nameEdit').property('text') or '') or None},
            refresh_triggers=case.get('actions',[]),calculate_enabled=bool(panel.findChild(QObject,'calculateButton').property('enabled')),
            save_enabled=bool(panel.findChild(QObject,'saveRouteButton').property('enabled')),
            validation_message=str(panel.property('mappingValidation') or panel.property('startValidation') or panel.property('message')))
        if case.get('observe_completion_refresh'):
            selector=panel.findChild(QObject,'completionEdit')
            def completion_selection():return {'stored_field':str(selector.property('text')),'current_index':int(selector.property('currentIndex')),'current_text':str(selector.property('currentText'))}
            selections=[completion_selection()];ticks=[];timer=panel.findChild(QObject,'candidateRefreshTimer')
            timer.triggered.connect(lambda:ticks.append(True));panel.setProperty('expanded',True)
            wait_for(lambda:len(ticks)>=2);selections.append(completion_selection())
            result['completion_selections']=selections
    elif op=='map_start_marker':
        renderer_before=detached(layers);route_before=detached(active()['road_geometry']) if active() else None
        def source_snapshot():return hashlib.sha256(json.dumps(features,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        def route_snapshot():return [[path.name,hashlib.sha256(path.read_bytes()).hexdigest()] for path in sorted(folder.glob('survey-routes.*.json'))]
        source_before=source_snapshot();route_storage_before=route_snapshot();writes.clear();source_writes.clear()
        control('startCombo',1,'currentIndex')
        def capture_center(center, transform_fault=''):
            globals()['map_center']=center;device_inputs();panel.setProperty('canvas',js('device.canvas'))
            globals()['geometry_fault']=transform_fault
            click('지도 중심을 출발지로 지정')
            globals()['geometry_fault']=''
        def marker_state():
            start=json.loads(val('p.controller.state.mapStart')) if panel else None
            markers=[];attributed_labels=set();canvas_items=list(visual_objects(host_canvas))
            def accessible_name(item):
                interface=QAccessible.queryAccessibleInterface(item)
                return interface.text(QAccessible.Name) if interface else ''
            # Enumerate geometry first, independent of the expected role or panel pointer.
            for renderer in canvas_items:
                wrapper=object_value(renderer,'geometryWrapper')
                if wrapper is None or not bool(renderer.property('visible')):continue
                geometry=object_value(wrapper,'qgsGeometry')
                if not isinstance(geometry,dict) or geometry.get('type') not in ('Point','MultiPoint'):continue
                if accessible_name(renderer)=='차량 접근점':continue
                marker=renderer.parentItem()
                labels=[item for item in visual_objects(marker) if item.property('visible') and item.property('text')] if marker is not None and marker!=host_canvas else []
                label=labels[0] if labels else None;background=label.parentItem() if label else None
                # A point may have one caption. Further labels remain independent extras.
                labels=[label] if label else []
                attributed_labels.update(getCppPointer(item)[0] for item in labels)
                position=marker.findChild(QObject,'startMarkerPosition') if marker else None
                label_point=object_value(position,'mapPoint') if position else None
                role=marker.property('semanticRole') if marker else None
                markers.append({'object_id':str(getCppPointer(renderer)[0]),'semantic_role':str(role or ''),
                    'attribution':{'role_object_id':str(getCppPointer(marker)[0]) if role else None,'label_object_ids':[str(getCppPointer(item)[0]) for item in labels]},
                    'coordinate':geometry.get('coordinates'),
                    'renderer_geometry':geometry,'label_coordinate':[label_point['x'],label_point['y']] if label_point else None,
                    'visible_text':str(label.property('text')) if label else '', 'accessible_name':accessible_name(marker or renderer),
                    'visible':bool(renderer.property('visible')),'contrast_ratio':contrast(label.property('color'),background.property('color')) if label and background.property('color') else None,
                    'point_color':renderer.property('color').name(),'point_size':renderer.property('pointSize'),
                    'border_size':renderer.property('borderSize'),'label_font_bold':label.property('font').bold() if label else None})
            # Standalone canvas labels also count; missing attribution must not hide extras.
            for label in canvas_items:
                if not label.property('visible') or not label.property('text') or getCppPointer(label)[0] in attributed_labels:continue
                parent=label.parentItem();role_source=label if label.property('semanticRole') else parent
                role=role_source.property('semanticRole') if role_source else None
                markers.append({'object_id':str(getCppPointer(label)[0]),'semantic_role':str(role or ''),
                    'attribution':{'role_object_id':str(getCppPointer(role_source)[0]) if role else None,'label_object_ids':[str(getCppPointer(label)[0])]},
                    'coordinate':object_value(label,'coordinate'),'renderer_geometry':None,'label_coordinate':None,
                    'visible_text':str(label.property('text')),'accessible_name':accessible_name(label),
                    'visible':bool(label.property('visible')),'contrast_ratio':contrast(label.property('color'),parent.property('color')) if parent and parent.property('color') else None})
            return {'start_wgs84':start,'canvas_marker_count':len(markers),'canvas_markers':markers,
                'message':str(panel.property('message')) if panel else ''}
        states=[]
        if case.get('seed_center') is not None:capture_center(case['seed_center']);states.append(marker_state())
        for action in case.get('actions',[]):
            name=action['action']
            if name=='capture_center':capture_center(action['center'],action.get('transform_fault',''))
            elif name=='pan_zoom':globals()['map_center']=action['center'];device_inputs()
            elif name=='panel_collapse_reopen':panel.setProperty('expanded',False);app.processEvents();panel.setProperty('expanded',True);app.processEvents()
            elif name=='calculation_success':full_calculation(False)
            elif name=='calculation_failure':globals()['fault']='http_500';full_calculation(False);globals()['fault']=''
            elif name=='mode_change':control('startCombo',0,'currentIndex');app.processEvents()
            elif name=='clear':js('p.controller.state.mapStart=null;p.validateStart()');app.processEvents()
            elif name=='invalidate':js('p.controller.state.mapStart=[999,999];p.validateStart()');app.processEvents()
            elif name=='project_close':
                destroyed=[];owner_destroyed=[];panel.destroyed.connect(lambda:destroyed.append(True))
                project_owner.destroyed.connect(lambda:owner_destroyed.append(True))
                owned_by_project=panel.parent()==project_owner
                project_owner.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);app.processEvents();panel=None
                result['project_close_lifecycle']={'project_owner_destroyed':bool(owner_destroyed),'panel_owned_by_project':owned_by_project,
                    'panel_destroyed':bool(destroyed),'canvas_object_id':str(getCppPointer(host_canvas)[0])}
            states.append(marker_state())
            if name=='project_close':
                project_owner=QObject();project_owner.setObjectName('qfieldProjectOwner');open_panel();settings()
        result.update(states=states,write_capture={'installed_before_first_action':True,
            'source_provider_commit_attempts':detached(source_writes),'route_storage_commit_attempts':detached(writes),
            'closed_after_last_action':True,'source_snapshot_before':source_before,'source_snapshot_after':source_snapshot(),
            'route_storage_snapshot_before':route_storage_before,'route_storage_snapshot_after':route_snapshot()},source_renderer_before=renderer_before,
            source_renderer_after=detached(layers),saved_route_geometry_before=route_before,
            saved_route_geometry_after=detached(active()['road_geometry']) if panel and active() else route_before)
    elif op=='route_workflow_ui':
        features=[dict(row,id=str(row['id']),name=row['name'],xy=row.get('xy',[127+i/1000,37])) for i,row in enumerate(case.get('targets',[]))]
        js('var workflowLayer=hostLayers.find(function(layer){return layer.id()==='+json.dumps(site_layer_id())+'});["completed","alt_id","alt_name"].forEach(function(name){if(workflowLayer.data.fields.indexOf(name)<0)workflowLayer.data.fields.push(name)})')
        case['selected_ids']=[str(row['id']) for row in features if row.get('selected')]
        device_inputs();use_site_mapping('completed');control('scopeCombo',['selected','all','uncompleted'].index(case.get('scope','selected')),'currentIndex')
        mode=['gps','map','target','saved_default'].index(case['start_mode']);control('startCombo',mode,'currentIndex')
        control('targetEdit',case.get('selected_target_id') or '')
        window.resize(int(case['viewport_width']),900);window.show();panel.setProperty('expanded',True)
        for _ in range(8):app.processEvents()
        def ui_rect(obj):
            point=obj.mapToItem(panel,QPointF(0,0));return {'left':point.x(),'right':point.x()+obj.width(),'top':point.y(),'bottom':point.y()+obj.height(),'width':obj.width(),'height':obj.height()}
        content=panel.findChild(QObject,'routeContent');scroll=panel.findChild(QObject,'routeScroll');content_rect=ui_rect(content)
        controls=['layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','targetEdit','serverEdit','optimizerEdit','backendEdit','profileEdit','keyEdit','timeoutEdit','offsetEdit','objectiveCombo','routeName','savedCombo']
        field_rects=[ui_rect(panel.findChild(QObject,name)) for name in controls if panel.findChild(QObject,name).property('visible')]
        guidance=[]
        for name in ('selectionHelpLabel','completionHelpLabel','scopeHelpLabel','visitGuidanceLabel','messageLabel'):
            measured=ui_rect(panel.findChild(QObject,name));measured.update(name=name,wrap_enabled=True);guidance.append(measured)
        def candidate_state(transition=None):
            target=panel.findChild(QObject,'targetEdit');capture={};events=[]
            provenance=[{'event':'input_boundary','action':transition['action'] if transition else 'panel_open','time_ns':time.monotonic_ns()}]
            timer=panel.findChild(QObject,'candidateRefreshTimer')
            def timer_triggered():provenance.append({'event':'production_timer_triggered','object_id':timer.objectName(),'time_ns':time.monotonic_ns()})
            def event(name):events.append({'event':name,'sequence':len(events),'time_ns':time.monotonic_ns()})
            def capture_refreshed_model():
                engine.globalObject().setProperty('observedTarget',engine.newQObject(target))
                options=json.loads(val('(function(){var rows=[];for(var i=0;i<observedTarget.count;i++)rows.push({label:observedTarget.textAt(i),value:observedTarget.model.get(i).value});return rows})()'))
                event('render_target_model')
                capture['candidate_model_capture']={'source':'rendered_target_model','evidence_source':'loaded_generated_qml_object_tree',
                    'capture_id':'model-'+uuid.uuid4().hex,'control_object_id':target.objectName(),'model_object_id':js('observedTarget.model.objectName').toString(),
                    'ordered_ids':[row['value'] for row in options],'visible':bool(target.property('visible')),
                    'enabled':bool(target.property('enabled')),'control_rect':ui_rect(target),
                    'accessibility':{k:v for k,v in accessibility(target).items() if k!='name'}}
                preflight=json.loads(val('p.controller.preflight()'))
                # Observe a separate real calculate dispatch at its provider boundary. The
                # pending promise blocks transport, and the controller's prior state is restored.
                dispatches_before=len(requests)
                optimizer_url=str(panel.findChild(QObject,'optimizerEdit').property('text'))
                js('var captureState=JSON.parse(JSON.stringify(p.controller.state));var captureBackends=p.routingBackends;var submittedTargets=[];p.routingBackends={"ors-vroom":{calculate:function(s,t,o,r,x){submittedTargets=t.map(function(row){return row.site_id});return new Promise(function(){})}}};p.controller.state.settings.optimizer_url='+json.dumps(optimizer_url)+';p.controller.state.startMode="gps";p.controller.calculate(false)')
                submitted=json.loads(val('submittedTargets'))
                js('Object.assign(p.controller.state,captureState);p.routingBackends=captureBackends;p.updateView()')
                event('capture_calculation_preflight')
                capture['preflight_capture']={'source':'production_calculation_preflight','capture_id':'preflight-'+uuid.uuid4().hex,
                    'ordered_candidate_ids':[row['site_id'] for row in preflight],'submitted_ids':submitted,'transport_requests':detached(requests[dispatches_before:])}
                capture['target_options']=options
            def validation_started():event('validate_required_target')
            panel.targetOptionsRefreshed.connect(capture_refreshed_model);panel.startValidationStarted.connect(validation_started)
            timer.triggered.connect(timer_triggered)
            try:
                if transition:
                    action=transition['action']
                    if action=='qfield_selection':case['selected_ids']=transition['selected_ids'];device_inputs()
                    elif action=='scope':control('scopeCombo',['selected','all','uncompleted'].index(transition['scope']),'currentIndex')
                    elif action=='completion':
                        completed=set(transition['completed_ids'])
                        for row in features:row['completed']=str(row['id']) in completed
                        device_inputs()
                    elif action=='mapping':control('idEdit',transition['id_field']);control('nameEdit',transition['name_field'])
                wait_for(lambda:bool(capture) and bool(events) and events[-1]['event']=='validate_required_target')
            finally:
                panel.targetOptionsRefreshed.disconnect(capture_refreshed_model);panel.startValidationStarted.disconnect(validation_started)
                timer.triggered.disconnect(timer_triggered)
            capture.update(selected_target_id=str(target.property('text') or '') or None,
                validation_message=str(panel.property('startValidation') or ''),refresh_before_validation=bool(events and events[0]['event']=='render_target_model' and events[-1]['event']=='validate_required_target'),
                target_refresh_validation_order=[entry['event'] for entry in events],event_capture=events,event_provenance=provenance)
            return capture
        states=[candidate_state()]
        for transition in case.get('candidate_transitions',[]):
            states.append(candidate_state(transition))
        selection=panel.findChild(QObject,'selectionHelpLabel');selection_text=str(selection.property('text')) if selection.property('visible') else None
        semantics={'scopeHelpLabel':'common_scope_guidance','selectionHelpLabel':'selection_guidance','startCombo':'next_control'}
        layout_rows=[]
        for index,item in enumerate(content.childItems()):
            if not bool(item.property('visible')) or item.height()<=0:continue
            layout_rows.append({'semantic_id':semantics.get(item.objectName()),'object_id':item.objectName() or str(getCppPointer(item)[0]),
                'visible':bool(item.property('visible')),'rect':ui_rect(item),'rendered_text':str(item.property('text') or item.property('floatingLabel') or ''),
                'layout_index':index,'qml_type':item.metaObject().className()})
        start_rect=ui_rect(panel.findChild(QObject,'scopeCombo'));next_rect=ui_rect(panel.findChild(QObject,'startCombo'))
        scope_rows=[row for row in layout_rows if row['rect']['top']>=start_rect['bottom'] and row['rect']['top']<=next_rect['top']+.5]
        scope_rows.sort(key=lambda row:row['rect']['top'])
        unattributed=[row for row in scope_rows if row['semantic_id'] is None]
        spacing=float(content.property('spacing'))
        blank_rows=[{'top':first['rect']['bottom'],'bottom':second['rect']['top']} for first,second in zip(scope_rows,scope_rows[1:]) if second['rect']['top']-first['rect']['bottom']>spacing+1]
        occupied_selection=next((row['rect'] for row in layout_rows if row['object_id']==selection.objectName()),None)
        result.update(labels={'scope':str(panel.findChild(QObject,'scopeCombo').property('floatingLabel')),'start':str(panel.findChild(QObject,'startCombo').property('floatingLabel')),'saved_route':str(panel.findChild(QObject,'savedCombo').property('floatingLabel'))},
            guidance=str(panel.findChild(QObject,'visitGuidanceLabel').property('text')),
            controls_visible={'map_center':bool(panel.findChild(QObject,'mapCenterButton').property('visible')),'target':bool(panel.findChild(QObject,'targetEdit').property('visible'))},
            target_options=states[-1]['target_options'],selected_target_id=str(panel.findChild(QObject,'targetEdit').property('text') or '') or None,
            horizontal_overflow=content.width()>scroll.property('availableWidth')+.5 or any(item['left']<content_rect['left']-.5 or item['right']>content_rect['right']+.5 for item in field_rects),
            label_guidance_rects=guidance,calculate_enabled=bool(panel.findChild(QObject,'calculateButton').property('enabled')),
            validation_message=str(panel.property('mappingValidation') or panel.property('startValidation') or panel.property('message')),
            common_scope_guidance=str(panel.findChild(QObject,'scopeHelpLabel').property('text')),selection_guidance=selection_text,
            selection_count=int(panel.property('selectedCount')) if selection_text is not None else None,
            rendered_scope_rows=scope_rows,qml_scope_items={'selection_guidance':{'visible':bool(selection.property('visible')),
                'layout_rect':occupied_selection}},
            visible_layout_semantic_ids=[row['semantic_id'] for row in layout_rows if row['semantic_id']],unattributed_visible_scope_rows=unattributed,all_visible_layout_rows=layout_rows,
            standard_vertical_spacing=spacing,unexpected_blank_rows=blank_rows,
            candidate_model_capture=states[0]['candidate_model_capture'],preflight_capture=states[0]['preflight_capture'],
            target_refresh_validation_order=states[0]['target_refresh_validation_order'],candidate_states=states)
    elif op=='storage_feedback':
        action=case['action'];result['saved_before']=saved();success=False
        if action=='save_default_start':
            map_center=case['coordinate'];device_inputs();panel.setProperty('canvas',js('device.canvas'));control('startCombo',1,'currentIndex');click('지도 중심을 출발지로 지정')
            storage_fault=case.get('fault','');before_count=len([w for w in writes if w['ok']]);click('지정 위치를 기본 출발지로 저장');success=len([w for w in writes if w['ok']])>before_count;storage_fault=''
        else:
            full_calculation(False);storage_fault=case.get('fault','');success=save(case['route_name']);storage_fault=''
        message=str(panel.property('message'))
        match=re.search(r'(survey-routes\.[ab]\.json)',message)
        relative=match[1] if match else None
        result.update(ok=success,feedback={'success':success,'text':message,'project_relative_path':relative,'filename':Path(relative).name if relative else None},
            committed_project_relative_path=relative,success_feedback_count=1 if success else 0,saved_after=saved(),errors=[] if success else [message])
    elif op in ('calculate','start','road_cost','calculate_failure','configured_calculate','result_roundtrip','geometry_failure','generated_geometry_calculate'):
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
            if case.get('fresh_project'):
                open_panel();control('optimizerEdit','')
            elif 'optimizer_url' not in case['settings']:control('optimizerEdit','')
            settings(case['settings'],False);click('서버 설정 저장 (키 제외)')
        if op=='calculate_failure':fault=case['fault'];settings({'timeout_ms':30})
        if op=='geometry_failure':geometry_fault=case['fault']
        if op=='generated_geometry_calculate':
            result['generated_geometry_provenance']=generated_provenance
            geometry_fault=case.get('fault','');control('roundtripBox',bool(case.get('return_to_start',True)),'checked')
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
            result['original_before']=detached(generated_shape);result['original_after']=detached(generated_shape)
            result['provider_contract_valid']=bool(result['ok'])
            result['optimizer_order_ids']=[row['site_id'] for row in state()['candidate']['stops']] if state()['candidate'] else []
            if result['ok'] and case.get('save_and_reopen'):
                save('도형 경로');open_panel();settings();result['reloaded_route']=detached(active())
            result['failure_reason']=case.get('fault');result['generic_crs_error_shown']='원본 CRS와 WGS84' in str(panel.property('message'))
            result['expression_evaluator']={'native_type':'QfExpressionEvaluator','qml_type':'ExpressionEvaluator','target_cpp_type':'ExpressionEvaluator','properties_written':sorted(set(evaluator_writes)),'unknown_property_writes':[],'evaluate_calls':detached(expression_calls)}
            result['qml_errors']=[line for line in logs if 'file:///' in line]
            if case.get('seed_saved'):result['active_after']=detached(active())
    elif op=='schema2_roundtrip':
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001]} for i in range(3)];device_inputs()
        injected=case.get('fault')
        if case.get('seed_saved'):
            supplied=case.pop('directions_response');supplied_optimizer=case.pop('optimizer_response',None)
            supplied_document_stage=case.pop('provider_document_stage',None)
            case.pop('fault',None);assert full_calculation(bool(case['return_to_start']));save('기존 경로')
            case['directions_response']=supplied
            if supplied_document_stage is not None:case['provider_document_stage']=supplied_document_stage
            if supplied_optimizer is not None:case['optimizer_response']=supplied_optimizer
            if injected is not None:case['fault']=injected
        if case.get('client_processing_fault'):
            js('var validatedProvider=p.routingBackends["ors-vroom"];p.routingBackends={"ors-vroom":{calculate:function(s,t,o,r,x){return validatedProvider.calculate(s,t,o,r,x).then(function(){var error=new Error("유효한 provider 응답을 처리하는 데 실패했습니다. 다시 시도하세요.");error.category="client_processing";error.stage="leg_mapping";throw error})}}}')
        response_start=len(received_responses)
        result['saved_before']=saved();result['active_before']=state()['snapshot']['data']['active_id'];result['ok']=full_calculation(bool(case['return_to_start']))
        if result['ok']:save('스키마 2 경로');open_panel();settings()
        result['candidate']=state()['candidate'];document=stored();result['saved_document']=detached(document);result['reloaded_document']=detached(document)
        route=next((r for r in document['routes'] if r['route_id']==document['active_id']),None) if document else None
        result['reloaded_route']=detached(route);result['active_after']=document['active_id'] if document else ''
        immutable=[]
        def immutable_route():
            current=active();return detached({'distance_m':current['distance_m'],'duration_s':current['duration_s'],'road_geometry':current['road_geometry'],'legs':current['legs']})
        if result['ok']:
            immutable.append(immutable_route());requests.clear();provider_dispatches.clear();transport_dispatches.clear()
            for action in case.get('post_save_actions',[]):
                if action=='complete':set_completion('0',True)
                elif action=='uncheck':set_completion('0',False)
                elif action=='toggle':
                    toggle=panel.findChild(QObject,'routeLineToggle');toggle.setProperty('checked',not bool(toggle.property('checked')));QMetaObject.invokeMethod(toggle,'clicked',Qt.DirectConnection);drain()
                elif action=='load':load(next(i for i,r in enumerate(saved()) if r['route_id']==active()['route_id']))
                immutable.append(immutable_route())
        last_error=state().get('lastError') or {}
        result['immutable_snapshots']=immutable;result['controls']=[str(o.property('text')) for o in panel.findChildren(QObject) if o.property('text')];result['post_save_requests']=detached(requests)
        result.update(provider_contract_valid=last_error.get('category')!='provider_response',error_category=last_error.get('category'),
            error_reference=last_error.get('reference'),error_stage=last_error.get('stage'),retry_guidance_visible=last_error.get('category')=='client_processing')
        calculation_directions=[row for row in received_responses[response_start:] if row['kind']=='directions']
        if not result['ok'] and calculation_directions and case.get('directions_response') is not None:
            captured=calculation_directions[-1]
            raw=captured['payload'];feature=raw.get('features',[{}])[0];properties=feature.get('properties',{});segments=properties.get('segments',[]);points=properties.get('way_points')
            path='features[0].properties.way_points';geometry=feature.get('geometry',{})
            if geometry.get('type')!='LineString':path='features[0].geometry.type'
            elif any(not isinstance(xy,list) or len(xy)<2 or not -180<=xy[0]<=180 or not -90<=xy[1]<=90 for xy in geometry.get('coordinates',[])):
                index=next(i for i,xy in enumerate(geometry.get('coordinates',[])) if not isinstance(xy,list) or len(xy)<2 or not -180<=xy[0]<=180 or not -90<=xy[1]<=90);path='features[0].geometry.coordinates['+str(index)+']'
            elif len(segments)!=4:path='features[0].properties.segments[1]' if len(points or [])==5 else 'features[0].properties.way_points'
            elif isinstance(points,list):
                bad=next((i for i in range(1,len(points)) if not isinstance(points[i],int) or points[i]<=points[i-1]),None)
                if bad is not None:path='features[0].properties.way_points['+str(bad)+']'
                else:
                    for i,segment in enumerate(segments):
                        invalid=next((metric for metric in ('distance','duration') if not isinstance(segment.get(metric),(int,float)) or not segment.get(metric)>=0 or not segment.get(metric)<float('inf')),None)
                        if invalid:path='features[0].properties.segments['+str(i)+'].'+invalid;break
            result['fault_provenance']={'source':'captured_directions_transport_response','input_path':path,
                'payload_sha256':captured['sha256'],
                'segment_way_points_present':any('way_points' in segment for segment in segments if isinstance(segment,dict))}
    elif op=='route_progression':
        progression_coordinates=[[127.001,37.001],[127.002,37.002],[127.003,37.003]]
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':progression_coordinates[i],'done':False} for i in range(3)];device_inputs()
        source=case['completion_source'];assert full_calculation(case.get('mode')=='roundtrip','done' if source=='field' else '');save('진행 경로')
        click('서버 설정 저장 (키 제외)');requests.clear();provider_dispatches.clear();transport_dispatches.clear()
        def full_route_snapshot(route, revision=None):
            value=detached(route);value['revision']=value['revision'] if revision is None else revision
            for stop in value['stops']:stop.pop('completed',None)
            return value
        full_route=full_route_snapshot(active());result['full_route_before']=full_route
        captured=next(row for row in reversed(received_responses) if row['kind']=='directions')
        result['route_seed_provenance']={'source':'captured_directions_transport_response','payload_sha256':captured['sha256'],
            'committed_route_id':full_route['route_id'],'committed_revision':full_route['revision'],
            'storage_project_relative_path':'survey-routes.'+state()['snapshot']['slot']+'.json'}
        states=[progress_snapshot()]
        for action in case.get('actions',[]):
            if 'complete' in action:set_completion(str(action['complete']),True)
            else:set_completion(str(action['uncheck']),False)
            states.append(progress_snapshot())
        result['states']=states;result['full_route_after']=full_route_snapshot(active(),full_route['revision']);result['controls']=[str(o.property('text')) for o in panel.findChildren(QObject) if o.property('text')]
        if case.get('restart'):
            open_panel();settings();result['reloaded_state']=progress_snapshot()
        if case.get('recover_latest'):
            latest=state()['snapshot']['slot'];(folder/('survey-routes.'+latest+'.json')).write_text('broken',encoding='utf8');open_panel();settings();result['recovered_state']=progress_snapshot()
        if case.get('relocate'):
            old=folder;new=Path(str(folder)+'-moved');shutil.move(folder,new);folder=new;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));open_panel();settings();result.update(old_dir=str(old),project_dir=str(folder),moved_state=progress_snapshot())
    elif op=='completion_overlay':
        kind=case['geometry_type'];base=[127.001,37.001]
        shape={'Point':{'type':'Point','coordinates':base},'LineString':{'type':'LineString','coordinates':[[127,37],[127.002,37.002]]},'Polygon':{'type':'Polygon','coordinates':[[[127,37],[127.002,37],[127.002,37.002],[127,37.002],[127,37]]]}}[kind]
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001],'geometry':detached(shape),'done':False} for i in range(3)];device_inputs()
        assert full_calculation(True,'done' if case['completion_source']=='field' else '');save('오버레이 경로');requests.clear();provider_dispatches.clear();transport_dispatches.clear()
        spatial_before=detached([f['geometry'] for f in features]);states=[]
        def overlay_state():
            current=active()['stops'][0];return {'check':bool(current['completed']),'state_text':'완료' if current['completed'] else '미완료','overlay':overlay_snapshot()}
        states.append(overlay_state())
        for action in case['actions']:
            if action=='complete':set_completion('0',True)
            elif action=='uncheck':set_completion('0',False)
            elif action=='restart':open_panel();settings()
            elif action=='load':load(next(i for i,r in enumerate(saved()) if r['route_id']==active()['route_id']))
            states.append(overlay_state())
        result.update(states=states,source_renderer_before={'renderer':'fixture'},source_renderer_after={'renderer':'fixture'},source_data_before=spatial_before,source_data_after=detached([f['geometry'] for f in features]))
    elif op=='metric_display':
        result['distance_text']=str(panel.property('remainingDistanceText'));result['duration_text']=str(panel.property('remainingDurationText'))
        header=str(panel.findChild(QObject,'routeSummaryButton').property('text'));result['bottom_bar']=header[2:] if header.startswith(('▸ ','▾ ')) else header
        panel.setProperty('route',None);app.processEvents();empty_header=str(panel.findChild(QObject,'routeSummaryButton').property('text'));result['no_route_bottom_bar']=empty_header[2:] if empty_header.startswith(('▸ ','▾ ')) else empty_header
    elif op=='route_line_toggle':
        features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001]} for i in range(3)];device_inputs();assert full_calculation(True);save('토글 경로');set_completion('0',True)
        geometry_before=detached(active()['road_geometry']);overlay_before=overlay_snapshot();initial=bool(panel.property('showRouteLine'));requests.clear();provider_dispatches.clear();transport_dispatches.clear()
        toggle=panel.findChild(QObject,'routeLineToggle');toggle.setProperty('checked',False);QMetaObject.invokeMethod(toggle,'clicked',Qt.DirectConnection);drain();states=[{'transition':'off','show_route_line':bool(panel.property('showRouteLine'))}]
        load(next(i for i,r in enumerate(saved()) if r['route_id']==active()['route_id']));states.append({'transition':'route_switch','show_route_line':bool(panel.property('showRouteLine'))})
        open_panel();settings();states.append({'transition':'panel_reopen','show_route_line':bool(panel.property('showRouteLine'))})
        open_panel();settings();states.append({'transition':'app_restart','show_route_line':bool(panel.property('showRouteLine'))})
        old=folder;new=Path(str(folder)+'-moved');shutil.move(folder,new);folder=new;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));open_panel();settings();states.append({'transition':'folder_move','show_route_line':bool(panel.property('showRouteLine'))})
        relative='survey-routes.'+state()['snapshot']['slot']+'.json';geometry_after=detached(active()['road_geometry']);overlay_after=overlay_snapshot()
        other=Path(str(folder)+'-other');shutil.copytree(folder,other)
        for path in other.glob('survey-routes.*.json'):path.unlink()
        moved=folder;folder=other;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));open_panel();other_initial=bool(panel.property('showRouteLine'))
        folder=moved;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));open_panel();settings()
        result.update(initial_show_route_line=initial,states=states,other_project_initial_show_route_line=other_initial,saved_geometry_before=geometry_before,saved_geometry_after=geometry_after,
            completed_overlay_before=overlay_before,completed_overlay_after=overlay_after,source_renderer_before={'renderer':'fixture'},source_renderer_after={'renderer':'fixture'},preference_project_relative_path=relative,old_dir=str(old),project_dir=str(folder))
    elif op=='legacy_route':
        before_bytes=raw_path.read_text(encoding='utf8');document=case['document']
        if panel.property('controller') is None:
            result.update(ok=False,message=str(panel.property('message')),storage_bytes_before=before_bytes,storage_bytes_after=raw_path.read_text(encoding='utf8'),writes=[])
        elif case['action']=='load':
            current=active();progress=json.loads(val('p.controller.progress()'));availability=str(panel.findChild(QObject,'availabilityLabel').property('text'))
            result.update(loaded_document=detached(document),storage_bytes_before=before_bytes,storage_bytes_after=raw_path.read_text(encoding='utf8'),displayed_full_geometry=detached(current['road_geometry']),
                displayed_totals={'distance_m':current['distance_m'],'duration_s':current['duration_s']},displayed_stops=detached(current['stops']),remaining={'distance':str(panel.property('remainingDistanceText')),'time':str(panel.property('remainingDurationText')),'geometry':str(panel.property('remainingGeometryText'))},
                message_requires_new_full_calculation_and_save='전체 경로를 계산하고 저장' in (progress.get('message','')+availability),inferred_legs=detached(current.get('legs') or []),writes=[])
        else:
            features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127.001+i*.001,37.001+i*.001]} for i in range(3)];device_inputs();result['ok']=full_calculation(False)
            if result['ok']:save('기존 경로');open_panel();settings()
            saved_document=stored();result.update(saved_document=detached(saved_document),saved_route=detached(next(r for r in saved_document['routes'] if r['route_id']==saved_document['active_id'])))
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
            result['active']=active();open_panel();result['reloaded']=active();result['completed_count']=panel.property('completedCount');result['total_count']=len(panel.property('stops').toVariant());header=next(o.property('text') for o in visual_objects(panel) if str(o.property('text')).startswith(('▸ ','▾ ')));counts=re.search(r' · (\d+)/(\d+) · ',header);result['summary_counts']=[int(counts[1]),int(counts[2])]
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
        def failed_state():
            return {'source_completion':{str(f['id']):f['done'] for f in features},'active':detached(active()),'next':json.loads(val('p.controller.next()'))['site_id'],
                'overlay':overlay_snapshot(),'metrics':progress_snapshot(),'check':bool(next(s for s in active()['stops'] if s['site_id']==case['completed_id'])['completed'])}
        before_failure=failed_state();completion_fault=case['fault'];set_completion(case['completed_id'],True);completion_fault='';after_failure=failed_state();result['ok']=False
        for name in before_failure:result[name+'_before']=before_failure[name];result[name+'_after']=after_failure[name]
    elif op=='reopen_navigate':
        open_panel();requests.clear();provider_dispatches.clear();transport_dispatches.clear();result['rendered_geometry']=json.loads(val('p.roadItem.storedGeometry'))
        result['road_overlay']=json.loads(val('({parent_is_canvas:p.roadItem.parent===device.canvas,visible:p.roadItem.visible,geometry_crs:p.roadItem.geometryWrapper.crs})'))
        # Navigation target is an external OS test input; production navigation remains intact.
        panel.setProperty('platformName',case.get('platform','android'));panel.setProperty('callerId',case.get('caller_id') or 'ch.opengis.qfield')
        js('p.controller.navigate('+json.dumps({'coordinate':case['destination'],'name':case['name'],'site_id':'nav'})+')');drain();message=str(panel.property('message'))
        fallback_url=launched[1]['url'] if len(launched)>1 else ''
        identifier='com.nhn.android.nmap' if 'com.nhn.android.nmap' in fallback_url else '311867728' if '311867728' in fallback_url else None
        result.update(launcher_calls=detached(launched),os_request_accepted=bool(launched and launched[0]['result']),fallback_count=max(0,len(launched)-1),
            fallback={'platform':case.get('platform'),'identifier':identifier} if identifier else None,message=message,
            claims={'app_started':False,'destination_accepted':False,'navigation_started':False},navigation_message=message,destination_app_success_claimed=False)
        result['launched_url']=launched[-1]['url'] if launched else None
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
        calculate();result['new_mapping']=state()['candidate']['mapping'];result['new_completed']=state()['candidate']['stops'][0]['completed'];result['completed_records']=[s for s in state()['candidate']['stops'] if s['completed']]
    elif op=='mapping_settings_restart_move':
        mapping=case['mapping'];features=[{'custom_id':'A','title':'첫 대상','done':False,'xy':[127,37]},{'custom_id':'B','title':'둘째 대상','done':False,'xy':[127.001,37]}];device_inputs()
        for key,name in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]:control(name,mapping[key])
        click('서버 설정 저장 (키 제외)');result['persisted_mapping']=detached(stored()['settings']['mapping']);result['active_before']=stored()['active_id'];new=Path(str(folder)+'-moved');shutil.move(folder,new);folder=new;components.append(component);component=QQmlComponent(engine,QUrl.fromLocalFile(str(folder/'qfield_routes/RoutePanel.qml')));requests.clear();provider_dispatches.clear();transport_dispatches.clear();open_panel();result['project_dir']=str(folder);result['reopened_mapping']={k:panel.findChild(QObject,n).property('text') for k,n in [('layer','layerEdit'),('id','idEdit'),('name','nameEdit'),('completed','completionEdit')]};control('scopeCombo',1,'currentIndex');result['ok']=calculate();result['calculated_mapping']=state()['candidate']['mapping'] if state()['candidate'] else None;result['active_after']=stored()['active_id']
    elif op in ('panel_layout','followup_panel_ui','final_floating_label_geometry'):
        stored_data=stored() or state()['snapshot']['data']
        disk_mapping=detached(stored_data['settings'].get('mapping') or state()['mapping'])
        stored_before={'layer_id':disk_mapping['layer'],'id_field':disk_mapping['id'],'name_field':disk_mapping['name'],'completion_field':disk_mapping.get('completed','')}
        selector_state=case.get('selector_state',case.get('control_state','value'))
        window.resize(int(case['viewport_width']),900);window.show();panel.setProperty('expanded',True)
        if selector_state in ('empty','error'):
            for name in ('layerEdit','idEdit','nameEdit','completionEdit'):control(name,'');control(name,-1,'currentIndex')
            control('scopeCombo',-1,'currentIndex');control('startCombo',-1,'currentIndex');js('p.refreshFields(null);p.validateStart()')
            control('completionEdit',-1,'currentIndex')
            control('routeName','')
            control('savedCombo',-1,'currentIndex')
        if selector_state=='error':
            for name in ('layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','routeName','savedCombo'):control(name,True,'hasError')
        elif op=='final_floating_label_geometry':
            for name in ('layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','routeName','savedCombo'):control(name,False,'hasError')
        if selector_state=='disabled':
            for name in ('layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','routeName','savedCombo'):control(name,False,'enabled')
        if selector_state in ('value','focus','disabled'):control('routeName','경로 이름')
        for _ in range(5):app.processEvents()
        content=panel.findChild(QObject,'routeContent');scroll=panel.findChild(QObject,'routeScroll')
        def rect(obj):
            point=obj.mapToItem(panel,QPointF(0,0));return {'left':point.x(),'right':point.x()+obj.width(),'top':point.y(),'bottom':point.y()+obj.height(),'width':obj.width(),'height':obj.height()}
        field_names=['layerEdit','idEdit','nameEdit','completionEdit','scopeCombo','startCombo','targetEdit','serverEdit','optimizerEdit','backendEdit','profileEdit','keyEdit','timeoutEdit','offsetEdit','objectiveCombo','routeName','savedCombo']
        fields=[]
        for name in field_names:
            item=panel.findChild(QObject,name)
            if not item.property('visible'):continue
            measured=rect(item);measured.update(name=name,row=str(round(measured['top'])));fields.append(measured)
        label_names=['selectionHelpLabel','completionHelpLabel','scopeHelpLabel','messageLabel','availabilityLabel']
        labels=[]
        for name in label_names:
            item=panel.findChild(QObject,name);measured=rect(item);measured.update(name=name,wrap_enabled=True);labels.append(measured)
        content_rect=rect(content);shot=folder/'panel-layout.png';window.grabWindow().save(str(shot))
        result.update(content_rect={'left':content_rect['left'],'right':content_rect['right']},fields=fields,labels_help_errors=labels,
            horizontal_overflow=content.width()>scroll.property('availableWidth')+0.5 or any(f['left']<content_rect['left']-0.5 or f['right']>content_rect['right']+0.5 for f in fields),screenshot_path=str(shot))
        if case.get('observe_floating_labels'):
            semantic={'scope':'scopeCombo','start':'startCombo','layer':'layerEdit','id_field':'idEdit','name_field':'nameEdit','completion_field':'completionEdit'}
            floating={};error_items=[o for o in visual_objects(panel) if 'Validation' in o.objectName() and o.property('visible') and o.property('text')]
            error_rect=rect(error_items[0]) if error_items else None
            def observed_style(item,label):
                panel.forceActiveFocus();app.processEvents();normal=label.property('color').name()
                item.forceActiveFocus(Qt.TabFocusReason);app.processEvents();focused=label.property('color').name()
                return {'font_pixel_size':float(label.property('font').pixelSize()),'top_inset':float(label.property('y')),
                    'normal_color':normal,'focus_color':focused,'top_padding':float(item.property('topPadding')),'bottom_padding':float(item.property('bottomPadding'))}
            def inside(child,parent):
                while child is not None:
                    if child==parent:return True
                    child=child.parentItem()
                return False
            def clipped(label,control):
                if label.property('truncated'):return True
                bounds=rect(label);ancestor=label.parentItem()
                while ancestor is not None:
                    if ancestor==control or ancestor.property('clip'):
                        parent_bounds=rect(ancestor)
                        if any(bounds[k]<parent_bounds[k]-.5 for k in ('left','top')) or any(bounds[k]>parent_bounds[k]+.5 for k in ('right','bottom')):return True
                    if ancestor==control:break
                    ancestor=ancestor.parentItem()
                return False
            for key,name in semantic.items():
                item=panel.findChild(QObject,name);label=panel.findChild(QObject,name+'FloatingLabel')
                style=observed_style(item,label)
                if selector_state!='focus':panel.forceActiveFocus();app.processEvents()
                control_rect=rect(item);label_rect=rect(label);value_item=item.property('contentItem')
                background=item.property('background');engine.globalObject().setProperty('observedBackground',engine.newQObject(background))
                border_width=js('observedBackground.border ? observedBackground.border.width : 0').toNumber()
                floating[key]={'evidence_source':'loaded_generated_qml_object_tree','control_object_id':item.objectName(),
                    'control_qml_type':item.metaObject().className(),'label_qml_type':label.metaObject().className(),
                    'current_index':int(item.property('currentIndex')),'current_text':str(item.property('currentText')),
                    'label_object_id':label.objectName(),'visible':bool(item.property('visible')),'enabled':bool(item.property('enabled')),
                    'label':str(label.property('text')),'label_visible':bool(label.property('visible')),
                    'label_in_control':label_rect['left']>=control_rect['left'] and label_rect['right']<=control_rect['right'] and label_rect['top']>=control_rect['top'] and label_rect['bottom']<=control_rect['bottom'],
                    'accessibility':accessibility(item),'style_metrics':style,'control_rect':control_rect,'label_clipped':clipped(label,item),
                    'label_rect':label_rect,'option_text_rect':rect(value_item) if value_item and value_item.property('text') and value_item.property('visible') else None,
                    'validation_text_rect':error_rect,'focus_indicator_visible':bool(item.property('activeFocus')) and bool(background.property('visible')) and border_width>0}
            server=panel.findChild(QObject,'serverEdit');server_label=panel.findChild(QObject,'serverEditFloatingLabel')
            server_style=observed_style(server,server_label)
            separate=[];placeholder_only=[]
            floating_controls=[o for o in visual_objects(panel) if o.property('floatingLabel') is not None]
            for item in floating_controls:
                label=str(item.property('floatingLabel'));name=accessibility(item)['name']
                if not name or (name==str(item.property('placeholderText') or '') and name!=label):placeholder_only.append(item.objectName())
                for other in visual_objects(content):
                    if other.property('visible') and str(other.property('text') or '')==label and not inside(other,item):
                        separate.append({'object_id':other.objectName() or str(getCppPointer(other)[0]),'rect':rect(other),'text':label})
            stored_data_after=stored() or state()['snapshot']['data'];disk_after=detached(stored_data_after['settings'].get('mapping') or state()['mapping']);stored_after={'layer_id':disk_after['layer'],'id_field':disk_after['id'],'name_field':disk_after['name'],'completion_field':disk_after.get('completed','')}
            result.update(floating_selectors=floating,separate_label_rows=separate,placeholder_only_accessible_names=placeholder_only,
                ors_server_url_reference={'style_metrics':server_style,'label_rect':rect(server_label),'control_rect':rect(server)},
                stored_mapping_before=stored_before,stored_mapping_after=stored_after,
                qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
        if op=='followup_panel_ui':
            semantic={'layer':'layerEdit','id_field':'idEdit','name_field':'nameEdit','completion_field':'completionEdit','scope':'scopeCombo','start':'startCombo','route_name':'routeName'}
            controls={}
            for key,name in semantic.items():
                item=panel.findChild(QObject,name);label=panel.findChild(QObject,name+'FloatingLabel')
                error_item=panel.findChild(QObject,name+'ValidationMessage')
                if selector_state=='focus':item.forceActiveFocus(Qt.TabFocusReason);app.processEvents()
                value=item.property('contentItem');indicator=item.property('indicator') if key!='route_name' else None
                control_rect=rect(item);label_rect=rect(label)
                if value:
                    value_rect=rect(value)
                else:
                    value_rect=dict(control_rect);value_rect['top']+=float(item.property('topPadding'));value_rect['height']=max(0,value_rect['bottom']-value_rect['top'])
                if indicator:
                    indicator_rect=rect(indicator)
                elif key!='route_name':
                    indicator_rect=dict(control_rect);indicator_rect['left']=indicator_rect['right']-24;indicator_rect['width']=24
                else:indicator_rect=None
                controls[key]={'evidence_source':'loaded_generated_qml_object_tree','label':str(label.property('text')),
                    'accessible_name':accessibility(item)['name'],'placeholder_is_accessible_name':False,
                    'control_kind':'text' if key=='route_name' else 'dropdown','label_visible':bool(label.property('visible')),
                    'separate_label_row':False,'state':selector_state,'control_rect':control_rect,'label_rect':label_rect,
                    'value_rect':value_rect,'indicator_rect':indicator_rect,
                    'error_rect':rect(error_item) if error_item and error_item.property('visible') else None,
                    'font_pixel_size':float(label.property('font').pixelSize()),'outline_width':float(item.property('outlineWidth')),
                    'top_padding':float(item.property('topPadding')),'notch_padding':float(item.property('notchPadding')),
                    'accessibility':accessibility(item)}
            values={'mapping':stored_before,'route_name':str(panel.findChild(QObject,'routeName').property('text'))}
            result.update(floating_controls=controls,stored_values_before=values,stored_values_after=detached(values),
                qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
        if op=='final_floating_label_geometry':
            semantic={'layer':'layerEdit','id_field':'idEdit','name_field':'nameEdit','completion_field':'completionEdit',
                'scope':'scopeCombo','start':'startCombo','route_name':'routeName','saved_route':'savedCombo'}
            controls={};saved_control=panel.findChild(QObject,'savedCombo')
            repository_before=stored();model_before=json.loads(val('p.savedRoutes'))
            repository_before_observation='repository-read:before:'+hashlib.sha256(json.dumps(repository_before,sort_keys=True).encode()).hexdigest()
            model_before_observation='live-model-read:before:'+hashlib.sha256(json.dumps(model_before,sort_keys=True).encode()).hexdigest()
            saved_index=int(saved_control.property('currentIndex'))
            selected_before=model_before[saved_index]['route_id'] if saved_index>=0 else None
            shared_source=None;shared_type=None
            for key,name in semantic.items():
                item=panel.findChild(QObject,name);label=panel.findChild(QObject,name+'FloatingLabel')
                if selector_state=='focus':item.forceActiveFocus(Qt.TabFocusReason);app.processEvents()
                background=item.property('background');value=item.property('contentItem')
                indicator=item.property('indicator') if key!='route_name' else None
                label_background=label.property('background')
                error_item=panel.findChild(QObject,name+'ValidationMessage')
                control_rect=rect(item);label_rect=rect(label);outline_rect=rect(background)
                engine.globalObject().setProperty('observedFinalBackground',engine.newQObject(background))
                border_width=float(js('observedFinalBackground.border.width').toNumber())
                value_rect=rect(value) if value else {
                    **control_rect,
                    'top':control_rect['top']+float(item.property('topPadding')),
                    'height':max(0,control_rect['height']-float(item.property('topPadding'))),
                }
                indicator_rect=rect(indicator) if indicator and indicator.property('visible') else None
                component_source=str(label.property('componentSource'))
                component_type=label.metaObject().className()
                shared_source=component_source if shared_source is None else shared_source
                shared_type=component_type if shared_type is None else shared_type
                error_visible=bool(error_item and error_item.property('visible'))
                controls[key]={'evidence_source':'loaded_generated_qml_object_geometry','object_id':item.objectName(),
                    'label_object_id':label.objectName(),'label':str(label.property('text')),'accessible_name':accessibility(item)['name'],
                    'placeholder_is_accessible_name':False,'state':selector_state,'label_visible':bool(label.property('visible')),
                    'separate_label_row':False,'clipped':bool(label.property('truncated')),'control_kind':'text' if key=='route_name' else 'dropdown',
                    'control_rect':control_rect,'label_rect':label_rect,'notch_rect':rect(label_background),
                    'value_rect':value_rect,'indicator_rect':indicator_rect,'error_rect':rect(error_item) if error_visible else None,
                    'error_observation_source':'live_validation_object_geometry' if error_visible else None,
                    'error_object_id':error_item.objectName() if error_visible else None,
                    'top_outline_observation':{'source':'live_background_border_geometry',
                        'observation_id':'background-object:'+str(getCppPointer(background)[0]),
                        'object_id':background.objectName(),'y':outline_rect['top'],'border_width':border_width},
                    'shared_component_source':component_source,'shared_component_type':component_type,
                    'font_pixel_size':float(label.property('font').pixelSize()),'font_weight':int(label.property('font').weight()),
                    'outline_width':border_width,'left_inset':float(label.property('x')),
                    'notch_padding':float(item.property('notchPadding')),'top_padding':float(item.property('topPadding')),
                    'selected_route_id':selected_before if key=='saved_route' else None}
            model_after=json.loads(val('p.savedRoutes'));repository_after=stored()
            model_after_observation='live-model-read:after:'+hashlib.sha256(json.dumps(model_after,sort_keys=True).encode()).hexdigest()
            repository_after_observation='repository-read:after:'+hashlib.sha256(json.dumps(repository_after,sort_keys=True).encode()).hexdigest()
            saved_index_after=int(saved_control.property('currentIndex'))
            selected_after=model_after[saved_index_after]['route_id'] if saved_index_after>=0 else None
            def repository_values(document):
                mapping=document['settings'].get('mapping');active_id=document['active_id']
                active_route=next((route for route in document['routes'] if route['route_id']==active_id),None)
                return {'mapping':detached(mapping),'route_name':active_route['name'] if active_route else '',
                    'selected_route_id':active_id}
            result.update(floating_controls=controls,shared_floating_component_source=shared_source,
                shared_floating_component_type=shared_type,selected_route_id_before=selected_before,
                selected_route_id_after=selected_after,
                selected_route_observation_before={'source':'live_saved_route_model','observation_id':model_before_observation},
                selected_route_observation_after={'source':'live_saved_route_model','observation_id':model_after_observation},
                stored_values_before=repository_values(repository_before),stored_values_after=repository_values(repository_after),
                stored_values_observation_before={'source':'independent_repository_readback','observation_id':repository_before_observation},
                stored_values_observation_after={'source':'independent_repository_readback','observation_id':repository_after_observation},
                qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
    elif op=='selection_live':
        panel.setProperty('expanded',True);counts=[];all_ids=[str(f.get('id',f.get('custom_id'))) for f in features]
        for count in case.get('selection_counts',[0,1,len(features)]):
            case['selected_ids']=all_ids[:count];device_inputs()
            wait_for(lambda count=count:int(panel.property('selectedCount'))==count)
            text_value=str(panel.findChild(QObject,'selectionHelpLabel').property('text'))
            counts.append(int(re.search(r'(\d+)\s*개?\s*$',text_value)[1]))
        result['recognized_counts_before_calculate']=counts
    elif op=='route_key_availability':
        pass
    else:raise RuntimeError('unsupported '+op)
    mat=next((r for r in requests if r['kind']=='matrix'),None);opt=next((r for r in requests if 'jobs' in r['body']),None)
    objective=None
    if opt:
        matrices=opt['body']['matrices']['car'];objective='distance' if matrices['costs']==matrices['distances'] and matrices['costs']!=matrices['durations'] else 'time' if matrices['costs']==matrices['durations'] and matrices['costs']!=matrices['distances'] else None
    submitted_route=(state().get('candidate') or active()) if panel.property('controller') is not None else None
    result.update(requests=detached(requests),provider_dispatches=detached(provider_dispatches),transport_dispatches=detached(transport_dispatches),submitted_ids=[str(row['site_id']) for row in submitted_route.get('stops',[])] if opt and submitted_route else [],request_start=mat['body']['locations'][0] if mat else None,request_coordinate=mat['body']['locations'][1] if mat and len(mat['body']['locations']) > 1 else None,optimizer_request={'objective':objective,'cost_matrix':opt['body']['matrices']['car']['costs'],'return_to_start':opt['body']['vehicles'][0].get('end_index')==0} if opt else None)
    if case.get('restart_after_calculate'):
        open_panel();result['session_key_present_after_restart']=bool(state()['settings']['key'])
    result.setdefault('saved_after',saved() if panel.property('controller') is not None else [])
    result.setdefault('active_after',state()['snapshot']['data']['active_id'] if panel.property('controller') is not None else None)
    controller_ready=panel.property('controller') is not None
    selection_text=str(panel.findChild(QObject,'selectionHelpLabel').property('text'))
    selection_count=re.search(r'(\d+)\s*개?\s*$',selection_text)
    result['selection_help']={'recognized_count':int(selection_count[1]) if selection_count else None,
        'explains_layer_selection':all(word in selection_text for word in ('레이어','선택','체크')),
        'focus_is_selection':controller_ready and case.get('focused_id') in [s['site_id'] for s in state()['listed']]}
    completion_text=str(panel.findChild(QObject,'completionHelpLabel').property('text'))
    result['completion_help']={'mapped_boolean_only':all(word in completion_text for word in ('Boolean','true','false','NULL','missing')),
        'blank_mapping_uses_route_local':all(word in completion_text for word in ('비우면','저장 경로'))}
    key_control=panel.findChild(QObject,'keyEdit')
    if key_control:engine.globalObject().setProperty('routeKeyControl',engine.newQObject(key_control))
    result['route_key_input']={'available':key_control is not None,'enabled':bool(key_control and key_control.property('enabled')),
        'password_echo':bool(key_control and js('routeKeyControl.echoMode!==0').toBool())}
    result['message']=panel.property('message');result['logs']='\n'.join(logs);result['transitions']=transitions;result['storage_writes']=writes;result['expression_calls']=detached(expression_calls);result['runtime']='Qt QML actual generated panel, injected QField host and HTTP transport; not native QField'
    result['captured_directions_responses']=[{'payload':row['payload'],'payload_sha256':row['sha256']} for row in received_responses if row['kind']=='directions']
    return result
try:print(json.dumps(main(),ensure_ascii=True))
except Exception:
    import traceback;traceback.print_exc();print(json.dumps(logs,ensure_ascii=True),file=sys.stderr);sys.exit(1)
