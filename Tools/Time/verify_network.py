"""Transient two-world PIE clock/sky verification; never save maps or assets.

Run after starting a listen-server + client PIE session. If PIE is stopped, this
script can temporarily request two clients under one process if the engine
exports the play-settings enum. Otherwise it waits for the caller to start PIE.
Temporary editor play settings are restored once both worlds exist or on failure.
"""
import json
import time
import traceback
from pathlib import Path

import unreal


OUT = Path(__file__).resolve().parents[2] / 'Saved/Time'
OUT.mkdir(parents=True, exist_ok=True)
TIMEOUT_SECONDS = 60.0
HANDLE_NAME = '_townage_time_network_handle'
RESTORE_NAME = '_townage_time_network_restore'


def restore_play_settings():
    saved = getattr(unreal, RESTORE_NAME, None)
    if saved is None:
        return
    settings = unreal.get_default_object(unreal.LevelEditorPlaySettings)
    for key, value in saved.items():
        settings.set_editor_property(key, value)
    delattr(unreal, RESTORE_NAME)


# A rerun must not leave the previous callback or temporary play configuration.
if hasattr(unreal, HANDLE_NAME):
    try:
        unreal.unregister_slate_post_tick_callback(getattr(unreal, HANDLE_NAME))
    except Exception:
        pass
    delattr(unreal, HANDLE_NAME)
restore_play_settings()

STATE = {'stage': 'waiting', 'started': time.monotonic(), 'samples': [],
         'requested_pie': False, 'changed_clock': False}


def network_worlds():
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    servers = [world for world in worlds if unreal.SystemLibrary.is_server(world)
               and not unreal.SystemLibrary.is_standalone(world)]
    clients = [world for world in worlds if not unreal.SystemLibrary.is_server(world)]
    return (servers[0] if servers else None, clients[0] if clients else None)


def hour_difference(a, b):
    difference = abs(a - b) % 24.0
    return min(difference, 24.0 - difference)


def sample(world, gs):
    skies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.TownAgeTimeSky)
    assert len(skies) == 1, ('Expected one sky in rendering world', world.get_path_name(), len(skies))
    dome = skies[0].get_component_by_class(unreal.StaticMeshComponent)
    material = dome.get_material(0) if dome is not None else None
    assert material is not None, ('Missing sky material', world.get_path_name())
    color = material.get_vector_parameter_value('Zenith Color')
    return {'world': world.get_path_name(), 'hour': gs.get_time_of_day_hours(),
            'total_hours': gs.get_total_world_hours(), 'day': gs.get_day_number(),
            'day_length_minutes': gs.get_day_length_minutes(), 'sky_count': len(skies),
            'zenith': [color.r, color.g, color.b]}


def check_agreement(server, client, server_gs, client_gs, expected_minutes, label):
    server_sample, client_sample = sample(server, server_gs), sample(client, client_gs)
    difference = hour_difference(server_sample['hour'], client_sample['hour'])
    assert difference < .05, ('Clock drift exceeds .05 hours', difference, server_sample, client_sample)
    for value in [server_sample, client_sample]:
        assert abs(value['day_length_minutes'] - expected_minutes) < .0001, value
    color_difference = max(abs(a - b) for a, b in zip(server_sample['zenith'], client_sample['zenith']))
    assert color_difference < .025, ('Sky palettes diverged', color_difference)
    STATE['samples'].append({'phase': label, 'server': server_sample, 'client': client_sample,
                             'hour_difference': difference, 'zenith_max_difference': color_difference})


def finish(error=None):
    report = {key: value for key, value in STATE.items() if key not in ['started', 'since']}
    report['passed'] = error is None
    report['elapsed_seconds'] = time.monotonic() - STATE['started']
    if error:
        report['error'] = error
    try:
        restore_play_settings()
        if STATE['changed_clock']:
            server, _ = network_worlds()
            if server is not None:
                gs = unreal.GameplayStatics.get_game_state(server)
                report['clock_restored'] = bool(gs.set_day_length_minutes(24) and gs.set_time_of_day(8))
    except Exception:
        report['passed'] = False
        report['restore_error'] = traceback.format_exc()
    handle = getattr(unreal, HANDLE_NAME, None)
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
        delattr(unreal, HANDLE_NAME)
    (OUT / 'network_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('TIME_NETWORK_VERIFY_' + ('PASS' if report['passed'] else 'FAIL: ' + report.get('error', report.get('restore_error', 'unknown'))))


def tick(_delta):
    try:
        now = time.monotonic()
        assert now - STATE['started'] < TIMEOUT_SECONDS, 'Timed out waiting for a ready listen server and client / replication'
        server, client = network_worlds()
        if server is None or client is None:
            return
        restore_play_settings()
        server_gs, client_gs = (unreal.GameplayStatics.get_game_state(world) for world in [server, client])
        if not all(isinstance(gs, unreal.TownAgeGameState) and gs.is_clock_ready() for gs in [server_gs, client_gs]):
            return
        stage = STATE['stage']
        if stage == 'waiting':
            assert server_gs.has_authority()
            assert not client_gs.has_authority()
            assert server_gs.set_time_of_day(21.5)
            STATE['changed_clock'] = True
            assert server_gs.set_day_length_minutes(1)
            STATE.update(stage='fast_replication', since=now)
            return
        if now - STATE['since'] < 3.0:
            return
        if stage == 'fast_replication':
            check_agreement(server, client, server_gs, client_gs, 1.0, 'one_minute_day')
            before = client_gs.get_total_world_hours()
            assert not client_gs.set_time_of_day(12), 'Client directly changed authoritative time'
            assert not client_gs.set_day_length_minutes(60), 'Client directly changed authoritative rate'
            assert abs(client_gs.get_total_world_hours() - before) < .01, 'Rejected client setter changed local clock'
            STATE['client_setters_rejected'] = True
            before = server_gs.get_total_world_hours()
            assert server_gs.set_day_length_minutes(24)
            after = server_gs.get_total_world_hours()
            assert abs(after - before) < .01, ('Rate change jumped world time', before, after)
            STATE['rate_change_hour_difference'] = abs(after - before)
            STATE.update(stage='normal_replication', since=now)
            return
        if stage == 'normal_replication':
            check_agreement(server, client, server_gs, client_gs, 24.0, 'normal_day_after_rate_change')
            finish()
    except Exception:
        finish(traceback.format_exc())


try:
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    if not worlds and hasattr(unreal, 'PlayNetMode') and hasattr(unreal, 'LevelEditorPlaySettings'):
        settings = unreal.get_default_object(unreal.LevelEditorPlaySettings)
        keys = ['play_number_of_clients', 'play_net_mode', 'run_under_one_process']
        setattr(unreal, RESTORE_NAME, {key: settings.get_editor_property(key) for key in keys})
        settings.set_editor_property('play_number_of_clients', 2)
        settings.set_editor_property('play_net_mode', unreal.PlayNetMode.PIE_LISTEN_SERVER)
        settings.set_editor_property('run_under_one_process', True)
        STATE['requested_pie'] = True
    elif not worlds:
        STATE['configuration_note'] = ('PlayNetMode is not Python-wrapped; caller must start two-player '
                                       'listen-server PIE under one process. No editor settings changed.')
    setattr(unreal, HANDLE_NAME, unreal.register_slate_post_tick_callback(tick))
    if STATE['requested_pie']:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    print('TIME_NETWORK_VERIFY_READY')
except Exception:
    finish(traceback.format_exc())
