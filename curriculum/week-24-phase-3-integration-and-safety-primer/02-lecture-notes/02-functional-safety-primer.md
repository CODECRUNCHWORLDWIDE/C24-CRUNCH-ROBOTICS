# Lecture 2 — A Functional-Safety Primer: The Hazard Log, the Fail-Safe, and the 200 ms E-Stop

> **Reading time:** ~80 minutes. **Hands-on time:** ~70 minutes (you write your first hazard log, implement a software E-stop that cancels both the Nav2 action and the MoveIt2 trajectory, and measure the latch-to-stop latency).
> **Outcome:** You can state risk as severity × probability, name the fail-safe categories and the software-vs-hardware E-stop distinction, author a hazard log keyed on your controllers' known failure modes, frame your robot against ISO 10218 and ISO 13482, and build an E-stop that meets a measured 200 ms latch budget.

Lecture 1 composed the body. This lecture puts the leash on it. The composed robot can now drive *and* reach near a person, and the senior habit that this lecture installs is simple to state and uncomfortable to practice:

> **Every controller has a known failure mode. Write it down before you ship. A robot that can move near a person without a written hazard log and a measured fail-safe is not "almost safe" — it is undocumented, and undocumented is the same as unsafe in any review that matters.**

Safety is half engineering and half evidence. A working E-stop you never measured is not a fail-safe; it is a hope. A hazard you never wrote down is not mitigated; it is forgotten. This lecture is about turning the things-that-could-go-wrong rattling around in your head into engineering artifacts — a hazard log and a measured E-stop — that a reviewer (and, eight weeks from now, a capstone panel) can check.

---

## 2.1 — Risk, precisely: severity × probability

The word "risk" gets used loosely. In functional safety it has a precise, two-factor meaning, inherited from ISO 12100 (the parent risk-assessment standard for all machinery):

> **Risk = the severity of the harm × the probability of that harm occurring.**

Both factors matter, and conflating them is the most common beginner mistake. A hazard that is *catastrophic but astronomically unlikely* (the arm achieves relativistic velocity) and a hazard that is *trivial but constant* (the base's status LED is the wrong shade) are both low-risk, for opposite reasons. The hazard you must prioritize is the one where severity *and* probability are both meaningful: the base collides with a person at walking speed (moderate-to-high severity, non-trivial probability in shared space). Risk assessment is the discipline of estimating both factors for every hazard and ranking your mitigation effort by the product.

The probability factor itself decomposes — ISO 12100 splits it into the *frequency and duration of exposure*, the *probability of the hazardous event*, and the *possibility of avoiding or limiting harm*. You do not need the full apparatus this week. You need the instinct: a hazard near a person who cannot get out of the way (low avoidability) is worse than the same hazard in a caged cell (the person isn't there). Your mobile manipulator lives in shared space — low avoidability — which is precisely why its safety bar is higher than a caged industrial arm's, and why ISO 13482 (personal-care robots in shared space) is in scope at all.

The output of risk assessment is not a number you frame on the wall. It is a *ranking* that tells you where to spend mitigation effort. You cannot mitigate everything to zero; honest safety claims *bounded, justified* residual risk, not zero risk. The hazard log (§2.4) is where you record the ranking and the mitigations; the FMEA (Week 41) is where you make the ranking quantitative with the severity × occurrence × detectability RPN.

---

## 2.2 — The fail-safe categories

When something goes wrong, the robot must move to a *safe* state. "Safe" is not one thing; there are three categories, and choosing the right one per hazard is a design decision.

**Fail-stop (halt and stay halted).** On a fault, cut motion and stay cut until a human re-arms. This is the E-stop's behavior, and it is the right default for "a person might be in danger right now." It is simple, predictable, and unambiguous: zero velocity, zero torque (or holding torque to prevent the arm from falling), no further commands honored until reset. The cost is availability — a fail-stopped robot does no work — but availability is never the priority when a person is at risk.

**Fail-safe-state (move to a defined safe configuration).** On a fault, actively move to a configuration known to be safe before halting: retract the arm to a tucked pose, lower a lifted load, steer the base to the road edge. This is *more* than fail-stop because it requires the very actuators that may be implicated in the fault to perform a final controlled motion — which is why it is reserved for faults where the actuators are *trusted* (a perception dropout, say) and forbidden for faults where they are *suspect* (a runaway controller; you do not ask a runaway controller to perform a careful retraction).

**Fail-operational (degrade but keep going).** On a fault, continue operating with reduced capability: lose the LiDAR, fall back to camera-only navigation at reduced speed. This is the category that keeps an aircraft flying on one engine, and it is the *hardest* to get right because "keep going safely with a degraded sensor" is a much stronger claim than "stop." For a Week-24 mobile manipulator, fail-operational is aspirational; fail-stop and fail-safe-state are what you implement. (Phase 6's chaos drills explore graceful degradation, which is fail-operational's gentler cousin.)

The mapping you will write into your hazard log: *which* fault triggers *which* category. A LiDAR dropout → fail-safe-state (retract and stop; the actuators are trusted). A controller going unstable → fail-stop (kill motion immediately; the actuator is suspect). An E-stop press → fail-stop (the human has decided; obey instantly). Choosing the category per hazard, and writing it down, is the practice.

---

## 2.3 — Software E-stop vs. hardware E-stop

This is the distinction that separates a demo from a deployable robot, and it is the one reviewers probe hardest.

A **software E-stop** is a topic — `/safety/estop` — that, when latched `true`, causes your nodes to cancel actions and zero commands. It is fast to build, easy to test, and integrates with your behavior tree and your telemetry. It is also, fundamentally, *part of the same software that might be the thing that failed.* If your controller node has wedged, or the executor has deadlocked, or the DDS graph has partitioned, the software E-stop may never fire — because the very subsystem that would carry the stop is the subsystem that broke.

A **hardware E-stop** is a physical, normally-closed circuit — a big red mushroom button — wired so that pressing it *physically removes power or enable* from the motor drivers, *independent of any software.* It works precisely when the software is the thing that failed, because it does not go through the software at all. IEC 60204-1 defines what an emergency-stop function must guarantee and the stop categories (0: immediate power removal; 1: controlled stop then power removal; 2: controlled stop, power retained). The hardware E-stop is, classically, a category-0 stop: it does not negotiate, it does not wait for a graceful trajectory, it cuts the enable line.

> **The rule:** the software E-stop is for the failures you can anticipate and handle in software; the hardware E-stop is for the failures that take the software with them. A deployable robot has both. A safety case that lists only the software E-stop has a hole a reviewer will find: "what stops the robot when the bug is in the node that runs your E-stop?"

For Week 24 you implement and *measure* the software E-stop, and you *document* the hardware E-stop — what it would be, which stop category, how it relates to the software one. This is the same Path-A (build the hardware button) / Path-B (simulate and document it) split the capstone uses. Documenting the hardware E-stop is not busywork: it forces you to state the failure modes the software E-stop *cannot* cover, which is exactly the residual risk a safety case must own.

The IEC 60204-1 **stop categories** are the precise vocabulary for *how* a stop happens, and you should be able to name them because a safety review will ask which one your E-stop implements:

- **Category 0 — immediate removal of power.** The actuators lose drive power instantly; the robot coasts/brakes to a stop with no controlled trajectory. This is the classic hardware-mushroom-button behavior: it does not negotiate, it cuts the enable line. Fastest to *initiate*, but the stopping *motion* is uncontrolled (the arm may sag under gravity unless brakes engage).
- **Category 1 — controlled stop, then power removal.** The controller is allowed to bring the robot to a controlled stop (a smooth deceleration, the arm holding its path), and *then* power is removed. Safer for the *motion* (no uncontrolled coast) but it relies on the controller working long enough to execute the controlled stop — so it is appropriate only when the controller is trusted.
- **Category 2 — controlled stop, power retained.** The robot stops under control but stays powered (holding position, ready to resume). This is what a *pause* is, not an emergency stop; it is the right behavior for a non-emergency hold, not for "a person is in danger."

Your software E-stop, canceling actions and zeroing `/cmd_vel` while the controller still runs, is closest to a **category 1** stop (controlled, then the motion ceases). Your *hardware* E-stop, if you build it, is a **category 0** (cut power). A deployable robot pairs them: category 1 in software for the common case (smooth, controlled), category 0 in hardware for the case where the software is the failure (blunt, certain). Naming the category in your hazard log is how you tell a reviewer exactly what kind of stop each mitigation provides — and "category 0 hardware backing a category 1 software stop" is the honest, complete answer.

---

## 2.4 — The hazard log: your first safety artifact

A hazard log is a living table. Each row is a hazard, and the columns force you to think it through:

| Hazard | Cause | Effect | Severity (1–10) | Fail-safe category | Mitigation | Owning node/topic |
|---|---|---|---:|---|---|---|

You already know most of the rows, because you spent Weeks 20–23 learning each controller's failure mode. The hazard log is, in large part, a catalog of those failure modes promoted to safety artifacts. Here is a first pass for the composed base+arm robot:

| Hazard | Cause | Effect | Sev | Category | Mitigation | Owner |
|---|---|---|---:|---|---|---|
| Base collides with a person | PID integrator wind-up against a wall releases a velocity surge; or planner drives into an undetected obstacle | Impact at walking speed; injury | 8 | fail-stop | software E-stop (200 ms latch) + velocity clamp + hardware E-stop | `safety_wrapper`, `/safety/estop` |
| Arm strikes a person during a reach | MoveIt2 plans through a workspace the person entered after the planning scene was captured | Impact; injury | 8 | fail-stop | software E-stop halts trajectory; workspace clamp; reduced arm speed in shared mode | `safety_wrapper`, `/arm_controller` |
| Base runs away | Controller goes unstable (LQR far from linearization point; MPC returns infeasible plan past its time budget) | Uncontrolled motion | 9 | fail-stop | velocity clamp rejects out-of-bounds `cmd_vel`; E-stop; hardware E-stop (actuator is suspect — no fail-safe-state) | `safety_wrapper`, `/cmd_vel` |
| Arm collapses under gravity | Trajectory controller drops holding torque on fault | Arm falls; dropped/struck load | 6 | fail-safe-state | hold position on fault; brake engagement; retract to tucked pose if actuators trusted | `arm_controller` |
| E-stop missed by a late-joining node | `/safety/estop` published `VOLATILE`; a controller that subscribed late never sees the latch | Robot keeps moving after E-stop pressed | 9 | fail-stop | `RELIABLE`/`TRANSIENT_LOCAL` latched E-stop so late subscribers receive it | `/safety/estop` (QoS) |
| Stale goal executed after recovery | BT re-dispatches an old goal after a transient fault | Robot moves to an outdated target | 4 | fail-stop | clear goal on fault; require explicit re-arm | `task_bt` |

Read the table for what it teaches. The "E-stop missed by a late-joining node" row is the Week 5 QoS lesson appearing as a *safety hazard with a severity of 9* — durability is not a networking nicety here, it is the difference between an E-stop that works and one that silently doesn't. The "base runs away" row explicitly forbids fail-safe-state ("actuator is suspect"), which is the §2.2 reasoning made concrete. The "owning node/topic" column is the bridge to your real system: every mitigation cites the component that implements it, so a hazard with no owner is a visible gap — a finding, the same way an empty owning-artifact cell is a finding in the capstone contract.

This hazard log is the *seed* of the Week 41 safety case. There, it grows: each hazard gets an FMEA row (severity × occurrence × detectability → RPN), each mitigation gets a validation test, and the whole thing gets the ISO framing and the residual-risk argument. Starting it now means Week 41 expands a table instead of facing a blank page — and it means the safety stance is designed in from Phase 3, not bolted on at the end.

### 2.4.1 — How to fill a hazard-log row, step by step

A hazard log looks obvious once it exists, but filling a row well is a discipline. Take the worst row — "base collides with a person" — and walk it:

1. **Name the hazard as harm to someone or something, not as a component failure.** "PID wind-up" is a *cause*, not a hazard. The hazard is "base collides with a person." Naming the harm keeps you focused on consequences, which is what severity rates.
2. **List the causes — plural.** A hazard usually has several: PID integrator wind-up against a wall releasing a velocity surge; the planner driving into an undetected obstacle; an operator command sending the base into an occupied space. Each cause may need a different mitigation, which is why you enumerate them.
3. **State the effect concretely.** "Impact at walking speed; possible injury." Concreteness drives the severity rating — "impact at 1.5 m/s with a 30 kg base" is a different severity than "a gentle nudge."
4. **Rate severity 1–10.** Use a consistent scale (MIL-STD-1629A's): 1 = negligible, 10 = catastrophic/fatal. A person-impact at speed is high (8–9). Be honest; inflating everything to 10 makes the ranking useless, and deflating to protect a deadline is how people get hurt.
5. **Choose the fail-safe category (§2.2).** Person-impact → fail-stop (halt now). Write *why* — the actuator may be implicated, so no fail-safe-state.
6. **Name the mitigation and its owner.** "200 ms software E-stop + velocity clamp + hardware E-stop," owned by `safety_wrapper` / `/safety/estop`. Every mitigation cites a real component, or it is not a mitigation, it is a wish.
7. **Note what residual risk remains.** Even with the E-stop, a person who steps in within the stopping distance can be struck — that residual is what speed-and-separation monitoring (§2.7.1) and the hardware E-stop bound, and what the Week 41 residual-risk section argues is acceptable.

Do that for every row, and the hazard log stops being a list of worries and becomes an engineering artifact: each row is a hazard, ranked, with a category, an owned mitigation, and a stated residual. The discipline is the same for the arm hazards (strike, pinch, dropped load) — only the ISO framing (10218 for the arm) and the mitigations (workspace clamp, reduced shared-mode speed) change.

---

## 2.5 — The 200 ms software E-stop, in code

The capstone spec demands a `/safety/estop` topic with a **200 ms latch**: when it latches `true`, the robot stops within 200 milliseconds. You build and measure it this week so that by the time it is graded you have done it a dozen times. Three properties make it correct:

**It is latched at the QoS layer.** `/safety/estop` is `RELIABLE`/`TRANSIENT_LOCAL`/`KEEP_LAST(1)`. The durability is load-bearing: a controller node that subscribes *after* the E-stop was pressed must still receive the `true`. This is the "E-stop missed by a late-joining node" hazard, designed out by QoS — the exact Week 5 lesson, now with a severity of 9.

**It cancels actions directly, not only through the BT.** The behavior tree's `ReactiveFallback` (Lecture 1 §1.7) will halt the running motion leaf when it next ticks — but the tree's tick rate (say 10 Hz, 100 ms between ticks) is too slow to *guarantee* a 200 ms budget on its own, especially if a tick is mid-motion-leaf. So the safety node *also* holds the Nav2 and MoveIt2 action clients and calls `cancel_goal_async()` directly the instant the latch fires. Two paths to the same stop; you rely on the fast one for the budget and the BT one for clean state.

**It zeroes the command topic as a backstop.** Beyond canceling the actions, the safety node publishes a zero `Twist` on `/cmd_vel` (highest priority through `twist_mux`) so that even if an action cancel is slow to take effect, the base receives a stop command immediately.

```python
#!/usr/bin/env python3
"""Software E-stop monitor: on /safety/estop latch, cancel the Nav2 navigation
action and the MoveIt2 trajectory, and zero /cmd_vel. Measures latch->stop."""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
from control_msgs.action import FollowJointTrajectory


def estop_qos() -> QoSProfile:
    """Latched safety profile: a late-subscribing controller still sees the latch."""
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,   # the load-bearing line
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


class EStopMonitor(Node):
    def __init__(self) -> None:
        super().__init__("estop_monitor")
        self._nav_client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self._arm_client = ActionClient(
            self, FollowJointTrajectory, "/arm_controller/follow_joint_trajectory")
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 1)
        self._latched = False
        self.create_subscription(Bool, "/safety/estop", self._on_estop, estop_qos())
        # A high-rate timer keeps zero-velocity asserted while latched.
        self.create_timer(0.02, self._assert_stop_if_latched)   # 50 Hz

    def _on_estop(self, msg: Bool) -> None:
        if msg.data and not self._latched:
            self._latched = True
            t_latch = self.get_clock().now()
            self.get_logger().error("E-STOP LATCHED — canceling all motion")
            # Fast path: cancel both actions directly (do not wait for the BT tick).
            self._nav_client._cancel_goal_async  # held client; cancel current goals
            self._cancel_all()
            self._cmd_pub.publish(Twist())       # zero velocity immediately
            dt_ms = (self.get_clock().now() - t_latch).nanoseconds * 1e-6
            self.get_logger().error(f"cancel+zero dispatched in {dt_ms:.1f} ms")

    def _cancel_all(self) -> None:
        # cancel_goal_async on each client's tracked goal handles; in the full
        # node you keep the GoalHandle from send_goal and cancel it here.
        for client in (self._nav_client, self._arm_client):
            if client.server_is_ready():
                client._cancel_all_goals_async() if hasattr(
                    client, "_cancel_all_goals_async") else None

    def _assert_stop_if_latched(self) -> None:
        if self._latched:
            self._cmd_pub.publish(Twist())   # keep asserting zero while latched
```

The skeleton elides the goal-handle bookkeeping (you keep the `GoalHandle` returned by `send_goal_async` and call `cancel_goal_async` on it — Exercise 3 fills this in correctly). The shape is what matters: latch → cancel both actions directly → zero `/cmd_vel` → keep asserting zero. The fast path does not wait for the behavior tree.

---

## 2.6 — Measuring the latch, because "it stopped" is not a measurement

A fail-safe is a *measured latency*, not a claim. The measurement is precise: from the timestamp the latch is published to the first moment the robot is fully stopped (zero `/cmd_vel` *and* the arm trajectory canceled). You measure it, you report the distribution over several trials, and you assert the p95 (or the max, for a safety number) is under 200 ms.

```python
# measure_estop_latency.py (shape) — latch the E-stop, time to full stop.
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist


class EStopLatency(Node):
    def __init__(self):
        super().__init__("estop_latency")
        self._pub = self.create_publisher(Bool, "/safety/estop", estop_qos())
        self._t_latch = None
        self._stopped_at = None
        self.create_subscription(Twist, "/cmd_vel", self._on_cmd, 10)

    def fire(self):
        self._t_latch = self.get_clock().now()
        self._pub.publish(Bool(data=True))

    def _on_cmd(self, msg: Twist):
        # First zero-velocity command after the latch marks the base stop.
        is_zero = (msg.linear.x == 0.0 and msg.angular.z == 0.0)
        if self._t_latch and is_zero and self._stopped_at is None:
            self._stopped_at = self.get_clock().now()
            dt_ms = (self._stopped_at - self._t_latch).nanoseconds * 1e-6
            self.get_logger().info(f"latch->stop = {dt_ms:.1f} ms (budget 200)")
```

Run it while the robot is driving — the latency you care about is the latency *during motion*, not from a standstill — and run it ten times, because a single trial hides the tail. The challenge this week is exactly this: drive the composed robot, latch mid-motion, ten trials, report the distribution. A senior engineer reports "p95 = 74 ms, max = 91 ms over 10 trials, here is the script"; a junior reports "it stops fast." Measure under load, too (the stretch goal): a machine busy with perception-shaped CPU burn is where a 70 ms stop quietly becomes a 210 ms stop, and the budget you must meet is the one under realistic load.

### 2.6.1 — Where the 200 ms goes: a latency budget for the stop

The 200 ms is not one delay; it is a *budget* spent across a chain of hops, and knowing where it goes tells you where to look when it blows. The chain, from the latch to the robot actually stopped:

- **Publish + transport.** The latch is published and crosses DDS to the safety node. On a healthy local graph this is sub-millisecond, but a `BEST_EFFORT` or congested topic can add tens of milliseconds — which is one more reason the E-stop is `RELIABLE`/`TRANSIENT_LOCAL` and high-priority.
- **Detection.** The safety node's callback fires. If the node is under a single-threaded executor behind a slow callback, the latch waits its turn — which is why the safety node should be lean and ideally on its own executor/callback group (the Week 4 lesson).
- **Action cancel dispatch.** `cancel_goal_async` is sent to the Nav2 and arm action servers. Dispatch is fast; the server *acting* on the cancel is the variable part.
- **Actuator response.** The base's motor controller receives the zero `/cmd_vel` and the arm controller halts the trajectory. In sim this is near-instant; on hardware it includes the motor controller's own loop time and the mechanical deceleration.

The two hops that dominate and that you control are *detection* (keep the safety node lean and unblocked) and *actuator response* (which is partly physics). The budget discipline: measure not just the end-to-end number but, where you can, the *per-hop* contribution, so when the stop is slow you know whether it is a wedged callback (fix the executor) or a slow controller (fix the cancel path) rather than guessing. This is the same per-hop latency-budget thinking the capstone applies to perception — a whole-system latency requirement is met by accounting for each hop, not by hoping the sum is small.

### 2.6.2 — The E-stop must be tested as routinely as it is relied upon

A fail-safe that is never exercised rots silently. The QoS regresses in a refactor, a controller stops subscribing, a cancel handler breaks — and you find out the day you need it, near a person. The discipline that prevents this: the E-stop has an *automated test* that runs in CI and a *manual check* that runs before every session. The automated test is your `measure_estop_latency.py` in `--demo`-style form against synthetic action servers, asserting the latch cancels both and the latency is within budget — green on every push. The manual check is a thirty-second ritual at bring-up: latch the E-stop, confirm both halves stop, un-latch, confirm motion resumes. Aviation tests the controls before every flight regardless of how recently they worked; you test the E-stop before every run regardless of how recently it passed CI, because the cost of an untested stop is measured in injuries, not in minutes. An E-stop you have not exercised today is an E-stop you are *hoping* works — and hope is not a safety control.

---

## 2.7 — ISO 10218 and ISO 13482: framing a shared-space manipulator

Your robot is a hybrid: an industrial-style 6-DOF manipulator bolted to a mobile base that operates near people. That hybrid lives between two standards.

**ISO 10218** (parts 1 and 2; the 2025 revision is current) governs **industrial robots and robot systems** — the manipulator. It enumerates the manipulator hazards you wrote into your hazard log (collision, trapping/crushing, energy release) and the protective measures: safety-rated stops, speed and separation monitoring, hand-guiding, power-and-force limiting. The arm half of your robot answers to ISO 10218's framing: the workspace clamp, the reduced-speed shared mode, and the trajectory halt are the "power-and-force limiting" and "safety-rated stop" measures the standard describes.

**ISO 13482** governs **personal-care robots** — service robots operating in shared human environments, which is exactly your mobile base near people. It scopes mobile servant robots and enumerates hazards specific to *moving among people who cannot be fenced out*: collision with a person, instability/tipping, and the impossibility of the caged-cell assumption ISO 10218 makes for classic industrial arms. The base half of your robot answers to ISO 13482's framing: the 200 ms E-stop, the velocity clamp, and the perception confidence gate (Phase 4) are its protective measures.

You do not need to buy or read the standards' text this week — the summaries tell you the scope and the hazard categories, which is what a first hazard log needs. What you *do* need is the framing instinct: when you write a hazard-log row, ask "is this an arm hazard (ISO 10218) or a shared-space-base hazard (ISO 13482)?" and let the standard's hazard categories prompt you for the rows you forgot. The standards are checklists of hazards experts have already enumerated; using them as prompts is how you avoid the hazard you didn't think of — which is the one that hurts someone.

A note on honesty: framing *against* a standard is not the same as *certifying* to it. Certification is a formal, audited process with a notified body, far beyond a course. What you do this week — and in the Week 41 safety case — is *frame* your hazard analysis using the standards' structure and cite the relevant clauses. That is the right and honest claim: "this hazard analysis is structured against ISO 13482's hazard categories," not "this robot is ISO 13482 certified." A reviewer who knows the difference will respect the precise claim and distrust the inflated one.

### 2.7.1 — Speed and separation monitoring: the protective measure your robot can actually implement

ISO 10218 and the collaborative-robot technical specification (ISO/TS 15066) name four collaborative operating modes; the one your composed robot can implement in software is **speed and separation monitoring (SSM)**. The idea: the robot continuously knows the distance to the nearest person (from the LiDAR and the perception stack), and it modulates its speed as a function of that distance — full speed when nobody is near, reduced speed inside a warning zone, and a protective stop inside a critical zone. The critical-zone radius is not arbitrary; it is computed from the robot's stopping distance at its current speed plus the human's possible approach speed plus a sensor-uncertainty margin. That is why the 200 ms E-stop latency matters beyond a single number: a faster stop means a *smaller* required separation distance, which means the robot can work faster and closer to people while staying safe. Your hazard log's "base collides with a person" mitigation is, properly stated, an SSM mitigation: the velocity clamp scales with proximity, and the E-stop is the protective stop when proximity goes critical. You implement the full SSM curve in the capstone; this week you implement its two endpoints — full speed when clear, protective stop on E-stop — and you write the proximity-scaled middle as a hazard-log mitigation to build later.

### 2.7.2 — Why the safety layer is separate from the controller

A recurring junior instinct is to put the safety logic *inside* the controller — "I'll just clamp the velocity in the PID node." Resist it, and understand why, because it is a real architectural principle. The safety layer must be **separate from and independent of** the thing it is guarding, for the same reason the hardware E-stop is independent of the software: *a bug in the controller must not be able to disable the safety check.* If the velocity clamp lives inside the PID node and the PID node wedges, the clamp wedges with it — the guard and the guarded fail together. So the safety wrapper is its own node, subscribing to the controller's output, clamping it, and republishing the clamped command (the `twist_mux` pattern from Lecture 1, with the safety node as the highest-priority input). The controller proposes; the independent safety node disposes. This separation is also what lets the safety node have a *simpler, more auditable* codebase than the controller it guards — a small, boring, well-tested node is a better leash than clamp logic buried in a complex controller, because you can actually reason about whether the small node is correct. The general principle, which the capstone safety case leans on: the higher the integrity required of a function, the simpler and more isolated it should be. A 200 ms E-stop that is fifty lines of audited code in its own node is trustworthy; a 200 ms E-stop tangled into a thousand-line MPC is not.

---

## 2.8 — How the pieces compose into the milestone

The hazard log, the fail-safe categories, and the E-stop are not independent — they compose into the safety stance the milestone is graded on:

- The **hazard log** identifies *what* can go wrong and *how severe*; it ranks where your safety effort goes.
- The **fail-safe categories** decide, per hazard, *what the robot does* when it goes wrong (stop, move-to-safe, degrade).
- The **software E-stop** is the *mechanism* that implements fail-stop for the highest-severity hazards, measured against the 200 ms budget.
- The **hardware E-stop** (documented) covers the residual: the failures that take the software with them.
- The **pre-flight check** (Lecture 1) verifies the *preconditions* the safety stance assumes — the safety wrapper is active, the E-stop topic is present and latched, the frames are valid — so a failed pre-flight is itself a safety-relevant abort.

This is why you build them in the same week as the composition. Composing the body without the leash is a robot that can move near a person with no documented stop — exactly the thing the milestone exists to prevent. The mini-project runs the composed drive-reach-return once, cleanly, with the E-stop armed and measured, and the hazard log written. That is the Phase 3 milestone: the controller stack signed off, and the first hazard log signed off.

---

## 2.8.5 — Quick reference: the safety vocabulary

Keep these answers crisp; a safety review asks them directly.

**Q: What is risk?**
Severity × probability of occurrence. Both factors; a hazard near a person who cannot avoid it ranks higher.

**Q: Name the three fail-safe categories.**
Fail-stop (halt and stay halted), fail-safe-state (move to a defined safe configuration, then halt), fail-operational (degrade but keep going).

**Q: When is fail-safe-state forbidden?**
When the actuator is suspect (a runaway controller). You do not ask a suspect actuator to perform a careful final motion.

**Q: Software E-stop vs. hardware E-stop?**
Software: fast, integrated, but part of the software that may have failed. Hardware: independent of software, works when the software is the failure. A deployable robot has both.

**Q: What QoS does the E-stop topic use, and why?**
`RELIABLE` / `TRANSIENT_LOCAL` / `KEEP_LAST(1)`. So a node that subscribes after the latch still receives `true`. A best-effort E-stop a late subscriber misses is a severity-9 hazard.

**Q: What are the IEC 60204-1 stop categories?**
0 = immediate power removal (uncontrolled coast). 1 = controlled stop, then power removal. 2 = controlled stop, power retained (a pause).

**Q: Which category is your software E-stop? Your hardware E-stop?**
Software ≈ category 1 (controlled, then ceases). Hardware ≈ category 0 (cut power).

**Q: How do you report E-stop latency?**
Mid-motion, both halves, ten trials, the slower half, under load. "p95 = 74 ms, max = 91 ms, here is the script" — never "it stops fast."

**Q: ISO 10218 vs. ISO 13482?**
10218 = industrial manipulators (your arm). 13482 = personal-care robots in shared space (your mobile base near people).

**Q: Certified or framed?**
Framed. You structure your hazard analysis against the standards' categories and cite clauses; you do not certify (an audited process beyond a course).

## 2.9 — Recap

You should now be able to:

- State risk as severity × probability, and explain why a hazard near a person who cannot avoid it ranks higher than the same hazard in a cage.
- Name the three fail-safe categories — fail-stop, fail-safe-state, fail-operational — and choose the right one per hazard (and explain why a suspect actuator forbids fail-safe-state).
- Distinguish the software E-stop (fast, integrated, but part of the software that may have failed) from the hardware E-stop (independent of software, works when the software is the failure), and explain why a deployable robot has both.
- Author a hazard log keyed on your controllers' known failure modes, with the QoS-durability E-stop hazard included, and every mitigation citing an owning node/topic.
- Implement a `RELIABLE`/`TRANSIENT_LOCAL` software E-stop that cancels the Nav2 action and the MoveIt2 trajectory and zeroes `/cmd_vel`, and *measure* the latch-to-stop latency against a 200 ms budget with a runnable harness.
- Frame the arm against ISO 10218 and the shared-space base against ISO 13482, using the standards' hazard categories as prompts, and make the honest "framed against," not "certified to," claim.

## 2.10 — Common safety anti-patterns to avoid

A handful of mistakes recur across every cohort and every junior safety review. Name them so you don't make them:

- **The E-stop that depends on the thing it guards.** Putting the clamp inside the controller, or the E-stop logic inside the executor that might wedge. The guard must outlive the guarded (§2.7.2). Independent node, simple code, its own callback group.
- **The best-effort safety topic.** A `/safety/estop` on a `VOLATILE` or `BEST_EFFORT` profile, so a late subscriber or a dropped packet misses the latch. A safety topic is `RELIABLE`/`TRANSIENT_LOCAL`, always. This is the severity-9 hazard-log row, and it is the most common QoS mistake on a safety topic.
- **The unmeasured fail-safe.** "It stops when I press the button" with no number. A fail-safe you have not measured is a hope. Measure it, mid-motion, ten trials, under load, both halves.
- **The deep command queue.** A `KEEP_LAST(50)` on `/cmd_vel`, so stale velocity commands drain into the motors after a hiccup — "the robot kept driving after I let go." Commands are `KEEP_LAST(1)` (the Week 5 lesson, now a safety issue).
- **The undocumented mitigation.** A working clamp that appears nowhere in the hazard log, so the safety review can't see it and can't credit it. A mitigation that isn't written down doesn't discharge the hazard, because the panel grades the *case*, not just the behavior.
- **The fail-safe-state on a suspect actuator.** Asking a runaway controller to perform a careful retraction. If the actuator is suspect, fail-stop — do not trust the suspect component to execute a graceful motion.
- **Certifying when you mean framing.** Claiming "ISO 13482 compliant" when you have only *framed* your analysis against it. The precise claim earns trust; the inflated one earns a skeptical reviewer who now doubts everything else.

Each anti-pattern maps to a lecture section and a hazard-log row. The cure for all of them is the same posture: treat safety as half engineering and half evidence, write down every hazard and every mitigation with an owner, and measure every fail-safe you rely on. A robot that is "probably safe" is a robot whose safety nobody has actually checked.

You have composed the robot and put a measured leash on it. The exercises stand it up; the mini-project runs it once and signs the milestone. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *ISO 12100:2010 — Safety of machinery, risk assessment* (summary): <https://www.iso.org/standard/51528.html>
- *ISO 10218-1:2025 — Industrial robots, safety* (summary): <https://www.iso.org/standard/73101.html>
- *ISO 13482:2014 — Personal care robots* (summary): <https://www.iso.org/standard/53820.html>
- *IEC 60204-1 — Electrical equipment of machines, E-stop function and stop categories*: <https://webstore.iec.ch/publication/64761>
- *NASA Software Safety Guidebook (hazard analysis, FDIR)*: <https://standards.nasa.gov/standard/NASA/NASA-GB-871913>
- *MIL-STD-1629A — FMEA procedure* (S/O/D, RPN): search "MIL-STD-1629A FMEA"
- *About Quality of Service settings* (durability for latched safety topics): <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
