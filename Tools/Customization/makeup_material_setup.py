"""Create a separate makeup-capable parent; keep original mesh/material intact."""
import datetime
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/Customization/Makeup'
FOLDER = '/Game/Characters/Customization'
SOURCE = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001'
BACKUP = OUT / datetime.datetime.now().strftime('backup_%Y%m%d_%H%M%S')
BACKUP.mkdir(parents=True, exist_ok=True)
for name in ['M_TownKeeper_Makeup','T_MakeupMaskA','T_MakeupMaskB']:
    path=ROOT/('Content/Characters/Customization/'+name+'.uasset')
    if path.exists():
        shutil.copy2(path,BACKUP/path.name)
tools=unreal.AssetToolsHelpers.get_asset_tools()
textures=[]
for name in ['T_MakeupMaskA','T_MakeupMaskB']:
    source=OUT/(name+'.png')
    assert source.is_file(), 'Run makeup_masks.py first'
    task=unreal.AssetImportTask()
    task.filename=str(source);task.destination_path=FOLDER;task.destination_name=name
    task.replace_existing=task.automated=task.save=True
    tools.import_asset_tasks([task])
    texture=unreal.load_asset(FOLDER+'/'+name)
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('never_stream',True)
    texture.set_editor_property('max_texture_size',2048)
    assert unreal.EditorAssetLibrary.save_loaded_asset(texture,False)
    textures.append(texture)
material=unreal.load_asset(FOLDER+'/M_TownKeeper_Makeup')
if material is None:
    material=tools.create_asset('M_TownKeeper_Makeup',FOLDER,unreal.Material,unreal.MaterialFactoryNew())
assert isinstance(material,unreal.Material)
edit=unreal.MaterialEditingLibrary
edit.delete_all_material_expressions(material)
material.set_editor_property('used_with_skeletal_mesh',True)
material.set_editor_property('two_sided',False)


def node(cls):
    return edit.create_material_expression(material,cls)


def link(source,output,destination,input_name):
    assert edit.connect_material_expressions(source,output,destination,input_name), input_name


def scalar(value):
    result=node(unreal.MaterialExpressionConstant);result.r=value
    return result


def color(value):
    result=node(unreal.MaterialExpressionConstant3Vector)
    result.constant=unreal.LinearColor(*value,1)
    return result


def parameter(name,value):
    result=node(unreal.MaterialExpressionScalarParameter)
    result.set_editor_property('parameter_name',name)
    result.set_editor_property('default_value',value)
    return result


def tint(name,value):
    result=node(unreal.MaterialExpressionVectorParameter)
    result.set_editor_property('parameter_name',name)
    result.set_editor_property('default_value',unreal.LinearColor(*value,1))
    return result


def sample(texture,sampler):
    result=node(unreal.MaterialExpressionTextureSample)
    result.texture=texture;result.sampler_type=sampler
    return result


def multiply(a,b,a_output='',b_output=''):
    result=node(unreal.MaterialExpressionMultiply)
    link(a,a_output,result,'A');link(b,b_output,result,'B')
    return result


def add(a,b):
    result=node(unreal.MaterialExpressionAdd)
    link(a,'',result,'A');link(b,'',result,'B')
    return result


def blend(a,b,alpha,a_output='',b_output=''):
    result=node(unreal.MaterialExpressionLinearInterpolate)
    link(a,a_output,result,'A');link(b,b_output,result,'B');link(alpha,'',result,'Alpha')
    return result


base=sample(unreal.load_asset(SOURCE+'/T_TownKeeper_Meshy_basecolor'),unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
normal=sample(unreal.load_asset(SOURCE+'/T_TownKeeper_Meshy_normal'),unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
rough=sample(unreal.load_asset(SOURCE+'/T_TownKeeper_Meshy_roughness'),unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
hair=sample(unreal.load_asset(FOLDER+'/T_HairDyeMask'),unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
mask_a=sample(textures[0],unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
mask_b=sample(textures[1],unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
luma=node(unreal.MaterialExpressionDotProduct)
link(base,'RGB',luma,'A');link(color((.299,.587,.114)),'',luma,'B')
hair_light=node(unreal.MaterialExpressionClamp)
link(add(multiply(luma,scalar(1.8)),scalar(.25)),'',hair_light,'')
hair_color=multiply(hair_light,tint('HairTint',(1,1,1)),b_output='RGB')
hair_alpha=multiply(hair,parameter('DyeStrength',0.),a_output='R')
result=blend(base,hair_color,hair_alpha,a_output='RGB')


def overlay(previous,mask,channel,amount_name,scale,target,target_output=''):
    alpha=multiply(multiply(mask,parameter(amount_name,0.),a_output=channel),scalar(scale))
    return blend(previous,target,alpha,b_output=target_output)


result=overlay(result,mask_a,'R','BlushAmount',.32,tint('BlushTint',(.70,.24,.31)),'RGB')
result=overlay(result,mask_a,'G','LinerAmount',.65,color((.008,.004,.003)))
iris_light=node(unreal.MaterialExpressionClamp)
iris_light.set_editor_property('min_default',.2)
iris_light.set_editor_property('max_default',.85)
link(add(multiply(luma,scalar(2.8)),scalar(.18)),'',iris_light,'')
iris_color=multiply(iris_light,tint('IrisTint',(.30,.19,.065)),b_output='RGB')
result=overlay(result,mask_a,'B','IrisAmount',.85,iris_color)
result=overlay(result,mask_a,'A','AegyoAmount',.18,color((.93,.78,.60)))
result=overlay(result,mask_b,'R','AegyoAmount',.08,color((.33,.23,.20)))
result=overlay(result,mask_b,'G','JawAmount',.20,color((.34,.25,.22)))
result=overlay(result,mask_b,'B','NoseAmount',.18,color((.34,.25,.22)))
assert edit.connect_material_property(result,'',unreal.MaterialProperty.MP_BASE_COLOR)
assert edit.connect_material_property(normal,'RGB',unreal.MaterialProperty.MP_NORMAL)
assert edit.connect_material_property(rough,'R',unreal.MaterialProperty.MP_ROUGHNESS)
edit.layout_material_expressions(material)
edit.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
report={'material':material.get_path_name(),'textures':[t.get_path_name() for t in textures],
        'source_mesh_modified':False,'source_material_modified':False,'backup':str(BACKUP),
        'parameters':['HairTint','DyeStrength','BlushTint','BlushAmount','LinerAmount','IrisTint',
                      'IrisAmount','AegyoAmount','JawAmount','NoseAmount'],
        'mask_channels':{'A':['blush','upper_liner','iris','aegyo_highlight'],
                         'B':['aegyo_shadow','jaw','nose','skin']}}
(OUT/'material_setup_report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('MAKEUP_MATERIAL_READY',json.dumps(report))
