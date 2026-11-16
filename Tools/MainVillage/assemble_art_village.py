"""Assemble generated village art on a new copy of the reviewed streetscape.

Run in Unreal Editor Python after the asset import. No source map or mesh is
modified. A pre-existing destination map is always refused.
"""

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/Art'
SOURCE = '/Game/Maps/L_MainVillage_Blockout_01'
MAP = '/Game/Maps/L_MainVillage_Art_01'
BASE = '/Game/Environment/MainVillage'
ASSETS = unreal.EditorAssetLibrary
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT.mkdir(parents=True, exist_ok=True)
overrides_path = OUT / 'assembly_overrides.json'
OVERRIDES = json.loads(overrides_path.read_text(encoding='utf-8-sig')) if overrides_path.exists() else {}

PATHS = {
    **{name: f'{BASE}/Architecture/{name}/v001/SM_{name}' for name in ('Mart', 'GreenHouse', 'Salon')},
    **{name: f'{BASE}/Nature/{name}/v001/SM_{name}' for name in ('Tree', 'Shrub', 'Flowers', 'Rock')},
    **{name: f'{BASE}/Streetscape/{name}/v001/SM_{name}' for name in ('Bench', 'Lamp', 'Fence', 'Bridge', 'Planter')},
    'ExistingHouse': '/Game/Characters/Meshy/CozyHouse01/candidate_v001/SM_CozyHouse01',
}
PATHS.update(OVERRIDES.get('asset_paths', {}))
meshes = {key: ASSETS.load_asset(path) for key, path in PATHS.items()}
missing = [PATHS[key] for key, mesh in meshes.items() if not isinstance(mesh, unreal.StaticMesh)]
(OUT / 'preflight.json').write_text(json.dumps({'missing_assets': missing, 'paths': PATHS}, indent=2), encoding='utf-8')
assert not missing, f'Import the required art first: {missing}'
assert not ASSETS.does_asset_exist(MAP), f'Refusing to overwrite {MAP}'
source_file = ROOT / 'Content/Maps/L_MainVillage_Blockout_01.umap'
source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
assert LEVELS.load_level(SOURCE)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, MAP)
assert LEVELS.load_level(MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith(MAP + '.')

plans = [actor for actor in ACTORS.get_all_level_actors()
         if isinstance(actor, unreal.TownAgeMapLayout) and actor.get_actor_label() == 'MainVillage_Blockout']
assert len(plans) == 1
plan = plans[0]
layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
removed = [element for element in layout['elements'] if element['label'] in
           ('Market shell', 'Salon shell', 'NPC house A', 'NPC house B')]
assert len(removed) == 4
layout['elements'] = [element for element in layout['elements'] if element not in removed]
unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(layout))
layout_instance_count = unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan)
assert layout_instance_count >= len(layout['elements']), 'Layout regeneration failed'
for actor in list(ACTORS.get_all_level_actors()):
    if str(actor.get_folder_path()) == 'MainVillage/Blockout/Entrances':
        ACTORS.destroy_actor(actor)

placements = []


def place(key, label, x, y, height, yaw=0., ground=0., max_width=None, max_depth=None, collision=False):
    """Use actual mesh bounds, including off-center pivots, to seat art on ground."""
    mesh = meshes[key]
    bounds = mesh.get_bounds()
    extent, center = bounds.box_extent, bounds.origin
    assert extent.z > .001, f'{key} has no usable height'
    scale = height / (2 * extent.z)
    angle = math.radians(yaw + float(OVERRIDES.get('yaw_degrees', {}).get(key, 0.)))
    c, s = math.cos(angle), math.sin(angle)
    width = 2 * (abs(c) * extent.x + abs(s) * extent.y)
    depth = 2 * (abs(s) * extent.x + abs(c) * extent.y)
    if max_width:
        scale = min(scale, max_width / max(width, .001))
    if max_depth:
        scale = min(scale, max_depth / max(depth, .001))
    pivot = unreal.Vector(x - scale * (c * center.x - s * center.y),
                          y - scale * (s * center.x + c * center.y),
                          ground - scale * (center.z - extent.z))
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, pivot,
                                         unreal.Rotator(pitch=0, yaw=math.degrees(angle), roll=0))
    assert actor
    actor.set_actor_label(label)
    group = 'Architecture' if key in ('Mart', 'Salon', 'GreenHouse', 'ExistingHouse') else (
        'Nature' if key in ('Tree', 'Shrub', 'Flowers', 'Rock') else 'Streetscape')
    actor.set_folder_path('MainVillage/Art/' + group)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
    actor.static_mesh_component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    location, half = actor.get_actor_bounds(False)
    assert abs(location.z - half.z - ground) < .1, label
    placements.append({'label': label, 'asset': key, 'path': mesh.get_path_name(),
                       'center_cm': [location.x, location.y, location.z],
                       'extent_cm': [half.x, half.y, half.z], 'ground_cm': ground,
                       'scale': scale, 'yaw': math.degrees(angle), 'collision': collision})
    return actor


# Keep reviewed door approach points and the original interacting cottage intact.
place('Mart', 'Village_Mart', 3725, -1187.5, 420, max_width=710, max_depth=525, collision=True)
place('Salon', 'Village_Salon', 4585, -940, 400, max_width=490, max_depth=440, collision=True)
place('GreenHouse', 'Village_GreenRoofHouse', 1420, -750, 430, max_width=540, max_depth=500, collision=True)
place('ExistingHouse', 'Village_FallbackHouse', 415, -647.5, 430, max_width=530, max_depth=455, collision=True)

# A single quiet plaza focal point; preserve the main entrance/crossing routes.
place('Planter', 'Plaza_CentralPlanter', 4110, -420, 65, max_width=330, max_depth=330, ground=9)
place('Tree', 'Plaza_CentralTree', 4110, -420, 720, ground=38)
for index, (x, y, yaw) in enumerate([(3750, -390, 90), (4500, -340, -90), (4750, 35, 180), (2100, 1175, 0)]):
    place('Bench', f'Village_Bench_{index:02d}', x, y, 95, yaw, ground=9, max_width=210, max_depth=210)
for index, (x, y) in enumerate([(3230, 15), (4840, 140), (3300, 1170), (1250, 1160), (-200, 795), (2060, -20)]):
    place('Lamp', f'Village_Lamp_{index:02d}', x, y, 330, ground=9)

trees = [(-550, -1200, 800), (200, -1450, 690), (1150, -1540, 760),
         (2150, -1450, 820), (3050, -1700, 710), (4030, -1730, 720),
         (5350, -1100, 850), (5520, -300, 800), (5200, 1500, 780),
         (4250, 1730, 650), (2700, 1700, 710), (1400, 1700, 740),
         (150, 1550, 790), (-950, 300, 780), (550, -3200, 780),
         (2200, -3300, 860), (3800, -3300, 800), (5600, -3650, 850)]
for index, (x, y, height) in enumerate(trees):
    place('Tree', f'Village_Tree_{index:02d}', x, y, height, yaw=(index * 137) % 360)

garden_points = [(190, -245), (690, -450), (1190, -420), (1700, -335),
                 (2510, -415), (3090, -400), (3290, -1150), (4880, -650),
                 (5260, -600), (5030, 1320), (100, 1320), (1850, 1450)]
for index, (x, y) in enumerate(garden_points):
    place('Shrub', f'Village_Shrub_{index:02d}', x, y, 105 + (index % 3) * 12, yaw=index * 47)
    place('Flowers', f'Village_Flowers_{index:02d}', x + 85, y + 75, 50, yaw=index * 31)
for index, (x, y) in enumerate([(3950, -420), (4240, -420), (4110, -560), (4110, -290)]):
    place('Flowers', f'Plaza_Flowers_{index:02d}', x, y, 45, ground=48)
for index, (x, y) in enumerate([(3370, 50), (4680, 160), (700, 1020)]):
    place('Planter', f'Village_Planter_{index:02d}', x, y, 60, ground=9, max_width=160)
    place('Flowers', f'Village_PlanterFlowers_{index:02d}', x, y, 55, ground=50)

for index, (x, y, yaw) in enumerate([(2480, -250, 0), (2690, -250, 0),
                                    (3080, -250, 0), (3190, -500, 90),
                                    (165, -90, 0), (660, -190, 0),
                                    (1210, -120, 0), (1730, -130, 0)]):
    place('Fence', f'Village_Fence_{index:02d}', x, y, 90, yaw, max_width=250, max_depth=250)

# Water is deliberately absent. These persistent editor markers encode the
# future strip without introducing a runtime plugin or modifying the Landscape.
river = {'centerline_cm': [[-700, -2200, 15], [1200, -2350, 15], [2900, -2250, 15],
                          [4300, -2400, 15], [5500, -2900, 15], [6500, -3200, 15]],
         'width_cm': 650, 'water_surface_z_cm': 15, 'current_bed_z_cm': 0,
         'water_created': False, 'landscape_excavated': False,
         'note': 'A shallow water strip at Z=15cm sits above the current flat ground at Z=0cm. No excavation is needed for this initial visual surface; deeper water needs later Landscape sculpting.'}
for index, point in enumerate(river['centerline_cm']):
    marker = ACTORS.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(*point))
    marker.set_actor_label(f'FutureRiver_Center_{index:02d}_WaterZ15')
    marker.set_folder_path('MainVillage/River/WaterReservation')
    marker.set_editor_property('is_editor_only_actor', True)
    marker.tags = ['FutureRiver', 'WidthCm650', 'WaterSurfaceCm15', 'CurrentBedCm0']
    for side in (-1, 1):
        bank = ACTORS.spawn_actor_from_class(unreal.TargetPoint,
            unreal.Vector(point[0], point[1] + side * 325, 0))
        bank.set_actor_label(f'FutureRiver_Bank_{index:02d}_{side:+d}')
        bank.set_folder_path('MainVillage/River/WaterReservation')
        bank.set_editor_property('is_editor_only_actor', True)

place('Bridge', 'Village_RiverBridge', 4700, -2567, 210, yaw=67, ground=0, max_width=1000, max_depth=1000, collision=True)
for index, (x, y) in enumerate([(0, -1830), (900, -1980), (1850, -1930),
                               (2900, -1870), (3750, -1960), (4400, -2800),
                               (5200, -3100), (5700, -3350)]):
    place('Rock', f'River_BankRock_{index:02d}', x, y, 80 + (index % 3) * 20, yaw=index * 83)

# Saved editor review camera, not a new player camera or gameplay view target.
camera = ACTORS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(7000, 6500, 6400),
    unreal.Rotator(pitch=-39, yaw=-118, roll=0))
camera.set_actor_label('MainVillage_Art_Overview')
camera.set_folder_path('MainVillage/Review')
camera.camera_component.set_field_of_view(48)
camera.set_editor_property('is_editor_only_actor', True)

starts = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
assert len(starts) == 1
assert LEVELS.save_current_level()
assert hashlib.sha256(source_file.read_bytes()).hexdigest() == source_hash, 'Source map changed unexpectedly'
report = {'map': MAP, 'source': SOURCE, 'source_sha256': source_hash,
          'asset_paths': PATHS, 'missing_assets': missing, 'removed_shells': [e['label'] for e in removed],
          'counts': dict(Counter(p['asset'] for p in placements)), 'placements': placements,
          'river': river, 'source_map_unchanged': True, 'player_start_count': len(starts),
          'layout_instance_count': layout_instance_count,
          'visual_review_required': True, 'collision_walk_test_required': True,
          'limitations': ['Generated new buildings are static exteriors; their doors do not yet implement travel.',
                         'No water surface or excavated river bed yet.',
                         'Desktop package, multiplayer and physical mobile performance are not verified here.']}
(OUT / 'assembly_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
(OUT / 'water_reservation.json').write_text(json.dumps(river, indent=2), encoding='utf-8')
print('MAIN_VILLAGE_ART_ASSEMBLED', json.dumps({'map': MAP, 'counts': report['counts'], 'report': str(OUT / 'assembly_report.json')}))
