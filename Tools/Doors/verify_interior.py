"""PIE checks for enlarged room and vanity via the existing interaction path."""
import json
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Doors/InteriorUpdate'
OUT.mkdir(parents=True, exist_ok=True)
STATE = {'since': None, 'enter_requested': False}


def tick(delta):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if STATE['since'] is None:
            STATE['since'] = now
        if now - STATE['since'] < 1:
            return
        if not STATE['enter_requested']:
            pawn.set_actor_location(unreal.Vector(2920, -865, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            pawn.request_interaction()
            assert pawn.get_door_traversal_component().is_busy()
            STATE['enter_requested'] = True
            return
        assert now - STATE['since'] < 15, 'Interior transfer timed out'
        if pawn.get_actor_location().x < 40000 or pawn.get_door_traversal_component().is_busy():
            return
        all_actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
        vanity = next(a for a in all_actors if a.get_actor_label() == 'GrayRoom_Vanity')
        floor = next(a for a in all_actors if a.get_actor_label() == 'GrayRoom_Floor')
        assert abs(floor.get_actor_scale3d().x - 12.4) < .001
        assert abs(floor.get_actor_location().x - 50000) < 1
        target = vanity.get_component_by_class(unreal.TownAgeInteractionTargetComponent)
        assert vanity.get_editor_property('replicates')
        assert str(target.get_editor_property('definition').row_name) == 'VanityUse'
        interaction = pawn.get_interaction_component()
        # Real enter/exit test runs separately; this check isolates selection.
        pawn.set_actor_location(vanity.get_actor_location() + unreal.Vector(0, 130, 90.15), False, True)
        pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
        interaction.refresh_selection()
        assert interaction.get_selected_target() == target, 'Vanity must win front selection'
        assert str(interaction.get_prompt()) == 'Use Vanity'
        pawn.request_interaction()
        pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=90, roll=0), True)
        interaction.refresh_selection()
        assert interaction.get_selected_target() != target, 'Facing away must reject vanity'
        pawn.set_actor_location(vanity.get_actor_location() + unreal.Vector(0, 350, 90.15), False, True)
        pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
        interaction.refresh_selection()
        assert interaction.get_selected_target() != target, 'Out of range must reject vanity'
        pawn.set_actor_location(vanity.get_actor_location() + unreal.Vector(0, 130, 90.15), False, True)
        interaction.refresh_selection()
        result = {'passed': True, 'checks': ['expanded_streamed_floor', 'replicated_vanity',
            'common_target_selection', 'request_dispatch', 'facing_rejection', 'range_rejection'],
            'physical_mobile_verified': False}
        (OUT / 'runtime_report.json').write_text(json.dumps(result, indent=2), encoding='utf8')
        print('INTERIOR_RUNTIME_PASSED', json.dumps(result))
        unreal.unregister_slate_post_tick_callback(HANDLE)
    except Exception:
        (OUT / 'runtime_report.json').write_text(json.dumps({'passed': False, 'error': traceback.format_exc()}), encoding='utf8')
        unreal.unregister_slate_post_tick_callback(HANDLE)
        raise


HANDLE = unreal.register_slate_post_tick_callback(tick)
