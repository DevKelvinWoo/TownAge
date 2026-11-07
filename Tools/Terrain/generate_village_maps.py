"""Deterministic 252m pedestrian village terrain; stdlib only, no UE mutation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

SIZE, HALF, SEED = 253, 126, 3701
ROOT = Path(__file__).resolve().parents[2]


def smooth(low, high, value):
    t = max(0.0, min(1.0, (value-low)/(high-low)))
    return t*t*(3-2*t)


def curve(points):
    return [tuple(sum(math.comb(3,j)*(1-t)**(3-j)*t**j*points[j][axis]
                      for j in range(4)) for axis in range(2))
            for t in (i/64 for i in range(65))]


ROUTES = [
    curve([(25,-6),(-15,5),(-76,8),(-126,18)]),
    curve([(37,4),(35,45),(-14,85),(0,126)]),
    curve([(37,-16),(37,-62),(-22,-82),(-12,-126)]),
    curve([(49,-6),(78,-9),(92,30),(126,25)]),
]
SECONDARY = curve([ROUTES[0][40],(-86,51),(-23,62),ROUTES[1][38]])
SEGMENTS = [(a,b,2.5) for route in ROUTES for a,b in zip(route,route[1:])]
SEGMENTS += [(a,b,2.0) for a,b in zip(SECONDARY,SECONDARY[1:])]


def road_distance(x,y):
    nearest = 1e9
    for (ax,ay),(bx,by),radius in SEGMENTS:
        dx,dy=bx-ax,by-ay
        t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
        nearest=min(nearest,math.hypot(x-ax-t*dx,y-ay-t*dy)-radius)
    return nearest


def plaza_distance(x,y):
    # Rounded 24x20m rectangle, radius4m, center(37,-6).
    qx,qy=abs(x-37)-8,abs(y+6)-6
    return math.hypot(max(qx,0),max(qy,0))+min(max(qx,qy),0)-4


def generate():
    heights, paving, distances = [], [], []
    for iy in range(SIZE):
        y=iy-HALF
        for ix in range(SIZE):
            x=ix-HALF
            outer=smooth(50,118,max(abs(x),abs(y)))
            phase=SEED*.001
            noise=.55+.25*math.sin(x/31+phase)*math.cos(y/39-phase)+.20*math.sin((x+y)/53+phase)
            hill=outer*(1.7+6.3*noise)
            distance=min(road_distance(x,y),plaza_distance(x,y))
            # Low route crests and wide shoulders keep routes accessible.
            height=(1-smooth(1,34,distance))*(outer*.7)+smooth(1,34,distance)*hill
            heights.append(round(32768+max(0,min(8,height))*128))
            paving.append(round(255*(1-smooth(-.15,.85,distance))))
            distances.append(distance)
    slopes=[]
    for iy in range(SIZE):
        for ix in range(SIZE):
            left,right=max(0,ix-1),min(SIZE-1,ix+1)
            down,up=max(0,iy-1),min(SIZE-1,iy+1)
            dx=(heights[iy*SIZE+right]-heights[iy*SIZE+left])/128/(right-left)
            dy=(heights[up*SIZE+ix]-heights[down*SIZE+ix])/128/(up-down)
            slopes.append(math.hypot(dx,dy))
    earth=[round((255-p)*.22*smooth(.12,.24,s)) for p,s in zip(paving,slopes)]
    grass=[255-p-e for p,e in zip(paving,earth)]
    files={'Height.r16':struct.pack('<'+'H'*len(heights),*heights),
           'Grass.r8':bytes(grass),'Paving.r8':bytes(paving),'Earth.r8':bytes(earth)}
    assert len(files['Height.r16'])==SIZE*SIZE*2
    assert all(len(files[name])==SIZE*SIZE for name in ('Grass.r8','Paving.r8','Earth.r8'))
    assert all(g+p+e==255 for g,p,e in zip(grass,paving,earth))
    assert min(heights)>=32768 and max(heights)<=32768+8*128
    central=[heights[y*SIZE+x] for y in range(76,177) for x in range(76,177)]
    assert min(central)==max(central)==32768, 'Central100m square must remain flat'
    route_slope=max(s for s,d in zip(slopes,distances) if d<0)
    assert route_slope<.10, 'Main routes must remain below10% grade'
    assert max(slopes)<math.tan(math.radians(18)), 'Outer hills must remain gentle'
    report={'seed':SEED,'grid':[SIZE,SIZE],'width_m':252,'origin_cm':[-12600,-12600,0],
            'landscape_scale':[100,100,100],'components':16,'subsection_quads':63,
            'height_encoding':'little-endianuint16;32768+height_cm*128/100',
            'height_min_max_m':[(min(heights)-32768)/128,(max(heights)-32768)/128],
            'max_slope_degrees':math.degrees(math.atan(max(slopes))),
            'max_route_slope_degrees':math.degrees(math.atan(route_slope)),
            'central_flat_width_m':100,'plaza_center_m':[37,-6],'plaza_size_m':[24,20],
            'path_width_m':5,'secondary_path_width_m':4,
            'secondary_connection_endpoints_m':[SECONDARY[0],SECONDARY[-1]],
            'layer_average_coverage':{n:sum(a)/(255*len(a)) for n,a in [('Grass',grass),('Paving',paving),('Earth',earth)]},
            'files':{n:{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for n,data in files.items()}}
    # Numeric map preview, not a concept-art edit; PNG encoding uses stdlib.
    rgb=[]
    for h,g,p,e in zip(heights,grass,paving,earth):
        shade=.90+.10*(h-32768)/1024
        rgb.extend(round(shade*(g*a+p*b+e*c)/255) for a,b,c in [(119,225,143),(164,218,127),(73,195,99)])
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    scan=b''.join(b'\0'+bytes(rgb[y*SIZE*3:(y+1)*SIZE*3]) for y in range(SIZE))
    files['Terrain_Data_Overview.png']=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',SIZE,SIZE,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b'')
    files['terrain_manifest.json']=(json.dumps(report,indent=2)+'\n').encode()
    return files,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'ArtSource/Terrain/Village01')
    parser.add_argument('--replace',action='store_true',help='Replace only named generated outputs when bytes differ')
    parser.add_argument('--validate-only',action='store_true',help='Validate all existing outputs against deterministic expected bytes')
    args=parser.parse_args();files,report=generate()
    conflicts=[str(args.output/name) for name,data in files.items() if (args.output/name).exists() and (args.output/name).read_bytes()!=data]
    if conflicts and not args.replace:raise SystemExit('Refusing to overwrite different data: '+', '.join(conflicts))
    if args.validate_only:
        assert all((args.output/name).read_bytes()==data for name,data in files.items()),'Generated output mismatch'
    else:
        args.output.mkdir(parents=True,exist_ok=True)
        for name,data in files.items():
            path=args.output/name
            if not path.exists() or path.read_bytes()!=data:path.write_bytes(data)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
