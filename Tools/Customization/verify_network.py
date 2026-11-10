"""Observe a real remote G -> color-chip -> Close workflow in two-player PIE.

Never invoke the client RPC from editor Python: use native G/button input after
network_input_ready.json appears. Other player and shared village stay intact.
"""
import json
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Customization'
STATE = {'stage': 0, 'since': None, 'start': None, 'checks': []}


def advance(stage, now):
    STATE['stage'], STATE['since'] = stage, now


def ready(value):
    (OUT / 'network_input_ready.json').write_text(json.dumps({'input': value}), encoding='utf8')
    print('CUSTOMIZATION_REMOTE_READY', value)


def finish(error=None):
    (OUT / 'network_report.json').write_text(json.dumps({'passed': error is None,
        'error': error, 'checks': STATE['checks'], 'native_client_input': True,
        'physical_mobile_verified': False}, indent=2), encoding='utf8')
    unreal.unregister_slate_post_tick_callback(HANDLE)


def tick(delta):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        servers = [w for w in worlds if unreal.SystemLibrary.is_server(w)]
        clients = [w for w in worlds if not unreal.SystemLibrary.is_server(w)]
        if not servers or not clients:
            return
        server, client = servers[0], clients[0]
        cp = unreal.GameplayStatics.get_player_pawn(client, 0)
        if not isinstance(cp, unreal.TownAgePlayer) or cp.get_editor_property('player_state') is None:
            return
        player_id = cp.get_editor_property('player_state').get_editor_property('player_id')
        pawns = unreal.GameplayStatics.get_all_actors_of_class(server, unreal.TownAgePlayer)
        sp = next((p for p in pawns if p.get_editor_property('player_state') is not None
                   and p.get_editor_property('player_state').get_editor_property('player_id') == player_id), None)
        host = next((p for p in pawns if p != sp), None)
        if not sp or not host:
            return
        now = unreal.GameplayStatics.get_time_seconds(server)
        if STATE['start'] is None:
            STATE['start'] = STATE['since'] = now
        assert now - STATE['start'] < 180, 'Remote workflow timed out at ' + str(STATE['stage'])
        sc, cc = sp.get_customization_component(), cp.get_customization_component()
        elapsed = now - STATE['since']
        stage = STATE['stage']
        if stage == 0 and elapsed > 1:
            vanity = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(server, unreal.Actor)
                          if a.get_actor_label() == 'GrayRoom_Vanity')
            variant = unreal.load_asset('/Game/Developers/CustomizationTests/SK_OwnerPreviewVariant')
            assert variant, 'Run create_owner_preview_fixture.py before the network test'
            for pawn in (sp, cp):
                avatar = pawn.get_editor_property('mesh')
                avatar.set_skeletal_mesh_asset(variant)
                avatar.set_editor_property('relative_scale3d', unreal.Vector(.85, .85, 1.12))
                avatar.set_material(0, unreal.load_asset('/Game/Characters/Customization/M_TownKeeper_HairDye'))
                pawn.set_actor_location(vanity.get_actor_location() + unreal.Vector(0, 130, 90.15), False, True)
                pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            STATE['host_origin'] = host.get_actor_location()
            advance(1, now)
        elif stage == 1:
            # Background PIE can tick at 3Hz; allow several movement frames.
            if elapsed < 1.2:
                cp.add_movement_input(unreal.Vector(0, -1, 0), 1, True)
                return
            cc_owner_interaction = cp.get_interaction_component()
            cc_owner_interaction.refresh_selection()
            if not cc_owner_interaction.has_interactable():
                return
            ready('Press G in remote client window')
            advance(2, now)
        elif stage == 2 and sc.is_server_session_active() and cc.is_preview_ready():
            assert cc.is_customization_open()
            source_mesh = cp.get_editor_property('mesh')
            preview_mesh = cc.get_preview_actor().get_preview_mesh()
            assert preview_mesh.get_editor_property('skeletal_mesh_asset') == source_mesh.get_editor_property('skeletal_mesh_asset')
            assert preview_mesh.get_editor_property('skeletal_mesh_asset') != host.get_editor_property('mesh').get_editor_property('skeletal_mesh_asset')
            assert (preview_mesh.get_editor_property('relative_scale3d') - source_mesh.get_editor_property('relative_scale3d')).length() < .001
            assert not unreal.GameplayStatics.get_all_actors_of_class(server, unreal.TownAgeCustomizationPreview)
            assert len(unreal.GameplayStatics.get_all_actors_of_class(client, unreal.TownAgeCustomizationPreview)) == 1
            assert (host.get_actor_location() - STATE['host_origin']).length() < 2
            assert host.get_actor_location().x < 10000
            assert host.get_customization_component().get_hair_color_index() == 0
            STATE['checks'].extend(['native_remote_G_opens_authority_session',
                'preview_exists_only_in_participating_client', 'other_player_stays_village', 'different_players_use_their_own_mesh_and_scale'])
            ready('Click BLUE in remote customization window')
            advance(3, now)
        elif stage == 3 and sc.get_hair_color_index() == 2 and cc.get_hair_color_index() == 2:
            expected = sc.get_owner().get_editor_property('mesh').get_material(0).get_vector_parameter_value('HairTint')
            actual = cp.get_editor_property('mesh').get_material(0).get_vector_parameter_value('HairTint')
            assert actual == expected
            assert host.get_customization_component().get_hair_color_index() == 0
            STATE['checks'].extend(['native_chip_reaches_server', 'live_hair_color_replicates', 'other_player_appearance_unchanged'])
            ready('Click Close in remote customization window')
            advance(4, now)
        elif stage == 4 and not sc.is_server_session_active() and not cc.is_customization_open():
            assert sc.get_hair_color_index() == cc.get_hair_color_index() == 2
            assert not unreal.GameplayStatics.get_all_actors_of_class(client, unreal.TownAgeCustomizationPreview)
            STATE['movement_origin'] = sp.get_actor_location()
            STATE['checks'].append('native_close_preserves_color_and_cleans_preview')
            advance(5, now)
        elif stage == 5:
            if elapsed < .5:
                cp.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
            elif elapsed > 1.2:
                assert sp.get_actor_location().x - STATE['movement_origin'].x > 10
                assert (host.get_actor_location() - STATE['host_origin']).length() < 2
                STATE['checks'].append('remote_movement_restored_shared_world_unchanged')
                finish()
                print('CUSTOMIZATION_NETWORK_PASSED')
    except Exception:
        finish(traceback.format_exc())
        raise


previous = getattr(unreal, '_townage_customization_network_handle', None)
if previous is not None:
    unreal.unregister_slate_post_tick_callback(previous)
HANDLE = unreal.register_slate_post_tick_callback(tick)
unreal._townage_customization_network_handle = HANDLE
