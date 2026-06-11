# Week 46 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 47. Answer key is at the bottom — don't peek.

---

**Q1.** What is a *steady-state hypothesis* in chaos engineering?

- A) A guess about what will break.
- B) A measurable definition of "the system is healthy" that you assert holds, then test by injecting a failure.
- C) The list of all possible failures.
- D) A promise that the system will never fail.

---

**Q2.** During a sensor-dropout drill, the LiDAR dies but the robot keeps driving on a cached costmap and happens not to hit anything. Is this a pass?

- A) Yes — it didn't crash.
- B) No — it never *detected* the failure; the non-crash was luck, not graceful degradation. The drill grades detection and response.
- C) Yes, if the costmap was less than 5 seconds old.
- D) Only if it reached the goal.

---

**Q3.** Why is the default failure response for a robot a *controlled stop* rather than a *retry*?

- A) Stopping is cheaper to implement.
- B) Continuing on possibly-bad state is the dangerous option for a machine moving through shared space; "when in doubt, stop" is the safe inversion of the cloud's "when in doubt, retry."
- C) Robots cannot retry.
- D) Retrying always succeeds.

---

**Q4.** Which QoS policy gives you the *fastest* detection of a sensor that stopped publishing?

- A) Reliability.
- B) The `deadline` policy — missing the expected inter-sample gap fires an event within ~one deadline period, far faster than polling.
- C) History depth.
- D) Durability.

---

**Q5.** What is the job of the *health aggregator*?

- A) To publish each sensor's raw data faster.
- B) To fuse per-sensor status into one robot-health signal and decide which losses are survivable (DEGRADED) vs not (FAULT).
- C) To restart dead sensors automatically.
- D) To record the rosbag.

---

**Q6.** When the LiDAR dies, why must you *remove* the LiDAR costmap layer rather than let it freeze?

- A) Freezing uses more memory.
- B) A frozen layer lets the planner reason against a stale snapshot — it *lies* about the world, which is worse than having no layer.
- C) ROS2 forbids frozen layers.
- D) Removing it is faster to code.

---

**Q7.** In a shared aisle with people, the robot loses the LiDAR mid-approach to a grasp that *needs* the LiDAR. It comes to a controlled stop and flags the operator. Is safe-abort the right call?

- A) No — it should have pushed through to complete the task.
- B) Yes — continuing would require trusting state it doesn't have, in a shared space; safe-abort is the correct, defensible response, not a failure.
- C) No — safe-abort is always a failure.
- D) Only if the battery was low.

---

**Q8.** What is the *signature* of a planner deadlock at a doorway?

- A) The robot stops moving.
- B) The planner produces a new plan repeatedly *while* the robot makes no forward progress — the conjunction of replanning and not-progressing.
- C) The planner crashes.
- D) The goal becomes unreachable.

---

**Q9.** Why is "the planner is replanning a lot" *alone* not enough to declare a deadlock?

- A) Replanning is impossible.
- B) Replanning while still making forward progress is normal dynamic-obstacle avoidance; only replanning *without* progress is a deadlock.
- C) Replanning always means a deadlock.
- D) The planner never replans in normal operation.

---

**Q10.** In the recovery ladder, the robot cannot solve the deadlock autonomously and raises an operator-assist request, then waits, stopped. Is this a pass?

- A) No — needing a human is a failure.
- B) Yes — escalating to a human operator is a defined, correct behavior in a fleet; a clean assist request inside 60 s is a pass.
- C) Only if the operator responds within 1 second.
- D) No — the robot must always solve it alone.

---

**Q11.** What does the "operator-detectable within 60 seconds" bar require?

- A) Only that recovery happens within 60 seconds.
- B) Both that recovery happens within 60 s *and* that the fault and recovery are visible to a human on the dashboard — a recovery only in the logs fails the operator-detectable half.
- C) Only that the fault appears in a log file.
- D) That an email is sent.

---

**Q12.** In a postmortem, what distinguishes the *root cause* from a *contributing factor*?

- A) Nothing — they're the same.
- B) The root cause is the one thing without which the failure does not happen; contributing factors shaped the outcome but were not THE cause. Conflating them leads you to "fix" a factor and leave the cause live.
- C) The root cause is whoever is to blame.
- D) Contributing factors are always more important.

---

**Q13.** Why must the postmortem timeline come from a rosbag rather than memory?

- A) Bags are required by ROS2.
- B) A gameday is a stressful two minutes; human memory of the order and timing of events is unreliable, and the 60-second bar must be measured from data.
- C) Memory is illegal in postmortems.
- D) Bags are faster to write.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — A measurable "healthy" you assert and then test by breaking something. (Lecture 1 §2.1.)
2. **B** — It never detected the failure; the non-crash was luck. The drill grades detection and response, not crash-avoidance. (Lecture 1 §1, Lecture 2 §6.)
3. **B** — Continuing on bad state is the dangerous option; "when in doubt, stop" inverts the cloud's retry instinct. (Lecture 1 §1.)
4. **B** — The `deadline` QoS event fires within ~one deadline period, far faster than polling staleness. (Lecture 1 §3.1.)
5. **B** — It fuses per-sensor status into one signal and encodes which losses are survivable (DEGRADED vs FAULT). (Lecture 1 §4.)
6. **B** — A frozen layer lies about the world; removing it forces the planner to reason with what it actually has. (Lecture 2 §2.)
7. **B** — Continuing would mean trusting absent state in a shared space; safe-abort is the correct, defensible call. (Lecture 2 §5.)
8. **B** — The conjunction: replanning *and* not progressing. (Lecture 2 §3.)
9. **B** — Replanning while progressing is normal avoidance; only replanning without progress is a deadlock. (Lecture 2 §3.)
10. **B** — Escalating to a human is a designed, correct fleet behavior; a clean assist request inside 60 s is a pass. (Lecture 2 §3, §5.)
11. **B** — Both halves required: fast *and* operator-detectable on the dashboard. (Lecture 2 §4.)
12. **B** — Root cause is the one thing without which it doesn't happen; conflating it with factors leaves the cause live. (Lecture 2 §7.)
13. **B** — Memory under stress is unreliable; the timeline and the 60-second bar must come from the bag. (Lecture 1 §7, Lecture 2 §7.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
