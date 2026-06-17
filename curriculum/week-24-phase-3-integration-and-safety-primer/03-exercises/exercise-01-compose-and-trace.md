# Exercise 1 — Compose Nav2 + MoveIt2 and Trace the Four Defects

**Type:** Guided (Markdown deliverable + a working composed launch). **Estimated time:** 90 minutes.

This is the most important 90 minutes of the week, and most of it is not writing new code — it is *composing* code you already have and writing down the seams so the defects surface at kickoff instead of mid-run. You will bring your Week-17 Nav2 base and your Week-23 MoveIt2 arm up in one launch graph, build the **integration interface table** from Lecture 1 §1.2, and deliberately reproduce and diagnose each of the four canonical integration defects on your own graph.

The deliverable is a working `bringup_base_arm.launch.py` plus a Markdown file `integration-trace.md`. A peer reviews the table against your running graph.

---

## Step 0 — Have both halves working separately first

Before you compose, confirm each half works alone (you built both in earlier weeks):

```bash
# Base half (Week 17):
ros2 launch <your_nav2_bringup> nav2.launch.py
ros2 action list | grep navigate_to_pose      # NavigateToPose present

# Arm half (Week 23), separate terminal:
ros2 launch <your_moveit2_bringup> moveit.launch.py
ros2 action list | grep move_action            # MoveGroup present
```

If either half is broken alone, fix that first — composition does not heal a broken component.

---

## Step 1 — Compose into one launch graph with namespaces

Write `bringup_base_arm.launch.py` that brings up both halves, the base under a `base` namespace and the arm under an `arm` namespace (Lecture 1 §1.4), with the shared globals (`/tf`, `/tf_static`, `/clock`, `/safety/estop`) un-namespaced.

```python
from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch_ros.actions import PushRosNamespace

def generate_launch_description():
    base = GroupAction([PushRosNamespace("base"),
                        IncludeLaunchDescription(nav2_bringup)])
    arm = GroupAction([PushRosNamespace("arm"),
                       IncludeLaunchDescription(moveit2_bringup)])
    # The static base_link -> arm_base transform MUST be broadcast here,
    # on /tf_static (StaticTransformBroadcaster), or the arm cannot find the base.
    return LaunchDescription([base, arm, static_arm_mount_tf])
```

```bash
ros2 launch <your_pkg> bringup_base_arm.launch.py
```

---

## Step 2 — Build the integration interface table

In `integration-trace.md`, build the table from Lecture 1 §1.2 — but filled in from your *actual* running graph, not from the lecture. For every seam, run `ros2 topic info <topic> -v` (or `ros2 action list -t`) and record the real values:

| Producer | Consumer | Topic | Type | Frame | Rate | QoS |
|---|---|---|---|---|---|---|

Cover at minimum: `/odometry/filtered`, `/scan`, `/base/cmd_vel`, `/arm/joint_states`, the arm `FollowJointTrajectory` action, `/tf_static` (the `base_link → arm_base` row), `navigate_to_pose`, and `/safety/estop`. Every QoS cell comes from real `ros2 topic info -v` output, not memory.

---

## Step 3 — Reproduce and diagnose each of the four defects

For each defect, break it on purpose, observe the symptom, diagnose it from the outside, then fix it. Record all four in `integration-trace.md` with: the break, the symptom, the diagnostic signal, and the fix.

**Defect 1 — Frame/timing mismatch.** Broadcast the `base_link → arm_base` transform on `/tf` (dynamic, `VOLATILE`) instead of `/tf_static`. Start `move_group` after it. Observe: `move_group` logs `Could not find a connection`. Confirm with `ros2 run tf2_ros tf2_echo base_link arm_base` (which may itself show it intermittently — the masking trap from Lecture 1 §1.8). Fix: `StaticTransformBroadcaster` on `/tf_static`.

**Defect 2 — Bring-up-order deadlock.** Order the arm's controller manager to start *after* `move_group`. Observe: `move_group` hangs on "waiting for joint states." Diagnose: `ros2 lifecycle get /move_group` (or the node's log) shows it never reaches ready; the joint-state source isn't up. Fix: reorder so the controller manager precedes `move_group`.

**Defect 3 — Joint-states/namespace collision.** Publish the base's wheel joints on the same `/joint_states` the arm's `move_group` reads (remove the namespace). Observe: `move_group` complains about unknown joints. Fix: namespace the arm's joint states to `/arm/joint_states` and point `move_group` at it.

**Defect 4 — Controller clash.** Start a stray `teleop_twist_keyboard` (or a second publisher) on `/base/cmd_vel`. Observe: the base jitters. Diagnose: `ros2 topic info /base/cmd_vel -v` shows two publishers. Fix: kill the stray, or `twist_mux` with the E-stop highest-priority.

---

## Step 4 — Confirm the composed graph is clean

```bash
ros2 topic info /base/cmd_vel -v     # exactly one publisher
ros2 run tf2_ros tf2_echo base_link arm_base   # static transform present and steady
ros2 action list | grep -E "navigate_to_pose|follow_joint_trajectory"
ros2 doctor                          # all checks pass
```

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `bringup_base_arm.launch.py` brings up both the base and the arm with one command, base under `base` namespace, arm under `arm` namespace, shared globals un-namespaced.
- [ ] `integration-trace.md` contains the integration interface table with at least eight seams, every QoS cell from real `ros2 topic info -v` output.
- [ ] All four defects are reproduced, with the symptom, the diagnostic signal, and the fix recorded for each.
- [ ] The `base_link → arm_base` transform is on `/tf_static` (latched), confirmed with `tf2_echo`.
- [ ] `/base/cmd_vel` has exactly one publisher and `ros2 doctor` is clean.
- [ ] Committed to your Week 24 repo.

---

## Stretch

- Convert the composed launch to a single lifecycle manager that orders both the base and the arm controllers (Lecture 1 §1.5), with the safety wrapper activated before the BT.
- Add a `twist_mux` so the E-stop's zero-velocity is the highest-priority `/cmd_vel` input, and a teleop is the lowest — the production pattern for the controller-clash defect.
- Visualize the top-level drive-reach-return tree (Lecture 1 §1.7) in Groot 2 and confirm the `ReactiveFallback` short-circuits when you publish `/safety/estop true`.

---

When the composed graph is clean and the table is honest, move to [Exercise 2 — The pre-flight check](./exercise-02-preflight-check.py).
