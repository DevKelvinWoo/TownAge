# TownAge Project Context

## Product vision

TownAge is a cozy Unreal Engine game about charming characters cultivating and improving a village together. The intended emotional tone is warm, peaceful, playful, and restorative.

## Core pillars

- Village building and gradual community growth
- Nature, ecology, changing vegetation, and a living environment
- Farming, gathering, crafting, decorating, and everyday life simulation
- Cute characters, social interaction, and relaxing repeatable routines
- Multiplayer support as a first-class requirement
- PC release on Steam as the final shipping target

## Genre boundaries

- TownAge is not a combat-first MMORPG.
- Combat, if introduced, must remain secondary to village life, nature, farming, social play, and healing gameplay.
- The Sims, Animal Crossing, and Coral Island are useful genre and mood references, not designs to copy.

## Engineering implications

- Consider multiplayer authority, replication, session flow, persistence, and save synchronization when designing gameplay systems.
- Avoid single-player-only shortcuts that would make later multiplayer conversion expensive.
- Keep Steam distribution, online services, controller and keyboard/mouse input, performance, achievements, localization, and packaging constraints in mind.
- Prefer systems that support calm co-operative play and player expression over competitive power progression.

## Character production pipeline

- Use ImageGen for original character turnarounds and expression or outfit references.
- Build and refine production character meshes in Blender through Blender MCP.
- Preserve reproducible Blender build scripts and source `.blend` files alongside exported FBX files.
- Use a shared, Unreal-friendly skeleton and modular materials or parts wherever possible.
- Import and validate Skeletal Mesh, Skeleton, Physics Asset, materials, and later animation assets through Unreal MCP.
- Meshy may be used for prototypes or inspiration, but not as the default source for production character topology.
- When animation is out of scope, export no animation clips while retaining an A-pose, skinned mesh, named bone hierarchy, and physics-ready structure.

When requirements are ambiguous, choose the interpretation that best reinforces the cozy village-life vision and preserves multiplayer and Steam compatibility.
