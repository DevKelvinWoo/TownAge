# World clock and day/night sky

The world uses a 24-hour clock, starting at **08:00**. One unpaused real second
advances one game minute: a complete day takes **24 real minutes** by default.
The top-center HUD shows `HH:mm`, day number and Morning/Noon/Evening/Night.
It uses a translucent panel, viewport scaling and the Canvas safe-area inset,
does not intercept touches, and stays available while chat is open. The mobile
chat composer is capped before the clock's left edge to prevent overlap.

## Authority and configuration

`ATownAgeGameMode` selects `ATownAgeGameState`. Authority replicates a single
snapshot containing epoch server seconds, total game hours and day length.
Clients evaluate it with Unreal's synchronized `GetServerWorldTimeSeconds()`;
they do not run independent incrementing clocks. The engine synchronizes server
seconds every two seconds, and late joiners receive the current epoch/rate.
No per-frame time RPC is sent. A dedicated server owns time without sky rendering.

Configure `Config/DefaultGame.ini`:

```ini
[/Script/TownAge.TownAgeGameState]
StartHour=8.0
RealMinutesPerDay=24.0
```

Day length supports 1–1440 real minutes. Authority-only Blueprint functions
`SetTimeOfDay(Hours)` and `SetDayLengthMinutes(Minutes)` allow later sleep/event
systems to control time; a rate change rebases the epoch without jumping time.
These functions are not client-callable RPCs. In non-Shipping development builds,
the **server** accepts `-TownAgeStartHour=18 -TownAgeDayMinutes=1` for quick QA.

The clock advances during active simulation, pauses with the world and follows
global time dilation. It continues through streamed cottage travel. Midnight
increments the day counter. This is session state: restart/full map travel starts
a fresh clock; save persistence and offline elapsed time are not implemented.
Future saves should store total world hours and the chosen day length on authority.

## Sky presentation

Every rendering world creates one nonreplicated `ATownAgeTimeSky` which samples
the shared clock at 10 Hz. A native sky dome uses engine mesh/material references:
`SM_SkySphere`, `M_Sky_Panning_Clouds2`, and `DaylightAmbientCubemap`. Nine palette
keys smoothly interpolate blue daylight, warm dawn/dusk and dark-blue night,
including a continuous midnight seam. The sun rotates and fades across the horizon;
the same directional light blends into a soft above-horizon moon key at night.
Its 3% daytime intensity floor is an artistic readability choice, not physical
moonlight simulation. No extra directional light/shadow budget is added.

The actor reuses persistent-level directional/sky lights and preserves each map's
daytime peak intensity (CharacterTest is 10; VillageTerrain is 50000). It changes
mobility at runtime and only adjusts outdoor lighting. Streamed interior lights
are left alone; daylight shading can still affect open/cutaway interiors.
Exposure overrides bias (0 by day, -1.25 at night) and adaptation speed (4 stops/s).
Existing map exposure method/range and all map assets remain untouched. Sky
emissive radiance is calibrated to each map's sun intensity. The persistent
physical SkyAtmosphere is hidden during play so it cannot extinguish the dome's
night colors; the stylized dome provides the visible sky instead.

A fixed ambient cubemap provides the same baseline for a client joining at night
as for the daytime host. Its intensity/tint changes with time. Dynamic cubemap
recapture, volumetric clouds and additional shadow lights are avoided for mobile.
Reflections are consequently an approximation of the current sky. No new binary
assets or external dependencies are needed.

## Verification tools

- `inspect_environment.py`: read-only commandlet inventory of both supported maps.
- `verify_runtime.py`: run in a GPU editor, optionally in existing standalone PIE.
  Starts PIE if needed, temporarily points the pawn's camera toward the horizon,
  samples dawn/noon/evening/night, captures images, verifies sun/palette
  changes, midnight rollover and rate continuity, and restores the camera/08:00.
  Use a fresh session at the configured default rate; map assets are never saved.
- `verify_network.py`: two-player PIE authority/replication verification.
  When play-setting enums are unavailable in Python, configure Number of Players=2,
  Net Mode=Play As Listen Server in the Play dropdown, run the script, then Play.
  Restore the original one-player standalone settings after verification.
- Automation: `Automation RunTests TownAge` includes `TownAge.Time.Clock` for rate,
  wrap, multi-day elapsed time, formatting, phase boundaries and rebasing.

Example editor launch:

```powershell
Start-Process 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList "$PWD/TownAge.uproject",'/Game/Maps/L_VillageTerrain_01','-ExecCmds="py C:/Users/Kelvin/Desktop/TownAge/Tools/Time/verify_runtime.py"' -WindowStyle Hidden
```

Reports/images stay local under `Saved/Time`; automated test output is in
`Saved/Logs/TimeAutomation.log`. Physical Android/iOS packaging, safe-area reporting,
GPU performance and network-loss testing must be reported separately from desktop
touch previews. Existing startup/default maps are unchanged.

Local validation passed: final editor/UHT build and all seven TownAge automation
tests; GPU village dawn/noon/evening/night screenshots; midnight day increment;
rate changes without jumps; two-world listen-server/client replication, rejected
client setters and matching sky palettes. The measured post-rate-change clock
difference was below one game second. One-player standalone PIE settings were
restored. Native 960x540 touch preview confirmed the top-center clock, readable
village night lighting, and mobile chat/clock separation. Physical Android/iOS,
device GPU budgets, packet loss and late-join transport timing were not tested.
