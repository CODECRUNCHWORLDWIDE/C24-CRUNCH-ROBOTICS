# Lecture 2 — The Capstone-Kickoff Ritual: Pre-flight Checks, the Chaos-Drill Template, and the Safety-Case Template

> **Reading time:** ~80 minutes. **Hands-on time:** ~70 minutes (you write a pre-flight check node, fill in a chaos-drill template for one fault, and scaffold a safety-case template for your robot).

Lecture 1 turned the capstone spec into a contract you can read and write back. This lecture is about the *ritual* that stands the contracted system up safely — the deterministic sequence you run before you ever send the robot a goal. A complex robot is not "launched"; it is *brought up* under a checklist, the way an aircraft is not "started" but taken through pre-flight. The ritual has three artifacts you build this week and reuse for the rest of the track: the **pre-flight check**, the **chaos-drill template**, and the **safety-case template**. Build all three now and the build sprints of Phase 6 have a scaffold instead of a blank page.

## 2.1 — Why a ritual, and why now

You have stood up small ROS2 graphs before — a robot, a sensor, a slam node, an rviz2 layout. The capstone graph is different in kind, not just in size. It has, at minimum: a sim, two robot models (base + arm), the `ros_gz` bridge, the EKF, the fused perception node, a YOLO detector, a 3D clustering node, Nav2 (planner + controller + behavior + smoother + recovery + lifecycle manager), MoveIt2 (`move_group` + planning scene), the VLA policy node, the behavior tree, the safety wrapper, the telemetry spine, and the heartbeat publisher. Twenty-plus nodes, a dozen of them lifecycle-managed, all of which must come up in the right order, on the right topics, in the right frames, at the right rates, before a single instruction is meaningful.

When that many things must be true at once, "launch it and see" is not a strategy — it is a coin flip you pay for in lost hours. The senior move is a **pre-flight check**: a scripted node that asserts, deterministically and before any goal is sent, that every precondition holds, and that *aborts the run loudly with an actionable message* the moment one does not. Aviation runs the checklist not because the crew is forgetful but because an unchecked assumption at altitude is unrecoverable. Your robot's altitude is "about to command a 6-DOF arm near a person." The checklist is not optional discipline; it is the cheapest place to catch the integration defects from Lecture 1's list before they become a robot doing the wrong thing.

## 2.2 — The four integration defects the pre-flight check is hunting

The pre-flight check exists to catch the four canonical integration defects. Know them, because each one maps to a specific check.

**The frame/timing mismatch.** Two components agree on a topic but disagree on the frame or the timestamp. The EKF publishes `map → odom`; the VLA expects a grasp pose in `base_link`; the `tf2` chain between them is broken or stale. Symptom: the arm reaches confidently to the wrong place. The pre-flight check catches it by asserting every required transform in the coverage matrix is resolvable *and recent* (`can_transform` with a non-zero time, then a freshness check on the stamp).

**The stale-perception race.** The planner reads a detection that is older than its own tolerance. `/perception/objects` is published at 10 Hz; the BT ticks at 20 Hz and grabs whatever is latest; on a slow frame the "latest" detection is 150 ms old and the object has moved. Symptom: the grasp targets where the cup *was*. The pre-flight check catches the *rate* (it asserts `/perception/objects` publishes at ≥ its required Hz); the runtime guard (a stamp-age check before use) catches the rest, and it belongs in the BT condition node, not the pre-flight.

**The lifecycle bring-up-order deadlock.** Node A's `on_activate` blocks waiting for an input that only Node B produces, but the lifecycle manager is trying to activate A before B. Symptom: cold boot hangs forever, never reaching "operational." The pre-flight check catches it by asserting the lifecycle state of every managed node is `active` within a timeout, and by reporting *which* node is stuck so you can fix the bring-up order.

**The safety-clamp/controller fight.** The safety wrapper clamps a velocity the MPC was counting on, so the controller and the filter oscillate. Symptom: jittery motion, the safety-filter status flickering between pass and clamp. The pre-flight check cannot catch this directly (it is a dynamic interaction), but it asserts the safety wrapper is *present and subscribed* so you at least know the leash is on; the telemetry spine makes the fight *visible* so you catch it during the run.

The lesson: a pre-flight check is not a unit test. It is a *precondition* assertion over the live, composed graph, run once at bring-up, that fails fast and points you at the broken assumption. It catches the static defects (presence, rate, frame, lifecycle state) so the run only has to worry about the dynamic ones.

## 2.3 — The pre-flight check, in code

Here is the shape of the pre-flight check node. It runs a list of named checks, each returning pass/fail with a message, prints a coverage report, and exits non-zero if any check fails — which a launch file or CI can gate on. This is the skeleton; Exercise 2 makes you build the full version against your own stack.

```python
#!/usr/bin/env python3
"""Pre-flight check skeleton: assert the composed capstone graph is healthy
before any goal is sent. Exits 0 if all checks pass, 1 otherwise."""

import sys
import time
from dataclasses import dataclass
from typing import Callable

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from tf2_ros import Buffer, TransformListener
from rclpy.duration import Duration
from rclpy.time import Time


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class PreflightCheck(Node):
    """Runs a battery of preconditions over the live graph and reports."""

    def __init__(self) -> None:
        super().__init__("preflight_check")
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        # Sensor-style QoS so we can sample best-effort streams.
        self._sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

    # --- individual checks ----------------------------------------------

    def check_topic_publishing(self, topic: str, min_hz: float,
                               window_s: float = 3.0) -> CheckResult:
        """Assert `topic` is publishing at >= min_hz over a short window."""
        count = {"n": 0}
        # We subscribe with a generic message-agnostic counter via the
        # rclpy raw-subscription API is overkill here; in the full exercise
        # we subscribe with the concrete type. For the skeleton we count
        # using the topic's discovered type.
        from rosidl_runtime_py.utilities import get_message
        types = dict(self.get_topic_names_and_types()).get(topic)
        if not types:
            return CheckResult(f"topic:{topic}", False,
                               f"{topic} not present on the graph")
        msg_type = get_message(types[0])

        def _cb(_msg) -> None:
            count["n"] += 1

        sub = self.create_subscription(msg_type, topic, _cb, self._sensor_qos)
        end = time.monotonic() + window_s
        while time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
        self.destroy_subscription(sub)

        hz = count["n"] / window_s
        ok = hz >= min_hz
        return CheckResult(
            f"topic:{topic}", ok,
            f"{hz:.1f} Hz observed (need >= {min_hz:.1f} Hz)",
        )

    def check_transform(self, target: str, source: str,
                        max_age_s: float = 1.0) -> CheckResult:
        """Assert target<-source is resolvable and recent."""
        try:
            tf = self._tf_buffer.lookup_transform(
                target, source, Time(),
                timeout=Duration(seconds=2.0))
        except Exception as exc:  # tf2 raises several concrete types
            return CheckResult(
                f"tf:{target}<-{source}", False,
                f"lookup failed: {exc}")
        stamp = Time.from_msg(tf.header.stamp)
        age = (self.get_clock().now() - stamp).nanoseconds * 1e-9
        ok = age <= max_age_s
        return CheckResult(
            f"tf:{target}<-{source}", ok,
            f"transform age {age:.2f}s (need <= {max_age_s:.2f}s)")

    def check_lifecycle_active(self, node_name: str) -> CheckResult:
        """Assert a managed node reports the ACTIVE state."""
        from lifecycle_msgs.srv import GetState
        client = self.create_client(
            GetState, f"/{node_name}/get_state")
        if not client.wait_for_service(timeout_sec=3.0):
            return CheckResult(
                f"lifecycle:{node_name}", False,
                "get_state service not available")
        future = client.call_async(GetState.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result() is None:
            return CheckResult(
                f"lifecycle:{node_name}", False,
                "get_state call timed out")
        label = future.result().current_state.label
        ok = label == "active"
        return CheckResult(
            f"lifecycle:{node_name}", ok,
            f"state={label} (need active)")

    def check_clock_advancing(self, window_s: float = 1.0) -> CheckResult:
        """Assert the ROS clock is advancing (sim time not frozen)."""
        t0 = self.get_clock().now()
        end = time.monotonic() + window_s
        while time.monotonic() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
        dt = (self.get_clock().now() - t0).nanoseconds * 1e-9
        ok = dt > 0.5 * window_s
        return CheckResult(
            "clock", ok,
            f"clock advanced {dt:.2f}s in {window_s:.2f}s wall")


def run_battery(node: PreflightCheck) -> list[CheckResult]:
    """The coverage matrix: every precondition the capstone run depends on."""
    checks: list[Callable[[], CheckResult]] = [
        lambda: node.check_clock_advancing(),
        lambda: node.check_topic_publishing("/odometry/filtered", 20.0),
        lambda: node.check_topic_publishing("/perception/objects", 8.0),
        lambda: node.check_topic_publishing("/scan", 8.0),
        lambda: node.check_transform("map", "base_link", max_age_s=1.0),
        lambda: node.check_transform("base_link", "arm_tool0", max_age_s=1.0),
        lambda: node.check_lifecycle_active("controller_server"),
        lambda: node.check_lifecycle_active("planner_server"),
        lambda: node.check_lifecycle_active("move_group"),
        lambda: node.check_lifecycle_active("safety_wrapper"),
    ]
    return [c() for c in checks]


def main(argv=None) -> None:
    rclpy.init(args=argv)
    node = PreflightCheck()
    # Let discovery settle before we sample.
    settle_end = time.monotonic() + 2.0
    while time.monotonic() < settle_end and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)

    results = run_battery(node)
    width = max(len(r.name) for r in results)
    failed = 0
    node.get_logger().info("==== PRE-FLIGHT CHECK ====")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        node.get_logger().info(f"[{mark}] {r.name.ljust(width)}  {r.detail}")
        if not r.passed:
            failed += 1
    node.get_logger().info(
        f"==== {len(results) - failed}/{len(results)} checks passed ====")

    node.destroy_node()
    rclpy.shutdown()
    # The contract: a failed pre-flight aborts the run.
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
```

Read the design choices. Every check returns a `CheckResult` with a *detail string* — not just pass/fail, but the observed value next to the required value, so a failure is immediately actionable. The battery is a flat list (the "coverage matrix") so adding a precondition is one line. `main` exits non-zero on any failure, which is the load-bearing behavior: a launch file or CI step can gate the run on `preflight_check` returning 0. The clock check exists because a frozen sim clock (the most common Gz/Isaac integration footgun) makes every rate check lie, so you check it first.

What the pre-flight check is *not*: it is not a substitute for runtime guards. The stale-perception race needs a stamp-age check at the moment of use, inside the BT condition node — pre-flight only verifies the *rate*. The safety-clamp fight needs telemetry to see it live. Pre-flight catches the static preconditions; the run and the telemetry catch the dynamic ones. Both are part of the ritual.

## 2.4 — Ordered lifecycle bring-up

The pre-flight check assumes the graph is *already* up. Getting it up in the right order is the job of a lifecycle manager — the Nav2 pattern you rehearsed in Week 4's mini-project, now at full scale. The principle: nothing transitions to `active` until the nodes it depends on are `active`. The dependency order for the capstone is roughly:

1. **Sensors and the bridge.** The `ros_gz` bridge, the simulated IMU, LiDAR, RGB-D. These are not lifecycle-managed (they are sim plugins) but they must be publishing before anything downstream configures.
2. **State estimation.** The EKF (`robot_localization`) and the `tf2` broadcasters. The `map → odom → base_link` chain must be live.
3. **Perception.** The fused perception node, which depends on (1) and (2).
4. **Planning and control.** Nav2's lifecycle manager brings up planner → controller → behavior → smoother → recovery; MoveIt2's `move_group`. These depend on (2) and (3).
5. **Policy and safety.** The VLA policy node and the safety wrapper. The safety wrapper must activate *before* the controllers it guards can command — it is the leash, and the leash goes on first among the things that can move the robot.
6. **The behavior tree and telemetry.** The top-level BT (which dispatches everything below) and the telemetry spine, last, because they observe and orchestrate the rest.

A bring-up that activates the BT before the safety wrapper is a hazard: the tree could tick a motion goal before the leash is on. The ordering is a safety property, not a convenience. Encode it in the lifecycle manager's `node_names` list and its activation sequence, exactly as Nav2 does, and let the pre-flight check verify the end state.

## 2.5 — The chaos-drill template

Week 46 is Gameday: an instructor injects a fault mid-task and grades your recovery against the clock and the dashboard. You do not want to *design* your chaos response under live-grading pressure. You design it now, as a template you fill in for each fault, and Week 46 becomes execution. The template borrows its structure from chaos engineering (a steady-state hypothesis, a real fault, a measured deviation) and ends with the postmortem structure from the Google SRE book.

A chaos-drill specification has six parts. Here is the template, filled in for the **sensor-dropout-mid-task** drill so you see the shape; you fill in the **planner-deadlock-at-doorway** drill in the homework.

> ### Chaos Drill: Sensor Dropout Mid-Task
>
> **1. Steady-state hypothesis.** Under normal operation, the robot executes a language-conditioned pick-and-place with the LiDAR contributing to the costmap and the localization. The dashboard shows `/scan` at ~10 Hz, the costmap populated, and the safety-filter status `clear`.
>
> **2. Injected fault.** Mid-execution (after the base goal is sent, before the grasp), the LiDAR is killed: `ros2 lifecycle set /lidar_driver deactivate` plus a process-kill of the sim plugin, so `/scan` stops cold. Blast radius: one sensor, one robot, sim only.
>
> **3. Detection signal.** A `scan_watchdog` node subscribes to `/scan` and publishes `/health/lidar = STALE` when no message arrives for > 0.5 s. This is the operator-detectable event. It must reach the dashboard.
>
> **4. Graceful-degradation path.** On `/health/lidar = STALE`: the safety wrapper latches a soft-stop (the base halts; the arm completes or safely retracts the in-flight trajectory), the BT transitions to a `DEGRADED` branch, and the robot either completes the task on remaining sensors (if the object is already localized and the arm is in reach) or aborts to a safe pose and alerts.
>
> **5. Recovery deadline and success criterion.** The dashboard shows the `/health/lidar = STALE` event within **60 seconds** of the fault (the acceptance number), and the robot reaches a defined safe state (completed-or-safely-aborted) without colliding. Measured: time from fault injection to dashboard event, and time to safe state.
>
> **6. Postmortem (filled in after the drill).** Timeline (fault at t=…, detected at t=…, safe at t=…). Root cause. Contributing factors. What worked. What didn't. Action items. Two-to-four pages, against the Week 46 rubric.

Notice that the template is *runnable as a thought experiment* before you have the code. Filling it in for both faults this week tells you exactly what to build before Week 46: the `scan_watchdog`, the `/health/*` topic family, the `DEGRADED` BT branch, and the dashboard panels that surface the health signals. Without the template, you discover those needs live on Gameday. With it, Gameday is a rehearsed play.

## 2.6 — The safety-case template

The safety case is the Week 41 artifact and a portfolio piece — an 8–15-page argument that your robot is acceptably safe to operate in shared space. You scaffold the template this week and do a first hazard pass, so Week 41 is filling a structured form rather than facing a blank page. The structure follows the ISO 13482 / ISO 10218 framing and Goal Structuring Notation: a top-level safety claim, decomposed into sub-claims, each supported by evidence.

The template has seven sections:

**1. Intended use and operational design domain.** What the robot is for ("fetch a named object from a bench and bring it to the operator in a shared indoor space"), where it operates, who is nearby, and the explicit boundaries. The ODD is the fence; everything outside it is out of scope and must be stated as such.

**2. Foreseeable misuse.** How a reasonable person might use it wrongly — standing in the workspace, issuing an instruction that names a hazardous object, blocking the base. Foreseeable misuse is a requirement of ISO 13482; "the user shouldn't do that" is not a mitigation.

**3. Hazard list.** Every way the robot could cause harm. For a mobile manipulator: base collision with a person, arm strike during a grasp, dropped object, pinch at the gripper, runaway under a failed controller, wrong-object delivery of a hazardous item. This is your Week 24 hazard log, expanded. Start it this week.

**4. FMEA.** For each hazard, the failure mode, effect, severity (1–10), occurrence (1–10), detectability (1–10), and the resulting Risk Priority Number (S × O × D). The MIL-STD-1629A procedure. The RPN ranks where mitigation effort goes.

**5. Mitigations.** For each high-RPN hazard, the control that reduces it, mapped to a component in your system: the 200 ms software E-stop (base collision), the workspace clamps (arm strike), the perception confidence gate (wrong-object delivery), the classical fallback (runaway policy), the velocity clamp (runaway controller). Each mitigation cites the node/topic that implements it — the safety property's "owning artifact" column from Lecture 1 feeds straight in here.

**6. Residual risk.** What risk remains after mitigation, and the argument that it is acceptable. Honest robotics safety never claims zero risk; it claims *bounded, justified* residual risk.

**7. Validation plan.** How each mitigation is tested. The 200 ms latch is measured. The clamps are exercised with out-of-bounds inputs. The fallback is triggered by forcing three rejections. The chaos drills *are* part of the validation plan. This section connects the safety case to the chaos-drill template — the drills are how you validate the degradation paths.

Here is the skeleton you scaffold this week:

```text
safety-case/
├── 01-intended-use-and-odd.md
├── 02-foreseeable-misuse.md
├── 03-hazard-list.md            # start populating this week (Week 24 log, expanded)
├── 04-fmea.md                   # table: hazard | mode | effect | S | O | D | RPN
├── 05-mitigations.md            # each mitigation -> owning node/topic
├── 06-residual-risk.md
├── 07-validation-plan.md        # ties to the chaos-drill template
└── README.md                    # the top-level safety claim + GSN structure
```

The mitigations section is the bridge between the safety case and everything you built. Every safety property in the Lecture 1 contract — the E-stop latch, the clamps, the fallback, the confidence gate — appears here as a mitigation with an owning artifact and a validation test. If a hazard has no mitigation, that is a finding the panel will catch; better you catch it this week, scaffolding the template, than the panel catches it at the defense.

## 2.7 — Wiring the pre-flight check as a launch gate

A pre-flight check that prints a report and exits is only half the ritual. The other half is *gating the run on it*: nothing downstream may proceed until pre-flight returns 0. There are three ways to wire this, in increasing order of robustness, and you should know all three because the capstone uses the third.

**The shell gate (fast, blunt).** In a wrapper script, run the check and branch on its exit code:

```bash
#!/usr/bin/env bash
set -euo pipefail
ros2 launch crunch_capstone bringup_only.launch.py &  # graph up, no run yet
BRINGUP_PID=$!
sleep 8                                                # let lifecycle settle

if ! python3 -m crunch_capstone.preflight_check; then
    echo "PRE-FLIGHT FAILED — aborting run, tearing down."
    kill "${BRINGUP_PID}"
    exit 1
fi

echo "PRE-FLIGHT PASSED — starting the run."
ros2 run crunch_capstone capstone_run
```

This is the blunt instrument: the run never starts if pre-flight fails, and the graph is torn down. It is honest and it works, but the fixed `sleep 8` is fragile — too short and you check before bring-up settles; too long and your cold-boot number suffers.

**The launch `OnProcessExit` gate (integrated).** Inside the launch file, register the run to start only when the pre-flight process exits successfully, using a `RegisterEventHandler` on `OnProcessExit` that inspects the return code:

```python
from launch import LaunchDescription
from launch.actions import RegisterEventHandler, ExecuteProcess, LogInfo
from launch.event_handlers import OnProcessExit

def generate_launch_description() -> LaunchDescription:
    preflight = ExecuteProcess(
        cmd=["python3", "-m", "crunch_capstone.preflight_check"],
        name="preflight_check", output="screen",
    )
    run = ExecuteProcess(
        cmd=["ros2", "run", "crunch_capstone", "capstone_run"],
        name="capstone_run", output="screen",
    )
    gate = RegisterEventHandler(
        OnProcessExit(
            target_action=preflight,
            on_exit=lambda event, ctx: (
                [LogInfo(msg="pre-flight passed; starting run"), run]
                if event.returncode == 0
                else [LogInfo(msg="PRE-FLIGHT FAILED; run will NOT start")]
            ),
        )
    )
    # In the full launch file you also include the sensor, state-estimation,
    # perception, Nav2, MoveIt2, policy, safety, and telemetry actions before
    # `preflight`, so the graph is up by the time the check runs.
    return LaunchDescription([preflight, gate])
```

This keeps the gate inside the launch graph, so there is one command and one place that owns the bring-up-then-verify-then-run sequence. The return-code branch is the load-bearing line: a non-zero pre-flight means the run action is simply never added.

**The lifecycle-transition gate (production).** The most robust form makes pre-flight a *condition of activation*: the lifecycle manager will not transition the behavior tree to `active` until a pre-flight node reports healthy via a service. The BT — which dispatches every motion — therefore cannot tick a goal until the preconditions hold, structurally. This is the form the capstone uses, because it ties the gate to the same lifecycle machinery that orders the rest of the bring-up. The pre-flight node exposes a `trigger`-style service; the lifecycle manager calls it as the last step before activating the BT, and aborts the activation sequence if it fails.

The lesson across all three: **the gate is not the check; the gate is what the check's result is wired to.** A check whose failure does not stop the run is decoration. Wire the exit code — or the service result — to something that actually withholds the run, and the ritual has teeth.

## 2.8 — How the three templates compose into the milestone

The three artifacts are not independent. They compose:

- The **pre-flight check** verifies the preconditions the **safety case** assumes (the safety wrapper is active, the E-stop topic is present, the frames are valid). A failed pre-flight is a safety-relevant event.
- The **chaos-drill template** is the **validation plan** for the safety case's degradation-path mitigations. You cannot claim "the robot degrades gracefully on sensor loss" without the drill that exercises it.
- The **safety case** justifies the **pre-flight check's** coverage matrix: every check exists because some hazard's mitigation depends on the precondition it verifies.

This is why you build all three in the same week. Together they form the kickoff ritual: read the contract (Lecture 1), prove the preconditions (pre-flight), know how you will break and recover (chaos template), and argue you are safe to run (safety template). With the ritual in hand, you stand the system up — and the mini-project is the first time you run it all the way through.

## 2.9 — Summary

A complex robot is brought up under a checklist, not launched and hoped over. Build three reusable artifacts this week: a **pre-flight check** node that asserts every precondition (topic presence and rate, transform validity and freshness, lifecycle state, clock advance) and aborts the run loudly on any failure; a **chaos-drill template** with six parts (steady-state hypothesis, injected fault, detection signal, degradation path, recovery deadline, postmortem) filled in for both Week-46 faults; and a **safety-case template** with seven sections (intended use, misuse, hazards, FMEA, mitigations, residual risk, validation) scaffolded and started. Order your lifecycle bring-up so the safety leash goes on before anything can move. The pre-flight check hunts the four integration defects — frame/timing mismatch, stale-perception race, lifecycle-order deadlock, safety-clamp fight — and catches the static ones before they become a robot doing the wrong thing. With the ritual in hand, the mini-project's job is to run the whole contracted system once, cleanly, observably, with nobody touching the keyboard.

---

**References**

- Google SRE Book — "Reliable Product Launches at Scale" (the launch checklist): <https://sre.google/sre-book/reliable-product-launches/>
- Google SRE Book — "Postmortem Culture": <https://sre.google/sre-book/postmortem-culture/>
- Principles of Chaos Engineering: <https://principlesofchaos.org/>
- Nav2 — Lifecycle and bringup: <https://docs.nav2.org/concepts/index.html>
- REP 105 — Coordinate frames: <https://www.ros.org/reps/rep-0105.html>
- ISO 13482:2014 — Personal care robots (summary): <https://www.iso.org/standard/53820.html>
- ISO 10218-1:2025 — Industrial robots, safety (summary): <https://www.iso.org/standard/73101.html>
- NASA Software Safety Guidebook (hazard analysis, FDIR): <https://standards.nasa.gov/standard/NASA/NASA-GB-871913>
