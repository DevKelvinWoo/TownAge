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

When requirements are ambiguous, choose the interpretation that best reinforces the cozy village-life vision and preserves multiplayer and Steam compatibility.
