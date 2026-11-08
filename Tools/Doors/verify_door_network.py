"""Prepare real remote G/touch tests; Python must never invoke client RPCs."""
import json
import math
import traceback
from pathlib import Path

import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Doors/Integration'
STATE = {'stage': 0, 'since': None, 'samples': [], 'checks': []}
PHASE = unreal.TownAgeDoorPhase


def advance(value, now):
    STATE['stage'] = value
    STATE['since'] = now


def finish(error=None):
    report = {'passed': error is None, 'error': error, 'checks': STATE['checks'],
              'samples': STATE['samples'], 'native_input_required': True,
              'physical_mobile_device_tested': False}
    (OUT / 'network_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    unreal.unregister_slate_post_tick_callback(HANDLE)


def tick(delta_time):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        servers = [w for w in worlds if unreal.SystemLibrary.is_server(w)]
        clients = [w for w in worlds if not unreal.SystemLibrary.is_server(w)]
        if not servers or not clients:
            return
        server, client = servers[0], clients[0]
        cp = unreal.GameplayStatics.get_player_pawn(client, 0)
        if not isinstance(cp, unreal.TownAgePlayer):
            return
        ps = cp.get_editor_property('player_state')
        if ps is None:
            return
        player_id = ps.get_editor_property('player_id')
        pawns = unreal.GameplayStatics.get_all_actors_of_class(server, unreal.TownAgePlayer)
        remote = [p for p in pawns if p.get_editor_property('player_state') is not None
                  and p.get_editor_property('player_state').get_editor_property('player_id') == player_id]
        hosts = [p for p in pawns if p not in remote]
        if len(remote) != 1 or not hosts:
            return
        sp, host = remote[0], hosts[0]
        st, ct = sp.get_door_traversal_component(), cp.get_door_traversal_component()
        house = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(server, unreal.Actor)
                      if a.get_class().get_name() == 'BP_CozyHouse01_Split_C'), None)
        if house is None:
            return
        portal = house.get_component_by_class(unreal.TownAgeDoorPortalComponent)
        now = unreal.GameplayStatics.get_time_seconds(server)
        if STATE['since'] is None:
            STATE['since'] = now
        elapsed = now - STATE['since']
        p, q, h = sp.get_actor_location(), cp.get_actor_location(), host.get_actor_location()
        if len(STATE['samples']) < 2400:
            STATE['samples'].append({'time': now, 'stage': STATE['stage'],
                'server': [p.x,p.y,p.z], 'client': [q.x,q.y,q.z], 'host': [h.x,h.y,h.z],
                'server_phase': str(st.get_phase()), 'client_phase': str(ct.get_phase())})
        current = STATE['stage']
        if current == 0 and elapsed > 1:
            # A failed observer can be resumed after an already verified entry;
            # never fake an enter by teleporting the pawn into the room.
            prior_path = OUT / 'network_report.json'
            prior = json.loads(prior_path.read_text(encoding='utf8')) if prior_path.exists() else {}
            if p.x>40000 and q.x>40000 and 'native_client_enter_committed' in prior.get('checks', []):
                STATE['checks']=prior['checks']
                STATE['host_origin']=[h.x,h.y,h.z]
                STATE['arrival']=[q.x,q.y,q.z]
                advance(4,now)
                return
            for pawn in (sp, cp):
                pawn.set_actor_location(unreal.Vector(2920, -865, 90.15), False, True)
                pawn.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=0), True)
            host.set_actor_location(unreal.Vector(2837,-865,90.15),False,True)
            host.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=0),True)
            advance(1,now)
        elif current == 1:
            cp.add_movement_input(unreal.Vector(0,-1,0),1,True)
            if elapsed > .8:
                cp.get_interaction_component().refresh_selection()
                assert cp.get_interaction_component().has_interactable()
                assert portal.can_use(host)
                STATE['host_origin']=[h.x,h.y,h.z]
                (OUT/'network_input_ready.json').write_text(json.dumps(
                    {'stage':'enter','input':'Native G in remote client window'}),encoding='utf8')
                print('DOOR_REMOTE_ENTER_READY')
                advance(2,now)
        elif current == 2 and st.is_busy():
            assert not portal.can_use(host), 'Linked reservation did not block another player'
            host.request_interaction()  # Authority-side rejected request, not client RPC proof.
            assert not host.get_door_traversal_component().is_busy()
            STATE['checks'].append('shared_reservation_rejects_other_player')
            advance(3,now)
        elif current == 3:
            if p.x>40000 and q.x>40000 and not st.is_busy() and not ct.is_busy():
                STATE['arrival']=[q.x,q.y,q.z]
                STATE['checks'].append('native_client_enter_committed')
                advance(4,now)
            elif elapsed>12:
                raise AssertionError('Remote enter failed: '+str(p)+' / '+str(q))
        elif current == 4 and elapsed > 2.2:
            assert p.x>40000 and q.x>40000, 'Client snapped back after entry'
            assert math.hypot(p.x-q.x,p.y-q.y)<6
            assert math.hypot(q.x-STATE['arrival'][0],q.y-STATE['arrival'][1])<6
            assert sp.get_editor_property('character_movement').is_moving_on_ground()
            assert cp.get_editor_property('character_movement').is_moving_on_ground()
            assert h.x<10000 and math.hypot(h.x-STATE['host_origin'][0],h.y-STATE['host_origin'][1])<5
            STATE['checks'].append('remote_inside_stable_grounded_other_player_outside')
            unreal.SystemLibrary.collect_garbage()
            advance(5,now)
        elif current == 5:
            # Use actual movement so CharacterMovement owns the client's turn;
            # direct editor rotation is not a network movement input.
            if elapsed<.6:
                cp.add_movement_input(unreal.Vector(0,1,0),1,True)
                return
            cp.get_interaction_component().refresh_selection()
            assert cp.get_interaction_component().has_interactable()
            (OUT/'network_input_ready.json').write_text(json.dumps(
                {'stage':'exit','input':'Native mobile USE or G in remote client window'}),encoding='utf8')
            print('DOOR_REMOTE_EXIT_READY')
            advance(6,now)
        elif current == 6 and st.is_busy():
            assert not portal.can_use(host), 'Interior use did not reserve the exterior side'
            STATE['checks'].append('inside_use_reserves_both_sides')
            advance(7,now)
        elif current == 7:
            if p.x<10000 and q.x<10000 and not st.is_busy() and not ct.is_busy():
                STATE['checks'].append('native_client_exit_committed')
                advance(8,now)
            elif elapsed>12:
                raise AssertionError('Remote exit failed: '+str(p)+' / '+str(q))
        elif current == 8 and elapsed>2.2:
            assert math.hypot(q.x-2920,q.y+920)<8, 'Return anchor drifted'
            assert math.hypot(p.x-q.x,p.y-q.y)<6
            assert math.hypot(h.x-STATE['host_origin'][0],h.y-STATE['host_origin'][1])<5
            assert 'BS_TownKeeper_Meshy_Locomotion' in cp.get_editor_property('mesh').get_anim_instance().get_animation_asset().get_name()
            assert portal.can_use(host)
            STATE['checks'].append('return_stable_idle_and_reservation_released')
            finish()
            print('DOOR_NETWORK_VERIFIED')
    except Exception:
        finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
print('DOOR_NETWORK_CHECK_READY')
