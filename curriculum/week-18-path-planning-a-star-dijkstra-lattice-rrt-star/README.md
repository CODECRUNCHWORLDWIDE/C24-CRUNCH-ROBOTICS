# Week 18 — Path Planning: A*, Dijkstra, Lattice, RRT*

Welcome to the week where the planner stops being a black box. Last week Nav2's `NavfnPlanner` produced a path and you trusted it. This week you *build* the planner — A* and Dijkstra by hand on an occupancy grid, in pure Python, no library — then you build RRT* for continuous spaces, and you learn to choose a planner by the *structure of the state space* instead of by habit. By Friday you will be able to look at any planning problem and say, with reasons, "that's an A*-on-a-grid problem" or "that's an RRT*-in-a-7-DOF-configuration-space problem" or "that needs a state lattice because the vehicle can't turn in place."

We assume you finished Week 17 — you have Nav2 up on your week-7 map, you know what a costmap is, and you can swap the planner plugin in `nav2_params.yaml`. That matters this week because you will run *your own* A* against Nav2's `NavfnPlanner` on the *same* costmap and compare path quality and runtime, then drop in `SMAC Hybrid-A*` for an Ackermann-like vehicle and watch the turning radius constraint reshape the path.

The one idea to internalize before you read another line: **choose your planner by the structure of your state space.** A flat warehouse floor where the robot can spin in place is a 2D grid — A* and Dijkstra own it. A car that can't turn in place lives in a 3D state space (x, y, heading) with motion constraints — that's where state lattices and Hybrid-A* live. A 7-DOF arm lives in a high-dimensional continuous configuration space where grids explode combinatorially — that's where sampling-based planners (RRT, RRT*, BIT*) dominate. **The planner is not a preference. It is a consequence of the geometry of where the robot can go.** Get the state space right and the planner picks itself; get it wrong and no amount of tuning saves you.

This week continues Phase 3's safety stance. The fail-safe question this week: *what does the robot do when the planner returns no path at all, or returns one too slowly to be safe?* You will answer it by measuring — runtime is a safety property, not a benchmark vanity metric.

## Learning objectives

By the end of this week, you will be able to:

- **Implement** Dijkstra and A* from scratch on an occupancy grid in pure Python — the open set as a priority queue, the closed set, `g`/`h`/`f` costs, the parent map, and path reconstruction — with no planning library.
- **State and verify** the admissibility and consistency conditions on a heuristic, and explain precisely why an admissible heuristic guarantees A* finds the optimal path while an inadmissible one trades optimality for speed.
- **Compare** A*, Dijkstra, and Nav2's `NavfnPlanner` on the *same* costmap: path length, nodes expanded, and wall-clock runtime — and explain the differences from the algorithms, not folklore.
- **Explain** D* Lite and incremental replanning: why recomputing from scratch every cycle is wasteful when only a few cells changed, and how D* Lite reuses prior search under dynamic obstacles.
- **Describe** state-lattice planners and Hybrid-A*: how a motion primitive set encodes a vehicle's kinematic constraints, why the search runs over (x, y, heading) instead of (x, y), and what `minimum_turning_radius` does to the path.
- **Implement** RRT and RRT* in continuous 2D: random sampling, nearest-neighbor, steering, collision checking, and — the RRT* additions — the rewiring step and the near-radius that make it asymptotically optimal.
- **Choose** the right planner for a problem from the structure of its state space — grid search for flat ground, lattice/Hybrid-A* for nonholonomic vehicles, sampling-based for high-DOF manipulation — and defend the choice.
- **Treat runtime as a safety property**: measure planning latency, and declare what the robot does when the planner is too slow or returns no path.

## Prerequisites

This week assumes you have completed **C24 weeks 1–17**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**, with **Nav2** installed and your **week-7 map** loadable — Exercise 4 (the Nav2 comparison) runs against a live `planner_server`.
- **Python 3.12** with `numpy`, `matplotlib`, and `heapq` (stdlib). The hand-rolled planners are pure Python; you only need numpy for the grid and matplotlib to visualize.
- The **costmap literacy** from Week 17 — you know a costmap is a grid of costs 0–254, what `lethal`/`inscribed`/`inflated` mean, and how to read an `OccupancyGrid`.
- Comfort with **graph terminology** — nodes, edges, neighbors, a priority queue — and with **asymptotic complexity** (you can say why a priority-queue pop is `O(log n)`).
- The **SMAC planner plugin** available: `sudo apt install ros-jazzy-nav2-smac-planner` for the Hybrid-A* comparison.

You do **not** need a formal algorithms course. We derive Dijkstra and A* from first principles and build RRT* step by step. If you've only ever called a planner and read its output, this is the week the search inside becomes load-bearing.

## Topics covered

- **Graph search foundations**: the occupancy grid as a graph, 4-connected vs. 8-connected neighborhoods, edge costs (uniform, diagonal `√2`, costmap-weighted), the open set (priority queue) and closed set.
- **Dijkstra**: uniform-cost search, why it expands in cost-rings, optimality, and its `O((V+E) log V)` complexity with a binary heap.
- **A***: the `f = g + h` evaluation function, admissible heuristics (Euclidean, Manhattan, octile), consistency/monotonicity, why A* with an admissible heuristic is optimal, and why a *weighted* A* (`f = g + ε·h`, ε > 1) trades optimality for a dramatic speedup.
- **D* Lite and incremental replanning**: the cost of full replanning under dynamic obstacles, the key idea of searching backward from the goal and reusing the prior tree, and where Nav2 uses replanning instead (re-running the planner each cycle via the BT's `RateController`).
- **State-lattice planners**: motion primitives that respect kinematic constraints, the (x, y, heading) search space, and how a lattice encodes "this vehicle can only move like *this*."
- **Hybrid-A* / SMAC**: continuous-state A* with a discretized control set, the Dubins/Reeds-Shepp analytic expansion, `minimum_turning_radius`, and why it dominates car-like ground vehicles.
- **Sampling-based planning**: RRT (rapidly-exploring random tree) — sample, nearest, steer, collision-check, extend — its probabilistic completeness, and why it scales to high dimensions where grids explode.
- **RRT***: the two additions that make RRT asymptotically optimal — `choose_parent` (connect a new node to the lowest-cost reachable neighbor) and `rewire` (re-parent nearby nodes through the new node if it lowers their cost) — plus the shrinking near-radius and BIT* at a glance.
- **The planner-selection taste test**: matching a planner to a state space — flat-ground grid (A*), nonholonomic vehicle (lattice/Hybrid-A*), high-DOF arm (RRT*/BIT*) — and the runtime-as-safety lens.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Grid as graph; Dijkstra; A*; heuristics              |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | A* by hand; heuristic admissibility; the Nav2 compare |   1h     |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | D* Lite; state lattices; Hybrid-A*; SMAC swap        |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | RRT; RRT* rewiring; sampling-based planning           |   1h     |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Planner selection; runtime-as-safety; the benchmark   |   0h     |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                               |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, benchmark write-up polish              |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                      | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The planning textbook chapters, the Nav2 planner docs, the canonical papers, and the talks worth your time |
| [lecture-notes/01-graph-search-dijkstra-and-a-star.md](./lecture-notes/01-graph-search-dijkstra-and-a-star.md) | The grid as a graph, Dijkstra, A*, heuristic admissibility, weighted A*, and D* Lite |
| [lecture-notes/02-lattices-hybrid-a-star-and-sampling-based-planning.md](./lecture-notes/02-lattices-hybrid-a-star-and-sampling-based-planning.md) | State lattices, Hybrid-A*/SMAC, RRT, RRT* rewiring, and the planner-selection taste test |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-a-star-by-hand.md](./exercises/exercise-01-a-star-by-hand.md) | Implement A* and Dijkstra on a grid, then compare nodes-expanded against the Nav2 NavFn planner |
| [exercises/exercise-02-grid-planners.py](./exercises/exercise-02-grid-planners.py) | A runnable, correct A*/Dijkstra implementation with a self-checking test harness and an admissibility demo |
| [exercises/exercise-03-rrt-star.py](./exercises/exercise-03-rrt-star.py) | A runnable RRT and RRT* in continuous 2D, with the rewiring step that makes RRT* asymptotically optimal |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-planner-bakeoff.md](./challenges/challenge-01-planner-bakeoff.md) | Benchmark four planners on three maps; produce the path-quality vs. runtime table that justifies a planner choice |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the runtime-as-safety fail-safe declaration |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_planners` library: A*, Dijkstra, RRT* behind one interface, with a Nav2 global-planner plugin wrapper |

## The "the path is optimal" promise

C24 uses a recurring marker for every exercise that ends in a planner producing a correct path. For grid search, that marker is **optimality against a known-shortest path**:

```
$ python3 exercise-02-grid-planners.py
A*       path length: 28.14  nodes expanded:  412  time: 1.83 ms
Dijkstra path length: 28.14  nodes expanded: 1187  time: 4.91 ms
[OK] A* and Dijkstra agree on path length (both optimal).
[OK] A* expanded fewer nodes than Dijkstra (the heuristic did its job).
```

If A* and Dijkstra disagree on path length, your A* heuristic is **inadmissible** (it over-estimates) and you have a bug — A* with an admissible heuristic must match Dijkstra's optimal length exactly. If A* expands *more* nodes than Dijkstra, your heuristic is doing nothing (or is negative). The point of Week 18 is to make "same length, fewer nodes" ordinary — and to make a wrong heuristic *loud* instead of a silently sub-optimal path.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement **weighted A*** (`f = g + ε·h` with ε = 1.5, 2.0, 3.0) and plot the trade-off curve: as ε grows, nodes-expanded drops sharply while path length creeps up. This is the single most useful practical A* knob and almost nobody teaches it.
- Implement **Theta\*** (any-angle A* that allows line-of-sight shortcuts between non-adjacent cells) and compare its path against grid-constrained A* — Theta\* paths look like what a human would draw.
- Read the **RRT\* paper** (Karaman & Frazzoli 2011) until you can state the near-radius `r(n) = γ(log n / n)^{1/d}` and explain why it shrinks as the tree grows. This is the heart of asymptotic optimality.
- Profile your A* with `cProfile` and find the hot line. It is almost always the priority-queue operation or the neighbor generation. Optimize one and measure the speedup — runtime is a safety property (this week's fail-safe).

## Up next

Week 19 takes the planners you built and the Nav2 stack you brought up and wires them into a coherent task with **behavior trees** — the integration glue that decides *when* to plan, *when* to recover, and *when* to yield to a person. The planner-selection instinct you build this week is what the BT's `ComputePathToPose` leaf is choosing under the hood. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
