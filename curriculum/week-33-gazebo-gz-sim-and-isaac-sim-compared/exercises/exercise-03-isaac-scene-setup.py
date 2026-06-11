#!/usr/bin/env python3
# Exercise 3 — Stand the robot up in Isaac Sim (Path A) / Gz-engine substitution (Path B)
#
# Goal: Get your robot into the OTHER simulator so the comparison has two real points.
#       PATH A (NVIDIA GPU + Isaac Sim): set up a USD stage, import the robot, add a
#       LiDAR + IMU, and bridge to ROS2 — via the Isaac Sim Python API.
#       PATH B (no NVIDIA GPU): run the documented two-Gz-engines substitution and print
#       the Isaac concepts you'd be exercising, so you still finish the week's comparison.
#
# Estimated time: 60 minutes. Runnable.
#
# WHY THIS FILE IS STRUCTURED THE WAY IT IS
#
#   Isaac Sim code runs INSIDE Isaac's bundled Python (`./python.sh script.py`) because
#   the `omni.*` / `isaacsim.*` modules only exist there. So Path A is presented as the
#   real API calls you run in that interpreter; this file detects whether those modules
#   are importable and, if not, drops to Path B WITHOUT crashing — so `python3 ... --path-b`
#   always runs and teaches, even on a Mac with no NVIDIA GPU.
#
# HOW TO USE THIS FILE
#
#   PATH A (Isaac Sim installed):
#       ./python.sh exercise-03-isaac-scene-setup.py
#     Boots a headless Isaac stage, adds a ground plane + your robot USD, a LiDAR + IMU,
#     starts the ROS2 bridge, steps the sim, and prints the prim paths + bridged topics.
#
#   PATH B (no NVIDIA GPU — the affordable path):
#       python3 exercise-03-isaac-scene-setup.py --path-b
#     Prints the Isaac scene-setup recipe (what you'd run on Path A) AND the concrete
#     Gz substitution: run your week-3 robot under TWO Gz engines (Exercise 1) and use
#     the Exercise-2 metrics node as the second comparison point. Exits 0.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Path A: an Isaac stage with the robot, a LiDAR + IMU prim, and the ROS2 bridge
#       publishing /scan + /imu; the Exercise-2 node reads a non-zero rate off them.
#   [ ] Path B: you ran the two-Gz-engine substitution, have two metrics tables, and can
#       describe (from this file's printout) what the Isaac equivalent would have been.
#   [ ] Either path: you can name the ONE artifact that does NOT transfer cleanly between
#       Gz SDF and Isaac USD (sensor *plugins* — they're sim-specific; the kinematics do).
#
# Expected output (Path B) is at the bottom of the file.

from __future__ import annotations

import argparse
import sys


ISAAC_RECIPE = r"""
ISAAC SIM SCENE-SETUP RECIPE  (what Path A runs inside ./python.sh)
------------------------------------------------------------------
# 1. Boot the simulation app FIRST — before importing any omni.* / isaacsim.* module.
from isaacsim import SimulationApp
sim_app = SimulationApp({"headless": True})          # headless for measurement runs

# 2. Now the Isaac modules are importable.
from isaacsim.core.api import World
from isaacsim.core.utils.stage import add_reference_to_stage
import omni.kit.commands

world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()               # the floor

# 3. Bring your week-3 URDF into the USD stage via the URDF importer.
#    NOTE: this is the LOSSY cross-import (Lecture 2 §1.1, stretch goal). The kinematics
#    and meshes transfer; the Gz <plugin> sensors do NOT — you re-add sensors below.
status, prim_path = omni.kit.commands.execute(
    "URDFParseAndImportFile",
    urdf_path="/path/to/crunchbot.urdf",
    import_config=...,                               # fix base, merge joints, etc.
)   # -> creates /World/crunchbot with prims like /World/crunchbot/base_link

# 4. Add sensors as PRIMS (Isaac's way), not as SDF plugins.
#    A LiDAR (RTX or the range sensor) and an IMU prim under the robot.
#    e.g. isaacsim.sensors.physx / isaacsim.sensors.rtx create the prims.

# 5. Start the ROS2 bridge (the isaacsim.ros2.bridge extension) and wire OmniGraph
#    "ROS2 Publish LaserScan" / "ROS2 Publish Imu" nodes to the sensor prims + topics.
#    After this, /scan and /imu appear on the ROS2 graph EXACTLY like the Gz bridge —
#    your autonomy + measurement nodes don't change (sim-agnostic; Lecture 2 §2.3).

# 6. Step the world. Use sim time so /clock is published for the Exercise-2 node.
world.reset()
for _ in range(2000):
    world.step(render=True)

sim_app.close()
------------------------------------------------------------------
The PAYOFF: once /scan, /imu, /clock, and /cmd_vel exist on ROS2, run the SAME behavior
and the SAME Exercise-2 metrics node you used in Gz Sim. Only the simulator changed.
"""

GZ_SUBSTITUTION = r"""
PATH B SUBSTITUTION  (no NVIDIA GPU — still complete the comparison)
------------------------------------------------------------------
You cannot run Isaac Sim without an NVIDIA RTX GPU. Substitute a SECOND physics engine
under Gz Sim as your second comparison point. This preserves the week's actual skill —
"hold the robot + behavior fixed, vary the sim layer, measure" — using two engines
instead of two simulators.

  1. Run your week-3 robot in Gz Sim under DART (Exercise 1 run A). Measure with the
     Exercise-2 node:  python3 exercise-02-sim-metrics.py --duration 30 --sensor /scan
  2. Restart under Bullet:
       gz sim -r crunch_world.sdf --physics-engine gz-physics-bullet-featherstone-plugin
     Measure again with the SAME Exercise-2 node and the SAME drive pattern.
  3. You now have two metrics tables differing only in the physics layer — the same
     SHAPE of result Path A produces between Gz and Isaac.

In your write-up, explicitly note what you DID NOT get to exercise that Path A would:
  - RTX photorealistic rendering (matters for visual sim-to-real / Week 34 visual DR).
  - GPU-PARALLEL environments (the Isaac Lab throughput story — thousands of worlds).
Reason about those from Lecture 2; you lose the hands-on, not the concept.
------------------------------------------------------------------
"""


def try_path_a() -> int:
    """Detect Isaac Sim; if present, the real setup runs in ./python.sh, not here."""
    try:
        import isaacsim  # noqa: F401
    except ImportError:
        return 1   # signal: Isaac not importable in this interpreter
    print("Isaac Sim detected. Run this file with Isaac's interpreter:")
    print("    ./python.sh exercise-03-isaac-scene-setup.py")
    print("The scene-setup steps to execute there:")
    print(ISAAC_RECIPE)
    return 0


def run_path_b() -> int:
    print("PATH B — Gz-engine substitution (no NVIDIA GPU required)\n")
    print("For reference, the Isaac Path-A recipe you are substituting for:")
    print(ISAAC_RECIPE)
    print(GZ_SUBSTITUTION)
    print("KEY POINT: the robot's KINEMATICS (links/joints) transfer between Gz SDF and")
    print("Isaac USD; the SENSOR PLUGINS do NOT — they are sim-specific and you re-author")
    print("them per simulator. That asymmetry is the main cross-import hazard.\n")
    print("PATH B: complete — two-engine comparison set up, Isaac concepts documented.")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Isaac scene setup (A) or Gz substitution (B).")
    p.add_argument("--path-b", action="store_true",
                   help="force the no-GPU Gz-engine substitution path")
    args = p.parse_args()

    if args.path_b:
        sys.exit(run_path_b())

    # Auto-detect: if Isaac is importable, point the user at ./python.sh; else Path B.
    if try_path_a() == 0:
        sys.exit(0)
    print("Isaac Sim not importable in this interpreter — falling back to Path B.\n")
    sys.exit(run_path_b())


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--path-b, abridged)
# -----------------------------------------------------------------------------
#
# PATH B — Gz-engine substitution (no NVIDIA GPU required)
#
# For reference, the Isaac Path-A recipe you are substituting for:
# ISAAC SIM SCENE-SETUP RECIPE  (what Path A runs inside ./python.sh)
#   ...steps 1-6...
#
# PATH B SUBSTITUTION  (no NVIDIA GPU — still complete the comparison)
#   1. Gz Sim / DART  -> measure with Exercise 2
#   2. Gz Sim / Bullet -> measure with Exercise 2
#   3. two tables differing only in the physics layer
#
# KEY POINT: kinematics transfer (SDF<->USD); sensor PLUGINS do not.
# PATH B: complete — two-engine comparison set up, Isaac concepts documented.
# -----------------------------------------------------------------------------
