# TownAge dedicated server

`TownAgeServer` is the Unreal server target for Windows and Linux. It uses the
same runtime game module on the development PC and on an external host. Build a
package for the operating system that runs the server, and keep server and
client builds compatible.

## Build a server package

Use an Unreal Engine source build compatible with the project, or an installed
engine distribution explicitly built with Server target support. Build its
editor first for cooking and install the toolchain for the target platform.
The workspace engine at `E:/UE/UE_5.8` is an installed build whose platform
manifest has no Server configurations. It can run editor network tests, but a
standalone dedicated-server package requires a server-capable engine build.
The `TownAgeServer Win64 Development` build reaches UnrealBuildTool's engine
support check and reports `Server targets are not currently supported from this
engine distribution.`
[Epic's dedicated server setup](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-dedicated-servers-in-unreal-engine)

On Windows, run this from the repository root with the source engine path.

```powershell
$engine = 'E:/UE/UE_5.8_Source'
& "$engine/Engine/Build/BatchFiles/RunUAT.bat" BuildCookRun "-project=$PWD/TownAge.uproject" -server -noclient -serverplatform=Win64 -serverconfig=Development -build -cook -stage -pak -map=/Game/Maps/L_VillageTerrain_01 -unattended
```

On Linux, use the Linux toolchain and source engine build.

```bash
engine=/path/to/UnrealEngine
"$engine/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun "-project=$PWD/TownAge.uproject" -server -noclient -serverplatform=Linux -serverconfig=Development -build -cook -stage -pak -map=/Game/Maps/L_VillageTerrain_01 -unattended
```

Copy or deploy the complete staged package, including its cooked content. The
commands select the village as a cook entry point and leave startup maps in
project configuration unchanged. If you change maps at launch, include that
map in the cook as well. Keep generated packages out of Git.

## Run the same package locally or on a host

Use the executable from the staged server build. Both
scripts default to `/Game/Maps/L_VillageTerrain_01` on port `7777`. Set
`TOWNAGE_MAP` and `TOWNAGE_PORT` per process. The Windows script also accepts
explicit `-Map` and `-Port` arguments. Arguments after the Linux executable, or
in Windows `-ServerArguments`, are forwarded as separate Unreal arguments.

```powershell
.\Tools\Server\Start-TownAgeServer.ps1 -Executable 'D:/TownAgeServer/TownAgeServer.exe' -Port 7777 -ServerArguments @('-TownAgeProfileDirectory=D:/TownAgeData/Profiles')
```

```bash
TOWNAGE_PORT=7777 bash Tools/Server/start-townage-server.sh /opt/townage/TownAge/Binaries/Linux/TownAgeServer -TownAgeProfileDirectory=/var/lib/townage/profiles
```

For a local smoke test, connect a compatible client to `127.0.0.1:7777` with
`open 127.0.0.1:7777` in its developer console. For an external smoke test, use
the host address and configure access to the selected UDP port. For Linux
supervision, pass the actual server binary as shown above. The launcher uses
`exec` to pass the supervisor's shutdown signals directly to that process.

## Data and migration checks

`UTownAgeProfiles` owns the authoritative appearance cache and pending saves.
The local provider stores versioned JSON in `Saved/Profiles`, or at the absolute
path supplied by `TOWNAGE_PROFILE_DIRECTORY` or `-TownAgeProfileDirectory` (the
command line takes precedence). Mount that directory on persistent storage
when moving the local provider to a different host. Only one server process
may write to a local profile directory. Keep development and production
directories separate.

- Standalone game worlds bind to one local offline appearance profile. PIE and
  unauthenticated network players keep session-only state. Durable network
  profiles require a stable internal account key from trusted authentication.
- Override `ATownAgeGameMode::ResolveAppearanceAccount` to supply a server-verified
  key at possession. If login finishes later, call the native authority-only
  `BindAppearanceAccount` after verification. The default resolver never trusts
  a client or PlayerState ID for durable network storage.
- Gameplay stages hair and makeup together after validating the owned request.
  The local provider batches changes about once per second, flushes on logout
  and orderly game-instance shutdown, and keeps the preceding record during
  replacement. A hard stop can lose edits that were still buffered. A malformed
  record fails loading without replacing it with defaults.
- Select a compatible `UTownAgeProfileStore` with `StoreClass` in
  `[/Script/TownAge.TownAgeProfiles]` in Game config. The default is the local
  provider. This small synchronous contract is suitable for local files or a
  preloaded cache; connect remote authentication, I/O and durable write
  confirmation through the backend, outside the gameplay thread. Use backend
  transactions for inventory/currency, not the buffered cosmetics writer.

Door traversal, stamina, chat and the current clock stay authoritative runtime
state. Preserve streamed room and door animation assets when cooking. The
headless door path skips player animation, lighting and camera effects, while
the authoritative movement and collision paths still run. Persist future village
time by a stable village ID and a real-time anchor, since engine world time
starts over when a process restarts.

The launchers do not provision an authentication service, database, matchmaking
or session allocator. Development tooling plugins are enabled for Editor targets.

When preparing an external deployment, verify a separate client can join the
packaged server and reconnect after a restart. Once account authentication and
external persistence are available, repeat that check with the same verified
account on a different host. A working editor PIE session verifies network
behavior inside the editor. Verify a server package separately on each target OS.

The launchers were checked with local stub executables on Windows PowerShell
and Git Bash. The checks cover map and port selection, a forwarded argument
containing spaces, invalid port rejection, and propagation of the child exit
code. Building and running a packaged server on Windows or Linux remains to
be verified with a server-capable engine.
