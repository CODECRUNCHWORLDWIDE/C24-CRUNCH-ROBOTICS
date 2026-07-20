# Week 17 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 18. Answer key is at the bottom — don't peek.

---

**Q1.** Which Nav2 node *orchestrates* navigation by ticking a behavior tree, doing no planning or control itself?

- A) `planner_server`
- B) `controller_server`
- C) `bt_navigator`
- D) `lifecycle_manager`

---

**Q2.** A managed (lifecycle) node is in the `inactive [2]` state. What is true of it?

- A) It is processing normally.
- B) It has run `configure()` (params read, plugins/publishers created) but is *not* processing — a planner in `inactive` will not plan.
- C) Its process has crashed.
- D) It has never started.

---

**Q3.** What is the deterministic bring-up the `lifecycle_manager` performs at startup with `autostart: true`?

- A) It activates every node simultaneously.
- B) It calls `configure()` on all nodes in `node_names` order, then `activate()` on all in the same order — so nothing processes until everything is configured.
- C) It only configures nodes; activation is manual.
- D) It starts nodes in random order for load balancing.

---

**Q4.** `planner_server`'s *process* segfaults mid-goal. From the lifecycle manager's perspective, how is this detected, and why is it different from "no path found"?

- A) The planner returns `FAILURE`; the BT recovers. Same as no-path.
- B) The `bond` heartbeat goes silent; after `bond_timeout` the manager declares the server dead. A crash is silent (no `FAILURE` returned), unlike a no-path error which the BT *can* react to.
- C) rviz2 turns red automatically.
- D) AMCL stops publishing `map → odom`.

---

**Q5.** What is the load-bearing difference between the global costmap and the local costmap?

- A) The global costmap is in the `map` frame and covers the whole map (planner's world); the local costmap is a rolling window in the `odom` frame (controller's world).
- B) They are identical; "global" and "local" are just names.
- C) The local costmap is in `map`; the global is in `odom`.
- D) The global costmap updates faster than the local one.

---

**Q6.** Your global costmap is empty — the planner routes straight through walls. The `static_layer` subscribes to `/map` with `map_subscribe_transient_local: false`. What happened?

- A) The map file is corrupt.
- B) `map_server` publishes the map once with `TRANSIENT_LOCAL`; a `VOLATILE` static-layer subscriber joins after that single publish and receives nothing, so the costmap has no walls. (A Week-5 QoS mismatch.)
- C) The inflation radius is too small.
- D) AMCL hasn't converged.

---

**Q7.** In the default navigation BT, what does `PipelineSequence` do that a plain `Sequence` does not?

- A) Nothing; they are aliases.
- B) It re-ticks the *earlier* children every cycle, so the planner keeps replanning while the controller follows the path — this is what makes navigation reactive.
- C) It runs children in parallel.
- D) It only ticks the last child.

---

**Q8.** The robot keeps spinning in place and backing up "for no reason." What is the most likely explanation?

- A) A QoS mismatch on `/cmd_vel`.
- B) The BT has dropped into its **recovery subtree** (spin/wait/back-up) because the controller's progress checker keeps tripping — often a too-tight goal tolerance or an over-large inflation radius making the goal cell lethal.
- C) The IMU is uncalibrated.
- D) `bt_navigator` is in `unconfigured`.

---

**Q9.** Why does the planner-crash fail-safe live *outside* the behavior tree?

- A) Behavior trees can't call actions.
- B) A *crashed* server hangs the BT leaf in `RUNNING` — it never returns `FAILURE`, so the tree has nothing to recover from. Detecting the silence and stopping the base must happen outside the tree.
- C) The BT runs in C++ and fail-safes must be Python.
- D) It doesn't; the BT handles all crashes.

---

**Q10.** You want to add a custom recovery behavior to Nav2. Which interface do you implement, and which server loads it?

- A) `nav2_core::GlobalPlanner`, loaded by `planner_server`.
- B) `nav2_core::Behavior` (e.g. via `nav2_behaviors::TimedBehavior`), loaded by `behavior_server`, exported with `PLUGINLIB_EXPORT_CLASS` and listed in `behavior_plugins`.
- C) `nav2_core::Controller`, loaded by `controller_server`.
- D) A Python BT node, loaded by `bt_navigator`.

---

**Q11.** Why is the local costmap placed in the `odom` frame rather than `map`?

- A) `map` is slower to compute.
- B) The local costmap must be *locally smooth* (no jumps), which `odom` provides; if it were in `map`, every AMCL relocalization jump would yank the local obstacles sideways and the controller would swerve.
- C) `odom` is the only frame the LiDAR publishes in.
- D) There is no reason; it's arbitrary.

---

**Q12.** In the costmap, what does the `inflation_layer` do, and what breaks if `inflation_radius` is set too large?

- A) It marks lethal obstacles; too large means it marks too many obstacles.
- B) It spreads a *decaying* cost outward from obstacles so the planner keeps clearance; too large and the inflated cost fills a doorway the robot physically fits through, so the planner refuses to route through it.
- C) It clears the costmap; too large means it clears too much.
- D) It controls the LiDAR range.

---

**Q13.** You bring up Nav2, send a goal, and nothing happens. What is the *first* command you run?

- A) Restart the whole stack.
- B) `ros2 lifecycle get` on every server — a server stuck below `active [3]` is the most common cause, and you fix *that* before anything else.
- C) Echo `/cmd_vel`.
- D) Re-send the goal a few times.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **C** — `bt_navigator` orchestrates by ticking the navigation BT; the leaves are action clients into the planner/controller/behavior servers. It does no planning or control itself. (Lecture 1 §1.1.)
2. **B** — `inactive` means `configure()` ran but the node is not processing. The only working state is `active [3]`. (Lecture 1 §2.1.)
3. **B** — The manager does a configure pass then an activate pass, both in `node_names` order, so nothing processes until everything is configured. (Lecture 1 §2.3.)
4. **B** — The bond heartbeat detects a *crash* (silent), which differs from a *no-path error* that returns `FAILURE` for the BT to handle. (Lecture 1 §2.4, §5.)
5. **A** — Global = `map` frame, whole map, planner's world; local = `odom` frame, rolling window, controller's world. (Lecture 1 §3.1.)
6. **B** — The `TRANSIENT_LOCAL` latched map is missed by a `VOLATILE` subscriber that joins late → empty costmap. A Week-5 QoS lesson in production. (Lecture 2 §1.1.)
7. **B** — `PipelineSequence` re-ticks earlier children each cycle, which is how the planner replans while the controller follows. (Lecture 2 §2.2.)
8. **B** — The recovery subtree (spin/wait/back-up) is firing because the progress checker keeps tripping, frequently from too-tight tolerance or an over-large inflation radius. (Lecture 2 §2.3.)
9. **B** — A crashed server hangs the leaf in `RUNNING`; no `FAILURE` means the BT can't recover, so the fail-safe must live outside it. (Lecture 1 §5, Lecture 2 §2.3.)
10. **B** — `nav2_core::Behavior`, loaded by `behavior_server`, exported with `PLUGINLIB_EXPORT_CLASS`, listed in `behavior_plugins`. (Lecture 2 §3.1–3.3.)
11. **B** — Local smoothness over global accuracy; `map` jumps on AMCL corrections and would yank local obstacles. (Lecture 1 §3.1, Lecture 2 §1.2.)
12. **B** — Inflation spreads decaying cost for clearance; too large blocks doorways the robot fits through. (Lecture 2 §1.1, Exercise 3.)
13. **B** — Always `ros2 lifecycle get` first. A server below `active [3]` is the most common "won't navigate" cause. (Lecture 1 §2.5, Lecture 2 §4.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
