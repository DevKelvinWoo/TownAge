"""Capture editor data after a native authoring action without changing the map."""
import json
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/MapLayout'
plans = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
         if isinstance(a, unreal.TownAgeMapLayout)]
rows = []
for plan in plans:
    data = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
    data['generatedInstances'] = unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan)
    rows.append(data)
(OUT / 'interaction_state.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('MAP_LAYOUT_NATIVE_STATE_CAPTURED')
