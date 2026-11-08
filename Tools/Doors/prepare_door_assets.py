"""Bake the approved door actions, preserving the Meshy skeleton and skin.

Run in Blender background mode. Outputs are isolated from approved drafts and
existing production assets; the FBX mesh is a bind carrier for animation-only
Unreal import, not a replacement skeletal mesh.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
CHARACTER = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy'
DRAFT = CHARACTER / 'Animations/DoorDraft01'
OUT = CHARACTER / 'Animations/Door01'
LEAF_OUT = ROOT / 'ArtSource/Meshy/CozyHouse01/candidate_v003'
IDLE = CHARACTER / 'Animations/Idle01/TownKeeper_Meshy_Idle_Calm.fbx'
FPS = 30
START, END = 1, 108
BLEND_FRAMES = 6  # 0.2 seconds at the authored rate.
EXPECTED_NAMES = json.loads((CHARACTER / 'candidate_v001/rig_inspection.json').read_text())['armatures'][0]['bones']


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose(arm):
    return {bone.name: tuple(value.copy() for value in bone.matrix_basis.decompose())
            for bone in arm.pose.bones}


def rest(arm):
    return {bone.name: bone.matrix_local.copy() for bone in arm.data.bones}


def matrix_error(a, b):
    return max(abs(a[row][column] - b[row][column]) for row in range(4) for column in range(4))


def smooth(value):
    t = max(0., min(1., value))
    return t * t * (3. - 2. * t)


def bones_world(arm):
    return {bone.name: arm.matrix_world @ bone.head for bone in arm.pose.bones}


def assign_pose(arm, values):
    for bone in arm.pose.bones:
        location, rotation, scale = values[bone.name]
        bone.rotation_mode = 'QUATERNION'
        bone.location = location
        bone.rotation_quaternion = rotation
        bone.scale = scale


def selected(objects, active):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def idle_reference():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(IDLE))
    arm = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    bpy.context.scene.frame_set(int(arm.animation_data.action.frame_range[0]))
    assert [bone.name for bone in arm.data.bones] == EXPECTED_NAMES
    return pose(arm), rest(arm), arm.pose.bones['Hips'].matrix.translation.copy()


def prepare_motion(mode, idle, idle_rest, root_reference):
    source = DRAFT / f'{mode}_Review_Draft01.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    arm = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    carriers = [obj for obj in scene.objects if obj.type == 'MESH'
                and any(mod.type == 'ARMATURE' and mod.object == arm for mod in obj.modifiers)]
    assert arm.name == 'Armature' and len(carriers) == 1
    assert [bone.name for bone in arm.data.bones] == EXPECTED_NAMES
    rest_error = max(matrix_error(bone.matrix_local, idle_rest[bone.name]) for bone in arm.data.bones)
    assert rest_error < .0001, rest_error
    original_scale = arm.scale.copy()
    assert max(abs(value - .01) for value in original_scale) < .000001
    source_rest = rest(arm)
    source_skin = [(vertex.index, tuple((group.group, group.weight) for group in vertex.groups))
                   for vertex in carriers[0].data.vertices]
    cached = {}
    for frame in range(START, END + 1):
        scene.frame_set(frame)
        cached[frame] = pose(arm)

    arm.animation_data_clear()
    arm.animation_data_create()
    action_name = 'TownKeeper_Meshy_DoorPush' if mode == 'PushEnter' else 'TownKeeper_Meshy_DoorPull'
    action = bpy.data.actions.new(action_name)
    arm.animation_data.action = action
    arm.rotation_mode = 'XYZ'
    arm.location = (0, 0, 0)
    arm.rotation_euler = (0, 0, 0)
    arm.scale = original_scale
    scene.frame_start, scene.frame_end, scene.render.fps = START, END, FPS
    root_samples = []
    endpoint_errors = {}
    reference = {}
    for frame in range(START, END + 1):
        scene.frame_set(frame)
        weight = min(smooth((frame - START) / BLEND_FRAMES),
                     smooth((END - frame) / BLEND_FRAMES))
        values = {}
        for name in EXPECTED_NAMES:
            src_loc, src_rot, src_scale = cached[frame][name]
            idle_loc, idle_rot, idle_scale = idle[name]
            values[name] = (idle_loc.lerp(src_loc, weight),
                            idle_rot.slerp(src_rot, weight),
                            idle_scale.lerp(src_scale, weight))
        assign_pose(arm, values)
        bpy.context.view_layer.update()
        hips = arm.pose.bones['Hips']
        root_matrix = hips.matrix.copy()
        root_matrix.translation.x = root_reference.x
        root_matrix.translation.y = root_reference.y
        hips.matrix = root_matrix
        bpy.context.view_layer.update()
        for bone in arm.pose.bones:
            bone.keyframe_insert('location', frame=frame, group=bone.name)
            bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
            bone.keyframe_insert('scale', frame=frame, group=bone.name)
        root_samples.append(list(arm.matrix_world @ hips.head))
        reference[frame] = bones_world(arm)
        if frame in (START, END):
            endpoint_errors[str(frame)] = {
                'local_rotation_radians': max(bone.rotation_quaternion.rotation_difference(idle[bone.name][1]).angle
                                              for bone in arm.pose.bones),
                'local_location_units': max((bone.location - idle[bone.name][0]).length
                                            for bone in arm.pose.bones),
            }
    assert max(matrix_error(bone.matrix_local, source_rest[bone.name]) for bone in arm.data.bones) == 0
    assert source_skin == [(vertex.index, tuple((group.group, group.weight) for group in vertex.groups))
                           for vertex in carriers[0].data.vertices]
    root_xy_range_cm = [100 * (max(value[i] for value in root_samples) - min(value[i] for value in root_samples))
                        for i in range(2)]
    assert max(root_xy_range_cm) < .001, root_xy_range_cm
    assert all(error['local_rotation_radians'] < .001 and error['local_location_units'] < .001
               for error in endpoint_errors.values()), endpoint_errors
    scene.frame_set(START)
    # Keep only the character in the editable delivery; original reviews remain.
    keep = set(carriers + [arm])
    for obj in list(scene.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    selected(carriers + [arm], arm)
    filename = OUT / f'{action_name}.fbx'
    blend_file = OUT / f'{action_name}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
    bpy.ops.export_scene.fbx(
        filepath=str(filename), use_selection=True, object_types={'ARMATURE', 'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
        add_leaf_bones=False, armature_nodetype='NULL', bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0,
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(filename))
    round_scene = bpy.context.scene
    imported = next(obj for obj in round_scene.objects if obj.type == 'ARMATURE')
    assert [bone.name for bone in imported.data.bones] == EXPECTED_NAMES
    imported_action = imported.animation_data.action
    first, last = map(int, imported_action.frame_range)
    assert last - first == END - START, (first, last)
    roundtrip_error = 0.
    for frame, positions in reference.items():
        round_scene.frame_set(frame + first - START)
        points = bones_world(imported)
        roundtrip_error = max(roundtrip_error, max((points[name] - point).length for name, point in positions.items()))
    assert roundtrip_error < .0001, roundtrip_error
    mesh = next(obj for obj in round_scene.objects if obj.type == 'MESH')
    bpy.context.view_layer.update()
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
    height = max(point.z for point in points) - min(point.z for point in points)
    assert 1.5 < height < 1.9, height
    result = {
        'clip': action_name, 'mode': mode, 'fbx': str(filename), 'blend': str(blend_file),
        'source_draft': str(source), 'sha256': sha256(filename), 'bytes': filename.stat().st_size,
        'fps': FPS, 'frames': [START, END], 'sample_duration_seconds': (END-START) / FPS,
        'playback_duration_seconds': 3.6, 'endpoint_blend_seconds': BLEND_FRAMES / FPS,
        'endpoint_vs_calm_idle': endpoint_errors, 'root_xy_range_cm': root_xy_range_cm,
        'bone_count': len(EXPECTED_NAMES), 'bone_names': EXPECTED_NAMES,
        'rest_error_vs_calm_idle': rest_error, 'rest_or_skin_changed': False,
        'roundtrip_max_bone_error_m': roundtrip_error, 'roundtrip_mesh_height_m': height,
        'roundtrip_frames': [first, last], 'armature_scale': list(original_scale),
        'root_policy': 'Object root remains at zero; fixed Hips XY; gameplay controls capsule displacement.',
        'unreal_policy': 'Import animation-only onto retained TownKeeper_Meshy skeleton; do not import mesh/update reference pose.',
    }
    print('DOOR_ANIMATION_EXPORTED', action_name, roundtrip_error, flush=True)
    return result


def prepare_leaf():
    bpy.ops.wm.open_mainfile(filepath=str(DRAFT / 'PullExit_Review_Draft01.blend'))
    scene = bpy.context.scene
    scene.frame_set(1)
    door = bpy.data.objects['DoorLeaf']
    handle = bpy.data.objects['InsideHandle_Draft']
    assert door.type == handle.type == 'MESH'
    door.animation_data_clear()
    door.rotation_mode = 'XYZ'
    door.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    matrix = handle.matrix_world.copy()
    handle.parent = None
    handle.matrix_world = matrix
    selected([door, handle], door)
    bpy.ops.object.join()
    door.name = 'DoorLeaf'
    door.location = (0, 0, 0)
    door.rotation_euler = (0, 0, 0)
    selected([door], door)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    assert len(door.data.materials) == 1, len(door.data.materials)
    assert door.data.uv_layers.active is not None
    door.data.calc_loop_triangles()
    triangle_count = len(door.data.loop_triangles)
    assert 1030 < triangle_count < 2000, triangle_count
    for obj in list(scene.objects):
        if obj != door:
            bpy.data.objects.remove(obj, do_unlink=True)
    fbx = LEAF_OUT / 'DoorLeaf.fbx'
    blend = LEAF_OUT / 'DoorLeaf.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', apply_unit_scale=True, bake_anim=False)
    return {'fbx': str(fbx), 'blend': str(blend), 'sha256': sha256(fbx),
            'triangles': triangle_count, 'material_count': 1, 'uv_preserved': True,
            'pivot': 'Hinge-local origin (0,0,0)', 'includes_inside_handle': True,
            'previous_house_body_or_candidates_changed': False}


def prepare_frame():
    bpy.ops.wm.open_mainfile(filepath=str(DRAFT / 'PullExit_Review_Draft01.blend'))
    scene = bpy.context.scene
    scene.frame_set(1)
    frame = bpy.data.objects['DoorFrame_ReviewCutaway']
    assert frame.type == 'MESH'
    # The frame source has the house's original object transform. Bake it into
    # vertices, then express the complete arch relative to the leaf's hinge.
    hinge = Vector((1.685, -1.395, .01411533356))
    transform = Matrix.Translation(-hinge) @ frame.matrix_world
    frame.data.transform(transform)
    frame.matrix_world = Matrix.Identity(4)
    frame.name = 'DoorFrame'
    frame.hide_render = False
    frame.animation_data_clear()
    frame.data.calc_loop_triangles()
    triangles = len(frame.data.loop_triangles)
    assert triangles > 150
    assert len(frame.data.materials) == 1
    for obj in list(scene.objects):
        if obj != frame:
            bpy.data.objects.remove(obj, do_unlink=True)
    selected([frame], frame)
    fbx = LEAF_OUT / 'DoorFrame.fbx'
    blend = LEAF_OUT / 'DoorFrame.blend'
    assert not fbx.exists(), 'Door frame delivery already exists'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', apply_unit_scale=True, bake_anim=False)
    positions = [vertex.co for vertex in frame.data.vertices]
    lo = [min(point[i] for point in positions) for i in range(3)]
    hi = [max(point[i] for point in positions) for i in range(3)]
    result = {'fbx': str(fbx), 'blend': str(blend), 'sha256': sha256(fbx),
              'triangles': triangles, 'material_count': 1, 'uv_preserved': True,
              'pivot': 'Shared leaf hinge-local origin (0,0,0)',
              'bounds_min_cm': [value * 100 for value in lo],
              'bounds_max_cm': [value * 100 for value in hi],
              'source': 'Approved complete door-frame island; no house-body edits'}
    print('DOOR_FRAME_EXPORTED', json.dumps(result), flush=True)
    return result


def main():
    for path in (OUT, LEAF_OUT):
        path.mkdir(parents=True, exist_ok=True)
    if '--frame-only' in sys.argv:
        frame = prepare_frame()
        leaf_manifest = json.loads((LEAF_OUT / 'manifest.json').read_text(encoding='utf8'))
        leaf_manifest['frame'] = frame
        (LEAF_OUT / 'manifest.json').write_text(json.dumps(leaf_manifest, indent=2), encoding='utf8')
        manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf8'))
        manifest['door_frame'] = frame
        (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
        return
    # Do not overwrite deliveries produced by a prior successful run.
    assert not (OUT / 'manifest.json').exists(), 'Door01 delivery already exists'
    assert not (LEAF_OUT / 'DoorLeaf.fbx').exists(), 'Door candidate already exists'
    idle, idle_rest, root_reference = idle_reference()
    clips = [prepare_motion(mode, idle, idle_rest, root_reference) for mode in ('PushEnter', 'PullExit')]
    leaf = prepare_leaf()
    frame = prepare_frame()
    manifest = {'approval': 'User approved DoorDraft01 and requested smooth Idle transitions.',
                'provider_task': '01a1b907-edc0-7760-933e-9f845a9c05cb',
                'provider_actions': {'PushEnter': 288, 'PullExit': 285}, 'provider_credits': 6,
                'new_paid_generation': False, 'clips': clips, 'door_leaf': leaf, 'door_frame': frame,
                'timing_seconds': {'contact': [.38, .95], 'door_fully_open': 1.55,
                                   'step': [.40, 1.05], 'traverse': [1.65, 3.20], 'finish': 3.6},
                'step_cm': 22, 'traverse_cm': 134.85, 'door_inward_yaw_ue_degrees': 82,
                'unreal_imported': False}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    (LEAF_OUT / 'manifest.json').write_text(json.dumps({**leaf, 'frame': frame}, indent=2), encoding='utf8')
    print('DOOR_ASSET_DELIVERY_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
