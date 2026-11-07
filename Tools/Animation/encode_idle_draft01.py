"""Encode actual rendered idle frames using the existing bundled Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json
OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Animations/IdleDraft01')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
numbers=list(range(1,109,2));durations=[60,70,70]*18
views={v:[Image.open(OUT/'frames'/v/f'frame_{f:04d}.png').convert('RGB') for f in numbers] for v in ('front','side','gameplay')}
def gif(frames,path):
    sample=Image.new('RGB',(frames[0].width,frames[0].height*4))
    for j,i in enumerate((0,16,24,40)):sample.paste(frames[i],(0,j*frames[0].height))
    palette=sample.quantize(colors=192,method=Image.Quantize.MEDIANCUT)
    imgs=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    imgs[0].save(path,save_all=True,append_images=imgs[1:],duration=durations,loop=0,disposal=2,optimize=False)
for view,frames in views.items():gif(frames,OUT/f'IdleDraft01_{view}.gif')
combined=[]
for i in range(len(numbers)):
    canvas=Image.new('RGB',(1152,600),(34,36,39));d=ImageDraw.Draw(canvas)
    for j,(view,title) in enumerate(zip(('front','side','gameplay'),('FRONT / BREATHING','SIDE / WEIGHT SHIFT','GAME-SCALE CAMERA'))):
        d.text((j*384+15,13),title,font=font,fill=(242,235,221))
        im=views[view][i]
        if view=='gameplay':
            canvas.paste(im.resize((384,216),Image.Resampling.LANCZOS),(768,130))
            d.text((783,365),'32deg pitch / 1500cm / 38deg FOV',font=small,fill=(220,215,205))
            d.text((783,390),'Blender approximation, not Unreal PIE',font=small,fill=(220,215,205))
        else:canvas.paste(im,(j*384,43))
    d.text((15,570),'IDLE DRAFT 01   |   3.6s breath cycle   |   Planted feet / fixed root   |   Subtle motion, no amplification',font=small,fill=(242,235,221))
    combined.append(canvas)
gif(combined,OUT/'IdleDraft01_three_views.gif')
sheet=Image.new('RGB',(1536,1120),(34,36,39));d=ImageDraw.Draw(sheet)
phases=[(1,'Rest'),(31,'Inhaling'),(49,'Inhale hold'),(81,'Exhaling')]
for row,view in enumerate(('front','side')):
    for col,(frame,label) in enumerate(phases):
        x=col*384;y=row*560;sheet.paste(views[view][numbers.index(frame)],(x,y+32));d.text((x+10,y+5),f'{view} {frame:03}: {label}',font=font,fill='white')
sheet.save(OUT/'IdleDraft01_phase_sheet.png')
manifest=json.loads((OUT/'manifest.json').read_text())
manifest['previews']={v:str(OUT/f'IdleDraft01_{v}.gif') for v in views};manifest['previews']['combined']=str(OUT/'IdleDraft01_three_views.gif');manifest['previews']['phase_sheet']=str(OUT/'IdleDraft01_phase_sheet.png');manifest['gif_cycle_seconds']=sum(durations)/1000
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest['previews'],indent=2))
