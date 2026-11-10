# Modular character customization

`VanityUse` opens a character customization panel through the existing
server-validated G/mobile USE interaction. Its left column renders the owner's
looping Idle; its right column offers Dye, Surgery and Makeup categories. Dye
uses a full-body camera and four test hair colors. Surgery and Makeup select the
face camera automatically. Surgery is preview-only; Makeup provides six surface
effects, palettes, strength sliders, Natural and Reset. Close/Escape retains
server-approved appearance on the playable character. Art research and asset
reproduction are in [MAKEUP.md](MAKEUP.md).

## Assets and reproduction

1. Run `generate_hair_mask.py` in isolated Blender background mode. It reads the
   retained rigged GLB, rasterizes its UVs and excludes skin/clothing/leather.
   The hair mask, provenance and visual checks are local in `Saved/Customization`.
   No mesh, skeleton, skin or original atlas is reimported or edited.
2. Build `TownAgeEditor`, close conflicting asset editors, then run
   `setup_customization.py` through Unreal Python. It imports the mask and creates
   `/Game/Characters/Customization/M_TownKeeper_HairDye`. It creates the isolated
   `/Game/Maps/Customization/L_CharacterCustomizationPreview` only when absent,
   preserving any existing map. Owned material/table packages are backed up.
3. The material preserves the existing base color, normal and roughness. Only
   masked hair is blended toward a luminance-preserving `HairTint` controlled by
   `DyeStrength`. Zero strength retains the exact original base color. A per-mesh
   dynamic instance avoids recoloring other players. The existing single mesh
   material slot remains intact; one shared resident 2048px mask is added for
   densely packed UVs. Its mips are disabled so coarse atlas averages cannot
   tint neighboring face/limb islands while texture streaming settles or the
   live character moves farther from the camera. Profile this shared texture's
   memory and distant boundary aliasing on target mobile devices.

The packaging settings always cook the two new asset directories without
replacing the project's existing map selection. Models, textures, levels,
screenshots and generated masks remain local; only source and docs are published.

## Runtime and authority

The live pawn stays in its interior and its server movement is disabled only for
the active session. Opening, choosing a color and retaining the selection use
an owned replicated customization component. The server rechecks the authored
vanity, approach, range, enabled state and session sequence for every choice.
Clients cannot submit arbitrary material values or object paths. Palette index
zero is the original appearance; user-selectable indices are 1..4.

Only the participating local client loads a dynamic preview sublevel at 100000cm
and spawns its preview actor into that level. There is no `OpenLevel`, pawn
transfer or shared village replacement. A show-only SceneCapture2D renders the
preview mesh and floor to a 768x1024 target at up to 30Hz. A single directional
key and shadowless point fill use lighting channel 2; atmosphere, fog and motion
blur and temporal antialiasing are disabled for this capture, avoiding facial
smearing at low frame rates. Eight capture frames warm up the preview before
enabling the chips. The camera faces the character independently
of the gameplay camera. See [Epic SceneCapture2D API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/USceneCaptureComponent2D).

Until the render target is assigned and preview readiness is confirmed, the
portrait is hidden behind an opaque loading panel with a localized opening
message and three-dot indicator. An empty image brush explicitly draws nothing,
preventing the white placeholder flash. Color chips remain disabled during
loading; Close/Escape remain available. This adds only a lightweight UMG overlay
and does not keep the preview level/capture resident after closing.

Closing, pawn EndPlay, invalid/destroyed targets and loading failure clean up the
widget, capture actor and preview streaming instance. Session IDs prevent old
close/choice messages from acting on a reopened session. Gameplay interaction,
sprint, movement and chat are gated while the panel is open; touch state still
updates so held input cannot become a fresh press after closing.

Appearance replicates to other clients, including a newly relevant pawn. The
selection currently belongs to this pawn's lifetime. Account saves, persistence
across game restarts and respawn migration are outside this prototype.

## Owner avatars and preview views

The preview is initialized from the participating pawn's actual mesh, rather
than a hardcoded TownKeeper mesh. It copies mesh identity, current scale, morph
values, material values and visible skeletal/static attachments. Preview MIDs
are independent of the live player and other players. A compatible zero-speed
Blend Space sample is reused for Idle; avatars with another animation setup can
author `PreviewIdleAnimation` on their customization component. A foreign
TownKeeper animation is never forced onto an unrelated skeleton.

Each avatar may author `HairDyeMaterials` (material slot -> masked material),
using `HairTint` and `DyeStrength`. A dedicated slot whose name contains `Hair`
may instead provide `HairTint` or `HairColor`. The shared helper checks attached
skeletal/static hair too. Only the exact original TownKeeper mesh/material gets
the existing TownKeeper atlas conversion. An unprepared model keeps its own
materials, can still use both camera views, and shows a dye-unavailable notice
until its artist provides a compatible hair channel. Character spawning/model
selection and its network replication remain the owning avatar system's job.

Camera framing follows the selected cosmetic category. Face framing uses the
avatar's Head socket (or bounds fallback), upper mesh bounds and forward depth,
so a neck-root bone does not crop the forehead. The same render target and Idle
continue during the smooth camera transition. Reopening selects the first
category allowed by that station. No surgery mutations are implemented yet.

`create_owner_preview_fixture.py` creates a separate developer-only alternate
mesh asset with the supported dye interface, reusing approved geometry. Run
`verify_owner_preview.py` after the normal standalone verifier to check alternate
mesh identity/scale, dye/zoom, unrelated-skeleton material safety, and restoration
of the original avatar. The developer fixture is outside always-cook folders.
The two-player `verify_network.py` now uses that alternate mesh for the remote
player and checks its preview against its own mesh, with the host left unchanged.

Owner/view revision verified: build/UHT and 13 automation tests; initial loading
mask with disabled chips followed by a visible ready portrait; owner mesh and
independent MID identity; full-body/face camera round trip; all four dyes;
alternate owner asset/scale, an unrelated skeleton without a foreign atlas,
and restoration of the original avatar. Native two-player G, Face and Blue
clicks verified a different remote avatar while the host stayed unchanged.
The original 1-player PC PIE settings were restored. Reports stay local in
`Saved/Customization`; new avatar art/rig authoring and physical mobile device
validation remain separate work.

## Verification

- Build the editor and run `TownAge` automation, including
  `TownAge.Customization.HairPalette` for supported/invalid palette indices.
- Register `verify_customization.py` before standalone PIE in the village. It
  enters through the real door, opens the vanity, checks a separate preview level
  and changing Idle pose, all four live/preview material tints, movement gating,
  invalid index rejection, close cleanup and reopen after GC. It exports four
  preview captures and leaves the red preview open for review.
- Verify actual G opening and native chip/Close input. For remote client evidence,
  use native input outside Python; Unreal's editor Python guard localizes RPCs.
- Check PC and landscape touch layouts, shared-world isolation, material mask
  edges around face/leaf/clothing, and appearance replication. Physical
  Android/iOS packages/device performance are separate checks.

Verified locally: editor build/UHT; 13 TownAge automation tests; the complete
standalone flow including all four preview/live tints, changing Idle poses,
frozen live pawn, close/unload/GC/reopen; native remote-client G, Blue chip and
Close in two-player listen-server PIE. The remote dye reached the authority and
replicated back, the host's position/appearance stayed unchanged, and the preview
existed only in the participating client. PC PIE settings were restored after
testing. Native captures confirm facial colors stay intact with the final
resident mask and non-temporal capture settings. Reports and captures remain in
`Saved/Customization`. Physical mobile devices, shipping packages, network loss
and save/account persistence were not tested.
