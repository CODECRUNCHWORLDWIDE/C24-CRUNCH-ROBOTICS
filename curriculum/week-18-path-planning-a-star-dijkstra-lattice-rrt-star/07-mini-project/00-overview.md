# Mini-Project — `crunch_planners`: One Library, Every Planner, Behind One Interface

> Build a reusable planning library that exposes A*, weighted A*, Dijkstra, and RRT* behind a single clean `Planner` interface, with a self-checking benchmark harness — *and* a thin C++ `nav2_core::GlobalPlanner` plugin that lets you run your own grid planner inside a live Nav2 `planner_server`, side by side with `NavfnPlanner`. This is where the planners you wrote in the exercises stop being scripts and become a thing you can drop into a robot.

This is the artifact that turns "I implemented A* once" into "I have a planning library I trust and can deploy." After this week, your planners live behind one interface, prove their own correctness, and one of them runs *inside Nav2* — so you've closed the loop from "wrote a planner in Python" to "shipped a planner plugin in the production stack."

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** The planner-selection instinct and the Nav2 plugin wrapper feed directly into **Week 19** (the behavior tree's `ComputePathToPose` leaf is choosing a planner) and the **Week 24 Phase 3 integration**, where your global planner is one of the components in the combined Nav2 + MoveIt2 graph. Build it well now; you'll defend the planner choice at the integration review.

---

## What you will build

A package `crunch_planners` with three deliverables:

1. **The Python planning library** — `crunch_planners/` with `astar.py`, `rrt_star.py`, and a common `Planner` base class so every planner has the same `plan(start, goal) -> Path` signature. The exercises' code, cleaned into a library with one interface.
2. **The benchmark harness** — `crunch_planners/bench.py` that runs any registered planner on any map, reports path length / nodes-or-samples / runtime (mean + p95), and **self-checks** the invariants (A* matches Dijkstra; RRT* improves with samples). This is the Challenge's bake-off, productized.
3. **The Nav2 global-planner plugin** — a C++ `nav2_core::GlobalPlanner` (`CrunchAStarPlanner`) that runs your A* over the live global costmap and publishes a `nav_msgs/Path`, exported with `PLUGINLIB_EXPORT_CLASS` and selectable in `nav2_params.yaml` as `planner_plugins: ["GridBased"]` → `crunch_planners/CrunchAStarPlanner`.

By the end you have a public repo of ~600–900 lines (Python library + tests + the C++ plugin + the benchmark) that any future crunchbot package can use — and a planner that you can A/B against NavFn on the real robot.

---

## Why one interface and not four scripts

You could keep four standalone scripts. Don't — not for anything you'll reuse. A single `Planner` interface gives you:

- **Swappability.** The benchmark, the Nav2 plugin, and the Week-24 integration all call `planner.plan(start, goal)` — swapping A* for RRT* for weighted A* is a one-line change, not a rewrite.
- **Self-checking invariants in one place.** The benchmark asserts the optimality and improvement properties for *every* planner that implements the interface, so a new planner can't silently ship broken.
- **A clean Nav2 boundary.** The C++ plugin is a thin adapter — costmap in, `Path` out — because the planning logic lives behind the interface. That's the senior-shop convention: the algorithm and the framework adapter are separate concerns.

---

## Package layout

```
crunch_planners/
├── package.xml
├── CMakeLists.txt                  # builds the C++ Nav2 plugin
├── setup.py / setup.cfg            # the Python library (ament_python side)
├── global_planner_plugin.xml       # pluginlib manifest for CrunchAStarPlanner
├── crunch_planners/                # the Python library
│   ├── __init__.py
│   ├── base.py                     # the Planner interface + Path type
│   ├── grid.py                     # the occupancy-grid graph model (neighbors, costs)
│   ├── astar.py                    # A*, weighted A*, Dijkstra (one search, parameterized)
│   ├── rrt_star.py                 # RRT and RRT* with choose_parent + rewire
│   └── bench.py                    # the benchmark + self-check harness
├── include/crunch_planners/
│   └── crunch_astar_planner.hpp
├── src/
│   └── crunch_astar_planner.cpp    # the nav2_core::GlobalPlanner adapter
└── test/
    ├── test_astar.py               # asserts A* == Dijkstra length; admissibility
    └── test_rrt_star.py            # asserts RRT* improves with samples
```

---

## Deliverable 1 — the Python library

Clean the exercises into a library with one interface:

```python
# crunch_planners/base.py
from __future__ import annotations
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class PlanResult:
    path: list            # list of (row, col) cells, or (x, y) points
    length: float         # path cost
    work: int             # nodes expanded (grid) or samples used (sampling)
    runtime_ms: float
    success: bool


class Planner(ABC):
    """Every planner implements this. The benchmark and the Nav2 plugin call plan()."""

    @abstractmethod
    def plan(self, grid_or_space, start, goal) -> PlanResult:
        ...
```

`astar.py` implements `AStarPlanner(eps=1.0)` (eps=1 is A*, eps>1 is weighted A*, and a `DijkstraPlanner` is `AStarPlanner` with the heuristic disabled). `rrt_star.py` implements `RRTStarPlanner(samples, step, goal_bias)`. Each returns a `PlanResult`. Reuse the exercise code — but route it all through `plan()`.

> **The invariant the tests enforce:** `test_astar.py` asserts `AStarPlanner().plan(...).length == DijkstraPlanner().plan(...).length` and that A* expands fewer nodes. `test_rrt_star.py` asserts RRT* at `2N` samples is no worse than at `N`. These are the exercise self-checks, promoted to CI.

---

## Deliverable 2 — the benchmark harness

`bench.py` runs any registered planner on any map and produces the bake-off table:

```bash
python3 -m crunch_planners.bench --maps open maze corridors --trials 20 --seed 7
```

It must:

- Run each planner over `--trials` randomized start/goal pairs per map.
- Report path length (mean ± std), work (nodes/samples), and runtime (**mean and p95** — the tail is a safety property, Lecture 2 §3.1).
- Self-check the invariants and exit non-zero if any planner violates them (so the benchmark doubles as a regression gate).
- Emit a markdown table you can paste into a design review.

This is the Challenge's bake-off, but as reusable code instead of a one-off script — so every future planner you add gets benchmarked the same way.

---

## Deliverable 3 — the Nav2 global-planner plugin

A C++ `nav2_core::GlobalPlanner` that runs your A* over the live costmap. The interface (from `nav2_core/global_planner.hpp`):

```cpp
// crunch_astar_planner.hpp (spine)
#ifndef CRUNCH_PLANNERS__CRUNCH_ASTAR_PLANNER_HPP_
#define CRUNCH_PLANNERS__CRUNCH_ASTAR_PLANNER_HPP_

#include <memory>
#include <string>
#include "nav2_core/global_planner.hpp"
#include "nav2_util/lifecycle_node.hpp"
#include "nav2_costmap_2d/costmap_2d_ros.hpp"
#include "nav_msgs/msg/path.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"

namespace crunch_planners
{
class CrunchAStarPlanner : public nav2_core::GlobalPlanner
{
public:
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;
  void cleanup() override;
  void activate() override;
  void deactivate() override;

  // The one method that matters: run A* on the costmap, return a Path.
  nav_msgs::msg::Path createPlan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal) override;

private:
  nav2_costmap_2d::Costmap2D * costmap_{nullptr};
  std::string global_frame_, name_;
  double eps_{1.0};   // weighted-A* knob, declared as a parameter
};
}  // namespace crunch_planners
#endif
```

In `createPlan`, you: read the costmap into your A* grid model (each cell's cost from `costmap_->getCost(mx, my)`, lethal = `LETHAL_OBSTACLE`), convert start/goal world coords to cells with `costmap_->worldToMap`, run A*, convert the cell path back to world coords with `mapToWorld`, and fill a `nav_msgs::msg::Path`. Export it:

```cpp
PLUGINLIB_EXPORT_CLASS(crunch_planners::CrunchAStarPlanner, nav2_core::GlobalPlanner)
```

```xml
<!-- global_planner_plugin.xml -->
<library path="crunch_planners_global_planner">
  <class type="crunch_planners::CrunchAStarPlanner" base_class_type="nav2_core::GlobalPlanner">
    <description>A* over the global costmap, with a weighted-A* eps parameter.</description>
  </class>
</library>
```

```yaml
planner_server:
  ros__parameters:
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "crunch_planners/CrunchAStarPlanner"
      eps: 1.0
```

Restart Nav2, send a goal, and your planner produces the `/plan`. Now you can A/B it against `NavfnPlanner` on the real robot — the closing-the-loop moment.

---

## Rules

- **You may** read the Nav2 docs, the `nav2_core::GlobalPlanner` source, the NavFn planner source, and your own exercise code.
- **You must not** call an external planning library (OMPL, networkx) — the planners are *yours*. (You may use `numpy`/`heapq`.)
- **You must not** duplicate the search logic between the Python library and the C++ plugin's *algorithm* — the C++ plugin reimplements A* in C++ (it must, to run in-process), but the *behavior* must match the Python library, verified by feeding both the same small grid and comparing path length.
- C++17 / `rclcpp` for the plugin; Python 3.12 for the library. Jazzy + Nav2.
- The benchmark must exit non-zero on any invariant violation.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-18-crunch-planners-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_planners` succeeds (Python library + C++ plugin).
- [ ] `colcon test --packages-select crunch_planners` passes, including `test_astar` (A* == Dijkstra length, fewer nodes) and `test_rrt_star` (improves with samples).
- [ ] `python3 -m crunch_planners.bench --maps open maze corridors --trials 20` prints the bake-off table and exits `0`.
- [ ] The Nav2 plugin loads: `planner_plugins: ["GridBased"]` → `crunch_planners/CrunchAStarPlanner`, the stack reaches `active [3]`, and a goal produces a `/plan`.
- [ ] You demonstrate (in the README) that your plugin's `/plan` length matches `NavfnPlanner`'s within a few percent on the same goal — proving your A* is correct *in the production stack*, not just in a script.
- [ ] You confirm the C++ plugin and the Python library agree on path length for a shared small test grid.
- [ ] A `README.md` with the bake-off table, the plugin swap instructions, and a paragraph on the planner-selection taste test.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Library correctness** | 25 | A*, weighted A*, Dijkstra, RRT* all correct behind one `Planner` interface; invariants hold. |
| **Benchmark & self-check** | 20 | Reports length/work/runtime with **p95**; self-checks every planner; non-zero exit on violation. |
| **Nav2 plugin correctness** | 25 | `CrunchAStarPlanner` implements `GlobalPlanner`; reads the costmap correctly (lethal handling, world↔map); produces a valid `/plan`; stack reaches `active`. |
| **Cross-validation** | 15 | Plugin `/plan` length matches NavFn within a few percent; C++ and Python agree on a shared grid. |
| **Tests & hygiene** | 10 | `test_astar` + `test_rrt_star` green; clean CMake/setup; no `build/`/`install/` checked in. |
| **Docs** | 5 | Clear README, bake-off table included, taste-test paragraph. |

**90+** is portfolio-grade and ready to fold into Week 24. **70–89** works but has a rough edge (the plugin needs a manual nudge, or the C++/Python parity isn't shown). **Below 70** means a planner is incorrect — run the self-checks and fix the failing invariant first.

---

## Stretch goals

- **Hybrid-A\* lite.** Add a minimal `(x, y, θ)` Hybrid-A* with a Dubins steering function to the library, and show it produces turning-radius-respecting paths on a corridor map — your own version of what SMAC does.
- **Anytime weighted A\*.** Make the planner return a quick weighted-A* path immediately, then refine toward optimal if time remains, exposing a `deadline_ms`. This is the runtime-as-safety mitigation from the homework, productized.
- **Plug RRT* into Nav2 too.** Write a second plugin wrapping RRT* (note: it's a poor fit for a 2D ground costmap — A* dominates there — but doing it teaches you why, and sets up the manipulation planners in Week 23).
- **CI job.** A GitHub Actions workflow that builds the package, runs `colcon test`, and runs the benchmark in a headless container. Green check on every push.

---

## How this connects to the rest of C24

- **Week 19 (behavior trees)** — the BT's `ComputePathToPose` leaf calls a global planner; your plugin can be the one it calls, and the planner-selection instinct decides which.
- **Week 23 (MoveIt2 / OMPL)** — your hand-rolled RRT* is exactly what OMPL does for the arm; you'll recognize RRT-Connect and BIT* immediately.
- **Week 24 (Phase 3 integration)** — your global planner is one component in the combined Nav2 + MoveIt2 graph, and the review grades whether your planner choice (and its latency fail-safe) is justified. This mini-project is that justification, built six weeks early. Push it, keep the repo, plug it into Week 24.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
