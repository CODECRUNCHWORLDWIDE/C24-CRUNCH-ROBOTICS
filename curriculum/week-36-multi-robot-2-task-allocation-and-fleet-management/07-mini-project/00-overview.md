# Mini-Project — `crunch_fleet`: A Dispatcher That Reallocates a Dead Robot's Work

> Build a small, real fleet dispatcher for the crunchbot fleet: it allocates a batch of tasks across N robots with a cost-matrix solver, listens to each robot's `/fleet/heartbeat`, **detects a stalled robot from its heartbeat going stale**, and **reallocates the orphaned tasks** to the survivors — all observable on a status topic. Then run the reallocation drill the syllabus demands and *measure the recovery latency*.

This is the artifact that turns this week's two lectures into one runnable system. The allocation math from Lecture 1 (Hungarian + auction) becomes the assignment engine; the fleet-management and heartbeat lessons from Lecture 2 become the failure detector and the reallocation loop. After this week, "the fleet reallocated" is a line in your log with a number next to it (seconds-to-recover), not a hope.

**Estimated time:** ~9 hours, split across Thursday, Friday, Saturday, and Sunday in the suggested schedule.

**Compounds forward:** The heartbeat schema and the reallocation loop you build here become the **`/fleet/heartbeat` substrate the capstone requires** (the syllabus capstone property #7: "reports identity, capabilities, and health on a `/fleet/heartbeat` topic at 1 Hz, conformant to a documented schema"). One half of the Week 46 chaos drill — a robot dies mid-task and the fleet must recover with an operator-detectable event in under 60 s — is *exactly this dispatcher's reallocation event*. Build it well now; you'll defend it in the capstone.

---

## What you will build

A small ament-python package `crunch_fleet` with three deliverables:

1. **`crunch_fleet/dispatcher.py`** — the dispatcher node. Subscribes to `/fleet/heartbeat` from every robot, maintains a live model of the fleet (who's alive, where, what they're doing), allocates a task batch with a cost-matrix solver, detects staleness, and re-bids orphaned tasks. Publishes a `/fleet/status` summary.
2. **`crunch_fleet/robot_sim.py`** — a simulated robot node that publishes `/fleet/heartbeat` at 1 Hz with the documented schema, accepts a task assignment, "executes" it (a timer that advances toward the goal), and can be told to **stall** (stop heartbeating, or heartbeat with `nav_state=ERROR`) to drive the drill.
3. **A reallocation drill** (`launch/drill.launch.py` + a short script) that brings up the dispatcher and three robot sims, submits five tasks, then kills one robot mid-task and **measures the seconds from stall to reassignment**.

By the end you have a public repo of ~300–400 lines of Python (excluding tests) that demonstrates an end-to-end fleet: allocation, health monitoring, and autonomous recovery — the portfolio centerpiece of the multi-robot phase.

---

## Why a heartbeat-driven detector and not a poll

You could have the dispatcher poll each robot with a service call ("are you alive?"). Don't. A heartbeat the robot *pushes* is better because:

- **It catches a wedged-but-alive robot.** A robot whose process is up but whose control loop deadlocked still answers a liveness *service* (the service handler runs on a different thread) but stops *publishing* a heartbeat (the publish call is in the wedged loop). The push model fails closed; the poll model fails open. This is the Week 5 §3.6 `MANUAL_BY_TOPIC` liveliness lesson, applied.
- **It scales.** N robots pushing 1 Hz is N messages/second; the dispatcher polling N robots is N round-trips it has to schedule and time out individually.
- **It's the capstone schema.** The capstone *requires* a heartbeat topic, so you build the right thing once.

The detector is therefore: subscribe to `/fleet/heartbeat`, record each robot's last-seen time, and on every dispatcher tick flag any robot whose last heartbeat is older than the lease (e.g., 2× the 1 s period = 2 s). Optionally also register the QoS `deadline`/`liveliness` event callbacks (Week 5) for a second, middleware-level signal.

---

## Package layout

```
crunch_fleet/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_fleet
├── crunch_fleet/
│   ├── __init__.py
│   ├── allocation.py        # cost matrix + Hungarian + SSI re-auction (from the exercises)
│   ├── dispatcher.py        # the dispatcher node (the heart of the project)
│   ├── robot_sim.py         # a simulated robot that heartbeats and can stall
│   └── schema.py            # the heartbeat schema + QoS profile (one source of truth)
├── launch/
│   └── drill.launch.py      # dispatcher + 3 robot sims + task submission
└── test/
    ├── test_allocation.py   # Hungarian optimal; SSI coherence; reallocation correctness
    └── test_staleness.py    # the staleness detector flags a robot past its lease
```

If you have a `crunch_fleet_msgs` interfaces package, define the heartbeat as a real `.msg` (Lecture 2 §5.1) and use it. If you'd rather not build an interfaces package this week, a `std_msgs/String` carrying JSON is acceptable — but document the schema in `schema.py` and validate it on receive. The real `.msg` is the better artifact for the capstone.

---

## Deliverable 1 — the heartbeat schema (`schema.py`)

Define the heartbeat once. Fields (Lecture 2 §5.1): `robot_id`, `fleet_id`, `capabilities` (list), `battery_percent`, `nav_state` (IDLE/MOVING/PAUSED/ERROR), `current_task_id`, `location` (x, y, yaw), and a send-time stamp. Also define, in one place, the **heartbeat QoS** and justify it in a docstring:

```python
# crunch_fleet/schema.py — the heartbeat schema + its QoS, in ONE place.
from rclpy.duration import Duration
from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, LivelinessPolicy,
    QoSProfile, ReliabilityPolicy,
)

HEARTBEAT_TOPIC = "/fleet/heartbeat"
HEARTBEAT_PERIOD_S = 1.0
HEARTBEAT_LEASE_S = 2.0     # 2x period: miss two and you're stale.


def heartbeat_qos() -> QoSProfile:
    """A heartbeat exists to DETECT a dead publisher, so:
      - RELIABLE: don't false-alarm on a dropped UDP packet.
      - TRANSIENT_LOCAL depth 1: a late-joining dispatcher sees current state.
      - MANUAL_BY_TOPIC liveliness: catches a wedged-but-alive robot (Week 5 §3.6).
      - deadline ~2x period: a second, middleware-level staleness signal.
    """
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
        liveliness=LivelinessPolicy.MANUAL_BY_TOPIC,
        liveliness_lease_duration=Duration(seconds=int(HEARTBEAT_LEASE_S)),
        deadline=Duration(seconds=int(HEARTBEAT_LEASE_S)),
    )
```

> **The QoS is graded.** If you set the heartbeat to `BEST_EFFORT` or leave liveliness `AUTOMATIC`, you've reproduced the exact bug Week 5 warned about — a wedged robot reported healthy. Get this right and write the one-paragraph justification.

---

## Deliverable 2 — the dispatcher (`dispatcher.py`)

A node that:

1. Subscribes to `/fleet/heartbeat` with `heartbeat_qos()`. On each message, update a `robots[robot_id]` record (location, capabilities, battery, nav_state, **last_seen** = now).
2. Accepts a **task batch** (read from a parameter, a file, or a `/fleet/submit_task` topic). Each task has a location and a required capability.
3. **Allocates** the batch: build the cost matrix (distance from each *capable* robot's current location to each task; ∞ if the robot lacks the capability or battery is too low), solve with the Hungarian allocator from `allocation.py`. Publish each assignment to the assigned robot (`/<robot_id>/assignment`).
4. On a fixed timer (e.g., 0.5 s), run the **staleness check**: any robot with `now - last_seen > HEARTBEAT_LEASE_S` (or `nav_state == ERROR`) is declared **stalled**. Print the stale event with the actual age.
5. **Reallocate:** the stalled robot's not-yet-completed, not-yet-started tasks are re-bid (single-item auction / re-solve over survivors). Started tasks are **flagged**, not silently re-auctioned (Lecture 2 §4.3). Print `ORPHANED` then `RE-ASSIGNED` with the new owner.
6. Publish a `/fleet/status` summary (robots alive, tasks queued/assigned/done, last reallocation latency) at 1 Hz.

The reallocation latency — **seconds from stall-detected to task-reassigned** — is the headline metric. Log it.

---

## Deliverable 3 — the robot sim + the drill

`robot_sim.py` is a node parameterized by `robot_id` that:

- Publishes `/fleet/heartbeat` at 1 Hz with `heartbeat_qos()` and the schema.
- Subscribes to `/<robot_id>/assignment`; on assignment, sets `nav_state=MOVING`, `current_task_id`, and runs a timer that linearly advances `location` toward the task; on arrival, sets the task complete and goes `IDLE`.
- Accepts a `~stall` parameter / a `/<robot_id>/stall` trigger that makes it **stop publishing heartbeats** (simulating process death/comms loss) or publish `nav_state=ERROR` (simulating a wedge) — your choice; do both for full marks.

The drill (`launch/drill.launch.py` + script): bring up the dispatcher and **three** robot sims, submit **five** tasks (matching the syllabus lab: "submit five delivery tasks"), let allocation settle, then **stall one robot mid-task** and capture the reallocation. The drill prints a verdict:

```
[drill] 5 tasks submitted, allocated across robot1/robot2/robot3
[drill] all robots heartbeating; allocation stable
[drill] STALLING robot2 at t=8.0s (had task delivery_3 underway)
[dispatcher] robot2 heartbeat STALE (age 2.1s > 2.0s lease)
[dispatcher] task delivery_3 ORPHANED — re-bidding among {robot1, robot3}
[dispatcher] task delivery_3 RE-ASSIGNED to robot1 (bid 4.2 < robot3 bid 6.8)
[drill] RECOVERY LATENCY: 2.4s  ->  PASS (< 60s capstone bound)
```

---

## Rules

- **You may** use `numpy`, `scipy` (for the Hungarian solver), and the ROS2 Jazzy desktop install. Reuse the `allocate_hungarian` / `auction_one` functions from the exercises.
- **You must not** detect failure by polling a service — the detector must be heartbeat-staleness-driven (the whole point, per "why a heartbeat" above).
- **You must not** reallocate a task marked `started` without flagging it; silently re-auctioning a half-done task is the unsafe behavior Lecture 2 §4.3 warns against.
- Python 3.12 (Ubuntu 24.04 default), `rclpy` on Jazzy.
- The drill must **measure and print** the recovery latency and assert it's under the 60 s capstone bound.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-36-crunch-fleet-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_fleet` succeeds with no warnings.
- [ ] `schema.py` defines the heartbeat fields and `heartbeat_qos()` with `RELIABLE` + `TRANSIENT_LOCAL` + `MANUAL_BY_TOPIC` liveliness, plus a docstring justifying each choice.
- [ ] `dispatcher.py` allocates a five-task batch across three robots using the Hungarian solver, respecting capability/battery (∞ cost for infeasible pairs).
- [ ] Stalling one robot mid-task produces an `ORPHANED` → `RE-ASSIGNED` sequence in the dispatcher log; the orphaned task lands on a healthy robot.
- [ ] A *started* task on the stalled robot is **flagged**, not silently re-auctioned.
- [ ] `launch/drill.launch.py` runs the full drill end-to-end and prints the recovery latency and a PASS/FAIL against the 60 s bound.
- [ ] `colcon test --packages-select crunch_fleet` passes, with at least:
  - `test_allocation.py`: Hungarian returns the optimal assignment on a known matrix; SSI builds coherent routes; reallocation moves only un-started tasks.
  - `test_staleness.py`: a robot whose last_seen is older than the lease is flagged; one within the lease is not.
- [ ] A `README.md` in the repo root with the heartbeat schema, the QoS justification, the run commands, and a recorded drill trace with the measured latency.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Allocation correctness** | 20 | Cost matrix is honest (∞ for infeasible); Hungarian optimal; capability/battery respected. |
| **Heartbeat + QoS** | 20 | Schema complete; QoS is RELIABLE/TRANSIENT_LOCAL/MANUAL_BY_TOPIC with a justification that names the wedged-robot failure mode. |
| **Staleness detection** | 20 | Heartbeat-driven, not polled; lease-based; catches both no-heartbeat and `nav_state=ERROR`; tested. |
| **Reallocation** | 20 | Orphaned un-started tasks re-bid to survivors; started tasks flagged not re-auctioned; latency measured and bounded. |
| **Drill + tests** | 15 | The end-to-end drill runs, kills a robot, recovers, prints latency; `colcon test` green. |
| **Docs & hygiene** | 5 | Clear README with a recorded trace; sensible commits; no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to feed the capstone's `/fleet/heartbeat`. **70–89** works but has a soft detector or a missing flag-don't-reallocate rule. **Below 70** means the failure handling isn't real — fix the detector and the started-task rule first.

---

## Stretch goals

- **Open-RMF integration.** Instead of (or alongside) the sim robots, wire your dispatcher's tasks into the real `rmf_demos` fleet via the API server, and read RMF's `/fleet_states` as your heartbeat source. Now your allocation runs on a production fleet manager.
- **Battery-aware bidding.** Make a robot's bid penalize low battery so the dispatcher naturally routes a near-empty robot to a charger task and keeps it out of long deliveries. Show a robot pulling itself out of bidding as it drains.
- **Foxglove panel.** Publish `/fleet/status` in a shape a Foxglove panel can render — a row per robot that goes red on stale. A direct preview of the Week 43 operator dashboard.
- **Vendor sweep.** Run the whole drill under both `rmw_fastrtps_cpp` and `rmw_cyclonedds_cpp` and confirm the heartbeat QoS (especially the liveliness lease) behaves identically — proving your detector is vendor-portable (Week 5 lesson).

---

## How this connects to the rest of C24

- **Week 37 (VLMs for robotics)** turns a plain-English instruction into a task; *this dispatcher* is what that task gets submitted to. The heartbeat's `capabilities` field is how a language-conditioned task ("pick up the tool") gets routed only to a robot with an arm.
- **Week 40 (Phase 5 milestone)** you defend multi-robot coordination; this drill *is* that defense, with a measured recovery latency.
- **Week 46 (chaos drill)** the "robot dies mid-task" drill is this reallocation, run on the capstone robot, graded live with the 60 s bound. You built and measured it four weeks early. Push it, keep the repo, reuse the heartbeat schema in the capstone.

## A closing note on what makes this portfolio-grade

The line between a toy fleet manager and a real one is the *failure handling*, not the allocation. Anyone can write `linear_sum_assignment` over a cost matrix; the engineering judgment a reviewer (and an interviewer) looks for is: does it detect a dead robot from a *pushed* heartbeat (not a poll)? does it catch a *wedged-but-alive* robot, not just a silent one? does it refuse to silently re-auction a *started* task that may have left the world in a bad state? does it *measure* the recovery latency and bound it? Those four questions are the difference between "I ran the allocation example" and "I built a fleet manager that survives a robot dying." Spend your time there — the allocation is the easy 20%, the robust failure handling is the 80% that makes this the centerpiece of your multi-robot story and the substrate of the capstone's `/fleet/heartbeat`.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
