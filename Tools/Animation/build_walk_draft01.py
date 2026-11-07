"""Contact-driven, in-place walk draft. No production assets or rest bones change."""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
OUT=ROOT/'ArtSource/Characters/Main/Animations/WalkDraft01'
SOURCE=ROOT/'ArtSource/Characters/Main/Revision04/TownKeeper_Reference04.blend'
OUT.mkdir(parents=True,exist_ok=True)
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
# This script runs in an isolated background process loaded from the source file.
# Remove unrelated draft scenes only from this process before saving a separate file.
for other in list(bpy.data.scenes):
    if other!=scene:bpy.data.scenes.remove(other)
bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
scene.name='TownKeeper_WalkDraft01';rig.name='RIG_TownKeeper_WalkDraft01'
rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4);b.rotation_mode='QUATERNION'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
rest_signature={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones}
action=bpy.data.actions.new('WALK_TownKeeper_Draft01');rig.animation_data_create();rig.animation_data.action=action
FPS=30;PERIOD=28;STRIDE=64.0;STANCE=.55;HALF=STRIDE*STANCE/2
scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=PERIOD
footverts={}
for side in ('l','r'):
    gi=body.vertex_groups['foot_'+side].index
    footverts[side]=[body.matrix_world@v.co for v in body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups)]

def periodic(values,phase):
    n=len(values);t=(phase%1)*n;i=int(t);u=t-i
    a,b,c,d=[values[k%n] for k in (i-1,i,i+1,i+2)]
    return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)

def footpath(u):
    u%=1
    if u<=STANCE:return -HALF+STRIDE*u,0.0,0.0,True
    t=(u-STANCE)/(1-STANCE)
    # Hermite swing preserves backward stance velocity at toe-off and contact.
    h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t;h11=t**3-t*t
    y=h00*HALF+h10*STRIDE*(1-STANCE)+h01*(-HALF)+h11*STRIDE*(1-STANCE)
    lift=7.0*16*t*t*(1-t)*(1-t)
    pitch=math.radians(7)*math.sin(math.pi*t)
    return y,lift,pitch,False

def oriented(name,head,direction):
    b=rig.data.bones[name];delta=(b.tail_local-b.head_local).normalized().rotation_difference(direction.normalized())
    return Matrix.Translation(head) @ delta.to_matrix().to_4x4() @ rest[name].to_3x3().to_4x4()

def attach(name,parentpose):
    b=rig.data.bones[name]
    return parentpose @ rest[b.parent.name].inverted() @ rest[name]

poses=[];metrics=[]
for frame in range(1,PERIOD+2):
    phase=(frame-1)/PERIOD
    dz=periodic([-4.8,-6.0,-4.3,-3.5,-4.8,-6.0,-4.3,-3.5],phase)
    sway=periodic([0,-1.1,-1.5,-.8,0,1.1,1.5,.8],phase)
    yaw=math.radians(periodic([-2.2,-1.6,0,1.6,2.2,1.6,0,-1.6],phase))
    roll=math.radians(periodic([0,-1,-1.5,-.8,0,1,1.5,.8],phase))
    matrices={'root':rest['root'].copy()}
    pelvis_head=rig.data.bones['pelvis'].head_local+Vector((sway,0,dz))
    matrices['pelvis']=Matrix.Translation(pelvis_head) @ Quaternion((0,0,1),yaw).to_matrix().to_4x4() @ Quaternion((0,1,0),roll).to_matrix().to_4x4() @ rest['pelvis'].to_3x3().to_4x4()
    for name in ('spine_01','spine_02','neck_01','head'):
        b=rig.data.bones[name];p=matrices[b.parent.name]
        head=(p @ rest[b.parent.name].inverted()) @ b.head_local
        factor={'spine_01':.6,'spine_02':.2,'neck_01':.1,'head':0}[name]
        matrices[name]=Matrix.Translation(head) @ Quaternion((0,0,1),yaw*factor).to_matrix().to_4x4() @ Quaternion((0,1,0),roll*factor).to_matrix().to_4x4() @ rest[name].to_3x3().to_4x4()
    frame_metric={'frame':frame,'phase':phase%1,'feet':{}}
    for sign,side,offset in ((-1,'l',0),(1,'r',.5)):
        u=(phase+offset)%1
        y,lift,pitch,stance=footpath(u)
        footname='foot_'+side;ankle_rest=rig.data.bones[footname].head_local
        footrot=Quaternion((1,0,0),pitch).to_matrix()
        support=min((footrot@(v-ankle_rest)).z for v in footverts[side])
        ankle=Vector((ankle_rest.x,y,-support+lift))
        thigh='thigh_'+side;calf='calf_'+side
        hip=(matrices['pelvis']@rest['pelvis'].inverted())@rig.data.bones[thigh].head_local
        l1=rig.data.bones[thigh].length;l2=rig.data.bones[calf].length
        delta=ankle-hip;distance=delta.length
        if distance>l1+l2-.02:raise RuntimeError(f'Leg reach exceeded at frame{frame}: {distance}/{l1+l2}')
        direction=delta.normalized();a=(l1*l1-l2*l2+distance*distance)/(2*distance)
        height=math.sqrt(max(0,l1*l1-a*a));pole=Vector((0,-1,0))
        perp=(pole-direction*pole.dot(direction)).normalized();knee=hip+direction*a+perp*height
        matrices[thigh]=oriented(thigh,hip,knee-hip)
        matrices[calf]=oriented(calf,knee,ankle-knee)
        matrices[footname]=Matrix.Translation(ankle)@footrot.to_4x4()@rest[footname].to_3x3().to_4x4()
        arm_angle=math.radians(periodic([9,7,0,-7,-9,-7,0,7],u))
        # Modest extra right-arm abduction clears the approved rigid satchel.
        abduction=.40 if side=='r' else .23
        shoulder=(matrices['spine_02']@rest['spine_02'].inverted())@rig.data.bones['upperarm_'+side].head_local
        upperdir=Vector((sign*abduction,math.sin(arm_angle),-math.cos(arm_angle))).normalized()
        elbow=shoulder+upperdir*rig.data.bones['upperarm_'+side].length
        lowerdir=Vector((sign*abduction,math.sin(arm_angle-.12),-math.cos(arm_angle-.12))).normalized()
        wrist=elbow+lowerdir*rig.data.bones['lowerarm_'+side].length
        matrices['upperarm_'+side]=oriented('upperarm_'+side,shoulder,upperdir)
        matrices['lowerarm_'+side]=oriented('lowerarm_'+side,elbow,lowerdir)
        matrices['hand_'+side]=oriented('hand_'+side,wrist,lowerdir)
        frame_metric['feet'][side]={'stance':stance,'ankle':list(ankle),'sole_clearance_cm':lift,'knee':list(knee),'reach_cm':distance}
    for name,matrix in matrices.items():
        pb=rig.pose.bones[name];b=pb.bone
        pb.matrix_basis=rest[name].inverted()@rest[b.parent.name]@matrices[b.parent.name].inverted()@matrix if b.parent else rest[name].inverted()@matrix
        pb.keyframe_insert(data_path='location',frame=frame,group=name)
        pb.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=name)
        pb.keyframe_insert(data_path='scale',frame=frame,group=name)
    poses.append({n:[list(row) for row in p.matrix_basis] for n,p in rig.pose.bones.items()})
    metrics.append(frame_metric)
# Per-frame samples with a matching endpoint: rendered cycles omit duplicate frame29.
for layer in action.layers:
    for strip in layer.strips:
        for slot in action.slots:
            bag=strip.channelbag(slot,ensure=False)
            if bag:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
                    curve.modifiers.new('CYCLES')
loop_error=max(abs(poses[0][name][r][c]-poses[-1][name][r][c]) for name in poses[0] for r in range(4) for c in range(4))

# Treadmill marks move at the draft's own calibrated speed, not gameplay260cm/s.
marker_material=bpy.data.materials.new('WalkDraft_GroundMarker');marker_material.diffuse_color=(.30,.28,.23,1)
markers=[]
for i in range(-5,6):
    bpy.ops.mesh.primitive_cube_add(location=(0,i*STRIDE,.1))
    o=bpy.context.object;o.name=f'DraftGroundMarker_{i}';o.scale=(125,.22,.08);o.data.materials.append(marker_material)
    o.location.y=i*STRIDE;o.keyframe_insert(data_path='location',frame=1,index=1)
    o.location.y=(i+1)*STRIDE;o.keyframe_insert(data_path='location',frame=PERIOD+1,index=1)
    for layer in o.animation_data.action.layers:
        for strip in layer.strips:
            for slot in o.animation_data.action.slots:
                bag=strip.channelbag(slot,ensure=False)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
    markers.append(o)

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG'
scene.render.resolution_x=384;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.frame_set(1)
camera=scene.camera
def lookat(loc,target):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=205;lookat((230,-460,205),(0,0,82))
scene.render.filepath=str(OUT/'check_contact.png');bpy.ops.render.render(write_still=True)
scene.frame_set(8);scene.render.filepath=str(OUT/'check_passing.png');bpy.ops.render.render(write_still=True)

# Evaluate actual skinned boot vertices, not only the authored IK targets.
samples=[]
for frame in range(1,PERIOD+1):
    scene.frame_set(frame);bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();evaluated=body.evaluated_get(deps);me=evaluated.to_mesh()
    row={'frame':frame}
    for side in ('l','r'):
        gi=body.vertex_groups['foot_'+side].index
        indexes=[v.index for v in body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups)]
        row[side]=min((evaluated.matrix_world@me.vertices[i].co).z for i in indexes)
    samples.append(row);evaluated.to_mesh_clear()
scene.frame_set(1)
blend=OUT/'TownKeeper_WalkDraft01.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest={'status':'draft_pending_user_direction','source_blend':str(SOURCE),'source_sha256':source_hash,'editable_blend':str(blend),'action':action.name,'fps':FPS,'frame_start':1,'frame_end_inclusive':PERIOD,'matching_endpoint_frame':PERIOD+1,'cycle_seconds':PERIOD/FPS,'stride_cm':STRIDE,'intended_treadmill_speed_cm_s':STRIDE/(PERIOD/FPS),'current_gameplay_walk_speed_cm_s':260,'speed_match_to_gameplay':False,'root_motion':'in_place; root transforms fixed','foot_stance_fraction':STANCE,'foot_swing_clearance_target_cm':7,'key_phases':{'contact_left':1,'down_left':4,'passing_left':8,'up_left':11,'contact_right':15,'down_right':18,'passing_right':22,'up_right':25},'loop_matrix_max_error':loop_error,'skinned_sole_heights':samples,'trajectory':metrics,'skeleton_rest':rest_signature,'rest_bones_unchanged':rest_signature=={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones},'notes':['Only WALK draft. No final FBX or Unreal integration.','No toe bones: boot articulation is one rigid foot segment.','Right arm slightly abducted to clear rigid satchel.','No production mesh, materials or rest skeleton modified.']}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WALK_DRAFT_BUILT',json.dumps({k:manifest[k] for k in ('editable_blend','cycle_seconds','intended_treadmill_speed_cm_s','loop_matrix_max_error','rest_bones_unchanged')}))
