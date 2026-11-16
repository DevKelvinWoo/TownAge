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

## Generated-art village assembly

`assemble_art_village.py` creates `/Game/Maps/L_MainVillage_Art_01` from the
reviewed blockout and refuses any existing destination. Import the three new
buildings and nine environment meshes first. Preflight reports missing assets
before any map writes. The expected folders are:

- `Architecture/{Mart,GreenHouse,Salon}/v001/SM_<name>`
- `Nature/{Tree,Shrub,Flowers,Rock}/v001/SM_<name>`
- `Streetscape/{Bench,Lamp,Fence,Bridge,Planter}/v001/SM_<name>`

All paths above are below `/Game/Environment/MainVillage`. The complete existing
CozyHouse01 mesh fills the fourth shell; the original interactive cottage and
its doorway are retained. New buildings are static exterior set dressing, not
new travel portals. Actual imported bounds determine scale and ground contact.

With the editor closed, run:

```powershell
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/MainVillage/assemble_art_village.py" -unattended -nullrhi -nosound -nop4
```

Optional `Saved/MainVillage/Art/assembly_overrides.json` accepts `asset_paths`
and `yaw_degrees` dictionaries keyed by asset name. Use these before first
assembly when import review reveals a different front axis. This file is local
art configuration, not a runtime dependency. No existing assets or startup maps
are changed. `MainVillage_Art_Overview` is an editor-only review camera.

`Saved/MainVillage/Art/assembly_report.json` records all actor bounds, scales,
counts, source-map hash and unverified runtime checks. The water reservation
uses a 650cm strip behind the shops, with centerline markers and a future water
surface at Z=15cm above the existing flat ground. A shallow surface can be added
there without excavation; a deep river requires later Landscape sculpting.
Water itself is intentionally absent. The exact coordinates are also saved to
`water_reservation.json`. Check the bridge orientation and clearance in a GPU
editor before adding water. This commandlet is not proof of visual quality,
walkable collision, multiplayer behavior or mobile performance.

For three GPU captures and a grounded player-spawn check, launch a normal
rendering editor with one-player standalone PIE settings:

```powershell
Start-Process -FilePath 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList "$PWD/TownAge.uproject",'-unattended',"-ExecutePythonScript=$PWD/Tools/MainVillage/review_art_village.py" -WindowStyle Hidden
```

The script waits 15 seconds, captures the saved overview and a closer storefront
view, starts PIE automatically, checks that the actual player is grounded, and
captures the gameplay camera. It exits the editor afterward and does not save
review-only changes. Outputs are `Saved/MainVillage/Art/Review/01_Overview.png`,
`02_Storefronts.png`, `03_Gameplay.png`, and `review_report.json`. A successful
capture is evidence of that view only; inspect the images and run route checks
before claiming the whole level is collision-tested.
The review also isolates each new building in a blocking collision trace and
walks the actual pawn toward the crossing for two seconds, requiring grounded
movement of at least 80cm. It does not teleport the pawn or test building entry.

## Building replacement candidates

`import_environment_art.py` requires a normal GPU editor because collision and
LOD editing subsystems are unavailable in a Python commandlet. The default run
imports or verifies all twelve `v001` deliveries. Use `-MainVillageBuildingV2`
to import only Mart, GreenHouse and Salon from
`ArtSource/Meshy/MainVillage/<name>/v002/model.fbx` into separate
`/Game/Environment/MainVillage/Architecture/<name>/v002` folders:

```powershell
Start-Process -FilePath 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList "$PWD/TownAge.uproject",'-unattended',"-ExecutePythonScript=$PWD/Tools/MainVillage/import_environment_art.py",'-MainVillageBuildingV2','-MainVillageQuitAfterImport' -WindowStyle Hidden -Wait
```

The replacement run writes `Saved/MainVillage/Art/import_report_v002.json` and
does not change the successful `v001` report or packages. It recomputes geometry
normals and MikkTSpace tangents, uses single-sided building materials, and
generates three LODs. This does not reconstruct missing faces; inspect each
replacement before changing the level's asset paths. Normal textures remain
omitted unless their convention has verified local evidence.

## Art district delivery (2026-11-16)

The local art map is `/Game/Maps/L_MainVillage_Art_01`. Three new buildings use
the `v002` architecture candidates; nine environment models use `v001`.
Existing CozyHouse art supplies extra homes. New shop doors are static exterior
art; only the retained cottage has the established travel interaction.

After assembly and building import, run `polish_art_village.py` in the same
commandlet form as the assembler. It backs up the art map, updates only that
map, protects existing cottage/portal transforms numerically, and uses the
available v002 buildings. It adds a curved side street, opens its curb mouth,
adjusts planting and building proportions, and records its changes in
`Saved/MainVillage/Art/polish_report.json`. The source blockout and startup maps
are preserved. The art map opts into the existing cozy day/night lighting.

No water is placed. `Saved/MainVillage/Art/water_reservation.json` contains the
650cm-wide centerline and planned surface at Z=15cm. The shortened river strip
was checked against 657 conservative heightmap samples: maximum bed height
8.59375cm, minimum sampled surface clearance 6.40625cm. This supports a shallow
visual water surface; it is not an excavated or swimmable river.

Meshy expenditure was 270 credits (1036 before, 766 after): 45 for initial
buildings, 135 for nine textured environment assets, and 90 for improved
building candidates. Provider receipts and binary art remain local.

The GPU review checks real screenshots, grounded spawn, a two-second walking
input toward the crossing, and isolated building collision traces. It does not
certify every path, bridge traversal, packaged multiplayer, or physical mobile
performance. Generated window/interior details still require art cleanup for
close-up production shots. Unreal import success is not visual equivalence to
the concept.

## Warm illustrated presentation

Run `refine_surfaces.py` after the warm appearance pass for world-aligned grass,
asphalt and paving plus shared mitered street edges. Passing
`-VillageSurfacePreview` targets `/Game/Maps/L_MainVillage_SurfaceReview_01`.
The GPU review accepts the same flag and writes to `Saved/MainVillage/Surfaces/Review`.

`apply_warm_look.py` is the final appearance step, after assembly/polish. It
backs up Art_01, keeps source textures and meshes intact, and assigns isolated
matte material variants under `/Game/Environment/MainVillage/Look/WarmIllustrated_v001`.
The variants lift dark baked colors, suppress metallic/specular response, and
add a small diffuse fill. Softer sage ground replaces the coarse grass patches.
A dedicated grade restores bright cream/pink colors without the initial gray
wash. The original maps and streamed-room component materials are unchanged.

Run the script in the same Python commandlet form as assembly, then use the GPU
review. `WarmIllustratedLightingMaps` keeps the art map's soft shadows and daytime
exposure consistent with its runtime clock; other cozy-map presets retain their
existing values. Before/after screenshots live in `Saved/MainVillage/WarmLook`.
Run this appearance step again after `polish_art_village.py`, which sets the
baseline Landscape and lighting.

## Debug click teleport

In a non-Shipping play session, hold **Ctrl + Alt** and left-click a visible
walkable surface. The cursor is temporarily shown and restored on release.
Chat, appearance customization and lighting UI retain input ownership; doorway
traversal blocks teleport. The server resolves the floor, checks capsule space,
stops movement and replicates the resulting pawn position. No durable profile
or village record is changed.

PIE and standalone enable the feature immediately. Other development network
servers must explicitly set `TownAge.Debug.AllowTeleport 1` on authority;
client console settings cannot enable server permission. Shipping has no key
binding and rejects both local requests and the server RPC.

Run `verify_debug_teleport.py` in a normal GPU editor for success/rejection tests.
`verify_debug_teleport_network.py` exercises a two-player listen PIE session and
restores its transient play settings. Both use `-ExecutePythonScript` and write
reports under `Saved/MainVillage/DebugTeleport`. These tests do not substitute
for physical keyboard/mouse input or packaged-device verification.
For the network verifier, also pass
`-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=PIE_ListenServer`.
UE 5.8 does not export this settings enum to Python; the override applies to the
test process. The script restores client count/process settings without saving
them, while normal editor preference updates can still occur during PIE.
