# Week 24 — Quiz

Thirteen questions on composing Nav2 and MoveIt2, the four integration defects, the pre-flight ritual, functional-safety vocabulary, the hazard log, and the 200 ms E-stop. Take it with your lecture notes closed. Aim for 11/13 before you sign the milestone. Answer key at the bottom — don't peek.

---

**Q1.** You compose Nav2 and MoveIt2 into one graph and the arm logs `Could not find a connection between 'base_link' and 'arm_base'`, even though `tf2_echo base_link arm_base` sometimes prints the transform. The most likely root cause is:

- A) A QoS reliability mismatch on `/scan`.
- B) The `base_link → arm_base` transform was broadcast on `/tf` (`VOLATILE`) instead of `/tf_static`; `move_group` started late and a `VOLATILE` publisher does not replay to late subscribers.
- C) MoveIt2 cannot plan for a 6-DOF arm.
- D) The base and arm are in different `ROS_DOMAIN_ID`s.

---

**Q2.** Which of the four canonical Phase-3 integration defects is described by: "`move_group` hangs forever on 'waiting for joint states' because the arm's controller manager was scheduled to start after `move_group`"?

- A) The frame/timing mismatch.
- B) The bring-up-order deadlock.
- C) The joint-states/namespace collision.
- D) The controller-fights-controller clash.

---

**Q3.** In the composed launch, you put the base under a `base` namespace and the arm under an `arm` namespace. What happens to the TF frames `base_link` and `arm_base`?

- A) They become `/base/base_link` and `/arm/arm_base`; frames are namespaced like topics.
- B) They stay `base_link` and `arm_base`; `PushRosNamespace` namespaces topics, not TF frames — and that is correct, because the TF tree is one tree.
- C) The frames are deleted and must be re-broadcast.
- D) Namespacing breaks TF entirely; you must never namespace a robot with an arm.

---

**Q4.** Why does the pre-flight check's clock-advancing check run **first**, before any topic-rate check?

- A) Alphabetical ordering of the checks.
- B) A frozen sim clock (a common Gz integration footgun) makes every rate computed against the ROS clock lie, so the clock must be trusted before any rate is.
- C) The clock check is the fastest.
- D) The order of pre-flight checks is arbitrary.

---

**Q5.** The pre-flight check node calls `sys.exit(1)` when any check fails. Why is the exit code "load-bearing"?

- A) It is not; it is a convenience for the developer reading the terminal.
- B) A launch file or CI step gates the run on the node returning 0, so a non-zero exit deterministically aborts the run rather than letting it proceed on a broken precondition. A failed pre-flight is a safety-relevant abort.
- C) ROS2 requires every node to exit with a status code.
- D) The exit code sets the node's lifecycle state.

---

**Q6.** In the ordered, safety-first lifecycle bring-up, what is the actual invariant that protects against an unguarded robot?

- A) The controller server must never be activated.
- B) Nothing that *dispatches a motion goal* (the behavior tree) activates before the safety wrapper; a controller being live-but-idle behind an un-dispatched goal is fine.
- C) The arm must activate before the base.
- D) All nodes must activate simultaneously.

---

**Q7.** Functional safety defines risk as:

- A) The severity of the harm alone.
- B) The probability of occurrence alone.
- C) Severity × probability of occurrence; a hazard near a person who cannot avoid it ranks higher than the same hazard in a cage.
- D) The number of lines of safety code.

---

**Q8.** A controller goes unstable and the base runs away. Which fail-safe category is appropriate, and which is explicitly *forbidden*?

- A) Fail-operational is appropriate; fail-stop is forbidden.
- B) Fail-stop is appropriate (kill motion immediately); fail-safe-state is forbidden because the actuator is suspect — you do not ask a runaway controller to perform a careful retraction.
- C) Fail-safe-state is appropriate; fail-stop is forbidden.
- D) All three categories are equivalent for a runaway.

---

**Q9.** Why does a deployable robot need a *hardware* E-stop in addition to a software E-stop?

- A) Hardware E-stops are cheaper.
- B) The software E-stop is part of the same software that might be the thing that failed; the hardware E-stop physically removes enable/power independent of software, so it works precisely when the software is the failure.
- C) ROS2 requires a hardware E-stop.
- D) The hardware E-stop is faster than 200 ms by definition; the software one is always slower than 200 ms.

---

**Q10.** Your `/safety/estop` topic is published `VOLATILE`. A controller node that subscribes *after* the E-stop was latched receives nothing and keeps moving. In the hazard log, what is this?

- A) A networking nicety, severity 1.
- B) A severity-9 hazard ("E-stop missed by a late-joining node"); the fix is `RELIABLE`/`TRANSIENT_LOCAL` durability so the late subscriber still receives the latch.
- C) Not a hazard; the controller should have subscribed earlier.
- D) A frame/timing mismatch.

---

**Q11.** For the 200 ms E-stop budget, why is canceling motion *only* through the behavior tree's tick too slow?

- A) The BT cannot cancel actions at all.
- B) A BT ticking at, say, 10 Hz can take up to 100 ms just to *see* the latch on its next tick, plus more to halt the running leaf — that alone can blow the 200 ms budget, so the safety node also cancels the actions directly and zeroes `/cmd_vel`.
- C) The BT runs on a separate computer.
- D) Behavior trees are deprecated in Jazzy.

---

**Q12.** Measuring the E-stop latency on the composed robot, you must report the latency of:

- A) The base only, because the base is the dangerous half.
- B) The *later* of the base stop and the arm stop — the robot is not stopped until *both* halves are; reporting only the fast base measurement while the arm keeps executing is the trap.
- C) The arm only.
- D) Whichever half stops first.

---

**Q13.** What is the honest claim to make about your robot and ISO 13482 after this week?

- A) "This robot is ISO 13482 certified."
- B) "This hazard analysis is structured against ISO 13482's hazard categories" — you *frame* against the standard and cite clauses; certification is a formal audited process beyond a course.
- C) ISO 13482 does not apply to robots.
- D) Framing and certification are the same thing.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — A fixed relationship (the arm bolted to the base) is a *static* transform and belongs on `/tf_static` (`RELIABLE`/`TRANSIENT_LOCAL`, deep history) so a late-joining `move_group` still receives it. Broadcast `VOLATILE` on `/tf`, a late subscriber misses the one-shot. `tf2_echo` catching it intermittently is the masking trap. (Lecture 1 §1.8.)
2. **B** — The bring-up-order deadlock: a node blocks on an input from a node activated later. The fix is in the bring-up order, not the node. (Lecture 1 §1.3, defect 2.)
3. **B** — `PushRosNamespace` namespaces topics, not TF frames. Frames stay global, which is correct — the TF tree is one tree. The topic-vs-frame asymmetry trips people up. (Lecture 1 §1.4.)
4. **B** — A frozen sim clock makes every rate check compute against a stopped clock and lie. The clock check runs first so the rate checks are trustworthy. (Lecture 1 §1.6.)
5. **B** — The exit code is the contract: a launch file or CI gates the run on the check returning 0, so a failure deterministically aborts. A failed pre-flight is a safety-relevant abort. (Lecture 1 §1.6.)
6. **B** — The invariant is that nothing that *dispatches* a motion goal activates before the safety wrapper. A controller live-but-idle behind an un-dispatched goal is fine; the orchestrator that would dispatch is what waits for the leash. (Lecture 1 §1.5.)
7. **C** — Risk = severity × probability (ISO 12100). Low avoidability (a person who can't get out of the way) raises the probability factor, which is why a shared-space robot's bar is higher. (Lecture 2 §2.1.)
8. **B** — Fail-stop for a runaway (kill motion now); fail-safe-state is forbidden because it asks a *suspect* actuator to perform a careful final motion. Trust the actuator → fail-safe-state is allowed; suspect it → fail-stop only. (Lecture 2 §2.2.)
9. **B** — The software E-stop can be taken down by the same failure it's meant to handle (wedged node, deadlocked executor). The hardware E-stop is independent of software and works when the software is the failure. A deployable robot has both. (Lecture 2 §2.3.)
10. **B** — A severity-9 hazard. Durability is not a networking nicety here; `RELIABLE`/`TRANSIENT_LOCAL` is the difference between an E-stop that works and one that silently doesn't for a late subscriber. The Week 5 lesson, now safety-critical. (Lecture 2 §2.4.)
11. **B** — The BT's tick rate adds latency before it even sees the latch, plus halt time; that can exceed 200 ms. The safety node cancels the actions directly (the fast path) and zeroes `/cmd_vel`; the BT's `ReactiveFallback` is a correct *secondary* path for clean state. (Lecture 2 §2.5, Lecture 1 §1.7.)
12. **B** — The robot-stopped latency is the *later* of the two halves. Measuring only the fast base while the arm keeps executing is the trap — half the robot is still moving toward a person. Cancel the arm goal directly and report the max. (Lecture 2 §2.6, Challenge 1.)
13. **B** — You *frame against* the standard's hazard categories and cite clauses; you do not *certify* (a formal audited process beyond a course). The precise claim earns respect; the inflated one earns distrust. (Lecture 2 §2.7.)

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially Lecture 1 on the four integration defects and Lecture 2 on the fail-safe categories and the E-stop. If you scored 11 or higher, you are ready to stand the composed system up: head to the [homework](./homework.md) and the [mini-project](./mini-project/README.md).
