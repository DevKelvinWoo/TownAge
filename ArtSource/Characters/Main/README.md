# TownKeeper Character Source

The TownKeeper is the first main-character model for TownAge. It follows the project's cozy, original village-life style and is not a copy of an existing game character.

## Source files

- `CHR_Main_TownKeeper_Turnaround.png`: generated production reference sheet
- `build_townkeeper.py`: reproducible Blender build and export script
- `CHR_Main_TownKeeper.blend`: editable Blender source with mesh and armature
- `SK_TownKeeper.fbx`: animation-free skeletal FBX exported for Unreal Engine
- `CHR_Main_TownKeeper_Preview.png`: approved Blender preview render

## Unreal destination

`/Game/Characters/Main/TownKeeper`

The import creates the Skeletal Mesh, Skeleton, Physics Asset, and material assets. No animation sequence is included at this stage.

## Animation readiness

- Neutral A-pose
- Unreal-friendly named bone hierarchy
- Rigid vertex groups for the current stylized segmented body
- Dedicated root, pelvis, spine, neck, head, arm, hand, leg, and foot bones
- No baked animation clips

Future animation work should preserve the existing skeleton and may add Control Rig, IK Retargeter, sockets, facial morphs, and refined deformation weights as needed.
