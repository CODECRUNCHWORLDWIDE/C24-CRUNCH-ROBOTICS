# Week 43 Homework

Six practice problems that revisit the week's topics and harden the operations layer of your capstone. The full set should take about **5 hours**. Work in your capstone repository so each problem produces at least one commit you can point to during the week-48 defense.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Translate the four golden signals to your robot

**Problem statement.** Google SRE's four golden signals are latency, traffic, errors, and saturation. Write `docs/golden-signals.md` mapping each signal to a *specific metric on your capstone*, naming the Prometheus metric name, type (counter/gauge/histogram), and the alert threshold you would set. Include the PromQL expression for each alert.

**Acceptance criteria.**

- `docs/golden-signals.md` exists with all four signals mapped to a concrete metric.
- Each row names the metric type and gives a working PromQL alert expression (e.g., `histogram_quantile(0.95, rate(capstone_cycle_latency_seconds_bucket[1m])) > 0.030`).
- At least one signal uses a histogram and at least one uses a counter `rate()`.
- File is committed.

**Hint.** Latency → cycle-latency histogram; Traffic → tasks-accepted counter; Errors → safety-triggers counter + planner-failure counter; Saturation → CPU/GPU/thermal gauges. The SRE chapter is in the resources page.

**Estimated time.** 40 minutes.

---

## Problem 2 — Add a real OpenTelemetry span to a slow stage

**Problem statement.** Wire the `tracing.py` helper from Lecture 1 §3 into your autonomy pipeline so one task execution produces a trace with a span per stage. Run a task. Export the trace to a local OTLP collector (or the `debug` exporter) and identify which stage dominates the latency. Write a 150-word note at `notes/where-the-time-went.md` with the per-stage durations and which stage you would optimize first.

**Acceptance criteria.**

- The autonomy pipeline produces one trace per task with named spans for perception, planner, policy, and controller.
- You captured one exported trace (JSON dump or screenshot) and committed it under `notes/`.
- The note correctly identifies the dominant span by duration and names a concrete next optimization.
- The `BatchSpanProcessor` is used (not synchronous export).

**Hint.** Run `otelcol --config otel-config.yaml` locally with an OTLP receiver and a `debug` exporter; the spans print to stdout. The slowest span is almost always perception (a learned model) or policy (a VLA forward pass).

**Estimated time.** 50 minutes.

---

## Problem 3 — The heartbeat health-rollup rule

**Problem statement.** Implement and document the `health` field of `/fleet/heartbeat` as a *rollup* of your diagnostics, not a single sensor. Define the exact rule for NOMINAL / DEGRADED / FAULT in `docs/heartbeat-health-rule.md` and implement it in `heartbeat_node.py`. Then prove it: induce a WARN (load the box to push thermal into the WARN band) and confirm the heartbeat reports DEGRADED, not FAULT.

**Acceptance criteria.**

- `heartbeat_node.py` computes `health` from the worst current `DiagnosticStatus` level plus the safety-override state.
- The rule is documented: NOMINAL (all OK, no override), DEGRADED (any WARN), FAULT (any ERROR or a dropped sensor).
- You demonstrate (a log or screenshot) the heartbeat transitioning OK → DEGRADED → OK as you load and unload the box.
- File and code are committed.

**Hint.** Subscribe `/diagnostics`, take the worst level across all `DiagnosticStatus` entries, and combine with `/safety/trigger.active`. `stress-ng --cpu 4 --timeout 20s` pushes thermal into WARN on most boxes.

**Estimated time.** 50 minutes.

---

## Problem 4 — The teleop-link watchdog test

**Problem statement.** Write a small test (a `pytest` or a `launch_testing` test) that starts your `control_arbiter`, activates it, flips to TELEOP, publishes a few `/cmd_vel_teleop` messages, then *stops* publishing and asserts that `/cmd_vel_out` goes to a zero `Twist` within the watchdog window. This is the property the chaos drill will check.

**Acceptance criteria.**

- A runnable test exists at `test/test_teleop_watchdog.py`.
- The test activates the arbiter, flips authority to TELEOP, and verifies forwarding works while teleop is live.
- The test stops teleop and asserts `/cmd_vel_out` is zero within `teleop_watchdog` seconds.
- `colcon test` (or `pytest`) passes.

**Hint.** Use `rclpy` directly in the test: spin the arbiter on an executor in a thread, publish from the test, and capture `/cmd_vel_out`. Compare against `Twist()` with a small epsilon. The watchdog param defaults to 0.5 s.

**Estimated time.** 60 minutes.

---

## Problem 5 — Dry-run the OTA rollback

**Problem statement.** Do an end-to-end OTA dry run that *fails on purpose* and proves the rollback. Build a "broken" image (one whose graph crashes on boot, e.g., a node that raises in `__init__`). Run `ota-apply.sh` against it. Confirm the health gate fails within its budget, the old container/slot keeps running, and the robot is never bricked. Write the timeline at `notes/ota-rollback-dryrun.md`.

**Acceptance criteria.**

- You ran `ota-apply.sh` against a deliberately-broken image.
- The health gate failed (non-zero exit) and the script left the previous version running.
- The robot remained operable throughout (the old heartbeat never stopped).
- `notes/ota-rollback-dryrun.md` has a timeline: pull → start candidate → gate fails → rollback → old version confirmed running.

**Hint.** Make the broken image's `health_gate.py` time out by having the candidate graph never publish a nominal heartbeat. The script's `timeout` wrapper handles the budget; verify the `exit 1` path leaves `capstone-candidate` removed and the old `capstone` container untouched.

**Estimated time.** 50 minutes.

---

## Problem 6 — Align the heartbeat with Open-RMF

**Problem statement.** Read `rmf_fleet_msgs/RobotState` and `FleetState` in `rmf_internal_msgs`. Write `notes/rmf-alignment.md` mapping each field of your `Heartbeat.msg` to its Open-RMF analogue, noting where they match, where they differ, and what you would need to add to make your robot droppable into an Open-RMF fleet (the Week 36 fleet manager) without redesign.

**Acceptance criteria.**

- `notes/rmf-alignment.md` maps every `Heartbeat.msg` field to an `rmf_fleet_msgs` field (or "no analogue").
- It identifies at least two fields Open-RMF expects that your heartbeat lacks (e.g., `task_id`, `seq`, `location.level_name`) and states whether you would add them.
- It cites the exact `rmf_internal_msgs` file/message you read.
- File is committed.

**Hint.** The repo is <https://github.com/open-rmf/rmf_internal_msgs>; `RobotState.msg` is the one to compare against. Open-RMF carries a multi-floor `Location` with `level_name` — your single-floor capstone may not, and that is fine to document as a known gap.

**Estimated time.** 30 minutes.

---

## Submission

Push the `docs/`, `notes/`, and any test code to your capstone repository. The instructor reviews by:

1. Reading each note and doc.
2. Re-running the watchdog test (Problem 4) and the OTA dry run (Problem 5) and confirming they behave as the notes claim.
3. Cross-checking the cited Open-RMF and SRE references are real and the claims are consistent with the source.

A submission whose notes are present and whose two runnable artifacts (the watchdog test and the rollback dry run) reproduce is a pass. The most common review-fail is "the OTA note claims a rollback but the script actually left both containers running" — verify the old-version-only end state before submitting.

---

## Rubric

| Area | Weight | What earns full marks |
|------|-------:|-----------------------|
| Golden-signals mapping (P1) | 15% | All four signals mapped to concrete metrics with working PromQL alerts. |
| Tracing + analysis (P2) | 20% | Per-stage spans captured; dominant stage correctly identified with a concrete next step. |
| Heartbeat health rollup (P3) | 20% | Documented rule implemented and demonstrated transitioning NOMINAL↔DEGRADED. |
| Watchdog test (P4) | 20% | Runnable test that proves the teleop-link safe-stop within the watchdog window. |
| OTA rollback dry run (P5) | 15% | Broken image rolled back cleanly; robot never bricked; timeline documented. |
| Open-RMF alignment (P6) | 10% | Field-by-field mapping with at least two real gaps identified, cited from the source. |

Pass threshold: **75%**, with the watchdog test (P4) and the OTA rollback (P5) both reproducing — those two are the operationally load-bearing safety properties and a fail on either is a fail on the homework regardless of the total.

---

**References**

- Google SRE — Monitoring Distributed Systems (four golden signals): <https://sre.google/sre-book/monitoring-distributed-systems/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/languages/python/getting-started/>
- `diagnostic_msgs/DiagnosticArray`: <https://docs.ros2.org/latest/api/diagnostic_msgs/msg/DiagnosticArray.html>
- ROS2 launch_testing: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Testing/Integration.html>
- Open-RMF `rmf_internal_msgs`: <https://github.com/open-rmf/rmf_internal_msgs>
- RAUC / Mender (OTA rollback): <https://rauc.readthedocs.io/> · <https://docs.mender.io/>
