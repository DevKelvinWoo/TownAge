# CozyHouse01 split-door delivery

The approved Meshy cottage has an isolated `candidate_v002` with a static body,
independent door mesh, and right-hand hinge. The door is closed at zero rotation.
That base delivery contains the mesh separation. Current interaction and animated
travel extend its placement BP through `Tools/Interaction` and `Tools/Doors`.

Local source: `ArtSource/Meshy/CozyHouse01/candidate_v002/CozyHouse01_Split.blend`.
Unreal BP: `/Game/Characters/Meshy/CozyHouse01/candidate_v002/BP_CozyHouse01_Split`.
Components: static root and `HouseBody`; movable `DoorHinge` with movable
`DoorLeaf` attached at relative location zero. Future motion should rotate the
hinge's local Z axis. Use component transform functions; editor property setters
on live instances can reconstruct the actor and invalidate component references.

`CozyHouse01_Review` is saved in `/Game/Maps/L_VillageTerrain_01` at approximately
`(2800, -1180, -0.8)` cm, 5.89 m from the preserved PlayerStart. Original map backup:
`Saved/Meshy/CozyHouse01/backups/L_VillageTerrain_01-before-house.umap`.
Terrain and project startup/default maps were not regenerated or changed.

## Reproduction and safeguards

- Run `split_cozy_house_door.py` in Blender background mode. It reads the retained
  v001 mesh, groups positional connectivity on a temporary copy, separates twelve
  complete door-detail islands, and clips hidden doorway backfill with UV/normal
  interpolation. It writes the v002 FBXs, GLB, blend, manifest and static open/closed
  checks. This script is specific to this source geometry. It rewrites its named
  local v002 outputs; preserve later manual edits before rerunning.
- Run `import_place_cozy_house.py` as an Unreal Python commandlet only in a copy
  without this candidate and placement. It refuses occupied destinations, existing
  review actors and existing backup files. It reuses the v001 atlas material,
  verifies FBX axis signs, creates the split BP, traces ground and adds one house.
  Do not run a commandlet against packages open in an interactive editor.
- `verify_cozy_house.py` runs in the GPU editor. It reimports the v002 body,
  normalizes the component hierarchy, recreates only the named review instance,
  verifies mesh bounds and a temporary 75-degree hinge pose, restores closed and
  saves. Starting PIE then records the native player, grounded state and separate
  meshes. It is an explicit repair/verification command, not a read-only audit.

## Verified delivery

Body: 13,626 triangles. Door: 1,030 triangles. Combined: 14,656 triangles;
two mesh sections sharing one 2048x2048 base-color atlas. Bounds approximately
462.23 x 398.24 x 430 cm. Measure colliding mesh bounds to exclude editor-only
component visualization sprites. Body and closed door block collision; the
arched body entrance uses complex static collision so a convex hull does not
seal the doorway. This has not been profiled on mobile devices.

Technical reports and screenshots are local under `Saved/Meshy/CozyHouse01`.
Art direction and look-and-feel judgment remain with the user. Keep models,
textures, map files, previews and task receipts out of commits.

The runtime now uses the `candidate_v003` leaf with an inside handle, while
retaining this base body and prior source deliveries. Refer to `Tools/Doors/README.md`
for the native pose blend, synchronized hinge and streamed gray-room connection.
