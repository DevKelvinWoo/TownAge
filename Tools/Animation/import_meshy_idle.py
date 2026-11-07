"""Import the approved calm Idle and preserve it in Meshy locomotion and previews.

Run in the saved/closed editor's Python commandlet. No mesh, skin or rest-pose import.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
manifest = json.loads((ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/Animations/Idle01/manifest.json').read_text(encoding='utf-8'))
DEST = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/Animations/Locomotion01'
MODEL = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy'
BP_PATHS = ['/Game/Characters/Main/TownKeeper/BP_TownKeeper',
            '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/BP_TownKeeper_Meshy']
mesh = unreal.load_asset(MODEL)
skeleton = mesh.get_editor_property('skeleton')
assert skeleton
source = Path(manifest['fbx_path'])
assert source.is_file() and source.name == 'TownKeeper_Meshy_Idle_Calm.fbx'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
options = unreal.FbxImportUI()
options.automated_import_should_detect_type = False
options.skeleton = skeleton
options.import_mesh = False
options.import_as_skeletal = True
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', True)
task = unreal.AssetImportTask()
task.filename = str(source)
task.destination_path = DEST
task.destination_name = 'A_TownKeeper_Meshy_Idle'
task.options = options
task.factory = unreal.FbxFactory()
task.automated = True
task.replace_existing = True
task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
idle = unreal.load_asset(DEST + '/A_TownKeeper_Meshy_Idle')
assert isinstance(idle, unreal.AnimSequence)
assert idle.get_editor_property('skeleton') == skeleton
assert abs(idle.get_play_length() - manifest['duration_seconds']) < .001
idle.set_editor_property('enable_root_motion', False)
unreal.EditorAssetLibrary.save_loaded_asset(idle, False)

blend = unreal.load_asset(DEST + '/BS_TownKeeper_Meshy_Locomotion')
assert blend.get_editor_property('skeleton') == skeleton
samples = blend.get_editor_property('sample_data')
assert len(samples) == 3
zero = samples[0]
assert zero.get_editor_property('sample_value').x == 0
zero.set_editor_property('animation', idle)
samples[0] = zero
blend.set_editor_property('sample_data', samples)
blend.set_editor_property('target_weight_interpolation_speed_per_sec', 6.0)
blend.set_editor_property('target_weight_interpolation_ease_in_out', True)
# One sample-weight filter; no extra axis or native velocity smoothing.
parameters = blend.get_editor_property('interpolation_param')
for index, parameter in enumerate(parameters):
    parameter.set_editor_property('interpolation_time', 0.0)
    parameters[index] = parameter
blend.set_editor_property('interpolation_param', parameters)
assert unreal.TownAgePlayer.rebuild_walk_blend_space(blend)
for index, speed in enumerate([0, 87, 304]):
    weights = unreal.TownAgePlayer.get_locomotion_sample_weights(blend, speed)
    assert [weights.x, weights.y, weights.z][index] > .99
unreal.EditorAssetLibrary.save_loaded_asset(blend, False)

subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
for path in BP_PATHS:
    blueprint = unreal.load_asset(path)
    assert blueprint
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(blueprint):
        component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
        if isinstance(component, unreal.SkeletalMeshComponent):
            assert component.get_skeletal_mesh_asset() == mesh
            component.override_animation_data(idle, True, True, 0, 1)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Maps/L_CharacterTest')
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_class().get_path_name().split('.')[0] in BP_PATHS:
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            component.override_animation_data(idle, True, True, 0, 1)
assert level.save_current_level()
report = {'idle': idle.get_path_name(), 'duration_seconds': idle.get_play_length(),
          'skeleton': skeleton.get_path_name(), 'blend_space': blend.get_path_name(),
          'weight_interpolation_speed': 6.0, 'weight_ease_in_out': True,
          'axis_smoothing_seconds': 0.0, 'native_moving_thresholds_cm_s': {'enter': 4, 'exit': 2},
          'model_or_weights_modified': False}
(ROOT / 'Saved/meshy_idle_import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MESHY_IDLE_IMPORTED', json.dumps(report))
