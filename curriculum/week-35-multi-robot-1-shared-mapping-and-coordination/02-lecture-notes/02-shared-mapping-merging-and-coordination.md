# Lecture 2 — Shared Mapping, Merging, and Latency-Bounded Coordination

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can merge two occupancy grids in a common frame with correct cell-fusion rules, publish and reason about the inter-robot transform, keep coordination off the critical path with a periodic eventually-consistent exchange, and place the distributed-SLAM landscape of 2026 around what you built.

Lecture 1 gave you two robots with two clean, prefixed TF trees tied into a shared `world` frame. This lecture is where the maps actually become one. Three parts: (1) the occupancy-grid merge, done correctly; (2) the inter-robot transform and what goes wrong when it's stale; (3) coordination as a distributed-systems problem, plus a survey of where real distributed SLAM goes.

---

## Part 1 — Merging two occupancy grids

### 1.1 The `OccupancyGrid` you are merging

`nav_msgs/OccupancyGrid` is deceptively simple, and every field matters for the merge:

```
# nav_msgs/OccupancyGrid
std_msgs/Header header          # frame_id = which frame the grid origin lives in
nav_msgs/MapMetaData info
  float32 resolution            # meters per cell (e.g. 0.05)
  uint32 width                  # cells across (x)
  uint32 height                 # cells up (y)
  geometry_msgs/Pose origin     # pose of cell (0,0) in header.frame_id
int8[] data                     # row-major, length width*height, values 0/100/-1
```

The `data` array is **row-major**: cell `(x, y)` is at index `y * width + x`. Each value is:

- `0` — free (the robot has seen this cell and it's empty),
- `100` — occupied (a wall, an obstacle),
- `-1` — unknown (never observed).

(`slam_toolbox` emits intermediate values too — a probability scaled 0–100 — but for the merge we treat anything above a threshold as occupied and anything below as free; -1 stays unknown.)

The `origin` is the pose of cell `(0,0)` expressed in `header.frame_id`. This is the field people forget, and forgetting it is why merged maps come out shifted. A grid is not just an array — it's an array *plus where its corner sits in the world*. Two grids with the same data but different origins describe walls in different places.

### 1.2 The merge problem, stated

You have grid A in frame `robotA/map` and grid B in frame `robotB/map`. You want one grid in frame `world` that contains both robots' knowledge. The steps:

1. **Transform each grid's cells into `world`.** For every cell in grid A, compute its world coordinate using grid A's `origin` and `resolution`, then apply `world -> robotA/map`. Same for grid B with `world -> robotB/map`.
2. **Compute the merged grid's extent.** The merged grid must cover the bounding box of both robots' explored world coordinates. Find min/max x and y across both grids' corners in `world`; that's the merged grid's origin and size.
3. **Fuse overlapping cells.** Where both grids observed the same world cell, combine their values with the fusion rule (§1.4).

### 1.3 Cell-to-world and world-to-cell

The two coordinate conversions you'll write a dozen times this week. A cell `(cx, cy)` in a grid maps to a *local* metric point in the grid's frame:

```python
def cell_to_local(cx: int, cy: int, info) -> tuple[float, float]:
    """Center of cell (cx, cy) in the grid's own frame (info.origin frame)."""
    lx = info.origin.position.x + (cx + 0.5) * info.resolution
    ly = info.origin.position.y + (cy + 0.5) * info.resolution
    return lx, ly


def local_to_cell(lx: float, ly: float, info) -> tuple[int, int]:
    """Which cell a local metric point falls in. Inverse of cell_to_local."""
    cx = int((lx - info.origin.position.x) / info.resolution)
    cy = int((ly - info.origin.position.y) / info.resolution)
    return cx, cy
```

To go from a cell in grid A all the way to a cell in the merged `world` grid: `cell_to_local` (in `robotA/map`) → apply `world -> robotA/map` (a 2D rigid transform: rotate by the yaw, add the translation) → `local_to_cell` (in the merged grid). For this week's *known-offset, same-orientation* setup the transform is a pure translation, so the rotation drops out and the math is an integer cell-offset add. That's the simplification that makes Exercise 2 tractable; the general rotated case is in the stretch goal.

### 1.4 The fusion rule: occupied wins

When both grids observed the same world cell, what value does the merged cell get? The instinct is to average. **Do not average.** Averaging free (0) and occupied (100) gives 50, which most consumers render as "probably occupied, kind of" gray mush — and worse, it can turn a definite wall one robot saw into a maybe-wall the planner drives through.

The correct rule is a **priority**:

> **occupied (100) > free (0) > unknown (-1).**

- If *either* robot saw the cell as occupied, the merged cell is occupied. A wall is a wall; one robot's confident observation of it should not be diluted by the other robot's never having looked.
- Else if *either* robot saw it as free, the merged cell is free.
- Else (both unknown), the merged cell is unknown.

```python
def fuse(a: int, b: int) -> int:
    """Merge two cell values. occupied(100) > free(0) > unknown(-1)."""
    OCC, FREE, UNK = 100, 0, -1
    if a == OCC or b == OCC:
        return OCC
    if a == FREE or b == FREE:
        return FREE
    return UNK
```

This is conservative in the safe direction: the merged map over-reports obstacles, never under-reports them. For navigation that's exactly the bias you want — a planner that thinks there's a wall where there isn't will route around empty space (wasteful but safe); a planner that thinks there's free space where there's a wall will drive into it (unsafe). The fusion rule encodes "trust any robot that saw a wall."

> **Caveat for moving robots and dynamic obstacles.** Occupied-wins is right for *static structure*. If robot A saw a corridor as occupied because robot B was standing in it, and robot B has since moved, occupied-wins will leave a phantom wall where robot B used to be. Real systems handle this with time-decay of occupancy and by masking out other robots' footprints before merging. We note it this week and handle it as a stretch goal; the honest 80% is "merge static structure, occupied wins."

### 1.5 A complete merge node sketch

```python
import numpy as np
from nav_msgs.msg import OccupancyGrid


def merge_grids(grid_a: OccupancyGrid, grid_b: OccupancyGrid,
                offset_b_cells: tuple[int, int],
                res: float) -> OccupancyGrid:
    """Merge two same-resolution, same-orientation grids. grid_a is the reference;
    grid_b is offset from it by offset_b_cells (integer cell shift in world).
    Returns a merged grid in the 'world' frame. (Known-offset simplification.)"""
    a = np.array(grid_a.data, dtype=np.int16).reshape(grid_a.info.height, grid_a.info.width)
    b = np.array(grid_b.data, dtype=np.int16).reshape(grid_b.info.height, grid_b.info.width)

    ox, oy = offset_b_cells
    # Merged extent = bounding box of A at (0,0) and B at (ox,oy).
    min_x = min(0, ox); min_y = min(0, oy)
    max_x = max(grid_a.info.width, ox + grid_b.info.width)
    max_y = max(grid_a.info.height, oy + grid_b.info.height)
    W, H = max_x - min_x, max_y - min_y

    merged = np.full((H, W), -1, dtype=np.int16)   # start all-unknown

    def blit(grid, gx, gy):
        h, w = grid.shape
        sy, sx = gy - min_y, gx - min_x
        region = merged[sy:sy + h, sx:sx + w]
        # occupied-wins / free-over-unknown fusion, vectorized
        occ = (grid == 100) | (region == 100)
        free = (grid == 0) | (region == 0)
        out = np.full_like(region, -1)
        out[free] = 0
        out[occ] = 100
        merged[sy:sy + h, sx:sx + w] = out

    blit(a, 0, 0)
    blit(b, ox, oy)

    out = OccupancyGrid()
    out.header.frame_id = "world"
    out.info.resolution = res
    out.info.width = W
    out.info.height = H
    out.info.origin.position.x = min_x * res
    out.info.origin.position.y = min_y * res
    out.info.origin.orientation.w = 1.0
    out.data = merged.flatten().astype(np.int8).tolist()
    return out
```

This is the spine of Exercise 2. It assumes same resolution and same orientation (known offset) — the realistic-but-tractable case. Differing resolutions require resampling; differing orientations require the full rotated cell-transform from §1.3.

---

## Part 2 — The inter-robot transform

### 2.1 Where it comes from

Everything in Part 1 depended on knowing how grid B sits relative to grid A in the world — the offset between `robotA/map` and `robotB/map`. There are three ways to get it, in increasing order of realism and difficulty:

1. **Known by setup (this week).** You place the robots at known starting poses — robot A at the world origin, robot B two meters along `+y`, both facing the same way. Then `world -> robotA/map` is identity and `world -> robotB/map` is a 2 m translation. You broadcast both as *static* transforms (Lecture 1 §7). Simple, correct, and exactly how a warehouse with docking stations at surveyed positions actually works.
2. **Estimated from a shared landmark.** Both robots see the same AprilTag (or the same distinctive feature). Each computes the tag's pose in *its own* `map` frame. The difference of those two poses *is* the `robotA/map -> robotB/map` transform. This is the poor-man's inter-robot loop closure and the week's stretch goal.
3. **Estimated by distributed SLAM (Part 3).** The robots recognize they've visited the same *place* (place recognition), generate an inter-robot loop-closure constraint, and a distributed pose-graph optimizer solves for the relative transform that best aligns both trajectories. This is Kimera-Multi territory.

### 2.2 Publishing it

For the known-offset case, two `static_transform_publisher`s (Lecture 1 §7) do it. For the estimated case, you publish a *dynamic* `world -> robotB/map` from your estimator node and update it whenever a new estimate arrives — but slowly, because the relative transform between two robots' maps should not jitter every tick. A good estimator publishes a smoothed estimate at, say, 1 Hz, not at the rate of every shared-landmark detection.

> **QoS note (week 5 returns).** The `world -> robot/map` transforms, if static, go on `/tf_static`, which is `RELIABLE` + `TRANSIENT_LOCAL` with a deep history — so a merger node that starts late still gets every static transform. If you publish them as static and the merger comes up late and `/tf_static` were `VOLATILE`, the merger would never learn how the maps relate and would silently produce a single-robot map. This is the week-5 durability lesson, re-paid at the multi-robot layer.

### 2.3 What a stale or wrong transform does: double-walling

The most instructive multi-robot failure: a wrong inter-robot transform. Suppose robot B actually started 2.0 m along `+y` but your static transform says 2.3 m. Now every wall robot B saw is painted into the merged grid 0.3 m off from where robot A saw the *same* wall. A corridor both robots drove down appears in the merged map as **two parallel walls 0.3 m apart** — a "double-walled" map. The planner sees a corridor that's 0.3 m narrower than reality, or an obstacle that isn't there.

A *stale* transform does the same thing dynamically: if robot B's `map` frame drifts (SLAM correction, a loop closure that shifts its origin) and your `world -> robotB/map` doesn't update, the offset is wrong by the drift, and B's contributions to the merged map smear. **You can see this with your eyes in rviz2** — the merged map of a known rectangular room shows doubled or thickened walls. That visual is your debugging signal, and it's exactly what Exercise 3 makes you produce and quantify. When the merged map's walls are crisp and single, the transform is right; when they're doubled, it's wrong. No metric needed to *detect* it; you need one to *quantify* it.

---

## Part 3 — Coordination as a distributed-systems problem

### 3.1 Never block one robot on another

The cardinal rule of multi-robot coordination, and the one most violated by engineers coming from single-robot work:

> **Never put an inter-robot call on a robot's critical path.** Robot A's control loop must never `await` a synchronous response from robot B. The network between them is slow, lossy, and occasionally gone; a robot that blocks its 50 Hz controller on a 200 ms (or never-arriving) reply from a peer is a robot that drives into a wall while waiting.

This is week 4's "use a topic until you can't" lesson, escalated. *Within* one robot, a synchronous service call is fine — it's in-process, microseconds. *Between* robots, even a service call that "usually" returns in 10 ms will someday hang because the Wi-Fi hiccuped, and your robot's safety loop must not hang with it. So inter-robot interaction is **asynchronous and best-effort**: robots publish their state (map, pose, intent) on topics; peers consume those topics at their own cadence; nobody waits on anybody.

### 3.2 The periodic-exchange, eventually-consistent pattern

Concretely, the shared-mapping system you build does *not* have robot A call robot B to ask "send me your map." Instead:

- Each robot **publishes** its current map on a latched (`TRANSIENT_LOCAL`) namespaced topic, `/robotA/map`, whenever SLAM updates it.
- A **merger node** subscribes to both `/robotA/map` and `/robotB/map`, and on its *own* timer (say every 2 s) merges the two latest maps it has and publishes `/shared_map`.
- No robot waits for the merger. No robot waits for the other robot. If robot B's map is 2 s stale when the merger runs, the merged map is 2 s stale on B's side — and that's *fine*, because a 2-s-old map of static walls is still a correct map of static walls.

This is **eventual consistency**: every consumer's view of the shared map converges over time, never instantaneously, and the system stays live even when one robot drops off the network. It is the only honest consistency model for a robot fleet, because the alternative — a globally synchronized, always-current shared map — requires a reliable low-latency network that does not exist in the real world. The week-5 fallacies of distributed computing ("the network is reliable," "latency is zero") are not abstractions here; they are the reason the merger runs on a timer instead of a synchronous gather.

### 3.3 Latency-bounded coordination

"Latency-bounded" means you design the coordination so that the *staleness* of shared state has a known upper bound, and the robot's behavior is *safe* under that bound. If the merger runs every 2 s and the network adds up to 500 ms, then the shared map any robot consults is at most ~2.5 s old. You then design behavior that's safe under 2.5 s of staleness — fine for "don't plan through a wall the other robot mapped," dangerous for "don't collide with the other robot *right now*." The latter (live collision avoidance between robots) needs a much tighter loop and is its own problem; the shared *map* is the slow, eventually-consistent layer, and live inter-robot avoidance is a fast, local layer on top. Conflating the two — trying to do live avoidance through the 2 s map exchange — is a classic and dangerous mistake. Keep the slow shared-state layer and the fast local-safety layer separate.

---

## Part 4 — The distributed-SLAM landscape (survey)

You built a *grid merger* with a *known* transform. Real fleets need more, and you should know the names so you can place your work and read a job description honestly.

### 4.1 Multi-robot Cartographer

Google's Cartographer supports multiple trajectories in one map and merges at the **submap** level — locally-consistent chunks — rather than fusing raw grids. Merging submaps lets the back-end optimizer correct for drift *across* robots, which raw-grid merging cannot. It's the natural next step up from what you built: same idea, but the unit of merging is a SLAM-native submap with a pose in the global graph, not a finished occupancy grid.

### 4.2 Kimera-Multi

Kimera-Multi (Tian, Chang, Carlone, et al.) is the 2026 reference for **fully distributed** multi-robot SLAM. Its defining properties:

- **No central server.** Each robot runs its own SLAM and pose-graph optimizer; they exchange compact information peer-to-peer.
- **Inter-robot loop closures.** When two robots recognize they've seen the same place (place recognition via learned descriptors), they generate a constraint linking their trajectories — *this* is what produces the inter-robot transform you assumed by setup.
- **Robustness to bad matches.** Place recognition produces false positives; a wrong inter-robot loop closure corrupts both robots' maps. Kimera-Multi uses distributed outlier rejection (pairwise-consistent measurement sets, the DOOR-SLAM idea) to reject them.

The hard part, the part that makes this a research-grade system and not a week's lab, is **place recognition under viewpoint and appearance change** — recognizing the same corridor from a different angle, in different lighting, possibly with the other robot in the frame. That's the bottleneck, and it's why we *assume* the inter-robot transform this week instead of estimating it.

### 4.3 Where your week-35 work sits

Your grid-merger with a known transform is the honest, deployable 80% for a structured environment with surveyed start positions — a warehouse, a fulfillment center, a hospital floor with docking stations. It is *not* a research-grade distributed SLAM, and you should say so. The gap is exactly the inter-robot loop closure: the moment your robots don't start at known offsets, or their maps drift apart, you need the place-recognition machinery that Kimera-Multi provides. Knowing precisely what you built and what you didn't is the senior move — it's the difference between "I did multi-robot SLAM" (overclaim) and "I built shared mapping with a known inter-robot transform; estimating it is distributed SLAM, which is Kimera-Multi's problem" (honest, and exactly what an interviewer wants to hear).

### 4.4 Bandwidth: the constraint nobody mentions until the field

One more reality that separates the bench from the deployment: **bandwidth**. On your laptop, both robots' maps live in the same process memory and "exchanging" them is free. On real hardware, each robot is a separate computer on a shared, finite radio link, and a full occupancy grid is not small — a 50 m × 50 m map at 5 cm resolution is a million cells, ~1 MB raw. Publishing that at even 1 Hz from each of several robots saturates a Wi-Fi link fast, and the week-5 fallacy "bandwidth is infinite" bites hard.

The field answers, in increasing sophistication:

- **Publish deltas, not full maps.** Send only the cells that changed since the last exchange. `slam_toolbox`'s update structure and most real merge stacks do this.
- **Compress.** Occupancy grids compress extremely well (huge runs of identical cells); even gzip on the wire is a large win, and is one reason a fleet may prefer a transport that supports it.
- **Exchange submaps or pose-graph deltas, not grids.** This is again why Cartographer and Kimera-Multi work at the submap / graph level — a pose-graph update is kilobytes where a full grid is megabytes. Distributed SLAM's peer-to-peer exchange is compact *by design* precisely because the radio link is the bottleneck.

For this week's single-laptop sim you ignore bandwidth, exactly as you ignore real discovery. But put it on the same list as multicast and latency: the three things that are free in sim and expensive — sometimes fatal — the day you go to hardware. A merger that publishes full megabyte grids at 10 Hz works beautifully in your demo and takes down the fleet Wi-Fi in the warehouse. Designing the exchange to be *small* is the part of the work that the laptop never forces you to do, so you must remember to do it on purpose.

### 4.5 A worked sizing of the staleness budget

Make the latency-bound concrete, because "eventually consistent" is too vague to design against. Suppose: the merger runs every **2 s**, the radio adds up to **0.5 s** of delivery latency under load, and each robot's SLAM updates its map at most every **1 s**. Then the worst-case age of robot B's contribution in the `/shared_map` that robot A consults is:

```
map age = SLAM update interval (1 s)
        + delivery latency to merger (0.5 s)
        + merger period (2 s)
        + delivery latency merger->A (0.5 s)
        = up to ~4 s stale.
```

Now you can ask the only question that matters: **is the robot's behavior safe with a 4-second-old view of the other robot's contribution to the shared map?** For *static structure* — "don't plan a path through a wall robot B mapped" — yes, trivially: a wall that was there 4 s ago is there now. For *the other robot's current position* — "don't drive into where robot B is right now" — absolutely not; 4 s at 1 m/s is 4 m of uncertainty about where B is. That is the line that separates the two layers (§3.3): the slow shared *map* tolerates 4 s of staleness; live inter-robot *collision avoidance* needs tens of milliseconds and must run on a different, local, fast path (each robot sensing the other directly with its own LiDAR, not via the shared map). Sizing the budget this way — writing down the number and then asking what's safe under it — is the design discipline. Skipping it, and hoping "eventually consistent" is good enough, is how a fleet has its first robot-on-robot collision.

---

## 5. The failure-mode decision tree

When the shared map is wrong, walk this tree:

```
Shared map looks wrong.
│
├─ Does `tf2_echo world robotB/base_link` resolve at all?
│   ├─ No  → the world->robotB/map transform isn't published.
│   │        Check /tf_static (TRANSIENT_LOCAL!) and the static broadcaster.
│   └─ Yes ↓
│
├─ Are the walls DOUBLED / thickened in rviz2?
│   ├─ Yes → wrong or stale inter-robot transform. Re-measure the offset;
│   │        check whether robotB/map drifted (a loop closure moved its origin).
│   └─ No ↓
│
├─ Is one robot's region MISSING from /shared_map?
│   ├─ Yes → merger isn't receiving that robot's /map. Check the namespaced
│   │        topic name and that /map is TRANSIENT_LOCAL (durability, week 5).
│   └─ No ↓
│
├─ Is the overlap region GRAY MUSH (value ~50)?
│   ├─ Yes → you averaged instead of occupied-wins. Fix the fusion rule. (§1.4)
│   └─ No ↓
│
└─ Map drifts/smears over time → other robots' footprints aren't masked,
   or occupancy isn't time-decayed (dynamic-obstacle caveat, §1.4).
```

Tape this next to the merge-fusion rule. Between the two, you can diagnose almost any "the shared map is wrong" problem in under five minutes — which is the whole point of this week.

---

## 5.5 Why we merge finished grids and not raw scans (this week)

A reasonable question: why merge two *finished* occupancy grids at all? Why not pool both robots' raw LiDAR scans into one SLAM instance and let it build a single map directly? The answer is a clean illustration of the centralized-vs-distributed trade-off, and it's worth stating because the choice recurs in every fleet design.

**Centralized SLAM** — one node consumes every robot's scans and odometry and produces one map — is *more accurate*, because the optimizer sees all the constraints at once and can close loops across robots inside a single pose graph. But it has three liabilities that grow with the fleet: it's a **single point of failure** (the SLAM node dies, the whole fleet goes blind), it needs **every robot's full sensor stream** on the network (the bandwidth problem of §4.4, at its worst — raw scans are larger and faster than maps), and it **doesn't degrade gracefully** (a robot that drops off doesn't just lose its own contribution; it can destabilize the shared optimization).

**Grid merging** — each robot runs its own SLAM, the merger fuses the outputs — is *less accurate* (no cross-robot loop closure; that's the §4 gap) but **robust and cheap**: each robot maps independently and keeps working if a peer or the merger dies, only maps cross the network (smaller than scans), and the system degrades one-robot-at-a-time. This is the same resilience-vs-optimality trade you'll see everywhere in distributed systems, and for a *deployable* fleet in 2026 the robust option usually wins — which is why you build the merger this week and treat centralized cross-robot optimization (Cartographer's multi-trajectory, Kimera-Multi's distributed graph) as the accuracy upgrade you reach for only when the known-transform merge isn't good enough. Independent SLAM plus a merger is the architecture that survives contact with a real warehouse; one heroic central SLAM node is the architecture that demos well and pages you at 3 a.m.

---

## 6. Recap

You should now be able to:

- Read every field of `nav_msgs/OccupancyGrid` and explain why `info.origin` is what keeps two grids from merging shifted.
- Convert cells to world coordinates and back, and merge two same-resolution grids with the **occupied-wins** fusion rule, never averaging.
- Identify the three sources of the inter-robot transform (known, shared-landmark, distributed-SLAM) and publish the known one as a `TRANSIENT_LOCAL` static transform.
- Recognize a double-walled merged map as the signature of a wrong or stale inter-robot transform, and quantify it.
- Keep coordination off the critical path with a periodic, eventually-consistent map exchange, and explain why latency-bounded staleness is the only honest fleet consistency model.
- Place your grid-merger relative to multi-robot Cartographer and Kimera-Multi, and name inter-robot loop closure / place recognition as the gap between them.
- Size a concrete staleness budget and use it to decide which behaviors are safe under the shared map's latency and which need a separate fast local layer.
- Explain why independent-SLAM-plus-merger is the robust, deployable choice over a single centralized SLAM node, and when you'd pay the accuracy upgrade.

The one-sentence summary of the whole week: **a shared map is two robots' independent beliefs, reconciled periodically and best-effort in a common frame, with obstacles trusted conservatively and the inter-robot transform treated as a quantity to estimate, not a constant to assume.** Every design choice this week — occupied-wins, the timer-driven merger, the `world` frame, the honest survey of what you didn't build — falls out of taking that sentence seriously.

Next: the exercises put all of this on two real robots in Gz Sim. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *`nav_msgs/OccupancyGrid`* — ROS2 docs: <https://docs.ros.org/en/jazzy/p/nav_msgs/interfaces/msg/OccupancyGrid.html>
- *`m-explore-ros2` `multirobot_map_merge`* (the production grid merger): <https://github.com/robo-friends/m-explore-ros2>
- *Cartographer ROS* (multi-trajectory, submap merging): <https://github.com/cartographer-project/cartographer_ros>
- *Kimera-Multi* (Tian et al., distributed multi-robot SLAM): <https://arxiv.org/abs/2106.14386>
- *DOOR-SLAM* (Lajoie et al., outlier-resilient distributed SLAM): <https://arxiv.org/abs/1909.12198>
- *Fallacies of distributed computing* (why coordination is best-effort): <https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing>
- *`tf2_ros` static broadcaster* (publishing the inter-robot transform): <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html>
