"""Inspect baked production source and FBX roundtrip; assemble Unreal handoff.

Run in isolated Blender with TownKeeper_Reference05.blend open, after animation
export and the right-hand/satchel pose verification have both completed.
"""
import json
from pathlib import Path
import bpy
from io_scene_fbx import parse_fbx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ArtSource/Characters/Main/Revision05'
manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
animations = json.loads((OUT / 'animation_manifest.json').read_text(encoding='utf-8'))
collision = json.loads((OUT / 'hand_collision_check.json').read_text(encoding='utf-8'))
assert collision['worst']['overlapping_triangles'] == 0, collision['worst']
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.parent and o.parent.type == 'ARMATURE')
CHARACTER_MESH_NAME = body.name
inspector = ROOT / 'Tools/Skills/townage-character/scripts/inspect_blender_character.py'
exec(compile(inspector.read_text(encoding='utf-8'), str(inspector), 'exec'))
source_report = result
assert abs(result['height_cm'] - 170) < .1, result
assert result['bad_weight_vertices'] == 0 and result['uv_layers'] > 0, result
assert not result['assigned_animation'], 'Model source must remain animation-free'
assert len(result['bones']) == 18 and len(result['materials']) == 1, result
assert all(abs(v - 1) < 1e-5 for v in result['mesh_scale'] + result['armature_scale']), result

tree, _ = parse_fbx.parse(manifest['fbx_path'])
units = {}
def visit(node):
    if node.id == b'P' and node.props and node.props[0] in (b'UnitScaleFactor', b'OriginalUnitScaleFactor'):
        units[node.props[0].decode()] = node.props[-1]
    for child in node.elems:
        visit(child)
visit(tree)
assert units['UnitScaleFactor'] == 1, units

original_scene = bpy.context.scene
test = bpy.data.scenes.new('Revision05_FBX_Verification')
test.unit_settings.scale_length = .01
try:
    bpy.context.window.scene = test
    bpy.ops.import_scene.fbx(filepath=manifest['fbx_path'], use_anim=False)
    imported = next(o for o in test.objects if o.type == 'MESH')
    points = [imported.matrix_world @ v.co for v in imported.data.vertices]
    roundtrip_height = max(p.z for p in points) - min(p.z for p in points)
    assert abs(roundtrip_height - 170) < .1, roundtrip_height
    assert set(imported.find_armature().data.bones.keys()) == set(source_report['bones'])
finally:
    bpy.context.window.scene = original_scene
    for obj in list(test.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(test)

assert animations['rest_skeleton_unchanged'] and animations['weights_bad'] == 0
for clip in animations['roundtrip']:
    assert clip['root_matrix_max_change'] < 1e-5 and clip['bone_scale_max_error'] < 1e-5, clip
manifest['walk'] = dict(animations['walk'], speed_cm_s=animations['walk_speed_cm_s'])
manifest['standing'] = animations['standing']
manifest['verification'] = {'source': source_report, 'fbx_units': units,
                            'roundtrip_height_cm': roundtrip_height,
                            'right_hand_satchel_overlaps': 0,
                            'collision_samples': len(collision['samples'])}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('REVISION05_VERIFIED', json.dumps(manifest['verification']), flush=True)
