# CozyHouse01 door traversal

The approved DoorDraft01 motions are used for a synchronized push/enter and
pull/exit sequence. Both leafs swing toward the interior. First/last clip poses
ease into the existing calm Idle over 0.2s; the native single-node proxy blends
asset changes over 0.22s, including interrupted transitions.

## Source and authoring

- `prepare_door_assets.py` runs in Blender background mode. It preserves the
  approved 24-bone rig, rest pose and skin; removes preview object displacement;
  bakes only the chosen deform take; exports with the original bind carrier;
  and verifies every-frame FBX roundtrip, source size, fixed root XY and Idle
  endpoints. Deliveries are local in `ArtSource/Meshy/TownKeeper_Meshy/Animations/Door01`.
- The local `ArtSource/Meshy/CozyHouse01/candidate_v003` contains a hinge-local
  leaf with the inside handle and a separate static arch for the gray room.
  Previous house/model deliveries are retained.
- `create_gray_interior.py` creates only a new isolated gray map. It refuses an
  existing map by default. `-ResumeGrayRoom` is limited to repairing this tool's
  own incomplete room; do not use it to regenerate a finished edited room.
- After building `TownAgeEditor`, run `setup_door_travel.py` through Unreal Python
  with conflicting interactive packages closed. It backs up the village, room,
  house BP and interaction table under `Saved/Doors/Integration/backups`, imports
  only animations onto the retained Skeleton, updates the owned portals, and
  saves the persistent village explicitly after adding the streaming room.
  `-DoorReimport` refreshes the named door candidate files; default reruns reuse
  existing imported candidates.

Data rows `DoorEnter` and `DoorExit` in `Tools/Interaction/Interactions.csv` select
the common `DoorTransition` action. `DoorInspect` remains a log-only fixture.
Portal component properties hold the server-authored anchors, destination,
animation, room package, timing and shared `PortalId`. Client requests never
provide an arbitrary destination or package name.

## Runtime

`L_VillageTerrain_01` stays the persistent world. The small
`/Game/Maps/Interiors/L_CozyHouse01_Gray` is a cached streaming sublevel at
`(50000,0,0)`cm. Only the participating pawn transfers; other village players
keep their world and session. This prototype deliberately caches the tiny room
for server/clients rather than claiming per-client unloading. There is no extra
PlayerStart in the sublevel to interfere with village spawning.

`UTownAgeDoorPortalComponent` identifies each side. A world-scoped reservation
locks both sides, with a replicated reserved bit independent of participant
relevancy. The two portal owners are always relevant for this prototype. Their
replicated clock drives local hinge yaw; skeletal poses are not replicated.

`UTownAgeDoorTraversalComponent` advances Align -> Action -> WaitReady -> Closing
-> Idle on authority. Root-motion sources move the capsule for alignment, the
short weight-transfer step, and threshold crossing. Hand/leaf timing derives
from server time, not client animation notifies. The server waits for the room
and the owning connection's initialized level before committing the transfer.
Timeout, blocked paths, destroyed portals or disconnect cancel safely and
release the reservation. Only the participant ignores the moving leaf; house
and frame collision remain in force.

Movement, sprint and repeated interaction are gated while busy. Touch states
are still sampled so a held disabled button cannot turn into a fresh press on
completion. Locomotion still follows velocity during Align/Closing; the action
owns animation only during Action/WaitReady. A brief local fade hides transfer;
camera lag is reset across the 500m move and previous camera flags are restored.

`UTownAgeDoorAnimInstance` is a native subclass of `UAnimSingleNodeInstance`,
hosted via `SetAnimInstanceClass` (the mesh mode is AnimationBlueprint, without
an Anim Blueprint asset). Access it through `GetAnimInstance()` and call
`SetAnimationAsset` directly. Calling mesh `SetAnimationMode`/`SetAnimation`, or
relying on `GetSingleNodeInstance()`, would replace/bypass this smooth proxy.
The existing Blend Space remains responsible for its one locomotion sample
filter; the new proxy only blends discrete asset changes and retains current
curves/attributes. Portal clips have a strong transient cache for cooked/runtime GC.

## Validation

- Build the editor and run `Automation RunTests TownAge` (door curve/order,
  interaction selection, touch regions and stamina).
- Register `verify_door_runtime.py` in a GPU editor and start standalone PIE. It
  checks streamed-floor collision/offset, enter/exit, Idle restoration, GC,
  movement restoration, and destroyed-portal cancellation. It destroys only the
  transient PIE house; restart PIE afterward for a clean user review.
- Validate native G/touch and two-player enter/exit. The remote player must
  remain stable after transfer while the other player stays in the village.
  Use native input for RPC evidence: this engine's Python ProcessEvent editor
  guard forces client RPC callspace to local.
- Check slow/missing-room and blocked paths, camera/input restoration and
  reservation release. Reports, pose samples and screenshots stay under
  `Saved/Doors/Integration`; physical Android/iOS packaging/device tests are separate.
- `verify_door_lifetime.py` can run in the same two-player session after return.
  It prepares a native client G request, destroys the authoritative participant
  during the action, and verifies the other player can use the released door.
  This tests pawn EndPlay cleanup, not a transport-level connection drop.

Local validation passed: editor build/UHT; five TownAge automation tests;
standalone enter/exit, streamed-floor collision and grounded return, locomotion
restoration and portal-destruction rollback; real remote G enter and simulated
touch exit with the other player remaining in the village; post-transfer client
position stability; animation after GC; and participant EndPlay reservation cleanup.
Packet loss/latency injection and physical mobile devices were not tested.

Only source, source datasets and documentation are published. Models, clips,
textures, imported assets and levels remain local.
