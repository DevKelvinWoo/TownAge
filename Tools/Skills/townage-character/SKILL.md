---
name: townage-character
description: Create, polish, rig, and integrate TownAge 3D characters using reference art, Blender MCP, and Unreal MCP. Use for new character modeling or reference-driven character revisions, including animation-ready assets and placement Blueprints.
---

# TownAge character production

Use the project's AGENTS.md for the cozy village-life direction, multiplayer constraints, and active test level. Follow the user's stopping point and animation scope.

## Reference and modeling

For a new design, use the available ImageGen skill/tool for an original consistent front/side/back turnaround and beauty view. For revisions preserve the existing reference and identity. Save references under ArtSource/Characters/<character>/.

### Required user art-direction checkpoint

After generating or materially revising concept art, show the actual images to the user with a brief description of the design and ask for their direction or approval to model that specific version. End the turn and wait for the user's response so they can personally judge the art. Do not start Blender modeling, blockouts, rigging, modeling scripts, or Unreal asset creation during this waiting stage.

Time passing, silence, an automatically selected option, or the original general request to create a character is not concept approval. If the user gives art changes, revise the concept and present it again for review. Begin modeling only after an explicit instruction such as "이 원화로 모델링 진행해" or equivalent approval of the shown version. Record the approved reference path/version and the user's art direction before proceeding.

An existing reference that the user has already reviewed and explicitly approved for modeling satisfies this checkpoint; do not ask for the same approval again. Approval remains valid for polishing that follows the approved design. A material redesign requires a new concept review.

Inspect the reference and current model before editing. Measure head/body ratio, silhouette, facial placement, hair flow, garment volume, hands and boots. Use shaped continuous surfaces where deformation or silhouette requires them. A visibly intersecting collection of primitive shapes is a blockout, not a finished character.

Use Blender MCP to author and inspect the actual scene. Preserve editable .blend files and reproducible build/bake/export scripts. Work in a dedicated scene or explicit target collection so existing user scenes survive. Keep a candidate separate until verified.

Render comparable front, side, back and beauty views. Inspect every view for scalp holes, garment intersections, jagged cuffs and disconnected hands. Record concrete differences and revise. Do not substitute a numeric pass or successful compilation for visual fidelity. If the user stops polishing, describe remaining differences honestly.

## Materials and rig

Bake Blender procedural materials into actual UV-mapped base color, roughness and tangent normal images for Unreal. FBX does not transfer shader graphs. Match the reference palette and subtle cloth/leather grain while controlling plastic-like reflections. Prefer manageable atlas/material counts without sacrificing face texel density.

For animation-ready delivery use a neutral A-pose, stable named hierarchy, normalized weights and clean transforms. Temporarily bend elbows/knees to inspect joints, then restore rest pose. Do not create clips or keyframes unless animations are requested. Disclose rigid segmented weights if still present.

Before exporting read [references/engine-verification.md](references/engine-verification.md). Run scripts/inspect_blender_character.py inside Blender through MCP with CHARACTER_MESH_NAME set to the explicit target. It inspects without editing; the report is technical evidence, not artistic approval.

## Unreal integration

Discover live toolsets and schemas. Prefer supported SkeletalMesh/Texture/Material/Blueprint tools. A headless Unreal Python task is a fallback for reimports or missing operations; save/close the interactive editor before conflicting writes, then reopen the working level.

Import without clips when animation is out of scope. Retain compatible skeleton/physics assets, explicitly connect texture maps, and produce or update a placement BP. Use Character/Pawn when gameplay control is requested. Preserve stable production asset paths referenced by code and maps.

Verify actual Unreal front/side/back rendering and a newly placed Actor at scale 1. Source renders alone do not prove engine correctness. Save/reload the test level; preserve user placements and unsaved work.

Retain the final .blend, FBX, textures, reference, scripts, manifest and engine assets. When cleanup is requested, inspect package referencers before removing old versions. Archive outside Content to a scoped ignored path and report recovery location. Preserve helpers used by final scripts. Do not silently rename production paths or remove referenced skeletons.

Report preview, source and BP paths, measured size, rig/animation status, tests and remaining defects. Publishing to Git follows user instructions; skill invocation alone does not authorize a push.
