"""Retarget the approved walk's foot trajectory/timing to Revision05 limb lengths."""
from pathlib import Path
import json
ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
path=ROOT/'Tools/Animation/build_walk_draft01.py'
source=path.read_text(encoding='utf-8')
source=source.replace("OUT=ROOT/'ArtSource/Characters/Main/Animations/WalkDraft01'","OUT=ROOT/'ArtSource/Characters/Main/Revision05/WalkAuthoring'")
source=source.replace("SOURCE=ROOT/'ArtSource/Characters/Main/Revision04/TownKeeper_Reference04.blend'","SOURCE=ROOT/'ArtSource/Characters/Main/Revision05/TownKeeper_Reference05.blend'")
source=source.replace("rig.name='RIG_TownKeeper_WalkDraft01'","rig.name='Armature_008'")
source=source.replace("'WALK_TownKeeper_Draft01'","'WALK_TownKeeper_Revision05'")
source=source.replace("abduction=.40 if side=='r' else .23","abduction=.60 if side=='r' else .23")
source=source.replace("'TownKeeper_WalkDraft01.blend'","'TownKeeper_Walk05_Authoring.blend'")
injection=r'''
# Keep the approved64cm trajectory if reachable. A minimal constant pelvis
# lowering accommodates shorter limbs instead of stretching bones or copying
# the previous rig's per-frame translations.
PELVIS_FIT_OFFSET_CM=0.0
for fitframe in range(1,PERIOD+2):
    phase=(fitframe-1)/PERIOD
    dz=periodic([-4.8,-6.0,-4.3,-3.5,-4.8,-6.0,-4.3,-3.5],phase)
    sway=periodic([0,-1.1,-1.5,-.8,0,1.1,1.5,.8],phase)
    yaw=math.radians(periodic([-2.2,-1.6,0,1.6,2.2,1.6,0,-1.6],phase))
    roll=math.radians(periodic([0,-1,-1.5,-.8,0,1,1.5,.8],phase))
    ph=rig.data.bones['pelvis'].head_local+Vector((sway,0,dz))
    pm=Matrix.Translation(ph)@Quaternion((0,0,1),yaw).to_matrix().to_4x4()@Quaternion((0,1,0),roll).to_matrix().to_4x4()@rest['pelvis'].to_3x3().to_4x4()
    for side,off in [('l',0),('r',.5)]:
        y,lift,pitch,stance=footpath((phase+off)%1)
        ankle_rest=rig.data.bones['foot_'+side].head_local;rot=Quaternion((1,0,0),pitch).to_matrix()
        support=min((rot@(v-ankle_rest)).z for v in footverts[side]);ankle=Vector((ankle_rest.x,y,-support+lift))
        hip=(pm@rest['pelvis'].inverted())@rig.data.bones['thigh_'+side].head_local
        length=rig.data.bones['thigh_'+side].length+rig.data.bones['calf_'+side].length-.10
        horizontal=(hip.x-ankle.x)**2+(hip.y-ankle.y)**2
        assert horizontal<length*length,'Approved stride is physically unreachable with these legs'
        required=hip.z-ankle.z-math.sqrt(length*length-horizontal)
        PELVIS_FIT_OFFSET_CM=max(PELVIS_FIT_OFFSET_CM,required)
PELVIS_FIT_OFFSET_CM+=.10
print('PROPORTION_FIT_PELVIS_OFFSET_CM',PELVIS_FIT_OFFSET_CM,flush=True)
'''
source=source.replace('poses=[];metrics=[]',injection+'\nposes=[];metrics=[]')
# Replace only the actual frame loop's expression, keeping fit calculation intact.
anchor="for frame in range(1,PERIOD+2):\n    phase=(frame-1)/PERIOD\n    dz=periodic([-4.8,-6.0,-4.3,-3.5,-4.8,-6.0,-4.3,-3.5],phase)"
assert source.count(anchor)==1
source=source.replace(anchor,anchor+'-PELVIS_FIT_OFFSET_CM')
exec(compile(source,str(path),'exec'))
manifest['status']='approved_walk_retargeted_to_revision05'
manifest['approved_motion']='WalkDraft01; same28-frame timing and64cm stride'
manifest['pelvis_fit_offset_cm']=PELVIS_FIT_OFFSET_CM
manifest['current_gameplay_walk_speed_cm_s']=68.57142857142857
manifest['speed_match_to_gameplay']=True
manifest['notes']=['Recomputed each pose with new limb lengths and rest transforms.','Constant pelvis fit lowering preserves approved stride without stretching bones.','No new sprint or idle motion.']
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
