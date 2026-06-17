# Week 36 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 37. Answer key is at the bottom — don't peek.

---

**Q1.** In the Gerkey–Matarić taxonomy, a fleet where each robot does one task at a time, each task needs one robot, and you assign them all *right now* with no lookahead is which class — and what's its optimal solver?

- A) MT-MR-TA; solved by a combinatorial auction.
- B) ST-SR-IA; solved optimally in polynomial time by the Hungarian algorithm.
- C) ST-SR-TA; NP-hard, no polynomial optimal solver.
- D) ST-MR-IA; solved by greedy `argmin`.

---

**Q2.** Why is greedy `argmin` (assign each task to its cheapest free robot in turn) *not* a safe choice for ST-SR-IA?

- A) It's slower than the Hungarian algorithm.
- B) A locally cheap assignment can force a globally ruinous one — e.g., grabbing a cost-1 cell strands the only other robot on a cost-100 cell.
- C) It can't handle more than three robots.
- D) It requires a central solver and the Hungarian algorithm doesn't.

---

**Q3.** The Hungarian algorithm's correctness rests on which invariant?

- A) Multiplying a row by a constant preserves the optimal assignment.
- B) Subtracting a constant from an entire row (or column) does not change which assignment is optimal, only the total.
- C) Adding the same task to every robot's row keeps the matrix square.
- D) The cheapest cell is always in the optimal assignment.

---

**Q4.** You call `scipy.optimize.linear_sum_assignment` on a 2×4 cost matrix (2 robots, 4 tasks). What does it return?

- A) All 4 tasks assigned, two robots double-booked.
- B) An error — the matrix must be square.
- C) `min(N, M) = 2` pairs: each robot gets one distinct task; the other two tasks are unassigned and go back in the queue.
- D) The 2 cheapest cells regardless of row/column conflicts.

---

**Q5.** In a sequential single-item (SSI) auction, a robot's bid on a task is its *marginal* cost. Why does that produce near-optimal, geographically coherent routes?

- A) Marginal cost is always lower than total cost, so bids are cheaper.
- B) A robot that already won a task near a cluster has a small marginal cost to add the rest of that cluster and a large marginal cost for far-away tasks — so clusters naturally stay on one robot.
- C) Marginal cost ignores the robot's current position.
- D) It forces every robot to bid the same amount.

---

**Q6.** On a *live* fleet where tasks arrive continuously and robots occasionally fail, why prefer an SSI auction over re-running the Hungarian algorithm on every change?

- A) The Hungarian algorithm is not optimal.
- B) Re-auctioning just the new or orphaned task is cheap and stable; re-solving the whole assignment churns robots off tasks they've started and costs O(n³) every time.
- C) Auctions are always more optimal than the Hungarian algorithm.
- D) The Hungarian algorithm can't compute Euclidean distance.

---

**Q7.** In Open-RMF, what does the **traffic schedule** (`rmf_traffic_schedule`) actually store?

- A) Each robot's current 2D position only.
- B) Every robot's reserved trajectory through *space and time* — where each robot will be, and when — so conflicts can be predicted before they happen.
- C) The occupancy grid of the building.
- D) The list of pending tasks.

---

**Q8.** A robot exposes only a Nav2-style "go to this pose" interface and has no onboard multi-robot awareness. Which RMF fleet-adapter control category fits?

- A) Read-only — RMF can only observe it.
- B) Traffic light — the robot plans its own path, RMF grants go/stop.
- C) Full control — RMF plans the path and commands the robot to follow it (via Nav2). `EasyFullControl` is the low-boilerplate API.
- D) None — Nav2 robots can't join RMF.

---

**Q9.** Two robots meet in a corridor; the schedule's negotiation makes the robot that *arrived first* wait while the second proceeds. Why is that not a bug?

- A) RMF always favors the second robot.
- B) The negotiation is cost-based: it minimizes total disruption across both robots, so it may make the first-arriving robot wait if that's globally cheaper — joint optimization beats first-come-first-served.
- C) The first robot must have a QoS mismatch.
- D) The schedule processes robots in reverse order of arrival.

---

**Q10.** Two robots freeze nose-to-nose in a single bidirectional corridor with no passing place, and the deadlock does not self-resolve. The correct fix is:

- A) Add a special case to the task allocator so it never sends two robots through that corridor in opposite directions.
- B) Restart the dispatcher.
- C) A map-level change: add a passing place, or make the pinch one-way with a separate return lane. A deadlock here is a map invariant problem, not a code bug.
- D) Switch the DDS vendor.

---

**Q11.** Why is a **pushed heartbeat** a better failure detector than the dispatcher **polling** each robot with a service call?

- A) Polling uses more bandwidth in all cases.
- B) A wedged-but-alive robot (process up, control loop deadlocked) still answers a liveness service on another thread but stops publishing its heartbeat — so the push model fails closed while the poll model falsely reports it healthy.
- C) Services can't carry battery information.
- D) Heartbeats are always more reliable than services.

---

**Q12.** For the capstone `/fleet/heartbeat` (1 Hz), why is `MANUAL_BY_TOPIC` liveliness the correct QoS choice, not `AUTOMATIC`?

- A) `AUTOMATIC` isn't supported on Jazzy.
- B) With `AUTOMATIC`, a robot whose publishing thread wedged but whose process is alive is still reported live (it lies to the fleet manager). `MANUAL_BY_TOPIC` requires the node to actively assert liveliness by publishing, so a wedge expires the lease and fires a liveliness-lost event.
- C) `MANUAL_BY_TOPIC` is faster.
- D) Liveliness has no effect on heartbeats.

---

**Q13.** When a robot stalls mid-task, your dispatcher reallocates its tasks. Which task must it **not** silently re-auction, and why?

- A) The lowest-cost task, because it's most valuable.
- B) A task already marked `started`, because the robot may have left the world in a bad state (half-done, holding a payload, blocking a corridor) — it must be flagged for an operator, not blindly reassigned.
- C) The most recently assigned task, because the assignment is stale.
- D) All tasks — none can ever be reallocated.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — ST-SR-IA (single-task robots, single-robot tasks, instantaneous assignment) is polynomial and the Hungarian algorithm solves it optimally in O(n³). (Lecture 1 §1.1.)
2. **B** — Greedy reasons one cell at a time; a locally cheap choice can strand a robot on a catastrophic cell (the 1 vs 100 counterexample, 25× worse). (Lecture 1 §2.)
3. **B** — Subtracting a row/column constant changes every assignment's total by the same amount, so the *argmin* assignment is unchanged. That's why row/column reduction is valid. (Lecture 1 §3.1.)
4. **C** — On a non-square matrix the solver assigns `min(N, M)` distinct pairs and leaves the surplus tasks unassigned; they return to the queue. (Lecture 1 §3.4.)
5. **B** — Marginal cost (the extra route length to add a task) is small for tasks near a robot's existing route and large for far ones, so clusters stay coherent — the reason SSI is near-optimal. (Lecture 1 §4.2.)
6. **B** — Incremental re-auction is cheap and stable; a full Hungarian re-solve on every change is O(n³) and churns in-progress assignments. (Lecture 1 §4.4.)
7. **B** — The schedule holds every robot's reserved *space-time* trajectory, enabling conflict prediction. Two robots in the same space at different *times* don't conflict. (Lecture 2 §1.1, §3.1.)
8. **C** — Full control via `EasyFullControl`: RMF owns navigation and commands the Nav2 robot. (Lecture 2 §1.3, §2.3.)
9. **B** — The negotiation minimizes joint disruption (cost-based), not arrival order; it may make the first robot wait if globally cheaper. (Lecture 2 §3.2.)
10. **C** — A deadlock in a single bidirectional pinch is a map invariant problem; the fix is a passing place or a one-way lane, not an allocator special case (which couples allocation to geometry and breaks for read-only fleets). (Lecture 2 §3.4; Challenge 1.)
11. **B** — Push fails closed on a wedge; poll fails open. The wedged-but-alive case is exactly why a heartbeat beats a liveness service. (Lecture 2 §4.1; mini-project.)
12. **B** — `MANUAL_BY_TOPIC` catches a wedged-but-alive publisher that `AUTOMATIC` would falsely report live. The capstone heartbeat is the canonical use. (Lecture 2 §5.2; Week 5 §3.6.)
13. **B** — A `started` task may have left the world in a bad state; reallocate only un-started tasks and *flag* started ones for an operator. (Lecture 2 §4.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
