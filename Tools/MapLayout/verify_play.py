"""Check actual PIE geometry/collision from a saved review layout; never save the map."""
import json
import time
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/MapLayout'
STARTED = time.monotonic()
if hasattr(unreal, '_map_layout_play_handle'):
    unreal.unregister_slate_post_tick_callback(unreal._map_layout_play_handle)


def finish(report):
    (OUT / 'play_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(unreal._map_layout_play_handle)
    print('MAP_LAYOUT_PLAY_' + ('PASS' if report.get('passed') else 'FAIL'))


def tick(_delta):
    try:
        if time.monotonic() - STARTED > 45:
            finish({'passed': False, 'error': 'Timed out waiting for PIE'})
            return
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        rows = []
        for world in worlds:
            plans = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.TownAgeMapLayout)
            if len(plans) != 1:
                return
            plan = plans[0]
            components = plan.get_components_by_class(unreal.InstancedStaticMeshComponent)
            actual = sum(c.get_instance_count() for c in components)
            reported = unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan)
            assert actual == reported == 9, (actual, reported)
            assert all(c.get_collision_enabled() == unreal.CollisionEnabled.QUERY_AND_PHYSICS for c in components)
            rows.append({'world': world.get_path_name(), 'instances': actual, 'components': len(components)})
        finish({'passed': True, 'worlds': rows})
    except Exception:
        finish({'passed': False, 'error': traceback.format_exc()})


unreal._map_layout_play_handle = unreal.register_slate_post_tick_callback(tick)
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
