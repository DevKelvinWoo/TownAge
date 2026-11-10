"""Standalone cosmetic integration; run after verify_customization.py finishes."""
import json
import gc
import types
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Customization/Makeup'
OUT.mkdir(parents=True, exist_ok=True)
STATE = {'phase': 0, 'since': None, 'start': None, 'checks': []}
CATEGORY = unreal.TownAgeCosmeticCategory
FIELDS = ['blush_amount', 'liner_amount', 'iris_amount', 'aegyo_amount', 'jaw_amount', 'nose_amount']
PARAMS = ['BlushAmount', 'LinerAmount', 'IrisAmount', 'AegyoAmount', 'JawAmount', 'NoseAmount']


def advance(phase, now):
    STATE['phase'], STATE['since'] = phase, now


def finish(error=None):
    (OUT / 'runtime_report.json').write_text(json.dumps({'passed': error is None,
        'error': error, 'checks': STATE['checks'], 'physical_mobile_verified': False}, indent=2), encoding='utf8')
    unreal.unregister_slate_post_tick_callback(HANDLE)


def station_target(world):
    vanity = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                  if a.get_actor_label() == 'GrayRoom_Vanity')
    return vanity.get_component_by_class(unreal.TownAgeInteractionTargetComponent)


def tick(delta):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        custom = pawn.get_customization_component()
        now = unreal.GameplayStatics.get_time_seconds(world)
        if STATE['start'] is None:
            STATE['start'] = STATE['since'] = now
        assert now - STATE['start'] < 60, 'Makeup test timed out'
        phase, elapsed = STATE['phase'], now - STATE['since']
        if phase == 0 and custom.is_preview_ready():
            STATE['hair'] = custom.get_hair_color_index()
            custom.set_category(CATEGORY.SURGERY)
            advance(1, now)
        elif phase == 1 and elapsed > .5:
            assert custom.get_category() == CATEGORY.SURGERY
            assert custom.get_preview_actor().is_face_view()
            custom.set_category(CATEGORY.MAKEUP)
            assert custom.can_apply_makeup()
            state = unreal.TownAgeMakeupState(blush_color=0, blush_amount=30, liner_amount=25,
                iris_color=1, iris_amount=35, aegyo_amount=30, jaw_amount=20, nose_amount=20)
            custom.choose_makeup(state)
            STATE['natural'] = state
            advance(2, now)
        elif phase == 2 and elapsed > .6:
            preview = custom.get_preview_actor()
            live = pawn.get_editor_property('mesh').get_material(0)
            shown = preview.get_preview_mesh().get_material(0)
            assert live != shown
            assert preview.is_face_view()
            for field, parameter in zip(FIELDS, PARAMS):
                expected = getattr(STATE['natural'], field) / 100.
                assert abs(live.get_scalar_parameter_value(parameter) - expected) < .001, parameter
                assert abs(shown.get_scalar_parameter_value(parameter) - expected) < .001, parameter
            assert custom.get_hair_color_index() == STATE['hair']
            assert live.get_vector_parameter_value('HairTint') == shown.get_vector_parameter_value('HairTint')
            unreal.RenderingLibrary.export_render_target(world, preview.get_render_target(), str(OUT), 'UE_Natural.png')
            STATE['checks'].extend(['categories_drive_face_camera', 'six_makeup_parameters_live_and_preview', 'hair_preserved_independent_materials'])
            invalid = custom.get_makeup_state()
            invalid.nose_amount = 255
            custom.choose_makeup(invalid)
            assert custom.get_makeup_state().nose_amount == 20
            custom.close_customization()
            advance(3, now)
        elif phase == 3 and elapsed > .6:
            pawn.request_interaction()
            advance(4, now)
        elif phase == 4 and custom.is_preview_ready():
            assert custom.get_makeup_state().nose_amount == 20
            custom.set_category(CATEGORY.MAKEUP)
            custom.choose_makeup(unreal.TownAgeMakeupState())
            advance(5, now)
        elif phase == 5 and elapsed > .6:
            assert all(getattr(custom.get_makeup_state(), field) == 0 for field in FIELDS)
            live = pawn.get_editor_property('mesh').get_material(0)
            assert all(abs(live.get_scalar_parameter_value(parameter)) < .001 for parameter in PARAMS)
            unreal.RenderingLibrary.export_render_target(world, custom.get_preview_actor().get_render_target(), str(OUT), 'UE_Original.png')
            STATE['checks'].extend(['makeup_survives_close_reopen', 'invalid_amount_rejected', 'remove_makeup_restores_zero_layers'])
            custom.close_customization()
            STATE['mask'] = station_target(world).get_editor_property('allowed_cosmetic_categories')
            station_target(world).set_editor_property('allowed_cosmetic_categories', 4)
            advance(6, now)
        elif phase == 6 and elapsed > .5:
            pawn.request_interaction()
            advance(7, now)
        elif phase == 7 and custom.is_preview_ready():
            assert custom.get_category() == CATEGORY.MAKEUP
            custom.set_category(CATEGORY.DYE)
            assert custom.get_category() == CATEGORY.MAKEUP
            custom.choose_hair_color(4)
            assert custom.get_hair_color_index() == STATE['hair']
            custom.choose_makeup(STATE['natural'])
            STATE['checks'].append('makeup_only_station_reuses_module_and_rejects_dye')
            custom.close_customization()
            station_target(world).set_editor_property('allowed_cosmetic_categories', STATE['mask'])
            advance(8, now)
        elif phase == 8 and elapsed > .5:
            pawn.request_interaction()
            advance(9, now)
        elif phase == 9 and custom.is_preview_ready():
            custom.set_category(CATEGORY.MAKEUP)
            finish()
            print('MAKEUP_RUNTIME_PASSED')
    except Exception:
        error = traceback.format_exc()
        if 'mask' in STATE:
            try:
                station_target(world).set_editor_property('allowed_cosmetic_categories', STATE['mask'])
            except Exception:
                error += '\nStation cleanup: ' + traceback.format_exc()
        finish(error)
        raise


for callback in gc.get_objects():
    if isinstance(callback, types.FunctionType) and callback is not tick and callback.__name__ == 'tick' \
            and callback.__code__.co_filename.replace('\\', '/').endswith('/Tools/Customization/verify_makeup.py'):
        previous = callback.__globals__.get('HANDLE')
        if previous is not None:
            try:
                unreal.unregister_slate_post_tick_callback(previous)
            except Exception:
                pass
HANDLE = unreal.register_slate_post_tick_callback(tick)
