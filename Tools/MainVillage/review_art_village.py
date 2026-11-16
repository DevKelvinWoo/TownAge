"""Capture two GPU editor views and one real player-camera view, then exit.

Run with -ExecutePythonScript in a rendering editor, not a null-RHI commandlet.
The review does not save changes to the level or imported assets.
"""

import hashlib
import json
import time
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
MAP = '/Game/Maps/L_MainVillage_Art_01'
OUT = ROOT / 'Saved/MainVillage/Art/Review'
OUT.mkdir(parents=True, exist_ok=True)
settings_file = OUT / 'review_settings.json'
SETTINGS = json.loads(settings_file.read_text(encoding='utf-8-sig')) if settings_file.exists() else {}
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
STATE = {'start': time.monotonic(), 'since': time.monotonic(), 'stage': 'warmup',
         'busy': False, 'captures': [], 'gameplay': None}
REPORT = {'map': MAP, 'resolution': [1280, 720], 'assets': [], 'captures': [],
          'limitations': ['A short crossing walk and roof collision traces do not verify the full walking route.',
                         'Packaged builds, external multiplayer and physical mobile devices were not tested.']}


def xyz(vector):
    return [vector.x, vector.y, vector.z]


def advance(stage):
    STATE.update(stage=stage, since=time.monotonic())
    STATE.pop('shot', None)


def finish(error=None):
    REPORT.update(passed=error is None, error=error, captures=STATE['captures'], gameplay=STATE['gameplay'])
    REPORT['source_map_unchanged'] = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest() == SOURCE_HASH
    REPORT['art_map_unchanged'] = hashlib.sha256(MAP_FILE.read_bytes()).hexdigest() == MAP_HASH
    (OUT / 'review_report.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def capture(label, camera=None):
    path = OUT / (label + '.png')
    if 'shot' not in STATE:
        STATE['shot_wall_time'] = time.time()
        STATE['shot_monotonic'] = time.monotonic()
        STATE['shot'] = unreal.AutomationLibrary.take_high_res_screenshot(
            1280, 720, str(path), camera=camera, force_game_view=True)
        return False
    assert time.monotonic() - STATE['shot_monotonic'] < 30, f'Screenshot timed out: {path}'
    if not path.is_file() or path.stat().st_mtime < STATE['shot_wall_time'] or path.stat().st_size < 1000:
        return False
    if time.monotonic() - STATE['shot_monotonic'] < 1:
        return False
    STATE['captures'].append({'label': label, 'path': str(path), 'bytes': path.stat().st_size,
                              'camera': camera.get_actor_label() if camera else 'Actual player camera'})
    return True


def tick(_):
    if STATE['busy']:
        return
    STATE['busy'] = True
    try:
        now = time.monotonic()
        assert now - STATE['start'] < 180, 'Art review timed out'
        if STATE['stage'] == 'warmup':
            if now - STATE['since'] >= 15:
                advance('overview')
        elif STATE['stage'] == 'overview':
            if capture('01_Overview', OVERVIEW):
                STOREFRONT.set_actor_location(unreal.Vector(*SETTINGS.get('storefront_position_cm', [5050, 1450, 1450])), False, True)
                target = unreal.Vector(*SETTINGS.get('storefront_target_cm', [4020, -950, 220]))
                rotation = unreal.MathLibrary.find_look_at_rotation(STOREFRONT.get_actor_location(), target)
                STOREFRONT.set_actor_rotation(rotation, True)
                EDITOR.set_level_viewport_camera_info(STOREFRONT.get_actor_location(), rotation)
                advance('storefront_settle')
        elif STATE['stage'] == 'storefront_settle':
            if now - STATE['since'] >= 3:
                advance('storefront')
        elif STATE['stage'] == 'storefront':
            if capture('02_Storefronts', STOREFRONT):
                LEVELS.editor_request_begin_play()
                advance('pie_wait')
        elif STATE['stage'] in ('pie_wait', 'pie_settle', 'gameplay', 'walk'):
            worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            if not worlds:
                assert now - STATE['since'] < 60, 'PIE did not start'
                return
            assert len(worlds) == 1, 'Use one-player standalone PIE for this visual review'
            world = worlds[0]
            pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
            if not isinstance(pawn, unreal.TownAgePlayer):
                assert now - STATE['since'] < 60, 'TownAge player did not spawn'
                return
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            assert controller.get_view_target() == pawn, 'Capture must use normal gameplay camera'
            if STATE['stage'] == 'pie_wait':
                clock = unreal.GameplayStatics.get_game_state(world)
                if isinstance(clock, unreal.TownAgeGameState):
                    assert clock.set_time_of_day(8.)
                    assert clock.set_day_length_minutes(1440.)
                advance('pie_settle')
            elif STATE['stage'] == 'pie_settle':
                if now - STATE['since'] < 5:
                    return
                movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
                assert movement.is_moving_on_ground(), 'Player spawn is not grounded'
                manager = unreal.GameplayStatics.get_player_camera_manager(world, 0)
                STATE['gameplay'] = {'pawn_cm': xyz(pawn.get_actor_location()),
                                     'camera_cm': xyz(manager.get_camera_location()),
                                     'fov': manager.get_fov_angle(), 'grounded': True,
                                     'view_target_is_player': True}
                all_runtime_actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                collision_checks = []
                for label in ('Village_Mart', 'Village_Salon', 'Village_GreenRoofHouse'):
                    building = next(a for a in all_runtime_actors if a.get_actor_label() == label)
                    center, extent = building.get_actor_bounds(False)
                    # Ignore every other actor so a tree or the Landscape cannot
                    # make a missing building collider look like a successful hit.
                    hit = unreal.SystemLibrary.line_trace_single(world,
                        unreal.Vector(center.x, center.y, center.z + extent.z + 100),
                        unreal.Vector(center.x, center.y, center.z - extent.z - 10),
                        unreal.TraceTypeQuery.ECC_VISIBILITY, False,
                        [a for a in all_runtime_actors if a != building], unreal.DrawDebugTrace.NONE, True)
                    assert hit, f'Building has no blocking query collision: {label}'
                    position = hit.to_dict()['location']
                    collision_checks.append({'building': label, 'hit_cm': xyz(position),
                                             'other_actors_ignored': True, 'trace_complex': False})
                REPORT['building_collision_checks'] = collision_checks
                advance('gameplay')
            elif STATE['stage'] == 'gameplay':
                if capture('03_Gameplay'):
                    STATE['walk_start'] = pawn.get_actor_location()
                    advance('walk')
            elif STATE['stage'] == 'walk':
                movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
                assert movement.is_moving_on_ground(), 'Player left ground during short crossing walk'
                if now - STATE['since'] < 2:
                    pawn.add_movement_input(unreal.Vector(0, -1, 0), 1.)
                    return
                end = pawn.get_actor_location()
                start = STATE['walk_start']
                distance = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** .5
                assert distance >= 80 and end.y < start.y - 75, 'Player did not advance toward crossing'
                STATE['gameplay']['short_walk'] = {'start_cm': xyz(start), 'end_cm': xyz(end),
                    'distance_cm': distance, 'duration_seconds': now - STATE['since'], 'grounded': True,
                    'method': 'Actual add_movement_input toward the crossing; no teleport'}
                finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        STATE['busy'] = False


SOURCE_FILE = ROOT / 'Content/Maps/L_MainVillage_Blockout_01.umap'
MAP_FILE = ROOT / 'Content/Maps/L_MainVillage_Art_01.umap'
SOURCE_HASH = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
MAP_HASH = hashlib.sha256(MAP_FILE.read_bytes()).hexdigest()
assert LEVELS.load_level(MAP)
actors = ACTORS.get_all_level_actors()
OVERVIEW = next(a for a in actors if a.get_actor_label() == 'MainVillage_Art_Overview')
if 'overview_position_cm' in SETTINGS:
    OVERVIEW.set_actor_location(unreal.Vector(*SETTINGS['overview_position_cm']), False, True)
if 'overview_target_cm' in SETTINGS:
    OVERVIEW.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(
        OVERVIEW.get_actor_location(), unreal.Vector(*SETTINGS['overview_target_cm'])), True)
if 'overview_fov' in SETTINGS:
    OVERVIEW.camera_component.set_field_of_view(float(SETTINGS['overview_fov']))
REPORT['review_settings'] = SETTINGS
REPORT['overview_position_cm'] = xyz(OVERVIEW.get_actor_location())
REPORT['overview_rotation'] = str(OVERVIEW.get_actor_rotation())
ACTORS.set_selected_level_actors([])
EDITOR.set_level_viewport_camera_info(OVERVIEW.get_actor_location(), OVERVIEW.get_actor_rotation())
STOREFRONT = ACTORS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector())
STOREFRONT.set_actor_label('Transient_Art_StorefrontReview')
STOREFRONT.camera_component.set_field_of_view(float(SETTINGS.get('storefront_fov', 58.)))
STOREFRONT.set_editor_property('is_editor_only_actor', True)

for actor in actors:
    if not str(actor.get_folder_path()).startswith('MainVillage/Art/'):
        continue
    center, extent = actor.get_actor_bounds(False)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if not component:
        continue
    mesh = component.get_editor_property('static_mesh')
    body = mesh.get_editor_property('body_setup') if mesh else None
    REPORT['assets'].append({'label': actor.get_actor_label(), 'center_cm': xyz(center),
                             'extent_cm': xyz(extent), 'mesh': mesh.get_path_name() if mesh else None,
                             'collision_profile': str(component.get_collision_profile_name()),
                             'collision_enabled': str(component.get_collision_enabled()),
                             'collision_trace': str(body.get_editor_property('collision_trace_flag')) if body else None})
REPORT['source_map_sha256'] = SOURCE_HASH
REPORT['art_map_sha256'] = MAP_HASH
(OUT / 'preflight.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
HANDLE = unreal.register_slate_post_tick_callback(tick)
print('MAIN_VILLAGE_ART_GPU_REVIEW_STARTED', str(OUT))
