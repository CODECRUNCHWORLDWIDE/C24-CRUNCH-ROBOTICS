# Challenge 1 — Tune the EKF and Quantify the Fusion

**Time estimate:** ~120 minutes.

## Problem statement

You have an `ekf_node` fusing wheel odometry and the calibrated IMU. Out of the box it may already beat raw odometry — or it may not, if the process noise is mistuned or an input covariance is dishonest. This challenge makes you **tune `process_noise_covariance` methodically** and **prove the result with a number**, then write the tuning rationale a senior reviewer expects. By the end you'll have a before/after drift plot and a defensible explanation of every value you changed.

This is the canonical state-estimation deliverable: not "I ran the EKF," but "I tuned it, measured a 4× drift reduction, and here's why each parameter is what it is." That distinction is exactly what the Week 16 midterm and a robotics interview probe.

## Background you need

`process_noise_covariance` (`Q`) is the EKF's trust in its own motion model (Lecture 1 §5.2). Too small → the filter overtrusts prediction, lags real corrections, and is confidently wrong. Too large → the filter chases noisy measurements and jitters. The right `Q` makes the filter's *stated* uncertainty match its *actual* error (consistency). You tune it by driving a known trajectory and comparing fused vs. raw drift and the covariance growth.

`R` (measurement noise) comes from the sensors — it is NOT something you tune here. Before touching `Q`, verify `R` is honest: `/odom` must have a non-zero `pose.covariance`, and the IMU must carry your Week 9 covariance. A zero odom covariance silently ruins everything downstream, so fix that first.

## Your task

### Part A — Verify the inputs (do this before tuning)

```bash
ros2 topic echo /odom --field pose.covariance                      # NOT all zeros
ros2 topic echo /imu/data_calibrated --field angular_velocity_covariance   # Week 9 numbers
ros2 run tf2_tools view_frames                                     # one odom->base_link
```

If `/odom`'s covariance is all zeros, set a realistic one in your Week 6 odom node (small on velocity, larger on absolute pose) and document that you did. If `view_frames` shows two publishers of `odom→base_link`, fix that (turn off the broadcast in the odom node) — no amount of `Q` tuning fixes a TF conflict.

### Part B — Baseline drift

Drive the **10×10 m square** from Week 6, returning to the start point. Use the Exercise 3 comparison node to record the raw `/odom` and fused `/odometry/filtered` end-point error. This is your *baseline* (untuned or default `Q`). Record both numbers and the improvement factor.

### Part C — Tune `process_noise_covariance`

Now iterate, changing **one group of `Q` entries at a time** and re-driving the square:

1. If the fused heading **lags the IMU** during turns → increase the `vyaw` (yaw-rate) process noise.
2. If the fused position **jitters** → decrease the velocity process noise.
3. If the fused estimate is **sluggish and confidently wrong** → increase the relevant `Q` entries.

For each change, record: which entry you changed, from what to what, the *hypothesis* (what you expected to improve), and the *measured* end-point error after. Keep a log — this log IS the deliverable. Stop when the improvement plateaus.

### Part D — The before/after artifact

Produce a single plot (PlotJuggler or matplotlib from recorded bags) overlaying the raw `/odom` path, the fused `/odometry/filtered` path, and the ground-truth square. Report the final improvement factor.

## Acceptance criteria

- [ ] A `tuning-log.md` recording the baseline drift, each `Q` change (entry, old→new, hypothesis, measured result), and the final values — at least three iterations.
- [ ] A before/after plot (`fusion_paths.png`) overlaying raw path, fused path, and the true square.
- [ ] The final fused end-point error is **smaller** than raw odometry, with the improvement factor stated.
- [ ] A `tuning-rationale.md` (≈350 words) explaining, for the final config: why those `vyaw`/velocity process-noise values, evidenced by your measurements — NOT "I fiddled until it looked right."
- [ ] You verified the inputs (Part A) and say so, including any odom-covariance fix.
- [ ] Committed to your Week 10 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

If tuning `Q` doesn't help no matter what you do, the problem is almost certainly **not** `Q` — it's an input or a frame issue you skipped in Part A:

1. **Zero `/odom` covariance.** The EKF thinks the wheels are perfect (`R = 0`), so it ignores the IMU entirely and the fused estimate just *is* raw odom. No `Q` value fixes this; fix the odom covariance.
2. **Two `odom→base_link` publishers.** The TF jitters between two poses regardless of the filter. `view_frames`, then turn off the odom node's broadcast.
3. **Double-counting absolute yaw** (both odom and IMU fuse absolute yaw). Overconfident, possibly divergent. One source per absolute (Lecture 1 §7).
4. **`two_d_mode` off.** On a planar robot the filter chases z/roll/pitch noise.

The discipline: **verify the inputs and frames before you tune.** Tuning `Q` on a broken input pipeline is the most common wasted afternoon in `robot_localization`.

## Stretch

- **Consistency check.** Don't just measure end-point error — check whether the filter's *stated* uncertainty (the `pose.covariance` of `/odometry/filtered`) matches its *actual* error. Plot the 1σ envelope against the true error over the trajectory. A consistent filter's error stays inside ~1σ most of the time; an overconfident one (Q or R too small) blows past it. This is the rigorous version of "is my tuning right."
- **Wrong-covariance experiment.** Deliberately set the IMU covariance 10× too small in the config and watch the filter over-trust the IMU and jitter on the yaw; then restore it. This single experiment teaches more about `R` than any amount of reading.
- **Second EKF.** Add the `map→odom` EKF (`world_frame: map`) fed by the same local sensors plus a placeholder global pose; confirm it doesn't fight the local EKF over `odom→base_link`. This is the dual-EKF pattern you'll complete with AMCL in Week 11.

## Why this matters

In Week 11 you add AMCL and a global correction; in Phase 3 the whole Nav2 stack stands on `/odometry/filtered`. If your fused estimate drifts or jitters, *everything* downstream inherits it — the planner plans from a wrong pose, the controller tracks a wrong path. This challenge is where you make the foundation solid and *prove* it's solid with a number. "I tuned the EKF to a measured 4× drift reduction and verified consistency" is the sentence that opens a robotics-engineering interview well. "I used the default config and hoped" is the sentence that ends it.
