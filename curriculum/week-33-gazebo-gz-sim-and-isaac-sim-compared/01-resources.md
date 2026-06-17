# Week 33 — Resources

Every resource here is **free**. The Gz Sim docs are open; the Isaac Sim and Isaac Lab docs are public (the software is free to use, GPU required); the physics engines are open-source (ODE, Bullet, DART, MuJoCo) or freely available (PhysX). No paywalled material is linked.

Where a version matters: this week assumes **Gz Sim Harmonic** (paired with **ROS2 Jazzy** via `ros_gz`) and **Isaac Sim 4.x / Isaac Lab** (2026-current). If you are on Gz Garden or an older Isaac, the concepts are stable; only specific API names and a few URLs move.

## Gazebo / Gz Sim (where you build and debug)

- **Gazebo (Gz Sim) documentation home** — install, SDF, plugins, the `gz sim` CLI:
  <https://gazebosim.org/docs>
- **Gazebo release/feature matrix (Harmonic, Garden, and Classic EOL)** — which Gz release pairs with which ROS2 distro, and the Classic end-of-life notice:
  <https://gazebosim.org/docs/latest/releases>
- **SDF format specification** — the scene/robot description format Gz Sim uses natively:
  <http://sdformat.org/spec>
- **`ros_gz` (the ROS2 ↔ Gz bridge)** — `ros_gz_bridge`, `ros_gz_sim`, the declarative topic mapping:
  <https://github.com/gazebosim/ros_gz>
- **Migrating from Gazebo Classic to Gz Sim** — what changed, why, and how to port a Classic world:
  <https://gazebosim.org/docs/latest/migrating_gazebo_classic_ros2_packages>

## NVIDIA Isaac Sim & Isaac Lab (where you train)

- **Isaac Sim documentation** — install, the `SimulationApp`, the Python API, USD scenes, sensors:
  <https://docs.isaacsim.omniverse.nvidia.com/latest/index.html>
- **Isaac Lab documentation** — the GPU-parallel RL/IL framework on top of Isaac Sim (envs, tasks, training):
  <https://isaac-sim.github.io/IsaacLab/>
- **Isaac Sim ROS2 bridge** — the `isaacsim.ros2.bridge` extension; OmniGraph action graphs that publish `sensor_msgs`/`tf`:
  <https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/index.html>
- **Isaac Sim URDF importer** — bringing your week-3 URDF into a USD stage (the lossy round-trip in the stretch goal):
  <https://docs.isaacsim.omniverse.nvidia.com/latest/robot_setup/import_urdf.html>

## Universal Scene Description (USD) — the Isaac scene format

- **OpenUSD documentation** — the scene-description format Isaac Sim is built on (stages, prims, references):
  <https://openusd.org/release/index.html>
- **Pixar USD introduction** — the "what is a stage / a prim / a layer" primer; read this before Lecture 2's USD section:
  <https://openusd.org/release/intro.html>

## The physics engines

- **MuJoCo** — now open-source (DeepMind); the RL-favorite, excellent contact + speed:
  <https://mujoco.readthedocs.io/en/stable/overview.html>
- **NVIDIA PhysX** — the GPU-capable engine under Isaac Sim:
  <https://nvidia-omniverse.github.io/PhysX/physx/>
- **DART (Dynamic Animation and Robotics Toolkit)** — Gz Sim's featured engine, accurate articulated dynamics:
  <https://dartsim.github.io/>
- **Bullet Physics** — games + robotics, good contact:
  <https://pybullet.org/wordpress/>
- **ODE (Open Dynamics Engine)** — the old Gazebo default; mature, robust, CPU:
  <https://www.ode.org/>
- **Gz Sim physics plugins** — how Gz Sim selects an engine (`--physics-engine`) and which are available:
  <https://gazebosim.org/api/physics/latest/index.html>

## Context: choosing a simulator in 2026

- **A Review of Robotics Simulators / "which sim" surveys** — search recent (2024–2025) robotics-simulator survey papers for fidelity/throughput comparisons across Gz, Isaac, MuJoCo, PyBullet.
- **NVIDIA Isaac Lab blog / GTC robotics-learning talks** — the GPU-parallel-training pitch from the source; useful for the throughput numbers:
  <https://developer.nvidia.com/isaac/sim>
- **ROSCon Gz Sim sessions** — the maintainers on the Classic→Gz migration and the `ros_gz` design:
  <https://roscon.ros.org/>

## Tools you'll use this week

- **`gz sim`** — launch a world, `-r` to run, `-s`/`--headless-rendering` for headless, `--physics-engine gz-physics-<engine>-plugin` to swap engines.
- **`gz topic` / `gz stats`** — Gz's own introspection; `gz stats` prints real-time factor and step-time directly.
- **`ros2 topic hz` / `ros2 topic info -v`** — confirm bridged sensor rates and QoS (Week 5 muscle memory).
- **Isaac Sim `SimulationApp`** — the headless/standalone entry point for the Python-API scene setup.
- **`nvidia-smi` / `nvtop`** — watch the GPU during Isaac runs; the parallel-env stretch goal lives or dies on VRAM.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Gazebo Classic** | The original Gazebo; end-of-life. A migration target, not a starting point. |
| **Gz Sim** | The modern Gazebo (Garden/Harmonic), formerly "Ignition." ROS2-native, CPU-friendly. |
| **Isaac Sim** | NVIDIA's USD-based, RTX-rendered, PhysX-powered simulator. GPU required. |
| **Isaac Lab** | The GPU-parallel RL/IL framework on top of Isaac Sim (successor to Isaac Gym). |
| **USD** | Universal Scene Description — Pixar's scene format; Isaac Sim's native world format. |
| **SDF** | Simulation Description Format — Gz Sim's native world/robot format. |
| **ODE / Bullet / DART** | Open-source physics engines selectable in Gz Sim. DART is the featured one. |
| **PhysX** | NVIDIA's GPU-capable physics engine under Isaac Sim. |
| **MuJoCo** | Open-source physics engine; the RL community's favorite for contact + speed. |
| **`ros_gz_bridge`** | The ROS2 ↔ Gz Sim topic bridge (declarative type/topic mapping). |
| **Isaac ROS2 bridge** | The Omniverse extension that publishes Isaac Sim sensors/tf onto ROS2 topics. |
| **Real-time factor (RTF)** | Sim-time / wall-time. 1.0 = real time; >1 = faster than real time. |
| **Step-time** | Wall-clock time to advance the physics one step. Lower = faster sim. |
| **Parallel environments** | Many independent sim worlds stepped together on one GPU — the Isaac Lab advantage. |
| **Throughput vs fidelity** | The core trade-off: many cheap worlds (RL) vs. one accurate world (integration). |

---

*If a link 404s, please open an issue so we can replace it.*
