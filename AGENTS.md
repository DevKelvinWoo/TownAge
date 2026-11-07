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
- `ATownAgePlayer` provides screen-relative WASD movement and a fixed cozy third-person camera. The mesh remains animation-free for now.
- Hold Shift with movement to sprint. Stamina is server-authoritative: capacity 100, drain 20/s, regeneration 15/s after 1.5 seconds without sprinting, exhaustion unlock at 20. `ATownAgeHUD` shows a plain single-color stamina ring beside the character only while Shift is held.
- This is the editor startup map and the current game default map.

## Character production pipeline

- Use the installed `$townage-character` skill for future character creation and polishing. Its repository source is `Tools/Skills/townage-character/SKILL.md`; keep installed and repository copies aligned when updating it.

- Use ImageGen for original character turnarounds and expression or outfit references.
- Present generated/revised concept art and wait for the user's explicit art direction and approval of that version before starting Blender modeling. End the turn at this review checkpoint; elapsed time or the general character request does not count as approval. Reuse an already approved reference without asking again.
- Build and refine production character meshes in Blender through Blender MCP.
- Preserve reproducible Blender build scripts and source `.blend` files alongside exported FBX files.
- Use a shared, Unreal-friendly skeleton and modular materials or parts wherever possible.
- Import and validate Skeletal Mesh, Skeleton, Physics Asset, materials, and later animation assets through Unreal MCP.
- Meshy may be used for prototypes or inspiration, but not as the default source for production character topology.
- When animation is out of scope, export no animation clips while retaining an A-pose, skinned mesh, named bone hierarchy, and physics-ready structure.

## Feature commits and publishing

- Once a feature is complete and verified, commit and push its code/configuration/documentation as a focused feature commit using the Lore message format.
- Do not stage or push game/art assets: .uasset, .umap, .blend, .fbx, textures, audio, or other binary media. Keep asset edits local. Do not assume existing tracked assets are safe to include.
- Stage explicit source/config/doc paths, inspect the staged file list and diff, and check for credentials before committing. No git add-all for feature publication.
- Preserve unrelated pending work. Do not erase Git history or untrack existing assets without a separate request.

When requirements are ambiguous, reinforce the cozy village-life vision and preserve mobile/PC cross-platform, multiplayer, and Steam compatibility.
