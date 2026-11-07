# TownAge Meshy pipeline

Meshy is the default source for new TownAge 3D characters and props. The workflow is approved reference -> Meshy generation -> visual review when needed -> mobile-budget remesh -> character rigging -> local FBX/textures -> validated Unreal candidate. Setup alone does not submit paid tasks.

The latest main-character brief is a long-haired female in TownAge's rounded, cozy style. No generation of that character is implied by installing this pipeline. Existing procedural revisions and production assets are preserved.

## Local connection

The launcher uses the pinned official `@meshy-ai/meshy-mcp-server` package (0.6.9 for this setup) under `C:\Users\Kelvin\.codex\mcp\meshy`. `launch_meshy_mcp.ps1` reads `MESHY_API_KEY` from the process or Windows user environment and launches the server. The Codex MCP entry is `meshy`; new sessions load the configuration.

To recreate the local package installation with Node.js18 or later:

```powershell
npm.cmd install --prefix C:/Users/Kelvin/.codex/mcp/meshy --save-exact --ignore-scripts @meshy-ai/meshy-mcp-server@0.6.9
codex.exe mcp add meshy -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/Kelvin/Desktop/TownAge/Tools/Meshy/launch_meshy_mcp.ps1
```

Create an API key on the [Meshy API Keys page](https://www.meshy.ai/developers/keys). Enter it locally using the hidden prompt:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Tools\Meshy\set_meshy_key.ps1
```

Do not paste the key into chat or a command argument. The helper stores a Windows user environment variable, not an encrypted vault, and does not print the value. Credentials must never enter this repository. The launcher reads the user environment at startup, so a newly launched server can use the key even if an already running desktop process has an older environment snapshot.

The existing Python MCP environment is reused below; Blender does not need to run for these commands:

```powershell
& 'C:\Users\Kelvin\.codex\mcp\blender-mcp\Scripts\python.exe' .\Tools\Meshy\meshy_mcp.py list-tools
& 'C:\Users\Kelvin\.codex\mcp\blender-mcp\Scripts\python.exe' .\Tools\Meshy\meshy_mcp.py check
```

`list-tools` saves live input schemas to `Saved/Meshy/list-tools.json`. `check` calls the read-only balance tool. This setup verified the official server handshake,28-tool catalog and authenticated balance response. No paid generation was executed. Local importer fixture verification is separate from a real Meshy generation/import run, which remains untested.

Validation on UE5.8.4 passed for skeletal and static local FBX fixtures, candidate BP creation,170cm placement scale, saved Skeleton/Physics dependencies and texture settings after a fresh process reload. Twelve automated tests passed, including destination protection, unsupported material sets and paid-call/receipt guards. These fixtures use the existing local character FBX, not a newly generated Meshy asset.

## Requests and receipts

Use a separate ignored job folder such as `Saved/Meshy/TownKeeper_Meshy/run001/`. Request JSON has the form `{"tool": "tool_name", "arguments": {}}`. Preserve each returned task ID and type with its request and response. Use a new output filename for every call; the helper refuses overwriting an existing call receipt. Calls without `--output` get timestamped response filenames. The pre-call journal is `Saved/Meshy/calls.jsonl`.

Read the live schema before filling requests. The following examples match the setup catalog but have **not** been executed and use illustrative input paths/IDs.

An approved image-to-3D request can use a local reference file:

```json
{
  "tool": "meshy_image_to_3d",
  "arguments": {
    "file_path": "C:/Users/Kelvin/Desktop/TownAge/ArtSource/Meshy/TownKeeper_Meshy/reference.png",
    "ai_model": "meshy-7.1",
    "pose_mode": "t-pose",
    "should_texture": true,
    "enable_pbr": true,
    "target_formats": ["fbx", "glb"],
    "response_format": "json"
  }
}
```

Only after generation and its expected credit/attempt budget are authorized, submit the saved request explicitly:

```powershell
& 'C:\Users\Kelvin\.codex\mcp\blender-mcp\Scripts\python.exe' .\Tools\Meshy\meshy_mcp.py call --request .\Saved\Meshy\TownKeeper_Meshy\run001\generate-request.json --output .\Saved\Meshy\TownKeeper_Meshy\run001\generate-response.json --allow-create
```

`--allow-create` permits a potentially charged operation; it is not a spending cap or an idempotency key. Check current [models](https://docs.meshy.ai/en/api/models) and [pricing](https://docs.meshy.ai/en/api/pricing) before selecting paid stages. No automatic paid retry is performed.

Poll an existing task using its recorded ID. Use `wait: false` so the caller can give progress updates. The official tool defaults to a wait of up to300seconds; the project helper overrides omitted waits tofalse and caps an explicit wait at45seconds.

```json
{
  "tool": "meshy_get_task_status",
  "arguments": {
    "task_id": "recorded-generation-task-id",
    "task_type": "image-to-3d",
    "wait": false,
    "response_format": "json"
  }
}
```

Run status/list/download requests with the same `call --request ... --output ...` syntax, without `--allow-create`. A timeout does not cancel a remote job. If a create response is lost, reconcile the journal and recent tasks of the appropriate type before submitting anything new. The helper deliberately rejects `meshy_cancel_task`, which deletes tasks.

After preview review, use the live `meshy_remesh` schema if needed to reach the stated triangle budget. Rig the successful textured humanoid result:

```json
{
  "tool": "meshy_rig",
  "arguments": {
    "input_task_id": "recorded-successful-remesh-task-id",
    "height_meters": 1.7,
    "response_format": "json"
  }
}
```

Rigging is charged and also needs `--allow-create`. Keep existing textures; do not supply the deprecated `texture_image_url` override for an already textured result. Do not request animation jobs unless animation is in scope.

Download the successful rigged FBX and returned texture maps:

```json
{
  "tool": "meshy_download_model",
  "arguments": {
    "task_id": "recorded-successful-rig-task-id",
    "task_type": "rigging",
    "format": "fbx",
    "include_textures": true,
    "save_to": "C:/Users/Kelvin/Desktop/TownAge/ArtSource/Meshy/TownKeeper_Meshy/candidate_v001/model.fbx"
  }
}
```

Use the actual returned local texture paths in the import manifest. Downloaded files, screenshots, job receipts and signed download URLs stay local.

## Unreal candidate handoff

The exact schema and verification requirements are in [engine-handoff.md](../Skills/townage-meshy/references/engine-handoff.md). The current importer supports one atlas with optional basecolor/roughness/normal maps, static or skeletal input, and optional placement BP creation. It rejects multiple material slots, imports no clips and changes no production pawn or maps.

Validate a real downloaded delivery offline before starting Unreal writes:

```powershell
& 'C:\Users\Kelvin\.codex\mcp\blender-mcp\Scripts\python.exe' .\Tools\Meshy\import_meshy_unreal.py --validate .\ArtSource\Meshy\TownKeeper_Meshy\candidate_v001\import_manifest.json
```

Once inputs exist and candidate import is requested, save/close an overlapping interactive editor before a headless import:

```powershell
& 'E:\UE\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$PWD\TownAge.uproject" -run=pythonscript "-script=$PWD\Tools\Meshy\import_meshy_unreal.py" "-MeshyManifest=$PWD\ArtSource\Meshy\TownKeeper_Meshy\candidate_v001\import_manifest.json" -unattended -nullrhi
```

The candidate lives under `/Game/Characters/Meshy/<asset_name>/<candidate_version>`. Nonempty candidate folders are rejected. Inspect `Saved/Meshy/<asset_name>/<candidate_version>/import_report.json`, then review the candidate in the editor. A failed partial import remains isolated for inspection; use a new version for a deliberate retry. Production replacement is a separate requested step after visual, size, skeleton and budget checks.

## Durable rules

- Reference/visual changes requiring art direction return to user review; reuse existing approval of the same version.
- Meshy output is the default. Do not silently replace it with GPT procedural Blender reconstruction.
- Remesh/rig/output success is not proof of good hands, hair, skin weights or mobile performance.
- Meshy skeletons may need explicit retargeting to existing approved motion.
- Only code/configuration/documentation is committed. Art/game binaries, receipts and keys remain local.

Sources: [Meshy AI integration](https://docs.meshy.ai/en/api/ai), [official MCP repository](https://github.com/meshy-dev/meshy-mcp-server), [task lifecycle](https://docs.meshy.ai/en/api/task-lifecycle), [rigging API](https://docs.meshy.ai/en/api/rigging).
