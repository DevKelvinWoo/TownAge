"""Drive the development lighting widget and capture four real gameplay-camera states."""

import json
import time
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/Lighting/PIE'
MAP = '/Game/Maps/L_MainVillage_Blockout_01'
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
PRESETS = [('Morning', 8., 'SelectMorning'), ('Noon', 12., 'SelectNoon'),
           ('Evening', 17.5, 'SelectEvening'), ('Night', 22., 'SelectNight')]
STATE = {'stage': 'start', 'index': 0, 'samples': [], 'start': time.monotonic(), 'busy': False}


def finish(error=None):
    report = {'passed': error is None, 'map': MAP, 'error': error, 'samples': STATE['samples']}
    (OUT / 'lighting_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def widgets(world):
    return unreal.WidgetLibrary.get_all_widgets_of_class(world, unreal.TownAgeLightingPreviewWidget, True)


def advance(stage):
    STATE['stage'] = stage
    STATE['since'] = time.monotonic()
    STATE.pop('shot', None)


def screenshot(label, controller=None):
    path = OUT / (label + '.png')
    if 'shot' not in STATE:
        STATE['shot_started'] = time.time()
        if controller:
            command = f'Shot SHOWUI -nosuffix filename="{path.as_posix()}"'
            unreal.SystemLibrary.execute_console_command(controller, command, controller)
            STATE['shot'] = True
        else:
            STATE['shot'] = unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, str(path))
        return False
    return path.is_file() and path.stat().st_mtime >= STATE['shot_started']


def tick(_):
    if STATE['busy']:
        return
    STATE['busy'] = True
    try:
        now = time.monotonic()
        assert now - STATE['start'] < 85, 'Lighting review timed out'
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        assert len(worlds) == 1, 'Select one-player standalone PIE'
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not isinstance(pawn, unreal.TownAgePlayer):
            return
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        clock = unreal.GameplayStatics.get_game_state(world)
        assert pc.get_view_target() == pawn and isinstance(clock, unreal.TownAgeGameState)
        if STATE['stage'] == 'start':
            pawn.set_actor_location(unreal.Vector(3190, -475, 100), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            assert clock.set_day_length_minutes(1440.)
            assert not pc.set_lighting_preview_time(unreal.TownAgeLightingPreview.NIGHT)
            pc.toggle_lighting_preview()
            assert len(widgets(world)) == 1
            advance('panel')
        elif STATE['stage'] == 'panel':
            if now - STATE['since'] >= 2 and screenshot('LightingTool', pc):
                widgets(world)[0].call_method('CloseClicked', ())
                assert not widgets(world)
                advance('select')
        elif STATE['stage'] == 'select':
            label, hour, handler = PRESETS[STATE['index']]
            pc.toggle_lighting_preview()
            panel = widgets(world)[0]
            panel.call_method(handler, ())
            assert abs(clock.get_time_of_day_hours() - hour) < .025, label
            panel.call_method('CloseClicked', ())
            assert not widgets(world)
            advance('capture')
        elif STATE['stage'] == 'capture' and now - STATE['since'] >= 2.2:
            label, hour, _ = PRESETS[STATE['index']]
            if not screenshot(label):
                return
            sun_actor = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.DirectionalLight)
                             if 'Interiors/' not in a.get_path_name())
            sun = sun_actor.get_editor_property('light_component')
            assert abs(sun.get_editor_property('light_source_angle') - 2.8) < .05
            assert abs(sun.get_editor_property('shadow_amount') - .62) < .05
            manager = unreal.GameplayStatics.get_player_camera_manager(world, 0)
            view = manager.get_camera_location()
            STATE['samples'].append({'preset': label, 'requested_hour': hour,
                'actual_hour': clock.get_time_of_day_hours(),
                'sun_lux': sun.get_editor_property('intensity'),
                'sun_rgb': str(sun.get_editor_property('light_color')), 'sun_rotation': str(sun.get_world_rotation()),
                'pawn_camera_cm': [view.x, view.y, view.z], 'fov': manager.get_fov_angle()})
            STATE['index'] += 1
            if STATE['index'] == len(PRESETS):
                first, noon, evening, night = STATE['samples']
                assert noon['sun_lux'] > first['sun_lux'] > evening['sun_lux'] > night['sun_lux']
                assert len({item['sun_rotation'] for item in STATE['samples']}) == 4
                finish()
            else:
                advance('select')
    except Exception:
        finish(traceback.format_exc())
    finally:
        STATE['busy'] = False


OUT.mkdir(parents=True, exist_ok=True)
assert LEVELS.load_level(MAP)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
HANDLE = unreal.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
