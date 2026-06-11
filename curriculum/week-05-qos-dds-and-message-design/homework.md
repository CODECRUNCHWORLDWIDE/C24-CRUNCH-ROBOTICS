# Week 5 Homework

Six problems that revisit the week's topics and force the QoS literacy into your fingers. The full set should take about **5 hours**. Work in your Week 5 Git repository (the same workspace as the exercises and the `crunchbot_qos` mini-project) so every problem produces at least one commit you can point to at the Phase 1 architecture review in Week 8.

The headline deliverable is **Problem 4 — the one-page mismatch postmortem**, called out explicitly in the syllabus. Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and source your overlay if you've built one. Have your **week-3 differential-drive robot** spawnable in Gz Sim — Problems 1, 2, and 4 run against it. If the sim is broken, the standalone publishers from the exercises are your fallback; say so in your writeup.

---

## Problem 1 — The graph audit table

**Problem statement.** Bring up your week-3 robot in Gz Sim. For **every** topic the robot publishes (`/scan`, `/imu/data`, `/odom`, `/tf`, `/tf_static`, `/clock`, `/cmd_vel`, plus anything your URDF's plugins add), run `ros2 topic info <topic> -v` and record the actual offered QoS. Build a markdown table in `notes/week-05/graph-audit.md` with one row per topic and these columns:

| Topic | Type | Reliability | Durability | History (Depth) | Pub/Sub count | Class (your call) | Correct? |
|---|---|---|---|---|---|---|---|

The **Class** column is your judgement — `sensor`, `latched`, `command`, `tf`, `clock`, `diagnostic`. The **Correct?** column is `yes`/`no` against the topic-class taste test from Lecture 1, with a one-line reason where you wrote `no`.

**Acceptance criteria.**

- `notes/week-05/graph-audit.md` exists with one row per published topic (at least seven rows).
- Every row's QoS columns come from real `ros2 topic info -v` output, not from memory.
- At least one topic is marked `no` with a reason, or you explicitly argue every topic is already correct and why.
- Committed.

**Hint.** `/tf_static` should be `RELIABLE` + `TRANSIENT_LOCAL` (it's a latch). `/scan` and `/imu/data` from a Gz Sim plugin are frequently `RELIABLE` by default — that's the row you mark `no`. Pipe the loop: `for t in $(ros2 topic list); do echo "=== $t ==="; ros2 topic info "$t" -v; done > /tmp/qos_dump.txt` and transcribe from there.

**Estimated time.** 40 minutes.

---

## Problem 2 — Make the sensor topics correct, prove it

**Problem statement.** Take the two sensor topics from Problem 1 that you marked `no` (almost certainly `/scan` and `/imu/data`). Apply `BEST_EFFORT` / `KEEP_LAST` / `depth=5` to both — either by configuring the Gz Sim sensor bridge QoS, or by writing a thin `rclpy` relay node that subscribes with matching QoS and re-publishes on `/scan_be` and `/imu_be` with the sensor profile. Re-run `ros2 topic info -v` and capture the before/after QoS blocks.

**Acceptance criteria.**

- Both target topics (or their relayed equivalents) now show `Reliability: BEST_EFFORT`, `Durability: VOLATILE`, `History (Depth): KEEP_LAST (5)` in `ros2 topic info -v`.
- A subscriber actually receives data on the corrected topic — `Subscription count` is non-zero and `ros2 topic hz` shows the expected rate.
- Before/after `ros2 topic info -v` output is pasted into `notes/week-05/sensor-fix.md`.
- Committed.

**Hint.** If you relay, your subscriber QoS must be **compatible** with the original publisher (a `BEST_EFFORT` subscriber on a `RELIABLE` publisher is fine — reliable offered satisfies best-effort requested). The clean way is the `crunchbot_qos.sensor_qos()` factory from the mini-project; if you've built it, import it here and note that you did.

**Estimated time.** 45 minutes.

---

## Problem 3 — Version a message and watch the hash refuse to lie

**Problem statement.** In a `crunch_interfaces` package (create it if you don't have one), define `msg/SystemHealth.msg` v1:

```
std_msgs/Header header
float32 battery_voltage
float32 cpu_temp_celsius
uint8 nav_state
```

Build it. Write a tiny `rclpy` publisher and subscriber for `/system_health` and confirm they connect. Now **append** a field to make v2:

```
std_msgs/Header header
float32 battery_voltage
float32 cpu_temp_celsius
uint8 nav_state
float32 disk_free_gb
```

Rebuild **only the publisher's** workspace overlay against v2 while leaving the subscriber's terminal sourcing the v1 overlay (use two separate overlays, or rebuild and re-source asymmetrically). Run both. Observe and document what happens to the connection.

**Acceptance criteria.**

- `crunch_interfaces/msg/SystemHealth.msg` exists and builds clean under both v1 and v2.
- A `notes/week-05/message-versioning.md` records: the v1 `ros2 interface show crunch_interfaces/msg/SystemHealth`, the v2 version, and the observed behavior when a v1 subscriber meets a v2 publisher.
- You correctly identify that the **type hash (RIHS)** differs and the endpoints **do not connect** — and explain why that's a feature, not a bug.
- Committed.

**Hint.** `ros2 topic info /system_health -v` will show both endpoints existing but no data flowing once the hashes diverge — discovery succeeded, type-hash check failed. This is *not* a QoS mismatch; if you misdiagnose it as one you'll waste an hour. Compare against Lecture 2 §3.4.

**Estimated time.** 1 hour.

---

## Problem 4 — The one-page mismatch postmortem (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Take Exercise 3 (the mismatch probe) or engineer a fresh mismatch on your robot: publish `/scan` `BEST_EFFORT` and subscribe `RELIABLE`, or publish `/map` `VOLATILE` and subscribe `TRANSIENT_LOCAL` late. Reproduce the **silent failure** — a topic that exists, with both endpoints visible, but zero data flowing. Then write a one-page postmortem at `notes/week-05/qos-mismatch-postmortem.md` against this template:

1. **Summary** — one sentence: what broke and the user-visible symptom.
2. **Timeline** — what you ran, what you expected, what you saw, in order, with the actual `ros2 topic info -v` and `ros2 doctor` lines that were diagnostic.
3. **Root cause** — the exact policy that was incompatible, stated as a request–offered rule violation (e.g., "subscriber requested `RELIABLE`; publisher offered `BEST_EFFORT`; reliable-requested is not satisfied by best-effort-offered, so SEDP rejected the match").
4. **Why it was silent** — why no exception or error log fired, and where the `incompatible_qos` event *could* have been surfaced.
5. **Fix** — the corrected profile, with the before/after QoS blocks.
6. **Prevention** — one concrete process change (e.g., "all sensor QoS comes from `crunchbot_qos.sensor_qos()`; the auditor runs in pre-launch").

**Acceptance criteria.**

- `notes/week-05/qos-mismatch-postmortem.md` exists, fits on roughly one page (350–550 words), and hits all six headings.
- The root cause is stated as a **specific** request–offered rule violation, not "the QoS was wrong."
- At least one real diagnostic command's output is quoted (`ros2 topic info -v`, `ros2 doctor`, or an `incompatible_qos` event log line).
- The prevention item is concrete and actionable, not "be more careful."
- Committed.

**Hint.** Register the `incompatible_qos` event callback (`SubscriptionEventCallbacks(incompatible_qos=...)`) to make the silent failure *loud* — quoting that event's `last_policy_kind` (e.g., `RELIABILITY_QOS_POLICY`) is the strongest possible evidence for your root-cause section. The whole point of the postmortem is that you can turn a silent failure into a named one.

**Estimated time.** 1 hour.

---

## Problem 5 — Swap the DDS vendor under your own graph

**Problem statement.** Run your week-3 robot under the Jazzy default (`rmw_fastrtps_cpp`). Capture `ros2 doctor --report | grep -iA2 middleware`. Then `sudo apt install ros-jazzy-rmw-cyclonedds-cpp`, `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, **re-source and restart every node** (vendor cannot be changed on a live node), and re-run the same `ros2 doctor` capture and a `ros2 topic hz /scan`. Record both runs side by side.

**Acceptance criteria.**

- `notes/week-05/vendor-swap.md` shows the `ros2 doctor` middleware section for both Fast-DDS and CycloneDDS.
- You confirm the graph still functions under CycloneDDS (`/scan` echoes, `ros2 topic hz` reasonable).
- You note in one sentence the rule: **every node in a graph must run the same rmw**, and what symptom appears if one terminal forgot to export the variable.
- Committed.

**Hint.** The classic self-own: you `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in the terminal running the sim but not in the terminal running your subscriber. The two land on different vendors and — depending on versions and RTPS interop — silently don't talk. Set it in your bring-up environment, not per-terminal, to avoid this in real life.

**Estimated time.** 40 minutes.

---

## Problem 6 — Wire the auditor into a pre-launch check

**Problem statement.** Take the `crunchbot_qos/audit.py` auditor from the mini-project (or, if you haven't finished it, a minimal version that checks just `/scan`, `/imu/data`, and `/map`). Make it usable as a **gate**: it must exit `0` when every policy-listed topic matches the registry and exit non-zero when any topic is mis-configured. Then prove the gate works by intentionally breaking one topic's QoS and showing the non-zero exit.

**Acceptance criteria.**

- Running the auditor against a correctly-configured graph prints a pass table and `echo $?` shows `0`.
- Running it against a graph where you've deliberately mis-set one topic prints a `FAIL` row naming the offending topic and the expected-vs-actual policy, and `echo $?` shows non-zero.
- Both runs are captured in `notes/week-05/auditor-gate.md`.
- Committed.

**Hint.** The exit code is what makes it a CI/pre-launch gate rather than a pretty printer — `sys.exit(1 if failures else 0)` at the end of the script. To break one topic deterministically, publish `/scan` from a one-liner with the wrong reliability: `ros2 topic pub /scan sensor_msgs/msg/LaserScan "{}" --qos-reliability reliable` while the registry expects `best_effort`.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Graph audit table | 40 min |
| 2 — Correct the sensor topics | 45 min |
| 3 — Version a message | 1 h 0 min |
| 4 — Mismatch postmortem (headline) | 1 h 0 min |
| 5 — DDS vendor swap | 40 min |
| 6 — Auditor as a pre-launch gate | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_qos` [mini-project](./mini-project/README.md) is in the same workspace — Week 8 imports it. Then take the [quiz](./quiz.md) with your notes closed.
