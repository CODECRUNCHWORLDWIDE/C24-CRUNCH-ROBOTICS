# Mini-Project — `crunchbot_rgbd`: A Trustworthy RGB-D Bring-up

> Build a reusable RGB-D bring-up package that takes a depth camera (real or simulated) and produces a **synchronized, filtered, correctly-colored, confidence-gated** point cloud in the robot's `base_link` frame — a cloud where every point is metric, right-side-up, and *trustworthy*, with the parts the camera invented dropped rather than passed downstream.

This is the artifact that turns "the camera is plugged in" into "perception I can build on." After this week, an RGB-D camera is not a mystery stream of five topics with surprising encodings — it is one launch file that yields a cloud you can hand to next week's Open3D/PCL processing and, four weeks out, to the fused perception node you defend at the Week 16 midterm.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This cloud is the **exact input Week 15 assumes** — voxel downsampling, RANSAC ground segmentation, and Euclidean clustering all run on the `/crunchbot/points` your bring-up publishes. And the confidence-gating discipline you build here is what lets the Week 16 fused perception node hit its latency budget without choking on fabricated points. Build it well now; it's load-bearing for the next two weeks.

---

## What you will build

A small ament-python package `crunchbot_rgbd` with three deliverables:

1. **`crunchbot_rgbd/rgbd_node.py`** — the core node. It synchronizes color + depth + camera-info (`message_filters`), back-projects depth to a metric cloud using the intrinsics, colors it from the *aligned* color image, transforms it into `base_link` via tf2, gates it on a confidence/validity rule, and publishes `/crunchbot/points` (`PointCloud2`, XYZRGB) at the camera rate.
2. **`crunchbot_rgbd/measure_plane.py`** — the verifier. Subscribes to the output cloud, fits a plane to the floor (and optionally a wall), and reports the plane normal, height, and RMS flatness — the "metric and right-side-up" promise from the README, as a runnable check.
3. **A launch file** (`launch/rgbd.launch.py`) that brings up the camera (real RealSense, or the sim/bag, selectable by a launch argument), the `rgbd_node`, and an rviz2 with a saved layout showing the cloud in `base_link`.

By the end you have a public repo of ~300–400 lines of Python that any future crunchbot package can launch to get a trustworthy cloud, and a one-command verification that the cloud is metric.

---

## Why a node and not just `depth_image_proc`

`depth_image_proc` already projects depth to a cloud — so why build a node? Because `depth_image_proc` gives you a *raw* cloud: every point, including the fabricated ones (flying pixels, `Z²` noise, glass readings). It does not gate on confidence, it does not range-threshold, and it does not know your robot's tolerance. Your node wraps the projection with the *judgment* a robot needs:

- **Confidence/validity gating** — drop pixels the camera couldn't measure (invalid sentinel) and pixels beyond the camera's useful range (the `Z²` threshold from Lecture 1).
- **Discontinuity rejection** — drop the flying-pixel skirt at depth edges.
- **One frame, one policy** — the cloud arrives in `base_link`, stamped with the acquisition time, ready for downstream consumers that shouldn't each re-derive the transform.

You may *use* `depth_image_proc` internally for the raw projection if you like — but the gating, the framing, and the verification are yours, because they encode decisions only you can make for your robot.

---

## Package layout

```
crunchbot_rgbd/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunchbot_rgbd
├── crunchbot_rgbd/
│   ├── __init__.py
│   ├── rgbd_node.py           # sync + project + color + transform + gate + publish
│   ├── measure_plane.py       # the "metric and right-side-up" verifier
│   └── gating.py              # the confidence/range/discontinuity gate (testable)
├── launch/
│   └── rgbd.launch.py
├── rviz/
│   └── rgbd.rviz
└── test/
    ├── test_gating.py         # unit tests for the gate logic
    └── test_projection.py     # unit tests for the back-projection math
```

---

## Deliverable 1 — `rgbd_node.py` (the core)

It must, on every synchronized frame:

1. **Synchronize** color, depth, and color-info with `ApproximateTimeSynchronizer` (slop < one frame period), all subscribers using `qos_profile_sensor_data` (sensor QoS — Week 5).
2. **Convert depth to metres** by branching on `image.encoding` (`16UC1` → divide by 1000; `32FC1` → as-is). Never assume.
3. **Back-project** with the intrinsics, vectorized (no per-pixel loop), masking the invalid sentinel.
4. **Gate** the points through `gating.py`:
   - drop invalid/hole pixels,
   - drop points beyond `max_range_m` (the `Z²` confidence threshold; default 3.0 m, a parameter),
   - drop flying pixels by a depth-discontinuity gradient threshold.
5. **Color** each surviving point from the *aligned* color image at its `(u, v)` (so color lands on the right geometry — Lecture 2 §5).
6. **Transform** the cloud into `base_link` with tf2 (look up `base_link ← depth_optical_frame` at the frame's stamp).
7. **Publish** `/crunchbot/points` as XYZRGB `PointCloud2`, stamped with the **acquisition time**, `frame_id = base_link`.

Parameters (declared, documented, settable from the launch file): `max_range_m`, `discontinuity_threshold_m`, `target_frame` (default `base_link`), `slop_s`, the input topic names.

---

## Deliverable 2 — `measure_plane.py` (the verifier)

A node/script that subscribes to `/crunchbot/points`, segments the dominant horizontal plane (the floor) with a simple RANSAC-or-least-squares fit, and prints:

```
floor plane: normal=(0.00, 0.00, 1.00), height=+0.01 m, rms=0.004 m   [FLAT, level]
```

It is the runnable form of the "metric and right-side-up" promise. A correct cloud has the floor normal ≈ `(0, 0, 1)` in `base_link` (z-up), the floor height ≈ 0, and a small RMS. If the normal points sideways, your optical-frame TF is wrong; if the height is off by a metre, your transform or units are wrong; if the RMS is large, you didn't gate the `Z²` noise. This script *is* the acceptance test for the cloud.

---

## Deliverable 3 — the launch file

`launch/rgbd.launch.py` brings up the whole chain with one command and a `source` argument:

```bash
ros2 launch crunchbot_rgbd rgbd.launch.py source:=realsense   # real D435i
ros2 launch crunchbot_rgbd rgbd.launch.py source:=sim         # Gz Sim RGB-D
ros2 launch crunchbot_rgbd rgbd.launch.py source:=bag bag:=/path/to/bag
```

It starts the camera (or sim, or bag), the `rgbd_node`, and rviz2 with `rviz/rgbd.rviz` showing the cloud in `base_link` plus the TF tree. One command, a trustworthy cloud on screen.

---

## Rules

- **You may** read the ROS2 docs, the lecture notes, `realsense-ros`, `depth_image_proc`, and `message_filters` source.
- **You must** branch on `image.encoding` for the unit conversion — no hard-coded `/1000`. A node that assumes `16UC1` and silently mishandles `32FC1` fails the project's reason to exist.
- **You must** gate on confidence/range — the output cloud must drop invalid pixels and points beyond `max_range_m`. A node that publishes every raw point (including `Z²` noise and flying pixels) is `depth_image_proc`, not this project.
- **You must not** color from *unaligned* depth — color comes from the aligned image (or you do the extrinsic warp yourself). An unaligned colored cloud fails.
- **You must** stamp the output cloud with the *acquisition* time, not `now()` (Week 5 §3.1).
- Python 3.12 (Ubuntu 24.04 default), `rclpy` + NumPy on Jazzy. The vectorized projection must run at the camera rate; a per-pixel Python loop will not.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-14-crunchbot-rgbd-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_rgbd` succeeds with no warnings.
- [ ] `ros2 launch crunchbot_rgbd rgbd.launch.py source:=sim` (or `realsense`/`bag`) brings up the camera, the node, and rviz2 in one command.
- [ ] `/crunchbot/points` publishes XYZRGB `PointCloud2` in `base_link` at ~the camera rate; `ros2 topic info -v` shows sensor QoS on the input subscriptions.
- [ ] `ros2 run crunchbot_rgbd measure_plane` reports the floor normal ≈ `(0, 0, 1)`, height ≈ 0, and a small RMS — the "metric and right-side-up" promise.
- [ ] The cloud drops invalid pixels and points beyond `max_range_m`; setting `max_range_m:=0.5` visibly shrinks the cloud, proving the gate is live.
- [ ] Color lands on the correct geometry (the red box is red where the box is, not smeared beside it) — demonstrated in rviz2.
- [ ] `colcon test --packages-select crunchbot_rgbd` passes, with at least:
  - `test_projection.py`: a known synthetic depth back-projects to the known geometry (the Exercise-2 verification, as a unit test).
  - `test_gating.py`: the gate drops invalids, drops beyond-range points, and drops a synthetic flying-pixel edge.
- [ ] A `README.md` with the launch commands, a screenshot of the cloud in rviz2, and the `measure_plane` output.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Projection correctness** | 25 | Vectorized back-projection; encoding-branched unit conversion; metric, right-side-up cloud; `measure_plane` confirms normal/height/RMS. |
| **Synchronization & alignment** | 20 | `ApproximateTime` with sane slop; sensor QoS on inputs; color from the *aligned* image, landing on the right geometry. |
| **Confidence/range/discontinuity gating** | 25 | Invalid pixels dropped; `max_range_m` enforced (and demonstrably live); flying-pixel skirt rejected. |
| **Framing & stamping** | 10 | Output in `base_link` via tf2; stamped with the acquisition time, not `now()`. |
| **Tests** | 10 | Projection and gating unit tests; `colcon test` green. |
| **Launch & docs** | 10 | One-command bring-up with the `source` argument; clear README; rviz layout checked in. |

**90+** is portfolio-grade and ready to feed Week 15's point-cloud processing. **70–89** works but leaks fabricated points or smears color. **Below 70** means the cloud isn't trustworthy — fix the gating and the alignment first.

---

## What "good" looks like at the demo

When you launch this node and view it in rviz2, a *correct* result is unmistakable, and knowing the tells lets you self-grade before submission:

- **The floor is flat and level.** In `base_link`, the floor is a plane at `z ≈ 0` — not tilted, not curved. `measure_plane` confirms the normal ≈ `(0, 0, 1)` and a small RMS. A tilted floor means the optical-frame TF is wrong; a curved one means lens distortion isn't handled (rectification).
- **Distances are metric.** A box known to be 30 cm tall measures ~30 cm in the cloud, a wall 1 m away sits at `x ≈ 1.0`. If everything is 1000× off, it's the unit bug; if it's off by 10%, it's intrinsics or rectification.
- **Color lands on geometry.** A red object's points are red; the color tracks the object as it moves, not smeared beside it. Smearing on moving objects is a sync problem; smearing on static near objects is an alignment problem.
- **The holes are honest.** Glass and dark surfaces show as *gaps* in the cloud (dropped), not as fake surfaces and not as a slab at the origin. A slab at `z ≈ 0` means you didn't mask invalids; a fake surface where glass is means you hole-filled (don't, for safety-relevant geometry).
- **The gate is live.** Tightening `max_range_m` visibly shrinks the cloud; loosening it grows it. A cloud that doesn't respond is a gate that isn't wired.

If all five hold, the node is portfolio-grade and ready to feed Week 15. If any fails, the tell points at the stage to fix — and that diagnostic clarity is itself a skill the week builds.

## Common failure modes and their fixes

- **"The cloud is sideways."** Optical-frame TF missing or wrong. Fix: verify `tf2_echo base_link camera_depth_optical_frame` resolves with the expected ~90° rotation pair.
- **"Everything is 1000× too far."** Read `16UC1` as metres. Fix: branch on `image.encoding`, divide millimetres by 1000.
- **"A wall of points at the camera."** Unmasked holes (`0`/`NaN` treated as points). Fix: `valid = isfinite & (z > 0)` before projecting.
- **"The camera publishes but my subscriber gets nothing."** QoS mismatch — your subscriber is `RELIABLE`, the camera is `BEST_EFFORT`. Fix: `qos_profile_sensor_data` on every sensor subscription (Week 5).
- **"Color is offset from the geometry."** Coloring from raw (unaligned) depth. Fix: color from `aligned_depth_to_color` (or warp via the extrinsic).
- **"The node runs at 2 Hz."** A per-pixel Python loop in the projection. Fix: vectorize with NumPy `meshgrid` — never loop over pixels.

Each failure has a distinct signature and a known fix; recognizing them rather than randomly tweaking is the disciplined-debugging habit the week is teaching, and the exact skill the Week 16 midterm tests.

## Stretch goals

- **Two cameras, one cloud.** Bring up a second RGB-D camera (or a second sim camera) facing a different direction, transform both into `base_link`, and publish a merged cloud. Now you have a wider field of view — and a new failure mode (the two clouds disagree in the overlap if either extrinsic is wrong).
- **Confidence overlay in Foxglove.** Publish a second debug topic that colors each point by its confidence (green = high, red = near the range threshold) so the dashboard *shows* which points are trustworthy. This is the visualization that makes "the camera invented this" visible at a glance.
- **The `Z²` range curve, automated.** Add a mode to `measure_plane.py` that drives the camera (or you move a target) to several distances and fits the depth-error-vs-distance curve, confirming the `Z²` law and reporting your camera's useful range for a given tolerance.
- **Drop in `depth_image_proc`.** Replace your hand-rolled projection with `depth_image_proc`'s node for the raw cloud, keep your gate/transform/color stages, and confirm `measure_plane` reports the same numbers — proving your projection math matched the production node.

---

## Implementation guidance — the order that avoids the bugs

The single biggest determinant of whether this project goes smoothly is the *order* you build it in. Build it bottom-up, verifying each stage before adding the next, so a bug is always in the thing you just added:

1. **Conversion first.** Write and unit-test the `16UC1`/`32FC1`→metres conversion in `gating.py` (or a small `conversions.py`) before anything else. A unit test that asserts `1500` in `16UC1` → `1.5 m` catches the #1 bug before it can hide in a live pipeline.
2. **Projection, verified against the synthetic scene.** Port your Exercise-2 `back_project` and verify it on a known synthetic depth image (floor + wall + box at known distances) in a unit test. Now your math is proven independent of the camera.
3. **Live projection, no gating yet.** Wire the projector to the live camera, publish the raw cloud, and confirm it's metric and right-side-up with `measure_plane` *before* adding gating. If the floor normal is sideways here, it's the optical-frame TF, and you fix it now — not after you've layered gating on top and can't tell which stage broke.
4. **Synchronization and color.** Add the `message_filters` sync and color from the aligned image. Confirm in rviz2 that color lands on the right geometry (wave a colored object; the color should track it, not smear).
5. **Gating last.** Add the confidence/range/discontinuity gate. Prove it's live by toggling `max_range_m` and watching the cloud shrink. Gating is last because it's the easiest to verify once everything under it is known-good.

Building top-down — gating first, then wondering why the cloud is empty — is the path to an afternoon of confusion. Bottom-up, each stage verified, is the path to a working node by Saturday. The `test_projection.py` and `test_gating.py` requirements exist precisely to force this order: you can't write the projection test without working projection, and you can't write the gating test without a working gate.

## A note on the confidence model

The mini-project asks you to gate on "confidence," and you have a design decision to make about what that means, because not every camera exposes a confidence map. Three options, in increasing fidelity:

- **The invalid sentinel as a binary confidence.** Every depth camera gives you this for free: `0`/`NaN` is "no confidence," everything else is "confident." This is the floor, and it's enough to pass the project — drop the holes.
- **Range-thresholded confidence.** Add the `Z²` insight (Lecture 1 §2): trust depth under `max_range_m`, drop beyond it, because the error there exceeds your tolerance. This is the `max_range_m` gate, and it's the highest-value addition — it drops the noisy far field that would otherwise produce garbage clusters next week.
- **A real confidence map, if your camera exposes one.** Some cameras (and the RealSense SDK in certain modes) publish a per-pixel confidence. If yours does, gate on it directly; if not, the invalid-sentinel + range threshold is a perfectly defensible confidence model, and you say so in your README.

The point the grader looks for is not a sophisticated confidence model — it's that you *have* one, you can *articulate* it, and the output cloud *honors* it (fabricated points are dropped, not passed downstream). "I gate on the invalid sentinel plus a `Z²`-derived range threshold of 3 m, because beyond that my D435i's depth error exceeds my obstacle tolerance" is a complete, defensible answer. The anti-pattern is publishing every raw point and calling it confidence-gated; that's the thing this project exists to prevent.

## How this connects to the rest of C24

- **Week 15 (point clouds, Open3D, PCL)** consumes `/crunchbot/points` directly: voxel-downsample it, RANSAC the ground plane, cluster the rest into object proposals. Your gating is what keeps those clusters from being flying-pixel garbage.
- **Week 16 (Phase 2 integration + midterm)** folds this bring-up into the fused perception node and the perception latency budget. Your confidence gate is part of why the node hits 30 ms — it isn't projecting and clustering points the camera invented.
- **Capstone** (the tabletop pick-and-place) grasps objects this cloud localizes. A grasp planner that trusts a flying pixel grasps at air; your gate is the first line of defense.

When you've finished, push the repo and take the [quiz](../quiz.md).
