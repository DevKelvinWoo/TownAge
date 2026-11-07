# Village01 terrain foundation

The first TownAge village is a modern pedestrian neighborhood foundation: maintained grass, light paving, a small off-center plaza and connected curved paths. It contains no buildings, farmland, foliage, decoration objects or water. The active visual reference is the local `ArtSource/Terrain/Village01/Village_Terrain_Modern_Concept02.png`.

## Representation

- New map: `/Game/Maps/L_VillageTerrain_01`; terrain assets: `/Game/Terrain/Village01`.
- Native Unreal Landscape,253x253 vertices,1m spacing,16components with one63quad section each:252x252m.
- Central100m area is flat. Height range0–7.625m; main paths remain below1degree grade. Three weight-blended layers: Grass, Paving and Earth.
- Two small repeating surface textures:128x128 grass variation and512x512 paving with50cm staggered slab joints. No Nanite, virtual textures, grass-instance output or runtime procedural generation is required.
- `TownAgeTerrainEditor` is an Editor-only project plugin exposing native `ALandscape::Import`, which is not directly callable from the installed Python/MCP tools. Created actors are normal engine Landscape actors; the helper is not a gameplay dependency.
- This first small district is a normal fully loaded map, not a World Partition streaming demonstration. Integrating a larger streamed world is a later step. Existing default/startup maps and character code are preserved.

## Reproduce

Generate deterministic source maps with Python; the generator uses only the standard library:

```powershell
python.exe Tools/Terrain/generate_village_maps.py
python.exe Tools/Terrain/generate_village_maps.py --validate-only
```

Outputs are local `Height.r16` (little-endian unsigned16), `Grass.r8`, `Paving.r8`, `Earth.r8`, a numeric overview and `terrain_manifest.json`. Each vertex's three weights sum to255. Conflicting source bytes are refused; `--replace` replaces only explicitly named generated files, preserving concept art and other files.

Save and close an interactive editor before building the new plugin or performing commandlet asset writes:

```powershell
& 'E:/UE/UE_5.8/Engine/Build/BatchFiles/Build.bat' TownAgeEditor Win64 Development "$PWD/TownAge.uproject" -WaitMutex -NoHotReloadFromIDE
& 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$PWD/TownAge.uproject" -run=pythonscript "-script=$PWD/Tools/Terrain/create_village_terrain.py" -unattended -nullrhi -nosound -nop4
```

Null-RHI creation prepares geometry, collision and raw edit layers, but is **not** a completed visual import. Finish edit-layer merging and rebuild the generated Landscape material instances in a normal GPU editor:

```powershell
Start-Process -FilePath 'E:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList 'C:/Users/Kelvin/Desktop/TownAge/TownAge.uproject','/Game/Maps/L_VillageTerrain_01','-VillageFinalize','-ExecCmds="py C:/Users/Kelvin/Desktop/TownAge/Tools/Terrain/create_village_terrain.py"' -WindowStyle Hidden
```

The finalizer is restricted to this generated map. Wait for `Saved/Terrain/Village01/gpu_finalization_report.json` and inspect actual grass/paving appearance before declaring completion. The new map's exposure range accounts for both legacy brightness units and extended EV100 projects; no global renderer settings are changed.

The creator refuses an existing map and incompatible/pre-existing destination assets rather than overwriting user work. Inspect partial results after a failed import before an explicit retry; do not blindly delete or replace existing content.

## Verification

Check native Landscape/collision component counts,252m bounds, saved paint layers and material compilation in a fresh editor. Trace paths and test actual character movement/collision, then inspect overhead and current gameplay-camera views. Report screenshots and measurements separately from concept art. Desktop checks do not prove Android/iOS package or device performance, streaming or multi-client behavior.

Generated source maps, textures, references and Unreal assets remain local under the project's asset publishing policy. Commit only this tooling, the Editor plugin and documentation.
