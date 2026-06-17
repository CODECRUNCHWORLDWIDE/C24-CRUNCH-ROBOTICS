# Week 24 — Phase 3 Integration: Nav2 + MoveIt2 in One Graph, and the First Hazard Log

Welcome to **C24 · Crunch Robotics**, Week 24 — the last week of Phase 3 and the week your robot stops being a base *or* an arm and becomes a base *and* an arm, in one launch graph, under one safety contract. For seven weeks you built planning and control as separate skills. Nav2 drove a costmap. A* searched a grid. A behavior tree patrolled waypoints. PID, LQR, and MPC each tracked a trajectory. MoveIt2 reached a pose. Each was correct in isolation, on its own bench, against its own test. This week you compose two of the largest reusable codebases in robotics — **Nav2 for the base and MoveIt2 for the arm** — into a single graph that drives to a table, reaches a pose, and drives back, all dispatched by a behavior tree at the top. And because a robot that can drive *and* reach near a person is a robot that can hurt one, this is also the week functional safety stops being a footnote and becomes a discipline: you build your first **hazard log**, you write down the failure mode of every controller before you ship it, and you wire a software E-stop that cancels both the Nav2 action and the MoveIt2 trajectory within a measured deadline.

That is the deliverable, and it is the Phase 3 milestone. When the composed run completes and a reviewer signs off your controller stack and your first hazard log, you leave Phase 3 with the integration discipline that the rest of the track is built on. Phase 4 hangs learned policies off this exact graph; Phase 6's capstone is this graph plus perception and a VLA. Get the composition and the safety stance right here, once, and you compound it for twenty-four more weeks.

The first thing to internalize is that **integration is not "run both launch files at once." Integration is where two correct subsystems disagree, and your job this week is to find every disagreement before the robot does.** Nav2 publishes `map → odom → base_link` and plans in `map`; MoveIt2 plans in the arm's planning frame and expects a static `base_link → arm_base` transform that nobody has broadcast yet. Nav2's lifecycle manager wants to activate the controller server before the arm controllers are spawned; MoveIt2's `move_group` blocks on a `/joint_states` that the base bring-up never remapped into the arm's namespace. Two controllers fight over `/cmd_vel` because someone forgot to namespace. None of these is a bug in Nav2 or in MoveIt2 — each codebase is correct. They are *integration defects*, and they only appear when the two graphs are live at once. A senior robotics engineer expects this, budgets a full day for it, and brings the graph up under a checklist instead of launching it and hoping.

The second thing to internalize is that **every controller has a known failure mode, and a senior engineer writes it down before shipping.** The PID integrator winds up when the base is stuck against a wall. The LQR gain is only valid near the linearization point and goes unstable far from it. The MPC solver can exceed its time budget and return a stale or infeasible plan. MoveIt2 can plan a trajectory through a self-collision the planning scene didn't model. Each of these is a hazard, and the practice that turns a pile of "things that could go wrong" into an engineering artifact is the **hazard log**: a living table of hazard, cause, effect, severity, and the mitigation that owns it. Lecture 2 teaches you the hazard log and the vocabulary of functional safety — risk as severity × probability, the fail-safe categories, the crucial distinction between a software E-stop and a hardware E-stop, and where ISO 10218 (industrial manipulators) and ISO 13482 (personal-care robots) draw the lines that your shared-space mobile manipulator lives between.

The third thing to internalize is that **a fail-safe is a measured latency, not a claim.** The lab this week ends with a `/safety/estop` topic that, when latched `true`, cancels the in-flight Nav2 navigation action *and* the in-flight MoveIt2 trajectory within **200 ms**. "Within 200 ms" is not a vibe — it is a number you measure, from the latch timestamp to the first zero `/cmd_vel` and the first halted arm trajectory, and report with evidence. This is the same 200 ms latch the capstone spec demands at Week 48, introduced here so that by the time it is graded you have measured it a dozen times. The E-stop must also be designed correctly at the QoS layer: a `RELIABLE`/`TRANSIENT_LOCAL` latch, so a node that subscribes *after* the latch still receives `true` — a best-effort E-stop a late subscriber misses is a safety defect of the worst kind, and you carry that lesson straight from Week 5.

## Learning objectives

By the end of this week, you will be able to:

- **Compose** Nav2 (base) and MoveIt2 (arm) into one launch graph under a single lifecycle manager, with namespace discipline that keeps two controllers from fighting over a topic, and bring it up cleanly with one command.
- **Diagnose** the four canonical Phase-3 integration defects — the frame/timing mismatch, the bring-up-order deadlock, the joint-states/namespace collision, and the controller-fights-controller topic clash — and name each from its symptom.
- **Author** a pre-flight check node that asserts every required topic, transform, lifecycle state, and the clock is healthy before any goal is sent, and aborts the run loudly with an actionable message when one is not.
- **Build** a top-level behavior tree that sequences "drive to the table → reach a pose → return," dispatching the Nav2 and MoveIt2 action interfaces and wiring a safety branch.
- **Write** a hazard log: for each controller and each subsystem, the hazard, its cause, its effect, a severity rating, and the mitigation that owns it — the artifact that opens your capstone safety case.
- **Explain** the vocabulary of functional safety for robots: risk as severity × probability, the fail-safe categories (fail-stop, fail-operational, fail-safe-state), the software-vs-hardware E-stop distinction, and the ISO 10218 / ISO 13482 framings that bound a shared-space manipulator.
- **Implement** a software E-stop on a `RELIABLE`/`TRANSIENT_LOCAL` `/safety/estop` topic that cancels both the Nav2 action and the MoveIt2 trajectory within a measured 200 ms, and report the latency honestly with a measurement script.
- **Measure** the milestone's numbers — E-stop latch latency and cold-boot-to-ready time — with runnable harnesses, not adjectives.

## Prerequisites

This week assumes you have completed **Weeks 17–23** of C24, or have the equivalent components already built and tested. Specifically:

- **Nav2 brought up on a saved map (Week 17).** It accepts goals through the `NavigateToPose` action, you can inspect the costmap layers, and you wrote at least one custom behavior plugin. This week Nav2 becomes the base half of the composed graph.
- **A behavior tree (Week 19).** BT.CPP authoring — sequence, fallback, parallel, decorators, condition nodes — and Groot 2 for visualization. The composed task is a tree whose leaves call Nav2 and MoveIt2.
- **Controllers from PID to MPC (Weeks 20–22).** You know each controller's anatomy and, crucially, its failure mode — the integrator wind-up, the linearization validity region, the solver time budget. The hazard log is, in part, a catalog of these.
- **MoveIt2 on a 6-DOF arm (Week 23).** A UR5 or MyCobot 280 brought up in MoveIt2 + Gz Sim, planning to pose goals, and a Python script that triggers plan-and-execute through the `move_group` action interface. This week the arm joins the base under one lifecycle manager.
- **QoS literacy (Week 5).** You can read `ros2 topic info -v`, you know `RELIABLE`/`TRANSIENT_LOCAL` is the latched profile, and you understand why a best-effort E-stop a late subscriber misses is a silent safety failure.
- **A working ROS2 Jazzy on Ubuntu 24.04**, a Gz Sim (Harmonic) install that runs your base and arm, and roughly 16 GB of RAM.

You do **not** need any new library this week. Week 24 introduces almost no new API. It introduces a new *discipline*: composition, ordered bring-up, pre-flight verification, and the hazard-log practice. The hard part is not writing code — it is making two correct codebases agree, and writing down what happens when they don't.

## Topics covered

- **Composing Nav2 and MoveIt2.** One launch graph for base + arm. The two lifecycle stories (Nav2's lifecycle manager; MoveIt2's `move_group` and controller manager) and how to bring them up in one ordered sequence. Namespace discipline so the base and arm controllers never collide on `/cmd_vel`, `/joint_states`, or `/follow_joint_trajectory`.
- **The four Phase-3 integration defects.** The frame/timing mismatch (the `base_link → arm_base` static transform nobody broadcast; stamps that disagree). The bring-up-order deadlock (a node's `on_activate` blocks on an input from a node activated later). The joint-states/namespace collision (the arm's `move_group` reads a `/joint_states` that mixes base and arm joints). The controller-fights-controller clash (two controllers commanding the same topic).
- **The pre-flight check.** A scripted, deterministic, abort-on-failure node that asserts the clock advances, every required topic publishes at rate, every required transform resolves and is recent, and every managed node reports `active`. The aviation analogy and why experience does not let you skip the checklist.
- **Ordered, safety-first lifecycle bring-up.** Sensors → state estimation → Nav2 → MoveIt2 → safety wrapper → behavior tree, with the safety leash going on before anything can move. The Nav2 lifecycle-manager pattern at the scale of two controllers.
- **Functional safety, the vocabulary.** Risk as severity × probability of occurrence. The fail-safe categories: fail-stop (halt and stay halted), fail-safe-state (move to a defined safe configuration), fail-operational (degrade but keep going). The software E-stop vs. the hardware E-stop, and why the hardware one is the one that has to work when the software is the thing that failed.
- **The hazard log.** A living table: hazard, cause, effect, severity (1–10), mitigation, owning node/topic. Built from the controller failure modes you already know. This is the seed of the Week 41 capstone safety case.
- **ISO 10218 and ISO 13482, framed.** ISO 10218-1:2025 for industrial manipulators (the arm); ISO 13482 for personal-care robots in shared space (the mobile base near people). What each scopes, the hazard categories they enumerate, and which clauses your composed robot must answer to.
- **The software E-stop, measured.** A `RELIABLE`/`TRANSIENT_LOCAL` `/safety/estop` topic; a safety node that, on latch, cancels the Nav2 action via the action client and halts the MoveIt2 trajectory; and a measurement harness that reports the latch-to-stop latency against the 200 ms budget.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — though this is one of the two weeks per phase where "contract" is the operative word. Integration is best done in long, uninterrupted blocks: you need the full launch graph, Gz Sim, Groot 2, and the introspection tools all live at once, and context-switching out of a half-brought-up robot is the most expensive thing you can do this week.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Compose Nav2 + MoveIt2; the four integration defects           |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Pre-flight checks; ordered lifecycle bring-up                  |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Functional safety; the hazard log; ISO framings                |    1.5h  |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | The software E-stop; latch latency; the challenge              |    0.5h  |    0h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Mini-project — the composed drive-reach-return run             |    0h    |    0h     |     0h     |    0.5h   |   1h     |     3h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work; measure E-stop + cold-boot             |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, milestone sign-off prep                          |    0h    |    0h     |     0h     |    1h     |   0h     |     3h       |    0h      |     4h      |
| **Total** |                                                                | **6h**   | **5.5h**  | **2h**     | **3.5h**  | **5h**   | **14h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The Nav2 / MoveIt2 / BT.CPP integration docs, the lifecycle and launch references, and the functional-safety / ISO framings that matter in 2026 |
| [lecture-notes/01-composing-nav2-and-moveit2.md](./02-lecture-notes/01-composing-nav2-and-moveit2.md) | One launch graph for base + arm; the four integration defects; ordered safety-first lifecycle bring-up; the pre-flight check |
| [lecture-notes/02-functional-safety-primer.md](./02-lecture-notes/02-functional-safety-primer.md) | Risk and fail-safe categories; the hazard log; software vs. hardware E-stop; the 200 ms latch; ISO 10218 / ISO 13482 |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-compose-and-trace.md](./03-exercises/exercise-01-compose-and-trace.md) | Guided: bring Nav2 + MoveIt2 up in one graph and build the integration interface table that catches the four defects |
| [exercises/exercise-02-preflight-check.py](./03-exercises/exercise-02-preflight-check.py) | Runnable: a pre-flight check node that verifies topics, rates, TF, lifecycle states, and the clock, and aborts on any failure |
| [exercises/exercise-03-estop-latch.py](./03-exercises/exercise-03-estop-latch.py) | Runnable: a software E-stop node that cancels the Nav2 action and the MoveIt2 trajectory on latch, with a latch-to-stop latency measurement |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-estop-under-200ms.md](./04-challenges/challenge-01-estop-under-200ms.md) | Drive the composed robot, latch the E-stop mid-motion, and prove both the base and the arm stop within 200 ms — measured, ten trials |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the hazard log and the E-stop latency report |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The Phase 3 milestone — the composed drive-reach-return run with a hazard log and a measured E-stop |

## The "both stopped, and I can prove it" promise

C24 has had a recurring marker since Week 4 — the clean-shutdown promise: every node that commands the robot stops it on every exit path. Week 24 sharpens it into the safety promise the whole track will be measured against:

```
[estop_monitor] /safety/estop latched TRUE at t=12.418s
[estop_monitor]   nav2 NavigateToPose: cancel sent @ +3 ms, goal CANCELED @ +71 ms
[estop_monitor]   moveit2 trajectory: stop sent @ +4 ms, controller halted @ +58 ms
[estop_monitor]   first zero /cmd_vel observed @ +74 ms
[estop_monitor]   latch->full-stop latency = 74 ms  (budget 200 ms)  PASS
```

If your E-stop "probably stops the robot" but you cannot put a number on the latch-to-stop latency, the milestone is not met. "It stopped" is not a measurement; "74 ms, here is the script, run it yourself" is. The point of Week 24 is to make that measured-stop line ordinary — and to make a missed 200 ms budget *loud* instead of a thing you discover near a person at Week 48.

## A note on what's not here

Week 24 composes the base and the arm and puts the first safety stance around them. It does **not** cover:

- **Perception or learned policies.** The arm reaches a *fixed* pose this week, not a perceived object. Perceiving the object and selecting a grasp is Phase 4 (Weeks 25–32). This week the pose is a parameter, so the integration and the safety are the only variables.
- **The full safety case.** You build the *hazard log* this week — the first table. The portfolio-quality 8–15-page safety case with FMEA, mitigations, and validation plan is the **Week 41** artifact. Starting the hazard log now means Week 41 is expanding a table, not facing a blank page.
- **The hardware E-stop, physically.** You implement and measure the *software* E-stop and you *document* the hardware E-stop and how the software relates to it (the same Path-A/Path-B split the capstone uses). Wiring a physical button is Phase 6 hardware work.
- **MPC as the base controller.** The composed run uses your PID (or whichever base controller you trust most); the milestone does not require MPC. Do not spend integration hours upgrading the controller — spend them making the two stacks agree and the E-stop measured.

The point of Week 24 is a sharp, load-bearing skill: stand two large codebases up in one graph under a checklist, write down how every controller fails before it does, and prove your fail-safe meets its latency budget with a number. Everything in Phase 4 hangs off this graph, and everything in the capstone's safety case grows from this hazard log.

## Stretch goals

If you finish the regular work early and want to push further:

- Convert your bring-up to a single `LaunchDescription` with a Nav2-style lifecycle manager that brings up both the base and the arm controllers in one ordered sequence: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>.
- Wire your pre-flight check as a **launch gate** so nothing downstream activates until pre-flight passes, using a lifecycle transition the manager waits on.
- Add a **second fail-safe category**: alongside the fail-stop E-stop, implement a fail-safe-state behavior that retracts the arm to a defined safe pose on a soft fault, and contrast the two in your hazard log.
- Measure the E-stop latency under **load** — with the perception-shaped CPU burn of a `stress-ng` worker running — and show whether the 200 ms budget holds when the machine is busy. The number that matters is the number under realistic load.
- Read the **ISO 10218-1:2025** summary and map each of its enumerated manipulator hazards onto a row in your hazard log, citing the clause.

## Up next

Continue to **Week 25 — Grasping Foundations** once your milestone is signed and your controller stack and hazard log are reviewed. Week 25 begins Phase 4: the arm stops reaching a fixed pose and starts reaching a *grasp* computed from a point cloud — force closure, antipodal grasps, gripper-frame transforms. The composed graph you built this week is the body that grasp will command; the hazard log you started is where "the arm strikes during a grasp" becomes a row with a mitigation. You have built the robot's planning-and-control spine and put the first leash on it. Phase 4 teaches it to touch the world.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
