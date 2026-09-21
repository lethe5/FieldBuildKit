"""Real-QML regressions and mutation sensitivity for independent review findings."""
import json
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from qfield_builder.survey_route_acceptance import _build, _node, _qml_probe, run


def test_generated_identity_map_button_without_gps(tmp_path):
    r=run(case={'operation':'start','mode':'map','coordinate':[128,38],'gps':None},work_dir=str(tmp_path))
    assert r['ok'] and r['request_start']==[128,38]
    assert r['candidate']['stops']
    assert 'TypeError' not in r['logs']


def test_generated_route_assets_load_after_relocation(tmp_path):
    result=_build(tmp_path,identification_enabled=True)
    old=Path(result['project_dir']);moved=old.with_name(old.name+'-moved');shutil.move(old,moved)
    result['project_dir']=str(moved);result['qgs_path']=str(moved/Path(result['qgs_path']).relative_to(old))
    observed=_qml_probe(result,tmp_path)
    assert observed['qml_errors']==[] and set(observed['loaded_features'])>={'routes','report','identification'}
    assert {p.name for p in (moved/'qfield_routes').iterdir()}>={'RoutePanel.qml','backend.js','controller.js','geometry.js','repository.js','navigation.js'}
    root_qml=Path(result['qgs_path']).with_suffix('.qml').read_text(encoding='utf8')
    route_qml=(moved/'qfield_routes/RoutePanel.qml').read_text(encoding='utf8')
    assert 'import org.qfield\n' in root_qml
    assert 'import org.qfield\n' in route_qml
    assert 'import "qrc:/qml" as QFieldItems\n' in route_qml
    assert 'org.qfield.core' not in root_qml+route_qml
    assert 'org.qfield.gui' not in root_qml+route_qml
    native_names = (
        'ExpressionEvaluator', 'FeatureModel', 'AttributeFormModel',
        'QFieldItems.GeometryRenderer', 'LayerUtils', 'FileUtils',
    )
    assert all(name in route_qml for name in native_names)
    assert not any(name in route_qml for name in (
        'QfExpressionEvaluator', 'QfFeatureModel', 'QfAttributeFormModel',
        'QfLinePolygon', 'QfGeometryRenderer', 'QfGeometryWrapper', 'QfLayerUtils', 'QfFileUtils',
    ))


def test_layer_dropdown_uses_qgis_tree_order_paths_and_stable_ids(tmp_path):
    project=_build(tmp_path)
    layers=[
        {'layer_id':'z-layer','source_name':'plots_z','alias':'표본구','tree_path':'현장 Z/표본구','fields':['plot_id','plot_name']},
        {'layer_id':'a-layer','source_name':'plots_a','alias':'표본구','tree_path':'현장 A/표본구','fields':['plot_id','plot_name']},
        {'layer_id':'m-layer','source_name':'other','alias':'기타','tree_path':'현장 M/기타','fields':['other_id','other_name']},
    ]
    r=_node({'operation':'project_dropdowns','layers':layers,'actions':['open']},project['project_dir'])
    assert [option['layer_id'] for option in r['layer_options']]==['z-layer','a-layer','m-layer']
    assert r['layer_tree_paths']==['현장 Z / 표본구','현장 A / 표본구','현장 M / 기타']
    assert r['layer_options'][0]['label']=='표본구 · 현장 Z / 표본구 · z-layer'
    assert r['layer_options'][1]['label']=='표본구 · 현장 A / 표본구 · a-layer'


def test_real_qfield_canvas_property_layers_fill_dropdown_and_fields(tmp_path):
    project=_build(tmp_path)
    layers=[
        {'layer_id':'points','source_name':'points','alias':'점 대상','geometry_type':0,'fields':['point_id','point_name']},
        {'layer_id':'site-stable','source_name':'site','alias':'조사지','geometry_type':2,'fields':['uuid','site_id','site_name']},
        {'layer_id':'lines','source_name':'lines','alias':'선 대상','geometry_type':1,'fields':['line_id','line_name']},
        {'layer_id':'polygons','source_name':'polygons','alias':'면 대상','geometry_type':2,'fields':['polygon_id','polygon_name']},
        {'layer_id':'raster','source_name':'raster','alias':'배경 영상','vector':False,'fields':[]},
        {'layer_id':'table','source_name':'table','alias':'비공간 표','geometry_type':4,'fields':['table_id','table_name']},
    ]
    r=_node({'operation':'project_dropdowns','qfield_property_api':True,'layers':layers,'actions':['open']},project['project_dir'])
    assert [option['layer_id'] for option in r['layer_options']]==['points','site-stable','lines','polygons']
    assert r['selected_layer_id']=='site-stable'
    assert r['field_options']==['uuid','site_id','site_name']
    assert r['selected_fields']=={'id':'site_id','name':'site_name'}


def test_polygon_completion_overlay_observes_target_renderer_composition(tmp_path):
    r=run(case={'operation':'completion_overlay','geometry_type':'Polygon','completion_source':'route_stop',
                'actions':['complete']},work_dir=str(tmp_path))
    overlay=next(state['overlay'] for state in r['states'] if state['overlay'])
    composition=overlay['composition']
    assert composition=={
        'base_renderer':True,'base_item_opacity':1,'boost_renderer':True,
        'boost_visible':True,'boost_item_opacity':pytest.approx(8/15),'same_geometry':True,
    }
    assert overlay['fill_opacity']==pytest.approx(.35)
    assert overlay['outline_opacity']==1


def test_selection_help_polls_current_selection_before_calculate(tmp_path):
    project=_build(tmp_path)
    features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(3)]
    r=_node({'operation':'selection_live','features':features,'selection_counts':[0,1,3]},project['project_dir'])
    assert r['recognized_counts_before_calculate']==[0,1,3]
    assert r['requests']==[]


@pytest.mark.parametrize(('survey_type','expected'),[
    ('simple_inventory',{'layer':'','id':'','name':''}),
    ('temporary_plots',{'id':'site_id','name':'site_name'}),
])
def test_generated_project_owns_route_mapping_defaults(tmp_path,survey_type,expected):
    project=_build(tmp_path,survey_type=survey_type)
    observed=_qml_probe(project,tmp_path)
    assert observed['qml_errors']==[]
    assert {key:observed['mapping_defaults'][key] for key in expected}==expected
    if survey_type=='temporary_plots':
        assert observed['mapping_defaults']['layer'].startswith('site_')
    else:
        assert observed['mapping_defaults']['layer']==''


def test_generated_site_label_uses_configured_route_name_field(tmp_path):
    import sqlite3
    import xml.etree.ElementTree as ET

    project=_build(tmp_path,sites=[{
        'site_name':'fallback','display_name':'configured','geom_wkt':'POINT(127 37)'}],
        site_geometry_type='POINT',survey_route={'name_field':'display_name'})
    with sqlite3.connect(project['gpkg_path']) as connection:
        assert connection.execute(
            'SELECT display_name FROM site').fetchone()[0]=='configured'
    site=next(layer for layer in ET.parse(project['qgs_path']).findall('./projectlayers/maplayer')
              if layer.findtext('datasource','').endswith('|layername=site'))
    style=site.find('labeling/settings/text-style')
    assert style.get('isExpression')=='1'
    assert 'display_name' in style.get('fieldName') and 'site_id' in style.get('fieldName')
    assert 'defaultName: "display_name"' in Path(project['qgs_path']).with_suffix('.qml').read_text(encoding='utf8')


def test_generated_site_label_falls_back_when_configured_field_is_absent(tmp_path):
    import sqlite3
    import xml.etree.ElementTree as ET

    project=_build(tmp_path,sites=[{'site_name':'fallback','geom_wkt':'POINT(127 37)'}],
        site_geometry_type='POINT',survey_route={'name_field':'missing_name'})
    with sqlite3.connect(project['gpkg_path']) as connection:
        fields={row[1] for row in connection.execute('PRAGMA table_info(site)')}
    assert 'missing_name' not in fields
    site=next(layer for layer in ET.parse(project['qgs_path']).findall('./projectlayers/maplayer')
              if layer.findtext('datasource','').endswith('|layername=site'))
    expression=site.find('labeling/settings/text-style').get('fieldName')
    assert 'missing_name' not in expression and 'site_id' in expression


def test_builder_route_key_uses_real_worker_and_desktop_encryption(tmp_path):
    secret='UNIT_SYNTHETIC_ROUTE_KEY'
    r=run(case={'operation':'builder_route_key','input_key':secret,'consent':False,
                'remember':True,'outcome':'success'},work_dir=str(tmp_path))
    project=Path(r['project_dir']);store=Path(r['desktop_credential_store'])
    assert r['project_published'] and Path(r['qgs_path']).is_file()
    assert r['manual_session_available'] is True
    assert r['remembered_key_available_to_qfield'] is False
    assert store.name=='credentials.enc' and store.is_file()
    assert secret.encode() not in store.read_bytes()
    assert all(secret.encode() not in path.read_bytes() for path in project.rglob('*') if path.is_file())


def test_load_button_restores_mapping_for_both_calculations(tmp_path):
    r=run(case={'operation':'mapping_reload'},work_dir=str(tmp_path))
    assert r['loaded_mapping']==r['new_mapping']
    assert r['loaded_mapping']['layer'].startswith('site_')
    assert {key:r['loaded_mapping'][key] for key in ('id','name','completed')}=={
        'id':'site_id','name':'site_name','completed':'doneA'}
    assert r['new_completed'] is True
    assert [s['site_id'] for s in r['completed_records']]==['0']


def test_vroom_numeric_arrival_persists_and_is_disclosed(tmp_path):
    r=run(case={'operation':'result_roundtrip','response':{'arrivals':[1,2,3]}},work_dir=str(tmp_path))
    assert r['ok'] and r['reloaded']['eta']==[1,2,3]
    assert r['reloaded']['eta_basis']=='relative_seconds'
    assert r['availability']['eta'] is True


def test_reopened_saved_road_overlay_uses_native_geometry_with_wgs84_crs(tmp_path):
    road={'type':'LineString','coordinates':[[127,37],[127.001,37.003],[127.002,37]]}
    r=run(case={'operation':'reopen_navigate','road_geometry':road,'destination':[127.123,37.456],
                'name':'조사지','launch_result':True},work_dir=str(tmp_path))
    assert r['rendered_geometry']==road
    overlay=r['road_overlay']
    assert overlay['parent_is_canvas'] is True and overlay['visible'] is True
    assert overlay['geometry_crs']=='EPSG:4326'
    assert not any('geom_from_wkt(' in call['expression_text'] for call in r['expression_calls'])


def test_completion_progression_uses_saved_legs_without_request(tmp_path):
    r=run(case={'operation':'route_progression','mode':'roundtrip','completion_source':'route_stop',
                'actions':[{'complete':'0'},{'complete':'1'}]},work_dir=str(tmp_path))
    assert r['states'][-1]['prefix_length']==2
    assert r['states'][-1]['remaining_leg_sequences']==[3,4]
    assert r['full_route_after']==r['full_route_before']
    assert r['requests']==[]


def test_ui_availability_mutation_is_observed(tmp_path):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/RoutePanel.qml'
    p.write_text(p.read_text(encoding='utf8').replace('"ETA 제공 (출발 기준 초)"','"ETA 미제공"'),encoding='utf8')
    r=_node({'operation':'result_roundtrip','response':{'arrivals':[1,2,3]}},project['project_dir'])
    with pytest.raises(AssertionError):assert r['availability']['eta'] is True
    assert r['reloaded']['eta']==[1,2,3]
    print('Sensitivity: erroneous UI ETA availability fails the availability assertion')


def test_storage_success_mutation_is_observed(tmp_path):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/controller.js'
    source=p.read_text(encoding='utf8');start=source.index('    function save(name)');end=source.index('    function select(',start)
    source=source[:start]+source[start:end].replace('error(e); return false;','error(e); return true;')+source[end:]
    p.write_text(source,encoding='utf8')
    r=_node({'operation':'storage_fault','fault':'storage_full'},project['project_dir'])
    with pytest.raises(AssertionError):assert r['outcome'] in {'recovered','rejected'}
    assert r['outcome']=='committed'
    print('Sensitivity: erroneous storage success fails the approved recovery outcome assertion')


def test_raw_vroom_order_mutation_is_observed(tmp_path):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/backend.js'
    p.write_text(p.read_text(encoding='utf8').replace('return targets[s.id];','return targets[(s.id+1)%targets.length];'),encoding='utf8')
    response={'code':0,'unassigned':[],'routes':[{'distance':3,'duration':4,'steps':[
        {'type':'start'},{'type':'job','id':2},{'type':'job','id':0},{'type':'job','id':1},{'type':'end'}]}]}
    r=_node({'operation':'result_roundtrip','optimizer_response':response,'directions_response':None},project['project_dir'])
    with pytest.raises(AssertionError):assert [s['site_id'] for s in r['reloaded']['stops']]==['2','0','1']
    assert [s['site_id'] for s in r['reloaded']['stops']]!=['2','0','1']
    print('Sensitivity: mutated VROOM job mapping changes the independently reloaded stop order')


def test_secret_persistence_mutation_is_observed(tmp_path):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/controller.js'
    p.write_text(p.read_text(encoding='utf8').replace('delete s.key;delete s.objective;','delete s.objective;'),encoding='utf8')
    secret='UNIT_SYNTHETIC_SESSION_KEY'
    settings={'server_url':'https://routing.invalid/ors','optimizer_url':'https://optimizer.invalid/vroom','backend':'ors-vroom','profile':'driving-car','timeout_ms':1250,'max_road_offset_m':50,'objective':'time','key':secret}
    r=_node({'operation':'configured_calculate','settings':settings,'seed_saved':True},project['project_dir'])
    with pytest.raises(AssertionError):assert 'key' not in r['persisted_settings']
    assert r['persisted_settings']['key']==secret
    print('Sensitivity: mutated secret filtering is visible in independently decoded project storage')


@pytest.mark.parametrize('mutation', ['server', 'profile', 'header', 'timeout', 'objective'])
def test_transport_observation_comes_from_provider_and_http_boundaries(tmp_path, mutation):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/backend.js'
    source=p.read_text(encoding='utf8')
    changes={
        'server': ('base + "/v2/matrix/"', '"https://wrong.invalid/v2/matrix/"'),
        'profile': ('encodeURIComponent(settings.profile)', 'encodeURIComponent("wrong-profile")'),
        'header': ('headers.Authorization = settings.key', 'headers.Authorization = "wrong-key"'),
        'timeout': ('timeout_ms: settings.timeout_ms', 'timeout_ms: 9999'),
        'objective': ('settings.objective === "distance"', 'false'),
    }
    old,new=changes[mutation]
    assert old in source
    p.write_text(source.replace(old,new,1),encoding='utf8')
    secret='UNIT_SYNTHETIC_TRANSPORT_KEY'
    settings={'server_url':'https://routing.invalid/ors','optimizer_url':'https://optimizer.invalid/vroom','backend':'ors-vroom','profile':'driving-car','timeout_ms':1250,'max_road_offset_m':50,'objective':'distance','key':secret}
    r=_node({'operation':'configured_calculate','settings':settings,'seed_saved':True},project['project_dir'])
    with pytest.raises(AssertionError):
        assert r['transport_settings']==settings
    print('Sensitivity: mutated '+mutation+' dispatch changes decoded transport evidence')


@pytest.mark.parametrize('content_type', ['application/json; charset=utf-8', 'text/plain'])
def test_transport_observation_validates_actual_http_content_type(tmp_path, content_type):
    project=_build(tmp_path)
    p=Path(project['project_dir'])/'qfield_routes/backend.js'
    source=p.read_text(encoding='utf8')
    assert '"Content-Type": "application/json"' in source
    p.write_text(source.replace('"Content-Type": "application/json"',
                                '"Content-Type": '+json.dumps(content_type),1),encoding='utf8')
    settings={'server_url':'https://routing.invalid/ors','optimizer_url':'https://optimizer.invalid/vroom',
              'backend':'ors-vroom','profile':'driving-car','timeout_ms':1250,
              'max_road_offset_m':50,'objective':'distance','key':'UNIT_SYNTHETIC_TRANSPORT_KEY'}
    if content_type=='text/plain':
        with pytest.raises(RuntimeError,match='HTTP Content-Type must be application/json'):
            _node({'operation':'configured_calculate','settings':settings,'seed_saved':True},project['project_dir'])
    else:
        r=_node({'operation':'configured_calculate','settings':settings,'seed_saved':True},project['project_dir'])
        assert r['transport_settings']==settings


def test_type1_project_mapping_survives_no_route_restart_and_move(tmp_path):
    mapping={'layer':'custom_targets','id':'custom_id','name':'title','completed':'done'}
    r=run(case={'operation':'mapping_settings_restart_move','survey_type':'simple_inventory','mapping':mapping},work_dir=str(tmp_path))
    assert r['active_before']==r['active_after']==''
    assert r['persisted_mapping']==r['reopened_mapping']==r['calculated_mapping']==mapping
    assert r['submitted_ids']==['A','B']


@pytest.mark.parametrize('completion_source', ['field', 'route_stop'])
def test_blocked_completion_attempt_reaches_panel_controller_feedback(tmp_path, completion_source):
    result = run(case={
        'operation': 'ordered_completion_checklist',
        'completion_source': completion_source,
        'actions': [{'attempt_complete': '1'}],
    }, work_dir=str(tmp_path))
    blocked = result['blocked_attempts'][0]
    assert blocked['control_enabled'] is False
    assert blocked['checkbox_accessibility']['enabled'] is False
    assert blocked['action_accessibility']['enabled'] is True
    assert blocked['action_accessibility']['role'] == 'Button'
    assert '2. 조사지 1' in blocked['action_accessibility']['name']
    assert blocked['after'] == blocked['before']
    assert blocked['requests'] == [] and blocked['writes'] == []
    assert blocked['feedback_next_id'] == blocked['expected_next_id'] == '0'
    assert '다음 지점: 1. 조사지 0' in blocked['message']


@pytest.mark.parametrize('active_route', [False, True])
def test_candidate_rows_expose_no_completion_action(tmp_path, active_route):
    result = run(case={
        'operation': 'candidate_completion_guard',
        'active_route': active_route,
    }, work_dir=str(tmp_path))
    assert result['candidate']['stops']
    assert all(row['checkbox_enabled'] is False for row in result['rows'])
    assert all(row['blocked_action_visible'] is False for row in result['rows'])
    assert all(row['blocked_action_accessibility']['visible'] is False for row in result['rows'])
    assert result['active_after'] == result['active_before']
    assert result['requests'] == result['provider_dispatches'] == result['transport_dispatches'] == []
    assert result['writes'] == result['source_writes'] == []
    if active_route:
        assert result['next_before']['site_id'] == result['candidate']['stops'][0]['site_id'] == '0'
    else:
        assert result['active_before'] is None and result['next_before'] is None


def test_normal_build_materializes_configured_route_id_for_label_fallback(tmp_path):
    result = run(case={
        'operation': 'generated_site_label_contract',
        'geometry_type': 'Point',
        'crs': 'EPSG:4326',
        'name_field': None,
        'stable_id_field': 'custom_id',
        'features': [{
            'stable_id': 'ID-01',
            'name': None,
            'geometry': {'type': 'Point', 'coordinates': [127, 37]},
        }],
    }, work_dir=str(tmp_path))
    provenance = result['generated_artifact_provenance']
    with sqlite3.connect(provenance['generated_gpkg_path']) as conn:
        fields = [row[1] for row in conn.execute('PRAGMA table_info("site")')]
        row = conn.execute('SELECT site_id, custom_id FROM "site"').fetchone()
    root = ET.parse(provenance['generated_project_path']).getroot()
    layer = next(item for item in root.findall('./projectlayers/maplayer')
                 if item.findtext('datasource', '').endswith('|layername=site'))
    expression = layer.find('./labeling/settings/text-style').get('fieldName')
    assert fields == ['fid', 'site_id', 'site_name', 'site_geom', 'custom_id']
    assert row == ('ID-01', 'ID-01')
    assert 'to_string("custom_id")' in expression


def test_generated_qml_centroids_one_member_multipoint(tmp_path):
    r=run(case={'operation':'generated_geometry_calculate',
                'geometry_type':'MultiPoint','wkt':'MULTIPOINT ((127 37))','crs':'EPSG:4326'},
          work_dir=str(tmp_path))
    expressions=[call['expression_text'].lower()
                 for call in r['expression_evaluator']['evaluate_calls']]
    assert r['ok'] is True and r['request_coordinate']==pytest.approx([127,37])
    assert 'is_multipart($geometry)' in expressions
    assert any(expression.startswith('x(transform(centroid($geometry)') for expression in expressions)
    assert any(expression.startswith('y(transform(centroid($geometry)') for expression in expressions)
    assert r['original_after']==r['original_before'] and r['qml_errors']==[]


def test_geometry_roundtrip_source_really_contains_z_and_product_strips_it(tmp_path):
    r=run(case={'operation':'geometry_roundtrip','wkts':['POINT Z (1 2 50)'],'crs':'EPSG:4326'},work_dir=str(tmp_path))
    assert r['source_geometries']==[{'type':'Point','coordinates':[1,2,50]}]
    assert r['stored_geometries']==[{'type':'Point','coordinates':[1,2]}]


def test_geometry_roundtrip_xy_assertion_detects_missing_product_normalization(monkeypatch):
    import struct
    from qfield_builder import wkt
    point_z=struct.pack('<BI3d',1,1001,1,2,50)
    assert wkt.wkb_to_wkt(point_z)==('POINT(1.0 2.0)','POINT')
    monkeypatch.setattr(wkt,'wkb_to_wkt',lambda value:('POINT Z (1 2 50)','POINT'))
    with pytest.raises(AssertionError):
        assert wkt.wkb_to_wkt(point_z)==('POINT(1.0 2.0)','POINT')


def test_map_recapture_observes_renderer_geometry_and_label_separately(tmp_path):
    result=run(case={'operation':'map_start_marker','seed_center':[127.1,37.1],
        'actions':[{'action':'capture_center','center':[128.2,38.2]}]},work_dir=str(tmp_path))
    first,second=[state['canvas_markers'][0] for state in result['states']]
    assert first['coordinate']==first['label_coordinate']==[127.1,37.1]
    assert second['coordinate']==second['label_coordinate']==[128.2,38.2]
    assert second['renderer_geometry']=={'type':'Point','coordinates':[128.2,38.2]}
    assert second['contrast_ratio']>=4.5 and second['accessible_name']=='출발지'


def test_runtime_observers_detect_accessibility_model_and_extra_row_mutations(tmp_path):
    project=_build(tmp_path)
    path=Path(project['project_dir'])/'qfield_routes/RoutePanel.qml'
    source=path.read_text(encoding='utf8')
    source=source.replace('Accessible.name: floatingLabel','Accessible.name: "broken-name"',1)
    source=source.replace('targetOptionsModel.append(option);','targetOptionsModel.append({label:option.label,value:"broken-id"});')
    source=source.replace('Label {objectName:"scopeHelpLabel";', 'Label {objectName:"unattributedRow";text:"extra row";Layout.fillWidth:true}\n                Label {objectName:"scopeHelpLabel";')
    path.write_text(source,encoding='utf8')
    result=_node({'operation':'route_workflow_ui','viewport_width':320,'start_mode':'target','scope':'all',
        'targets':[{'id':'A','name':'조사지','selected':True}]},project['project_dir'])
    assert result['candidate_model_capture']['ordered_ids']==['broken-id']
    assert result['preflight_capture']['submitted_ids']==['A']
    assert result['unattributed_visible_scope_rows'][0]['object_id']=='unattributedRow'
    result=_node({'operation':'panel_layout','viewport_width':320,'selector_state':'value',
        'observe_floating_labels':True},project['project_dir'])
    assert result['floating_selectors']['scope']['accessibility']['name']=='broken-name'


@pytest.mark.parametrize('metric',['distance','duration'])
def test_invalid_optimizer_total_is_provider_error_and_retains_saved_route(tmp_path,metric):
    optimizer={'code':0,'unassigned':[],'routes':[{'distance':1234,'duration':456,
        'steps':[{'type':'job','id':index} for index in range(3)]}]}
    optimizer['routes'][0][metric]=-1
    result=run(case={'operation':'schema2_roundtrip','return_to_start':True,'seed_saved':True,
        'optimizer_response':optimizer,'directions_response':None},work_dir=str(tmp_path))
    assert result['ok'] is False and result['error_category']=='provider_response'
    assert result['error_reference']=='route.'+metric
    assert result['active_after']==result['active_before']


def test_generated_project_provider_retains_projected_source_representative(tmp_path):
    import fiona
    result=run(case={'operation':'generated_geometry_calculate','crs':'EPSG:3857',
        'wkt':'LINESTRING(0 0,1000000 1000000,3000000 1000000)','target_id':'stable-zero'},work_dir=str(tmp_path))
    provenance=result['generated_geometry_provenance']
    assert provenance['fixture_feature_injected'] is False
    assert provenance['generated_crs']=='EPSG:4326'
    with fiona.open(provenance['generated_gpkg_path'],layer=provenance['generated_layer_name']) as provider:
        row=next(iter(provider))
        assert result['request_coordinate']==pytest.approx([row.properties['_fb_route_lon'],row.properties['_fb_route_lat']])
        assert str(row.properties['site_id'])=='stable-zero'
    assert result['submitted_ids']==['stable-zero']


@pytest.mark.parametrize('source_format',['gpkg','shapefile'])
def test_mapped_zero_id_survives_raw_and_crs_explicit_shapefile(tmp_path,source_format):
    import fiona
    from qfield_builder.build import _resolve_sites_from_upload
    from qfield_builder.gpkg import build_geopackage
    source=tmp_path/('source.gpkg' if source_format=='gpkg' else 'source.shp')
    with fiona.open(source,'w',driver='GPKG' if source_format=='gpkg' else 'ESRI Shapefile',
            crs='EPSG:4326',schema={'geometry':'Point','properties':{'external':'int','name':'str'}}) as target:
        target.write({'geometry':{'type':'Point','coordinates':[127,37]},'properties':{'external':0,'name':'zero'}})
    if source_format=='shapefile':source.with_suffix('.prj').unlink()
    rows=_resolve_sites_from_upload({'format':source_format,'path':str(source),'source_crs':'EPSG:4326',
        'encoding':'utf-8','attribute_mapping':{'site_id':'external','site_name':'name'}},work_dir=tmp_path)
    assert rows[0]['site_id']==0
    output=tmp_path/'output.gpkg'
    build_geopackage(str(output),'temporary_plots','test-project',seed_sites=rows,site_geometry_type='POINT')
    with fiona.open(output,layer='site') as provider:assert str(next(iter(provider)).properties['site_id'])=='0'


def test_received_raw_directions_hash_links_to_committed_route(tmp_path):
    import hashlib
    response={'features':[{'geometry':{'type':'LineString','coordinates':[[127,37],[127.005,37.003],[127.01,37]]},
        'properties':{'segments':[{'distance':10,'duration':2}],'way_points':[0,2],'summary':{'distance':10,'duration':2}}}]}
    result=run(case={'operation':'generated_geometry_calculate','wkt':'POINT(127.01 37)','crs':'EPSG:4326',
        'return_to_start':False,'save_and_reopen':True,'directions_response':response},work_dir=str(tmp_path))
    digest=hashlib.sha256(json.dumps(response,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert result['captured_directions_responses'][-1]=={'payload':response,'payload_sha256':digest}
    commits=[write for write in result['storage_writes'] if write['ok'] and result['reloaded_route']['route_id'] in write['bytes']]
    assert commits and commits[-1]['directions_payload_sha256']==digest
    assert result['reloaded_route']['legs'][0]['geometry']==response['features'][0]['geometry']


def test_completion_dropdown_displays_stored_field_after_timer_refresh(tmp_path):
    result=run(case={'operation':'project_dropdowns',
        'layers':[{'layer_id':'site-stable','source_name':'site','alias':'조사지','fields':['site_id','site_name','done']}],
        'stored_mapping':{'layer_id':'site-stable','id_field':'site_id','name_field':'site_name','completion_field':'done'},
        'observe_completion_refresh':True},work_dir=str(tmp_path))
    assert result['completion_selections']==[{'stored_field':'done','current_index':3,'current_text':'done'}]*2


@pytest.mark.parametrize('stage',['matrix','optimizer','directions'])
@pytest.mark.parametrize('document',[None,False,7,'not a document',[]])
def test_provider_document_boundary_classifies_error_and_keeps_last_good(tmp_path,stage,document):
    result=run(case={'operation':'schema2_roundtrip','return_to_start':True,'seed_saved':True,
        'directions_response':None,'provider_document_stage':stage,'provider_document':document},work_dir=str(tmp_path))
    assert result['ok'] is False and result['candidate'] is None
    assert result['error_category']=='provider_response'
    assert result['error_reference']==result['error_stage']==stage
    assert '다시 시도' in result['message'] and 'TypeError' not in result['message']
    assert result['saved_after']==result['saved_before'] and result['active_after']==result['active_before']


@pytest.mark.parametrize('extra',['point','label','nested_label'])
def test_canvas_marker_enumeration_includes_unattributed_extras(tmp_path,extra):
    project=_build(tmp_path);path=Path(project['project_dir'])/'qfield_routes/RoutePanel.qml'
    source=path.read_text(encoding='utf8')
    component=('QFieldItems.GeometryRenderer {Component.onCompleted:geometryWrapper.qgsGeometry=GeometryUtils.createGeometryFromWkt("POINT(127 37)")}'
        if extra=='point' else 'Label {text:"unexpected label"}')
    source=source.replace('property var startMarkerItem: null','Component {id:extraMarkerFactory;'+component+'}\n    property var startMarkerItem: null')
    source=source.replace('startMarkerItem=next;','startMarkerItem=next;extraMarkerFactory.createObject('+('next' if extra=='nested_label' else 'canvas')+');')
    path.write_text(source,encoding='utf8')
    result=_node({'operation':'map_start_marker','seed_center':[127,37]},project['project_dir'])
    markers=result['states'][0]['canvas_markers']
    assert result['states'][0]['canvas_marker_count']==len(markers)==2
    assert any(marker['renderer_geometry'] is None for marker in markers) if extra!='point' else any(marker['semantic_role']=='' for marker in markers)


def test_project_close_drives_destruction_and_detects_missing_cleanup(tmp_path):
    project=_build(tmp_path);case={'operation':'map_start_marker','seed_center':[127,37],'actions':[{'action':'project_close'}]}
    result=_node(case,project['project_dir'])
    assert result['project_close_lifecycle']['project_owner_destroyed'] is True
    assert result['project_close_lifecycle']['panel_owned_by_project'] is True
    assert result['project_close_lifecycle']['panel_destroyed'] is True
    assert result['states'][-1]['canvas_marker_count']==0
    path=Path(project['project_dir'])/'qfield_routes/RoutePanel.qml'
    source=path.read_text(encoding='utf8')
    source=source.replace('Component.onDestruction: {lifecycleActive=false;if(controller)controller.cancel("project-close");cancelTransports();if(roadItem)roadItem.destroy();clearCompletedOverlays();clearStartMarker();}',
        'Component.onDestruction: {lifecycleActive=false;if(controller)controller.cancel("project-close");cancelTransports();if(roadItem)roadItem.destroy();clearCompletedOverlays();}')
    path.write_text(source,encoding='utf8')
    result=_node(case,project['project_dir'])
    assert result['project_close_lifecycle']['project_owner_destroyed'] is True
    assert result['project_close_lifecycle']['panel_destroyed'] is True
    assert result['states'][-1]['canvas_marker_count']==1


def test_candidate_transitions_depend_on_production_timer(tmp_path):
    project=_build(tmp_path)
    case={'operation':'route_workflow_ui','viewport_width':320,'start_mode':'target','scope':'selected',
        'targets':[{'id':'A','name':'첫 조사지','alt_id':'X','alt_name':'대체','selected':True},
                   {'id':'B','name':'둘째 조사지','alt_id':'Y','alt_name':'대체','selected':False}],
        'candidate_transitions':[{'action':'qfield_selection','selected_ids':['B']},
            {'action':'scope','scope':'uncompleted'},{'action':'completion','completed_ids':['A']},
            {'action':'mapping','id_field':'alt_id','name_field':'alt_name'}]}
    result=_node(case,project['project_dir'])
    assert [state['candidate_model_capture']['ordered_ids'] for state in result['candidate_states']]==[['A'],['B'],['A','B'],['B'],['Y']]
    for state in result['candidate_states']:
        assert state['candidate_model_capture']['ordered_ids']==state['preflight_capture']['submitted_ids']
        assert [event['event'] for event in state['event_provenance']]==['input_boundary','production_timer_triggered']
    path=Path(project['project_dir'])/'qfield_routes/RoutePanel.qml';source=path.read_text(encoding='utf8')
    source=source.replace('onTriggered:{refreshSelectedCount();refreshProjectSelectors(layerEdit.text);refreshTargets();}',
        'onTriggered:{refreshSelectedCount();refreshProjectSelectors(layerEdit.text);}')
    path.write_text(source,encoding='utf8')
    with pytest.raises(RuntimeError,match='QML observation did not settle'):_node(case,project['project_dir'])


def _assert_selected_floating_values(result, mapping):
    assert result['stored_mapping_before']==result['stored_mapping_after']==mapping
    for selector in result['floating_selectors'].values():
        assert selector['current_index']>=0 and selector['current_text']
        value=selector['option_text_rect'];label=selector['label_rect']
        assert value and value['width']>0 and value['height']>0
        assert (label['right']<=value['left'] or value['right']<=label['left']
                or label['bottom']<=value['top'] or value['bottom']<=label['top'])
    completion=result['floating_selectors']['completion_field']
    assert completion['current_index']>0
    assert completion['current_text']==mapping['completion_field']


@pytest.mark.parametrize('viewport_width',[320,1024])
@pytest.mark.parametrize('selector_state',['empty','value','focus','error'])
def test_floating_selector_evidence_reports_real_types_and_selection_state(tmp_path,selector_state,viewport_width):
    import xml.etree.ElementTree as ET
    mapping={'layer_id':'site-layer-stable-01','id_field':'site_id','name_field':'site_name','completion_field':'completed'}
    case={'operation':'panel_layout','viewport_width':viewport_width,'selector_state':selector_state,
        'observe_floating_labels':True,'stored_mapping':mapping}
    result=run(case=case,work_dir=str(tmp_path))
    project=next(Path(result['project_dir']).glob('*.qgs'))
    site=next(layer for layer in ET.parse(project).findall('./projectlayers/maplayer')
              if layer.findtext('datasource','').endswith('|layername=site'))
    assert site.findtext('id')==mapping['layer_id']
    assert len(result['floating_selectors'])==6
    assert result['stored_mapping_before']==result['stored_mapping_after']==mapping
    for selector in result['floating_selectors'].values():
        assert 'ComboBox' in selector['control_qml_type']
        assert 'Label' in selector['label_qml_type']
        if selector_state in ('empty','error'):
            assert selector['current_index']==-1 and selector['current_text']==''
    if selector_state in ('value','focus'):
        _assert_selected_floating_values(result,mapping)
        # An unpatched fresh project reproduces the original identity mismatch.
        mismatch_project=_build(tmp_path)
        mismatch=_node(case,mismatch_project['project_dir'])
        assert mismatch['floating_selectors']['completion_field']['current_text']==''
        assert mismatch['floating_selectors']['completion_field']['option_text_rect'] is None
        with pytest.raises(AssertionError):_assert_selected_floating_values(mismatch,mapping)
