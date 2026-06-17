# Week 36 — Exercises

Three drills that take you from the assignment math on paper to a running auction that reallocates a failed robot's work. Do them in order — exercise 3 reuses the cost model you build in 1 and 2. The first is paper-and-`scipy`; the second and third are runnable Python (no ROS2 package required, though the cost functions are written to drop straight into a node).

## Index

1. **[Exercise 1 — The cost matrix on paper](./exercise-01-cost-matrix-on-paper.md)** — build a cost matrix from robot/task poses, solve it greedily *and* with the Hungarian algorithm, and prove greedy is sub-optimal on a planted matrix. (~50 min, guided)
2. **[Exercise 2 — The Hungarian allocator](./exercise-02-hungarian-allocator.py)** — a runnable optimal allocator: cost matrix from poses, `scipy.optimize.linear_sum_assignment`, and correct handling of the rectangular N≠M case. (~45 min, runnable)
3. **[Exercise 3 — The SSI auction](./exercise-03-ssi-auction.py)** — a sequential-single-item auctioneer that bids on marginal cost, re-auctions on task arrival, and *reallocates* when a robot drops out. (~50 min, runnable)

## How to work the exercises

- You need `numpy` and `scipy` (you have them from Phase 2). `python3 -c "import scipy; print(scipy.__version__)"` should work.
- Exercise 1 you do mostly by hand, then check with one `scipy` call. Resist running the solver before you've worked the greedy-vs-optimal argument on paper — the whole point is to *feel* why greedy loses.
- The two runnable exercises (`.py`) are standalone and pure Python — no `colcon`, no ROS2. They end with an **expected output** block. If your output doesn't match the *shape* (the assignment may tie-break differently), you're not done.
- Think about the cost model honestly. The toy exercises use Euclidean distance; note where that lies (through walls) versus a real nav-graph path cost, because that's the gap between the exercise and the mini-project.

## Running the Python exercises

```bash
python3 exercise-02-hungarian-allocator.py
python3 exercise-03-ssi-auction.py
```

No ROS2 needed. The cost functions are deliberately factored so you can later import them into a real allocator node that pulls robot poses from `/fleet_states` and task locations from the dispatcher.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-36` to compare.
