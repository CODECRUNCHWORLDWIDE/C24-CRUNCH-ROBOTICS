# Challenge 1 — Survive Gameday

**Type:** Live, graded, adversarial. Needs a human (or the mini-project's scripted injector) to inject the failures and run the stopwatch.
**Estimated time:** ~3 hours (safety-path check 30 min, two drills 60 min, two postmortems 90 min).
**Difficulty:** Hard — this is the live-graded chaos drill, 5% of the track, and the most predictive single test of whether your robot is real.

---

## The setup

Your robot runs a language-conditioned task. An instructor (or a peer, or the scripted injector) breaks it twice, live, on the clock. You must detect each failure, respond safely, make it operator-detectable inside 60 seconds, and write a blameless postmortem for each. Run it in sim or in a padded, empty test cell with a physical E-stop in a human's hand — never in a shared space the first time (Lecture 1 §2.3).

The two drills are fixed by the syllabus:

- **Drill 1 — sensor dropout mid-task.** The LiDAR is killed (`kill -9`, the brutal realistic version) while the robot is mid-task. The clock starts at the kill.
- **Drill 2 — planner deadlock at a doorway.** A moved obstacle partially blocks a corridor; the planner cycles. The clock starts at the obstacle injection.

---

## What you must do

### Step 0 — Prove the safety path survives (before the clock)

Inject each failure once, *off the clock*, and confirm the software E-stop still latches within its 200 ms budget and the controlled stop still works. If killing the LiDAR also takes down the E-stop, stop — fix that first; you have a single point of failure, not a safety path (Lecture 2 §1).

### Step 1 — Run Drill 1, graded

`ros2 bag record -a`, start the task, the injector `kill -9`s the LiDAR mid-drive. You must produce, on the clock:

- **Detection** — the robot notices (`/scan` deadline event or staleness → `sensor_health['lidar'] = DEAD`). Record the time.
- **Diagnosis** — health aggregator flips to DEGRADED or FAULT per `can_degrade`. Record the time.
- **Graceful response** — drop the LiDAR costmap layer (remove, don't freeze), degrade-and-continue on the remaining sensors *or* safe-abort. Either is a pass *if it was a detected, deliberate choice*.
- **Operator-detectable** — the fault and recovery action visible on the Foxglove dashboard within 2 s.
- **Recovery/abort within 60 s.**

### Step 2 — Run Drill 2, graded

`ros2 bag record -a`, robot heads for the doorway, the injector publishes the moved obstacle. You must produce, on the clock:

- **Detection** — the replan-without-progress signature trips (replanning *and* not progressing). Record the time and which cycle tripped it.
- **Recovery ladder** — relax → clear → operator-assist → controlled stop, escalating only as needed. Record which rung recovered.
- **Operator-detectable** — the deadlock and the recovery action visible on the dashboard.
- **Recovery or operator-assist request within 60 s** (escalating to a human is a pass, not a failure).

### Step 3 — Write both postmortems

Against the Lecture 2 §7 template — summary, timeline (from the bag), root cause vs contributing factors, what worked, what didn't, action items with owners/dates/safety-case impact.

---

## Acceptance criteria

You pass gameday if, for **both** drills:

- [ ] The robot **detected** the fault (this is the bar — a lucky non-crash on stale data is a fail; Lecture 2 §6).
- [ ] The response was a **deliberate, detected choice** — recover, degrade-and-continue, or safe-abort — never silently sailing on bad state.
- [ ] The fault and recovery were **operator-detectable** on the dashboard.
- [ ] Recovery / safe-abort / operator-assist happened **within 60 seconds**, measured from the bag.
- [ ] The **software E-stop survived** the injection (Step 0).
- [ ] A **blameless postmortem** per drill, timeline cited to the bag, root cause distinct from contributing factors, action items owned and dated.

## Deliverable

Commit, next to your capstone:

1. The two **rosbags** (or links).
2. The two **postmortems** (`postmortem-drill-1.md`, `postmortem-drill-2.md`).
3. The **dashboard recording** showing both faults and recoveries (this is also a capstone deliverable — the operator-dashboard recording).
4. The **marker line** at the top of each postmortem:

   ```
   Drill 1 (LiDAR dropout @ T+0):  detected T+1.2s · degraded-mode T+1.4s ·
                                   operator alert T+2.1s · safe-abort T+18s  → PASS (< 60s)
   ```

These postmortems are capstone artifacts — the Week 48 panel reads them and the Week 47 interviewer probes them. Write them as portfolio pieces.

---

## Stretch

- **The unannounced third failure.** Have the injector add a surprise (network partition between policy and planner, or a clock jump) that you did *not* design for in Exercise 1. Whether your health aggregator catches it tells you how complete your Week 41 safety case really is. The surprise becomes a hazard-log action item.
- **Mid-grasp dropout.** Run Drill 1 with the arm mid-grasp instead of mid-drive. Does the arm stop safely, or complete a grasp on stale perception? The nastier version, and a strong defense-panel story if you handle it.
- **Cascade the failure.** During the Drill-1 recovery, kill the camera too. Does degraded mode cascade safely to a controlled stop, or does losing the fallback sensor leave the robot with no safe action it recognizes?
- **Beat 500 ms detection.** Switch `/scan` to a QoS `deadline` and react to the deadline-missed event instead of a polling staleness check. Report the new detection latency (Lecture 1 §3.1).
