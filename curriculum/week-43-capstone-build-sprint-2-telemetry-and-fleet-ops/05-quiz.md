# Week 43 — Quiz

Thirteen questions on telemetry, the operator dashboard, the control-authority arbiter, the `/fleet/heartbeat` schema, and OTA. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 44. Answer key at the bottom — don't peek.

---

**Q1.** Which statement best captures why a serious robot fleet runs Prometheus, OpenTelemetry, *and* Foxglove rather than picking one?

- A) They are interchangeable; running three is for redundancy in case one crashes.
- B) Prometheus answers "is the robot healthy now / alert me," OpenTelemetry answers "where did the latency go," and Foxglove answers "what is the robot seeing and doing" — three different questions.
- C) Prometheus is for sim, OpenTelemetry is for hardware, and Foxglove is for both.
- D) Foxglove replaces the other two; the others exist only for legacy fleets.

---

**Q2.** Why does Prometheus use a *pull* (scrape) model rather than having the robot push metrics?

- A) Pull is faster on embedded hardware.
- B) A failed scrape is itself a signal — `up == 0` tells you the robot fell off the network, a failure a push model hides.
- C) Push is not supported by the `prometheus-client` library.
- D) Pull avoids the need for any network connection.

---

**Q3.** You add a `task_id` label to a Prometheus counter on an Orin Nano. What goes wrong?

- A) Nothing; labels are free.
- B) Each distinct `task_id` creates a new time series held in RAM; cardinality explodes and exhausts memory.
- C) The counter silently stops incrementing.
- D) Prometheus refuses to scrape labels with underscores.

---

**Q4.** Cycle latency should be exposed as which Prometheus metric type, and why?

- A) A gauge, because it goes up and down.
- B) A counter, because each cycle is one event.
- C) A histogram, because you need p95/p99 — a mean hides the tail that blows your 30 ms budget.
- D) A summary, because it is the only type that supports labels.

---

**Q5.** Why must autonomy-pipeline tracing use `BatchSpanProcessor` rather than a synchronous exporter on a robot?

- A) Synchronous export is not implemented in the Python SDK.
- B) The batch processor exports on a background thread, so tracing does not add latency to the very cycle it measures.
- C) The batch processor is the only one that supports OTLP.
- D) It encrypts the spans; the synchronous one does not.

---

**Q6.** The Nav2 costmap does not appear when Foxglove connects mid-run. The most likely cause is:

- A) The costmap topic was unpublished.
- B) The costmap is published transient-local (latched) and the panel's fixed frame is wrong, or QoS is incompatible — a late subscriber needs latched durability to get the last map.
- C) Foxglove cannot render `OccupancyGrid` at all.
- D) The robot's clock is unsynchronized.

---

**Q7.** Why is `/safety/trigger` published with transient-local (latched) QoS?

- A) To reduce bandwidth.
- B) So a freshly-connected Foxglove (or a late subscriber) immediately sees the *current* safety state instead of waiting for the next event.
- C) Because `bool` fields require latched QoS.
- D) Latched QoS is the ROS2 default for all custom messages.

---

**Q8.** Two nodes publish to `/cmd_vel`. What is the failure, and what is the fix?

- A) No failure; ROS2 merges the commands.
- B) The base receives interleaved conflicting commands and jerks; the fix is a single arbiter that owns the output and forwards exactly one source per a latched authority state.
- C) ROS2 throws a "duplicate publisher" error; the fix is to rename one topic.
- D) The second publisher is silently ignored; no fix needed.

---

**Q9.** Why does the arbiter zero the output for exactly one cycle on every authority flip?

- A) To reset the base driver.
- B) It is the defined safe-stop — it guarantees no instant where a stale source's command and the new source's command overlap, and no blind coast.
- C) To give the operator time to react.
- D) It is required by the lifecycle state machine.

---

**Q10.** The control arbiter is a *lifecycle* node. What does it publish to `/cmd_vel_out` while `inactive`?

- A) The last autonomy command.
- B) A continuous zero Twist.
- C) Nothing — a half-booted robot must not drive; only `activate` arms it.
- D) Whatever teleop sends.

---

**Q11.** State the two rules that prevent every robot brick during an OTA update.

- A) Update fast, and reboot twice.
- B) (1) Never modify the running system in place — update a copy, then switch. (2) Never trust an update until it passes a health gate; auto-roll-back on failure.
- C) Always update over Ethernet, never Wi-Fi; always update at night.
- D) Keep three copies of the rootfs; never use containers.

---

**Q12.** Why does the OTA health gate subscribe to `/fleet/heartbeat` rather than running its own independent checks?

- A) It is faster to read one topic.
- B) The heartbeat already aggregates the operationally meaningful signals (health rollup, safety state, version) — the same observability that lets an operator watch the robot lets the gate decide promote-vs-rollback.
- C) The gate cannot create its own subscriptions.
- D) `/fleet/heartbeat` is the only topic available after an update.

---

**Q13.** Under TELEOP authority, the operator's command stream (`/cmd_vel_teleop`) goes silent (link dropped). What must the arbiter do, and why?

- A) Keep forwarding the last teleop command, so the robot maintains momentum.
- B) Switch back to AUTONOMY automatically.
- C) Safe-stop the robot after a short watchdog timeout — a robot driven by a dead link must halt, not coast.
- D) Nothing; the base driver handles timeouts.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The three pillars answer three different operational questions: Prometheus (health now + alerting), OpenTelemetry (where did the latency go), Foxglove (live operator view). They are complementary, not redundant.
2. **B** — The pull model makes a failed scrape (`up == 0`) a first-class signal: the robot going silent is exactly the failure you most want to alert on, and a push model hides it.
3. **B** — High label cardinality is the classic Prometheus footgun on embedded boxes: every distinct label combination is a separate in-RAM time series. `task_id` (unbounded) would exhaust the Orin's memory. Keep labels low-cardinality.
4. **C** — A histogram gives you p50/p95/p99. A mean of 20 ms hides the 90 ms tail that blows the perception budget once a second. Choose buckets around the 30 ms budget for resolution where it matters.
5. **B** — `BatchSpanProcessor` exports on a background thread, so the act of measuring does not add latency to the measured cycle. Synchronous export would make the observer change the observed.
6. **B** — Nav2 publishes the costmap transient-local so late subscribers get the last map; the panel must subscribe with compatible durability and have the correct fixed frame (`map`). A wrong fixed frame silently hides it.
7. **B** — Latched (transient-local, depth 1) QoS means a subscriber that connects after the last event still receives the current state. The operator's Foxglove sees the live safety state instantly, not after the next trigger.
8. **B** — Two publishers to one command topic produce an interleaved, conflicting stream and the robot jerks. The fix is a single arbiter (a `/cmd_vel` mux with a brain) that owns the output and forwards exactly one source per a latched authority.
9. **B** — The one-cycle zero output is the defined safe-stop: it guarantees no overlap between the old and new source and no blind coast across the transition. Skipping it makes the robot lurch on a flip.
10. **C** — A lifecycle arbiter publishes nothing while `inactive`, so a half-booted robot (or an OTA trial before health-gate) never drives. Only `activate` arms it.
11. **B** — (1) Never modify the running system in place (update a copy, then switch — the A/B pattern). (2) Health-gate the trial and auto-roll-back on failure. These lift the C7 embedded A/B + watchdog pattern to a full Linux robot.
12. **B** — The heartbeat already carries the health rollup, safety state, and version. Reusing it means the same telemetry that lets an operator watch the robot also drives the automated promote-vs-rollback decision — build the observability once, use it three times.
13. **C** — A robot driven by a dead link must halt, not coast. The arbiter runs a watchdog on `/cmd_vel_teleop`; if commands stop arriving under TELEOP authority, it safe-stops within the timeout. Auto-switching to autonomy (B) would be unsafe — autonomy may not have re-localized.

</details>

---

If you scored under 9, re-read the lecture for the questions you missed — especially the arbiter state machine and the never-brick rules. If you scored 12 or 13, you're ready for the [homework](./06-homework.md).
