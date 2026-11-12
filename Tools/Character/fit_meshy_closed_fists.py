"""Fit Meshy fist meshes to the existing weighted TownKeeper meshes."""

import json
import math
from pathlib import Path
import re

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
JOB = ROOT / 'Saved/Meshy/TownKeeper_ClosedFists'
OUT = JOB / 'fitted_v003'
SOURCE = JOB / 'candidate_v001/source.glb'
MODELS = {
    'TownKeeper': ROOT / 'ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/Rigged_Final.fbx',
    **{name: ROOT / 'Saved/Wardrobe/Fitted' / name / f'SK_{name}.fbx'
       for name in ('PinkDress', 'YellowOveralls')},
}
HANDS = ('LeftHand', 'RightHand')


def smooth(t):
    t = max(0., min(1., t))
    return t * t * (3. - 2. * t)


def mesh_geometry(bm):
    return [*bm.verts, *bm.edges, *bm.faces]


def main_wrist_loop(edges, to_hand):
    pending = set(edges)
    loops = []
    while pending:
        seed = pending.pop()
        queue = [seed]
        component = [seed]
        while queue:
            for v in queue.pop().verts:
                for edge in v.link_edges:
                    if edge in pending:
                        pending.remove(edge)
                        queue.append(edge)
                        component.append(edge)
        vertices = {v for edge in component for v in edge.verts}
        if len(component) >= 6 and len(vertices) == len(component):
            center = sum((to_hand @ v.co for v in vertices), Vector()) / len(vertices)
            loops.append((len(component), -math.hypot(center.x, center.z), component))
    assert loops, 'The retained wrist has no closed boundary'
    return max(loops, key=lambda item: item[:2])[2]


def extract_meshy_hands():
    """Extract actual Meshy hands by cutting a plane through the two wrists."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    coords = [obj.matrix_world @ v.co for v in bm.verts]
    low, high = min(p.z for p in coords), max(p.z for p in coords)
    for vert, p in zip(bm.verts, coords):
        vert.co = Vector((p.x, p.y, p.z - low)) * (170. / (high - low))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.002)
    cut_height = .329 * 170.
    bmesh.ops.bisect_plane(bm, geom=mesh_geometry(bm), dist=.001,
                          plane_co=(0, 0, cut_height), plane_no=(0, 0, 1), clear_outer=True)
    components = []
    unseen = set(bm.verts)
    while unseen:
        root = unseen.pop()
        stack = [root]
        component = [root]
        while stack:
            for edge in stack.pop().link_edges:
                for other in edge.verts:
                    if other in unseen:
                        unseen.remove(other)
                        stack.append(other)
                        component.append(other)
        components.append(component)
    hands = {}
    for name, expected_x in zip(HANDS, (.143 * 170, -.160 * 170)):
        eligible = []
        for part in components:
            if len(part) < 50:
                continue
            mean = sum((v.co for v in part), Vector()) / len(part)
            width = max(v.co.x for v in part) - min(v.co.x for v in part)
            if abs(mean.x - expected_x) < 6. and -17. < mean.y < 2. and width < 13.:
                eligible.append((abs(mean.x - expected_x), part))
        assert eligible, (name, 'Meshy hand is not separable at the wrist plane')
        part = min(eligible, key=lambda item: item[0])[1]
        boundary = [v for v in part if abs(v.co.z - cut_height) < .005 and v.is_boundary]
        assert len(boundary) >= 8, (name, len(boundary))
        center = sum((v.co for v in boundary), Vector()) / len(boundary)
        lookup = {v: i for i, v in enumerate(part)}
        faces = {face for v in part for face in v.link_faces}
        vertices = [Vector((-(v.co.x - center.x), cut_height - v.co.z, -(v.co.y - center.y))) for v in part]
        polygons = [tuple(lookup[v] for v in face.verts) for face in faces]
        hands[name] = (vertices, polygons, {lookup[v] for v in boundary})
    bm.free()
    return hands


def fit_hands(rig, mesh, fists):
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    layer = bm.verts.layers.deform.verify()
    uv_layer = bm.loops.layers.uv.active
    assert uv_layer
    report = {}
    for name in HANDS:
        group = mesh.vertex_groups[name].index
        transform = (rig.matrix_world @ rig.data.bones[name].matrix_local).inverted() @ mesh.matrix_world
        inverse = transform.inverted()
        cut = 2.6
        forearm = mesh.vertex_groups[name.replace('Hand', 'ForeArm')].index
        def in_hand_region(face):
            center = transform @ face.calc_center_median()
            if not (-3. < center.y < 23. and abs(center.x) < 12. and abs(center.z) < 14.):
                return False
            return (max(v[layer].get(group, 0.) + v[layer].get(forearm, 0.) for v in face.verts) > .015
                    or (center.y >= cut and math.hypot(center.x, center.z) < 9.5))

        faces = [face for face in bm.faces if in_hand_region(face)]
        assert len(faces) > 100
        reference = min(faces, key=lambda f: abs((transform @ f.calc_center_median()).y - 9.3)
                        + .25 * abs((transform @ f.calc_center_median()).z))
        skin_uv = reference.loops[0][uv_layer].uv.copy()
        skin_slot = reference.material_index
        weld = {v for f in faces for v in f.verts}
        bmesh.ops.remove_doubles(bm, verts=list(weld), dist=.001)
        faces = [face for face in bm.faces if in_hand_region(face)]
        geo = {*faces, *(e for f in faces for e in f.edges), *(v for f in faces for v in f.verts)}
        result = bmesh.ops.bisect_plane(bm, geom=list(geo), dist=.00003,
                                       plane_co=inverse @ Vector((0, cut, 0)),
                                       plane_no=(inverse.to_3x3() @ Vector((0, 1, 0))).normalized(),
                                       clear_outer=True)
        # FBX UV seams can leave detached pieces on the distal side of a
        # scoped cut. Remove those original hand vertices before the graft.
        residual = []
        for vertex in bm.verts:
            p = transform @ vertex.co
            if cut + .025 < p.y < 24. and abs(p.x) < 11. and abs(p.z) < 13.:
                if (vertex[layer].get(group, 0.) + vertex[layer].get(forearm, 0.) > .001
                    or math.hypot(p.x, p.z) < 8.5):
                    residual.append(vertex)
        if residual:
            bmesh.ops.delete(bm, geom=residual, context='VERTS')
        wrist_edges = [edge for edge in result['geom_cut'] if isinstance(edge, bmesh.types.BMEdge)
                       and edge.is_valid and edge.is_boundary]
        wrist_edges = main_wrist_loop(wrist_edges, transform)
        ring = {v for edge in wrist_edges for v in edge.verts}
        wrist = [transform @ v.co for v in ring]
        cx = sum(p.x for p in wrist) / len(wrist)
        cz = sum(p.z for p in wrist) / len(wrist)
        source, polygons, border = fists[name]
        old_radius = sum(math.hypot(p.x - cx, p.z - cz) for p in wrist) / len(wrist)
        new_radius = sum(math.hypot(source[i].x, source[i].z) for i in border) / len(border)
        scale = max(.78, min(1.28, old_radius / new_radius))
        wrist_scale = min(1., (new_radius * scale) / old_radius)
        for v in bm.verts:
            if v[layer].get(group, 0.) + v[layer].get(forearm, 0.) <= .015:
                continue
            p = transform @ v.co
            if not cut - 2.7 < p.y <= cut + .012 or math.hypot(p.x - cx, p.z - cz) > old_radius * 2.:
                continue
            strength = smooth((p.y - cut + 2.7) / 2.7)
            factor = 1. + (wrist_scale - 1.) * strength
            v.co = inverse @ Vector((cx + (p.x - cx) * factor, p.y, cz + (p.z - cz) * factor))
            for face in v.link_faces:
                face.smooth = True
        new = []
        for p in source:
            point = inverse @ Vector((cx + p.x * scale, cut + .72 + p.y * .67, cz + p.z * scale))
            v = bm.verts.new(point)
            v[layer][group] = 1.
            new.append(v)
        for ids in polygons:
            f = bm.faces.new([new[i] for i in ids])
            f.smooth = True
            f.material_index = skin_slot
            for loop in f.loops:
                loop[uv_layer].uv = skin_uv
        end = {new[i] for i in border}
        new_edges = {edge for v in end for edge in v.link_edges
                     if edge.is_boundary and all(point in end for point in edge.verts)}
        assert len(new_edges) >= 8
        joined = bmesh.ops.bridge_loops(bm, edges=wrist_edges + list(new_edges))['faces']
        assert joined, (name, 'Wrist join failed')
        for face in joined:
            face.material_index = skin_slot
            face.smooth = True
            for loop in face.loops:
                loop[uv_layer].uv = skin_uv
        report[name] = {'meshy_vertices': len(new), 'wrist_bridge_faces': len(joined),
                        'removed_residual_vertices': len(residual),
                        'scale': scale}
    bm.normal_update()
    bm.to_mesh(mesh.data)
    bm.free()
    mesh.data.update()
    return report

def save_fbx(rig, mesh, path):
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE', 'MESH'},
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
                             axis_forward='-Z', axis_up='Y', add_leaf_bones=False,
                             armature_nodetype='NULL', mesh_smooth_type='FACE', bake_anim=False)
    data, count = re.subn(rb'(CreatorS.{4})Blender(?= \(stable FBX IO\))', rb'\g<1>TownAge',
                          path.read_bytes(), flags=re.DOTALL)
    assert count == 2
    path.write_bytes(data)


def render(name):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.light = 'STUDIO'
    scene.render.resolution_x, scene.render.resolution_y = 800, 560
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new('FistReview', bpy.data.cameras.new('FistReview'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 1.22
    target = Vector((0., -.11, .68))
    for view, position in [('front', (.03, -3., 1.0)), ('angle', (1.45, -2.6, 1.04))]:
        camera.location = position
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(OUT / f'{name}_{view}.png')
        bpy.ops.render.render(write_still=True)


OUT.mkdir(parents=True, exist_ok=True)
fists = extract_meshy_hands()
report = {}
for name, source in MODELS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    report[name] = fit_hands(rig, mesh, fists)
    save_fbx(rig, mesh, OUT / f'SK_{name}_ClosedFists.fbx')
    render(name)
(OUT / 'fit_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
