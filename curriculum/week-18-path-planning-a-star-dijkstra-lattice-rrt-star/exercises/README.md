# Week 18 — Exercises

Three focused drills on path planning, from grid search to sampling-based. Each takes 30–60 minutes. Do them in order — exercise 3 (RRT*) reuses the collision-checking and cost mental model you build in 1 and 2. The grid exercises are pure Python (no ROS2 needed); the Nav2 comparison in Exercise 1 runs against a live `planner_server`.

## Index

1. **[Exercise 1 — A* and Dijkstra by hand, vs. Nav2](exercise-01-a-star-by-hand.md)** — implement both on an occupancy grid, verify A* matches Dijkstra's optimal length while expanding fewer nodes, then race your A* against Nav2's `NavfnPlanner` on the same map. (~50 min, guided)
2. **[Exercise 2 — The grid planners](exercise-02-grid-planners.py)** — a runnable, correct A*/Dijkstra with a self-checking harness: it proves optimality against Dijkstra, demonstrates that an inadmissible heuristic breaks optimality, and shows weighted A*'s speed/quality trade-off. (~45 min, runnable)
3. **[Exercise 3 — RRT and RRT*](exercise-03-rrt-star.py)** — a runnable RRT and RRT* in continuous 2D, with the `choose_parent` + `rewire` steps that make RRT* asymptotically optimal, and a demo that RRT*'s path improves with more samples while RRT's doesn't. (~50 min, runnable)

## How to work the exercises

- The grid exercises need only **Python 3.12 + numpy + matplotlib**. `pip install numpy matplotlib` if you don't have them.
- Exercise 1's Nav2 comparison needs a **running `planner_server`** (bring up Nav2 from Week 17). If your sim is broken, the pure-Python comparison still works — you just skip the live Nav2 leg and compare against the reference numbers.
- **Run the self-checks.** Each `.py` ends with assertions that prove correctness (A* optimality, RRT* improvement). If an assertion fails, you have a bug — read the message, it names the property that broke.
- When your A* "works but takes a weird route," check the heuristic *first* — a wrong (inadmissible) heuristic is the #1 cause, and the self-check in Exercise 2 catches it.
- Each runnable exercise (`.py`) ends with an **expected output** block. If your output doesn't match the *shape* (exact node counts vary with tie-breaking), you're not done.

## Running the Python exercises

The two `.py` files are standalone — no ROS2 required for the planners themselves:

```bash
python3 exercise-02-grid-planners.py
python3 exercise-03-rrt-star.py --samples 1500 --seed 7
```

Both accept `--plot` to render the grid/tree and the path with matplotlib, and `--seed` for reproducibility. Read the file headers for the full flag list.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-18` to compare.
