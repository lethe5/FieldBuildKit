"""Run the generated route panel for AC-SRP-059/063/064/066 UI observations.

The canonical unit driver owns the QField, HTTP, repository, and Qt boundaries.  This
acceptance-only splice adds only the two approved observation workflows; it must fail
closed when the canonical operation set or branch marker changes.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path


payload = sys.stdin.read()
driver = Path(__file__).parents[2] / "unit" / "survey_route_qml_driver.py"
source = driver.read_text(encoding="utf-8-sig")

old_ops = "'ordered_completion_checklist','candidate_completion_guard','mixed_route_presentation'}"
new_ops = (
    "'ordered_completion_checklist','candidate_completion_guard','mixed_route_presentation',"
    "'route_ui_simplification','save_outcome_visibility'}"
)
if source.count(old_ops) != 1:
    raise RuntimeError("canonical QML driver operation set changed")
source = source.replace(old_ops, new_ops)

marker = "    elif op=='mixed_route_presentation':\n"
branch = r'''    elif op in ('route_ui_simplification','save_outcome_visibility'):
        fallback_notice='실제 도로 경로를 못 찾은 구간을 직선거리 추정치로 포함하였습니다.'
        endpoint_notice='ORS 경로 기준 · 요청 좌표까지의 endpoint gap 미포함'
        details_label='상세 정보'
        palette=QPalette();dark=case.get('theme')=='dark'
        palette.setColor(QPalette.Window,QColor('#111827' if dark else '#f8fafc'))
        palette.setColor(QPalette.WindowText,QColor('#f9fafb' if dark else '#111827'))
        app.setPalette(palette);window.resize(int(case.get('viewport_width',320)),900)
        window.show();panel.setProperty('expanded',True);app.processEvents()

        def item_text(item):
            value=item.property('text')
            return str(value or '')
        def shown(item):
            return bool(item.property('visible')) and item.width()>0 and item.height()>0
        def named(name):
            item=panel.findChild(QObject,name)
            if item is None:raise RuntimeError('missing generated QML object '+name)
            return item
        def center_in_view(item):
            scroll=named('routeScroll');flickable=scroll.property('contentItem')
            within=item.mapToItem(flickable,QPointF(0,0))
            flickable.setProperty('contentY',max(0,within.y()-flickable.height()/2+item.height()/2))
            app.processEvents()
        def pointer_click(item):
            center_in_view(item)
            point=item.mapToItem(window.contentItem(),QPointF(item.width()/2,item.height()/2))
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(round(point.x()),round(point.y())))
            drain()
        def visible_texts():
            return [item_text(item) for item in visual_objects(panel) if shown(item) and item_text(item)]
        def accessible_names():
            names=[]
            for item in visual_objects(panel):
                if not shown(item):continue
                interface=QAccessible.queryAccessibleInterface(item)
                if interface is not None and interface.text(QAccessible.Name):
                    names.append(interface.text(QAccessible.Name))
            return names
        def accessible_matches(text):
            matches=[]
            for item in visual_objects(panel):
                if not shown(item):continue
                interface=QAccessible.queryAccessibleInterface(item)
                if interface is not None and interface.text(QAccessible.Name)==text:
                    matches.append({'object_name':item.objectName(),'role':interface.role().name,
                        'name':interface.text(QAccessible.Name),'object_id':str(getCppPointer(item)[0])})
            return matches
        def viewport(item):
            scroll=named('routeScroll');flickable=scroll.property('contentItem')
            top=item.mapToItem(flickable,QPointF(0,0)).y();content_y=float(flickable.property('contentY') or 0)
            bottom=top+item.height();viewport_bottom=content_y+flickable.height()
            return {'top':top,'bottom':bottom,'content_y':content_y,
                'viewport_bottom':viewport_bottom,'fully_visible':top>=content_y and bottom<=viewport_bottom}
        def content_layout(items):
            content=named('routeContent');scroll=named('routeScroll');rows=[]
            for item in items:
                if not shown(item):continue
                point=item.mapToItem(content,QPointF(0,0))
                row={'object_name':item.objectName(),'left':point.x(),'right':point.x()+item.width(),
                    'top':point.y(),'bottom':point.y()+item.height(),'width':item.width(),'height':item.height(),
                    'truncated':bool(item.property('truncated')) if item.property('truncated') is not None else False}
                rows.append(row)
            overlaps=[]
            for index,first in enumerate(rows):
                for second in rows[index+1:]:
                    if not (first['right']<=second['left'] or second['right']<=first['left'] or
                            first['bottom']<=second['top'] or second['bottom']<=first['top']):
                        overlaps.append([first['object_name'],second['object_name']])
            return {'content_width':content.width(),'available_width':scroll.property('availableWidth'),
                'horizontal_overflow':content.width()>scroll.property('availableWidth')+.5 or
                    any(row['left']<-.5 or row['right']>content.width()+.5 for row in rows),
                'overlaps':overlaps,'items':rows}
        def object_id(item):
            return str(getCppPointer(item)[0])
        def semantic_observation():
            basic=[named(name) for name in ('mixedTotalsLabel','walkingTotalsAccessibility',
                'mappedWalkingDurationAccessibility','straightLineLowerBoundAccessibility')]
            disclosure=named('routeDetailsDisclosure');details=named('routeDetailsContent')
            detail_items=[item for item in visual_objects(details)
                if item is not details and shown(item) and item_text(item)]
            groups=[('basic_result',[item for item in basic if shown(item)]),
                ('fallback_notice',[named('fallbackNotice')]),
                ('details_disclosure',[disclosure]),('details_content',detail_items),
                ('route_name',[named('routeName')]),('save_button',[named('saveRouteButton')]),
                ('disabled_reason',[named('saveDisabledReason')]),
                ('outcome_status',[named('saveStatus')])]
            groups=[(name,[item for item in items if shown(item)]) for name,items in groups]
            groups=[(name,items) for name,items in groups if items]
            content=named('routeContent')
            def bounds(items):
                boxes=[]
                for item in items:
                    point=item.mapToItem(content,QPointF(0,0))
                    boxes.append((point.x(),point.y(),point.x()+item.width(),point.y()+item.height()))
                return {'left':min(box[0] for box in boxes),'top':min(box[1] for box in boxes),
                    'right':max(box[2] for box in boxes),'bottom':max(box[3] for box in boxes)}
            group_bounds={name:bounds(items) for name,items in groups}
            ids={object_id(item):name for name,items in groups for item in items}
            accessibility_order=[]
            for item in visual_objects(panel):
                category=ids.get(object_id(item))
                if category is None or category in accessibility_order or not shown(item):continue
                interface=QAccessible.queryAccessibleInterface(item)
                if interface is not None and interface.text(QAccessible.Name):
                    accessibility_order.append(category)
            visual_order=[name for name,_ in sorted(groups,key=lambda pair:group_bounds[pair[0]]['top'])]
            flat_items=[item for _,items in groups for item in items]
            return {'expected_order':[name for name,_ in groups],
                'visual_order':visual_order,'accessibility_order':accessibility_order,
                'group_bounds':group_bounds,'layout':content_layout(flat_items)}
        def keyboard_order():
            disclosure=named('routeDetailsDisclosure');disclosure.forceActiveFocus(Qt.TabFocusReason)
            app.processEvents();order=[]
            for _ in range(3):
                focused=window.activeFocusItem();order.append(focused.objectName() if focused else None)
                QTest.keyClick(window,Qt.Key_Tab);drain()
            return order
        def details_state():
            disclosure=named('routeDetailsDisclosure');content=named('routeDetailsContent')
            return {'expanded':bool(content.property('visible')),
                'label':accessibility(disclosure)['name'],'visual_label':item_text(disclosure),
                'role':accessibility(disclosure)['role'],
                'description':str(disclosure.property('accessibleDescription') or ''),
                'visible_texts':visible_texts(),'accessible_names':accessible_names()}
        def configure_candidate(composition):
            for feature in features:feature['done']=False
            device_inputs();use_site_mapping('done');settings({'max_access_distance_m':2000});control('roundtripBox',False,'checked')
            access=[];walking=[]
            for index,feature in enumerate(features):
                if composition=='exact_zero_only':
                    access.append(detached(feature['xy']))
                else:
                    point=[feature['xy'][0]+.0035,feature['xy'][1]];access.append(point)
                    if composition=='mixed' and index==len(features)-1:
                        walking.append({'explicit_no_path':True})
                    else:
                        geometry=[point,feature['xy']]
                        if case.get('snapped_presentation'):
                            geometry=[[point[0]+.00002,point[1]+.00002],
                                [feature['xy'][0]+.00002,feature['xy'][1]+.00002]]
                        walking.append({'distance_m':120+index,'duration_s':80+index,
                            'geometry':{'type':'LineString','coordinates':geometry}})
            case['access_snap_response']={'locations':[{'location':point} for point in access]}
            case['walking_responses']=walking
            if not calculate():raise RuntimeError('fixture calculation failed: '+str(panel.property('message')))

        if op=='route_ui_simplification':
            composition=case.get('composition','mixed')
            no_candidate_reason=named('saveDisabledReason')
            no_candidate_save=named('saveRouteButton')
            center_in_view(no_candidate_save)
            no_candidate_with_save_layout=content_layout([no_candidate_reason,no_candidate_save])
            no_candidate_observation={'text':item_text(no_candidate_reason),'visible':shown(no_candidate_reason),
                'save_enabled':bool(no_candidate_save.property('enabled')),
                'reason_viewport':viewport(no_candidate_reason),'save_viewport':viewport(no_candidate_save),
                'layout':no_candidate_with_save_layout}
            configure_candidate(composition)
            candidate_before=detached(state()['candidate']);payload_before=json.dumps(candidate_before,ensure_ascii=False,sort_keys=True,separators=(',',':'))
            requests_before=len(requests);writes_before=len(writes);save_before=bool(named('saveRouteButton').property('enabled'))
            fallback_anchor=named('fallbackNotice')
            details_before=details_state();default_texts=visible_texts()
            default_accessible_names=accessible_names()
            fallback_screen=[item for item in visual_objects(panel) if shown(item) and item_text(item)==fallback_notice]
            fallback_accessible=accessible_matches(fallback_notice)
            endpoint_default=[item for item in visual_objects(panel) if shown(item) and item_text(item)==endpoint_notice]
            acknowledgement_controls=[item for item in panel.findChildren(QObject)
                if '지도에 없는 도보 구간 포함' in item_text(item)]

            disclosure=named('routeDetailsDisclosure');pointer_click(disclosure)
            details_expanded=details_state();expanded_texts=visible_texts()
            endpoint_objects=[item for item in visual_objects(panel) if shown(item) and item_text(item)==endpoint_notice]
            details_content=named('routeDetailsContent')
            detail_labels=[item for item in visual_objects(details_content)
                if item is not details_content and item.objectName() and shown(item) and item_text(item)]
            expanded_layout=content_layout(
                [fallback_anchor,disclosure,named('routeName'),named('saveRouteButton')]+detail_labels)
            endpoint_inside=[]
            for item in endpoint_objects:
                parent=item.parentItem();inside=False
                while parent is not None:
                    if parent is details_content:inside=True;break
                    parent=parent.parentItem()
                endpoint_inside.append(inside)
            candidate_value=detached(state()['candidate'])
            all_walking_items=object_value(panel,'walkingItems')
            access_markers=[item for item in all_walking_items if item.property('accessCoordinate') is not None]
            rendered_lines=[item for item in all_walking_items if item.property('linePattern')]
            provider_rows=current_fixture_rows()
            current_presentation={'access_marker_observations':[
                    {'object_id':object_id(item),'object_name':item.objectName() or 'accessMarkerFactory',
                     'coordinate_property':'accessCoordinate',
                     'coordinate':detached(object_value(item,'accessCoordinate'))}
                    for item in access_markers],
                'source_feature_observations':[
                    {'provider_layer_id':site_layer_id(),
                     'provider_feature_id':row['attributes']['site_id'],
                     'coordinate_source':'provider feature geometry',
                     'coordinate':detached(row['geometry']['coordinates'])}
                    for row in provider_rows],
                'walking_line_observations':[
                    {'object_id':object_id(item),'object_name':item.objectName() or 'walkingFactory',
                     'coordinates_property':'coordinates',
                     'coordinates':detached(object_value(item,'coordinates')),
                     'line_pattern':str(item.property('linePattern')),
                     'warning_marker':bool(item.property('warningMarker'))}
                    for item in rendered_lines],
                'visit_model_observation':{'model_source':'panel.candidate.visits',
                    'visits':candidate_value['visits']},
                'walking_totals_observation':{'model_source':'panel.candidate.walking_totals',
                    'value':candidate_value['walking_totals']},
                'source_coordinate_write_attempts':detached(source_writes),
                'fallback_notice_accessible':fallback_accessible,
                'endpoint_gap_details':[{'text':item_text(item),
                    'accessible_name':accessibility(item)['name'],'object_id':object_id(item),
                    'inside_details':inside}
                    for item,inside in zip(endpoint_objects,endpoint_inside)]}
            pointer_click(disclosure);details_collapsed_again=details_state()
            candidate_after_toggle=detached(state()['candidate'])
            requests_after_toggle=len(requests);writes_after_toggle=len(writes)
            save_after_toggle=bool(named('saveRouteButton').property('enabled'))

            invalid_layer=named('layerEdit');valid_layer=str(invalid_layer.property('text'))
            invalid_layer.setProperty('text','');js('p.refreshTargets()');drain()
            center_in_view(named('saveRouteButton'))
            invalid_reason={'text':item_text(named('saveDisabledReason')),
                'mapping_validation':str(panel.property('mappingValidation')),
                'save_enabled':bool(named('saveRouteButton').property('enabled')),
                'reason_viewport':viewport(named('saveDisabledReason')),
                'save_viewport':viewport(named('saveRouteButton'))}
            invalid_layer.setProperty('text',valid_layer);js('p.refreshTargets()');drain()

            saved_observation=None
            if composition=='mixed':
                control('routeName','추정 포함 저장 경로')
                save_button=named('saveRouteButton');pointer_click(save_button)
                saved_document=detached(stored());saved_route=detached(active())
                open_panel();settings();window.show();panel.setProperty('expanded',True);app.processEvents()
                saved_notice=[item for item in visual_objects(panel) if shown(item) and item_text(item)==fallback_notice]
                saved_observation={'save_ok':saved_document is not None and state()['candidate'] is None,
                    'document':saved_document,'route':saved_route,'details':details_state(),
                    'notice_screen_count':len(saved_notice),'notice_accessible_count':len(accessible_matches(fallback_notice))}
            result.update(composition=composition,no_candidate_reason=no_candidate_observation,
                candidate_before=candidate_before,payload_before=payload_before,
                default_visible_texts=default_texts,default_accessible_names=default_accessible_names,
                details_before=details_before,
                fallback_notice_screen_count=len(fallback_screen),fallback_notice_accessible=fallback_accessible,
                endpoint_gap_default_visible_count=len(endpoint_default),acknowledgement_control_count=len(acknowledgement_controls),
                details_expanded=details_expanded,expanded_visible_texts=expanded_texts,
                expanded_layout=expanded_layout,
                endpoint_gap_expanded_count=len(endpoint_objects),endpoint_gap_inside_details=endpoint_inside,
                current_presentation=current_presentation,
                details_collapsed_again=details_collapsed_again,candidate_after_toggle=candidate_after_toggle,
                payload_after_toggle=json.dumps(candidate_after_toggle,ensure_ascii=False,sort_keys=True,separators=(',',':')),
                request_count_before_toggle=requests_before,request_count_after_toggle=requests_after_toggle,
                write_count_before_toggle=writes_before,write_count_after_toggle=writes_after_toggle,
                save_enabled_before_toggle=save_before,save_enabled_after_toggle=save_after_toggle,
                invalid_mapping_reason=invalid_reason,saved_observation=saved_observation,
                qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
        else:
            # Seed one last-good route through the production save path, then calculate a new
            # all-mapped candidate.  The save-attempt assertions below start after this setup.
            configure_candidate('all_mapped');control('routeName','마지막 정상 경로')
            if not save('마지막 정상 경로'):raise RuntimeError('failed to seed last-good route')
            configure_candidate('mixed')
            disclosure=named('routeDetailsDisclosure')
            if not bool(named('routeDetailsContent').property('visible')):pointer_click(disclosure)
            route_name='새 저장 경로';control('routeName',route_name)
            save_button=named('saveRouteButton');scroll=named('routeScroll');flickable=scroll.property('contentItem')
            keyboard_traversal=keyboard_order()
            save_button.forceActiveFocus(Qt.TabFocusReason);app.processEvents()
            within=save_button.mapToItem(flickable,QPointF(0,0))
            flickable.setProperty('contentY',max(0,within.y()-flickable.height()/2+save_button.height()/2));app.processEvents()
            status=named('saveStatus');status_before_viewport=viewport(status)
            outcome=case['outcome']
            if outcome=='revision_conflict':
                repository_source=(folder/'qfield_routes/repository.js').read_text(encoding='utf8')
                js('var conflictRepository=(function(){'+repository_source+';return {save:save};})();')
                js('conflictRepository.save({exists:function(p){return boundaryHost.exists(p)},read:function(p){return boundaryHost.read(p)},write:function(p,t){return boundaryHost.write(p,t)}},'+json.dumps(str(folder/'survey-routes'))+',JSON.parse('+json.dumps(json.dumps(stored(),ensure_ascii=False))+'),'+str(state()['snapshot']['revision'])+')')
            def latest_envelope():
                rows=[]
                for path in folder.glob('survey-routes.*.json'):
                    try:
                        envelope=json.loads(path.read_text(encoding='utf8'))
                        rows.append((int(envelope['revision']),path,envelope))
                    except (ValueError,KeyError,TypeError):pass
                return max(rows,key=lambda row:row[0])
            persisted_revision_before,last_good_path,_=latest_envelope()
            candidate_before=detached(state()['candidate']);document_before=detached(stored())
            revision_before=int(state()['snapshot']['revision']);last_good_bytes=last_good_path.read_bytes()
            provider_before=len(requests);write_before=len(writes);focus_before=window.activeFocusItem()
            disclosure_before=bool(named('routeDetailsContent').property('visible'))
            if outcome=='blank_name':control('routeName','')
            elif outcome=='stale_input':control('roundtripBox',not bool(named('roundtripBox').property('checked')),'checked')
            elif outcome=='write_false':storage_fault='commit_failure'
            elif outcome=='readback_mismatch':storage_fault='partial_write'
            name_before=str(named('routeName').property('text'))
            if outcome=='exception':
                js('var originalSave=p.controller.save;p.controller.save=function(){throw new Error("합성 저장 예외. 다시 시도하세요.")}')
            focus_transitions=[]
            window.activeFocusItemChanged.connect(lambda:focus_transitions.append(
                window.activeFocusItem().objectName() if window.activeFocusItem() else None))
            QMetaObject.invokeMethod(save_button,'clicked',Qt.DirectConnection)
            candidate_immediate=detached(state()['candidate'])
            save_enabled_immediate=bool(save_button.property('enabled'))
            disabled_reason_immediate={'text':item_text(named('saveDisabledReason')),
                'visible':shown(named('saveDisabledReason'))}
            focus_after_platform_clear=None
            if outcome=='success':
                save_button.setProperty('focus',False)
                focus_after_platform_clear=(window.activeFocusItem().objectName()
                    if window.activeFocusItem() else None)
            drain()
            if outcome=='exception':js('p.controller.save=originalSave')
            storage_fault=''
            final_message=str(panel.property('message'));status_after=named('saveStatus')
            status_matches=accessible_matches(final_message)
            document_after=detached(stored());candidate_after=detached(state()['candidate'])
            persisted_revision_after=latest_envelope()[0]
            success=outcome=='success'
            semantic_order=semantic_observation()
            qml_source=(folder/'qfield_routes/RoutePanel.qml').read_text(encoding='utf8')
            result.update(outcome=outcome,route_name=route_name,status_text=item_text(status_after),
                status_viewport_before=status_before_viewport,status_viewport_after=viewport(status_after),
                announcement_proxy_matches=status_matches,
                candidate_before=candidate_before,candidate_after=candidate_after,
                document_before=document_before,document_after=document_after,
                revision_before=revision_before,revision_after=int(state()['snapshot']['revision']),
                persisted_revision_before=persisted_revision_before,persisted_revision_after=persisted_revision_after,
                last_good_bytes_unchanged=last_good_path.exists() and last_good_path.read_bytes()==last_good_bytes,
                active_after=detached(active()),success_expected=success,
                provider_request_count_before=provider_before,provider_request_count_after=len(requests),
                write_attempt_count_before=write_before,write_attempt_count_after=len(writes),
                focus_object_before=focus_before.objectName() if focus_before else None,
                focus_object_after=window.activeFocusItem().objectName() if window.activeFocusItem() else None,
                focus_after_platform_clear=focus_after_platform_clear,
                focus_transitions=focus_transitions,
                app_focus_recovery_api_occurrences=qml_source.count('saveRouteButton.forceActiveFocus'),
                candidate_immediate=candidate_immediate,
                save_enabled_immediate=save_enabled_immediate,
                save_enabled_after=bool(save_button.property('enabled')),
                disabled_reason_immediate=disabled_reason_immediate,
                route_name_before=name_before,route_name_after=str(named('routeName').property('text')),
                disclosure_before=disclosure_before,disclosure_after=bool(named('routeDetailsContent').property('visible')),
                keyboard_traversal=keyboard_traversal,semantic_order=semantic_order,
                outcome_layout=semantic_order['layout'],
                qml_runtime={'loaded_generated_qml':True,'generated_qml_path':str(folder/'qfield_routes/RoutePanel.qml')})
'''
if source.count(marker) != 1:
    raise RuntimeError("canonical QML driver branch marker changed")
source = source.replace(marker, branch + marker)

sys.stdin = io.StringIO(payload)
exec(compile(source, str(driver), "exec"), {"__name__": "__main__", "__file__": str(driver)})
