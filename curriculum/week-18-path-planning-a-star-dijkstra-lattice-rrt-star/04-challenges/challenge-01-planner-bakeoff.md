# Challenge 1 — The Planner Bake-Off

**Time estimate:** ~90 minutes.

## Problem statement

You are the planning lead. The team is about to commit to a global planner for the crunchbot, and someone in the design review just said "let's just use A*, it's optimal." Your job is to replace that hand-wave with **data**: a controlled bake-off of four planners across three maps, producing a table of **path quality vs. runtime vs. success rate** that justifies a *per-situation* planner choice.

This mirrors the real skill: planner selection is not a preference, it's a measurement. You run the candidates on representative maps, read the trade-offs, and choose — with numbers a reviewer can't argue with.

## The contenders

Four planners, all of which you can run from this week's code plus Nav2:

1. **A\*** (octile, ε = 1) — your Exercise 2 implementation. Optimal grid baseline.
2. **Weighted A\*** (ε = 2.0) — same code, inflated heuristic. The latency-vs-optimality knob.
3. **RRT\*** — your Exercise 3 implementation, at a fixed sample budget. The sampling-based contender.
4. **Nav2 SMAC Hybrid-A\*** — the production nonholonomic planner (`nav2_smac_planner/SmacPlannerHybrid`), run via a live `planner_server`.

## The three maps

Build (or generate) three 40×40 occupancy grids that stress planners differently:

- **Map A — Open field.** No obstacles except a border. Tests raw speed and how a heuristic behaves with nothing to route around. (RRT* should look *bad* here — it samples a space that A* crosses in a straight line.)
- **Map B — Maze.** A serpentine corridor that forces a long, winding path. Tests heuristic informativeness (A*'s octile heuristic is misleading in a maze — the goal is "close" in Euclidean distance but far in path distance).
- **Map C — Narrow corridors with a turning constraint.** Doorways and tight passages, *and* a vehicle that can't turn in place (set `minimum_turning_radius` for SMAC). Tests the nonholonomic case where grid A* produces an infeasible path.

For the grid planners, run on the occupancy grid directly. For SMAC, load each map as a Nav2 map and run goals through `planner_server`.

## Your task

For **each (planner, map) pair**, run **at least 10 trials** with randomized start/goal pairs (fixed seed for reproducibility) and record:

1. **Path length** (mean ± std), in metres or cells consistently.
2. **Runtime** (mean and **p95** — the tail matters for safety, Lecture 2 §3.1), in milliseconds.
3. **Success rate** — fraction of trials that returned a valid path within a 200 ms deadline.
4. **Feasibility note** — for Map C, whether the path respects the turning constraint (grid A* will not; SMAC will).

Produce a table per map and a short recommendation:

| Map | Planner | Path len (mean±std) | Runtime mean / p95 (ms) | Success @200ms | Feasible? |
|---|---|---|---|---|---|

Then, for each map, write **2–3 sentences** naming the planner you'd ship and *why*, grounded in the table.

## Acceptance criteria

- [ ] A file `challenge-01-bakeoff.md` with a results table per map and a per-map recommendation.
- [ ] At least 10 randomized trials per (planner, map) pair, with a stated seed.
- [ ] Runtime reported as **both mean and p95** — and your recommendation references the p95, not just the mean (a planner with a great mean and a terrible tail is a safety hazard).
- [ ] Your recommendations are defensible and roughly match these expected conclusions:
  - **Map A (open):** A* or weighted A* — fast, optimal, RRT* wastes effort sampling an open space.
  - **Map B (maze):** A* (octile heuristic is misleading but still admissible, so still optimal); note weighted A* can go badly here because the inflated misleading heuristic chases the Euclidean-close-but-path-far goal.
  - **Map C (narrow + turning constraint):** **SMAC Hybrid-A\*** — the only contender that produces a *feasible* path for the nonholonomic vehicle; grid A* produces a shorter-but-undrivable path.
- [ ] A `bakeoff.py` harness that runs the trials and emits the table (reuse Exercises 2 and 3; shell out to Nav2 for SMAC or note the manual measurement).
- [ ] Committed to your Week 18 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The trap is judging planners by **mean runtime and path length alone** and concluding "A* always wins." Two things break that:

1. **The p95 tail.** RRT*'s runtime is *variable* — most trials are fast, but a few unlucky sampling runs are slow. A planner you ship on a safety-critical robot is judged by its worst case, not its average. A* with a fixed grid has a tighter tail; that's a point in its favor that the *mean* hides.
2. **Feasibility is not in the path-length number.** On Map C, grid A* will report the *shortest* path — and that path is *physically undrivable* by the nonholonomic vehicle. A shorter infeasible path is worse than a longer feasible one. If your recommendation for Map C is "A*, it's shortest," you've made the canonical junior mistake: optimizing the wrong objective. The state space (which includes the turning constraint) chooses the planner, not the length column.

## Stretch

- Add **Theta\*** (any-angle A*) as a fifth contender on Map A and B and show its paths are shorter than grid-constrained A* because it allows line-of-sight shortcuts — at a higher per-node cost. Another point on the quality/runtime curve.
- Sweep **weighted A*'s ε** from 1.0 to 4.0 on the maze and plot length and p95 runtime vs. ε. Find the knee — the ε that buys most of the speedup for the least path-length penalty. That knee is the value you'd actually ship.
- For RRT*, plot **path cost vs. sample budget** (250, 500, 1000, 2000, 4000) on Map B and show the asymptotic-optimality convergence curve flattening. This is the picture that explains *why* you pick a sample budget.

## Why this matters

Every robot you build from here has a planner, and someone always wants to "just use A*." The capstone's Nav2 stack (Week 40, Week 48) is graded partly on whether your planner choice is *justified*. This bake-off is how that justification is made: not by asserting a planner is best, but by measuring the candidates on representative maps and reading the trade-off table — including the tail and the feasibility, the two things that separate a benchmark from a decision. The engineer who walks into the review with this table is the one whose planner choice survives the review.
