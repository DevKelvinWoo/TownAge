"""Build a walkable main-village blockout on a copy of Village01."""

import hashlib
import json
import uuid
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage'
SOURCE = '/Game/Maps/L_VillageTerrain_01'
MAP = '/Game/Maps/L_MainVillage_Blockout_01'
FOLDER = '/Game/Environment/MainVillage/Blockout'
ASSETS = unreal.EditorAssetLibrary
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
OUT.mkdir(parents=True, exist_ok=True)
source_file = ROOT / 'Content/Maps/L_VillageTerrain_01.umap'
before = hashlib.sha256(source_file.read_bytes()).hexdigest()
refresh = unreal.SystemLibrary.parse_param(unreal.SystemLibrary.get_command_line(), 'MainVillageRefresh')

if ASSETS.does_asset_exist(MAP):
    if refresh:
        assert (OUT / 'placement.json').exists()
    else:
        assert unreal.SystemLibrary.parse_param(unreal.SystemLibrary.get_command_line(), 'MainVillageResume')
        assert not (OUT / 'placement.json').exists(), 'The review map was already completed'
else:
    assert LEVELS.load_level(SOURCE)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, MAP)
assert LEVELS.load_level(MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith(MAP + '.')
authored = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()
            if str(a.get_folder_path()).startswith('MainVillage/Blockout')}
assert ('MainVillage_Blockout' in authored) == refresh


def material(name, color, paving=False):
    path = FOLDER + '/M_' + name
    asset = ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if asset:
        if not asset.get_editor_property('used_with_instanced_static_meshes'):
            asset.set_editor_property('used_with_instanced_static_meshes', True)
            EDIT.recompile_material(asset)
            assert ASSETS.save_loaded_asset(asset, False)
        return asset
    asset = TOOLS.create_asset('M_' + name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    asset.set_editor_property('used_with_instanced_static_meshes', True)
    tint = EDIT.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector, -450, 0)
    tint.constant = unreal.LinearColor(*color, 1)
    color_source = tint
    color_output = ''
    if paving:
        position = EDIT.create_material_expression(asset, unreal.MaterialExpressionWorldPosition, -780, 190)
        scale = EDIT.create_material_expression(asset, unreal.MaterialExpressionDivide, -450, 190)
        scale.set_editor_property('const_b', 2400. if name == 'Lawn' else 400.)
        assert EDIT.connect_material_expressions(position, 'XY', scale, 'A')
        sample = EDIT.create_material_expression(asset, unreal.MaterialExpressionTextureSample, -240, 180)
        texture_name = 'T_GrassVariation' if name == 'Lawn' else 'T_PavingTiles'
        texture = ASSETS.load_asset('/Game/Terrain/Village01/' + texture_name)
        assert texture
        sample.set_editor_property('texture', texture)
        sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        assert EDIT.connect_material_expressions(scale, '', sample, 'UVs')
        color_source = EDIT.create_material_expression(asset, unreal.MaterialExpressionMultiply, 0, 0)
        assert EDIT.connect_material_expressions(tint, '', color_source, 'A')
        assert EDIT.connect_material_expressions(sample, 'RGB', color_source, 'B')
    assert EDIT.connect_material_property(color_source, color_output, unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = EDIT.create_material_expression(asset, unreal.MaterialExpressionConstant, 0, 180)
    roughness.r = .88
    assert EDIT.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    EDIT.recompile_material(asset)
    assert ASSETS.save_loaded_asset(asset, False)
    return asset


plan = authored.get('MainVillage_Blockout') or ACTORS.spawn_actor_from_class(unreal.TownAgeMapLayout, unreal.Vector())
plan.set_actor_label('MainVillage_Blockout')
plan.set_folder_path('MainVillage/Blockout')
snapshot = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
snapshot['types'] = []
snapshot['elements'] = []


def palette(key, kind, color, paving=False):
    asset = material(key, color, paving)
    snapshot['types'].append({'typeId': key, 'kind': kind, 'displayName': key,
                              'mesh': 'None', 'material': asset.get_path_name(),
                              'previewColor': dict(zip('rgba', (*color, 1))),
                              'defaultHeightCm': 300})


def element(kind, key, name, points, width=400, height=300):
    snapshot['elements'].append({
        'id': uuid.uuid5(uuid.NAMESPACE_URL, 'townage:main-village:' + name).hex,
        'kind': kind, 'typeId': key, 'label': name,
        'points': [dict(zip('xyz', p)) for p in points], 'widthCm': width, 'heightCm': height})


def rectangle(key, label, left, back, right, front, z, height=None):
    element('Building' if height else 'Field', key, label, [(left, back, z), (right, front, z)],
            height=height or 300)


for args in [
    ('Asphalt', 'Road', (.125, .12, .11)),
    ('Sidewalk', 'Road', (.92, .84, .71), True),
    ('Plaza', 'Field', (.94, .88, .76), True),
    ('Lawn', 'Field', (.7, .88, .59), True),
    ('Garden', 'Field', (.19, .105, .045)),
    ('Market', 'Building', (.39, .61, .45)),
    ('Salon', 'Building', (.71, .33, .38)),
    ('Homes', 'Building', (.64, .51, .34)),
]:
    palette(*args)

element('Road', 'Asphalt', 'Main street',
        [(-1200, 310, 1), (350, 550, 1), (1800, 600, 1), (4950, 600, 1)], 560)
element('Road', 'Sidewalk', 'Plaza-side sidewalk',
        [(-1160, -90, 0), (410, 150, 0), (1810, 190, 0), (4950, 190, 0)], 270)
element('Road', 'Sidewalk', 'Far sidewalk',
        [(-1250, 710, 0), (290, 950, 0), (1790, 1000, 0), (4950, 1000, 0)], 270)
rectangle('Plaza', 'Market square', 3180, -1320, 4950, 328, 2)
rectangle('Plaza', 'Player entrance path', 2810, -925, 3030, 190, 2)
rectangle('Lawn', 'Starter front lawn west', 2450, -825, 2810, -350, 0)
rectangle('Lawn', 'Starter front lawn east', 3030, -825, 3180, -350, 0)
for index, x in enumerate((2520, 2650, 3050)):
    rectangle('Garden', 'Starter raised-bed footprint ' + str(index + 1), x, -680, x + 115, -480, 1)
rectangle('Market', 'Market shell', 3370, -1450, 4080, -925, 0, 420)
rectangle('Salon', 'Salon shell', 4340, -1160, 4830, -720, 0, 350)
rectangle('Homes', 'NPC house A', 1150, -1000, 1690, -500, 0, 360)
rectangle('Homes', 'NPC house B', 150, -875, 680, -420, 0, 380)
for name, x, low in [('NPC A', 1420, -510), ('NPC B', 415, -430)]:
    rectangle('Plaza', name + ' front path', x - 95, low, x + 95, 158, 2)
rectangle('Garden', 'NPC A front garden', 1510, -435, 1740, -200, 1)
rectangle('Garden', 'NPC B front garden', 180, -360, 303, -145, 1)
rectangle('Lawn', 'NPC A front lawn', 1515, -490, 1760, -165, 0)
rectangle('Lawn', 'NPC B front lawn', 145, -410, 320, -120, 0)
result = unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(snapshot))
count = unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan)
assert count >= len(snapshot['elements']), (result, count)

# Reuse the current PlayerStart and the complete cottage/door setup from the copied map.
starts = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
assert len(starts) == 1, len(starts)
starts[0].set_actor_location(unreal.Vector(3260, 1010, 104), False, True)
starts[0].set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)

cube = ASSETS.load_asset('/Engine/BasicShapes/Cube')
paint = material('Paint', (.72, .66, .52))


def mark(label, x, y, width, length):
    actor = authored.get(label) or ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, 9.1))
    actor.set_actor_label(label)
    actor.set_folder_path('MainVillage/Blockout/Road markings')
    actor.set_actor_scale3d(unreal.Vector(width / 100, length / 100, .004))
    actor.static_mesh_component.set_static_mesh(cube)
    actor.static_mesh_component.set_material(0, paint)
    actor.static_mesh_component.set_cast_shadow(False)
    actor.static_mesh_component.set_collision_profile_name('NoCollision')


for index in range(6):
    mark(f'Crossing stripe {index + 1}', 3088 + index * 72, 600, 36, 510)
for x in (350, 875, 1400, 1925, 2450, 3700, 4225, 4750):
    y = 600 if x >= 1800 else 550 + (x - 350) * 50 / 1450
    mark(f'Lane marking {x}', x, y, 210, 16)

entry_material = material('EntryTrim', (.23, .11, .06))
for name, x, y in [('Market', 3720, -913), ('Salon', 4585, -708),
                   ('NPC_A', 1420, -488), ('NPC_B', 415, -408)]:
    marker = authored.get('Entrance_' + name) or ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, 112))
    marker.set_actor_label('Entrance_' + name)
    marker.set_folder_path('MainVillage/Blockout/Entrances')
    marker.set_actor_scale3d(unreal.Vector(1.12, .12, 2.2))
    marker.static_mesh_component.set_static_mesh(cube)
    marker.static_mesh_component.set_material(0, entry_material)
    marker.static_mesh_component.set_collision_profile_name('NoCollision')

assert LEVELS.save_current_level()
assert hashlib.sha256(source_file.read_bytes()).hexdigest() == before
(OUT / 'layout.json').write_text(unreal.TownAgeMapEditorLibrary.export_json(plan), encoding='utf-8')
report = {'map': MAP, 'source': SOURCE, 'source_sha256': before, 'layout_instances': count,
          'road_width_cm': 560, 'sidewalk_width_cm': 270, 'placeholder_buildings': 4}
(OUT / 'placement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MAIN_VILLAGE_BLOCKOUT_PLACED', json.dumps(report))
