# Week 19 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 20. Answer key is at the bottom — don't peek.

---

**Q1.** What problem with finite state machines do behavior trees primarily solve?

- A) FSMs are too slow to execute.
- B) The state-explosion problem: FSM logic lives in transitions, which grow quadratically and don't compose, so adding a behavior means rewiring many existing states. BTs move logic into a composable tree.
- C) FSMs can't run on robots.
- D) FSMs use too much memory.

---

**Q2.** What are the three statuses a behavior-tree node can return?

- A) `TRUE`, `FALSE`, `ERROR`
- B) `SUCCESS`, `FAILURE`, `RUNNING`
- C) `START`, `STOP`, `WAIT`
- D) `OK`, `RETRY`, `ABORT`

---

**Q3.** Why is the `RUNNING` status the key innovation that makes BTs work for robots?

- A) It makes the tree tick faster.
- B) A robot action takes seconds; `RUNNING` ("not done, tick me again") lets the action report progress without *blocking*, so the tree keeps ticking and can re-evaluate higher-priority branches and interrupt the action.
- C) It logs errors automatically.
- D) It is required by ROS2.

---

**Q4.** A plain `Sequence` (with memory) ticks `IsBatteryOK` then `Navigate`. On the *second* tick (while `Navigate` is `RUNNING`), does it re-tick `IsBatteryOK`?

- A) Yes, every tick.
- B) No — a plain `Sequence` has memory; it resumes at the running child (`Navigate`) and does not re-check `IsBatteryOK`. (That's why it can't reactively yield.)
- C) Only if the battery changed.
- D) Only on the first tick.

---

**Q5.** You need the robot to **yield the moment** a person appears, even while it's driving to a waypoint. Which control node makes this possible?

- A) A plain `Sequence`.
- B) A `ReactiveSequence` — it re-ticks all children from the left every tick, so the person-check is re-evaluated continuously and can interrupt (halt) the running navigation.
- C) A `Parallel` with `success_count=2`.
- D) An `Inverter`.

---

**Q6.** What does a `Fallback` (Selector) node return, and what pattern does it implement?

- A) It returns `SUCCESS` only if all children succeed (AND).
- B) It ticks children in order and returns `SUCCESS` on the *first* child that succeeds, `FAILURE` only if all fail (OR) — the recovery pattern: normal behavior first, fallback behavior second.
- C) It runs all children in parallel.
- D) It always returns `RUNNING`.

---

**Q7.** A `ReactiveSequence` interrupts a running `NavigateToWaypoint` action (a person appeared). What must the action implement so the robot actually *stops*?

- A) Nothing; the tree stops it automatically.
- B) Its halt handler (`onHalted` in BT.CPP) must cancel the underlying nav goal. Without it, the action node halts in the tree but the robot keeps driving.
- C) A faster tick rate.
- D) An `Inverter`.

---

**Q8.** How do you implement "retreat to the charger if blocked for more than 60 seconds" with *tree structure* (no special-case code)?

- A) A timer in a callback that sets a flag.
- B) Wrap the "wait for the person to leave" behavior in a `Timeout(60s)` decorator under a `Fallback` whose second child is the retreat — the timeout fires `FAILURE`, routing the fallback to retreat.
- C) A `Parallel` with three children.
- D) An `Inverter` on the wait.

---

**Q9.** Why must a condition node (re-ticked every cycle by a reactive parent) be fast and side-effect-free?

- A) It doesn't matter; conditions can do anything.
- B) Reactive nodes re-tick conditions every tick (10–30 Hz); if a condition did expensive work or had side effects, it would choke the tree and fire its effects repeatedly. Conditions should read a cached value; the expensive work happens in a separate callback.
- C) Conditions can't return `RUNNING`, so they must be slow.
- D) Side effects make the tree compile slower.

---

**Q10.** In BehaviorTree.CPP, what is the blackboard?

- A) A logging facility.
- B) The shared key-value store that nodes read from and write to via typed ports, so they pass data (a waypoint, a detection) without calling each other directly.
- C) The XML file format.
- D) The Groot 2 display.

---

**Q11.** What does Groot 2's Monitor mode give you that logs do not?

- A) Faster ticking.
- B) A live view of *which node is running right now* — nodes change color as they tick — so you can see exactly which branch the robot is in (and spot a stuck-green action that never returns) instead of guessing from logs.
- C) The ability to edit C++ code.
- D) Automatic bug fixing.

---

**Q12.** Your patrol tree: when a person *leaves* within the timeout, the robot **retreats** instead of resuming the patrol. This is a structural bug. What kind?

- A) A QoS mismatch.
- B) The wait subtree's success/failure polarity is wrong — leaving should make the wait *succeed* (resume patrol), but the structure makes it fail (trigger retreat). You must trace every scenario, because "loads and looks right" isn't "does the right thing."
- C) The tick rate is too low.
- D) Groot 2 isn't connected.

---

**Q13.** When is a finite state machine the *right* choice over a behavior tree?

- A) Never; BTs are always better.
- B) For a genuinely small, fixed task (e.g., a two-state estopped/not-estopped toggle) — wrapping it in a tree is needless ceremony. BTs win for complex, layered, growing tasks.
- C) For high-speed control loops only.
- D) Only in simulation.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The state-explosion problem; BTs move logic from non-composing transitions into a composable tree. (Lecture 1 §1.)
2. **B** — `SUCCESS`, `FAILURE`, `RUNNING`. (Lecture 1 §2.1.)
3. **B** — `RUNNING` lets a long action report progress without blocking, enabling reactivity. (Lecture 1 §2.2.)
4. **B** — A plain `Sequence` has memory; it doesn't re-check the earlier child. (Lecture 1 §2.3, §3.1.)
5. **B** — `ReactiveSequence` re-ticks all children every tick and can halt the running action. (Lecture 1 §3.4.)
6. **B** — `Fallback` is OR; first success wins; the recovery pattern. (Lecture 1 §3.2.)
7. **B** — The action's halt handler (`onHalted`) must cancel the nav goal, or the robot keeps moving. (Lecture 1 §5.2, Lecture 2 §1.2.)
8. **B** — `Timeout` decorator under a `Fallback` routing to retreat — fail-safe as tree structure. (Lecture 1 §4.)
9. **B** — Reactive re-ticking means conditions must be cheap and side-effect-free; read a cached value. (Lecture 1 §5.1, §6.2.)
10. **B** — The blackboard is the shared key-value store nodes use via ports. (Lecture 2 §2.1.)
11. **B** — Groot 2 Monitor shows the live running branch and stuck-green hangs. (Lecture 2 §2.2.)
12. **B** — Wrong success/failure polarity in the wait subtree; trace every scenario. (Lecture 2 §3.2.)
13. **B** — An FSM is fine for a small fixed task; BTs win for complex/growing ones. (Lecture 1 §1.2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
