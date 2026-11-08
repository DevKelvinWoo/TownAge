"""Import the source dataset and author the cottage's interaction target."""
import json
import shutil
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Interaction'
OUT.mkdir(parents=True, exist_ok=True)
FOLDER = '/Game/Data/Interactions'
TABLE = FOLDER + '/DT_Interactions'
HOUSE = '/Game/Characters/Meshy/CozyHouse01/candidate_v002/BP_CozyHouse01_Split'

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level('/Game/Maps/L_VillageTerrain_01')
table = unreal.load_asset(TABLE)
if table is None:
    factory = unreal.DataTableFactory()
    factory.struct = unreal.load_object(None, '/Script/TownAge.TownAgeInteractionRow')
    assert factory.struct
    table = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'DT_Interactions', FOLDER, unreal.DataTable, factory)
assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(
    table, str(ROOT / 'Tools/Interaction/Interactions.csv'))
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)

backup = OUT / 'backups'
backup.mkdir(exist_ok=True)
for relative in [
    'Content/Characters/Meshy/CozyHouse01/candidate_v002/BP_CozyHouse01_Split.uasset',
    'Content/Maps/L_VillageTerrain_01.umap',
]:
    destination = backup / Path(relative).name
    if not destination.exists():
        shutil.copy2(ROOT / relative, destination)

bp = unreal.load_asset(HOUSE)
assert bp
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
target = None
for handle in handles:
    obj = library.get_object_for_blueprint(library.get_data(handle), bp)
    if isinstance(obj, unreal.TownAgeInteractionTargetComponent):
        assert target is None, 'House must have exactly one door target'
        target = obj
if target is None:
    handle, error = subsystem.add_new_subobject(unreal.AddNewSubobjectParams(
        parent_handle=handles[0], new_class=unreal.TownAgeInteractionTargetComponent,
        blueprint_context=bp))
    assert library.is_handle_valid(handle), str(error)
    assert subsystem.rename_subobject(handle, unreal.Text('DoorInteraction'))
    target = library.get_object_for_blueprint(library.get_data(handle), bp)
target.set_editor_property('definition', unreal.DataTableRowHandle(
    data_table=table, row_name='DoorInspect'))
target.set_editor_property('local_interaction_point', unreal.Vector(123, 155, 90))
target.set_editor_property('local_approach_direction', unreal.Vector(0, 1, 0))
target.set_editor_property('interaction_enabled', True)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
generated = unreal.EditorAssetLibrary.load_blueprint_class(HOUSE)
defaults = unreal.get_default_object(generated)
defaults.set_editor_property('replicates', True)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
assert levels.save_current_level()
report = {
    'data_table': table.get_path_name(), 'source_csv': 'Tools/Interaction/Interactions.csv',
    'house': HOUSE, 'target_component': 'DoorInteraction', 'row': 'DoorInspect',
    'local_point_cm': [123, 155, 90], 'outward_normal': [0, 1, 0],
    'house_replicates': defaults.get_editor_property('replicates'),
    'map': '/Game/Maps/L_VillageTerrain_01', 'door_animation_created': False,
}
(OUT / 'setup_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('INTERACTION_SETUP_COMPLETE', json.dumps(report))
