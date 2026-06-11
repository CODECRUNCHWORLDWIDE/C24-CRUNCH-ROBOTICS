# Lecture 2 — Lifecycle Nodes, Executors, and Callback Groups: Why Managed Nodes Matter for Safety

> **Reading time:** ~80 minutes. **Hands-on time:** ~70 minutes (you reproduce the cancel deadlock, fix it with a callback group, and convert a node to a lifecycle node).

Lecture 1 got you up the decision ladder: you can pick a topic, a service, or an action, and you have an action-server skeleton in your hands. This lecture is about the two things that make that skeleton *safe* on a real robot: the concurrency model (executors and callback groups) and the lifecycle model (managed nodes). These are the two topics that separate "my action server works on my laptop" from "my action server does not deadlock on the robot at three in the morning, and it refuses to command motors before the IMU is ready."

We are going to do this in the order the bugs appear. First we build a `Spin90Degrees` action server the obvious way, run it under the default single-threaded executor, send a cancel, and watch it deadlock. Then we will understand *exactly* why, fix it with a callback group, and only then talk about lifecycle. The deadlock is not a corner case — it is the single most common bug in student (and plenty of professional) action servers, and the fix is three lines once you understand the model.

## 2.1 — What `spin` actually does

You have typed `rclpy.spin(node)` a dozen times by now. Here is what it actually means.

A ROS2 node does not run your callbacks itself. A node is a bag of *entities* that can become ready: subscriptions (a message arrived), timers (the period elapsed), service servers (a request arrived), action servers (a goal, cancel, or result request arrived), and guard conditions. An **executor** is the thing that watches those entities, notices when one is ready, and invokes the associated callback. `rclpy.spin(node)` is sugar for: create a `SingleThreadedExecutor`, add the node to it, and call `executor.spin()` forever.

```python
# What rclpy.spin(node) is, unrolled:
from rclpy.executors import SingleThreadedExecutor

executor = SingleThreadedExecutor()
executor.add_node(node)
try:
    executor.spin()          # loop: wait for a ready entity, run its callback, repeat
finally:
    executor.shutdown()
```

The loop inside `spin()` is, conceptually:

```
while rclpy.ok():
    wait_set = collect all ready entities (this is a DDS wait, with a timeout)
    for entity in wait_set:
        callback = entity.callback
        callback(...)          # runs TO COMPLETION before the loop continues
```

The load-bearing phrase is **to completion**. A `SingleThreadedExecutor` runs one callback at a time, on one thread, start to finish, before it even *looks* at the next ready entity. This is wonderful for reasoning: there are no data races inside a single-threaded executor, because two callbacks never run at once. It is a disaster for an action server, and here is why.

## 2.2 — The cancel deadlock, reproduced

Here is the obvious `Spin90Degrees` server. It is wrong, but it is wrong in an instructive way. Read the `execute_callback` carefully.

```python
import math
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu
from crunch_motion_interfaces.action import Spin90  # built from a .action file

def yaw_from_quaternion(q) -> float:
    # ZYX yaw extraction; safe for the small-roll/pitch case of a ground robot
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

def shortest_angular_distance(a: float, b: float) -> float:
    d = b - a
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return d

class Spin90ServerNaive(Node):
    def __init__(self):
        super().__init__("spin90_naive")
        self._yaw = None
        self.create_subscription(Imu, "/imu", self._on_imu, 10)
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._server = ActionServer(
            self,
            Spin90,
            "spin90",
            execute_callback=self._execute,
            cancel_callback=self._on_cancel,
        )

    def _on_imu(self, msg: Imu):
        self._yaw = yaw_from_quaternion(msg.orientation)

    def _on_cancel(self, goal_handle):
        self.get_logger().info("cancel requested")
        return CancelResponse.ACCEPT

    def _execute(self, goal_handle):
        # closed-loop rotate-by-90deg
        rate = self.create_rate(50.0)              # 50 Hz control loop
        while self._yaw is None:
            rate.sleep()                            # wait for first IMU sample
        target = self._yaw + math.radians(90.0)
        twist = Twist()
        try:
            while rclpy.ok():
                err = shortest_angular_distance(self._yaw, target)
                if abs(err) < math.radians(1.0):
                    break
                if goal_handle.is_cancel_requested:  # <-- we DO check this
                    goal_handle.canceled()
                    return Spin90.Result(final_error_deg=math.degrees(abs(err)))
                twist.angular.z = max(-1.0, min(1.0, 1.5 * err))
                self._cmd_pub.publish(twist)
                rate.sleep()
            goal_handle.succeed()
            return Spin90.Result(final_error_deg=math.degrees(abs(err)))
        finally:
            self._cmd_pub.publish(Twist())          # always stop
```

This looks complete. It has a control loop, it checks `is_cancel_requested`, it stops the robot in a `finally`. Run it under `rclpy.spin(node)` (a single-threaded executor) and it will rotate the robot beautifully. Now, mid-rotation, send a cancel:

```bash
ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 "{}" --feedback &
# ... while it is turning ...
ros2 action cancel /spin90   # (or Ctrl-C the send_goal, which sends a cancel)
```

It hangs. The robot keeps turning. The cancel never takes effect. The `_on_cancel` log line never prints. Why?

**Because the single-threaded executor is busy running `_execute`, and it runs callbacks to completion.** The cancel request arrives as a *separate entity* on the action server. For the executor to notice it and run `_on_cancel`, it has to return to the top of its loop — but it cannot, because it is *inside* `_execute`, which is spinning its own 50 Hz loop and will not return until the goal is reached. `_execute` checks `goal_handle.is_cancel_requested`, but that flag is only ever set by `_on_cancel`, and `_on_cancel` can only run when the executor is free, and the executor is not free, because it is running `_execute`. Classic deadlock: A waits for B, B cannot run because A holds the only thread.

There are two independent problems here, and you must fix both:

1. **`create_rate(...).sleep()` on a single-threaded executor does not pump callbacks.** `rate.sleep()` blocks the one thread. Even the IMU subscription stops firing, so `self._yaw` goes stale — the loop is steering on an old heading. (On a single-threaded executor, the very first `rate.sleep()` while waiting for the first IMU sample will hang forever, because the IMU callback can never run to populate `self._yaw`.)
2. **The cancel callback cannot run** while `_execute` holds the thread, so `is_cancel_requested` never flips.

Both are the same root cause: one thread, callbacks to completion, a long-running callback. The fix is a multi-threaded executor plus deliberate callback-group assignment.

## 2.3 — The `MultiThreadedExecutor`

A `MultiThreadedExecutor` runs callbacks on a pool of threads (by default, one per CPU core; configurable via `num_threads`). When two entities are ready at the same time, it can dispatch them to two threads and run them *concurrently*. That sounds like it solves everything — and naively swapping `rclpy.spin(node)` for a multi-threaded executor does make the cancel deadlock *sometimes* go away. But "sometimes" is the worst possible behavior, and the reason is **callback groups**.

By default, every callback in a node belongs to a single, implicit `MutuallyExclusiveCallbackGroup`. A mutually-exclusive group guarantees that **no two callbacks in that group run at the same time**, *even under a multi-threaded executor*. So if `_execute`, `_on_cancel`, and `_on_imu` are all in the same (default) group, the multi-threaded executor still will not run `_on_cancel` while `_execute` is running — because they are mutually exclusive. You have more threads, but the group serializes them anyway. The deadlock persists.

This is the single most important sentence in this lecture: **a multi-threaded executor only buys you concurrency between callbacks in *different* callback groups, or within a *reentrant* group.** Threads are necessary but not sufficient. You also have to tell ROS2 *which* callbacks are allowed to run concurrently, and that is what callback groups are for.

## 2.4 — The two callback groups

ROS2 gives you exactly two callback-group types, and they mean precisely this:

- **`MutuallyExclusiveCallbackGroup`** — callbacks in this group never run concurrently with each other. One at a time, within the group. (Different groups can still run concurrently.) This is the default for everything, and it is the right default: it means you do not have to think about data races between two callbacks that share a group.
- **`ReentrantCallbackGroup`** — callbacks in this group may run concurrently with each other *and* with themselves (the same callback can be running on two threads at once). This is the "let it interleave" group. It buys you concurrency at the price of needing to think about thread safety inside those callbacks.

Now the fix is mechanical. We want:

- The **execute** callback (the long control loop) in its own `MutuallyExclusiveCallbackGroup` — there should only ever be one rotation happening, so a single execute at a time is correct.
- The **cancel** callback and the **IMU subscription** in a `ReentrantCallbackGroup` — they must be allowed to run *while* execute is running. The cancel must be able to interrupt; the IMU must keep updating `self._yaw` so the loop steers on fresh data.

```python
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

class Spin90Server(Node):
    def __init__(self):
        super().__init__("spin90")
        self._yaw = None

        # Two groups, deliberately assigned.
        self._exec_group = MutuallyExclusiveCallbackGroup()   # the control loop
        self._reentrant = ReentrantCallbackGroup()            # cancel + IMU

        self.create_subscription(
            Imu, "/imu", self._on_imu, 10,
            callback_group=self._reentrant,                   # keeps firing during execute
        )
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self._server = ActionServer(
            self, Spin90, "spin90",
            execute_callback=self._execute,
            cancel_callback=self._on_cancel,
            callback_group=self._exec_group,                  # execute runs here
        )
```

And spin it under a multi-threaded executor:

```python
from rclpy.executors import MultiThreadedExecutor

def main():
    rclpy.init()
    node = Spin90Server()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        node.destroy_node()
        rclpy.shutdown()
```

Now trace what happens on a cancel. `_execute` is running on thread 1, inside its 50 Hz loop. The IMU subscription fires on thread 2 (reentrant group, allowed to run concurrently), keeping `self._yaw` fresh. A cancel request arrives; the executor dispatches `_on_cancel` to thread 3 (reentrant group, concurrent with execute). `_on_cancel` returns `CancelResponse.ACCEPT`, which sets the goal handle's cancel flag. Back on thread 1, the next `is_cancel_requested` check sees `True`, the loop breaks, the `finally` publishes a zero `Twist`, and `_execute` returns `CANCELED`. No deadlock. The robot stops in under one control tick.

### The `rate.sleep()` trap, fixed

One more thing. `self.create_rate(50.0).sleep()` still blocks a thread, and on a multi-threaded executor that is *usually* fine because other threads keep running — but it ties up a worker thread doing nothing. The more robust pattern for the control loop's pacing is to compute the loop period and use the node clock, or to drive the control loop from a timer in the reentrant group. For this week, `create_rate` under a multi-threaded executor with the IMU in a reentrant group is acceptable and is what the exercise uses; just know that on a busy node you would prefer a timer-driven loop. We flag this again in the mini-project, where the loop pacing matters for two primitives sharing a process.

## 2.5 — The reentrant data race (the bug the fix can introduce)

Callback groups are a trade. By putting the IMU subscription in a reentrant group so it can run concurrently with execute, you have created a shared-state hazard: `_on_imu` writes `self._yaw` on one thread while `_execute` reads it on another. In Python, the GIL makes a single attribute assignment effectively atomic, so reading and writing one float is safe-ish here. But the moment your shared state is a *compound* value — say, a `(yaw, timestamp, valid)` tuple you want to read consistently — you have a genuine race: the reader can see a half-updated value.

The discipline: **anything shared across callback groups that is read or written as a unit must be protected.** Use a `threading.Lock` around compound reads/writes, or design the shared state so a single atomic write swaps it (e.g., write a new immutable tuple and rebind the attribute). This is the cost of reentrancy, and it is why the default group is mutually exclusive — ROS2 makes you opt *into* the hazard. Do not put everything in a reentrant group "to be safe"; that is exactly backwards.

```python
import threading

class Spin90Server(Node):
    def __init__(self):
        super().__init__("spin90")
        self._state_lock = threading.Lock()
        self._yaw = None
        self._yaw_stamp = None
        # ... groups, sub, pub, server as above ...

    def _on_imu(self, msg):
        y = yaw_from_quaternion(msg.orientation)
        with self._state_lock:
            self._yaw = y
            self._yaw_stamp = self.get_clock().now()

    def _read_yaw(self):
        with self._state_lock:
            return self._yaw, self._yaw_stamp
```

## 2.6 — The three concurrency failures, named

You now have the vocabulary for the three classic ROS2 concurrency bugs. Memorize the names; you will diagnose all three this week.

1. **The single-threaded cancel deadlock.** A long-running callback (execute) holds the only thread; the cancel callback can never run; the cancel flag never flips. *Fix:* multi-threaded executor + reentrant group for the cancel path.
2. **The reentrant data race.** Shared compound state read on one thread while written on another, because both callbacks are reentrant or in different groups. *Fix:* a lock, or an atomic swap of immutable state.
3. **The "commanded motors while inactive" defect.** A node starts publishing `cmd_vel` or accepting goals before the hardware/estimator behind it is ready, because an ordinary node is *alive the instant its process starts*. *Fix:* lifecycle nodes — the subject of the rest of this lecture.

## 2.7 — Lifecycle nodes: the managed-node state machine

An ordinary `Node` has no notion of "ready." The moment `rclpy.init()` and the constructor run, its publishers publish, its subscriptions fire, its action server accepts goals. For a node that commands motors, that is a safety problem. Consider the bring-up sequence of a real robot: the IMU driver needs ~2 seconds to converge a bias estimate, the wheel encoders need a zero, the costmap needs the map. If the `Spin90` server accepts a goal during those two seconds, it will steer on a garbage heading and the robot will lurch. You want the server to exist, be discoverable, be configurable — but **refuse to do work** until a supervisor says "go."

That is a **lifecycle node** (also called a *managed node*). It is a node with an explicit, supervised state machine baked in. The primary states:

```
   ┌──────────────┐  configure   ┌────────────┐   activate   ┌──────────┐
   │ UNCONFIGURED │ ───────────▶ │  INACTIVE  │ ───────────▶ │  ACTIVE  │
   │              │ ◀─────────── │            │ ◀─────────── │          │
   └──────────────┘   cleanup    └────────────┘  deactivate  └──────────┘
          │                            │                          │
          │ shutdown                   │ shutdown                 │ shutdown
          ▼                            ▼                          ▼
                          ┌────────────────────────┐
                          │       FINALIZED        │
                          └────────────────────────┘
```

- **`unconfigured`** — the process is up; the node exists; nothing is allocated. No publishers, no work.
- **`inactive`** — `configure` has run: resources are allocated (publishers created, subscriptions created, the action server *created but not accepting goals*), but the node is dormant. It does not process data and does not command anything. This is the "ready but holding" state.
- **`active`** — `activate` has run: the node is doing its job. Publishers publish, the action server accepts goals.
- **`finalized`** — terminal; the node is being destroyed.

The transitions are driven by *external* calls — a supervisor, or you via the `ros2 lifecycle` CLI. The node does not transition itself; that is the whole point. A supervisor (Nav2's `lifecycle_manager`, or your own) brings a fleet of nodes from `unconfigured` to `active` *in a deliberate order*, and can take them back down cleanly.

You implement the transitions as callbacks. In `rclpy`:

```python
import rclpy
from rclpy.lifecycle import LifecycleNode, State, TransitionCallbackReturn
from rclpy.lifecycle import LifecyclePublisher
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu

class Spin90Lifecycle(LifecycleNode):
    def __init__(self):
        super().__init__("spin90_lifecycle")
        self._cmd_pub = None
        self._imu_sub = None
        self._server = None
        self._active = False

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        # Allocate resources. Create publishers/subscriptions/server, but the
        # lifecycle publisher will not actually publish until activated, and we
        # gate goal acceptance on self._active.
        self.get_logger().info("on_configure: allocating resources")
        self._cmd_pub = self.create_lifecycle_publisher(Twist, "/cmd_vel", 10)
        self._imu_sub = self.create_subscription(Imu, "/imu", self._on_imu, 10)
        # create the action server here (so it is discoverable while inactive)
        # ... action server construction ...
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("on_activate: now accepting goals")
        self._active = True
        return super().on_activate(state)   # activates lifecycle publishers

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("on_deactivate: refusing goals, stopping robot")
        self._active = False
        self._cmd_pub.publish(Twist())      # stop the robot on the way down
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("on_cleanup: freeing resources")
        self.destroy_publisher(self._cmd_pub)
        self.destroy_subscription(self._imu_sub)
        self._cmd_pub = None
        self._imu_sub = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info("on_shutdown")
        return TransitionCallbackReturn.SUCCESS

    def _on_imu(self, msg):
        # store yaw regardless of state; cheap and harmless
        ...
```

Two things make this *refuse goals while inactive*:

1. **The lifecycle publisher.** `create_lifecycle_publisher` returns a publisher that silently drops messages unless the node is `active`. So even if some code path tried to publish `cmd_vel` while inactive, nothing reaches the motors. This is a hardware-level safety net.
2. **The `self._active` gate in the goal callback.** Your action server's `goal_callback` checks `self._active` and returns `GoalResponse.REJECT` when the node is not active:

```python
def _on_goal(self, goal_request):
    if not self._active:
        self.get_logger().warn("rejecting goal: node is not ACTIVE")
        return GoalResponse.REJECT
    return GoalResponse.ACCEPT
```

Now you can prove the property the challenge asks for. Bring the node up to `inactive` only, send a goal, and watch it get rejected:

```bash
ros2 lifecycle set /spin90_lifecycle configure   # unconfigured -> inactive
ros2 lifecycle get  /spin90_lifecycle            # -> inactive [2]
ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 "{}"
# -> Goal was rejected by server   (because self._active is False)

ros2 lifecycle set /spin90_lifecycle activate    # inactive -> active
ros2 action send_goal /spin90 crunch_motion_interfaces/action/Spin90 "{}"
# -> Goal accepted, robot rotates
```

That is the entire safety argument in two CLI sessions: the node is alive and discoverable the whole time, but it *physically cannot* command the robot until a supervisor activates it.

## 2.8 — Why Nav2 is built this way

Nav2 is not a node; it is a graph of a dozen-plus lifecycle nodes (the planner server, the controller server, the behavior server, the smoother server, the costmaps, the BT navigator) supervised by a `lifecycle_manager`. When you launch Nav2, the manager brings them to `inactive` in dependency order (configure everything first), confirms each `configure` succeeded, then activates them in order. If any node's `on_configure` returns `FAILURE`, the manager *stops* — it does not bring a half-configured stack to `active`. This is exactly the property you want in a safety-critical system: **all-or-nothing, ordered bring-up, with a clean teardown path.** When you E-stop a Nav2 robot, the manager can `deactivate` the controller server, which stops the controller from publishing `cmd_vel`, in bounded time.

The reason this matters for *your* week-4 work: the capstone bring-up will dispatch your motion primitives (Week 4 mini-project) through their lifecycle interface, exactly the way the `lifecycle_manager` dispatches Nav2's servers. You are building a node that a supervisor can orchestrate. That is the difference between a script and a robot component.

A note on the C++ side, because in 2026 production lifecycle code is overwhelmingly `rclcpp`. The shape is identical: you inherit from `rclcpp_lifecycle::LifecycleNode`, override `on_configure`, `on_activate`, `on_deactivate`, `on_cleanup`, `on_shutdown`, each returning a `CallbackReturn`, and you use `rclcpp_lifecycle::LifecyclePublisher`. The `on_activate` override must call `LifecyclePublisher::on_activate()` to start publishing.

```cpp
#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "geometry_msgs/msg/twist.hpp"

using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

class Spin90Lifecycle : public rclcpp_lifecycle::LifecycleNode {
public:
  Spin90Lifecycle() : rclcpp_lifecycle::LifecycleNode("spin90_lifecycle") {}

  CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
    cmd_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
    RCLCPP_INFO(get_logger(), "on_configure: allocated cmd_vel publisher");
    return CallbackReturn::SUCCESS;
  }

  CallbackReturn on_activate(const rclcpp_lifecycle::State & s) override {
    LifecycleNode::on_activate(s);   // activates lifecycle publishers
    active_ = true;
    return CallbackReturn::SUCCESS;
  }

  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & s) override {
    active_ = false;
    cmd_pub_->publish(geometry_msgs::msg::Twist());   // stop on the way down
    LifecycleNode::on_deactivate(s);
    return CallbackReturn::SUCCESS;
  }

private:
  rclcpp_lifecycle::LifecyclePublisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  bool active_{false};
};
```

## 2.9 — Composition: many nodes, one process

The last topic is composition, and it is the cheapest win this week. By default each ROS2 node runs in its own process (`ros2 run pkg node`). Composition lets you load several nodes into a single process — a *component container* — so they share an executor and, critically, can use **intra-process communication**: when a publisher and subscriber are in the same process and intra-process comms is enabled, ROS2 passes the message by pointer instead of serializing it through DDS. For a node that publishes a 5 MB point cloud to a subscriber in the same process, that is the difference between a copy-and-serialize per message and a pointer hand-off. Zero-copy.

In `rclcpp`, you register a node as a component:

```cpp
#include "rclcpp_components/register_node_macro.hpp"
// ... your component class (a normal rclcpp::Node subclass) ...
RCLCPP_COMPONENTS_REGISTER_NODE(crunch_motion::RotateByAngleComponent)
```

and load it into a container at launch with a `ComposableNodeContainer`:

```python
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

container = ComposableNodeContainer(
    name="motion_primitives_container",
    namespace="",
    package="rclcpp_components",
    executable="component_container_mt",   # _mt = multi-threaded executor
    composable_node_descriptions=[
        ComposableNode(package="crunch_motion", plugin="crunch_motion::RotateByAngleComponent",
                       name="rotate_by_angle", extra_arguments=[{"use_intra_process_comms": True}]),
        ComposableNode(package="crunch_motion", plugin="crunch_motion::DriveStraightComponent",
                       name="drive_straight", extra_arguments=[{"use_intra_process_comms": True}]),
    ],
)
```

The mini-project composes your two motion primitives into one container exactly like this. Note `component_container_mt` — the multi-threaded container — because your primitives have action servers and you need the cancel-path concurrency from Section 2.4.

**When composition is premature optimization:** if your nodes do not exchange large messages, the zero-copy benefit is negligible and you have traded the ability to restart a single node independently for a marginal CPU win. The honest rule: compose nodes that exchange large messages or that must share a lifecycle/container for deployment reasons (Nav2 composes its servers). Do *not* compose a node graph just because you can — separate processes give you fault isolation, and on a robot, fault isolation is usually worth more than a copy.

## 2.10 — Summary and the muscle you built

You can now reason about the ROS2 concurrency and lifecycle model the way a robotics engineer must:

- `spin` runs callbacks; a single-threaded executor runs them one at a time, to completion — which deadlocks a long-running action server's cancel path.
- A multi-threaded executor is necessary but not sufficient; **callback groups** decide what runs concurrently. The canonical action pattern is *execute in a mutually-exclusive group, cancel + sensor subscriptions in a reentrant group*.
- Reentrancy introduces data races on shared compound state; protect it with a lock or an atomic swap.
- Lifecycle nodes make "not yet" expressible: a node can be alive and discoverable while `inactive`, refuse goals, and refuse to command motors (lifecycle publishers drop messages while inactive). This is how safety-critical robotics does ordered, all-or-nothing bring-up — and why Nav2 is built from managed nodes.
- Composition loads nodes into one process for intra-process zero-copy; use it for large-message graphs and shared deployment, not reflexively.

Take this into the exercises. Exercise 2 builds the correct `Spin90` server; Exercise 3 makes you reproduce the deadlock and fix it with callback groups; the challenge wraps the server in a lifecycle and makes you *prove* it refuses goals while inactive. The mini-project composes two lifecycle-managed, preemptible primitives into one container — which is exactly the shape the capstone bring-up expects.
