"""Rebuild continuous street surfaces and author map-local ground materials."""
import json
import math
import random
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
PREVIEW = '/Game/Maps/L_MainVillage_SurfaceReview_02'
FOLDER = '/Game/Environment/MainVillage/Look/Surfaces_v004'
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
for key, period in [('Grass', 1250), ('Asphalt', 260), ('Sidewalk', 200), ('Plaza', 200), ('Curb', 200), ('Blades', 240)]:
    name = 'M_' + key + '_Balanced'
    path = FOLDER + '/' + name
    material = A.load_asset(path) if A.does_asset_exist(path) else None
    if not material:
        material = TOOLS.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_property('used_with_instanced_static_meshes', True)
        atlas = '/Game/Environment/MainVillage/Streetscape/Textures/T_' + key
        sample = texture(grass if key in ('Grass', 'Blades') else ('/Game/Environment/MainVillage/Streetscape/Textures/T_Plaza_BaseColor' if key == 'Curb' else atlas + '_BaseColor'), period=period)
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
            'Curb': (1.1, .98, .92), 'Blades': (.70, .84, .56),
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
        if key == 'Blades':
            material.set_editor_property('two_sided', True)
            diffuse = E.create_material_expression(material, unreal.MaterialExpressionMultiply)
            diffuse.set_editor_property('const_b', .22)
            assert E.connect_material_expressions(multiply, '', diffuse, 'A')
            assert E.connect_material_property(diffuse, '', P.MP_EMISSIVE_COLOR)
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


def street_mesh(name, vertices, key, triangles=None):
    path = OUT / (name + '.obj')
    lines = ['o ' + name]
    # The legacy OBJ importer reflects Y and preserves Z.
    lines.extend(f'v {x:.5f} {-y:.5f} {z:.5f}' for x, y, z in vertices)
    if triangles is None:
        triangles = [(i, i+1, i+2) for i in range(0, len(vertices)-2, 2)] + [(i+1, i+3, i+2) for i in range(0, len(vertices)-2, 2)]
    lines.extend(f'f {a+1} {b+1} {c+1}' for a, b, c in triangles)
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
    actor.static_mesh_component.set_collision_profile_name('NoCollision' if key in ('Blades', 'Curb') else 'BlockAll')
    actor.static_mesh_component.set_cast_shadow(key == 'Curb')
    center, extent = actor.get_actor_bounds(False)
    for axis in range(3):
        coords = [v[axis] for v in vertices]
        assert abs(getattr(center, 'xyz'[axis]) - (min(coords)+max(coords))/2) < 1, (name, center, extent)
    return actor


actors = ACTORS.get_all_level_actors()
plan = next(a for a in actors if a.get_actor_label() == 'MainVillage_Blockout')
layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))


def rounded(points):
    for _ in range(2):
        result = [points[0]]
        for a, b in zip(points, points[1:]):
            for t in (.25, .75):
                result.append(tuple(x+(y-x)*t for x, y in zip(a, b)))
        points = result + [points[-1]]
    return points


def kerb(name, points, offset):
    z = [p[2] for p in points]
    profiles = [(-11, -4), (11, -4), (11, 8), (7, 12), (-7, 12), (-11, 8)]
    rails = [ribbon(points, (offset + lateral,)) for lateral, _ in profiles]
    vertices = [(rail[i][0], rail[i][1], z[i]+height)
                for i in range(len(points)) for rail, (_, height) in zip(rails, profiles)]
    count = len(profiles)
    faces = []
    for i in range(len(points)-1):
        for j in range(count):
            a, b = i*count+j, i*count+(j+1)%count
            faces.extend([(a, b+count, b), (a, a+count, b+count)])
    for j in range(1, count-1):
        end = (len(points)-1)*count
        faces.extend([(0, j, j+1), (end, end+j+1, end+j)])
    street_mesh(name, vertices, 'Curb', faces)


branch = [(2050, 430, 11.4), (2100, 180, 11.4), (2160, -260, 11.4),
          (2200, -800, 11.4), (2170, -1150, 11.4), (2100, -1500, 11.4), (1950, -1750, 11.4)]
branch = rounded(branch)
street_mesh('Village_BranchAsphalt', ribbon(branch, (-200, 200)), 'Asphalt')
# With the branch traveling toward -Y, positive offsets point east.
walk = [(x, y, 12.0) for x, y, _ in branch]
first_walk = next(i for i, (_, y, _) in enumerate(walk) if y < 310)
street_mesh('Village_BranchWestPavers', ribbon(walk, (-365, -197))[first_walk*2:], 'Sidewalk')
street_mesh('Village_BranchEastPavers', ribbon(walk, (197, 350))[first_walk*2:], 'Sidewalk')
for key, offset in [('West', -200), ('East', 200)]:
    kerb('Village_Branch' + key + 'Edge', branch[first_walk+1:], offset)

main_walk = [(-1160, -90, 8), (410, 150, 8), (1810, 190, 8), (4950, 190, 8)]
street_mesh('Village_MainNearWest', ribbon(main_walk[:-1]+[(1893, 190, 8)], (-135, 135)), 'Sidewalk')
street_mesh('Village_MainNearEast', ribbon([(2300, 190, 8), (4950, 190, 8)], (-135, 135)), 'Sidewalk')
main_street = [(-1200, 310, 9), (350, 550, 9), (1800, 600, 9), (4950, 600, 9)]
far_walk = [(-1250, 710, 8), (290, 950, 8), (1790, 1000, 8), (4950, 1000, 8)]
street_mesh('Village_MainAsphalt', ribbon(main_street, (-280, 280)), 'Asphalt')
street_mesh('Village_MainFarPavers', ribbon(far_walk, (-135, 135)), 'Sidewalk')
layout['elements'] = [item for item in layout['elements'] if item['label'] not in {
    'Village curved side street', 'Village side street west sidewalk', 'Village side street east sidewalk',
    'Main street', 'Plaza-side sidewalk', 'Far sidewalk'} and item['typeId'] not in ('Lawn', 'Garden')]
for item in layout['types']:
    if item['typeId'] in surfaces:
        item['material'] = surfaces[item['typeId']].get_path_name()
for item in layout['elements']:
    if item['label'] == 'Market square':
        for point in item['points']:
            point['y'] = min(point['y'], 318)
unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(layout))
assert json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))['elements'] == layout['elements']


def add_grass():
    rng = random.Random(6441)
    run = [(x, y) for x, y, _ in branch]
    river = json.loads((ROOT / 'Saved/MainVillage/Art/water_reservation.json').read_text(encoding='utf-8'))
    water = [point[:2] for point in river['centerline_cm']]

    def distance(x, y, path):
        distances = []
        for (ax, ay), (bx, by) in zip(path, path[1:]):
            dx, dy = bx-ax, by-ay
            t = max(0., min(1., ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            distances.append(math.hypot(x-ax-t*dx, y-ay-t*dy))
        return min(distances)

    total = 0
    for cell in range(6):
        vertices, triangles = [], []
        for _ in range(1750):
            x = -1250 + (cell+rng.random()) * 1240
            y = rng.uniform(-3550, 1730)
            if distance(x, y, water) < river['width_cm']/2+20 or distance(x, y, run) < 386:
                continue
            patch = .51 + .19*math.sin(x*.016+y*.009) + .19*math.cos(y*.013-x*.008)
            if rng.random() > patch:
                continue
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 1500),
                unreal.Vector(x, y, -100), unreal.TraceTypeQuery.ECC_VISIBILITY,
                False, [], unreal.DrawDebugTrace.NONE, True)
            if not hit:
                continue
            data = hit.to_dict()
            if not isinstance(data['hit_actor'], unreal.LandscapeProxy):
                continue
            z = data['location'].z
            for _ in range(rng.randint(5, 7)):
                angle = rng.uniform(0, math.tau)
                dx, dy = math.cos(angle), math.sin(angle)
                u, v = x+rng.uniform(-12, 12), y+rng.uniform(-12, 12)
                width, height = rng.uniform(1.6, 3.2), rng.uniform(9, 25)
                index = len(vertices)
                vertices.extend([(u-dy*width, v+dx*width, z), (u+dy*width, v-dx*width, z),
                                 (u+dx*4-dy*width*.5, v+dy*4+dx*width*.5, z+height*.6),
                                 (u+dx*4+dy*width*.5, v+dy*4-dx*width*.5, z+height*.6),
                                 (u+dx*10, v+dy*10, z+height)])
                triangles.extend([(index, index+1, index+2), (index+1, index+3, index+2),
                                  (index+2, index+3, index+4)])
            total += 1
        assert vertices, f'No terrain grass candidates in cell {cell}'
        street_mesh(f'Village_GrassClumps_{cell:02}', vertices, 'Blades', triangles)
    print('VILLAGE_GRASS_CLUMPS', total)


add_grass()
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
