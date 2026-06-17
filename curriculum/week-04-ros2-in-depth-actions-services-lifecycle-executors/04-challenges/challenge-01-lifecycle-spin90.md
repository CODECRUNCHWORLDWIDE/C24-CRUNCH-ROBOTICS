# Challenge 1 — A Managed `Spin90` Lifecycle Node That Refuses Goals While Inactive

**Time estimate:** ~2 hours.

## The problem

Your Exercise 3 `Spin90` server is correct: closed-loop, preemptible, multi-threaded, stops the robot on every exit. But it has one safety defect that no amount of executor tuning fixes — **it is alive the instant its process starts.** The moment `rclpy.init()` runs and the constructor finishes, the action server accepts goals, whether or not the IMU has converged, whether or not a supervisor has said "go." On a real robot that means it can command a rotation while its heading estimate is garbage, and the base will lurch.

The fix is to make it a **managed lifecycle node**. It should boot into `unconfigured`, allocate resources on `configure` (moving to `inactive`), and only accept goals after `activate` (moving to `active`). While `inactive`, it must **refuse every goal**, and `deactivate` must stop the robot and return to refusing.

This is not a paper exercise. You will write an automated test that drives the node through its transitions and *asserts* that a goal sent while `inactive` is rejected, and that the same goal sent while `active` is accepted and runs. "It should refuse goals" is a claim; the test is the proof.

## What to build

A package layout:

```
crunch_motion/
  crunch_motion/
    spin90_lifecycle.py        # the LifecycleNode
  test/
    test_lifecycle_refusal.py  # the proof-of-rejection test
  setup.py                     # entry point: spin90_lifecycle
```

### Requirements

1. **`spin90_lifecycle.py`** subclasses `rclpy.lifecycle.LifecycleNode` and implements all five transition callbacks:
   - `on_configure` — create the lifecycle `cmd_vel` publisher (`create_lifecycle_publisher`), the IMU subscription (in a `ReentrantCallbackGroup`), and the action server (in a `MutuallyExclusiveCallbackGroup`, created here so it is *discoverable* while inactive). Return `TransitionCallbackReturn.SUCCESS`.
   - `on_activate` — set an `self._active = True` gate, call `super().on_activate(state)` to activate the lifecycle publisher.
   - `on_deactivate` — set `self._active = False`, publish a zero `Twist` to stop the robot, call `super().on_deactivate(state)`.
   - `on_cleanup` — destroy the publisher, subscription, and action server; null the handles; return to `unconfigured`.
   - `on_shutdown` — best-effort stop and clean teardown from any state.
2. **The goal callback gates on state.** `goal_callback` returns `GoalResponse.REJECT` whenever `self._active` is `False`, and only `ACCEPT`s while `active`. The control loop is your Exercise 3 loop, unchanged.
3. **Two layers of refusal.** Both the `self._active` gate (rejects the goal) *and* the lifecycle publisher (drops `cmd_vel` while inactive, as a hardware-level backstop). The challenge wants both, and the test checks the goal-rejection layer.
4. **Runs under a `MultiThreadedExecutor`** — the cancel-path concurrency from Exercise 3 must still work while `active`.
5. **An automated test** (`test/test_lifecycle_refusal.py`) that:
   - launches the node in a background thread/executor,
   - drives it to `inactive` (calls the `configure` transition via the `/spin90_lifecycle/change_state` service or the `rclpy.lifecycle` client),
   - sends a goal and **asserts it is rejected** (`goal_handle.accepted is False`),
   - drives it to `active`,
   - sends the same goal and **asserts it is accepted**,
   - cancels it and asserts a `CANCELED` result,
   - drives it to `inactive` again and asserts goals are rejected once more.

## Driving transitions

You can drive transitions from the CLI to develop interactively:

```bash
ros2 run crunch_motion spin90_lifecycle &
ros2 lifecycle get  /spin90_lifecycle            # unconfigured
ros2 lifecycle set  /spin90_lifecycle configure  # -> inactive
ros2 lifecycle get  /spin90_lifecycle            # inactive [2]

# Send a goal while INACTIVE -- it must be rejected:
ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 \
  "{target_relative_yaw: 1.5708}"
# Expect: "Goal was rejected by server" and a log line "rejecting goal: node is not ACTIVE"

ros2 lifecycle set  /spin90_lifecycle activate    # -> active

# Now the same goal is accepted and runs:
ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 \
  "{target_relative_yaw: 1.5708}" --feedback

ros2 lifecycle set  /spin90_lifecycle deactivate  # stops robot, refuses goals again
```

In the test, drive transitions programmatically with the `lifecycle_msgs/srv/ChangeState` service client against `/spin90_lifecycle/change_state`, using the `Transition` IDs from `lifecycle_msgs/msg/Transition` (`TRANSITION_CONFIGURE = 1`, `TRANSITION_ACTIVATE = 3`, `TRANSITION_DEACTIVATE = 4`, `TRANSITION_CLEANUP = 2`).

## Acceptance criteria

- [ ] `ros2 lifecycle get /spin90_lifecycle` reports `unconfigured` immediately after launch — the node does **not** auto-activate.
- [ ] After `configure`, `ros2 lifecycle get` reports `inactive` and the action `/spin90` is visible in `ros2 action list` (discoverable but dormant).
- [ ] A goal sent while `inactive` is **rejected** (the client sees `accepted == False`); the node logs a rejection reason.
- [ ] After `activate`, the same goal is **accepted** and the robot rotates; feedback streams.
- [ ] A cancel mid-rotation while `active` is honored within the Exercise 3 budget (the multi-threaded + callback-group fix still holds).
- [ ] `deactivate` publishes a zero `Twist` (robot stops) and returns to refusing goals.
- [ ] The automated test passes end-to-end: reject-inactive, accept-active, cancel, reject-inactive-again — four assertions, all green.
- [ ] No exit path commands the robot while `inactive`. Prove it: subscribe to `/cmd_vel` (e.g. `ros2 topic echo /cmd_vel`) while sending a goal in `inactive` and confirm **nothing** is published.

## Stretch

- Write a tiny **lifecycle manager** node (the Nav2 pattern): on startup it calls `change_state` to drive `spin90_lifecycle` from `unconfigured` → `inactive` → `active` in order, logging each transition. This is the supervisor pattern the mini-project and the Week 17 Nav2 stack are built on.
- Port the node to `rclcpp_lifecycle::LifecycleNode` in C++. The transition callbacks map one-to-one; the payoff is that the composition story (mini-project) is cleaner in C++.

## What "done" looks like

A reviewer clones your repo, builds, launches the node, sees `unconfigured`, sends a goal and watches it bounce, runs `ros2 lifecycle set ... activate`, sends the goal and watches the robot turn, cancels it, watches it stop, and then runs your test and sees it pass. If every one of those steps does what this spec says, you have built the foundation the capstone bring-up dispatches its primitives through. That is the muscle this challenge builds: a node that can say "not yet," and means it.
