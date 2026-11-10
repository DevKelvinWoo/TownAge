"""Create an isolated alternate mesh asset for owner-preview regression checks.

The fixture stays in Developers, outside the customization always-cook folders.
It reuses approved geometry/rig with a dye-capable material, never production.
"""
from pathlib import Path
import unreal

SOURCE = '/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001/SK_TownKeeper_Meshy'
DEST = '/Game/Developers/CustomizationTests/SK_OwnerPreviewVariant'
mesh = unreal.load_asset(DEST)
if mesh is None:
    mesh = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
assert isinstance(mesh, unreal.SkeletalMesh)
material = unreal.load_asset('/Game/Characters/Customization/M_TownKeeper_HairDye')
assert material
slots = mesh.get_editor_property('materials')
slot = slots[0]
slot.set_editor_property('material_interface', material)
slots[0] = slot
mesh.set_editor_property('materials', slots)
assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
out = Path(__file__).resolve().parents[2] / 'Saved/Customization'
out.mkdir(parents=True, exist_ok=True)
(out / 'owner_fixture_path.txt').write_text(DEST, encoding='utf8')
print('OWNER_PREVIEW_FIXTURE_READY', DEST)
