"""Replay the native gizmo delta handler and editor undo when input injection lacks raw mouse deltas."""
import json
import time
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/MapLayout'
STATE = {'start': time.monotonic(), 'busy': False}


def tick(_delta):
    if STATE['busy'] or time.monotonic() - STATE['start'] < 2:
        return
    STATE['busy'] = True
    try:
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        plans = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.TownAgeMapLayout)]
        assert len(plans) == 1
        plan = plans[0]
        assert plan.get_actor_label() == 'MapLayoutReview_Plan'
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        before = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
        record = next(e for e in plan.get_editor_property('elements') if e.get_editor_property('label') == 'Village shop')
        guid = record.get_editor_property('id')
        assert unreal.TownAgeMapEditorLibrary.translate_element(plan, guid, unreal.Vector(1000, 0, 0))
        after = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
        for old, new in zip(before['elements'], after['elements']):
            if old['label'] == 'Village shop':
                for a, b in zip(old['points'], new['points']):
                    assert abs(b['x'] - a['x'] - 1000) < .001
                    assert a['y'] == b['y'] and a['z'] == b['z']
            else:
                assert old == new, 'Unrelated placement moved'
        assert not unreal.TownAgeMapEditorLibrary.translate_element(plan, guid, unreal.Vector(1e20, 0, 0))
        assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan)) == after
        unreal.SystemLibrary.execute_console_command(world, 'TRANSACTION UNDO')
        assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan)) == before, 'Move undo failed'
        unreal.SystemLibrary.execute_console_command(world, 'TRANSACTION REDO')
        assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan)) == after, 'Move redo failed'
        unreal.SystemLibrary.execute_console_command(world, 'TRANSACTION UNDO')
        assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan)) == before
        assert unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan) == 9
        report = {'passed': True, 'world_delta_cm': [1000, 0, 0], 'moved_label': 'Village shop',
                  'unrelated_placements_unchanged': True, 'undo_redo_passed': True}
        print('MAP_LAYOUT_MOVE_HANDLER_PASS')
    except Exception:
        report = {'passed': False, 'error': traceback.format_exc()}
        print('MAP_LAYOUT_MOVE_HANDLER_FAIL: ' + report['error'])
    (OUT / 'move_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(unreal._map_layout_move_handle)


unreal._map_layout_move_handle = unreal.register_slate_post_tick_callback(tick)
