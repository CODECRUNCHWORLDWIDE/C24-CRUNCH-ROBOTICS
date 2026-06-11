# Week 23 — Resources

Every resource here is **free** and, where versioned, pinned to **ROS2 Jazzy** and the **MoveIt2** release that ships against it. The kinematics theory is timeless; the API references move with the distro. If you are on a newer distro later, swap `jazzy` for your distro name — the kinematics math is identical; only the API-reference URLs move.

The one paid-but-free-online exception is *Modern Robotics* by Lynch and Park, whose full PDF the authors host free with their permission. It is the single best book for the screw-theory framing of this week, and it is genuinely free.

## Required reading (work it into your week)

- **Lynch & Park, *Modern Robotics* — Chapter 3 (Rigid-Body Motions), Chapter 4 (Forward Kinematics), Chapter 5 (Velocity Kinematics and the Jacobian), Chapter 6 (Inverse Kinematics).** The product-of-exponentials formulation this week leans on, free PDF from the authors:
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **MoveIt2 — Concepts.** The `move_group` architecture, the planning scene, the SRDF, the kinematics plugin. Read it Thursday before the bring-up:
  <https://moveit.picknik.ai/main/doc/concepts/concepts.html>
- **MoveIt2 — "Your First MoveIt Project" / Move Group C++ and Python interfaces.** The plan-and-execute pattern Exercise 3 and the mini-project build on:
  <https://moveit.picknik.ai/main/doc/tutorials/tutorials.html>
- **ROS2 `tf2` — already-doing-forward-kinematics.** Re-read with arm eyes: every link transform in your URDF is one DH/PoE link, and `tf2` composes the chain for you:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html>

## Kinematics theory (the math under the planner)

- **Denavit–Hartenberg convention** — the four parameters, and the standard-vs-modified split that has burned generations. Read it knowing PoE is the modern alternative:
  <https://en.wikipedia.org/wiki/Denavit%E2%80%93Hartenberg_parameters>
- **Product of exponentials** — the screw-theory forward kinematics; `exp([S]θ)` and the home configuration `M`:
  <https://en.wikipedia.org/wiki/Product_of_exponentials_formula>
- **The manipulator Jacobian, manipulability, and singularities** — *Modern Robotics* Ch. 5 is the canonical treatment; the Yoshikawa measure `sqrt(det(J Jᵀ))` is defined there.
- **Damped least squares (Levenberg–Marquardt) IK** — the classic Buss tutorial, "Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares methods" (free PDF):
  <https://mathweb.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf>

## Arms you can bring up for free

- **Universal Robots ROS2 description (`ur_description`)** — the UR5e URDF/xacro this week's exercises target; official, free, Jazzy-supported:
  <https://github.com/UniversalRobots/Universal_Robots_ROS2_Description>
- **`ur_moveit_config`** — the MoveIt2 config for the UR family (SRDF, kinematics YAML, OMPL config):
  <https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver>
- **MyCobot 280 ROS2** — the affordable Path-B alternative; a real 6-DOF arm under ~USD 700, with a community URDF and MoveIt2 config:
  <https://github.com/elephantrobotics/mycobot_ros2>
- **MoveIt2 `panda_moveit_config` / `moveit_resources`** — the Franka Panda, the canonical MoveIt2 tutorial arm if you want the exact setup from the docs:
  <https://github.com/moveit/moveit_resources>

## MoveIt2 API references (open all week Thursday–Sunday)

- **MoveIt2 main docs** — the umbrella; concepts, tutorials, how-tos:
  <https://moveit.picknik.ai/main/index.html>
- **`moveit_py` (the Python bindings)** — `MoveItPy`, `PlanningComponent`, the planning-scene monitor from Python:
  <https://moveit.picknik.ai/main/doc/api/python_api/index.html>
- **`moveit_msgs` action and message definitions** — `MoveGroup.action`, `MoveItErrorCodes.msg` (the error taxonomy in the README's promise), `MotionPlanRequest`, `Constraints`:
  <https://github.com/moveit/moveit_msgs>
- **`MoveItErrorCodes`** — the integer codes; `SUCCESS == 1`, `PLANNING_FAILED == -2`, `CONTROL_FAILED == -4`, `GOAL_CONSTRAINTS_VIOLATED == -10`:
  <https://github.com/moveit/moveit_msgs/blob/ros2/msg/MoveItErrorCodes.msg>

## Kinematics plugins (the IK that `move_group` actually runs)

- **`KDL` kinematics plugin** — MoveIt2's default numerical IK (a Newton-Raphson Jacobian solver); fine, but gives up on poses `TRAC-IK` solves:
  <https://moveit.picknik.ai/main/doc/examples/kinematics_configuration/kinematics_configuration_tutorial.html>
- **`TRAC-IK`** — the drop-in numerical IK that converges where KDL stalls (a dual SQP + KDL approach):
  <https://traclabs.com/projects/trac-ik/>
- **`IKFast`** — analytic IK compiled to C++ via OpenRAVE's generator; microsecond solves for arms that have a closed form:
  <https://moveit.picknik.ai/main/doc/examples/ikfast/ikfast_tutorial.html>

## Tools you'll use this week

- **`ros2 run tf2_ros tf2_echo base_link tool0`** — read the live FK of the arm; your hand-computed `T_base_tool(θ)` must match this.
- **`ros2 service call /compute_fk moveit_msgs/srv/GetPositionFK`** — MoveIt2's own forward kinematics, the ground truth for Exercise 1.
- **`ros2 service call /compute_ik moveit_msgs/srv/GetPositionIK`** — MoveIt2's IK service; compare its answer to your from-scratch solver.
- **RViz2 + the MotionPlanning panel** — drag the interactive marker, click Plan, click Execute; the panel you'll learn to stop needing.
- **`ros2 action send_goal /move_action moveit_msgs/action/MoveGroup`** — the raw action interface under the panel.
- **NumPy** — `np.linalg.svd`, `np.linalg.pinv`, `scipy.linalg.expm` for the matrix exponential (or roll your own with Rodrigues).

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Forward kinematics (FK)** | Joints → end-effector pose. Always well-defined, one answer. |
| **Inverse kinematics (IK)** | End-effector pose → joints. Many answers, or none. The hard direction. |
| **DH parameters** | Four numbers (`a`, `α`, `d`, `θ`) per link that encode the FK chain. Standard vs. modified — pick one and say which. |
| **Product of exponentials (PoE)** | FK as a product of matrix exponentials of screw axes. The modern, frame-light formulation. |
| **Screw axis `S`** | A 6-vector `(ω, v)` describing a twist: an axis of rotation plus a pitch. |
| **`exp([S]θ)`** | The matrix exponential of a screw — the `SE(3)` transform from moving distance `θ` along screw `S`. |
| **Jacobian `J`** | The 6×n matrix mapping joint velocities to the end-effector twist. The local linear map. |
| **Space / body Jacobian** | The Jacobian expressed in the base frame vs. the end-effector frame; related by the adjoint. |
| **Singularity** | A configuration where `J` loses rank — the hand can't move in some direction no matter the joint speeds. |
| **Manipulability** | `sqrt(det(J Jᵀ))` (Yoshikawa) — a scalar "how far from a singularity" measure. Zero at a singularity. |
| **Pseudoinverse `J⁺`** | `Jᵀ(J Jᵀ)⁻¹` — the least-squares inverse of a non-square `J`. Explodes near singularities. |
| **Damped least squares** | `Jᵀ(J Jᵀ + λ²I)⁻¹` — the pseudoinverse with a damping term `λ` that stays finite at singularities. |
| **`move_group`** | The MoveIt2 node that aggregates planning, IK, the planning scene, and execution behind action/service interfaces. |
| **SRDF** | Semantic Robot Description Format — planning groups, virtual joints, disabled collision pairs. The URDF's semantic companion. |
| **Planning scene** | The collision world + the current robot state that the planner checks against. |
| **OMPL** | Open Motion Planning Library — MoveIt2's default sampling-based planners (RRTConnect, etc.). |

---

*If a link 404s, please open an issue so we can replace it.*
