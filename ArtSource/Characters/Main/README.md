# Legacy TownKeeper character source

The active main character is now the Meshy delivery in `ArtSource/Meshy/TownKeeper_Meshy/candidate_v001`, with Standing/Walk/Run under its Unreal `Animations/Locomotion01` folder. This page describes the retained legacy Revision05 source for recovery; do not restore it as the native player by following old paths below. The stable placement Actor remains `/Game/Characters/Main/TownKeeper/BP_TownKeeper` and now shows the Meshy character.

The current source includes packed atlas textures and centimeter-scale FBX. Revision05 adds forearm-relative relaxed hands, shorter body proportions and a convex face profile, while retaining the approved outfit and identity. Earlier source revisions remain local for recovery. The original cleanup archive is `Saved/AssetArchive/CharacterCleanup-20261107/`.

The ten superseded Revision04 engine assets and earlier walk assets were audited for external referencers, then moved outside Content to `Saved/AssetArchive/Revision05-Replaced-20261107/`. The stable placement Blueprint and test map were retained.

## Source files

- `CHR_Main_TownKeeper_Turnaround.png`: production reference sheet
- `Revision05/TownKeeper_Reference05.blend`: editable final source
- `Revision05/SK_TownKeeper_Reference05.fbx`: animation-free skeletal FBX
- `Revision05/`: final color, roughness, DirectX normal maps and comparable previews
- `Revision05/TownKeeper_Animation05.blend`: compatible standing and approved walk actions
- `Tools/Character/`: build, bake, adaptation, export, inspection and import scripts

The Revision05 scripts reuse `build_reference03.py`, `bake_reference03.py` and the approved `Tools/Animation` walk builders. Retain these shared implementations despite their historical names. Run `build_revision05.py`, `bake_revision05.py`, `adapt_revision05_walk.py`, `export_revision05_animations.py`, then `verify_revision05_pose.py` on the animation file and `verify_revision05.py` on the model file before Unreal import. The last check runs the skill inspector, roundtrips the FBX and assembles the handoff manifest. Run these Blender scripts in isolated Blender processes, opening the appropriate source file for baking and inspection. Save and close Unreal before commandlet writes. `verify_revision05_runtime.py` registers the final live PIE movement check without changing the saved map.

## Unreal destination

`/Game/Characters/Main/TownKeeper/FinalCharacter05`

The import creates the Skeletal Mesh, compatible Skeleton, Physics Asset, atlas material and textures. Its `Animations` subfolder contains the standing support pose, adapted approved walk and `BS_TownKeeper_Walk`. The stable placement Blueprint and native player both use the current mesh. The editor's placed preview Actor is hidden during play so GameMode spawns the sole controllable character.

## Animation readiness

- Neutral A-pose
- Unreal-friendly named bone hierarchy
- Normalized weights with blended limb joints; fine finger/facial rigs remain future work
- Dedicated root, pelvis, spine, neck, head, arm, hand, leg, and foot bones
- Approved 28-frame in-place walk and static standing support clip, adapted to the shorter limbs

Future animation work should preserve the current skeleton and may add Control Rig, IK Retargeter, sockets, facial morphs, and refined deformation weights as needed. Bone names alone do not make older reference poses compatible. IdleDraft01 remains an unapproved draft on the earlier proportions; it is not the active standing animation. Sprint currently uses the existing capped walk fallback, not a new sprint clip. Mobile device performance and production LODs remain separate validation work.
