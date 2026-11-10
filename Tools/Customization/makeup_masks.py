"""Bake soft face-only makeup masks from the approved rig; no geometry edits.

Run in isolated Blender background mode. Generated masks/renders remain local.
A = blush / upper liner / iris / aegyo highlight.
B = aegyo shadow / jaw contour / nose contour / face skin.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Customization/Makeup'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/Rigged_Final.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.polygons))
material = mesh.data.materials[0]
bsdf = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
base_node = bsdf.inputs['Base Color'].links[0].from_node
base = base_node.image
width, height = base.size
pixels = np.array(base.pixels[:], dtype=np.float32).reshape(height, width, 4)
positions = np.zeros((height, width, 3), dtype=np.float32)
occupied = np.zeros((height, width), dtype=bool)
head_influence = np.zeros((height, width), dtype=np.float32)
mesh.data.calc_loop_triangles()
uv = mesh.data.uv_layers.active.data
vertices = np.array([v.co[:] for v in mesh.data.vertices], dtype=np.float32)
head_group = mesh.vertex_groups.get('Head')
assert head_group is not None, 'Retained face mask requires the approved Head group'
head_weights = np.array([next((g.weight for g in vertex.groups if g.group == head_group.index),0.)
                         for vertex in mesh.data.vertices],dtype=np.float32)
for triangle in mesh.data.loop_triangles:
    tex = np.array([uv[i].uv[:] for i in triangle.loops], dtype=np.float64) * [width, height]
    lo = np.maximum(np.floor(tex.min(0)).astype(int), 0)
    hi = np.minimum(np.ceil(tex.max(0)).astype(int), [width-1, height-1])
    if np.any(hi < lo):
        continue
    a, c, d = tex
    den = (c[1]-d[1])*(a[0]-d[0]) + (d[0]-c[0])*(a[1]-d[1])
    if abs(den) < 1.e-10:
        continue
    xx, yy = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
    u = ((c[1]-d[1])*(xx-d[0]) + (d[0]-c[0])*(yy-d[1]))/den
    v = ((d[1]-a[1])*(xx-d[0]) + (a[0]-d[0])*(yy-d[1]))/den
    w = 1-u-v
    inside = (u >= -1.e-7) & (v >= -1.e-7) & (w >= -1.e-7)
    region = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    sampled = u[...,None]*vertices[triangle.vertices[0]] + v[...,None]*vertices[triangle.vertices[1]] + w[...,None]*vertices[triangle.vertices[2]]
    positions[region][inside] = sampled[inside]
    weights = head_weights[list(triangle.vertices)]
    sampled_head = u*weights[0]+v*weights[1]+w*weights[2]
    head_influence[region][inside] = sampled_head[inside]
    occupied[region] |= inside
x, y, z = positions.transpose(2,0,1)
r, g, b = pixels[:,:,:3].transpose(2,0,1)
ax = np.abs(x)
front = occupied & (ax < 29) & (y < -18) & (z > 93) & (z < 145)
skin = front & (r > .25) & (g > .12) & (b > .07) & (r > g*1.06) & (g > b*1.03) & (r < g*2.0)
# The old broad low-face gate included pink scarf texels behind the chin.
# Retained head weights and a center-neck exclusion keep strong contour on skin.
skin &= ((z >= 106.) | (head_influence > .88))
skin &= ~((z < 101.) & (ax < 18.))
head_feather = np.maximum(np.clip((head_influence-.88)/.08,0,1),np.clip((z-104.)/3.,0,1))
neck_feather = np.maximum(np.clip((z-101.)/2.,0,1),np.clip((ax-18.)/2.,0,1))
skin_weight = skin * head_feather * neck_feather
dark = front & (r < .25) & (g < .18) & (b < .12)
hist = {}
for label, selection in [('skin',skin),('dark',dark),('brown_eye',dark & (r > g*1.2) & (g > .012))]:
    hist[label] = [{'z': zz, 'count': int((selection & (z>=zz) & (z<zz+2)).sum())} for zz in range(94,144,2)]
(OUT/'landmark_histogram.json').write_text(json.dumps(hist,indent=2),encoding='utf8')
np.savez_compressed(OUT/'face_raster.npz', positions=positions, pixels=pixels, occupied=occupied)

def gauss(cx, cz, sx, sz):
    return np.exp(-.5*((ax-cx)/sx)**2-.5*((z-cz)/sz)**2)

blush = gauss(22.,109.,5.2,3.8) * skin_weight
lash_region = front & (ax > 5.5) & (ax < 23.5) & (z > 125.) & (z < 133.)
lash_pigment = lash_region & (r < .19) & (g < .10) & (b < .075)
liner = lash_pigment.astype(np.float32)
# A connected three-texel feather gives the upper range a visible width change
# while following the actual painted lash, never a detached guessed arc.
expanded = lash_pigment.copy()
for edge_weight in [.65,.35,.12]:
    padded = np.pad(expanded,1)
    expanded = np.logical_or.reduce([padded[1+dy:height+1+dy,1+dx:width+1+dx]
                                    for dx in (-1,0,1) for dy in (-1,0,1)])
    liner = np.maximum(liner,expanded.astype(np.float32)*edge_weight)
liner *= lash_region
iris_region = ((ax-14.)**2/5.8**2+(z-119.5)**2/8.8**2 < 1.) & front & (z < 125.3)
iris_brown = (r > g*1.2) & (g > b*1.1) & (g < .35)
pupil = np.exp(-.5*((ax-14.)/3.1)**2-.5*((z-122.2)/5.2)**2)
iris = iris_region * iris_brown * np.clip((g-.020)/.035,0,1) * (1-pupil)
# Trace the actual painted lower-eye border rather than drawing a flat line
# through the cheeks. Its shallow highlight and shadow suggest natural volume.
eye_white = (r > .55) & (g > .50) & (b > .30) & (np.abs(r-g) < .12)
eye_paint = front & (ax > 6.) & (ax < 22.) & (z > 110.) & (z < 130.) & (dark | eye_white)
eye_x = np.linspace(6.25,21.75,32)
lower_eye=[]
for center_x in eye_x:
    values=z[eye_paint & (np.abs(ax-center_x)<.35)]
    lower_eye.append(float(np.percentile(values,5)) if len(values)>5 else 114.)
lower_eye=np.convolve(np.pad(lower_eye,2,mode='edge'),np.ones(5)/5,mode='valid')
lower_border=np.interp(ax,eye_x,lower_eye)
eye_falloff=np.exp(-.5*((ax-14.)/4.2)**2) * ((ax>7)&(ax<21))
aegyo = np.exp(-.5*((z-(lower_border-.65))/.55)**2) * eye_falloff * skin_weight
aegyo_shadow = np.exp(-.5*((z-(lower_border-1.6))/.45)**2) * eye_falloff * skin_weight
jaw = gauss(23.,102.5,5.5,2.7) * skin_weight
nose = (gauss(3.5,115.5,1.1,5.1) + .5*gauss(0.,109.5,2.6,1.)) * skin_weight
A = np.stack([blush,liner,iris,aegyo],axis=2).astype(np.float32)
B = np.stack([aegyo_shadow,np.clip(jaw,0,1),np.clip(nose,0,1),skin],axis=2).astype(np.float32)
hair_source=ROOT/'Saved/Customization/T_HairDyeMask.png'
assert hair_source.is_file(), 'Generate the retained hair mask before makeup masks'
hair_image=bpy.data.images.load(str(hair_source),check_existing=False)
hair_image.colorspace_settings.name='Non-Color'
hair_pixels=np.array(hair_image.pixels[:],dtype=np.float32).reshape(height,width,4)[:,:,0]
A *= (1-hair_pixels[:,:,None])
B *= (1-hair_pixels[:,:,None])
assert not np.any(A[hair_pixels>.99]) and not np.any(B[hair_pixels>.99])
protected_neck = occupied & (z < 101.) & (ax < 18.)
assert not np.any(A[protected_neck]) and not np.any(B[protected_neck]), 'Makeup entered center neck/scarf'


def pad_uv_gutters(packed):
    # Only unused UV texels may grow. This supplies bilinear samples at island
    # edges without changing any occupied non-target face/body/hair texel.
    result=packed.copy()
    for channel in range(4):
        values=packed[:,:,channel].copy()
        protected=(occupied & (values<=1.e-6)) | (hair_pixels>.001)
        safety=np.pad(protected,1)
        protected=np.logical_or.reduce([safety[1+dy:height+1+dy,1+dx:width+1+dx]
                                        for dx in (-1,0,1) for dy in (-1,0,1)])
        allowed=~occupied & ~protected
        for _ in range(2):
            padded=np.pad(values,1)
            expanded=np.maximum.reduce([padded[1+dy:height+1+dy,1+dx:width+1+dx]
                                        for dx in (-1,0,1) for dy in (-1,0,1)])
            values[allowed]=expanded[allowed]
        result[:,:,channel]=values
    assert np.array_equal(result[occupied],packed[occupied]), 'UV padding changed occupied geometry'
    assert not np.any(result[hair_pixels>.99]), 'UV padding entered retained hair'
    return result


A=pad_uv_gutters(A)
B=pad_uv_gutters(B)

def save_image(name, rgba, noncolor=False):
    image = bpy.data.images.new(name,width=width,height=height,alpha=True)
    if noncolor:
        image.colorspace_settings.name='Non-Color'
        image.alpha_mode='CHANNEL_PACKED'
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw=str(OUT/(name+'.png'))
    image.file_format='PNG'
    image.save()
    if noncolor:
        check=bpy.data.images.load(image.filepath_raw,check_existing=False)
        check.colorspace_settings.name='Non-Color'
        check.alpha_mode='CHANNEL_PACKED'
        restored=np.array(check.pixels[:],dtype=np.float32).reshape(height,width,4)
        assert np.max(np.abs(restored-rgba)) < .02, 'Packed mask channels changed on PNG roundtrip'
        bpy.data.images.remove(check)
    return image

save_image('T_MakeupMaskA',A,True)
save_image('T_MakeupMaskB',B,True)

def makeup(blush_amount=0.,liner_amount=0.,iris_amount=0.,aegyo_amount=0.,jaw_amount=0.,nose_amount=0.,
           blush_tint=(.70,.24,.31),iris_tint=(.30,.19,.065)):
    result=pixels.copy()
    rgb=result[:,:,:3]
    def gain(amount,soft,strong):
        return soft*amount+(strong-soft)*amount**4
    def blend(color, alpha):
        nonlocal rgb
        alpha=np.clip(alpha,0.,1.)
        rgb=rgb*(1-alpha[...,None])+np.asarray(color)*alpha[...,None]
    blend(blush_tint,A[:,:,0]*gain(blush_amount,.32,.90))
    blend([.008,.004,.003],A[:,:,1]*gain(liner_amount,.65,1.))
    luma=np.clip((pixels[:,:,:3]*np.asarray([.299,.587,.114])).sum(2)*2.8+.18,.2,.85)
    iris_color=luma[:,:,None]*np.array(iris_tint)
    alpha=np.clip(A[:,:,2]*gain(iris_amount,.85,1.60),0.,1.)
    rgb=rgb*(1-alpha[:,:,None])+iris_color*alpha[:,:,None]
    blend(rgb+(1-rgb)*np.asarray([.85,.70,.50]),A[:,:,3]*gain(aegyo_amount,.18,.45))
    blend([.33,.23,.20],B[:,:,0]*gain(aegyo_amount,.08,.35))
    blend([.34,.25,.22],B[:,:,1]*gain(jaw_amount,.20,1.80))
    blend([.34,.25,.22],B[:,:,2]*gain(nose_amount,.18,.75))
    result[:,:,:3]=rgb
    assert np.array_equal(result[occupied & ~front],pixels[occupied & ~front]), 'Makeup escaped the face geometry'
    return result

nodes=material.node_tree.nodes
output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
emission=nodes.new('ShaderNodeEmission')
material.node_tree.links.new(base_node.outputs['Color'],emission.inputs['Color'])
material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=640;scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('MakeupQA_World');scene.world.color=(.025,.03,.025)
scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='PNG'
camera_data=bpy.data.cameras.new('MakeupQA_Camera')
camera=bpy.data.objects.new('MakeupQA_Camera',camera_data)
scene.collection.objects.link(camera);scene.camera=camera
target=mesh.matrix_world @ Vector((0,-14,124))
camera.location=target+Vector((0,-3.5,0))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=.95
presets={'Original':{},'Natural':dict(blush_amount=.30,liner_amount=.25,iris_amount=.35,aegyo_amount=.30,jaw_amount=.20,nose_amount=.20),
         'Strong':dict(blush_amount=1.,liner_amount=1.,iris_amount=1.,aegyo_amount=1.,jaw_amount=1.,nose_amount=1.,iris_tint=(.12,.20,.29)),
         'Blush':dict(blush_amount=1),'Liner':dict(liner_amount=1),'Iris':dict(iris_amount=1,iris_tint=(.16,.23,.14)),
         'Aegyo':dict(aegyo_amount=1),'Jaw':dict(jaw_amount=1),'Nose':dict(nose_amount=1)}
for label,values in presets.items():
    qa=save_image('MakeupQA_'+label,makeup(**values))
    base_node.image=qa
    scene.render.filepath=str(OUT/('Makeup_'+label+'.png'))
    bpy.ops.render.render(write_still=True)
comparison=[]
for label in ['Original','Natural']:
    rendered=bpy.data.images.load(str(OUT/('Makeup_'+label+'.png')),check_existing=False)
    comparison.append(np.array(rendered.pixels[:],dtype=np.float32).reshape(720,640,4))
compare=bpy.data.images.new('Original_Left_Natural_Right',width=1280,height=720,alpha=True)
compare.pixels.foreach_set(np.concatenate(comparison,axis=1).ravel())
compare.filepath_raw=str(OUT/'Comparison_Original_Left_Natural_Right.png')
compare.file_format='PNG';compare.save()
strong=bpy.data.images.load(str(OUT/'Makeup_Strong.png'),check_existing=False)
strong_pixels=np.array(strong.pixels[:],dtype=np.float32).reshape(720,640,4)
compare=bpy.data.images.new('Before_Left_Maximum_Right',width=1280,height=720,alpha=True)
compare.pixels.foreach_set(np.concatenate([comparison[0],strong_pixels],axis=1).ravel())
compare.filepath_raw=str(OUT/'Comparison_Before_Left_Maximum_Right.png')
compare.file_format='PNG';compare.save()
diff_report={}
for label,values in presets.items():
    if label=='Original':continue
    changed=makeup(**values)[:,:,:3]-pixels[:,:,:3]
    delta=np.max(np.abs(changed),axis=2)
    diff_report[label]={'mean_abs_rgb':float(np.abs(changed).mean()),
                        'max_abs_rgb':float(delta.max()),
                        'pixels_over_1byte':int((delta>1/255).sum()),
                        'pixels_over_05':int((delta>.05).sum())}
(OUT/'strength_difference_report.json').write_text(json.dumps(diff_report,indent=2),encoding='utf8')
report={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'geometry_modified':False,'new_model_required':False,'resolution':[width,height],
        'packed_png_roundtrip_verified':True,
        'hair_and_nonface_exclusion_verified':True,
        'lower_face_head_weight_and_neck_exclusion':True,
        'unoccupied_uv_gutter_padding_pixels':2,
        'natural_preset':dict(blush_color=[.70,.24,.31],iris_color=[.30,.19,.065],amounts=[30,25,35,30,20,20]),
        'intensity_mapping':'soft*s+(strong-soft)*s^4; masked alpha clamped0..1',
        'mask_A':['blush','upper_liner','iris','aegyo_highlight'],
        'mask_B':['aegyo_shadow','jaw','nose','skin'],
        'coverage_A':[int((A[:,:,i]>.02).sum()) for i in range(4)],
        'coverage_B':[int((B[:,:,i]>.02).sum()) for i in range(4)]}
(OUT/'makeup_mask_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('MAKEUP_MASKS_COMPLETE',json.dumps(report))
