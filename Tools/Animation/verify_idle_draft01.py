"""Read-only validation of actual deformed idle geometry and source preservation."""
import bpy,json,hashlib
from pathlib import Path
OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Animations/IdleDraft01')
manifest=json.loads((OUT/'manifest.json').read_text());scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE');body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
indices={}
for side in ('l','r'):
    gi=body.vertex_groups['foot_'+side].index;indices[side]=[v.index for v in body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups)]
root0=None;feet0={};root_error=0;foot_error=0;minimum_z=1e9;maximum_z=0;first=None;last=None
idle_action=rig.animation_data.action
scene.frame_set(1);bpy.context.view_layer.update();idle_first={b.name:b.matrix.copy() for b in rig.pose.bones}
rig.animation_data.action=bpy.data.actions['POSE_TownKeeper_Standing'];scene.frame_set(1);bpy.context.view_layer.update()
standing_delta=max(abs(v) for b in rig.pose.bones for row in b.matrix-idle_first[b.name] for v in row)
rig.animation_data.action=idle_action
for frame in range(1,110):
    scene.frame_set(frame);bpy.context.view_layer.update();m=rig.pose.bones['root'].matrix
    if root0 is None:root0=m.copy()
    root_error=max(root_error,max(abs(v) for row in m-root0 for v in row))
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=obj.to_mesh()
    for side in ('l','r'):
        points=[obj.matrix_world@me.vertices[i].co for i in indices[side]]
        if frame==1:feet0[side]=[p.copy() for p in points]
        foot_error=max(foot_error,max((a-b).length for a,b in zip(points,feet0[side])))
        sole=min(p.z for p in points);minimum_z=min(minimum_z,sole);maximum_z=max(maximum_z,abs(sole))
    if frame==1:first=[v.co.copy() for v in me.vertices]
    if frame==109:last=[v.co.copy() for v in me.vertices]
    obj.to_mesh_clear()
report={'status':'draft_review_required','source_files_unchanged':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in manifest['source_hashes'].items()},'rest_skeleton_unchanged':manifest['rest_signature']=={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones},'neutral_pose_matrix_max_deviation_from_standing':standing_delta,'root_matrix_max_change':root_error,'loop_skinned_vertex_max_delta_cm':max((a-b).length for a,b in zip(first,last)),'planted_foot_vertex_max_displacement_cm':foot_error,'minimum_sole_z_cm':minimum_z,'maximum_sole_abs_z_cm':maximum_z,'deform_bone_count':len(rig.data.bones),'preview_engine':scene.render.engine,'preview_device':scene.cycles.device,'rendered_frames':{v:len(list((OUT/'frames'/v).glob('frame_*.png'))) for v in ('front','side','gameplay')},'not_tested':['User approval of this Idle motion','Unreal runtime blending','Network playback','Mobile device performance','Slopes and obstacle cases']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('IDLE_VALIDATION',json.dumps(report))
