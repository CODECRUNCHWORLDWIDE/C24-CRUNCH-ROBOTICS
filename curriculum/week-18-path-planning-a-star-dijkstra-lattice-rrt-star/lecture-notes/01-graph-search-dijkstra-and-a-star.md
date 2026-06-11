# Lecture 1 — Graph Search: Dijkstra, A*, and the Heuristic That Makes the Difference

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can implement Dijkstra and A* on an occupancy grid from scratch, state and check the admissibility and consistency conditions on a heuristic, explain exactly why an admissible heuristic guarantees optimality, and articulate when weighted A* and D* Lite earn their keep.

If you remember one sentence from this lecture, remember this one:

> **A* is Dijkstra with a heuristic that tells the search which way the goal is — and the entire art of A* is choosing a heuristic that never lies about being optimistic (admissible) so the path stays optimal, while being as informed as possible so the search stays fast.**

You spent Week 17 trusting Nav2's `NavfnPlanner`. It is, under the hood, almost exactly the algorithm you're about to build by hand. After this lecture, the planner is not magic. It is a priority queue, a cost function, and a heuristic — and you will have written all three.

---

## 1. The occupancy grid as a graph

Path planning on a 2D map starts by treating the grid as a **graph**. Each free cell is a **node**. Each node connects by an **edge** to its neighbors. Two choices define the graph:

### 1.1 Connectivity

- **4-connected** — each cell connects to its N, S, E, W neighbors. Edge cost 1 (or the cell's cost). Paths are Manhattan-shaped: only horizontal and vertical moves.
- **8-connected** — add the four diagonals. Diagonal edges cost `√2 ≈ 1.414` (not 1 — a diagonal move covers more ground, and pretending it costs 1 produces paths that cheat). 8-connected paths look more natural.

Almost always you want **8-connected**, with diagonal cost `√2`. The single most common beginner bug is giving diagonals cost 1, which makes the planner prefer staircases and produces paths that are provably too short on the grid metric.

### 1.2 Edge cost

The edge cost from cell A to cell B is the *move cost* (1 for orthogonal, `√2` for diagonal) optionally **weighted by the destination cell's costmap value**. On a Nav2 costmap (Week 17), entering an inflated cell costs more than entering a free cell, so the planner naturally keeps clearance from walls without you writing any "avoid walls" logic. The cost is in the grid, not the algorithm. A lethal cell (cost 254) is treated as an obstacle — no edge enters it.

```python
import math

ORTHO = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

def neighbors(grid, r, c):
    """Yield (nr, nc, move_cost) for free 8-connected neighbors of (r, c)."""
    H, W = grid.shape
    for dr, dc in ORTHO:
        nr, nc = r + dr, c + dc
        if 0 <= nr < H and 0 <= nc < W and grid[nr, nc] < LETHAL:
            yield nr, nc, 1.0
    for dr, dc in DIAG:
        nr, nc = r + dr, c + dc
        if 0 <= nr < H and 0 <= nc < W and grid[nr, nc] < LETHAL:
            # Prevent corner-cutting: a diagonal is only allowed if both
            # orthogonal cells it passes are also free.
            if grid[r, nc] < LETHAL and grid[nr, c] < LETHAL:
                yield nr, nc, math.sqrt(2.0)
```

> **Corner-cutting** is the second-most-common bug: an 8-connected planner will happily slip diagonally between two obstacles that touch at a corner, producing a path the robot can't physically follow. The fix is in the snippet: a diagonal move is only legal if both orthogonal cells it brushes are free. Forget this and your robot clips door frames.

One more subtlety that bites in production: the grid cells are **indices**, but the robot lives in **metres**. Conversion uses the costmap's `resolution` (metres per cell) and `origin` (the world coordinate of cell `(0,0)`): `world_x = origin_x + col * resolution`, `world_y = origin_y + row * resolution`. Mixing up `(row, col)` and `(x, y)` — they're *transposed*, since row is the y-axis and column is the x-axis — is a classic bug that flips your path 90°. Keep the grid in `(row, col)` internally and convert to `(x, y)` only at the boundary, exactly once, and you'll avoid it.

---

## 2. Dijkstra: uniform-cost search

Dijkstra's algorithm finds the shortest path from a start to *every* node (or, with early termination, to one goal). The idea: always expand the unexpanded node with the **lowest known cost from the start.** It expands outward in cost-rings, like a flood fill weighted by cost.

```python
import heapq

def dijkstra(grid, start, goal):
    g = {start: 0.0}             # best known cost from start
    parent = {start: None}
    open_set = [(0.0, start)]    # priority queue keyed on g
    closed = set()
    expanded = 0

    while open_set:
        cost, node = heapq.heappop(open_set)
        if node in closed:
            continue
        closed.add(node)
        expanded += 1
        if node == goal:
            return reconstruct(parent, goal), g[goal], expanded

        r, c = node
        for nr, nc, move_cost in neighbors(grid, r, c):
            nxt = (nr, nc)
            new_g = g[node] + move_cost * cell_weight(grid, nr, nc)
            if nxt not in g or new_g < g[nxt]:
                g[nxt] = new_g
                parent[nxt] = node
                heapq.heappush(open_set, (new_g, nxt))
    return None, math.inf, expanded     # no path
```

Dijkstra is **optimal** (it always finds the shortest path) and **complete** (if a path exists, it finds it). Its weakness: it has no idea where the goal is, so it expands cells in *every* direction equally. On a large open map, it explores a huge disc around the start before reaching a goal that might be straight ahead. That waste is exactly what the heuristic fixes.

The complexity is `O((V + E) log V)` with a binary heap — every node is pushed/popped (the `log V` per heap op) and every edge is relaxed.

---

## 3. A*: Dijkstra plus a sense of direction

A* changes one thing: instead of prioritizing the open set by `g(n)` (cost-so-far), it prioritizes by

```
f(n) = g(n) + h(n)
```

where `h(n)` is a **heuristic** — an estimate of the remaining cost from `n` to the goal. Now the search prefers nodes that are both cheap to reach *and* estimated to be close to the goal. It expands toward the goal instead of in all directions.

```python
def heuristic(node, goal):
    """Octile distance: the exact 8-connected distance ignoring obstacles.
    This is the tightest admissible heuristic for an 8-connected grid."""
    dr = abs(node[0] - goal[0])
    dc = abs(node[1] - goal[1])
    return (dr + dc) + (math.sqrt(2.0) - 2.0) * min(dr, dc)

def a_star(grid, start, goal):
    g = {start: 0.0}
    parent = {start: None}
    open_set = [(heuristic(start, goal), start)]   # f = g + h, g(start)=0
    closed = set()
    expanded = 0

    while open_set:
        f, node = heapq.heappop(open_set)
        if node in closed:
            continue
        closed.add(node)
        expanded += 1
        if node == goal:
            return reconstruct(parent, goal), g[goal], expanded

        r, c = node
        for nr, nc, move_cost in neighbors(grid, r, c):
            nxt = (nr, nc)
            new_g = g[node] + move_cost * cell_weight(grid, nr, nc)
            if nxt not in g or new_g < g[nxt]:
                g[nxt] = new_g
                parent[nxt] = node
                heapq.heappush(open_set, (new_g + heuristic(nxt, goal), nxt))
    return None, math.inf, expanded
```

The *only* differences from Dijkstra are the initial `f` and the `+ heuristic(nxt, goal)` in the push. **Dijkstra is A* with `h(n) = 0`.** That equivalence is worth burning in: it means everything you know about Dijkstra's correctness carries over, and the heuristic is a pure *speedup* — as long as it's admissible.

### 3.1 Which heuristic?

The heuristic must match the graph's geometry to be tight:

| Grid | Tightest admissible `h` | Why |
|---|---|---|
| 4-connected | **Manhattan** `|dr| + |dc|` | You can only move orthogonally; that's the exact obstacle-free distance. |
| 8-connected | **Octile** `(dr+dc) + (√2 − 2)·min(dr,dc)` | Accounts for cheaper diagonal moves; the exact 8-connected obstacle-free distance. |
| Any-angle | **Euclidean** `√(dr² + dc²)` | The straight-line distance; admissible for any movement model. |

Using **Manhattan on an 8-connected grid** is a classic mistake: it *over*-estimates (it assumes you can't move diagonally when you can), which makes it **inadmissible**, which breaks optimality. Use octile for 8-connected. Euclidean is always admissible but looser (it under-estimates more than octile), so A* with Euclidean expands more nodes than A* with octile — still optimal, just slower.

### 3.2 A worked expansion, by hand

Walking three expansions by hand cements what `f = g + h` actually does. Take a tiny obstacle-free 4-connected grid, start `S = (0,0)`, goal `G = (0,3)`, unit edge costs, Manhattan heuristic (admissible for 4-connected).

```
   col:  0   1   2   3
row 0:   S   .   .   G
```

- **Expand S.** `g(S)=0`, `h(S)=3` (Manhattan to G), `f(S)=3`. Its neighbors get pushed: `(0,1)` with `g=1, h=2, f=3`; `(1,0)` with `g=1, h=4, f=5`.
- **Pop the lowest f.** `(0,1)` (f=3) beats `(1,0)` (f=5), so A* expands *toward the goal*, not sideways. Push `(0,2)`: `g=2, h=1, f=3`.
- **Pop `(0,2)`** (f=3). Push `(0,3)=G`: `g=3, h=0, f=3`.
- **Pop G.** Done. Total cost 3, and A* never expanded `(1,0)` — the heuristic kept the search on the beeline.

Now compare to **Dijkstra** on the same grid: with `h=0`, the open set is keyed on `g` alone, so after expanding S, `(0,1)` and `(1,0)` are *tied* at `g=1` and Dijkstra expands *both* before reaching G — it has no reason to prefer the goal-ward one. That single extra expansion, scaled to a 1,000,000-cell map, is the difference between A* and Dijkstra: the heuristic prunes the sideways exploration. The whole speedup is "don't expand cells that point away from the goal," and `f = g + h` is exactly how that preference is encoded.

### 3.3 Tie-breaking matters more than you'd think

When two nodes have equal `f`, which do you expand first? The `heapq` breaks ties by whatever is second in the tuple — and a naive tie-break expands a *fat diamond* of equal-f cells, doing far more work than necessary on open maps. Two standard fixes:

- **Prefer higher `g` on ties** (push `(f, -g, node)`): break toward nodes deeper into the search, which heads to the goal faster.
- **Tiny heuristic nudge** (multiply `h` by `1 + ε` for a microscopic ε ≈ 1/1000): tilts ties toward the goal without breaking admissibility in practice.

On an open map, good tie-breaking can cut nodes-expanded by 2–10× with zero change to path length. It's the cheapest A* optimization there is, and it's why two correct A* implementations can report very different node counts (which is why this week's self-checks compare *path length*, which is invariant, not node count, which depends on tie-breaking).

---

## 4. Admissibility, consistency, and why optimality holds

This is the conceptual heart of the week. Get it right and you can reason about any heuristic search.

### 4.1 Admissibility

A heuristic `h` is **admissible** if it **never over-estimates** the true cost-to-go:

```
h(n) ≤ h*(n)   for every node n,   where h*(n) is the true optimal cost from n to goal.
```

In plain terms: an admissible heuristic is **optimistic** — it may say the goal is closer than it really is, but never further. The octile and Euclidean distances are admissible because the true path (around obstacles) can only be *longer* than the straight-line/diagonal-free distance, never shorter.

**Theorem (the one you must be able to state):** *A\* with an admissible heuristic always returns an optimal path.*

The intuition: suppose A* is about to return a sub-optimal path to the goal with cost `C > C*` (the optimal cost). Then some node `n` on the optimal path is still in the open set with `f(n) = g(n) + h(n)`. Because `h` is admissible, `f(n) = g(n) + h(n) ≤ g(n) + h*(n) = C*`. So `f(n) ≤ C* < C`. But A* always expands the *lowest-f* node, so it would have expanded `n` (with `f(n) ≤ C*`) before returning a goal with cost `C > C*`. Contradiction. Therefore A* can't return a sub-optimal path. That's the whole proof, and it's why **a single over-estimating cell anywhere in your heuristic can silently corrupt the path.**

### 4.2 Consistency (monotonicity)

A stronger condition. `h` is **consistent** if, for every edge from `n` to `n'`:

```
h(n) ≤ cost(n, n') + h(n')
```

This is a triangle inequality on the heuristic. Consistency implies admissibility, and it buys you a practical guarantee: **with a consistent heuristic, the first time A* expands a node, it has already found the optimal path to it** — so you never need to re-open a closed node. (With a merely-admissible-but-inconsistent heuristic, you may have to re-open closed nodes, which is slower and trickier to implement.) Octile and Euclidean on a grid are both consistent, which is why the `closed` set in the code above is safe.

### 4.2.1 Why consistency lets you skip the closed-node re-open

It's worth one more sentence on *why* consistency is the property you want, because it changes the code. With a consistent heuristic, the `f` values along any path are **non-decreasing** (`f` never drops as you move toward the goal). That monotonicity means A* pops nodes in non-decreasing `f` order, so the first pop of any node is its cheapest — there's never a cheaper route discovered *later*. Hence the simple `closed` set in the code above is correct: once closed, always optimal, never re-open. If your heuristic were admissible but *inconsistent*, you'd have to allow re-opening closed nodes (re-adding them to the open set when a cheaper path appears), which complicates the code and slows the search. The grid heuristics (octile, Euclidean) are consistent, so you get the simple version for free — but if you ever hand-craft a heuristic, check consistency, not just admissibility, before trusting a no-re-open implementation.

### 4.3 The verification habit

You verify admissibility *empirically* by the optimality test from the week's promise: **A\* with an admissible heuristic must return the exact same path length as Dijkstra** (which has no heuristic and is provably optimal). If your A* returns a *shorter* length than Dijkstra, that's impossible — you have a bug (probably a negative or wrong edge cost). If it returns a *longer* length, your heuristic over-estimates — it's inadmissible. Same length, fewer nodes expanded: correct. This is exactly the self-check in Exercise 2, and it's how you catch a broken heuristic the moment you write it instead of three weeks later when the robot takes a weird route.

---

## 5. Weighted A*: trading optimality for speed (on purpose)

Sometimes optimal is too slow. **Weighted A*** inflates the heuristic:

```
f(n) = g(n) + ε · h(n),   ε > 1
```

With ε > 1 the heuristic is now *inadmissible by construction* — it over-estimates by a factor of ε — so the path is no longer guaranteed optimal. But the search becomes far greedier toward the goal and expands dramatically fewer nodes. The guarantee you *do* keep: the returned path is at most **ε times** the optimal length (the *bounded sub-optimality* guarantee). In practice ε = 1.5–3.0 gives a 5–50× speedup for a path 10–30% longer — and on a robot that needs a plan in 50 ms, a slightly-longer path *now* beats an optimal path *too late*. This is the single most useful practical knob in grid planning, and the homework has you plot the trade-off curve.

> **Runtime is a safety property (this week's fail-safe theme).** A planner that returns the optimal path in 800 ms on a robot moving 1.5 m/s has let the robot travel 1.2 m on stale information before the plan exists. Weighted A* is one tool for staying inside the latency budget. The point is that "optimal" and "fast enough to be safe" can conflict, and the engineer chooses — explicitly, with a measured number, not by hoping.

There's a deeper version of weighted A* worth naming: **Anytime Repairing A\* (ARA\*)**. It runs weighted A* with a large ε to get *a* path immediately, then progressively *lowers* ε and re-searches, reusing prior work, so the path improves toward optimal *if and only if time remains*. When the deadline hits, you take the best path so far. This is the planner shape for a robot that needs *something* now and *better* if it can get it — the textbook anytime-planning pattern, and the natural answer to "what do I do when the planner might be too slow?" You don't implement ARA* this week, but it's the principled version of the latency/optimality trade-off, and it's a great stretch read.

---

## 6. D* Lite and incremental replanning

A* plans once, from scratch. But a robot's world changes — someone moves a chair into the hallway. Re-running A* from scratch every cycle, on a map where only a handful of cells changed, throws away almost all the prior work. **D* Lite** (Koenig & Likhachev, 2002) is the canonical fix.

The core ideas, conceptually (you don't implement D* Lite this week, but you must be able to explain it):

- **Search backward from the goal.** D* Lite computes costs *to the goal*, so when the robot moves, the goal-directed costs of most cells are still valid.
- **Reuse the prior search tree.** When a few cell costs change (a new obstacle), D* Lite identifies the *locally inconsistent* nodes affected and re-expands only those, propagating the change outward until consistency is restored — instead of re-expanding the whole map.
- **The payoff:** when the change is small and far from the robot, the replan is nearly free; the cost scales with the *size of the change*, not the size of the map.

### 6.0 Seeing the difference: the shape of the closed set

The clearest way to internalize A* vs. Dijkstra is to *color the closed set* (the cells each expanded) and look at the shape. The stretch goal in Exercise 1 has you do exactly this, and it's worth previewing because the picture is the whole lesson:

```
   Dijkstra closed set            A* (octile) closed set
   (a fat disc around start)      (a narrow corridor toward goal)
   ┌───────────────────┐          ┌───────────────────┐
   │     ▒▒▒▒▒▒▒        │          │  S                │
   │   ▒▒▒▒▒▒▒▒▒▒▒      │          │   ▒▒              │
   │  ▒▒▒▒▒S▒▒▒▒▒▒▒     │          │     ▒▒▒            │
   │  ▒▒▒▒▒▒▒▒▒▒▒▒▒  G  │          │       ▒▒▒▒         │
   │   ▒▒▒▒▒▒▒▒▒▒▒      │          │          ▒▒▒▒  G   │
   │     ▒▒▒▒▒▒▒        │          │             ▒▒     │
   └───────────────────┘          └───────────────────┘
```

Dijkstra has no idea where `G` is, so it expands in cost-rings *equally in all directions* — a fat disc. A* with an admissible heuristic expands a *narrow corridor* aimed at the goal, because `f = g + h` penalizes cells whose heuristic points away. Same path, far fewer cells touched. That picture — disc vs. corridor — is what every "A* is faster than Dijkstra" sentence is really about, and once you've *seen* it you never forget what the heuristic buys you.

### 6.1 What Nav2 actually does

Here's the honest 2026 picture: **Nav2 does not use D* Lite by default.** Instead, it **replans from scratch** — the navigation BT's `RateController` re-ticks `ComputePathToPose` at ~1 Hz (Week 17, Lecture 2), so the planner reruns `NavfnPlanner` (Dijkstra/A*) on the current costmap once a second. Modern grid A* on a building-sized costmap is fast enough (single-digit to low-tens of milliseconds) that full replanning at 1 Hz is simpler, more robust, and fast enough — so the incremental complexity of D* Lite isn't worth it for most ground robots. D* Lite shines when the map is *huge* or the replan budget is *tight* (planetary rovers, very large warehouses). Knowing *why* Nav2 chose periodic full-replan over D* Lite is the senior-level insight: incremental algorithms trade implementation complexity for replan speed, and you only pay that complexity when the map size forces you to.

---

## 7. Path reconstruction and a note on grid resolution

Both algorithms above build a `parent` map: each node remembers who discovered it on the best path. Reconstruction walks parents from the goal back to the start:

```python
def reconstruct(parent, goal):
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path
```

The path is a list of grid cells. To hand it to a controller you convert cells to world coordinates using the costmap's `resolution` and `origin` (Week 17). A grid path is **jagged** — it staircases on the diagonals — which is why Nav2 runs a `smoother_server` after the planner. The smoothing is a separate step; the planner's job is just to find the cheapest cell sequence.

Why separate the planner from the smoother at all? Because they optimize different things. The planner optimizes *cost over the grid graph* (shortest weighted cell path), which is a clean, optimal, fast computation. The smoother optimizes *drivability* (curvature, clearance, continuity) over the *continuous* path, which is a different objective the grid can't express. Bolting smoothing into the search would make the search slower and the objective murkier. Keeping them separate — plan optimally on the grid, then smooth for the controller — is the same separation-of-concerns instinct as the planner/controller split in Week 17. Each stage does one thing well.

> **Resolution is a trade-off you choose.** A 5 cm grid on a 50 m × 50 m building is a 1000 × 1000 = 1,000,000-cell graph. Halve the resolution to 10 cm and you quarter the node count and roughly quarter the planning time — at the cost of squeezing through tight gaps. This is why Hybrid-A* (next lecture) searches a *continuous* state with a discrete control set instead of a fine grid: for car-like vehicles, the grid resolution needed to capture the turning constraint would be ruinously fine.

---

## 7.5 Complexity, early termination, and where the time actually goes

It's worth being precise about the cost, because "runtime is a safety property" (next lecture) means you need to reason about it, not just measure it.

- **Dijkstra and A* are both `O((V + E) log V)`** with a binary heap. On an 8-connected grid, `E ≈ 8V`, so it's `O(V log V)` in the grid size `V`. The `log V` is the heap push/pop. In practice, the constant factors live in two places: **neighbor generation** (the eight bounds-checks and the corner-cut test per node) and **heap operations** (push per discovered neighbor). When you profile your A* (homework), one of those two is always the hot line.
- **Early termination** is the single most important practical optimization, and it's already in the code above: A* returns *the moment it pops the goal* from the open set, not when it finishes exploring. Because A* pops in `f`-order and the goal's `f` equals its true cost (admissible `h` makes `h(goal)=0`), the first time the goal is popped it has its optimal cost — so it's safe to stop. Dijkstra has the same property. Forgetting to terminate early (running until the open set empties) turns a single-goal query into an all-pairs computation and is a 10–100× slowdown on a large map.
- **A* expands `O(b^d)` nodes in the worst case** (branching factor `b`, solution depth `d`), but with a good heuristic it expands far fewer — the *effective* branching factor shrinks toward 1 as the heuristic tightens. A perfect heuristic (`h = h*`) expands *only the nodes on the optimal path*. This is why heuristic quality is the whole game: it doesn't change correctness (any admissible `h` is optimal), it changes *how much of the map you touch*.

A concrete number to carry: modern grid A* on a building-sized costmap (a few hundred thousand free cells) plans in **single-digit to low-tens of milliseconds** on a laptop, a bit more on a Jetson. That's the budget you're working inside, and it's *why* Nav2 replans from scratch at 1 Hz instead of reaching for D* Lite (§6.1) — the full replan is cheap enough.

> **A debugging habit:** when a planner is "too slow," profile *before* you optimize. `python3 -m cProfile -s cumtime your_planner.py` will tell you in thirty seconds whether the time is in neighbor generation, the heap, or (a beginner classic) an accidental `O(n)` membership test on a list instead of a set for the closed set. The number-one self-inflicted A* slowdown is using a Python `list` for `closed` (`node in closed` is `O(n)`) instead of a `set` (`O(1)`); on a million-cell map that single mistake is a 1000× regression. Measure, then fix the hot line — don't guess.

---

## 8. Recap

You should now be able to:

- Treat an occupancy grid as an 8-connected graph with `√2` diagonal costs and corner-cut prevention.
- Implement Dijkstra (priority queue on `g`) and A* (priority queue on `f = g + h`) from scratch, and state that Dijkstra is A* with `h = 0`.
- Choose the tightest admissible heuristic for the grid's connectivity (octile for 8-connected) and explain why Manhattan-on-8-connected is inadmissible.
- State the admissibility condition, sketch the proof that admissible A* is optimal, and verify it empirically by matching Dijkstra's path length.
- Use weighted A* (`f = g + ε·h`) to trade bounded sub-optimality for speed, and frame planning latency as a safety property.
- Explain D* Lite's reuse-of-prior-search idea and why Nav2 chose periodic full-replan over it.

Next: state spaces where a grid isn't enough — lattices and Hybrid-A* for vehicles that can't turn in place, and RRT* for high-dimensional continuous spaces. Continue to [Lecture 2 — Lattices, Hybrid-A*, and Sampling-Based Planning](./02-lattices-hybrid-a-star-and-sampling-based-planning.md).

---

## References

- *Planning Algorithms* (LaValle), Ch. 2 — discrete search: <http://lavalle.pl/planning/>
- *Introduction to A\** (Red Blob Games): <https://www.redblobgames.com/pathfinding/a-star/introduction.html>
- Hart, Nilsson, Raphael (1968) — the A* paper: <https://ieeexplore.ieee.org/document/4082128>
- Koenig & Likhachev (2002) — D* Lite: <http://idm-lab.org/bib/abstracts/papers/aaai02b.pdf>
- *Nav2 planner server configuration*: <https://docs.nav2.org/configuration/packages/configuring-planner-server.html>
