"""Leave a clean standalone PC review at the cottage; no interaction is auto-fired."""
import json
from pathlib import Path
import unreal

OUT=Path(__file__).resolve().parents[2]/'Saved/Doors/Integration'
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
camera=unreal.Vector(3400,650,850)
target=unreal.Vector(2920,-1080,170)
editor.set_level_viewport_camera_info(camera,unreal.MathLibrary.find_look_at_rotation(camera,target))
STATE={'moved':False}

def tick(delta_time):
    worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
    if not worlds:return
    pawn=unreal.GameplayStatics.get_player_pawn(worlds[0],0)
    if not isinstance(pawn,unreal.TownAgePlayer):return
    now=unreal.GameplayStatics.get_time_seconds(worlds[0])
    if now<.7:return
    if not STATE['moved']:
        pawn.set_actor_location(unreal.Vector(2920,-865,90.15),False,True)
        pawn.set_actor_rotation(unreal.Rotator(pitch=0,yaw=-90,roll=0),True)
        STATE['moved']=True
        return
    interaction=pawn.get_interaction_component();interaction.refresh_selection()
    if interaction.has_interactable():
        (OUT/'review_ready.json').write_text(json.dumps({'level':'L_VillageTerrain_01','mode':'PC standalone','G_ready':True,'auto_interaction_fired':False}),encoding='utf8')
        unreal.unregister_slate_post_tick_callback(HANDLE)
        print('DOOR_PC_REVIEW_READY')

HANDLE=unreal.register_slate_post_tick_callback(tick)
