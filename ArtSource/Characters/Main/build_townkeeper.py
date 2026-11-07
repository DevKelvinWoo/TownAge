import bpy
import bmesh
import math
from pathlib import Path
from mathutils import Vector


ROOT = Path(r"C:\Users\Kelvin\Desktop\TownAge")
SOURCE_DIR = ROOT / "ArtSource" / "Characters" / "Main"
BLEND_PATH = SOURCE_DIR / "CHR_Main_TownKeeper.blend"
FBX_PATH = SOURCE_DIR / "SK_TownKeeper.fbx"
PREVIEW_PATH = SOURCE_DIR / "CHR_Main_TownKeeper_Preview.png"


def clear_scene():
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def make_material(name, color, roughness=0.72, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def finish_object(obj, material, bone_name):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(material)
    group = obj.vertex_groups.new(name=bone_name)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    obj["townage_bind_bone"] = bone_name
    pieces.append(obj)
    return obj


def add_sphere(name, location, scale, material, bone_name, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return finish_object(obj, material, bone_name)


def add_upper_sphere(name, location, scale, material, bone_name):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    lower_vertices = [vertex for vertex in bm.verts if vertex.co.z < -0.15]
    bmesh.ops.delete(bm, geom=lower_vertices, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    obj.scale = scale
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return finish_object(obj, material, bone_name)


def add_rounded_cube(name, location, scale, material, bone_name, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new("SoftEdges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return finish_object(obj, material, bone_name)


def add_cylinder_between(name, start, end, radius, material, bone_name, vertices=20):
    start_v = Vector(start)
    end_v = Vector(end)
    direction = end_v - start_v
    midpoint = (start_v + end_v) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    bevel = obj.modifiers.new("SoftEdges", "BEVEL")
    bevel.width = radius * 0.28
    bevel.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return finish_object(obj, material, bone_name)


def add_bone(armature, name, head, tail, parent=None):
    bone = armature.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if parent:
        bone.parent = armature.edit_bones[parent]
    return bone


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


SOURCE_DIR.mkdir(parents=True, exist_ok=True)
clear_scene()

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 768
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = str(PREVIEW_PATH)
scene.render.fps = 30
scene.world.color = (0.055, 0.045, 0.035)
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass

skin = make_material("M_TownKeeper_Skin", (0.92, 0.56, 0.36), 0.78)
hair = make_material("M_TownKeeper_Hair", (0.055, 0.012, 0.006), 0.78)
cream = make_material("M_TownKeeper_Shirt", (0.82, 0.73, 0.57), 0.84)
moss = make_material("M_TownKeeper_Overalls", (0.25, 0.36, 0.15), 0.80)
coral = make_material("M_TownKeeper_Neckerchief", (0.68, 0.20, 0.12), 0.76)
leather = make_material("M_TownKeeper_Leather", (0.28, 0.12, 0.045), 0.74)
tan = make_material("M_TownKeeper_Tan", (0.56, 0.31, 0.10), 0.77)
leaf = make_material("M_TownKeeper_Leaf", (0.50, 0.67, 0.16), 0.70)
dark = make_material("M_TownKeeper_Eyes", (0.045, 0.018, 0.010), 0.54)
gold = make_material("M_TownKeeper_Metal", (0.75, 0.43, 0.08), 0.35, 0.45)

pieces = []

# Torso, hips, and clothing layers.
add_sphere("Torso_Shirt", (0.0, 0.0, 0.91), (0.30, 0.21, 0.37), cream, "spine_02")
add_sphere("Hips_Overalls", (0.0, 0.0, 0.69), (0.285, 0.205, 0.24), moss, "pelvis")
add_rounded_cube("Overall_Bib", (0.0, -0.202, 0.97), (0.205, 0.025, 0.205), moss, "spine_02", 0.035)
for x in (-0.145, 0.145):
    add_rounded_cube(f"Overall_Strap_{'L' if x < 0 else 'R'}", (x, -0.218, 1.13), (0.035, 0.018, 0.18), moss, "spine_02", 0.018)
    add_sphere(f"Overall_Button_{'L' if x < 0 else 'R'}", (x, -0.245, 1.01), (0.035, 0.018, 0.035), gold, "spine_02", 16, 10)

# Legs and boots. Rigid parts overlap at joints for clean deformation.
for side, x in (("L", -0.155), ("R", 0.155)):
    suffix = side.lower()
    add_cylinder_between(f"Thigh_{side}", (x, 0.0, 0.70), (x, 0.0, 0.43), 0.145, moss, f"thigh_{suffix}")
    add_sphere(f"Knee_{side}", (x, 0.0, 0.42), (0.148, 0.142, 0.14), moss, f"calf_{suffix}")
    add_cylinder_between(f"Calf_{side}", (x, 0.0, 0.40), (x, 0.0, 0.20), 0.13, moss, f"calf_{suffix}")
    add_rounded_cube(f"Boot_{side}", (x, -0.035, 0.115), (0.145, 0.205, 0.12), leather, f"foot_{suffix}", 0.060)
    add_rounded_cube(f"Boot_Sole_{side}", (x, -0.055, 0.025), (0.157, 0.22, 0.032), tan, f"foot_{suffix}", 0.023)

# Arms in a relaxed A-pose.
arm_points = {
    "L": ((-0.27, 0.0, 1.10), (-0.50, 0.0, 0.97), (-0.69, 0.0, 0.84)),
    "R": ((0.27, 0.0, 1.10), (0.50, 0.0, 0.97), (0.69, 0.0, 0.84)),
}
for side, (shoulder, elbow, wrist) in arm_points.items():
    suffix = side.lower()
    add_sphere(f"Sleeve_{side}", shoulder, (0.17, 0.17, 0.17), cream, f"upperarm_{suffix}")
    add_cylinder_between(f"UpperArm_{side}", shoulder, elbow, 0.105, skin, f"upperarm_{suffix}")
    add_sphere(f"Elbow_{side}", elbow, (0.11, 0.105, 0.11), skin, f"lowerarm_{suffix}")
    add_cylinder_between(f"LowerArm_{side}", elbow, wrist, 0.095, skin, f"lowerarm_{suffix}")
    hand_x = -0.75 if side == "L" else 0.75
    add_sphere(f"Hand_{side}", (hand_x, -0.005, 0.80), (0.108, 0.092, 0.13), skin, f"hand_{suffix}")

# Neck, head and face.
add_cylinder_between("Neck", (0.0, 0.0, 1.19), (0.0, 0.0, 1.29), 0.13, skin, "neck_01")
add_sphere("Head", (0.0, -0.045, 1.48), (0.41, 0.37, 0.40), skin, "head", 36, 24)

# Hair cap, side locks, bangs and sprout clip.
add_sphere("Hair_Cap", (0.0, 0.10, 1.60), (0.44, 0.39, 0.43), hair, "head", 32, 20)
add_upper_sphere("Hair_Top", (0.0, -0.035, 1.64), (0.43, 0.38, 0.38), hair, "head")
for i, x in enumerate((-0.31, -0.17, 0.0, 0.17, 0.31)):
    z = 1.67 - 0.04 * abs(i - 2)
    add_sphere(f"Hair_Bang_{i}", (x, -0.335, z), (0.135, 0.075, 0.19), hair, "head", 24, 14)
for side, x in (("L", -0.38), ("R", 0.38)):
    add_sphere(f"Hair_Side_{side}", (x, -0.01, 1.40), (0.13, 0.20, 0.25), hair, "head", 20, 12)

add_cylinder_between("Sprout_Stem", (0.18, -0.30, 1.72), (0.18, -0.31, 1.84), 0.018, gold, "head", 12)
left_leaf = add_sphere("Sprout_Leaf_L", (0.125, -0.31, 1.86), (0.075, 0.025, 0.045), leaf, "head", 16, 10)
left_leaf.rotation_euler[1] = math.radians(-22)
right_leaf = add_sphere("Sprout_Leaf_R", (0.235, -0.31, 1.86), (0.075, 0.025, 0.045), leaf, "head", 16, 10)
right_leaf.rotation_euler[1] = math.radians(22)

# Eyes, brows, nose and mouth use geometry so they remain readable without textures.
for side, x in (("L", -0.145), ("R", 0.145)):
    add_sphere(f"Eye_{side}", (x, -0.385, 1.52), (0.068, 0.022, 0.100), dark, "head", 24, 16)
    add_sphere(f"Eye_Highlight_{side}", (x - 0.018, -0.410, 1.555), (0.018, 0.009, 0.026), cream, "head", 12, 8)
    brow = add_rounded_cube(f"Brow_{side}", (x, -0.402, 1.65), (0.075, 0.010, 0.014), hair, "head", 0.012)
    brow.rotation_euler[1] = math.radians(-5 if side == "L" else 5)
add_sphere("Nose", (0.0, -0.418, 1.42), (0.043, 0.026, 0.040), skin, "head", 18, 12)
add_cylinder_between("Mouth_L", (-0.055, -0.422, 1.350), (0.0, -0.426, 1.333), 0.008, dark, "head", 12)
add_cylinder_between("Mouth_R", (0.0, -0.426, 1.333), (0.055, -0.422, 1.350), 0.008, dark, "head", 12)

# Neckerchief, satchel and strap.
add_sphere("Neckerchief", (0.0, -0.20, 1.18), (0.255, 0.055, 0.11), coral, "spine_02", 24, 12)
add_sphere("Neckerchief_Knot", (0.18, -0.235, 1.14), (0.09, 0.045, 0.075), coral, "spine_02", 18, 10)
add_cylinder_between("Satchel_Strap", (-0.20, -0.235, 1.20), (0.29, -0.235, 0.69), 0.028, tan, "spine_02", 12)
add_rounded_cube("Satchel", (0.34, -0.22, 0.66), (0.17, 0.07, 0.18), tan, "pelvis", 0.05)
add_rounded_cube("Satchel_Flap", (0.34, -0.30, 0.71), (0.17, 0.025, 0.075), leather, "pelvis", 0.025)
add_sphere("Satchel_Button", (0.34, -0.33, 0.69), (0.027, 0.012, 0.027), gold, "pelvis", 12, 8)

# Armature uses Unreal-friendly names and an A-pose suitable for retargeting.
bpy.ops.object.armature_add(enter_editmode=True, location=(0.0, 0.0, 0.0))
rig = bpy.context.object
rig.name = "SKEL_TownKeeper"
armature = rig.data
armature.name = "SKEL_TownKeeper_Armature"
armature.edit_bones.remove(armature.edit_bones[0])

add_bone(armature, "root", (0, 0, 0.0), (0, 0, 0.10))
add_bone(armature, "pelvis", (0, 0, 0.62), (0, 0, 0.80), "root")
add_bone(armature, "spine_01", (0, 0, 0.80), (0, 0, 0.98), "pelvis")
add_bone(armature, "spine_02", (0, 0, 0.98), (0, 0, 1.16), "spine_01")
add_bone(armature, "neck_01", (0, 0, 1.16), (0, 0, 1.28), "spine_02")
add_bone(armature, "head", (0, 0, 1.28), (0, 0, 1.70), "neck_01")

for side, sign in (("l", -1), ("r", 1)):
    shoulder = (0.27 * sign, 0, 1.10)
    elbow = (0.50 * sign, 0, 0.97)
    wrist = (0.69 * sign, 0, 0.84)
    hand = (0.78 * sign, 0, 0.80)
    add_bone(armature, f"upperarm_{side}", shoulder, elbow, "spine_02")
    add_bone(armature, f"lowerarm_{side}", elbow, wrist, f"upperarm_{side}")
    add_bone(armature, f"hand_{side}", wrist, hand, f"lowerarm_{side}")
    add_bone(armature, f"thigh_{side}", (0.155 * sign, 0, 0.68), (0.155 * sign, 0, 0.42), "pelvis")
    add_bone(armature, f"calf_{side}", (0.155 * sign, 0, 0.42), (0.155 * sign, 0, 0.17), f"thigh_{side}")
    add_bone(armature, f"foot_{side}", (0.155 * sign, 0, 0.17), (0.155 * sign, -0.24, 0.10), f"calf_{side}")

bpy.ops.object.mode_set(mode="OBJECT")
rig.show_in_front = True
rig["townage_animation_ready"] = True
rig["townage_contains_animation"] = False

# Combine all visible pieces into one skeletal mesh while preserving materials and rigid vertex groups.
bpy.ops.object.select_all(action="DESELECT")
for obj in pieces:
    obj.select_set(True)
bpy.context.view_layer.objects.active = pieces[0]
bpy.ops.object.join()
body = bpy.context.object
body.name = "SK_TownKeeper_Body"
scene.cursor.location = (0.0, 0.0, 0.0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
body["townage_character_role"] = "MainCharacter"
body["townage_animation_ready"] = True
body["townage_contains_animation"] = False

armature_modifier = body.modifiers.new("TownKeeper_Armature", "ARMATURE")
armature_modifier.object = rig
body.parent = rig
body.matrix_parent_inverse = rig.matrix_world.inverted()

# Export only the skinned mesh and armature. No animation data is baked.
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(FBX_PATH),
    use_selection=True,
    object_types={"ARMATURE", "MESH"},
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_UNITS",
    axis_forward="-Y",
    axis_up="Z",
    add_leaf_bones=False,
    use_armature_deform_only=True,
    bake_anim=False,
    path_mode="AUTO",
)

# Preview studio objects are not part of the FBX export.
bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0.0, 0.0, -0.015))
ground = bpy.context.object
ground.name = "Preview_Ground"
ground_material = make_material("M_Preview_Ground", (0.12, 0.16, 0.09), 0.95)
ground.data.materials.append(ground_material)

bpy.ops.object.camera_add(location=(2.7, -4.8, 2.05))
camera = bpy.context.object
camera.name = "Preview_Camera"
camera.data.lens = 58
look_at(camera, (0.0, 0.0, 0.93))
scene.camera = camera

for name, location, energy, size, color in (
    ("Key", (-3.2, -4.0, 5.0), 620, 4.0, (1.0, 0.72, 0.52)),
    ("Fill", (3.8, -2.0, 3.0), 360, 3.0, (0.58, 0.75, 1.0)),
    ("Rim", (0.0, 3.0, 4.2), 520, 2.5, (0.72, 1.0, 0.62)),
):
    light_data = bpy.data.lights.new(f"Preview_{name}", type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_data.color = color
    light_obj = bpy.data.objects.new(f"Preview_{name}", light_data)
    scene.collection.objects.link(light_obj)
    light_obj.location = location
    look_at(light_obj, (0.0, 0.0, 0.85))

rig.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
bpy.ops.render.render(write_still=True)

result = {
    "status": "ok",
    "blend": str(BLEND_PATH),
    "fbx": str(FBX_PATH),
    "preview": str(PREVIEW_PATH),
    "mesh": body.name,
    "armature": rig.name,
    "bones": [bone.name for bone in armature.bones],
    "materials": [slot.material.name for slot in body.material_slots if slot.material],
    "animations": 0,
    "vertices": len(body.data.vertices),
    "polygons": len(body.data.polygons),
}
