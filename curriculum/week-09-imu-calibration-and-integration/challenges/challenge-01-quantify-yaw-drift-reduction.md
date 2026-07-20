# Challenge 1 — Quantify the Yaw-Drift Reduction

**Time estimate:** ~90 minutes.

## Problem statement

Everyone *says* IMU calibration reduces drift. This challenge makes you **measure the reduction factor** on your own sensor, so the claim becomes a number you can defend at the Phase 2 midterm. You will integrate yaw two ways over the same stationary data — once from the raw gyro, once from the bias-corrected gyro — and show, with a plot and a single ratio, exactly how much the bias subtraction bought you.

This is the canonical "before/after" artifact of state estimation. A senior engineer never claims an improvement without the metric; this challenge builds that reflex on the simplest possible case.

## Background you need

A stationary gyro should integrate to *zero* yaw — the robot isn't turning. But the raw gyro has a bias `b_gz`, so integrating it yields a ramp: `yaw_raw(t) = b_gz · t`. Subtracting the bias should flatten that ramp to near-zero (residual: random walk + bias instability, from Lecture 1). The ratio of the two final drifts is your reduction factor.

## Your task

Record (or `ros2 bag play`) a **fresh stationary log** of `/imu/data` — at least 120 seconds, robot truly still. Then write a script `yaw_drift.py` that does the following.

### Part A — Estimate the bias

Use the *first* 30 seconds of the log to estimate the gyro bias (the per-axis mean), exactly as the Exercise 3 node does. Hold out the *remaining* ≥90 seconds for the drift test, so you're not testing on the same data you calibrated on (that would be cheating — and a classic ML-style data-leakage mistake worth naming explicitly in your write-up).

### Part B — Integrate yaw both ways

Over the held-out window, integrate the z-axis gyro two ways:

```
yaw_raw[k]  = yaw_raw[k-1]  + gyro_z_raw[k]                  * dt
yaw_calib[k] = yaw_calib[k-1] + (gyro_z_raw[k] - bias_z)     * dt
```

Plot both `yaw_raw(t)` and `yaw_calib(t)` (in degrees) on the same axes versus time. The raw curve should ramp; the calibrated curve should stay near zero (a slow random walk, not a clean ramp).

### Part C — Report the reduction factor

Report:

- Final `yaw_raw` drift (degrees over the window).
- Final `yaw_calib` drift (degrees over the window).
- The **reduction factor** = `|yaw_raw_final / yaw_calib_final|`.
- The drift *rate* of each in °/min, so it's comparable across window lengths.

A healthy result is a 10×–50× reduction. If you get ~1×, your calibration didn't take — see the trap.

## Acceptance criteria

- [ ] A script `yaw_drift.py` that estimates bias on a calibration window, integrates yaw raw vs. calibrated on a *held-out* window, and saves a `yaw_drift.png` with both curves.
- [ ] A `drift-findings.md` (≈300 words) reporting: the estimated `bias_z`, the raw and calibrated final drift, the reduction factor, and both drift rates in °/min.
- [ ] You used a **held-out** window for the drift test, distinct from the calibration window, and you say so.
- [ ] You correctly explain why the calibrated curve isn't *exactly* zero (residual random walk + bias instability — there's no fixing those by subtraction).
- [ ] Committed to your Week 9 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

If your reduction factor is ~1× (no improvement), the usual causes, in order of likelihood:

1. **The robot wasn't actually stationary during calibration.** Vibration, a fan, someone leaning on the bench — your "bias" then includes real motion, and subtracting it is meaningless. Re-record on a solid surface, nothing touching the robot.
2. **The calibration window was too short.** A few hundred samples is noisy; the bias estimate's standard error is `~σ_w/√N`. Use ≥3000 samples (30 s at 100 Hz).
3. **You calibrated and tested on the *same* data.** Then `yaw_calib` is near-zero by construction (you subtracted exactly the mean of that window) and the "improvement" is fake. Always hold out a separate test window — that's the whole point of Part A's split.
4. **Wrong axis or units.** Confirm the z-gyro is in rad/s and you're integrating the right axis.

## Stretch

- **Three-axis drift.** Repeat for roll and pitch. You'll find roll and pitch drift *less* than yaw even raw, because — if you also run a complementary filter — gravity bounds them (Lecture 1 §3). Show the asymmetry: yaw is the one that runs away.
- **Window-length sweep.** Plot the reduction factor as a function of calibration-window length (5 s, 10 s, 30 s, 60 s, 120 s). It improves then plateaus near the Allan-minimum τ — connect the plateau to the bias-instability floor from Lecture 1.
- **Temperature confound.** Record a log *immediately* after power-on (cold) and another after 10 minutes (warm). Show the bias *changed* as the chip heated — which is why real systems re-estimate bias at every standstill (the ZUPT idea), not just once at boot.
- **Drive test.** Instead of stationary, drive a closed loop (return to start) and compare the *heading* error at loop closure raw vs. calibrated. This is the drift that actually matters for navigation, and it's what Week 10's EKF will bound further.

## Why this matters

In Week 10 you fuse this IMU with wheel odometry, and the EKF's whole job is to *bound* drift. But the EKF can only weight the IMU correctly if (a) you removed the gross bias first and (b) you stated the residual uncertainty honestly. This challenge is where you prove (a) worked, with a number. The before/after drift plot is exactly the artifact a midterm panel — and a real robotics interviewer — wants to see when they ask "how do you know your sensor calibration is good?" "I measured a 26× yaw-drift reduction on a held-out window" is a senior answer. "I subtracted the mean and assume it's better" is not.
