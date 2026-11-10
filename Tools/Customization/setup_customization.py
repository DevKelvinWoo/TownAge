"""Create the owned hair dye material and isolated local preview map in Unreal.

Run generate_hair_mask.py first. Does not reimport or modify the production mesh,
skeleton, original material, village, interior, or startup map settings.
"""
import datetime
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Customization'
OUT.mkdir(parents=True, exist_ok=True)
FOLDER = '/Game/Characters/Customization'
PREVIEW = '/Game/Maps/Customization/L_CharacterCustomizationPreview'
SOURCE = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001'
MASK_SOURCE = OUT / 'T_HairDyeMask.png'
assert MASK_SOURCE.is_file(), 'Run generate_hair_mask.py before Unreal setup'
BACKUP = OUT / datetime.datetime.now().strftime('backup_%Y%m%d_%H%M%S')
BACKUP.mkdir(exist_ok=True)
for relative in ['Content/Characters/Customization/M_TownKeeper_HairDye.uasset',
                 'Content/Characters/Customization/T_HairDyeMask.uasset',
                 'Content/Data/Interactions/DT_Interactions.uasset']:
    path = ROOT / relative
    if path.exists():
        shutil.copy2(path, BACKUP / path.name)

tools = unreal.AssetToolsHelpers.get_asset_tools()
task = unreal.AssetImportTask()
task.filename = str(MASK_SOURCE)
task.destination_path = FOLDER
task.destination_name = 'T_HairDyeMask'
task.replace_existing = task.automated = task.save = True
tools.import_asset_tasks([task])
mask = unreal.load_asset(FOLDER + '/T_HairDyeMask')
assert isinstance(mask, unreal.Texture2D)
mask.set_editor_property('srgb', False)
mask.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
mask.set_editor_property('max_texture_size', 2048)
# This semantic atlas mask must not average hair with adjacent face/limb islands
# in coarse independently streamed mips. One shared resident mask costs 2MiB BC1.
mask.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
mask.set_editor_property('never_stream', True)
assert unreal.EditorAssetLibrary.save_loaded_asset(mask, False)
material = unreal.load_asset(FOLDER + '/M_TownKeeper_HairDye')
if material is None:
    material = tools.create_asset('M_TownKeeper_HairDye', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
assert isinstance(material, unreal.Material)
edit = unreal.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_property('two_sided', False)
material.set_editor_property('used_with_skeletal_mesh', True)


def node(cls):
    return edit.create_material_expression(material, cls)


def connect(source, output, destination, input_name):
    assert edit.connect_material_expressions(source, output, destination, input_name), input_name


def scalar(value):
    result = node(unreal.MaterialExpressionConstant)
    result.r = value
    return result


def sample(texture, sampler):
    result = node(unreal.MaterialExpressionTextureSample)
    result.texture = texture
    result.sampler_type = sampler
    return result


base_texture = unreal.load_asset(SOURCE + '/T_TownKeeper_Meshy_basecolor')
normal_texture = unreal.load_asset(SOURCE + '/T_TownKeeper_Meshy_normal')
rough_texture = unreal.load_asset(SOURCE + '/T_TownKeeper_Meshy_roughness')
assert base_texture and normal_texture and rough_texture
base = sample(base_texture, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
normal = sample(normal_texture, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
roughness = sample(rough_texture, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
hair_mask = sample(mask, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)

# Preserve strand contrast while lifting the brown atlas enough for all four dyes.
luma_weights = node(unreal.MaterialExpressionConstant3Vector)
luma_weights.constant = unreal.LinearColor(.299, .587, .114, 1)
luma = node(unreal.MaterialExpressionDotProduct)
connect(base, 'RGB', luma, 'A')
connect(luma_weights, '', luma, 'B')
contrast = node(unreal.MaterialExpressionMultiply)
connect(luma, '', contrast, 'A')
connect(scalar(1.8), '', contrast, 'B')
lift = node(unreal.MaterialExpressionAdd)
connect(contrast, '', lift, 'A')
connect(scalar(.25), '', lift, 'B')
clamp = node(unreal.MaterialExpressionClamp)
connect(lift, '', clamp, '')
tint = node(unreal.MaterialExpressionVectorParameter)
tint.set_editor_property('parameter_name', 'HairTint')
tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
dyed = node(unreal.MaterialExpressionMultiply)
connect(clamp, '', dyed, 'A')
connect(tint, 'RGB', dyed, 'B')
strength = node(unreal.MaterialExpressionScalarParameter)
strength.set_editor_property('parameter_name', 'DyeStrength')
strength.set_editor_property('default_value', 0.)
alpha = node(unreal.MaterialExpressionMultiply)
connect(hair_mask, 'R', alpha, 'A')
connect(strength, '', alpha, 'B')
blend = node(unreal.MaterialExpressionLinearInterpolate)
connect(base, 'RGB', blend, 'A')
connect(dyed, '', blend, 'B')
connect(alpha, '', blend, 'Alpha')
assert edit.connect_material_property(blend, '', unreal.MaterialProperty.MP_BASE_COLOR)
assert edit.connect_material_property(normal, 'RGB', unreal.MaterialProperty.MP_NORMAL)
assert edit.connect_material_property(roughness, 'R', unreal.MaterialProperty.MP_ROUGHNESS)
edit.layout_material_expressions(material)
edit.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)

table = unreal.load_asset('/Game/Data/Interactions/DT_Interactions')
assert table
assert unreal.DataTableFunctionLibrary.fill_data_table_from_csv_file(table, str(ROOT / 'Tools/Interaction/Interactions.csv'))
assert unreal.EditorAssetLibrary.save_loaded_asset(table, False)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not unreal.EditorAssetLibrary.does_asset_exist(PREVIEW):
    assert levels.new_level(PREVIEW)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    marker = actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector())
    marker.set_actor_label('CustomizationPreview_Origin')
    assert levels.save_current_level()

report = {'preview_level': PREVIEW, 'client_only_streaming': True,
          'material': material.get_path_name(), 'mask': mask.get_path_name(),
          'production_mesh_reimported': False, 'original_material_changed': False,
          'material_slots': 1, 'extra_mask_max_resolution': 2048,
          'hair_parameters': ['HairTint', 'DyeStrength'], 'backup': str(BACKUP)}
(OUT / 'setup_report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print('CUSTOMIZATION_SETUP_COMPLETE', json.dumps(report))
