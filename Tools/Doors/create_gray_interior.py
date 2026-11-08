"""Create an isolated cutaway test room; do not link or alter the village."""
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
MAP = '/Game/Maps/Interiors/L_CozyHouse01_Gray'
FOLDER = '/Game/Environment/Interiors/CozyHouse01_Gray'
OUT = ROOT / 'Saved/Doors/GrayRoom'
OUT.mkdir(parents=True, exist_ok=True)
resume = '-ResumeGrayRoom' in unreal.SystemLibrary.get_command_line()
exists = unreal.EditorAssetLibrary.does_asset_exist(MAP)
assert not exists or resume, 'Existing room must not be overwritten'
existing_materials = unreal.EditorAssetLibrary.list_assets(FOLDER, True, False)
assert not existing_materials or (resume and all(
    path.split('.')[0] == FOLDER + '/M_GrayRoom' for path in existing_materials)), 'Material destination occupied'

tools = unreal.AssetToolsHelpers.get_asset_tools()
material = unreal.load_asset(FOLDER + '/M_GrayRoom') if resume else None
if material is None:
    material = tools.create_asset('M_GrayRoom', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    base = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
    base.set_editor_property('constant', unreal.LinearColor(.30, .32, .34, 1))
    assert unreal.MaterialEditingLibrary.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
    roughness.r = .9
    assert unreal.MaterialEditingLibrary.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
assert isinstance(material, unreal.Material)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level(MAP) if exists else levels.new_level(MAP)
assert all(a.get_actor_label().startswith('GrayRoom_') for a in actors.get_all_level_actors()), 'Unexpected user actors in room'
cube = unreal.load_asset('/Engine/BasicShapes/Cube')
assert cube


def box(name, center, size, visible=True):
    existing = [a for a in actors.get_all_level_actors() if a.get_actor_label() == name]
    assert len(existing) <= 1
    actor = existing[0] if existing else actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center))
    assert isinstance(actor, unreal.StaticMeshActor)
    actor.set_actor_location(unreal.Vector(*center), False, True)
    actor.set_actor_label(name)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_static_mesh(cube)
    component.set_material(0, material)
    component.set_collision_profile_name('BlockAll')
    component.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,
                                              unreal.CollisionResponseType.ECR_IGNORE)
    actor.set_actor_scale3d(unreal.Vector(*[v / 100. for v in size]))
    if not visible:
        actor.set_actor_hidden_in_game(True)
        component.set_editor_property('cast_shadow', False)
    return actor


box('GrayRoom_Floor', (0, 0, -10), (640, 640, 20))
box('GrayRoom_BackWall', (0, -310, 120), (640, 20, 240))
box('GrayRoom_LeftWall', (-310, 0, 120), (20, 600, 240))
box('GrayRoom_RightWall', (310, 0, 120), (20, 600, 240))
# Camera is south/+Y looking north. A visible full wall/roof would obstruct it.
# Separate pawn-blocking boundary pieces leave a 120cm doorway at the center.
box('GrayRoom_CameraSideBoundaryLeft', (-190, 310, 120), (260, 20, 240), False)
box('GrayRoom_CameraSideBoundaryRight', (190, 310, 120), (260, 20, 240), False)
for label, position, yaw in [
    ('GrayRoom_ArrivalAnchor', (0, 120, 88), -90),
    ('GrayRoom_ExitAlignAnchor', (0, 180, 88), 90),
    ('GrayRoom_ExitThreshold', (0, 310, 88), 90),
]:
    anchor = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*position),
                                          unreal.Rotator(pitch=0, yaw=yaw, roll=0))
    anchor.set_actor_label(label)
light = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(0, 0, 300))
light.set_actor_label('GrayRoom_LocalLight')
light.get_editor_property('light_component').set_mobility(unreal.ComponentMobility.MOVABLE)
light.get_editor_property('light_component').set_editor_property('intensity', 5000.)
light.get_editor_property('light_component').set_editor_property('attenuation_radius', 800.)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode', unreal.TownAgeGameMode)
assert levels.save_current_level()
assert unreal.EditorAssetLibrary.save_directory(FOLDER, False, True)
report = {'map': MAP, 'usable_floor_cm': [600, 600], 'roof': False,
          'camera_side_cutaway': True, 'player_start_added': False,
          'streaming_offset_planned_cm': [50000, 0, 0],
          'village_changed': False, 'linked_to_gameplay': False,
          'status': 'isolated_gray_room_created',
          'actors': [a.get_actor_label() for a in actors.get_all_level_actors()]}
(OUT / 'creation_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('GRAY_INTERIOR_CREATED', json.dumps(report))
