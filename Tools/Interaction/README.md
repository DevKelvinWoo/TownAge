# Interaction prototype

The cottage door currently executes a server-side log only. It does not open or
play an animation. `G` and the mobile circular `USE` button share the same request
path. The PC prompt appears above the selected target; mobile keeps the button
visible in a disabled state when no interaction is available. A touch is consumed
on press, so holding a disabled button cannot later trigger an action.

## Authoring

`Interactions.csv` is the source for `/Game/Data/Interactions/DT_Interactions`,
whose row struct is `FTownAgeInteractionRow`. Each row provides prompt text,
planar range, vertical tolerance, maximum facing angle, action and log event.
Run `setup_interaction.py` through Unreal Python after building the editor. It
imports this table and attaches `DoorInteraction` to the existing split-house BP
in `L_VillageTerrain_01`, backing up that BP and the level before mutation. It
preserves the house placement, independent door meshes and PlayerStart.

To author another target, add `TownAgeInteractionTargetComponent` to its actor,
assign a table row and set `LocalInteractionPoint`. Keep the actor replicated.
An optional `LocalApproachDirection` restricts use to the front half-space of
the target point; zero allows approach from every side. The cottage uses +Y.
`bInteractionEnabled` is replicated. Set it on the authority when gameplay
enables/disables the target.

To implement subsequent doors, chests, NPCs or gathering, extend the action enum
and native dispatcher, or subclass the target component and override the
authority-only `ExecuteInteraction` event. Keep eligibility and server validation
in the common component. The current data contains only the implemented door
log action; other gameplay behaviors are not implied by placeholder rows.

## Selection and authority

Targets register in a world-scoped weak registry during BeginPlay and unregister
on EndPlay. Local selection refreshes at 20Hz. Within each row's range, vertical,
approach and facing limits, the greatest planar forward dot wins: the smallest
angle to the character's forward vector has priority over distance. Distance and
component path break ties. Camera angle does not affect selection.

The player's replicated interaction component sends the selected target through
an owned Server RPC. The server reselects from its own registry and rejects a
different, disabled, destroyed or ineligible target; requests are rate-limited to
one per 0.2 seconds. The action/log runs only on authority. Local prompt state is
not a client authorization. Registry iteration is proportional to registered
targets; large streamed worlds may need a spatial index when measured.

## Checks

- Build: `Build.bat TownAgeEditor Win64 Development <TownAge.uproject>`.
- Automation: `TownAge.Interaction.Selection`, `TownAge.Interaction.TouchLayout`.
- Runtime: verify the native player is out of range at PlayerStart; approach the
  door and face it to show `G`; pressing it writes `LogTownAgeInteraction` with
  `Event=Door.Inspect`. Turn away or leave range and verify no action is emitted.
- Desktop touch preview: launch with `-faketouches`; check disabled/enabled
  circular `USE`, one action per press, and concurrent movement/sprint fingers.
- Remote-client check: register `verify_network.py`, then use a two-player
  listen-server PIE session. After `network_input_ready.json` appears, press G
  in the actual client window. The helper matches PlayerState IDs across worlds,
  verifies server eligibility and checks the authoritative action log. Restore
  the original PIE settings afterward. In this engine, the native Config Settings
  tool's `Editor/LevelEditor/PlayIn` section can read/write `PlayNetMode`,
  `PlayNumberOfClients` and `RunUnderOneProcess`; the enum is not Python-wrapped.
  Do not invoke the client action directly from Python: Unreal's editor script
  guard forces RPC callspace to local during Python ProcessEvent calls.

Sources: [Epic component replication](https://dev.epicgames.com/documentation/unreal-engine/replicating-actor-components-in-unreal-engine),
[Epic data-driven gameplay](https://dev.epicgames.com/documentation/en-us/unreal-engine/data-driven-gameplay-elements-in-unreal-engine).

Models, levels, imported DataTables, screenshots and local reports stay local.
Only source, the CSV dataset and documentation are published. Desktop checks do
not establish Android/iOS packaging or physical-device performance.

Verified locally: editor build; four TownAge automation tests; standalone prompt
eligibility and request throttling; native PC G input; native G and simulated
touch USE input from a connected PIE client reaching the authoritative server;
disabled mobile button ignoring input. PIE settings were restored to one-player
standalone. `Saved/Interaction` contains the reports and corresponding engine logs.
