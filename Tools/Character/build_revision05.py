"""Targeted Revision05 reconstruction using the preserved reference builder.

Changes are applied to source text in memory with exact anchors. Older source and
assets are not edited. Hands use anatomical forearm frames, not world axes.
"""
from pathlib import Path

ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
BASE=ROOT/'ArtSource/Characters/Main/build_reference03.py'
source=BASE.read_text(encoding='utf-8')
def replace(old,new):
    global source
    assert source.count(old)==1, f'Builder anchor changed: {old[:80]}'
    source=source.replace(old,new)
def section(start,end,new):
    global source
    a=source.index(start);b=source.index(end,a)
    source=source[:a]+new+source[b:]

source=source.replace('Revision03','Revision05').replace('Reference03','Reference05').replace('TK03_','TK05_')
source=source.replace('scene.cycles.samples=32','scene.cycles.samples=16')
replace('    vs=[];fs=[];count=(len(points)-1)*steps+1','    steps=min(steps,5);sides=min(sides,16)\n    vs=[];fs=[];count=(len(points)-1)*steps+1')

helpers=r'''
def face_y(x,z):
    rr=math.sqrt(max(.0001,1-((z-133)/28)**2))
    cheek=1+.06*math.exp(-((z-122)/8)**2)
    cosine=max(-.9999,min(.9999,x/(29*rr*cheek)))
    sine=-math.sqrt(1-cosine*cosine)
    return 25*rr*sine-2.3*math.exp(-((z-125)/12)**2)*(-sine)**3

def hand_tube(name,points,radii,thumb_axis,bone):
    vs=[];fs=[];steps=5;sides=14;count=(len(points)-1)*steps+1
    for i in range(count):
        t=i/(count-1)*(len(points)-1);p=catmull(points,t)
        tangent=(catmull(points,min(len(points)-1,t+.01))-catmull(points,max(0,t-.01))).normalized()
        width=(thumb_axis-tangent*thumb_axis.dot(tangent)).normalized();depth=tangent.cross(width).normalized()
        k=min(int(t),len(points)-2);u=t-k;r=radii[k]*(1-u)+radii[k+1]*u
        for j in range(sides):
            a=j*2*math.pi/sides;vs.append(p+width*(math.cos(a)*r)+depth*(math.sin(a)*r))
    for i in range(count-1):
        for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs += [tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))]
    return mesh(name,vs,fs,skin,bone)

def create_hand(sign,side,wrist,elbow):
    from mathutils import Quaternion
    w=Vector(wrist);axis=(w-Vector(elbow)).normalized()
    relaxed=Vector((sign*(.40 if side=='r' else .23),math.sin(-.12),-math.cos(-.12))).normalized()
    delta=axis.rotation_difference(relaxed)
    forward=Vector((0,-1,0));thumb_relaxed=(forward-relaxed*forward.dot(relaxed)).normalized()
    thumb_axis=delta.inverted()@thumb_relaxed
    palm_normal=sign*axis.cross(thumb_axis).normalized()
    # Palm has a broad metacarpal body and narrows into the wrist.
    vs=[];fs=[];rings=[(0,3.1,2.7),(1.8,3.7,2.4),(4.2,4.2,2.05),(6.5,3.8,1.9),(7.4,3.35,1.75)]
    sides=24
    for distance,width,depth in rings:
        for j in range(sides):
            angle=j*2*math.pi/sides
            vs.append(w+axis*distance+thumb_axis*(width*math.cos(angle))+palm_normal*(depth*math.sin(angle)))
    for i in range(len(rings)-1):
        for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs += [tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))]
    mesh('Palm_'+side,vs,fs,skin,'hand_'+side)
    for k,(offset,length,radius) in enumerate([(2.65,4.6,1.05),(.85,5.3,1.12),(-1.05,4.8,1.07),(-2.75,3.6,.94)]):
        points=[w+axis*6.7+thumb_axis*offset,
                w+axis*(7.5+length*.35)+thumb_axis*(offset*1.02)+palm_normal*.25,
                w+axis*(7.5+length*.75)+thumb_axis*(offset*1.04)+palm_normal*.70,
                w+axis*(7.5+length)+thumb_axis*(offset*1.02)+palm_normal*1.15]
        hand_tube('Finger_'+side+str(k),points,[radius,radius*.96,radius*.88,radius*.62],thumb_axis,'hand_'+side)
        ell('Fingertip_'+side+str(k),points[-1],(radius*.66,)*3,skin,'hand_'+side,16,10)
    points=[w+axis*2.5+thumb_axis*2.8+palm_normal*.25,
            w+axis*4.0+thumb_axis*4.5+palm_normal*.5,
            w+axis*6.1+thumb_axis*5.0+palm_normal*1.1,
            w+axis*7.3+thumb_axis*4.3+palm_normal*1.6]
    hand_tube('Thumb_'+side,points,[1.9,1.7,1.4,.95],thumb_axis,'hand_'+side)
    ell('Thumbtip_'+side,points[-1],(.98,)*3,skin,'hand_'+side,16,10)

'''
replace('# A pear-like face with broad cheeks and a softly flattened facial plane.',helpers+'# Convex cheek, chin and forehead surface; no flat or retracted facial mask.')
section('vs=[];fs=[];N=64;R=36',"mesh('Face',vs,fs,skin,'head')",r'''vs=[];fs=[];N=64;R=36
for i in range(R+1):
    th=.001+(math.pi-.002)*i/R;z=133+28*math.cos(th);rr=math.sin(th)
    cheek=1+.06*math.exp(-((z-122)/8)**2)
    for j in range(N):
        a=2*math.pi*j/N;x=29*rr*math.cos(a)*cheek;y=25*rr*math.sin(a)
        if y<0:y-=2.3*math.exp(-((z-125)/12)**2)*(-math.sin(a))**3
        vs.append((x,y,z))
for i in range(R):
    for j in range(N):a=i*N+j;b=i*N+(j+1)%N;fs.append((a,b,b+N,a+N))
''')
replace("(x,-23.0,133)","(x,face_y(x,133)-.6,133)")
replace("(x-sign*.35,-24.5,132.5)","(x-sign*.35,face_y(x,133)-2.0,132.5)")
replace("(x-sign*1.8,-25.55,135.2)","(x-sign*1.8,face_y(x,133)-3.2,135.2)")
replace("[(sign*4.5,-23.6,136),(sign*7.0,-24,140),(sign*12,-23.9,141),(sign*16.5,-22.5,137)]","[(sign*x,face_y(sign*x,z)-.7,z) for x,z in [(4.5,136),(7,140),(12,141),(16.5,137)]]")
replace("[(sign*6.2,-23,146),(sign*10,-23.2,147),(sign*14.5,-22.5,145.5)]","[(sign*x,face_y(sign*x,z)-.6,z) for x,z in [(6.2,146),(10,147),(14.5,145.5)]]")
replace("(0,-25,127.7)","(0,face_y(0,127.7)-1.2,127.7)")
replace("[(-4.5,-23.1,120),( -2.5,-24,118.4),(0,-24.2,118),(2.5,-24,118.4),(4.5,-23.1,120)]","[(x,face_y(x,z)-.35,z) for x,z in [(-4.5,120),(-2.5,118.4),(0,118),(2.5,118.4),(4.5,120)]]")
section("    palm=ell('Palm_'",'\n# Folded kerchief',"    create_hand(sign,side,wrist,elbow)\n")
section('    pivot=Vector((sign*33,-1,73));inv=hand.matrix_world.inverted()',"    hand['tk_bone']",'')
replace("rem.voxel_size=.40","rem.voxel_size=.45")
replace("    hand['tk_bone']='hand_'+side;hand['tk_hand_union']=side","    dec=hand.modifiers.new('Hand surface budget','DECIMATE');dec.ratio=.65;bpy.ops.object.modifier_apply(modifier=dec.name)\n    hand['tk_bone']='hand_'+side;hand['tk_hand_union']=side")
replace("bone('hand_'+side,(sign*33,-1,73),(sign*36,-1,66),'lowerarm_'+side)","bone('hand_'+side,(sign*33,-1,73),Vector((sign*33,-1,73))+Vector((sign*8,-1,-12)).normalized()*8,'lowerarm_'+side)")
replace("z=(o.matrix_world@v.co).z;w=max(0,min(1,(z-71)/6));group.add([v.index],1-w,'REPLACE');g.add([v.index],w,'REPLACE')","p=o.matrix_world@v.co;sgn=-1 if side=='l' else 1;u=(p-Vector((sgn*33,-1,73))).dot(Vector((sgn*8,-1,-12)).normalized());w=max(0,min(1,(2-u)/4));group.add([v.index],1-w,'REPLACE');g.add([v.index],w,'REPLACE')")

warp=r'''
# Explicit body-proportion edit, applied to geometry AND bone rest positions.
def body_z(z):
    if z<=22:return z*(18.5/22)
    if z<=65:return 18.5+(z-22)*.64
    if z<=103:return 46.02+(z-65)*.92
    return 80.98+(z-103)*.55
def warp_point(p,kind):
    p=p.copy()
    if kind=='head':return Vector((p.x*1.10,p.y*1.10,90+(p.z-106)*1.14))
    if kind=='neck_01':return Vector((p.x,p.y,88+(p.z-106)))
    return Vector((p.x,p.y,body_z(p.z)))
head_points=[]
for o in parts:
    inv=o.matrix_world.inverted();kind=o['tk_bone']
    for v in o.data.vertices:
        target=warp_point(o.matrix_world@v.co,kind);v.co=inv@target
        if kind=='head':head_points.append(target.copy())
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for b in arm.edit_bones:
    if b.name=='head':b.head=warp_point(b.head,'head');b.tail=warp_point(b.tail,'head')
    elif b.name=='neck_01':b.head=warp_point(b.head,'body');b.tail=warp_point(b.tail,'head')
    else:b.head=warp_point(b.head,'body');b.tail=warp_point(b.tail,'body')
bpy.ops.object.mode_set(mode='OBJECT')
rig.name='Armature_008'
'''
replace("bpy.ops.object.select_all(action='DESELECT')\nfor o in parts:o.select_set(True)",warp+"\nbpy.ops.object.select_all(action='DESELECT')\nfor o in parts:o.select_set(True)")
budget=r'''
# Keep a high-quality hero silhouette while avoiding the prior120k triangle cost.
body.data.calc_loop_triangles()
triangles_before=len(body.data.loop_triangles)
if triangles_before>58000:
    bpy.context.view_layer.objects.active=body
    dec=body.modifiers.new('Game mesh triangle budget','DECIMATE');dec.ratio=58000/triangles_before
    bpy.ops.object.modifier_apply(modifier=dec.name)
for v in body.data.vertices:
    total=sum(g.weight for g in v.groups)
    if total>0:
        for g in list(v.groups):body.vertex_groups[g.group].add([v.index],g.weight/total,'REPLACE')
'''
replace('# Height normalization in source geometry and skeleton, not only Actor scale.',budget+'\n# Height normalization in source geometry and skeleton, not only Actor scale.')
replace("body.parent=rig;mod=body.modifiers.new('Deform','ARMATURE');mod.object=rig","body.parent=rig;mod=body.modifiers.new('Deform','ARMATURE');mod.object=rig\nbody['head_fraction_of_height']=(max(p.z for p in head_points)-min(p.z for p in head_points))/height\nbody['revision05_authorization']='User directed natural hands, shorter body and fuller face profile'\n")
# Remove the default empty scene from this isolated process only.
replace("scene.render.image_settings.file_format='PNG'","for other in list(bpy.data.scenes):\n    if other!=scene:bpy.data.scenes.remove(other)\nbpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)\nscene.render.image_settings.file_format='PNG'")
exec(compile(source,str(BASE),'exec'))
