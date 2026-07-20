# Mini-Project — `crunchbot_multi`: Two Robots, One Shared Map

> Build a reusable multi-robot package that brings up two namespaced, frame-prefixed diff-drive robots in one Gz Sim world, runs independent `slam_toolbox` per robot, and serves a live merged `/shared_map` in a common `world` frame — with an rviz2 layout that shows both robots and the shared map at once.

This is the artifact that proves you understand the whole week: namespacing (no collisions), frame prefixing (two clean trees), discovery (one domain), the inter-robot transform (tying both maps into `world`), occupancy-grid merging (occupied-wins fusion), and latency-bounded coordination (a periodic, eventually-consistent merger that never blocks a robot). After this week, "two robots share a map" is a launch command, not a research project.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This package is the substrate for **Week 36 (task allocation and fleet management)** — the fleet manager you build there allocates tasks across the *same* two namespaced robots, and the shared map is what makes "robot A is closer to that shelf" a computable statement. It also feeds the **Week 40 Phase 5 milestone** ("two simulated robots share a map without collision"). Build it well now; you'll extend it twice.

---

## What you will build

A `colcon` package `crunchbot_multi` with three deliverables:

1. **`launch/two_robots.launch.py`** — brings up two robots (`robotA`, `robotB`) from one parameterized group, each namespaced and frame-prefixed, each with its own `slam_toolbox`, plus the two `world -> robot/map` static transforms. Adding a third robot is two lines.
2. **`crunchbot_multi/map_merger.py`** — a node that subscribes to `/robotA/map` and `/robotB/map` (latched, `TRANSIENT_LOCAL`), and on its **own** timer merges the two latest grids it has into `/shared_map` in the `world` frame, using the occupied-wins fusion rule. It never blocks on either robot; it merges whatever it last received.
3. **An rviz2 layout** (`rviz/shared_map.rviz`) with Fixed Frame `world`, two `RobotModel`s (one per namespace), the two per-robot `/map`s, and the merged `/shared_map`, so a reviewer sees the whole system in one window.

By the end you have a public repo of ~300–400 lines that any future crunchbot multi-robot work can build on, and a one-command demo of two robots sharing a map.

---

## Why a periodic merger, not a synchronous gather

You could have the merger *request* each robot's map synchronously every cycle. Don't. As Lecture 2 §3 argues, an inter-robot call on the critical path is a liability: the merger would block whenever a robot is slow or briefly off the network, and a blocked merger means a stale `/shared_map` *and* a hung node. Instead:

- Each robot **publishes** its map on a latched topic whenever SLAM updates it.
- The merger **subscribes** and caches the latest map per robot.
- The merger merges on **its own timer** (every ~2 s), using whatever it last cached.

This is eventual consistency: `/shared_map` is at most ~2 s + network latency stale, the system stays live if a robot drops off, and no robot ever waits for the merger. That staleness bound is fine for static structure (the only thing we merge) and explicitly *not* fine for live inter-robot collision avoidance (a separate, fast, local layer — out of scope this week).

---

## Package layout

```
crunchbot_multi/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunchbot_multi
├── crunchbot_multi/
│   ├── __init__.py
│   ├── map_merger.py        # the periodic, eventually-consistent merger
│   └── grid_ops.py          # cell<->world, fuse(), merge() — pure functions, tested
├── launch/
│   └── two_robots.launch.py
├── rviz/
│   └── shared_map.rviz
└── test/
    ├── test_grid_ops.py     # unit tests: fuse() priority, merge() extent + offset
    └── test_merger_logic.py # unit tests: the cache-and-merge logic with stale inputs
```

---

## Deliverable 1 — the two-robot launch

The spine is Lecture 1 §7: a `robot(ns, x, y)` function building one namespaced, frame-prefixed stack, called twice, plus a `world_to_map(ns, x, y)` static transform per robot. Requirements:

- Every per-robot topic is **relative** (no leading slash) so namespacing prefixes it.
- `robot_state_publisher` gets `frame_prefix: "<ns>/"`; `slam_toolbox` gets `map_frame/odom_frame/base_frame` prefixed.
- Upstream nodes that publish absolute `/map` are **remapped** to relative `map` before the namespace prefixes them.
- The two robots start at known offsets (e.g. `robotA` at world origin, `robotB` 2 m along `+y`), so the `world -> robot/map` transforms are static and correct by construction.
- The launch takes a `use_sim_time` argument and passes it to every node (two SLAM instances on sim time).

Here is the spine to start from; fill in your week-8 sensor/spawn bring-up:

```python
from launch import LaunchDescription
from launch.actions import GroupAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def robot(ns: str, x: float, y: float, use_sim_time):
    return GroupAction([
        PushRosNamespace(ns),
        Node(
            package="robot_state_publisher", executable="robot_state_publisher",
            parameters=[{"frame_prefix": f"{ns}/", "use_sim_time": use_sim_time}],
            # TODO 1: pass your URDF (robot_description) here as in week 8.
        ),
        # TODO 2: your Gz Sim spawn + sensor bridge for this robot, all RELATIVE topics.
        Node(
            package="slam_toolbox", executable="async_slam_toolbox_node",
            parameters=[{
                "map_frame": f"{ns}/map",
                "odom_frame": f"{ns}/odom",
                "base_frame": f"{ns}/base_link",
                "scan_topic": f"/{ns}/scan",
                "use_sim_time": use_sim_time,
            }],
            remappings=[("/map", "map")],
        ),
    ])


def world_to_map(ns: str, x: float, y: float):
    return Node(
        package="tf2_ros", executable="static_transform_publisher",
        arguments=[str(x), str(y), "0", "0", "0", "0", "world", f"{ns}/map"],
    )


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time")
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        robot("robotA", 0.0, 0.0, use_sim_time),
        robot("robotB", 0.0, 2.0, use_sim_time),
        world_to_map("robotA", 0.0, 0.0),
        world_to_map("robotB", 0.0, 2.0),
        Node(package="crunchbot_multi", executable="map_merger"),
        # TODO 3: launch rviz2 with the shared_map.rviz layout.
    ])
```

---

## Deliverable 2 — the map merger

A node that:

1. Subscribes to `/robotA/map` and `/robotB/map` with the **latched** QoS (`RELIABLE` / `TRANSIENT_LOCAL` / depth 1 — the week-5 map profile; a `VOLATILE` subscriber here silently misses a map published before it started).
2. Caches the latest `OccupancyGrid` from each robot. Does **not** merge in the subscription callback.
3. On a **2 s timer**, if it has a map from each robot, looks up `world -> robotA/map` and `world -> robotB/map` from tf2, converts the per-robot offsets into integer cell shifts, merges the two grids with `grid_ops.merge()`, and publishes `/shared_map` in the `world` frame (also latched, so a late rviz2 or planner gets it).
4. Logs a one-line status each tick: which robots it has maps for, the merged extent, the occupied-cell count.

The merge math (`cell<->world`, `fuse()`, `merge()`) lives in `grid_ops.py` as **pure functions** so they're unit-testable without ROS. Reuse the `fuse()` and `merge()` from Exercise 2 — they are exactly the same functions, now in a package. The `fuse()` rule is occupied-wins; the auditor in Week 36 will rely on it.

Skeleton of the merger core:

```python
class MapMerger(Node):
    def __init__(self) -> None:
        super().__init__("map_merger")
        self.latest = {}   # ns -> OccupancyGrid, the cache
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(OccupancyGrid, "/shared_map", latched_qos())
        for ns in ("robotA", "robotB"):
            self.create_subscription(
                OccupancyGrid, f"/{ns}/map",
                lambda msg, ns=ns: self._cache(ns, msg), latched_qos())
        self.create_timer(2.0, self._merge_tick)   # periodic, eventually-consistent

    def _cache(self, ns: str, msg) -> None:
        self.latest[ns] = msg          # just cache; never merge in the callback

    def _merge_tick(self) -> None:
        if len(self.latest) < 2:
            self.get_logger().info(f"waiting for maps; have {list(self.latest)}")
            return
        # TODO 4: look up world->robotA/map and world->robotB/map from tf2,
        #         convert to cell offsets, merge with grid_ops.merge(), publish.
```

---

## Deliverable 3 — the rviz2 layout

A saved `shared_map.rviz` with:

- **Fixed Frame: `world`** (not `map` — there are two of those now).
- A `Map` display on `/shared_map`.
- Optionally the two per-robot `/map`s on separate `Map` displays (different color schemes) so you can *see* the merge overlap.
- A `RobotModel` per robot, or at least a `TF` display, so both robots' poses appear in `world`.

The point: one window where a reviewer sees two robots and one crisp shared map, with single (not doubled) walls. That visual *is* the deliverable's acceptance.

---

## Rules

- **You may** read the ROS2 docs, the lecture notes, `slam_toolbox` and `multirobot_map_merge` source, and reuse your Exercise 2 `fuse`/`merge`.
- **You must not** put an inter-robot interaction on a robot's critical path. The merger merges on its own timer from cached maps; it never blocks a robot, and no robot waits for it. If your merger does a synchronous gather, you've missed the week's core lesson.
- **You must not** hard-code a namespace or frame prefix in any *node*; they come from launch arguments. The same node code runs under any namespace.
- **You must not** average overlapping cells. Occupied-wins, every time. (`test_grid_ops.py` will check this.)
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy, `slam_toolbox` from apt.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-35-crunchbot-multi-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_multi` succeeds with no warnings.
- [ ] `ros2 launch crunchbot_multi two_robots.launch.py` brings up two robots; `ros2 topic list` shows `/robotA/*` and `/robotB/*` with no bare `/scan` or `/map`.
- [ ] `ros2 run tf2_ros tf2_echo world robotA/base_link` and `... robotB/base_link` both resolve into the shared `world` frame.
- [ ] `/shared_map` publishes, covers both robots' explored area, and in rviz2 shows **single, crisp walls** (no double-walling) when the transforms are correct.
- [ ] The merger merges on its own timer from cached maps — demonstrably never blocking (kill one robot's SLAM and the merger keeps publishing the last good shared map, logging that it's stale).
- [ ] `colcon test --packages-select crunchbot_multi` passes, with at least:
  - `test_grid_ops.py`: `fuse()` returns occupied for (occupied, free), free for (free, unknown), unknown for (unknown, unknown); `merge()` produces the correct extent and offset.
  - `test_merger_logic.py`: the merger publishes only when it has both maps, and reuses a cached map when one robot is silent.
- [ ] A `README.md` with the launch command, the rviz2 screenshot showing crisp walls, and a paragraph on why the merger is periodic, not synchronous.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Namespacing & frames** | 20 | Two clean prefixed TF trees under one `world`; no bare topics; node names unique; `tf2_echo world robot/base_link` resolves for both. |
| **Merge correctness** | 25 | Occupied-wins fusion (no averaging); correct extent and `info.origin`; single crisp walls in rviz2; `info.origin` handled so maps don't shift. |
| **Latency-bounded coordination** | 20 | Merger merges on its own timer from cached maps; never blocks a robot; survives one robot going silent by reusing the last cached map and logging staleness. |
| **Inter-robot transform** | 15 | `world -> robot/map` published correctly (static, `TRANSIENT_LOCAL` on `/tf_static`); merger reads it from tf2, not hard-coded. |
| **Tests** | 15 | `grid_ops` pure functions tested (fusion priority, extent, offset); merger cache-and-merge logic tested with a missing/stale input. |
| **Docs & hygiene** | 5 | Clear README, rviz2 screenshot, sensible commits, no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to extend in Week 36. **70–89** works but has shifted maps, a blocking merger, or thin tests. **Below 70** means the maps don't actually share a frame — fix the namespacing/transform first.

---

## Stretch goals

- **Estimated transform.** Replace the static `world -> robotB/map` with an estimate from a shared AprilTag both robots see (Lecture 2 §2.1). Now the merge works even when you *don't* know the starting offset — the poor-man's inter-robot loop closure.
- **Drift recovery.** Fold in the Challenge-1 occupied-cell-minimizing re-estimator so the merger self-heals when a robot's `map` frame drifts after a loop closure.
- **Third robot.** Add `robotC` in two lines and confirm the merger generalizes; note where N-robot discovery traffic starts to want a discovery server (week 5).
- **Benchmark against `multirobot_map_merge`.** Run the open-source merger on the same two `slam_toolbox` instances and compare its feature-aligned output to your known-transform output. Document where each wins.

---

## How this connects to the rest of C24

- **Week 36 (fleet management)** allocates tasks across these *same* two namespaced robots; `/shared_map` is what makes "which robot is closest" computable.
- **Week 40 (Phase 5 milestone)** grades "two simulated robots share a map without collision" — this package is that deliverable, built five weeks early.
- **The capstone** lists `/fleet/heartbeat` as a required topic; the namespacing discipline here is exactly what lets a fleet manager address each robot individually.

When you've finished, push the repo and take the [quiz](../quiz.md).
