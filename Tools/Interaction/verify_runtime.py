"""Register a short PIE interaction check without changing saved player placement."""
import json
import traceback
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Interaction'
STATE = {'stage': 0, 'since': None, 'checks': []}


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
        if STATE['since'] is None:
            STATE['since'] = now
        if now - STATE['since'] < .6:
            return
        interaction = pawn.get_interaction_component()
        houses = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                  if a.get_class().get_name() == 'BP_CozyHouse01_Split_C']
        assert len(houses) == 1
        target = houses[0].get_component_by_class(unreal.TownAgeInteractionTargetComponent)
        assert target
        point = target.get_interaction_point()
        near = unreal.Vector(point.x, point.y + 160, 90.15)
        interaction.refresh_selection()
        stage = STATE['stage']
        if stage == 0:
            assert not interaction.has_interactable(), 'PlayerStart must be outside interaction range'
            pawn.request_interaction()
            STATE['checks'].append('far_start_disabled')
            pawn.set_actor_location(near, False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
        elif stage == 1:
            assert interaction.get_selected_target() == target
            assert str(interaction.get_prompt()) == 'Inspect Door'
            assert houses[0].get_editor_property('replicates')
            print('INTERACTION_EXPECT_ONE_LOG_BEGIN')
            pawn.request_interaction()
            pawn.request_interaction()  # Same-frame repeat must be rate limited.
            print('INTERACTION_EXPECT_ONE_LOG_END')
            STATE['checks'].append('near_facing_enabled_and_duplicate_request_sent')
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=90, roll=0), True)
        elif stage == 2:
            assert not interaction.has_interactable(), 'Facing away must disable the prompt'
            pawn.request_interaction()
            STATE['checks'].append('turned_away_disabled')
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            pawn.set_actor_location(unreal.Vector(point.x, point.y + 350, 90.15), False, True)
        elif stage == 3:
            assert not interaction.has_interactable(), 'Leaving range must disable interaction'
            pawn.request_interaction()
            STATE['checks'].append('left_range_disabled')
            pawn.set_actor_location(near, False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
        else:
            assert interaction.get_selected_target() == target
            position = pawn.get_actor_location()
            report = {'passed': True, 'checks': STATE['checks'],
                      'expected_action_logs_during_check': 1,
                      'player_cm': [position.x, position.y, position.z],
                      'target': target.get_path_name(), 'prompt': str(interaction.get_prompt()),
                      'input_left_ready': 'G or mobile USE', 'door_animation_created': False,
                      'physical_mobile_device_tested': False, 'multiclient_tested': False}
            (OUT / 'runtime_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
            unreal.unregister_slate_post_tick_callback(HANDLE)
            print('INTERACTION_RUNTIME_PASSED')
            return
        STATE['stage'] += 1
        STATE['since'] = now
    except Exception:
        (OUT / 'runtime_report.json').write_text(json.dumps(
            {'passed': False, 'error': traceback.format_exc(), 'state': STATE}, indent=2), encoding='utf8')
        unreal.unregister_slate_post_tick_callback(HANDLE)


HANDLE = unreal.register_slate_post_tick_callback(tick)
print('INTERACTION_RUNTIME_CHECK_READY')
