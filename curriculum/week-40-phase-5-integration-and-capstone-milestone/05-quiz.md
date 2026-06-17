# Week 40 — Quiz

Thirteen questions on reading the capstone spec as a contract, the kickoff ritual, the integration defects, observability, and the milestone acceptance numbers. Take it with your lecture notes closed. Aim for 11/13 before you sign the milestone. Answer key at the bottom — don't peek.

---

**Q1.** The capstone acceptance criteria are joined by the phrase "a capstone passes **if and only if**" followed by five conditions. You meet four of the five. What is your grade outcome at the gate?

- A) Pass with a minor finding; four of five is a strong majority.
- B) Fail the gate. "If and only if" is a biconditional — all five are necessary; there is no partial credit at the capstone gate.
- C) Pass, because the safety case can be re-signed later.
- D) Incomplete; the panel averages the five into a percentage.

---

**Q2.** The spec says "PID at minimum for the base; MPC bonus." Reading this like a contract, what do you owe?

- A) Both PID and MPC; "bonus" means extra-credit-but-required.
- B) MPC, because it is the more advanced controller and the spec mentions it.
- C) PID discharges the obligation; MPC is explicitly optional. Shipping PID and skipping MPC is a defensible non-goal.
- D) Neither; the base controller is the arm's responsibility via MoveIt2.

---

**Q3.** In the "what I heard" requirements-traceability table, a row's **owning-artifact** cell is empty. What does that mean?

- A) The requirement is satisfied by default.
- B) A gap: a requirement that nothing in your system owns. It is a finding to record and close, not a cell to leave blank.
- C) The requirement is optional.
- D) The table is malformed; every requirement always has an owner.

---

**Q4.** Why does the pre-flight check's clock-advancing check run **first**, before any topic-rate check?

- A) Alphabetical ordering of the checks.
- B) A frozen sim clock (a common Gz/Isaac integration footgun) makes every rate computed against `get_clock().now()` lie, so the clock must be verified before any rate is trusted.
- C) The clock check is the fastest and gets it out of the way.
- D) It does not matter; the order of pre-flight checks is arbitrary.

---

**Q5.** The pre-flight check node calls `sys.exit(1)` when any check fails. Why is the exit code described as "load-bearing"?

- A) It is not; it is a convenience for the developer reading the terminal.
- B) A launch file or CI step gates the run on the node returning 0, so a non-zero exit deterministically aborts the run rather than letting it limp forward on a broken precondition.
- C) ROS2 requires every node to exit with a status code.
- D) The exit code sets the node's lifecycle state.

---

**Q6.** Which of the four canonical integration defects is described by: "the planner reads a detection that is older than its own tolerance because `/perception/objects` publishes slower than the BT ticks"?

- A) The frame/timing mismatch.
- B) The stale-perception race.
- C) The lifecycle bring-up-order deadlock.
- D) The safety-clamp/controller fight.

---

**Q7.** The pre-flight check verifies `/perception/objects` is publishing at its required rate. Does that fully prevent the stale-perception race at runtime?

- A) Yes; if the rate is correct, the data is always fresh.
- B) No. Pre-flight verifies the *rate* once at bring-up; the runtime guard against using a stale detection (a stamp-age check at the moment of use) belongs in the BT condition node, not the pre-flight.
- C) Yes, as long as QoS is `RELIABLE`.
- D) No, because rate checks are unreliable in sim.

---

**Q8.** In the ordered lifecycle bring-up, why must the safety wrapper activate **before** any controller can command the robot?

- A) The safety wrapper publishes the clock the controllers need.
- B) It is the leash: if a controller could command motion before the safety wrapper is active, the robot could move unguarded. The activation order is a safety property, not a convenience.
- C) MoveIt2 will not plan until the safety wrapper is active.
- D) The lifecycle manager requires alphabetical activation order.

---

**Q9.** The Week 40 milestone requires "no manual intervention." Per the Exercise-1 ambiguity resolution, which of the following counts as manual intervention?

- A) Pre-positioning the red cup on the bench before the run starts.
- B) Publishing the instruction once to `/instruction`.
- C) Restarting a node that crashed mid-run to keep the run going.
- D) Loading the Foxglove layout before the run.

---

**Q10.** The "narrate the run from the screen" test means:

- A) The robot narrates its actions over a speaker.
- B) A reviewer watching only the Foxglove dashboard (terminal/logs hidden) can describe the run layer by layer in real time; if a layer goes dark on the screen, that layer is invisible and fails the observability criterion.
- C) You write a narration script and read it during the demo.
- D) The telemetry spine prints a narration to the log.

---

**Q11.** Two of the five capstone acceptance numbers are measurable *this week* at the sim milestone. Which two?

- A) Instruction success (15/20) and chaos recovery (60 s).
- B) State-estimate drift (< 0.5 m / 20 m) and cold-boot time (< 60 s).
- C) Safety-case signature and chaos recovery.
- D) Instruction success and cold-boot time.

---

**Q12.** The chaos-drill template has six parts: steady-state hypothesis, injected fault, detection signal, graceful-degradation path, recovery deadline, and postmortem. Why fill it in *this* week rather than at Week 46 when the drills are actually run?

- A) Week 46 has no time allocated for it.
- B) Filling in the template now reveals exactly what to build before Gameday (the watchdog, the `/health/*` topics, the `DEGRADED` BT branch, the dashboard panels), turning Week 46 from invention under live-grading pressure into a rehearsed play.
- C) The template is graded at Week 40, not Week 46.
- D) The instructor injects the faults at Week 40.

---

**Q13.** In the safety-case template, the **mitigations** section maps each high-RPN hazard to a control. Why is this section the bridge between the safety case and the rest of your system?

- A) It is the longest section.
- B) Each mitigation cites the node/topic that implements it (the 200 ms E-stop, the workspace clamps, the perception confidence gate, the classical fallback) — the same "owning artifact" column from the Lecture-1 contract — so the safety case is grounded in real components, and a hazard with no mitigation is a finding the panel will catch.
- C) It is where the FMEA table lives.
- D) It is required by ROS2 Jazzy.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — "If and only if" is a biconditional; all five conditions are necessary. The capstone gate has no partial credit (partial credit lives in the weekly rubrics). Meeting four of five fails the gate.

2. **C** — "At minimum" is a floor; "bonus" is an explicitly optional ceiling. PID discharges the obligation. Shipping PID and deferring MPC is a defensible, stated non-goal — and the right call when hours are tight, because the spec says you do not owe MPC.

3. **B** — An empty owning-artifact cell is a gap: a requirement nothing in your system delivers. It is a finding to record in the "Gaps" subsection and close, not a blank to ignore. Better found at kickoff than at the defense.

4. **B** — A frozen sim clock makes every rate computed against the ROS clock lie. The clock check runs first so that the rate checks are trustworthy. A frozen Gz/Isaac clock is among the most common integration footguns.

5. **B** — The exit code is the contract: a launch file or CI step gates the run on `preflight_check` returning 0, so a failure deterministically aborts the run instead of letting it proceed on a broken precondition. A failed pre-flight is a safety-relevant abort.

6. **B** — The stale-perception race: the planner/BT reads a detection older than its tolerance because the producer publishes slower than the consumer ticks. The fix is a runtime stamp-age check at the point of use.

7. **B** — Pre-flight verifies the *rate* once at bring-up; it does not prevent a single late frame from being used stale at runtime. The runtime guard — a stamp-age check before use — belongs in the BT condition node. Pre-flight catches the static precondition; the runtime guard catches the dynamic one.

8. **B** — The safety wrapper is the leash. If a controller could command motion before the wrapper is active, the robot could move unguarded. Activation order is a safety property; the lifecycle manager encodes it deliberately.

9. **C** — Restarting a crashed node mid-run to keep the run alive is manual intervention; it hides a defect behind a human. Pre-positioning the object (A) and issuing the one instruction (B) and loading the dashboard (D) are setup, not intervention, per the Exercise-1 boundary.

10. **B** — The narration test: a reviewer watching only the dashboard, with logs hidden, narrates the run layer by layer. A dark layer (one with no visible telemetry) is invisible, and invisible fails the observability criterion regardless of whether the task completed.

11. **B** — State-estimate drift (< 0.5 m / 20 m) and cold-boot time (< 60 s) are measurable at the sim milestone now. Instruction success (Week 44 eval suite) and chaos recovery (Week 46 Gameday) come later; the safety-case signature is a Week 41/48 artifact.

12. **B** — Filling in the template now surfaces exactly what to build before Gameday: the watchdog node, the `/health/*` topics, the `DEGRADED` BT branch, and the dashboard panels. Week 46 then becomes execution of a rehearsed play instead of invention under live-grading pressure.

13. **B** — The mitigations section cites, for each hazard, the node/topic that implements its control — the same owning-artifact mapping from the Lecture-1 contract. This grounds the safety case in real components and makes a hazard-without-mitigation a visible finding. It is the bridge between the safety argument and the system.

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially Lecture 1 on reading the spec and Lecture 2 on the pre-flight ritual. If you scored 11 or higher, you are ready to stand the system up: head to the [homework](./06-homework.md) and the [mini-project](./07-mini-project/00-overview.md).
