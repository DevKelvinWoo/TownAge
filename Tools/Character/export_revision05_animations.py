"""Package retargeted approved gait and new-proportion standing support clip."""
from pathlib import Path
import json
ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
path=ROOT/'Tools/Animation/export_walk_final01.py'
source=path.read_text(encoding='utf-8')
source=source.replace("OUT=ROOT/'ArtSource/Characters/Main/Animations/WalkFinal01'","OUT=ROOT/'ArtSource/Characters/Main/Revision05'")
source=source.replace("DRAFT=ROOT/'ArtSource/Characters/Main/Animations/WalkDraft01/TownKeeper_WalkDraft01.blend'","DRAFT=ROOT/'ArtSource/Characters/Main/Revision05/WalkAuthoring/TownKeeper_Walk05_Authoring.blend'")
source=source.replace("PRODUCTION=ROOT/'ArtSource/Characters/Main/Revision04/TownKeeper_Reference04.blend'","PRODUCTION=ROOT/'ArtSource/Characters/Main/Revision05/TownKeeper_Reference05.blend'")
source=source.replace('A_TownKeeper_Walk.fbx','A_TownKeeper_Walk05.fbx').replace('A_TownKeeper_Standing.fbx','A_TownKeeper_Standing05.fbx')
source=source.replace('TownKeeper_WalkFinal01.blend','TownKeeper_Animation05.blend')
source=source.replace("OUT/'manifest.json'","OUT/'animation_manifest.json'")
source=source.replace("'WALK_TownKeeper_Final01'","'WALK_TownKeeper_Revision05_Final'")
source=source.replace("'POSE_TownKeeper_Standing'","'POSE_TownKeeper_Standing05'")
source=source.replace("abd=.40 if side=='r' else .23","abd=.60 if side=='r' else .23")
exec(compile(source,str(path),'exec'))
fit=json.loads((OUT/'WalkAuthoring/manifest.json').read_text())
report['approved_draft']='WalkDraft01 trajectory/timing retargeted to Revision05 proportions'
report['pelvis_fit_offset_cm']=fit['pelvis_fit_offset_cm']
report['retarget_transform_max_change_during_export']=report.pop('walk_transform_max_change_from_approved')
(OUT/'animation_manifest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

# Directly inspect both relaxed hands at actual standing orientation.
rig.animation_data.action=stand;scene.frame_set(1);bpy.context.view_layer.update()
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=24
scene.render.resolution_x=640;scene.render.resolution_y=640
for side,sign in (('l',-1),('r',1)):
    bone=rig.pose.bones['hand_'+side];center=rig.matrix_world@(bone.head.lerp(bone.tail,.65))
    camera.location=center+Vector((sign*55,-35,16))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'Hand_{side}_Standing.png');bpy.ops.render.render(write_still=True)
print('REVISION05_ANIMATIONS_READY',json.dumps({'walk':report['walk']['path'],'standing':report['standing']['path'],'pelvis_fit_offset_cm':fit['pelvis_fit_offset_cm']}),flush=True)
