"""TownKeeper reference reconstruction. Coordinates are centimeters; no clips."""
import bpy, bmesh, math, json
from mathutils import Vector
from pathlib import Path

OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Revision03')
OUT.mkdir(parents=True,exist_ok=True)
SCALE=1.0
parts=[]
scene=bpy.data.scenes.new('TownKeeper_Reference03')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=.01
scene.render.engine='CYCLES'; scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=1120;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('TownKeeper_Studio03');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.60,.53,.45,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'

def lin(hexstr):
    a=[int(hexstr[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in a)

def mat(name,color,rough=.8,grain=0,metal=0):
    m=bpy.data.materials.new('TK03_'+name);m.use_nodes=True;m.diffuse_color=(*lin(color),1)
    n=m.node_tree.nodes;l=m.node_tree.links;b=n.get('Principled BSDF')
    b.inputs['Base Color'].default_value=m.diffuse_color;b.inputs['Roughness'].default_value=rough
    b.inputs['Metallic'].default_value=metal;b.inputs['Specular IOR Level'].default_value=.22
    if grain:
        tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=190
        noise.inputs['Detail'].default_value=2;l.new(tc.outputs['Generated'],noise.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=tuple(v*.83 for v in lin(color))+(1,)
        ramp.color_ramp.elements[1].color=tuple(min(v*1.15,1) for v in lin(color))+(1,)
        l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],b.inputs['Base Color'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=grain;bump.inputs['Distance'].default_value=.025
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    return m

skin=mat('Skin','F0AC74',.74); hair=mat('Hair','633721',.77,.14)
shirt=mat('Linen','E7D2A5',.91,.23); green=mat('Canvas','667043',.91,.22)
cuff=mat('Cuff','848653',.91,.2);coral=mat('Scarf','BD6248',.88,.16)
leather=mat('BootLeather','6D432D',.84,.12);tan=mat('BagLeather','B48043',.82,.13)
sole=mat('Sole','A47440',.9,.10);stitch=mat('Thread','B6A064',.93)
gold=mat('Brass','D5A542',.45,0,.55); eyes=mat('Eyes','3D2519',.42)
white=mat('Catchlight','FFF6DE',.38);leaf=mat('Sprout','A8B84B',.73)
inner=mat('EarInner','DA9369',.82);mouth=mat('Mouth','63321D',.84)

def finish(o,name,m,bone):
    o.name=name;o.data.materials.clear();o.data.materials.append(m)
    for p in o.data.polygons:p.use_smooth=True
    o['tk_bone']=bone;parts.append(o);return o

def mesh(name,vs,fs,m,bone):
    data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update()
    # Custom latitude rings and lofts must face outwards in single-sided game renderers.
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data);bm.free();data.update()
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o)
    return finish(o,name,m,bone)

def ell(name,center,r,m,bone,seg=32,rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=center)
    o=bpy.context.object;o.scale=r
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,m,bone)

def box(name,c,r,m,bone,bevel=1):
    bpy.ops.mesh.primitive_cube_add(location=c);o=bpy.context.object;o.scale=r
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('Tailored edges','BEVEL');mod.width=bevel;mod.segments=4
    bpy.ops.object.modifier_apply(modifier=mod.name)
    finish(o,name,m,bone)
    mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return o

def catmull(points,t):
    i=min(int(t),len(points)-2);u=t-i
    a=Vector(points[max(0,i-1)]);b=Vector(points[i]);c=Vector(points[i+1]);d=Vector(points[min(len(points)-1,i+2)])
    return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)

def loft(name,points,widths,depths,m,bone,steps=5,sides=16):
    vs=[];fs=[];count=(len(points)-1)*steps+1
    for i in range(count):
        t=i/(count-1)*(len(points)-1);p=catmull(points,t)
        pa=catmull(points,max(0,t-.01));pb=catmull(points,min(len(points)-1,t+.01));tangent=(pb-pa).normalized()
        wvec=tangent.cross(Vector((0,1,0))).normalized()
        if wvec.length<.5:wvec=Vector((1,0,0))
        dvec=tangent.cross(wvec).normalized()
        k=min(int(t),len(points)-2);u=t-k
        width=widths[k]*(1-u)+widths[k+1]*u;depth=depths[k]*(1-u)+depths[k+1]*u
        for j in range(sides):
            a=2*math.pi*j/sides;v=p+wvec*(math.cos(a)*width)+dvec*(math.sin(a)*depth);vs.append(v)
    for i in range(count-1):
        for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs.append(tuple(reversed(range(sides))));fs.append(tuple(range(len(vs)-sides,len(vs))))
    return mesh(name,vs,fs,m,bone)

def line(name,points,r,m,bone):return loft(name,points,[r]*len(points),[r]*len(points),m,bone,3,8)

def panel(name,outline,m,bone,thickness=.6):
    n=len(outline);vs=[(x,y-thickness/2,z) for x,y,z in outline]+[(x,y+thickness/2,z) for x,y,z in outline]
    fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,vs,fs,m,bone);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Soft stitched border','BEVEL');mod.width=.6;mod.segments=3
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return o

# A pear-like face with broad cheeks and a softly flattened facial plane.
vs=[];fs=[];N=64;R=36
for i in range(R+1):
    th=.001+(math.pi-.002)*i/R;z=133+27*math.cos(th);rr=math.sin(th)
    cheek=1+.08*math.exp(-((z-125)/10)**2)
    for j in range(N):
        a=2*math.pi*j/N;x=27*rr*math.cos(a)*cheek;y=23*rr*math.sin(a)
        if y<0:
            flat=-23*(max(0,1-(x/31)**4-((z-134)/33)**4)**.25)*rr**.16
            mix=max(0,min(1,(z-137)/10));y=flat*(1-mix)+y*mix
            if z>146:y*=.88
        vs.append((x,y,z))
for i in range(R):
    for j in range(N):a=i*N+j;b=i*N+(j+1)%N;fs.append((a,b,b+N,a+N))
mesh('Face',vs,fs,skin,'head')
ell('Neck',(0,0,106),(7,7,9),skin,'neck_01')
for sign,side in [(-1,'l'),(1,'r')]:
    ell('Ear_'+side,(sign*26,-1,128),(5,4,7),skin,'head')
    ell('EarBowl_'+side,(sign*28,-3.8,128),(2.3,1.2,4.2),inner,'head')
    x=sign*10.7
    ell('EyeWhite_'+side,(x,-23.0,133),(5.5,1.7,7.1),white,'head')
    ell('Iris_'+side,(x-sign*.35,-24.5,132.5),(4.8,1.15,6.7),eyes,'head')
    ell('EyeShine_'+side,(x-sign*1.8,-25.55,135.2),(1.35,.35,1.7),white,'head',20,12)
    line('UpperLid_'+side,[(sign*4.5,-23.6,136),(sign*7.0,-24,140),(sign*12,-23.9,141),(sign*16.5,-22.5,137)],.55,hair,'head')
    line('Brow_'+side,[(sign*6.2,-23,146),(sign*10,-23.2,147),(sign*14.5,-22.5,145.5)],.85,hair,'head')
ell('Nose',(0,-25,127.7),(2.4,2.2,2.0),skin,'head')
line('Smile',[(-4.5,-23.1,120),( -2.5,-24,118.4),(0,-24.2,118),(2.5,-24,118.4),(4.5,-23.1,120)],.45,mouth,'head')

# Back cap leaves the face open, with scalloped low bob and overlapping swept bangs.
vs=[];fs=[];N=64;R=24
for i in range(R+1):
    u=i/R
    for j in range(N):
        a=2*math.pi*j/N
        front=max(0,-math.sin(a));bottom=2.60-1.45*front**1.2
        th=.001+u*bottom
        scallop=(math.sin(a*9)*.8)*u**4
        vs.append((30.5*math.sin(th)*math.cos(a),31*math.sin(th)*math.sin(a)+2,137+29*math.cos(th)+scallop))
for i in range(R):
    for j in range(N):a=i*N+j;b=i*N+(j+1)%N;fs.append((a,b,b+N,a+N))
mesh('HairCap',vs,fs,hair,'head')
locks=[([(7,-2,164),(4,-16,160),(-3,-26,153),(-11,-28,145),(-21,-25,140),(-29,-20,143)],[.4,7,9,9,5,.1],[.3,3,4,4,2,.1]),
       ([(10,-1,164),(12,-18,158),(10,-27,150),(6,-28,144),(1,-25,141)],[.4,6,7,5,.1],[.3,3.5,4,2.8,.1]),
       ([(11,0,163),(20,-12,156),(25,-21,147),(30,-15,139),(33,-9,141)],[.5,7,8,5,.1],[.4,3.5,4,2,.1])]
for i,(p,w,d) in enumerate(locks):loft('Fringe_'+str(i),p,w,d,hair,'head',8,20)
for sign,side in [(-1,'l'),(1,'r')]:
    for i in range(4):
        y=-5+i*7;x=sign*(24-.5*i)
        loft('Bob_'+side+str(i),[(x,y,148),(sign*(27+i*.15),y-1,136),(sign*(28+i*.1),y-3,122),(sign*(25+i*.2),y-4,113+i),(sign*22,y-3,114+i)],[2,5.5,6,4,.1],[2,7,7.5,5,.1],hair,'head',6,20)
loft('Cowlick',[(5,1,163),(6,0,169),(1,-1,174),(-6,-2,175)],[3,3,2,.1],[2,2,1.2,.1],hair,'head',6,16)
for i,x in enumerate((-23,-16,-8,0,8,16,23)):
    y=30-abs(x)*.20
    tip=112+abs(x)*.12+(i%2)*2.5
    loft('RearHair_'+str(i),[(x*.45,13,160),(x*.85,y,148),(x*1.05,y+2,131),(x*.95,y,tip),(x*.7,y+1,tip+1.8)],[.3,6.5,8,4.5,.1],[.3,4.5,5.5,3.5,.1],hair,'head',7,20)
# Sprout pin visible on the right temple.
line('SproutStem',[(22,-23,145),(21,-24,151)],.9,gold,'head')
loft('SproutLeft',[(21,-24,150),(17,-25,154),(16,-24,157)],[.3,2.7,.1],[.3,1,.1],leaf,'head',5,12)
loft('SproutRight',[(21,-24,150),(24,-25,155),(24,-24,158)],[.3,2.7,.1],[.3,1,.1],leaf,'head',5,12)

# Shirt and continuous trouser tubes, waist hidden beneath overall bib.
loft('ShirtBody',[(0,0,81),(0,0,86),(0,0,94),(0,0,101),(0,0,105)],[14,15.3,16.5,13,8],[9.5,10.5,10.7,9,7],shirt,'spine_02',5,32)
loft('OverallWaist',[(0,0,62),(0,0,72),(0,0,85)],[19,18,16],[10.8,11.7,11.4],green,'pelvis',4,32)
vs=[];fs=[]
for row in range(17):
    v=row/16;z=79+22*v;width=12.5-3.5*v**3
    for col in range(25):
        u=col/24*2-1;x=width*u
        y=-12.1*math.sqrt(max(.1,1-(x/17.5)**2))-.45-.24*math.sin(u*math.pi*2)*math.sin(v*math.pi)**2
        vs.append((x,y,z))
for row in range(16):
    for col in range(24):a=row*25+col;fs.append((a,a+1,a+26,a+25))
bib=mesh('Bib',vs,fs,green,'spine_02');bpy.context.view_layer.objects.active=bib
solid=bib.modifiers.new('Cloth thickness','SOLIDIFY');solid.thickness=.8;bpy.ops.object.modifier_apply(modifier=solid.name)
panel('BibPocket',[(-6,-12.4,82),(-7,-12.7,88),(7,-12.7,88),(6,-12.4,82)],green,'spine_02',.7)
for sign,side in [(-1,'l'),(1,'r')]:
    loft('OverallStrap_'+side,[(sign*10,-12,91),(sign*12,-9,101),(sign*10,0,105),(sign*10,10,99),(sign*10,11,80)],[2]*5,[.7]*5,green,'spine_02',5,12)
    ell('Button_'+side,(sign*10,-14,94),(2.4,.8,2.4),gold,'spine_02',24,12)
    x=sign*10.5
    leg=loft('Trouser_'+side,[(x,0,68),(x,0,61),(x,0,49),(x,0,36),(x,0,24)],[8.8,9.5,8.9,8.1,7.5],[10.8,11,9.7,8.9,8],green,'thigh_'+side,6,24)
    leg['tk_leg']=side
    loft('Cuff_'+side,[(x,0,22),(x,0,23),(x,0,28),(x,0,29)],[7.6,8.7,8.7,7.6],[8.2,9,9,8.2],cuff,'calf_'+side,3,24)
    panel('SidePocket_'+side,[(sign*12,-10.4,50),(sign*17.5,-7.4,51),(sign*17.5,-7.5,59),(sign*12,-10.5,59)],green,'thigh_'+side,.35)
    # Boots with rounded toe, shaped shaft, tongue, toe seam, welt and laces.
    ell('BootToe_'+side,(x,-3.5,8),(8,12,8),leather,'foot_'+side)
    loft('BootShaft_'+side,[(x,1,5),(x,1,12),(x,1,19),(x,1,22)],[7.6,7,7.2,6.5],[8,7.5,7,6.5],leather,'foot_'+side,4,24)
    ell('BootSole_'+side,(x,-3.7,2),(8.6,12.5,2.1),sole,'foot_'+side)
    panel('BootTongue_'+side,[(x-3.2,-6.8,10),(x-3.5,-6.8,21),(x+3.5,-6.8,21),(x+3.2,-6.8,10)],leather,'foot_'+side,.7)
    for k in range(3):
        z=12+k*2.8
        line('LaceA_'+side+str(k),[(x-3.5,-7.7,z),(x,-8.5,z+1.3),(x+3.5,-7.7,z+2.2)],.55,sole,'foot_'+side)
        line('LaceB_'+side+str(k),[(x+3.5,-7.7,z),(x,-8.7,z+1.3),(x-3.5,-7.7,z+2.2)],.55,sole,'foot_'+side)
    # Sleeves taper down the arm; skin emerges only after rolled cuff.
    shoulder=(sign*14,0,98);elbow=(sign*25,0,85);wrist=(sign*33,-1,73)
    loft('Sleeve_'+side,[shoulder,(sign*19,0,94),(sign*24,0,88),(sign*26,0,85)],[7,7.5,6,5.5],[7,7,6,5.5],shirt,'upperarm_'+side,5,24)
    loft('SleeveCuff_'+side,[(sign*24,0,88),(sign*25,0,86),(sign*27,0,84)],[6.8,7,6.2],[6.4,6.7,6],shirt,'upperarm_'+side,4,24)
    arm=loft('Forearm_'+side,[(sign*25,0,85),(sign*29,-.5,79),wrist],[4.7,4.1,3.3],[4.5,3.9,3.2],skin,'lowerarm_'+side,5,20)
    palm=ell('Palm_'+side,(sign*35,-1,70),(4.2,3,4),skin,'hand_'+side)
    for k in range(4):
        xx=sign*(32.2+k*2.05);length=8.5-abs(k-1)*1.0
        loft('Finger_'+side+str(k),[(xx,-1,69),(xx+sign*.6,-1.4,64),(xx+sign*.7,-2,69-length)],[.95,.85,.7],[1.05,.85,.7],skin,'hand_'+side,5,12)
        ell('Fingertip_'+side+str(k),(xx+sign*.7,-2,69-length),(.72,.72,.85),skin,'hand_'+side,16,10)
    loft('Thumb_'+side,[(sign*32.5,-1,72),(sign*30.5,-2,69),(sign*30.8,-3,67)],[1.8,1.5,.3],[1.7,1.4,.3],skin,'hand_'+side,5,12)

# Folded kerchief rather than a necklace of spheres.
panel('ScarfFront',[(-10,-9,107),(-7,-12,103),(0,-15,96),(8,-12,103),(10,-9,107)],coral,'spine_02',1.5)
panel('ScarfBack',[(-9,9,106),(-7,11,103),(0,13,96),(7,11,103),(9,9,106)],coral,'spine_02',1.3)
loft('ScarfCollar',[(-10,-7,106),(-7,3,108),(0,7,109),(8,3,108),(10,-7,106)],[2.2]*5,[2.3]*5,coral,'spine_02',4,16)
ell('ScarfKnot',(10,-11,103),(3.2,2.3,3.0),coral,'spine_02')
loft('ScarfTail',[(11,-11,103),(15,-12,101),(18,-11,96),(17,-10,94)],[1,3,2,.1],[.5,1,1,.1],coral,'spine_02',5,14)
# Bag at wearer's right, broad flat shoulder strap and brass buckle.
strap=panel('BagStrap',[(-12,-13,103),(-9,-14,104),(20,-14,69),(17,-14,67)],tan,'spine_02',1.1)
for side in (-1,1):
    panel('RearPocket'+str(side),[(side*3,11,60),(side*13,9,60),(side*13,10,69),(side*3,12,69)],green,'pelvis',.6)
box('Bag',(20,-10,65),(8,4,9),tan,'pelvis',3)
panel('BagFlap',[(12,-14.4,68),(12,-14.5,74),(28,-14.5,74),(28,-14.4,68),(25,-15,66),(15,-15,66)],tan,'pelvis',1)
ell('BagSnap',(20,-15.8,68),(1.4,.65,1.4),gold,'pelvis')
for dx in (-2,2):line('BuckleSide'+str(dx),[(3+dx,-15,85),(7+dx,-15,90)],.55,gold,'spine_02')
line('BuckleBottom',[(1,-15,85),(5,-15,85)],.55,gold,'spine_02')
line('BuckleTop',[(5,-15,90),(9,-15,90)],.55,gold,'spine_02')
# Stitches are small separate geometry and will be baked into the atlas.
for side in (-1,1):
    for k in range(9):
        z=81+k*1.8
        line('BibStitch'+str(side)+str(k),[(side*11.3,-13,z),(side*11.3,-13,z+.8)],.13,stitch,'spine_02')
for k in range(9):
    x=-6+k*1.5
    line('PocketStitch'+str(k),[(x,-13.3,87),(x+.7,-13.3,87)],.13,stitch,'spine_02')

# Merge the trouser legs and hips into one continuous garment surface.
pants_parts=[o for o in parts if o.name.startswith('OverallWaist') or o.name.startswith('Trouser_')]
bpy.ops.object.select_all(action='DESELECT')
for o in pants_parts:o.select_set(True)
bpy.context.view_layer.objects.active=pants_parts[0];bpy.ops.object.join();pants=bpy.context.object
parts=[o for o in parts if o not in pants_parts]+[pants]
rem=pants.modifiers.new('Continuous tailored trousers','REMESH');rem.mode='VOXEL';rem.voxel_size=.65
bpy.ops.object.modifier_apply(modifier=rem.name)
smooth=pants.modifiers.new('Relax cloth','SMOOTH');smooth.factor=.65;smooth.iterations=4;bpy.ops.object.modifier_apply(modifier=smooth.name)
dec=pants.modifiers.new('Surface density','DECIMATE');dec.ratio=.60;bpy.ops.object.modifier_apply(modifier=dec.name)
pants['tk_bone']='pelvis';pants['tk_pants']=True
if 'tk_leg' in pants:del pants['tk_leg']
for p in pants.data.polygons:p.use_smooth=True

# Merge fingers into the palm for continuous soft hand silhouettes.
for sign,side in [(-1,'l'),(1,'r')]:
    handparts=[o for o in parts if o['tk_bone']=='hand_'+side or o.name.startswith('Forearm_'+side)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in handparts:o.select_set(True)
    bpy.context.view_layer.objects.active=handparts[0];bpy.ops.object.join();hand=bpy.context.object
    parts=[o for o in parts if o not in handparts]+[hand]
    rem=hand.modifiers.new('Continuous fingers','REMESH');rem.mode='VOXEL';rem.voxel_size=.40
    bpy.ops.object.modifier_apply(modifier=rem.name)
    smooth=hand.modifiers.new('Soft palm','SMOOTH');smooth.factor=.6;smooth.iterations=3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    pivot=Vector((sign*33,-1,73));inv=hand.matrix_world.inverted()
    for v in hand.data.vertices:
        w=hand.matrix_world@v.co;fac=1+.14*max(0,min(1,(76-w.z)/7));v.co=inv@(pivot+(w-pivot)*fac)
    hand['tk_bone']='hand_'+side;hand['tk_hand_union']=side
    for p in hand.data.polygons:p.use_smooth=True

# Cheek tint is actual vertex color and is baked into the shared UV atlas.
for o in parts:
    if o.data.materials[0]!=skin:continue
    attr=o.data.color_attributes.new(name='SkinTint',type='FLOAT_COLOR',domain='CORNER')
    for loop in o.data.loops:
        p=o.matrix_world@o.data.vertices[loop.vertex_index].co
        strength=.42*math.exp(-((abs(p.x)-17)/5)**2-((p.z-125)/4)**2)*max(0,min(1,(-p.y-12)/8))
        base=lin('F0AC74');rosy=lin('E98A66')
        attr.data[loop.index].color=tuple(a*(1-strength)+b*strength for a,b in zip(base,rosy))+(1,)
attrnode=skin.node_tree.nodes.new('ShaderNodeVertexColor');attrnode.layer_name='SkinTint'
skin.node_tree.links.new(attrnode.outputs['Color'],skin.node_tree.nodes['Principled BSDF'].inputs['Base Color'])

# Named deform hierarchy, centimeter units, weighted overlap at the knee.
bpy.ops.object.armature_add(enter_editmode=True);rig=bpy.context.object;rig.name='Armature'
arm=rig.data;arm.edit_bones.remove(arm.edit_bones[0])
def bone(n,h,t,p=None):
    b=arm.edit_bones.new(n);b.head=h;b.tail=t
    if p:b.parent=arm.edit_bones[p]
bone('root',(0,0,0),(0,0,5));bone('pelvis',(0,0,65),(0,0,76),'root')
bone('spine_01',(0,0,76),(0,0,89),'pelvis');bone('spine_02',(0,0,89),(0,0,103),'spine_01')
bone('neck_01',(0,0,103),(0,0,112),'spine_02');bone('head',(0,0,112),(0,0,151),'neck_01')
for sign,side in [(-1,'l'),(1,'r')]:
    bone('upperarm_'+side,(sign*14,0,98),(sign*25,0,85),'spine_02')
    bone('lowerarm_'+side,(sign*25,0,85),(sign*33,-1,73),'upperarm_'+side)
    bone('hand_'+side,(sign*33,-1,73),(sign*36,-1,66),'lowerarm_'+side)
    bone('thigh_'+side,(sign*10.5,0,65),(sign*10.5,0,43),'pelvis')
    bone('calf_'+side,(sign*10.5,0,43),(sign*10.5,0,18),'thigh_'+side)
    bone('foot_'+side,(sign*10.5,0,18),(sign*10.5,-12,7),'calf_'+side)
bpy.ops.object.mode_set(mode='OBJECT')
for o in parts:
    group=o.vertex_groups.new(name=o['tk_bone'])
    group.add(range(len(o.data.vertices)),1,'REPLACE')
    if o.get('tk_leg'):
        side=o['tk_leg'];g=o.vertex_groups.new(name='calf_'+side)
        for v in o.data.vertices:
            z=(o.matrix_world@v.co).z;w=max(0,min(1,(50-z)/14));group.add([v.index],1-w,'REPLACE');g.add([v.index],w,'REPLACE')
    if o.get('tk_hand_union'):
        side=o['tk_hand_union'];g=o.vertex_groups.new(name='lowerarm_'+side)
        for v in o.data.vertices:
            z=(o.matrix_world@v.co).z;w=max(0,min(1,(z-71)/6));group.add([v.index],1-w,'REPLACE');g.add([v.index],w,'REPLACE')
    if o.get('tk_pants'):
        gs={n:o.vertex_groups.new(name=n) for n in ('thigh_l','thigh_r','calf_l','calf_r')}
        for v in o.data.vertices:
            p=o.matrix_world@v.co;side='l' if p.x<0 else 'r'
            pelvis=max(0,min(1,(p.z-57)/10));calf=max(0,min(1,(50-p.z)/14))
            group.add([v.index],pelvis,'REPLACE')
            gs['thigh_'+side].add([v.index],(1-pelvis)*(1-calf),'REPLACE')
            gs['calf_'+side].add([v.index],(1-pelvis)*calf,'REPLACE')
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();body=bpy.context.object;body.name='SK_TownKeeper_Reference03'
scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
# Height normalization in source geometry and skeleton, not only Actor scale.
height=max((body.matrix_world@v.co).z for v in body.data.vertices)-min((body.matrix_world@v.co).z for v in body.data.vertices)
factor=170/height
for v in body.data.vertices:v.co*=factor
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for b in arm.edit_bones:b.head*=factor;b.tail*=factor
bpy.ops.object.mode_set(mode='OBJECT')
body.parent=rig;mod=body.modifiers.new('Deform','ARMATURE');mod.object=rig

def look(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(240,-460,220));cam=bpy.context.object;cam.name='ReferenceCamera';cam.data.type='ORTHO';cam.data.ortho_scale=205;look(cam,(0,0,85));scene.camera=cam
for name,loc,power,size in [('Key',(-200,-280,330),1500000,230),('Fill',(250,-160,170),650000,180),('Rim',(50,220,290),1100000,150)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc;look(o,(0,0,85))
bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-.3));ground=bpy.context.object;ground.name='StudioGround'
ground.data.materials.append(mat('Studio','D9CABB',.9))
scene.render.image_settings.file_format='PNG'
rig.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TownKeeper_Reference03.blend'))
for view,loc in [('Beauty',(230,-460,205)),('Front',(0,-500,87)),('Side',(500,0,87)),('Back',(0,500,87))]:
    cam.location=loc;look(cam,(0,0,85));scene.render.filepath=str(OUT/(view+'.png'));bpy.ops.render.render(write_still=True)
cam.location=(230,-460,205);look(cam,(0,0,85))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TownKeeper_Reference03.blend'))
result={'blend':str(OUT/'TownKeeper_Reference03.blend'),'vertices':len(body.data.vertices),'height_cm':170,'bones':len(arm.bones),'animations':len(bpy.data.actions)}
