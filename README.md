# C24 · Crunch Robotics — Intelligent Robotics & Autonomy

> A forty-eight-week, mastery-tier track that takes an industry-ready engineer and walks them through every layer of a modern autonomous robot — math, ROS2, perception, sensor fusion, SLAM, planning, control, manipulation, learned policies, sim-to-real, multi-robot fleets, AI-powered task execution, safety cases, and on-call operations. By the end, you can architect, ship, and operate the autonomy stack of a real (or simulated) mobile manipulator that takes a natural-language instruction and carries it out under uncertainty without hurting anybody.

This is the longest track in Crunch Labs. It is also the most demanding. Robotics is genuinely a year of intentional work, and no shorter course produces the engineer described above. We refuse to oversell.

---

## Who this is for

C24 is built for four overlapping personas. If you see yourself in any of them, this is your track.

### Persona 1 · The firmware engineer pivoting to autonomy
You finished **C7 (Crunch Wire — Embedded Systems)** or have shipped firmware in industry. You know how a motor controller talks to an MCU, how to bring up a CAN bus at three in the morning, and how to debug a RTOS task that misses its deadline. You want to climb the stack — from "this device runs" to "this fleet of robots decides what to do." C24 is the bridge.

### Persona 2 · The ML engineer wanting embodied AI
You finished **C5 (AI / Data Science)** and probably **C23 (Crunch Agents)**. You can train, deploy, and orchestrate models. You are tired of agents that only manipulate text. You want your model to **touch the world** — to drive, grasp, place, and recover. C24 is where vision-language models meet wheels and grippers.

### Persona 3 · The mechanical or electrical engineer adding the software stack
You designed the chassis, you wired the harness, you sized the motors. The robot moves. Now it has to *think*. You want the software discipline — ROS2, sensor fusion, motion planning, learned policies — without the marketing fluff. C24 treats you as a peer engineer and never apologizes for the depth of math.

### Persona 4 · The senior backend engineer moving to a robotics startup
You have shipped at scale. You know microservices, observability, on-call. You have an offer from (or a tab open at) a robotics company and you need the discipline-specific vocabulary fast. C24 gives you the perception-to-policy stack, the safety case, the fleet ops, and a portfolio piece that lets you walk into the interview as a peer.

---

## What you can do at the end

After forty-eight weeks of intentional work, you can:

1. **Architect a ROS2 system** end-to-end — nodes, topics, services, actions, lifecycle, executors, QoS, composition, DDS tuning — and explain every choice in a design review.
2. **Calibrate and fuse a heterogeneous sensor stack** (IMU + wheel odometry + 2D/3D LiDAR + depth camera + RTK GPS) into a single, drift-bounded state estimate with quantified covariance.
3. **Ship a perception pipeline** that combines classical CV (corners, descriptors, optical flow, ICP) with learned models (YOLO family, DETR, SAM, Depth-Anything, Contact-GraspNet) and runs inside the latency budget of a Jetson Orin.
4. **Run a SLAM stack** (Cartographer for 2D, ORB-SLAM3 or FAST-LIO for 3D), localize against an existing map with AMCL, and recover when localization fails.
5. **Plan motion** with Nav2 for navigation and OMPL / MoveIt2 for manipulation — and write the behavior trees that wire them into a coherent task.
6. **Implement controllers** — PID, LQR, MPC, admittance/impedance — and pick the right one for the situation, with stability arguments you can defend.
7. **Train and deploy learned policies** — imitation (BC, DAgger), reinforcement (PPO, SAC), Diffusion Policy, Action Chunking Transformer — and integrate them into a ROS2 graph that still has fallbacks.
8. **Use vision-language models for robotics** — RT-2, OpenVLA, grounded planners — for language-conditioned manipulation, with the safety scaffolding that real deployment demands.
9. **Bridge sim and real** — bring up a robot in Gz Sim or Isaac Sim, apply domain randomization, transfer to hardware, and quantify the gap.
10. **Coordinate a small fleet** — shared mapping, distributed perception, task allocation — and ship telemetry to an operator dashboard.
11. **Bring up hardware** — motor controllers (ODrive, RoboClaw), micro-ROS for MCUs, CAN, encoders, IMU calibration — without losing a weekend per integration.
12. **Optimize edge ML for tight latency budgets** — TensorRT, ONNX Runtime, model pruning, quantization, mixed-precision — and meet a 30 ms perception cycle on Orin Nano.
13. **Construct a safety case** — ISO 13482 / ISO 10218 framings, fail-safe behaviors, software and hardware E-stop, hazard log, FMEA — at portfolio quality.
14. **Operate a robot in production** — telemetry, alerting, OTA updates, fleet rollback, on-call shift, remote teleop assist — and respond to a chaos drill (sensor dropout mid-task; planner deadlock at a doorway) without making the situation worse.

---

## Prerequisites

**Hard prerequisites**

- **C1 (Crunch Convos)** or equivalent — fluent Python.
- **C7 (Crunch Wire — Embedded Systems)** *or* equivalent industry firmware experience — you must already understand low-level I/O, real-time loops, RTOS basics, and embedded networking. The hardware-bring-up weeks assume this.
- **C5 (Crunch AI / Data Science)** *or* equivalent applied ML background — you must already be able to train a CNN, fine-tune a transformer, and reason about loss curves. We do not re-teach classical ML.

**Strongly recommended**

- **C23 (Crunch Agents)** before week 33 — the AI-powered-robotics phase leans heavily on grounded planners, structured tool use, and small-model deployment, which C23 covers properly.

**Helpful but optional**

- **C22 (Crunch Mesh)** — useful for the fleet-ops weeks; we teach the minimum distributed-systems vocabulary inline.
- **C15 (Crunch DevOps)** — useful for the OTA and telemetry weeks.

If you are coming straight from industry without the above tracks, expect to spend an extra two to three weeks shoring up Python, C++ basics, and applied ML before week 1.

---

## Program at a glance — six phases

C24 runs as six eight-week phases. Each phase ends with an integration milestone that gets reviewed against a rubric before you advance.

| Phase | Weeks | Theme | Milestone |
|---|---|---|---|
| **1 · Foundations** | 1–8 | Rigid-body math, SE(3), ROS2 deeply, first simulated robot, first SLAM in sim | A TurtleBot in Gz Sim drives a known map, publishes a clean TF tree, and runs Cartographer end-to-end. |
| **2 · Perception** | 9–16 | Classical + learned CV, depth, point clouds, sensor fusion, on-Jetson inference | A perception node fuses IMU + LiDAR + RGB-D, detects objects with a learned model, and runs inside a 30 ms cycle on an Orin Nano (or sim equivalent). |
| **3 · Planning & Control** | 17–24 | Nav2, A*, RRT*, behavior trees, PID → LQR → MPC, manipulator kinematics | The robot navigates a multi-room map autonomously and the manipulator reaches a goal pose under MPC. |
| **4 · Manipulation & Learning** | 25–32 | MoveIt2, grasping, imitation learning, RL, Diffusion Policy, ACT | A learned policy completes a constrained pick-and-place from demonstrations, with a classical fallback. |
| **5 · Sim2Real & Multi-Robot** | 33–40 | Isaac Sim, domain randomization, fleet coordination, vision-language robotics | A vision-language policy executes a language-conditioned task; two simulated robots share a map without collision. |
| **6 · Capstone** | 41–48 | Integrated mobile manipulator, safety case, fleet ops, chaos drills, interview prep | One graded robot, one safety case, two postmortems, one mock interview, one portfolio. |

---

## Weekly cadence

Plan for **36 hours per week** of focused work. We treat this as a full-time year. The distribution is, on average:

- **6 h** — lecture material and reading group
- **10 h** — supervised lab work (instructor office hours, paired code review)
- **14 h** — independent build (the heart of the week — your robot, your code)
- **4 h** — quiz, homework, and architecture-review writeup
- **2 h** — peer review of another learner's lab

A learner doing this part-time at 18 hours per week should plan on closer to ninety calendar weeks. We will not pretend otherwise.

---

## Hardware expectations — explicit, with an affordable alternate path

Robotics is the most hardware-expensive track in Crunch Labs. We refuse to make hardware a gate. Two paths are supported end-to-end; both clear the capstone bar.

### Path A · Physical robot (recommended if budget allows)

- **Phase 1 (weeks 1–8)** — Laptop only. Ubuntu 22.04 or 24.04 (or a Windows + WSL2 + Docker setup), ROS2 Humble/Iron/Jazzy, Gz Sim. A discrete GPU is helpful for the visualization labs but not required.
- **Phase 2 (weeks 9–16)** — Add a **Jetson Orin Nano (8 GB)** and a simple wheeled platform: **TurtleBot 4 Lite** (off-the-shelf, ~USD 1,200) *or* a DIY differential-drive base (Roomba chassis or 4WD aluminum kit + 2x BLDC with ODrive S1 + RPLIDAR A2). A **RealSense D435i** or **OAK-D Lite** depth camera is required.
- **Phase 3 (weeks 17–24)** — Same platform; the Orin Nano handles Nav2 and the perception cycle.
- **Phase 4 (weeks 25–32)** — Add a **6-DOF manipulator**. Open-source options: **PiArm**, **MyCobot 280 Pi**, or a used **UR-style** arm if the budget allows. Mastery-track learners aiming for learned policies should upgrade to a **Jetson Orin NX (16 GB)** or **AGX Orin**.
- **Phase 5+6 (weeks 33–48)** — Same platform. The capstone integrates the wheeled base + arm into one autonomous mobile manipulator.

### Path B · Simulation only (the affordable path)

- **Every phase** — Laptop with a discrete GPU (NVIDIA, ≥ 8 GB VRAM recommended; Apple Silicon acceptable for CPU-bound labs). **Gz Sim** for the first half; **NVIDIA Isaac Sim** (free tier) for phases 4 onward where GPU-accelerated training matters.
- **No physical robot.** The capstone is **fully gradable in simulation**. The rubric scores autonomy-stack quality, safety case construction, and chaos-drill recovery — *not* whether a real robot was bought.

A learner on Path B who cannot run Isaac Sim locally can substitute Gz Sim throughout, with a small expressiveness penalty in the learned-policy weeks. We document the substitution in each affected lab.

### Always required, regardless of path

- A laptop you can install Ubuntu (or run WSL2 / Linux VM) on, with at least **16 GB RAM**, **256 GB free disk**, and a **modern x86_64 or Apple Silicon CPU**.
- A GitHub account for the public portfolio.
- A Foxglove account (free tier) for the visualization weeks.
- Roughly **USD 25/month** of cloud GPU credit (Lambda, RunPod, or equivalent) for the four weeks where you train a Diffusion Policy or PPO controller and your laptop is not enough. This applies on both paths.

---

## Recommended pre/post tracks

### Pre-track pathways

- **Pathway D (Robotics Engineer, umbrella charter):** C1 → **C7 (Wire)** → **C24**.
- **AI-robotics specialization:** C1 → **C5 (AI/DS)** → **C23 (Agents)** → **C24** *(strongly recommended for the AI-powered-robotics phase)*.
- **Full breadth:** C1 → **C7** → **C5** → **C23** → **C24**.

### Post-track destinations

- **Robotics software engineer** at a mobile-robot startup (warehouse, last-mile, hospitality).
- **Autonomy engineer** at a self-driving, drone, or AMR company.
- **Embodied-AI research engineer** at a lab building generalist robot policies.
- **Robotics platform / fleet-ops engineer** at a company operating robots at scale.

The capstone is engineered to be the artifact you put at the top of your résumé. The safety-case appendix and the chaos-drill postmortems are designed to be the artifact that wins the second-round interview.

---

## How this track is graded

Crunch Labs grading is intentionally rigorous. Per the [Crunch Labs Charter](../CRUNCH-LABS-CHARTER.md):

- **Weekly quizzes** — 10 questions each, answer key in-repo.
- **Weekly labs** — pass/fail against an acceptance rubric.
- **Two midterm architecture reviews** — at weeks 16 and 32, you defend your stack to a panel.
- **Two capstone reviews** — at weeks 40 (sim milestone) and 48 (final).
- **One gameday / chaos drill** — week 46, live-graded.
- **One mock robotics-startup interview** — week 47, system-design + technical.
- **One safety-case writeup** — week 41, portfolio-quality artifact.

Full assessment matrix and capstone rubric live in [`SYLLABUS.md`](./SYLLABUS.md).

---

## Repo layout (target)

```text
C24-CRUNCH-ROBOTICS/
├── README.md                     ← this file
├── SYLLABUS.md                   ← 48-week breakdown, capstone spec, assessment matrix
├── CHARTER.md                    ← design rationale
├── LICENSE                       ← GPL-3.0 pointer
├── curriculum/
│   ├── week-01-rigid-body-math-and-ros2-intro/
│   ├── week-02-tf2-urdf-and-the-first-simulated-robot/
│   ├── ...
│   └── week-48-final-capstone-defense/
├── interview-prep/               ← robotics-startup system-design + technical drills
├── production-runbook.md         ← what an on-call shift on a robot fleet actually looks like
├── portfolio.md                  ← three flagship projects polished for a recruiter
└── safety-case-template/         ← reusable ISO 13482 / ISO 10218 writeup scaffold
```

Each weekly folder follows the per-week schema set by the [Crunch Labs Charter](../CRUNCH-LABS-CHARTER.md): `README.md`, `resources.md`, `lecture-notes/`, `exercises/`, `challenges/`, `quiz.md`, `homework.md`, `mini-project/`.

---

## Maintainers

- **Curriculum council** — Code Crunch Club
- **Track lead** — Crunch Robotics maintainer team
- **Brand** — Robotics sub-brand, accent `#DC2626` (cinnabar)
- **Status** — In progress, target launch cohort 2026
- **License** — [GPL-3.0-or-later](./LICENSE)

To propose an amendment, open an issue on the master curriculum repository tagged `track:C24`. To contribute a lab or a lecture, see `CONTRIBUTING.md` at the monorepo root.

---

*Sequel to nobody. Prerequisite for the rest of your career in robotics.*
