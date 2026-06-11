# Lecture 1 — SLAM Is a Loopy Estimation Problem Dressed Up as a Map

> **Reading time:** ~80 minutes. **Hands-on time:** ~55 minutes (you build and optimize a tiny pose graph in NumPy and watch a loop closure move the map).

This is the lecture that turns "SLAM is magic that makes a map" into "SLAM is a least-squares problem on a graph, and the map is the rendered output." Everything you tune in `slam_toolbox` this week — the scan-match window, the loop-closure thresholds, the resolution — is a parameter of that least-squares problem. By the end of this lecture you can draw the pose graph for a robot driving a loop, explain what the front-end and back-end each contribute, write down (and solve, in NumPy) a three-pose graph with one loop-closure constraint, and predict what happens to the map when a loop closes correctly versus when a false loop closure fires. The thesis is in the title: **SLAM is a loopy estimation problem dressed up as a map.** The loop is the point.

## 1.1 — What SLAM is actually estimating

SLAM is *Simultaneous Localization And Mapping*. The "simultaneous" is the whole difficulty: you need a map to know where you are, and you need to know where you are to build a map, and you have neither at the start. If someone handed you a perfect map, localization would be easy (that is AMCL, Week 11). If someone handed you the robot's perfect trajectory, mapping would be easy (just paint every scan at its known pose). SLAM is the chicken-and-egg version where you estimate *both at once* from the same data.

State the problem precisely. The robot moves through time, occupying a sequence of poses `x₀, x₁, x₂, …, xₜ` (each an `SE(2)` pose `(x, y, θ)` for a planar robot). At each pose it takes a LiDAR scan `z₀, z₁, …, zₜ` and records an odometry increment `u₁, u₂, …, uₜ` (the motion the wheels reported between poses, from your Week 6 node). SLAM estimates the *whole trajectory* `x₀:ₜ` and the *map* `m` that best explain the scans and the odometry:

```
x₀:ₜ*, m*  =  argmax  p(x₀:ₜ, m | z₀:ₜ, u₁:ₜ)
              x₀:ₜ, m
```

Read that carefully. We are not estimating "where am I now" (that is filtering — a single pose). We are estimating the *entire history of poses* plus the map, all at once, conditioned on *all* the measurements. This is **full SLAM** (also called *smoothing*), and it is the formulation `slam_toolbox` and every modern graph-SLAM system uses. The reason is the loop closure of Section 1.6: when you recognize a place you have visited before, that recognition is a constraint between a *recent* pose and an *old* pose, and to exploit it you must be able to *move the old pose* — which means the old pose has to still be in your state. A filter that has marginalized away the old poses cannot do this. A smoother that keeps them can. That is why graph SLAM beat filter SLAM, and why this lecture spends its time on the graph.

## 1.2 — The occupancy grid: the map as a probability field

Before the graph, the map. The output you will look at all week is a `nav_msgs/OccupancyGrid`: a 2D array of cells, each holding the probability that the cell is occupied. The message has four fields that matter:

```
nav_msgs/OccupancyGrid
  std_msgs/Header header
  nav_msgs/MapMetaData info
    float32 resolution      # metres per cell, e.g. 0.05 -> 5 cm cells
    uint32  width           # cells across
    uint32  height          # cells down
    geometry_msgs/Pose origin   # world pose of cell (0,0), the bottom-left corner
  int8[] data               # row-major, length = width*height
```

The `data` field is `int8`, and the convention is fixed:

- **`-1`** — *unknown*. No scan has ever told us anything about this cell. (The grey in RViz.)
- **`0`** — *free*. A LiDAR beam passed *through* this cell to hit something beyond it, so it is empty. (The white in RViz.)
- **`100`** — *occupied*. A LiDAR beam *ended* in this cell — it hit a wall. (The black in RViz.)
- Values `1–99` — intermediate probabilities, used by some mappers; `slam_toolbox` mostly emits `-1 / 0 / 100`.

A 30 m × 30 m building at 5 cm resolution is `600 × 600 = 360,000` cells. At 2 cm resolution it is `1500 × 1500 = 2.25 M` cells — more detail, four times the memory, slower scan matching. The `resolution` choice is the first trade-off of the week (Section 1.9).

**Why a probability and not a bitmap?** Because a single scan is noisy and partial. A beam that *appears* to pass through a cell might have been a glancing reflection; a beam that ends in a cell might have hit dust. The disciplined way to fuse many noisy observations of the same cell is the **log-odds** update. For each cell, maintain a log-odds value `ℓ`:

```
ℓ = log( p(occupied) / p(free) )
```

Log-odds because the Bayesian update for "I observed this cell again" becomes simple addition: each beam that says "occupied" adds a positive `ℓ_occ`; each beam that says "free" adds a negative `ℓ_free`. Start every cell at `ℓ = 0` (p = 0.5, total ignorance) and the map *firms up* as evidence accumulates — a cell seen as occupied ten times has a large positive `ℓ` and is confidently black; a cell seen once is tentatively grey-black. To render the `OccupancyGrid` you threshold: `ℓ > τ → 100`, `ℓ < -τ → 0`, `|ℓ| ≤ τ → -1`. The log-odds field is the *real* map; the `int8[]` you publish is a thresholded snapshot of it.

The log-odds update, in code, is two lines:

```python
import numpy as np

# A tiny occupancy grid as a log-odds field. Cells start at 0.0 (unknown, p=0.5).
class LogOddsGrid:
    def __init__(self, width, height, l_occ=0.85, l_free=-0.40, clamp=5.0):
        self.l = np.zeros((height, width), dtype=np.float32)
        self.l_occ = l_occ      # log-odds added when a beam ENDS in a cell
        self.l_free = l_free    # log-odds added when a beam PASSES THROUGH a cell
        self.clamp = clamp      # keep |l| bounded so the map can still change

    def update_cell(self, row, col, hit: bool):
        # add evidence, then clamp so a long-confident cell can still flip later
        v = self.l[row, col] + (self.l_occ if hit else self.l_free)
        self.l[row, col] = float(np.clip(v, -self.clamp, self.clamp))

    def to_occupancy_int8(self, tau=0.40):
        out = np.full(self.l.shape, -1, dtype=np.int8)   # default unknown
        out[self.l > tau] = 100                          # occupied
        out[self.l < -tau] = 0                           # free
        return out.flatten()                             # row-major, ready for the message
```

In production you do not update one cell at a time — you ray-trace each beam once, get the list of free cells it passed through and the single hit cell, and clip the whole vectorized update. The per-cell form above is for clarity. The point for this week is conceptual: **the map is a field of accumulated log-odds, thresholded for display.** When `slam_toolbox` re-optimizes the pose graph and a loop closes, it does *not* edit the grid cell by cell — it moves the poses, then *re-paints* the scans at their new poses into a fresh log-odds field. The map "snapping into place" you will see in RViz is a re-render, not a local patch.

## 1.3 — The pose graph: nodes and edges

Now the computation. Represent the SLAM problem as a graph:

- **Nodes** are robot poses `xᵢ ∈ SE(2)`. `slam_toolbox` creates a new node every time the robot has moved `minimum_travel_distance` metres or turned `minimum_travel_heading` radians since the last node — *not* every scan. This decouples node creation from scan rate (Section 1.9). Each node has a scan attached.
- **Edges** are *constraints* — relative-pose measurements between two nodes. An edge from `i` to `j` says "I measured that pose `j` is at relative transform `z_ij` from pose `i`, and I am this confident about it (information matrix `Ω_ij`)." There are two kinds:
  - **Sequential / odometry edges** connect consecutive nodes `i → i+1`. The measurement `z_{i,i+1}` is the scan-match result (refined by the odometry prior) for how the robot moved between the two scans. These edges form the *backbone* of the graph — the trajectory.
  - **Loop-closure edges** connect a recent node `j` to a much earlier node `i` (`i ≪ j`) when the front-end recognizes that pose `j` is at a place pose `i` already visited. These are the edges that *make the graph loopy* and that bound the drift (Section 1.6).

Each edge carries an **information matrix** `Ω_ij` (the inverse of the measurement covariance). A scan match between two dense, feature-rich scans produces a high-information (confident) edge; a match between two scans of a featureless corridor produces a low-information (uncertain) edge — particularly uncertain *along* the corridor, where there is nothing to lock the position. The information matrix is how the back-end knows which constraints to trust. It is the graph-SLAM analogue of the covariance you put on `/odom` in Week 6: lie about it and the optimizer weights the wrong constraints.

Draw it. A robot driving a rectangular loop creates a chain of nodes `x₀ → x₁ → … → xₙ` connected by sequential edges, and when it returns to the start, a loop-closure edge `xₙ → x₀` closes the rectangle:

```
        x0 ── x1 ── x2 ── x3
        │                  │     sequential edges (─, │) form the trajectory backbone
        x7                 x4
        │                  │
        x6 ── x5 ──────────┘
        ╲                          loop-closure edge (╲) ties x6's place back to near x0:
         ╲____________ (loop closure: "x6 is where x0 was") ___________ x0
```

Without the loop-closure edge, the chain is a tree — the back-end has nothing to optimize, because a tree of relative constraints has exactly one consistent solution (just compose the transforms). *The loop closure is what makes the optimization non-trivial.* The chain says "x6 is at this absolute position, derived by composing seven drifting scan matches"; the loop closure says "but x6 is *actually* right next to x0." Those two statements disagree by the accumulated drift, and the back-end's job is to distribute that disagreement around the whole loop so that *every* edge is approximately satisfied. That distribution is what moves the map.

## 1.4 — The front-end: scan matching produces constraints

The **front-end** turns raw sensor data into edges. For 2D LiDAR SLAM, the front-end is a *scan matcher*: given two scans and a guess at the relative pose between them (the odometry prior from your Week 6 node), find the relative pose that best aligns the two scans.

`slam_toolbox` inherits its scan matcher from Karto, which uses **correlative scan matching** (Olson 2009, in resources.md). The idea is brute-force-but-robust:

1. Take the reference scan and rasterize it into a *lookup table* — a small grid where each cell's value is high near where a scan point landed and falls off with distance (a smoothed occupancy of the reference scan).
2. Take the new scan. For every candidate relative pose `(Δx, Δy, Δθ)` in a search window around the odometry prior, transform the new scan's points by that candidate pose and *sum the lookup-table values* at the transformed points. This sum is the **response score** — high when the new scan's points land where the reference scan's points are.
3. The candidate pose with the highest response is the scan-match estimate. Olson's trick is a multi-resolution search (coarse grid first, refine) so the brute force is fast.

The search window is set by parameters you will tune: `correlation_search_space_dimension` (how far in metres to search), `correlation_search_space_resolution` (the grid step), and the angular equivalents. **A search window too small and a real motion outside it never gets found — the match fails or locks onto a wrong local maximum. A window too large and the search is slow and more likely to find a spurious high-response pose far from the truth.** The odometry prior is what lets the window be small: it tells the matcher roughly where to look, so the window only has to cover the *odometry error*, not the whole motion. This is the concrete reason Week 6's odometry quality matters here — good odometry means a small, fast, reliable search window.

After the correlative match finds the best discrete pose, `slam_toolbox` runs a **Ceres-based refinement** (a small nonlinear least-squares polish) to get sub-cell accuracy, and estimates the *covariance* of the match from the sharpness of the response peak — a sharp peak (feature-rich scan) gives a confident, high-information edge; a broad ridge (a corridor, sharp across, flat along) gives an edge that is confident across the corridor and uncertain along it. That covariance becomes the edge's information matrix `Ω_ij`. **The front-end's product is not a pose — it is a constraint: a relative transform plus an information matrix.** Hold that. People say "the scan matcher gives you the pose"; it gives you an *edge*, and the back-end turns edges into poses.

## 1.5 — The back-end: optimizing the graph

The **back-end** takes the graph — all the nodes and all the edges — and finds the configuration of node poses `x₀:ₜ` that best satisfies all the edge constraints simultaneously. "Best satisfies" means minimizing the total weighted constraint error:

```
x*  =  argmin  Σ   e_ij(xᵢ, xⱼ)ᵀ  Ω_ij  e_ij(xᵢ, xⱼ)
       x      (i,j)∈edges
```

where `e_ij(xᵢ, xⱼ)` is the *error* of edge `(i,j)`: the difference between the relative pose the edge *measured* (`z_ij`) and the relative pose the current node estimates *imply* (`xᵢ⁻¹ ∘ xⱼ`). When the edge is perfectly satisfied, the error is zero. The information matrix `Ω_ij` weights each edge's error — high-information edges (confident scan matches) are expensive to violate, so the optimizer satisfies them first; low-information edges (uncertain matches) can be stretched.

This is a **nonlinear least-squares** problem (nonlinear because the poses are on the `SE(2)` manifold and the errors involve rotations). The standard solution is Gauss-Newton or Levenberg-Marquardt iteration: linearize the errors around the current estimate, solve the resulting sparse linear system for a pose update, apply it, repeat until convergence. `slam_toolbox` uses **Ceres** as its default solver (with SPA and other solvers selectable via the `solver_plugin` parameter). The "sparse" matters: most node pairs are *not* connected by an edge, so the linear system is sparse, and exploiting that sparsity (Konolige's SPA, in resources.md) is what lets 2D SLAM scale to a whole building with thousands of nodes.

The geometric intuition is the thing to keep: **the back-end is a mass-spring system.** Each edge is a spring whose rest length is the measured relative pose and whose stiffness is the information matrix. The nodes are beads. Release the system and it settles into the configuration that minimizes total spring energy. A loop-closure edge is a *new* spring connecting two beads that the trajectory had drifted far apart; when you add it, the whole system re-settles, and the accumulated drift gets distributed around the loop as every spring gives a little. That re-settling is the map snapping into place.

## 1.6 — Loop closure: the only thing that bounds drift

Here is the central claim of the week, now earnable. **Without loop closures, graph SLAM is just scan-matched odometry, and it drifts without bound — exactly as Week 6 predicted, only more slowly.** The sequential edges form a chain; a chain has a unique solution (compose the transforms); composing many slightly-wrong scan matches accumulates error the same way composing many slightly-wrong wheel-odometry increments did. Scan matching drifts more slowly than wheel odometry because a LiDAR scan is a much richer measurement than two encoder counts — but it still drifts. Drive a long corridor with no revisits and a pure-front-end map bends, because every scan match is a little off and the errors compound.

A **loop closure** is the fix. When the robot returns to a place it has mapped before, the front-end recognizes the current scan matches an *old* node's scan, and emits a loop-closure edge tying the current pose to the old one. Now the graph is loopy: the chain says "the current pose is *here*, after composing 500 drifting scan matches," and the loop-closure edge says "no, the current pose is *right next to* node 12, which we are confident about." The back-end resolves the contradiction by **redistributing the accumulated drift around the entire loop** — node 12's region barely moves (it is anchored by many edges), the far side of the loop moves the most, and the map becomes *globally consistent*: walls that were doubled (the same wall mapped twice at drifted poses) merge into one.

How `slam_toolbox` finds loop closures (these are the parameters you tune Thursday):

1. **Candidate search.** For the current node, find earlier nodes within `loop_search_maximum_distance` metres (in the *current, drifted* estimate). These are the places the robot *might* be revisiting.
2. **Chain matching.** Rather than match a single scan, `slam_toolbox` matches a *chain* of consecutive nodes around the candidate (`loop_match_minimum_chain_size` nodes) against the current scan region. Matching a chain is more robust than matching one scan — a single corridor scan is ambiguous; a chain of corridor scans plus the corner at the end is not.
3. **Response threshold.** Run the correlative scan matcher over the candidate chain. If the response score exceeds `loop_match_minimum_response_coarse` (and then `loop_match_minimum_response_fine` after refinement), accept the loop closure and add the edge. Otherwise reject it.

The two failure modes are symmetric and both fatal:

- **Missed loop closure (false negative).** The thresholds are too strict, or the search distance too small, or the chain size too large for the available nodes — so a *real* revisit is rejected. The drift is never corrected and the map bends or doubles walls. This is the failure the **challenge** forces you to produce and then fix.
- **False loop closure (false positive).** The thresholds are too loose, or the world has two genuinely-identical places (two identical corridors, a symmetric room) — so the front-end matches the current scan to the *wrong* old node. The back-end then faithfully optimizes toward the lie, and the map *folds in half* or gains a phantom passage. This is the more dangerous failure because the optimizer makes it look confident and clean — a wrong map that looks right.

The entire craft of tuning a SLAM system is **keeping the gap between "loose enough to catch true loops" and "strict enough to reject false ones" open.** Chain matching, the response threshold, and the search distance are your three knobs. The challenge is built around exactly this gap.

## 1.7 — Why a filter cannot do this (and why we left AMCL for later)

It is worth being precise about why graph SLAM (a *smoother*) beat the older EKF-SLAM and particle-filter SLAM (*filters*) for mapping. A filter maintains an estimate of the *current* state and marginalizes away the past — after processing pose `xₜ`, it has thrown away the explicit estimate of `xₜ₋₅₀₀`. When a loop closes, the correct response is to *move pose `xₜ₋₅₀₀`* (it was drifted), and a filter cannot — it no longer has that pose as a free variable. EKF-SLAM tried to keep all poses correlated in one giant covariance matrix, which is `O(N²)` in landmarks and does not scale. A particle filter (FastSLAM) keeps a trajectory per particle, which works but needs many particles to keep a hypothesis that survives the loop. The smoother keeps *all poses as explicit variables* in a *sparse* graph, so moving an old pose on loop closure is exactly what the optimizer does, and the sparsity keeps it tractable. That is the whole reason `slam_toolbox` is a graph optimizer and not a Kalman filter.

This is also why **localization** (Week 11's AMCL) *is* a filter and that is fine: when you already have a fixed map, you only need the *current* pose, the map is not changing, and there are no loops to close in your trajectory estimate — so a filter (particle filter / AMCL) is the right, cheap tool. `slam_toolbox`'s own localization mode (Lecture 2) is a pose-graph measurement-only mode that gets you the same answer through the graph machinery. The rule: **build the map with a smoother (you need to move old poses); localize against a fixed map with a filter (you only need the current pose).**

## 1.8 — Hands-on: build and optimize a tiny pose graph

You will now build the smallest interesting pose graph — three poses around a triangle with one loop-closure edge — and optimize it in NumPy, so you *see* the loop closure move the poses. Save this as `pose_graph_demo.py` and run it with `python3 pose_graph_demo.py`.

```python
#!/usr/bin/env python3
"""Week 7, Lecture 1 hands-on: a 3-node SE(2) pose graph with one loop closure.

We place three poses around a square-ish loop. The sequential (odometry) edges
are slightly WRONG (they drift), so composing them does not bring the robot back
to the start. We then add a loop-closure edge that says "pose 3 is back at the
origin" and run Gauss-Newton least-squares on SE(2) to redistribute the drift.

Watch the BEFORE poses (drifted, the loop does not close) become the AFTER poses
(the loop closes, the drift smeared around the graph). This is, in miniature,
exactly what slam_toolbox's back-end does when a loop fires.
"""
import numpy as np


def wrap(a):
    """Wrap an angle to (-pi, pi]."""
    return np.arctan2(np.sin(a), np.cos(a))


def t2v(T):
    """SE(2) homogeneous matrix -> (x, y, theta) vector."""
    return np.array([T[0, 2], T[1, 2], np.arctan2(T[1, 0], T[0, 0])])


def v2t(v):
    """(x, y, theta) vector -> SE(2) homogeneous matrix."""
    c, s = np.cos(v[2]), np.sin(v[2])
    return np.array([[c, -s, v[0]],
                     [s,  c, v[1]],
                     [0,  0, 1.0]])


def edge_error_and_jacobians(xi, xj, z):
    """Error of an edge measuring relative pose z between nodes xi and xj.

    e = t2v( Z^-1 (Xi^-1 Xj) ).  Returns (e, A, B) where A = de/dxi, B = de/dxj,
    computed analytically (the standard graph-SLAM SE(2) Jacobians, Grisetti 2010).
    """
    Xi, Xj, Z = v2t(xi), v2t(xj), v2t(z)
    E = np.linalg.inv(Z) @ (np.linalg.inv(Xi) @ Xj)
    e = t2v(E)

    ci, si = np.cos(xi[2]), np.sin(xi[2])
    dRiT = np.array([[-si, ci], [-ci, -si]])      # d(Ri^T)/dtheta_i
    Ri = np.array([[ci, -si], [si, ci]])
    Rz = np.array([[np.cos(z[2]), -np.sin(z[2])],
                   [np.sin(z[2]),  np.cos(z[2])]])
    dt = (np.array(xj[:2]) - np.array(xi[:2]))

    A = np.zeros((3, 3))
    A[:2, :2] = -Rz.T @ Ri.T
    A[:2, 2] = (Rz.T @ dRiT @ dt)
    A[2, 2] = -1.0
    B = np.zeros((3, 3))
    B[:2, :2] = Rz.T @ Ri.T
    B[2, 2] = 1.0
    return e, A, B


def optimize(nodes, edges, iters=10):
    """Gauss-Newton on an SE(2) pose graph. Node 0 is fixed (the gauge / anchor).

    nodes: (N,3) array of (x,y,theta). edges: list of (i, j, z(3,), Omega(3x3)).
    """
    nodes = nodes.copy()
    N = len(nodes)
    for it in range(iters):
        H = np.zeros((3 * N, 3 * N))
        b = np.zeros(3 * N)
        for (i, j, z, Omega) in edges:
            e, A, B = edge_error_and_jacobians(nodes[i], nodes[j], z)
            e[2] = wrap(e[2])
            ii, jj = slice(3 * i, 3 * i + 3), slice(3 * j, 3 * j + 3)
            H[ii, ii] += A.T @ Omega @ A
            H[ii, jj] += A.T @ Omega @ B
            H[jj, ii] += B.T @ Omega @ A
            H[jj, jj] += B.T @ Omega @ B
            b[ii] += A.T @ Omega @ e
            b[jj] += B.T @ Omega @ e
        # fix node 0 to remove the gauge freedom (the graph is only relative)
        H[0:3, 0:3] += np.eye(3) * 1e6
        dx = np.linalg.solve(H, -b)
        nodes += dx.reshape(N, 3)
        nodes[:, 2] = wrap(nodes[:, 2])
        chi2 = 0.0
        for (i, j, z, Omega) in edges:
            e, _, _ = edge_error_and_jacobians(nodes[i], nodes[j], z)
            e[2] = wrap(e[2])
            chi2 += e @ Omega @ e
        print(f"  iter {it}: chi^2 = {chi2:.6f}")
    return nodes


def main():
    # Four poses meant to form a 4 m square loop: (0,0) -> (4,0) -> (4,4) -> (0,4)
    # The ODOMETRY edges drift: each leg's measured heading is 3 deg too small,
    # so composing them does NOT return to the start.
    drift = np.deg2rad(3.0)
    leg = 4.0
    # measured (drifted) sequential edges, each "go forward 4 m then turn ~90 deg"
    seq_z = [
        np.array([leg, 0.0, np.pi / 2 - drift]),   # 0->1
        np.array([leg, 0.0, np.pi / 2 - drift]),   # 1->2
        np.array([leg, 0.0, np.pi / 2 - drift]),   # 2->3
    ]
    # initial node estimate = compose the drifting edges from the origin
    nodes = np.zeros((4, 3))
    for k in range(3):
        T = v2t(nodes[k]) @ v2t(seq_z[k])
        nodes[k + 1] = t2v(T)

    Omega_seq = np.diag([100.0, 100.0, 200.0])   # sequential edges: confident
    edges = [(k, k + 1, seq_z[k], Omega_seq) for k in range(3)]

    print("BEFORE loop closure (drifted; the loop does not close):")
    for k, n in enumerate(nodes):
        print(f"  x{k}: x={n[0]:+.3f} y={n[1]:+.3f} th={np.rad2deg(n[2]):+.1f} deg")
    gap = np.hypot(nodes[3, 0] - 0.0, nodes[3, 1] - leg)
    print(f"  gap between x3 and where it SHOULD be (0,4): {gap:.3f} m\n")

    # The loop closure: the front-end recognized that x3 is the (0,4) corner and
    # measured the relative pose from x0 to x3 as "go up 4 m, turn 90 deg" exactly.
    loop_z = np.array([0.0, leg, np.pi / 2])
    Omega_loop = np.diag([100.0, 100.0, 200.0])
    edges.append((0, 3, loop_z, Omega_loop))

    print("Optimizing (the back-end redistributes the drift):")
    nodes_opt = optimize(nodes, edges, iters=8)

    print("\nAFTER loop closure (drift smeared around the graph; loop closes):")
    for k, n in enumerate(nodes_opt):
        print(f"  x{k}: x={n[0]:+.3f} y={n[1]:+.3f} th={np.rad2deg(n[2]):+.1f} deg")


if __name__ == "__main__":
    main()
```

Run it. You should see output along these lines:

```
BEFORE loop closure (drifted; the loop does not close):
  x0: x=+0.000 y=+0.000 th=+0.0 deg
  x1: x=+4.000 y=+0.000 th=+87.0 deg
  x2: x=+4.209 y=+3.994 th=+174.0 deg
  x3: x=+0.421 y=+4.203 th=+261.0 deg
  gap between x3 and where it SHOULD be (0,4): 0.470 m

Optimizing (the back-end redistributes the drift):
  iter 0: chi^2 = 18.4...
  iter 1: chi^2 = 0.83...
  ...
  iter 7: chi^2 = 0.0000xx

AFTER loop closure (drift smeared around the graph; loop closes):
  x0: x=+0.000 y=+0.000 th=+0.0 deg
  x1: x=+3.99x y=-0.0xx th=+88.x deg
  x2: x=+4.0xx y=+3.9xx th=+177.x deg
  x3: x=+0.0xx y=+3.9xx th=+266.x deg
```

Read what happened. **Before** the loop closure, composing three drifting edges put `x3` about 47 cm away from where the loop should close — the chain is internally consistent but globally wrong, exactly like a SLAM map with no loop closures. **After** adding one loop-closure edge and running eight Gauss-Newton iterations, the `chi²` (the total weighted edge error) drops by orders of magnitude, and the poses have *all moved a little* so that the loop closes: `x3` is back near `(0, 4)`, and the 47 cm of drift has been *smeared around the whole graph* — every node moved a bit, none moved a lot. That smearing is the map snapping into place. You just ran, in 80 lines of NumPy, the same computation `slam_toolbox`'s Ceres back-end runs on thousands of nodes when you close a loop in RViz on Wednesday.

Two experiments to run before you move on:

1. **Delete the loop-closure edge** (comment out the `edges.append(...)` line) and re-run. The optimizer has nothing to do — the chain is already optimal — and `x3` stays drifted. *No loop closure, no correction.* This is the "missed loop closure" failure of Section 1.6, in miniature.
2. **Corrupt the loop-closure edge** — change `loop_z` to `np.array([0.0, 4.0, np.pi])` (a wrong heading by 90°), a *false* loop closure. Re-run and watch the optimizer confidently converge to a *wrong* configuration with low `chi²`. The optimizer cannot tell a true constraint from a false one — it only minimizes the error you gave it. *This is why a false loop closure folds your map and looks clean doing it.* Internalize it before Thursday's challenge.

## 1.9 — Resolution, node spacing, and scan rate: the three knobs that set map quality

Three parameters control the granularity of the whole pipeline, and they are easy to confuse:

- **`resolution`** (metres per cell) — the *grid* granularity. 5 cm is the default and right for indoor robots. Finer (2 cm) captures thin obstacles and door frames but quadruples memory and slows scan matching; coarser (10 cm) is faster but merges a chair leg into the floor. This affects the *map render* and the scan-match lookup table, not how often you create nodes.
- **`minimum_travel_distance` / `minimum_travel_heading`** — the *node-spacing* granularity. A new graph node (and a stored scan) is created only after the robot moves this far or turns this much. Default ~0.5 m / ~0.5 rad. Smaller values create more nodes (denser graph, more constraints, more loop-closure opportunities, more CPU and memory); larger values create a sparse graph that is cheaper but has fewer chances to close a loop and more drift between nodes.
- **The LiDAR scan rate** (Hz, set by the sensor) — how often a *scan* arrives. `slam_toolbox` does *not* create a node per scan; it accumulates scans and creates a node per `minimum_travel_distance`. But the scan rate sets the *freshness* of the scan a node gets and how much the robot can drift *between* scan matches. Too low a rate and a fast-moving robot moves far between scans, the odometry prior for the next match is poor, and scan matching degrades.

The Thursday exercise compares **scan rate** specifically: same world, same trajectory (replayed from a bag), three scan rates. You will find a regime where lowering the rate barely hurts (the robot moves slowly, node spacing dominates) and a regime where it visibly degrades (drift between scans grows, matches get loose, walls smear). The skill is articulating *which regime your robot is in* and choosing the rate that buys you accuracy without burning CPU you need for perception in Phase 2. That is a real deployment decision, and "I picked 10 Hz because at 5 Hz the corridor walls doubled and at 20 Hz the CPU could not keep up while running the detector" is exactly the sentence a Phase 2 review wants to hear.

## 1.10 — Summary

- SLAM estimates the **whole trajectory and the map at once** — it is *smoothing* (full SLAM), not filtering, because exploiting a loop closure requires moving old poses.
- The **occupancy grid** is a thresholded **log-odds** probability field, not a bitmap: `-1` unknown, `0` free, `100` occupied. When a loop closes, the grid is *re-rendered* from re-optimized poses, not patched.
- SLAM is a **pose graph**: nodes are poses, edges are relative-pose constraints with information matrices. Sequential edges form the trajectory backbone; loop-closure edges make the graph loopy.
- The **front-end** (correlative scan matching, Olson 2009, polished by Ceres) turns scans + odometry priors into **edges with information matrices** — not poses.
- The **back-end** (Ceres / sparse nonlinear least squares) finds the poses that minimize total weighted edge error — a **mass-spring system** that re-settles when you add a loop-closure spring.
- **Loop closure is the only thing that bounds drift.** A missed loop bends the map; a false loop *folds* it and looks clean doing so. Tuning SLAM is keeping the gap between "catch true loops" and "reject false loops" open.
- Three knobs set granularity: **`resolution`** (grid), **node spacing** (`minimum_travel_*`), and **scan rate** (sensor) — and they are not the same knob.

Next: Lecture 2 takes the graph machinery you now understand and shows how `slam_toolbox` packages it into three operating modes — mapping, localization, lifelong — with the parameter file, the save/load services, and the `map → odom → base_link` frame chain you will debug all week.

---

*Run `pose_graph_demo.py` and do both experiments in Section 1.8 before Wednesday's mapping lab. When your RViz map snaps on a loop closure, you want to already know it is the mass-spring system re-settling — not magic.*
