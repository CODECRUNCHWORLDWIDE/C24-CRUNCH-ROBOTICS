# Week 10 Homework

Six problems that revisit the week's topics and force the sensor-fusion workflow into your fingers. The full set should take about **5 hours**. Work in your Week 10 Git repository (the same workspace as the exercises and the `crunch_localization` mini-project) so every problem produces at least one commit you can point to at the Phase 2 midterm in Week 16.

The headline deliverable is **Problem 4 — the EKF tuning-rationale write-up**, the document that defends every value in your config. Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Source ROS2 Jazzy in every terminal. Have your robot up with Week 6 odom and the Week 9 calibrated IMU. The pure-math problems need only NumPy.

---

## Problem 1 — Derive the predict/update by hand on a 2-state filter

**Problem statement.** For a 2-state constant-velocity filter (state `[position, velocity]`), write out by hand the matrices `F` (a `2×2` with a `Δt` in it), `H` (you measure position only), and the full predict and update equations. Then plug in numbers for one step and compute `x̂` and `P` after a predict followed by an update. Record it in `notes/week-10/kf-by-hand.md`.

**Acceptance criteria.**

- `F = [[1, Δt], [0, 1]]`, `H = [1, 0]` correctly written.
- One full predict+update step worked numerically, showing `P` grow on predict and shrink on update.
- A sentence each on what the innovation and the Kalman gain were for your step.
- Committed.

**Hint.** Keep `Q` and `R` simple (small diagonal numbers). The point is to *feel* the matrix algebra of one step, not to optimize. Confirm your `P` after update is smaller (in the trace sense) than after predict.

**Estimated time.** 45 minutes.

---

## Problem 2 — Verify input covariance honesty

**Problem statement.** Echo and record the covariance of *both* EKF inputs. For `/odom`, capture `pose.covariance` and `twist.covariance`; for `/imu/data_calibrated`, capture `angular_velocity_covariance`. Confirm the odom covariance is **not** all zeros and the IMU covariance matches your Week 9 measured numbers. If the odom covariance is zeros (common in sim), set a realistic one in your Week 6 node and re-capture.

**Acceptance criteria.**

- `notes/week-10/input-covariance.md` shows both inputs' covariance fields.
- The odom covariance is non-zero (and you note if you had to fix it).
- The IMU covariance traces to your Week 9 Allan numbers.
- A one-line statement of what a zero covariance would do to the EKF (over-trust).
- Committed.

**Hint.** `ros2 topic echo /odom --field pose.covariance` prints the 36-element row-major 6×6. A diagonal of zeros means "infinitely precise," which the EKF reads as `R = 0` and over-trusts. Set the velocity-related diagonals small and the absolute-pose diagonals larger.

**Estimated time.** 40 minutes.

---

## Problem 3 — Confirm the frame chain

**Problem statement.** Bring up your robot and the EKF. Generate the TF tree (`ros2 run tf2_tools view_frames`) and confirm the REP 105 chain `map → odom → base_link` (or at least `odom → base_link` this week), with **exactly one** publisher of `odom→base_link` (the EKF). If your wheel-odom node also broadcasts it, fix the conflict and document how.

**Acceptance criteria.**

- `notes/week-10/frame-chain.md` includes the `view_frames` output (or a description) showing one `odom→base_link` publisher.
- If you had a two-publisher conflict, you document the symptom (jitter/teleport) and the fix (disabled the odom node's broadcast).
- A sentence on why `map→odom` is kept separate from `odom→base_link` (jumps vs. smoothness).
- Committed.

**Hint.** Two publishers of the same transform is the #1 Week-10 bug. If rviz2 shows the robot flickering between two nearby poses, that's it. `ros2 topic info /tf` showing two publishers, or `view_frames` showing a conflict, confirms it.

**Estimated time.** 40 minutes.

---

## Problem 4 — The EKF tuning-rationale write-up (headline deliverable)

**Problem statement.** Write `notes/week-10/ekf-tuning-rationale.md` that defends your `ekf.yaml` line by line. It must contain:

1. **What each input contributes** — the `odom0_config` and `imu0_config` decoded into English (velocity from odom, heading from IMU), and why each absolute quantity has exactly one source.
2. **Frames** — `world_frame`, `two_d_mode`, and confirmation of one `odom→base_link` publisher.
3. **`R`** — where the measurement noise comes from (the inputs' covariance, verified in Problem 2).
4. **`Q` tuning** — the process-noise values you settled on, with the measurement-backed reason for each non-default change (from the challenge tuning log).
5. **Validation** — the raw-vs-fused drift improvement over the Week 6 square, with the number.
6. **Consistency** — whether the filter's stated uncertainty roughly matches its actual error.

**Acceptance criteria.**

- `notes/week-10/ekf-tuning-rationale.md` exists and hits all six headings.
- Every config value is justified by reasoning or measurement, not "it looked right."
- The fusion improvement is a real measured number.
- Committed.

**Hint.** This is the document the Week 16 panel — and a real interviewer — wants when they point at your config and ask "why?". "I raised `vyaw` process noise because heading lagged on turns and end-point error dropped from 0.4 to 0.2 m" is the senior answer. Pull the numbers from your challenge tuning log.

**Estimated time.** 1 hour.

---

## Problem 5 — The wrong-covariance experiment

**Problem statement.** Deliberately set the IMU's effective covariance 10× *too small* (either edit the corrector to publish a smaller `angular_velocity_covariance`, or override it in the EKF config). Drive the square. Observe and document the failure: the filter over-trusts the IMU and the yaw estimate jitters or over-corrects. Then restore the honest covariance and confirm the jitter resolves.

**Acceptance criteria.**

- `notes/week-10/wrong-covariance.md` describes the observed jitter/over-trust with the too-small covariance, and the recovery with the honest one (a plot or PlotJuggler screenshot helps).
- A sentence connecting this to the Kalman gain: too-small `R` → large gain → over-correction toward a noisy measurement.
- Committed.

**Hint.** This is the single most instructive experiment in the week. The effect is most visible on yaw during turns. If you see no difference, your `Q` may be dominating; lower `Q` so the measurement covariance actually matters.

**Estimated time.** 45 minutes.

---

## Problem 6 — Quantify the drift improvement

**Problem statement.** Using the Exercise 3 / mini-project drift-compare node, drive the 10×10 m square back to start and record the raw `/odom` and fused `/odometry/filtered` end-point error. Report both and the improvement factor. Do it twice (two runs) to show it's repeatable, not a fluke.

**Acceptance criteria.**

- `notes/week-10/drift-improvement.md` records two runs, each with raw error, fused error, and the factor.
- The fused error is consistently smaller than raw (a real factor, e.g. 2×–5×).
- A path plot (raw, fused, true square) for at least one run.
- Committed.

**Hint.** Drive the same square the same way both times for a fair comparison. If fused isn't better, walk the footgun checklist (Lecture 2 §3.4) before re-tuning — it's almost always an input or frame problem, not `Q`.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — KF by hand | 45 min |
| 2 — Input covariance honesty | 40 min |
| 3 — Frame chain | 40 min |
| 4 — Tuning rationale (headline) | 1 h 0 min |
| 5 — Wrong-covariance experiment | 45 min |
| 6 — Drift improvement | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_localization` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 11 adds AMCL on top of it. Then take the [quiz](./05-quiz.md) with your notes closed.
