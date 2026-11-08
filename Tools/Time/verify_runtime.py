"""GPU editor QA: begin PIE, sample four phases, verify clock and rollover.

Launch the desired map with -ExecCmds="py <absolute path to this script>".
Only transient PIE actors/state are modified; the editor map is never saved.
"""
import json
import time
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Time'
OUT.mkdir(parents=True, exist_ok=True)
STAGES = [('morning', 6.5), ('noon', 12.0), ('evening', 18.0), ('night', 0.0)]
STATE = {'stage': -1, 'since': time.monotonic(), 'samples': [], 'camera': None, 'tasks': []}
if hasattr(unreal, '_townage_time_handle'):
    unreal.unregister_slate_post_tick_callback(unreal._townage_time_handle)


def finish(error=None):
    STATE['passed'] = error is None
    if error:
        STATE['error'] = error
    report = {key: value for key, value in STATE.items() if key not in ['camera', 'tasks', 'since', 'restore']}
    (OUT / 'runtime_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(unreal._townage_time_handle)
    print('TIME_RUNTIME_VERIFY_' + ('PASS' if error is None else 'FAIL: ' + error))


def tick(_delta):
    # Screenshot tasks pump Slate while waiting; do not reenter this callback.
    if STATE.get('busy', False):
        return
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        world = next((w for w in worlds if unreal.SystemLibrary.is_server(w)), None)
        if world is None:
            return
        gs = unreal.GameplayStatics.get_game_state(world)
        if not isinstance(gs, unreal.TownAgeGameState) or not gs.is_clock_ready():
            return
        now = time.monotonic()
        if STATE['stage'] == -1:
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            if pawn is None:
                return
            assert not gs.set_day_length_minutes(0), 'Invalid duration accepted'
            assert gs.set_day_length_minutes(1440)
            boom = pawn.get_component_by_class(unreal.SpringArmComponent)
            camera = pawn.get_component_by_class(unreal.CameraComponent)
            STATE['restore'] = {'length': boom.get_editor_property('target_arm_length'),
                                'offset': boom.get_editor_property('target_offset'),
                                'rotation': boom.get_world_rotation(),
                                'fov': camera.get_editor_property('field_of_view')}
            boom.set_editor_property('target_arm_length', 0)
            boom.set_editor_property('target_offset', unreal.Vector(0, 0, 450))
            boom.set_world_rotation(unreal.Rotator(pitch=10, yaw=-90), False, True)
            camera.set_field_of_view(75)
            STATE.update(camera=camera, stage=0, since=now)
            gs.set_time_of_day(STAGES[0][1])
            return
        stage = STATE['stage']
        if stage < len(STAGES):
            if now - STATE['since'] < 3.0:
                return
            name, expected = STAGES[stage]
            hour = gs.get_time_of_day_hours()
            assert abs(hour - expected) < .05, (name, hour)
            skies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.TownAgeTimeSky)
            assert len(skies) == 1, 'Expected exactly one local sky presentation'
            sky = skies[0]
            material = sky.get_component_by_class(unreal.StaticMeshComponent).get_material(0)
            assert material is not None
            sun_actor = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.DirectionalLight)[0]
            sun = sun_actor.get_editor_property('light_component')
            assert sun is not None
            color = material.get_vector_parameter_value('Zenith Color')
            sample = {'phase': name, 'hour': hour, 'day': gs.get_day_number(),
                      'sun_intensity': sun.get_editor_property('intensity'),
                      'sun_rotation': str(sun.get_world_rotation()),
                      'zenith': [color.r, color.g, color.b],
                      'stars': material.get_scalar_parameter_value('Stars brightness')}
            STATE['samples'].append(sample)
            STATE['busy'] = True
            try:
                task = unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, str(OUT / (name + '.png')))
            finally:
                STATE['busy'] = False
            STATE['tasks'].append(task)
            STATE['stage'] += 1
            STATE['since'] = now
            if STATE['stage'] < len(STAGES):
                # Wait for screenshot completion before changing the next phase.
                STATE['pending_hour'] = STAGES[STATE['stage']][1]
                STATE['stage'] += 100
            else:
                samples = STATE['samples']
                assert samples[1]['sun_intensity'] > samples[3]['sun_intensity']
                assert samples[1]['zenith'] != samples[2]['zenith'] != samples[3]['zenith']
                STATE['stage'] = 200
            return
        if 100 <= stage < 200:
            if now - STATE['since'] < 2.0:
                return
            gs.set_time_of_day(STATE.pop('pending_hour'))
            STATE['stage'] -= 100
            STATE['since'] = now
            return
        if stage == 200:
            if now - STATE['since'] < 2.0:
                return
            assert gs.set_day_length_minutes(1)
            gs.set_time_of_day(23.99)
            STATE['rollover_day'] = gs.get_day_number()
            STATE['since'] = now
            STATE['stage'] = 201
            return
        if stage == 201:
            if now - STATE['since'] < 1.0:
                return
            assert gs.get_day_number() == STATE['rollover_day'] + 1
            before = gs.get_total_world_hours()
            assert gs.set_day_length_minutes(24)
            assert abs(gs.get_total_world_hours() - before) < .01, 'Speed change jumped the clock'
            gs.set_time_of_day(8)
            pc = unreal.GameplayStatics.get_player_controller(world, 0)
            boom = unreal.GameplayStatics.get_player_pawn(world, 0).get_component_by_class(unreal.SpringArmComponent)
            restore = STATE.pop('restore')
            boom.set_editor_property('target_arm_length', restore['length'])
            boom.set_editor_property('target_offset', restore['offset'])
            boom.set_world_rotation(restore['rotation'], False, True)
            STATE['camera'].set_field_of_view(restore['fov'])
            finish()
    except Exception:
        finish(traceback.format_exc())


unreal._townage_time_handle = unreal.register_slate_post_tick_callback(tick)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.is_in_play_in_editor():
    levels.editor_request_begin_play()
