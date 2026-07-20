# Mini-Project — `crunch_arm`: MoveIt2 Bring-Up + a Pose-Goal Plan-and-Execute Service

> Bring a public 6-DOF arm (UR5e or MyCobot 280) up in MoveIt2 + Gz Sim, then wrap the plan-and-execute behind a clean ROS2 **service** so the rest of your stack can say "put the tool at this pose" and get back an honest success/failure with a named error code — never a hang, never a silent half-plan.

This is the artifact that turns "I dragged the RViz marker and it planned" into "my robot has an arm I can command from code, reliably, with the failure modes handled." After this week, sending the arm to a pose is a *service call* your behavior tree, your VLA policy, and your grasp planner will all make — so it has to be solid. You build it once, here, and every manipulation week after this depends on it.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This package is the arm half of your **Week 24 Phase 3 integration** (Nav2 + MoveIt2 in one launch graph, with the `/safety/estop` that cancels its trajectory). It is the motion layer the **Week 25 grasp planner** sends grasp poses to, and the **Week 26 learned-grasping** pipeline pipes Contact-GraspNet poses into. The capstone's arm is this service, hardened. Build it well now; you will call it for the rest of the track.

---

## What you will build

A `colcon` package `crunch_arm` with three deliverables:

1. **A MoveIt2 bring-up** (`launch/arm.launch.py`) that stands up the UR5e (or MyCobot) in Gz Sim with `move_group`, RViz, the controllers, and a tabletop in the planning scene — one launch file, clean every time.
2. **A pose-goal service** (`crunch_arm/pose_goal_server.py`) — a node exposing a `crunch_arm_interfaces/srv/PlanToPose` service: a client sends a `geometry_msgs/PoseStamped`, the server runs a MoveIt2 plan-and-execute, and returns `(success: bool, error_code: int, error_name: string, planning_time: float, waypoints: int)`. Honest failure handling for every `MoveItErrorCodes` value (Lecture 2 §5.5).
3. **A from-scratch FK/Jacobian library** (`crunch_arm/kinematics.py`) — the product-of-exponentials FK, the space Jacobian, and the manipulability measure from Lecture 1, with unit tests that verify the FK against MoveIt2's `/compute_fk` for 100 random joint vectors. This is the proof you understand what `move_group` does under the hood.

By the end you have a public repo of ~400–600 lines (Python + launch + config + tests) that any future `crunch_*` package can call to move the arm.

---

## Why a service, not just a script

Exercise 3 drove the arm from a *topic*. For the real stack you want a *service*, and the difference matters:

- **A service has a result.** "Did the arm reach the pose?" is a request/response question — the caller blocks until it knows, then branches on success. A topic is fire-and-forget; the caller never learns the outcome. A behavior tree leaf that says "reach this pose" *must* know whether it succeeded to decide what to tick next.
- **A service is composable.** The Week 24 behavior tree, the Week 25 grasp executor, and the Week 26 pipeline all become *clients* of this one service. One owner of the arm-motion logic; many callers. (This is the same single-source-of-truth instinct as Week 5's QoS module, applied to motion.)
- **A service forces the error taxonomy into the interface.** Returning `error_code` and `error_name` in the response means every caller sees *why* a motion failed and can route on it — `NO_IK_SOLUTION` → pick a different grasp; `CONTROL_FAILED` → check the controller. The failure mode is part of the contract, not buried in a log.

A long motion is technically an *action* (it has feedback and is cancellable), and the capstone version will be one. For this week a service is the right altitude: simpler, blocking, and it forces you to nail the result-handling before you add cancellation. (Week 24 adds the cancellation, when the E-stop must abort a trajectory in flight.)

---

## Package layout

```
crunch_arm/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_arm
├── crunch_arm/
│   ├── __init__.py
│   ├── kinematics.py          # PoE FK + space Jacobian + manipulability (Lecture 1)
│   ├── pose_goal_server.py    # the PlanToPose service node (Lecture 2 §6)
│   └── reachability.py        # optional: the reachability check the service uses pre-plan
├── launch/
│   └── arm.launch.py          # MoveIt2 + Gz Sim + RViz + tabletop bring-up
├── config/
│   └── tabletop_scene.yaml    # the collision object(s) added to the planning scene
└── test/
    ├── test_kinematics.py     # FK vs /compute_fk for 100 random joint vectors
    └── test_error_taxonomy.py # name_for() maps every code; unreachable -> negative code

crunch_arm_interfaces/
├── package.xml
├── CMakeLists.txt
└── srv/
    └── PlanToPose.srv
```

The `PlanToPose.srv` definition:

```
# Request
geometry_msgs/PoseStamped target
string planning_group        # e.g. "ur_manipulator"; defaults applied if empty
string ee_link               # e.g. "tool0"; defaults applied if empty
bool execute                 # true = plan AND execute; false = plan only (dry run)
---
# Response
bool success                 # error_code.val == 1
int32 error_code             # the raw MoveItErrorCodes value
string error_name            # the human name (SUCCESS, NO_IK_SOLUTION, ...)
float64 planning_time
int32 waypoints              # length of the planned joint trajectory
```

---

## Deliverable 1 — the MoveIt2 bring-up

A single `launch/arm.launch.py` that brings up:

- The arm's `robot_state_publisher` from the UR5e (or MyCobot) URDF.
- Gz Sim with the arm spawned (or, on a constrained laptop, the MoveIt2 `demo.launch.py` fake controller — document which you used).
- `move_group` with the `ur_moveit_config` SRDF, kinematics YAML, OMPL config, and controllers YAML.
- RViz with the MotionPlanning panel and a saved layout.
- A **tabletop collision object** added to the planning scene from `config/tabletop_scene.yaml`, so the arm plans *around* the table, not through it. (A missing table is the #1 reason a first MoveIt2 setup plans a trajectory that drives the gripper through the desk.)

Acceptance for this deliverable: `ros2 launch crunch_arm arm.launch.py` brings everything up clean, RViz shows the arm and the table, and dragging the marker + clicking Plan produces a path that avoids the table.

---

## Deliverable 2 — the `PlanToPose` service

The heart of the project. The server node:

1. Loads MoveIt2 (via `moveit_py`'s `MoveItPy`, or the raw `MoveGroup` action like Exercise 3 — your call; document it).
2. On each `PlanToPose` request, sets the start state to current, sets the goal to the requested `PoseStamped` on the requested `ee_link`, plans, and (if `execute`) executes.
3. **Pre-checks reachability** before planning: run your own IK/FK reachability check (Deliverable 3) and, if the pose is clearly outside the workspace, return `NO_IK_SOLUTION` *fast* instead of making OMPL spend its whole time budget failing. (This is the senior move: cheap local checks before expensive global ones.)
4. Maps the `MoveItErrorCodes` value to a name and fills the response. **Never** returns a bare boolean; the caller always learns *why*.
5. Handles the planning-failed, no-IK, control-failed, and start-in-collision cases explicitly, each with its own log line and the right response code.

The honest-failure discipline is the grade here. A service that returns `success: false` with no `error_name` is a service that turns one debugging session into ten. The response carries the diagnosis.

```python
# Sketch of the result-mapping core (full version in the repo).
def make_response(error_code_val: int, planning_time: float, n_waypoints: int):
    resp = PlanToPose.Response()
    resp.error_code = int(error_code_val)
    resp.error_name = ERROR_NAMES.get(error_code_val, f"UNKNOWN({error_code_val})")
    resp.success = (error_code_val == 1)
    resp.planning_time = float(planning_time)
    resp.waypoints = int(n_waypoints)
    return resp
```

---

## Deliverable 3 — the from-scratch kinematics library

`kinematics.py` is the proof you understand the stack you just wrapped. It implements, in pure NumPy (the Lecture 1 code):

- `exp_screw(S, theta)` — the closed-form matrix exponential of a screw.
- `fk_space(screws, M, thetas)` — product-of-exponentials FK.
- `space_jacobian(screws, thetas)` — the 6×n space Jacobian.
- `manipulability(J)` — the Yoshikawa measure.

And `reachability.py` uses them for the pre-plan check: a pose whose position is beyond the arm's max reach, or whose required configuration would sit below a manipulability threshold, is rejected before OMPL is ever called.

The clincher is the test: `test_kinematics.py` generates 100 random joint vectors within limits, runs `fk_space` *and* queries MoveIt2's `/compute_fk`, and asserts they agree to 1e-4 m and 1e-3 rad. If your FK disagrees with MoveIt2's, your screw table is wrong — and the test catches it, automatically, the way Exercise 1 caught it by hand.

---

## Rules

- **You may** use `ur_description`, `ur_moveit_config`, `moveit_py`, `moveit_msgs`, and the ROS2 Jazzy desktop install plus `pytest`/`numpy`.
- **You must not** skip the honest-failure handling: every non-success `MoveItErrorCodes` value must produce a named, logged response, not a bare `false`.
- **You must** verify your from-scratch FK against `/compute_fk` in a test — the kinematics library exists to prove understanding, not to be decorative.
- **You must** add the tabletop to the planning scene; "it planned through the table" is an automatic fail on Deliverable 1.
- Python 3.12 (Ubuntu 24.04 default), ROS2 Jazzy, MoveIt2.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-23-crunch-arm-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_arm crunch_arm_interfaces` succeeds with no warnings.
- [ ] `ros2 launch crunch_arm arm.launch.py` brings up the arm + `move_group` + RViz + the tabletop; drag-and-plan avoids the table.
- [ ] `ros2 service call /plan_to_pose crunch_arm_interfaces/srv/PlanToPose "{...reachable pose...}"` returns `success: true`, `error_name: 'SUCCESS'`, and the arm moves in Gz/RViz.
- [ ] The same call with an *unreachable* pose returns `success: false` and a negative `error_code` with the right `error_name` (`NO_IK_SOLUTION` or `PLANNING_FAILED`) — and the service does **not** hang or crash.
- [ ] `colcon test --packages-select crunch_arm` passes, including:
  - `test_kinematics.py`: `fk_space` agrees with `/compute_fk` (or a recorded reference set) for 100 random joint vectors to 1e-4 m.
  - `test_error_taxonomy.py`: `name_for()` covers every code in the response path.
- [ ] A `README.md` with the launch commands, the service interface, an example call, and a paragraph on why the arm is a service.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **MoveIt2 bring-up** | 20 | One clean launch; arm + `move_group` + RViz + tabletop; drag-and-plan avoids the table; no missing-controller or SRDF errors. |
| **Service correctness** | 25 | `PlanToPose` plans and executes a reachable pose; the arm physically reaches it; the response is fully populated. |
| **Honest failure handling** | 25 | Every non-success code returns a named, logged response; unreachable poses fail fast and cleanly; no hangs, no bare booleans, no crashes. |
| **From-scratch kinematics** | 20 | FK/Jacobian/manipulability implemented in NumPy; `test_kinematics.py` verifies FK against `/compute_fk` for 100 vectors; the reachability pre-check uses it. |
| **Docs & hygiene** | 10 | Clear README, sensible commits, no `build/`/`install/` checked in, the service interface documented. |

**90+** is portfolio-grade and ready to drop into Week 24's integration launch. **70–89** works but has a soft failure path or an unverified FK. **Below 70** means the arm isn't a reliable service yet — fix the failure handling first, because Week 24 will cancel this very trajectory mid-flight and a fragile service won't survive it.

---

## Stretch goals

- **Make it an action.** Promote `PlanToPose` from a service to an action with feedback (current waypoint) and cancellation — the shape Week 24 needs for the E-stop to abort a trajectory in flight. Wire a cancel that stops the arm cleanly.
- **Manipulability-aware goals.** When a pose is reachable with tolerance, have the service pick the *most manipulable* nearby configuration (the challenge's stretch) so executed motions are robust, not on the edge of a singularity.
- **Swap to TRAC-IK.** Change the kinematics plugin in the YAML and re-run a set of borderline poses; show in the README that TRAC-IK solves poses KDL gave up on, with the success-rate numbers.
- **CI job.** A GitHub Actions workflow that builds both packages, runs `colcon test`, and runs the FK-vs-reference test headless. Green check on every push.

---

## How this connects to the rest of C24

- **Week 24 (Phase 3 integration + safety)** puts this arm in the same launch graph as Nav2 and wires `/safety/estop` to cancel its trajectory inside 200 ms. Your service becomes an action so it can be cancelled.
- **Week 25 (grasping foundations)** sends the *best antipodal grasp pose* to this service and checks it's reachable with the reachability library you built here.
- **Week 26 (Contact-GraspNet)** pipes learned grasp poses into this same service — your honest error handling is what lets the pipeline pick a different grasp when one is unreachable.

When you've finished, push the repo and take the [quiz](../quiz.md).
