"""Exercise the real debug-teleport authority path in standalone PIE, then exit.

Use a normal editor with -ExecutePythonScript=<this file>. Does not save the map.
The keyboard/mouse chord still needs an interactive input check; these tests
exercise the same request and authority validation called by that chord.
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
EDITOR_ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
FIXTURE_TAG = 'TownAge_DebugTeleportCeilingFixture'
MAP_FILE = ROOT / 'Content/Maps/L_MainVillage_Art_01.umap'
MAP_HASH = hashlib.sha256(MAP_FILE.read_bytes()).hexdigest()
STATE = {'start': time.monotonic(), 'since': time.monotonic(), 'stage': 'wait', 'busy': False}
REPORT = {'checks': [], 'map': '/Game/Maps/L_MainVillage_Art_01',
          'not_tested': ['Physical keyboard/mouse chord', 'Network client RPC replication',
                         'Packaged Shipping binary', 'Door/customization busy rejection']}


def xyz(v):
    return [v.x, v.y, v.z]


def record(name, passed, **data):
    REPORT['checks'].append({'name': name, 'passed': bool(passed), **data})
    assert passed, name


def stage(name):
    STATE.update(stage=name, since=time.monotonic())


def finish(error=None):
    REPORT.update(passed=error is None, error=error)
    REPORT['map_unchanged_on_disk'] = hashlib.sha256(MAP_FILE.read_bytes()).hexdigest() == MAP_HASH
    (OUT / 'report.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def tick(_):
    if STATE['busy']:
        return
    STATE['busy'] = True
    try:
        now = time.monotonic()
        assert now - STATE['start'] < 90, 'PIE teleport verification timed out'
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        assert len(worlds) == 1, 'Run standalone one-player PIE'
        world = worlds[0]
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not isinstance(pc, unreal.TownAgePlayerController) or not isinstance(pawn, unreal.TownAgePlayer):
            return
        movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
        capsule = pawn.get_component_by_class(unreal.CapsuleComponent)
        if STATE['stage'] == 'wait':
            if now - STATE['since'] < 4 or not movement.is_moving_on_ground():
                return
            before = pawn.get_actor_location()
            point = unreal.Vector(3500, 600, 9)
            accepted = pc.request_debug_teleport_at(point)
            after = pawn.get_actor_location()
            record('Walkable destination accepted', accepted and pc.last_debug_teleport_succeeded,
                   before_cm=xyz(before), after_cm=xyz(after), notice=pc.last_debug_teleport_notice)
            record('Capsule placed above clicked floor', abs(after.x-point.x) < 1 and abs(after.y-point.y) < 1
                   and abs(after.z - (point.z + capsule.get_scaled_capsule_half_height() + 3)) < 5)
            record('Velocity stopped', movement.velocity.length() < .1)
            record('Immediate retry rate limited', not pc.request_debug_teleport_at(unreal.Vector(3600, 600, 9)))
            stage('settle')
        elif STATE['stage'] == 'settle':
            if now - STATE['since'] < .5:
                return
            record('Landed safely after teleport', movement.is_moving_on_ground())
            before = pawn.get_actor_location()
            record('Out-of-bounds rejected', not pc.request_debug_teleport_at(unreal.Vector(10000001, 0, 0)))
            record('Non-finite rejected', not pc.request_debug_teleport_at(unreal.Vector(float('nan'), 0, 0)))
            record('No floor rejected', not pc.request_debug_teleport_at(unreal.Vector(3850, 600, 10000)),
                   notice=pc.last_debug_teleport_notice)
            record('Rejected requests do not move pawn', (pawn.get_actor_location() - before).length() < .1)
            # A low ceiling does not intercept the floor trace, but intersects
            # the standing capsule. This verifies clearance independently.
            fixtures = unreal.GameplayStatics.get_all_actors_with_tag(world, FIXTURE_TAG)
            assert len(fixtures) == 1, 'Expected exactly one duplicated ceiling fixture in PIE'
            obstacle = fixtures[0]
            obstacle.static_mesh_component.set_collision_profile_name('BlockAll')
            STATE['obstacle'] = obstacle
            stage('blocked')
        elif STATE['stage'] == 'blocked':
            if now - STATE['since'] < .3:
                return
            before = pawn.get_actor_location()
            record('Low-ceiling capsule overlap rejected', not pc.request_debug_teleport_at(unreal.Vector(3850, 600, 9)),
                   notice=pc.last_debug_teleport_notice)
            record('Blocked destination does not move pawn', (pawn.get_actor_location() - before).length() < .1)
            STATE['obstacle'].static_mesh_component.set_collision_profile_name('NoCollision')
            stage('clear')
        elif STATE['stage'] == 'clear':
            if now - STATE['since'] < .3:
                return
            record('Same point accepted after disabling obstacle', pc.request_debug_teleport_at(unreal.Vector(3850, 600, 9)),
                   notice=pc.last_debug_teleport_notice)
            stage('ui')
        elif STATE['stage'] == 'ui':
            if now - STATE['since'] < .3:
                return
            pc.toggle_lighting_preview()
            record('Lighting UI blocks request', not pc.request_debug_teleport_at(unreal.Vector(3500, 600, 9)))
            pc.toggle_lighting_preview()
            finish()
    except Exception:
        finish(traceback.format_exc())
    finally:
        STATE['busy'] = False


assert LEVELS.load_level(REPORT['map'])
# The Blueprint-internal deferred spawn functions are not exposed to Python.
# Create an unsaved editor fixture that PIE duplicates, then toggle only its PIE
# collision. The editor process exits without saving this map.
assert not any(actor.actor_has_tag(FIXTURE_TAG) for actor in EDITOR_ACTORS.get_all_level_actors())
fixture = EDITOR_ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(3850, 600, 174))
fixture.set_actor_label('DebugTeleport_CeilingFixture_UnSaved')
fixture.tags = [FIXTURE_TAG]
fixture.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
fixture.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
fixture.set_actor_scale3d(unreal.Vector(3, 3, .3))
fixture.set_actor_hidden_in_game(True)
fixture.static_mesh_component.set_collision_profile_name('NoCollision')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
HANDLE = unreal.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
