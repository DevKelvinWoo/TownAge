"""Register remote-client checks; caller starts two-player listen-server PIE."""
import json
import traceback
from pathlib import Path

import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Interaction'
if hasattr(unreal, '_townage_network_check_handle'):
    unreal.unregister_slate_post_tick_callback(unreal._townage_network_check_handle)
STATE = {'stage': 0, 'since': None}


def tick(delta_time):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        servers = [w for w in worlds if unreal.SystemLibrary.is_server(w)]
        clients = [w for w in worlds if not unreal.SystemLibrary.is_server(w)]
        if not servers or not clients:
            return
        server, client = servers[0], clients[0]
        local_pc = unreal.GameplayStatics.get_player_controller(client, 0)
        client_pawn = unreal.GameplayStatics.get_player_pawn(client, 0)
        if local_pc is None or client_pawn is None:
            return
        player_state = client_pawn.get_editor_property('player_state')
        if player_state is None:
            return
        player_id = player_state.get_editor_property('player_id')
        remote = [pawn for pawn in unreal.GameplayStatics.get_all_actors_of_class(server, unreal.TownAgePlayer)
                  if pawn.get_editor_property('player_state') is not None
                  and pawn.get_editor_property('player_state').get_editor_property('player_id') == player_id]
        if not remote:
            return
        server_pawn = remote[0]
        houses = [a for a in unreal.GameplayStatics.get_all_actors_of_class(client, unreal.Actor)
                  if a.get_class().get_name() == 'BP_CozyHouse01_Split_C']
        if not houses:
            return
        target = houses[0].get_component_by_class(unreal.TownAgeInteractionTargetComponent)
        if target is None:
            return
        point = target.get_interaction_point()
        near = unreal.Vector(point.x, point.y + 160, 90.15)
        far = unreal.Vector(point.x + 800, point.y + 800, 90.15)
        now = unreal.GameplayStatics.get_time_seconds(server)
        if STATE['since'] is None:
            STATE['since'] = now
        if STATE['stage'] == 1:
            client_pawn.add_movement_input(unreal.Vector(0, -1, 0), 1, True)
        if now - STATE['since'] < 1:
            return
        interaction = client_pawn.get_interaction_component()
        stage = STATE['stage']
        if stage == 0:
            assert not unreal.SystemLibrary.is_standalone(server)
            assert local_pc.is_local_controller()
            for pawn in unreal.GameplayStatics.get_all_actors_of_class(server, unreal.TownAgePlayer):
                if pawn != server_pawn:
                    pawn.set_actor_location(far, False, True)
            for pawn in (server_pawn, client_pawn):
                pawn.set_actor_location(near, False, True)
                pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
        elif stage == 1:
            interaction.refresh_selection()
            assert interaction.get_selected_target() == target
            server_interaction = server_pawn.get_interaction_component()
            server_interaction.refresh_selection()
            (OUT / 'network_diagnostics.json').write_text(json.dumps({
                'player_id': player_id, 'client_pawn': client_pawn.get_name(),
                'server_pawn': server_pawn.get_name(), 'server_location': str(server_pawn.get_actor_location()),
                'server_forward': str(server_pawn.get_actor_forward_vector()),
                'server_selected': str(server_interaction.get_selected_target()),
                'client_location': str(client_pawn.get_actor_location()),
                'client_forward': str(client_pawn.get_actor_forward_vector())}, indent=2), encoding='utf8')
            assert server_interaction.has_interactable(), 'Authority must see an eligible door before client RPC'
            print('INTERACTION_REMOTE_VALID_REQUEST_BEGIN')
            (OUT / 'network_input_ready.json').write_text(json.dumps({
                'client_world': client.get_path_name(), 'input': 'Press native G or touch USE',
                'reason': 'Python ProcessEvent forces editor RPC callspace to Local.'}), encoding='utf8')
        elif stage == 2:
            log_text = (OUT.parent / 'Logs/TownAge.log').read_text(encoding='utf8', errors='replace')
            valid_section = log_text.rsplit('INTERACTION_REMOTE_VALID_REQUEST_BEGIN', 1)[-1]
            if valid_section.count('Interaction executed:') == 0:
                return
            print('INTERACTION_REMOTE_EXPECTED_ONE_LOG_END')
        else:
            log_text = (OUT.parent / 'Logs/TownAge.log').read_text(encoding='utf8', errors='replace')
            valid_section = log_text.rsplit('INTERACTION_REMOTE_VALID_REQUEST_BEGIN', 1)[-1].split('INTERACTION_REMOTE_EXPECTED_ONE_LOG_END', 1)[0]
            valid_logs = valid_section.count('Interaction executed:')
            assert valid_logs == 1, ('Expected exactly one authoritative action', valid_logs)
            report = {'passed': True, 'server_world': server.get_path_name(),
                      'client_world': client.get_path_name(), 'interactor': server_pawn.get_name(),
                      'client_target': target.get_path_name(), 'expected_valid_action_logs': 1,
                      'actual_valid_action_logs': valid_logs,
                      'input_method': 'Native G/touch outside Python execution guard'}
            (OUT / 'network_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
            unreal.unregister_slate_post_tick_callback(HANDLE)
            print('INTERACTION_NETWORK_CHECK_COMPLETE')
            return
        STATE['stage'] += 1
        STATE['since'] = now
    except Exception:
        (OUT / 'network_report.json').write_text(json.dumps(
            {'passed': False, 'error': traceback.format_exc(), 'state': STATE}, indent=2), encoding='utf8')
        unreal.unregister_slate_post_tick_callback(HANDLE)


HANDLE = unreal.register_slate_post_tick_callback(tick)
unreal._townage_network_check_handle = HANDLE
print('INTERACTION_NETWORK_CHECK_READY')
