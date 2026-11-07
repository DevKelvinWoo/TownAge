---
name: townage-meshy
description: Generate TownAge characters and props through Meshy MCP, prepare mobile-aware mesh and texture deliveries, and import verified Unreal candidates. Use for Meshy setup, reference-to-3D work and Meshy asset handoff; standalone locomotion authoring uses townage-locomotion.
---

# TownAge Meshy production

Meshy is the default 3D generation route for TownAge. Read the project's AGENTS.md and the actual brief. Keep existing production assets intact while preparing a separately named candidate. Do not substitute GPT-authored primitive/loft reconstruction or procedural Blender modeling unless the user explicitly requests that route.

## Scope and connection

A setup, connection or capability-check request may configure the pipeline and run authorized offline checks or isolated local fixture imports. It does not authorize unsolicited paid generation, remeshing, rigging or conversion. The current long-haired female main-character direction is a brief, not an instruction to start a paid task during setup.

Use the official `@meshy-ai/meshy-mcp-server`. Discover its live tools and schemas; names, models and supported combinations can change. The repository's `Tools/Meshy/README.md` contains the local launcher and client commands. A successful tool catalog proves connectivity, not API authentication or generation quality. Check account access with the read-only balance tool when a key is available.

Read `MESHY_API_KEY` from the environment. Never request the key in chat, place it in a request file/config committed to Git, print it, or record it in task receipts. The local key-entry helper stores a Windows user environment variable; this is local persistence, not an encrypted vault.

## Reference to candidate

1. Reuse an approved reference and its recorded direction. For a new or materially changed concept, show the image and wait for explicit direction/approval before image-to-3D. An instruction to model a supplied image is approval to use that image; do not ask again for the same version. Use ImageGen only when reference creation/editing is in scope.
2. Prefer image-to-3D for a concrete approved design. Use text-to-3D when no visual reference is intended, and multi-image only for consistent views of the same character/object. Discover current schema options for separated limbs, neutral pose, textures and output formats. Keep character identity, accessories and silhouette readable.
3. Before charged calls, make the selected stages, expected credits and bounded attempt count clear and keep them within the user's authorization. Read current pricing/model compatibility rather than copying old rates. Do not automatically exhaust credits trying to improve a result.
4. Inspect a generated preview from front, side and back before treating it as production-ready. If the output materially changes the approved design or needs a new visual choice, show it and wait for direction before further paid revisions. Otherwise continue the already authorized post-processing chain.
5. Remesh before rigging when the generation exceeds the planned budget. Treat a hero LOD0 budget of roughly30–60k triangles as a starting TownAge convention, not proof of mobile performance. Count triangles, not just source quads; verify hands, face, hair and accessory clearance after reduction. Use a smaller budget/LODs for crowds and measure in-engine cost later. Skip a redundant remesh when the output already satisfies the agreed budget.
6. Rig animation-ready characters through the supported Meshy rigging route; static props skip rigging. The API route documents textured humanoids with clearly separated limbs—do not assume every web-app rig option is available through MCP. Use the requested real-world size, normally `height_meters: 1.7` for TownAge characters. Preserve pre-rig textures, and inspect what the rigged output actually retains. Leave the deprecated `texture_image_url` override out of already textured inputs; it can replace the existing maps. Do not submit animation jobs when animation is out of scope.
7. Download FBX and its texture maps into a versioned local asset folder. Inspect successful task output first; convert only if FBX is unavailable and conversion is authorized. Prefer an explicit local save path. Keep a GLB preview when useful. Never infer a skeleton from a filename or guess the normal-map convention. Verify the actual saved file: MCP0.6.9 rigging downloads can return asset URLs despite `save_to`; retrieve those exact returned HTTPS asset URLs if needed, preserve the receipt locally, and check file size/hash before import. Do not create another paid task to fix a local download failure.
8. Create the local import manifest described in [references/engine-handoff.md](references/engine-handoff.md), validate it offline, then import into an empty Unreal candidate folder. Inspect actual engine appearance, native bounds, placed Actor size, normals, material channels, rig/deformation and mobile budget before a requested production replacement.

## Task receipts and retries

Keep each request, response and returned task ID under an ignored `Saved/Meshy/<asset>/<run>/` job folder. Record stage, task type, predecessor ID, request/reference hash, status, selected model and consumed credits when returned. Store these job receipts separately from the strict Unreal import manifest.

The local client writes a pre-call journal, does not automatically retry create calls, and refuses overwriting an existing call receipt. Its `--allow-create` switch is an explicit execution guard, not a provider idempotency key or a spending limit.

For polling, use `meshy_get_task_status` with `wait: false`, or a bounded wait no longer than45seconds, and honor backoff/Retry-After. A client timeout does not cancel the remote job. If submission outcome is uncertain, reconcile the journal and `meshy_list_tasks` for the relevant task type before doing anything that could create another billable job. Resume the existing ID. Do not blindly resend generation, remesh or rig requests. A failed task requires reading its error and deciding a bounded correction; a setup failure does not justify a modeling fallback. `meshy_cancel_task` deletes tasks and is deliberately excluded from the project helper.

## Handoff and limits

Meshy skeletons are not automatically compatible with the previous TownKeeper skeleton or approved walk. Keep a new skeleton in the candidate, inspect its hierarchy, and plan explicit animation retargeting using the locomotion workflow when requested. Do not attach incompatible clips or overwrite the reference pose just to make an import succeed.

Report source/task provenance, preview, local manifest, candidate asset/BP paths, actual measurements, remaining visual defects and untested device/network behavior. Stage only explicit code/configuration/documentation paths. Models, textures, clips, `.uasset`, `.umap`, receipts and credentials stay local. Never promote a candidate or replace the playable pawn as an incidental setup/import step.

Authoritative references: [Meshy AI integration](https://docs.meshy.ai/en/api/ai), [official MCP source](https://github.com/meshy-dev/meshy-mcp-server), [task lifecycle](https://docs.meshy.ai/en/api/task-lifecycle), [rigging](https://docs.meshy.ai/en/api/rigging), [remesh](https://docs.meshy.ai/en/api/remesh).
