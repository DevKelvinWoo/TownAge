# Cosmetic modules and makeup art direction

The station UI has Dye, Surgery and Makeup categories. Dye uses the full-body
portrait; Surgery and Makeup use the face camera. Surgery is a future module,
not a geometry editor in this revision. Stations can grant categories separately
so a future salon or clinic can reuse the same services without a vanity actor.

## Research translated into the stylized face

- **Blush:** a soft wash over the apples/high part of the cheek, feathered into
  surrounding skin. The model already has baked cheek color, so the added layer
  must remain sheer. Reference: [Bobbi Brown blush basics](https://www.bobbibrowncosmetics.com/how-to-blush-basics).
- **Eyeliner:** define the upper lash edge with a thin, soft dark-brown line and
  a restrained outer lift. Avoid large solid wings over this character's already
  bold lashes. Reference: [Charlotte Tilbury eyeliner guide](https://www.charlottetilbury.com/ca/secrets/guide-to-eyeliners-find-best-eyeliner).
- **Lens/iris color:** recolor the iris area while preserving the pupil, white
  catchlights and sclera. This is a material effect for the avatar, not a physical
  contact-lens simulation. Brown, hazel and muted sage/blue-gray options should
  retain the original eye's depth.
- **Aegyo sal:** a narrow, gentle highlight below the lower lid paired with a
  faint shadow below that fullness. It should look like a soft under-eye volume,
  not a dark circle or a white stripe. Reference: [THEFACESHOP dual under-eye maker](https://au.thefaceshop.com/products/eye-rise-dual-under-eye-maker).
- **Jaw contour:** cool neutral shading softly blended around the lower jaw
  perimeter. The center of the chin remains clear; the effect does not move
  vertices or change the silhouette.
- **Nose contour:** softly shade the sides of the bridge and below the tip,
  avoiding hard parallel bars. Reference for jaw and nose: [Charlotte Tilbury contour guide](https://www.charlottetilbury.com/us/secrets/how-to-contour).

These are art-direction interpretations of the sources, adapted to TownAge's
rounded, already-painted face. Effects start at zero and remain independently
adjustable. A conservative Natural preset offers a coherent starting point.
The original baked makeup remains when additional layers are disabled.

## Runtime modules and station reuse

`UTownAgeDyeModule`, `UTownAgeMakeupModule` and `UTownAgeSurgeryModule` are
independent appearance services. `UTownAgeCustomizationComponent` owns the
session, camera and replicated appearance; the widget only emits choices.
`AllowedCosmeticCategories` on the common interaction target grants Dye=1,
Surgery=2 and Makeup=4. The current vanity grants7. A future salon can grant1,
clinic2 or makeup station4, using the same action and UI without vanity logic.
The authority checks the session, target, category and bounded state on every
choice. Slider changes update during dragging at up to10Hz, and release flushes
the final value. Acknowledgments do not overwrite an actively dragged value.

## Visible strength and comparison

The0–100 data range remains unchanged. The original implementation applied
slider changes only after release and its shader gains were too conservative.
A native blush drag30→100 reached both live/preview materials as0.3→1.0;
frozen-pose pixel captures also proved all six effects rendered, but weakly.
Repeated zero captures were identical, separating effect changes from Idle
motion or lighting noise.

Each shader blend now uses `soft*s + (strong-soft)*s^4`, then clamps the masked
alpha to0–1. This preserves the Natural preset's low range while making the
upper range deliberately stronger. Aegyo highlight uses a screen lift that
always brightens. The liner has a softly widened connected edge, and contour
masks exclude neck/scarf pixels.

**강하게 비교** selects strengths100 with coral blush and blue-gray iris.
Holding **원본 보기** displays zero additional layers only in the preview;
the authoritative appearance and live pawn stay unchanged. Release restores the
latest selected makeup. Category changes and close clear the comparison state.

Run `verify_makeup_pixels.py` in an open standalone session for frozen-pose
zero/100 captures, actual material values, hold/release isolation and category
reset checks. Timestamped captures remain in
`Saved/Customization/Makeup/SliderAudit`. These are comparisons of additional
layers, so the original painted cheek color and lashes remain in the baseline.

Native pixel audit after the fix: repeated zeros are identical. Mean0/100
pixel change increased3.68x overall (changed pixels over4/255:24,499→50,036).
Per-effect mean gains: blush2.82x, liner5.65x, iris2.22x, aegyo3.75x,
jaw5.00x, nose4.86x. Holding Original matches zero exactly; releasing matches
the selected100 image exactly while the live/state values stay100. Contour
masks protect the lower neck/scarf and fill only safe unused UV gutters.
Reports and the aligned native comparison are local in the timestamped
`SliderAudit` run directories. Build/UHT and all14 TownAge tests pass.

For another avatar, author its own combined hair/makeup material with the same
parameter interface and its own masks. Do not assign a dye-only override to an
avatar that needs both services; its `HairDyeMaterials` override should reference
the combined parent. Unsupported meshes keep their own material unchanged.

Run `makeup_masks.py` in isolated Blender, then `makeup_material_setup.py` in
Unreal Python. The latter backs up owned packages and creates a separate parent
`/Game/Characters/Customization/M_TownKeeper_Makeup`; original materials and
geometry remain untouched. Packed masks reload from PNG to verify independent
RGBA channels, and exclude retained hair/nonface texels. Both masks are resident
2048px data textures without coarse mips, preserving packed UV boundaries.

Verified: editor build/UHT; 14 TownAge automation tests including makeup bounds;
category-driven camera, six matching live/preview shader amounts, hair retention,
reset, close/reopen, invalid-value rejection and makeup-only station permission.
Native remote G, Dye, Makeup and Natural preset clicks replicated to the server
and owning client while the host's appearance stayed unchanged. All six rows
were reachable in the small client window. Physical Android/iOS devices,
shipping packages and cross-session/account persistence were not tested.

## Assets and material interface

The retained rig/geometry supports these surface effects; no new model or Meshy
generation is authorized or needed for this implementation. Artist-authored new
avatars require their own UV masks/material mapping. Never apply TownKeeper
face masks to another avatar merely because it shares a skeleton.

The makeup material preserves the hair dye branch and original normal/roughness.
The intended packed channels are:

| Texture | R | G | B | A |
| --- | --- | --- | --- | --- |
| Makeup A | Blush | Upper lash line | Iris | Aegyo highlight |
| Makeup B | Aegyo shadow | Jaw contour | Nose contour | Face skin |

Parameters: `BlushTint`, `BlushAmount`, `LinerAmount`, `IrisTint`, `IrisAmount`,
`AegyoAmount`, `JawAmount`, `NoseAmount`, alongside existing `HairTint` and
`DyeStrength`. Amounts are normalized scalars in the shader; network state uses
bounded byte values. Soft masks must not affect hair, clothing, pupil or eye
highlights. Generated masks, candidate materials, captures and model sources
remain local; only reproducible scripts, code and documentation are published.
