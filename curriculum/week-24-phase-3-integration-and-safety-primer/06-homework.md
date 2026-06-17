# Week 24 Homework

Six problems that turn this week's lectures into the integration discipline and the first safety artifacts your capstone needs. The full set should take about **5 hours**. Work in your Week 24 capstone repository so each problem produces a committed artifact you point at during the Phase 3 milestone sign-off.

The headline deliverables are **Problem 1 — the hazard log** and **Problem 3 — the E-stop latency report**, both called out by the milestone. Treat them as artifacts a reviewer reads, not journal entries.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — The hazard log (headline deliverable)

**Problem statement.** Open a new `safety/hazard-log.md` and populate it with the hazards for your specific composed mobile manipulator, expanding the first pass from Lecture 2 §2.4. Each row has: hazard, cause, effect, severity (1–10), fail-safe category (fail-stop / fail-safe-state / fail-operational), mitigation, and owning node/topic. Cover both the base (collision, runaway) and the arm (strike, pinch, dropped object), plus the QoS-durability E-stop hazard.

**Acceptance criteria.**

- `safety/hazard-log.md` lists at least eight hazards across both the base and the arm.
- Each row has a severity, a fail-safe category, a mitigation, and an owning node/topic — no empty cells. An empty owning-node cell is a gap to record, not to leave blank.
- At least one row is the "E-stop missed by a late-joining node" hazard with the `TRANSIENT_LOCAL` mitigation, and at least one row uses fail-safe-state (not fail-stop) with a one-line justification.
- For each hazard, you note whether it is an ISO 10218 (arm) or ISO 13482 (shared-space base) framing.
- Committed.

**Hint.** Your Weeks 20–23 controller failure modes are most of the rows: PID integrator wind-up, LQR validity region, MPC time-budget overrun, MoveIt2 self-collision. The "base runs away" row forbids fail-safe-state (suspect actuator); the "LiDAR dropout" row permits it (trusted actuator). Use the standards' hazard categories as prompts for the row you forgot.

**Estimated time.** 50 minutes.

---

## Problem 2 — Run the pre-flight check against your live composed stack

**Problem statement.** Take your Exercise 2 pre-flight check node, point it at your *live composed base+arm stack* (not `--demo`), and run it. Record the first output verbatim. For every check that fails, diagnose which of the four integration defects it is, fix it, and re-run until all checks pass.

**Acceptance criteria.**

- `notes/preflight-run.md` contains the first (likely-failing) pre-flight output and the final all-pass output.
- For each initial failure, a one-paragraph diagnosis naming which of the four integration defects it was (frame/timing, bring-up-order, joint-states/namespace, controller clash) and the fix.
- The final run shows all checks PASS and the node exits 0.
- Committed.

**Hint.** The most common first failures are a `base_link → arm_base` lookup that fails because the static broadcaster wasn't started or used `/tf` instead of `/tf_static`, and a `move_group` reporting `inactive` because the controller manager came up after it. Both are exactly the defects the check exists to catch.

**Estimated time.** 50 minutes.

---

## Problem 3 — The E-stop latency report (headline deliverable)

**Problem statement.** Drive the composed robot with *both halves moving*, latch `/safety/estop` mid-motion, and use `measure_estop_latency.py` (from Exercise 3) to measure the latch-to-stop latency over ten trials. Report the base latency, the arm latency, and the robot-stopped latency (the later of the two), against the 200 ms budget. Then repeat under a `stress-ng` CPU load and report whether the budget still holds.

**Acceptance criteria.**

- `safety/estop-latency-report.md` records the ten-trial distribution (mean, p95, max) for the base stop, the arm stop, and the robot-stopped (max-of-two) latency, with the command that produced each.
- The report states clearly whether the worst-case robot-stopped latency is within 200 ms, both idle and under load.
- If the budget is missed (idle or under load), the report states the gap honestly with a Phase-6 action item. A fabricated "0 ms, passed" with no method fails.
- The report confirms the E-stop cancels the *arm* goal (`FollowJointTrajectory` reaches `CANCELED`), not only the base — i.e., you avoided the trap.
- Committed.

**Hint.** The arm is the half that bites. If your E-stop only zeroes `/cmd_vel` and forgets the arm goal cancel, the arm keeps executing and your base-only number lies. Measure both; report the max. Under load, the budget that matters is the one under load, not the idle one.

**Estimated time.** 60 minutes.

---

## Problem 4 — Wire the pre-flight check as a launch gate

**Problem statement.** Make your pre-flight check a *gate*: the composed run does not start until pre-flight returns 0. Use the launch `OnProcessExit` pattern (Lecture-1 stretch / the SRE-launch idea) so the run action is only added when the pre-flight process exits successfully. Then prove the gate works by forcing one check to fail and showing the run refuses to start.

**Acceptance criteria.**

- A `launch/run_gated.launch.py` brings up the graph, runs `preflight_check`, and starts the run only on a 0 exit.
- `notes/gate-demo.md` shows two runs: one where pre-flight passes and the run starts, and one where a forced pre-flight failure (e.g., `--break tf` in demo, or a deliberately broken transform on the live stack) makes the run refuse to start.
- One sentence states why a check whose failure does not stop the run is "decoration."
- Committed.

**Hint.** The load-bearing line is the return-code branch in the `OnProcessExit` handler: `if event.returncode == 0: [run] else: [LogInfo("PRE-FLIGHT FAILED; run will NOT start")]`. The gate is not the check; the gate is what the check's result is wired to.

**Estimated time.** 45 minutes.

---

## Problem 5 — Document the hardware E-stop and its relationship to the software one

**Problem statement.** Write a one-page `safety/hardware-estop.md` describing the hardware E-stop your robot would have: which IEC 60204-1 stop category (0/1/2), what it physically removes (enable line, motor power), how it is wired independent of software, and — crucially — which failure modes it covers that the *software* E-stop cannot. This is a document (Path B) or a wiring description (Path A); not an implementation this week.

**Acceptance criteria.**

- `safety/hardware-estop.md` names the stop category and what it removes, and states the independence-from-software property.
- It lists at least two failure modes the software E-stop cannot cover (e.g., a wedged executor, a partitioned DDS graph) and explains why the hardware E-stop covers them.
- It cross-references the hazard log: which hazard rows the hardware E-stop is the mitigation (or backup mitigation) for.
- Committed.

**Hint.** The whole reason for the hardware E-stop is "what stops the robot when the bug is in the node that runs the software E-stop?" Answering that question *is* the residual-risk argument the Week 41 safety case needs. A category-0 stop (immediate power removal) is the classic hardware-E-stop behavior.

**Estimated time.** 35 minutes.

---

## Problem 6 — Add a fail-safe-state behavior and contrast it with fail-stop

**Problem statement.** Implement a second fail-safe path for a *soft* fault (a simulated perception dropout or a `/health/sensor STALE` signal): instead of the E-stop's fail-stop, command the arm to retract to a defined tucked pose before halting. Run both the fail-stop (E-stop) and the fail-safe-state (soft fault) paths and contrast them.

**Acceptance criteria.**

- A `safety/failsafe_state.py` (or a BT branch) that, on the soft-fault signal, retracts the arm to a tucked pose and then halts.
- `notes/failsafe-contrast.md` records: the fault that triggers each path, the category each uses, and why the runaway-controller fault must *not* use fail-safe-state (suspect actuator).
- The fail-safe-state path is demonstrably distinct from the E-stop path in behavior (one retracts, one halts in place).
- Committed.

**Hint.** Fail-safe-state requires the actuators you're worried about to perform a final controlled motion, so it is only valid when the actuators are *trusted* (perception dropout) and forbidden when they are *suspect* (runaway). That distinction is the lesson, not the retract animation.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Hazard log (headline) | 50 min |
| 2 — Pre-flight against live stack | 50 min |
| 3 — E-stop latency report (headline) | 60 min |
| 4 — Pre-flight as a launch gate | 45 min |
| 5 — Hardware E-stop document | 35 min |
| 6 — Fail-safe-state behavior | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo. The hazard log and the E-stop latency report are the two artifacts the Phase 3 milestone is signed against — make sure they are in the same repo as the composed launch and the pre-flight gate. Then take the [quiz](./05-quiz.md) with your notes closed.

---

## Rubric (100 points)

| Problem | Points | What earns them |
|---------|-------:|-----------------|
| P1 — Hazard log | 25 | Eight+ hazards across base and arm; severity, category, mitigation, owner per row; the QoS-durability hazard and a fail-safe-state row with justification; ISO framing noted. |
| P2 — Pre-flight against live stack | 15 | First + final output recorded; each failure diagnosed by defect category and fixed; final all-pass exit 0. |
| P3 — E-stop latency report | 25 | Base, arm, and robot-stopped latencies measured (ten trials); idle and under-load; honest gap-and-action-item if missed; arm cancel confirmed (trap avoided). |
| P4 — Pre-flight as a launch gate | 15 | Run gated on pre-flight exit code; pass-and-fail demo; the "gate is what the result is wired to" point made. |
| P5 — Hardware E-stop document | 10 | Stop category, independence, software-can't-cover failure modes, hazard-log cross-reference. |
| P6 — Fail-safe-state behavior | 10 | Distinct retract-then-halt path; contrast with fail-stop; suspect-vs-trusted actuator reasoning. |

A submission whose E-stop latency report measures only the base (ignoring the arm), or whose hazard log has empty owning-node cells, **caps at 60 points** regardless of polish — those are the load-bearing safety properties of the week, and the rubric weights them accordingly.

---

**References**

- C24 capstone specification — `SYLLABUS.md` (the 200 ms E-stop clause)
- ISO 12100 / ISO 10218 / ISO 13482 (summaries) — see `resources.md`
- IEC 60204-1 — E-stop stop categories: <https://webstore.iec.ch/publication/64761>
- MIL-STD-1629A — FMEA (severity scale): search "MIL-STD-1629A FMEA"
- About Quality of Service settings (durability for latched safety topics): <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html>
