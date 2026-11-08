"""Standalone enter/exit and cancellation checks; no saved actor placement changes."""
import json
import math
import traceback
from pathlib import Path

import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Doors/Integration'
OUT.mkdir(parents=True, exist_ok=True)
STATE = {'stage': 0, 'since': None, 'start': None, 'samples': [], 'checks': [],
         'entered': False, 'exited': False, 'cancelled': False}
PHASE = unreal.TownAgeDoorPhase


def stage(value, now):
    STATE['stage'] = value
    STATE['since'] = now


def fail_or_finish(error=None):
    result = {'passed': error is None, 'error': error, 'checks': STATE['checks'],
              'entered': STATE['entered'], 'exited': STATE['exited'],
              'cancelled': STATE['cancelled'], 'samples': STATE['samples'],
              'physical_mobile_device_tested': False}
    (OUT / 'runtime_report.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    unreal.unregister_slate_post_tick_callback(HANDLE)


def tick(delta_time):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not isinstance(pawn, unreal.TownAgePlayer):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if STATE['start'] is None:
            STATE['start'] = STATE['since'] = now
        assert now - STATE['start'] < 40, 'Door test timed out: ' + str(STATE['stage'])
        traversal = pawn.get_door_traversal_component()
        interaction = pawn.get_interaction_component()
        mesh = pawn.get_editor_property('mesh')
        animation = mesh.get_anim_instance()
        assert isinstance(animation, unreal.TownAgeDoorAnimInstance), animation
        phase = traversal.get_phase()
        position = pawn.get_actor_location()
        all_actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
        houses = [a for a in all_actors if a.get_class().get_name() == 'BP_CozyHouse01_Split_C']
        interiors = [a for a in all_actors if a.get_class().get_name() == 'BP_CozyHouse01_InteriorDoor_C']
        if not interiors:
            return
        interior = interiors[0]
        if len(STATE['samples']) < 1800:
            head = mesh.get_socket_transform('Head', unreal.RelativeTransformSpace.RTS_COMPONENT)
            hand = mesh.get_socket_transform('LeftHand', unreal.RelativeTransformSpace.RTS_COMPONENT)
            asset = animation.get_animation_asset()
            STATE['samples'].append({'time': now, 'stage': STATE['stage'], 'phase': str(phase),
                'position': [position.x, position.y, position.z],
                'head_cm': [head.translation.x, head.translation.y, head.translation.z],
                'head_quat': [head.rotation.x, head.rotation.y, head.rotation.z, head.rotation.w],
                'hand_cm': [hand.translation.x, hand.translation.y, hand.translation.z],
                'asset': asset.get_path_name() if asset else None})
        elapsed = now - STATE['since']
        current = STATE['stage']
        if current == 0 and elapsed > .8:
            assert len(houses) == 1
            floor = next(a for a in all_actors if a.get_actor_label() == 'GrayRoom_Floor')
            floor_position = floor.get_actor_location()
            assert abs(floor_position.x - 50000) < .1, floor_position
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(50000, 0, 500),
                unreal.Vector(50000, 0, -100), unreal.TraceTypeQuery.ECC_VISIBILITY,
                False, [], unreal.DrawDebugTrace.NONE, True)
            assert hit, 'Streamed room has no floor collision'
            assert abs(hit.to_dict()['location'].z) < .1
            STATE['checks'].append('streamed_floor_collision_and_offset')
            assert not traversal.is_busy()
            pawn.set_actor_location(unreal.Vector(2920, -865, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            stage(1, now)
        elif current == 1 and elapsed > .4:
            interaction.refresh_selection()
            assert interaction.has_interactable(), 'Outside door unavailable'
            pawn.request_interaction()
            assert traversal.is_busy()
            pawn.request_interaction()  # Busy press must not start a second sequence.
            stage(2, now)
        elif current == 2:
            if position.x > 40000 and not traversal.is_busy():
                STATE['entered'] = True
                STATE['checks'].append('push_enter_transfer_and_idle_restore')
                assert 'BS_TownKeeper_Meshy_Locomotion' in animation.get_animation_asset().get_name()
                STATE['interior_position'] = [position.x, position.y, position.z]
                stage(3, now)
            elif elapsed > 9:
                raise AssertionError('Entry failed; phase=' + str(phase) + ' position=' + str(position))
        elif current == 3 and elapsed > 1.0:
            assert pawn.get_editor_property('character_movement').is_moving_on_ground()
            assert abs(position.z - 90.15) < 5
            assert abs(position.x - STATE['interior_position'][0]) < 5
            STATE['checks'].append('interior_grounding_and_stability')
            unreal.SystemLibrary.collect_garbage()
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=90, roll=0), True)
            stage(4, now)
        elif current == 4 and elapsed > .4:
            interaction.refresh_selection()
            assert interaction.has_interactable(), 'Interior exit unavailable after GC'
            pawn.request_interaction()
            assert traversal.is_busy()
            stage(5, now)
        elif current == 5:
            if position.x < 10000 and not traversal.is_busy():
                STATE['exited'] = True
                STATE['checks'].append('pull_exit_transfer_and_idle_restore_after_gc')
                assert 'BS_TownKeeper_Meshy_Locomotion' in animation.get_animation_asset().get_name()
                assert abs(position.x - 2920) < 5 and abs(position.y + 920) < 5, position
                stage(6, now)
            elif elapsed > 9:
                raise AssertionError('Exit failed; phase=' + str(phase) + ' position=' + str(position))
        elif current == 6:
            if elapsed < .6:
                pawn.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
            elif elapsed > 1.2:
                assert position.x > 2940, 'Normal movement did not resume'
                assert pawn.get_editor_property('character_movement').is_moving_on_ground()
                STATE['checks'].append('movement_restored')
                pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
                stage(7, now)
        elif current == 7 and elapsed > .4:
            interaction.refresh_selection()
            assert interaction.has_interactable()
            pawn.request_interaction()
            stage(8, now)
        elif current == 8:
            if phase == PHASE.ACTION and traversal.get_animation_time() > .65:
                houses[0].destroy_actor()
                stage(9, now)
            elif elapsed > 5:
                raise AssertionError('Cancellation test never reached action')
        elif current == 9 and elapsed > .8:
            assert not traversal.is_busy()
            assert 'BS_TownKeeper_Meshy_Locomotion' in animation.get_animation_asset().get_name()
            spring = pawn.get_component_by_class(unreal.SpringArmComponent)
            assert spring.get_editor_property('do_collision_test')
            assert spring.get_editor_property('enable_camera_lag')
            assert interior.get_component_by_class(unreal.TownAgeDoorPortalComponent).can_use(pawn)
            STATE['cancelled'] = True
            STATE['checks'].append('destroyed_portal_restores_idle_camera_input_and_reservation')
            assert any('A_TownKeeper_DoorPush' in (s['asset'] or '') for s in STATE['samples'])
            assert any('A_TownKeeper_DoorPull' in (s['asset'] or '') for s in STATE['samples'])
            fail_or_finish()
            print('DOOR_RUNTIME_VERIFIED')
    except Exception:
        fail_or_finish(traceback.format_exc())


HANDLE = unreal.register_slate_post_tick_callback(tick)
print('DOOR_RUNTIME_CHECK_READY')
