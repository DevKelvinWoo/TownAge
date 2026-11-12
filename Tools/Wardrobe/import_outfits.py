"""Import the fitted two-material outfits against the existing TownKeeper skeleton."""

import json
import math
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
FITTED = ROOT / 'Saved/Wardrobe/Fitted'
BASE = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy'
CLOTHING = '/Game/Characters/Clothing'
OUTFITS = ('PinkDress', 'YellowOveralls')

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
base = assets.load_asset(BASE)
face = assets.load_asset('/Game/Characters/Customization/M_TownKeeper_Makeup')
assert base and face
skeleton = base.get_editor_property('skeleton')
assert skeleton


def reference_bones(mesh):
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(mesh)
    bones = {}
    for index in range(component.get_num_bones()):
        name = component.get_bone_name(index)
        bones[str(name)] = (str(component.get_parent_bone(name)),
                            component.get_ref_pose_transform(index))
    return bones


def verify_rig(mesh):
    original = reference_bones(base)
    fitted = reference_bones(mesh)
    assert original.keys() == fitted.keys(), (original.keys(), fitted.keys())
    differences = []
    for name, (parent, pose) in original.items():
        new_parent, other = fitted[name]
        assert parent == new_parent, (name, parent, new_parent)
        distance = (pose.translation - other.translation).length()
        scale_delta = (pose.scale3d - other.scale3d).length()
        q, r = pose.rotation, other.rotation
        dot = abs(q.x * r.x + q.y * r.y + q.z * r.z + q.w * r.w)
        angle = math.degrees(2 * math.acos(min(1, dot)))
        if distance > .1 or scale_delta > .005 or angle > .2:
            differences.append((name, round(distance, 4), round(scale_delta, 4), round(angle, 4)))
    assert not differences, differences


def import_file(path, folder, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options:
        task.factory = unreal.FbxFactory()
        task.options = options
    tools.import_asset_tasks([task])
    asset = assets.load_asset(folder + '/' + name)
    assert asset, f'Import did not produce {folder}/{name}'
    return asset


def import_outfit(name):
    folder = CLOTHING + '/' + name
    source = FITTED / name
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.physics_asset = base.get_editor_property('physics_asset')
    data = options.skeletal_mesh_import_data
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('update_skeleton_reference_pose', False)

    fbx = source / f'SK_{name}.fbx'
    probe = import_file(fbx, '/Game/Developers/WardrobeImportProbe', f'SK_{name}', options)
    assert isinstance(probe, unreal.SkeletalMesh)
    verify_rig(probe)

    options.skeleton = skeleton
    mesh = import_file(fbx, folder, f'SK_{name}', options)
    assert isinstance(mesh, unreal.SkeletalMesh)
    assert mesh.get_editor_property('skeleton') == skeleton
    height = mesh.get_bounds().box_extent.z * 2
    assert abs(height - base.get_bounds().box_extent.z * 2) < 1., height
    assert (mesh.get_bounds().origin - base.get_bounds().origin).length() < 1.
    slots = mesh.get_editor_property('materials')
    names = [str(slot.material_slot_name) for slot in slots]
    assert names == ['Material_0', 'OutfitFabric'], names

    texture = import_file(source / f'T_{name}_BaseColor.png', folder, f'T_{name}_BaseColor')
    assert isinstance(texture, unreal.Texture2D)
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
    material = tools.create_asset(f'M_{name}', folder, unreal.Material, unreal.MaterialFactoryNew())
    assert material
    material.set_editor_property('two_sided', True)
    material.set_editor_property('used_with_skeletal_mesh', True)
    edit = unreal.MaterialEditingLibrary
    color = edit.create_material_expression(material, unreal.MaterialExpressionTextureSample, -340, 0)
    color.texture = texture
    color.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_COLOR
    assert edit.connect_material_property(color, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = edit.create_material_expression(material, unreal.MaterialExpressionConstant, -320, 260)
    rough.r = .85
    assert edit.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    edit.recompile_material(material)
    for index, parent in enumerate((face, material)):
        slot = slots[index]
        slot.material_interface = parent
        slots[index] = slot
    mesh.set_editor_property('materials', slots)
    for asset in (texture, material, mesh):
        assert assets.save_loaded_asset(asset, False), asset.get_path_name()
    return {'mesh': mesh.get_path_name(), 'height_cm': height, 'materials': names,
            'skeleton': skeleton.get_path_name(), 'texture': texture.get_path_name()}


for outfit in OUTFITS:
    assert (FITTED / outfit / f'SK_{outfit}.fbx').is_file()
    assert (FITTED / outfit / f'T_{outfit}_BaseColor.png').is_file()
    folder = f'{CLOTHING}/{outfit}'
    assert not assets.does_directory_exist(folder) or not assets.list_assets(folder), folder

report = {outfit: import_outfit(outfit) for outfit in OUTFITS}
(FITTED / 'unreal_import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('WARDROBE_OUTFITS_IMPORTED', json.dumps(report))
