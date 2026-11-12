"""Add the wardrobe mockup to the existing interior with Unreal Editor Python."""

from datetime import datetime
from pathlib import Path
import shutil

import unreal

ROOT = Path(__file__).resolve().parents[2]
ROOM = '/Game/Maps/Interiors/L_CozyHouse01_Gray'
TABLE = '/Game/Data/Interactions/DT_Interactions'
FOLDER = '/Game/Environment/Interiors/CozyHouse01_Gray'
BLUEPRINT = FOLDER + '/BP_GrayWardrobe'
LABEL = 'GrayRoom_Wardrobe'

backup = ROOT / 'Saved/Wardrobe' / datetime.now().strftime('backup_%Y%m%d_%H%M%S_%f')
backup.mkdir(parents=True)
for asset in (ROOM, TABLE, BLUEPRINT):
    path = ROOT / asset.replace('/Game/', 'Content/', 1)
    path = path.with_suffix('.umap' if asset == ROOM else '.uasset')
    if path.exists():
        shutil.copy2(path, backup / path.name)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level(ROOM)
table = unreal.load_asset(TABLE)
cube = unreal.load_asset('/Engine/BasicShapes/Cube')
gray = unreal.load_asset(FOLDER + '/M_GrayRoom')
assert table and cube and gray
assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(
    table, str(ROOT / 'Tools/Interaction/Interactions.csv'))
assert unreal.DataTableFunctionLibrary.does_data_table_row_exist(table, 'WardrobeUse')

bp = unreal.load_asset(BLUEPRINT)
if bp is None:
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.Actor)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'BP_GrayWardrobe', FOLDER, unreal.Blueprint, factory)
assert bp
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary

def component(cls, name):
    handles = subobjects.k2_gather_subobject_data_for_blueprint(bp)
    for handle in handles:
        obj = lib.get_object_for_blueprint(lib.get_data(handle), bp)
        if obj and obj.get_name().removesuffix('_GEN_VARIABLE') == name:
            return obj
    handle, error = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=handles[0], new_class=cls, blueprint_context=bp))
    assert lib.is_handle_valid(handle), str(error)
    assert subobjects.rename_subobject(handle, unreal.Text(name))
    return lib.get_object_for_blueprint(lib.get_data(handle), bp)

mesh = component(unreal.StaticMeshComponent, 'WardrobeCube')
mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
mesh.set_static_mesh(cube)
mesh.set_material(0, gray)
mesh.set_editor_property('relative_location', unreal.Vector(0, 0, 105))
mesh.set_editor_property('relative_scale3d', unreal.Vector(1.35, .65, 2.10))
mesh.set_collision_profile_name('BlockAll')
mesh.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA,
                                       unreal.CollisionResponseType.ECR_IGNORE)
mesh.set_lighting_channels(False, True, False)
mesh.set_editor_property('cast_shadow', False)
target = component(unreal.TownAgeInteractionTargetComponent, 'WardrobeInteraction')
target.set_editor_property('definition', unreal.DataTableRowHandle(data_table=table, row_name='WardrobeUse'))
target.set_editor_property('local_interaction_point', unreal.Vector(0, 42, 95))
target.set_editor_property('local_approach_direction', unreal.Vector(0, 1, 0))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
cls = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
assert cls
unreal.get_default_object(cls).set_editor_property('replicates', True)

matches = [actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == LABEL]
assert len(matches) <= 1
location = unreal.Vector(310, -780, 0)
wardrobe = matches[0] if matches else actors.spawn_actor_from_class(cls, location)
assert wardrobe.get_component_by_class(unreal.TownAgeInteractionTargetComponent)
wardrobe.set_actor_label(LABEL)
wardrobe.set_actor_location(location, False, True)
wardrobe.set_replicates(True)
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
assert levels.save_current_level()
print('WARDROBE_PLACED', wardrobe.get_path_name(), location)
