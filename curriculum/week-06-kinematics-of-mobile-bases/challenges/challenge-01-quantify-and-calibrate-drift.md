# Challenge 1 — Quantify how drift scales, then calibrate one correction that reduces it

> **Estimated time:** 120–150 minutes. This is the week's signature artifact. It is the experiment that turns "odometry drifts" into a defensible engineering claim with a number, a cause, and a fix.

You have an odometry node (Exercise 2) and a square-driver that logs odom vs ground truth (Exercise 3). Now you run a controlled experiment. The deliverable is a short report that answers three questions with data:

1. **How does closure error scale with commanded speed?** (Probes slip — the non-systematic, non-calibratable error.)
2. **How does closure error scale with commanded turn rate?** (Probes heading injection — the dominant systematic error.)
3. **Can you fit one calibration correction that measurably reduces the systematic error?** (Probes whether you understand which knob to turn.)

You may not "fix" the drift by closing a loop on pose, by fusing an IMU, or by running SLAM. Those are later weeks. The only intervention allowed is a *calibration* — adjusting `wheel_radius` and/or `wheel_separation` so the model better matches the physics.

---

## Setup: induce a known miscalibration (so there is something to find)

A perfectly-tuned Gz Sim robot drifts only from slip and integration error, which makes the calibration step anticlimactic. To make the experiment real, **introduce a deliberate, known systematic error** between the simulator's physics and your odometry node's parameters, then *recover* it from the closure data. Two ways:

- **Sim-side (preferred):** in your Week 3 URDF / Gz `diff_drive` plugin, set the *true* wheel radius to `0.0505` and wheel separation to `0.2955` while leaving your odometry node at the nominal `0.05` / `0.30`. The simulator now moves the robot with the true parameters; your node integrates with the wrong ones. This mirrors the real world exactly: the URDF is a *claim* and the hardware disagrees.
- **Node-side (if you cannot edit the sim):** drive the real (well-tuned) sim, but feed your odometry node deliberately-wrong parameters (`wheel_radius:=0.0495`, `wheel_separation:=0.309`). Same effect: a known gap between model and motion.

Record the *true* values — they are the answer key for your calibration. The challenge is to recover a correction close to them from closure error alone, *without* peeking until the end.

---

## Part 1 — The speed sweep

Drive the 10×10 m square at **three speeds**: `0.25`, `0.5`, `1.0 m/s`, holding turn rate fixed at `0.5 rad/s`. Run each speed **three times** (slip is stochastic; you want a mean and a spread). For each run record:

- The **drift** (odom-end vs ground-truth-end distance), the headline number from Exercise 3.
- The **true closure error** (ground-truth end vs ground-truth start).
- The **odom closure error** (odom end vs odom start) — the "optimistic" number.

Tabulate mean ± std of drift per speed. Then answer, in your report: **does drift grow with speed?** Decompose:

- The *systematic* component (radius/wheelbase miscalibration) is speed-independent — it is a percentage error that applies equally at any speed.
- The *slip* component grows with speed and acceleration.

If your drift is roughly flat across speed, your error is dominated by your induced miscalibration (good — Part 3 will fix it). If it grows with speed, you are also seeing Gz Sim's friction/slip model. Report which you observe and how you can tell them apart. A clean way to separate them: subtract the predicted systematic drift (from your known miscalibration) and attribute the residual growth to slip.

---

## Part 2 — The turn-rate sweep

Hold speed fixed at `0.5 m/s` and drive the square at **two turn rates**: `0.5` and `1.5 rad/s` (slower vs snappier corners), three runs each. Tabulate drift mean ± std per turn rate.

The expected signature (Lecture 1, §1.3): **turn rate is where heading error is injected.** A wheelbase miscalibration produces an angular error *per corner*; snappier corners do not change the per-corner systematic angle error much, but they *do* increase corner slip (the robot is yawing faster, the wheels skid more), so faster turns should show *more* drift if slip is present. Report whether your data shows turn rate amplifying drift more steeply than the straight-line speed sweep did — this is the experimental fingerprint of heading-dominated error.

---

## Part 3 — Fit and test a calibration correction

Now fix it. You have two correctable parameters; pick the dominant one (Lecture 1 says heading dominates, so the **wheelbase** is usually the bigger lever, but a pure distance scale on a straight run is the easier fit). Two acceptable methods:

### Method A — Single radius / wheelbase scale from one direction

From a straight-line segment, the ratio of true distance travelled (ground truth) to odometry-reported distance gives a **radius scale factor**:

```
radius_scale = true_distance / odom_reported_distance
new_wheel_radius = wheel_radius * radius_scale
```

From a pure-rotation segment (drive an in-place 360° and compare ground-truth yaw to odom yaw), the ratio gives a **wheelbase correction**:

```
wheelbase_scale = odom_reported_yaw / true_yaw
new_wheel_separation = wheel_separation * wheelbase_scale
```

(The wheelbase sits in the denominator of `ω`, so an over-reported yaw means your assumed `L` is too small — scale it up.)

### Method B — UMBmark (the rigorous version)

Drive the square **clockwise five times and counter-clockwise five times** (Lecture 1, §1.6). Take the centroid of the five CW end points and the five CCW end points. The CW/CCW *common* offset isolates the wheel-diameter error `Ed`; the CW/CCW *differential* offset isolates the wheelbase error `Eb`. Apply both corrections. This is more work but separates the two systematic errors cleanly and reports the non-systematic scatter as a bonus.

### Test

Re-run the speed sweep with the corrected parameters. **Show the drift drop.** The acceptance bar is a *measurable* reduction in the systematic component — at the speed where slip is smallest (`0.25 m/s`), the corrected drift should fall to a fraction of the uncorrected drift. Plot uncorrected vs corrected closure error on the same axes.

---

## Acceptance criteria

- [ ] A table of drift (mean ± std over 3 runs) across the three speeds at fixed turn rate.
- [ ] A table of drift (mean ± std over 3 runs) across the two turn rates at fixed speed.
- [ ] A stated, defended claim about which error class dominates your robot, with the speed/turn-rate signature as evidence.
- [ ] A fitted calibration correction (radius scale and/or wheelbase scale), with the arithmetic shown, recovered from closure/yaw data **before** you reveal the true induced values.
- [ ] A before/after comparison showing the systematic drift component measurably reduced after applying the correction. At `0.25 m/s` the corrected drift is < 50% of the uncorrected drift.
- [ ] The recovered correction is within ~30% of the true induced miscalibration (you reveal it only at the end and report the match).
- [ ] At least two PlotJuggler/matplotlib figures: the XY trajectory overlay (odom vs ground truth, uncorrected) and the before/after closure-error bar/line plot.
- [ ] A 1–2 page `results.md` tying it together.

---

## A worked sketch of the calibration arithmetic

Suppose your odometry node uses `wheel_radius = 0.0500` and over a single straight 10 m segment it reports the robot travelled `9.90 m` while ground truth says `10.00 m`. The model under-reports distance, so the true radius is larger than assumed:

```
radius_scale = 10.00 / 9.90 = 1.0101
new_wheel_radius = 0.0500 * 1.0101 = 0.05051 m
```

That recovers the induced `0.0505` to three decimals. Now suppose an in-place 360° spin reports `366°` of yaw while ground truth says `360°`. Odom over-reports yaw, which (since `ω ∝ 1/L`) means your assumed `L` was too small:

```
wheelbase_scale = 366 / 360 = 1.0167
new_wheel_separation = 0.3000 * 1.0167 = 0.3050 m
```

Hold on — your induced *true* separation was `0.2955`, smaller than nominal, which would make the robot *under*-report yaw, not over-report it. If your numbers come out with the wrong sign, **you have the relationship backwards** — re-derive it from `ω = r(φ̇_R − φ̇_L)/L` and check which way the error pushes. Getting the sign right is half the challenge; a calibration applied with the wrong sign *doubles* the error, and the re-run square will visibly drift worse. That failure is informative — if your "correction" makes closure worse, your sign is flipped.

---

## Going further (no extra grade)

- Fit a **velocity-proportional twist covariance** (`σ²_vx = k_v·|vx|`, `σ²_w = k_w·|w|`) from your speed-sweep slip data, and feed *that* into your odometry node's covariance instead of the static diagonal. This is the principled covariance of *Probabilistic Robotics* Ch. 5, and it is exactly what makes the Week 10 EKF tune cleanly. Report the `k_v`, `k_w` you fit.
- Use **`evo`** (`evo_ape`) on your logged trajectories to compute absolute pose error and compare its number to your hand-rolled closure metric. They should agree in magnitude; where they differ, understand why (`evo` aligns trajectories with Umeyama by default — turn that off with `--no_align` for an honest dead-reckoning comparison).
- Repeat the whole experiment on a **smooth vs high-friction floor** (change the Gz Sim surface friction) and show that slip — not your calibration — moves.

---

## Submission

Commit `challenges/challenge-01-drift-calibration/` containing:

- `data/` — the trajectory CSVs from every run (named by speed/turn-rate/direction).
- `plots/` — the XY overlay and the before/after closure figures.
- `calibrate.py` — the script that fits the correction from the CSVs (do not eyeball it; fit it).
- `results.md` — the tables, the dominant-error claim, the fitted correction, the before/after comparison, and the reveal of how close your recovery came to the true induced values.

The reviewer re-runs `calibrate.py` against your CSVs and checks the fitted correction reproduces. The most common review-fail is a `results.md` whose claimed correction does not match what `calibrate.py` actually computes — keep them in sync.

---

**References**

- Borenstein & Feng — UMBmark paper (the CW/CCW correction): see `resources.md`.
- Lecture 1, §1.3 (heading dominates), §1.6 (UMBmark), §1.8 (the speed-independence control).
- `evo` trajectory evaluation toolkit: <https://github.com/MichaelGrupp/evo>
