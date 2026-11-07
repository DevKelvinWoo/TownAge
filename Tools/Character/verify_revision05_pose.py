"""Check actual deformed hands against the satchel on retargeted walk/stand."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Revision05')
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');body=next(o for o in scene.objects if o.type=='MESH' and o.parent==rig)
hand_group=body.vertex_groups['hand_r'].index
hand_vertices={v.index for v in body.data.vertices if sum(g.weight for g in v.groups if g.group==hand_group)>.75}
hand_faces=[tuple(p.vertices) for p in body.data.polygons if all(i in hand_vertices for i in p.vertices)]
bag_attribute=body.data.attributes.get('tk_satchel_faces')
bag_faces=[tuple(p.vertices) for p in body.data.polygons if (bag_attribute.data[p.index].value if bag_attribute else 'BagLeather' in body.data.materials[p.material_index].name)]
assert hand_faces and bag_faces,'Hand/satchel membership is empty; cannot claim collision validation'
walk=rig.animation_data.action;standing=bpy.data.actions['POSE_TownKeeper_Standing05']
rows=[]
for action,frames in [(walk,range(1,30)),(standing,[1])]:
    rig.animation_data.action=action
    for frame in frames:
        scene.frame_set(frame);bpy.context.view_layer.update();obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=obj.to_mesh()
        points=[obj.matrix_world@v.co for v in me.vertices]
        a=BVHTree.FromPolygons(points,hand_faces,all_triangles=False,epsilon=0)
        b=BVHTree.FromPolygons(points,bag_faces,all_triangles=False,epsilon=0)
        overlaps=a.overlap(b)
        nearest=min(b.find_nearest(points[i])[3] for i in hand_vertices)
        rows.append({'action':action.name,'frame':frame,'overlapping_triangles':len(overlaps),'nearest_hand_vertex_to_bag_cm':nearest})
        obj.to_mesh_clear()
worst=max(rows,key=lambda r:r['overlapping_triangles'])
rig.animation_data.action=bpy.data.actions[worst['action']];scene.frame_set(worst['frame']);bpy.context.view_layer.update()
camera=scene.camera;bone=rig.pose.bones['hand_r'];center=rig.matrix_world@(bone.head.lerp(bone.tail,.65))
camera.data.type='ORTHO';camera.data.ortho_scale=25;camera.location=center+Vector((55,-35,16));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.render.filepath=str(OUT/'Hand_r_WorstWalk.png');bpy.ops.render.render(write_still=True)
report={'scope':'right hand versus satchel/strap only','source_blend':bpy.data.filepath,'bag_membership':'persistent face attribute' if bag_attribute else 'unbaked material assignment','hand_face_count':len(hand_faces),'bag_face_count':len(bag_faces),'worst':worst,'samples':rows}
(OUT/'hand_collision_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HAND_COLLISION_REPORT',json.dumps(report),flush=True)
assert worst['overlapping_triangles']==0,'Right hand/satchel collision regression; inspect saved report and render'
