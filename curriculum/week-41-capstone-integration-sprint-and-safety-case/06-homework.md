# Week 41 Homework

Six concrete deliverables that feed directly into the graded mini-project. The full set should take about **4 hours**. Work in your capstone repository under `safety-case/` so each item produces a real commit you can point a reviewer at. Nothing here is busywork — every item is a section or an artifact the mini-project assembles.

Each problem includes a **problem statement**, **deliverables**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Pick and justify your standard

**Problem statement.** Decide which standard(s) your capstone safety case is framed against — ISO 13482 (personal-care/service), ISO 10218-1/-2 (industrial manipulator + application), or both, plus ISO/TS 15066 if your arm is collaborative. Write one tight paragraph justifying the choice against your robot's *type* (mobile servant? physical assistant? mobile manipulator?).

**Deliverables.** `safety-case/standard-choice.md` — the paragraph, plus a one-line statement of which clauses you expect to be most relevant.

**Acceptance criteria.**
- The choice is justified by the robot type and where it operates, not by which standard is easiest.
- If your robot is a mobile manipulator near people, you chose *both* families (this is the common correct answer for C24).
- Committed.

**Hint.** A pure delivery base near people → 13482. A fenced arm → 10218. A base *and* an arm near people → both, because your robot has the hazards of both machines. ISO/TS 15066 enters only if the arm is *meant* to share space and may contact people.

**Estimated time.** 20 minutes.

---

## Problem 2 — The energy-source hazard sweep

**Problem statement.** Run the energy-source method (Lecture 1 §6) across your robot. For each energy source — base kinetic, arm kinetic + potential, stored mechanical, electrical/battery, thermal, pinch/shear, and information (misperception/mis-grounding/deadlock) — list at least one hazard. You should end with **at least 12 hazards**, and at least two must be autonomy-information hazards.

**Deliverables.** Rows added to `safety-case/safety.yaml` (the `hazards:` section), in the exercise-3 format, with honest S/P/E ratings.

**Acceptance criteria.**
- ≥ 12 hazards, covering every energy source above.
- ≥ 2 information hazards (e.g. "policy grounds an instruction to a sharp object," "planner deadlocks at a doorway and the base jitters into a wall").
- Running `python3 exercise-03-hazard-log-fmea.py safety.yaml` produces a clean table with at least one HIGH or INTOLERABLE row.
- Committed.

**Hint.** Don't forget the gravity hazard: the arm falling on power loss. Juniors miss it because they think "power off = safe," but an arm with no brake falls *harder* when the power dies. Walk the sources mechanically; don't brainstorm.

**Estimated time.** 1 hour.

---

## Problem 3 — Five FMEA rows for the software stack

**Problem statement.** Write **five FMEA rows** for the *software* parts of your stack — the parts a mechanical-safety mindset ignores: the EKF/localizer, the global/local planner, the learned policy, the safety filter, and the behavior tree (or DDS/network). For each: failure mode, effect, cause, current controls, and honest S/O/D scores.

**Deliverables.** Rows added to `safety-case/safety.yaml` (the `fmea:` section).

**Acceptance criteria.**
- Exactly the five software subsystems above are covered (one row minimum each).
- The "safety filter fails to engage" row is present, with severity 9 or 10 and an honest (poor) detection score.
- Generating `03-fmea.md` flags the right rows critical under the dual cutoff.
- Committed.

**Hint.** For the policy row, the failure mode is "outputs an out-of-distribution action" or "grounds a language instruction incorrectly," the effect is "unsafe action reaches the actuators," and the *real* control is the confidence gate + classical fallback — not "we tested it."

**Estimated time.** 1 hour.

---

## Problem 4 — Wire and trip the watchdog

**Problem statement.** Take the exercise-2 watchdog + confidence-gate node, finish it (if you haven't), and demonstrate it tripping. Kill a critical sensor (Path A: unplug/`kill` the driver; Path B: stop the sim sensor or `ros2 lifecycle` it down) and capture the software E-stop latching within its deadline.

**Deliverables.** The runnable node in `safety-case/mitigations/`, plus `safety-case/evidence/watchdog-trip.log` (or a short `ros2 bag` + a note) showing `/safety/estop_state` going `true` after the sensor goes silent, and `/cmd_vel_safe` holding zero.

**Acceptance criteria.**
- `python3 exercise-02-watchdog-and-confidence-gate.py --selftest` prints `SELFTEST PASSED`.
- The captured evidence shows the latch firing after the injected silence, within the configured deadline.
- The deadline is justified in a comment or note in distance-on-stale-data terms (deadline × top speed).
- Committed.

**Hint.** If you don't have hardware (Path B), `ros2 lifecycle set /your_lidar shutdown` or simply `kill` the sim sensor node is your fault-injection lever — the same lever the Week 46 chaos drill pulls. Wire it now.

**Estimated time.** 45 minutes.

---

## Problem 5 — One residual-risk statement, signed

**Problem statement.** Pick your single highest post-mitigation hazard and write a complete residual-risk statement for it: quantify the remainder against a standard, argue ALARP, and sign it with the C24 marker line. This is the hardest 30 minutes of the week because it forces you to commit to a number and a name.

**Deliverables.** `safety-case/residual-risk-sample.md` containing the statement and the marker line.

**Acceptance criteria.**
- The remainder is *quantified* (a speed, a force, a distance) and tied to a standard (e.g. ISO/TS 15066 body-region threshold).
- ALARP is argued: what further mitigation you considered and why the remainder is reasonably practicable.
- Ends with the marker: `Residual risk: ACCEPTED by <name> on <date>  basis: …  ALARP: yes  conditions: …`
- It does **not** claim zero residual risk anywhere.
- Committed.

**Hint.** Compute one real number. For an arm contact: peak force ≈ effective mass × speed change / contact time, or just cite your validated speed-gate limit (≤ 0.25 m/s) and the corresponding force, and compare to the 15066 quasi-static threshold for that body region. A number a skeptic can check beats a paragraph of reassurance.

**Estimated time.** 30 minutes.

---

## Problem 6 — Fill the pre-flight checklist for one real run

**Problem statement.** Take the path-appropriate pre-flight checklist (Lecture 2 §2 for Path A, §3 for Path B), put it in your repo, and *run it* once for real — every box, in order. Capture the result, including any item that failed and what you did about it.

**Deliverables.** `safety-case/preflight-checklist.md` filled in for one session, with timestamps and a pass/fail per item, plus a one-line note on any failure and its resolution.

**Acceptance criteria.**
- Every item is marked, in order, for one real bring-up (Path A) or cold-boot session (Path B).
- The hardware-E-stop-continuity item (Path A) or the clean-cold-boot-under-60s item (Path B) is genuinely verified, not assumed.
- If an item failed, the note says what you did — "skipped" is not an acceptable resolution.
- Committed.

**Hint.** The point of running it for real is that you *will* find an item that's red the first time — an orphaned node, an E-stop you assumed was wired, a cold boot that takes 90 seconds. That discovery is the entire value. Don't paper over it; fix it and record it.

**Estimated time.** 25 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 | 20 min |
| 2 | 1 h 0 min |
| 3 | 1 h 0 min |
| 4 | 45 min |
| 5 | 30 min |
| 6 | 25 min |
| **Total** | **~4 h 0 min** |

---

## Rubric

| Criterion | Weight | What "great" looks like |
|-----------|-------:|-------------------------|
| Hazard breadth | 25% | Every energy source covered; the gravity and information hazards are present, not missed |
| FMEA honesty | 20% | Software subsystems scored honestly; the worst mode has a poor detection score, not a flattering one |
| Watchdog evidence | 20% | The latch is *shown* firing on injected silence, with a justified deadline — not asserted |
| Residual-risk discipline | 20% | Quantified, ALARP, signed, never claims zero |
| Pre-flight rigor | 15% | Run for real, in order; the critical item genuinely verified; failures recorded and fixed |

When you've finished all six, you have most of the mini-project's raw material already in `safety-case/`. Push your repo and open the [mini-project](./07-mini-project/00-overview.md) — the weekend's job is assembling these pieces into one coherent, signed safety case.
