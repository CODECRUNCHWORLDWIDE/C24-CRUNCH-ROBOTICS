# Exercise 1 — Design the Drill

**Type:** Written, no code.
**Estimated time:** ~50 minutes.
**Outcome:** A defensible experiment design for *both* gameday drills — the document that turns a live drill from a demo into science (Lecture 1 §6).

You do not get to improvise gameday. A senior engineer writes the experiment down first: what "healthy" means, exactly what they will break, what they predict will happen, and how they will undo it if it goes wrong. This exercise is that document. You will reference it during the live drill (the challenge) and grade your robot's behavior against your *prediction*, which is the only way the drill teaches you anything.

---

## What you must produce

For **each** of the two drills — sensor dropout and doorway deadlock — write the five-part design from Lecture 1 §6.

### Part A — Drill 1: Sensor dropout mid-task

1. **Steady-state hypothesis (measurable).** Define "healthy" as numbers, not adjectives. E.g. "`/scan` at ≥ 9 Hz, costmap age < 0.5 s, forward progress ≥ 0.1 m/s, robot-health = OK." Vague hypotheses cannot be tested.
2. **The injection.** Exactly what you do and when. E.g. "`kill -9` the `lidar_driver` PID at T+0, while the robot is driving toward the bench mid-task." Specify `kill -9` (brutal, realistic) vs `lifecycle shutdown` (graceful) and say why.
3. **The blast radius — and the E-stop proof.** What the injection can affect (LiDAR topic → costmap → Nav2 → task) and the *proof* that the software E-stop path is **outside** it (separate node/process/executor, subscribes to nothing the fault poisons). This proof is mandatory (Lecture 2 §1).
4. **The predicted detection + response.** Your prediction, with times: "detected within 500 ms via the `/scan` deadline event; health → DEGRADED; BT drops the LiDAR costmap layer and caps velocity at 0.2 m/s; operator alert on the dashboard within 2 s; safe-abort the grasp because it needs LiDAR." Commit to numbers — the drill grades reality against this.
5. **The abort plan.** The human's finger on the physical E-stop, and the exact command to reverse the injection (`ros2 lifecycle set lidar_driver activate` or restart), for the case where the robot does *not* degrade gracefully.

### Part B — Drill 2: Planner deadlock at a doorway

Same five parts, for the doorway deadlock:

1. **Steady-state hypothesis** — including the forward-progress metric (≥ 0.1 m over a 5 s window) and a healthy replan rate.
2. **The injection** — "`ros2 topic pub` a moved obstacle partially blocking the doorway at T+0," with the obstacle pose. *Partially*, not fully — a fully blocked door is a trivial "goal unreachable," not a deadlock.
3. **The blast radius + E-stop proof** — as above.
4. **The predicted detection + response** — "deadlock detected within ~8 s on the 3rd replan-without-progress cycle; ladder rung 1 (relaxed replan); if that fails, rung 3 (operator-assist request); recovery or assist-request within 60 s; operator-detectable throughout."
5. **The abort plan** — how you remove the obstacle and reset.

---

## Acceptance criteria

- [ ] Both drills have all five parts, with **measurable** hypotheses (numbers, not adjectives).
- [ ] Each injection is specific (which process/topic, when, `kill -9` vs lifecycle, and why).
- [ ] Each blast radius includes a **proof the E-stop path is outside it** — the safety invariant from Lecture 2 §1.
- [ ] Each predicted response commits to **detection, operator-alert, and recovery times** you will grade reality against.
- [ ] Each drill has a concrete, reversible abort plan with the exact reversal command.

## Deliverable

`drill-design.md`, committed next to your capstone. During the live drill you will fill in an "actual vs predicted" column next to each prediction — that delta is the heart of your postmortem's "what didn't" section.

---

## Hint

The part learners skip is the **E-stop proof** (part 3). It is the most important part. Open your launch file and actually trace it: is the E-stop node in the same process as anything the LiDAR feeds? Does it subscribe to a topic that goes stale when the LiDAR dies? If yes, your safety path is *inside* the blast radius and the drill will expose it — better to find that now, in the design, than live on the clock. The whole point of writing the design is to find these gaps before gameday, not during it.
