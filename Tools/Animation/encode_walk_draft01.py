"""Encode rendered frame previews. Requires bundled Pillow, not an AI image edit."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json

OUT=Path(r'C:/Users/Kelvin/Desktop/TownAge/ArtSource/Characters/Main/Animations/WalkDraft01')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
durations=[30,30,40]*9+[30]
views={v:[Image.open(OUT/'frames'/v/f'frame_{i:04d}.png').convert('RGB') for i in range(1,29)] for v in ('front','side','gameplay')}
def gif(frames,path):
    samples=Image.new('RGB',(frames[0].width,frames[0].height*4))
    for j,i in enumerate((0,7,14,21)):samples.paste(frames[i],(0,j*frames[0].height))
    palette=samples.quantize(colors=192,method=Image.Quantize.MEDIANCUT)
    quantized=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    quantized[0].save(path,save_all=True,append_images=quantized[1:],duration=durations,loop=0,disposal=2,optimize=False)
for view,frames in views.items():gif(frames,OUT/f'WalkDraft01_{view}.gif')
combined=[]
for i in range(28):
    canvas=Image.new('RGB',(1152,600),(34,36,39));draw=ImageDraw.Draw(canvas)
    titles=['FRONT','SIDE / FOOT CONTACT','GAME-SCALE CAMERA']
    for j,view in enumerate(('front','side','gameplay')):
        draw.text((j*384+15,13),titles[j],font=font,fill=(242,235,221))
        frame=views[view][i]
        if view=='gameplay':
            frame=frame.resize((384,216),Image.Resampling.LANCZOS)
            canvas.paste(frame,(768,130))
            draw.text((783,365),'32 degree pitch / 1500cm / 38deg FOV',font=small,fill=(220,215,205))
            draw.text((783,390),'Blender camera approximation, not PIE',font=small,fill=(220,215,205))
        else:canvas.paste(frame,(j*384,43))
    draw.text((15,570),'WALK DRAFT 01   |   0.933s cycle   |   68.6 cm/s treadmill   |   In-place root   |   Awaiting direction',font=small,fill=(242,235,221))
    combined.append(canvas)
gif(combined,OUT/'WalkDraft01_three_views.gif')
sheet=Image.new('RGB',(4*384,2*560),(34,36,39));draw=ImageDraw.Draw(sheet)
frames=[1,4,8,11,15,18,22,25]
names=['L contact','L down','L passing','L up','R contact','R down','R passing','R up']
for i,(frame,label) in enumerate(zip(frames,names)):
    x=(i%4)*384;y=(i//4)*560
    sheet.paste(views['side'][frame-1],(x,y+32));draw.text((x+10,y+5),f'{frame:02d}: {label}',font=font,fill='white')
sheet.save(OUT/'WalkDraft01_contact_sheet.png')
manifest=json.loads((OUT/'manifest.json').read_text())
manifest['previews']={v:str(OUT/f'WalkDraft01_{v}.gif') for v in views}
manifest['previews']['combined']=str(OUT/'WalkDraft01_three_views.gif')
manifest['previews']['contact_sheet']=str(OUT/'WalkDraft01_contact_sheet.png')
manifest['gif_cycle_seconds']=sum(durations)/1000
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest['previews'],indent=2))
