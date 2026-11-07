# Export and engine checks

- Recalculate consistent outward face normals for custom rings/lofts. Blender's two-sided appearance can hide inward faces that Unreal culls, exposing the head interior. Inspect actual single-sided engine rendering. Two-sided material is not a replacement for repairing a closed head.
- Validate scale with FBX roundtrip, native Unreal bounds and a placed Actor. TownKeeper target is170cm unless overridden. For numeric centimeter geometry with Blender scale_length=.01, apply_unit_scale=True and FBX_SCALE_NONE produce unit factor1. Check differently scaled source scenes separately.
- Keep mesh/armature scale1. Root mesh component scale may be overwritten by actor spawn transforms, so a100x BP correction is unreliable.
- Preserve existing skeleton root names on reimport. Blender's repeated-object suffixes can change the bone tree. Current TownKeeper export preserves Armature_008.
- Base color uses sRGB; roughness is linear. Normal maps need normalmap compression, linear sampling and matching tangent convention. Current atlas is DirectX -Y; do not invert green twice. Match texture sample sampler type to its texture.
- Reimport may change material slot names: query them again and explicitly assign the retained material. Unreal struct arrays return value copies; modify a struct and write it back into the array before assigning the array. Prefer supported material setter. Save/reload to refresh component render state.
- Current native mesh path: /Game/Characters/Main/TownKeeper/ReferenceRevision04/SK_TownKeeper_Reference. Placement BP: /Game/Characters/Main/TownKeeper/BP_TownKeeper. Future characters use their own paths.
- Current working map is /Game/Maps/L_CharacterTest. Preserve user-added actors. The controllable native player spawns during Play; a placement BP may also be present.
- Record triangle and section counts. High-detail hero meshes still need a separate LOD/performance pass for many multiplayer characters; a beauty render cannot establish performance readiness.
