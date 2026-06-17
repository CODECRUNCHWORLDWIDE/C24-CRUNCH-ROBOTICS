# Mini-Project — The Capstone Sim Milestone

> Deliver the **integrated end-to-end sim system** — mobile base + 6-DOF arm, perception + planning + control + VLA policy + behavior tree + safety wrapper + telemetry — running **one language-conditioned pick-and-place**, observable in telemetry, with **no manual intervention**. This is the **Phase 5 milestone**: everything from Weeks 1–39 composed into one robot. When a reviewer signs it off, you have eight weeks to make it real on hardware (Path A) or sim-production-grade on a documented hardware target (Path B).

**Estimated time:** ~14 hours (split across Thursday through Sunday in the suggested schedule).

This is the most important mini-project in the track. It is not a new build — it is the **integration** of thirty-nine weeks of builds into a single robot that takes an English sentence and carries it out. You are not adding a feature this week. You are proving that the parts you built, composed, agree. The deliverable is graded as a milestone (10% of the track, per the assessment matrix), and the sign-off is the gate into Phase 6.

This mini-project **compounds — it is the compounding.** Every prior mini-project fed this one: the Week 4 motion primitives are the BT's recovery leaves, the Week 16 fused perception node is the perception layer, the Week 32 safety wrapper is the leash, the Week 37 VLA-as-policy is the policy layer. The capstone spec in `SYLLABUS.md` is explicit that this is "one substantial integrated robot, not three loosely-related deliverables." This week you assemble it for the first time and run it once, cleanly.

---

## What you will build

A single composed system, brought up under one launch graph, that executes this run with no human in the loop after the instruction:

```bash
# Bring up the whole robot under the lifecycle manager + pre-flight gate.
ros2 launch crunch_capstone capstone_sim.launch.py

# Issue ONE instruction. Nothing else is touched until the cup is placed.
ros2 topic pub --once /instruction std_msgs/String \
  "{data: 'bring me the red cup from the left bench'}"
```

The system then, with every step observable on a Foxglove dashboard:

1. **Perceives** — the fused EKF localizes the robot; the perception node detects the red cup and publishes `/perception/objects` in `map` frame.
2. **Plans** — Nav2 plans a base path to the left bench; MoveIt2 stands ready for the arm.
3. **Controls** — the base drives the path under its PID controller; the fused estimate tracks it.
4. **Decides** — the VLA takes the instruction and the perceived scene and selects a grasp pose at the red cup.
5. **Manipulates** — MoveIt2 plans and executes the arm trajectory to the grasp; the gripper closes; the arm lifts and places the cup at the delivery pose.
6. **Supervises** — the safety wrapper guards every motion: E-stop armed, velocity/workspace clamps active, the classical fallback ready after three policy rejections.
7. **Reports** — the telemetry spine streams every layer to Foxglove; `/fleet/heartbeat` ticks at 1 Hz throughout.

By the end you have a public repo, a launch graph that stands the whole robot up, a five-minute video walkthrough, two measured acceptance numbers (drift and cold-boot), and a signed milestone.

---

## Why this is a milestone, not a feature

The previous milestones gated a phase: the Phase 1 architecture review, the two midterms, the Phase 3 and 4 sign-offs. This one gates the *capstone*. The acceptance criteria in `SYLLABUS.md` are the contract you read in Lecture 1 and wrote back in Exercise 1. Five of them are graded at Week 48; two of them — **state-estimate drift < 0.5 m over 20 m** and **cold-boot < 60 s** — are measurable *now*, and you measure them this week as evidence the milestone is on track. The instruction-success suite (15/20) and the chaos drills are Phase 6, but the system that runs them is the one you stand up this week. A weak milestone here is a weak capstone in eight weeks; the composition does not heal a broken component.

---

## Package layout

One umbrella package that composes the rest, plus the artifacts you scaffolded this week:

```
crunch_ws/src/
└── crunch_capstone/                        # ament_python (the integrator)
    ├── crunch_capstone/
    │   ├── __init__.py
    │   ├── preflight_check.py               # Exercise 2, productionized
    │   ├── telemetry_spine.py               # Exercise 3, productionized
    │   ├── lifecycle_manager.py             # ordered, safety-first bring-up
    │   └── capstone_run.py                  # the run orchestrator + logging
    ├── bt/
    │   └── capstone_pick_place.xml          # the top-level BT.CPP tree
    ├── launch/
    │   └── capstone_sim.launch.py           # stands the WHOLE robot up
    ├── config/
    │   ├── nav2_params.yaml                 # from Week 17
    │   ├── ekf_params.yaml                  # from Week 10
    │   └── moveit_params.yaml               # from Week 23
    ├── dashboard/
    │   └── milestone-layout.json            # the Foxglove layout (Challenge 1)
    ├── chaos-drills/
    │   ├── sensor-dropout.md                # template, filled in (Lecture 2)
    │   └── planner-deadlock.md              # template, filled in (homework)
    ├── safety-case/                         # the seven-section scaffold (Lecture 2)
    │   ├── 01-intended-use-and-odd.md
    │   ├── 02-foreseeable-misuse.md
    │   ├── 03-hazard-list.md                # first pass populated this week
    │   ├── 04-fmea.md
    │   ├── 05-mitigations.md
    │   ├── 06-residual-risk.md
    │   ├── 07-validation-plan.md
    │   └── README.md
    ├── what-i-heard.md                      # the contract restatement (Exercise 1)
    ├── measure_drift.py                     # acceptance measurement
    ├── measure_cold_boot.py                 # acceptance measurement
    ├── setup.py
    └── package.xml
```

The `crunch_capstone` package does not re-implement perception, planning, control, or the VLA — it **depends on** the packages you already built and composes them. Its own code is the integrator: the pre-flight gate, the lifecycle manager, the telemetry spine, the BT, the run orchestrator, and the measurement scripts.

---

## Functional requirements

### R1 — One launch graph stands the whole robot up

`capstone_sim.launch.py` brings up, in the safety-first order from Lecture 2: the sim + `ros_gz` bridge, the base + arm models, the EKF and `tf2` broadcasters, the fused perception node, Nav2 (under its lifecycle manager), MoveIt2's `move_group`, the VLA policy node, the safety wrapper, the behavior tree, and the telemetry spine. A single command brings it all up. No second terminal of manual `ros2 run` calls.

### R2 — Ordered, safety-first lifecycle bring-up

`lifecycle_manager.py` drives the managed nodes `unconfigured → inactive → active` in dependency order, and the **safety wrapper activates before any controller can command the robot**. The manager logs each transition and refuses to declare `system ready` until every node is `active` and pre-flight passes. This is the Nav2 pattern from Week 4, at full scale.

### R3 — The pre-flight gate

`preflight_check.py` (Exercise 2) runs after bring-up and before the run. It verifies the clock advances, every required topic publishes at rate, every required transform resolves and is recent, and every managed node is `active`. It exits non-zero on any failure, and the launch graph / run orchestrator **does not proceed past a failed pre-flight**. A failed pre-flight is a safety-relevant abort, not a warning.

### R4 — One language-conditioned pick-and-place, end to end

The BT (`capstone_pick_place.xml`) takes the instruction from `/instruction`, ticks perception → Nav2 → VLA grasp selection → MoveIt2 grasp+lift+place, with the safety branches wired. The run completes with the cup at the delivery pose and the tree reporting `SUCCEEDED`. The VLA selects the grasp from the language instruction (it is not hard-coded to "red cup" — it resolves the referring expression).

### R5 — No manual intervention

After `/instruction` is published, no keyboard, `ros2 topic pub`, or `rviz2` action influences the run. Pre-positioning the cup and issuing the instruction are not intervention (per your Exercise-1 ambiguity resolution); anything after the instruction is. If the run requires a nudge to complete, the milestone is not met — fix the integration defect, do not nudge past it.

### R6 — Every layer observable in telemetry

`telemetry_spine.py` (Exercise 3) streams `/telemetry/pose`, `/telemetry/detections`, `/telemetry/path_summary`, `/telemetry/policy`, `/telemetry/safety`, and `/fleet/heartbeat`. The `dashboard/milestone-layout.json` Foxglove layout shows one panel per layer. The run passes the "narrate from the screen" test from Challenge 1.

### R7 — The acceptance numbers, measured honestly

- `measure_drift.py` drives a measured 20 m trajectory and reports the Euclidean error between `/odometry/filtered` and sim ground truth. Report the number; target < 0.5 m.
- `measure_cold_boot.py` times power-on (launch start) to `system ready` (lifecycle all-active + pre-flight pass). Report the number; target < 60 s.

Report the numbers you get, not the numbers you want. If drift is 0.7 m, the milestone notes that and the fix becomes a Phase 6 action item. Honest measurement is the point.

### R8 — The Phase-6 scaffolds exist

The `chaos-drills/` templates are filled in for both faults (sensor-dropout from Lecture 2, planner-deadlock from the homework). The `safety-case/` seven-section scaffold exists with the hazard list (`03-hazard-list.md`) populated in a first pass. These are not graded for completeness this week — they are graded for *existence and structure*, so Phase 6 inherits a scaffold.

---

## Rules

- **You may** reuse every package you built in Weeks 1–39, the ROS2 Jazzy docs, the Nav2 / MoveIt2 / BT.CPP docs, and your own exercise and challenge code.
- **You must** target ROS2 **Jazzy** on **Ubuntu 24.04**, with Gz Sim (Harmonic) or Isaac Sim. `rclpy` for the integrator nodes; `rclcpp` / BT.CPP for the behavior tree (the tree is C++ per Week 19).
- **You must** bring the whole robot up with **one launch command** under a lifecycle manager. A bring-up that needs a sequence of manual `ros2 run` calls is an automatic fail — the cold-boot criterion is a real number and a manual sequence cannot meet it.
- **You must** run the pre-flight gate before the run and honor its exit code. Starting the run after a failed pre-flight is a safety defect.
- **You must** treat "the run needed a manual nudge" as a build-breaking defect, the same way Week 4 treats a robot that keeps moving after a goal is dead.
- **You must not** hard-code the grasp target to bypass the VLA. The policy selects the grasp from the language instruction; a hard-coded grasp fails R4.

---

## Acceptance criteria

- [ ] A public repo named `c24-week-40-crunch-capstone-<yourhandle>`.
- [ ] `colcon build` of `crunch_capstone` and its dependencies succeeds with no errors.
- [ ] `ros2 launch crunch_capstone capstone_sim.launch.py` brings up the whole robot in one command; the lifecycle manager logs `system ready`.
- [ ] The safety wrapper activates before any controller can command the robot (verifiable in the bring-up log order).
- [ ] `preflight_check` runs before the run, passes, and the run honors its exit code (demonstrate the abort path on a forced failure too).
- [ ] Publishing one `/instruction` runs the full pick-and-place to `SUCCEEDED` with no manual intervention.
- [ ] The VLA selects the grasp from the instruction (not hard-coded); `/telemetry/policy` shows `source=vla`.
- [ ] Every layer is observable on the Foxglove dashboard; the run passes the narration test.
- [ ] `/fleet/heartbeat` publishes at ~1 Hz with `health=OK` for the whole run.
- [ ] `measure_drift.py` and `measure_cold_boot.py` run and report numbers; both are recorded in the repo README (target < 0.5 m and < 60 s, but report actuals).
- [ ] The chaos-drill templates (both faults) and the safety-case scaffold (seven sections, hazard list started) exist in the repo.
- [ ] A **five-minute video walkthrough** of the end-to-end run, with voiceover, is linked in the repo README.

---

## Grading rubric (100 points)

| Area | Points | What earns them |
|------|-------:|-----------------|
| **One-command bring-up + ordered lifecycle** | 15 | Whole robot up in one launch; safety-first activation order; `system ready` only when all active and pre-flight passes. |
| **Pre-flight gate** | 10 | Pre-flight runs before the run, covers the four integration defects, honored as a gate, abort path demonstrated. |
| **End-to-end run** | 25 | One instruction runs the full perception → planner → controller → policy → arm pick-and-place to `SUCCEEDED`. |
| **No manual intervention** | 15 | The run completes with nothing touched after the instruction; demonstrated with the terminal hidden. |
| **Observability** | 15 | Every layer on the telemetry spine and the Foxglove dashboard; passes the narration test. |
| **Safety integration** | 10 | Safety wrapper active throughout; E-stop armed; clamps and fallback wired and observable. |
| **Acceptance measurement** | 5 | Drift and cold-boot measured and reported honestly with the scripts. |
| **Phase-6 scaffolds + video** | 5 | Chaos-drill templates filled, safety-case scaffold present, five-minute walkthrough recorded. |

A submission that completes the pick-and-place but required a manual nudge, or whose policy grasp is hard-coded, or whose safety wrapper is absent, **caps at 50 points** regardless of polish. No-manual-intervention, a real VLA grasp, and the safety leash are the milestone's load-bearing properties — the rubric weights them accordingly.

---

## How this compounds into Phase 6

| Week | What it does with the capstone milestone |
|------|------------------------------------------|
| **41 — Safety case** | Turns the `safety-case/` scaffold into the portfolio-quality 8–15-page artifact; (Path A) begins the move to hardware. |
| **42 — Build sprint 1** | (Path A) brings this exact stack up on a physical Jetson + base + arm; (Path B) hardens the launch graph for a clean cold boot. |
| **43 — Telemetry + fleet ops** | Grows the telemetry spine into a production operator dashboard with the teleop-takeover button. |
| **44 — Eval-suite tuning** | Curates the 20-instruction suite and fine-tunes the VLA against it; the one instruction you ran this week becomes twenty. |
| **46 — Chaos drills** | Executes the two drills whose templates you filled in this week, live-graded. |
| **48 — Defense** | The panel reads your safety case, watches your videos, and applies the acceptance criteria from the contract you read in Lecture 1. |

Build it once, build it observable, measure it honestly, and it carries you to graduation. That is why this is a milestone and not a feature.

---

## Submission

Push to your public repo, tag it `week-40-milestone`, and open the repo's README with: the instruction you ran, the two measured numbers (drift, cold-boot), a link to the five-minute walkthrough video, and a one-line confirmation of zero manual intervention. In your cohort channel, post the repo link and the video. Schedule the milestone sign-off with a reviewer: they run your pre-flight, watch one end-to-end run, apply the narration test, and sign — or send you back to the layer that went dark. The signed milestone is the gate into Phase 6. Eight weeks left.
