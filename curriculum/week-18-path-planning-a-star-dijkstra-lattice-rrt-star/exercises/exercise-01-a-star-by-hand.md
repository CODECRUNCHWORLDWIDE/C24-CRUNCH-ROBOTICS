# Exercise 1 — A* and Dijkstra by Hand, Then vs. Nav2

**Goal:** Implement A* and Dijkstra on an occupancy grid *from scratch* (no library), prove your A* is optimal by matching Dijkstra's path length while expanding fewer nodes, and then race your A* against Nav2's `NavfnPlanner` on the same map. You will train the single most important planning habit: verifying optimality empirically instead of trusting the path looks right.

**Estimated time:** 50 minutes. Guided.

---

## Setup

Pure Python for the first half:

```bash
pip install numpy matplotlib       # if you don't have them
```

For the Nav2 comparison (Step 5), bring up Nav2 on your week-7 map (Week 17, Exercise 1) so `/planner_server` is `active [3]`.

The provided `exercise-02-grid-planners.py` is a *complete, correct* implementation — but for this exercise, **write your own first**, then check it against that file. You only learn A* by writing the priority queue yourself.

---

## Step 1 — Build a test grid

Make a 30×30 occupancy grid (0 = free, 100 = lethal) with a wall that forces a non-trivial path — say a vertical wall from row 5 to row 25 in column 15, with a gap at row 15. Start at `(2, 2)`, goal at `(28, 28)`.

```python
import numpy as np
LETHAL = 100
grid = np.zeros((30, 30), dtype=np.int16)
grid[5:25, 15] = LETHAL      # vertical wall
grid[15, 15] = 0             # gap (doorway) at row 15
start, goal = (2, 2), (28, 28)
```

A planner that doesn't route through the gap is broken. A planner that cuts the corner of the wall is broken (corner-cutting). Keep this grid; you'll reuse it.

---

## Step 2 — Implement Dijkstra

Write `dijkstra(grid, start, goal)` returning `(path, length, nodes_expanded)`. The spine is in Lecture 1 §2: a `heapq` keyed on `g`, a `closed` set, a `parent` map, 8-connected neighbors with `√2` diagonals and corner-cut prevention. Dijkstra is your **ground truth** — it's provably optimal, so its `length` is the number A* must match.

---

## Step 3 — Implement A*

Write `a_star(grid, start, goal)` returning the same triple. The *only* change from Dijkstra: prioritize by `f = g + h`, where `h` is the **octile** distance (Lecture 1 §3.1) for an 8-connected grid. Use the octile formula exactly:

```python
import math
def octile(a, b):
    dr, dc = abs(a[0]-b[0]), abs(a[1]-b[1])
    return (dr + dc) + (math.sqrt(2) - 2) * min(dr, dc)
```

---

## Step 4 — The optimality self-check (the load-bearing step)

Run both on your grid and assert:

```python
p_d, len_d, exp_d = dijkstra(grid, start, goal)
p_a, len_a, exp_a = a_star(grid, start, goal)

assert abs(len_a - len_d) < 1e-6, \
    f"A* length {len_a} != Dijkstra {len_d} — your heuristic is INADMISSIBLE (over-estimates)"
assert exp_a <= exp_d, \
    f"A* expanded {exp_a} >= Dijkstra {exp_d} — your heuristic isn't helping (is it zero/negative?)"
print(f"A*:       length {len_a:.2f}, expanded {exp_a}")
print(f"Dijkstra: length {len_d:.2f}, expanded {exp_d}")
print("[OK] A* is optimal (matches Dijkstra) and faster (fewer nodes).")
```

**If the first assert fires:** your octile formula is wrong, or you used Manhattan (which over-estimates on an 8-connected grid and is inadmissible). **If the second fires:** your heuristic returns 0 (that's just Dijkstra) or is mis-signed. This is the entire point — you catch a broken heuristic *the instant you write it*, not three weeks later when the robot takes a weird route.

To deliberately *see* the failure, swap octile for Manhattan (`dr + dc`) and watch the optimality assert fire — Manhattan over-estimates the diagonal-rich path, so A* returns a longer-than-optimal route. Restore octile.

---

## Step 5 — Race your A* against Nav2's NavFn

With Nav2 up on your week-7 map, send a goal and capture Nav2's path:

```bash
ros2 topic echo /plan --once > /tmp/nav2_plan.txt
```

Then run your A* on the *same* costmap. Get the costmap as an `OccupancyGrid`:

```bash
ros2 topic echo /global_costmap/costmap --once > /tmp/costmap.txt
```

Load the costmap into your grid (the `OccupancyGrid.data` is row-major, `info.width` × `info.height`), run your A* start→goal in grid cells, and compare:

- **Path length** — convert your cell path to metres (× `resolution`) and compare to Nav2's `/plan` arc length. They should be within a few percent (both are grid A*/Dijkstra variants).
- **Nodes expanded** — yours is instrumented; Nav2's isn't easily, so just note your count and your wall-clock time (`time.perf_counter()` around the call).

Record both in a short `notes/week-18/a-star-vs-navfn.md`. The point is not to beat Nav2 — it's to confirm your hand-rolled planner produces a path of the *same quality*, proving you understand what `NavfnPlanner` does.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] Your `dijkstra` and `a_star` both return a valid path through the doorway (no corner-cutting).
- [ ] The optimality self-check passes: A* length == Dijkstra length, A* expands fewer nodes.
- [ ] Swapping octile → Manhattan makes the optimality assert fire (you saw the inadmissibility break optimality on purpose), then you restored octile.
- [ ] Your A* path on the week-7 costmap is within a few percent of Nav2's `/plan` length.
- [ ] `notes/week-18/a-star-vs-navfn.md` records the length and runtime comparison.

---

## Stretch

- Visualize the expanded nodes for A* vs. Dijkstra with matplotlib (color the closed set). A*'s closed set is a narrow corridor toward the goal; Dijkstra's is a fat disc. *Seeing* the heuristic at work is worth a thousand words.
- Add weighted A* (`f = g + ε·h`, ε = 2.0) and confirm it expands far fewer nodes than ε = 1.0, at a slightly longer path. This is your preview of the homework's trade-off curve.
- Instrument the open-set max size. A* keeps a smaller frontier than Dijkstra — quantify it. Frontier size is memory, and memory is a real constraint on the Jetson.

---

When this feels comfortable, move to [Exercise 2 — The grid planners](exercise-02-grid-planners.py) to check your implementation against a reference, then [Exercise 3 — RRT*](exercise-03-rrt-star.py).
