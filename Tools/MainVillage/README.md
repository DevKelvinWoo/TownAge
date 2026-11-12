# Main Village blockout

The approved reference is `ArtSource/Terrain/MainVillage/MainVillage_Concept_v001.png`.
The review map is `/Game/Maps/L_MainVillage_Blockout_01`. It copies the existing
Village01 Landscape and cottage exterior, door and streamed room. The original
terrain map remains the source for future changes. The review map starts on the
far sidewalk opposite the central crossing.

The main street is 5.6 m wide and its sidewalks are 2.7 m wide. Four blockout
shells represent the market, salon and two NPC homes. Their dark door markers
show the intended approach points. The shell doors serve as layout markers.
Street markings have no collision. The existing cottage is the working doorway.

## Reproduce and review

Run the placement command with the editor closed. The script refuses a completed
review map by default. `-MainVillageResume` is available for an incomplete
duplicate with no saved blockout layout. `-MainVillageRefresh` explicitly
reapplies the scripted blockout elements and markers to this review map.

```powershell
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/MainVillage/create_blockout.py" -unattended -nullrhi -nosound -nop4
```

Open the review map and enter Play, or launch the editor with
`-ExecutePythonScript=<path to Tools/MainVillage/verify_blockout.py>` and one
standalone PIE player. The script follows the actual pawn movement and camera.
It checks a route from the far sidewalk through the crossing, plaza and shell
entrances to the existing cottage interior. Results and camera captures go under
`Saved/MainVillage/PIE_v02`. The review fixes the clock to the morning so the
storefront and cottage entry markers can be compared under the same light.

## Resume with production art

Keep the blockout footprints and door approach points until the camera route is
approved. Use the approved village art for the storefront designs and generate
isolated exterior references for individual Meshy jobs. Keep
versioned Meshy source models, textures and task receipts under
`Saved/Meshy/MainVillage/<asset>/<run>`. Review front, side and rear views,
collision and door alignment before replacing a blockout shell.

| Order | Unreal asset folder | Next asset work |
| --- | --- | --- |
| 1 | `/Game/Environment/MainVillage/Architecture/Market` | Market shell, mint awning, basket sign and outdoor produce crates |
| 2 | `/Game/Environment/MainVillage/Architecture/Salon` | Salon shell, pink awning and scissors sign |
| 3 | `/Game/Environment/MainVillage/Architecture/NPCHomes` | Two cottage variants with a shared door/window palette |
| 4 | `/Game/Environment/MainVillage/River` | Bank rocks, reeds and wooden pedestrian bridge |
| 5 | `/Game/Environment/MainVillage/Nature` | Shade tree, fruit tree, willow, grass clusters and garden plants |
| 6 | `/Game/Environment/MainVillage/Streetscape` | Curbs, lamps, benches, mailboxes, planters and fence kit |

Keep generated meshes and map packages local. Review PC and mobile budgets
before promotion. Reuse the Landscape, pavement and road surfaces already in
the blockout when refining the streetscape.

## Streetscape finish

The approved reference is
`ArtSource/Terrain/MainVillage/Streetscape/Streetscape_Concept_v001.png`.
The road and paving share world-aligned, tiling textures. The sidewalk uses
50 × 25 cm staggered blocks and the plaza uses 50 × 50 cm squares. Pavement
relief is a normal map. Chamfered curb stones and tapered curb ends are two
reusable static meshes under `/Game/Environment/MainVillage/Streetscape`.
The map uses two instanced groups for the curb edges. Curbs are visual
geometry. The existing road and sidewalk surfaces provide walkable collision.

```powershell
& 'E:/UE/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' Tools/MainVillage/generate_streetscape_textures.py
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/MainVillage/apply_streetscape.py" -unattended -nullrhi -nosound -nop4
```

The application backs up the review map and changes its streetscape only.
Pass `-MainVillageRefreshStreetTextures` after regenerating texture revisions
to back up and reimport the five existing streetscape texture packages.
It derives the curb edges from the authored Main street polyline. The current
crosswalk needs to be on the final straight segment. If the route changes,
move the crossing markers with the route and reapply to regenerate the curbs.
The earlier blockout refresh restores the original surface palette, so run the
streetscape application again after a blockout refresh.

Add `-MainVillageStreetscape` to the PIE verifier to check the saved curb
instances, material references and vertical movement at the crossing. It
writes the capture sequence to `Saved/MainVillage/Streetscape/PIE`.

## Lighting review

Open `/Game/Maps/L_MainVillage_Blockout_01`, start a standalone development
Play session, and press **F7** to jump to one of the four lighting presets.
The map is listed in `CozyVillageLightingMaps` in `Config/DefaultGame.ini`.

Run the editor with `-ExecutePythonScript=<path to Tools/MainVillage/verify_lighting.py>`
to exercise the preview buttons and save the panel plus four matched
gameplay-camera captures under `Saved/MainVillage/Lighting/PIE`.
