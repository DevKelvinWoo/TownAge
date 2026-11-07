"""Cozy idle direction draft on the approved standing basis; no final export."""
import bpy, json, math, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
OUT=ROOT/'ArtSource/Characters/Main/Animations/IdleDraft01';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'ArtSource/Characters/Main/Animations/WalkFinal01/TownKeeper_WalkFinal01.blend'
PRODUCTION=ROOT/'ArtSource/Characters/Main/Revision04/TownKeeper_Reference04.blend'
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE,PRODUCTION)}
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
standing=bpy.data.actions.get('POSE_TownKeeper_Standing')
assert standing is not None,'Approved standing support Action is missing'
rig.animation_data.action=standing;scene.frame_set(1);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in rig.pose.bones};rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
rest_signature={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones}
for o in list(scene.objects):
    if o.name.startswith('DraftGroundMarker_'):bpy.data.objects.remove(o,do_unlink=True)
rig.animation_data_clear();rig.animation_data_create()
action=bpy.data.actions.new('IDLE_TownKeeper_Draft01');rig.animation_data.action=action
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
scene.name='TownKeeper_IdleDraft01';scene.render.fps=30;scene.frame_start=1;scene.frame_end=108
PERIOD=108

def smooth(t):return t*t*(3-2*t)
def breath(phase):
    p=phase%1
    if p<.12:return 0.0
    if p<.43:return smooth((p-.12)/.31)
    if p<.50:return 1.0
    if p<.90:return 1-smooth((p-.50)/.40)
    return 0.0
def authored(keys,phase):
    p=phase%1
    for (t0,v0),(t1,v1) in zip(keys,keys[1:]):
        if t0<=p<=t1:return v0+(v1-v0)*smooth((p-t0)/(t1-t0))
    return keys[0][1]
def oriented(name,head,direction):
    b=rig.data.bones[name];delta=(b.tail_local-b.head_local).normalized().rotation_difference(direction.normalized())
    return Matrix.Translation(head)@delta.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
def anchored(name,parent_matrix):
    parent=rig.data.bones[name].parent.name
    return (parent_matrix@base[parent].inverted())@base[name].translation

pose_samples=[];motion=[]
for frame in range(1,110):
    phase=(frame-1)/PERIOD;b=breath(phase);lag=breath(phase-.055);headlag=breath(phase-.09)
    sway=authored([(0,0),(.18,-.18),(.36,-.65),(.58,-.42),(.78,.25),(.90,.18),(1,0)],phase)
    yaw=authored([(0,0),(.28,.10),(.58,-.12),(.84,-.08),(1,0)],phase)
    pelvis_z=.16*b+.025*abs(sway)
    matrices={'root':base['root'].copy()}
    pelvis_delta=Matrix.Translation((sway,0,pelvis_z))@Quaternion((0,1,0),math.radians(sway*.25)).to_matrix().to_4x4()
    matrices['pelvis']=pelvis_delta@base['pelvis']
    for name,pitch,roll,yscale,zscale in (
        ('spine_01',-.20*b,sway*.10,1.0,1.0),
        ('spine_02',-.90*b,sway*.08,1.0,1+.009*b),
        ('neck_01',-.25*b+.20*headlag,0,1.0,1.0),
        ('head',-.15*b+.25*headlag,0,1.0,1.0)):
        parent=rig.data.bones[name].parent.name;head=anchored(name,matrices[parent])
        delta=Quaternion((1,0,0),math.radians(pitch)).to_matrix()@Quaternion((0,1,0),math.radians(roll)).to_matrix()@Quaternion((0,0,1),math.radians(yaw)).to_matrix()
        scale=Matrix.Diagonal((1+.005*b if name=='spine_02' else 1,yscale,zscale))
        matrices[name]=Matrix.Translation(head)@(delta@base[name].to_3x3()@scale).to_4x4()
    for side,sign in (('l',-1),('r',1)):
        upper='upperarm_'+side;lower='lowerarm_'+side;hand='hand_'+side
        shoulder=anchored(upper,matrices['spine_02'])+Vector((0,0,.08*b))
        angle=math.radians((.45 if side=='l' else .30)*lag)
        upper_rotation=Quaternion((1,0,0),angle).to_matrix()@base[upper].to_3x3()
        matrices[upper]=Matrix.Translation(shoulder)@upper_rotation.to_4x4()
        elbow=anchored(lower,matrices[upper])
        lower_rotation=Quaternion((1,0,0),angle*.7).to_matrix()@base[lower].to_3x3()
        matrices[lower]=Matrix.Translation(elbow)@lower_rotation.to_4x4()
        wrist=anchored(hand,matrices[lower]);matrices[hand]=Matrix.Translation(wrist)@(Quaternion((1,0,0),angle*.45).to_matrix()@base[hand].to_3x3()).to_4x4()
        thigh='thigh_'+side;calf='calf_'+side;foot='foot_'+side
        hip=anchored(thigh,matrices['pelvis']);ankle=base[foot].translation.copy()
        l1=rig.data.bones[thigh].length;l2=rig.data.bones[calf].length
        d=ankle-hip;distance=d.length;direction=d.normalized();a=(l1*l1-l2*l2+distance*distance)/(2*distance)
        assert distance<l1+l2,f'Unreachable planted foot at {frame}'
        h=math.sqrt(max(0,l1*l1-a*a));pole=Vector((0,-1,0));perp=(pole-direction*pole.dot(direction)).normalized();knee=hip+direction*a+perp*h
        matrices[thigh]=oriented(thigh,hip,knee-hip);matrices[calf]=oriented(calf,knee,ankle-knee);matrices[foot]=base[foot].copy()
    for name,matrix in matrices.items():
        pb=rig.pose.bones[name];parent=pb.bone.parent
        pb.matrix_basis=rest[name].inverted()@rest[parent.name]@matrices[parent.name].inverted()@matrix if parent else rest[name].inverted()@matrix
        for prop in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=prop,frame=frame,group=name)
    pose_samples.append({name:[list(row) for row in pb.matrix_basis] for name,pb in rig.pose.bones.items()})
    motion.append({'frame':frame,'breath':b,'pelvis_sway_cm':sway,'pelvis_vertical_cm':pelvis_z})
for layer in action.layers:
    for strip in layer.strips:
        for slot in action.slots:
            bag=strip.channelbag(slot,ensure=False)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
                    curve.modifiers.new('CYCLES')
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.resolution_x=384;scene.render.resolution_y=512;scene.render.resolution_percentage=100
camera=scene.camera;camera.data.clip_end=5000;camera.data.type='ORTHO';camera.data.ortho_scale=205
camera.location=(230,-460,205);camera.rotation_euler=(Vector((0,0,84))-camera.location).to_track_quat('-Z','Y').to_euler()
for label,frame in [('rest',1),('inhale',49)]:
    scene.frame_set(frame);scene.render.filepath=str(OUT/f'check_{label}.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1)
blend=OUT/'TownKeeper_IdleDraft01.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report={'status':'draft_pending_explicit_user_approval','clip':'IDLE_TownKeeper_Draft01','source_blend':str(SOURCE),'source_hashes':hashes,'source_standing_action':'POSE_TownKeeper_Standing','editable_blend':str(blend),'fps':30,'unique_frame_range':[1,108],'matching_endpoint_frame':109,'duration_seconds':3.6,'preview_fps':15,'root_motion':'none; both feet planted','inhalation_seconds':[.432,1.548],'inhale_hold_seconds':[1.548,1.8],'exhalation_seconds':[1.8,3.24],'neutral_pause_seconds':.792,'pelvis_sway_range_cm':[min(m['pelvis_sway_cm'] for m in motion),max(m['pelvis_sway_cm'] for m in motion)],'pelvis_vertical_range_cm':[min(m['pelvis_vertical_cm'] for m in motion),max(m['pelvis_vertical_cm'] for m in motion)],'loop_basis_max_error':max(abs(pose_samples[0][n][r][c]-pose_samples[-1][n][r][c]) for n in rest for r in range(4) for c in range(4)),'rest_signature':rest_signature,'motion_samples':motion,'notes':['No new deform bones, morphs, model/material edits or final FBX.','Chest width/depth scaling stays below1 percent; subtle bone-driven breathing only.','Hands and head respond slightly after the chest.','Existing WalkFinal neutral pose is the base for compatibility.','User motion review precedes final polishing and Unreal integration.']}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('IDLE_DRAFT_BUILT',json.dumps({k:report[k] for k in ('editable_blend','duration_seconds','pelvis_sway_range_cm','pelvis_vertical_range_cm','loop_basis_max_error')}),flush=True)
