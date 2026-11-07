"""Execute in Blender with CHARACTER_MESH_NAME set; produces JSON-safe result."""
import bpy
obj = bpy.data.objects.get(CHARACTER_MESH_NAME)
if obj is None or obj.type != 'MESH':
    raise ValueError('Set CHARACTER_MESH_NAME to the explicit character mesh')
rig = obj.find_armature()
points = [obj.matrix_world @ v.co for v in obj.data.vertices]
bad = sum(1 for v in obj.data.vertices if not v.groups or abs(sum(g.weight for g in v.groups) - 1) > 1e-4)
obj.data.calc_loop_triangles()
result = {
    'mesh': obj.name,
    'height_cm': (max(p.z for p in points) - min(p.z for p in points)) * bpy.context.scene.unit_settings.scale_length * 100 if points else 0,
    'mesh_scale': list(obj.scale),
    'armature': rig.name if rig else None,
    'armature_scale': list(rig.scale) if rig else None,
    'bones': [b.name for b in rig.data.bones] if rig else [],
    'bad_weight_vertices': bad,
    'uv_layers': len(obj.data.uv_layers),
    'triangles': len(obj.data.loop_triangles),
    'materials': [s.material.name if s.material else None for s in obj.material_slots],
    'assigned_animation': bool(obj.animation_data and obj.animation_data.action) or bool(rig and rig.animation_data and rig.animation_data.action),
}
