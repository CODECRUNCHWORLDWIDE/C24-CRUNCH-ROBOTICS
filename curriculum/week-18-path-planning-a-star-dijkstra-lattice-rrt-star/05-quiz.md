# Week 18 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 19. Answer key is at the bottom — don't peek.

---

**Q1.** What is the relationship between Dijkstra and A*?

- A) They are unrelated algorithms.
- B) Dijkstra is A* with the heuristic `h(n) = 0` — A* prioritizes the open set by `f = g + h`, Dijkstra by `g` alone.
- C) A* is Dijkstra run twice.
- D) Dijkstra is always faster than A*.

---

**Q2.** On an 8-connected grid, what is the correct cost of a diagonal move, and why does it matter?

- A) 1, same as orthogonal — simpler.
- B) `√2 ≈ 1.414`, because a diagonal covers more ground; using 1 makes the planner prefer impossible-to-justify staircases and breaks the metric.
- C) 2, because it crosses two cells.
- D) 0.5, because it's a shortcut.

---

**Q3.** A heuristic `h` is *admissible* if:

- A) It always over-estimates the cost-to-go.
- B) It never *over*-estimates the true cost-to-go (it's optimistic) — which guarantees A* returns an optimal path.
- C) It equals the true cost exactly.
- D) It is always zero.

---

**Q4.** You run A* on an 8-connected grid with the **Manhattan** heuristic and get a path *longer* than Dijkstra's. What happened?

- A) Dijkstra has a bug.
- B) Manhattan over-estimates on an 8-connected grid (it ignores cheaper diagonals), making it inadmissible — so A* lost its optimality guarantee and returned a sub-optimal path. Use octile.
- C) The grid is too big.
- D) A* is just slower, not wrong.

---

**Q5.** What does weighted A* (`f = g + ε·h`, ε > 1) trade, and what guarantee survives?

- A) It trades nothing; it's strictly better.
- B) It trades optimality for speed: the search is greedier and expands far fewer nodes, but the path can be up to ε× the optimal length — a *bounded* sub-optimality guarantee.
- C) It trades memory for accuracy.
- D) It makes A* admissible.

---

**Q6.** Why does Nav2 use periodic full-replanning (re-running NavFn at ~1 Hz) instead of D* Lite?

- A) D* Lite doesn't work in ROS2.
- B) For building-sized costmaps, grid A* is fast enough (tens of ms) that full replan at 1 Hz is simpler and more robust than D* Lite's incremental complexity; D* Lite pays off only when the map is huge or the replan budget is very tight.
- C) D* Lite is slower than A*.
- D) Nav2 can't replan at all.

---

**Q7.** Why does a 2D grid planner (A*) fail for a car-like (Ackermann) vehicle?

- A) Grids are too slow for cars.
- B) A car's state is `(x, y, θ)` with a minimum turning radius; a 2D-grid A* path has sharp turns and in-place pivots the car physically can't execute. You need a state lattice or Hybrid-A*.
- C) Cars don't use occupancy grids.
- D) A* only works indoors.

---

**Q8.** What is the key idea of Hybrid-A* that a plain grid A* lacks?

- A) It uses a bigger grid.
- B) It searches a *continuous* `(x, y, θ)` state with a *discrete control set* (steering actions), buckets states into grid cells only for termination, and uses analytic Dubins/Reeds-Shepp expansions — so every edge is a feasible vehicle motion.
- C) It runs A* backward.
- D) It ignores obstacles.

---

**Q9.** Why do sampling-based planners (RRT, RRT*) dominate high-DOF manipulation while grids dominate flat ground?

- A) Sampling is always better than grids.
- B) A grid is exponential in dimension (a 6-DOF arm discretized at 100 values/joint is `100^6` cells — unsearchable); sampling probes the space with samples, so its cost scales with sample count, not space volume.
- C) Arms don't have obstacles.
- D) RRT is optimal and A* is not.

---

**Q10.** What are the two additions RRT* makes to RRT, and what do they achieve?

- A) Faster sampling and bigger steps; they speed it up.
- B) `choose_parent` (connect a new node to the lowest-cost reachable neighbor) and `rewire` (re-parent nearby nodes through the new node if cheaper) — together they make RRT *asymptotically optimal*: the path cost converges to optimal as samples grow.
- C) Goal bias and collision checking; they make it complete.
- D) A heuristic and a closed set; they make it like A*.

---

**Q11.** What does "asymptotically optimal" mean for RRT*, precisely?

- A) It always returns the optimal path immediately.
- B) It returns a path whose cost *converges to* the optimal as the number of samples → ∞; at any finite budget it's the best-so-far, which improves with more samples.
- C) It is optimal only in 2D.
- D) It is never optimal.

---

**Q12.** You're choosing a planner. The robot is a long forklift that can't turn in place, operating in narrow warehouse aisles. Which planner family, and why?

- A) RRT*, because warehouses are high-dimensional.
- B) Plain Dijkstra, because it's optimal.
- C) State lattice / Hybrid-A* (SMAC), because the vehicle is nonholonomic — the planner must respect the turning radius, which a 2D grid can't encode; a grid path would be undrivable.
- D) Weighted A*, because aisles are tight.

---

**Q13.** Why is planner *runtime* treated as a safety property this week, not just a benchmark metric?

- A) It isn't; runtime is only about performance.
- B) On a moving robot, a plan that arrives late describes a world that no longer exists; a planner that occasionally takes 2 s lets the robot travel on stale information, so you measure the latency tail (p95) and declare a deadline behavior (stop if no path in time).
- C) Faster planners use less battery.
- D) Runtime only matters in simulation.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Dijkstra is A* with `h = 0`; A* adds a heuristic that points the search toward the goal. (Lecture 1 §3.)
2. **B** — `√2` for diagonals; using 1 cheats the metric and produces staircase paths. (Lecture 1 §1.1.)
3. **B** — Admissible = never over-estimates (optimistic); this is what guarantees A* optimality. (Lecture 1 §4.1.)
4. **B** — Manhattan over-estimates on 8-connected grids → inadmissible → A* loses optimality. Use octile. (Lecture 1 §3.1, §4.)
5. **B** — Weighted A* trades optimality for speed with a bounded (ε×) sub-optimality guarantee. (Lecture 1 §5.)
6. **B** — Full replan at 1 Hz is simpler and fast enough for building-sized maps; D* Lite's complexity only pays off for huge maps / tight budgets. (Lecture 1 §6.1.)
7. **B** — A car's `(x, y, θ)` state with a turning radius makes grid-A* paths infeasible; use a lattice/Hybrid-A*. (Lecture 2 §1.1.)
8. **B** — Continuous state, discrete controls, analytic Dubins/Reeds-Shepp expansion → every edge is a feasible motion. (Lecture 2 §1.3.)
9. **B** — Grids are exponential in dimension; sampling scales with sample count, so it survives high-DOF C-spaces. (Lecture 2 §2.1.)
10. **B** — `choose_parent` + `rewire` give asymptotic optimality. (Lecture 2 §2.3.)
11. **B** — Cost converges to optimal as samples → ∞; best-so-far improves with budget. (Lecture 2 §2.3.)
12. **C** — Nonholonomic → lattice/Hybrid-A*; a grid path would be undrivable. (Lecture 2 §1, §3.)
13. **B** — A late plan describes a stale world; measure the tail and declare a deadline behavior. (Lecture 2 §3.1.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
