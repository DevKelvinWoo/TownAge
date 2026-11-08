import unreal,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Saved/Meshy/CozyHouse01'
FOLDER='/Game/Characters/Meshy/CozyHouse01/candidate_v002'
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if 'L_VillageTerrain_01' not in unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name():
    assert levels.load_level('/Game/Maps/L_VillageTerrain_01')
bp=unreal.load_asset(FOLDER+'/BP_CozyHouse01_Split')
# Reimport only the body after correcting its exported floor origin.
options=unreal.FbxImportUI();options.automated_import_should_detect_type=False;options.import_mesh=True;options.import_as_skeletal=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False;options.import_textures=False;options.import_animations=False
options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=unreal.AssetImportTask();task.filename=str(ROOT/'ArtSource/Meshy/CozyHouse01/candidate_v002/HouseBody.fbx');task.destination_path=FOLDER;task.destination_name='SM_CozyHouse01_HouseBody';task.automated=True;task.replace_existing=True;task.save=True;task.factory=unreal.FbxFactory();task.options=options
unreal.SystemLibrary.execute_console_command(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
body_asset=unreal.load_asset(FOLDER+'/SM_CozyHouse01_HouseBody');body_asset.set_material(0,unreal.load_asset('/Game/Characters/Meshy/CozyHouse01/candidate_v001/M_CozyHouse01'))
body_asset.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
unreal.EditorAssetLibrary.save_loaded_asset(body_asset,False)
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
components={}
for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(handle),bp)
    if isinstance(obj,unreal.SceneComponent):
        name=obj.get_name().removesuffix('_GEN_VARIABLE');components[name]=obj
        obj.set_mobility(unreal.ComponentMobility.MOVABLE if name in ('DoorHinge','DoorLeaf') else unreal.ComponentMobility.STATIC)
        if name=='DoorLeaf':
            obj.set_editor_property('relative_location',unreal.Vector(0,0,0))
            obj.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=0,roll=0))
        if name=='HouseBody':
            obj.set_editor_property('relative_location',unreal.Vector(0,0,0))
            obj.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=0,roll=0))
            obj.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
unreal.BlueprintEditorLibrary.compile_blueprint(bp);assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
# Recreate only our own just-added instance so prior detached component state
# cannot survive the corrected static-root hierarchy.
old=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='CozyHouse01_Review']
assert len(old)==1
position=old[0].get_actor_location();rotation=old[0].get_actor_rotation()
actors.destroy_actor(old[0])
cls=unreal.EditorAssetLibrary.load_blueprint_class(FOLDER+'/BP_CozyHouse01_Split')
house=actors.spawn_actor_from_class(cls,position,rotation);house.set_actor_label('CozyHouse01_Review')
meshes={c.get_name():c for c in house.get_components_by_class(unreal.StaticMeshComponent)}
assert set(meshes)=={'HouseBody','DoorLeaf'},list(meshes)
hinge=next(c for c in house.get_components_by_class(unreal.SceneComponent) if c.get_name()=='DoorHinge')
assert meshes['DoorLeaf'].get_attach_parent()==hinge
origin,extent=house.get_actor_bounds(True);dims=[extent.x*2,extent.y*2,extent.z*2]
(OUT/'component_diagnostics.json').write_text(json.dumps({'components':[{ 'name':c.get_name(),'relative':str(c.get_editor_property('relative_location')),'world':str(c.get_world_location()),'asset_bounds':str(c.get_editor_property('static_mesh').get_bounds())} for c in meshes.values()],'origin':str(origin),'extent':str(extent)},indent=2))
assert all(abs(a-b)<.2 for a,b in zip(dims,[462.2263,398.2445,430])),dims
assert abs(origin.z-extent.z-position.z)<.1,(origin,extent,position)
assert meshes['HouseBody'].get_attach_parent() is not None
assert hinge.get_editor_property('mobility')==unreal.ComponentMobility.MOVABLE
closed=meshes['DoorLeaf'].get_world_location();closed_xyz=[closed.x,closed.y,closed.z]
hinge.set_relative_rotation(unreal.Rotator(pitch=0,yaw=75,roll=0),False,True)
opened=meshes['DoorLeaf'].get_world_location();opened_xyz=[opened.x,opened.y,opened.z]
(OUT/'pivot_diagnostics.json').write_text(json.dumps({'closed':closed_xyz,'opened':opened_xyz,'relative':str(meshes['DoorLeaf'].get_editor_property('relative_location')),'hinge_world':str(hinge.get_world_location()),'hinge_relative':str(hinge.get_editor_property('relative_location'))},indent=2))
hinge.set_relative_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0),False,True)
assert sum((a-b)**2 for a,b in zip(closed_xyz,opened_xyz))<.01,(closed_xyz,opened_xyz)
assert levels.save_current_level()
target=position+unreal.Vector(0,0,180)
camera=position+unreal.Vector(850,1250,750)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(camera,unreal.MathLibrary.find_look_at_rotation(camera,target))
actors.set_selected_level_actors([])
report={'status':'gpu_editor_placement_verified','dimensions_cm':dims,'body_static':True,'hinge_movable':True,'door_separate':True,'door_parent':'DoorHinge','closed_yaw':0,'static_rotation_check_degrees':75,'animation_created':False,'map':'/Game/Maps/L_VillageTerrain_01','landscape_components':sum(len(a.get_components_by_class(unreal.LandscapeComponent)) for a in actors.get_all_level_actors() if isinstance(a,unreal.Landscape))}
(OUT/'gpu_placement_verification.json').write_text(json.dumps(report,indent=2))
STATE={'frames':0}
def tick(dt):
    try:
        worlds=unreal.EditorLevelLibrary.get_pie_worlds(False)
        if not worlds:return
        world=worlds[0];pawns=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.TownAgePlayer)
        if not pawns:return
        pawn=pawns[0];STATE['frames']+=1
        if STATE['frames']<90:return
        p=pawn.get_actor_location();houses=[a for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor) if a.get_class().get_name()=='BP_CozyHouse01_Split_C']
        assert len(houses)==1
        assert pawn.get_editor_property('character_movement').is_moving_on_ground()
        result={'status':'PIE_verified','player_cm':[p.x,p.y,p.z],'player_mesh':pawn.get_editor_property('mesh').get_skeletal_mesh_asset().get_path_name(),'grounded':True,'house_count':1,'door_components':[c.get_name() for c in houses[0].get_components_by_class(unreal.StaticMeshComponent)],'mobile_device_tested':False}
        (OUT/'pie_review.json').write_text(json.dumps(result,indent=2))
        unreal.unregister_slate_post_tick_callback(HANDLE)
    except Exception:
        (OUT/'pie_review.json').write_text(json.dumps({'error':traceback.format_exc()},indent=2));unreal.unregister_slate_post_tick_callback(HANDLE)
HANDLE=unreal.register_slate_post_tick_callback(tick)
print('HOUSE_GPU_REVIEW_READY')
