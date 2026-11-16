"""Rebuild continuous street surfaces and author map-local ground materials."""
import json
import math
import shutil
import runpy
from datetime import datetime
from pathlib import Path

import unreal
texture_functions = runpy.run_path(str(Path(__file__).with_name('generate_streetscape_textures.py')))
png, pixel = texture_functions['png'], texture_functions['pixel']

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/Surfaces'
MAP = '/Game/Maps/L_MainVillage_Art_01'
PREVIEW = '/Game/Maps/L_MainVillage_SurfaceReview_01'
FOLDER = '/Game/Environment/MainVillage/Look/Surfaces_v002'
OUT.mkdir(parents=True, exist_ok=True)
A = unreal.EditorAssetLibrary
E = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert LEVELS.load_level(MAP)
shutil.copy2(ROOT / 'Content/Maps/L_MainVillage_Art_01.umap',
             OUT / datetime.now().strftime('backup_%Y%m%d_%H%M%S.umap'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if unreal.SystemLibrary.parse_param(unreal.SystemLibrary.get_command_line(), 'VillageSurfacePreview'):
    if not A.does_asset_exist(PREVIEW):
        assert unreal.EditorLoadingAndSavingUtils.save_map(world, PREVIEW)
    assert LEVELS.load_level(PREVIEW)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.OBJ 0')


def import_file(path, name, options=None):
    destination = FOLDER + '/' + name
    if not A.does_asset_exist(destination):
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = FOLDER
        task.destination_name = name
        task.automated = True
        task.save = False
        if options:
            task.factory = unreal.FbxFactory()
            task.options = options
        TOOLS.import_asset_tasks([task])
    asset = A.load_asset(destination)
    assert asset, destination
    return asset


def texture(name, normal=False, period=200):
    sample = E.create_material_expression(material, unreal.MaterialExpressionTextureSample)
    sample.texture = name if isinstance(name, unreal.Texture) else A.load_asset(name)
    assert sample.texture
    sample.sampler_type = (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal
                           else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    pos = E.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
    uv = E.create_material_expression(material, unreal.MaterialExpressionDivide)
    uv.set_editor_property('const_b', float(period))
    assert E.connect_material_expressions(pos, 'XY', uv, 'A')
    assert E.connect_material_expressions(uv, '', sample, 'UVs')
    return sample


def scalar(value, prop):
    node = E.create_material_expression(material, unreal.MaterialExpressionConstant)
    node.r = value
    assert E.connect_material_property(node, '', prop)


size = 256
pixels = bytearray()
for y in range(size):
    for x in range(size):
        u, v = x * math.tau / size, y * math.tau / size
        broad = 8 * math.sin(2*u + v) + 6 * math.cos(u - 3*v) + 4 * math.sin(3*u + 4*v)
        detail = 3 * math.sin(39*u + 41*v) * math.cos(71*u - 27*v)
        pixels.extend(pixel(base + broad * strength + detail) for base, strength in
                      [(132, 1.35), (150, .88), (84, .67)])
png(OUT / 'Grass.png', size, pixels)
grass = import_file(OUT / 'Grass.png', 'T_Grass')
assert A.save_loaded_asset(grass, False)
P = unreal.MaterialProperty
surfaces = {}
for key, period in [('Grass', 1250), ('Asphalt', 260), ('Sidewalk', 200), ('Plaza', 200)]:
    name = 'M_' + key + '_Balanced'
    path = FOLDER + '/' + name
    material = A.load_asset(path) if A.does_asset_exist(path) else None
    if not material:
        material = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_property('used_with_instanced_static_meshes', True)
        atlas = '/Game/Environment/MainVillage/Streetscape/Textures/T_' + key
        sample = texture(grass if key == 'Grass' else atlas + '_BaseColor', period=period)
        base = sample
        output = 'RGB'
        if key == 'Grass':
            variation = texture(grass, period=3920)
            base = E.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate)
            base.set_editor_property('const_alpha', .62)
            assert E.connect_material_expressions(sample, 'RGB', base, 'A')
            assert E.connect_material_expressions(variation, 'RGB', base, 'B')
            output = ''
        tint = E.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        tint.constant = unreal.LinearColor(*{
            'Grass': (.69, .81, .84), 'Asphalt': (.52, .54, .61),
            'Sidewalk': (.88, .83, .81), 'Plaza': (.91, .85, .86),
        }[key], 1)
        multiply = E.create_material_expression(material, unreal.MaterialExpressionMultiply)
        assert E.connect_material_expressions(base, output, multiply, 'A')
        assert E.connect_material_expressions(tint, '', multiply, 'B')
        assert E.connect_material_property(multiply, '', P.MP_BASE_COLOR)
        if key in ('Sidewalk', 'Plaza'):
            # World XY samples require a world-aligned tangent frame on the flat pavement.
            material.set_editor_property('tangent_space_normal', False)
            normal = texture(atlas + '_Normal', normal=True)
            assert E.connect_material_property(normal, 'RGB', P.MP_NORMAL)
        scalar(.89, P.MP_ROUGHNESS)
        scalar(.20, P.MP_SPECULAR)
        E.layout_material_expressions(material)
        E.recompile_material(material)
        assert A.save_loaded_asset(material, False)
    surfaces[key] = material


def ribbon(points, offsets):
    """Every strip uses the same miter vectors, so adjacent edges coincide."""
    directions = []
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        directions.append((-dy/length, dx/length))
    vertices = []
    for i, (x, y, z) in enumerate(points):
        a = directions[max(0, i-1)]
        b = directions[min(i, len(directions)-1)]
        denominator = 1 + a[0]*b[0] + a[1]*b[1]
        nx, ny = (a[0]+b[0])/denominator, (a[1]+b[1])/denominator
        vertices.extend((x+nx*offset, y+ny*offset, z) for offset in offsets)
    return vertices


def street_mesh(name, vertices, key):
    path = OUT / (name + '.obj')
    lines = ['o ' + name]
    # The legacy OBJ importer reflects Y and preserves Z.
    lines.extend(f'v {x:.5f} {-y:.5f} {z:.5f}' for x, y, z in vertices)
    lines.append('vn 0 0 1')
    for i in range(1, len(vertices)-2, 2):
        lines.extend([f'f {i}//1 {i+1}//1 {i+2}//1', f'f {i+1}//1 {i+3}//1 {i+2}//1'])
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.auto_generate_collision = False
    mesh = import_file(path, 'SM_' + name, options)
    body = mesh.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_material(0, surfaces[key])
    assert A.save_loaded_asset(mesh, False)
    existing = next((a for a in ACTORS.get_all_level_actors() if a.get_actor_label() == name), None)
    actor = existing or ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
    actor.set_actor_label(name)
    actor.set_folder_path('MainVillage/Streetscape/Continuous')
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_collision_profile_name('BlockAll')
    actor.static_mesh_component.set_cast_shadow(False)
    center, extent = actor.get_actor_bounds(False)
    for axis in range(3):
        coords = [v[axis] for v in vertices]
        assert abs(getattr(center, 'xyz'[axis]) - (min(coords)+max(coords))/2) < 1, (name, center, extent)
    return actor


actors = ACTORS.get_all_level_actors()
plan = next(a for a in actors if a.get_actor_label() == 'MainVillage_Blockout')
layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
branch = [(2050, 430, 11.4), (2100, 180, 11.4), (2160, -260, 11.4),
          (2200, -800, 11.4), (2170, -1150, 11.4), (2100, -1500, 11.4), (1950, -1750, 11.4)]
street_mesh('Village_BranchAsphalt', ribbon(branch, (-200, 200)), 'Asphalt')
# With the branch traveling toward -Y, positive offsets point east.
walk = [(x, y, 12.0) for x, y, _ in branch]
street_mesh('Village_BranchWestPavers', ribbon(walk, (-365, -197))[2:], 'Sidewalk')
street_mesh('Village_BranchEastPavers', ribbon(walk, (197, 350))[2:], 'Sidewalk')
# Cover the 0.6cm height transition and give both pavement edges an intentional lip.
for key, offset in [('West', -200), ('East', 200)]:
    curb = [(x, y, 15.) for x, y, _ in branch]
    street_mesh('Village_Branch' + key + 'Edge', ribbon(curb, (offset-8, offset+8))[4:], 'Plaza')
layout['elements'] = [item for item in layout['elements'] if item['label'] not in {
    'Village curved side street', 'Village side street west sidewalk', 'Village side street east sidewalk'}]
for item in layout['types']:
    if item['typeId'] in surfaces:
        item['material'] = surfaces[item['typeId']].get_path_name()
unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(layout))
assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))['elements'] == layout['elements']
for actor in actors:
    if isinstance(actor, unreal.Landscape):
        actor.set_editor_property('landscape_material', surfaces['Grass'])
    if actor.get_actor_label() == 'Village_Lamp_05':
        loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(2430, loc.y, loc.z), False, True)
    if actor.get_actor_label() == 'Village_WarmIllustratedGrade':
        settings = actor.get_editor_property('settings')
        settings.set_editor_property('ambient_occlusion_intensity', .35)
        actor.set_editor_property('settings', settings)
assert LEVELS.save_current_level()
print('VILLAGE_SURFACES_SAVED')
