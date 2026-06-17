# Week 18 — Resources

Every resource here is **free** wherever possible. The planning references are open lecture notes and open-access papers; the Nav2 planner docs are open; the textbook chapters linked are the openly-available ones (Steven LaValle's *Planning Algorithms* is free online in full). No paywalled books are linked.

The algorithms this week — Dijkstra, A*, RRT* — are decades stable. The papers are the original sources and worth reading once; the Nav2 docs version with the distro but the planner concepts don't move.

## Required reading (work it into your week)

- **LaValle, *Planning Algorithms*** — the free, complete textbook. Chapter 2 (discrete search: Dijkstra, A*) and Chapter 5 (sampling-based: RRT) are this week:
  <http://lavalle.pl/planning/>
- **Amit Patel's "Introduction to A\*"** (Red Blob Games) — the best visual A* explainer on the internet, with interactive diagrams. Read it before you write a line of A*:
  <https://www.redblobgames.com/pathfinding/a-star/introduction.html>
- **Red Blob Games — "Implementation of A\*"** — the priority queue, the heuristic, the reconstruct-path step, in clean pseudocode:
  <https://www.redblobgames.com/pathfinding/a-star/implementation.html>
- **Nav2 — Planner server configuration** — the planner plugins you compare against (`NavfnPlanner`, `SmacPlannerHybrid`, `SmacPlanner2D`, `ThetaStarPlanner`):
  <https://docs.nav2.org/configuration/packages/configuring-planner-server.html>
- **Nav2 — SMAC planner** — the Hybrid-A* you drop in for the Ackermann comparison:
  <https://docs.nav2.org/configuration/packages/configuring-smac-planner.html>

## The canonical papers (read once, cite forever)

- **Hart, Nilsson, Raphael (1968) — "A Formal Basis for the Heuristic Determination of Minimum Cost Paths"** — the original A* paper, where admissibility is defined:
  <https://ieeexplore.ieee.org/document/4082128>
- **Koenig & Likhachev (2002) — "D\* Lite"** — incremental replanning under changing costs:
  <http://idm-lab.org/bib/abstracts/papers/aaai02b.pdf>
- **LaValle (1998) — "Rapidly-Exploring Random Trees: A New Tool for Path Planning"** — the original RRT:
  <http://lavalle.pl/papers/Lav98c.pdf>
- **Karaman & Frazzoli (2011) — "Sampling-based Algorithms for Optimal Motion Planning"** — RRT* and the asymptotic-optimality proof; the rewiring step lives here:
  <https://journals.sagepub.com/doi/10.1177/0278364911406761>
- **Dolgov et al. (2010) — "Path Planning for Autonomous Vehicles in Unknown Semi-structured Environments"** — the Hybrid-A* paper from the DARPA Urban Challenge:
  <https://ai.stanford.edu/~ddolgov/papers/dolgov_gpp_stair08.pdf>

## API and library references

- **Python `heapq`** — the binary-heap priority queue your A*/Dijkstra open set uses:
  <https://docs.python.org/3/library/heapq.html>
- **`numpy`** — the grid as an array; vectorized collision checks for RRT*:
  <https://numpy.org/doc/stable/>
- **`matplotlib`** — visualize the grid, the expanded nodes, and the RRT* tree:
  <https://matplotlib.org/stable/users/index.html>
- **OMPL (Open Motion Planning Library)** — the sampling-based planner library MoveIt2 uses (read its RRT*/BIT* for reference; you implement your own this week):
  <https://ompl.kavrakilab.org/>
- **`nav2_core::GlobalPlanner`** — the interface your mini-project plugin implements:
  <https://github.com/ros-navigation/navigation2/blob/main/nav2_core/include/nav2_core/global_planner.hpp>

## Visualizations and interactive tools (build intuition fast)

- **PathFinding.js** — watch A*, Dijkstra, and others expand on a grid, side by side, in the browser:
  <https://qiao.github.io/PathFinding.js/visual/>
- **RRT visualization (various)** — search "RRT* visualization" for the canonical animations of the tree exploring and rewiring; LaValle's site hosts the originals:
  <http://lavalle.pl/rrt/>
- **Theta\* and any-angle planning** — the Nav2 `ThetaStarPlanner` docs and the original any-angle papers for the stretch goal:
  <https://docs.nav2.org/configuration/packages/configuring-thetastar.html>

## Talks worth your time (free, no signup)

- **ROSCon — Nav2 planner deep-dives** — Steve Macenski's talks on the SMAC planners and Nav2 planning internals; the OSRF posts every talk free:
  <https://roscon.ros.org/>
- **MIT 6.881 / Russ Tedrake — Robotic Manipulation** (the planning lectures) — free course notes covering sampling-based planning for arms:
  <https://manipulation.csail.mit.edu/>

## Tools you'll use this week

- **`python3` + `heapq` + `numpy` + `matplotlib`** — the hand-rolled planners and their visualization.
- **`cProfile`** — `python3 -m cProfile -s cumtime your_planner.py` to find the hot line (runtime is a safety property).
- **Nav2 `planner_server`** — swap `GridBased.plugin` between `NavfnPlanner`, `SmacPlanner2D`, and `SmacPlannerHybrid` to compare against your own.
- **`ros2 topic echo /plan`** — the path Nav2's planner produced, to diff against yours.
- **rviz2** — visualize the planned path and the costmap it searched.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Open set** | The frontier: nodes discovered but not yet expanded. A priority queue keyed on `f`. |
| **Closed set** | Nodes already expanded; never revisited (with a consistent heuristic). |
| **`g(n)`** | Cost of the best-known path from start to node `n`. |
| **`h(n)`** | Heuristic estimate of the cost from `n` to the goal. |
| **`f(n)`** | `g(n) + h(n)` — A*'s priority. Dijkstra is A* with `h = 0`. |
| **Admissible** | `h(n)` never *over*-estimates the true cost-to-go. Guarantees A* optimality. |
| **Consistent** | `h(n) ≤ cost(n, n') + h(n')` for every edge. Stronger than admissible; lets you never re-open a closed node. |
| **Weighted A\*** | `f = g + ε·h`, ε > 1. Faster, but the path can be up to ε× longer than optimal. |
| **D\* Lite** | Incremental replanner: reuses prior search when only a few cells change. |
| **State lattice** | A graph of pre-computed motion primitives that respect a vehicle's kinematics. |
| **Hybrid-A\*** | A* over continuous (x, y, heading) with a discrete control set; respects turning radius. |
| **Nonholonomic** | A vehicle whose velocity is constrained (a car can't move sideways). Needs lattice/Hybrid-A*. |
| **RRT** | Rapidly-exploring Random Tree: sample, find nearest, steer toward it, extend. Probabilistically complete. |
| **RRT\*** | RRT + `choose_parent` + `rewire`. Asymptotically optimal — the path improves as samples grow. |
| **Steering function** | Given two states, produce a feasible local path between them (a straight line in holonomic 2D; a Dubins curve for a car). |
| **Configuration space (C-space)** | The space of all robot configurations (joint angles for an arm). Sampling-based planners search here. |

---

*If a link 404s, please open an issue so we can replace it.*
