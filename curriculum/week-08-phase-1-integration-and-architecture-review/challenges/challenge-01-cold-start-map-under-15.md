# Challenge 1 — Cold start to saved map in under fifteen minutes

> **Estimated time:** 90–120 minutes including practice runs. Worth far more than its time cost: this is the single most realistic test of whether your Phase 1 stack is operable by someone other than you.

You will take a multi-room Gz Sim world you have **never mapped before**, bring the entire stack up with **one command**, drive the robot to map it, and save a complete, loop-closed map — all in **under fifteen minutes of wall-clock time**, measured from the moment you press Enter on the launch command to the moment a `.pgm`/`.yaml` map pair exists on disk. This is exactly the hands-on lab the syllabus specifies for the Phase 1 milestone, and it is the practical evidence that your `crunchbot_bringup` package is a product, not a demo.

## The setup

You need a world you have not seen. Three ways to get one, in order of preference:

1. **A teammate swaps worlds with you.** Each of you builds (or downloads) a multi-room `.sdf` world the other has not seen, drops it in `worlds/`, and tells the other only its filename. This is the most honest version — you map blind.
2. **Use a community world you have not opened.** The `aws-robomaker-small-warehouse-world` and `aws-robomaker-small-house-world` are public Gz worlds; pick whichever you did *not* use in week 7. Do not open it in the Gz GUI to "study the layout" first — that defeats the cold-start premise.
3. **Procedurally vary a world.** Take your week-7 world and rearrange the interior walls into a layout you do not have memorized. Weaker, because you know the rough scale, but acceptable if you genuinely scramble the rooms.

The world must have **at least three rooms** connected by **at least two doorways**, and a layout that requires **at least one loop closure** to map cleanly (i.e., a path that returns to a previously-seen area). A single open box is not a valid challenge world; the loop closure is the part that tests your SLAM configuration.

## The rules

- **One command.** The only thing you may type to bring the system up is your single `ros2 launch crunchbot_bringup robot.launch.py ...` line plus, in a separate terminal, your teleop and the `map_run_timer`. If you find yourself running a fourth `ros2 run`, your package is incomplete — fix it before the timed run.
- **The clock starts at the launch command** and stops when the saved map files exist on disk. Bring-up time counts. A package that takes 90 seconds to come up has spent 10% of its budget before the robot moves.
- **No pre-driving.** You may not drive the unseen world before the clock starts. You map it live.
- **Loop closure required.** The saved map must show a closed loop — the corridor you traversed twice must line up, not show as two offset ghost walls. A drifted, un-closed map fails the challenge even if it was saved in time.
- **Reproducible.** Document the exact command and the world file so a reviewer can re-run on the same world.

## What "done" looks like

A `.pgm` image and a `.yaml` metadata file under `maps/`, produced by `slam_toolbox`'s `save_map` service, showing a recognizably-complete multi-room map with straight, single walls (no doubling from drift) and correct relative room positions. The `map_run_timer` from exercise 3 prints an elapsed time under `15.0` minutes.

## Suggested approach

### Practice phase (untimed)

1. Bring up your stack on a **known** world and rehearse the full workflow end to end: launch, teleop, drive a deliberate coverage pattern, trigger a loop closure, save the map, confirm the files. Time yourself loosely. If a known world takes you twelve minutes, an unknown one will blow the budget — tighten your workflow first.
2. Settle your teleop. The `teleop_twist_keyboard` node is fine, but a gamepad is faster and smoother, and smoother driving produces better scan matching (jerky motion causes scan-match failures and drift). Decide and rehearse.
3. Tune `slam_toolbox` for *speed of convergence*, not map prettiness. The parameters that matter under a time budget:
   - `minimum_travel_distance` / `minimum_travel_heading` — smaller values add pose-graph nodes more often (better tracking, more compute). Find the value that tracks reliably without saturating your CPU.
   - `map_update_interval` — how often the map republishes. 2.0 s is fine; do not set it so low you starve the optimizer.
   - `loop_search_maximum_distance` — must be large enough to find your loop. If your corridors are long, raise it.
   - `max_laser_range` — clip to your LiDAR's reliable range; phantom long returns pollute the map.

### Timed phase (the actual challenge)

4. Start the `map_run_timer` (`ros2 run crunchbot_bringup map_run_timer -p map_name:=<world>`) so you have an authoritative clock and a coverage readout.
5. Launch the stack. Note the wall-clock time.
6. Drive a **deliberate coverage pattern**: follow walls, clear each room corner, and *return through at least one corridor you have already mapped* to force a loop closure. Watch the map in rviz2 — when the loop closes, the previously-drifted geometry snaps into alignment. That snap is your signal the map is consistent.
7. When every room is covered and the loop has closed, save:
   ```bash
   ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
       "{name: {data: '<world>'}}"
   ```
8. Confirm `maps/<world>.pgm` and `maps/<world>.yaml` exist and the `map_run_timer` printed the elapsed time.

## Acceptance criteria

- [ ] The entire stack comes up from a single `ros2 launch` command (plus teleop and the timer in separate terminals).
- [ ] The world used was genuinely unseen before the timed run (document which option from "The setup" you used).
- [ ] The saved map covers all rooms and at least one loop closure is visibly resolved (straight single walls where you traversed twice).
- [ ] The `map_run_timer` reports an end-to-end time **< 15.0 minutes** from launch to save.
- [ ] `maps/<world>.pgm` and `maps/<world>.yaml` exist on disk.
- [ ] You write a `challenge-01-results.md` (250–400 words) containing:
  - The world name/source and how you obtained an unseen world.
  - The exact launch command.
  - The `map_run_timer` summary line (the elapsed-time log).
  - The saved-map image (embed the `.pgm` rendered to PNG).
  - A short paragraph on what you tuned in `slam_toolbox.yaml` to hit the budget, and what would have happened with the week-7 defaults.

## Going further (no extra grade, no time pressure)

- **Restart in localization mode.** After saving, kill the stack, then bring it up with `slam:=true` but `slam_toolbox` in `localization` mode against your saved map. Verify the robot localizes from a known initial pose. This is the mapping-vs-localization distinction from week 7, applied.
- **Halve the time.** Once you reliably hit fifteen minutes, optimize for ten: better coverage routing, a faster `minimum_travel_distance`, a higher teleop speed (without inducing scan-match failure). Senior teams obsess over this number; cold-boot-to-operational time is a real product metric.
- **Add a `world:=` you generated.** Build your own three-room `.sdf` with a deliberate loop, swap with a peer, and map each other's worlds. The peer-swap is the closest thing to the real milestone experience.
- **Two robots.** Bring the stack up twice with `namespace:=robot1` and `namespace:=robot2` in the same world and confirm both map independently without TF collisions. This previews the Phase 5 multi-robot work and validates that your namespacing from lecture 2 actually holds.

## Submission

Commit to your Week 8 repository at `challenges/challenge-01-cold-start/` containing:

- `challenge-01-results.md` — the writeup above.
- `maps/<world>.pgm` and `maps/<world>.yaml` — the saved map.
- `<world>.png` — the rendered map image embedded in the writeup.
- The world `.sdf` if you generated it (so the reviewer can re-run).

A reviewer passes this challenge by reading `challenge-01-results.md`, confirming the elapsed time is under fifteen minutes, inspecting the saved map for loop-closure quality, and — for full marks — re-running your one command on the same world and confirming a comparable result. The most common fail is not the time; it is a map with doubled walls because the loop never closed, or a command that does not reproduce on the reviewer's machine because of a hard-coded path.

---

**References**

- `slam_toolbox` — configuration and the `save_map` service: <https://github.com/SteveMacenski/slam_toolbox>
- ROS2 Jazzy — `teleop_twist_keyboard`: <https://github.com/ros-teleop/teleop_twist_keyboard>
- Steve Macenski et al. — "SLAM Toolbox" (the loop-closure back-end): <https://joss.theoj.org/papers/10.21105/joss.02783>
