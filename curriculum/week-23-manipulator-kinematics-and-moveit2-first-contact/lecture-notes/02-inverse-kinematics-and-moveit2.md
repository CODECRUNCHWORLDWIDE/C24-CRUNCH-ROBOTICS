# Lecture 2 — Inverse Kinematics and the MoveIt2 Architecture

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can name the three families of IK solver and pick the right one, implement a damped-least-squares numerical IK from scratch that survives a singularity, and explain the MoveIt2 stack from `move_group` down to the kinematics plugin so a pose-goal failure is a diagnosis, not a mystery.

Lecture 1 built the *easy* direction — joints to pose — and its derivative, the Jacobian. This lecture is the *hard* direction: pose to joints, **inverse kinematics**. It is hard for a reason that is geometric, not algorithmic: the map from six joints to a 6-DOF pose is many-to-one (a typical 6-DOF arm has up to **eight** distinct joint configurations that reach the same pose) and not-always-onto (poses outside the workspace have *zero* solutions). So an IK solver is never just "compute the inverse." It is "find *a* valid configuration, or honestly report that there isn't one," and the three families of solver make different trades to do that.

---

## 1. Why IK is hard

Forward kinematics is a function: one input, one output, always defined. Inverse kinematics is a *relation*:

- **Many solutions.** A 6-DOF arm reaching a pose typically has up to 8 solutions — elbow-up vs elbow-down, wrist-flipped vs not, shoulder-left vs -right. They are all *correct*; they differ in which one is collision-free, which is far from a joint limit, and which is closest to where the arm is now.
- **No solutions.** Ask for a pose outside the reachable workspace and there is no answer. A good solver says so quickly; a bad one spins forever.
- **Singular solutions.** Near a singularity (Lecture 1 §5) the solution exists but the solver's linear step blows up, demanding huge joint velocities for tiny pose corrections.

Every IK family below is a different answer to "how do I find one valid configuration while handling those three realities."

---

## 2. Family 1 — closed-form analytic IK

For arms with special geometry — in particular a **spherical wrist** (the last three joint axes intersect at a point), which the UR family and most industrial 6-DOF arms have — IK has a **closed-form algebraic solution.** You decouple the problem: the wrist *center* position depends only on the first three joints (solve those with geometry/trigonometry), and the wrist *orientation* depends only on the last three (solve those from the remaining rotation). The result is a handful of explicit formulas that produce all (up to eight) solution branches in **microseconds**, exactly, with no iteration and no seed.

- **Pros:** fast (µs), exact, finds *all* solutions, never gets stuck.
- **Cons:** arm-specific (you derive it once per arm geometry), only exists for arms with the right structure, and the derivation is fiddly.

This is the gold standard *when it exists.* The UR analytic IK is published; deriving it is a README stretch goal. When you can't or won't derive it by hand, **IKFast** (Family 3) generates it for you.

---

## 3. Family 2 — numerical IK (the Jacobian methods)

When you don't have a closed form, you **iterate.** Start from a seed configuration `θ₀`, compute the pose error between where the hand is and where you want it, use the Jacobian to take a step that reduces the error, and repeat until you converge (or give up). This is general — it works on *any* chain, including ones with no analytic solution — at the cost of being iterative (milliseconds, not microseconds), seed-dependent (it finds the *one* solution nearest the seed, not all eight), and capable of failing to converge near singularities if you're not careful.

### 3.1 The pose error as a twist

At each iteration you need a 6-vector error between the current pose `T_cur` and the target `T_goal`. The clean way is the twist that would carry `T_cur` to `T_goal` in unit time — the log of the relative transform:

```python
import numpy as np

def pose_error_twist(T_cur, T_goal):
    """6-vector (angular, linear) error twist from T_cur to T_goal, in the base frame."""
    # Relative rotation -> axis-angle (the angular error).
    R_err = T_goal[:3, :3] @ T_cur[:3, :3].T
    angle = np.arccos(np.clip((np.trace(R_err) - 1) / 2, -1.0, 1.0))
    if abs(angle) < 1e-9:
        w_err = np.zeros(3)
    else:
        axis = (1 / (2 * np.sin(angle))) * np.array([
            R_err[2, 1] - R_err[1, 2],
            R_err[0, 2] - R_err[2, 0],
            R_err[1, 0] - R_err[0, 1],
        ])
        w_err = axis * angle
    # Linear error (the translation difference).
    v_err = T_goal[:3, 3] - T_cur[:3, 3]
    return np.concatenate([w_err, v_err])
```

### 3.2 The naive pseudoinverse step — and why it explodes

The obvious step is: joint correction = (pseudoinverse of Jacobian) × (pose error).

```
Δθ = J⁺ · e        where  J⁺ = Jᵀ(J Jᵀ)⁻¹   (the right pseudoinverse)
```

This works beautifully far from singularities and **catastrophically near them.** Recall from Lecture 1 §5.1 that near a singularity the smallest singular value `σ_min → 0`. The pseudoinverse contains a `1/σ` factor, so as `σ_min → 0` the step `Δθ` → infinity: you ask for a millimeter of hand motion and the solver commands a joint to slew 50 radians. On a real arm that is a violent, dangerous lurch; in simulation it's an exploded robot. The naive pseudoinverse is *correct math and unusable engineering* near singularities.

### 3.3 Damped least squares (Levenberg–Marquardt) — the fix

The fix is to add a **damping term** `λ²` that keeps the inverse finite even when `σ_min` hits zero:

```
Δθ = Jᵀ(J Jᵀ + λ²I)⁻¹ · e
```

This is the **damped least squares** (DLS) method, equivalent to Levenberg–Marquardt. The `λ²I` term means the worst-case amplification is bounded by roughly `1/(2λ)` instead of `1/σ_min` — so near a singularity the solver takes a *smaller, safe* step in the collapsed direction instead of an infinite one. You trade a little accuracy (the step no longer perfectly nulls the error in the singular direction) for stability (it never blows up). That trade is almost always the right one on a real robot.

```python
def dls_ik_step(J, e, lam=0.05):
    """One damped-least-squares joint step. lam is the damping; bigger = safer, slower."""
    n = J.shape[1]
    JT = J.T
    return JT @ np.linalg.solve(J @ JT + (lam ** 2) * np.eye(6), e)
```

A complete DLS IK loop seeds at the current configuration, steps, and checks convergence:

```python
def dls_ik(fk, jac, theta0, T_goal, lam=0.05, tol=1e-4, max_iters=200):
    """Damped-least-squares IK. Returns (theta, converged).

    fk(theta)  -> 4x4 current pose
    jac(theta) -> 6xn space Jacobian
    """
    theta = np.array(theta0, float)
    for _ in range(max_iters):
        e = pose_error_twist(fk(theta), T_goal)
        if np.linalg.norm(e) < tol:
            return theta, True
        theta = theta + dls_ik_step(jac(theta), e, lam)
    return theta, False     # honest failure: did not converge in budget
```

The honest `(theta, converged)` return is the point. A solver that returns garbage and claims success is worse than one that says "I didn't make it." Exercise 2 makes you run this *through* a singular pose and watch the damping keep it stable where the naive pseudoinverse diverges.

### 3.4 The kinematics plugins MoveIt2 ships

MoveIt2's default numerical IK plugin is **`KDL`** — a Newton-Raphson Jacobian solver in the spirit above. It's fine, but it gives up on poses near limits or singularities more often than you'd like. The popular drop-in replacement is **`TRAC-IK`**, which runs a damped solver *and* a nonlinear-optimization solver in parallel and returns whichever converges first — it solves many poses `KDL` abandons. Swapping `KDL` for `TRAC-IK` in the kinematics YAML is a one-line change and a real success-rate win; it's a README stretch goal and a homework problem.

---

## 4. Family 3 — IKFast (precompiled analytic IK)

**IKFast** (from OpenRAVE) is the best-of-both: you feed it the arm's kinematics once, and it *generates and compiles* the closed-form analytic IK to C++ ahead of time. At runtime it's analytic-IK fast (microseconds, all solutions, no seed) but you didn't have to derive the algebra by hand. The catch is the offline generation step (it can be finicky, and it needs the arm to have a solvable structure) and that the compiled plugin is arm-specific.

The decision, in one table:

| Family | Speed | Finds all solutions? | Needs a seed? | Works on any arm? | When to reach for it |
|---|---|---|---|---|---|
| **Analytic (by hand)** | µs | Yes | No | No (special geometry) | You need every branch and have the geometry; teaching/derivation. |
| **Numerical (KDL / TRAC-IK / your DLS)** | ms | No (one near the seed) | Yes | Yes | General arms, MoveIt2 default, anything without a closed form. |
| **IKFast (compiled analytic)** | µs | Yes | No | Arms with a solvable structure | Production, high-rate IK, when you can run the generator once. |

For this week's mini-project the numerical path is what MoveIt2 uses by default and what you build from scratch. Know that the other two exist and why a shop reaches for IKFast when it needs to solve IK at 1 kHz.

---

## 5. The MoveIt2 architecture

You've built FK, the Jacobian, and IK by hand. Now meet the system that wraps all of it for real planning. MoveIt2 is not one thing — it's a constellation of components orchestrated by one central node.

### 5.1 `move_group`: the orchestrator

The **`move_group`** node is the heart of MoveIt2. It does not plan, solve IK, or check collisions *itself* — it *aggregates* the components that do, and exposes them behind a uniform set of ROS2 action and service interfaces. When you send a pose goal, `move_group`:

1. takes your goal (a pose or joint target plus constraints),
2. calls the **kinematics plugin** to turn a pose goal into joint targets (IK),
3. asks the **planning pipeline** (OMPL by default) for a collision-free joint-space path,
4. runs the path through a **smoother** and a **time-parameterization** step (to respect velocity/acceleration limits),
5. hands the timed trajectory to a **controller** for execution,
6. returns a `MoveItErrorCodes` result.

Every one of those steps is a place a plan-and-execute can fail, and the error code tells you *which*. That is the architecture you must hold in your head to debug MoveIt2 at all.

### 5.2 The inputs: URDF, SRDF, and the config

`move_group` needs three descriptions:

- **The URDF** (Week 3) — the kinematic and collision geometry. Links, joints, meshes, limits.
- **The SRDF** (Semantic Robot Description Format) — the *semantic* layer the URDF lacks: **planning groups** (e.g., `ur_manipulator` = the six arm joints; `gripper` = the finger joints), the **virtual joint** that attaches the robot to the world, named poses (`home`, `ready`), and the **disabled collision pairs** (links that are *always* adjacent — like a wrist and its mounting flange — so the collision checker doesn't waste time on them or, worse, declare the home pose in self-collision). A wrong SRDF is a top-three cause of "MoveIt2 says everything collides."
- **The kinematics, OMPL, and controllers YAML** — which kinematics plugin (`KDL` / `TRAC-IK` / `IKFast`), which OMPL planner, and which ROS2 controllers execute the trajectory.

The MoveIt Setup Assistant generates the SRDF and these YAMLs from your URDF; for the public arms in `resources.md` they already exist (`ur_moveit_config`).

### 5.3 The planning scene

The **planning scene** is `move_group`'s model of the world it must avoid: the current robot state *plus* a collision world of obstacles (the table, a wall, objects to manipulate). You add and remove collision objects through the planning-scene interface; OMPL checks every candidate path against it. The first time the arm "won't plan to a perfectly reachable pose," the planning scene is the first suspect — a stale collision object, or a table you forgot to add so the arm plans *through* it.

### 5.4 OMPL: the planner library

MoveIt2's default planners come from **OMPL** (Open Motion Planning Library) — sampling-based planners like **RRTConnect** (the workhorse default), RRT*, and BIT*. Sampling-based means: randomly sample joint configurations, connect collision-free ones into a tree/graph, and search for a path from start to goal. This is *why* RRT-family planners "dominate manipulation" (the Week 18 framing): a 6-DOF joint space is too high-dimensional for grid search, but sampling handles it. The trade is that sampling-based plans are non-deterministic (two runs give different paths) and benefit from a post-plan **smoother** to remove the jitter.

### 5.5 The error taxonomy (the README's promise, decoded)

Every plan-and-execute returns a `moveit_msgs/MoveItErrorCodes`. The ones you will actually see:

| `error_code.val` | Name | What it actually means |
|---:|---|---|
| `1` | `SUCCESS` | The plan was found and executed. The line you want. |
| `-1` | `FAILURE` | Generic failure; check the logs for the real reason. |
| `-2` | `PLANNING_FAILED` | OMPL could not find a collision-free path in the time budget. Often a planning-scene or reachability problem. |
| `-3` | `INVALID_MOTION_PLAN` | The plan was malformed (e.g., start state in collision). |
| `-4` | `CONTROL_FAILED` | The trajectory was sent but the controller didn't track it — a controller/hardware problem, not a planning one. |
| `-7` | `NO_IK_SOLUTION` | IK found no joint configuration for the pose goal. The pose is unreachable or singular. |
| `-10` | `GOAL_CONSTRAINTS_VIOLATED` | The executed motion ended outside the goal tolerance. |

The discipline this buys you: when `error_code.val` is not `1`, you do **not** start randomly editing. You read the code, and it routes you — `-7` sends you to check reachability (is the pose even in the workspace? Lecture 1 and the challenge), `-2` sends you to the planning scene (did I add a collision object that blocks every path?), `-4` sends you to the controllers (is the controller active and tracking?). One number, one direction to look. That is the entire reason to learn the architecture instead of treating MoveIt2 as magic.

---

## 6. Driving `move_group` from code

You have two ways to send a goal programmatically.

### 6.1 The `MoveGroup` action interface (raw)

`move_group` exposes a `moveit_msgs/action/MoveGroup` action on `/move_action`. You build a `MotionPlanRequest` with a goal constraint (a `PositionConstraint` + `OrientationConstraint` for a pose goal, or `JointConstraint`s for a joint goal), send it, and read the `error_code` from the result. This is verbose but transparent — it's exactly what Exercise 3 and the mini-project use, because seeing the request you build makes the failure modes concrete.

### 6.2 `moveit_py` (the Python bindings)

`moveit_py` (`from moveit.planning import MoveItPy`) wraps the action and the planning-scene monitor in a friendlier Python API: you get a `PlanningComponent` per planning group, call `set_goal_state(pose_stamped_msg=...)`, then `plan()` and `execute()`. It's the ergonomic path for a Python-first stack and what the mini-project's service node uses internally. Under the hood it is still `move_group`, still OMPL, still the same error codes.

```python
# Sketch of the moveit_py plan-and-execute the mini-project wraps in a service.
# (Full, runnable version is in exercise-03 and the mini-project.)
from moveit.planning import MoveItPy

moveit = MoveItPy(node_name="pose_goal_driver")
arm = moveit.get_planning_component("ur_manipulator")

arm.set_start_state_to_current_state()
arm.set_goal_state(pose_stamped_msg=goal_pose, pose_link="tool0")

plan_result = arm.plan()
if plan_result:                          # truthy == a trajectory was found
    moveit.execute(plan_result.trajectory, controllers=[])
else:
    node.get_logger().error("planning failed — pose unreachable or in collision")
```

The honest `if plan_result:` check is the same discipline as the DLS solver's `converged` flag and Week 4's clean-shutdown promise: a node that commands an arm must handle the *failed-plan* path explicitly, every time, or it will eventually dispatch a half-baked trajectory into hardware. Exercise 3 makes you wire that error path on purpose.

---

## 7. Recap

You should now be able to:

- Explain why IK is hard — many solutions (up to 8 for a 6-DOF arm), sometimes none, and singular blow-ups — and why a solver's job is "find one valid config or honestly report none."
- Name the three IK families (analytic, numerical, IKFast), state each one's speed / generality / seed trade, and pick the right one for an arm and a latency budget.
- Implement damped-least-squares IK from scratch, explain why the `λ²I` term tames the pseudoinverse's blow-up near a singularity, and return an honest converged/failed flag.
- Map the MoveIt2 architecture: `move_group` orchestrates the kinematics plugin, OMPL, the smoother, time-parameterization, and the controller, over the URDF + SRDF + YAML inputs and against the planning scene.
- Read a `MoveItErrorCodes` value and let it route your debugging — `-7` to reachability, `-2` to the planning scene, `-4` to the controllers — instead of editing at random.
- Drive `move_group` from code two ways (the raw `MoveGroup` action and `moveit_py`) with the failed-plan path handled explicitly.

Next: the exercises put all of this on a real UR5e — you'll build the FK by hand, watch your DLS solver survive a singularity, and dispatch a pose goal from a topic into a live plan-and-execute. Continue to [the exercises](../exercises/README.md).

---

## References

- *Modern Robotics* (Lynch & Park), Ch. 6 (Inverse Kinematics) — free PDF: <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- Buss, *Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares methods* — free PDF: <https://mathweb.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf>
- *MoveIt2 concepts* (`move_group`, planning scene, kinematics): <https://moveit.picknik.ai/main/doc/concepts/concepts.html>
- *MoveIt2 tutorials* (Move Group interface, `moveit_py`): <https://moveit.picknik.ai/main/doc/tutorials/tutorials.html>
- *`moveit_msgs/MoveItErrorCodes.msg`* (the error taxonomy): <https://github.com/moveit/moveit_msgs/blob/ros2/msg/MoveItErrorCodes.msg>
- *TRAC-IK* (the KDL replacement): <https://traclabs.com/projects/trac-ik/>
- *IKFast tutorial* (compiled analytic IK): <https://moveit.picknik.ai/main/doc/examples/ikfast/ikfast_tutorial.html>
- *OMPL* (the planner library): <https://ompl.kavrakilab.org/>
