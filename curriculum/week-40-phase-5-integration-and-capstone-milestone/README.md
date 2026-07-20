# Week 40 — Phase 5 Integration: Unseal the Capstone, Stand the Whole Robot Up in Sim

Welcome to **C24 · Crunch Robotics**, Week 40 — the last week of Phase 5 and the week the capstone stops being a rumor at the end of the syllabus and becomes a contract on your desk. For thirty-nine weeks you built parts. Rotations became a group. Transforms became a tree. A URDF became a robot in Gz Sim. An IMU got calibrated, an EKF fused it with wheel odometry, a LiDAR got clustered, a YOLO detector hit its latency budget, ICP registered two point clouds, Nav2 drove a multi-room map, MoveIt2 reached a pose, a Diffusion Policy and an ACT learned a pick, an OpenVLA fine-tune took an English sentence and chose a grasp, two robots shared a map, and a grounded planner turned "clear the table" into a skill sequence. This week you take **all of it** and stand it up as **one robot**, in sim, end to end, and run a single language-conditioned pick-and-place all the way through — perception to planner to controller to policy to safety wrapper to telemetry — with nobody touching the keyboard while it runs.

That is the deliverable. It is also the Phase 5 milestone, and it is graded. When the run completes and a reviewer signs it off, you have eight weeks left to make it real on hardware (Path A) or sim-production-grade on a documented hardware target (Path B). This is the hinge of the whole track.

The first thing to internalize is that **integration is not "wire the parts together." Integration is where the parts disagree, and your job this week is to find every disagreement before the robot does.** Each component you built was correct in isolation against its own test. Composed, they fight: the EKF publishes `map → odom` at 30 Hz but the VLA wants a frame stamped in `base_link`; the perception node's detection is 80 ms stale by the time the planner reads it; the safety wrapper clamps a velocity the MPC was counting on; the behavior tree ticks a grasp before the arm controller is `active`. None of these is a bug in any single component. All of them are integration defects, and they only appear when the whole graph is live. A senior robotics engineer expects this and budgets for it. The learner who thinks "I'll just run all my launch files at once on Friday" loses the weekend.

The second thing to internalize is that **the capstone spec is a contract, and you read a contract before you sign it.** When the spec says "the fused state estimate drifts < 0.5 m over a 20-meter trajectory," that is a number you will be measured against, not a vibe. When it says "completes at least 15 of 20 language-conditioned instructions," that is an acceptance test with a pass line. When it says "software E-stop topic with 200 ms latch," that is a latency budget your safety wrapper either meets or fails. Lecture 1 walks the spec clause by clause and teaches you the senior habit that makes or breaks a capstone: **read it back.** You write a one-page "what I heard" document that restates every required property in your own words, with the measurable acceptance criterion next to each, and the file/node/topic in your system that owns it. Half of capstone failures are not engineering failures — they are reading failures, where the team built something excellent that answered a question the spec never asked.

The third thing to internalize is that **a kickoff is a ritual, not a kickoff meeting.** Before you stand a complex system up, you run pre-flight checks — a deterministic, scripted sequence that proves every subsystem is present, on the right topic, at the right rate, in the right frame, before you ever send a goal. Aviation does not skip the checklist because the crew is experienced; they run it *because* they are experienced and know what an unchecked assumption costs at altitude. Lecture 2 gives you three reusable templates: the **pre-flight check** (a scripted node that asserts every topic, TF, lifecycle state, and clock is healthy and aborts loudly if not), the **chaos-drill template** (the structure you will fill in at Week 46 when an instructor kills your LiDAR mid-task), and the **safety-case template** (the artifact you author at Week 41 and defend at Week 48). You build the templates this week so that the build sprints of Phase 6 have a scaffold instead of a blank page.

The fourth thing to internalize is that **observability is a requirement of the run, not a nicety after it.** The Week 40 milestone is not "the robot did a pick-and-place." It is "every layer of the robot was *observable in telemetry* while it did a pick-and-place, with no manual intervention." If the VLA chose a grasp and you cannot point at the Foxglove panel where that grasp pose appeared, the layer is invisible, and an invisible layer cannot be debugged, cannot be graded, and cannot survive a chaos drill. This week you wire a telemetry spine — `/telemetry/*` topics and a Foxglove layout — so that pose, costmap, the detection array, the planned path, the policy action, the safety-filter status, and the heartbeat are all on screen at once. A reviewer watching that screen should be able to narrate the run without reading a single log line.

## Learning objectives

By the end of this week, you will be able to:

- **Read** the capstone specification clause by clause as a contract, extract every required system property and its measurable acceptance criterion, and write a "what I heard" restatement that maps each requirement to the node, topic, or file in your system that owns it.
- **Author** a pre-flight check node that scripts a deterministic bring-up verification — every required topic present and publishing at its expected rate, every TF transform resolvable, every lifecycle node `active`, the clock advancing — and that aborts the run loudly with an actionable message when any check fails.
- **Compose** the full Phase 1–39 stack into one launch graph: mobile base + 6-DOF arm, the fused perception node, Nav2 for the base, MoveIt2 for the arm, the VLA policy, a behavior tree on top, the runtime safety wrapper, and the telemetry spine — and bring it up cleanly under a lifecycle manager.
- **Execute** one happy-path, language-conditioned pick-and-place end to end ("bring me the red cup from the left bench") with zero manual intervention from instruction to placed object.
- **Instrument** every layer of the stack onto a telemetry spine so perception, planning, control, policy, and safety are each observable on a Foxglove dashboard in real time.
- **Fill in** the chaos-drill template and the safety-case template for your specific robot, so Phase 6 inherits a scaffold instead of a blank page.
- **Measure** the milestone's acceptance numbers honestly — state-estimate drift over a 20 m trajectory, cold-boot time to operational, end-to-end task latency — and report them with evidence, not adjectives.
- **Record** a five-minute video walkthrough of the end-to-end run that a reviewer can sign off against the milestone rubric.
- **Diagnose** the four canonical integration defects: the frame/timing mismatch, the stale-perception race, the lifecycle bring-up-order deadlock, and the safety-clamp/controller fight.

## Prerequisites

This week assumes you have completed **Weeks 1–39** of C24, or have the equivalent components already built and tested. Specifically:

- **A fused perception node (Week 16).** IMU + wheel odometry into an EKF, LiDAR into 3D clustering, RGB-D into a learned 2D detector, publishing a unified `/perception/objects` in the `map` frame. This week it becomes one input to the planner and the policy.
- **Nav2 for the base (Week 17) and MoveIt2 for the arm (Week 23).** Both bring up cleanly under a lifecycle manager and accept goals through their action interfaces. The behavior tree dispatches both this week.
- **A behavior tree (Week 19) and the motion primitives (Week 4).** BT.CPP authoring, control/decorator/condition nodes, Groot 2. The capstone task is a tree whose leaves call Nav2, MoveIt2, the VLA, and your `crunch_motion` primitives.
- **A learned policy with a safety wrapper and a classical fallback (Week 32).** The runtime safety filter that rejects out-of-bounds actions and the `/policy/fallback` BT branch that takes over after three rejections. This week the safety wrapper is mandatory, not optional.
- **A fine-tuned OpenVLA wired as a policy (Weeks 31, 37).** Text instruction in, action chunks / grasp pose out, dispatched by the behavior tree. This week it selects the grasp from the language instruction.
- **The telemetry instinct (Week 39).** You profiled the integrated graph and drew a latency Gantt. This week you stream the same signals live to Foxglove.
- **A working ROS2 Jazzy on Ubuntu 24.04**, a Gz Sim (Harmonic) or Isaac Sim install that runs your robot, a Foxglove account (free tier), and roughly 16 GB of RAM with a GPU that runs your VLA at interactive latency (or a documented Path-B substitution).

You do **not** need any new library this week. Week 40 introduces almost no new API. It introduces a new *discipline*: composition, pre-flight verification, and honest measurement against a contract. The hard part is not writing code — it is making thirty-nine weeks of code agree.

## Topics covered

- **The capstone spec as a contract.** Reading every clause of the SYLLABUS capstone specification, extracting the required system properties (perception, planning, control, policy, safety, telemetry, fleet readiness, OTA), and mapping each to an acceptance criterion with a pass line. The "read it back" habit and the "what I heard" document.
- **The acceptance numbers.** 15/20 instructions, < 0.5 m drift over 20 m, 200 ms E-stop latch, < 60 s cold boot, 60 s chaos-drill recovery. What each number means, how to measure it, and where each one fails first.
- **The capstone-kickoff ritual.** Pre-flight checks as a scripted, deterministic, abort-on-failure node. The aviation analogy and why experience does not let you skip the checklist. The "every topic, every TF, every lifecycle state, the clock" coverage matrix.
- **The chaos-drill template.** The structure of a chaos drill — the injected fault, the detection signal, the graceful-degradation path, the operator-visible event, the recovery deadline, the postmortem. Filled in for sensor-dropout and planner-deadlock, ready for Week 46.
- **The safety-case template.** Intended use, foreseeable misuse, hazard list, FMEA, mitigations (software E-stop, workspace clamps, perception confidence gates, classical fallback), residual risk, validation plan. ISO 13482 / ISO 10218 framing. The artifact you author at Week 41.
- **Full-stack composition.** One launch graph for base + arm + perception + Nav2 + MoveIt2 + VLA + BT + safety + telemetry. Namespace discipline across two controllers and two manipulanda. Ordered lifecycle bring-up so nothing commands hardware before its inputs are valid.
- **The telemetry spine.** A `/telemetry/*` topic family and a Foxglove layout that makes every layer observable: pose, costmap, `/perception/objects`, the planned path, the VLA action, the safety-filter status, the `/fleet/heartbeat`. The "narrate the run from the screen" test.
- **The four integration defects.** The frame/timing mismatch (TF and stamps disagree), the stale-perception race (the planner reads a detection older than its tolerance), the lifecycle bring-up-order deadlock (a node waits on an input from a node that has not activated), and the safety-clamp/controller fight (the filter and the MPC disagree about the velocity envelope).
- **The five-minute walkthrough.** What a milestone video must show: the instruction, the pre-flight pass, the live telemetry, the end-to-end run with no intervention, and the placed object. The difference between a demo and a defensible recording.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — though this is the one week where "contract" is the operative word. Integration is best done in long, uninterrupted blocks: you need the full launch graph, Gz/Isaac Sim, Foxglove, and the introspection tools all live at once, and context-switching out of a half-brought-up robot is the most expensive thing you can do this week.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Unseal the spec; read it as a contract; write "what I heard"   |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The kickoff ritual: pre-flight checks, chaos & safety templates |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Compose the full stack; bring it up; fight the integration bugs |    1.5h  |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | Telemetry spine; observability; the challenge                  |    0.5h  |    0h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Mini-project — the end-to-end happy-path run                   |    0h    |    0h     |     0h     |    0.5h   |   1h     |     3h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work; measure the acceptance numbers; record |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, milestone sign-off prep                          |    0h    |    0h     |     0h     |    1h     |   0h     |     3h       |    0h      |     4h      |
| **Total** |                                                                | **6h**   | **5.5h**  | **2h**     | **3.5h**  | **5h**   | **14h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The integration, observability, and safety-case references that matter in 2026 — ROS2 Jazzy docs, Foxglove, Open-RMF schemas, ISO framings, and the systems-integration talks |
| [lecture-notes/01-read-the-spec-like-a-contract.md](./lecture-notes/01-read-the-spec-like-a-contract.md) | The capstone spec clause by clause; required properties → acceptance criteria → owning node; the "read it back" habit and the "what I heard" document |
| [lecture-notes/02-the-capstone-kickoff-ritual.md](./lecture-notes/02-the-capstone-kickoff-ritual.md) | Pre-flight checks as a scripted abort-on-failure node; the chaos-drill template; the safety-case template; ordered lifecycle bring-up |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-read-the-spec-and-write-it-back.md](./exercises/exercise-01-read-the-spec-and-write-it-back.md) | Guided: turn the capstone spec into a requirements-traceability table and a one-page "what I heard" restatement |
| [exercises/exercise-02-preflight-check-node.py](./exercises/exercise-02-preflight-check-node.py) | Runnable: a pre-flight check node that verifies topics, rates, TF, lifecycle states, and the clock, and aborts loudly on any failure |
| [exercises/exercise-03-telemetry-spine.py](./exercises/exercise-03-telemetry-spine.py) | Runnable: a telemetry aggregator that republishes every layer's state onto `/telemetry/*` for a Foxglove dashboard, plus a `/fleet/heartbeat` at 1 Hz |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-observable-happy-path.md](./challenges/challenge-01-observable-happy-path.md) | Demonstrate a clean happy-path pick-and-place where every layer is observable in telemetry, with no manual intervention |
| [quiz.md](./quiz.md) | 13 multiple-choice questions with an answer key |
| [homework.md](./homework.md) | Six practice problems with deliverables and a rubric |
| [mini-project/README.md](./mini-project/README.md) | Full spec for the **capstone sim milestone** — the integrated end-to-end system running one language-conditioned pick-and-place |

## The "no manual intervention" promise

C24 has had a recurring marker since Week 4 — the clean-shutdown promise: every node that commands the robot stops it on every exit path. Week 40 adds the promise this whole track has been building toward:

```
[capstone_run] instruction="bring me the red cup from the left bench" -> SUCCEEDED
[capstone_run]   perception: red_cup detected @ map(1.82, -0.41, 0.74), conf=0.91
[capstone_run]   planner:    base goal reached, 0 replans; arm plan: 9 waypoints, 0 collisions
[capstone_run]   policy:     VLA grasp accepted (0 safety rejections, 0 fallbacks)
[capstone_run]   safety:     estop=clear, 0 velocity clamps, 0 workspace violations
[capstone_run]   timing:     instruction->placed = 41.3 s; manual interventions = 0
```

If your run required you to touch the keyboard — to nudge the base, re-trigger the grasp, or restart a hung node — the milestone is not met. "No manual intervention" is the property. We treat a hidden human-in-the-loop the same way Week 4 treats a robot that keeps moving after a goal is dead: a defect, not a footnote. The point of Week 40 is to make that zero-intervention line ordinary, and to make every number on it a measurement you can defend.

## A note on what's not here

Week 40 stands the system up and runs it once, cleanly, observably. It does **not** cover:

- **Hardware bring-up.** Moving from sim to a physical Jetson + base + arm is **Week 41–42** (Path A). This week is sim-only by design — the milestone is explicitly a *sim* milestone. Path B learners stay in sim through graduation and harden it instead.
- **Running the chaos drills for real.** You build the chaos-drill *template* this week and fill it in for two faults. The instructor-injected, live-graded drills are **Week 46**. We rehearse the structure now so Gameday is execution, not invention.
- **The full safety-case writeup.** You build the *template* and a first hazard pass this week. The portfolio-quality 8–15-page safety case is the **Week 41** artifact. Authoring the scaffold now means Week 41 is filling a form, not facing a blank page.
- **The twenty-instruction eval suite.** This week you run **one** happy-path instruction end to end. Curating and scoring the full 20-instruction suite, and fine-tuning the VLA against it, is **Week 44**. One clean run now; the suite later.
- **Robustness, edge cases, and recovery polish.** The happy path is the milestone. Adversarial inputs, degraded sensors, and the long tail are Phase 6 work. Do not gold-plate the run this week — get *one* clean pass observable in telemetry and sign the milestone.

The point of Week 40 is a sharp, load-bearing skill: read the contract, stand the whole robot up under a checklist, run it once cleanly with every layer on screen, and measure yourself honestly against the numbers you will be graded on in eight weeks. Everything in Phase 6 is downstream of getting this milestone signed.

## Stretch goals

If you finish the regular work early and want to push further:

- Read the **ROS2 Jazzy launch and lifecycle composition** docs end to end and convert your bring-up to a single `LaunchDescription` with a Nav2-style lifecycle manager: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html>.
- Wire your pre-flight check node into the launch graph as a **gate**: nothing downstream activates until pre-flight passes, using a lifecycle transition that the manager waits on.
- Add **`ros2 bag` recording** to your run so the milestone produces a replayable rosbag, not just a video. A bag is the artifact a reviewer can re-open; a video is the artifact a reviewer can watch.
- Read the **Foxglove "layouts as code"** docs and check your milestone dashboard layout into the repo so it is reproducible: <https://docs.foxglove.dev/docs/visualization/layouts>.
- Skim the **Open-RMF fleet-state message definitions** and make your `/fleet/heartbeat` conformant to a real schema rather than an ad-hoc one: <https://github.com/open-rmf/rmf_internal_msgs>.
- Read a **published robotics post-incident report** (the Open Robotics or a vendor engineering blog) and map its failure to one of this week's four integration-defect categories.

## Up next

Continue to **Week 41 — Capstone Integration Sprint + Safety Case** once your milestone is signed and your five-minute walkthrough is recorded. Week 41 takes the safety-case *template* you scaffolded this week and turns it into the portfolio-quality artifact — hazard log, FMEA, ISO 13482 / ISO 10218 framing, validation plan — and (Path A) begins the move to hardware. The pre-flight discipline you build this week becomes the hardware bring-up checklist; the telemetry spine becomes the operator dashboard; the chaos-drill template becomes the Gameday script. You have eight weeks. The robot exists now. The rest is making it real, making it safe, and making it defensible.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
