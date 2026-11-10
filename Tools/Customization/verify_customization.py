"""Standalone integration check; register before starting PIE in the village."""
import json
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Customization'
OUT.mkdir(parents=True, exist_ok=True)
STATE = {'stage': 0, 'since': None, 'start': None, 'checks': [], 'colors': [], 'heads': []}


def advance(stage, now):
    STATE['stage'], STATE['since'] = stage, now


def finish(error=None):
    (OUT / 'runtime_report.json').write_text(json.dumps({
        'passed': error is None, 'error': error, 'checks': STATE['checks'],
        'colors': STATE['colors'], 'physical_mobile_verified': False}, indent=2), encoding='utf8')
    unreal.unregister_slate_post_tick_callback(HANDLE)


def tick(delta):
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
        assert now - STATE['start'] < 55, 'Customization test timeout at ' + str(STATE['stage'])
        elapsed = now - STATE['since']
        custom = pawn.get_customization_component()
        stage = STATE['stage']
        if stage == 0 and elapsed > 1:
            pawn.set_actor_location(unreal.Vector(2920, -865, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            pawn.request_interaction()
            assert pawn.is_door_busy()
            advance(1, now)
        elif stage == 1 and pawn.get_actor_location().x > 40000 and not pawn.is_door_busy():
            vanity = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                          if a.get_actor_label() == 'GrayRoom_Vanity')
            STATE['vanity'] = vanity
            pawn.set_actor_location(vanity.get_actor_location() + unreal.Vector(0, 130, 90.15), False, True)
            pawn.set_actor_rotation(unreal.Rotator(pitch=0, yaw=-90, roll=0), True)
            advance(2, now)
        elif stage == 2 and elapsed > .4:
            pawn.request_interaction()
            assert custom.is_server_session_active()
            assert custom.is_customization_open()
            widgets = unreal.WidgetLibrary.get_all_widgets_of_class(world, unreal.TownAgeCustomizationWidget, True)
            assert len(widgets) == 1
            widget = widgets[0]
            assert widget.get_editor_property('preview_image').get_visibility() == unreal.SlateVisibility.HIDDEN
            assert widget.get_editor_property('loading_panel').get_visibility() == unreal.SlateVisibility.HIT_TEST_INVISIBLE
            assert all(not chip.get_is_enabled() for chip in widget.get_editor_property('chips'))
            STATE['widget'] = widget
            STATE['checks'].append('loading_overlay_hides_uninitialized_preview_and_disables_chips')
            STATE['origin'] = pawn.get_actor_location()
            STATE['checks'].append('vanity_authority_opens_customization')
            advance(3, now)
        elif stage == 3:
            preview = custom.get_preview_actor()
            if not preview or not custom.is_preview_ready():
                return
            if 'idle_since' not in STATE:
                STATE['idle_since'] = now
            widget = STATE['widget']
            assert widget.get_editor_property('preview_image').get_visibility() == unreal.SlateVisibility.HIT_TEST_INVISIBLE
            assert widget.get_editor_property('loading_panel').get_visibility() == unreal.SlateVisibility.COLLAPSED
            assert all(chip.get_is_enabled() for chip in widget.get_editor_property('chips'))
            mesh = preview.get_preview_mesh()
            capture = preview.get_component_by_class(unreal.SceneCaptureComponent2D)
            flags = {str(flag.show_flag_name): flag.enabled for flag in capture.get_editor_property('show_flag_settings')}
            assert flags.get('TemporalAA') is False and flags.get('AntiAliasing') is False
            source_mesh = pawn.get_editor_property('mesh')
            assert mesh.get_editor_property('skeletal_mesh_asset') == source_mesh.get_editor_property('skeletal_mesh_asset')
            assert mesh.get_material(0) != source_mesh.get_material(0), 'Preview needs an independent material instance'
            assert preview.get_outer() != pawn.get_outer(), 'Preview must belong to separate loaded ULevel'
            assert not preview.get_editor_property('replicates')
            assert abs(preview.get_actor_location().x - 100000) < 1
            assert mesh.get_anim_instance().get_animation_asset().get_name() == 'A_TownKeeper_Meshy_Idle'
            STATE['heads'].append(str(mesh.get_socket_transform('Head', unreal.RelativeTransformSpace.RTS_COMPONENT).rotation))
            pawn.add_movement_input(unreal.Vector(1, 0, 0), 1, True)
            assert (pawn.get_actor_location() - STATE['origin']).length() < 2, 'UI must not move live pawn'
            if now - STATE['idle_since'] > 1.2:
                assert len(set(STATE['heads'])) > 1, 'Idle pose must animate'
                STATE['checks'].extend(['separate_local_preview_level', 'looping_idle_pose_changes', 'live_pawn_stays_interior_and_frozen'])
                STATE['full_distance'] = (preview.get_preview_camera_location() - preview.get_preview_view_target()).length()
                STATE['full_target_z'] = preview.get_preview_view_target().z
                custom.set_face_view(True)
                advance(30, now)
        elif stage == 30 and elapsed > .7:
            preview = custom.get_preview_actor()
            assert preview.is_face_view()
            distance = (preview.get_preview_camera_location() - preview.get_preview_view_target()).length()
            assert distance < STATE['full_distance'] * .65
            assert preview.get_preview_view_target().z > STATE['full_target_z'] + 10
            unreal.RenderingLibrary.export_render_target(world, preview.get_render_target(), str(OUT), 'preview_face.png')
            custom.set_face_view(False)
            advance(31, now)
        elif stage == 31 and elapsed > .7:
            preview = custom.get_preview_actor()
            assert not preview.is_face_view()
            distance = (preview.get_preview_camera_location() - preview.get_preview_view_target()).length()
            assert abs(distance - STATE['full_distance']) < 12
            STATE['checks'].extend(['owner_model_and_independent_material', 'face_zoom_and_full_body_restore'])
            custom.choose_hair_color(1)
            advance(4, now)
        elif 4 <= stage <= 7 and elapsed > .4:
            index = stage - 3
            assert custom.get_hair_color_index() == index
            preview = custom.get_preview_actor()
            live_material = pawn.get_editor_property('mesh').get_material(0)
            preview_material = preview.get_preview_mesh().get_material(0)
            assert isinstance(live_material, unreal.MaterialInstanceDynamic)
            assert isinstance(preview_material, unreal.MaterialInstanceDynamic)
            live_color = live_material.get_vector_parameter_value('HairTint')
            preview_color = preview_material.get_vector_parameter_value('HairTint')
            assert live_color == preview_color, 'Preview and live character hair disagree'
            assert abs(live_material.get_scalar_parameter_value('DyeStrength') - 1) < .001
            unreal.RenderingLibrary.export_render_target(world, preview.get_render_target(), str(OUT), 'preview_' + str(index) + '.png')
            STATE['colors'].append({'index': index, 'live_and_preview_equal': True, 'tint': str(live_color)})
            if index < 4:
                custom.choose_hair_color(index + 1)
                advance(stage + 1, now)
            else:
                custom.choose_hair_color(255)
                assert custom.get_hair_color_index() == 4
                STATE['checks'].extend(['four_live_and_preview_material_tints', 'invalid_palette_rejected'])
                STATE.pop('widget', None)
                custom.close_customization()
                advance(8, now)
        elif stage == 8 and elapsed > .7:
            assert not custom.is_customization_open()
            assert not custom.is_server_session_active()
            assert custom.get_preview_actor() is None
            assert not unreal.GameplayStatics.get_all_actors_of_class(world, unreal.TownAgeCustomizationPreview)
            assert custom.get_hair_color_index() == 4
            assert pawn.get_editor_property('character_movement').is_moving_on_ground()
            unreal.SystemLibrary.collect_garbage()
            pawn.request_interaction()
            advance(9, now)
        elif stage == 9 and custom.is_preview_ready() and elapsed > .5:
            assert custom.get_hair_color_index() == 4
            custom.choose_hair_color(1)
            STATE['checks'].extend(['close_unloads_preview_restores_movement', 'selected_color_survives_close_gc_reopen'])
            advance(10, now)
        elif stage == 10 and elapsed > .5:
            assert custom.get_hair_color_index() == 1
            finish()
            print('CUSTOMIZATION_RUNTIME_PASSED')
    except Exception:
        finish(traceback.format_exc())
        raise


HANDLE = unreal.register_slate_post_tick_callback(tick)
