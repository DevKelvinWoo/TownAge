---
name: townage-locomotion
description: Create, polish, export and integrate TownAge locomotion animations using Blender MCP and Unreal MCP, with user review of motion drafts. Use for idle, walk, sprint and movement-transition animation requests; use townage-character for character modeling or redesign.
---

# TownAge locomotion production

Read the project's AGENTS.md and inspect the active character, movement code and skeleton before working. This pipeline targets cozy village-life movement shared by PC and mobile, with server-authoritative CharacterMovement. Preserve approved character appearance and existing user work.

## 1. Motion brief and rig preflight

Establish requested clips and the intended personality: relaxed short steps, restrained body bounce and soft arm swing are TownAge defaults. Start with Idle, Walk and Sprint unless the user requests another scope. Start/stop and turn clips follow a stable core set; do not silently expand to an eight-direction library.

Inspect actual source and Unreal bone names, reference pose, units, mesh orientation and current gameplay speeds. Current defaults are walking 260cm/s and sprinting 440cm/s; read code rather than assuming these values remain fixed. Reuse the approved character reference, without regenerating its concept art.

Check the shoulders, hips/crotch, knees, ankles/boots and satchel through representative movement ranges. A prior 25-degree joint test alone does not establish walking readiness. Correct limited skin weights as needed; material character redesign returns to the townage-character reference approval stage. Do not add deform bones or change the production skeleton hierarchy as an incidental animation edit.

Add separate authoring controls for foot IK/poles, pelvis and arm/head posing when useful. Export baked deform bones, not control objects. Preserve root names, rest transforms, skin and existing compatible skeleton/physics assets.

## 2. Draft clips and required user direction checkpoint

Build a first readable draft on the actual rig using contact, down, passing and up poses, their mirrored phases and appropriate interpolation. Work in a separate animation source file or versioned Actions so the final model and existing Actions are not overwritten. Simple periodic rotation curves can seed a blockout but do not qualify as a polished gait.

Show short looping Idle/Walk/Sprint videos or animated previews from the side, front and gameplay camera. Describe cadence, stride, body bounce and arm swing. **End the turn and wait for the user to direct and explicitly approve the shown motion version before polishing, final export or production Unreal integration.** A general request to create animations, silence or elapsed time is not draft approval.

When feedback changes a draft, revise and present it again. Record the approved draft version and directions. Existing explicit approval of the same motion version remains valid for faithful polish; do not ask repeatedly. Follow an explicit user instruction to change or stop the checkpoint/process.

## 3. Polish the approved motion

Inspect foot planting/sliding, toe clearance, knee direction, hip and shoulder timing, balance, hand/satchel/body collisions, hair clearance and loop continuity. Keep a calm character personality without removing believable weight transfer.

Use in-place clips for basic locomotion: CharacterMovement controls displacement, and the root remains fixed horizontally. A planted foot moves backward relative to the character during stance to cancel the actor's forward travel; freezing its local position would cause sliding. Match stride per cycle divided by cycle duration to the clip's intended movement speed. If the gameplay speed makes the desired gait implausible, present the tradeoff before changing movement tuning.

Use a shared left/right contact phase for walk and sprint. First/last poses and interpolation should loop without a pause or snap; avoid a duplicated endpoint that adds unintended dwell. Preview slow motion and repeated cycles, not only selected stills. Start with baked 30fps clips and adjust sampling only for demonstrated quality needs.

## 4. Export and engine integration

Before exporting or reimporting, read [references/engine-handoff.md](references/engine-handoff.md). Bake authoring constraints to the deform hierarchy in explicit clip ranges. Export only intended animation takes; exclude unrelated Actions/NLA strips and avoid resaving a posed reference mesh as its new rest pose.

Discover live Unreal toolsets and input schemas. Use Blender MCP for Actions/keyframes/baking and Unreal MCP for asset import, graph authoring and PIE inspection. Local scripts or Unreal Python tasks are fallbacks for missing operations; preserve unsaved editor work before restart or conflicting writes. Tool catalog presence alone is not a live-connection test.

Import AnimSequences against the existing Skeleton without replacing the approved Skeletal Mesh or updating its reference pose. Configure looping and compatible compression. Build a speed-based 1D Blend Space for the current rotate-to-movement controller, and an Anim Blueprint using actual planar velocity and grounded/falling state. Use state transitions for distinct behavior as needed. Do not drive walk/run solely from Shift or a touch button: blocked movement and remote players must remain correct.

Place related cycles in a Locomotion Sync Group with matching left/right foot-contact markers. Tune speed interpolation and thresholds to avoid idle jitter and acceleration/deceleration pops. Recompute animation state from each client's movement data; do not replicate a frame-by-frame animation phase or each bone transform for ordinary walking. Keep gameplay movement/stamina authority separate from cosmetic animation.

## 5. Validate and deliver

Read [references/play-validation.md](references/play-validation.md) before final verification. Test the active level, normally /Game/Maps/L_CharacterTest. Inspect the actual spawned playable character as well as placement previews; assigning an Anim Blueprint only to a decorative Actor does not finish integration.

Prefer baked animation for baseline mobile runtime. Add live foot IK/Control Rig, pose warping or motion matching only when a concrete requirement justifies their cost. Measure animation updates, compression, LOD and multiple-character behavior. A Windows touch preview is not Android/iOS packaging or device-performance verification.

Keep editable animation .blend files, bake/export helpers, approved preview references and a manifest with skeleton identity, clips, frame ranges, fps, intended speeds and root-motion policy. Preserve runtime code changes as focused Lore commits when tested, then push per AGENTS.md. Animation FBX, .blend, movies, textures, .uasset and .umap remain local; stage explicit code/doc paths only.

Report clip previews, approved version, local asset/Anim Blueprint paths, actual tests and unresolved defects. Do not claim visual completion from a numeric score or successful compilation. Honor user stop requests after finishing the authorized current pass and saving reviewable results.
