"""Import approved door clips and link the village to its cached gray sublevel."""
import json
import shutil
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Doors/Integration'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / 'backups'
BACKUP.mkdir(exist_ok=True)
VILLAGE = '/Game/Maps/L_VillageTerrain_01'
ROOM = '/Game/Maps/Interiors/L_CozyHouse01_Gray'
HOUSE = '/Game/Characters/Meshy/CozyHouse01/candidate_v002/BP_CozyHouse01_Split'
STATIC_FOLDER = '/Game/Characters/Meshy/CozyHouse01/candidate_v003'
ANIM_FOLDER = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/Animations/Door01'
INTERIOR_FOLDER = '/Game/Doors/CozyHouse01'
TABLE = '/Game/Data/Interactions/DT_Interactions'
REIMPORT = '-DoorReimport' in unreal.SystemLibrary.get_command_line()

for path in ['Content/Maps/L_VillageTerrain_01.umap',
             'Content/Maps/Interiors/L_CozyHouse01_Gray.umap',
             'Content/Characters/Meshy/CozyHouse01/candidate_v002/BP_CozyHouse01_Split.uasset',
             'Content/Data/Interactions/DT_Interactions.uasset']:
    source = ROOT / path
    destination = BACKUP / source.name
    if source.exists() and not destination.exists():
        shutil.copy2(source, destination)

tools = unreal.AssetToolsHelpers.get_asset_tools()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
material = unreal.load_asset('/Game/Characters/Meshy/CozyHouse01/candidate_v001/M_CozyHouse01')
model = unreal.load_asset('/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy')
skeleton = model.get_editor_property('skeleton')
assert material and skeleton


def import_asset(filename, folder, name, kind):
    existing = unreal.load_asset(folder + '/' + name)
    expected = unreal.AnimSequence if kind == 'animation' else unreal.StaticMesh
    if existing and not REIMPORT:
        assert isinstance(existing, expected)
        return existing
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_materials = options.import_textures = False
    if kind == 'animation':
        options.skeleton = skeleton
        options.import_mesh = False
        options.import_as_skeletal = True
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        options.import_animations = True
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', True)
    else:
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_animations = False
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = unreal.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = folder
    task.destination_name = name
    task.automated = task.save = True
    task.replace_existing = bool(existing)
    task.factory = unreal.FbxFactory()
    task.options = options
    tools.import_asset_tasks([task])
    asset = unreal.load_asset(folder + '/' + name)
    assert isinstance(asset, expected), name
    if kind == 'animation':
        assert asset.get_editor_property('skeleton') == skeleton
        assert 3.5 < asset.get_play_length() < 3.7, asset.get_play_length()
        asset.set_editor_property('enable_root_motion', False)
    else:
        assert len(asset.get_editor_property('static_materials')) == 1
        asset.set_material(0, material)
        asset.get_editor_property('body_setup').set_editor_property(
            'collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    return asset


motion_dir = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/Animations/Door01'
push = import_asset(motion_dir / 'TownKeeper_Meshy_DoorPush.fbx', ANIM_FOLDER, 'A_TownKeeper_DoorPush', 'animation')
pull = import_asset(motion_dir / 'TownKeeper_Meshy_DoorPull.fbx', ANIM_FOLDER, 'A_TownKeeper_DoorPull', 'animation')
static_dir = ROOT / 'ArtSource/Meshy/CozyHouse01/candidate_v003'
leaf = import_asset(static_dir / 'DoorLeaf.fbx', STATIC_FOLDER, 'SM_CozyHouse01_DoorLeaf', 'static')
frame_mesh = import_asset(static_dir / 'DoorFrame.fbx', STATIC_FOLDER, 'SM_CozyHouse01_DoorFrame', 'static')

table = unreal.load_asset(TABLE)
assert table
assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(
    table, str(ROOT / 'Tools/Interaction/Interactions.csv'))
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)


def template_components(bp):
    result = {}
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        obj = lib.get_object_for_blueprint(lib.get_data(handle), bp)
        result[obj.get_name().removesuffix('_GEN_VARIABLE')] = (handle, obj)
    return result


def add_component(bp, parent, cls, name):
    current = template_components(bp)
    if name in current:
        handle, obj = current[name]
        assert isinstance(obj, cls), name
        return handle, obj
    handle, error = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=parent, new_class=cls, blueprint_context=bp))
    assert lib.is_handle_valid(handle), str(error)
    assert subobjects.rename_subobject(handle, unreal.Text(name))
    return handle, lib.get_object_for_blueprint(lib.get_data(handle), bp)


def transform(position, yaw=0):
    return unreal.Transform(location=unreal.Vector(*position),
                            rotation=unreal.Rotator(pitch=0, yaw=yaw, roll=0))


def author_portal(bp, interior):
    handles = subobjects.k2_gather_subobject_data_for_blueprint(bp)
    root = handles[0]
    components = template_components(bp)
    if interior:
        root_handle, root_component = add_component(bp, root, unreal.SceneComponent, 'InteriorRoot')
        root_component.set_mobility(unreal.ComponentMobility.STATIC)
        frame_handle, frame = add_component(bp, root_handle, unreal.StaticMeshComponent, 'DoorFrame')
        frame.set_static_mesh(frame_mesh)
        frame.set_mobility(unreal.ComponentMobility.STATIC)
        frame.set_editor_property('relative_location', unreal.Vector(46.1, 0, 1.4))
        frame.set_collision_profile_name('BlockAll')
        hinge_handle, hinge = add_component(bp, root_handle, unreal.SceneComponent, 'DoorHinge')
        hinge.set_mobility(unreal.ComponentMobility.MOVABLE)
        hinge.set_editor_property('relative_location', unreal.Vector(46.1, 0, 1.4))
        _, door = add_component(bp, hinge_handle, unreal.StaticMeshComponent, 'DoorLeaf')
    else:
        door = components['DoorLeaf'][1]
    door.set_static_mesh(leaf)
    door.set_mobility(unreal.ComponentMobility.MOVABLE)
    door.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
    door.set_editor_property('relative_rotation', unreal.Rotator(pitch=0, yaw=0, roll=0))
    door.set_collision_profile_name('BlockAll')
    _, target = add_component(bp, root, unreal.TownAgeInteractionTargetComponent, 'DoorInteraction')
    target.set_editor_property('definition', unreal.DataTableRowHandle(
        data_table=table, row_name='DoorExit' if interior else 'DoorEnter'))
    target.set_editor_property('local_interaction_point', unreal.Vector(0, -12, 90) if interior else unreal.Vector(123, 155, 90))
    target.set_editor_property('local_approach_direction', unreal.Vector(0, -1, 0) if interior else unreal.Vector(0, 1, 0))
    _, portal = add_component(bp, root, unreal.TownAgeDoorPortalComponent, 'DoorPortal')
    portal.set_editor_property('portal_id', 'CozyHouse01')
    portal.set_editor_property('interior_side', interior)
    portal.set_editor_property('interior_level', unreal.load_asset(ROOM))
    portal.set_editor_property('action_animation', pull if interior else push)
    portal.set_editor_property('local_align_transform', transform((-2.4, -59.5, 88.2), 90) if interior else transform((120, 190, 89), -90))
    portal.set_editor_property('local_end_transform', transform((-2.4, 53.5, 88.2), 90) if interior else transform((120, 33, 89), -90))
    portal.set_editor_property('destination_transform', transform((2920, -920, 88.2), 90) if interior else transform((49997.6, 120, 88.2), -90))
    for _, component in template_components(bp).values():
        if isinstance(component, unreal.SceneComponent) and component.get_name().removesuffix('_GEN_VARIABLE') == 'DefaultSceneRoot':
            component.set_mobility(unreal.ComponentMobility.STATIC)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cls = unreal.EditorAssetLibrary.load_blueprint_class(bp.get_path_name().split('.')[0])
    defaults = unreal.get_default_object(cls)
    defaults.set_editor_property('replicates', True)
    defaults.set_editor_property('always_relevant', True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    return cls


house_bp = unreal.load_asset(HOUSE)
assert house_bp
author_portal(house_bp, False)
interior_path = INTERIOR_FOLDER + '/BP_CozyHouse01_InteriorDoor'
interior_bp = unreal.load_asset(interior_path)
if interior_bp is None:
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    interior_bp = tools.create_asset('BP_CozyHouse01_InteriorDoor', INTERIOR_FOLDER, unreal.Blueprint, factory)
interior_class = author_portal(interior_bp, True)

# Author the room in its own local coordinates before applying a streaming transform.
assert levels.load_level(ROOM)
exits = [a for a in actors.get_all_level_actors() if a.get_actor_label() == 'CozyHouse01_InteriorDoor']
assert len(exits) <= 1
if exits:
    actors.destroy_actor(exits[0])
exit_actor = actors.spawn_actor_from_class(interior_class, unreal.Vector(0, 300, 0))
exit_actor.set_actor_label('CozyHouse01_InteriorDoor')
assert levels.save_current_level()

assert levels.load_level(VILLAGE)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
houses = [a for a in actors.get_all_level_actors() if a.get_actor_label() == 'CozyHouse01_Review']
assert len(houses) == 1
assert houses[0].get_component_by_class(unreal.TownAgeDoorPortalComponent)
streaming = unreal.GameplayStatics.get_streaming_level(world, ROOM)
if streaming is None:
    streaming = unreal.EditorLevelUtils.add_level_to_world_with_transform(
        world, ROOM, unreal.LevelStreamingDynamic, transform((50000, 0, 0)))
assert streaming
streaming.set_editor_property('level_transform', transform((50000, 0, 0)))
streaming.set_editor_property('initially_loaded', True)
streaming.set_editor_property('initially_visible', True)
# These serialized dynamic-level defaults control runtime loading. The native
# portal prepares visibility as needed; BlueprintSetter methods are exposed as
# properties rather than callable methods in this Python build.
# Adding a streaming level makes it the editor's current level. Save the
# persistent village explicitly, never bake its offset into the room package.
assert unreal.EditorLoadingAndSavingUtils.save_map(world, VILLAGE)
report = {'village': VILLAGE, 'room': ROOM, 'streaming_offset_cm': [50000, 0, 0],
          'room_cached': True, 'room_player_start_added': False,
          'outside_portal': HOUSE, 'inside_portal': interior_path,
          'push_animation': push.get_path_name(), 'pull_animation': pull.get_path_name(),
          'pose_blend_seconds': .22, 'clip_endpoint_ease_seconds': .2,
          'door_leaf': leaf.get_path_name(), 'door_frame': frame_mesh.get_path_name(),
          'data_rows': ['DoorEnter', 'DoorExit'], 'production_character_mesh_changed': False}
(OUT / 'setup_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('DOOR_TRAVEL_SETUP_COMPLETE', json.dumps(report))
