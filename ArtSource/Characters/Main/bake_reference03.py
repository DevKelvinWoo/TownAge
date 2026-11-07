"""Bake the reference character into portable UV textures and export cm FBX."""
import bpy, json, math, bmesh
from pathlib import Path
from mathutils import Vector

OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Revision03')
scene=bpy.context.scene
body=next(o for o in scene.objects if o.type=='MESH' and o.name.startswith('SK_TownKeeper_Reference03'))
rig=body.parent
# Remove the disconnected draft rear strap identified by its material and rear position.
bm=bmesh.new();bm.from_mesh(body.data)
bad=set()
for face in bm.faces:
    if 'BagLeather' in body.data.materials[face.material_index].name and all(v.co.y>0 for v in face.verts):bad.update(face.verts)
if bad:bmesh.ops.delete(bm,geom=list(bad),context='VERTS')
bm.to_mesh(body.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008,area_weight=.2,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.bake.use_clear=True;scene.render.bake.margin=8
materials=list(body.data.materials)
original={}
for m in materials:
    nodes=m.node_tree.nodes;output=nodes.get('Material Output');bsdf=nodes.get('Principled BSDF')
    original[m.name]=(output,bsdf)

def target(name,noncolor=False):
    image=bpy.data.images.new(name,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
    for m in materials:
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.name='BakeTarget_'+name;n.image=image
        m.node_tree.nodes.active=n
    return image

base=target('T_TownKeeper_BaseColor')
for m in materials:
    output,bsdf=original[m.name];e=m.node_tree.nodes.new('ShaderNodeEmission');e.name='BakeEmission'
    source=bsdf.inputs['Base Color']
    if source.is_linked:m.node_tree.links.new(source.links[0].from_socket,e.inputs['Color'])
    else:e.inputs['Color'].default_value=source.default_value
    m.node_tree.links.new(e.outputs[0],output.inputs['Surface'])
bpy.ops.object.bake(type='EMIT')
base.filepath_raw=str(OUT/'T_TownKeeper_BaseColor.png');base.file_format='PNG';base.save()

rough=target('T_TownKeeper_Roughness',True)
for m in materials:
    output,bsdf=original[m.name];e=m.node_tree.nodes.get('BakeEmission')
    for link in list(e.inputs['Color'].links):m.node_tree.links.remove(link)
    v=bsdf.inputs['Roughness'].default_value;e.inputs['Color'].default_value=(v,v,v,1)
bpy.ops.object.bake(type='EMIT')
rough.filepath_raw=str(OUT/'T_TownKeeper_Roughness.png');rough.file_format='PNG';rough.save()
for m in materials:
    output,bsdf=original[m.name];m.node_tree.links.new(bsdf.outputs[0],output.inputs['Surface'])
normal=target('T_TownKeeper_Normal_DX',True)
scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='NEG_Y';scene.render.bake.normal_b='POS_Z'
bpy.ops.object.bake(type='NORMAL')
normal.filepath_raw=str(OUT/'T_TownKeeper_Normal_DX.png');normal.file_format='PNG';normal.save()

# Keep source materials as unassigned datablocks; render/export the actual atlas.
atlas=bpy.data.materials.new('M_TownKeeper_Reference03');atlas.use_nodes=True
n=atlas.node_tree.nodes;l=atlas.node_tree.links;bsdf=n.get('Principled BSDF')
for name,img,port in [('BaseColor',base,'Base Color'),('Roughness',rough,'Roughness')]:
    tex=n.new('ShaderNodeTexImage');tex.name=name;tex.image=img;l.new(tex.outputs['Color'],bsdf.inputs[port])
tex=n.new('ShaderNodeTexImage');tex.name='NormalDX';tex.image=normal
sep=n.new('ShaderNodeSeparateColor');combine=n.new('ShaderNodeCombineColor');invert=n.new('ShaderNodeMath');invert.operation='SUBTRACT';invert.inputs[0].default_value=1
l.new(tex.outputs['Color'],sep.inputs[0]);l.new(sep.outputs[0],combine.inputs[0]);l.new(sep.outputs[1],invert.inputs[1]);l.new(invert.outputs[0],combine.inputs[1]);l.new(sep.outputs[2],combine.inputs[2])
norm=n.new('ShaderNodeNormalMap');l.new(combine.outputs[0],norm.inputs['Color']);l.new(norm.outputs[0],bsdf.inputs['Normal'])
bsdf.inputs['Specular IOR Level'].default_value=.22
body.data.materials.clear();body.data.materials.append(atlas)
for p in body.data.polygons:p.material_index=0
for image in (base,rough,normal):image.pack()

bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'SK_TownKeeper_Reference03.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},global_scale=1.0,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,mesh_smooth_type='FACE',use_mesh_modifiers=True,path_mode='AUTO')
height=max((body.matrix_world@v.co).z for v in body.data.vertices)-min((body.matrix_world@v.co).z for v in body.data.vertices)
unweighted=sum(1 for v in body.data.vertices if not v.groups or abs(sum(g.weight for g in v.groups)-1)>1e-4)
body.data.calc_loop_triangles()
manifest={'fbx_path':str(fbx),'blend_path':str(OUT/'TownKeeper_Reference03.blend'),'height_cm':height,'unit_scale':.01,'normal_convention':'DirectX -Y','vertices':len(body.data.vertices),'triangles':len(body.data.loop_triangles),'bone_names':[b.name for b in rig.data.bones],'unweighted_or_unnormalized_vertices':unweighted,'animations':0,'materials':[{'name':'M_TownKeeper_Reference03','slot':'M_TownKeeper_Reference03','basecolor':base.filepath_raw,'roughness':rough.filepath_raw,'normal':normal.filepath_raw}]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# Source file is deliberately self-contained with packed baked images.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TownKeeper_Reference03.blend'))
scene.cycles.samples=32
scene.render.filepath=str(OUT/'Beauty_Baked.png');bpy.ops.render.render(write_still=True)
result=manifest
