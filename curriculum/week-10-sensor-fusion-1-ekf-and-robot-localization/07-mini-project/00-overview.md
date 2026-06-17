# Mini-Project — `crunch_localization`: A Tuned, Documented EKF Stack

> Build a ROS2 package that fuses your wheel odometry and calibrated IMU into a single bounded-drift `/odometry/filtered` using `robot_localization`'s `ekf_node`, with a config you can defend line-by-line, the REP 105 frames done correctly, and a drift-reduction proof over the Week 6 square.

This is the artifact that turns "I have sensors" into "I have a *state estimate*." After this week, your robot doesn't just have wheel odometry and an IMU — it has a fused pose with honest covariance that every downstream system (Nav2, the controllers, SLAM correction) will stand on. This is the Phase 2 sensor-fusion deliverable, and it is the foundation of the rest of the track's autonomy.

**Estimated time:** ~10.5 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** `/odometry/filtered` and the `odom→base_link` transform this produces become the **pose source for Nav2** (Phase 3) and the local estimate that AMCL/GPS correct in the `map→odom` EKF (Week 11). The Week 16 midterm grades your fused estimate's drift and your config's defensibility. Build it well now; the whole autonomy stack rides on it.

---

## What you will build

An `ament_python` (or mixed) package `crunch_localization` with three deliverables:

1. **`config/ekf.yaml`** — the `ekf_node` configuration: the input topics, the boolean `_config` matrices (velocity from odom, heading from IMU, one source per absolute), `two_d_mode`, the REP 105 frame parameters, and a tuned `process_noise_covariance`. Every non-default value is commented with *why*.
2. **`launch/localization.launch.py`** — brings up `ekf_node` with the config, alongside (or composable with) your robot bring-up, ensuring exactly one publisher of `odom→base_link`.
3. **A drift-reduction report** (`FUSION.md`) — the raw-vs-fused end-point error over the Week 6 square, the before/after path plot, the tuning log, and the rationale for the final `Q`.

By the end you have a public repo of ~150–250 lines (config + launch + a small drift-compare node) plus a report that defends the whole thing.

---

## Why this is a config project, not a code project

You will write very little Python this week — `robot_localization` *is* the EKF, and re-implementing it would be foolish (it's battle-tested, handles the timing and frames correctly, and is what every real stack uses). The skill is **configuring and tuning** a production estimator and **proving** it works — which is exactly the real job. The hard part isn't code; it's:

- Getting the boolean matrices right (the covariance rules in YAML form).
- Getting the frames right (one `odom→base_link` publisher, REP 105 chain).
- Feeding it honest covariance (`R` from the sensors).
- Tuning `Q` methodically and documenting it.

A senior robotics engineer is measured on exactly these, not on whether they can hand-roll a Kalman filter (though you can, from Exercise 2).

---

## Package layout

```
crunch_localization/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_localization
├── config/
│   └── ekf.yaml               # the documented, tuned EKF config
├── launch/
│   └── localization.launch.py # bring up ekf_node + frame hygiene
├── crunch_localization/
│   ├── __init__.py
│   └── drift_compare.py       # raw vs fused end-point error (from Exercise 3)
├── FUSION.md                  # the drift-reduction report
└── test/
    └── test_ekf_config.py     # static checks: no absolute double-count, frames sane
```

---

## Deliverable 1 — `config/ekf.yaml` (the defensible config)

The config must:

- Fuse **`/odom`** (linear velocity `vx, vy` + yaw rate `vyaw`) and **`/imu/data_calibrated`** (absolute `yaw` + `vyaw` + optionally `ax`), with the boolean matrices encoding "one source per absolute quantity" (Lecture 1 §7, Lecture 2 §1.1).
- Set `two_d_mode: true` (planar robot), `frequency: 30.0`, and the REP 105 frame params (`map_frame`, `odom_frame`, `base_link_frame`, `world_frame: odom`, `publish_tf: true`).
- Carry a **tuned** `process_noise_covariance` — not the default, unless you can show by measurement the default is best for your robot.
- Have a **comment on every non-default line** explaining the choice. A reviewer should be able to read the YAML and reconstruct your reasoning.

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0
    two_d_mode: true                 # planar diff-drive: zero z/roll/pitch
    publish_tf: true                 # this EKF OWNS odom->base_link
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom                # estimating the LOCAL transform

    odom0: /odom
    odom0_config: [false, false, false,   # no absolute position (wheel drift)
                   false, false, false,
                   true,  true,  false,    # linear velocity (doesn't drift)
                   false, false, true,     # yaw rate
                   false, false, false]
    odom0_differential: false

    imu0: /imu/data_calibrated
    imu0_config: [false, false, false,
                  false, false, true,      # absolute yaw (IMU only -> one source)
                  false, false, false,
                  false, false, true,      # yaw rate
                  true,  false, false]     # forward accel (optional)
    imu0_differential: false
    imu0_remove_gravitational_acceleration: true

    # Tuned: vyaw and velocity terms raised from default after the square test
    # reduced end-point error from 0.41 m to 0.21 m. See FUSION.md.
    process_noise_covariance: [ ... 15x15, documented ... ]
```

> **The comments are graded.** A config with the right values but no rationale is a config you copied. A config where every non-default line says *why* is one you understand — and one a reviewer trusts.

---

## Deliverable 2 — `launch/localization.launch.py` (frame hygiene)

The launch must bring up `ekf_node` and ensure **exactly one publisher of `odom→base_link`**. If your Week 6 odom node broadcasts that transform, the launch must configure it to publish the topic only (a parameter, a remap, or disabling its broadcaster), or you get the two-publisher TF conflict (Lecture 2 §2). Document how you guaranteed one publisher.

Run and verify:

```bash
ros2 launch crunch_localization localization.launch.py
ros2 run tf2_tools view_frames     # exactly ONE arrow odom -> base_link
ros2 topic echo /odometry/filtered --field pose.pose
```

---

## Deliverable 3 — `FUSION.md` (the proof)

The report a reviewer reads to trust your estimate. It must contain:

- The raw-vs-fused end-point error over the Week 6 square, with the improvement factor.
- A before/after path plot (raw, fused, true square overlaid).
- The tuning log (each `Q` change: entry, old→new, hypothesis, result) — at least three iterations.
- A paragraph confirming input covariance is honest (non-zero odom covariance, Week 9 IMU covariance) and that exactly one node publishes `odom→base_link`.
- A consistency note: does the filter's stated covariance roughly match its actual error?

---

## Rules

- **You may** read the `robot_localization` docs, REP 105, the lecture notes, and example configs.
- **You must not** double-count an absolute quantity (no absolute yaw from both odom and IMU). `test_ekf_config.py` should statically catch this.
- **You must** ensure exactly one publisher of `odom→base_link`.
- **You must** verify input covariance is honest before claiming a tuning result.
- **You must** comment every non-default config line with its rationale.
- Python 3.12, `rclpy` on Jazzy, `ros-jazzy-robot-localization`.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-10-crunch-localization-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_localization` succeeds with no warnings.
- [ ] `ros2 launch crunch_localization localization.launch.py` brings up `ekf_node` and publishes `/odometry/filtered`.
- [ ] `ros2 run tf2_tools view_frames` shows exactly one `odom→base_link` publisher (the EKF).
- [ ] `config/ekf.yaml` has the correct boolean matrices (no absolute double-count), `two_d_mode: true`, REP 105 frames, and a tuned `process_noise_covariance` — every non-default line commented.
- [ ] `colcon test` passes, including `test_ekf_config.py` (no absolute quantity fused from two sources; frame params sane).
- [ ] `FUSION.md` shows fused end-point error < raw, with the factor, the path plot, and the tuning log.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Config correctness** | 25 | Boolean matrices encode the fusion rules (velocity from odom, heading from IMU, one source per absolute); `two_d_mode`; sane frames. |
| **Frame hygiene** | 15 | Exactly one `odom→base_link` publisher; REP 105 chain correct; documented. |
| **Honest inputs** | 15 | Non-zero odom covariance; Week 9 IMU covariance fed as `R`; verified, not assumed. |
| **Tuning & rationale** | 20 | Methodical `Q` tuning log (≥3 iterations); every non-default value justified by measurement. |
| **Drift proof** | 20 | Fused beats raw on the square, real factor, before/after plot. |
| **Tests & docs** | 5 | `test_ekf_config.py` green; `FUSION.md` review-grade; clean repo. |

**90+** is portfolio-grade and ready to drive Nav2 in Phase 3. **70–89** works but copies a config or skips the consistency check. **Below 70** means the estimate isn't trustworthy — walk the footgun checklist (Lecture 2 §3.4) first, because everything in Phases 3–6 stands on this pose.

---

## Stretch goals

- **Dual EKF.** Add the `map→odom` EKF (`world_frame: map`) fed by the local sensors plus a placeholder global pose, completing the REP 105 chain. Confirm the two EKFs don't fight over `odom→base_link`. (You'll plug AMCL in next week.)
- **Consistency dashboard.** Plot the fused covariance's 1σ envelope against the actual error over the trajectory; show the filter is consistent (error mostly within 1σ). This is the rigorous correctness check senior reviewers love.
- **UKF comparison.** Swap `ekf_node` for `ukf_node` (same config), re-run the square, and compare drift — a hands-on preview of Week 11's "the EKF lies about nonlinearity; the UKF lies less."
- **CI.** A GitHub Actions workflow that runs `colcon test` (including the static config check) on every push.

---

## How this connects to the rest of C24

- **Week 11 (UKF, particle filters, factor graphs)** adds AMCL for the `map→odom` global correction, completing the localization stack on top of this local EKF.
- **Phase 3 (Nav2, Weeks 17–24)** consumes `/odometry/filtered` and the `odom→base_link` transform as the robot's pose source for navigation.
- **Week 16 (Phase 2 midterm)** grades your fused perception+estimation stack; this EKF and its drift proof are central to the defense. This mini-project is that estimate, built and documented early.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
