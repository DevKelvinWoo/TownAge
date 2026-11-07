# Meshy to Unreal candidate contract

Read this when downloaded Meshy files are ready for local validation/import. `Tools/Meshy/import_meshy_unreal.py` accepts a strict JSON object; keep task IDs, costs and approval history in a separate job receipt. Unknown import fields are rejected.

```json
{
  "asset_name": "TownKeeper_Meshy",
  "asset_type": "skeletal",
  "fbx_path": "model.fbx",
  "target_height_cm": 170,
  "textures": {
    "basecolor": "textures/basecolor.png",
    "normal": "textures/normal.png",
    "roughness": "textures/roughness.png"
  },
  "normal_convention": "DirectX",
  "destination": "/Game/Characters/Meshy/TownKeeper_Meshy",
  "candidate_version": "candidate_v001",
  "create_placement_blueprint": true
}
```

This is a format example, not an existing model or permission to generate one. Supply only texture channels actually present and identify the actual normal convention before import.

| Field | Contract |
| --- | --- |
| `asset_name` | Required. Starts with a letter; remaining characters are letters, digits or underscores. |
| `asset_type` | Required: `skeletal` or `static`. The imported class must agree. |
| `fbx_path` | Required local `.fbx` file. Absolute or relative to the manifest file. |
| `target_height_cm` | Optional finite positive number, default170. |
| `textures` | Optional map of `basecolor`, `normal`, `roughness` to existing local image files. Paths resolve relative to the manifest. |
| `normal_convention` | Optional `DirectX` or `OpenGL`, defaultDirectX. Do not assume the default is correct for a downloaded asset. |
| `destination` | Optional package folder under `/Game/Characters/Meshy`; default `/Game/Characters/Meshy/<asset_name>`. |
| `candidate_version` | Optional safe identifier, default `candidate_v001`. |
| `create_placement_blueprint` | Optional boolean, defaultfalse. |

The actual import folder is `destination/candidate_version`. An already populated candidate folder is rejected rather than overwritten. A failed partial import also remains isolated: inspect its report and choose a new version for a deliberate retry.

## What the current importer does

- Imports one static or skeletal FBX with animation import disabled.
- Creates and saves a new Skeleton/Physics Asset for skeletal input.
- Connects one atlas material and supplied texture channels; base color is sRGB, roughness linear, normal-map compression is enabled, and OpenGL green is flipped once.
- Optionally creates a placement Actor BP with a mesh child component. Its uniform placement scale is calculated from target height/native mesh height.
- Writes `Saved/Meshy/<asset_name>/<candidate_version>/import_report.json` and leaves production assets/maps/pawn references unchanged.

The current texture contract is **one atlas**. The importer rejects FBX inputs with more than one material slot instead of silently assigning one texture to unrelated UV/material sets. A multi-material Meshy delivery must be consolidated through an authorized workflow or the importer extended. Missing maps remain missing and must be reported; the helper supplies a roughness constant when no roughness map exists.

## Verification before promotion

Check front/side/back engine views, back-face culling, UVs, texture color space and normal direction. Confirm the report's native height and scale, and measure a newly placed candidate Actor—target metadata and a successful import alone do not prove170cm placement. A placement scale is not evidence that the source FBX has correct centimeter units; resolve bone/root-scale errors instead of hiding them with an arbitrary Actor multiplier.

For characters, inspect the new skeleton, normalized skin, joint deformation, hair/accessory clearance, Physics Asset and animation compatibility. Do not reuse old clips based only on similar bone names. For PC/mobile, record triangles, material sections, texture memory and intended LODs; actual packaged-device/network tests are separate evidence.

Only a requested production integration step may change the native playable mesh path, placement BP, current level or animation references. Preserve the previous working character until the new candidate has passed these checks.
