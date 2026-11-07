"""Create the modern ground-only Village01 Landscape in Unreal Editor.

First run generate_village_maps.py, then this file through Unreal's Python
commandlet with the interactive editor saved/closed. Finish edit-layer rendering
in a GPU editor with -VillageFinalize -ExecCmds="py <this file>". Existing maps
are never recreated. Outside Unreal, --textures-only prepares two surface maps.
"""
import json
import math
from pathlib import Path
import random
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Terrain/Village01'
DEST = '/Game/Terrain/Village01'
MAP = '/Game/Maps/L_VillageTerrain_01'
LAYERS = ('Grass', 'Paving', 'Earth')


def write_png(path, size, pixels):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    rows = b''.join(b'\0' + bytes(pixels[y * size * 3:(y + 1) * size * 3]) for y in range(size))
    payload = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))
    if path.exists() and path.read_bytes() != payload:
        raise ValueError('Refusing to overwrite a changed surface texture: ' + str(path))
    path.write_bytes(payload)


def generate_surface_textures():
    SOURCE.mkdir(parents=True, exist_ok=True)
    rng = random.Random(3701)
    grass = []
    for y in range(128):
        for x in range(128):
            variation = (.055 * math.sin(x * .13 + math.sin(y * .09))
                         + .035 * math.cos(y * .17 + x * .04) + rng.uniform(-.018, .018))
            grass.extend(max(0, min(255, round(c * (1 + variation)))) for c in (123, 163, 92))
    grass_path = SOURCE / 'T_GrassVariation.png'
    write_png(grass_path, 128, grass)
    paving = []
    for y in range(512):
        row = y // 64
        for x in range(512):
            offset_x = (x + (32 if row % 2 else 0)) % 512
            col = offset_x // 64
            joint = y % 64 < 2 or offset_x % 64 < 2
            variation = math.sin(row * 13.1 + col * 7.7) * 3 + rng.uniform(-.8, .8)
            base = (157, 154, 141) if joint else (201, 196, 178)
            paving.extend(max(0, min(255, round(c + variation))) for c in base)
    paving_path = SOURCE / 'T_PavingTiles.png'
    write_png(paving_path, 512, paving)
    return {'Grass': grass_path, 'Paving': paving_path}


def validate_raw_maps():
    count = 253 * 253
    height_bytes = (SOURCE / 'Height.r16').read_bytes()
    assert len(height_bytes) == count * 2
    weights = [(SOURCE / (name + '.r8')).read_bytes() for name in LAYERS]
    assert all(len(w) == count for w in weights)
    assert all(sum(values) == 255 for values in zip(*weights))
    heights = struct.unpack('<' + str(count) + 'H', height_bytes)
    assert min(heights) >= 32768 and max(heights) <= 32768 + 1024
    return json.loads((SOURCE / 'terrain_manifest.json').read_text(encoding='utf-8'))


def create_material(unreal, paths):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = unreal.load_asset(DEST + '/M_Village01_Surface')
    if not material:
        material = tools.create_asset('M_Village01_Surface', DEST, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('two_sided', False)
    blend = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    if not isinstance(blend, unreal.MaterialExpressionLandscapeLayerBlend):
        blend = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionLandscapeLayerBlend)
    entries = []
    for name in LAYERS:
        entry = unreal.LayerBlendInput()
        entry.set_editor_property('layer_name', name)
        entry.set_editor_property('blend_type', unreal.LandscapeLayerBlendType.LB_WEIGHT_BLEND)
        entry.set_editor_property('preview_weight', 1 / 3)
        entry.set_editor_property('const_layer_input', unreal.Vector(.19, .135, .08))
        entries.append(entry)
    blend.set_editor_property('layers', entries)
    position = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionWorldPosition)
    for name, path in paths.items():
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = DEST
        task.destination_name = path.stem
        task.automated = True
        task.replace_existing = False
        task.save = True
        tools.import_asset_tasks([task])
        texture = unreal.load_asset(DEST + '/' + path.stem)
        assert texture
        texture.set_editor_property('srgb', True)
        unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
        scale = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionDivide)
        scale.set_editor_property('const_b', 2400.0 if name == 'Grass' else 400.0)
        sample = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSample)
        sample.set_editor_property('texture', texture)
        sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        assert unreal.MaterialEditingLibrary.connect_material_expressions(position, 'XY', scale, 'A')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(scale, '', sample, 'UVs')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(sample, 'RGB', blend, 'Layer ' + name)
    assert unreal.MaterialEditingLibrary.connect_material_property(blend, '', unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop in [(.9, unreal.MaterialProperty.MP_ROUGHNESS), (.12, unreal.MaterialProperty.MP_SPECULAR)]:
        constant = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
        constant.set_editor_property('r', value)
        unreal.MaterialEditingLibrary.connect_material_property(constant, '', prop)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material


def create_level(unreal):
    assert not unreal.EditorAssetLibrary.does_asset_exist(MAP), 'Existing level must not be overwritten: ' + MAP
    assert not unreal.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False), 'Terrain destination must be empty: ' + DEST
    metadata = validate_raw_maps()
    paths = generate_surface_textures()
    unreal.EditorAssetLibrary.make_directory(DEST)
    material = create_material(unreal, paths)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert levels.new_level(MAP)
    landscape = unreal.TownAgeTerrainLibrary.import_village_landscape(str(SOURCE), material)
    assert isinstance(landscape, unreal.Landscape), 'Native Landscape import failed'
    components = landscape.get_components_by_class(unreal.LandscapeComponent)
    collision = landscape.get_components_by_class(unreal.LandscapeHeightfieldCollisionComponent)
    assert len(components) == 16 and len(collision) == 16, (len(components), len(collision))
    assert not landscape.get_editor_property('bEnableNanite')

    sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(-50, -30, 0))
    sun.set_actor_label('Village_Daylight')
    light = sun.get_editor_property('light_component')
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_editor_property('intensity', 50000.0)
    light.set_editor_property('atmosphere_sun_light', True)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1500))
    sky.set_actor_label('Village_SkyFill')
    sky.get_editor_property('light_component').set_mobility(unreal.ComponentMobility.MOVABLE)
    actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    exposure = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    exposure.set_editor_property('unbound', True)
    settings = exposure.get_editor_property('settings')
    settings.set_editor_property('override_auto_exposure_method', True)
    settings.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM)
    settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
    settings.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
    settings.set_editor_property('override_auto_exposure_bias', True)
    settings.set_editor_property('auto_exposure_bias', 0.0)
    extended_exposure = unreal.SystemLibrary.get_console_variable_int_value('r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange') != 0
    settings.set_editor_property('override_auto_exposure_min_brightness', True)
    settings.set_editor_property('override_auto_exposure_max_brightness', True)
    settings.set_editor_property('auto_exposure_min_brightness', -10.0 if extended_exposure else .01)
    settings.set_editor_property('auto_exposure_max_brightness', 20.0 if extended_exposure else 100000.0)
    settings.set_editor_property('override_histogram_log_min', True)
    settings.set_editor_property('override_histogram_log_max', True)
    settings.set_editor_property('histogram_log_min', -10.0)
    settings.set_editor_property('histogram_log_max', 20.0)
    exposure.set_editor_property('settings', settings)
    start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(2900, -600, 120))
    start.set_actor_label('Village_PlayerStart')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode', unreal.TownAgeGameMode)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        unreal.Vector(0, 0, 33000), unreal.Rotator(-90, -90, 0))
    assert unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    assert levels.save_current_level()
    origin, extent = landscape.get_actor_bounds(False)
    report = {'map': MAP, 'landscape': landscape.get_path_name(), 'type': 'native Landscape',
              'grid': [253, 253], 'xy_scale_cm': 100, 'z_scale': 100,
              'render_components': len(components), 'collision_components': len(collision),
              'sections_per_component': 1, 'section_quads': 63,
              'bounds_origin_cm': [origin.x, origin.y, origin.z], 'bounds_extent_cm': [extent.x, extent.y, extent.z],
              'world_partition': False, 'nanite': False, 'material': material.get_path_name(),
              'surface_texture_sizes': {'grass': [128, 128], 'paving': [512, 512]},
              'ground_layers': list(LAYERS), 'source_metrics': metadata,
              'existing_maps_or_defaults_modified': False, 'physical_mobile_device_tested': False,
              'requires_gpu_finalization': True}
    output = ROOT / 'Saved/Terrain/Village01'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'creation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('VILLAGE_LANDSCAPE_CREATED', json.dumps(report))


def finalize_level(unreal):
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.load_level(MAP)
    landscapes = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                  if isinstance(a, unreal.Landscape)]
    assert len(landscapes) == 1
    allocations = unreal.TownAgeTerrainLibrary.finalize_village_landscape(landscapes[0])
    assert allocations > 0, 'GPU edit-layer finalization did not produce paint allocations'
    assert unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    assert levels.save_current_level()
    report = {'map': MAP, 'gpu_edit_layer_finalized': True, 'paint_allocations': allocations}
    (ROOT / 'Saved/Terrain/Village01/gpu_finalization_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('VILLAGE_GPU_FINALIZED', json.dumps(report))


if __name__ == '__main__':
    try:
        import unreal
    except ImportError:
        import argparse
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--textures-only', action='store_true', required=True)
        parser.parse_args()
        print({name: str(path) for name, path in generate_surface_textures().items()})
    else:
        if '-VillageFinalize' in unreal.SystemLibrary.get_command_line():
            finalize_level(unreal)
        else:
            create_level(unreal)
