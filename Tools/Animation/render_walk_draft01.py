"""Render the actual walk draft from front, side, and gameplay-scale cameras."""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector

OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Animations/WalkDraft01')
scene=bpy.context.scene;camera=scene.camera
camera.data.clip_end=5000
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG'
def lookat(loc,target):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
for view in (('gameplay',) if '--gameplay-only' in sys.argv else ('front','side','gameplay')):
    folder=OUT/'frames'/view;folder.mkdir(parents=True,exist_ok=True)
    if view=='gameplay':
        scene.render.resolution_x=640;scene.render.resolution_y=360
        camera.data.type='PERSP';camera.data.sensor_fit='HORIZONTAL';camera.data.angle=math.radians(38)
        lookat((0,1500*math.cos(math.radians(32)),133+1500*math.sin(math.radians(32))),(0,0,133))
    else:
        scene.render.resolution_x=384;scene.render.resolution_y=512
        camera.data.type='ORTHO';camera.data.ortho_scale=205
        lookat((0,-500,84) if view=='front' else (500,0,84),(0,0,84))
    for frame in range(1,29):
        scene.frame_set(frame);scene.render.filepath=str(folder/f'frame_{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
    print('VIEW_RENDERED',view,flush=True)
print('DRAFT_PREVIEWS_RENDERED',flush=True)
