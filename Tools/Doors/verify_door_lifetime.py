"""In two-player PIE, destroy the active remote pawn and verify reservation cleanup."""
import json
import traceback
from pathlib import Path
import unreal

OUT=Path(__file__).resolve().parents[2]/'Saved/Doors/Integration'
STATE={'stage':0,'since':None}

def tick(delta_time):
    try:
        worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
        server=next((w for w in worlds if unreal.SystemLibrary.is_server(w)),None)
        client=next((w for w in worlds if not unreal.SystemLibrary.is_server(w)),None)
        if server is None or client is None:return
        now=unreal.GameplayStatics.get_time_seconds(server)
        if STATE['since'] is None:STATE['since']=now
        elapsed=now-STATE['since']
        if STATE['stage']<2:
            cp=unreal.GameplayStatics.get_player_pawn(client,0)
            if cp is None:return
            player_id=cp.get_editor_property('player_state').get_editor_property('player_id')
            pawns=unreal.GameplayStatics.get_all_actors_of_class(server,unreal.TownAgePlayer)
            sp=next(p for p in pawns if p.get_editor_property('player_state').get_editor_property('player_id')==player_id)
            host=next(p for p in pawns if p!=sp)
            house=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(server,unreal.Actor) if a.get_class().get_name()=='BP_CozyHouse01_Split_C')
            portal=house.get_component_by_class(unreal.TownAgeDoorPortalComponent)
            if STATE['stage']==0:
                if elapsed<.5:
                    cp.add_movement_input(unreal.Vector(0,-1,0),1,True)
                    return
                cp.get_interaction_component().refresh_selection()
                assert cp.get_interaction_component().has_interactable()
                (OUT/'lifetime_input_ready.json').write_text('{"input":"Native G on remote client"}',encoding='utf8')
                STATE['stage']=1
                print('DOOR_LIFETIME_INPUT_READY')
            elif sp.get_door_traversal_component().get_phase()==unreal.TownAgeDoorPhase.ACTION and sp.get_door_traversal_component().get_animation_time()>.5:
                assert not portal.can_use(host)
                STATE['host']=host;STATE['portal']=portal
                sp.destroy_actor()
                STATE['stage']=2;STATE['since']=now
        elif elapsed>1:
            host=STATE['host'];portal=STATE['portal']
            assert not host.get_door_traversal_component().is_busy()
            assert portal.can_use(host),'Destroyed participant left doorway locked'
            report={'passed':True,'participant_destroyed_during_action':True,'linked_reservation_released':True,'other_player_remains':True,'test_scope':'Server pawn EndPlay cleanup, not a transport-level disconnect'}
            (OUT/'lifetime_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
            unreal.unregister_slate_post_tick_callback(HANDLE)
            print('DOOR_LIFETIME_VERIFIED')
    except Exception:
        (OUT/'lifetime_report.json').write_text(json.dumps({'passed':False,'error':traceback.format_exc()},indent=2),encoding='utf8')
        unreal.unregister_slate_post_tick_callback(HANDLE)

HANDLE=unreal.register_slate_post_tick_callback(tick)
print('DOOR_LIFETIME_CHECK_READY')
