"""Run the canonical loaded-QML driver with the unmapped-save click observation added.

The production QML/JS and all existing host/provider/file boundaries remain owned by the
canonical driver.  The approved acceptance-only splice and approved observation-timing correction
(approval 2026-09-22) change no application or unit-test harness during the test-design stage.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path


payload = sys.stdin.read()
driver = Path(__file__).parents[2] / "unit" / "survey_route_qml_driver.py"
source = driver.read_text(encoding="utf-8-sig")

old_ops = "'ordered_completion_checklist','candidate_completion_guard','mixed_route_presentation'}"
new_ops = "'ordered_completion_checklist','candidate_completion_guard','mixed_route_presentation','unmapped_save_qml_click'}"
if source.count(old_ops) != 1:
    raise RuntimeError("canonical QML driver operation set changed")
source = source.replace(old_ops, new_ops)

marker = "    elif op=='mixed_route_presentation':\n"
branch = r'''    elif op=='unmapped_save_qml_click':
        for feature in features:feature['done']=False
        device_inputs();window.show();panel.setProperty('expanded',True);app.processEvents();use_site_mapping('');settings({'max_access_distance_m':2000});control('roundtripBox',False,'checked')
        offsets=[.0035 for _ in features]
        access=[[feature['xy'][0]+offsets[index],feature['xy'][1]] for index,feature in enumerate(features)]
        case['access_snap_response']={'locations':[{'location':point} for point in access]}
        case['walking_responses']=[{'explicit_no_path':True} for _ in features]
        assert calculate()
        acknowledgement=panel.findChild(QObject,'unmappedAcknowledgement')
        save_button=panel.findChild(QObject,'saveRouteButton')
        if acknowledgement is None or save_button is None:raise RuntimeError('missing generated QML save controls')
        scroll=panel.findChild(QObject,'routeScroll');flickable=scroll.property('contentItem')
        def pointer_click(item):
            within=item.mapToItem(flickable,QPointF(0,0))
            flickable.setProperty('contentY',max(0,within.y()-flickable.height()/2+item.height()/2))
            app.processEvents()
            point=item.mapToItem(window.contentItem(),QPointF(item.width()/2,item.height()/2))
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(round(point.x()),round(point.y())))
            drain()
        candidate_before=detached(state()['candidate'])
        enabled_before_ack=bool(save_button.property('enabled'))
        pointer_click(acknowledgement)
        acknowledgement_checked_after_click=bool(acknowledgement.property('checked'))
        enabled_after_ack=bool(save_button.property('enabled'))
        route_name=case['route_name'];control('routeName',route_name)
        storage_fault=case.get('fault','')
        js('var originalSave=p.controller.save;var saveResult=null;p.controller.save=function(name){saveResult=originalSave(name);return saveResult}')
        pointer_click(save_button)
        js('p.controller.save=originalSave');save_ok=js('saveResult').toBool()
        storage_fault=''
        message_after_click=str(panel.property('message'))
        message_label=panel.findChild(QObject,'messageLabel')
        message_top=message_label.mapToItem(scroll,QPointF(0,0)).y()
        feedback_in_viewport=bool(message_label.property('visible') and message_top<scroll.height() and message_top+message_label.height()>0)
        candidate_after_click=detached(state()['candidate'])
        document_after_click=detached(stored())
        slot_after_click=state()['snapshot']['slot']
        relative_path='survey-routes.'+slot_after_click+'.json' if slot_after_click else None
        route_after_click=detached(active())
        listed_after_click=detached(object_value(panel,'savedRoutes'))
        load_enabled_after_click=bool(panel.findChild(QObject,'loadRouteButton').property('enabled'))
        independently_reopened_document=None
        independently_reopened_route=None
        independently_reopened_list=[]
        independently_reopened_load_enabled=False
        if save_ok:
            open_panel();settings()
            independently_reopened_document=detached(stored())
            independently_reopened_route=detached(active())
            independently_reopened_list=detached(object_value(panel,'savedRoutes'))
            independently_reopened_load_enabled=bool(panel.findChild(QObject,'loadRouteButton').property('enabled'))
        result.update(qml_controls={'acknowledgement_object_name':acknowledgement.objectName(),
                'save_object_name':save_button.objectName(),'save_enabled_before_ack':enabled_before_ack,
                'save_enabled_after_ack':enabled_after_ack,'acknowledgement_checked':acknowledgement_checked_after_click},
            route_name_input=route_name,save_ok=bool(save_ok),message_after_click=message_after_click,
            feedback_in_viewport=feedback_in_viewport,
            candidate_before_click=candidate_before,candidate_after_click=candidate_after_click,
            document_after_click=document_after_click,route_after_click=route_after_click,
            committed_project_relative_path=relative_path,listed_after_click=listed_after_click,
            load_enabled_after_click=load_enabled_after_click,
            independently_reopened_document=independently_reopened_document,
            independently_reopened_route=independently_reopened_route,
            independently_reopened_list=independently_reopened_list,
            independently_reopened_load_enabled=independently_reopened_load_enabled,
            qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
'''
if source.count(marker) != 1:
    raise RuntimeError("canonical QML driver branch marker changed")
source = source.replace(marker, branch + marker)

sys.stdin = io.StringIO(payload)
exec(compile(source, str(driver), "exec"), {"__name__": "__main__", "__file__": str(driver)})
