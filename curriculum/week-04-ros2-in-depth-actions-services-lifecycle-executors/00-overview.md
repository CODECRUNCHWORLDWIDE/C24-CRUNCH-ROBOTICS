# Week 4 — ROS2 in Depth: Actions, Services, Lifecycle, Executors

Welcome to **C24 · Crunch Robotics**, Week 4. Week 1 made rotations a group instead of a bag of numbers. Week 2 made every transform a tree. Week 3 gave you a differential-drive robot that spawns in Gz Sim, takes `cmd_vel`, and publishes IMU and LiDAR. So far every node you have written has been a **publisher** or a **subscriber** — fire-and-forget streams of data over topics. That is the right tool for a 50 Hz IMU feed. It is the *wrong* tool for "turn ninety degrees and tell me when you're done, and let me cancel it if I change my mind." This week is about everything that is not a topic.

By Friday you should be able to: choose correctly between a topic, a service, an action, and a behavior tree for a given problem and defend the choice in a design review; write a `Spin90Degrees` action server in `rclpy` that closes the loop on IMU yaw, streams feedback, and honors a cancel request mid-rotation; run that server under a `MultiThreadedExecutor` with a dedicated `ReentrantCallbackGroup` so the cancel handler is not blocked behind the control loop; explain why the `cancel_callback` deadlocks under a single-threaded executor and what a callback group actually partitions; and convert an ordinary node into a managed **lifecycle node** with clean `configure` / `activate` / `deactivate` transitions so a supervisor can bring it up, take it down, and prove it refuses goals while inactive.

This is the most under-taught week in most ROS2 curricula, and it is the one that separates people who *use* ROS2 from people who can *architect* a robot in it. The first thing to internalize is the decision ladder, and it is worth saying out loud before any code: **use a topic until you can't; then use a service; then use an action; then use a behavior tree.** Each rung up the ladder buys you something — a reply, a result, progress feedback, cancellation, composability — at the cost of more machinery. The senior move is to climb exactly as far as the problem requires and not one rung further. A junior engineer reaches for an action because actions are exciting. A senior engineer reaches for a topic because topics are boring, and boring is what you want at three in the morning when the robot is wedged against a wall.

The second thing to internalize is that **a long-running operation that cannot be cancelled is a safety defect, not a feature gap.** Your `Spin90Degrees` server commands angular velocity. If the operator hits the stop button, the IMU goes silent, or the goal becomes invalid, that rotation *must* stop, and it must stop in bounded time. The ROS2 action protocol is built around this: goals can be cancelled, servers acknowledge or reject the cancel, and the result carries a status (`SUCCEEDED`, `CANCELED`, `ABORTED`) that a caller can branch on. Topics give you none of this. Wiring cancellation correctly is most of the work, and getting it wrong — a cancel that the server accepts but never acts on, a control loop that keeps publishing `cmd_vel` after the goal is dead — is the single most common bug we see in student action servers.

The third thing to internalize is that **executors and callback groups are the concurrency model of ROS2, and the defaults are wrong for any node that does two things at once.** A `SingleThreadedExecutor` runs every callback on one thread, one at a time, to completion. That is fine for a node that only subscribes to one topic. It is a deadlock waiting to happen for an action server whose execute callback runs a control loop *and* whose cancel callback needs to run *during* that loop. The fix is not "add threads everywhere" — that way lies data races. The fix is a `MultiThreadedExecutor` plus deliberate `CallbackGroup` assignment: a `MutuallyExclusiveCallbackGroup` for things that must not run concurrently with each other, a `ReentrantCallbackGroup` for things that must be allowed to interleave. Callback groups are how you say "the cancel handler is allowed to preempt the execute handler" without hand-rolling a thread pool. We will get this exactly right, with diagrams, because getting it wrong produces the worst kind of bug: one that works on your laptop and deadlocks on the robot.

The fourth thing to internalize is that **lifecycle nodes are how safety-critical robotics says "not yet."** An ordinary node is alive the moment its process starts: its publishers publish, its subscribers fire, its action server accepts goals — whether or not the hardware behind it is ready. A lifecycle node starts in `unconfigured`, moves to `inactive` when you call `configure` (allocate resources, but stay dormant), and only starts doing work when you call `activate`. While `inactive`, it refuses goals. This is the difference between a robot that boots cleanly under a supervisor's orchestration and a robot that starts commanding motors before its IMU has a valid bias estimate. Nav2 is built entirely out of lifecycle nodes for exactly this reason, and Week 17 will lean on the muscle you build this week. The capstone bring-up dispatches the motion primitives you write this week through their lifecycle interface; you are building the foundation now.

## Learning objectives

By the end of this week, you will be able to:

- **Choose** correctly among a topic, a service, an action, and a behavior tree for a given communication problem, and defend the choice with the decision-ladder criteria (does the caller need a reply? a result? progress? cancellation? composition?).
- **Write** a ROS2 service server and client in `rclpy`, and explain why a service callback that blocks for more than a few milliseconds is an anti-pattern that an action exists to replace.
- **Author** a custom action definition (`.action` file), build it with `rosidl`, and generate the `Goal` / `Result` / `Feedback` interfaces.
- **Implement** a `Spin90Degrees` action server that consumes IMU yaw, runs a closed-loop proportional controller on heading error, publishes `cmd_vel`, streams `Feedback`, and returns a `Result` with the correct terminal status.
- **Implement** preemption — a `cancel_callback` that accepts a cancel request, a control loop that checks `goal_handle.is_cancel_requested` every tick, stops the robot, and returns `CANCELED`.
- **Run** the server under a `MultiThreadedExecutor` with a dedicated `ReentrantCallbackGroup` for the cancellation path, and explain the deadlock that occurs without it.
- **Distinguish** `MutuallyExclusiveCallbackGroup` from `ReentrantCallbackGroup` and assign each correctly so that the cancel handler can run concurrently with the execute handler but two control loops never run at once.
- **Convert** an ordinary node into a `LifecycleNode` with `on_configure`, `on_activate`, `on_deactivate`, `on_cleanup`, and `on_shutdown` transitions, and prove it rejects goals while `inactive`.
- **Compose** multiple nodes into a single process with `rclcpp_components` / `ComposableNodeContainer` and explain the intra-process zero-copy benefit.
- **Diagnose** the three classic concurrency failures in a ROS2 node: the single-threaded cancel deadlock, the reentrant data race, and the lifecycle "commanded motors while inactive" defect.

## Prerequisites

This week assumes you have completed **Weeks 1–3** of C24, or have equivalent ROS2 fluency. Specifically:

- **Week 3 complete.** You have a differential-drive robot in Gz Sim that spawns cleanly, takes `geometry_msgs/Twist` on `/cmd_vel`, and publishes a `sensor_msgs/Imu` on `/imu` and a `sensor_msgs/LaserScan` on `/scan`. This week's `Spin90Degrees` server commands that exact robot.
- **A working `ros2` on your PATH.** ROS2 **Jazzy Jalisco** on **Ubuntu 24.04** is the target. `ros2 --version`, `ros2 topic list`, and `ros2 node list` should all work, and you should have built at least one `colcon` workspace.
- **`rclpy` publisher/subscriber fluency from Week 1.** You can write a node class, create a publisher and a timer, spin it, and read its output. This week we move past pub/sub; you should not be surprised by the node-and-spin skeleton.
- **Comfortable reading both Python and C++.** The lectures and exercises are `rclpy`-first because Python iterates faster, but the lifecycle and composition material shows the `rclcpp` form too, because in 2026 the production lifecycle and component code is overwhelmingly C++. You do not need to *write* C++ fluently this week; you do need to *read* it.
- **A terminal with three panes.** You will run a server, a client, and `ros2 action`/`ros2 lifecycle` introspection commands simultaneously. `tmux` or three terminal tabs; either is fine.

You do **not** need any prior experience with actions, services, executors, or lifecycle. We start at the decision ladder and build up. If you have used `actionlib` from ROS1, you will need to unlearn a couple of habits (the ROS2 action protocol is goal-handle-centric, not callback-soup-centric); we flag them as we go.

## Topics covered

- **The decision ladder.** Topic → service → action → behavior tree. The five questions that move you up a rung: reply, result, feedback, cancellation, composition. Why "use a topic until you can't" is the senior default.
- **Services.** `rclpy` service server and client; `srv` definitions; synchronous vs. asynchronous service calls; the "never block in a service callback" rule and why an action exists.
- **Actions — the protocol.** The five interfaces under the hood: `send_goal`, `goal_response`, `feedback`, `get_result`, `cancel_goal`. The goal handle. The three terminal statuses (`SUCCEEDED`, `CANCELED`, `ABORTED`). Why ROS2 actions are built on services + topics under the hood.
- **Action definitions.** The `.action` file format (Goal `---` Result `---` Feedback), building with `rosidl`, the generated Python and C++ types.
- **Closed-loop control inside an action.** Consuming IMU yaw, computing heading error across the ±π wrap, a proportional controller on angular velocity, publishing `cmd_vel`, the tick rate, and the termination tolerance.
- **Preemption and cancellation.** The `cancel_callback`, `goal_handle.is_cancel_requested`, `goal_handle.canceled()`, stopping the robot, returning the right terminal status, and the "always stop the motors on the way out" discipline (`try/finally`).
- **Executors.** `SingleThreadedExecutor` vs. `MultiThreadedExecutor`; what "spin" actually does; the relationship between executors, threads, and callbacks.
- **Callback groups.** `MutuallyExclusiveCallbackGroup` vs. `ReentrantCallbackGroup`; what a group partitions; the canonical "execute in one group, cancel + subscriptions in a reentrant group" pattern; the deadlock without it.
- **Lifecycle nodes.** The managed-node state machine (`unconfigured` → `inactive` → `active` → `finalized`); the transition callbacks (`on_configure`, `on_activate`, `on_deactivate`, `on_cleanup`, `on_shutdown`); lifecycle publishers; why Nav2 is built this way; proving a node refuses work while inactive.
- **Composition.** `rclcpp_components`, `ComposableNodeContainer`, intra-process communication, the zero-copy benefit, and when composition matters (and when it is premature optimization).

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract. The action-server work is best done in long uninterrupted blocks — you need the server, a Gz Sim instance, and the introspection tools all live at once, and context-switching out of that mid-debug is expensive.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The decision ladder; services; the "don't block" rule       |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | Actions: protocol, `.action` files, the Spin90 server       |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Preemption; executors; callback groups; the cancel deadlock |    1.5h  |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Lifecycle nodes; composition; challenge #1                  |    0.5h  |    0h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Mini-project — motion primitives package bring-up           |    0h    |    0h     |     0h     |    0.5h   |   1h     |     3h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work; lifecycle + composition integration |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, polish                                        |    0h    |    0h     |     0h     |    1h     |   0h     |     2h       |    0h      |     3h      |
| **Total** |                                                             | **6h**   | **8h**    | **3h**     | **3.5h**  | **5h**   | **15h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The ROS2 Jazzy docs that matter, the design articles, the talks, and the source to read |
| [lecture-notes/01-the-decision-ladder.md](./02-lecture-notes/01-the-decision-ladder.md) | Topic → service → action → behavior tree. When each is right, services in depth, and the "don't block in a callback" rule that forces you up the ladder |
| [lecture-notes/02-lifecycle-executors-callback-groups.md](./02-lecture-notes/02-lifecycle-executors-callback-groups.md) | Executors, callback groups, the cancel deadlock and its fix, lifecycle nodes, composition, and why managed nodes matter for safety |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-decision-ladder-and-service.md](./03-exercises/exercise-01-decision-ladder-and-service.md) | Guided: classify ten problems on the ladder, then write a `ResetOdometry` service server + client |
| [exercises/exercise-02-spin90-action-server.py](./03-exercises/exercise-02-spin90-action-server.py) | Runnable: a `Spin90Degrees` action server with closed-loop IMU yaw and preemption |
| [exercises/exercise-03-multithreaded-executor.py](./03-exercises/exercise-03-multithreaded-executor.py) | Runnable: run the server under a `MultiThreadedExecutor` with a reentrant callback group for the cancel path |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-lifecycle-spin90.md](./04-challenges/challenge-01-lifecycle-spin90.md) | Convert `Spin90Degrees` into a managed lifecycle node that refuses goals while inactive |
| [quiz.md](./05-quiz.md) | 12 multiple-choice questions with an answer key |
| [homework.md](./06-homework.md) | Six practice problems with deliverables and a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the "motion primitives" action package — `RotateByAngle` + `DriveStraightDistance`, preemptible, lifecycle-managed, composed into one process |

## The "clean shutdown" promise

C24 has a recurring marker for every node that commands the robot. A server that finishes — whether it succeeded, was cancelled, or aborted — must always leave the robot stopped:

```
[spin90_action_server] goal reached: yaw_error=0.41° (tol=1.00°) — publishing zero Twist, terminating SUCCEEDED
```

If your server can exit any path — return, exception, cancel — without publishing a zero `Twist`, you are not done. We treat "robot keeps moving after the goal is dead" as a safety defect, the same way Week 7 of C9 treats a compiler warning as a bug. The point of Week 4 is to make that zero-Twist-on-every-exit line ordinary. Every action server you write this week wraps its control loop in `try / finally` and stops the motors in the `finally`.

## A note on what's not here

Week 4 goes deep on the ROS2 communication and process model. It does **not** cover:

- **QoS policies in depth.** Reliability, durability, history, deadline, liveliness — and the silent failures that come from mismatches — are **Week 5**. This week we use the sensible defaults and note where QoS will matter later. The one place it bites you this week (action feedback and the IMU subscription) we flag inline.
- **Behavior trees as an implementation.** We teach the decision ladder's top rung — *when* you reach for a behavior tree — but the BT.CPP authoring, control/decorator/condition nodes, and Groot 2 are **Week 19**. This week the behavior tree is a concept on the ladder, not a deliverable.
- **Nav2's lifecycle manager.** We explain *why* Nav2 is built on lifecycle nodes; we do not bring up the Nav2 stack. That is **Week 17**, and it assumes the lifecycle muscle you build here.
- **`micro-ROS` and real-time executors.** The `rclc` executor, the static memory model, and the deadline-aware scheduling that matters on an MCU are a C7-bridge topic, mentioned in resources and left for an elective.

The point of Week 4 is a sharp, narrow skill: pick the right rung of the ladder, write a cancellable closed-loop action server, run it under the right executor with the right callback groups, and wrap it in a lifecycle so a supervisor can bring it up and down safely. Everything in Phase 3 (Nav2, behavior trees, the safety stance) is downstream of getting this right.

## Stretch goals

If you finish the regular work early and want to push further:

- Read the **ROS2 design article on actions** end-to-end: <https://design.ros2.org/articles/actions.html>. It explains *why* the protocol is shaped the way it is — goal IDs, the result cache, the separation of feedback from result.
- Read the **`rclcpp` executors design article**: <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html>. Then skim the `rclcpp` `MultiThreadedExecutor` source and trace how callbacks are dispatched to threads.
- Convert your **exercise-02 `rclpy` server to `rclcpp`**. The action server template in C++ is more verbose but the lifecycle and composition story is cleaner; doing it once teaches you why production robotics is C++-heavy.
- Add a **`ros2 lifecycle` orchestration launch file** that brings your lifecycle node from `unconfigured` to `active` automatically using the `Nav2`-style lifecycle manager pattern (a node that calls `change_state` services in order).
- Read the **Open Navigation blog** post on lifecycle management in Nav2 and write a one-paragraph note on why the planner, controller, and behavior servers are all lifecycle-managed: <https://navigation.ros.org/concepts/index.html>.

## Up next

Continue to **Week 5 — QoS, DDS, and Message Design** once you have pushed the mini-project's motion-primitives package. Week 5 takes the communication model you built this week and asks the question every ROS2 engineer eventually gets burned by: *why did my action feedback silently stop arriving, and why did my map topic never latch?* The answer is QoS, and the defaults are wrong for half your topics. The action-server discipline you build this week — feedback streams, the IMU subscription, the `cmd_vel` publisher — are exactly the topics whose QoS you will tune next week. Get the structure right this week; make it robust next week.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
