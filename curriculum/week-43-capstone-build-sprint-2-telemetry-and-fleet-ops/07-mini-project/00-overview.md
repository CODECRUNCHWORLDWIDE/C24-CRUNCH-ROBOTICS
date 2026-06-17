# Mini-Project — The Capstone Operator Dashboard, Teleop Takeover, and OTA Procedure

> Build the production-operations layer of your capstone robot. By the end you have: a Foxglove **operator dashboard** streaming pose, costmap, policy actions, safety triggers, and CPU/GPU load; a **one-click teleop-takeover** with a provably clean transition; a documented, never-brick **OTA-update procedure**; and a published, documented **`/fleet/heartbeat`** schema. The dashboard recording is a **required week-48 deliverable** and the heartbeat schema is wired here so you never have to redesign it during defense week.

This is the week your capstone stops being a robot only you can run and becomes a robot an operator who is not you can *watch* and *rescue*. That is the entire job of a fleet-ops engineer, and it is graded twice: the dashboard recording is week-48 deliverable #6, and the heartbeat + telemetry are how you survive the week-46 chaos drill. Everything you build here compounds directly into those two graded events. Do not treat it as a side quest.

**Estimated time:** ~11.5 hours (split across Thursday, Friday, Saturday in the suggested schedule).

**This compounds on:** Week 41 (the safety case — its mitigations are the safety filter you visualize and keep in the loop under teleop), Week 42 (the hardened deployment you instrument), Week 18 (the Nav2 costmap you stream), and Week 32 (the policy whose actions you render). It feeds forward into Week 46 (the chaos drill you watch on this dashboard) and Week 48 (the dashboard recording and the OTA/heartbeat deliverables you defend).

---

## What you will build

One ROS2 Jazzy package set, on top of your existing capstone workspace, comprising:

1. **`capstone_msgs`** — the custom interface package with three messages: `SafetyTrigger.msg`, `PolicyAction.msg` (if not already from Week 32), and `Heartbeat.msg` (the `/fleet/heartbeat` schema from Lecture 2 §5).
2. **`capstone_ops`** — the operations nodes:
   - `metrics_node.py` — the Prometheus `/metrics` endpoint (Lecture 1 §2).
   - `load_panel_node.py` — the CPU/GPU/thermal `DiagnosticArray` publisher (exercise 2).
   - `action_marker_node.py` — the policy-action-to-Marker adapter (exercise 1).
   - `heartbeat_node.py` — the 1 Hz `/fleet/heartbeat` publisher.
   - `control_arbiter.py` — the lifecycle control-authority arbiter (exercise 3).
   - `tracing.py` — the OpenTelemetry init helper wired into your autonomy pipeline (Lecture 1 §3).
3. **`autonomy_has_authority`** — the BT.CPP condition node (C++) that makes autonomy yield (Lecture 2 §4.4), registered into your capstone behavior tree.
4. **`dashboard/capstone_layout.json`** — the exported Foxglove layout, version-controlled.
5. **`ota/`** — the documented OTA procedure: `ota-apply.sh`, `health_gate.py`, and `OTA-PROCEDURE.md`.
6. **`docs/heartbeat-schema.md`** — the documented `/fleet/heartbeat` schema (the capstone artifact).

You ship this as part of your capstone repo, not a standalone project — these nodes run alongside your autonomy stack.

---

## Rules

- **You may** read all of the resources, the lecture notes, your exercises, the Foxglove/Prometheus/OTel/Open-RMF docs, and the `twist_mux` / Open-RMF source.
- **You may NOT** replace your safety filter with a stub to make the dashboard look calmer. The safety triggers on the dashboard must be *real* — driven by your Week 41 safety case mitigations. A dashboard that never goes red because the filter is fake is an automatic fail.
- **You may NOT** bypass the arbiter by having teleop publish directly to the base. The arbiter must be the *only* publisher to `/cmd_vel_out`. The two-publisher race must be structurally impossible, not merely unlikely.
- Target ROS2 **Jazzy** on Ubuntu **24.04**. Python **3.12**, `rclpy`. The one C++ node uses BehaviorTree.CPP v4 and `rclcpp`.
- The whole package set must `colcon build` with **zero warnings** and pass `ros2 doctor` with no new errors.
- Prometheus label cardinality stays low — no per-task or per-goal labels. (Lecture 1 §2.2 explains why.)

---

## Acceptance criteria

The grading rubric is below. Each box maps to a specific deliverable.

### The dashboard (35%)

- [ ] Foxglove connects to your robot through `foxglove_bridge` over WebSocket.
- [ ] The dashboard streams, live and simultaneously: **pose** (map frame), **costmap** (Nav2 `OccupancyGrid`), **policy action** (Marker arrow), **safety triggers** (latched Indicator banner), and **CPU/GPU/thermal load** (Gauge + Indicator from `/diagnostics`).
- [ ] The policy-action arrow **recolors** when the safety filter overrides, in lockstep with the banner.
- [ ] A **cycle-latency plot** (`/perf/cycle_latency`) is on the layout.
- [ ] `dashboard/capstone_layout.json` is exported and committed; a fresh clone + import reproduces the exact view.
- [ ] You produce a **3-minute MCAP recording** of a real task execution that includes at least one safety-filter trigger and one teleop takeover, and it replays cleanly when scrubbed. *(This is week-48 deliverable #6 — bank it now.)*

### The teleop takeover (25%)

- [ ] The `control_arbiter` is a **lifecycle node**, owns `/cmd_vel_out`, and forwards exactly one of `/cmd_vel_auto` / `/cmd_vel_teleop` per the latched authority.
- [ ] A one-click `/control/takeover` Bool flips authority **atomically** with a one-cycle safe-stop on every transition.
- [ ] The `autonomy_has_authority` BT.CPP condition halts the navigation subtree cleanly (cancels the Nav2 goal) when authority is not AUTONOMY.
- [ ] The teleop-link **watchdog** safe-stops the robot if `/cmd_vel_teleop` goes silent under TELEOP authority.
- [ ] The **dashboard banner** shows AUTONOMY/TELEOP and changes the instant a flip happens.
- [ ] Challenge 1's `check_takeover.py` passes on a recorded run. (The challenge and the mini-project share this evidence.)

### Telemetry plumbing (20%)

- [ ] `metrics_node.py` exposes a Prometheus `/metrics` endpoint with a cycle-latency **histogram**, CPU/GPU **gauges**, and a safety-trigger **counter**.
- [ ] A local Prometheus scrapes it (`prometheus.yml` committed), and the `RobotUnreachable` + `CycleBudgetBlown` alert rules from Lecture 1 §2.3 are present.
- [ ] OpenTelemetry tracing produces **one trace per task** with a span per pipeline stage, exportable to a local OTLP collector. Include one exported trace (screenshot or JSON) showing the per-stage spans.
- [ ] `heartbeat_node.py` publishes `/fleet/heartbeat` at **1 Hz** conformant to the documented schema; a consumer (or Prometheus) detects staleness when you kill the node.

### OTA + documentation (20%)

- [ ] `ota/OTA-PROCEDURE.md` documents a never-brick update for your capstone (A/B-partition on Path A, container-swap on Path B), honoring the **five never-brick rules** from Lecture 2 §3.
- [ ] `ota/ota-apply.sh` (or the RAUC/Mender config equivalent) implements update-to-inactive → trial → health-gate → auto-rollback.
- [ ] `ota/health_gate.py` reuses `/fleet/heartbeat` to decide promote-vs-rollback.
- [ ] `docs/heartbeat-schema.md` documents every field of `Heartbeat.msg`, its units, its source, and its Open-RMF analogue. *(This is a capstone artifact; week 48 checks it.)*
- [ ] A top-level `OPS-README.md` explains how to bring up the whole ops layer in order (bridge, metrics, heartbeat, arbiter) and how to import the layout.

---

## Suggested implementation outline

The order matters: get the dashboard streaming before you wire the takeover, because you need the banner to *see* the takeover work.

### Day 1 (Thursday — ~3.5 hours)

1. **Define `capstone_msgs`.** Create `SafetyTrigger.msg`, `PolicyAction.msg`, and `Heartbeat.msg` (copy the schema from Lecture 2 §5). `colcon build --packages-select capstone_msgs`. Confirm with `ros2 interface show capstone_msgs/msg/Heartbeat`.
2. **Stand up the bridge and the basic 3D panel.** Run `foxglove_bridge`, connect, get pose + costmap rendering in the `map` frame (exercise 1 steps 1–2). This is your foundation; everything else hangs off the live connection.
3. **Wire the metrics node and Prometheus.** Run `metrics_node.py`, point a local Prometheus at it, confirm `up == 1` and that `capstone_cycle_latency_seconds` appears in the expression browser. Add the two alert rules.

### Day 2 (Friday — ~4 hours)

4. **The action marker + safety banner.** Finish exercise 1: render the policy action, publish the latched `/safety/trigger`, add the Indicator, and prove the arrow recolors on override.
5. **The CPU/GPU panel.** Run exercise 2's `load_panel_node.py`, add the Gauge panels, confirm the thermal gauge moves when you load the box (`stress-ng --cpu 4` for a few seconds).
6. **The heartbeat node.** Write `heartbeat_node.py`: gather `software_version` (read the OTA image tag / a `VERSION` file), `control_authority` (subscribe `/control/authority`), `safety_active` (subscribe `/safety/trigger`), `battery_percent`, and `pose`. Publish at 1 Hz. Add a Foxglove Raw Messages panel on `/fleet/heartbeat` and confirm every field populates.
7. **Export the layout.** `dashboard/capstone_layout.json`, committed.

### Day 3 (Saturday — ~4 hours)

8. **The arbiter + BT condition.** Bring up `control_arbiter.py` (exercise 3), remap autonomy → `/cmd_vel_auto`, teleop → `/cmd_vel_teleop`, base → `/cmd_vel_out`. Build and register the `autonomy_has_authority` BT.CPP node into your tree. Run the full takeover cycle and watch the banner flip.
9. **The OTA procedure.** Write `OTA-PROCEDURE.md`, `ota-apply.sh`, and `health_gate.py`. Do a *dry run*: update to a trivially-changed image (bump the `VERSION` file), watch the health gate pass on the heartbeat, confirm a deliberately-broken image (one that crashes on boot) rolls back without bricking.
10. **The recording.** Record the 3-minute MCAP: a task execution with a real safety trigger and a clean teleop takeover. Scrub it. This is the week-48 deliverable; trim it with the `mcap` CLI and commit (or link if large).
11. **Documentation.** `docs/heartbeat-schema.md`, `OPS-README.md`. Run the challenge checker against your recording for the takeover-quality evidence.

---

## The `/fleet/heartbeat` schema — get it right now

This is the field you will most regret rushing, because week 48 grades it and Open-RMF integration depends on it. Document each field in `docs/heartbeat-schema.md` with:

| Field | Type | Units | Source | Open-RMF analogue |
|-------|------|-------|--------|-------------------|
| `robot_id` | string | — | launch param | `RobotState.name` |
| `software_version` | string | — | OTA image tag / `VERSION` | `RobotState.task_id` adjacent |
| `capabilities` | string[] | — | static config | fleet adapter config |
| `health` | uint8 enum | NOMINAL/DEGRADED/FAULT | diagnostics rollup | `RobotState.mode` |
| `control_authority` | string | AUTONOMY/TELEOP | arbiter `/control/authority` | `RobotMode` MODE_PAUSED |
| `safety_active` | bool | — | `/safety/trigger` | fleet adapter status |
| `battery_percent` | float32 | % | BMS / sim | `RobotState.battery_percent` |
| `pose` | Pose2D | m, rad | localization | `RobotState.location` |

The `health` rollup is the interesting one: it is not a single sensor, it is a function of your diagnostics. NOMINAL when all `DiagnosticStatus` levels are OK and no safety override; DEGRADED when something WARNs (high thermal, a single sensor flaky) but the robot can still do its job; FAULT when something ERRORs (a sensor dropped, the cycle blew budget hard) and the robot should be quarantined. Document the exact rule you implement — the week-48 panel asks you to defend it.

---

## What "done" looks like

When you bring up the ops layer, the recurring marker is live on your dashboard and your heartbeat:

```
[ops] heartbeat OK · authority=AUTONOMY · cycle p99=27ms · gpu=61% · thermal=58°C
```

Then you press takeover, and the operator watches it flip cleanly:

```
[ops] heartbeat OK · authority=TELEOP · cycle p99=27ms · gpu=58% · thermal=57°C
[control_arbiter]: control authority -> TELEOP (safe-stop one cycle)
```

and hand it back, and autonomy resumes from a fresh plan. If you can do that, record it, and prove it with the checker, you have the operations layer the capstone defense expects — and a dashboard recording already in the bank for week 48.

---

## Submission

Commit to your capstone repository (not a separate repo — these run with your stack):

- `capstone_msgs/` — the three message definitions.
- `capstone_ops/` — the ops nodes.
- `autonomy_has_authority/` — the BT.CPP condition node.
- `dashboard/capstone_layout.json` — the layout.
- `dashboard/takeover_run.mcap` — the 3-minute recording (or a link).
- `ota/` — `OTA-PROCEDURE.md`, `ota-apply.sh`, `health_gate.py`.
- `docs/heartbeat-schema.md` and `OPS-README.md`.

The instructor reviews by: importing your layout and connecting to your running robot (or replaying your MCAP), running the challenge checker, reading `OTA-PROCEDURE.md` against the five never-brick rules, and reading `heartbeat-schema.md` for Open-RMF alignment. The most common review-fail is a dashboard whose safety banner never fires because the filter was stubbed — keep it real.

---

**References**

- Foxglove docs: <https://docs.foxglove.dev/docs>
- `foxglove_bridge`: <https://github.com/foxglove/ros-foxglove-bridge>
- Prometheus instrumentation: <https://prometheus.io/docs/practices/instrumentation/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/languages/python/getting-started/>
- ROS2 Jazzy lifecycle nodes: <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Node-Lifecycle.html>
- Open-RMF `rmf_fleet_msgs`: <https://github.com/open-rmf/rmf_internal_msgs>
- RAUC (A/B updates): <https://rauc.readthedocs.io/> · Mender: <https://docs.mender.io/>
