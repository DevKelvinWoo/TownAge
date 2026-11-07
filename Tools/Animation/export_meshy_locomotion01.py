"""Deliver original Meshy cycles and static support pose, no mesh or skin edits.

Walk/run remain byte-identical provider files. FBX meshes carry bind poses only;
Unreal must import animations only against the existing candidate Skeleton.
"""
import bpy, json, math, shutil, hashlib
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'ArtSource/Meshy/TownKeeper_Meshy'
OUT=BASE/'Animations/Locomotion01'
OUT.mkdir(parents=True,exist_ok=True)
manifest={'skeleton_wrapper':'Armature','fps':30,'source_policy':'Original provider skin and actions; no experimental repairs','approval':'User explicitly requested Meshy main character and walking/running application','clips':{}}
for label,filename,speed in [('Walk','Provider_Walk.fbx',87),('Run','Provider_Run.fbx',304),('Standing',None,0)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=BASE/'Animations/LocomotionDraft01'/filename if filename else BASE/'candidate_v001/Rigged_Final.fbx'
    bpy.ops.import_scene.fbx(filepath=str(source))
    s=bpy.context.scene;s.render.fps=30;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    arm=next(o for o in s.objects if o.type=='ARMATURE')
    if filename:
        target=OUT/f'TownKeeper_Meshy_{label}.fbx'
        shutil.copyfile(source,target)
        start,end=map(int,arm.animation_data.action.frame_range)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest==hashlib.sha256(target.read_bytes()).hexdigest()
        manifest['clips'][label.lower()]={'path':str(target),'source':str(source),'sha256':digest,'frame_start':start,'frame_end':end,'duration_seconds':(end-start)/30,'speed_cm_s':speed,'bone_count':len(arm.data.bones),'delivery_policy':'Byte-identical original provider FBX; import animations only, mesh retained as original bind-pose carrier','root_policy':'Original in-place wrapper and cyclic Hips motion unchanged'}
        continue
    if label=='Standing':
        arm.animation_data_clear()
        for bone in arm.pose.bones:bone.matrix_basis.identity()
        for side,sign in [('Left',1),('Right',-1)]:
            bone=arm.pose.bones[side+'Arm'];rest=bone.bone.matrix_local.to_quaternion()
            current=(bone.bone.tail_local-bone.bone.head_local).normalized()
            desired=arm.matrix_world.to_quaternion().inverted() @ Vector((sign*.20,0,-.98)).normalized()
            delta=current.rotation_difference(desired)
            bone.rotation_mode='QUATERNION';bone.rotation_quaternion=rest.inverted() @ delta @ rest
        for frame in (1,2):
            for bone in arm.pose.bones:
                bone.keyframe_insert('location',frame=frame);bone.keyframe_insert('rotation_quaternion' if bone.rotation_mode=='QUATERNION' else 'rotation_euler',frame=frame);bone.keyframe_insert('scale',frame=frame)
        start,end=1,2
    else:start,end=map(int,arm.animation_data.action.frame_range)
    arm.animation_data.action.name='TownKeeper_Meshy_'+label
    s.frame_start=start;s.frame_end=end;s.frame_set(start)
    motion_samples={}
    for frame in (start,(start+end)//2,end):
        s.frame_set(frame)
        motion_samples[frame]={b.name:list(arm.matrix_world@b.head) for b in arm.pose.bones}
    s.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);bpy.context.view_layer.objects.active=arm
    for obj in s.objects:
        if obj.type=='MESH':obj.select_set(True)
    target=OUT/f'TownKeeper_Meshy_{label}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(target),use_selection=True,object_types={'ARMATURE','MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,armature_nodetype='NULL',use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    names=[b.name for b in arm.data.bones];parents={b.name:b.parent.name if b.parent else None for b in arm.data.bones}
    expected={b.name:list(arm.matrix_world@b.head_local) for b in arm.data.bones}
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(target))
    check=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    assert names==[b.name for b in check.data.bones]
    assert parents=={b.name:b.parent.name if b.parent else None for b in check.data.bones}
    error=max((Vector(expected[b.name])-(check.matrix_world@b.head_local)).length for b in check.data.bones)
    pose_error=0
    for frame,sample in motion_samples.items():
        bpy.context.scene.frame_set(frame)
        pose_error=max(pose_error,max((Vector(sample[b.name])-(check.matrix_world@b.head)).length for b in check.pose.bones))
    assert pose_error<.0001,(label,pose_error)
    actual=list(check.animation_data.action.frame_range)
    assert abs((actual[1]-actual[0])-(end-start))<.01
    manifest['clips'][label.lower()]={'path':str(target),'source':str(source),'frame_start':start,'frame_end':end,'duration_seconds':(end-start)/30,'speed_cm_s':speed,'bone_count':len(names),'roundtrip_sampled_pose_max_error_m':pose_error,'roundtrip_animation_only_rest_difference_m':error,'roundtrip_frames':actual,'root_policy':'Fixed wrapper; original cyclic Hips horizontal sway and vertical bounce retained'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(manifest,indent=2),flush=True)
