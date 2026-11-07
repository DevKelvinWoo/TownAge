# TownAge Project Context

## Product vision

TownAge is a cozy Unreal Engine game about charming characters cultivating and improving a village together. The intended emotional tone is warm, peaceful, playful, and restorative.

## Core pillars

- Village building and gradual community growth
- Nature, ecology, changing vegetation, and a living environment
- Farming, gathering, crafting, decorating, and everyday life simulation
- Cute characters, social interaction, and relaxing repeatable routines
- Multiplayer support as a first-class requirement
- Mobile (Android/iOS) and PC cross-platform development, with Steam as the PC release target

## Genre boundaries

- TownAge is not a combat-first MMORPG.
- Combat, if introduced, must remain secondary to village life, nature, farming, social play, and healing gameplay.
- The Sims, Animal Crossing, and Coral Island are useful genre and mood references, not designs to copy.

## Engineering implications

- Design every gameplay feature for both keyboard/mouse and touch input. Account for landscape phone/tablet aspect ratios, usable touch targets, safe margins, mobile GPU/memory budgets, and shared server-authoritative multiplayer logic.
- A Windows build or touch preview is not proof of an Android/iOS package or device performance. Report SDK/package/device verification separately.

- Consider multiplayer authority, replication, session flow, persistence, and save synchronization when designing gameplay systems.
- Avoid single-player-only shortcuts that would make later multiplayer conversion expensive.
- Keep Steam distribution, online services, controller and keyboard/mouse input, performance, achievements, localization, and packaging constraints in mind.
- Prefer systems that support calm co-operative play and player expression over competitive power progression.

## Default working level

- Open `/Game/Maps/L_CharacterTest` for ordinary project work and character tests.
- The test level uses `ATownAgeGameMode`, which spawns the controllable `ATownAgePlayer` at PlayerStart during Play.
- `ATownAgePlayer` uses the Meshy character under `/Game/Characters/Meshy/TownKeeper_Meshy/candidate_v001`, screen-relative WASD movement and the fixed cozy camera. Its native single-node AnimInstance evaluates Idle/Walk/Run through `Animations/Locomotion01/BS_TownKeeper_Meshy_Locomotion` from actual planar velocity. The zero-speed sample is the calm4second Idle, not the legacy.033second static pose. Smooth sample weights once in the Blend Space; do not add a second velocity filter. Moving-state hysteresis enters above4cm/s and exits at2cm/s.
- Walking speed is87cm/s and sprint speed304cm/s, matched to the supplied Meshy cycles. The previous accelerated-walk sprint fallback is retired. Meshy hair/pouch automatic-skin deformation remains a known limitation; the user requested applying the available clips without further deep repair.
- Hold Shift with movement to sprint. Stamina is server-authoritative: capacity 100, drain 20/s, regeneration 15/s after 1.5 seconds without sprinting, exhaustion unlock at 20. `ATownAgeHUD` shows a plain single-color stamina ring beside the character only while Shift is held.
- This is the editor startup map and the current game default map.

## 3D asset production pipeline — Meshy default

- Use `$townage-meshy` for new character/prop generation and Meshy handoff. Its repository source is `Tools/Skills/townage-meshy/SKILL.md`; operational commands are in `Tools/Meshy/README.md`.
- Default route: approved reference image -> Meshy image/text-to-3D -> visual candidate review when direction is needed -> mobile-budget remesh -> character rigging -> local FBX/textures/manifest -> isolated Unreal candidate -> verification before requested production replacement.
- Use ImageGen when new concept art is requested. Show a new or materially changed reference and wait for explicit art direction/approval before generation. Reuse an already approved version without asking again; a direct instruction to model a supplied image approves that input.
- Meshy is the production generation default. Do not fall back to GPT-authored primitive/loft or procedural Blender modeling unless the user explicitly asks for that route. `$townage-character` remains available for explicitly requested Blender authoring/repair.
- Keep `MESHY_API_KEY` only in the local environment. Never put it in chat, request files, committed configuration or logs. Setup/check requests do not authorize paid generation. Bound paid attempts, persist task IDs/receipts locally and reconcile ambiguous submissions instead of blindly retrying.
- Remesh against a stated PC/mobile triangle/material/texture budget, then rig animation-ready characters. Keep source references, FBX, textures and task provenance local. When animation is out of scope, do not submit animation jobs or import optional example clips.
- Import into versioned folders under `/Game/Characters/Meshy`; the candidate importer must not overwrite production characters, maps or the playable pawn. Verify actual appearance, normals, placed size, skeleton/weights and performance assumptions first. Meshy skeletons may require explicit animation retargeting.
- Current main-character brief remains a long-haired female with TownAge's cute, rounded, cozy style. This records art direction only; pipeline setup does not start generating that character.

## Locomotion animation pipeline

- Use the installed `$townage-locomotion` skill for movement-animation creation, polishing and integration. Repository source: `Tools/Skills/townage-locomotion/SKILL.md`.
- Default sequence: motion brief and rig check -> Blender Idle/Walk/Sprint drafts -> show looping previews and wait for explicit user direction/approval -> polish and bake in-place clips -> Unreal Blend Space/Anim Blueprint -> PC/mobile/multiplayer verification.
- Reuse approved character art and stable skeleton names. Do not begin final polish or production integration before the motion draft is approved. Existing approval of the same draft remains valid.

## Feature commits and publishing

- Once a feature is complete and verified, commit and push its code/configuration/documentation as a focused feature commit using the Lore message format.
- Do not stage or push game/art assets: .uasset, .umap, .blend, .fbx, textures, audio, or other binary media. Keep asset edits local. Do not assume existing tracked assets are safe to include.
- Stage explicit source/config/doc paths, inspect the staged file list and diff, and check for credentials before committing. No git add-all for feature publication.
- Preserve unrelated pending work. Do not erase Git history or untrack existing assets without a separate request.

When requirements are ambiguous, reinforce the cozy village-life vision and preserve mobile/PC cross-platform, multiplayer, and Steam compatibility.
