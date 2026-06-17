# Mini-Project — The Phase 3 Milestone: Composed Drive-Reach-Return with a Measured E-Stop

> Deliver the **composed base+arm system** — Nav2 for the base, MoveIt2 for the arm, a behavior tree at the top, a pre-flight gate, and a software E-stop — running **one drive-to-the-table → reach-a-pose → return** task end to end, brought up with one command under an ordered, safety-first lifecycle, with a **hazard log** and a **measured 200 ms E-stop**. This is the **Phase 3 milestone**: the planning-and-control spine of the whole track, composed and leashed for the first time. When a reviewer signs off your controller stack and your first hazard log, you leave Phase 3 ready for Phase 4 to hang learned policies off this exact graph.

**Estimated time:** ~14 hours (split across Friday through Sunday in the suggested schedule).

This is the integration milestone for Phase 3. It is not a new build — it is the **composition** of your Week-17 Nav2, your Week-23 MoveIt2, your Week-19 behavior tree, and the safety stance from this week into a single robot that drives, reaches, returns, and stops on demand within a measured budget. You are not adding a feature this week. You are proving that two of the largest reusable codebases in robotics, composed, agree — and that you can stop the result near a person. The deliverable is graded as the Phase 3 phase-milestone (per the assessment matrix), and the sign-off gates Phase 4.

This mini-project **compounds forward.** The composed graph is the body Phase 4's grasps will command; the top-level BT is the tree whose `{reach_pose}` leaf becomes a perceived grasp at Week 25; the hazard log is the seed of the Week 41 capstone safety case; the 200 ms E-stop is the exact safety clause graded at Week 48. Build the composition and the safety stance well now, and you compound them for twenty-four more weeks.

---

## What you will build

A single composed system, brought up under one launch graph, that executes this task with the E-stop armed throughout:

```bash
# Bring up the whole robot under the lifecycle manager + pre-flight gate.
ros2 launch crunch_p3 drive_reach_return.launch.py

# The behavior tree runs automatically once the system is ready, or is
# triggered with one goal. Nothing else is touched while it runs.
```

The system then:

1. **Brings up, safety-first** — sensors → state estimation + `tf2` (including the static `base_link → arm_base`) → Nav2 → MoveIt2 → the safety wrapper (the leash) → the behavior tree (last). The lifecycle manager logs each transition and refuses `system ready` until every node is `active` and pre-flight passes.
2. **Pre-flight gates the run** — the pre-flight check verifies the clock advances, every required topic publishes at rate, the `base_link → arm_base` transform resolves and is recent, every managed node is `active`, and `/base/cmd_vel` has exactly one publisher. A failed pre-flight aborts; the run does not start.
3. **Drives to the table** — the BT dispatches a Nav2 `NavigateToPose` goal; the base drives the path under its controller; the fused estimate tracks it.
4. **Reaches a pose** — the BT dispatches a MoveIt2 `MoveGroup` goal to a *fixed* reach pose at the table; the arm plans and executes.
5. **Returns** — the arm retracts to home; the base drives back to start. The tree reports `SUCCEEDED`.
6. **Is leashed throughout** — `/safety/estop` is armed (`RELIABLE`/`TRANSIENT_LOCAL`); at any moment a latch cancels both the Nav2 action and the MoveIt2 trajectory and zeroes `/cmd_vel` within a measured 200 ms.

By the end you have a public repo, a one-command composed launch, a hazard log, a measured E-stop latency report, and the two milestone numbers (E-stop latch latency and cold-boot-to-ready time).

---

## Why this is a milestone, not a feature

The previous Phase 3 weeks built parts: a planner, a controller, an arm. This one gates the *phase*. The Phase 3 milestone, per the syllabus, is "the controller stack signed off and the first hazard log." Composition is where the parts you built in isolation either agree or fight, and the milestone is the proof that yours agree — and that the composed result is safe to operate. A weak composition here is a weak Phase 4: every learned policy in the next eight weeks commands this graph, and the composition does not heal a broken seam.

---

## Package layout

One umbrella package that composes the rest, plus the safety artifacts:

```
crunch_ws/src/
└── crunch_p3/                              # ament_python (the integrator)
    ├── crunch_p3/
    │   ├── __init__.py
    │   ├── preflight_check.py              # Exercise 2, productionized
    │   ├── estop_monitor.py                # Exercise 3, productionized
    │   ├── lifecycle_manager.py            # ordered, safety-first bring-up
    │   └── task_runner.py                  # triggers + logs the BT run
    ├── bt/
    │   └── drive_reach_return.xml          # the top-level BT.CPP tree
    ├── launch/
    │   └── drive_reach_return.launch.py    # stands the WHOLE robot up, gated
    ├── config/
    │   ├── nav2_params.yaml                # from Week 17
    │   ├── moveit_params.yaml              # from Week 23
    │   └── lifecycle.yaml                  # the safety-first activation order
    ├── safety/
    │   ├── hazard-log.md                   # the first hazard log (homework P1)
    │   ├── hardware-estop.md               # documented hardware E-stop (homework P5)
    │   └── estop-latency-report.md         # the measured 200 ms report (homework P3)
    ├── integration-trace.md                # the interface table (Exercise 1)
    ├── measure_estop_latency.py            # acceptance measurement
    ├── measure_cold_boot.py                # acceptance measurement
    ├── setup.py
    └── package.xml
```

The `crunch_p3` package does not re-implement Nav2, MoveIt2, or the controllers — it **depends on** the packages you already built and composes them. Its own code is the integrator: the pre-flight gate, the lifecycle manager, the E-stop monitor, the top-level BT, the task runner, and the measurement scripts.

---

## Functional requirements

### R1 — One launch graph stands the whole robot up

`drive_reach_return.launch.py` brings up, in the safety-first order from Lecture 1 §1.5: the sim + `ros_gz` bridge, the base + arm models, the EKF and `tf2` broadcasters (including the static `base_link → arm_base` on `/tf_static`), Nav2 (under its lifecycle manager), MoveIt2's `move_group` and controllers, the safety wrapper, and the behavior tree. One command brings it all up. No second terminal of manual `ros2 run` calls.

### R2 — Ordered, safety-first lifecycle bring-up

`lifecycle_manager.py` drives the managed nodes `unconfigured → inactive → active` in dependency order, and the **behavior tree (the motion dispatcher) does not activate until the safety wrapper is active**. The manager logs each transition and refuses to declare `system ready` until every node is `active` and pre-flight passes.

### R3 — The pre-flight gate

`preflight_check.py` (Exercise 2) runs after bring-up and before the run. It verifies the clock advances, every required topic publishes at rate, the `base_link → arm_base` transform resolves and is recent, every managed node is `active`, and `/base/cmd_vel` has exactly one publisher. It exits non-zero on any failure, and the launch graph **does not proceed past a failed pre-flight**. A failed pre-flight is a safety-relevant abort, not a warning. Demonstrate the abort path on a forced failure.

### R4 — One drive-reach-return task, end to end

The BT (`drive_reach_return.xml`) sequences: Nav2 to the table → MoveIt2 to a *fixed* reach pose → MoveIt2 to home → Nav2 to start, under a `ReactiveFallback` guarded by the E-stop condition. The run completes with the tree reporting `SUCCEEDED`. The reach pose is a *parameter*, not a perceived object — perception is Phase 4; this week the only variables are integration and safety.

### R5 — The E-stop, armed and measured

`estop_monitor.py` (Exercise 3) subscribes to a `RELIABLE`/`TRANSIENT_LOCAL` `/safety/estop`; on latch it cancels both the Nav2 action and the MoveIt2 trajectory directly and zeroes `/cmd_vel`. `measure_estop_latency.py` reports the latch-to-stop latency for *both halves*, mid-motion, over ten trials. The robot-stopped latency (the later of the two) must be reported against the 200 ms budget. Report the number you get.

### R6 — The hazard log exists and is keyed on real components

`safety/hazard-log.md` (homework P1) lists at least eight hazards across the base and the arm, each with severity, fail-safe category, mitigation, and owning node/topic, including the QoS-durability E-stop hazard and at least one fail-safe-state row. Every mitigation cites a component in your system; a hazard with no owner is a recorded gap.

### R7 — The acceptance numbers, measured honestly

- `measure_estop_latency.py` reports the latch-to-full-stop latency (both halves, mid-motion, ten trials). Report the number; target < 200 ms.
- `measure_cold_boot.py` times launch start to `system ready` (lifecycle all-active + pre-flight pass). Report the number; target < 60 s.

Report the numbers you get, not the numbers you want. If the E-stop is 230 ms under load, the milestone notes that and the fix becomes a Phase-4 action item. Honest measurement is the point.

---

## Rules

- **You may** reuse every package you built in Weeks 17–23, the ROS2 Jazzy docs, the Nav2 / MoveIt2 / BT.CPP docs, and your own exercise and challenge code.
- **You must** target ROS2 **Jazzy** on **Ubuntu 24.04**, with Gz Sim (Harmonic). `rclpy` for the integrator nodes; `rclcpp` / BT.CPP for the behavior tree (the tree is C++ per Week 19).
- **You must** bring the whole robot up with **one launch command** under a lifecycle manager. A bring-up that needs a sequence of manual `ros2 run` calls is an automatic fail — the cold-boot criterion is a real number a manual sequence cannot meet.
- **You must** activate the safety wrapper before the behavior tree (the motion dispatcher). A bring-up that can dispatch a goal before the leash is on fails R2.
- **You must** measure the E-stop latency for *both* halves and report the slower one. Reporting only the base while the arm keeps executing is the trap and an automatic fail of R5.
- **You must not** require a manual nudge to complete the run. The run completes hands-off after the trigger, or the integration defect that needed the nudge is a build-breaking bug, not a footnote.

---

## Acceptance criteria

- [ ] A public repo named `c24-week-24-crunch-p3-<yourhandle>`.
- [ ] `colcon build` of `crunch_p3` and its dependencies succeeds with no errors.
- [ ] `ros2 launch crunch_p3 drive_reach_return.launch.py` brings up the whole robot in one command; the lifecycle manager logs `system ready`.
- [ ] The safety wrapper activates before the behavior tree (verifiable in the bring-up log order).
- [ ] `preflight_check` runs before the run, passes, and the run honors its exit code (demonstrate the abort path on a forced failure too).
- [ ] The BT runs the full drive-reach-return to `SUCCEEDED` with no manual intervention.
- [ ] Latching `/safety/estop` mid-motion cancels both the base and the arm; `measure_estop_latency.py` reports the robot-stopped latency over ten trials.
- [ ] `safety/hazard-log.md` lists eight+ hazards with severity, category, mitigation, and owner; the QoS-durability hazard and a fail-safe-state row present.
- [ ] `measure_estop_latency.py` and `measure_cold_boot.py` run and report numbers; both are recorded in the repo README (targets < 200 ms and < 60 s, but report actuals).
- [ ] `integration-trace.md` (the interface table) and `safety/hardware-estop.md` exist in the repo.

---

## Grading rubric (100 points)

| Area | Points | What earns them |
|------|-------:|-----------------|
| **One-command bring-up + ordered lifecycle** | 15 | Whole robot up in one launch; safety-wrapper-before-BT activation order; `system ready` only when all active and pre-flight passes. |
| **Pre-flight gate** | 10 | Pre-flight runs before the run, covers the four integration defects, honored as a gate, abort path demonstrated. |
| **End-to-end drive-reach-return** | 20 | One trigger runs Nav2 → MoveIt2 → return to `SUCCEEDED`, hands-off. |
| **E-stop, measured** | 25 | Both halves cancel on latch; robot-stopped latency measured mid-motion over ten trials; reported against 200 ms; arm cancel confirmed (trap avoided). |
| **Hazard log** | 15 | Eight+ hazards across base and arm; severity/category/mitigation/owner per row; QoS-durability and fail-safe-state rows present; ISO framing noted. |
| **Acceptance measurement + hygiene** | 15 | Cold-boot measured; numbers reported honestly; interface table and hardware-E-stop doc present; clean repo (no `build/`/`install/` checked in). |

A submission that completes the drive-reach-return but **measures only the base E-stop latency**, or whose **safety wrapper activates after the BT**, or whose **hazard log is missing**, caps at 55 points regardless of polish. The measured both-halves E-stop, the safety-first order, and the hazard log are the milestone's load-bearing safety properties — the rubric weights them accordingly.

---

## Common pitfalls (read before you start, re-read when stuck)

These are the failures that eat the most hours on this milestone. Knowing them in advance is half the cure.

- **The arm can't find the base.** `move_group` logs `Could not find a connection between 'base_link' and 'arm_base'`. Almost always: the static transform was broadcast `VOLATILE` on `/tf` instead of latched on `/tf_static`, and `move_group` joined late. Fix: `StaticTransformBroadcaster`.
- **Cold boot hangs.** `move_group` waits forever for joint states. The controller manager came up after `move_group`. Fix the bring-up *order*, not the node.
- **The base jitters.** Two publishers on `/cmd_vel` — a stray teleop from your Week-20 testing fighting Nav2. `ros2 topic info /cmd_vel -v` shows the second publisher. Kill it or `twist_mux` it.
- **The E-stop "works" but only the base stops.** You zeroed `/cmd_vel` and forgot to cancel the arm's `FollowJointTrajectory` goal. The arm keeps executing. Measure *both* halves; cancel the arm goal directly.
- **The E-stop is missed by a late subscriber.** `/safety/estop` is `VOLATILE`, so a controller that subscribed late never sees the latch. It must be `RELIABLE`/`TRANSIENT_LOCAL`. This is the severity-9 hazard, reproduced as a bug.
- **The latency number is from a standstill.** You measured the E-stop from a stopped robot, where everything is fast. Measure mid-motion — that is the number that matters.
- **The safety wrapper activates after the BT.** The bring-up order lets the BT dispatch a goal before the leash is on. Re-order so the safety wrapper precedes the BT.
- **The hazard log has empty owner cells.** A mitigation with no owning node/topic is a wish, and an empty cell is a finding. Fill every cell or record the gap explicitly.
- **You report "it stops fast."** Not a measurement. The milestone wants a distribution — p95, max, ten trials, mid-motion, under load.

Each pitfall maps to a lecture section. When the milestone misbehaves, walk this list before you walk the code — most of these are diagnosable from `ros2 topic info -v`, the bring-up log order, and the E-stop latency script, in minutes.

## How this compounds into the rest of C24

| Week | What it does with the Phase 3 milestone |
|------|------------------------------------------|
| **25 — Grasping foundations** | The fixed `{reach_pose}` becomes a grasp computed from a point cloud; the composed graph is the body that grasp commands; "arm strikes during a grasp" becomes a hazard-log row with a mitigation. |
| **26–32 — Learned manipulation** | Every learned policy dispatches through this BT and this safety wrapper; the E-stop and clamps are the leash on the learned action. |
| **41 — Safety case** | The hazard log grows into the portfolio-quality 8–15-page safety case: FMEA, mitigations, residual risk, validation plan. |
| **48 — Defense** | The 200 ms E-stop you measured this week is the safety clause the panel grades; the composition discipline is the architecture they question. |

Build it once, compose it cleanly, leash it with a measured stop, and it carries you through manipulation, learning, and the capstone. That is why this is a milestone and not a feature.

---

## Definition of done (the one-line self-check per requirement)

Before you schedule the sign-off, confirm each in one line:

- **R1:** One `ros2 launch` brings up the whole robot. (Not a script of `ros2 run` calls.)
- **R2:** The bring-up log shows the safety wrapper `active` before the BT.
- **R3:** `preflight_check` runs first and the run honors its exit code; the abort path is demonstrated.
- **R4:** One trigger runs drive → reach → return to `SUCCEEDED`, hands-off.
- **R5:** Latching `/safety/estop` mid-motion stops *both* halves; `measure_estop_latency.py` reports the slower-half number over ten trials.
- **R6:** `safety/hazard-log.md` has eight+ rows, every cell filled, the QoS-durability and a fail-safe-state row present.
- **R7:** `measure_estop_latency.py` and `measure_cold_boot.py` print numbers, recorded in the README.

If any line is "no," that requirement is not done — fix it before the reviewer finds it. The sign-off is a confirmation of these seven lines, not a discovery of them.

## Submission

Push to your public repo, tag it `week-24-milestone`, and open the repo's README with: the task it runs, the two measured numbers (E-stop latch latency, cold-boot), a one-line confirmation of hands-off completion, and a link to the hazard log. Schedule the milestone sign-off with a reviewer: they run your pre-flight, watch one drive-reach-return, latch the E-stop mid-motion and confirm both halves stop within budget, and read your hazard log — then sign, or send you back to the seam that disagreed or the half that didn't stop. The signed milestone is the gate into Phase 4.
