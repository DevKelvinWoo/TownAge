"""Validate a local Meshy delivery or import an isolated Unreal candidate.

Offline: python import_meshy_unreal.py --validate manifest.json
Unreal: -run=pythonscript -script=<this file> -MeshyManifest="<manifest.json>"
No generation API, production replacement, animation import or map save occurs.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

NAMESPACE = '/Game/Characters/Meshy'
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_]*\Z')
CHANNELS = {'basecolor', 'normal', 'roughness'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.tga', '.bmp', '.exr', '.tif', '.tiff'}


def validate_manifest(filename):
    """Resolve local inputs before Unreal performs any asset mutation."""
    manifest_path = Path(filename).resolve(strict=True)
    data = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('Manifest must be a JSON object')
    allowed = {'asset_name', 'fbx_path', 'asset_type', 'target_height_cm', 'textures',
               'normal_convention', 'destination', 'candidate_version', 'create_placement_blueprint'}
    if set(data) - allowed:
        raise ValueError('Unknown manifest fields: ' + ', '.join(sorted(set(data) - allowed)))
    for key in ('asset_name', 'asset_type', 'fbx_path'):
        if not isinstance(data.get(key), str) or not data[key]:
            raise ValueError(key + ' must be a nonempty string')
    if not IDENTIFIER.fullmatch(data['asset_name']):
        raise ValueError('asset_name must begin with a letter and contain only letters, digits or underscores')
    if data['asset_type'] not in ('skeletal', 'static'):
        raise ValueError('asset_type must be skeletal or static')
    version = data.get('candidate_version', 'candidate_v001')
    if not isinstance(version, str) or not IDENTIFIER.fullmatch(version):
        raise ValueError('candidate_version must be a safe identifier beginning with a letter')
    destination = data.get('destination', NAMESPACE + '/' + data['asset_name'])
    if (not isinstance(destination, str) or not destination.startswith(NAMESPACE + '/')
            or any(not IDENTIFIER.fullmatch(part) for part in destination[len(NAMESPACE) + 1:].split('/'))):
        raise ValueError('destination must be a package folder below ' + NAMESPACE)
    height = data.get('target_height_cm', 170.0)
    if isinstance(height, bool) or not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0:
        raise ValueError('target_height_cm must be a finite positive number')
    convention = data.get('normal_convention', 'DirectX')
    if convention not in ('DirectX', 'OpenGL'):
        raise ValueError('normal_convention must be DirectX or OpenGL')
    create_bp = data.get('create_placement_blueprint', False)
    if not isinstance(create_bp, bool):
        raise ValueError('create_placement_blueprint must be a boolean')

    def local_file(value, suffixes, label):
        if not isinstance(value, str) or not value or '://' in value:
            raise ValueError(label + ' must be a local file path')
        path = Path(value)
        if not path.is_absolute():
            path = manifest_path.parent / path
        path = path.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() not in suffixes:
            raise ValueError(label + ' has an unsupported file type')
        return str(path)

    textures = data.get('textures', {})
    if not isinstance(textures, dict) or set(textures) - CHANNELS:
        raise ValueError('textures must map only basecolor, normal and roughness to local images')
    result = dict(data)
    result.update(asset_name=data['asset_name'], candidate_version=version, destination=destination,
                  candidate_folder=destination + '/' + version, target_height_cm=float(height),
                  normal_convention=convention, create_placement_blueprint=create_bp,
                  fbx_path=local_file(data['fbx_path'], {'.fbx'}, 'fbx_path'),
                  textures={key: local_file(value, IMAGE_SUFFIXES, 'textures.' + key) for key, value in textures.items()})
    return result


def ensure_empty_candidate(existing_assets):
    if existing_assets:
        raise ValueError('Candidate already contains assets; choose a new candidate_version. No assets were overwritten.')


def validate_material_slots(slot_names, has_textures):
    if len(slot_names) > 1:
        raise ValueError('Multiple material slots are unsupported by this single-atlas importer; prepare a shared-atlas FBX or a separate per-material import workflow')
    if not slot_names and has_textures:
        raise ValueError('Textured FBX has no material slot for the supplied atlas')


def import_candidate(manifest, unreal):
    folder = manifest['candidate_folder']
    ensure_empty_candidate(unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    # FbxImportUI belongs to the legacy pipeline; Interchange has different options.
    unreal.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    unreal.EditorAssetLibrary.make_directory(folder)

    def import_file(filename, name, options=None):
        task = unreal.AssetImportTask()
        task.filename = filename
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = False
        task.save = True
        if options:
            task.factory = unreal.FbxFactory()
            task.options = options
        tools.import_asset_tasks([task])
        asset = unreal.load_asset(folder + '/' + name)
        if not asset:
            raise RuntimeError('Import failed: ' + filename)
        return asset

    skeletal = manifest['asset_type'] == 'skeletal'
    name = ('SK_' if skeletal else 'SM_') + manifest['asset_name']
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = skeletal
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    if skeletal:
        options.create_physics_asset = True
        options.skeletal_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    else:
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = import_file(manifest['fbx_path'], name, options)
    expected_class = unreal.SkeletalMesh if skeletal else unreal.StaticMesh
    if not isinstance(mesh, expected_class):
        raise RuntimeError('FBX did not produce the requested mesh type')
    slots = mesh.get_editor_property('materials' if skeletal else 'static_materials')
    slot_names = [str(slot.material_slot_name) for slot in slots]
    validate_material_slots(slot_names, bool(manifest['textures']))
    dependencies = {}
    if skeletal:
        skeleton = mesh.get_editor_property('skeleton')
        if not skeleton or not unreal.EditorAssetLibrary.save_loaded_asset(skeleton, False):
            raise RuntimeError('Skeleton dependency could not be saved')
        physics = mesh.get_editor_property('physics_asset')
        if not physics:
            physics = unreal.get_default_object(unreal.PhysicsAssetToolset).call_method('CreateFromMesh', (folder + '/' + name, True))
        if not physics or not unreal.EditorAssetLibrary.save_loaded_asset(physics, False):
            raise RuntimeError('Physics dependency could not be saved')
        dependencies = {'skeleton': skeleton.get_path_name(), 'physics_asset': physics.get_path_name()}

    height = mesh.get_bounds().box_extent.z * 2
    if not math.isfinite(height) or height <= .001:
        raise RuntimeError('Mesh has no usable Z height; verify axes and geometry')
    scale = manifest['target_height_cm'] / height
    material = tools.create_asset('M_' + manifest['asset_name'], folder, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('two_sided', False)
    properties = {'basecolor': unreal.MaterialProperty.MP_BASE_COLOR,
                  'normal': unreal.MaterialProperty.MP_NORMAL, 'roughness': unreal.MaterialProperty.MP_ROUGHNESS}
    samplers = {'basecolor': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                'normal': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, 'roughness': unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR}
    imported_textures = {}
    for channel, filename in manifest['textures'].items():
        texture = import_file(filename, 'T_' + manifest['asset_name'] + '_' + channel)
        texture.set_editor_property('srgb', channel == 'basecolor')
        if channel == 'normal':
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property('flip_green_channel', manifest['normal_convention'] == 'OpenGL')
        unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
        node = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureSample)
        node.texture = texture
        node.sampler_type = samplers[channel]
        if not unreal.MaterialEditingLibrary.connect_material_property(node, 'R' if channel == 'roughness' else 'RGB', properties[channel]):
            raise RuntimeError('Texture could not be connected: ' + channel)
        imported_textures[channel] = texture.get_path_name()
    if 'roughness' not in imported_textures:
        roughness = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
        roughness.r = .8
        unreal.MaterialEditingLibrary.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    # The manifest supports one atlas and rejects multiple source material slots.
    if skeletal:
        for index, slot in enumerate(slots):
            slot.material_interface = material
            slots[index] = slot
        mesh.set_editor_property('materials', slots)
    else:
        for index in range(len(slot_names)):
            mesh.set_material(index, material)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)

    blueprint_path = None
    if manifest['create_placement_blueprint']:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.Actor)
        blueprint = tools.create_asset('BP_' + manifest['asset_name'], folder, unreal.Blueprint, factory)
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
        params = unreal.AddNewSubobjectParams(parent_handle=handles[0],
            new_class=unreal.SkeletalMeshComponent if skeletal else unreal.StaticMeshComponent, blueprint_context=blueprint)
        handle, failure = subsystem.add_new_subobject(params)
        if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
            raise RuntimeError('Candidate Blueprint component failed: ' + str(failure))
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        component = unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data, blueprint)
        if skeletal:
            component.set_skeletal_mesh_asset(mesh)
        else:
            component.set_static_mesh(mesh)
        component.set_editor_property('relative_scale3d', unreal.Vector(scale, scale, scale))
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
        blueprint_path = blueprint.get_path_name()
    if not unreal.EditorAssetLibrary.save_directory(folder, only_if_is_dirty=False, recursive=True):
        raise RuntimeError('Candidate packages could not all be saved')
    return {'status': 'imported_candidate', 'source_fbx': manifest['fbx_path'], 'candidate_folder': folder,
            'mesh': mesh.get_path_name(), **dependencies,
            'asset_type': manifest['asset_type'], 'native_height_cm': height,
            'target_height_cm': manifest['target_height_cm'], 'placement_uniform_scale': scale,
            'placement_blueprint': blueprint_path, 'material': material.get_path_name(),
            'material_slots': slot_names, 'textures': imported_textures,
            'normal_convention': manifest['normal_convention'], 'animations_imported': False,
            'material_support': 'single_atlas_only',
            'production_replaced': False, 'review_required': ['visual quality', 'skeleton and animation compatibility', 'PC/mobile performance']}


def unreal_manifest_argument(command_line):
    match = re.search(r'(?:^|\s)-MeshyManifest=(?:"([^"]+)"|([^\s]+))', command_line, re.IGNORECASE)
    if not match:
        raise ValueError('Pass -MeshyManifest="<local manifest.json>"')
    return match.group(1) or match.group(2)


def main():
    try:
        import unreal
    except ImportError:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--validate', required=True, metavar='MANIFEST')
        args = parser.parse_args()
        print(json.dumps(validate_manifest(args.validate), indent=2))
        return
    filename = unreal_manifest_argument(unreal.SystemLibrary.get_command_line())
    manifest = validate_manifest(filename)
    root = Path(unreal.Paths.project_saved_dir()) / 'Meshy' / manifest['asset_name'] / manifest['candidate_version']
    root.mkdir(parents=True, exist_ok=True)
    try:
        report = import_candidate(manifest, unreal)
    except Exception as error:
        # Partial candidates remain isolated for inspection; never delete or retry over them.
        (root / 'last_failed_attempt.json').write_text(json.dumps({'status': 'failed', 'error': str(error), 'candidate_folder': manifest['candidate_folder']}, indent=2), encoding='utf-8')
        raise
    (root / 'import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('MESHY_CANDIDATE_IMPORTED', json.dumps(report))


if __name__ == '__main__':
    main()
