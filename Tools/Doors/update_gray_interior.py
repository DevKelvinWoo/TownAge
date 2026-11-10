"""Expand the existing room in place, preserving its door and streaming anchors.

Run with Unreal Python after setup_door_travel.py. Only explicitly named room
fixtures are changed; dated backups preserve the local map/table/vanity BP.
"""
import datetime
import json
import shutil
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
ROOM = '/Game/Maps/Interiors/L_CozyHouse01_Gray'
FOLDER = '/Game/Environment/Interiors/CozyHouse01_Gray'
TABLE = '/Game/Data/Interactions/DT_Interactions'
OUT = ROOT / 'Saved/Doors/InteriorUpdate'
BACKUP = OUT / datetime.datetime.now().strftime('backup_%Y%m%d_%H%M%S')
BACKUP.mkdir(parents=True, exist_ok=True)
for relative in ['Content/Maps/Interiors/L_CozyHouse01_Gray.umap',
                 'Content/Data/Interactions/DT_Interactions.uasset',
                 'Content/Environment/Interiors/CozyHouse01_Gray/BP_GrayVanity.uasset']:
    source = ROOT / relative
    if source.exists():
        shutil.copy2(source, BACKUP / source.name)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level(ROOM)
tools = unreal.AssetToolsHelpers.get_asset_tools()
cube = unreal.load_asset('/Engine/BasicShapes/Cube')
gray = unreal.load_asset(FOLDER + '/M_GrayRoom')
assert cube and gray


def material(name, color, unlit=False):
    asset = unreal.load_asset(FOLDER + '/' + name)
    if asset:
        return asset
    asset = tools.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    if unlit:
        asset.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    node = unreal.MaterialEditingLibrary.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
    node.set_editor_property('constant', unreal.LinearColor(*color, 1))
    assert unreal.MaterialEditingLibrary.connect_material_property(
        node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR if unlit else unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.recompile_material(asset)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    return asset


black = material('M_InteriorVoid', (0., 0., 0.), True)
mirror = material('M_VanityMirrorPlaceholder', (.42, .46, .48), True)


def find(label):
    matches = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
    assert len(matches) <= 1, label
    return matches[0] if matches else None


def box(label, center, size, visible=True, mat=None, collision=True):
    actor = find(label) or actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center))
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    actor.set_actor_location(unreal.Vector(*center), False, True)
    actor.set_actor_scale3d(unreal.Vector(*[v / 100. for v in size]))
    actor.set_actor_label(label)
    component.set_static_mesh(cube)
    component.set_material(0, mat or gray)
    component.set_lighting_channels(False, True, False)
    component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    component.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,
                                              unreal.CollisionResponseType.ECR_IGNORE)
    component.set_editor_property('cast_shadow', False)
    actor.set_actor_hidden_in_game(not visible)
    return actor


# Grow away from the existing entrance, keeping all exit/arrival transforms intact.
box('GrayRoom_Floor', (0, -300, -10), (1240, 1240, 20))
box('GrayRoom_BackWall', (0, -910, 150), (1240, 20, 300))
box('GrayRoom_LeftWall', (-610, -300, 150), (20, 1200, 300))
box('GrayRoom_RightWall', (610, -300, 150), (20, 1200, 300))
box('GrayRoom_CameraSideBoundaryLeft', (-335, 310, 150), (550, 20, 300), False)
box('GrayRoom_CameraSideBoundaryRight', (335, 310, 150), (550, 20, 300), False)
box('GrayRoom_BlackSurround', (0, -300, -35), (40000, 40000, 20), mat=black, collision=False)

# At most two overlapping shadowless lights: no directional sun in this channel.
for label, center in [('GrayRoom_LocalLight', (0, -50, 330)),
                      ('GrayRoom_BackFill', (0, -650, 330))]:
    light = find(label) or actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*center))
    light.set_actor_label(label)
    component = light.get_editor_property('light_component')
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_actor_location(unreal.Vector(*center), False, True)
    component.set_editor_property('intensity', 3500.)
    component.set_editor_property('attenuation_radius', 1100.)
    component.set_editor_property('source_radius', 160.)
    component.set_editor_property('cast_shadows', False)
    component.set_lighting_channels(False, True, False)

table = unreal.load_asset(TABLE)
assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(
    table, str(ROOT / 'Tools/Interaction/Interactions.csv'))
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)

# A replicated BP keeps the target's stable component identity valid in RPCs.
path = FOLDER + '/BP_GrayVanity'
bp = unreal.load_asset(path)
if bp is None:
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    bp = tools.create_asset('BP_GrayVanity', FOLDER, unreal.Blueprint, factory)
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary


def components():
    return {lib.get_object_for_blueprint(lib.get_data(h), bp).get_name().removesuffix('_GEN_VARIABLE'):
            (h, lib.get_object_for_blueprint(lib.get_data(h), bp))
            for h in subobjects.k2_gather_subobject_data_for_blueprint(bp)}


root = subobjects.k2_gather_subobject_data_for_blueprint(bp)[0]


def add(cls, name):
    current = components()
    if name in current:
        return current[name][1]
    handle, error = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=root, new_class=cls, blueprint_context=bp))
    assert lib.is_handle_valid(handle), str(error)
    assert subobjects.rename_subobject(handle, unreal.Text(name))
    return lib.get_object_for_blueprint(lib.get_data(handle), bp)


for name, center, size, mat in [
    ('TableTop', (0, 0, 78), (150, 55, 10), gray),
    ('LeftDrawers', (-53, 0, 37), (38, 49, 70), gray),
    ('RightDrawers', (53, 0, 37), (38, 49, 70), gray),
    ('MirrorFrame', (0, -24, 132), (104, 10, 96), gray),
    ('MirrorInset', (0, -17, 133), (88, 3, 78), mirror),
]:
    part = add(unreal.StaticMeshComponent, name)
    part.set_mobility(unreal.ComponentMobility.MOVABLE)
    part.set_static_mesh(cube)
    part.set_material(0, mat)
    part.set_editor_property('relative_location', unreal.Vector(*center))
    part.set_editor_property('relative_scale3d', unreal.Vector(*[v / 100. for v in size]))
    part.set_collision_profile_name('BlockAll')
    part.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,
                                          unreal.CollisionResponseType.ECR_IGNORE)
    part.set_lighting_channels(False, True, False)
    part.set_editor_property('cast_shadow', False)
target = add(unreal.TownAgeInteractionTargetComponent, 'VanityInteraction')
target.set_editor_property('definition', unreal.DataTableRowHandle(data_table=table, row_name='VanityUse'))
target.set_editor_property('local_interaction_point', unreal.Vector(0, 35, 95))
target.set_editor_property('local_approach_direction', unreal.Vector(0, 1, 0))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
defaults = unreal.get_default_object(cls)
defaults.set_editor_property('replicates', True)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
vanity = find('GrayRoom_Vanity') or actors.spawn_actor_from_class(cls, unreal.Vector(-310, -780, 0))
vanity.set_actor_label('GrayRoom_Vanity')
vanity.set_actor_location(unreal.Vector(-310, -780, 0), False, True)
vanity.set_replicates(True)
assert vanity.get_component_by_class(unreal.TownAgeInteractionTargetComponent)

# The authored interior door also uses the indoor channel.
door = find('CozyHouse01_InteriorDoor')
assert door, 'Integrated exit must already exist'
for component in door.get_components_by_class(unreal.StaticMeshComponent):
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_lighting_channels(False, True, False)
    component.set_editor_property('cast_shadow', False)

assert levels.save_current_level()
report = {'room': ROOM, 'usable_floor_cm': [1200, 1200], 'floor_area_ratio': 4,
          'door_anchors_preserved': True, 'lighting_channel': 1,
          'shadow_casting_local_lights': 0, 'black_surround': True,
          'vanity_actor': vanity.get_path_name(), 'vanity_action': 'LogOnly',
          'interaction_event': 'Vanity.Use', 'input_path': 'existing_G_and_touch_USE',
          'backup': str(BACKUP), 'physical_mobile_verified': False}
(OUT / 'setup_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('GRAY_INTERIOR_UPDATED', json.dumps(report))
