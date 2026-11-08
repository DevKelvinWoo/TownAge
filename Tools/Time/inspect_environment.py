"""Read-only environment inventory; run with Unreal's Python commandlet."""
import json
from pathlib import Path
import unreal

reports = []
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for path in ['/Game/Maps/L_CharacterTest', '/Game/Maps/L_VillageTerrain_01']:
    if not levels.load_level(path):
        raise RuntimeError(path)
    rows = []
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        cls = actor.get_class().get_name()
        if not any(word in (label + cls).lower() for word in ['sky', 'light', 'fog', 'exposure', 'postprocess']):
            continue
        row = {'label': label, 'class': cls, 'path': actor.get_path_name()}
        if isinstance(actor, unreal.DirectionalLight):
            light = actor.get_editor_property('light_component')
            row.update(intensity=light.get_editor_property('intensity'), rotation=str(actor.get_actor_rotation()))
        if isinstance(actor, unreal.SkyLight):
            light = actor.get_editor_property('light_component')
            row.update(intensity=light.get_editor_property('intensity'), source_type=str(light.get_editor_property('source_type')),
                       realtime_capture=light.get_editor_property('real_time_capture'))
        if isinstance(actor, unreal.PostProcessVolume):
            settings = actor.get_editor_property('settings')
            row['exposure'] = {key: str(settings.get_editor_property(key)) for key in
                ['auto_exposure_method', 'auto_exposure_bias', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness']}
        for mesh in actor.get_components_by_class(unreal.StaticMeshComponent):
            materials = []
            for i in range(mesh.get_num_materials()):
                mat = mesh.get_material(i)
                if mat:
                    materials.append({'path': mat.get_path_name(), 'vectors': [str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(mat)],
                                      'scalars': [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mat)]})
            row['materials'] = materials
        rows.append(row)
    reports.append({'map': path, 'actors': rows})
out = Path(__file__).resolve().parents[2] / 'Saved/Time'
out.mkdir(parents=True, exist_ok=True)
(out / 'environment_inventory.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print('TIME_ENVIRONMENT_INVENTORY_COMPLETE')
