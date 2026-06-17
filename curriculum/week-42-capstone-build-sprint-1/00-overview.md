# Week 42 — Capstone Build Sprint 1: Sim Meets Reality

Welcome to **C24 · Crunch Robotics**, Week 42 — the first of five capstone build sprints. Up to this point your stack has lived in a forgiving world. Gz Sim (or Isaac Sim) gave you perfect timestamps, Gaussian-clean IMU noise you set yourself, actuators that moved the instant you commanded them, and a clock you could pause. This week the forgiveness ends. You either bring the robot up on real hardware (**Path A**) or you harden the sim deployment until it behaves like a production service that has to survive a cold boot, a flaky network, and an operator who power-cycles it at the worst possible moment (**Path B**).

This is the week where simulation assumptions meet physical or production-grade constraints, and the gap is always larger than you expect. Real sensors do not produce the noise you simulated — they produce *bias*, *dropout*, *quantization*, *timestamp jitter*, and *correlated drift* that your nicely-tuned EKF never saw. Real actuators do not move instantly — they have dead time, a velocity ramp, and a transport delay through the CAN bus and the motor controller's own control loop. A production launch graph that "worked on my laptop" does not cold-boot cleanly under systemd when the LiDAR's Ethernet link comes up 1.2 seconds after the compute does. None of this is exotic. All of it shows up on integration day, every time, and the engineers who ship are the ones who expected it.

By Friday you should have one concrete, recorded result: a **20-meter trajectory driven under your full stack** with the fused state estimate's terminal drift measured and logged (Path A), or a **hardened launch graph that cold-boots in under 60 seconds** with a telemetry subscriber confirming every node, sensor, and actuator reports correctly (Path B). Both paths feed the same place — the Week 48 capstone acceptance bar of **under 0.5 m of drift over 20 meters**. This week is where you find out how far you actually are from it.

We do not pretend Path A and Path B are equivalent. Path A is harder, riskier, and more valuable on a résumé — but it requires a real robot, and not everyone has one. Path B is a legitimate, demanding alternative that produces a production-grade artifact and trains the exact skills (cold-boot determinism, launch-graph health, telemetry) that fleet operators interview for. Pick the path your hardware situation supports and commit to it for the rest of the course. **Do not switch paths after this week** — Weeks 43–48 build directly on whichever artifact you produce here.

## Learning objectives

By the end of this week, you will be able to:

- **Characterize** the difference between the noise you *simulated* and the noise a real sensor *produces* — bias instability, random walk, quantization, dropout, and timestamp jitter — and read an Allan-deviation plot to quantify IMU noise the way a calibration engineer does.
- **Measure** real-actuator latency end to end: command timestamp to first motion, the velocity-ramp time constant, and the transport delay through CAN + motor controller, using `ros2 topic` timestamps and a recorded `rosbag2`.
- **Re-tune** an `robot_localization` EKF (or your GTSAM smoother) for *measured* sensor characteristics rather than the values you guessed in sim — `process_noise_covariance`, per-sensor `*_config` masks, and the differential/relative settings that bite on real hardware.
- **Bring up** a real robot (Path A): confirm every sensor publishes at its rated rate with sane covariance, every actuator responds to a commanded velocity, and the TF tree is fully connected with no `extrapolation into the future` errors.
- **Drive** a 20-meter trajectory under the full autonomy stack and **log** the terminal drift of the fused estimate against a ground-truth reference (a tape measure and a chalk line are legitimate ground truth this week).
- **Harden** a launch graph (Path B): convert ad-hoc `launch` files into lifecycle-managed nodes with explicit ordering, readiness gates, and a `RegisterEventHandler` chain that fails loud instead of hanging.
- **Verify** a clean cold boot in under 60 seconds — from `systemctl start` to "all nodes active, all sensors nominal, ready to accept a goal" — measured, not estimated.
- **Write** a telemetry subscriber that aggregates node liveness, sensor rates, actuator status, and the fused-estimate health into one heartbeat topic an operator dashboard can consume (the seed for Week 43's Foxglove work).
- **Defend** your number — the measured drift or the measured cold-boot time — with a recorded artifact, not an assertion.

## Prerequisites

This week assumes the entire C24 track up to Week 41 is behind you and integrated. Specifically:

- **Weeks 1–16 (foundations + perception):** you have a working perception cycle — calibrated cameras, a depth pipeline, and a TF tree you trust.
- **Weeks 17–24 (state estimation + SLAM):** you have a fused state estimate. This week you re-tune it for real data, so you must already understand what `process_noise_covariance` and the per-sensor masks *do*. We do not re-teach the EKF; we re-tune it.
- **Weeks 25–32 (planning, control, learned policy):** you have a stack that can take a goal and drive to it — Nav2 or your own planner, a controller you can defend, and (optionally) a learned policy with a fallback.
- **Weeks 33–41 (sim-to-real groundwork, safety case, fleet seeds):** you have run domain randomization, you have a draft safety case, and your stack runs end-to-end in sim. Week 42 is the first time it leaves sim (Path A) or gets treated as a production deployment (Path B).
- **ROS2 Jazzy on Ubuntu 24.04.** Every command this week is Jazzy. If you are still on Humble, stop and upgrade — the lifecycle and launch APIs differ in ways that will cost you the week.
- **Path A only:** a real robot you can drive. A differential-drive base with wheel encoders, an IMU, and a 2D or 3D LiDAR is the minimum. The mobile manipulator from the hardware-bring-up weeks is ideal.
- **Path B only:** a deployment target — a spare machine, a VM, or a Jetson — where you can install your stack under systemd and power-cycle it without disrupting your dev box.

## Topics covered

- **Simulated noise vs. real noise.** What you put into `<gaussian_noise>` versus what an MPU-9250 or a BMI088 actually emits: bias instability, angle/velocity random walk, quantization steps, axis misalignment, temperature drift, and saturation. Why "white Gaussian" is a lie your sim told you.
- **The Allan deviation.** The one plot every IMU datasheet hides and every serious integrator computes themselves. How to record a 1-hour static `rosbag2` and compute the Allan deviation to extract the random-walk and bias-instability coefficients your EKF actually wants.
- **Timestamp discipline.** `use_sim_time`, the difference between the driver's hardware timestamp and `now()`, header stamp vs. arrival time, and why a 40 ms timestamp error turns a 20 cm trajectory error into a 2 m one.
- **Real-actuator latency.** Dead time, the velocity-ramp time constant, CAN transport delay, and the motor controller's own loop. Measuring command-to-motion latency from a `rosbag2`. Why your controller's `cmd_vel` assumptions break and how to model the delay.
- **Re-tuning `robot_localization` for measured data.** `process_noise_covariance`, `initial_estimate_covariance`, the `odomN_config` / `imuN_config` boolean masks, `differential` vs. `relative`, two-stage estimation (`ekf_local` + `ekf_global`), and the `transform_timeout`.
- **Path A bring-up.** The bring-up checklist: power, E-stop, motor enable, encoder sign, IMU axis convention (ENU vs. NED), LiDAR frame, the TF tree, and the first commanded motion. Confirming sensors and actuators report correctly *before* you trust the stack.
- **Path B hardening.** Lifecycle nodes (`configure` → `activate`), `Nav2`'s lifecycle manager, launch-graph ordering with `RegisterEventHandler`, readiness gates, systemd units, and the cold-boot stopwatch.
- **Telemetry.** A heartbeat aggregator: node liveness, per-topic rate monitoring with `rclpy` and `message_filters`, actuator status, fused-estimate covariance trace, published as one `DiagnosticArray` plus a compact custom heartbeat message.
- **The drift measurement.** Ground truth on a budget: tape, chalk, and a total station if you have one. Measuring terminal drift, logging it, and recording the run for your capstone evidence folder.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract. Integration days run long; protect Thursday and Friday for the actual run, and do not schedule the 20-meter drive (or the cold-boot stopwatch) for the last 30 minutes of an evening when you are tired and the robot is the only thing in the building that is not.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Real vs. simulated noise; Allan deviation; timestamp discipline |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Actuator latency; re-tuning the EKF for measured data       |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Wednesday | Path A bring-up / Path B lifecycle hardening                |    1h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5h      |
| Thursday  | Integration day: first run; challenge #1                    |    0h    |    1h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | The 20-meter run / the sub-60s cold boot; mini-project       |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work; record the evidence                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, write the integration-day log                 |    0h    |    0h     |     0h     |    1h     |   0h     |     0.5h     |    1h      |     2.5h    |
| **Total** |                                                             | **7h**   | **6h**    | **3h**     | **3.5h**  | **5h**   | **11.5h**    | **3.5h**   | **35h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | ROS2 Jazzy docs, `robot_localization`, Allan-deviation tooling, lifecycle/launch references, and the sim-to-real papers worth reading in 2026 |
| [lecture-notes/01-real-noise-and-actuator-latency.md](./02-lecture-notes/01-real-noise-and-actuator-latency.md) | What real sensors emit vs. what you simulated; the Allan deviation; timestamp discipline; measuring actuator latency; re-tuning the EKF for measured data |
| [lecture-notes/02-bring-up-and-hardening.md](./02-lecture-notes/02-bring-up-and-hardening.md) | Path A hardware bring-up end to end; Path B lifecycle hardening, launch-graph ordering, systemd, and the sub-60-second cold boot; telemetry |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-bring-up-and-verify.md](./03-exercises/exercise-01-bring-up-and-verify.md) | Path A: bring the robot up; confirm every sensor and actuator reports correctly, with a scripted health check |
| [exercises/exercise-02-trajectory-drive-and-drift.py](./03-exercises/exercise-02-trajectory-drive-and-drift.py) | Path A: drive a 20-meter trajectory under the full stack and log terminal drift |
| [exercises/exercise-03-telemetry-and-cold-boot.py](./03-exercises/exercise-03-telemetry-and-cold-boot.py) | Path B: harden the launch graph, add a telemetry subscriber, verify a clean cold boot under 60 seconds |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-half-meter-drift-bar.md](./04-challenges/challenge-01-half-meter-drift-bar.md) | Demonstrate the fused estimate drifts under 0.5 m over 20 meters — the capstone acceptance bar — on hardware (A) or the hardened sim deployment (B) |
| [quiz.md](./05-quiz.md) | 13 questions on real noise, latency, EKF tuning, lifecycle, and cold-boot determinism, with an answer key |
| [homework.md](./06-homework.md) | The integration-day log, the drift/cold-boot report, and a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the bring-up/hardening sprint deliverable that advances the capstone toward Week 48 |

## The "show me the number" promise

C24 has a recurring marker, and this week it gets sharper. Every claim about your stack must come with a measured number and a recorded artifact:

```
[capstone] run_id=2026-06-12T14:03:11Z  path=A  distance=20.04 m
[capstone] terminal_drift=0.41 m  (x=+0.33, y=-0.24)  PASS (< 0.50 m)
[capstone] rosbag=runs/2026-06-12_2003m_run07/  duration=58.2 s
```

or, on Path B:

```
[capstone] run_id=2026-06-12T14:03:11Z  path=B  cold_boot=53.8 s  PASS (< 60 s)
[capstone] nodes_active=14/14  sensors_nominal=4/4  actuators_nominal=2/2
[capstone] heartbeat_topic=/capstone/heartbeat  rate=2.0 Hz  ready_to_goal=true
```

If your terminal does not print a number with a PASS/FAIL next to it, you are not done. "It looked about right" is not an integration-day result. "0.41 m, here is the rosbag" is.

## A note on what's *not* here

Week 42 is the *first* sprint. It deliberately does **not** include:

- **Foxglove dashboards and full fleet telemetry** — that is Week 43. This week you publish *one* heartbeat topic; next week you visualize it and wire OTA and teleop-assist.
- **Policy fine-tuning on capstone demos** — Week 44. This week the policy runs as-is (or is bypassed for a classical planner) so the variable under test is the *sim-to-real / hardening gap*, not the policy.
- **The chaos drill** — Week 46. This week things may break, but the breakage is integration friction, not an *intentional* injected failure you must survive.
- **The full safety case sign-off** — that is finalized for Week 48. Your draft safety case from the earlier weeks is in force; respect its E-stop and speed-limit requirements during every run.

The single job of Week 42 is to close the largest part of the sim-to-reality (or sim-to-production) gap and produce one defensible number. Everything else waits.

## Stretch goals

If you finish the regular work early and want to push further:

- Compute the **Allan deviation** for your IMU two ways — with [`allan_variance_ros`](https://github.com/ori-drs/allan_variance_ros) and with a 30-line NumPy script you write yourself — and confirm they agree within 10%.
- Add a **second estimator** (GTSAM fixed-lag smoother) running in parallel with the EKF on the same recorded bag, and compare terminal drift on the *same* 20-meter run. You now have two numbers to defend instead of one.
- Instrument your actuator path with a **dead-time + first-order-lag model**, identify the parameters from a step response, and feed the delay into your controller's prediction step. Re-run and report the drift delta.
- On Path B, add a **chaos pre-flight**: kill the LiDAR driver 5 seconds into the cold boot and confirm the lifecycle manager reports the node as not-active instead of the whole graph hanging. (This is a free head start on Week 46.)

## Up next

Continue to **Week 43 — Capstone Build Sprint 2 + Telemetry and Fleet Ops** once you have pushed this week's artifact (the 20-meter run with its drift number, or the sub-60-second cold boot with its heartbeat) to your capstone repo. Week 43 takes the single heartbeat topic you build this week and turns it into a real operator dashboard in Foxglove, adds OTA update plumbing, and wires the one-click teleop-takeover button. The telemetry subscriber you write this week is not throwaway — it is the data source for everything that follows.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
