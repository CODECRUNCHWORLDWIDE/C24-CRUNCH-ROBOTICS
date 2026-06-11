# Challenge 1 — Force a missed loop closure, then tune it closed

> **Estimated time:** 90–120 minutes. Worth more than its time-cost suggests; this is the canonical shape of senior SLAM work — operating at the knife-edge between catching true loops and rejecting false ones.

You will deliberately make `slam_toolbox` **miss a real loop closure**, watch the map fold or double, diagnose *exactly which mechanism failed*, prove with a manual loop closure that the back-end would have fixed it, and then tune the loop-closure parameters until the loop closes *automatically* — documenting the single constraint that made the difference. This is the difference between "I ran SLAM" and "I understand the data-association trade-off at the heart of every estimation system I will ever ship."

## Why this matters

A SLAM map is only as good as its loop closures (Lecture 1, §1.6). A missed loop closure leaves the drift uncorrected — the map bends, walls double, the far end of a corridor lands tens of centimetres off. A *false* loop closure is worse: the back-end optimizes toward the lie and folds the map in half, confidently and cleanly. The entire craft is keeping the gap open between "loose enough for true loops" and "strict enough against false ones." You cannot learn that gap by reading about it; you learn it by standing on the edge of it once, on purpose. That is this challenge.

## The setup: a world that drifts before it revisits

The key to forcing a *missed* (not false) loop closure is a world where the robot accumulates enough drift before it returns that the true revisit is either (a) outside the candidate search distance, or (b) too poorly aligned to clear the response threshold. The cleanest way to produce this is a **long, feature-poor loop**: a corridor loop where the straight segments give the scan matcher little to lock onto, so drift accumulates, *and* the return approach is long enough that by the time the robot is back, the drifted estimate places the start node beyond the default `loop_search_maximum_distance`.

Build (or adapt from exercise 1) a world like this:

```xml
<!-- A long, thin rectangular loop corridor: 20 m x 12 m outer, 2 m wide corridor
     all the way around. Feature-poor straights + four corners. The robot drives
     the full perimeter loop and returns to its start. By the return, scan-matched
     odometry has drifted ~0.3-0.6 m -- enough that the default 3 m loop search may
     still find it, so we make the loop LONGER or the corridor FEATURELESS to push
     the drift past the search radius. Tune the dimensions until the loop reliably
     MISSES with the exercise-1 default parameters. -->
<model name="loop_corridor_walls">
  <static>true</static>
  <link name="link">
    <!-- outer rectangle, 20 x 12 -->
    <collision name="o_s_c"><pose>0 -6 1 0 0 0</pose><geometry><box>
      <size>20 0.2 2</size></box></geometry></collision>
    <visual    name="o_s_v"><pose>0 -6 1 0 0 0</pose><geometry><box>
      <size>20 0.2 2</size></box></geometry></visual>
    <collision name="o_n_c"><pose>0 6 1 0 0 0</pose><geometry><box>
      <size>20 0.2 2</size></box></geometry></collision>
    <visual    name="o_n_v"><pose>0 6 1 0 0 0</pose><geometry><box>
      <size>20 0.2 2</size></box></geometry></visual>
    <collision name="o_w_c"><pose>-10 0 1 0 0 0</pose><geometry><box>
      <size>0.2 12 2</size></box></geometry></collision>
    <visual    name="o_w_v"><pose>-10 0 1 0 0 0</pose><geometry><box>
      <size>0.2 12 2</size></box></geometry></visual>
    <collision name="o_e_c"><pose>10 0 1 0 0 0</pose><geometry><box>
      <size>0.2 12 2</size></box></geometry></collision>
    <visual    name="o_e_v"><pose>10 0 1 0 0 0</pose><geometry><box>
      <size>0.2 12 2</size></box></geometry></visual>
    <!-- inner rectangle, 16 x 8 -> leaves a 2 m corridor all the way around -->
    <collision name="i_s_c"><pose>0 -4 1 0 0 0</pose><geometry><box>
      <size>16 0.2 2</size></box></geometry></collision>
    <visual    name="i_s_v"><pose>0 -4 1 0 0 0</pose><geometry><box>
      <size>16 0.2 2</size></box></geometry></visual>
    <collision name="i_n_c"><pose>0 4 1 0 0 0</pose><geometry><box>
      <size>16 0.2 2</size></box></geometry></collision>
    <visual    name="i_n_v"><pose>0 4 1 0 0 0</pose><geometry><box>
      <size>16 0.2 2</size></box></geometry></visual>
    <collision name="i_w_c"><pose>-8 0 1 0 0 0</pose><geometry><box>
      <size>0.2 8 2</size></box></geometry></collision>
    <visual    name="i_w_v"><pose>-8 0 1 0 0 0</pose><geometry><box>
      <size>0.2 8 2</size></box></geometry></visual>
    <collision name="i_e_c"><pose>8 0 1 0 0 0</pose><geometry><box>
      <size>0.2 8 2</size></box></geometry></collision>
    <visual    name="i_e_v"><pose>8 0 1 0 0 0</pose><geometry><box>
      <size>0.2 8 2</size></box></geometry></visual>
  </link>
</model>
```

You may also (or instead) force the miss by *degrading the parameters* from the exercise-1 baseline: shrink `loop_search_maximum_distance` to `1.5`, raise `loop_match_minimum_response_fine` to `0.65`, or raise `loop_match_minimum_chain_size` to `25`. Any of these will cause a real loop to be missed. The point is to produce the *observable inconsistent map*, then explain which knob caused it.

## Step 1 — Reproduce the miss

Map the loop world (sync mode, off a recorded bag so the drive is repeatable — exercise 3 shows how to record one). Drive the full perimeter loop and return to the start. With the failing parameters, you should see one of:

- **Doubled walls.** The corridor's outer wall is mapped twice, offset by the accumulated drift — two parallel black lines where there is one wall.
- **A folded / open loop.** The map does not close into a rectangle; the return corridor lands rotated or translated off the start, leaving an open gap or an overlapping fold.

Confirm `slam_toolbox` logged **no** `Loop closure found` line for the true revisit. Save this broken map (`map_saver_cli -f ~/maps/broken`). Screenshot the RViz view. This is your **before**.

## Step 2 — Diagnose which mechanism failed

There are exactly three reasons a true loop is missed (Lecture 1, §1.6; Lecture 2, §2.2):

1. **The candidate was never found** — `loop_search_maximum_distance` is smaller than the accumulated drift, so the start node is "too far" in the drifted estimate to be a candidate. Diagnostic: estimate your drift at the return (compare the SLAM pose to ground truth, exercise 2's metric) and compare it to `loop_search_maximum_distance`. If drift > search distance, this is your cause.
2. **The chain was too short to match** — `loop_match_minimum_chain_size` requires more consecutive nodes than the revisit region provides, so the chain match never runs. Diagnostic: the corridor is feature-poor and the chain of nodes around the candidate is ambiguous; a smaller chain or a richer revisit area is needed.
3. **The response did not clear the gate** — a candidate *was* found and a chain *was* matched, but the correlative-scan-match response stayed below `loop_match_minimum_response_fine`. Diagnostic: `slam_toolbox` may log a rejected candidate; the feature-poor corridor gives a broad, low response peak.

Determine *which one* applies to your failure. The honest way: bump `slam_toolbox`'s log level to debug (`--ros-args --log-level slam_toolbox:=debug`) and watch what it says about loop-closure candidates during the return. If it never mentions a candidate, it is cause (1). If it mentions a candidate but rejects it, it is (2) or (3).

## Step 3 — Prove the back-end is innocent (manual loop closure)

Before tuning the front-end thresholds, prove the *back-end* would fix the map if only the edge existed — this isolates the failure to the front-end candidate/threshold logic. Use the RViz SlamToolbox panel's **manual loop closure** (Lecture 2, §2.9): select the current node and the start node and force a loop-closure edge. Watch the back-end re-optimize and the doubled walls merge / the loop close. This confirms: the geometry is closable; the optimizer works; what failed was the *automatic detection*. Note this in your writeup — it is the step that separates "the back-end is broken" (it is not) from "the front-end missed it" (it did).

## Step 4 — Tune it closed, minimally

Now make the loop close *automatically*, with the **minimal** change. Work one parameter at a time, in this order (least-dangerous first):

1. If the cause was (1), raise `loop_search_maximum_distance` just past your measured drift (e.g. drift 3.4 m → set 4.5 m, not 20 m). This is the *safest* change — it only widens *which* old nodes are candidates; the response gate still rejects bad matches.
2. If the cause was (3), lower `loop_match_minimum_response_fine` just enough to admit the true match (e.g. true match scored 0.52 → set the gate to 0.48, not 0.1). This is *more dangerous* — a lower gate admits more false positives — so argue why this world's geometry will not produce a false match at the new gate.
3. If the cause was (2), lower `loop_match_minimum_chain_size` to fit the available nodes, or add features to the revisit region.

Re-map the *same bag*. Confirm `slam_toolbox` now logs `Loop closure found` for the true revisit and the map closes — single-thick walls, a closed rectangle. Save this map (`map_saver_cli -f ~/maps/fixed`). Screenshot it. This is your **after**.

## Step 5 — Argue you did not open the door to false positives

The hard part of the grade: show that your fix closes the *true* loop **without** making a *false* one likely. For this world, the argument is geometric — there is only one place that looks like the start (it is not a symmetric world with two identical corridors), so widening the search or lowering the gate cannot match the wrong node. If you tested on a *symmetric* world, you would have to show the false match does *not* fire at your new settings (drive it and confirm no spurious loop closure folds the map). State the argument explicitly. "I lowered the gate and it closed" is not enough; "I lowered the gate to 0.48, the true match scores 0.52, the next-best wrong candidate in this world scores 0.21, so a 0.48 gate admits the true match with a 0.31 margin and rejects the wrong one with a 0.27 margin" is the answer.

## Acceptance criteria

- [ ] You produced a **broken map** (doubled walls or a folded loop) where a *real* loop closure was missed, with the failing parameter file saved and the RViz screenshot captured. `slam_toolbox` logged no `Loop closure found` for the true revisit.
- [ ] You **diagnosed** which of the three mechanisms (search distance / chain size / response gate) caused the miss, with evidence (the drift-vs-search-distance comparison, or the debug log showing a rejected candidate).
- [ ] You used **manual loop closure** in RViz to prove the back-end closes the map when the edge is supplied, isolating the failure to the front-end.
- [ ] You tuned the loop **closed automatically** with the **minimal** change, saved the fixed parameter file, and captured the after-map showing single-thick walls and a closed loop. `slam_toolbox` logged `Loop closure found` for the true revisit.
- [ ] You wrote a 1–2 page `results.md` containing: the before/after maps, the failing and fixed parameter diffs, the diagnosis, and the **single-sentence statement of the constraint that fixed it** (e.g. "raising `loop_search_maximum_distance` from 1.5 to 4.5 m made the start node a candidate; the existing 0.45 fine gate then accepted the 0.61-response match").
- [ ] You included the false-positive argument from Step 5 — why your fix does not admit a false loop in this world.

## Hints

1. **Make the bag once.** Record one drive of the loop, then replay it for every parameter trial. Comparing parameter sets across *different* drives is uncontrolled and you will chase noise. Same bag, same trajectory, only the parameters change.

2. **Debug logging is your friend.** `--ros-args --log-level slam_toolbox:=debug` makes `slam_toolbox` narrate its loop-closure search — candidates found, chains matched, responses scored, accept/reject. This turns "it didn't close" into "it found a candidate at node 14, matched a chain of 8, scored 0.38, and rejected it against the 0.45 gate." That is your diagnosis, written by the node itself.

3. **Measure the drift before you blame the search distance.** Use exercise 2's ground-truth comparison to read how far the SLAM pose has drifted by the time the robot returns. If the drift is 3.4 m and `loop_search_maximum_distance` is 3.0 m, you have your cause without guessing.

4. **Change one thing at a time.** The temptation is to loosen all five loop-closure parameters at once and declare victory. You will not know *which* change mattered, and you will probably have opened the false-positive door. One parameter, re-map, observe, revert if it did not help.

5. **The minimal fix is the graded fix.** A reviewer can tell the difference between "raised the search distance 1.5 m past the measured drift" (surgical, defensible) and "set every threshold to its loosest value" (a sledgehammer that will fold the next map). The challenge rewards the scalpel.

## Going further (no extra grade, no time pressure)

- **Build the false-positive world.** Make a *symmetric* world — two identical corridors — and watch a *false* loop closure fold the map (Lecture 1, §1.8, experiment 2). Then defend against it: raise the chain size and the response gate until the false match is rejected, and confirm the true loop still closes. This is the harder, more realistic version of the challenge.
- **Plot `map → odom` over time** through the loop closure (PlotJuggler, from Week 6). The discontinuous *jump* when the loop fires is REP-105's design in a time series (Lecture 2, §2.7). Annotate the jump magnitude — it is the drift the loop closure corrected.
- **Quantify the correction.** Compute the SLAM trajectory's absolute pose error against ground truth (`evo_ape`, resources.md) before and after the loop closes. Report the metres of drift the single loop closure removed.

## Submission

Commit to your Week 7 GitHub repository at `challenges/challenge-01-loop-closure/` containing:

- `worlds/loop_corridor.sdf` (or the bag of the failing drive).
- `config/params_failing.yaml` and `config/params_fixed.yaml`.
- `maps/broken.pgm` + `maps/fixed.pgm` and the two RViz screenshots.
- `results.md` — the before/after, the diagnosis, the single-sentence fix, and the false-positive argument.

The instructor reviews by reading `results.md` and re-mapping your bag with both parameter files. A submission whose `params_fixed.yaml` does not actually close the loop on a re-run is the most common review-fail; verify your fix reproduces before submitting.

---

**References**

- `slam_toolbox` configuration (the loop-closure parameter group): <https://github.com/SteveMacenski/slam_toolbox#configuration>
- Olson — "Real-Time Correlative Scan Matching" (the response score you are gating on): <https://april.eecs.umich.edu/pdfs/olson2009icra.pdf>
- Grisetti et al. — "A Tutorial on Graph-Based SLAM" (why the back-end fixes the map once the edge exists): <https://www.dfki.de/fileadmin/user_upload/import/8336_GraphSLAM-Tutorial-Grisetti.pdf>
- REP-105 (the `map → odom` jump on loop closure): <https://www.ros.org/reps/rep-0105.html>
