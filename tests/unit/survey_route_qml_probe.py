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
os.environ['QT_QPA_FONTDIR']='C:/Windows/Fonts'
from PySide6.QtCore import QObject, Property, Slot, QByteArray, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent
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
class Project(QObject):
    homePath=Property(str,lambda self:str(folder),constant=True)
    @Slot(result='QVariantMap')
    def mapLayers(self):return {}
    @Slot(str,result='QVariantList')
    def mapLayersByName(self,name):return []
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
put('org.qfield','qmldir','module org.qfield\nQfToolButton 1.0 QfToolButton.qml\n')
put('org.qfield','QfToolButton.qml','import QtQuick\nimport QtQuick.Controls\nButton {property string iconSource;property color iconColor;property color bgcolor;property bool round}')
put('org.qfield.core','qmldir','module org.qfield.core\nQfFeatureModel 1.0 QfFeatureModel.qml\nQfLinePolygon 1.0 QfLinePolygon.qml\nQfGeometryWrapper 1.0 QfGeometryWrapper.qml\nsingleton QfFileUtils 1.0 QfFileUtils.qml\nsingleton QfLayerUtils 1.0 QfLayerUtils.qml\nsingleton QfFeatureUtils 1.0 QfFeatureUtils.qml\n')
put('org.qfield.core','QfFeatureModel.qml','import QtQml\nQtObject {property var project;property var currentLayer;property var feature}')
put('org.qfield.core','QfLinePolygon.qml','import QtQuick\nItem {property var mapSettings;property var geometry;property color color;property real lineWidth}')
put('org.qfield.core','QfGeometryWrapper.qml','import QtQml\nQtObject {property var qgsGeometry;property var crs}')
put('org.qfield.core','QfFileUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function fileExists(p){return boundaryHost.exists(p)} function readFileContent(p){return boundaryHost.read(p)} function writeFileContent(p,t){return boundaryHost.write(p,t)}}')
put('org.qfield.core','QfLayerUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createFeatureIterator(layer){throw Error("not invoked in load probe")}}')
put('org.qfield.core','QfFeatureUtils.qml','pragma Singleton\nimport QtQml\nQtObject {function createBlankFeature(){return ({})} function attributeIsNull(value){return value===null || value===undefined}}')
put('org.qfield.gui','qmldir','module org.qfield.gui\nQfExpressionEvaluator 1.0 QfExpressionEvaluator.qml\nQfAttributeFormModel 1.0 QfAttributeFormModel.qml\n')
put('org.qfield.gui','QfExpressionEvaluator.qml','import QtQml\nQtObject {property var project;property var layer;property var feature;function evaluate(text){return boundaryHost.evaluate(text);}}')
put('org.qfield.gui','QfAttributeFormModel.qml','import QtQml\nQtObject {property var featureModel;function applyFeatureModel(){} function save(){throw Error("not invoked in load probe")} function changeAttribute(){throw Error("not invoked in load probe")}}')
put('org.qgis','qmldir','module org.qgis\nDummy 1.0 Dummy.qml\n')
put('org.qgis','Dummy.qml','import QtQml\nQtObject {}')
put('Theme','qmldir','module Theme\nsingleton Theme 1.0 Theme.qml\n')
put('Theme','Theme.qml','pragma Singleton\nimport QtQuick\nQtObject {property color mainColor: "blue";property bool darkTheme:false}')
app=QGuiApplication([]);engine=QQmlEngine();engine.addImportPath(str(stubs));window=Window();window.resize(800,900)
host=Host();project=Project();iface=Iface(window)
engine.rootContext().setContextProperty('boundaryHost',host);engine.rootContext().setContextProperty('qgisProject',project);engine.rootContext().setContextProperty('iface',iface)
messages=[]
qInstallMessageHandler(lambda typ,ctx,msg:messages.append(str(msg)))
component=QQmlComponent(engine,QUrl.fromLocalFile(payload['qml_path']));obj=component.create()
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
controls=[]
for token,label in [('targets','대상 레이어 이름 / ID'),('settings','서버 설정 저장 (키 제외)'),('results','결과 없음'),('save','계산 결과 저장'),('load','저장 경로 불러오기')]:
    if label in texts or (panel and any(child.property('placeholderText')==label for child in panel.findChildren(QObject))):controls.append(token)
result={'loaded_features':sorted(loaded),'qml_errors':messages,'runtime':'PySide6 Qt QML with injected QField host types; not native QField','panel':{'edge':'bottom' if panel and abs(panel.y()+collapsed-window.contentItem().height())<1 else None,'collapsed_rows':1 if collapsed==44 else None,'controls':controls}}
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
print(json.dumps(result,ensure_ascii=False))
