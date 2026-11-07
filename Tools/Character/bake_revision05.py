"""Bake the verified Revision05 source into portable texture atlas and cm FBX."""
from pathlib import Path
ROOT=Path(r'C:/Users/Kelvin/Desktop/TownAge')
path=ROOT/'ArtSource/Characters/Main/bake_reference03.py'
source=path.read_text(encoding='utf-8').replace('Revision03','Revision05').replace('Reference03','Reference05')
source=source.replace("rig=body.parent","rig=body.parent\nrig.name='Armature_008'")
source=source.replace('scene.cycles.samples=32','scene.cycles.samples=16')
anchor="body.data.materials.clear();body.data.materials.append(atlas)"
assert source.count(anchor)==1
source=source.replace(anchor,"bag_attribute=body.data.attributes.new('tk_satchel_faces','BOOLEAN','FACE')\nfor polygon in body.data.polygons:bag_attribute.data[polygon.index].value='BagLeather' in body.data.materials[polygon.material_index].name\n"+anchor)
exec(compile(source,str(path),'exec'))
