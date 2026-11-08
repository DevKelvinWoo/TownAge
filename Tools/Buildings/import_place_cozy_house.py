"""Import the reviewed split house and add one instance near the existing start."""
import unreal,json,shutil,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'ArtSource/Meshy/CozyHouse01/candidate_v002'
OUT=ROOT/'Saved/Meshy/CozyHouse01'
FOLDER='/Game/Characters/Meshy/CozyHouse01/candidate_v002'
MAP='/Game/Maps/L_VillageTerrain_01'
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert levels.load_level(MAP)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
existing=actors.get_all_level_actors()
starts=[a for a in existing if isinstance(a,unreal.PlayerStart)]
assert len(starts)==1
assert not any(a.get_actor_label()=='CozyHouse01_Review' for a in existing),'House already placed; inspect before retrying'
assert not unreal.EditorAssetLibrary.list_assets(FOLDER,True,False),'Candidate folder occupied'
backup=OUT/'backups/L_VillageTerrain_01-before-house.umap'
backup.parent.mkdir(exist_ok=True)
assert not backup.exists(),'Backup already exists; inspect the prior run before retrying'
shutil.copy2(ROOT/'Content/Maps/L_VillageTerrain_01.umap',backup)
unreal.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
tools=unreal.AssetToolsHelpers.get_asset_tools()
material=unreal.load_asset('/Game/Characters/Meshy/CozyHouse01/candidate_v001/M_CozyHouse01')
assert material
def import_mesh(name):
    options=unreal.FbxImportUI()
    options.automated_import_should_detect_type=False
    options.import_mesh=True;options.import_as_skeletal=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials=False;options.import_textures=False;options.import_animations=False
    options.static_mesh_import_data.combine_meshes=True
    options.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=unreal.AssetImportTask();task.filename=str(SOURCE/(name+'.fbx'))
    task.destination_path=FOLDER;task.destination_name='SM_CozyHouse01_'+name
    task.automated=True;task.replace_existing=False;task.save=True
    task.factory=unreal.FbxFactory();task.options=options
    tools.import_asset_tasks([task])
    mesh=unreal.load_asset(FOLDER+'/'+task.destination_name)
    assert isinstance(mesh,unreal.StaticMesh)
    assert len(mesh.get_editor_property('static_materials'))==1
    mesh.set_material(0,material)
    # Preserve the actual arched entrance rather than a single convex hull.
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh,False)
    return mesh
body=import_mesh('HouseBody');door=import_mesh('DoorLeaf')
meta=json.loads((SOURCE/'split_manifest.json').read_text())
local=meta['door_local_bounds_m'];expected=[(a+b)*50 for a,b in zip(local['min'],local['max'])]
actual=door.get_bounds().origin
signs=[1 if abs(getattr(actual,axis)-v)<abs(getattr(actual,axis)+v) else -1 for axis,v in zip('xyz',expected)]
assert signs[2]==1 and abs(door.get_bounds().box_extent.z*2-183.479)<.1
hinge=unreal.Vector(*[v*100*sign for v,sign in zip(meta['door_hinge_blender_m'],signs)])
factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
bp=tools.create_asset('BP_CozyHouse01_Split',FOLDER,unreal.Blueprint,factory)
subsystem=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
root=subsystem.k2_gather_subobject_data_for_blueprint(bp)[0]
lib=unreal.SubobjectDataBlueprintFunctionLibrary
def component(parent,cls,name):
    handle,error=subsystem.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=parent,new_class=cls,blueprint_context=bp))
    assert lib.is_handle_valid(handle),str(error)
    assert subsystem.rename_subobject(handle,unreal.Text(name))
    obj=lib.get_object_for_blueprint(lib.get_data(handle),bp)
    return handle,obj
body_handle,body_component=component(root,unreal.StaticMeshComponent,'HouseBody')
body_component.set_static_mesh(body)
body_component.set_mobility(unreal.ComponentMobility.STATIC)
body_component.set_editor_property('relative_location',unreal.Vector(0,0,0))
body_component.set_collision_profile_name('BlockAll')
hinge_handle,hinge_component=component(root,unreal.SceneComponent,'DoorHinge')
hinge_component.set_mobility(unreal.ComponentMobility.MOVABLE)
hinge_component.set_editor_property('relative_location',hinge)
door_handle,door_component=component(hinge_handle,unreal.StaticMeshComponent,'DoorLeaf')
door_component.set_static_mesh(door)
door_component.set_mobility(unreal.ComponentMobility.MOVABLE)
door_component.set_editor_property('relative_location',unreal.Vector(0,0,0))
door_component.set_collision_profile_name('BlockAll')
for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(handle),bp)
    if isinstance(obj,unreal.SceneComponent) and obj.get_name().removesuffix('_GEN_VARIABLE')=='DefaultSceneRoot':
        obj.set_mobility(unreal.ComponentMobility.STATIC)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
assert unreal.EditorAssetLibrary.save_directory(FOLDER,False,True)
start=starts[0].get_actor_location();x,y=start.x-100,start.y-580
hit=unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,5000),unreal.Vector(x,y,-1000),unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
assert hit
z=hit.to_dict()['location'].z
# Imported front normal is -Y times the FBX Y sign; face +Y toward the start.
yaw=0 if signs[1]==-1 else 180
cls=unreal.EditorAssetLibrary.load_blueprint_class(FOLDER+'/BP_CozyHouse01_Split')
house=actors.spawn_actor_from_class(cls,unreal.Vector(x,y,z-.8),unreal.Rotator(pitch=0,yaw=yaw,roll=0))
house.set_actor_label('CozyHouse01_Review')
assert levels.save_current_level()
all_after=actors.get_all_level_actors()
assert len(all_after)==len(existing)+1
assert len([a for a in all_after if isinstance(a,unreal.PlayerStart)])==1
origin,extent=house.get_actor_bounds(True)
assert abs(extent.z*2-430)<.2
report={'map':MAP,'actor':house.get_path_name(),'label':house.get_actor_label(),'location_cm':[x,y,z-.8],'yaw':yaw,'player_start_cm':[start.x,start.y,start.z],'horizontal_distance_from_start_cm':math.hypot(x-start.x,y-start.y),'ground_height_cm':z,'dimensions_cm':[extent.x*2,extent.y*2,extent.z*2],'blueprint':bp.get_path_name(),'body_mesh':body.get_path_name(),'door_mesh':door.get_path_name(),'door_hinge_cm':[hinge.x,hinge.y,hinge.z],'fbx_axis_signs':signs,'door_movable':True,'door_animation_created':False,'actor_count_before':len(existing),'actor_count_after':len(all_after),'level_backup':str(backup),'terrain_regenerated':False}
(OUT/'placement_report.json').write_text(json.dumps(report,indent=2))
print('SPLIT_HOUSE_PLACED',json.dumps(report))
