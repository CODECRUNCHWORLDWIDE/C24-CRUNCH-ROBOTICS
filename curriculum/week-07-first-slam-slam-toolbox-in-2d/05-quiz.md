# Week 7 — Quiz

Thirteen questions on occupancy grids, pose graphs, scan matching, loop closure, and the three `slam_toolbox` modes. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 8. Answer key at the bottom — don't peek.

---

**Q1.** In a `nav_msgs/OccupancyGrid`, the `int8[] data` field uses three canonical values. Which mapping is correct?

- A) `0` = occupied, `100` = free, `-1` = unknown.
- B) `0` = free, `100` = occupied, `-1` = unknown.
- C) `0` = unknown, `1` = free, `2` = occupied.
- D) `-1` = free, `0` = unknown, `100` = occupied.

---

**Q2.** Why is an occupancy grid maintained internally as a field of **log-odds** rather than as a binary occupied/free bitmap?

- A) Log-odds uses less memory than one bit per cell.
- B) Each new observation of a cell becomes a simple *addition* of log-odds, so fusing many noisy beams over the same cell is a Bayesian update that firms up (or flips) the cell's probability as evidence accumulates.
- C) ROS2 requires log-odds for all map messages.
- D) Log-odds is required for the LiDAR to return ranges.

---

**Q3.** SLAM is described in Lecture 1 as estimating the *whole trajectory* `x₀:ₜ` and the map, not just the current pose. Why does it estimate the whole trajectory rather than filtering down to a single current pose?

- A) To save memory.
- B) Because a loop closure is a constraint between a recent pose and an *old* pose, and exploiting it requires *moving the old pose* — which is only possible if old poses are still explicit variables in the state. A filter that marginalized them away cannot.
- C) Because the LiDAR needs the full trajectory to produce a scan.
- D) It does not; SLAM is always a filter.

---

**Q4.** In the pose-graph formulation, what does an **edge** carry, and what is the role of its **information matrix**?

- A) An edge carries an absolute pose; the information matrix is the map resolution.
- B) An edge carries a relative-pose measurement between two nodes; the information matrix (inverse covariance) weights how expensive it is to violate that constraint, so the back-end trusts confident edges over uncertain ones.
- C) An edge carries a LiDAR scan; the information matrix is the number of beams.
- D) An edge carries the robot's velocity; the information matrix is unused in 2D.

---

**Q5.** The front-end (correlative scan matcher) is sometimes described as "giving you the pose." Lecture 1 corrects this. What does the front-end actually produce?

- A) An absolute pose in the `map` frame.
- B) A constraint — a *relative* transform between two nodes *plus* an information matrix derived from the sharpness of the scan-match response peak. The back-end turns constraints into poses.
- C) A new occupancy grid.
- D) A velocity command for the controller.

---

**Q6.** Why does the scan-matcher's search window only need to cover the *odometry error* between two nodes rather than the full robot motion?

- A) Because the LiDAR is omnidirectional.
- B) Because the odometry prior (from your Week 6 node) tells the matcher roughly where the new scan should land, so the window only has to span the *uncertainty* in that prior — which is the accumulated odometry error, not the whole displacement. This is why good odometry makes scan matching faster and more reliable.
- C) Because the window size is fixed by the resolution.
- D) Because `slam_toolbox` ignores odometry entirely.

---

**Q7.** A robot drives a long corridor with no revisits, running graph SLAM. The map bends slightly over the corridor's length. Why?

- A) The LiDAR is broken.
- B) Without loop closures, graph SLAM is just *scan-matched odometry* — the sequential edges form a chain, composing many slightly-wrong scan matches accumulates error, and there is no loop-closure constraint to correct it. Scan matching drifts more slowly than wheel odometry but it still drifts.
- C) The occupancy grid resolution is too coarse.
- D) The back-end converged to a wrong local minimum because the corridor is straight.

---

**Q8.** A **false** loop closure (the front-end matches the current scan to the *wrong* old node) is described as more dangerous than a *missed* one. Why?

- A) It uses more CPU.
- B) The back-end cannot tell a true constraint from a false one — it faithfully minimizes the error of *every* edge it is given. A false loop-closure edge makes the optimizer confidently fold the map toward the lie, producing a wrong map that looks clean and globally consistent.
- C) It crashes `slam_toolbox`.
- D) It is not more dangerous; a missed loop is always worse.

---

**Q9.** You launch `slam_toolbox` in Gz Sim. The map never builds, and the node logs transform-timeout / "failed to compute odom pose" warnings, even though `/scan` and `odom → base_link` both look fine on the command line. What is the most likely cause?

- A) The LiDAR resolution is wrong.
- B) A `use_sim_time` mismatch — `slam_toolbox` (or another node in the graph) is on wall time while the scans are stamped with sim time, so every TF lookup fails silently. Set `use_sim_time: True` on *every* node and confirm `/clock` is published.
- C) The map resolution is set to 0.05.
- D) `do_loop_closing` is set to false.

---

**Q10.** What is the difference between **synchronous** and **asynchronous** mapping mode, and when do you use each?

- A) Sync is faster; async is slower. Always use sync.
- B) Sync processes *every* scan in order (never drops data, can lag real time) — use it for deterministic bag replays and abundant CPU. Async processes scans as fast as it can and *drops* scans under load to stay current — use it for live mapping where the `map → odom` transform must track the robot *now*.
- C) Sync builds 2D maps; async builds 3D maps.
- D) They are identical; the names are aliases.

---

**Q11.** You finish a mapping run and save the map with `map_saver_cli` (PGM + YAML). Later you try to start `slam_toolbox` in localization mode pointing at that PGM and it cannot re-localize. Why, and what should you have saved?

- A) The PGM is corrupt; re-save it.
- B) The PGM/YAML is a *static thresholded snapshot* with no pose graph, no constraints, no scans — localization mode needs the **serialized pose graph** (`.posegraph` + `.data`) from the `serialize_map` service, which preserves the full graph. You should have saved *both* formats. AMCL reads the PGM; `slam_toolbox` localization reads the serialized graph.
- C) Localization mode does not exist in `slam_toolbox`.
- D) The YAML `origin` was wrong.

---

**Q12.** Per REP-105, who publishes `map → odom`, who publishes `odom → base_link`, and which one jumps?

- A) `slam_toolbox` publishes both; neither jumps.
- B) `slam_toolbox` publishes `map → odom` (accurate, *jumps* discontinuously when a loop closure re-optimizes the estimate); your odometry node publishes `odom → base_link` (smooth, continuous, drifts). The jump is isolated in `map → odom` so the controller's smooth frame is undisturbed.
- C) Your odometry publishes `map → odom`; `slam_toolbox` publishes `odom → base_link`.
- D) `slam_toolbox` publishes `map → base_link` directly.

---

**Q13.** During a mapping run a *true* loop closure is missed and the map doubles a wall. You raise `loop_search_maximum_distance` from 3.0 m to 20.0 m and lower `loop_match_minimum_response_fine` from 0.45 to 0.05, and the loop now closes. Why is this a *poor* fix even though the map looks right?

- A) It is the correct fix; bigger numbers are always better.
- B) It is a sledgehammer: a 0.05 response gate admits almost any candidate, so the next time the robot sees a similar-looking place (a second identical corridor, a symmetric room) the front-end will accept a *false* loop closure and fold the map. The disciplined fix is the *minimal* change — raise the search distance just past the measured drift, lower the gate just enough to admit the true match — with an argument that it does not also admit a false one.
- C) `loop_search_maximum_distance` cannot exceed 5.0 m.
- D) Lowering the response gate disables the back-end.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The `nav_msgs/OccupancyGrid` convention is `0` = free (a beam passed through), `100` = occupied (a beam ended here), `-1` = unknown (no information). Values `1–99` are intermediate probabilities some mappers emit; `slam_toolbox` mostly uses `-1 / 0 / 100`.

2. **B** — Log-odds turns the Bayesian occupancy update into addition: each "occupied" observation adds a positive increment, each "free" observation a negative one. This lets many noisy beams over the same cell accumulate into a confident estimate that can still flip if the world changes (with clamping). It is about *fusing evidence correctly*, not memory.

3. **B** — Full SLAM (smoothing) keeps all poses as explicit variables precisely because a loop closure must *move an old pose* to correct accumulated drift. A filter that marginalized away the old poses cannot do this — which is why graph SLAM (a smoother) beat EKF/particle SLAM (filters) for mapping. (Localization against a *fixed* map is fine with a filter — Week 11's AMCL — because nothing old needs to move.)

4. **B** — An edge is a *relative-pose constraint* between two nodes, carrying a measured transform and an information matrix (inverse covariance). The information matrix weights the edge in the back-end's least-squares cost: a confident scan match (sharp response) is expensive to violate and gets satisfied first; an uncertain one (a corridor, flat along its length) can be stretched.

5. **B** — The front-end produces a *constraint*, not a pose: a relative transform plus an information matrix estimated from the response-peak sharpness. The back-end (Ceres least-squares) turns the collection of constraints into the optimized poses. Saying "the scan matcher gives you the pose" skips the back-end's job.

6. **B** — The odometry prior tells the matcher roughly where to look, so the search window only has to cover the *uncertainty* of that prior — the accumulated odometry error between nodes — not the full motion. This is the concrete reason Week 6 odometry quality matters: good odometry → small, fast, reliable scan-match window.

7. **B** — With no loop closures, graph SLAM degenerates to scan-matched odometry: a chain of sequential edges with a unique solution (compose the transforms), and composing many slightly-wrong scan matches accumulates error. Scan matching drifts slower than wheel odometry (richer measurement) but is still unbounded without a loop closure to reset it.

8. **B** — The back-end only minimizes the error of the edges it is given; it has no way to distinguish a true constraint from a false one. A false loop-closure edge makes the optimizer fold the map toward the lie — and because the optimizer converges cleanly, the wrong map *looks* right. A missed loop merely leaves drift uncorrected (the map bends); a false loop actively corrupts good geometry.

9. **B** — The classic simulation SLAM bug. If any node in the graph uses wall time while scans carry sim-time stamps, every TF lookup falls outside the buffer and fails silently — `slam_toolbox` waits forever for transforms it can never get. Fix: `use_sim_time: True` on every node, and confirm `/clock` is published and bridged.

10. **B** — Sync processes every scan in order and never drops data, but can lag real time under load — right for deterministic bag replays and reproducible experiments. Async drops scans under load to keep the `map → odom` transform current — right for live mapping where tracking the robot *now* beats processing every scan. Both build the same kind of graph.

11. **B** — `map_saver_cli` writes a *thresholded occupancy-grid snapshot* (PGM/YAML) with no pose graph — exactly what Nav2 and AMCL want, and exactly what `slam_toolbox` localization *cannot* re-localize from. Localization mode needs the serialized pose graph (`.posegraph` + `.data`) from `serialize_map`, which preserves nodes, scans, edges, and information matrices. Save both formats; they serve two different consumers.

12. **B** — REP-105: `slam_toolbox` publishes `map → odom` (the accurate correction, which *jumps* when a loop closure re-optimizes the estimate); your Week 6 node publishes `odom → base_link` (smooth, continuous, drifting). The robot's pose in `map` is the composition. Isolating the jump in `map → odom` keeps the controller's smooth `odom` frame undisturbed — that separation is REP-105's whole design. Never publish `map → base_link` yourself.

13. **B** — A 0.05 response gate admits almost any candidate, so the fix that closes *this* loop also opens the door to *false* loop closures on the next similar-looking place — which would fold the map. The graded fix is *minimal*: raise the search distance just past the measured drift (the safest change), lower the gate just enough to admit the true match, and argue (from the world's geometry) that no false match clears the new gate. "I loosened everything and it closed" fails even when the map looks right, because it will fold on the next symmetric corridor.

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially the front-end/back-end split (Q4, Q5) and the loop-closure knife-edge (Q8, Q13), which the challenge and mini-project both depend on. If you scored 11 or higher, you're ready for the [homework](./06-homework.md) and the mini-project.
