"""Register a short live-PIE walk check; then start PIE through the editor.

Use -ExecCmds="py <absolute script path>" when reopening the saved test map.
The callback adds forward input for two seconds and does not save the level.
"""
import json
import traceback
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/revision05_runtime_report.json'
STATE = {'samples': [], 'start': None}

def tick(delta_time):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        pawns = unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.TownAgePlayer)
        if not pawns:
            return
        pawn = pawns[0]
        now = unreal.GameplayStatics.get_time_seconds(worlds[0])
        if STATE['start'] is None:
            STATE['start'] = now
        elapsed = now - STATE['start']
        if .4 < elapsed < 2.4:
            pawn.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
        mesh = pawn.get_editor_property('mesh')
        foot = mesh.get_socket_transform('foot_l', unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        position = pawn.get_actor_location()
        velocity = pawn.get_velocity()
        instance = mesh.get_anim_instance()
        STATE['samples'].append({'time': elapsed, 'position': [position.x, position.y, position.z],
                                 'speed': (velocity.x ** 2 + velocity.y ** 2) ** .5,
                                 'foot': [foot.x, foot.y, foot.z],
                                 'anim_instance': instance.get_class().get_name() if instance else None})
        if elapsed > 3.2:
            samples = STATE['samples']
            moving = [s for s in samples if .6 < s['time'] < 2.4]
            assert moving, 'No movement frames'
            foot_delta = max(s['foot'][2] for s in moving) - min(s['foot'][2] for s in moving)
            distance = sum((samples[-1]['position'][i] - samples[0]['position'][i]) ** 2 for i in (0, 1)) ** .5
            asset = mesh.get_skeletal_mesh_asset()
            report = {'mesh': asset.get_path_name(), 'height_cm': asset.get_bounds().box_extent.z * 2,
                      'skeleton': asset.get_editor_property('skeleton').get_path_name(),
                      'distance_cm': distance, 'max_speed_cm_s': max(s['speed'] for s in samples),
                      'moving_foot_z_range_cm': foot_delta, 'samples': samples}
            report['passed'] = (distance > 20 and foot_delta > 2 and
                                abs(report['max_speed_cm_s'] - 64 * 30 / 28) < .1 and
                                abs(report['height_cm'] - 170) < 1 and
                                '/FinalCharacter05/' in report['mesh'] and
                                '/FinalCharacter05/' in report['skeleton'])
            OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')
            unreal.unregister_slate_post_tick_callback(HANDLE)
            print('REVISION05_RUNTIME_VERIFIED', report['passed'], distance, foot_delta)
    except Exception:
        OUT.write_text(json.dumps({'error': traceback.format_exc()}, indent=2), encoding='utf-8')
        unreal.unregister_slate_post_tick_callback(HANDLE)

HANDLE = unreal.register_slate_post_tick_callback(tick)
print('REVISION05_RUNTIME_CHECK_READY')
