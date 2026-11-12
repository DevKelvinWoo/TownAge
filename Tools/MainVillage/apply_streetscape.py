"""Apply approved streetscape materials and reusable curb modules to the village review map."""

import hashlib
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/Streetscape'
MAP = '/Game/Maps/L_MainVillage_Blockout_01'
FOLDER = '/Game/Environment/MainVillage/Streetscape'
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REFRESH_TEXTURES = unreal.SystemLibrary.parse_param(
    unreal.SystemLibrary.get_command_line(), 'MainVillageRefreshStreetTextures')
assert LEVELS.load_level(MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith(MAP + '.')
review = ROOT / 'Content/Maps/L_MainVillage_Blockout_01.umap'
original = ROOT / 'Content/Maps/L_VillageTerrain_01.umap'
source_hash = hashlib.sha256(original.read_bytes()).hexdigest()
backup = OUT / datetime.now().strftime('backup_%Y%m%d_%H%M%S_%f')
backup.mkdir(parents=True)
shutil.copy2(review, backup / review.name)
plans = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.TownAgeMapLayout)
         and a.get_actor_label() == 'MainVillage_Blockout']
assert len(plans) == 1
plan = plans[0]
layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
before_elements = layout['elements']
(backup / 'layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')


def asset_at(folder, name):
    path = f'{FOLDER}/{folder}/{name}'
    return ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None


def texture(name, is_normal=False):
    existing = asset_at('Textures', name)
    if existing and not REFRESH_TEXTURES:
        return existing
    if existing:
        original_texture = ROOT / 'Content/Environment/MainVillage/Streetscape/Textures' / (name + '.uasset')
        shutil.copy2(original_texture, backup / original_texture.name)
    path = OUT / 'Textures' / (name + '.png')
    assert path.is_file(), path
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = FOLDER + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = existing is not None
    task.save = False
    TOOLS.import_asset_tasks([task])
    asset = asset_at('Textures', name)
    assert isinstance(asset, unreal.Texture2D)
    asset.set_editor_property('srgb', not is_normal)
    if is_normal:
        asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
    assert ASSETS.save_loaded_asset(asset, False)
    return asset


textures = {name: texture('T_' + name, name.endswith('_Normal')) for name in (
    'Asphalt_BaseColor', 'Sidewalk_BaseColor', 'Sidewalk_Normal', 'Plaza_BaseColor', 'Plaza_Normal')}


def material(name, roughness, *, color=None, period=200., normal=False):
    existing = asset_at('Materials', 'M_' + name)
    if existing:
        return existing
    asset = TOOLS.create_asset('M_' + name, FOLDER + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    assert asset
    asset.set_editor_property('used_with_instanced_static_meshes', True)

    def node(cls):
        return EDIT.create_material_expression(asset, cls)

    if color:
        tint = node(unreal.MaterialExpressionConstant3Vector)
        tint.constant = unreal.LinearColor(*color, 1.)
        assert EDIT.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        position = node(unreal.MaterialExpressionWorldPosition)
        scale = node(unreal.MaterialExpressionDivide)
        scale.set_editor_property('const_b', period)
        assert EDIT.connect_material_expressions(position, 'XY', scale, 'A')
        for suffix, prop in [('BaseColor', unreal.MaterialProperty.MP_BASE_COLOR)] + (
                [('Normal', unreal.MaterialProperty.MP_NORMAL)] if normal else []):
            sample = node(unreal.MaterialExpressionTextureSample)
            sample.set_editor_property('texture', textures[f'{name}_{suffix}'])
            sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
                                       if suffix == 'Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
            assert EDIT.connect_material_expressions(scale, '', sample, 'UVs')
            assert EDIT.connect_material_property(sample, 'RGB', prop)
    for amount, prop in [(roughness, unreal.MaterialProperty.MP_ROUGHNESS),
                         (.18, unreal.MaterialProperty.MP_SPECULAR)]:
        value = node(unreal.MaterialExpressionConstant)
        value.r = amount
        assert EDIT.connect_material_property(value, '', prop)
    EDIT.layout_material_expressions(asset)
    EDIT.recompile_material(asset)
    assert ASSETS.save_loaded_asset(asset, False)
    return asset


materials = {
    'Asphalt': material('Asphalt', .94, period=260.),
    'Sidewalk': material('Sidewalk', .87, normal=True),
    'Plaza': material('Plaza', .87, normal=True),
}
stone = material('Curb', .87, color=(.75, .62, .48))
paint = material('Markings', .88, color=(.89, .82, .69))
swapped = set()
for row in layout['types']:
    key = row['typeId']
    if key in materials:
        row['material'] = materials[key].get_path_name()
        swapped.add(key)
assert swapped == set(materials)
result = unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(layout))
assert plan.get_editor_property('elements'), result
after = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
assert before_elements == after['elements']
assert {t['typeId']: t['material'] for t in after['types'] if t['typeId'] in swapped} == {
    key: asset.get_path_name() for key, asset in materials.items()}


def curb_mesh(name, taper):
    existing = asset_at('Meshes', name)
    if existing:
        return existing
    vertices = []
    triangles = []
    uvs = []

    def face(points):
        start = len(vertices)
        vertices.extend(unreal.Vector(*p) for p in points)
        spans = [max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)]
        u, v = sorted(range(3), key=lambda i: spans[i], reverse=True)[:2]
        uvs.extend(unreal.Vector2D(p[u] / 100., p[v] / 100.) for p in points)
        triangles.extend(unreal.IntVector(start, start + j + 1, start + j) for j in range(1, len(points) - 1))

    profile = [(-8, 0), (8, 0), (8, 7), (6, 9), (-6, 9), (-8, 7)]
    rings = [[(x, y, z * (0.08 if taper and x > 50 else 1.)) for y, z in profile] for x in (.4, 99.6)]
    face(list(reversed(rings[0])))
    face(rings[1])
    for i in range(len(profile)):
        j = (i + 1) % len(profile)
        face([rings[0][i], rings[0][j], rings[1][j], rings[1][i]])
    mesh = unreal.new_object(unreal.DynamicMesh)
    buffers = unreal.GeometryScriptSimpleMeshBuffers(vertices=vertices, triangles=triangles, uv0=uvs)
    unreal.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh, buffers)
    options = unreal.GeometryScriptCreateNewStaticMeshAssetOptions(
        enable_recompute_normals=True, enable_recompute_tangents=True, enable_collision=False)
    asset, outcome = unreal.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        mesh, f'{FOLDER}/Meshes/{name}', options)
    assert isinstance(asset, unreal.StaticMesh), outcome
    asset.set_material(0, stone)
    assert ASSETS.save_loaded_asset(asset, False)
    return asset


def instance_class():
    name = 'BP_StreetscapeCurbStrip'
    folder = 'Placement'
    existing = asset_at(folder, name)
    if not existing:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        bp = TOOLS.create_asset(name, FOLDER + '/' + folder, unreal.Blueprint, factory)
        subs = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = subs.k2_gather_subobject_data_for_blueprint(bp)
        handle, error = subs.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=handles[0], new_class=unreal.InstancedStaticMeshComponent, blueprint_context=bp))
        assert lib.is_handle_valid(handle), str(error)
        assert subs.rename_subobject(handle, unreal.Text('CurbInstances'))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert ASSETS.save_loaded_asset(bp, False)
    return ASSETS.load_blueprint_class(f'{FOLDER}/{folder}/{name}')


street = next(e for e in after['elements'] if e['label'] == 'Main street')
points = [(p['x'], p['y'], p['z'] + 8.) for p in street['points']]
half = street['widthCm'] / 2.
markings = [a for a in ACTORS.get_all_level_actors()
            if str(a.get_folder_path()) == 'MainVillage/Blockout/Road markings']
stripes = [a for a in markings if a.get_actor_label().startswith('Crossing stripe ')]
assert len(stripes) >= 2 and abs(points[-2][1] - points[-1][1]) < .1
for a in markings:
    a.static_mesh_component.set_material(0, paint)

start = min(a.get_actor_location().x - a.get_actor_scale3d().x * 50 for a in stripes) - 14.
end = max(a.get_actor_location().x + a.get_actor_scale3d().x * 50 for a in stripes) + 14.
assert points[-2][0] < start - 65 < end + 65 < points[-1][0]

unit_normals = []
for a, b in zip(points, points[1:]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    unit_normals.append((-dy / length, dx / length))


def curb_edge(side):
    result = []
    for i, (x, y, z) in enumerate(points):
        a = unit_normals[max(0, i - 1)]
        b = unit_normals[min(i, len(unit_normals) - 1)]
        denominator = 1. + a[0] * b[0] + a[1] * b[1]
        result.append((x + side * half * (a[0] + b[0]) / denominator,
                       y + side * half * (a[1] + b[1]) / denominator, z))
    return result


def segments(a, b, max_length):
    count = max(1, math.ceil(math.dist(a, b) / max_length))
    cuts = [tuple(x + (y - x) * j / count for x, y in zip(a, b)) for j in range(count + 1)]
    return list(zip(cuts, cuts[1:]))


straight, tapered = [], []
for side in (-1, 1):
    edge = curb_edge(side)
    for a, b in zip(edge[:-2], edge[1:-1]):
        straight.extend(segments(a, b, 105.))
    y = edge[-1][1]
    z = edge[-1][2]
    straight.extend(segments(edge[-2], (start - 65, y, z), 105.))
    straight.extend(segments((end + 65, y, z), edge[-1], 105.))
    tapered.extend([((start - 65, y, z), (start, y, z)),
                    ((end + 65, y, z), (end, y, z))])

cls = instance_class()
existing = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()
            if str(a.get_folder_path()) == 'MainVillage/Streetscape'}
counts = {}
for label, asset, transforms in [
    ('Street_Curb_Stone', curb_mesh('SM_CurbStone', False), straight),
    ('Street_Curb_Tapers', curb_mesh('SM_CurbTaper', True), tapered),
]:
    actor = existing.get(label) or ACTORS.spawn_actor_from_class(cls, unreal.Vector())
    assert actor.get_class() == cls
    actor.set_actor_label(label)
    actor.set_folder_path('MainVillage/Streetscape')
    component = actor.get_component_by_class(unreal.InstancedStaticMeshComponent)
    component.set_static_mesh(asset)
    component.set_material(0, stone)
    component.set_cast_shadow(False)
    component.set_collision_profile_name('NoCollision')
    component.clear_instances()
    for a, b in transforms:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        rotation = unreal.Rotator(pitch=0, yaw=math.degrees(math.atan2(dy, dx)), roll=0)
        transform = unreal.Transform(location=unreal.Vector(*a), rotation=rotation,
                                     scale=unreal.Vector(length / 100., 1., 1.))
        component.add_instance(transform, world_space=True)
    counts[label] = component.get_instance_count()
    assert counts[label] == len(transforms)

assert LEVELS.save_current_level()
assert hashlib.sha256(original.read_bytes()).hexdigest() == source_hash
report = {'map': MAP, 'asset_folder': FOLDER, 'backup': str(backup),
          'materials': {k: a.get_path_name() for k, a in materials.items()},
          'curb_instances': counts, 'crossing_opening_cm': [start, end],
          'route_geometry_preserved': True, 'source_map_sha256': source_hash}
(OUT / 'application.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MAIN_VILLAGE_STREETSCAPE_APPLIED', json.dumps(report))
