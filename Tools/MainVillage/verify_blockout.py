"""Walk the main-village review route and capture the live TownKeeper camera in PIE."""

import json
import math
import time
import traceback
from pathlib import Path

import unreal

MAP = '/Game/Maps/L_MainVillage_Blockout_01'
OUT = Path(__file__).resolve().parents[2] / 'Saved/MainVillage/PIE_v02'
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ROUTE = [
    ('01_Start', 3260, 1010),
    ('02_Crossing', 3260, 615),
    ('03_Plaza', 3260, 155),
    (None, 3720, 155),
    ('04_Market', 3720, -585),
    (None, 3720, -765),
    (None, 3720, -540),
    ('05_Salon', 4585, -540),
    (None, 4585, 185),
    (None, 1420, 185),
    ('06_NPC_Homes', 1420, -350),
    (None, 1420, 185),
    (None, 2920, 185),
    ('07_Home', 2920, -885),
]
STATE = {'index': 0, 'start': time.monotonic(), 'progress_at': time.monotonic(),
         'best': math.inf, 'observations': [], 'busy': False}


def finish(error=None):
    path = OUT / 'playtest.json'
    path.write_text(json.dumps({'passed': error is None, 'error': error, 'map': MAP,
                                'route': STATE['observations']}, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(_):
    if STATE['busy']:
        return
    STATE['busy'] = True
    try:
        now = time.monotonic()
        assert now - STATE['start'] < 100, 'Review route timed out'
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        assert len(worlds) == 1, 'Use one-player standalone PIE for camera captures'
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not isinstance(pawn, unreal.TownAgePlayer):
            return
        position = pawn.get_actor_location()
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        camera = unreal.GameplayStatics.get_player_camera_manager(world, 0)
        assert controller.get_view_target() == pawn, 'Review must use the normal pawn camera'
        if not STATE.get('started'):
            unreal.GameplayStatics.set_global_time_dilation(world, 2.5)
            game_state = unreal.GameplayStatics.get_game_state(world)
            if isinstance(game_state, unreal.TownAgeGameState):
                game_state.set_day_length_minutes(120.)
                game_state.set_time_of_day(9.)
            STATE['started'] = True
            STATE['progress_at'] = now
        if 'door_at' in STATE:
            if not pawn.is_door_busy() and position.x > 40000:
                STATE['observations'].append({'checkpoint': 'Existing cottage interior',
                                               'pawn_cm': [position.x, position.y, position.z]})
                finish()
            else:
                assert now - STATE['door_at'] < 12, 'Existing cottage door did not complete travel'
            return
        if STATE['index'] >= len(ROUTE):
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            pawn.get_interaction_component().refresh_selection()
            pawn.request_interaction()
            assert pawn.is_door_busy(), 'Existing cottage interaction was not available'
            STATE['door_at'] = now
            return

        label, x, y = ROUTE[STATE['index']]
        offset = unreal.Vector(x - position.x, y - position.y, 0.)
        distance = offset.length()
        if distance < STATE['best'] - 8:
            STATE['best'] = distance
            STATE['progress_at'] = now
        tolerance = 15 if label == '07_Home' else 45
        if distance > tolerance and 'settle' not in STATE:
            assert now - STATE['progress_at'] < 6, f'Blocked before {label or (x, y)}'
            pawn.add_movement_input(offset / distance, 1.)
            return
        movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
        assert movement.is_moving_on_ground(), f'Pawn left walkable surface at {label or (x, y)}'
        if label and 'settle' not in STATE:
            STATE['settle'] = now
            return
        if label and now - STATE['settle'] < .35:
            return
        if label:
            path = OUT / f'{label}.png'
            if 'shot' not in STATE:
                STATE['shot'] = unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, str(path))
                STATE['shot_at'] = now
                return
            if not path.exists() or now - STATE['shot_at'] < .35:
                assert now - STATE['shot_at'] < 8, f'Screenshot did not save: {label}'
                return
            view = camera.get_camera_location()
            STATE['observations'].append({'checkpoint': label, 'pawn_cm': [position.x, position.y, position.z],
                                           'camera_cm': [view.x, view.y, view.z], 'fov': camera.get_fov_angle()})
        for key in ('settle', 'shot', 'shot_at'):
            STATE.pop(key, None)
        STATE.update(index=STATE['index'] + 1, best=math.inf, progress_at=now)
    except Exception:
        finish(traceback.format_exc())
    finally:
        STATE['busy'] = False


OUT.mkdir(parents=True, exist_ok=True)
assert LEVELS.load_level(MAP)
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
HANDLE = unreal.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
