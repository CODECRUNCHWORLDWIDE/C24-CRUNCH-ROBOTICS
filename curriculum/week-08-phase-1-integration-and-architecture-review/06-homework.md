# Week 8 Homework — The milestone evidence pack and the architecture-review rubric

This week's homework is different from the others. There is no set of disconnected practice problems; there is one thing — **assemble the evidence pack that lets you pass the Phase 1 milestone architecture review, and then pass it.** The milestone is a hard gate in the C24 assessment matrix: you do not advance to Phase 2 with an unsigned rubric. The full set should take about **6 hours**, spread across Saturday and Sunday in the suggested schedule.

The review is a live session (with an instructor, a senior-engineer peer, or — if you are solo — a recorded self-defense you submit). The reviewer reads your `crunchbot_bringup` package the way lecture 1 taught you to read a stranger's `launch/` directory, then asks you to defend four things: your **TF tree**, your **QoS choices**, your **odometry**, and your **map**. For each, you make a one-sentence claim and back it with one artifact. This homework builds those artifacts and rehearses those claims.

Work in your Week 8 Git repository under `mini-project/crunchbot_bringup/docs/milestone/` so every artifact produces a commit you can point to.

---

## Part 1 — Build the evidence pack (4 hours)

Produce the four evidence sets below. Each lives in its own subdirectory of `docs/milestone/`.

### 1A — The TF tree evidence (`docs/milestone/tf/`)

**Deliverables.**

1. `frames.pdf` — output of `ros2 run tf2_tools view_frames`, captured during a full bring-up (`slam:=true`). It must show one connected tree rooted at `map`.
2. `tf2_monitor.txt` — output of `ros2 run tf2_ros tf2_monitor odom base_link` run for ~20 seconds, showing a single authority and a stable average rate.
3. `tf_owners.md` — a table listing every TF edge, whether it is static or dynamic, and which node broadcasts it. Example:

   | Edge | Static/Dynamic | Broadcaster | QoS |
   |---|---|---|---|
   | `base_link → laser` | static | `robot_state_publisher` | `tf_static` (RELIABLE, TRANSIENT_LOCAL) |
   | `odom → base_link` | dynamic | Gz `DiffDrive` plugin | `tf` (default) |
   | `map → odom` | dynamic | `slam_toolbox` | `tf` (default) |

4. A note confirming a 60-second run produced **no** `extrapolation` errors (paste the relevant log tail, or state "no extrapolation errors observed").

**Acceptance.** The tree is connected and rooted at `map`; every edge has exactly one named owner; the static/dynamic split is correct against REP 105.

### 1B — The QoS evidence (`docs/milestone/qos/`)

**Deliverables.**

1. `topic_info.md` — the `ros2 topic info -v <topic>` output for each of `/scan`, `/imu/data`, `/odom`, `/map`, and `/tf`, showing publisher and subscriber QoS profiles.
2. `qos_rationale.md` — a table: for each topic, its reliability/durability/history, and a one-sentence justification tying back to the week-5 rules.
3. `ros2_doctor.txt` — the output of `ros2 doctor` during a full bring-up, confirming no QoS-mismatch warnings.

**Acceptance.** Sensor streams are `BEST_EFFORT`/`KEEP_LAST`; `/map` is `RELIABLE`/`TRANSIENT_LOCAL`; publisher and subscriber QoS match on every topic; `ros2 doctor` is clean.

### 1C — The odometry evidence (`docs/milestone/odom/`)

**Deliverables.**

1. `drift_measurement.md` — drive a 10×10 m square (or a known closed loop) and report the position error on return-to-origin, with the speed and conditions stated. Repeat at three speeds and tabulate.
2. `drift_plot.png` — a PlotJuggler (or matplotlib) plot of the commanded/odometry path vs. the Gz ground-truth path. (Gz publishes a ground-truth pose; subscribe and diff it against `/odom`.)
3. `odom_source.md` — one paragraph: where `odom → base_link` comes from in sim (the Gz `DiffDrive` plugin), how it would come from your week-6 node on hardware, and *why* the odometry drifts (slip, radius error, integration) and what Phase 2 does about it.

**Acceptance.** A real, numeric drift measurement at three speeds; a plot against ground truth; a correct causal explanation of the drift.

### 1D — The map evidence (`docs/milestone/map/`)

**Deliverables.**

1. `map_low_rate.png` and `map_high_rate.png` — the saved map of one multi-room world, mapped at two lidar update rates (e.g., 5 Hz and 15 Hz).
2. `map_comparison.md` — one paragraph comparing the two: which captured the loop closure more cleanly, which produced thinner walls, what the CPU cost difference was, and which rate you would ship.
3. The saved `.pgm` + `.yaml` pair for at least one map, with a visible resolved loop closure.

**Acceptance.** Two maps at two rates; a substantive comparison; a clear loop closure in at least one.

---

## Part 2 — Rehearse and pass the review (2 hours)

### 2A — Prepare the four defenses (`docs/milestone/defense.md`)

For each of the four defenses, write your **one-sentence claim** and name the **one artifact** that proves it. This is the script you walk the reviewer through. Example for the TF defense:

> **Claim:** "My TF tree is a single connected graph rooted at `map`, with `robot_state_publisher` owning the static joints, the Gz `DiffDrive` plugin owning `odom → base_link`, and `slam_toolbox` owning `map → odom` — no edge has two owners."
> **Artifact:** `tf/frames.pdf` and `tf/tf2_monitor.txt`.

Write the analogous claim+artifact for QoS, odometry, and map.

### 2B — Sit the review

Conduct the review (live with a reviewer, or recorded self-defense). The reviewer reads your package, then asks the rubric questions below. You answer each with your claim and artifact. The reviewer signs the rubric.

---

## The Phase 1 milestone rubric

The reviewer scores each row Pass / Needs-work. **All four defenses must pass** for the milestone to be signed. A "Needs-work" sends you back to fix the specific item and re-defend that row; it does not fail the whole milestone unless unresolved.

### TF tree (must pass)

| # | Criterion | Pass condition |
|---|---|---|
| T1 | Connectivity | `view_frames` shows one tree rooted at `map`; no disconnected frames. |
| T2 | Single authority | Every edge has exactly one broadcaster; `tf2_monitor` shows no rate anomaly. |
| T3 | Static/dynamic split | Learner correctly identifies which edges are static (URDF fixed joints) and dynamic, and who owns each. |
| T4 | No extrapolation | A 60-second run produces no extrapolation errors; learner explains the `use_sim_time` discipline that prevents them. |

### QoS (must pass)

| # | Criterion | Pass condition |
|---|---|---|
| Q1 | Sensor streams | `/scan`, `/imu/data`, odometry use `BEST_EFFORT`/`KEEP_LAST`; learner justifies. |
| Q2 | Latched map | `/map` uses `RELIABLE`/`TRANSIENT_LOCAL`; learner explains the late-joiner rationale. |
| Q3 | No mismatches | `ros2 topic info -v` shows matching pub/sub QoS; `ros2 doctor` is clean. |
| Q4 | Failure mode | Learner can describe what *silently* breaks under a reliability mismatch (e.g., rviz shows no map). |

### Odometry (must pass)

| # | Criterion | Pass condition |
|---|---|---|
| O1 | Source | Learner states where `odom → base_link` originates in sim and on hardware. |
| O2 | Measurement | A numeric drift measurement over a known path at ≥ 2 speeds, with conditions stated. |
| O3 | Causation | Learner correctly attributes drift to slip / radius error / integration. |
| O4 | Forward plan | Learner names the Phase 2 fusion (EKF, `robot_localization`) that bounds it. |

### Map (must pass)

| # | Criterion | Pass condition |
|---|---|---|
| M1 | Completeness | A saved multi-room map covering all rooms. |
| M2 | Loop closure | At least one loop closure visibly resolved (single, aligned walls). |
| M3 | Rate comparison | Maps at ≥ 2 lidar rates with a substantive comparison and a shipping decision. |
| M4 | Reproducibility | The map regenerates from the documented one command on the reviewer's machine. |

### Package quality (informational, folds into mini-project Documentation score)

| # | Criterion | Pass condition |
|---|---|---|
| P1 | One command | The stack comes up from a single `ros2 launch` line on a clean checkout. |
| P2 | No absolute paths | No `/home/` anywhere; all assets via `FindPackageShare`. |
| P3 | Params in files | Every node configured by a YAML keyed by node name; non-defaults commented. |
| P4 | README co-evolves | The package README documents the one command and every `--show-args` argument. |

---

## Submission

Push `docs/milestone/` (the four evidence subdirectories plus `defense.md`) and the signed rubric to your Week 8 repository. If the review was live, the reviewer commits their signature to the rubric; if it was a recorded self-defense, commit the recording link and a self-scored rubric, and flag it for asynchronous instructor sign-off.

The instructor confirms the milestone by:

1. Reading `docs/milestone/defense.md` and the four evidence subdirectories.
2. Re-running your one command on a clean machine and spot-checking the TF tree and the map.
3. Confirming the rubric is signed with all four defenses passing.

The most common reason a milestone is *not* signed is not a broken robot — it is a learner who built a working stack but cannot explain *why* it works. The evidence pack exists to force you to find out before the reviewer asks.

---

**References**

- REP 105 — "Coordinate Frames for Mobile Platforms": <https://www.ros.org/reps/rep-0105.html>
- ROS2 QoS design doc: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
- `tf2` tooling (`view_frames`, `tf2_monitor`): <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>
- `slam_toolbox` — the `save_map` service and mapping modes: <https://github.com/SteveMacenski/slam_toolbox>
