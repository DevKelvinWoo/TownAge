import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ArtSource/Meshy/CozyHouse01/candidate_v002'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ArtSource/Meshy/CozyHouse01/candidate_v001/CozyHouse01.blend'))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
source_triangles=len(body.data.polygons)
# Connectivity lookup welds only a temporary copy, preserving original UV splits/normals.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bm.verts.ensure_lookup_table()
remaining=set(bm.verts);selected_positions=set();chosen=[]
while remaining:
    stack=[remaining.pop()];comp=[]
    while stack:
        v=stack.pop();comp.append(v)
        for e in v.link_edges:
            other=e.other_vert(v)
            if other in remaining:remaining.remove(other);stack.append(other)
    pts=[body.matrix_world@v.co for v in comp]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    # All complete islands contained in the approved door leaf region. The
    # encompassing arch/outer jamb is a different island and remains in Body.
    if lo[0]>.65 and hi[0]<1.85 and hi[1]<-1.1 and hi[2]<1.9:
        selected_positions.update(tuple(round(c,5) for c in v.co) for v in comp)
        chosen.append({'vertices':len(comp),'min':lo,'max':hi})
bm.free()
assert len(chosen)==12,chosen
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='DESELECT')
edit=bmesh.from_edit_mesh(body.data)
for face in edit.faces:
    if all(tuple(round(c,5) for c in v.co) in selected_positions for v in face.verts):
        face.select_set(True)
bmesh.update_edit_mesh(body.data)
bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
door=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body)
body.name='HouseBody';door.name='DoorLeaf'
door.rotation_mode='XYZ'
# Remove the provider's hidden wall/backfill inside the doorway. Subtract a
# convex arched prism by clipping triangles, interpolating UVs and normals.
# This repairs an existing aperture, without rebuilding the house geometry.
profile=[(.725,-.05),(1.725,-.05)]+[(1.225+.5*math.cos(t*math.pi/16),1.34+.5*math.sin(t*math.pi/16)) for t in range(17)]
planes=[]
for a,b in zip(profile,profile[1:]+profile[:1]):
    normal=Vector((b[1]-a[1],0,a[0]-b[0]));planes.append((normal,normal.x*a[0]+normal.z*a[1]))
planes.extend([(Vector((0,1,0)),-1.14),(Vector((0,-1,0)),1.68)])
def clip(poly,n,d):
    inside=[];outside=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=n.dot(a[0])-d;db=n.dot(b[0])-d
        (inside if da<=1e-7 else outside).append(a)
        if (da<0<db) or (db<0<da):
            t=da/(da-db);v=tuple(a[k].lerp(b[k],t) for k in range(3));inside.append(v);outside.append(v)
    return inside,outside
old=body.data;uv=old.uv_layers.active;inv=body.matrix_world.inverted();verts=[];faces=[];uvs=[];normals=[]
cut_faces=0
for face in old.polygons:
    poly=[(body.matrix_world@old.vertices[old.loops[i].vertex_index].co,Vector(uv.data[i].uv),Vector(old.corner_normals[i].vector)) for i in face.loop_indices]
    coords=[p[0] for p in poly]
    overlap=(max(p.x for p in coords)>.725 and min(p.x for p in coords)<1.725 and max(p.z for p in coords)>-.05 and min(p.z for p in coords)<1.84 and max(p.y for p in coords)>-1.68 and min(p.y for p in coords)<-1.14)
    pieces=[]
    if overlap:
        remainder=poly
        for n,d in planes:
            if len(remainder)<3:break
            remainder,outside=clip(remainder,n,d)
            if len(outside)>=3:pieces.append(outside)
        if len(remainder)>=3:cut_faces+=1
    else:pieces=[poly]
    for piece in pieces:
        indices=[]
        for pos,tex,norm in piece:
            indices.append(len(verts));verts.append(inv@pos);uvs.append(tex);normals.append(norm.normalized())
        faces.append(indices)
repaired=bpy.data.meshes.new('HouseBody_DoorwayRepaired');repaired.from_pydata(verts,[],faces);repaired.update()
for material in old.materials:repaired.materials.append(material)
layer=repaired.uv_layers.new(name='UVMap')
for loop in repaired.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
for face in repaired.polygons:face.use_smooth=True
repaired.normals_split_custom_set([normals[l.vertex_index] for l in repaired.loops])
body.data=repaired
assert cut_faces>0,'No doorway backfill was removed'
# Right-hand hinge pin, a vertical axis; zero rotation means closed.
pivot=Vector((1.685,-1.395,0.014115333557128906))
s=bpy.context.scene;s.cursor.location=pivot
bpy.ops.object.select_all(action='DESELECT');door.select_set(True);bpy.context.view_layer.objects.active=door
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
def bb(o):
    pp=[Vector(p) for p in o.bound_box]
    return {'min':[min(p[i] for p in pp) for i in range(3)],'max':[max(p[i] for p in pp) for i in range(3)]}
counts={}
for o in (body,door):o.data.calc_loop_triangles();counts[o.name]=len(o.data.loop_triangles)
assert counts['HouseBody']>10000 and 500<counts['DoorLeaf']<3000,counts
assert sum(counts.values())<15000,counts
manifest={'source':'candidate_v001/CozyHouse01.blend','door_hinge_blender_m':list(pivot),'door_local_bounds_m':bb(door),'body_triangles':counts['HouseBody'],'door_triangles':counts['DoorLeaf'],'total_triangles':sum(counts.values()),'doorway_backfill_faces_cut':cut_faces,'selected_islands':chosen,'animation_created':False,'closed_rotation_degrees':0,'swing_axis':'local Z','textures':'../candidate_v001/textures/Image_0.png'}
for o,name in [(body,'HouseBody'),(door,'DoorLeaf')]:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    old=o.location.copy()
    if name=='DoorLeaf':o.location=Vector((0,0,0))
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True)
    o.location=old
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);door.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'CozyHouse01_Split.glb'),export_format='GLB',use_selection=True)
(OUT/'split_manifest.json').write_text(json.dumps(manifest,indent=2))
# Still open/closed inspections are static verification poses, no animation.
s.render.resolution_x=800;s.render.resolution_y=800;s.cycles.samples=16
for angle,label in [(0,'Closed'),(75,'OpenCheck')]:
    door.rotation_euler.z=math.radians(angle)
    s.render.filepath=str(OUT/('Preview_'+label+'.png'));bpy.ops.render.render(write_still=True)
door.rotation_euler.z=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CozyHouse01_Split.blend'))
print('DOOR_SPLIT_COMPLETE',json.dumps(manifest))
