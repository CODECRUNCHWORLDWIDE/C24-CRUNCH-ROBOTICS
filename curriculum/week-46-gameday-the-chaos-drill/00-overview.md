# Week 46 — Gameday: The Chaos Drill

Welcome to the week your robot stops being graded on what it does when everything works, and starts being graded on what it does when something breaks. This is **gameday** — a live, instructor-injected chaos drill, two intentional failures, on the clock, in front of someone with a stopwatch and a rubric. It is the single most predictive exercise in the whole track for whether you are ready to operate a robot in the real world, because in the real world things break, and the only question that matters is whether your robot makes the situation *better* or *worse* when they do.

Here is the thing nobody tells you until you have been on call for a fleet at 3 a.m. A robot that works perfectly in the demo and falls over the first time a sensor drops out is not a working robot — it is a working *demo*. The difference between the two is graceful degradation: detecting the failure, refusing to act on bad state, alerting a human, and either recovering or coming to a safe, controlled stop. That is the skill chaos engineering trains, and this week is where you find out whether your capstone has it or only pretended to.

You will run two drills, both from the syllabus and both lifted straight from the capstone acceptance criteria:

- **Drill 1 — sensor dropout mid-task.** The LiDAR is killed mid-execution of a language-conditioned task. Your robot must detect the dropout, degrade gracefully, raise an operator-detectable event on the dashboard, and either complete the task on degraded sensing or abort safely. Recovery is timed; the bar is **60 seconds**.
- **Drill 2 — planner deadlock at a doorway.** A narrow corridor is partially blocked by a moved obstacle. The planner cycles. Your robot must detect the deadlock, replan around it, request operator assist, or come to a safe stop — again with an operator-detectable event, again inside **60 seconds**.

Then you write two postmortems against a real template, because the postmortem *is* the deliverable. Surviving a chaos drill and being unable to explain why is not a pass.

## Learning objectives

By the end of this week, you will be able to:

- **Inject** controlled failures into a running robot system the way a chaos engineer does — process kills, sensor dropouts, network partitions, induced planner deadlocks — deliberately, reversibly, and with a hypothesis stated *before* the injection.
- **Detect** a sensor dropout in software with a watchdog: a deadline-or-liveliness QoS event, a staleness check on the message timestamp, and a health-aggregator node that fuses per-sensor status into a single robot-health signal.
- **Degrade gracefully** under a missing sensor — drop the dependent perception cleanly, widen the safety margins, reduce speed, and either continue on the remaining sensors or trigger a controlled stop, never silently trusting stale data.
- **Detect and break a planner deadlock** — recognize the replanning-cycle signature, trip a timeout, and escalate through a defined ladder (replan with relaxed constraints → request operator assist → controlled stop).
- **Make every failure operator-detectable** — surface health, the active fault, and the recovery action on the Foxglove dashboard within the 60-second bar, because a recovery a human cannot see is not a recovery you can defend.
- **Write a real postmortem** against the template — blameless, with a precise timeline, a root cause distinguished from contributing factors, what worked, what didn't, and dated, owned action items.
- **Distinguish** the three failure responses — recover, degrade-and-continue, safe-abort — and argue which is correct for a given fault in a given context (a shared space changes the answer).
- **Connect** the drill back to the Week 41 safety case: every failure you survive should already be a hazard you logged, and every surprise is a gap in that case you now have to close.

## Prerequisites

This week assumes you have completed Weeks 1–45 of C24, and specifically that:

- You have a **working capstone** that runs a language-conditioned task end to end — perception → planner → controller → policy, with the Week 41 safety layer (software E-stop, velocity/workspace clamps, classical fallback) wired in. The drills are run against *this* robot; it has to run.
- You completed the **Week 41 safety case** — its hazard log is the list of failures you claim to have anticipated, and the drill tests whether you actually did.
- You have the **Week 43 telemetry dashboard** in Foxglove — the drill grades partly on whether the failure and recovery are *visible* there inside 60 seconds.
- You did the **Week 45 interview ramp** — defending the drill afterward is exactly the "what happened when the sensor died?" question the mocks rehearsed.
- You have an **instructor or peer** to inject the failures live and run the stopwatch. Solo-path learners: the mini-project provides a scripted, reproducible injector so you can self-run both drills on a timer.

You do **not** need new hardware or new models this week. Everything runs on the stack you already have. The new "tool" is an adversary — a person (or a script) whose job is to break your robot at the worst moment.

## Topics covered

- Chaos engineering, adapted from the cloud (Netflix's Chaos Monkey lineage) to robots: the steady-state hypothesis, the blast radius, the controlled injection, and why you run it in a safe environment *before* you trust it.
- The watchdog patterns for sensor health: QoS **deadline** and **liveliness** events (the Week 5 policies finally earning their keep), message-staleness checks against the acquisition timestamp, and a health-aggregator node.
- Graceful degradation as a design stance: the difference between "the LiDAR died and the robot kept driving on stale data" (a fail) and "the LiDAR died, the robot dropped LiDAR-dependent costmap layers, slowed to a crawl on the camera alone, and flagged degraded mode" (a pass).
- The planner-deadlock signature and the recovery ladder: detecting a replanning cycle, the timeout, relaxed-constraint replanning, operator-assist request, and the controlled stop of last resort.
- Operator-detectable events: surfacing health, faults, and recovery actions on the dashboard; the 60-second bar; why an alert a human never sees is not a mitigation.
- The three responses — recover, degrade-and-continue, safe-abort — and how the context (shared space vs empty test cell) decides which is correct.
- The blameless postmortem: timeline, root cause vs contributing factors, what worked, what didn't, action items with owners and dates, and how it feeds back into the safety case.
- The on-call mindset: triage, the alert taxonomy (P0/P1/P2) from the production runbook, and the discipline of not making a bad situation worse.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract — the build time is yours to reallocate toward whichever drill exposes the bigger gap in your stack.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Chaos engineering for robots; the hypothesis + blast radius    |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Watchdogs, QoS deadline/liveliness, the health aggregator      |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | Drill 1 dry-run: sensor dropout + graceful degradation         |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1h       |    0.5h    |     6.5h    |
| Thursday  | Drill 2 dry-run: planner deadlock + the recovery ladder        |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     6.5h    |
| Friday    | The graded live gameday (both drills) + the postmortem write-up|    0h    |    0h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     5h      |
| Saturday  | Mini-project: the chaos harness + two postmortems              |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, action-item + safety-case-gap write-up           |    0h    |    0h     |     0h     |    1h     |   1h     |     1.5h     |    0h      |     3.5h    |
| **Total** |                                                                | **6h**   | **6.5h**  | **4h**     | **3.5h**  | **6h**   | **9h**       | **1.5h**   | **36.5h**   |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Chaos-engineering, watchdog, Nav2-recovery, and postmortem references, current to 2026 |
| [lecture-notes/01-chaos-engineering-for-robots.md](./02-lecture-notes/01-chaos-engineering-for-robots.md) | The chaos method adapted to robots; watchdogs, health aggregation, and graceful degradation |
| [lecture-notes/02-the-two-drills-and-the-postmortem.md](./02-lecture-notes/02-the-two-drills-and-the-postmortem.md) | Both drills end to end, the recovery ladders, the 60-second bar, and the postmortem template |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of this week's three exercises |
| [exercises/exercise-01-design-the-drill.md](./03-exercises/exercise-01-design-the-drill.md) | Write the steady-state hypothesis, blast radius, and abort plan for both drills |
| [exercises/exercise-02-sensor-watchdog.py](./03-exercises/exercise-02-sensor-watchdog.py) | A runnable sensor watchdog + health aggregator that detects dropout and emits degraded mode |
| [exercises/exercise-03-deadlock-detector.py](./03-exercises/exercise-03-deadlock-detector.py) | A runnable planner-deadlock detector that trips a timeout and walks the recovery ladder |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of this week's challenge |
| [challenges/challenge-01-survive-gameday.md](./04-challenges/challenge-01-survive-gameday.md) | Run both live drills, recover inside 60 s with operator-detectable events, write both postmortems |
| [quiz.md](./05-quiz.md) | 13 questions with an answer key |
| [homework.md](./06-homework.md) | Concrete deliverables with a grading rubric |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The reproducible chaos harness + the two graded postmortems |

## The "made it better, not worse" promise

Every technical week in C24 ended in working code. This week ends in something harder to fake: **proof that your robot makes a failure better instead of worse.** The marker we use here is not `Build succeeded`. It is this, written at the top of your postmortem:

```
Drill 1 (LiDAR dropout @ T+0):  detected T+1.2s · degraded-mode T+1.4s ·
                                operator alert T+2.1s · safe-abort T+18s  → PASS (< 60s)
Drill 2 (doorway deadlock @ T+0): detected T+8s (3rd replan cycle) · operator-assist
                                  requested T+9s · replanned-around T+41s → PASS (< 60s)
```

If you cannot fill in those timestamps — a detection time, an operator-alert time, and a recovery time inside 60 seconds — you did not pass gameday. A robot that "kept going" through a sensor dropout because it never noticed did not survive the drill; it got lucky, and luck is not a mitigation.

## A note on honesty

The single most common way a chaos drill goes wrong is a robot that *appears* to handle a failure because it never detected it. The LiDAR dies, but the costmap was cached, so the robot drives the next two meters on a stale map and happens not to hit anything. That is **not** graceful degradation — it is undetected failure that got lucky, and in a shared space the luck runs out and someone gets hurt. The drill is graded on *detection and response*, not on "did it crash." A robot that detected the fault and chose a controlled stop *passed*; a robot that sailed through on stale data *failed*, even though it looked smoother. Do not optimize for looking smooth. Optimize for noticing.

## Stretch goals

If you finish the regular work early:

- Inject a **third, unannounced** failure (a network partition between the policy node and the planner, or a clock jump) and see whether your health aggregator catches a fault you did not design for. The failures you did not anticipate are the gaps in your Week 41 safety case.
- Reduce your **detection latency** for the LiDAR dropout below 500 ms by switching the sensor topic to a QoS `deadline` and reacting to the deadline-missed event instead of a polling staleness check (Lecture 1 §3).
- Run Drill 1 with the robot **mid-grasp** instead of mid-drive — does the arm stop safely, or does it complete a grasp on stale perception? Mid-manipulation dropout is the nastier version.
- Chaos-test the **recovery itself**: kill the LiDAR, and during the recovery, kill the camera too. Does your degraded-mode logic cascade safely, or does losing the fallback sensor leave the robot with no safe action but a stop?

## Up next

**Week 47 — Mock interview + portfolio polish.** You run a full-loop mock interview with a senior reviewer and polish your three flagship portfolio projects. The two postmortems you write this week are *exactly* the artifacts the Week 47 interviewer will probe ("walk me through a time your robot failed") and the Week 48 panel will read — so write them as portfolio pieces, not lab notes. Push your chaos harness and both postmortems before you start.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
