"""Import the bounded MainVillage Meshy delivery into isolated environment folders.

Run in a normal GPU editor with -ExecutePythonScript=<this file>.
Use -MainVillageBuildingV2 for the three replacement building candidates only.
Existing successful imports are resumed only when all source hashes match.
No maps, existing art, gameplay configuration, or provider jobs are changed.
"""
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Meshy/MainVillage'
REPORT = ROOT / 'Saved/MainVillage/Art/import_report.json'
CATEGORIES = {
    'Mart': 'Architecture', 'GreenHouse': 'Architecture', 'Salon': 'Architecture',
    'Tree': 'Nature', 'Shrub': 'Nature', 'Flowers': 'Nature', 'Rock': 'Nature',
    'Bench': 'Streetscape', 'Lamp': 'Streetscape', 'Fence': 'Streetscape',
    'Bridge': 'Streetscape', 'Planter': 'Streetscape',
}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_sources(name, version='v001'):
    directory = SOURCE / name / version
    mesh = directory / 'model.fbx'
    if not mesh.is_file() or mesh.stat().st_size == 0:
        raise ValueError('Missing or empty FBX: ' + str(mesh))
    textures = {}
    for path in sorted(directory.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        # FBX importer extracts embedded copies here; source textures are authoritative.
        if any(part.lower().endswith('.fbm') for part in path.relative_to(directory).parts):
            continue
        stem = path.stem.lower().replace('-', '_')
        channel = None
        if 'base_color' in stem or 'basecolor' in stem or 'albedo' in stem:
            channel = 'basecolor'
        elif 'roughness' in stem:
            channel = 'roughness'
        elif 'metallic' in stem:
            channel = 'metallic'
        elif 'normal' in stem:
            channel = 'normal'
        elif stem in ('texture', 'texture_0', 'model_texture', 'model_texture_0'):
            channel = 'basecolor'
        if channel:
            if channel in textures:
                raise ValueError(f'{name}: ambiguous {channel} textures; expected a single atlas')
            textures[channel] = path
    if 'basecolor' not in textures:
        raise ValueError(name + ': no base-color texture found in ' + str(directory))
    convention_file = directory / 'normal_convention.json'
    convention = None
    if convention_file.exists():
        data = json.loads(convention_file.read_text(encoding='utf-8-sig'))
        convention = data.get('convention')
        if convention not in ('OpenGL', 'DirectX') or not data.get('evidence'):
            raise ValueError('Normal convention requires OpenGL/DirectX and evidence')
    files = [mesh, *textures.values()]
    if convention_file.exists():
        files.append(convention_file)
    hashes = {str(path.relative_to(directory)): sha256(path) for path in files}
    return mesh, textures, hashes, convention


def save_report(report):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    temporary.replace(REPORT)


def import_asset(unreal, name, category, mesh_source, textures, hashes, convention, repair=False,
                 version='v001'):
    assets = unreal.EditorAssetLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    edit = unreal.MaterialEditingLibrary
    meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    folder = f'/Game/Environment/MainVillage/{category}/{name}/{version}'
    if assets.list_assets(folder, recursive=True, include_folder=False) and not repair:
        raise ValueError('Destination is populated; refusing overwrite: ' + folder)
    assets.make_directory(folder)

    def import_file(path, asset_name, options=None):
        if repair:
            existing = assets.load_asset(folder + '/' + asset_name)
            if not existing:
                raise RuntimeError('Partial repair requires existing asset: ' + asset_name)
            return existing
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = folder
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = False
        task.save = True
        if options is not None:
            task.factory = unreal.FbxFactory()
            task.options = options
        tools.import_asset_tasks([task])
        result = assets.load_asset(folder + '/' + asset_name)
        if not result:
            raise RuntimeError('Asset import failed: ' + str(path))
        return result

    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    recompute_geometry_normals = version == 'v002'
    options.static_mesh_import_data.normal_import_method = (
        unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS if recompute_geometry_normals
        else unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    mesh = import_file(mesh_source, 'SM_' + name, options)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(name + ': FBX did not import as a StaticMesh')
    slots = mesh.get_editor_property('static_materials')
    if len(slots) != 1:
        raise RuntimeError(f'{name}: expected one texture atlas/material slot, received {len(slots)}; partial import retained')
    bounds = mesh.get_bounds()
    dimensions = [float(getattr(bounds.box_extent, axis)) * 2 for axis in 'xyz']
    if any(not math.isfinite(value) or value <= .001 for value in dimensions):
        raise RuntimeError(name + ': invalid mesh bounds')

    material = (assets.load_asset(folder + '/M_' + name) if repair else
                tools.create_asset('M_' + name, folder, unreal.Material, unreal.MaterialFactoryNew()))
    if not material:
        raise RuntimeError(name + ': expected saved material is missing')
    material.set_editor_property('two_sided', category == 'Architecture' and version == 'v001')
    material.set_editor_property('used_with_instanced_static_meshes', True)
    properties = {'basecolor': unreal.MaterialProperty.MP_BASE_COLOR,
                  'roughness': unreal.MaterialProperty.MP_ROUGHNESS,
                  'metallic': unreal.MaterialProperty.MP_METALLIC,
                  'normal': unreal.MaterialProperty.MP_NORMAL}
    imported_textures = {}
    warnings = []
    for channel, path in textures.items():
        if channel == 'normal' and convention is None:
            warnings.append('Normal atlas retained locally but omitted: convention has not been verified')
            continue
        texture = import_file(path, 'T_' + name + '_' + channel)
        texture.set_editor_property('srgb', channel == 'basecolor')
        texture.set_editor_property('max_texture_size', 2048)
        if channel == 'normal':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', convention == 'OpenGL')
        assert assets.save_loaded_asset(texture, False)
        if not repair:
            node = edit.create_material_expression(material, unreal.MaterialExpressionTextureSample)
            node.texture = texture
            node.sampler_type = (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == 'normal'
                                 else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == 'basecolor'
                                 else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            output = 'RGB' if channel in ('normal', 'basecolor') else 'R'
            assert edit.connect_material_property(node, output, properties[channel])
        imported_textures[channel] = texture.get_path_name()
    if 'roughness' not in imported_textures and not repair:
        constant = edit.create_material_expression(material, unreal.MaterialExpressionConstant)
        constant.r = .8
        assert edit.connect_material_property(constant, '', unreal.MaterialProperty.MP_ROUGHNESS)
    edit.recompile_material(material)
    assert assets.save_loaded_asset(material, False)
    mesh.set_material(0, material)
    assert assets.save_loaded_asset(mesh, False)

    # All assets are static. Foliage is deliberately nonblocking; assembly controls actors.
    collision = 'none'
    if name == 'Bridge':
        mesh.get_editor_property('body_setup').set_editor_property(
            'collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        collision = 'complex_as_simple_static_bridge'
    elif name not in ('Tree', 'Shrub', 'Flowers'):
        if meshes.get_simple_collision_count(mesh) == 0:
            collision_index = meshes.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
            if collision_index < 0:
                raise RuntimeError(name + ': box collision generation failed')
        collision = 'box'
    reduction = unreal.StaticMeshReductionOptions()
    if recompute_geometry_normals:
        build = meshes.get_lod_build_settings(mesh, 0)
        build.set_editor_property('recompute_normals', True)
        build.set_editor_property('recompute_tangents', True)
        build.set_editor_property('use_mikk_t_space', True)
        build.set_editor_property('compute_weighted_normals', True)
        meshes.set_lod_build_settings(mesh, 0, build)
    reduction.auto_compute_lod_screen_size = False
    reduction.reduction_settings = [
        unreal.StaticMeshReductionSettings(percent_triangles=1., screen_size=1.),
        unreal.StaticMeshReductionSettings(percent_triangles=.5, screen_size=.4),
        unreal.StaticMeshReductionSettings(percent_triangles=.2, screen_size=.15),
    ]
    if meshes.set_lods(mesh, reduction) < 0 or meshes.get_lod_count(mesh) < 3:
        raise RuntimeError(name + ': failed to generate three LODs')
    assert assets.save_loaded_asset(mesh, False)
    assert assets.save_directory(folder, only_if_is_dirty=False, recursive=True)
    return {
        'status': 'imported', 'name': name, 'version': version, 'mesh': mesh.get_path_name(),
        'folder': folder, 'source_hashes': hashes, 'dimensions_cm': dimensions,
        'bounds_origin': [float(getattr(bounds.origin, axis)) for axis in 'xyz'],
        'material_slots': [str(slot.material_slot_name) for slot in slots],
        'material': material.get_path_name(), 'textures': imported_textures,
        'normal_convention': convention, 'texture_max_size': 2048,
        'triangles_by_lod': [mesh.get_num_triangles(index) for index in range(meshes.get_lod_count(mesh))],
        'collision': collision, 'simple_collision_count': meshes.get_simple_collision_count(mesh),
        'recomputed_geometry_normals_tangents': recompute_geometry_normals,
        'warnings': warnings + (['Two-sided building material masks observed backface patches; geometry still needs visual review'] if category == 'Architecture' and version == 'v001' else []),
        'physical_mobile_verified': False,
    }


def main():
    global REPORT
    import unreal
    command_line = unreal.SystemLibrary.get_command_line()
    building_v2 = unreal.SystemLibrary.parse_param(command_line, 'MainVillageBuildingV2')
    version = 'v002' if building_v2 else 'v001'
    categories = {name: category for name, category in CATEGORIES.items()
                  if not building_v2 or category == 'Architecture'}
    if building_v2:
        REPORT = REPORT.with_name('import_report_v002.json')
    if not unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem):
        raise RuntimeError('StaticMeshEditorSubsystem requires normal editor: use -ExecutePythonScript, not -run=pythonscript')
    previous = json.loads(REPORT.read_text(encoding='utf-8-sig')) if REPORT.exists() else {}
    repair = unreal.SystemLibrary.parse_param(command_line, 'MainVillageRepairPartial')
    if repair and building_v2:
        raise ValueError('Building v002 cannot use the v001 partial repair journal')
    repair_names = set()
    if repair:
        journal_path = REPORT.parent / 'partial_repair_journal.json'
        if not journal_path.exists():
            raise RuntimeError('Missing reviewed partial repair journal: ' + str(journal_path))
        journal = json.loads(journal_path.read_text(encoding='utf-8-sig'))
        provenance = REPORT.parent / 'initial_import.log'
        if sha256(provenance) != journal['provenance_sha256']:
            raise RuntimeError('Original import provenance changed')
        for name, entry in journal['assets'].items():
            if name not in CATEGORIES:
                raise RuntimeError('Unexpected asset in repair journal: ' + name)
            if discover_sources(name)[2] != entry['source_hashes']:
                raise RuntimeError('Source changed since repair review: ' + name)
            prior = previous.get('assets', {}).get(name, {})
            if prior.get('status') != 'imported':
                for relative, digest in entry['package_hashes'].items():
                    if sha256(ROOT / relative) != digest:
                        raise RuntimeError('Partial package changed since review: ' + relative)
                repair_names.add(name)
    report = {'status': 'running', 'assets': previous.get('assets', {}), 'errors': {}}
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
    for name, category in categories.items():
        try:
            mesh, textures, hashes, convention = discover_sources(name, version)
            prior = report['assets'].get(name, {})
            if prior.get('status') == 'imported' and prior.get('source_hashes') == hashes:
                if unreal.EditorAssetLibrary.does_asset_exist(prior['mesh']):
                    continue
                raise RuntimeError(name + ': successful report exists but mesh package is missing')
            report['assets'][name] = import_asset(unreal, name, category, mesh, textures, hashes, convention,
                                                  repair=name in repair_names, version=version)
        except Exception as error:
            report['errors'][name] = str(error)
            unreal.log_error(f'MainVillage import {name}: {error}')
        save_report(report)
    report['status'] = 'failed' if report['errors'] else 'complete'
    save_report(report)
    if report['errors']:
        raise RuntimeError('MainVillage imports incomplete; inspect ' + str(REPORT))
    print('MAIN_VILLAGE_ART_IMPORTED ' + str(REPORT))


if __name__ == '__main__':
    try:
        main()
    finally:
        import unreal
        if unreal.SystemLibrary.parse_param(unreal.SystemLibrary.get_command_line(), 'MainVillageQuitAfterImport'):
            unreal.SystemLibrary.quit_editor()
