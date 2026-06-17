# Mini-Project — `crunch_posegraph`: A GTSAM Pose-Graph Optimizer as a ROS2 Node

> Build a reusable ROS2 node that ingests a stream of `nav_msgs/Odometry` (the robot's drifting odometry) plus loop-closure constraints, maintains a GTSAM factor graph, optimizes it, and publishes the corrected trajectory as a `nav_msgs/Path` in the `map` frame — with marginal covariances on request. This is the **back-end of a SLAM system**, built by hand, and it is the artifact that proves you understand factor graphs as engineering, not just as math.

This is the week's flagship. The exercises taught you the pieces — AMCL, the UKF, a toy GTSAM graph. The mini-project assembles the factor-graph piece into something that runs on your robot's data and corrects its drift online. After this, "modern SLAM back-ends are factor graphs" (Lecture 2 §8) is not a slogan you read; it is a thing you built.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This node is a building block for the **Phase 2 midterm in Week 16** (where your fused perception graph must produce a drift-bounded state estimate) and a direct on-ramp to the **3D-perception SLAM work in Week 15**, where you register LiDAR scans and feed the relative transforms in as between factors. The capstone's "fused state estimate drifts < 0.5 m over 20 m" acceptance criterion is, ultimately, a pose-graph problem. Build this well now.

---

## What you will build

A small ament-python package `crunch_posegraph` with three deliverables:

1. **`crunch_posegraph/graph_backend.py`** — a pure-Python, ROS-free `PoseGraphBackend` class wrapping GTSAM. It exposes `add_odometry(prev_key, new_key, relative_pose, sigmas)`, `add_loop_closure(key_a, key_b, relative_pose, sigmas, robust=True)`, `add_prior(key, pose, sigmas)`, `optimize()`, `get_trajectory()`, and `marginal_trace(key)`. It is fully unit-testable without ROS — this is where the GTSAM logic lives.
2. **`crunch_posegraph/posegraph_node.py`** — the ROS2 node. It subscribes to `/odom` (`nav_msgs/Odometry`), converts each odometry message into a relative-pose **between factor** (composing consecutive odom poses), feeds it to the backend, and on a timer (or on each loop closure) calls `optimize()` and publishes the corrected trajectory on `/posegraph/path` (`nav_msgs/Path`). Loop closures arrive on a `/posegraph/loop_closure` topic (a small custom or `geometry_msgs/PoseStamped`-based message keyed by two pose indices).
3. **A demo + tests** — a `loop_harness.py`-style demo publisher that replays a drifting odometry trajectory and injects one loop closure, plus `pytest` unit tests on the backend (a noise-free graph optimizes to error ~0; a loop closure reduces ATE on synthetic data; a robust kernel survives a planted false closure).

By the end you have a public repo of ~300–400 lines of Python that any future crunchbot package can import as a SLAM back-end, and that you can demo live: drift in, corrected path out.

---

## Why a ROS-free backend class

The single most important design decision in this project is that **all the GTSAM logic lives in a plain Python class with no ROS imports.** The ROS node is a thin adapter that converts messages to/from the backend's plain types (keys, `(x, y, theta)` tuples, sigma arrays). This buys you:

- **Testability.** `pytest` runs the backend in milliseconds with no `rclpy.init()`, no executor, no DDS. The factor-graph correctness — the part that's hard — is tested in isolation.
- **Reusability.** The same backend runs offline on a recorded bag, in a notebook for tuning, or inside the node. SLAM back-ends are reused everywhere; coupling yours to `rclpy` would throw that away.
- **Clarity.** When the node misbehaves, you know instantly whether the bug is in the graph (test the backend) or in the plumbing (the node). That separation is the senior-shop convention in 2026.

This mirrors the Week 5 `crunchbot_qos` discipline: the hard logic in one importable module, the ROS layer thin on top.

---

## Package layout

```
crunch_posegraph/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_posegraph
├── crunch_posegraph/
│   ├── __init__.py
│   ├── graph_backend.py        # the GTSAM wrapper (ROS-free, the heart)
│   ├── posegraph_node.py       # the ROS2 node (thin adapter)
│   └── demo_publisher.py       # replays drifting odom + one loop closure
├── launch/
│   └── demo.launch.py
└── test/
    ├── test_backend_consistency.py   # noise-free graph -> error ~0
    └── test_loop_closure.py          # loop closure reduces ATE; Huber survives outlier
```

---

## Deliverable 1 — `graph_backend.py` (the GTSAM wrapper)

This is the heart. It must:

- Hold a `gtsam.NonlinearFactorGraph`, a `gtsam.Values` (the current best estimate / initial guess), and a counter of how many poses exist.
- `add_prior(key, pose, sigmas)` — add a `PriorFactorPose2`. The first thing any graph needs; without it the graph floats (Lecture 2 §2).
- `add_odometry(prev_key, new_key, relative_pose, sigmas)` — add a `BetweenFactorPose2`, and seed the new variable's initial estimate by composing the previous estimate with the relative pose (so Levenberg-Marquardt starts near the answer).
- `add_loop_closure(key_a, key_b, relative_pose, sigmas, robust=True)` — add a `BetweenFactorPose2` between two existing poses, wrapping the noise model in a Huber kernel when `robust=True` (Lecture 2 §4). Real loop closures get `robust=True`.
- `optimize()` — run `LevenbergMarquardtOptimizer`, store the result as the new estimate, and return the final graph error.
- `get_trajectory()` — return the optimized poses as a list of `(x, y, theta)` tuples (ROS-free types).
- `marginal_trace(key)` — return `trace(marginalCovariance(key))`, the scalar uncertainty summary.

Here is the spine to start from; fill in the remaining methods yourself:

```python
"""crunch_posegraph.graph_backend — a ROS-free GTSAM pose-graph wrapper.

All factor-graph logic lives here so it is unit-testable without rclpy.
"""
from __future__ import annotations

import numpy as np
import gtsam
from gtsam import Pose2, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X


class PoseGraphBackend:
    def __init__(self) -> None:
        self._graph = NonlinearFactorGraph()
        self._estimate = Values()
        self._keys: set[int] = set()

    def add_prior(self, key: int, pose: tuple[float, float, float],
                  sigmas: tuple[float, float, float]) -> None:
        noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(sigmas))
        self._graph.add(gtsam.PriorFactorPose2(X(key), Pose2(*pose), noise))
        if key not in self._keys:
            self._estimate.insert(X(key), Pose2(*pose))
            self._keys.add(key)

    def add_odometry(self, prev_key: int, new_key: int,
                     relative_pose: tuple[float, float, float],
                     sigmas: tuple[float, float, float]) -> None:
        noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(sigmas))
        rel = Pose2(*relative_pose)
        self._graph.add(gtsam.BetweenFactorPose2(X(prev_key), X(new_key), rel, noise))
        if new_key not in self._keys:
            # Seed the new pose from the previous estimate composed with odometry.
            prev_pose = self._estimate.atPose2(X(prev_key))
            self._estimate.insert(X(new_key), prev_pose.compose(rel))
            self._keys.add(new_key)

    def add_loop_closure(self, key_a: int, key_b: int,
                         relative_pose: tuple[float, float, float],
                         sigmas: tuple[float, float, float],
                         robust: bool = True) -> None:
        base = gtsam.noiseModel.Diagonal.Sigmas(np.array(sigmas))
        noise = base
        if robust:
            huber = gtsam.noiseModel.mEstimator.Huber.Create(1.345)
            noise = gtsam.noiseModel.Robust.Create(huber, base)
        self._graph.add(gtsam.BetweenFactorPose2(
            X(key_a), X(key_b), Pose2(*relative_pose), noise))

    def optimize(self) -> float:
        params = gtsam.LevenbergMarquardtParams()
        result = gtsam.LevenbergMarquardtOptimizer(
            self._graph, self._estimate, params).optimize()
        self._estimate = result
        return float(self._graph.error(result))

    def get_trajectory(self) -> list[tuple[float, float, float]]:
        out = []
        for key in sorted(self._keys):
            p = self._estimate.atPose2(X(key))
            out.append((p.x(), p.y(), p.theta()))
        return out

    def marginal_trace(self, key: int) -> float:
        marginals = gtsam.Marginals(self._graph, self._estimate)
        return float(np.trace(marginals.marginalCovariance(X(key))))
```

---

## Deliverable 2 — `posegraph_node.py` (the ROS2 node)

A thin `rclpy` node that:

1. Subscribes to `/odom` (`nav_msgs/Odometry`) with a sensor-ish QoS. On the **first** message, `add_prior(0, ...)` anchoring the graph at that pose. On each subsequent message, compute the **relative** pose from the previous odom message to this one (compose: `prev.between(curr)`), and `add_odometry(prev_key, new_key, relative, sigmas)`. Use the message's covariance (or a configured default) for the sigmas.
2. Subscribes to `/posegraph/loop_closure` for loop-closure constraints. A loop closure carries two pose indices and a relative pose; on receipt, `add_loop_closure(...)` with `robust=True`, then trigger an `optimize()`.
3. On a timer (e.g. 2 Hz) calls `optimize()` and publishes the corrected trajectory on `/posegraph/path` (`nav_msgs/Path`), every pose stamped with `frame_id="map"` (Lecture 2 §3 from Week 5: honest `frame_id`).
4. Publishes the `map → odom` correction transform (optional stretch) so the corrected estimate is consumable by the rest of the stack the way AMCL's correction is.

The node must **not** import GTSAM directly — it talks only to `PoseGraphBackend`. Converting between `nav_msgs/Odometry` (which carries a quaternion) and the backend's `(x, y, theta)` is the node's job: extract yaw from the quaternion with `tf_transformations.euler_from_quaternion`.

```python
# the yaw-extraction helper the node needs (sketch):
from tf_transformations import euler_from_quaternion

def yaw_of(odom_msg) -> float:
    q = odom_msg.pose.pose.orientation
    return euler_from_quaternion([q.x, q.y, q.z, q.w])[2]
```

---

## Deliverable 3 — the demo and tests

- **`demo_publisher.py`** — replays a drifting square-loop odometry trajectory (reuse the `make_world` generator from Challenge 1) onto `/odom`, then after the loop publishes one loop closure on `/posegraph/loop_closure`. This gives the node a real stream to correct, and gives you a before/after `nav_msgs/Path` to visualize in rviz2 (add a Path display, watch the corrected path snap closed when the loop closure arrives).
- **`test_backend_consistency.py`** — `pytest` tests with no ROS: build a noise-free two/three-pose graph, optimize, assert final error `< 1e-6` and the poses match the hand calculation.
- **`test_loop_closure.py`** — build a drifting synthetic loop, assert that `add_loop_closure` + `optimize` reduces ATE vs. the open chain, and that a planted *false* loop closure with `robust=True` yields a far lower ATE than with `robust=False` (the Huber kernel survives the outlier — Lecture 2 §4).

---

## Rules

- **You may** read the GTSAM docs and Python examples, the Dellaert & Kaess factor-graph survey, and `slam_toolbox` for inspiration.
- **You must not** import `gtsam` anywhere except `graph_backend.py`. The node and the demo talk to `PoseGraphBackend` only. If `grep -rn "import gtsam" --include=*.py | grep -v graph_backend.py` returns anything (besides tests), you've broken the layering the project exists to teach.
- **You must not** depend on anything outside the ROS2 Jazzy desktop install plus `gtsam`, `numpy`, and `pytest`.
- Python 3.12 (Ubuntu 24.04 default), `rclpy` on Jazzy, `gtsam` from `pip`.
- Every published `nav_msgs/Path` pose carries `frame_id="map"` and an honest stamp.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-11-crunch-posegraph-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_posegraph` succeeds with no warnings.
- [ ] `graph_backend.py` implements all the listed methods; loop closures default to `robust=True`.
- [ ] `grep -rn "import gtsam" --include=*.py` finds matches **only** in `graph_backend.py` (and `test/`).
- [ ] `colcon test --packages-select crunch_posegraph` passes, including:
  - a noise-free-graph-optimizes-to-zero-error test,
  - a loop-closure-reduces-ATE test,
  - a Huber-survives-false-loop-closure test.
- [ ] Running `demo.launch.py` brings up the node + demo publisher; rviz2's Path display shows the drifted trajectory snap into a closed loop when the loop closure arrives.
- [ ] The node publishes `/posegraph/path` with every pose in the `map` frame, honestly stamped.
- [ ] A `README.md` in the repo root with the architecture (backend vs node), the run commands, a before/after screenshot of the path, and the ATE numbers from your demo.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Backend correctness** | 25 | Prior/between/loop factors built correctly; new variables seeded from the previous estimate; `optimize()` returns the right error; marginals read correctly. |
| **Layering discipline** | 15 | The `grep` check is clean; the node never imports GTSAM; backend is pure-Python and reusable. |
| **Loop-closure + robustness** | 20 | Loop closures reduce ATE; `robust=True` uses a Huber kernel; a false closure is survived under Huber and breaks under plain Gaussian, demonstrated. |
| **ROS node plumbing** | 15 | Odometry → relative-pose between factor is correct (quaternion yaw extracted right); `/posegraph/path` is published in `map` frame, honestly stamped, with sane QoS. |
| **Tests** | 15 | Unit tests cover consistency, ATE reduction, and robustness; `colcon test` green. |
| **Docs & demo** | 10 | Clear README with architecture, before/after path screenshot, ATE numbers, and run commands. |

**90+** is portfolio-grade and ready to feed the Week 16 fused-perception graph. **70–89** works but has a coupling leak or a soft test. **Below 70** means the backend isn't cleanly separated or the loop closure doesn't actually correct drift — fix that first.

---

## Stretch goals

- **Incremental iSAM2 backend.** Add a `PoseGraphBackendISAM2` that uses `gtsam.ISAM2` and `update()` incrementally instead of re-optimizing from scratch. Benchmark per-step time vs. the batch backend on a 500-pose trajectory; the incremental version should be dramatically cheaper, with a spike on the loop-closure update.
- **Real `slam_toolbox` comparison.** Run `slam_toolbox` on the same Gz Sim world, export its pose graph, and compare your optimizer's ATE against `slam_toolbox`'s on the same odometry. You're benchmarking your hand-built back-end against the production one.
- **Loop-closure detection (front-end taste).** Add a trivial front-end: when two poses come within a distance threshold *and* their scans match (reuse a simple scan-matching score), auto-generate a loop closure. Now you have a (tiny) full SLAM system, front-end and back-end.
- **3D (`Pose3`).** Generalize the backend to `gtsam.Pose3` / `BetweenFactorPose3` so it ingests full 6-DOF poses — the version you'll want for the Week 15 LiDAR registration work.

---

## How this connects to the rest of C24

- **Week 15 (3D perception)** produces relative transforms from point-cloud (ICP) registration. Feed those into this backend as between factors and you have LiDAR-odometry pose-graph SLAM — the structure of LIO-SAM.
- **Week 16 (Phase 2 midterm)** requires a drift-bounded fused state estimate. This pose-graph optimizer, fed by odometry + loop closures, is one honest way to bound that drift, and the marginals quantify it.
- **The capstone** is graded in part on "fused state estimate drifts < 0.5 m over 20 m." That is a pose-graph claim. The back-end you build here is the thing that makes it true.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
