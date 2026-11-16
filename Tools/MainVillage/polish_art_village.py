"""Polish the copied village composition without changing its source or portals."""

import hashlib
import json
import math
import shutil
import struct
import uuid
from datetime import datetime
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/Art'
MAP = '/Game/Maps/L_MainVillage_Art_01'
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
map_file = ROOT / 'Content/Maps/L_MainVillage_Art_01.umap'
source = ROOT / 'Content/Maps/L_MainVillage_Blockout_01.umap'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
backup = OUT / ('polish_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
backup.mkdir(parents=True)
shutil.copy2(map_file, backup / map_file.name)
assert LEVELS.load_level(MAP)
actors = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()}
changes = []
replacement_assets = {}
def transform_values(actor):
    position, rotation, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    return {'location_cm': [position.x, position.y, position.z],
            'rotation_degrees': [rotation.pitch, rotation.yaw, rotation.roll],
            'scale': [scale.x, scale.y, scale.z]}


protected = {label: transform_values(actor) for label, actor in actors.items()
             if 'CozyHouse' in label or 'Door' in label or 'Portal' in label}


def fit(actor, x, y, height, *, width=None, depth=None, yaw=None, ground=0.):
    mesh = actor.static_mesh_component.get_editor_property('static_mesh')
    bounds = mesh.get_bounds()
    center, half = bounds.origin, bounds.box_extent
    assert min(half.x, half.y, half.z) > .001
    sz = height / (2 * half.z)
    sx = width / (2 * half.x) if width else sz
    sy = depth / (2 * half.y) if depth else sz
    rotation = actor.get_actor_rotation()
    if yaw is not None:
        rotation = unreal.Rotator(pitch=0, yaw=yaw, roll=0)
    angle = math.radians(rotation.yaw)
    c, s = math.cos(angle), math.sin(angle)
    actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    actor.set_actor_rotation(rotation, True)
    actor.set_actor_location(unreal.Vector(x - c * center.x * sx + s * center.y * sy,
                                          y - s * center.x * sx - c * center.y * sy,
                                          ground - (center.z - half.z) * sz), False, True)
    origin, extent = actor.get_actor_bounds(False)
    changes.append({'label': actor.get_actor_label(), 'center_cm': [origin.x, origin.y, origin.z],
                    'size_cm': [extent.x * 2, extent.y * 2, extent.z * 2],
                    'yaw': rotation.yaw, 'ground_cm': ground})


def clone(source_label, label, x, y, height, **kwargs):
    actor = actors.get(label)
    if not actor:
        template = actors[source_label]
        actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector())
        actor.set_actor_label(label)
        actor.set_folder_path('MainVillage/Art/Polish')
        actor.static_mesh_component.set_static_mesh(template.static_mesh_component.get_editor_property('static_mesh'))
        actor.static_mesh_component.set_collision_profile_name(template.static_mesh_component.get_collision_profile_name())
        actor.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
        actors[label] = actor
    fit(actor, x, y, height, **kwargs)
    return actor


# Stagger the left cottages and enlarge the plaza shops relative to the trees.
for name, label in [('Mart', 'Village_Mart'), ('Salon', 'Village_Salon'),
                    ('GreenHouse', 'Village_GreenRoofHouse')]:
    path = f'/Game/Environment/MainVillage/Architecture/{name}/v002/SM_{name}'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        assert isinstance(mesh, unreal.StaticMesh), path
        actors[label].static_mesh_component.set_static_mesh(mesh)
        replacement_assets[name] = path
fit(actors['Village_Mart'], 3650, -1390, 430, width=850, depth=530)
fit(actors['Village_Salon'], 4700, -1160, 440, width=600, depth=510)
fit(actors['Village_GreenRoofHouse'], 1500, -1320, 450, width=510, depth=450)
fit(actors['Village_FallbackHouse'], 850, -1840, 480, width=515, depth=465)
clone('Village_FallbackHouse', 'Village_ForegroundFallbackHouse', 5480, -290, 520,
      width=600, depth=520)

# Keep center foliage between storefronts instead of covering the mart facade.
fit(actors['Plaza_CentralPlanter'], 4250, -460, 55, width=300, depth=300, ground=9)
fit(actors['Plaza_CentralTree'], 4250, -460, 550, ground=40)
for index, (x, y) in enumerate([(4125, -460), (4380, -460), (4250, -580), (4250, -335)]):
    fit(actors[f'Plaza_Flowers_{index:02d}'], x, y, 90, ground=48)

# Move the near lamp away from the PlayerStart/gameplay camera sight line.
fit(actors['Village_Lamp_02'], 3850, 1210, 310, ground=9)
for index in range(12):
    actor = actors[f'Village_Flowers_{index:02d}']
    center, extent = actor.get_actor_bounds(False)
    fit(actor, center.x, center.y, 95, ground=max(0., center.z - extent.z))

tree_positions = [(-230, -1100), (380, -1650), (1360, -1950),
                  (2700, -1800), (3090, -1850), (4100, -1840),
                  (5340, -1300), (5950, -700), (5980, 900),
                  (4650, 1600), (2700, 1580), (1400, 1550),
                  (-150, 1100), (-1000, 100), (550, -3100),
                  (2200, -3250), (3800, -3250), (5600, -3700)]
for index, (x, y) in enumerate(tree_positions):
    fit(actors[f'Village_Tree_{index:02d}'], x, y, 560 + (index % 4) * 25, yaw=(index * 137) % 360)
for index, (x, y) in enumerate([(-400, -3000), (300, -3450), (1100, -3100),
                               (1700, -3550), (2600, -3200), (3300, -3650),
                               (4200, -3350), (4800, -3900), (5400, -3500), (6200, -4000)]):
    clone('Village_Tree_00', f'Polish_BackgroundTree_{index:02d}', x, y,
          570 + index % 4 * 35, yaw=index * 111)

for index, (x, y, yaw) in enumerate([(3860, -450, 90), (4610, -430, -90),
                                    (4800, 40, 180), (1950, 1190, 0)]):
    fit(actors[f'Village_Bench_{index:02d}'], x, y, 105, yaw=yaw, ground=9)

# Extend the existing paving to the foreground cottage rather than placing it
# in an unrelated empty field. Only this copied map's layout changes.
plan = actors['MainVillage_Blockout']
layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(plan))
layout['elements'] = [e for e in layout['elements'] if e['label'] not in
                      ('Foreground cottage approach', 'Green cottage approach', 'Rear cottage approach',
                       'Village curved side street', 'Village side street west sidewalk',
                       'Village side street east sidewalk')]
for name, a, b in [('Foreground cottage approach', (4910, -50, 2), (5480, 180, 2)),
                   ('Green cottage approach', (1480, -1100, 2), (1660, -450, 2)),
                   ('Rear cottage approach', (760, -1610, 2), (940, -450, 2))]:
    layout['elements'].append({'id': uuid.uuid5(uuid.NAMESPACE_URL, 'townage:art:' + name).hex,
        'kind': 'Field', 'typeId': 'Plaza', 'label': name,
        'points': [dict(zip('xyz', a)), dict(zip('xyz', b))], 'widthCm': 200, 'heightCm': 300})
branch = [(2050, 600, 3), (2100, 180, 3), (2160, -260, 3),
          (2200, -800, 3), (2170, -1150, 3), (2100, -1500, 3), (1950, -1750, 3)]
for label, key, points, width in [
    ('Village curved side street', 'Asphalt', branch, 400),
    ('Village side street west sidewalk', 'Sidewalk',
     [(x - 300, y, z) for x, y, z in branch[1:]], 160),
    ('Village side street east sidewalk', 'Sidewalk',
     [(x + 280, y, z) for x, y, z in branch[1:]], 140),
]:
    layout['elements'].append({'id': uuid.uuid5(uuid.NAMESPACE_URL, 'townage:art:' + label).hex,
        'kind': 'Road', 'typeId': key, 'label': label,
        'points': [dict(zip('xyz', point)) for point in points], 'widthCm': width, 'heightCm': 300})
unreal.TownAgeMapEditorLibrary.import_json(plan, json.dumps(layout))
assert unreal.TownAgeMapEditorLibrary.get_generated_instance_count(plan) >= len(layout['elements'])

# Remove only the north-edge curb instances at the new side-street mouth.
# Existing crossing, south curb, cottage components and all other ISMs remain.
curb_changes = []
for label in ('Street_Curb_Stone', 'Street_Curb_Tapers'):
    curb_actor = actors.get(label)
    if not curb_actor:
        continue
    component = curb_actor.get_component_by_class(unreal.InstancedStaticMeshComponent)
    assert component and str(curb_actor.get_folder_path()) == 'MainVillage/Streetscape'
    before_count = component.get_instance_count()
    removed_indices = []
    for index in reversed(range(before_count)):
        transform = component.get_instance_transform(index, world_space=True)
        location = transform.translation
        if 1750 <= location.x <= 2400 and 0 <= location.y <= 450:
            assert component.remove_instance(index)
            removed_indices.append(index)
    curb_changes.append({'actor': label, 'before': before_count,
                         'after': component.get_instance_count(), 'removed_indices': removed_indices})

# Small contiguous garden groups give the same lush boundaries as the concept.
garden_clusters = [(450, -1300), (1190, -900), (1100, -950), (1000, -1450),
                   (3310, -1710), (5000, -1110), (5150, -750), (5740, -660),
                   (5780, 50), (5200, 80), (-100, 880), (1350, 1350),
                   (3800, 1390), (4700, 1300)]
for index, (x, y) in enumerate(garden_clusters):
    for offset in range(2):
        clone('Village_Shrub_00', f'Polish_Shrub_{index:02d}_{offset}', x + offset * 105,
              y - offset * 35, 95 + (index % 3) * 10, yaw=index * 37)
    clone('Village_Flowers_00', f'Polish_Flower_{index:02d}', x + 40, y + 90, 105, yaw=index * 53)

# The long bridge axis must span the 650cm reserved channel, with bank overlap.
bridge = actors['Village_RiverBridge']
half = bridge.static_mesh_component.get_editor_property('static_mesh').get_bounds().box_extent
long_axis = 'x' if half.x >= half.y else 'y'
fit(bridge, 4700, -2567, 195, width=850 if long_axis == 'x' else 300,
    depth=300 if long_axis == 'x' else 850, yaw=67 if long_axis == 'x' else -23, ground=0)

# Repeated source rocks outline both banks without creating a water mesh.
river_path = [(-700, -2200), (1200, -2350), (2900, -2250), (4300, -2400), (5500, -2900), (5600, -2940)]
# Read the original native Landscape samples. Conservatively use each sampled
# cell's maximum corner rather than assuming every part of this district is flat.
height_bytes = (ROOT / 'ArtSource/Terrain/Village01/Height.r16').read_bytes()
assert len(height_bytes) == 253 * 253 * 2
heights = struct.unpack('<' + 'H' * (253 * 253), height_bytes)
max_bed_height = 0.
sample_count = 0
for a, b in zip(river_path, river_path[1:]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    steps = math.ceil(length / 100)
    for step in range(steps + 1):
        for offset in (-325, -300, -200, -100, 0, 100, 200, 300, 325):
            x = a[0] + dx * step / steps - dy / length * offset
            y = a[1] + dy * step / steps + dx / length * offset
            ix, iy = int((x + 12600) / 100), int((y + 12600) / 100)
            assert 0 <= ix < 252 and 0 <= iy < 252
            max_bed_height = max(max_bed_height,
                max((heights[j * 253 + i] - 32768) * 100 / 128
                    for j in (iy, iy + 1) for i in (ix, ix + 1)))
            sample_count += 1
assert max_bed_height < 15, f'Future water would intersect terrain: {max_bed_height}'
for index, (x, y) in enumerate(river_path):
    a, b = river_path[max(0, index - 1)], river_path[min(len(river_path) - 1, index + 1)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    for label, actor in actors.items():
        if label.startswith(f'FutureRiver_Center_{index:02d}_'):
            actor.set_actor_location(unreal.Vector(x, y, 15), False, True)
            actor.tags = ['FutureRiver', 'WidthCm650', 'WaterSurfaceCm15', 'TerrainSampled']
    for side in (-1, 1):
        actor = actors[f'FutureRiver_Bank_{index:02d}_{side:+d}']
        actor.set_actor_location(unreal.Vector(x - dy / length * 325 * side,
                                               y + dx / length * 325 * side, 15), False, True)
rock_index = 0
for a, b in zip(river_path, river_path[1:]):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    count = max(1, round(length / 260))
    for step in range(count):
        t = (step + .5) / count
        for side in (-1, 1):
            x, y = a[0] + dx * t + nx * 355 * side, a[1] + dy * t + ny * 355 * side
            clone('River_BankRock_00', f'Polish_BankRock_{rock_index:03d}', x, y,
                  65 + (rock_index % 4) * 10, yaw=rock_index * 71)
            rock_index += 1
for label, actor in list(actors.items()):
    if label.startswith('Polish_BankRock_') and int(label.rsplit('_', 1)[1]) >= rock_index:
        ACTORS.destroy_actor(actor)

grass = unreal.load_asset('/Game/Environment/MainVillage/Blockout/M_Lawn')
assert isinstance(grass, unreal.MaterialInterface)
landscape_overrides = []
for actor in ACTORS.get_all_level_actors():
    if isinstance(actor, unreal.Landscape):
        actor.set_editor_property('landscape_material', grass)
        landscape_overrides.append(actor.get_actor_label())

lighting = []
for actor in ACTORS.get_all_level_actors():
    if isinstance(actor, unreal.DirectionalLight):
        actor.set_actor_rotation(unreal.Rotator(pitch=-55, yaw=-30, roll=0), True)
        light = actor.get_editor_property('light_component')
        light.set_editor_property('light_source_angle', 4.)
        light.set_editor_property('shadow_amount', .55)
        # Match the stylized cubemap's exposure scale instead of overwhelming it
        # with the source terrain's physical 50,000-lux daylight.
        light.set_editor_property('intensity', 10.)
        lighting.append({'actor': actor.get_actor_label(), 'intensity': 10., 'source_angle': 4, 'shadow_amount': .55})
    elif isinstance(actor, unreal.SkyLight):
        light = actor.get_editor_property('light_component')
        cubemap = unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')
        assert cubemap
        light.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        light.set_editor_property('cubemap', cubemap)
        light.set_editor_property('intensity', 2.)
        lighting.append({'actor': actor.get_actor_label(), 'intensity': 2.,
                         'cubemap': cubemap.get_path_name()})

camera = actors['MainVillage_Art_Overview']
camera_location, target = unreal.Vector(6200, 4800, 4800), unreal.Vector(3000, -800, 150)
camera.set_actor_location(camera_location, False, True)
camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera_location, target), True)
camera.camera_component.set_field_of_view(50.)
protected_checks = {}
for label, before_transform in protected.items():
    after_transform = transform_values(actors[label])
    deltas = {key: max(abs(a - b) for a, b in zip(before_transform[key], after_transform[key]))
              for key in before_transform}
    protected_checks[label] = {'before': before_transform, 'after': after_transform,
                                'maximum_deltas': deltas}
    assert all(delta <= 1e-4 for delta in deltas.values()), f'Interactive object moved: {label}: {deltas}'
assert LEVELS.save_current_level()
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
water_path = OUT / 'water_reservation.json'
if water_path.exists():
    shutil.copy2(water_path, backup / water_path.name)
water = {'centerline_cm': [[x, y, 15] for x, y in river_path], 'width_cm': 650,
         'water_surface_z_cm': 15, 'max_bed_height_cm': max_bed_height,
         'minimum_sampled_clearance_cm': 15 - max_bed_height, 'terrain_sample_count': sample_count,
         'sampling': '100cm along centerline; across strip at <=100cm spacing, conservatively maximum four cell corners',
         'water_created': False, 'landscape_excavated': False,
         'note': 'Shallow visual water strip is above sampled terrain. No claim of uniform zero-height bed or deep river.'}
water_path.write_text(json.dumps(water, indent=2), encoding='utf-8')
report = {'map': MAP, 'backup': str(backup), 'changes': changes, 'lighting': lighting,
          'replacement_assets': replacement_assets,
          'side_street_points_cm': branch, 'side_street_width_cm': 400, 'curb_changes': curb_changes,
          'source_map_unchanged': True, 'interactive_transforms_preserved': protected_checks,
          'bridge_long_axis': long_axis, 'bridge_span_cm': 850, 'water_width_cm': 650,
          'water_surface_z_cm': 15, 'water_present': False,
          'water_reservation': water, 'landscape_grass_override': landscape_overrides,
          'camera': {'position_cm': [6200, 4800, 4800], 'target_cm': [3000, -800, 150], 'fov': 50},
          'visual_review_required': True}
(OUT / 'polish_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MAIN_VILLAGE_ART_POLISHED', str(OUT / 'polish_report.json'))
