"""Run after standalone verification; exercise alternate owner mesh and fallback.

Requires create_owner_preview_fixture.py. All avatar swaps are PIE-only, and
the original live mesh/material/scale/animation are restored before completion.
"""
import json
import traceback
from pathlib import Path
import unreal

OUT = Path(__file__).resolve().parents[2] / 'Saved/Customization'
STATE = {'stage': 0, 'since': None, 'start': None, 'checks': []}


def stage(value, now):
    STATE['stage'], STATE['since'] = value, now


def restore(mesh):
    mesh.set_skeletal_mesh_asset(STATE['mesh'])
    mesh.set_editor_property('relative_scale3d', STATE['scale'])
    mesh.set_material(0, STATE['material'])
    mesh.set_anim_instance_class(unreal.TownAgeDoorAnimInstance)
    mesh.get_anim_instance().set_animation_asset(STATE['animation'], True, 1.)


def finish(error=None):
    (OUT / 'owner_preview_report.json').write_text(json.dumps({'passed': error is None,
        'error': error, 'checks': STATE['checks'], 'fixture_uses_retained_approved_geometry': True}, indent=2), encoding='utf8')
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
        custom = pawn.get_customization_component()
        live = pawn.get_editor_property('mesh')
        now = unreal.GameplayStatics.get_time_seconds(world)
        if STATE['start'] is None:
            STATE['start'] = STATE['since'] = now
        assert now - STATE['start'] < 55, 'Owner preview test timeout'
        current, elapsed = STATE['stage'], now - STATE['since']
        if current == 0:
            STATE.update(mesh=live.get_editor_property('skeletal_mesh_asset'), scale=live.get_editor_property('relative_scale3d'),
                         material=live.get_material(0), animation=live.get_anim_instance().get_animation_asset())
            custom.close_customization()
            stage(1, now)
        elif current == 1 and elapsed > .5:
            variant = unreal.load_asset('/Game/Developers/CustomizationTests/SK_OwnerPreviewVariant')
            assert variant
            live.set_skeletal_mesh_asset(variant)
            live.set_editor_property('relative_scale3d', unreal.Vector(.85, .85, 1.12))
            material = live.create_dynamic_material_instance(0, unreal.load_asset('/Game/Characters/Customization/M_TownKeeper_HairDye'))
            material.set_vector_parameter_value('HairTint', STATE['material'].get_vector_parameter_value('HairTint'))
            material.set_scalar_parameter_value('DyeStrength', 1.)
            pawn.request_interaction()
            stage(2, now)
        elif current == 2 and custom.is_preview_ready():
            preview = custom.get_preview_actor()
            mesh = preview.get_preview_mesh()
            assert mesh.get_editor_property('skeletal_mesh_asset') == live.get_editor_property('skeletal_mesh_asset')
            assert mesh.get_editor_property('skeletal_mesh_asset') != STATE['mesh'], 'Hardcoded avatar was reused'
            assert (mesh.get_editor_property('relative_scale3d') - live.get_editor_property('relative_scale3d')).length() < .001
            assert mesh.get_material(0) != live.get_material(0)
            assert custom.can_dye_hair()
            custom.choose_hair_color(3)
            custom.set_face_view(True)
            stage(3, now)
        elif current == 3 and elapsed > .7:
            preview = custom.get_preview_actor()
            assert preview.is_face_view()
            assert custom.get_hair_color_index() == 3
            assert preview.get_preview_mesh().get_material(0).get_vector_parameter_value('HairTint') == live.get_material(0).get_vector_parameter_value('HairTint')
            unreal.RenderingLibrary.export_render_target(world, preview.get_render_target(), str(OUT), 'owner_variant_face.png')
            STATE['checks'].extend(['alternate_owner_mesh_asset_and_scale', 'independent_owner_materials', 'alternate_model_dye_and_face_zoom'])
            custom.close_customization()
            stage(4, now)
        elif current == 4 and elapsed > .5:
            cube = unreal.load_asset('/Engine/EngineMeshes/SkeletalCube')
            live.set_skeletal_mesh_asset(cube)
            live.set_editor_property('relative_scale3d', unreal.Vector(1, 1, 1))
            live.set_material(0, cube.get_editor_property('materials')[0].material_interface)
            live.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            STATE['cube_material'] = live.get_material(0)
            pawn.request_interaction()
            stage(5, now)
        elif current == 5 and custom.is_preview_ready():
            preview = custom.get_preview_actor()
            assert preview.get_preview_mesh().get_editor_property('skeletal_mesh_asset') == live.get_editor_property('skeletal_mesh_asset')
            assert not custom.can_dye_hair()
            custom.choose_hair_color(2)
            assert custom.get_hair_color_index() == 3
            assert live.get_material(0) == STATE['cube_material'], 'Unsupported model received foreign atlas'
            STATE['checks'].append('unrelated_skeleton_and_material_preserved_without_foreign_idle_or_atlas')
            custom.close_customization()
            stage(6, now)
        elif current == 6 and elapsed > .5:
            restore(live)
            pawn.request_interaction()
            stage(7, now)
        elif current == 7 and custom.is_preview_ready():
            assert custom.get_preview_actor().get_preview_mesh().get_editor_property('skeletal_mesh_asset') == STATE['mesh']
            assert not custom.get_preview_actor().is_face_view()
            custom.choose_hair_color(1)
            STATE['checks'].append('original_owner_model_and_full_body_restored')
            finish()
            print('OWNER_PREVIEW_RUNTIME_PASSED')
    except Exception:
        if 'mesh' in STATE:
            try:
                custom.close_customization()
                restore(live)
            except Exception:
                pass
        finish(traceback.format_exc())
        raise


HANDLE = unreal.register_slate_post_tick_callback(tick)
