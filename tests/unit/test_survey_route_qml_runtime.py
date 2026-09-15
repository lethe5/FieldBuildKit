"""Real-QML regressions and mutation sensitivity for independent review findings."""
import json
import shutil
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
    assert 'import org.qfield.core\n' in root_qml
    assert 'import org.qfield.gui\n' in root_qml
    assert 'import org.qfield.core\n' in route_qml
    assert 'import org.qfield.gui\n' in route_qml
    native_names = (
        'QfExpressionEvaluator', 'QfFeatureModel', 'QfAttributeFormModel',
        'QfLinePolygon', 'QfGeometryWrapper', 'QfLayerUtils', 'QfFileUtils',
    )
    assert all(name in route_qml for name in native_names)


def test_selection_help_polls_current_selection_before_calculate(tmp_path):
    project=_build(tmp_path)
    features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(3)]
    r=_node({'operation':'selection_live','features':features,'selection_counts':[0,1,3]},project['project_dir'])
    assert r['recognized_counts_before_calculate']==[0,1,3]
    assert r['requests']==[]


@pytest.mark.parametrize(('survey_type','expected'),[
    ('simple_inventory',{'layer':'','id':'','name':''}),
    ('temporary_plots',{'layer':'site','id':'site_id','name':'site_name'}),
])
def test_generated_project_owns_route_mapping_defaults(tmp_path,survey_type,expected):
    project=_build(tmp_path,survey_type=survey_type)
    observed=_qml_probe(project,tmp_path)
    assert observed['qml_errors']==[]
    assert observed['mapping_defaults']==expected


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
    expected={'layer':'site','id':'site_id','name':'site_name','completed':'doneA'}
    assert r['loaded_mapping']==r['new_mapping']==r['remaining_mapping']==expected
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


def test_remaining_with_completed_stops_drops_partial_eta_and_roundtrips(tmp_path):
    features=[{'id':str(i),'name':'조사지 '+str(i),'xy':[127+i/1000,37]} for i in range(12)]
    r=run(case={'operation':'remaining','features':features,'completed_ids':['0','1','2','3'],
                'gps':[127.55,37.66],'outcome':'save','response':{'arrivals':list(range(8))}},
          work_dir=str(tmp_path))
    route=r['saved_after']
    assert r['ok'] and r['submitted_ids']==[str(i) for i in range(4,12)]
    assert r['request_start']==[127.55,37.66]
    assert route['route_id']==r['saved_before']['route_id']
    assert route['revision']>r['saved_before']['revision']
    assert len(route['stops'])==12
    assert [s['site_id'] for s in route['stops']]==[str(i) for i in range(12)]
    assert [s['site_id'] for s in route['stops'] if s['completed']]==['0','1','2','3']
    assert route['eta'] is None and route['eta_basis'] is None


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
    assert [s['site_id'] for s in r['reloaded']['stops']]==['0','1','2']
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
