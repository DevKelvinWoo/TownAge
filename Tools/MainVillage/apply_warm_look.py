"""Apply an isolated matte, softly graded look to the art village only."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/MainVillage/WarmLook'
MAP = '/Game/Maps/L_MainVillage_Art_01'
FOLDER = '/Game/Environment/MainVillage/Look/WarmIllustrated_v001'
A = unreal.EditorAssetLibrary
E = unreal.MaterialEditingLibrary
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT.mkdir(parents=True, exist_ok=True)
backup = OUT / datetime.now().strftime('backup_%Y%m%d_%H%M%S')
backup.mkdir()
shutil.copy2(ROOT / 'Content/Maps/L_MainVillage_Art_01.umap', backup)
assert LEVELS.load_level(MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
materials = {}


def scalar(mat, value):
    node = E.create_material_expression(mat, unreal.MaterialExpressionConstant)
    node.r = value
    return node


def color(mat, values):
    node = E.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector)
    node.constant = unreal.LinearColor(*values, 1)
    return node


def wire(source, target, slot, output=''):
    assert E.connect_material_expressions(source, output, target, slot)


def matte(source):
    if not source or not isinstance(source, unreal.Material):
        return source
    path = source.get_path_name()
    if path.startswith(FOLDER):
        return source
    if path in materials:
        return materials[path]
    name = source.get_name() + '_' + hashlib.sha1(path.encode()).hexdigest()[:6]
    dest = FOLDER + '/' + name
    mat = A.load_asset(dest) if A.does_asset_exist(dest) else A.duplicate_asset(path, dest)
    assert mat
    # A previously authored variant is reused without multiplying correction nodes.
    if A.get_metadata_tag(mat, 'TownAgeWarmLook') != '1':
        original = E.get_material_property_input_node(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        output = E.get_material_property_input_node_output_name(mat, unreal.MaterialProperty.MP_BASE_COLOR)
        if original:
            power = E.create_material_expression(mat, unreal.MaterialExpressionPower)
            power.set_editor_property('const_exponent', .72)
            wire(original, power, 'Base', output)
            desat = E.create_material_expression(mat, unreal.MaterialExpressionDesaturation)
            wire(power, desat, '')
            wire(scalar(mat, .12), desat, 'Fraction')
            tint = E.create_material_expression(mat, unreal.MaterialExpressionMultiply)
            wire(desat, tint, 'A')
            wire(color(mat, (1.04, 1.015, .94)), tint, 'B')
            assert E.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
            fill = E.create_material_expression(mat, unreal.MaterialExpressionMultiply)
            wire(tint, fill, 'A')
            wire(scalar(mat, .08), fill, 'B')
            assert E.connect_material_property(fill, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        for prop, value in [(unreal.MaterialProperty.MP_METALLIC, 0),
                            (unreal.MaterialProperty.MP_ROUGHNESS, .88),
                            (unreal.MaterialProperty.MP_SPECULAR, .15),
                            (unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 1)]:
            assert E.connect_material_property(scalar(mat, value), '', prop)
        A.set_metadata_tag(mat, 'TownAgeWarmLook', '1')
        E.recompile_material(mat)
        assert A.save_loaded_asset(mat, False)
    materials[path] = mat
    return mat


actors = ACTORS.get_all_level_actors()
assignments = []
for actor in actors:
    # The streamed interior is far away and retains its original presentation.
    if abs(actor.get_actor_location().x) > 20000 or abs(actor.get_actor_location().y) > 20000:
        continue
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        for slot in range(component.get_num_materials()):
            source = component.get_material(slot)
            if not source or not source.get_path_name().startswith('/Game/'):
                continue
            variant = matte(source)
            component.set_material(slot, variant)
            assignments.append({'actor': actor.get_actor_label(), 'slot': slot, 'material': variant.get_path_name()})
    if isinstance(actor, unreal.Landscape):
        # Remove the coarse alternating grass color blocks: a calm, nearly flat
        # sage ground lets flowers and silhouettes carry the detail.
        path = FOLDER + '/M_SoftGrass'
        grass = A.load_asset(path) if A.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_SoftGrass', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        if A.get_metadata_tag(grass, 'TownAgeWarmLook') != '1':
            base = color(grass, (.26, .38, .115))
            E.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
            E.connect_material_property(scalar(grass, .95), '', unreal.MaterialProperty.MP_ROUGHNESS)
            E.connect_material_property(color(grass, (.0208, .0304, .0092)), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            A.set_metadata_tag(grass, 'TownAgeWarmLook', '1')
            E.recompile_material(grass)
            assert A.save_loaded_asset(grass, False)
        actor.set_editor_property('landscape_material', grass)
    if isinstance(actor, unreal.DirectionalLight):
        light = actor.get_editor_property('light_component')
        light.set_intensity(8.)
        light.set_light_color(unreal.LinearColor(1., .94, .80, 1.))
        light.set_editor_property('light_source_angle', 6.)
        light.set_editor_property('light_source_soft_angle', 2.)
        light.set_editor_property('shadow_amount', .38)
        actor.set_actor_rotation(unreal.Rotator(pitch=-52, yaw=-55, roll=0), True)
    if isinstance(actor, unreal.SkyLight):
        light = actor.get_editor_property('light_component')
        light.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        light.set_editor_property('cubemap', A.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
        light.set_intensity(3.)
        light.set_light_color(unreal.LinearColor(1., .97, .90, 1.))

# Preserve the material remap if the layout's own editor regeneration is invoked.
for actor in actors:
    if isinstance(actor, unreal.TownAgeMapLayout):
        layout = json.loads(unreal.TownAgeMapEditorLibrary.export_json(actor))
        for item in layout['types']:
            source = A.load_asset(item['material']) if item.get('material') not in ('None', '', None) else None
            if source:
                item['material'] = matte(source).get_path_name()
        unreal.TownAgeMapEditorLibrary.import_json(actor, json.dumps(layout))

volume = next((a for a in actors if a.get_actor_label() == 'Village_WarmIllustratedGrade'), None)
volume = volume or ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
volume.set_actor_label('Village_WarmIllustratedGrade')
volume.set_folder_path('MainVillage/Look')
volume.set_editor_property('unbound', True)
volume.set_editor_property('priority', .5)
settings = volume.get_editor_property('settings')
values = {
    'color_saturation': unreal.Vector4(1.12, 1.12, 1.12, 1.),
    'color_contrast': unreal.Vector4(1.02, 1.02, 1.02, 1.),
    'color_gamma': unreal.Vector4(1., 1., 1., 1.),
    'color_gain': unreal.Vector4(1.035, 1.015, .97, 1.),
    'film_slope': .88, 'film_toe': .55, 'film_shoulder': .26,
    'ambient_occlusion_intensity': .15, 'bloom_intensity': .12,
    'vignette_intensity': .05, 'scene_fringe_intensity': 0., 'motion_blur_amount': 0.,
    'auto_exposure_bias': 1.1,
}
for key, value in values.items():
    settings.set_editor_property('override_' + key, True)
    settings.set_editor_property(key, value)
volume.set_editor_property('settings', settings)
assert LEVELS.save_current_level()
(OUT / 'applied.json').write_text(json.dumps({'map': MAP, 'backup': str(backup),
    'materials': {key: value.get_path_name() for key, value in materials.items()},
    'assignments': assignments, 'look_folder': FOLDER,
    'note': 'No source textures or mesh geometry were changed; scene component material overrides are local to this level.'}, indent=2), encoding='utf-8')
print('WARM_ILLUSTRATED_LOOK_APPLIED', len(assignments))
