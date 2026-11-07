"""Import the polished character and its rest-pose-adapted approved walk.

Run in Unreal's Python commandlet with the interactive editor saved and closed.
The old production assets remain untouched for recovery.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Characters/Main/Revision05'
DEST = '/Game/Characters/Main/TownKeeper/FinalCharacter05'
ANIMS = DEST + '/Animations'
BP_PATH = '/Game/Characters/Main/TownKeeper/BP_TownKeeper'
MAP_PATH = '/Game/Maps/L_CharacterTest'
manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
tools = unreal.AssetToolsHelpers.get_asset_tools()
# Use the FBX factory whose FbxImportUI options this script configures, rather
# than the default Interchange pipeline silently interpreting a different UI.
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
unreal.EditorAssetLibrary.make_directory(DEST)
unreal.EditorAssetLibrary.make_directory(ANIMS)


def import_asset(filename, name, folder=DEST, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.factory = unreal.FbxFactory()
        task.options = options
    tools.import_asset_tasks([task])
    asset = unreal.load_asset(folder + '/' + name)
    assert asset, (filename, list(task.imported_object_paths))
    return asset


options = unreal.FbxImportUI()
options.import_as_skeletal = True
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = True
existing_skeleton = unreal.load_asset(DEST + '/SK_TownKeeper_Reference05_Skeleton')
if existing_skeleton:
    options.skeleton = existing_skeleton
# Create a separate skeleton: the compact body's reference bone positions changed.
options.skeletal_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = import_asset(manifest['fbx_path'], 'SK_TownKeeper_Reference05', options=options)
assert isinstance(mesh, unreal.SkeletalMesh)
skeleton = mesh.get_editor_property('skeleton')
assert skeleton
# AssetImportTask.save can save only the primary Interchange result. Persist
# generated dependencies explicitly before any animation refers to them.
assert unreal.EditorAssetLibrary.save_loaded_asset(skeleton, False)
physics = mesh.get_editor_property('physics_asset')
if not physics:
    # AICallable UFUNCTION has no generated Python glue in UE5.8.
    physics = unreal.get_default_object(unreal.PhysicsAssetToolset).call_method(
        'CreateFromMesh', (DEST + '/SK_TownKeeper_Reference05', True))
assert physics, 'Physics asset creation failed'
assert unreal.EditorAssetLibrary.save_loaded_asset(physics, False)
height = mesh.get_bounds().box_extent.z * 2
assert abs(height - 170) < 1, height

materials = {}
for item in manifest['materials']:
    material = unreal.load_asset(DEST + '/' + item['name'])
    if not material:
        material = tools.create_asset(item['name'], DEST, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('two_sided', False)
    for channel, prop in [('basecolor', unreal.MaterialProperty.MP_BASE_COLOR),
                          ('roughness', unreal.MaterialProperty.MP_ROUGHNESS),
                          ('normal', unreal.MaterialProperty.MP_NORMAL)]:
        if not item.get(channel):
            continue
        texture = import_asset(item[channel], 'T_' + item['name'] + '_' + channel)
        texture.set_editor_property('srgb', channel == 'basecolor')
        if channel == 'normal':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', False)  # Source is DirectX -Y.
        unreal.EditorAssetLibrary.save_loaded_asset(texture)
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(material, prop)
        if not isinstance(node, unreal.MaterialExpressionTextureSample):
            node = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSample)
        node.texture = texture
        node.sampler_type = {'basecolor': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                             'roughness': unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,
                             'normal': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL}[channel]
        assert unreal.MaterialEditingLibrary.connect_material_property(node, 'R' if channel == 'roughness' else 'RGB', prop)
    specular = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_SPECULAR)
    if not isinstance(specular, unreal.MaterialExpressionConstant):
        specular = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
    specular.r = .22
    unreal.MaterialEditingLibrary.connect_material_property(specular, '', unreal.MaterialProperty.MP_SPECULAR)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    materials[item['slot']] = material

slots = mesh.get_editor_property('materials')
for index, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    assert name in materials, (name, list(materials))
    slot.material_interface = materials[name]
    slots[index] = slot
mesh.set_editor_property('materials', slots)
unreal.EditorAssetLibrary.save_loaded_asset(mesh)

clips = {}
for label in ('Standing', 'Walk'):
    entry = manifest[label.lower()]
    options = unreal.FbxImportUI()
    options.skeleton = skeleton
    options.import_mesh = False
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', True)
    clip = import_asset(entry['path'], 'A_TownKeeper_' + label, ANIMS, options)
    assert isinstance(clip, unreal.AnimSequence)
    assert clip.get_editor_property('skeleton') == skeleton
    clip.set_editor_property('enable_root_motion', False)
    unreal.EditorAssetLibrary.save_loaded_asset(clip)
    clips[label] = clip

speed = float(manifest['walk']['speed_cm_s'])
assert abs(speed - 64 * 30 / 28) < .001, 'Gameplay speed changes require an explicit coordinated update'
blend = unreal.load_asset(ANIMS + '/BS_TownKeeper_Walk')
if not blend:
    factory = unreal.BlendSpaceFactory1D()
    factory.target_skeleton = skeleton
    blend = tools.create_asset('BS_TownKeeper_Walk', ANIMS, unreal.BlendSpace1D, factory)
assert blend.get_editor_property('skeleton') == skeleton
params = blend.get_editor_property('blend_parameters')
axis = params[0]
axis.set_editor_property('display_name', 'Speed')
axis.set_editor_property('min', 0.0)
axis.set_editor_property('max', 70.0)  # Keep the double sample inside float axis bounds.
params[0] = axis
blend.set_editor_property('blend_parameters', params)
samples = []
for label, value in [('Standing', 0.0), ('Walk', speed)]:
    sample = unreal.BlendSample()
    sample.set_editor_property('animation', clips[label])
    sample.set_editor_property('sample_value', unreal.Vector(value, 0, 0))
    sample.set_editor_property('rate_scale', 1.0)
    samples.append(sample)
blend.set_editor_property('sample_data', samples)
assert unreal.TownAgePlayer.rebuild_walk_blend_space(blend)
idle = unreal.TownAgePlayer.get_walk_blend_weights(blend, 0)
walk = unreal.TownAgePlayer.get_walk_blend_weights(blend, speed)
assert idle.x > .99 and walk.y > .99, (idle, walk)
unreal.EditorAssetLibrary.save_loaded_asset(blend)

# Change the existing Blueprint's component template, retaining every placed actor.
blueprint = unreal.load_asset(BP_PATH)
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
updated = []
bone_names = []
for handle in subobjects.k2_gather_subobject_data_for_blueprint(blueprint):
    data = library.get_data(handle)
    component = library.get_object_for_blueprint(data, blueprint)
    if isinstance(component, unreal.SkeletalMeshComponent):
        component.set_skeletal_mesh_asset(mesh)
        component.set_editor_property('override_materials', [])
        component.set_editor_property('physics_asset_override', None)
        component.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
        component.override_animation_data(clips['Standing'], True, True, 0, 1)
        bone_names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
        assert bone_names and bone_names[0] == 'Armature_008', bone_names
        updated.append(component.get_path_name())
assert updated, 'No Blueprint skeletal component template found'
unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
unreal.EditorAssetLibrary.save_loaded_asset(blueprint)

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level(MAP_PATH)
placed = []
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_class().get_path_name() == BP_PATH + '.BP_TownKeeper_C':
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property('override_materials', [])
            component.set_editor_property('physics_asset_override', None)
            component.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
            component.override_animation_data(clips['Standing'], True, True, 0, 1)
        # Keep the editor's inspection actor but let GameMode spawn the sole playable hero.
        actor.set_actor_hidden_in_game(True)
        placed.append(actor.get_path_name())
assert level.save_current_level()
assert unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=False, recursive=True)
report = {'mesh': mesh.get_path_name(), 'height_cm': height,
          'bone_names': bone_names,
          'skeleton': skeleton.get_path_name(), 'material_slots': [str(s.material_slot_name) for s in slots],
          'placement_blueprint': BP_PATH, 'updated_templates': updated, 'placed_actors': placed,
          'clips': {k: {'path': v.get_path_name(), 'length_seconds': v.get_play_length()} for k, v in clips.items()},
          'blend_space': blend.get_path_name(), 'walk_speed_cm_s': speed,
          'idle_weights': [idle.x, idle.y], 'walk_weights': [walk.x, walk.y]}
(ROOT / 'Saved/revision05_import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REVISION05_IMPORT_COMPLETE', json.dumps(report))
