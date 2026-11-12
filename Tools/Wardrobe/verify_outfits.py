"""Check the real wardrobe in standalone or listen-server PIE."""

import json
import time
import traceback
from pathlib import Path

import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Wardrobe'
FIST_FOLDER = '/Game/Characters/Meshy/TownKeeper_ClosedFists/candidate_v003'
ORIGINAL_STEPS = [('SK_PinkDress', 1), ('SK_YellowOveralls', 2), ('SK_TownKeeper_Meshy', 0)]
FIST_STEPS = [('SK_PinkDress_ClosedFists', 1), ('SK_YellowOveralls_ClosedFists', 2),
              ('SK_TownKeeper_ClosedFists', 0)]
STEPS = [fitted if unreal.EditorAssetLibrary.does_asset_exist(FIST_FOLDER + '/' + fitted[0]) else original
         for original, fitted in zip(ORIGINAL_STEPS, FIST_STEPS)]
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
NETWORK = '-TownAgeWardrobeListenServer' in unreal.SystemLibrary.get_command_line()
REPORT = 'outfit_network.json' if NETWORK else 'outfit_runtime.json'
START = time.monotonic()
STATE = {'stage': 'start', 'since': START, 'checks': [], 'index': 0}


def advance(stage):
    STATE.update(stage=stage, since=time.monotonic())


def finish(error=None):
    (OUT / REPORT).write_text(json.dumps({
        'passed': error is None, 'checks': STATE['checks'], 'stage': STATE['stage'],
        'error': error}, indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    LEVELS.editor_request_end_play()
    unreal.SystemLibrary.quit_editor()


def mesh_asset(component):
    return component.get_editor_property('skeletal_mesh_asset')


def check_equipped(world, custom, mesh, name, capture=False):
    preview = custom.get_preview_actor()
    portrait = preview.get_preview_mesh()
    assert mesh_asset(mesh).get_name() == name, mesh_asset(mesh).get_name()
    if name.endswith('_ClosedFists'):
        assert mesh_asset(mesh).get_path_name().startswith(FIST_FOLDER + '/')
    assert mesh_asset(portrait) == mesh_asset(mesh)
    assert mesh.get_anim_instance() == STATE['anim'], 'Outfit restarted player animation'
    assert portrait.get_anim_instance().get_animation_asset() == STATE['idle']
    assert custom.can_apply_makeup() and custom.can_dye_hair()
    if name != STEPS[-1][0]:
        material = 'M_' + name.removeprefix('SK_').removesuffix('_ClosedFists')
        assert mesh.get_material(1).get_name() == material
        assert portrait.get_material(1).get_name() == material
        assert mesh.get_material(1).get_editor_property('used_with_skeletal_mesh')
    if NETWORK:
        client = STATE['client']
        local = unreal.GameplayStatics.get_player_pawn(client, 0)
        pawns = unreal.GameplayStatics.get_all_actors_of_class(client, unreal.TownAgePlayer)
        other = next(p for p in pawns if p != local)
        assert mesh_asset(other.get_editor_property('mesh')).get_name() == name
        assert mesh_asset(local.get_editor_property('mesh')).get_name() == STEPS[-1][0]
        assert not unreal.GameplayStatics.get_all_actors_of_class(client, unreal.TownAgeCustomizationPreview)
    elif capture:
        target = preview.get_render_target()
        if name != STEPS[-1][0]:
            color = unreal.RenderingLibrary.read_render_target_uv(world, target, .5, .515)
            if name == STEPS[0][0]:
                assert color.r > 75 and color.r > color.g * 1.45 and color.b > color.g, color
            else:
                assert color.r > 100 and color.g > 80 and color.g > color.b * 2, color
        unreal.RenderingLibrary.export_render_target(world, target, str(OUT), name + '_PIE.png')


def tick(_):
    try:
        assert time.monotonic() - START < 75, 'Wardrobe verification timed out'
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        if NETWORK:
            world = next((w for w in worlds if unreal.SystemLibrary.is_server(w)), None)
            client = next((w for w in worlds if not unreal.SystemLibrary.is_server(w)), None)
            if not world or not client or not unreal.GameplayStatics.get_player_pawn(client, 0):
                return
            STATE['client'] = client
        else:
            assert len(worlds) == 1, 'Set PIE to Play Standalone with one player'
            world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not isinstance(pawn, unreal.TownAgePlayer):
            return
        custom = pawn.get_customization_component()
        mesh = pawn.get_editor_property('mesh')
        stage = STATE['stage']
        elapsed = time.monotonic() - STATE['since']
        if stage == 'start' and elapsed > 1.5:
            pawn.set_actor_location(unreal.Vector(2920, -865, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            pawn.request_interaction()
            assert pawn.is_door_busy()
            advance('travel')
        elif stage == 'travel' and pawn.get_actor_location().x > 40000 and not pawn.is_door_busy():
            wardrobe = next(actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                            if actor.get_actor_label() == 'GrayRoom_Wardrobe')
            pawn.set_actor_location(wardrobe.get_actor_location() + unreal.Vector(0, 130, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            if NETWORK:
                pawns = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.TownAgePlayer)
                observer = next(p for p in pawns if p != pawn)
                observer.set_actor_location(wardrobe.get_actor_location() + unreal.Vector(-180, 180, 90.15), False, True)
            advance('open')
        elif stage == 'open' and elapsed > .5:
            pawn.request_interaction()
            assert custom.is_server_session_active()
            assert custom.get_category() == unreal.TownAgeCosmeticCategory.WARDROBE
            STATE['checks'].append('wardrobe_actor_opens_wardrobe_after_door_travel')
            advance('preview')
        elif stage == 'preview' and custom.is_preview_ready():
            STATE['anim'] = mesh.get_anim_instance()
            portrait = custom.get_preview_actor().get_preview_mesh()
            STATE['idle'] = portrait.get_anim_instance().get_animation_asset()
            assert STATE['anim'] and STATE['idle'].get_name() == 'A_TownKeeper_Meshy_Idle'
            assert STATE['anim'].get_animation_asset().get_name() == 'BS_TownKeeper_Meshy_Locomotion'
            widgets = unreal.WidgetLibrary.get_all_widgets_of_class(world, unreal.TownAgeCustomizationWidget, True)
            assert len(widgets) == 1
            assert widgets[0].get_editor_property('preview_image').get_visibility() == unreal.SlateVisibility.HIT_TEST_INVISIBLE
            STATE['widget'] = widgets[0]
            advance('choose')
        elif stage == 'choose':
            _, outfit = STEPS[STATE['index']]
            action = {0: 'DefaultOutfitClicked', 1: 'PinkDressClicked', 2: 'YellowOverallsClicked'}[outfit]
            portrait = custom.get_preview_actor().get_preview_mesh()
            position = portrait.get_position()
            STATE['widget'].call_method(action, ())
            assert abs(portrait.get_position() - position) < .05
            advance('inspect')
        elif stage == 'inspect' and elapsed > 1.25:
            name, _ = STEPS[STATE['index']]
            check_equipped(world, custom, mesh, name, capture=True)
            STATE['checks'].append(name + '_updates_player_and_preview_without_restarting_playback')
            custom.choose_outfit(255)
            check_equipped(world, custom, mesh, name)
            if STATE['index'] == 1:
                custom.close_customization()
                advance('reopen')
            else:
                STATE['index'] += 1
                if STATE['index'] == len(STEPS):
                    custom.close_customization()
                    advance('close')
                else:
                    advance('choose')
        elif stage == 'reopen' and elapsed > .55:
            assert not custom.is_customization_open()
            pawn.request_interaction()
            assert custom.is_server_session_active()
            advance('check_reopen')
        elif stage == 'check_reopen' and custom.is_preview_ready():
            assert mesh_asset(custom.get_preview_actor().get_preview_mesh()).get_name() == STEPS[1][0]
            STATE['checks'].append('equipped_outfit_survives_closing_and_reopening')
            widgets = unreal.WidgetLibrary.get_all_widgets_of_class(world, unreal.TownAgeCustomizationWidget, True)
            assert len(widgets) == 1
            STATE['widget'] = widgets[0]
            STATE['index'] += 1
            advance('choose')
        elif stage == 'close' and elapsed > .6:
            assert not custom.is_customization_open()
            custom.choose_outfit(1)
            assert mesh_asset(mesh).get_name() == STEPS[-1][0]
            assert pawn.get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('movement_mode') == unreal.MovementMode.MOVE_WALKING
            STATE['checks'].append('invalid_outfit_and_closed_session_rejected_movement_restored')
            if NETWORK:
                STATE['checks'].append('host_outfits_replicate_to_nearby_client_without_opening_client_preview')
            finish()
    except Exception:
        finish(traceback.format_exc())


assert LEVELS.load_level('/Game/Maps/L_VillageTerrain_01')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
HANDLE = unreal.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
