"""Verify saved-layout rehydration and select it for native viewport testing."""
import json
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/MapLayout'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
plans = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.TownAgeMapLayout)]
assert len(plans) == 1
plan = plans[0]
count = unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan)
components = plan.get_components_by_class(unreal.InstancedStaticMeshComponent)
actual = sum(c.get_instance_count() for c in components)
assert count == actual == 9, (count, actual)
snapshot = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
assert len(snapshot['elements']) == 7
unreal.TownAgeMapEditorLibrary.use_layout(plan)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    unreal.Vector(0, -100, 10000), unreal.Rotator(-90, -90, 0))
(OUT / 'editor_load_report.json').write_text(json.dumps({'passed': True, 'elements': 7, 'instances': count,
                                                       'components': len(components)}, indent=2), encoding='utf-8')
print('MAP_LAYOUT_SAVED_LOAD_PASS')
