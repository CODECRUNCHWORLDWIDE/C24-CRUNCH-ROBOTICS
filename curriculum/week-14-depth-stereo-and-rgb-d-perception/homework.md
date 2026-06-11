# Week 14 Homework

Six problems that drive the RGB-D literacy into your fingers. The full set should take about **5 hours**. Work in your Week 14 Git repository (the same workspace as the exercises and the `crunchbot_rgbd` mini-project) so every problem produces at least one commit you can point to at the Week 16 midterm.

The headline deliverable is **Problem 4 — the depth-camera characterization write-up**, the artifact that lets you answer "why this camera, and what's its useful range?" at the midterm. Treat it as a one-pager a reviewer reads, not a journal entry.

Each problem includes a short **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`). Have your RGB-D camera (or sim, or the recorded bag) publishing — Problems 1, 2, and 4 run against it.

---

## Problem 1 — The RGB-D topic audit table

**Problem statement.** Bring up your RGB-D camera (real, sim, or bag). For **every** topic it publishes, run `ros2 topic info <topic> -v` and `ros2 topic echo --field encoding --once` where relevant, and build a markdown table in `notes/week-14/rgbd-audit.md` with one row per topic and these columns:

| Topic | Type | Encoding | Reliability | Rate (Hz) | Frame | Notes |
|---|---|---|---|---|---|---|

Cover color, depth, aligned depth, both `camera_info` topics, the points topic, and the IMU.

**Acceptance criteria.**

- `notes/week-14/rgbd-audit.md` exists with one row per published topic (at least seven rows).
- Every QoS/encoding/rate value comes from real introspection, not memory.
- You explicitly note which depth encoding your camera uses (`16UC1` mm or `32FC1` m) and confirm every sensor stream is `BEST_EFFORT`.
- Committed.

**Hint.** `for t in $(ros2 topic list | grep camera); do echo "=== $t ==="; ros2 topic info "$t" -v; done`. The IMU runs much faster (~200 Hz) than the images (~30 Hz) — note the rate difference; it's why you can't naïvely sync them.

**Estimated time.** 35 minutes.

---

## Problem 2 — Verify your hand-rolled cloud against `depth_image_proc`

**Problem statement.** Run your Exercise-2 projector (or the mini-project node) and `depth_image_proc`'s `point_cloud_xyzrgb` node on the same depth stream. Transform both clouds into `base_link` and overlay them in rviz2. Confirm they coincide. Where they *don't*, diagnose why (unit, `cx/cy`, `u/v` transpose, alignment).

**Acceptance criteria.**

- A screenshot in `notes/week-14/projection-verify.md` showing both clouds overlaid in rviz2.
- A one-paragraph statement that they coincide (to floating-point/visual tolerance), or, if they don't, the specific bug you found and fixed.
- You confirm both clouds are metric using `measure_plane` (floor normal ≈ `(0,0,1)`, height ≈ 0).
- Committed.

**Hint.** If your cloud is offset from `depth_image_proc`'s by a constant, it's almost always a frame/alignment difference (raw depth vs aligned depth). If it's scaled, it's a unit bug. If it's mirrored, it's a `u`/`v` or `cx`/`cy` swap.

**Estimated time.** 50 minutes.

---

## Problem 3 — Reproduce and fix the unit bug on purpose

**Problem statement.** In a copy of your projector, deliberately remove the `16UC1`→metres conversion (read mm as if they were metres). Run it, observe the 1000× cloud in rviz2 (everything is kilometres away, the cloud is empty in the default view). Then add the encoding-branch fix back and confirm the cloud returns to metric. Document both states.

**Acceptance criteria.**

- `notes/week-14/unit-bug.md` shows the broken `measure_plane` output (height/RMS in the hundreds-of-metres) and the fixed output (metric).
- You state the rule in one sentence: read `image.encoding` and branch; `16UC1` is millimetres, `32FC1` is metres.
- Committed.

**Hint.** With the bug, `measure_plane`'s floor "height" will be ~1000× the real value (e.g. ~10 m instead of ~0.01 m), or the cloud will be entirely outside rviz2's default clip range. That number *is* the diagnostic.

**Estimated time.** 30 minutes.

---

## Problem 4 — The depth-camera characterization write-up (headline deliverable)

**Problem statement.** Characterize your depth camera's accuracy vs. distance — the artifact that lets you say "this camera's useful range for my robot is X." Place (or simulate) a flat target at 0.5, 1.0, 2.0, 3.0, and (if reachable) 4.0 m. At each distance, fit a plane to the cloud and record: the measured distance (vs. the true distance — a *bias* check) and the RMS flatness (a *noise* check). Plot RMS vs. distance and confirm it grows roughly as `Z²`. Then write a one-page characterization at `notes/week-14/depth-characterization.md`:

1. **Camera & config** — model, resolution, filters on/off, the intrinsics you read.
2. **Method** — how you placed the target and fit the plane.
3. **Results** — the bias and RMS table, and the RMS-vs-distance plot.
4. **The `Z²` confirmation** — does RMS grow with the square of distance? By how much?
5. **The useful range** — given a robot obstacle/grasp tolerance you state (e.g. ±1 cm for grasping), the maximum distance at which the camera meets it. *This is the headline number.*
6. **Failure surfaces** — one paragraph: which surfaces in your test environment defeat this camera (glass, dark, shiny), confirmed by observation.

**Acceptance criteria.**

- `notes/week-14/depth-characterization.md` exists, fits ~one page, and hits all six headings.
- The RMS-vs-distance data has at least four distances and a plot (or an ASCII table if you can't embed images).
- The "useful range" is a specific number tied to a specific stated tolerance, not "it seemed fine."
- At least one real failure surface is documented from observation, not just cited from the lecture.
- Committed.

**Hint.** In sim, the noise is too clean to show `Z²` clearly — add synthetic Gaussian noise that grows with `Z²` to your sim depth, or run this against the recorded real bag at a couple of distances. The point is the *method* and the useful-range conclusion; state honestly whether your numbers are real or sim.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — Filter chain A/B with a metric

**Problem statement.** On a *static* scene with a flat surface, run your camera (or sim) with the post-processing filters off, then with spatial + temporal on. Use `measure_plane`'s RMS flatness as the metric. Report the noise reduction. Then repeat on a *moving* scene (wave the camera or a target) and report the cost (the temporal filter's lag/smear).

**Acceptance criteria.**

- `notes/week-14/filter-ab.md` reports RMS flatness filters-off vs filters-on on the static scene (a ratio), and a qualitative or quantitative note on the moving-scene smear.
- You state the recommendation in one sentence: when to enable the temporal filter and when it hurts.
- Committed.

**Hint.** If you have a real RealSense, toggle the filters in `realsense-viewer` first to build intuition, then in the ROS2 driver's parameters. On Path B, use your Exercise-3 `TemporalFilter` class — the cost/benefit is the same shape.

**Estimated time.** 40 minutes.

---

## Problem 6 — Confidence-gate the cloud and prove the gate is live

**Problem statement.** Take your mini-project `gating.py` (or write a minimal version). Apply a range gate (`max_range_m`) and an invalid-pixel mask to your output cloud. Prove the gate is *live* by setting `max_range_m` to a small value and showing the cloud visibly shrinks (far points dropped), then to a large value and showing they return. Capture the point counts.

**Acceptance criteria.**

- `notes/week-14/gating.md` shows the output point count at two `max_range_m` settings (small and large) and confirms the small setting drops the far points.
- The invalid-pixel mask is confirmed: there is no slab of points at the camera origin (`Z ≈ 0`).
- You state why a robot should *drop* (not fill) unmeasurable regions for safety-relevant geometry.
- Committed.

**Hint.** `ros2 topic echo /crunchbot/points --field width --once` gives the point count for an unorganized cloud. Watch it drop as you tighten `max_range_m`. The invalid-mask check: `ros2 topic echo` a few points and confirm none are at `(0,0,0)`.

**Estimated time.** 30 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — RGB-D topic audit | 35 min |
| 2 — Verify vs depth_image_proc | 50 min |
| 3 — Reproduce the unit bug | 30 min |
| 4 — Depth-camera characterization (headline) | 1 h 15 min |
| 5 — Filter chain A/B | 40 min |
| 6 — Confidence-gate the cloud | 30 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_rgbd` [mini-project](./mini-project/README.md) is in the same workspace — Week 15 consumes its cloud. Then take the [quiz](./quiz.md) with your notes closed.
