# Week 43 — Capstone Build Sprint 2: Telemetry and Fleet Ops

Welcome to **C24 · Crunch Robotics**, Week 43. Week 41 gave your capstone robot a signed safety case. Week 42 moved it onto hardware (Path A) or hardened the sim deployment (Path B) and proved a clean cold-boot. This week we make the robot **observable and operable** — the production-operations layer of the capstone. By Friday you should be able to push robot telemetry into a Foxglove dashboard that streams pose, costmap, the policy's chosen actions, and every safety-filter trigger; add a CPU/GPU load panel that tells you when the Orin is thermally throttling before the perception cycle blows its budget; wire a one-click "remote teleop takeover" button that pauses autonomy, hands control to a human, and cleanly returns it; and write an OTA-update procedure that does not brick the robot.

This is the week the capstone stops being "a robot that runs on my desk" and becomes "a robot an operator who is not me can watch and rescue." That distinction is the entire job of a fleet-ops engineer. A robot you cannot see is a robot you cannot trust in a shared space, and a robot you cannot take over is a robot that will eventually wedge itself against a doorframe at 2 a.m. while you are asleep. Week 46's chaos drill will kill your LiDAR mid-task and deadlock your planner at a doorway, and the **only** way you pass that gameday is if the events you need to react to are already visible on a dashboard and the takeover you need to perform is already wired. We build that infrastructure now, three weeks early, on purpose.

The first thing to internalize is that **telemetry is not logging**. Logging is a stream of text you read after something went wrong. Telemetry is a stream of structured, numeric, time-aligned signals you watch *while* the robot runs, so you can act before something goes wrong. The three pillars we wire this week each do a different job: **Prometheus** scrapes numeric time-series (CPU%, GPU%, cycle latency, battery, heartbeat age) for alerting and dashboards; **OpenTelemetry** (OTel) carries traces and structured metrics across the perception→planner→policy→controller pipeline so you can answer "where did the 80 ms go?"; and **Foxglove** renders the live robot state — pose on the map, the costmap, the policy action arrows, the safety-filter banner — as a panel layout an operator stares at on shift. They are complementary. You do not pick one. A serious robot fleet runs all three, and you will run all three by Sunday.

The second thing to internalize is that **the takeover is a state machine, not a button**. The button is the easy part. The hard part is the transition: when the operator presses "take over," autonomy must stop publishing velocity commands *atomically* with teleop starting to publish them — no gap (the robot coasts blind) and no overlap (two nodes fight over `/cmd_vel` and the robot jerks). The clean way to do this in ROS2 Jazzy is a **mux with a lifecycle-managed arbiter**: a single node owns the output topic, subscribes to both the autonomy and teleop command streams, and publishes exactly one of them based on a latched control-authority state. When authority flips, the arbiter zeroes the output for one cycle (a deliberate, defined "safe stop") and then switches the source. The dashboard shows the authority state as a colored banner so the operator always knows who is driving. We build this arbiter and prove — in the challenge — that it never leaves the robot in an inconsistent or unsafe state across a flip in either direction.

The third thing to internalize is that **the `/fleet/heartbeat` schema you design this week is a capstone deliverable and a week-48 contract**. Capstone requirement 7 says the robot reports identity, capabilities, and health on `/fleet/heartbeat` at 1 Hz, conformant to a documented, Open-RMF-style schema. We design that schema here, publish it from a dedicated node, and scrape it into Prometheus so a fleet operator can see at a glance which robots are alive, which are degraded, and which have gone silent. Get it right now; you will not want to redesign it during defense week.

---

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish** the three telemetry pillars — Prometheus (numeric time-series + alerting), OpenTelemetry (traces + structured metrics), and Foxglove (live operator visualization) — and explain which job each does and why a serious fleet runs all three.
- **Instrument** a ROS2 Jazzy `rclpy` node with a Prometheus `/metrics` endpoint that exposes counters, gauges, and histograms (cycle latency, CPU%, GPU%, heartbeat age) on an HTTP port a Prometheus server can scrape.
- **Wire** the OpenTelemetry SDK into the perception→planner→policy pipeline so a single task execution produces one trace with a span per stage, exportable to an OTLP collector.
- **Build** a Foxglove dashboard layout that streams live pose (a `geometry_msgs/PoseStamped` on the map frame), the Nav2 costmap (`nav_msgs/OccupancyGrid`), the policy's chosen action (a custom message rendered as a marker), and a safety-filter banner driven by a latched `/safety/trigger` topic.
- **Add** a CPU/GPU/thermal load panel to the dashboard, reading `/proc`, `tegrastats` (Jetson) or `nvidia-smi`, and publishing a `DiagnosticArray` that Foxglove renders.
- **Design and publish** a `/fleet/heartbeat` schema (identity, capabilities, health, control-authority, battery, software version) at 1 Hz, Open-RMF-style, and document it as a capstone artifact.
- **Implement** a lifecycle-managed control-authority arbiter (a `/cmd_vel` mux) that switches between autonomy and teleop atomically, with a defined one-cycle safe-stop on every transition, and surfaces the authority state to the dashboard.
- **Demonstrate** that the one-click teleop-takeover pauses autonomy, transfers control to teleop, and returns control to autonomy without leaving the robot inconsistent or unsafe — with the transition visible on the dashboard.
- **Write** an OTA-update procedure for the robot (extending C7 embedded-OTA patterns) with an A/B partition or container-image strategy, a health-gated activation, and a documented rollback that does not brick the robot.
- **Cite** the ROS2, Foxglove, Prometheus, OpenTelemetry, and Open-RMF documentation that justifies each design choice.

## Prerequisites

- **Weeks 41 and 42 of C24 complete.** You have a signed safety case and a capstone robot (hardware on Path A, hardened sim on Path B) that cold-boots cleanly in under 60 seconds and drives a 20-meter trajectory under your own autonomy stack. This week instruments *that* robot; it is not a fresh project.
- **Week 18 (Nav2) and Week 32 (learned policy) integrated.** The dashboard streams the costmap from your Nav2 stack and the action from your policy node. If those topics do not exist on your robot yet, fix that before Wednesday — there is nothing to visualize otherwise.
- **C7 (Crunch Wire — Embedded Systems) OTA material, or equivalent.** The OTA lecture extends the embedded A/B-partition and health-gated-activation patterns from C7. You should already understand why an in-place `apt upgrade` on a running robot is how you brick a fleet.
- **A Foxglove account (free tier)** and the Foxglove desktop app or web app installed. We used it briefly in Week 14 (RGB-D bring-up); this week we build a real layout.
- **A working ROS2 Jazzy install on Ubuntu 24.04** (or the supported WSL2 path), with your capstone workspace building cleanly under `colcon build`. Python 3.12, `rclpy`, and a C++ toolchain for the one C++/BT.CPP node.
- **`pip`-installable extras:** `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `psutil`. A local Prometheus binary and (optionally) a Grafana or the Prometheus expression browser. We install all of these in Lecture 1.

## Topics covered

- **The three telemetry pillars.** Prometheus pull-model scraping vs. OpenTelemetry push-model export vs. Foxglove live MCAP/WebSocket streaming. Where each fits in a robot fleet. Why "just use ROS2 topics for everything" does not scale to alerting.
- **Prometheus on a robot.** The `prometheus-client` Python library, the `/metrics` HTTP endpoint, counters vs. gauges vs. histograms, label cardinality (and why high-cardinality labels are a footgun on an embedded box), the scrape config, and a minimal alerting rule.
- **OpenTelemetry for the autonomy pipeline.** Traces, spans, the `TracerProvider`, the OTLP exporter, context propagation across `rclpy` callbacks, and why a per-task trace is the right granularity for "where did the latency go."
- **Foxglove as the operator's eyes.** The Foxglove WebSocket bridge (`foxglove_bridge`), MCAP recording, panel types (3D, Plot, Raw Messages, Image, Indicator, Gauge), the layout JSON, and how to render a custom policy-action message as a `visualization_msgs/Marker`.
- **The operator dashboard, concretely.** Streaming pose, costmap, policy actions, and safety-filter triggers. Building each panel. The latched safety banner. Recording the MCAP that becomes a week-48 deliverable.
- **The CPU/GPU/thermal load panel.** Reading `psutil` for CPU/RAM, `tegrastats`/`nvidia-smi` for GPU and thermals, publishing `diagnostic_msgs/DiagnosticArray`, and rendering it as Foxglove Gauge + Indicator panels. Why thermal throttling silently breaks your 30 ms perception budget.
- **The `/fleet/heartbeat` schema.** Open-RMF-style identity + capabilities + health, the custom `.msg` definition, the 1 Hz publisher, the staleness-detection consumer, and scraping heartbeat age into Prometheus.
- **The control-authority arbiter (teleop takeover).** The `/cmd_vel` mux pattern, the lifecycle-managed arbiter node, atomic authority flips, the one-cycle safe-stop, the dashboard authority banner, and the BT.CPP condition node that makes autonomy yield.
- **OTA updates for robots.** Extending C7's A/B-partition and health-gate patterns to a ROS2 robot. Container-image vs. system-partition strategies, the staged rollout, the health-gated activation, the automatic rollback, and the "never brick the fleet" rules.
- **Remote teleop assist as a fleet concept.** Latency budgets for remote driving, the "assist, don't replace" posture, and how the takeover plumbing you build this week is the same plumbing a remote-assist operator uses.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract. The Foxglove layout work is best done with the robot (or sim) actually running so you see panels light up; do not save it for a tired evening.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Three telemetry pillars; Prometheus + OTel on a node        |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Foxglove dashboard: pose, costmap, policy actions, safety   |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | CPU/GPU panel; `/fleet/heartbeat` schema                    |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Thursday  | Control-authority arbiter; teleop takeover; OTA lecture      |    1h    |    1h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Mini-project: integrate the full dashboard + takeover        |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work: OTA procedure, MCAP recording        |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, polish                                        |    0h    |    0h     |     0h     |    1h     |   0h     |     0.5h     |    0h      |     1.5h    |
| **Total** |                                                             | **6h**   | **6.5h**  | **3h**     | **3.5h**  | **5h**   | **11.5h**    | **2h**     | **34.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Foxglove, Prometheus, OpenTelemetry, ROS2, and Open-RMF docs, with one-line annotations |
| [lecture-notes/01-the-operator-dashboard.md](./02-lecture-notes/01-the-operator-dashboard.md) | The operator dashboard end-to-end: the three pillars, Prometheus + OTel on an `rclpy` node, and the Foxglove layout streaming pose, costmap, policy actions, and safety triggers |
| [lecture-notes/02-ota-updates-and-teleop-assist.md](./02-lecture-notes/02-ota-updates-and-teleop-assist.md) | OTA for robots (extending C7's A/B + health-gate patterns) and the control-authority arbiter that powers the one-click teleop takeover |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-foxglove-telemetry-dashboard.md](./03-exercises/exercise-01-foxglove-telemetry-dashboard.md) | Wire robot telemetry into a Foxglove dashboard streaming pose, costmap, policy actions, and safety-filter triggers |
| [exercises/exercise-02-cpu-gpu-load-panel.py](./03-exercises/exercise-02-cpu-gpu-load-panel.py) | A `DiagnosticArray` publisher for CPU/GPU/thermal load, rendered as a Foxglove panel |
| [exercises/exercise-03-teleop-takeover-arbiter.py](./03-exercises/exercise-03-teleop-takeover-arbiter.py) | A lifecycle-managed `/cmd_vel` arbiter implementing the one-click teleop takeover |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-clean-takeover-and-return.md](./04-challenges/challenge-01-clean-takeover-and-return.md) | Prove the takeover pauses autonomy, transfers to teleop, and returns control with no inconsistent or unsafe state, all visible on the dashboard |
| [quiz.md](./05-quiz.md) | 13 questions on telemetry, the arbiter, the heartbeat schema, and OTA |
| [homework.md](./06-homework.md) | Six practice problems with deliverables and a rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the capstone operator dashboard + teleop-takeover + OTA procedure |

## The "operator can see it" promise

C24 uses a recurring marker for every operations artifact in this phase:

```
[ops] heartbeat OK · authority=AUTONOMY · cycle p99=27ms · gpu=61% · thermal=58°C
```

If your dashboard cannot show every field on that line in real time, your dashboard is not done. The point of Week 43 is to make that line ordinary — so that in Week 46, when the LiDAR dies and the line goes red, you *see it* and react inside 60 seconds. We treat "an operator who is not you can watch and rescue this robot" as the contract for the entire week.

## A note on what's not here

Week 43 builds the operations layer for a *single* capstone robot plus the *schema* and *plumbing* that make it fleet-ready. It does **not** build:

- **A full multi-robot fleet manager.** Open-RMF fleet adapters and conflict resolution were Week 36. This week we conform to the heartbeat schema Open-RMF expects and stop there; the capstone is one robot.
- **A production Grafana + Alertmanager + PagerDuty stack.** We stand up Prometheus and a minimal alert rule to prove the scrape works. The full on-call alerting stack is the `production-runbook.md` material at the track root, exercised in Week 46.
- **Cloud-side OTA orchestration (Mender, Balena, Greengrass at scale).** We document a *robot-side* OTA procedure that does not brick the box and name the cloud orchestrators in resources. Running a fleet-wide staged rollout is beyond a single capstone.
- **End-to-end-encrypted remote teleop over the public internet.** We build the local control-authority arbiter and the WebSocket bridge. Securing remote teleop across a WAN (DTLS, TURN, jitter buffers) is a real topic we name but do not implement here.

The point of Week 43 is a sharp, narrow capability: make your one capstone robot observable and operable by someone other than you, wire the `/fleet/heartbeat` contract that week 48 will check, and prove a clean takeover and return.

## Stretch goals

If you finish the regular work early and want to push further:

- Stand up **Grafana** against your Prometheus and rebuild the CPU/GPU/heartbeat panels there, so you have both the Foxglove (live robot state) and Grafana (time-series ops) views a real fleet runs side by side: <https://grafana.com/docs/grafana/latest/>.
- Add an **Alertmanager** rule that fires when `heartbeat_age_seconds > 5`, and route it to a local webhook. This is the first half of the Week 46 alerting muscle.
- Record a **5-minute MCAP** of a full task execution with a deliberate teleop takeover in the middle, and scrub it in Foxglove to confirm every panel replays. This is a dry run of the week-48 dashboard recording.
- Read the **Open-RMF `rmf_fleet_msgs`** definitions and align your `/fleet/heartbeat` schema field-for-field with `FleetState`/`RobotState`: <https://github.com/open-rmf/rmf_internal_msgs>.
- Extend the OTA procedure with a **canary stage**: update one robot, watch its heartbeat and cycle-latency metrics for ten minutes, and only then "promote" the image to the rest of the (simulated) fleet.

## Up next

Continue to **Week 44 — Capstone Build Sprint 3 + Language-Conditioned Task Tuning** once your dashboard records cleanly and your takeover passes the challenge. Week 44 fine-tunes the VLA policy on capstone-specific demos and curates the twenty-instruction eval suite. The telemetry you wired this week is exactly how you will *watch* those evals run and catch a policy regression before it ships — observability is not a detour from the capstone, it is the instrument panel you fly the rest of it with.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
