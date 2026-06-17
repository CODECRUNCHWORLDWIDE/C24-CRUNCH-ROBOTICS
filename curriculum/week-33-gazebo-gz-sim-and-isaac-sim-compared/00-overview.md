# Week 33 — Gazebo, Gz Sim, and Isaac Sim Compared

Welcome to Phase 5, and to the first question every robotics team eventually argues about in a meeting: **which simulator?** By Friday you will be able to stand up the *same* robot in two simulators, run the *same* behavior in each, and produce a one-page write-up that says — with measurements, not allegiance — when Gz Sim wins, when Isaac Sim wins, and what specifically you traded away by choosing one.

You arrive here having spent Phases 1–4 almost entirely inside **Gz Sim** (the modern Gazebo). You spawned your week-3 diff-drive robot there, ran SLAM there, navigated there, and — last week — fine-tuned and evaluated learned policies against tasks living there. You treated the simulator as a fixed backdrop. This week the simulator becomes a *design decision* with consequences you can name, because Phase 5 is about closing the gap between sim and reality, and you cannot close a gap you don't understand the shape of.

The one thing to internalize before you read another line: **there is no "best" simulator — there is a simulator that best fits what you are optimizing for, and the axes you optimize on are throughput, fidelity, ROS-nativeness, and cost.** Gz Sim is free, ROS2-native, CPU-friendly, and the path of least resistance for system integration — it is where you build and debug your autonomy stack. **NVIDIA Isaac Sim** (and **Isaac Lab** on top of it) is GPU-accelerated, photorealistic via RTX, and can run **thousands of environments in parallel** on one GPU — it is where you *train* reinforcement-learning policies and do large-scale domain randomization (next week). The mistake is treating this as a religious war. The senior move is treating it as a table: list the axes, score each sim, pick per-purpose, and write down what you gave up.

This week you build that table from your own hands, not from a vendor slide.

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish** Gazebo Classic (end-of-life) from **Gz Sim** (the modern Gazebo: Garden/Harmonic), and explain why "Gazebo" in 2026 means Gz Sim and why Classic is a migration target, not a starting point.
- **Explain** the physics-engine landscape — **ODE, Bullet, DART, PhysX, MuJoCo** — what each is good at, which simulator exposes which, and why "the physics engine" is a choice, not a fixed property of the simulator.
- **Describe** Isaac Sim's architecture (USD scene description, the Omniverse/RTX renderer, the PhysX GPU back-end) and **Isaac Lab**'s role as the GPU-parallel RL/learning framework layered on top.
- **Author** a robot in both worlds: an **SDF/URDF + Gz plugins** description for Gz Sim, and the equivalent **USD + Isaac Sim API** setup — and articulate exactly what does and doesn't transfer between them.
- **Bridge** each simulator to ROS2: `ros_gz_bridge` for Gz Sim and the `isaacsim.ros2.bridge` (the Omniverse ROS2 bridge) for Isaac Sim, and explain the topic/QoS implications (your Week 5 QoS literacy applies directly).
- **Measure** what actually matters: real-time factor and step-time, sensor fidelity, and contact behavior — for the same robot+behavior in each sim — and present it as a defensible comparison.
- **Decide**, as a senior engineer would, which simulator to reach for given a concrete goal (debug an autonomy stack → Gz Sim; train a PPO policy over 4,096 envs → Isaac Lab), and own the Path B substitution honestly.

## Prerequisites

This week assumes you have completed **C24 weeks 1–32**, all of Phases 1–4. Specifically:

- You have a **robot URDF/xacro** you trust — the week-3 differential-drive base (chassis, two driven wheels, casters, a 2D LiDAR, an IMU) that has carried you through SLAM, Nav2, and the learned-policy weeks. *Every comparison this week runs the same robot in two sims.* If it's broken, fix it first.
- You have a **patrol or navigation behavior** — a behavior tree (Week 19) or a simple "drive a square / patrol three waypoints" routine — that you can run identically in either sim. The point is to hold the *behavior* fixed and vary the *simulator*.
- **Gz Sim** (Garden or Harmonic, paired with ROS2 Jazzy via `ros_gz`) installed and working — you've used it all course.
- Your **Week 5 QoS literacy** — the bridges publish sensor topics, and a QoS mismatch between a bridge and a subscriber is the same silent failure you learned to diagnose in Week 5.
- For the Isaac Sim half (Path A or a GPU-equipped Path B): an **NVIDIA GPU with ≥ 8 GB VRAM** and the Isaac Sim free install (or a cloud GPU box). **Path B without an NVIDIA GPU:** you substitute "Gz Sim with PhysX vs. Gz Sim with DART/ODE" and the Isaac material becomes read-and-reason rather than hands-on — documented per the lab below.

You do **not** need prior Isaac Sim or USD experience. Lecture 2 starts at "what is a USD stage" and builds up.

## Topics covered

- **Gazebo Classic vs. Gz Sim:** the rename and rewrite (Ignition → Gz), why Classic reached end-of-life, the Garden/Harmonic releases, and the `ros_gz` bridge ecosystem that replaced the old `gazebo_ros`.
- **The physics-engine landscape:** **ODE** (the old Gazebo default — robust, mature, CPU), **Bullet** (games + robotics, good contact), **DART** (accurate articulated-body dynamics, Gz Sim's featured engine), **PhysX** (NVIDIA's GPU-capable engine under Isaac Sim), **MuJoCo** (the RL-favorite, now open-source, excellent contact and speed for learning). Which sim exposes which, and how to switch the engine.
- **The throughput vs. fidelity trade-off:** real-time factor, headless and GPU-parallel stepping, why one high-fidelity world is the *wrong* tool for RL (you want thousands of cheap worlds — the Week 34 lesson), and why thousands of cheap worlds are the *wrong* tool for a final integration sign-off.
- **Isaac Sim & Isaac Lab:** USD (Universal Scene Description) as the scene format, the Omniverse RTX renderer for photorealism, PhysX GPU physics, tensorized parallel environments, and Isaac Lab as the RL/IL framework (the successor to Isaac Gym / OmniIsaacGymEnvs).
- **The ROS2 bridges:** `ros_gz_bridge` (declarative topic mapping, type conversion, QoS) vs. the Isaac Sim ROS2 bridge (OmniGraph action graphs publishing `sensor_msgs`/`tf`), and the QoS/timing implications of each.
- **Authoring in both:** SDF/URDF + Gz plugins (diff-drive, IMU, LiDAR — your week-3 plugins) vs. the USD + Isaac Sim Python API (articulations, sensors, the `SimulationApp`), and the lossy reality of cross-importing URDF↔USD.
- **Measuring fairly:** holding robot + behavior fixed, varying only the sim/engine; capturing real-time factor, step-time, sensor noise characteristics, and contact behavior; the senior-engineer comparison table.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Gazebo Classic vs Gz Sim; physics-engine landscape          |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Throughput vs fidelity; the same robot in Gz Sim, engine swap |  1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Isaac Sim + Isaac Lab; USD; the GPU-parallel story          |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | The ROS2 bridges; same behavior in both sims; measure        |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | The comparison table; sim-selection write-up                |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work (the comparison harness)             |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, write-up polish                               |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **8.5h**  | **4h**     | **4h**    | **5h**   | **11h**      | **2h**     | **36.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The Gz Sim docs, Isaac Sim/Lab docs, physics-engine references, and the talks worth your time |
| [lecture-notes/01-gazebo-gz-sim-and-the-physics-engines.md](./02-lecture-notes/01-gazebo-gz-sim-and-the-physics-engines.md) | Gazebo Classic vs Gz Sim, the physics-engine landscape, SDF/plugins, and `ros_gz` |
| [lecture-notes/02-isaac-sim-isaac-lab-and-the-comparison.md](./02-lecture-notes/02-isaac-sim-isaac-lab-and-the-comparison.md) | Isaac Sim/Lab, USD, the GPU-parallel story, the ROS2 bridge, and the comparison framework |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-physics-engine-swap.md](./03-exercises/exercise-01-physics-engine-swap.md) | Run the same robot in Gz Sim under two physics engines and measure the difference |
| [exercises/exercise-02-sim-metrics.py](./03-exercises/exercise-02-sim-metrics.py) | Subscribe to `/clock` + sensor topics and compute real-time factor, step-time, and sensor-rate fidelity |
| [exercises/exercise-03-isaac-scene-setup.py](./03-exercises/exercise-03-isaac-scene-setup.py) | Stand up the robot in Isaac Sim via the Python API (or the documented Path B Gz-engine substitution) |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-same-robot-two-sims.md](./04-challenges/challenge-01-same-robot-two-sims.md) | Run the identical patrol behavior in both sims and write the defensible comparison |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the headline sim-selection comparison write-up |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunchbot_sim_compare` harness: a reproducible, metric-driven Gz-vs-Isaac comparison |

## The "same robot, same behavior" promise

C24 uses a recurring marker for every comparison this week: **the only thing that may differ between two runs is the simulator (or the engine).** Same URDF. Same patrol. Same goals. Same measurement window.

```
=== SIM COMPARISON: crunchbot patrol (3 waypoints, 60 s window) ===
sim / engine            RTF      mean step (ms)   /scan Hz   contacts/ s   note
Gz Sim / DART           0.98     1.6              9.8        12            ROS-native, CPU
Gz Sim / Bullet         1.02     1.4              9.9        14            contact differs
Isaac Sim / PhysX       1.20     0.9 (GPU)        10.0       11            RTX render, GPU
```

If you cannot produce a table like that — same robot, same behavior, numbers in each cell — you have not finished the week. A "comparison" of two simulators you ran *different* robots or *different* behaviors in is not a comparison; it's two anecdotes.

## Stretch goals

If you finish the regular work early and want to push further:

- **Spin up Isaac Lab with parallel envs.** Launch a trivial Isaac Lab task with 64, then 1,024 parallel environments and watch total-environment-steps-per-second scale with the GPU. This is the throughput story that makes next week's domain randomization (and Week 28's parallel-sim RL) possible — *feel* the GPU-parallel advantage before you depend on it.
- **MuJoCo as a third point.** Bring the same arm into MuJoCo (now open-source) and note its contact-solver behavior and speed. MuJoCo is the RL community's favorite for a reason; seeing it next to PhysX and DART sharpens your engine intuition.
- **The URDF→USD round-trip.** Import your URDF into Isaac Sim (the URDF importer), export the USD, and re-inspect it. Document precisely what was lost or changed (inertials, joint limits, sensor plugins) — the lossy cross-format reality is a real integration hazard.
- **Sensor-fidelity deep dive.** Capture a LiDAR scan of the same scene in Gz Sim and Isaac Sim and overlay them. Where do they disagree (noise model, ray count, max range behavior)? Sensor fidelity is exactly the gap domain randomization (Week 34) exists to bridge.

## Up next

Week 34 is **Domain randomization and sim-to-real strategy** — and it depends directly on this week's throughput lesson. The reason you randomize over a thousand cheap worlds rather than chase fidelity in one expensive one is precisely the throughput vs. fidelity trade-off you measured here, and the GPU-parallel Isaac Lab path you stood up is the engine that makes thousand-world randomization tractable. Push your comparison harness before you start it; next week extends it into a randomization harness.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
