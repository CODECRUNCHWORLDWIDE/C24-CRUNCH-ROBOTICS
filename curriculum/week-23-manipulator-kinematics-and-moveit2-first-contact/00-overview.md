# Week 23 — Manipulator Kinematics and MoveIt2 First Contact

For twenty-two weeks the robot has been a thing that *moves*. This week it grows an arm, and the arm changes everything you thought you knew about geometry. A mobile base lives on a plane: two translations and one heading, three numbers, and your odometry tracks them. A 6-DOF arm lives in the full pose group `SE(3)` — three translations and three rotations, six numbers — and the map from the six joint angles you can command to the one end-effector pose you actually want is *nonlinear, many-to-one, and sometimes has no solution at all.* That map is **kinematics**, and by Friday you will be able to compute it forward by hand, invert it numerically, and hand the whole problem to MoveIt2 the way a senior robotics engineer does: knowing exactly what the planner is doing under the hood so that when it fails — and it will fail — you know whether the fault is your URDF, your IK seed, a singularity, or a collision you forgot to model.

We assume you finished **Week 22** and have a working MPC for the base, a `colcon` workspace that builds clean, and the `SE(3)` / twist / `tf2` fluency from **Weeks 1–2**. Those weeks were not warm-up. The homogeneous transform you built by hand in Week 2 *is* a link of the forward-kinematics chain you build this week; the quaternion you sanity-checked in Week 1 *is* the orientation half of a MoveIt2 pose goal. If `base → shoulder → elbow → wrist` as a `tf2` tree still makes sense to you, the arm is just a longer tree with the joints actuated.

The one thing to internalize before you read another line: **an arm is a chain, the chain has a Jacobian, and the Jacobian is the door to everything.** Forward kinematics tells you where the hand *is* given the joints. The Jacobian tells you how the hand *moves* when the joints move — it is the local linear map between joint velocity and end-effector velocity, and its rank, condition number, and null space tell you about singularities, manipulability, and redundancy. Velocity IK, singularity avoidance, manipulability optimization, and the numerical IK that MoveIt2 runs every time you send a pose goal are all *the Jacobian, used five different ways.* Learn it once, here, properly.

This week is where the robot stops being a vehicle and starts being a manipulator.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the forward kinematics of an open-chain manipulator two ways — the Denavit–Hartenberg (DH) convention and the product-of-exponentials (PoE / screw) formulation — and explain why the modern robotics literature increasingly prefers PoE.
- **Build** the homogeneous transform for each joint, compose them into the base-to-tool transform `T_base_tool(θ)`, and verify your composition against `tf2` and against MoveIt2's own forward-kinematics service.
- **Compute** the space and body Jacobians of a manipulator, read their columns as twists, and use the Jacobian to map joint velocities to end-effector twists and back.
- **Diagnose** a singularity from the Jacobian's loss of rank (its smallest singular value going to zero) and quantify how close you are with the Yoshikawa manipulability measure and the condition number.
- **Distinguish** the three families of inverse kinematics — closed-form (analytic), numerical (Jacobian / damped least squares), and precompiled (IKFast) — and choose the right one for a given arm and latency budget.
- **Implement** a damped-least-squares (Levenberg–Marquardt) numerical IK solver from scratch in Python, handle the singular case without blowing up, and explain why damping trades accuracy for stability near a singularity.
- **Bring up** a public 6-DOF arm (UR5e or MyCobot 280) in MoveIt2 + Gz Sim, understand the role of the `move_group` node, the SRDF, the planning scene, and the kinematics plugin, and send a pose goal from RViz.
- **Write** a `rclpy` node that consumes `geometry_msgs/PoseStamped` from a topic and triggers a plan-and-execute through the MoveIt2 action interface, with honest error handling for the planning-failed and execution-aborted cases.

## Prerequisites

This week assumes you have completed **C24 weeks 1–22**, or have equivalent ROS2 + robotics-math fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works; `ros2 doctor` runs clean.
- **`SE(3)`, homogeneous transforms, twists, and `tf2`** from Weeks 1–2. You can build a 4×4 transform from a rotation and a translation, compose a chain of them, and invert one. You know a quaternion from an Euler angle and why ZYX Euler is a debugging trap.
- **URDF and xacro** from Week 3. You can read a URDF, find a joint's `axis` and `origin`, and tell a `revolute` joint from a `prismatic` one.
- **MPC and state-space control** from Weeks 20–22 — not because the arm uses MPC this week (MoveIt2 manages the trajectory), but because the optimization mindset (cost functions, constraints, iterative solvers) carries directly into numerical IK.
- A `colcon` workspace you can build, and comfort with `ros2 action send_goal`, `ros2 service call`, and reading an action's feedback/result.
- **NumPy.** Every kinematics computation this week is linear algebra. You will multiply 4×4 matrices, take an SVD, and solve a damped least-squares system by hand in code.

You do **not** need prior MoveIt experience. We start from the `move_group` architecture and build up. If you have only ever used MoveIt through the RViz "drag the marker, click Plan" panel, this is the week that panel becomes a stack you understand.

## Topics covered

- **Forward kinematics, two conventions.** The **Denavit–Hartenberg** convention (the four parameters `a`, `α`, `d`, `θ`; the standard vs. modified DH split that has burned a generation of students) and the **product-of-exponentials** formulation (screw axes, the matrix exponential of a twist, the home configuration `M` and the space-frame screws). When each is the right tool, and why `tf2` is *already* doing forward kinematics for you.
- **The matrix exponential and screw theory in practice.** `exp([S]θ)` for a screw axis `S`, Rodrigues' formula for the rotation part, and the closed form for the translation part — implemented, not just stated, so the PoE forward kinematics is real code you can run.
- **The manipulator Jacobian.** The space Jacobian and the body Jacobian, building each column from the screw axes, the geometric interpretation (each column is the end-effector twist produced by unit velocity of one joint), and the relationship between the two via the adjoint.
- **Singularities and manipulability.** What it means for the Jacobian to lose rank, the three classic UR-style singularities (shoulder, elbow, wrist), the **Yoshikawa manipulability measure** `sqrt(det(J Jᵀ))`, the condition number, and the manipulability ellipsoid as the picture of "which directions the hand can move easily here."
- **Inverse kinematics, three families.** Closed-form analytic IK (fast, exact, arm-specific — the UR and most 6-DOF wrist-partitioned arms have one); numerical IK (Jacobian transpose, pseudoinverse, and **damped least squares / Levenberg–Marquardt** — general, iterative, seed-dependent); and **IKFast** (analytic IK compiled to C++ ahead of time). The accuracy / generality / latency trade space.
- **Damped least squares from scratch.** The pseudoinverse `J⁺ = Jᵀ(J Jᵀ)⁻¹`, why it explodes near a singularity, and the damping term `Jᵀ(J Jᵀ + λ²I)⁻¹` that tames it — derived, implemented, and tested against a singular pose so you *see* the difference.
- **MoveIt2 architecture.** The **`move_group`** node and the capabilities it aggregates; the **SRDF** (planning groups, virtual joints, disabled collision pairs); the **planning scene** (collision world + robot state); **OMPL** as the default planner library; the **kinematics plugin** (`KDL`, `TRAC-IK`, `IKFast`) and how `move_group` picks one; the **planning pipeline** (planner → simplifier → time-parameterization).
- **Driving MoveIt2 from code.** Sending a pose goal through the `MoveGroup` action, the `moveit_py` Python bindings vs. the raw action interface, the planning-scene service, and the honest error taxonomy: `PLANNING_FAILED`, `INVALID_MOTION_PLAN`, `CONTROL_FAILED`, `GOAL_CONSTRAINTS_VIOLATED`, and what each one actually means when your plan-and-execute returns it.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Forward kinematics: DH and product-of-exponentials          |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The Jacobian; singularities; manipulability                 |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Inverse kinematics; damped least squares from scratch       |    1.5h  |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | MoveIt2 architecture; `move_group`, SRDF, planning scene    |    0.5h  |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Driving MoveIt2 from a topic; plan-and-execute              |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                       |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, reachability writeup polish                   |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **7h**    | **3h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The kinematics texts, the MoveIt2 docs, the UR5e/MyCobot URDFs, and the talks worth your time |
| [lecture-notes/01-forward-kinematics-jacobian-singularities.md](./02-lecture-notes/01-forward-kinematics-jacobian-singularities.md) | DH and product-of-exponentials forward kinematics, the space/body Jacobian, singularities, and manipulability |
| [lecture-notes/02-inverse-kinematics-and-moveit2.md](./02-lecture-notes/02-inverse-kinematics-and-moveit2.md) | The three IK families, damped least squares from scratch, and the MoveIt2 architecture from `move_group` to the kinematics plugin |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-forward-kinematics.md](./03-exercises/exercise-01-forward-kinematics.md) | Build the UR5e forward kinematics by hand and verify against `tf2` and the MoveIt2 FK service |
| [exercises/exercise-02-damped-least-squares-ik.py](./03-exercises/exercise-02-damped-least-squares-ik.py) | Implement a damped-least-squares numerical IK solver and watch it stay stable through a singularity |
| [exercises/exercise-03-pose-goal-driver.py](./03-exercises/exercise-03-pose-goal-driver.py) | A `rclpy` node that consumes `PoseStamped` and triggers a MoveIt2 plan-and-execute through the action interface |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-reachability-map.md](./04-challenges/challenge-01-reachability-map.md) | Build a reachability map of the arm's workspace and explain its singular boundaries |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the analytic-vs-numerical IK comparison |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunch_arm` MoveIt2 bring-up + the pose-goal plan-and-execute service |

## The "the plan succeeded" promise

C24 uses a recurring marker for every exercise that ends in the arm actually moving where you asked. From Week 23 forward, that marker is a clean plan-and-execute result:

```
$ ros2 action send_goal /move_action moveit_msgs/action/MoveGroup ...
Result:
  error_code:
    val: 1          # SUCCESS  (moveit_msgs/MoveItErrorCodes.SUCCESS == 1)
  planning_time: 0.214
  trajectory:
    joint_trajectory:
      points: [ ... 9 waypoints ... ]
```

`error_code.val == 1` is `SUCCESS`. Any other value is a specific, named failure — `-1` is `FAILURE`, `-2` is `PLANNING_FAILED`, `-4` is `CONTROL_FAILED`, `-10` is `GOAL_CONSTRAINTS_VIOLATED`, and so on. The point of Week 23 is to make `val: 1` ordinary, and to make every *other* value a diagnosis you can name in one sentence — not a mystery that sends you re-reading your URDF at midnight.

## Stretch goals

If you finish the regular work early and want to push further:

- Derive the **closed-form analytic IK** for the UR5e by hand using the wrist-partition (spherical-wrist decoupling) method, and compare its eight solution branches against your damped-least-squares solver's single seed-dependent answer. The UR analytic IK is in the literature; reproducing it teaches you why the numerical solver only ever finds *one* of the eight.
- Generate an **IKFast** solver for the UR5e with OpenRAVE's `ikfast` generator, build it as a MoveIt2 kinematics plugin, and benchmark its solve time against `KDL` and `TRAC-IK` on a thousand random reachable poses. Analytic IK is microseconds; numerical IK is milliseconds — measure the gap.
- Plot the **manipulability ellipsoid** at three configurations (a well-conditioned reach, near the elbow singularity, and at full extension) and watch it collapse to a pancake as the smallest singular value goes to zero. This is the picture that makes singularities stop being abstract.
- Swap MoveIt2's kinematics plugin from `KDL` to **`TRAC-IK`** in the kinematics YAML and re-run the mini-project's reachable-pose set. `TRAC-IK` solves poses `KDL` gives up on; measure the success-rate difference yourself.

## Up next

Week 24 takes the MoveIt2 arm you bring up here and puts it in the **same launch graph as Nav2** — drive to a table, reach a pose, return — and adds the first **functional-safety primer**: the hazard log, fail-safe categories, and a `/safety/estop` topic that cancels both the Nav2 action and the MoveIt2 trajectory inside 200 ms. The arm you make move this week is the arm you make *stop* next week. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
