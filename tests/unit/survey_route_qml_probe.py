"""Qt contract load of actual generated QML, with explicitly injected QField host boundary.
Not a native QField compatibility probe. No external transport is available.
"""
import json
import os
import sys
import uuid
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['QT_QUICK_CONTROLS_STYLE']='Basic'
if Path('C:/Windows/Fonts').is_dir():
    os.environ['QT_QPA_FONTDIR']='C:/Windows/Fonts'
from PySide6.QtCore import QObject, Property, Slot, QByteArray, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlAbstractUrlInterceptor, QQmlEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow, QQuickItem

payload=json.load(sys.stdin)
folder=Path(payload['project_dir'])
stubs=Path(payload['work_dir'])/'qfield-host-fixture'
class Host(QObject):
    @Slot(str,result='QVariant')
    def evaluate(self,text):
        if text=='@project_folder':return str(folder)
        if text.startswith('@project_folder'):
            import re
            strings=re.findall("'([^']*)'",text)
            return str(folder)+''.join(strings)
        if text.startswith('uuid('):return str(uuid.uuid4())
        return None
    @Slot(str,result=bool)
    def exists(self,path):return Path(path).is_file()
    @Slot(str,result=QByteArray)
    def read(self,path):return QByteArray(Path(path).read_bytes()) if Path(path).is_file() else QByteArray()
    @Slot(str,'QVariant',result=bool)
    def write(self,path,text):
        p=Path(path)
        if not p.resolve().is_relative_to(folder.resolve()):raise ValueError('outside fixture')
        p.write_bytes(bytes(text) if isinstance(text,QByteArray) else str(text).encode());return True
import xml.etree.ElementTree as ET
class Fields(QObject):
    @Slot(result='QVariantList')
    def names(self):return ['site_id','site_name','inventory_id','selected_korean_name','done']
class Layer(QObject):
    def __init__(self,layer_id,source_name,alias):super().__init__();self.layer_id=layer_id;self.source_name=source_name;self.alias=alias;self.field_set=Fields(self)
    @Slot(result=str)
    def id(self):return self.layer_id
    @Slot(result=str)
    def sourceName(self):return self.source_name
    @Slot(result=str)
    def name(self):return self.alias
    @Slot(result=QObject)
    def fields(self):return self.field_set
    @Slot(result=int)
    def type(self):return 0
    @Slot(result=int)
    def geometryType(self):return 0
class Project(QObject):
    def __init__(self):
        super().__init__();self.layers=[]
        for node in ET.parse(next(folder.glob('*.qgs'))).findall('./projectlayers/maplayer'):
            alias=node.findtext('layername') or '';source='site' if alias=='조사지' else alias
            self.layers.append(Layer(node.findtext('id') or source,source,alias))
    homePath=Property(str,lambda self:str(folder),constant=True)
    @Slot(result='QVariantList')
    def mapLayers(self):return self.layers
    @Slot(str,result=QObject)
    def mapLayer(self,layer_id):return next((layer for layer in self.layers if layer.layer_id==layer_id),None)
    @Slot(str,result='QVariantList')
    def mapLayersByName(self,name):return [layer for layer in self.layers if layer.alias==name or layer.source_name==name]
class Iface(QObject):
    def __init__(self,window):super().__init__();self.window=window;self.registered=[]
    @Slot(result=QObject)
    def mainWindow(self):return self.window
    @Slot(str,result=QObject)
    def findItemByObjectName(self,name):return self.window.contentItem().findChild(QObject,name)
    @Slot(QObject)
    def addItemToPluginsToolbar(self,item):self.registered.append(item)
class Window(QQuickWindow):
    @Slot(str)
    def displayToast(self,text):pass

def put(module,name,text):
    target=stubs/module.replace('.','/')
    target.mkdir(parents=True,exist_ok=True)
    (target/name).write_text(text,encoding='utf8')
put('org.qfield','qmldir','module org.qfield\nExpressionEvaluator 1.0 ExpressionEvaluator.qml\nFeatureModel 1.0 FeatureModel.qml\nAttributeFormModel 1.0 AttributeFormModel.qml\nQgsGeometryWrapper 1.0 QgsGeometryWrapper.qml\nMapToScreen 1.0 MapToScreen.qml\nsingleton GeometryUtils 1.0 GeometryUtils.qml\nsingleton CoordinateReferenceSystemUtils 1.0 CoordinateReferenceSystemUtils.qml\nsingleton FileUtils 1.0 FileUtils.qml\nsingleton LayerUtils 1.0 LayerUtils.qml\nsingleton FeatureUtils 1.0 FeatureUtils.qml\n')
put('org.qfield','ExpressionEvaluator.qml','import QtQml\nQtObject {property var project;property var layer;property var feature;function evaluate(text){return boundaryHost.evaluate(text);}}')
put('org.qfield','FeatureModel.qml','import QtQml\nQtObject {property var project;property var currentLayer;property var feature}')
put('org.qfield','AttributeFormModel.qml','import QtQml\nQtObject {property var featureModel;function applyFeatureModel(){} function save(){throw Error("not invoked in load probe")} function changeAttribute(){throw Error("not invoked in load probe")}}')
put('org.qfield','QgsGeometryWrapper.qml','import QtQml\nQtObject {property var qgsGeometry;property var crs}')
put('org.qfield','GeometryUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createGeometryFromWkt(wkt){return wkt} function point(x,y){return ({x:x,y:y})} function reprojectPoint(point){return point}}')
put('org.qfield','MapToScreen.qml','import QtQml\nQtObject {property var mapSettings;property var mapPoint;readonly property point screenPoint: Qt.point(mapPoint&&mapPoint.x||0,mapPoint&&mapPoint.y||0)}')
put('org.qfield','CoordinateReferenceSystemUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function wgs84Crs(){return "EPSG:4326"}}')
put('org.qfield','FileUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function fileExists(p){return boundaryHost.exists(p)} function readFileContent(p){return boundaryHost.read(p)} function writeFileContent(p,t){return boundaryHost.write(p,t)}}')
put('org.qfield','LayerUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createFeatureIterator(layer){throw Error("not invoked in load probe")}}')
put('org.qfield','FeatureUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createBlankFeature(){return ({})} function attributeIsNull(value){return value===null || value===undefined}}')
qrc_stubs=stubs/'qrc-qml';qrc_stubs.mkdir(parents=True,exist_ok=True)
(qrc_stubs/'GeometryRenderer.qml').write_text('import QtQuick\nimport org.qfield\nItem {property var mapSettings;property alias geometryWrapper:wrapper;property real lineWidth:3.5;property color color:"#ff0000";property real pointSize:20;property real borderSize:3;QgsGeometryWrapper {id:wrapper}}',encoding='utf8')
put('org.qgis','qmldir','module org.qgis\nDummy 1.0 Dummy.qml\n')
put('org.qgis','Dummy.qml','import QtQml\nQtObject {}')
put('Theme','qmldir','module Theme\nsingleton Theme 1.0 Theme.qml\nQfToolButton 1.0 QfToolButton.qml\n')
put('Theme','Theme.qml','pragma Singleton\nimport QtQuick\nQtObject {property color mainColor: "blue";property bool darkTheme:false}')
put('Theme','QfToolButton.qml','import QtQuick\nimport QtQuick.Controls\nButton {property string iconSource;property color iconColor;property color bgcolor;property bool round}')
class QrcInterceptor(QQmlAbstractUrlInterceptor):
    def intercept(self,url,data_type):
        if url.scheme()=='qrc' and url.path().startswith('/qml/'):
            return QUrl.fromLocalFile(str(qrc_stubs/url.path().removeprefix('/qml/')))
        return url
app=QGuiApplication([]);engine=QQmlEngine();qrc_interceptor=QrcInterceptor();engine.addUrlInterceptor(qrc_interceptor);engine.addImportPath(str(stubs));window=Window();window.resize(800,900)
host=Host();project=Project();iface=Iface(window)
engine.rootContext().setContextProperty('boundaryHost',host);engine.rootContext().setContextProperty('qgisProject',project);engine.rootContext().setContextProperty('iface',iface)
messages=[]
qInstallMessageHandler(lambda typ,ctx,msg:messages.append(str(msg)))
component=QQmlComponent(engine,QUrl.fromLocalFile(payload['qml_path']));obj=component.create()
messages=[message for message in messages if not message.startswith('Populating font family aliases took ')]
if not obj:print(json.dumps({'qml_errors':[e.toString() for e in component.errors()]+messages}));sys.exit()
app.processEvents()
panel=obj.findChild(QQuickItem,'qpbSurveyRoutePanel')
registered={o.objectName() for o in iface.registered}
loaded=set()
if panel and panel.property('controller').toVariant() is not None:loaded.add('routes')
if 'qpbReportToolbarButton' in registered:loaded.add('report')
if 'qpbIdentificationToolbarButton' in registered:loaded.add('identification')
collapsed=panel.height() if panel else None
if panel:panel.setProperty('expanded',True)
app.processEvents()
texts=[]
if panel:
    for child in panel.findChildren(QObject):
        value=child.property('text')
        if isinstance(value,str) and value:texts.append(value)
control_objects=[]
if panel:
    for semantic_id,object_name in (
        ('targets','layerEdit'),('settings','serverEdit'),('results','remainingLabel'),
        ('save','routeName'),('load','savedCombo'),
    ):
        control=panel.findChild(QObject,object_name)
        if control:
            control_objects.append({
                'semantic_id':semantic_id,'object_id':control.objectName(),
                'qml_type':control.metaObject().className(),
                'visible':bool(control.property('visible')),'enabled':bool(control.property('enabled')),
                'object_identity_source':'loaded_generated_qml',
            })
result={'loaded_features':sorted(loaded),'qml_errors':[message for message in messages if not message.startswith('Populating font family aliases took ')],'runtime':'PySide6 Qt QML with injected QField host types; not native QField','panel':{'edge':'bottom' if panel and abs(panel.y()+collapsed-window.contentItem().height())<1 else None,'collapsed_rows':1 if collapsed==44 else None,'control_objects':control_objects}}
if panel:
    result['mapping_defaults']={name:panel.findChild(QObject,object_name).property('text') for name,object_name in (
        ('layer','layerEdit'),('id','idEdit'),('name','nameEdit'))}
# Edge observation must precede expansion; anchors continue to follow the bottom after it.
if panel and abs(panel.y()+panel.height()-window.contentItem().height())<1:result['panel']['edge']='bottom'
if payload.get('widget_source'):
    widget_component=QQmlComponent(engine)
    widget_component.setData(payload['widget_source'].encode(),QUrl.fromLocalFile(str(folder/'identification-probe.qml')))
    widget=widget_component.create()
    if not widget:result['widget_errors']=[e.toString() for e in widget_component.errors()]
    else:
        js=engine.newQObject(widget)
        response=engine.toScriptValue({'version':'synthetic','results':[{'score':0.9,'species':{'scientificNameWithoutAuthor':'Synthetic species','scientificName':'Synthetic species'}}]})
        value=js.property('qpbHandlePlantNetResponse').callWithInstance(js,[response])
        result['widget_errors']=[value.toString()] if value.isError() else []
        candidates=widget.property('qpbCandidatesModel').toVariant()
        result['identification_candidate']=candidates[0] if candidates else None
print(json.dumps(result,ensure_ascii=True))
