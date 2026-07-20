# Week 40 Homework

Six practice problems that turn this week's lectures into the Phase-6 scaffolds your capstone needs. The full set should take about **5 hours**. Work in your Week 40 capstone repository so each problem produces a committed artifact you point at during the milestone sign-off.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Fill in the planner-deadlock chaos-drill template

**Problem statement.** Lecture 2 filled in the chaos-drill template for the sensor-dropout fault. You fill in the second one — **planner-deadlock-at-doorway** — for your robot, using the same six-part structure: steady-state hypothesis, injected fault, detection signal, graceful-degradation path, recovery deadline + success criterion, and the (empty-for-now) postmortem skeleton. The fault: a narrow corridor is partially blocked by a moved obstacle; the Nav2 planner cycles without converging.

**Acceptance criteria.**

- `chaos-drills/planner-deadlock.md` exists with all six parts filled (except the postmortem, which is a skeleton to fill at Week 46).
- The detection signal names a concrete, observable mechanism (e.g., a `plan_watchdog` that detects N consecutive replans without progress and publishes `/health/planner = CYCLING`).
- The recovery deadline is the spec's 60 s, the success criterion is operator-detectable on the dashboard, and the degradation path is concrete (replan around, request operator assist, or safely abort).

**Hint.** Mirror the sensor-dropout drill in Lecture 2. The Nav2 planner exposes enough state (number of replans, distance-to-goal not decreasing) to build a cycle detector. Your `/health/*` topic family is the seam.

**Estimated time.** 45 minutes.

---

## Problem 2 — Run the pre-flight check against your live stack and close every failure

**Problem statement.** Take your Exercise 2 pre-flight check node, point it at your *live composed stack* (not `--demo`), and run it. Record the first output verbatim. For every check that fails, diagnose the root cause, fix it, and re-run until all checks pass. Write up each failure-and-fix.

**Acceptance criteria.**

- `notes/preflight-run.md` contains the first (likely-failing) pre-flight output and the final all-pass output.
- For each initial failure, a one-paragraph diagnosis naming which of the four integration defects it was (frame/timing, stale-perception/rate, lifecycle-order, or a missing-topic presence failure) and the fix.
- The final run shows all checks PASS and the node exits 0.

**Hint.** The most common first failures are a `tf` lookup that fails because a broadcaster has not started, and a lifecycle node reporting `inactive` because the bring-up order is wrong. Both are exactly the defects the check exists to catch.

**Estimated time.** 60 minutes.

---

## Problem 3 — Measure the two milestone acceptance numbers

**Problem statement.** Write (or finish) `measure_drift.py` and `measure_cold_boot.py` and run them against your stack. `measure_drift.py` drives a measured 20 m trajectory and reports the Euclidean error between `/odometry/filtered` and sim ground truth. `measure_cold_boot.py` times launch-start to `system ready`. Report the actual numbers.

**Acceptance criteria.**

- `notes/acceptance-numbers.md` records both measured numbers with the command that produced each.
- The drift measurement names the ground-truth source (the Gz/Isaac model pose) and the 20 m path it drove.
- The cold-boot measurement defines "system ready" precisely (lifecycle all-active AND pre-flight pass) and reports the time.
- If either number misses its target (< 0.5 m, < 60 s), the note states the gap honestly and lists a Phase-6 action item to close it. Honest reporting passes; a fabricated "0.0 m, 12 s" with no method fails.

**Hint.** For drift, the Gz Sim `/<model>/pose` (via `ros_gz` bridge) or the Isaac ground-truth pose is your reference. For cold boot, timestamp the launch event and the lifecycle manager's `system ready` log line; their difference is the number.

**Estimated time.** 60 minutes.

---

## Problem 4 — Populate the safety-case hazard list, first pass

**Problem statement.** Open the `safety-case/03-hazard-list.md` scaffold and populate it with the hazards for your specific mobile manipulator, expanding your Week 24 hazard log. For each hazard, give a one-line description and a provisional severity (1–10). Then, for the three highest-severity hazards, add a row to `safety-case/04-fmea.md` with failure mode, effect, S, O, D, and the RPN (S × O × D).

**Acceptance criteria.**

- `03-hazard-list.md` lists at least six hazards covering both the base (collision, runaway) and the arm (strike, pinch, dropped object, wrong-object delivery).
- `04-fmea.md` has at least three rows with S, O, D, and a computed RPN.
- Each of the three FMEA rows names the mitigation that would reduce it and the node/topic that implements that mitigation (forward-reference to `05-mitigations.md`).

**Hint.** Wrong-object delivery of a hazardous item is the hazard the perception confidence gate mitigates; arm strike during a grasp is the hazard the workspace clamp mitigates. Use the MIL-STD-1629A S/O/D scale.

**Estimated time.** 45 minutes.

---

## Problem 5 — Wire the Foxglove milestone layout and pass the narration test

**Problem statement.** Build the Foxglove layout for your milestone dashboard (one panel per layer: 3D, detections, path summary, policy, safety, heartbeat), check it into the repo at `dashboard/milestone-layout.json`, and run one end-to-end pass with a peer narrating from the screen only (terminal hidden). Record whether the narration passed and which layer, if any, was unclear.

**Acceptance criteria.**

- `dashboard/milestone-layout.json` is committed and loads in Foxglove.
- A `notes/narration-test.md` records the peer's name, whether the narration passed, and any layer that was unclear plus the fix you applied.
- If a layer was dark, the note shows the before/after: what was missing and what you added to the telemetry spine or layout to make it observable.

**Hint.** The policy and safety layers are the ones most often "dark" — the grasp pose and the safety status are easy to compute but easy to forget to surface. Exercise 3 publishes both; make sure the layout has a panel for each.

**Estimated time.** 45 minutes.

---

## Problem 6 — Write the OTA-update procedure stub

**Problem statement.** The capstone spec's Property 8 requires "a documented update procedure that does not brick the robot." Write a one-page `OTA-PROCEDURE.md` describing how you would push a software update to the robot and roll it back if it fails. This is a document this week, not an implementation; the implementation is Phase 6 (a C7 wire-extension).

**Acceptance criteria.**

- `OTA-PROCEDURE.md` describes: how an update is delivered, how it is verified before activation (health check / pre-flight), how the previous version is retained, and how a rollback is triggered if the update fails its post-update pre-flight.
- The procedure references the pre-flight check from this week as the post-update health gate (an update that fails pre-flight is automatically rolled back).
- One sentence states the brick-avoidance invariant: the robot never deletes the known-good version until the new version passes pre-flight.

**Hint.** The A/B-partition pattern (two slots, atomic switch, rollback to the other slot) is the standard brick-avoidance design. Your pre-flight check is the natural post-update gate — reuse it.

**Estimated time.** 30 minutes.

---

## Submission

Push the entire `chaos-drills/`, `safety-case/`, `dashboard/`, `notes/`, and `OTA-PROCEDURE.md` artifacts to your Week 40 capstone repository. The instructor reviews by:

1. Reading each artifact and confirming it follows the template/structure from the lectures.
2. Re-running `preflight-check` and the two measurement scripts on the reviewer's copy of your stack and checking the numbers reproduce within reason.
3. Confirming the safety-case hazard list and FMEA name real mitigations with owning artifacts.

A submission whose scaffolds exist, follow the templates, and whose measurements reproduce is a pass. The most common review-fail is a measurement note that reports a target number with no method — report what you measured and how, not what you wish you measured.

If anything is unclear, post the question in the Week 40 channel before the homework deadline.

---

## Rubric (100 points)

| Problem | Points | What earns them |
|---------|-------:|-----------------|
| P1 — Planner-deadlock chaos drill | 15 | All six parts; concrete detection signal; 60 s deadline; operator-detectable degradation. |
| P2 — Pre-flight against live stack | 20 | First + final output recorded; each failure diagnosed by defect category and fixed; final all-pass. |
| P3 — Acceptance numbers | 20 | Both numbers measured with method; "system ready" defined; honest gap-and-action-item if a target is missed. |
| P4 — Hazard list + FMEA | 15 | Six+ hazards across base and arm; three FMEA rows with RPN and named mitigations. |
| P5 — Foxglove layout + narration | 20 | Layout committed and loads; narration test run with a peer; dark-layer fixes documented. |
| P6 — OTA procedure | 10 | Delivery, verification, retention, rollback documented; pre-flight as the post-update gate; brick-avoidance invariant stated. |

---

**References**

- C24 capstone specification — `SYLLABUS.md`
- Google SRE — "Postmortem Culture": <https://sre.google/sre-book/postmortem-culture/>
- Principles of Chaos Engineering: <https://principlesofchaos.org/>
- MIL-STD-1629A — FMEA procedure (S/O/D, RPN): search "MIL-STD-1629A FMEA"
- ISO 13482:2014 — Personal care robots (summary): <https://www.iso.org/standard/53820.html>
- Foxglove — Layouts: <https://docs.foxglove.dev/docs/visualization/layouts>
