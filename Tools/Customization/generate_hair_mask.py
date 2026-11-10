"""Bake a hair-only atlas mask from the retained Meshy rig, without mesh edits.

Run in Blender background: blender --background --factory-startup --python
Tools/Customization/generate_hair_mask.py. Outputs remain in Saved/Customization.
The authored classification is specific to this approved 170cm character.
It combines brown texels with rest-space exclusions, preserving eyes, brows,
skin, scarf, boots and pouch despite the character sharing one atlas/material.
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/Rigged_Final.glb'
OUT = ROOT / 'Saved/Customization'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.polygons))
assert len(mesh.data.materials) == 1
material = mesh.data.materials[0]
bsdf = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
base_node = bsdf.inputs['Base Color'].links[0].from_node
base = base_node.image
width, height = base.size
assert width == height == 2048
pixels = np.array(base.pixels[:], dtype=np.float32).reshape(height, width, 4)
r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
# Skin/cloth are much less red-saturated; the scarf's red has blue near green.
warm_brown = (r > g * 1.45) & (g > b * 1.13) & (r - g > .035) & (g - b > .02)
occupied = np.zeros((height, width), dtype=bool)
eligible = np.zeros((height, width), dtype=bool)
excluded = np.zeros((height, width), dtype=bool)
face_pixels = np.zeros((height, width), dtype=bool)
mesh.data.calc_loop_triangles()
uv = mesh.data.uv_layers.active.data
vertices = np.array([v.co[:] for v in mesh.data.vertices], dtype=np.float32)
assert abs(float(vertices[:, 2].max()) - 170.) < .1, 'Unexpected rest-space scale'

for triangle in mesh.data.loop_triangles:
    tex = np.array([uv[i].uv[:] for i in triangle.loops], dtype=np.float64)
    tex[:, 0] *= width
    tex[:, 1] *= height
    lo = np.maximum(np.floor(tex.min(0)).astype(int), 0)
    hi = np.minimum(np.ceil(tex.max(0)).astype(int), [width - 1, height - 1])
    if np.any(hi < lo):
        continue
    a, c, d = tex
    denominator = (c[1] - d[1]) * (a[0] - d[0]) + (d[0] - c[0]) * (a[1] - d[1])
    if abs(denominator) < 1.e-10:
        continue
    xx, yy = np.meshgrid(np.arange(lo[0], hi[0] + 1) + .5,
                         np.arange(lo[1], hi[1] + 1) + .5)
    u = ((c[1] - d[1]) * (xx - d[0]) + (d[0] - c[0]) * (yy - d[1])) / denominator
    v = ((d[1] - a[1]) * (xx - d[0]) + (a[0] - d[0]) * (yy - d[1])) / denominator
    w = 1. - u - v
    inside = (u >= -1.e-7) & (v >= -1.e-7) & (w >= -1.e-7)
    if not inside.any():
        continue
    positions = vertices[list(triangle.vertices)]
    world = u[..., None] * positions[0] + v[..., None] * positions[1] + w[..., None] * positions[2]
    x, y, z = world[..., 0], world[..., 1], world[..., 2]
    # Protect the dark eyes; the face/eyebrow texture is already rejected by
    # the chroma test. A broad face box would incorrectly remove the fringe.
    front_face = (np.abs(x) < 23.) & (y < -25.) & (z < 131.) & (z > 110.)
    hair_volume = (z > 35.) & ((z > 101.) | (np.abs(x) > 18.) | (y > 6.))
    valid = hair_volume & ~front_face
    view = np.s_[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
    occupied[view] |= inside
    eligible[view] |= inside & valid
    excluded[view] |= inside & ~valid
    face_pixels[view] |= inside & (np.abs(x) < 26.) & (y < -10.) & (z < 143.) & (z > 101.)

mask = eligible & warm_brown & ~excluded
# Facial marks share the brown pigment but form tiny isolated atlas components;
# unlike the broad fringe, they must remain their original color. Run-length
# connected components avoid an external imaging dependency.
parents = []
areas = []
runs = []
previous = []


def find(index):
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


for row in range(height):
    changes = np.diff(np.r_[False, mask[row], False].astype(np.int8))
    starts, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    current = []
    cursor = 0
    for start, end in zip(starts, ends):
        index = len(parents)
        parents.append(index)
        areas.append(int(end - start))
        while cursor < len(previous) and previous[cursor][1] < start:
            cursor += 1
        scan = cursor
        while scan < len(previous) and previous[scan][0] <= end:
            other = find(previous[scan][2])
            own = find(index)
            if other != own:
                parents[other] = own
            scan += 1
        current.append((int(start), int(end), index))
        runs.append((row, int(start), int(end), index))
    previous = current
component_areas = {}
for index, area in enumerate(areas):
    root = find(index)
    component_areas[root] = component_areas.get(root, 0) + area
for row, start, end, index in runs:
    if component_areas[find(index)] < 3500:
        mask[row, start:end] &= ~face_pixels[row, start:end]
original_mask = mask.copy()
# Keep padding away from occupied non-hair texels to prevent neighboring atlas
# islands from tinting boots/skin through bilinear sampling.
protected = occupied & ~mask
for _ in range(2):
    padded = np.pad(protected, 1, mode='constant')
    protected = np.logical_or.reduce([padded[1 + dy:height + 1 + dy, 1 + dx:width + 1 + dx]
                                     for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
# Fill UV gutters only; never dilate across occupied face or clothing texels.
for _ in range(4):
    padded = np.pad(mask, 1, mode='constant')
    expanded = np.zeros_like(mask)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            expanded |= padded[1 + dy:height + 1 + dy, 1 + dx:width + 1 + dx]
    mask |= expanded & ~occupied & ~protected
mask_rgba = np.empty((height, width, 4), dtype=np.float32)
mask_rgba[:, :, :3] = mask[:, :, None]
mask_rgba[:, :, 3] = 1
mask_image = bpy.data.images.new('T_HairDyeMask', width=width, height=height, alpha=False)
mask_image.colorspace_settings.name = 'Non-Color'
mask_image.pixels.foreach_set(mask_rgba.ravel())
mask_image.filepath_raw = str(OUT / 'T_HairDyeMask.png')
mask_image.file_format = 'PNG'
mask_image.save()

# Blue diagnostic atlas/render: all non-hair source texels remain bit-identical.
tinted = pixels.copy()
luminance = (r * .2126 + g * .7152 + b * .0722)
intensity = np.clip(np.sqrt(np.maximum(luminance, 0)) * 1.65, .12, 1.)
tinted[:, :, :3] = np.where(mask[:, :, None],
    intensity[:, :, None] * np.array([.12, .37, 1.], dtype=np.float32), pixels[:, :, :3])
assert np.array_equal(tinted[~mask], pixels[~mask])
qa_image = bpy.data.images.new('HairDye_Blue_QA', width=width, height=height, alpha=True)
qa_image.pixels.foreach_set(tinted.ravel())
qa_image.filepath_raw = str(OUT / 'HairDye_Blue_QA.png')
qa_image.file_format = 'PNG'
qa_image.save()
base_node.image = qa_image
nodes = material.node_tree.nodes
output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
emission = nodes.new('ShaderNodeEmission')
material.node_tree.links.new(base_node.outputs['Color'], emission.inputs['Color'])
material.node_tree.links.new(emission.outputs[0], output.inputs['Surface'])
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new('MaskQA_World')
scene.world.color = (.035, .035, .035)
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
for obj in list(scene.objects):
    if obj.type == 'MESH' and obj != mesh:
        obj.hide_render = True
corners = [mesh.matrix_world @ Vector(corner) for corner in mesh.bound_box]
low = Vector(tuple(min(c[i] for c in corners) for i in range(3)))
high = Vector(tuple(max(c[i] for c in corners) for i in range(3)))
center = (low + high) * .5
model_height = high.z - low.z
camera_data = bpy.data.cameras.new('MaskQA_Camera')
camera = bpy.data.objects.new('MaskQA_Camera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.ortho_scale = model_height * 1.12
for label, direction in [('Front', -1), ('Back', 1)]:
    camera.location = center + Vector((0, direction * model_height * 3, model_height * .02))
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('HairDye_Blue_' + label + '.png'))
    bpy.ops.render.render(write_still=True)

report = {'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'mesh': mesh.name, 'triangles': len(mesh.data.loop_triangles),
          'materials': 1, 'resolution': [width, height],
          'mask_pixels': int(original_mask.sum()), 'gutter_pixels': int((mask & ~original_mask).sum()),
          'non_hair_texels_unchanged_in_QA': True,
          'geometry_skeleton_weights_modified': False,
          'method': 'rest-space exclusion plus warm-brown atlas texels; 4px unoccupied-UV gutter padding',
          'mask': str(OUT / 'T_HairDyeMask.png')}
(OUT / 'hair_mask_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('HAIR_MASK_GENERATED', json.dumps(report))
