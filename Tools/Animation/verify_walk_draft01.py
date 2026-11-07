"""Read-only draft validation on an isolated loaded .blend; never exports animation."""
import bpy, json, hashlib
from pathlib import Path
OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Animations/WalkDraft01')
manifest=json.loads((OUT/'manifest.json').read_text())
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
indices={}
for side in ('l','r'):
    gi=body.vertex_groups['foot_'+side].index
    indices[side]=[v.index for v in body.data.vertices if any(g.group==gi and g.weight>.99 for g in v.groups)]
rows=[];root_reference=None;root_error=0;mesh_first=None;mesh_last=None
for f in range(1,30):
    scene.frame_set(f);bpy.context.view_layer.update()
    matrix=rig.pose.bones['root'].matrix
    if root_reference is None:root_reference=matrix.copy()
    root_error=max(root_error,max(abs(x) for row in matrix-root_reference for x in row))
    obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=obj.to_mesh()
    row={'frame':f}
    for side in ('l','r'):
        points=[obj.matrix_world@me.vertices[i].co for i in indices[side]]
        row[side]={'sole_z_cm':min(p.z for p in points),'mean_y_cm':sum(p.y for p in points)/len(points)}
    rows.append(row)
    if f in (1,29):
        points=[v.co.copy() for v in me.vertices]
        if f==1:mesh_first=points
        else:mesh_last=points
    obj.to_mesh_clear()
speed_residual=[]
for i in range(1,28):
    for side in ('l','r'):
        if manifest['trajectory'][i]['feet'][side]['stance'] and manifest['trajectory'][i-1]['feet'][side]['stance']:
            delta=rows[i][side]['mean_y_cm']-rows[i-1][side]['mean_y_cm']
            speed_residual.append(abs(delta-manifest['stride_cm']/28))
report={'source_file_unchanged':hashlib.sha256(Path(manifest['source_blend']).read_bytes()).hexdigest()==manifest['source_sha256'],'skeleton_rest_unchanged':manifest['skeleton_rest']=={b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones},'root_matrix_max_change':root_error,'loop_skinned_vertex_max_delta_cm':max((a-b).length for a,b in zip(mesh_first,mesh_last)),'maximum_planted_y_step_residual_cm':max(speed_residual),'minimum_skinned_sole_z_cm':min(row[s]['sole_z_cm'] for row in rows for s in ('l','r')),'maximum_stance_sole_abs_z_cm':max(abs(row[s]['sole_z_cm']) for row,m in zip(rows,manifest['trajectory']) for s in ('l','r') if m['feet'][s]['stance']),'editable_preview_engine':scene.render.engine,'editable_preview_device':scene.cycles.device,'rendered_view_frames':{v:len(list((OUT/'frames'/v).glob('frame_*.png'))) for v in ('front','side','gameplay')},'scope':'WALK draft only; final polish/export/Unreal integration intentionally not performed','not_tested':['260cm/s gameplay matching','Unreal PIE','mobile device/package performance','networked playback','slopes and obstacle handling'],'actual_foot_samples':rows}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALK_DRAFT_VALIDATION',json.dumps({k:v for k,v in report.items() if k!='actual_foot_samples'}))
