# Wardrobe

The gray cottage interior has a wardrobe cube to the right of the vanity. Open it
with the same G key or touch USE action. The wardrobe reuses the customization
preview at full-body framing and lists owned outfits in the right panel.

## Rebuild the local placement

Build the TownAge editor target, then run the placement script from the project
root on a closed editor. The script backs up the local interior map, interaction
table, and wardrobe Blueprint under `Saved/Wardrobe` before editing them.

```powershell
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/Wardrobe/setup_gray_wardrobe.py" -unattended -nullrhi -nosound -nop4
```

## Ownership and assets

Outfit IDs are defined in `TownAgeWardrobe.h`. The authority validates the
wardrobe session and the outfit against the account's ownership before staging
the equipped outfit. Version 1 profiles and new test profiles start with both
test garments. The default outfit is always available.

A future shop should grant the same catalog IDs through a durable server
transaction with an operation ID. The wardrobe consumes the resulting ownership
state. Replace the test defaults with the intended starter inventory before
using this profile schema for production purchases.

The approved references are `PinkDress_v02.png` and `YellowOveralls_v02.png`
under `Saved/Wardrobe/Concepts`. Meshy generated one textured mesh per image
with meshy-t2.5 and meshy-n1. The task receipts and original downloads are
under `Saved/Meshy/Wardrobe/<outfit>/v02`.

The clothing assets live under `/Game/Characters/Clothing/PinkDress` and
`/Game/Characters/Clothing/YellowOveralls`. Each variant uses the original
TownKeeper skeleton and face atlas in slot zero and its fabric in slot one.
On equip, both the pawn and its wardrobe preview switch to the same variant
while preserving animation playback. Without the local outfit
packages, the wardrobe displays an unavailable state for those choices.

To regenerate the local FBXs and base-color maps, run Blender in background
mode with `--python Tools/Wardrobe/fit_meshy_outfits.py`. The script uses the
original TownKeeper FBX, the hair mask from the customization pipeline, and
the Meshy GLBs from the task folders. Run `Tools/Wardrobe/import_outfits.py`
with Unreal Editor Python to import into empty outfit folders. The importer
checks the existing skeleton, native height, and material slots.

Launch the editor with `-ExecutePythonScript=<path to Tools/Wardrobe/verify_outfits.py>`
with Play Standalone and one player selected. It runs the door and wardrobe interaction,
switches outfits and back to default, and exports wardrobe portraits and its
result under `Saved/Wardrobe`. For a two-player PIE check, select Play As
Listen Server, two players, and Run Under One Process, then add
`-TownAgeWardrobeListenServer`. The check observes the host's outfit changes on
a nearby client and verifies the client's appearance and preview stay independent.

## Closed-fist variants

The fitted TownKeeper, PinkDress and YellowOveralls meshes under
`/Game/Characters/Meshy/TownKeeper_ClosedFists/candidate_v003` use the existing
skeleton, face atlas and fabric materials. The fist geometry comes from the
completed Meshy GLB in `Saved/Meshy/TownKeeper_ClosedFists/candidate_v001`.

Run Blender with `--python Tools/Character/fit_meshy_closed_fists.py` to extract
the fist meshes and fit them to the original TownKeeper and wardrobe wrists.
Run `Tools/Character/import_meshy_closed_fists.py` with Unreal Editor Python to
check the bind transforms and import into the empty versioned folder.
