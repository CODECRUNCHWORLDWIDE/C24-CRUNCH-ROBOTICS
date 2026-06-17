# Week 36 Homework

Six problems that drive the allocation math and the fleet-management discipline into your fingers. The full set should take about **5 hours**. Work in your Week 36 Git repository (the same workspace as the exercises and the `crunch_fleet` mini-project) so every problem produces at least one commit you can point to at the Phase 5 milestone in Week 40.

The headline deliverable is **Problem 4 — the reallocation-drill write-up**, the multi-robot analogue of the syllabus's "inject a robot-stalls event and verify reallocation." Treat it as the artifact a reviewer reads, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Have your **Week 35 two-robot bring-up** spawnable, and an Open-RMF install (`ros2 pkg list | grep rmf` shows packages). Problems 5 and 6 use RMF; if RMF won't install on your machine, the substitution (run against the `crunch_fleet` sim instead) is noted in each.

---

## Problem 1 — Cost matrices that lie

**Problem statement.** Build a 4-robot, 4-task scenario where the **Euclidean** cost matrix and the **nav-graph path** cost matrix give *different* optimal assignments. The setup: a wall separates two rooms; a robot is Euclidean-close to a task across the wall but path-far (it must go around). Compute both cost matrices, solve both with the Hungarian algorithm, and show the assignments differ. Write it up in `notes/week-36/cost-lies.md`.

**Acceptance criteria.**
- A diagram (ASCII is fine) of the rooms, wall, robots, and tasks.
- Both 4×4 cost matrices (Euclidean and path), with the path costs computed through a simple graph (you may hand-author the graph distances).
- Both Hungarian solutions, shown to differ, with the total cost of each assignment evaluated *under the true (path) costs* — proving the Euclidean assignment is worse in reality.
- Committed.

**Hint.** The cleanest construction: robot A at the wall on the left, task at the wall on the right — 1 m apart Euclidean, but 20 m path because the only door is at the far end. A reuses the `build_cost_matrix(cost_fn=...)` hook from Exercise 2 with a graph-distance `cost_fn`.

**Estimated time.** 45 minutes.

---

## Problem 2 — Greedy vs. Hungarian at scale

**Problem statement.** Generate 100 random 8×8 cost matrices (uniform costs in [1, 100]). For each, compute the greedy total and the Hungarian (optimal) total. Report the distribution of the **greedy excess** = (greedy − optimal) / optimal, as a percentage: mean, median, max. Write it up in `notes/week-36/greedy-excess.md` with a small table or histogram.

**Acceptance criteria.**
- A script `greedy_excess.py` that runs the experiment and prints the mean/median/max greedy excess over 100 trials.
- The reported mean greedy excess is clearly > 0 (greedy is, on average, worse), and the max is materially larger (greedy occasionally blunders badly).
- One sentence: at what fleet size / cost spread does greedy stop being "good enough," in your judgement?
- Committed.

**Hint.** Reuse `allocate_greedy` and `allocate_hungarian` from Exercise 2. Use `numpy.random.default_rng(seed)` for reproducibility and report the seed. Expect a mean excess in the low-single-digit-to-teens percent depending on the cost spread — small per matrix, large across a fleet's lifetime.

**Estimated time.** 40 minutes.

---

## Problem 3 — SSI vs. optimal

**Problem statement.** Take a 3-robot, 9-task routing problem (each robot starts at a depot; tasks are points in the plane; cost is route length). Compute the SSI auction allocation (from Exercise 3) and compare its *total route length* to a near-optimal baseline. For the baseline, since exact optimal routing is itself hard, use a strong heuristic: try all ways to partition tasks among robots is too many, so instead compute the optimal *one-shot Hungarian* assignment of 9 tasks to 3 robots in 3 rounds and route each robot's tasks with a nearest-neighbor tour. Report SSI's total vs. the baseline's total.

**Acceptance criteria.**
- A script `ssi_vs_baseline.py` and a `notes/week-36/ssi-quality.md` reporting both totals and the ratio.
- SSI's total is within ~10–15% of the baseline (confirming the "~90%+ of optimal" claim from Lecture 1 §4.2), or you explain why your instance is adversarial.
- One sentence on *why* you'd still pick SSI on a live fleet despite not being exactly optimal.
- Committed.

**Hint.** Exact optimal multi-robot routing is NP-hard, so don't chase it; the point is to show SSI is *close* to a strong baseline cheaply. Use the `Robot.marginal_cost` machinery from Exercise 3 for SSI.

**Estimated time.** 1 hour.

---

## Problem 4 — The reallocation-drill write-up (headline deliverable)

**Problem statement.** Run your `crunch_fleet` mini-project drill (or, if the mini-project isn't done, a minimal version: a dispatcher, three heartbeating robot sims, five tasks). Submit five tasks, let allocation settle, then stall one robot mid-task. Capture the full reallocation and **measure the recovery latency**. Then write a one-page report at `notes/week-36/reallocation-drill.md` against this template:

1. **Summary** — one sentence: a robot stalled mid-task and the fleet recovered in N seconds.
2. **Setup** — the fleet (robots, capabilities), the five tasks, the allocation that resulted (which robot got what), and *why* (cost matrix).
3. **The injection** — exactly how you stalled the robot (stopped heartbeat vs. `nav_state=ERROR`), at what point in its task, and the heartbeat trace showing it go stale.
4. **Detection** — the dispatcher log line declaring the robot stale, with the actual age vs. the lease.
5. **Reallocation** — the `ORPHANED` → `RE-ASSIGNED` sequence, including how a *started* task was flagged (not re-auctioned), and the new owner's bid.
6. **Latency + prevention** — the measured seconds-to-recover, whether it's under the 60 s capstone bound, and one concrete improvement (e.g., "shorten the lease to 1.5 s to detect faster, at the risk of false alarms on jitter").

**Acceptance criteria.**
- `notes/week-36/reallocation-drill.md` exists, fits roughly one page (400–600 words), hits all six headings.
- A **measured** recovery latency (a number in seconds), not "fast."
- The trace shows a *started* task being flagged, not silently reallocated.
- The prevention item is concrete (a number, a mechanism), not "be more careful."
- Committed.

**Hint.** The latency is (heartbeat lease) + (re-bid + assign time) + (new robot start). Most of it is the lease, so the report should reason about the lease/false-alarm trade-off explicitly. Quote the real dispatcher log lines.

**Estimated time.** 1 hour.

---

## Problem 5 — Submit five tasks to Open-RMF and watch the dispatcher bid

**Problem statement.** Launch the `rmf_demos` office (or airport) world. Submit **five** tasks via the API (`dispatch_delivery` / `dispatch_patrol`). Watch `/fleet_states` and record, for each task, which fleet/robot the dispatcher assigned it to and (where observable) the bid/cost that won. Write it up in `notes/week-36/rmf-dispatch.md`.

**Acceptance criteria.**
- `notes/week-36/rmf-dispatch.md` shows the five task submissions (the commands), and for each the assigned robot and its mode transition (IDLE → MOVING) from `/fleet_states`.
- You note at least one case where the dispatcher's choice was *not* the geographically nearest robot, and reason about why (existing commitments, capability, battery) — or confirm it was nearest and say so.
- One sentence connecting RMF's bidding to Lecture 1's auction.
- Committed.

**Hint.** `ros2 topic echo /fleet_states` is your window. If RMF won't install, substitute: submit five tasks to your `crunch_fleet` dispatcher and record its Hungarian allocation instead — note the substitution in the file.

**Estimated time.** 45 minutes.

---

## Problem 6 — Force and document a corridor negotiation

**Problem statement.** On the RMF office demo (good map, has passing room), send two robots through a shared corridor in opposite directions at overlapping times (the Challenge 1 Part A setup, abbreviated). Capture the negotiation outcome: which robot yielded, where it waited, and how many extra seconds the yield cost versus an unobstructed run. Write it up in `notes/week-36/corridor-negotiation.md`.

**Acceptance criteria.**
- `notes/week-36/corridor-negotiation.md` records the two task submissions, the observed yield (which robot, where), and the measured extra time the yielding robot spent.
- You explain in two sentences *why* that robot yielded (cost-based negotiation, not arrival order).
- Committed.

**Hint.** Time an unobstructed single-robot run through the corridor first (baseline), then the two-robot contended run; the difference for the yielding robot is "the price of sharing." If RMF won't install, substitute a written analysis of the negotiation from the Lecture 2 §3 material and the `rmf_traffic` docs, clearly labeled as a substitution.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Cost matrices that lie | 45 min |
| 2 — Greedy vs. Hungarian at scale | 40 min |
| 3 — SSI vs. optimal | 1 h 0 min |
| 4 — Reallocation drill (headline) | 1 h 0 min |
| 5 — Submit five tasks to RMF | 45 min |
| 6 — Corridor negotiation | 45 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_fleet` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — the capstone reuses its heartbeat schema. Then take the [quiz](./05-quiz.md) with your notes closed.
