# Mini-Project — Capstone Build Sprint 1: The Bring-Up / Hardening Result

> Deliver the result of the week's sprint as a single, committed, reproducible artifact in your capstone repo: on **Path A**, a 20-meter trajectory driven under your full stack with the fused-estimate drift measured and recorded; on **Path B**, a hardened launch graph that cold-boots in under 60 seconds with a telemetry heartbeat. Either way, this is the first sprint that advances your integrated capstone toward the **Week 48 acceptance criteria**.

This mini-project is not a throwaway. It compounds. Week 43 wires the heartbeat you build here into a Foxglove dashboard and adds OTA and teleop. Week 44 fine-tunes the policy that drives the trajectory you record here. Week 46's chaos drill runs against this exact deployment. Week 48's defense reads the rosbag and the drift number you produce here. **Treat every file you commit this week as something a panel will read in six weeks**, because it is.

**Estimated time:** ~11.5 hours (Thursday through Sunday in the suggested schedule).

---

## Which path?

You chose your path in Lecture 2. **Do not switch now.** The rest of the course builds on the artifact you produce here, and switching mid-stream costs you the integration you have already done. If you have a robot you can drive, do Path A. If you do not, Path B is a legitimate, demanding alternative that trains the fleet-ops skills operators interview for.

| | Path A — Hardware | Path B — Hardened Sim |
|---|---|---|
| **Headline deliverable** | 20 m trajectory, drift < 0.5 m, recorded | Cold boot < 60 s, heartbeat NOMINAL |
| **Ground truth** | Tape + chalk (or total station) | Simulator's true pose |
| **Hardest part** | Sensor/actuator reality gap | Launch-graph determinism |
| **Feeds Week 43** | Telemetry from a real robot | The heartbeat → Foxglove |
| **Risk** | Higher (real motion, real failure) | Lower, but unforgiving on determinism |

---

## What you will build

Regardless of path, you produce a directory `capstone/sprint-01/` in your capstone repo with a fixed, gradeable structure:

```
capstone/sprint-01/
├── README.md                  # the sprint report (see the required sections below)
├── characterization/
│   ├── allan_gyro.png         # Allan deviation of your IMU (both paths)
│   ├── actuator_step.png      # command-to-motion step response (Path A)
│   └── timestamps.md          # ros2 topic delay / tf2_monitor findings
├── config/
│   └── ekf.yaml               # your RE-TUNED estimator config, with comments
├── runs/
│   └── <run_id>/              # the rosbag2 of the headline run (or LFS pointer)
├── telemetry/
│   └── heartbeat.py           # the aggregator (Path B primary; Path A optional)
├── launch/
│   └── bringup.launch.py      # Path A bring-up OR Path B hardened launch graph
├── systemd/
│   └── capstone.service       # Path B: the unit file + boot wrapper
├── results/
│   ├── drift.png              # Path A: fused vs. ground-truth path
│   ├── cold_boot.txt          # Path B: systemd-analyze / journalctl evidence
│   └── capstone.log           # the [capstone] PASS/FAIL lines from your runs
└── video/
    └── run.mp4                # ≤ 90 s screen + robot capture of the headline run
```

You will not fill every cell on both paths — `actuator_step.png` is Path A, `systemd/` is Path B — but the structure is the same so a grader (and future-you) knows exactly where to look.

---

## Rules

- **You may** reuse every node, config, and launch file from Weeks 1–41. This is an *integration* sprint; you are wiring what you already built into one verified result, not writing new perception or planning.
- **You may NOT** fabricate the headline number. The rosbag must contain the run that produced the number. A drift plot without a bag behind it is a fail.
- **You must** keep `use_sim_time:=false` on Path A and document it; on Path B keep it consistent and document it.
- **You must** record the headline run. No bag, no result.
- **Target:** ROS2 Jazzy, Ubuntu 24.04. Python (rclpy) and/or C++ (rclcpp) for nodes; the launch graph is Python.
- **Speed cap:** honor your draft safety case. The reference cap this week is 0.30 m/s linear, 0.6 rad/s angular. Do not exceed it for a faster run.

---

## Milestones

### Milestone 1 — Characterize (≈ 2 h, both paths)

Produce the `characterization/` directory. This is Lecture 1 made concrete.

- Record a static IMU bag (30–60 min); compute and commit `allan_gyro.png` with the angle-random-walk and bias-instability numbers in the caption.
- Path A: run the actuator step test; commit `actuator_step.png` with `Td` and `τ`.
- Both: run `ros2 topic delay /imu/data /odom` (or `/odometry/filtered`) and `tf2_monitor`; write `timestamps.md` with the numbers and a one-line verdict ("stamps clean, < 15 ms" or "stamps lagging, fixed by …").

**Done when:** the three characterization numbers exist and are committed.

### Milestone 2 — Re-tune the estimator (≈ 2 h, both paths)

Produce `config/ekf.yaml`. Re-tune `process_noise_covariance` and the measurement covariances against a *replayed* bag (Lecture 1 §5), not by re-driving. Keep a short tuning table in the sprint README: what you changed, and the drift it produced on the replay.

**Done when:** the EKF runs without diverging on the replayed bag and the covariance trace stays bounded.

### Milestone 3 — The headline run (≈ 3 h)

- **Path A:** drive the 20-meter trajectory (the rectangle from Challenge 1 is preferred over out-and-back). Record `runs/<run_id>/`. Measure terminal drift with tape; produce `results/drift.png`.
- **Path B:** harden the launch graph into lifecycle-ordered nodes with a readiness gate; install the systemd unit with `Type=notify`; reboot and time the cold boot. Record `results/cold_boot.txt`. Drive the 20 m path and produce `results/drift.png` from the simulator's ground truth.

**Done when:** `results/capstone.log` contains a `[capstone] … PASS/FAIL` line for the headline metric.

### Milestone 4 — Telemetry (≈ 1.5 h; Path B primary, Path A optional but recommended)

Produce `telemetry/heartbeat.py` (Lecture 2 §B.5). It aggregates node liveness, per-topic rates, actuator status, and the EKF covariance trace into one heartbeat at 2 Hz. On Path B it is required; on Path A it is the head start that makes Week 43 trivial.

**Done when:** the heartbeat publishes and goes DEGRADED when you kill a driver.

### Milestone 5 — The video and the report (≈ 2 h)

- Record a ≤ 90 s video of the headline run (screen capture of RViz/the terminal plus, on Path A, the robot itself). This is one of the two videos the Week 48 panel watches.
- Write the sprint `README.md` (sections below).

**Done when:** the video plays and the report's required sections are all filled.

---

## The sprint report — required sections

`capstone/sprint-01/README.md` must contain, in order:

1. **Path and venue.** A or B, and what hardware / sim world.
2. **The number.** The headline metric, in the `[capstone]` format, with PASS/FAIL against the bar.
3. **Characterization summary.** The three numbers from Milestone 1, one sentence each.
4. **What the reality/production gap cost you.** The single most impactful difference between sim and your run — be specific. "The 38 ms IMU timestamp lag added ~0.6 m of drift until I fixed the driver stamp" is the shape of a good sentence.
5. **The tuning table.** What you changed in the EKF and the drift each change produced.
6. **What is still broken.** Honest list of what you would fix with another day. There is always something.
7. **Link to the rosbag and the video.**

---

## Acceptance criteria

- [ ] `capstone/sprint-01/` exists in your capstone repo with the structure above.
- [ ] `characterization/allan_gyro.png` exists with N and B in the caption.
- [ ] `config/ekf.yaml` is re-tuned and commented, not the sim default.
- [ ] The headline run's rosbag is committed (or an LFS/release pointer is).
- [ ] **Path A:** `results/drift.png` shows terminal drift, and `capstone.log` has a `path=A … terminal_drift=… ` line.
- [ ] **Path B:** `results/cold_boot.txt` shows a `systemd-analyze` / `journalctl` boot timeline, and `capstone.log` has a `path=B cold_boot=… ` line.
- [ ] `telemetry/heartbeat.py` runs (required Path B; recommended Path A).
- [ ] `video/run.mp4` is ≤ 90 s and shows the headline run.
- [ ] The sprint `README.md` has all seven required sections.
- [ ] Every number in the report traces to an artifact in the directory.

---

## Grading rubric (100 points)

| Area | Points | What full marks looks like |
|------|-------:|----------------------------|
| **The headline number** | 30 | A real, recorded, in-the-`[capstone]`-format metric with PASS/FAIL. Full marks require the bag/log behind it; an unbacked number scores 0 here. |
| **Characterization** | 20 | Allan deviation computed (not just datasheet-quoted), actuator latency measured (Path A) or boot timeline profiled (Path B), timestamps verified. |
| **Estimator re-tune** | 15 | `ekf.yaml` re-tuned from measurements, tuning table present, covariance bounded. |
| **Hardening / bring-up rigor** | 15 | Path A: scripted bring-up gate, verified layer by layer. Path B: lifecycle ordering, readiness gate, `Type=notify`, reproducible reboot. |
| **Telemetry** | 10 | Heartbeat aggregates rates + covariance and degrades on driver kill. |
| **Report honesty + the gap analysis** | 10 | Section 4 names the *specific* reality/production gap and quantifies its cost. "It was harder than sim" scores 0; a quantified attribution scores full. |

**Passing is 70.** A passing sprint advances your capstone; a sub-70 sprint means you carry an unmet bar into Week 43, which is a worse place to fix it.

---

## How this advances the Week 48 capstone

The Week 48 defense requires: the integrated repo, an architecture diagram, two videos (sim + real, or two clearly-labelled sim runs on Path B), the signed safety case, and two chaos postmortems. This sprint delivers **the first of the two videos**, **the first hard number against the 0.5 m bar**, and **the deployment that Weeks 43, 46, and 48 all run against**. The covariance-trace heartbeat becomes the data source for the Week 43 Foxglove dashboard. The hardened launch graph (Path B) or verified bring-up (Path A) is what the Week 46 chaos drill attacks. Nothing here is busywork — every artifact is a load-bearing input to a later week.

---

## A note on honesty

The temptation, when the number is 0.7 m and the bar is 0.5 m, is to round, to cherry-pick the one good run out of ten, or to quietly drop the bad waypoint. Do not. A capstone panel that catches a fabricated number fails the whole defense, and rightly so — a robot that lies about its localization confidence hurts people. The senior move is the opposite: report 0.7 m, name the cause, show the plan. An honest 0.7 m in Week 42 with a clear path to 0.4 m by Week 48 is a *stronger* artifact than a suspiciously perfect 0.41 m with no rosbag. Record the run. Report the number. Defend it.

---

## Up next

Push `capstone/sprint-01/` and continue to **Week 43 — Capstone Build Sprint 2 + Telemetry and Fleet Ops**, where the heartbeat topic you built here becomes a real operator dashboard, and the deployment you hardened gets OTA updates and a one-click teleop-takeover button.
