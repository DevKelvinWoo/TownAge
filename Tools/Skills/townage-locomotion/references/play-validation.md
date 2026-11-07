# Locomotion acceptance checks

Record each item as passed, failed, or not tested, with the observation or local evidence path. Technical metadata alone cannot prove an appealing animation.

## Source and clips

- Rest pose restored after authoring tests; no unintentional model/skeleton changes.
- Foot stance/swing readable from side and gameplay cameras; no visible sliding at intended speeds, knee flips, ground penetration or satchel/limb collisions.
- Several loop repetitions without seam pops or dwell; walk and sprint use compatible contact phases.
- Root is in-place throughout each clip; only intended takes exported and rebound to the existing UE skeleton.

## Gameplay

- Idle at zero velocity, walk on actual movement, sprint at actual sprint speed; holding sprint while stationary does not run in place.
- Acceleration, deceleration, abrupt stops, reversal and diagonal turning do not snap or produce mismatched feet.
- Wall-blocked motion and slopes are checked when available; do not claim slope support from a flat floor test.
- Stamina exhaustion transitions sprint to walk; recovery and repeated sprint requests preserve smooth motion.
- WASD/Shift and touch joystick/sprint button produce the same motion-state behavior. Test weak and full analog input, release and multitouch; distinguish mouse fake-touch checks from physical touch-device checks.
- A host and remote client show appropriate movement/animation on each other; test latency/correction when available. Label untested networking explicitly.

## Mobile and preservation

- Character readability checked at the actual fixed camera distance and phone/tablet aspect ratios.
- Baseline animation cost checked with multiple characters and intended LOD/compression settings. Report missing device/SDK tests explicitly.
- Test level and production references remain intact after save/reload; user placements survive.
- Staged commit list contains only code, configuration and documentation. Clips, models, previews and Unreal assets are excluded from pushes.
