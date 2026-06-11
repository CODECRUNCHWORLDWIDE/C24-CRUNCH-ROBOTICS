# Lecture 2 — Bring-Up (Path A) and Hardening (Path B): Integration Day

> **Duration:** ~1 hour of reading + a full day of hands-on.
> **Outcome:** On Path A you can bring a real robot up from cold metal to a fully connected TF tree with every sensor and actuator confirmed reporting correctly, then drive a 20-meter trajectory. On Path B you can convert an ad-hoc launch graph into a lifecycle-managed, systemd-supervised deployment that cold-boots in under 60 seconds with a telemetry heartbeat.

If you only remember one thing from this lecture, remember this:

> **Integration day is not a debugging day — it is a verification day.** You do not bring the whole stack up and "see if it works." You bring it up *one layer at a time*, confirm that layer reports correctly before you trust the layer above it, and the first time you run the full stack should be boring. Surprise on integration day means you skipped a verification step.

This is the only lecture in C24 that forks completely. Read your path. Skim the other so you can speak to it in the Week 48 defense, but do your hands-on work on one path and commit to it for the rest of the course.

---

## Part A — Bringing the robot up on hardware

### A.1 The bring-up order is power, then safety, then signals, then motion

You bring a robot up bottom-up, and you never skip a layer:

1. **Power.** Battery charged, voltage under load measured, the compute and the motor bus on separate rails if your design allows. A sagging battery causes "random" sensor dropouts that you will misdiagnose for hours as software.
2. **Safety.** The physical E-stop works *before* anything can move. Press it, confirm the motor bus de-energizes, release it, confirm it re-energizes only on an explicit re-enable — not automatically. Your draft safety case from the earlier weeks specifies this; honor it. Nothing in the rest of this lecture happens until the E-stop is verified.
3. **Signals.** Every sensor publishes at its rated rate with sane values, and the TF tree is fully connected. No motion yet.
4. **Motion.** One actuator at a time, lowest authority first: a commanded velocity of 0.05 m/s with a hand on the E-stop, confirming the *sign* of motion matches the *sign* of the command and the *sign* of the reported odometry.

Resist the urge to launch everything and look at RViz. RViz showing nothing tells you almost nothing. The bring-up checklist tells you exactly which layer failed.

### A.2 Confirm every sensor reports correctly

For each sensor, three checks: it publishes, at the right rate, with sane values. The CLI does all three:

```bash
# 1. Is the topic alive at all?
ros2 topic list | grep -E 'scan|imu|odom|camera'

# 2. Is it at the rated rate? (A LiDAR rated 10 Hz that reports 3 Hz is a bus/USB problem.)
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic hz /odom

# 3. Are the values sane? Eyeball one message.
ros2 topic echo --once /imu/data
ros2 topic echo --once /scan --field ranges
```

Sane means: the IMU reports ~9.81 in the gravity axis when level and near-zero rates when still; the LiDAR's `ranges` are finite and in the right band (not all `inf`, not all the minimum); odometry starts at zero and increments in the direction you push the robot. The single most common bring-up bug is a **sign or frame error**: push the robot forward and odometry counts *down*, or the IMU's yaw increases when you turn *right* instead of left (NED-vs-ENU convention). Catch these now, with your hands on the robot, not later when the EKF is silently fusing garbage.

Script the whole check so it is repeatable and so you can run it again after every power cycle. Exercise 1 builds exactly this scripted health check; here is the shape of it:

```python
#!/usr/bin/env python3
"""bringup_check.py - confirm every sensor publishes at rate with sane values.

A bring-up gate: exits 0 only if all required sensors pass. Run it after every
power cycle. This is the kernel of Exercise 1; the exercise extends it with
actuator checks and a TF-tree assertion.
"""
import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry

# topic, type, min acceptable Hz over a 3-second window
REQUIRED = [
    ("/imu/data", Imu, 100.0),
    ("/scan", LaserScan, 8.0),
    ("/odom", Odometry, 20.0),
]


class BringupCheck(Node):
    def __init__(self):
        super().__init__("bringup_check")
        self.counts = {topic: 0 for topic, _, _ in REQUIRED}
        self.last_msg = {topic: None for topic, _, _ in REQUIRED}
        for topic, msg_type, _ in REQUIRED:
            self.create_subscription(
                msg_type, topic,
                lambda m, t=topic: self._on(t, m), 50)

    def _on(self, topic, msg):
        self.counts[topic] += 1
        self.last_msg[topic] = msg

    def report(self, window_s: float) -> bool:
        ok = True
        for topic, _, min_hz in REQUIRED:
            hz = self.counts[topic] / window_s
            status = "OK " if hz >= min_hz else "LOW"
            if hz < min_hz:
                ok = False
            self.get_logger().info(
                f"[{status}] {topic:14s} {hz:6.1f} Hz  (need >= {min_hz} Hz)")
        # Sanity: IMU gravity axis should read ~9.81 when level and still.
        imu = self.last_msg["/imu/data"]
        if imu is not None:
            g = imu.linear_acceleration.z
            if not (8.5 < abs(g) < 11.0):
                self.get_logger().error(
                    f"IMU gravity axis reads {g:.2f}; expected ~9.81 when level")
                ok = False
        return ok


def main():
    rclpy.init()
    node = BringupCheck()
    window = 3.0
    end = node.get_clock().now().nanoseconds * 1e-9 + window
    while rclpy.ok() and node.get_clock().now().nanoseconds * 1e-9 < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    ok = node.report(window)
    node.get_logger().info("BRING-UP: PASS" if ok else "BRING-UP: FAIL")
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

### A.3 The TF tree must be fully connected, with no future extrapolation

Your EKF, your costmap, and your planner all stand on TF. A broken TF tree produces the most confusing errors in ROS2 because they surface far from their cause. Two checks:

```bash
# Render the full tree to a PDF and look for disconnected islands.
ros2 run tf2_tools view_frames
# -> frames.pdf : every frame should trace back to one root (usually 'map' or 'odom')

# Watch a specific transform's availability and delay live.
ros2 run tf2_ros tf2_monitor odom base_link
```

The error you will see if you got Lecture 1's timestamp discipline wrong is `Lookup would require extrapolation into the future`. It means a consumer asked for a transform at time `t` but the most recent transform is stamped *before* `t` — your TF publishers are lagging, or `use_sim_time` is inconsistent across nodes, or a sensor is stamping with capture-time while a consumer uses arrival-time. Fix the stamps; do not paper over it by widening `transform_timeout` past 0.1 s, because that just hides the latency that is also corrupting your fusion.

### A.4 Confirm actuators, then drive

With signals verified, command the lowest-authority motion with a hand on the E-stop:

```bash
# Smallest possible forward nudge. Hand on the E-stop.
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/Twist '{linear: {x: 0.05}}'
```

Confirm three signs agree: commanded direction, physical direction, and reported `/odom` direction. Then the same for rotation. Then run the actuator-latency step test from Lecture 1 §3 to record `Td` and `τ`. Only now do you bring up the full autonomy stack and drive the 20-meter trajectory — which is Exercise 2 and the mini-project. The order is: signals pass, actuators pass, *then* the stack runs. The first full-stack run should feel anticlimactic. If it is dramatic, a verification step was skipped.

### A.5 The Path A integration-day checklist

Keep this physically printed next to the robot:

- [ ] Battery charged; voltage under load measured and logged.
- [ ] E-stop verified: de-energizes on press, re-enables only on explicit command.
- [ ] `use_sim_time:=false` confirmed across every node (`ros2 param get <node> use_sim_time`).
- [ ] Each sensor: alive, at rated rate, sane values (`bringup_check.py` exits 0).
- [ ] IMU axis convention confirmed (gravity sign, yaw direction on a hand-turn).
- [ ] Odometry sign confirmed by pushing the robot by hand.
- [ ] TF tree fully connected (`frames.pdf`), no future-extrapolation errors.
- [ ] `ros2 topic delay` on `/imu/data` and `/odom` under ~20 ms.
- [ ] Actuator step test recorded; `Td` and `τ` written down.
- [ ] EKF re-tuned against a replayed bag (Lecture 1 §5).
- [ ] 20-meter trajectory driven; rosbag recorded; terminal drift measured against tape.

---

## Part B — Hardening the sim deployment

If you do not have a robot, Path B is not a consolation prize. Fleet operators interview specifically for the skills it trains: deterministic cold boot, launch-graph health, lifecycle sequencing, and telemetry. The goal is to take a launch graph that "works when I run it by hand" and turn it into a service that systemd starts on boot, that comes up in a known order, that fails *loud* when a dependency is missing, and that reports its own health — and to prove it cold-boots in under 60 seconds.

### B.1 Why ad-hoc launch graphs fail to cold-boot

The launch file you have been using all year almost certainly starts every node at once and hopes. In an interactive session that is fine: you start it, you wait, you watch the logs, and if the LiDAR driver came up before its Ethernet link you just restart it. A cold boot has no human to restart anything. The failure modes that do not matter interactively and are fatal on boot:

- **Ordering races.** The EKF starts, finds no `/odom` yet, and either spins logging warnings or — worse — initializes from a bad first measurement. The driver was 800 ms behind because its USB device enumerated late.
- **Network-not-ready.** An Ethernet LiDAR or a DDS discovery that needs the network gets `network-online.target` *after* your nodes started, so discovery half-completes and topics are flaky.
- **Silent partial failure.** One node crashes on startup, the rest come up, and nothing tells the operator the graph is only 90% alive. It looks ready. It is not.
- **No readiness signal.** systemd thinks the service is "started" the instant the process forks, which is 50 seconds before the stack is actually ready to accept a goal. Your "cold boot time" is then meaningless because nobody defined "ready."

The fix for all four is **lifecycle nodes with explicit ordering and an explicit readiness gate**.

### B.2 Lifecycle nodes: configure, then activate

A ROS2 managed (lifecycle) node has a state machine: `unconfigured → inactive → active`, driven by `configure()` and `activate()` transitions. The value is that *configuration* (loading params, allocating, opening devices) is separated from *activation* (publishing, accepting work). A launch graph can therefore say "configure everyone, confirm all configured, then activate in dependency order." That is determinism.

Most production drivers (the cameras, Nav2's whole stack, `robot_localization`'s `ekf_node` in newer releases) are lifecycle-capable. For your own nodes, inherit from `LifecycleNode`:

```python
#!/usr/bin/env python3
"""A minimal lifecycle node for Path B: a 'goal gate' that only accepts goals
once every upstream dependency is active. This is the readiness gate that makes
'cold boot time' meaningful."""
import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, State
from std_msgs.msg import Bool


class GoalGate(LifecycleNode):
    def __init__(self):
        super().__init__("goal_gate")
        self._ready_pub = None
        self._timer = None

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        # Allocate publishers but do NOT publish yet.
        self._ready_pub = self.create_lifecycle_publisher(Bool, "/capstone/ready", 1)
        self.get_logger().info("configured: ready publisher allocated")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        # Now we are last in the activation order, so 'active' == 'ready'.
        self._timer = self.create_timer(0.5, self._tick)
        self.get_logger().info("activated: stack is ready to accept goals")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        if self._timer:
            self._timer.cancel()
        self.get_logger().info("deactivated: no longer accepting goals")
        return super().on_deactivate(state)

    def _tick(self):
        msg = Bool()
        msg.data = True
        self._ready_pub.publish(msg)


def main():
    rclpy.init()
    node = GoalGate()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
```

### B.3 Ordering the launch graph with event handlers

The launch file is where ordering becomes explicit. The pattern: start the drivers, and only *after* they emit their "configured" or "active" transition do you start the next layer. `RegisterEventHandler` with `OnStateTransition` (for lifecycle nodes) or `OnProcessStart` (for plain nodes) is the primitive.

```python
#!/usr/bin/env python3
"""bringup.launch.py - a hardened, ordered launch graph for Path B.

Order: drivers -> ekf -> nav/planner -> goal_gate. Each layer waits for the
previous to reach 'active' before it is configured+activated. The goal_gate is
last, so '/capstone/ready' going true is the single, well-defined moment the
cold boot is 'done'.
"""
from launch import LaunchDescription
from launch.actions import RegisterEventHandler, EmitEvent, LogInfo
from launch.event_handlers import OnStateTransition
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition as RosOnStateTransition
from lifecycle_msgs.msg import Transition
import launch


def lifecycle(pkg, exe, name):
    return LifecycleNode(package=pkg, executable=exe, name=name,
                         namespace="", output="screen")


def configure_then_activate(node, on_active_emit_for=None):
    """Return event handlers that drive node: inactive -> active, and when it
    reaches 'active', optionally kick the next node's configure."""
    handlers = []
    # When the node reports 'inactive' (configured), emit 'activate'.
    handlers.append(RegisterEventHandler(RosOnStateTransition(
        target_lifecycle_node=node, goal_state="inactive",
        entities=[
            LogInfo(msg=["configured -> activating"]),
            EmitEvent(event=ChangeState(
                lifecycle_node_matcher=launch.events.matches_action(node),
                transition_id=Transition.TRANSITION_ACTIVATE)),
        ])))
    if on_active_emit_for is not None:
        # When this node reaches 'active', configure the next layer.
        handlers.append(RegisterEventHandler(RosOnStateTransition(
            target_lifecycle_node=node, goal_state="active",
            entities=[
                LogInfo(msg=["active -> configuring next layer"]),
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=launch.events.matches_action(on_active_emit_for),
                    transition_id=Transition.TRANSITION_CONFIGURE)),
            ])))
    return handlers


def generate_launch_description():
    drivers = lifecycle("my_robot_bringup", "sensor_drivers", "drivers")
    ekf = lifecycle("robot_localization", "ekf_node", "ekf_filter_node")
    gate = lifecycle("my_robot_bringup", "goal_gate", "goal_gate")

    ld = LaunchDescription()
    for n in (drivers, ekf, gate):
        ld.add_action(n)

    # Kick the first configure.
    ld.add_action(EmitEvent(event=ChangeState(
        lifecycle_node_matcher=launch.events.matches_action(drivers),
        transition_id=Transition.TRANSITION_CONFIGURE)))

    # drivers active -> configure ekf ; ekf active -> configure gate.
    for h in configure_then_activate(drivers, on_active_emit_for=ekf):
        ld.add_action(h)
    for h in configure_then_activate(ekf, on_active_emit_for=gate):
        ld.add_action(h)
    for h in configure_then_activate(gate):
        ld.add_action(h)

    return ld
```

The chain is the point: drivers configure, activate, and only then does the EKF configure; the EKF activates and only then does the goal gate configure. When `/capstone/ready` goes true, every layer below it is provably active. That is your cold-boot finish line.

### B.4 systemd: starting on boot and signalling readiness

Now put the launch graph under systemd so it starts on power-on without a human, and — crucially — so the boot time is *measurable*. The trick is `Type=notify`: your service tells systemd the exact moment it is ready, rather than systemd guessing "ready == forked."

```ini
# /etc/systemd/system/capstone.service
[Unit]
Description=Capstone autonomy stack (Path B)
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
NotifyAccess=all
# A wrapper that sources the workspace, runs the launch, and calls
# systemd-notify READY=1 when /capstone/ready first goes true.
ExecStart=/opt/capstone/bin/capstone_boot.sh
Restart=on-failure
RestartSec=3
TimeoutStartSec=90
WatchdogSec=10

[Install]
WantedBy=multi-user.target
```

`After=network-online.target` fixes the network race from B.1. `Type=notify` plus a wrapper that calls `systemd-notify --ready` the instant `/capstone/ready` goes true means `systemctl start` *blocks until the stack is genuinely ready*, so `systemd-analyze` gives you an honest cold-boot number. The wrapper:

```bash
#!/usr/bin/env bash
# /opt/capstone/bin/capstone_boot.sh - launch the stack, signal READY when up.
set -euo pipefail
source /opt/ros/jazzy/setup.bash
source /opt/capstone/install/setup.bash

# Background a watcher that notifies systemd the moment /capstone/ready is true.
(
  # Block until one 'data: true' arrives on /capstone/ready.
  ros2 topic echo --once /capstone/ready std_msgs/Bool | grep -q "data: true"
  systemd-notify --ready --status="stack ready, accepting goals"
) &

# Hand the watchdog its heartbeat from a lightweight pinger (see telemetry below).
exec ros2 launch my_robot_bringup bringup.launch.py
```

Measure the cold boot honestly:

```bash
sudo systemctl daemon-reload
sudo systemctl enable capstone.service
# The real test: reboot the machine and time from boot to 'ready'.
sudo reboot
# After it comes back:
systemd-analyze blame | grep capstone
systemctl show capstone.service -p ActiveEnterTimestampMonotonic
journalctl -u capstone.service -b --no-pager | grep -E 'ready|active'
```

If `capstone.service` shows, say, 53.8 s from start to `ActiveEnterTimestamp`, that is your number — and because `Type=notify` gates on actual readiness, it is defensible. Under 60 s passes the bar.

### B.5 Telemetry: the heartbeat aggregator

The last Path B deliverable is a telemetry subscriber that aggregates the health of the whole graph into one heartbeat topic an operator dashboard can consume. This is the seed for Week 43's Foxglove work. It watches node liveness, per-topic rates, actuator status, and the fused-estimate covariance, and publishes a compact heartbeat at a fixed rate. Exercise 3 builds the full version; here is the architecture and the rate-monitoring core:

```python
#!/usr/bin/env python3
"""heartbeat.py - aggregate stack health into one /capstone/heartbeat topic.

Monitors per-topic publish rates and the EKF covariance trace, and emits a
DiagnosticArray plus a compact heartbeat at 2 Hz. The single source of truth an
operator dashboard subscribes to (Week 43 wires this into Foxglove)."""
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# topic -> (msg type, minimum acceptable Hz)
WATCH = {
    "/imu/data": (Imu, 100.0),
    "/scan": (LaserScan, 8.0),
    "/odometry/filtered": (Odometry, 20.0),
}


class RateMonitor:
    """Sliding-window publish-rate estimator for one topic."""
    def __init__(self, window_s: float = 2.0):
        self.window_s = window_s
        self.stamps: list[float] = []

    def tick(self, now: float):
        self.stamps.append(now)
        cutoff = now - self.window_s
        while self.stamps and self.stamps[0] < cutoff:
            self.stamps.pop(0)

    def hz(self, now: float) -> float:
        cutoff = now - self.window_s
        recent = [s for s in self.stamps if s >= cutoff]
        return len(recent) / self.window_s if recent else 0.0


class Heartbeat(Node):
    def __init__(self):
        super().__init__("heartbeat")
        self.monitors = {t: RateMonitor() for t in WATCH}
        self.cov_trace = float("nan")
        for topic, (msg_type, _) in WATCH.items():
            self.create_subscription(
                msg_type, topic,
                lambda m, t=topic: self._on(t, m), 50)
        # Pull the fused-estimate covariance off the filtered odom.
        self.create_subscription(
            Odometry, "/odometry/filtered", self._on_cov, 10)
        self.diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self.create_timer(0.5, self._publish)  # 2 Hz heartbeat

    def _on(self, topic, _msg):
        self.monitors[topic].tick(time.monotonic())

    def _on_cov(self, msg: Odometry):
        c = msg.pose.covariance
        # trace of the 6x6 pose covariance (indices 0,7,14,21,28,35)
        self.cov_trace = sum(c[i] for i in (0, 7, 14, 21, 28, 35))

    def _publish(self):
        now = time.monotonic()
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()
        all_ok = True
        for topic, (_, min_hz) in WATCH.items():
            hz = self.monitors[topic].hz(now)
            ok = hz >= min_hz
            all_ok = all_ok and ok
            st = DiagnosticStatus(
                name=f"rate:{topic}",
                level=DiagnosticStatus.OK if ok else DiagnosticStatus.ERROR,
                message=f"{hz:.1f} Hz (need {min_hz})",
                values=[KeyValue(key="hz", value=f"{hz:.2f}")])
            arr.status.append(st)
        cov_ok = self.cov_trace == self.cov_trace and self.cov_trace < 1.0  # NaN check + bound
        all_ok = all_ok and cov_ok
        arr.status.append(DiagnosticStatus(
            name="estimate:covariance_trace",
            level=DiagnosticStatus.OK if cov_ok else DiagnosticStatus.WARN,
            message=f"trace={self.cov_trace:.4f}",
            values=[KeyValue(key="trace", value=f"{self.cov_trace:.6f}")]))
        self.diag_pub.publish(arr)
        self.get_logger().info(
            f"heartbeat: {'NOMINAL' if all_ok else 'DEGRADED'} "
            f"cov_trace={self.cov_trace:.4f}")


def main():
    rclpy.init()
    node = Heartbeat()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
```

The covariance trace is the most important line. If the EKF's reported pose covariance grows without bound, the heartbeat goes DEGRADED *before* the operator notices anything wrong on the map — which is exactly the early warning an operator needs. A healthy hardened deployment shows NOMINAL with a bounded covariance trace from the moment the cold boot completes.

### B.6 The Path B integration-day checklist

- [ ] Every node that *can* be lifecycle is lifecycle; ordering is explicit via `RegisterEventHandler`.
- [ ] `/capstone/ready` exists and goes true only when the last layer is active.
- [ ] systemd unit uses `Type=notify`; the wrapper calls `systemd-notify --ready` on `/capstone/ready`.
- [ ] `After=network-online.target` set; DDS discovery is clean post-boot.
- [ ] A full reboot brings the stack to `ready` in under 60 s, measured with `systemd-analyze` / `journalctl`.
- [ ] The heartbeat publishes at 2 Hz with per-topic rates and the covariance trace.
- [ ] A killed driver makes the heartbeat go DEGRADED rather than the graph hanging silently.
- [ ] The whole sequence is reproducible: reboot twice, get the same result.

---

## Where both paths converge

Path A produces a 20-meter run with a measured terminal drift. Path B produces a sub-60-second cold boot with a heartbeat. Different artifacts, same destination: both feed the Week 48 acceptance bar of under 0.5 m drift over 20 meters, and both train the same underlying discipline — *measure, verify layer by layer, fail loud, defend the number*. The challenge this week makes the bar explicit on whichever path you chose.

The thing that distinguishes the engineers who pass this week is not the robot or the deployment target. It is that they treated integration day as verification, not debugging. They brought the stack up one confirmed layer at a time, they measured before they trusted, and when something surprised them they had a checklist that told them exactly which layer to look at. Build the checklist. Run it after every power cycle and every reboot. That habit is the whole lecture.

---

## Key takeaways

- **Bring up bottom-up: power, safety, signals, motion.** Verify each layer reports correctly before trusting the one above it. The first full-stack run should be boring.
- **The TF tree must be fully connected with no future-extrapolation errors.** Those errors are a timestamp problem from Lecture 1; fix the stamps, do not widen the timeout.
- **Ad-hoc launch graphs do not cold-boot.** Lifecycle nodes plus explicit `RegisterEventHandler` ordering plus a readiness gate make the boot deterministic.
- **`Type=notify` makes the cold-boot time honest.** systemd blocks on actual readiness instead of guessing, so `systemd-analyze` gives a defensible number.
- **One heartbeat topic is the seed of fleet ops.** Aggregate node rates, actuator status, and the EKF covariance trace; go DEGRADED before the operator notices.
- **Both paths converge on the same discipline and the same Week 48 bar.** Verify layer by layer, fail loud, defend the number.
