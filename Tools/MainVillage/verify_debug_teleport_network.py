"""Verify owned debug-teleport RPC and replication in two-player listen PIE.

Run in a normal GPU editor with -ExecutePythonScript=<this file> and the
per-process config override:
-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=PIE_ListenServer
The native PlayNetMode enum has no Python wrapper in UE 5.8. Other play settings
are changed transiently without property notifications or SaveConfig, restored
before exit, and no map is saved. No external server is contacted.
"""
import hashlib
import json
import time
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/DebugTeleport'
OUT.mkdir(parents=True, exist_ok=True)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
SETTINGS = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
OVERRIDES = {
    'RunUnderOneProcess': True,
    'PlayNumberOfClients': 2,
    'bLaunchSeparateServer': False,
}
ORIGINAL = {key: SETTINGS.get_editor_property(key) for key in OVERRIDES}
CONFIG_FILE = ROOT / 'Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini'
CONFIG_HASH = hashlib.sha256(CONFIG_FILE.read_bytes()).hexdigest() if CONFIG_FILE.exists() else None
STATE = {'start': time.monotonic(), 'since': time.monotonic(), 'stage': 'connect', 'busy': False}
REPORT = {'map': '/Game/Maps/L_MainVillage_Art_01', 'checks': [],
          'net_mode': 'PIE_ListenServer supplied by per-process -ini override; verified through actual worlds',
          'editor_config_sha256_before': CONFIG_HASH,
          'settings_before': {key: str(value) for key, value in ORIGINAL.items()},
          'not_tested': ['Invalid packet transport (rejection is invoked directly on matched authority)',
                         'Packaged dedicated server permission opt-in', 'External hosting',
                         'Shipping executable', 'Physical Ctrl+Alt+mouse input']}


def xyz(vector):
    return [vector.x, vector.y, vector.z]


def player_id(controller):
    state = controller.get_editor_property('player_state')
    return state.get_editor_property('player_id') if state else None


def check(name, passed, **evidence):
    REPORT['checks'].append({'name': name, 'passed': bool(passed), **evidence})
    assert passed, name


def advance(name):
    STATE.update(stage=name, since=time.monotonic())


def restore_settings():
    for key, value in ORIGINAL.items():
        SETTINGS.set_editor_property(key, value, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    REPORT['settings_restored'] = all(SETTINGS.get_editor_property(key) == value
                                      for key, value in ORIGINAL.items())


def finish(error=None):
    REPORT.update(passed=error is None, error=error)
    restore_settings()
    config_after = hashlib.sha256(CONFIG_FILE.read_bytes()).hexdigest() if CONFIG_FILE.exists() else None
    REPORT['editor_config_sha256_after'] = config_after
    REPORT['editor_config_hash_matches_before_shutdown'] = config_after == CONFIG_HASH
    REPORT['editor_config_note'] = ('PIE may update unrelated editor preferences; only the three '
        'transient play settings are asserted restored. The per-process net-mode override is not saved by this script.')
    (OUT / 'network_report.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(_):
    if STATE['busy']:
        return
    STATE['busy'] = True
    try:
        now = time.monotonic()
        assert now - STATE['start'] < 90, 'Two-player PIE verification exceeded 90 seconds'
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        server_worlds = [world for world in worlds if unreal.SystemLibrary.is_server(world)]
        client_worlds = [world for world in worlds if not unreal.SystemLibrary.is_server(world)]
        if len(server_worlds) != 1 or len(client_worlds) != 1:
            return
        server_world, client_world = server_worlds[0], client_worlds[0]
        client = unreal.GameplayStatics.get_player_controller(client_world, 0)
        if not isinstance(client, unreal.TownAgePlayerController) or not client.get_controlled_pawn():
            return
        identity = player_id(client)
        if identity is None:
            return
        server_controllers = unreal.GameplayStatics.get_all_actors_of_class(
            server_world, unreal.TownAgePlayerController)
        matches = [pc for pc in server_controllers if player_id(pc) == identity]
        if len(matches) != 1 or not matches[0].get_controlled_pawn():
            return
        authority = matches[0]
        client_pawn, server_pawn = client.get_controlled_pawn(), authority.get_controlled_pawn()
        hosts = [pc for pc in server_controllers if pc.is_local_controller()]
        if len(hosts) != 1 or not hosts[0].get_controlled_pawn() or hosts[0] == authority:
            return
        host = hosts[0]

        if STATE['stage'] == 'connect':
            if now - STATE['since'] < 5:
                return
            check('Remote local controller resolves to matching authority',
                  client.is_local_controller() and not client.has_authority()
                  and authority.has_authority() and not authority.is_local_controller(),
                  player_id=identity, client_world=client_world.get_path_name(),
                  server_world=server_world.get_path_name())
            STATE['host_before'] = host.get_controlled_pawn().get_actor_location()
            STATE['destination'] = unreal.Vector(3500, 600, 9)
            check('Owning client submitted request', client.request_debug_teleport_at(STATE['destination']))
            advance('replicate')
        elif STATE['stage'] == 'replicate':
            expected = STATE['destination']
            server_location, client_location = server_pawn.get_actor_location(), client_pawn.get_actor_location()
            server_at_target = abs(server_location.x - expected.x) < 5 and abs(server_location.y - expected.y) < 5
            client_at_target = abs(client_location.x - expected.x) < 5 and abs(client_location.y - expected.y) < 5
            if not (client.last_debug_teleport_succeeded and server_at_target and client_at_target):
                assert now - STATE['since'] < 15, ('Teleport failed to replicate: '
                    + str((xyz(server_location), xyz(client_location), client.last_debug_teleport_notice)))
                return
            if now - STATE['since'] < 1:
                return
            check('Authority committed and owner received movement',
                  (server_location - client_location).length() < 5,
                  server_cm=xyz(server_location), client_cm=xyz(client_location),
                  notice=client.last_debug_teleport_notice)
            check('Other player did not teleport',
                  (host.get_controlled_pawn().get_actor_location() - STATE['host_before']).length() < 5)
            STATE['server_before_rejection'] = server_location
            STATE['client_before_rejection'] = client_location
            # Python's editor-script guard forces a direct RPC call local.
            # Exercise malformed-intent validation on the matched authority,
            # without claiming this invalid request traveled over the wire.
            authority.call_method('ServerDebugTeleport', (unreal.Vector(20000000, 0, 0),))
            advance('reject')
        elif STATE['stage'] == 'reject':
            if authority.last_debug_teleport_succeeded or 'bounds' not in authority.last_debug_teleport_notice.lower():
                assert now - STATE['since'] < 10, 'Server did not return the expected bounds rejection'
                return
            if now - STATE['since'] < 1:
                return
            server_location, client_location = server_pawn.get_actor_location(), client_pawn.get_actor_location()
            check('Invalid intent rejected by authoritative RPC handler', not authority.last_debug_teleport_succeeded,
                  notice=authority.last_debug_teleport_notice, invocation='Direct on matched authority, not packet transport')
            check('Rejected RPC preserves authority and owner position',
                  (server_location - STATE['server_before_rejection']).length() < 5
                  and (client_location - STATE['client_before_rejection']).length() < 5,
                  server_cm=xyz(server_location), client_cm=xyz(client_location))
            finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        STATE['busy'] = False


try:
    assert LEVELS.load_level(REPORT['map'])
    for key, value in OVERRIDES.items():
        SETTINGS.set_editor_property(key, value, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    HANDLE = unreal.register_slate_post_tick_callback(tick)
    LEVELS.editor_request_begin_play()
except Exception:
    restore_settings()
    raise
