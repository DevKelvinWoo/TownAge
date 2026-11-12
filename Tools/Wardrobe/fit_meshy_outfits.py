"""Fit approved Meshy garment meshes to the existing TownKeeper FBX rig in Blender."""

import json
from pathlib import Path
import re

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/Rigged_Final.fbx'
HAIR_MASK = ROOT / 'Saved/Customization/T_HairDyeMask.png'
OUTPUT = ROOT / 'Saved/Wardrobe/Fitted'
DRESS = 'PinkDress'
OVERALLS = 'YellowOveralls'


def pixels(image):
    w, h = image.size
    data = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(data)
    return data.reshape(h, w, 4)


def sample(data, uv):
    h, w, _ = data.shape
    return data[int(uv.y % 1 * h), int(uv.x % 1 * w)]


def base_color(material):
    nodes = material.node_tree.nodes
    shader = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
    node = shader.inputs['Base Color'].links[0].from_node
    nodes.active = node
    return node.image


def analyze_body(body, name):
    mesh = body.data
    mesh.calc_loop_triangles()
    world = [body.matrix_world @ v.co for v in mesh.vertices]
    original = pixels(base_color(mesh.materials[0]))
    mask_image = bpy.data.images.load(str(HAIR_MASK))
    mask = pixels(mask_image)
    uv_layer = mesh.uv_layers.active.data
    transfer_faces = []
    replaced_faces = []
    for tri in mesh.loop_triangles:
        center = sum((world[i] for i in tri.vertices), Vector()) / 3
        x, y, z = center
        uv = sum((uv_layer[i].uv for i in tri.loops), Vector((0, 0))) / 3
        r, g, b, _ = sample(original, uv)
        if .925 < z < 1.055 and abs(x) < .155 and r > g * 1.52 and g < b * 1.2 and r > .55:
            replaced_faces.append(tri.polygon_index)
            continue
        brown = r > g * 1.42 and g > b * 1.12 and r - g > .035
        hair = (z > .35 and (sample(mask, uv)[0] > .5 or (brown and (abs(x) > .21 or y > .015))))
        if not hair and .19 < z < 1.02:
            transfer_faces.append(tuple(tri.vertices))
        if hair or z >= .994:
            continue
        skin = r > g * 1.18 and g > b * 1.11 and r > .6
        if abs(x) > .39 or (abs(x) > .225 and skin and z < .82):
            continue
        if z > .943 and abs(x) < .095 and skin:
            continue
        if name == DRESS and z <= .352:
            continue
        if name == OVERALLS and z <= .212:
            continue
        replaced_faces.append(tri.polygon_index)
    assert len(replaced_faces) > 1000 and len(transfer_faces) > 1000
    return world, transfer_faces, set(replaced_faces)


def fit_points(garment, name):
    world = garment.matrix_world.copy()
    low = min((world @ v.co).z for v in garment.data.vertices)
    high = max((world @ v.co).z for v in garment.data.vertices)
    garment.parent = None
    garment.matrix_world = Matrix.Identity(4)
    for vertex in garment.data.vertices:
        x, y, z = world @ vertex.co
        t = (z - low) / (high - low)
        if name == DRESS:
            knots = [0, .50, .61, .70, .87, 1]
            z = np.interp(t, knots, [.338, .59, .676, .75, .897, .989])
            width = np.interp(t, knots, [.76, .91, 1.12, 1.04, 1.04, .92])
            depth = np.interp(t, knots, [.65, .77, 1.19, 1.04, 1.06, 1.01])
            y = y * depth - np.interp(t, knots, [.143, .13, .10, .108, .14, .145])
        else:
            knots = [0, .35, .47, .66, .78, .87, 1]
            z = np.interp(t, knots, [.201, .375, .452, .657, .752, .866, .989])
            width = np.interp(t, knots, [1.22, 1.33, 1.38, 1.32, 1.58, 1.53, 1.12])
            y = y * np.interp(t, knots, [1.17, 1.26, 1.48, 1.45, 1.24, 1.24, 1.15]) - .137
        # Extend the cuffs a little along the arm to cover the cut boundary.
        cuff = np.clip((abs(x) * width - .18) / .12, 0, 1) * np.clip((.89 - z) / .11, 0, 1)
        if .71 < z < .89:
            x += np.copysign(.018 * cuff, x)
            z -= .016 * cuff
        vertex.co = (x * width - .010, y, z)


def blended_weights(indices, barycentric, body_weights):
    weights = {}
    for index, multiplier in zip(indices, barycentric):
        for name, value in body_weights[index]:
            weights[name] = weights.get(name, 0) + value * max(multiplier, 0)
    return weights


def assign_weights(garment, body, rig, world, faces, name):
    tree = BVHTree.FromPolygons(world, faces, all_triangles=True)
    body_weights = [[(body.vertex_groups[g.group].name, g.weight) for g in v.groups]
                    for v in body.data.vertices]
    groups = {b.name: garment.vertex_groups.new(name=b.name) for b in rig.data.bones}
    for vertex in garment.data.vertices:
        x, y, z = vertex.co
        hit, _, face, _ = tree.find_nearest(vertex.co)
        indices = faces[face]
        a, b, c = [world[i] for i in indices]
        barycentric = geometry.barycentric_transform(hit, a, b, c, Vector((1, 0, 0)),
                                                      Vector((0, 1, 0)), Vector((0, 0, 1)))
        weights = blended_weights(indices, barycentric, body_weights)
        if name == DRESS and z < .655:
            side = 'LeftUpLeg' if x > 0 else 'RightUpLeg'
            thigh = np.interp(z, [.33, .55, .655], [.30, .16, 0])
            weights = {'Hips': 1 - thigh, side: thigh}
        if name == OVERALLS and z < .59:
            side = 'Left' if x > -.010 else 'Right'
            lower = np.interp(z, [.19, .25, .36, .59], [1, .92, 0, 0])
            pelvis = np.interp(z, [.39, .59], [0, 1])
            weights = {side + 'Leg': lower, 'Hips': pelvis, side + 'UpLeg': 1 - lower - pelvis}
        strongest = sorted(((key, value) for key, value in weights.items()
                            if value > .003 and key in groups), key=lambda row: -row[1])[:4]
        total = sum(value for _, value in strongest)
        assert total > 0
        for bone, value in strongest:
            groups[bone].add([vertex.index], value / total, 'REPLACE')


def trim_body(body, faces):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(faces)], context='FACES')
    bm.to_mesh(body.data)
    bm.free()


def render_views(directory):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    shading = scene.display.shading
    shading.color_type = 'TEXTURE'
    shading.light = 'STUDIO'
    shading.show_cavity = True
    scene.render.resolution_x = 560
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new('ReviewCamera', bpy.data.cameras.new('ReviewCamera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.92
    target = Vector((0, 0, .85))
    for label, direction in [('front', (0, -1, .02)), ('side', (1, 0, .02)),
                             ('back', (0, 1, .02)), ('three_quarter', (.5, -1, .12))]:
        camera.location = target + Vector(direction) * 3
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(directory / f'{label}.png')
        bpy.ops.render.render(write_still=True)


def preserve_fbx_root(path):
    # Unreal's legacy Blender FBX path removes an object named Armature.
    # Meshy's original FBX retains it, so mark this processed export as TownAge.
    data = path.read_bytes()
    data, count = re.subn(rb'(CreatorS.{4})Blender(?= \(stable FBX IO\))', rb'\g<1>TownAge',
                          data, flags=re.DOTALL)
    assert count == 2, 'Unexpected FBX creator metadata'
    path.write_bytes(data)


def fit(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    directory = OUTPUT / name
    directory.mkdir(parents=True, exist_ok=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE))
    body = next(obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
    rig = next(obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    world, transfer_faces, replaced_faces = analyze_body(body, name)
    garment_source = ROOT / 'Saved/Meshy/Wardrobe' / name / 'v02/source.glb'
    bpy.ops.import_scene.gltf(filepath=str(garment_source))
    garment = next(obj for obj in bpy.context.selected_objects if obj.type == 'MESH')
    garment.data.calc_loop_triangles()
    source_triangles = len(garment.data.loop_triangles)
    garment.data.materials[0].name = 'OutfitFabric'
    texture = base_color(garment.data.materials[0])
    texture.filepath_raw = str(directory / f'T_{name}_BaseColor.png')
    texture.file_format = 'PNG'
    texture.save()
    fit_points(garment, name)
    assign_weights(garment, body, rig, world, transfer_faces, name)
    trim_body(body, replaced_faces)
    garment.data.uv_layers.active.name = body.data.uv_layers.active.name
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    garment.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = f'SK_{name}'
    body.data.calc_loop_triangles()
    assert [m.name for m in body.data.materials] == ['Material_0', 'OutfitFabric']
    rig.select_set(True)
    filename = directory / f'SK_{name}.fbx'
    bpy.ops.export_scene.fbx(filepath=str(filename), use_selection=True,
                             object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True,
                             apply_scale_options='FBX_SCALE_NONE', axis_forward='-Z', axis_up='Y',
                             add_leaf_bones=False, armature_nodetype='NULL',
                             mesh_smooth_type='FACE', bake_anim=False)
    preserve_fbx_root(filename)
    report = {'outfit': name, 'garment_triangles': source_triangles,
              'outfit_character_triangles': len(body.data.loop_triangles),
              'removed_body_faces': len(replaced_faces), 'bone_count': len(rig.data.bones)}
    (directory / 'fit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(report, flush=True)
    render_views(directory)


for outfit in (DRESS, OVERALLS):
    fit(outfit)
