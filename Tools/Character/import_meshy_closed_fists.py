"""Import fitted Meshy fists on the existing TownKeeper rig and materials."""

import json
import math
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Saved/Meshy/TownKeeper_ClosedFists/fitted_v003'
DEST = '/Game/Characters/Meshy/TownKeeper_ClosedFists/candidate_v003'
ORIGINALS = {
    'TownKeeper': '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy',
    'PinkDress': '/Game/Characters/Clothing/PinkDress/SK_PinkDress',
    'YellowOveralls': '/Game/Characters/Clothing/YellowOveralls/SK_YellowOveralls',
}
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
base = assets.load_asset(ORIGINALS['TownKeeper'])
assert base
skeleton = base.get_editor_property('skeleton')
face = assets.load_asset('/Game/Characters/Customization/M_TownKeeper_Makeup')
assert skeleton and face


def bones(mesh):
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    comp.set_skeletal_mesh_asset(mesh)
    return {str(comp.get_bone_name(i)): (str(comp.get_parent_bone(comp.get_bone_name(i))),
                                         comp.get_ref_pose_transform(i))
            for i in range(comp.get_num_bones())}


def validate_bones(mesh):
    original, incoming = bones(base), bones(mesh)
    assert original.keys() == incoming.keys()
    for key, (parent, a) in original.items():
        other, b = incoming[key]
        assert parent == other
        assert (a.translation - b.translation).length() < .1, key
        assert (a.scale3d - b.scale3d).length() < .005, key
        p, q = a.rotation, b.rotation
        dot = abs(p.x*q.x + p.y*q.y + p.z*q.z + p.w*q.w)
        assert math.degrees(2 * math.acos(min(1., dot))) < .2, key


def import_mesh(name, folder, target_skeleton=None):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_mesh = True
    options.import_as_skeletal = True
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    if target_skeleton:
        options.skeleton = target_skeleton
        options.physics_asset = base.get_editor_property('physics_asset')
    data = options.skeletal_mesh_import_data
    data.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('update_skeleton_reference_pose', False)
    task = unreal.AssetImportTask()
    task.filename = str(SOURCE / (name + '.fbx'))
    task.destination_path = folder
    task.destination_name = name
    task.factory = unreal.FbxFactory()
    task.options = options
    task.automated = True
    task.save = False
    tools.import_asset_tasks([task])
    result = assets.load_asset(folder + '/' + name)
    assert isinstance(result, unreal.SkeletalMesh), name
    return result


assert not assets.does_directory_exist(DEST) or not assets.list_assets(DEST), DEST
for name in ORIGINALS:
    filename = f'SK_{name}_ClosedFists'
    assert (SOURCE / (filename + '.fbx')).is_file()
    validate_bones(import_mesh(filename, '/Game/Developers/ClosedFistImportProbe'))

results = {}
for name, original_path in ORIGINALS.items():
    filename = f'SK_{name}_ClosedFists'
    original = assets.load_asset(original_path)
    assert original and original.get_editor_property('skeleton') == skeleton
    mesh = import_mesh(filename, DEST, skeleton)
    assert mesh.get_editor_property('skeleton') == skeleton
    slots = mesh.get_editor_property('materials')
    old_slots = original.get_editor_property('materials')
    assert [str(s.material_slot_name) for s in slots] == [str(s.material_slot_name) for s in old_slots]
    assert abs(mesh.get_bounds().box_extent.z - original.get_bounds().box_extent.z) < .5
    for index, old in enumerate(old_slots):
        slot = slots[index]
        slot.material_interface = face if index == 0 else old.material_interface
        slots[index] = slot
    mesh.set_editor_property('materials', slots)
    assert assets.save_loaded_asset(mesh, False)
    results[name] = mesh.get_path_name()
(SOURCE / 'unreal_import.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('CLOSED_FISTS_IMPORTED', json.dumps(results))
