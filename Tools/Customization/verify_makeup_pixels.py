"""Capture zero/100 makeup at one frozen pose, with runtime material evidence.

Run in a standalone open vanity session. Each run is timestamped for before/after
comparison. The original state and playing Idle are restored on completion.
"""
import datetime
import json
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Customization/Makeup/SliderAudit' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUT.mkdir(parents=True, exist_ok=True)
FIELDS = ['blush_amount', 'liner_amount', 'iris_amount', 'aegyo_amount', 'jaw_amount', 'nose_amount']
PARAMS = ['BlushAmount', 'LinerAmount', 'IrisAmount', 'AegyoAmount', 'JawAmount', 'NoseAmount']
CASES = [('zero_a', unreal.TownAgeMakeupState()), ('zero_b', unreal.TownAgeMakeupState())]
for field in FIELDS:
    state = unreal.TownAgeMakeupState(blush_color=2, iris_color=3)
    setattr(state, field, 100)
    CASES.append((field + '_100', state))
CASES.append(('all_100', unreal.TownAgeMakeupState(blush_color=2, blush_amount=100, liner_amount=100,
    iris_color=3, iris_amount=100, aegyo_amount=100, jaw_amount=100, nose_amount=100)))
CASES.extend([('held_original', CASES[-1][1]), ('held_released', CASES[-1][1])])
STATE = {'index': -1, 'since': None, 'checks': []}


def tick(delta):
    try:
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:
            return
        world = worlds[0]
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        custom = pawn.get_customization_component()
        if not custom.is_preview_ready():
            return
        preview = custom.get_preview_actor()
        mesh = preview.get_preview_mesh()
        now = unreal.GameplayStatics.get_time_seconds(world)
        if STATE['since'] is None:
            STATE['original'] = custom.get_makeup_state()
            custom.set_category(unreal.TownAgeCosmeticCategory.MAKEUP)
            mesh.get_anim_instance().set_playing(False)
            STATE['since'] = now
            return
        if now - STATE['since'] < (1.5 if STATE['index'] < 0 else .65):
            return
        if STATE['index'] >= 0:
            label, expected = CASES[STATE['index']]
            live = pawn.get_editor_property('mesh').get_material(0)
            shown = mesh.get_material(0)
            values = {}
            for field, parameter in zip(FIELDS, PARAMS):
                value = getattr(expected, field) / 100.
                assert abs(live.get_scalar_parameter_value(parameter) - value) < .001
                shown_value = 0. if label == 'held_original' else value
                assert abs(shown.get_scalar_parameter_value(parameter) - shown_value) < .001
                values[parameter] = value
                assert getattr(custom.get_makeup_state(), field) == getattr(expected, field)
            assert custom.is_original_makeup_preview() == (label == 'held_original')
            unreal.RenderingLibrary.export_render_target(world, preview.get_render_target(), str(OUT), label + '.png')
            STATE['checks'].append({'capture': label, 'live_and_preview_parameters': values})
        STATE['index'] += 1
        if STATE['index'] == len(CASES):
            custom.preview_original_makeup(True)
            custom.set_category(unreal.TownAgeCosmeticCategory.DYE)
            assert not custom.is_original_makeup_preview()
            custom.set_category(unreal.TownAgeCosmeticCategory.MAKEUP)
            custom.choose_makeup(STATE['original'])
            mesh.get_anim_instance().set_playing(True)
            (OUT / 'runtime.json').write_text(json.dumps({'passed': True, 'frozen_pose': True,
                'cases': STATE['checks']}, indent=2), encoding='utf8')
            (OUT.parent / 'latest.txt').write_text(str(OUT), encoding='utf8')
            unreal.unregister_slate_post_tick_callback(HANDLE)
            print('MAKEUP_PIXEL_AUDIT_READY', str(OUT))
        else:
            label, value = CASES[STATE['index']]
            if label == 'held_original':
                custom.preview_original_makeup(True)
            elif label == 'held_released':
                custom.preview_original_makeup(False)
            else:
                custom.choose_makeup(value)
            STATE['since'] = now
    except Exception:
        (OUT / 'runtime.json').write_text(json.dumps({'passed': False, 'error': traceback.format_exc()}), encoding='utf8')
        try:
            custom.preview_original_makeup(False)
            custom.choose_makeup(STATE['original'])
            mesh.get_anim_instance().set_playing(True)
        except Exception:
            pass
        unreal.unregister_slate_post_tick_callback(HANDLE)
        raise


HANDLE = unreal.register_slate_post_tick_callback(tick)
