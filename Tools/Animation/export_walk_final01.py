"""Faithful export of approved WALK Draft01 plus a neutral standing support pose."""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
from io_scene_fbx import parse_fbx

ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
OUT=ROOT/'ArtSource/Characters/Main/Animations/WalkFinal01';OUT.mkdir(parents=True,exist_ok=True)
DRAFT=ROOT/'ArtSource/Characters/Main/Animations/WalkDraft01/TownKeeper_WalkDraft01.blend'
PRODUCTION=ROOT/'ArtSource/Characters/Main/Revision04/TownKeeper_Reference04.blend'
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (DRAFT,PRODUCTION)}
scene=bpy.context.scene;scene.name='TownKeeper_WalkFinal01';scene.unit_settings.scale_length=.01;scene.render.fps=30
rig=next(o for o in scene.objects if o.type=='ARMATURE');body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
rig.name='Armature_008';rig.data.name='TownKeeper_Deform'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
rest_signature={b.name:{'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones}
walk=rig.animation_data.action.copy();walk.name='WALK_TownKeeper_Final01';walk.use_fake_user=True;rig.animation_data.action=walk

def sample(action,start,end):
    rig.animation_data.action=action
    output=[]
    for frame in range(start,end+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        output.append({b.name:[list(row) for row in b.matrix] for b in rig.pose.bones})
    return output

approved=sample(walk,1,29)

def export(action,filename,start,end):
    rig.animation_data.action=action;scene.frame_start=start;scene.frame_end=end;scene.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},global_scale=1.0,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_force_startend_keying=True,bake_anim_step=1.0,bake_anim_simplify_factor=0.0,path_mode='AUTO')
    tree,version=parse_fbx.parse(str(OUT/filename));units={};stacks=[]
    def visit(node):
        if node.id==b'P' and node.props and node.props[0] in (b'UnitScaleFactor',b'OriginalUnitScaleFactor'):units[node.props[0].decode()]=node.props[-1]
        if node.id==b'AnimationStack':stacks.append(str(node.props[1]))
        for child in node.elems:visit(child)
    visit(tree)
    assert units['UnitScaleFactor']==1.0 and len(stacks)==1,(units,stacks)
    return {'path':str(OUT/filename),'units':units,'stacks':stacks,'frame_start':start,'frame_end':end,'samples':end-start+1,'duration_seconds':(end-start)/30}

walk_export=export(walk,'A_TownKeeper_Walk.fbx',1,29)
# A minimal stationary support pose, using the same relaxed shoulder clearance.
stand=bpy.data.actions.new('POSE_TownKeeper_Standing');stand.use_fake_user=True;rig.animation_data.action=stand
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
matrices={'root':rest['root'].copy()}
matrices['pelvis']=Matrix.Translation((0,0,-1.2))@rest['pelvis']
for name in ('spine_01','spine_02','neck_01','head'):
    b=rig.data.bones[name];matrices[name]=matrices[b.parent.name]@rest[b.parent.name].inverted()@rest[name]
def oriented(name,head,direction):
    b=rig.data.bones[name];delta=(b.tail_local-b.head_local).normalized().rotation_difference(direction.normalized())
    return Matrix.Translation(head)@delta.to_matrix().to_4x4()@rest[name].to_3x3().to_4x4()
for sign,side in ((-1,'l'),(1,'r')):
    upper='upperarm_'+side;lower='lowerarm_'+side;hand='hand_'+side
    shoulder=(matrices['spine_02']@rest['spine_02'].inverted())@rig.data.bones[upper].head_local
    abd=.40 if side=='r' else .23
    upperdir=Vector((sign*abd,0,-1)).normalized();elbow=shoulder+upperdir*rig.data.bones[upper].length
    lowerdir=Vector((sign*abd,math.sin(-.12),-math.cos(-.12))).normalized();wrist=elbow+lowerdir*rig.data.bones[lower].length
    matrices[upper]=oriented(upper,shoulder,upperdir);matrices[lower]=oriented(lower,elbow,lowerdir);matrices[hand]=oriented(hand,wrist,lowerdir)
    thigh='thigh_'+side;calf='calf_'+side;foot='foot_'+side
    hip=(matrices['pelvis']@rest['pelvis'].inverted())@rig.data.bones[thigh].head_local
    ankle_rest=rig.data.bones[foot].head_local;gi=body.vertex_groups[foot].index
    min_rest=min((body.matrix_world@v.co).z for v in body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups))
    ankle=Vector((ankle_rest.x,0,ankle_rest.z-min_rest))
    delta=ankle-hip;distance=delta.length;direction=delta.normalized();l1=rig.data.bones[thigh].length;l2=rig.data.bones[calf].length
    a=(l1*l1-l2*l2+distance*distance)/(2*distance);h=math.sqrt(max(0,l1*l1-a*a));pole=Vector((0,-1,0));perp=(pole-direction*pole.dot(direction)).normalized();knee=hip+direction*a+perp*h
    matrices[thigh]=oriented(thigh,hip,knee-hip);matrices[calf]=oriented(calf,knee,ankle-knee);matrices[foot]=Matrix.Translation(ankle)@rest[foot].to_3x3().to_4x4()
for name,m in matrices.items():
    pb=rig.pose.bones[name];b=pb.bone
    pb.matrix_basis=rest[name].inverted()@rest[b.parent.name]@matrices[b.parent.name].inverted()@m if b.parent else rest[name].inverted()@m
    for frame in (1,31):
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(data_path=channel,frame=frame,group=name)
stand_export=export(stand,'A_TownKeeper_Standing.fbx',1,31)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.frame_set(1);scene.render.filepath=str(OUT/'Standing_Support_Pose.png');bpy.ops.render.render(write_still=True)

# Compare exact approved walk transforms; do not accidentally export a resampled different gait.
again=sample(walk,1,29)
max_change=max(abs(approved[f][n][r][c]-again[f][n][r][c]) for f in range(29) for n in rest for r in range(4) for c in range(4))
assert max_change<1e-6,max_change
scene.frame_start=1;scene.frame_end=28;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TownKeeper_WalkFinal01.blend'))

# Reload each FBX in an isolated temporary scene and inspect the imported take.
roundtrip=[]
for data in (walk_export,stand_export):
    test=bpy.data.scenes.new('AnimationRoundtrip');test.unit_settings.scale_length=.01;test.render.fps=30
    try:
        if bpy.context.window:bpy.context.window.scene=test
        with bpy.context.temp_override(scene=test,view_layer=test.view_layers[0]):
            bpy.ops.import_scene.fbx(filepath=data['path'],use_anim=True)
            imported=next(o for o in test.objects if o.type=='ARMATURE')
            action=imported.animation_data.action
            frame_range=list(action.frame_range);root_samples=[];object_samples=[];scale_error=0
            for frame in range(int(round(frame_range[0])),int(round(frame_range[1]))+1):
                test.frame_set(frame);bpy.context.view_layer.update()
                root_samples.append(imported.pose.bones['root'].matrix.copy());object_samples.append(imported.matrix_world.copy())
                scale_error=max(scale_error,max(abs(s-1) for b in imported.pose.bones for s in b.scale))
            root_error=max(abs(v) for m in root_samples for row in m-root_samples[0] for v in row)
            object_error=max(abs(v) for m in object_samples for row in m-object_samples[0] for v in row)
            roundtrip.append({'file':data['path'],'armature_name':imported.name,'bone_names':[b.name for b in imported.data.bones],'object_scale':list(imported.scale),'frame_range':frame_range,'duration_seconds':(frame_range[1]-frame_range[0])/30,'root_matrix_max_change':root_error,'object_matrix_max_change':object_error,'bone_scale_max_error':scale_error})
    finally:
        if bpy.context.window:bpy.context.window.scene=scene
        for o in list(test.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.scenes.remove(test)

report={'approved_draft':'WalkDraft01','approval':'User: 시안 그대로 제작 시작해','wrapper_root':'Armature_008','deform_bones':list(rest),'fps':30,'walk':walk_export,'standing':stand_export,'walk_speed_cm_s':64/(28/30),'root_motion':'in_place','walk_transform_max_change_from_approved':max_change,'weights_bad':sum(1 for v in body.data.vertices if abs(sum(g.weight for g in v.groups)-1)>1e-4),'rest_skeleton_unchanged':rest_signature=={b.name:{'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in rig.data.bones},'source_files_unchanged':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()},'roundtrip':roundtrip,'editable_blend':str(OUT/'TownKeeper_WalkFinal01.blend'),'standing_preview':str(OUT/'Standing_Support_Pose.png'),'limitations':['No sprint clip','Standing is static support pose, not a breathing idle performance','Runtime speed blending/foot contacts still require Unreal validation by parent']}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('WALK_FINAL_HANDOFF',json.dumps(report,ensure_ascii=False),flush=True)
