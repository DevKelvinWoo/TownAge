"""Run with UnrealEditor-Cmd -run=pythonscript; imports approved in-place clips only."""
import unreal, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'ArtSource/Characters/Main/Animations/WalkFinal01'
DEST='/Game/Characters/Main/TownKeeper/Animations'
MODEL='/Game/Characters/Main/TownKeeper/ReferenceRevision04/SK_TownKeeper_Reference'
mesh=unreal.load_asset(MODEL)
assert mesh
skeleton=mesh.get_editor_property('skeleton')
manifest=json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))
tools=unreal.AssetToolsHelpers.get_asset_tools()
unreal.EditorAssetLibrary.make_directory(DEST)
clips={}
for label in ('Standing','Walk'):
    name='A_TownKeeper_'+label
    options=unreal.FbxImportUI()
    options.set_editor_property('skeleton',skeleton)
    options.set_editor_property('import_mesh',False)
    options.set_editor_property('import_as_skeletal',True)
    options.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_ANIMATION)
    options.set_editor_property('import_animations',True)
    options.set_editor_property('import_materials',False)
    options.set_editor_property('import_textures',False)
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',True)
    task=unreal.AssetImportTask()
    task.filename=str(SOURCE/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.factory=unreal.FbxFactory();task.options=options;task.automated=True;task.replace_existing=True;task.save=True
    tools.import_asset_tasks([task])
    clips[label]=unreal.load_asset(DEST+'/'+name)
    assert isinstance(clips[label],unreal.AnimSequence), list(task.imported_object_paths)
    assert clips[label].get_editor_property('skeleton')==skeleton
    clips[label].set_editor_property('enable_root_motion',False)
    unreal.EditorAssetLibrary.save_loaded_asset(clips[label])

name='BS_TownKeeper_Walk'
blend=unreal.load_asset(DEST+'/'+name)
if not blend:
    factory=unreal.BlendSpaceFactory1D();factory.set_editor_property('target_skeleton',skeleton)
    blend=tools.create_asset(name,DEST,unreal.BlendSpace1D,factory)
assert blend
params=blend.get_editor_property('blend_parameters')
axis=params[0];axis.set_editor_property('display_name','Speed');axis.set_editor_property('min',0.0);axis.set_editor_property('max',70.0);params[0]=axis
blend.set_editor_property('blend_parameters',params)
samples=[]
for label,speed in [('Standing',0.0),('Walk',manifest['walk_speed_cm_s'])]:
    sample=unreal.BlendSample()
    sample.set_editor_property('animation',clips[label]);sample.set_editor_property('sample_value',unreal.Vector(speed,0,0));sample.set_editor_property('rate_scale',1.0)
    samples.append(sample)
blend.set_editor_property('sample_data',samples)
assert unreal.TownAgePlayer.rebuild_walk_blend_space(blend)
idle_weights=unreal.TownAgePlayer.get_walk_blend_weights(blend,0.0)
walk_weights=unreal.TownAgePlayer.get_walk_blend_weights(blend,float(manifest['walk_speed_cm_s']))
assert idle_weights.x>.99 and walk_weights.y>.99,(idle_weights,walk_weights)
unreal.EditorAssetLibrary.save_loaded_asset(blend)
report={'skeleton':skeleton.get_path_name(),'clips':{k:{'path':v.get_path_name(),'length_seconds':v.get_play_length()} for k,v in clips.items()},'blend_space':blend.get_path_name(),'sample_count':len(blend.get_editor_property('sample_data')),'walk_speed_cm_s':manifest['walk_speed_cm_s'],'root_motion':False,'idle_weights':[idle_weights.x,idle_weights.y],'walk_weights':[walk_weights.x,walk_weights.y]}
(ROOT/'Saved/walk_import_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALK_IMPORT_COMPLETE',json.dumps(report))
