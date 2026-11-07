"""Apply the directly requested provider locomotion to the retained Meshy character.

Run in Unreal's Python commandlet after saving and closing the editor.
Only animation assets, placement Blueprint animation data and the test level change.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/Animations/Locomotion01'
MODEL = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy'
DEST = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/Animations/Locomotion01'
BP_PATHS = ['/Game/Characters/Main/TownKeeper/BP_TownKeeper',
            '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/BP_TownKeeper_Meshy']
SPEEDS = {'Standing': 0.0, 'Walk': 87.0, 'Run': 304.0}
manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
mesh = unreal.load_asset(MODEL)
assert mesh and abs(mesh.get_bounds().box_extent.z * 2 - 170) < .01
skeleton = mesh.get_editor_property('skeleton')
assert skeleton
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
tools = unreal.AssetToolsHelpers.get_asset_tools()
unreal.EditorAssetLibrary.make_directory(DEST)
clips = {}
for label in SPEEDS:
    entry = manifest['clips'][label.lower()]
    source = Path(entry['path'])
    if not source.is_absolute():
        source = SOURCE / source
    assert source.is_file(), source
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
    name = 'A_TownKeeper_Meshy_' + label
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = DEST
    task.destination_name = name
    task.factory = unreal.FbxFactory()
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    clip = unreal.load_asset(DEST + '/' + name)
    assert isinstance(clip, unreal.AnimSequence), list(task.imported_object_paths)
    assert clip.get_editor_property('skeleton') == skeleton
    assert abs(clip.get_play_length() - float(entry['duration_seconds'])) < .001, (label, clip.get_play_length())
    clip.set_editor_property('enable_root_motion', False)
    unreal.EditorAssetLibrary.save_loaded_asset(clip, False)
    clips[label] = clip

blend = unreal.load_asset(DEST + '/BS_TownKeeper_Meshy_Locomotion')
if not blend:
    factory = unreal.BlendSpaceFactory1D()
    factory.target_skeleton = skeleton
    blend = tools.create_asset('BS_TownKeeper_Meshy_Locomotion', DEST, unreal.BlendSpace1D, factory)
assert blend.get_editor_property('skeleton') == skeleton
params = blend.get_editor_property('blend_parameters')
axis = params[0]
axis.set_editor_property('display_name', 'Speed')
axis.set_editor_property('min', 0.0)
axis.set_editor_property('max', 305.0)
params[0] = axis
blend.set_editor_property('blend_parameters', params)
samples = []
for label, speed in SPEEDS.items():
    sample = unreal.BlendSample()
    sample.set_editor_property('animation', clips[label])
    sample.set_editor_property('sample_value', unreal.Vector(speed, 0, 0))
    sample.set_editor_property('rate_scale', 1.0)
    samples.append(sample)
blend.set_editor_property('sample_data', samples)
assert unreal.TownAgePlayer.rebuild_walk_blend_space(blend)
weights = {}
if hasattr(unreal.TownAgePlayer, 'get_locomotion_sample_weights'):
    for index, (label, speed) in enumerate(SPEEDS.items()):
        value = unreal.TownAgePlayer.get_locomotion_sample_weights(blend, speed)
        weights[label] = [value.x, value.y, value.z]
        assert weights[label][index] > .99, (label, weights[label])
else:
    # The first import may precede the native build that adds the 3-sample query.
    # Fresh-process gameplay verification must query all three after that build.
    assert unreal.TownAgePlayer.get_walk_blend_weights(blend, 0).x > .99
    assert unreal.TownAgePlayer.get_walk_blend_weights(blend, 87).y > .99
unreal.EditorAssetLibrary.save_loaded_asset(blend, False)

subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
updated = []
for path in BP_PATHS:
    blueprint = unreal.load_asset(path)
    assert blueprint, path
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(blueprint):
        component = library.get_object_for_blueprint(library.get_data(handle), blueprint)
        if isinstance(component, unreal.SkeletalMeshComponent):
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property('override_materials', [])
            component.set_editor_property('physics_asset_override', None)
            component.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
            component.override_animation_data(clips['Standing'], True, True, 0, 1)
            updated.append(component.get_path_name())
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
assert updated

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Maps/L_CharacterTest')
placements = []
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_class().get_path_name().split('.')[0] in BP_PATHS:
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property('override_materials', [])
            component.set_editor_property('physics_asset_override', None)
            component.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
            component.override_animation_data(clips['Standing'], True, True, 0, 1)
        actor.set_actor_hidden_in_game(True)
        placements.append({'actor': actor.get_path_name(), 'transform': str(actor.get_actor_transform())})
assert level.save_current_level()
assert unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=False, recursive=True)
report = {'mesh': mesh.get_path_name(), 'skeleton': skeleton.get_path_name(),
          'blend_space': blend.get_path_name(), 'speeds_cm_s': SPEEDS,
          'clips': {key: {'path': clip.get_path_name(), 'duration_seconds': clip.get_play_length()} for key, clip in clips.items()},
          'weights': weights, 'requires_post_build_weight_verification': not bool(weights),
          'updated_blueprint_components': updated, 'preserved_placements': placements,
          'root_motion': False, 'model_or_weights_modified': False}
(ROOT / 'Saved/meshy_locomotion_import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MESHY_LOCOMOTION_IMPORTED', json.dumps(report))
