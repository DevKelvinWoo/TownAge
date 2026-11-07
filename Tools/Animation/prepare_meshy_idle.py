"""Inspect Meshy Idle; --attenuate creates a calm motion-only derivative.

The approved mesh, skin weights and reference skeleton remain unchanged.
"""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ArtSource/Meshy/TownKeeper_Meshy/Animations/Idle01'
source=OUT/'TownKeeper_Meshy_Idle.fbx'
neutral={}
if '--attenuate' in sys.argv:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'ArtSource/Meshy/TownKeeper_Meshy/Animations/Locomotion01/TownKeeper_Meshy_Standing.fbx'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(int(rig.animation_data.action.frame_range[0]))
    neutral={b.name:b.matrix_basis.decompose() for b in rig.pose.bones}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(source))
s=bpy.context.scene;arm=next(o for o in s.objects if o.type=='ARMATURE');mesh=next(o for o in s.objects if o.type=='MESH')
action=arm.animation_data.action;start,end=map(int,action.frame_range);fps=s.render.fps/s.render.fps_base
attenuated='--attenuate' in sys.argv
if attenuated:
    original={}
    for frame in range(start,end+1):
        s.frame_set(frame);original[frame]={b.name:b.matrix_basis.decompose() for b in arm.pose.bones}
    basis=original[start]
    arm.animation_data_clear()
    for frame in range(start,end+1):
        for bone in arm.pose.bones:
            loc,rot,scale=original[frame][bone.name];bl,br,bs=basis[bone.name]
            nl,nr,ns=neutral[bone.name]
            bone.rotation_mode='QUATERNION';bone.location=nl;bone.rotation_quaternion=nr;bone.scale=ns
            if bone.name in ('Spine','Spine01','Spine02','neck','Head'):
                delta=br.inverted()@rot
                from mathutils import Quaternion
                bone.rotation_quaternion=nr@Quaternion().slerp(delta,.15)
                bone.location=nl+(loc-bl)*.15
            if frame==end:bone.location=nl;bone.rotation_quaternion=nr;bone.scale=ns
            bone.keyframe_insert('location',frame=frame);bone.keyframe_insert('rotation_quaternion',frame=frame);bone.keyframe_insert('scale',frame=frame)
    arm.animation_data.action.name='TownKeeper_Meshy_Idle_Calm'
    s.frame_start=start;s.frame_end=end;s.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=arm
    source=OUT/'TownKeeper_Meshy_Idle_Calm.fbx'
    bpy.ops.export_scene.fbx(filepath=str(source),use_selection=True,object_types={'ARMATURE','MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,armature_nodetype='NULL',bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    reference={}
    for frame in (start,(start+end)//2,end):
        s.frame_set(frame);reference[frame]={b.name:arm.matrix_world@b.head for b in arm.pose.bones}
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(source))
    s=bpy.context.scene;arm=next(o for o in s.objects if o.type=='ARMATURE');mesh=next(o for o in s.objects if o.type=='MESH');action=arm.animation_data.action
    new_start,new_end=map(int,action.frame_range);shift=new_start-start;error=0
    for frame,positions in reference.items():
        s.frame_set(frame+shift);error=max(error,max((positions[b.name]-(arm.matrix_world@b.head)).length for b in arm.pose.bones))
    assert error<.0001,error
    start,end=new_start,new_end
    maps=ROOT/'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/Generated_textures'
    for image in bpy.data.images:
        name=image.name.lower()
        key='base_color.png' if 'basecolor' in name else 'roughness.png' if 'roughness' in name else 'normal.png' if 'normal' in name else 'metallic.png' if 'metallic' in name else None
        if key:image.filepath=str(maps/key);image.reload()
names=[b.name for b in arm.data.bones]
expected=json.loads((ROOT/'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/rig_inspection.json').read_text())['armatures'][0]['bones']
assert names==expected
samples=[];first=None;dg=bpy.context.evaluated_depsgraph_get()
for frame in range(start,end+1):
 s.frame_set(frame);ev=mesh.evaluated_get(dg);pts=[ev.matrix_world@v.co for v in ev.data.vertices]
 if first is None:first=pts
 samples.append({name:list(arm.matrix_world@arm.pose.bones[name].head) for name in ['Hips','Head','LeftHand','RightHand','LeftFoot','RightFoot','LeftToeBase','RightToeBase']})
loop=max((a-b).length for a,b in zip(first,pts))*100
metrics={'fbx_path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'action':action.name,'action_id':0,'fps':fps,'frames':[start,end],'duration_seconds':(end-start)/fps,'bone_count':len(names),'wrapper':arm.name,'loop_max_vertex_delta_cm':loop,'bone_travel_range_cm':{name:[100*(max(row[name][i] for row in samples)-min(row[name][i] for row in samples)) for i in range(3)] for name in samples[0]},'source_policy':'Original Meshy FBX with original bind carrier; Unreal animations-only import; no mesh/weights changes'}
if attenuated:metrics.update(source_policy='NeutralStanding baseline plus15% originalIdle upperSpine/neck/head localdeltas relativefirstframe; hips/legs/arms fixed atbaseline. Exactloopendpoint. Mesh/skin/restunchanged.',amplitude_factor=.15,roundtrip_max_bone_error_m=error)
(OUT/'manifest.json').write_text(json.dumps(metrics,indent=2),encoding='utf8')
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8;s.cycles.use_denoising=True;s.render.resolution_x=300;s.render.resolution_y=400;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('IdleReview');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.25,.28,1)
center=Vector((0,0,.85))
for offset,power,size in [((3,-4,4),650,4),((-3,-2,2),350,3),((1,3,3),600,3)]:
 bpy.ops.object.light_add(type='AREA',location=offset);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.1
for name,offset in [('Front',(0,-5,0)),('Side',(5,0,0)),('Game',(3,-5,2.5))]:
 cam.location=center+Vector(offset);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();folder=OUT/('CalmPreview' if attenuated else 'Preview')/name;folder.mkdir(parents=True,exist_ok=True)
 for i in range(8):
  frame=start+(end-start)*i/8;s.frame_set(int(frame),subframe=frame-int(frame));s.render.filepath=str(folder/f'{i:02d}.png');bpy.ops.render.render(write_still=True)
print(json.dumps(metrics,indent=2),flush=True)
