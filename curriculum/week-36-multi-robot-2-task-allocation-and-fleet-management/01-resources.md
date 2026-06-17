# Week 36 — Resources

Every resource here is **free**. Open-RMF is open source (Apache-2.0) and its docs are public. The MRTA taxonomy and auction papers are published openly (arXiv or author PDFs). `scipy` and `numpy` are open. No paywalled books are linked.

Where a link is versioned, the Jazzy / current Open-RMF URL is given. Open-RMF moves faster than ROS distros; the architectural concepts are stable across releases, but double-check package names against your installed version with `ros2 pkg list | grep rmf`.

## Required reading (work it into your week)

- **Open-RMF documentation — overview and concepts** — start here Monday, return Wednesday:
  <https://osrf.github.io/ros2multirobotbook/intro.html>
- **The ROS 2 Multi-Robot Book (the canonical RMF reference)** — the chapters on the traffic schedule, fleet adapters, and task dispatch:
  <https://osrf.github.io/ros2multirobotbook/>
- **Gerkey & Matarić, "A Formal Analysis and Taxonomy of Task Allocation in Multi-Robot Systems" (IJRR 2004)** — the ST-SR-IA / ST-SR-TA / MT-MR taxonomy everyone still cites. Read §2–§4:
  <https://journals.sagepub.com/doi/10.1177/0278364904045564> (author PDF widely mirrored; search the title)
- **`scipy.optimize.linear_sum_assignment`** — the Hungarian solver you'll use, with the cost-matrix convention spelled out:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html>
- **Open-RMF `rmf_demos`** — the reference fleet bring-up you will adapt; read the office and airport launch files:
  <https://github.com/open-rmf/rmf_demos>

## The papers (skim, don't memorize)

You will not read these cover to cover. But the vocabulary — "SSI auction," "regret-based bidding," "deconfliction" — comes from here.

- **Kuhn, "The Hungarian Method for the Assignment Problem" (1955)** — the original; mostly of historical interest, but the cost-matrix formulation is exactly what you'll code:
  <https://onlinelibrary.wiley.com/doi/10.1002/nav.3800020109>
- **Lagoudakis et al., "Auction-Based Multi-Robot Routing" (RSS 2005)** — the sequential-single-item (SSI) auction and its bounded sub-optimality:
  <https://www.roboticsproceedings.org/rss01/p45.html>
- **Dias et al., "Market-Based Multirobot Coordination: A Survey and Analysis" (2006)** — the market metaphor, the auctioneer/bidder roles, and when markets beat central solvers:
  <https://www.ri.cmu.edu/pub_files/pub4/dias_m_bernardine_2006_1/dias_m_bernardine_2006_1.pdf>
- **Khamis, Hussein, Elmogy, "Multi-robot Task Allocation: A Review of the State-of-the-Art" (2015)** — a modern survey that maps the taxonomy onto real systems:
  <https://link.springer.com/chapter/10.1007/978-3-319-18299-5_2>

## Open-RMF docs and source (the ones you'll have open all week)

- **`rmf_traffic` — the schedule and negotiation core**:
  <https://github.com/open-rmf/rmf_traffic>
- **`rmf_task` — the dispatcher, bidding, and task lifecycle**:
  <https://github.com/open-rmf/rmf_task>
- **`rmf_ros2` (fleet adapters, `EasyFullControl`, the schedule node)**:
  <https://github.com/open-rmf/rmf_ros2>
- **`rmf_fleet_adapter_python` — write a fleet adapter in Python**:
  <https://github.com/open-rmf/rmf_ros2/tree/main/rmf_fleet_adapter_python>
- **`rmf_api_msgs` — the task-request and fleet-state schemas (JSON over the API server)**:
  <https://github.com/open-rmf/rmf_api_msgs>
- **`rmf_traffic_editor` / `rmf_building_map_tools` — author the nav graph and building map**:
  <https://github.com/open-rmf/rmf_traffic_editor>

## Install and run

- **Open-RMF install (binary, recommended for this week)** — the `ros-jazzy-rmf-*` apt packages:
  <https://github.com/open-rmf/rmf>
- **`rmf_demos` quick start** — `ros2 launch rmf_demos office.launch.xml`:
  <https://github.com/open-rmf/rmf_demos#readme>
- **Submitting a task via the API** — `dispatch_patrol`, `dispatch_delivery` CLI tools that POST to the API server:
  <https://github.com/open-rmf/rmf_demos/tree/main/rmf_demos_tasks>

## How-to / background

- **Nav2 + RMF integration** — how a Nav2-driven robot becomes an RMF fleet adapter:
  <https://osrf.github.io/ros2multirobotbook/integration_nav2.html>
- **RMF fleet adapter tutorial (full control)** — `EasyFullControl`, state reporting, command consumption:
  <https://osrf.github.io/ros2multirobotbook/integration_fleets.html>
- **The traffic schedule and negotiation explained**:
  <https://osrf.github.io/ros2multirobotbook/traffic-management.html>

## Tools you'll use this week

- **`scipy.optimize.linear_sum_assignment`** — the Hungarian solver. `pip install scipy` (you have it from Phase 2).
- **`ros2 launch rmf_demos office.launch.xml`** — the reference two-fleet world.
- **`dispatch_delivery` / `dispatch_patrol`** — submit tasks to the running fleet via the API server.
- **`ros2 topic echo /fleet_states`** — watch every robot's RMF-reported state (mode, battery, location, task).
- **`rmf_api_server`** websocket — the JSON gateway; the same data a web dashboard consumes.
- **`ros2 node list | grep rmf`** — confirm the schedule node, dispatcher, and each fleet adapter are up.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **MRTA** | Multi-Robot Task Allocation — the who-does-what problem. |
| **ST-SR-IA** | Single-Task robots, Single-Robot tasks, Instantaneous Assignment — the simplest class; an assignment problem. |
| **ST-SR-TA** | Same, but Time-extended Assignment — you also schedule *when*, not just *who*. |
| **Cost matrix** | An N×M matrix where `C[i][j]` is robot `i`'s cost to do task `j` (often travel time/distance). |
| **Hungarian algorithm** | Kuhn–Munkres; finds the minimum-cost perfect assignment in O(n³). Optimal. |
| **Greedy `argmin`** | Assign each task to its cheapest free robot in turn. Fast, *not* optimal. |
| **Auction / market** | A distributed allocator: tasks are auctioned, robots bid their cost, lowest bid wins. |
| **SSI auction** | Sequential Single-Item auction — auction one task at a time, winner re-bids on the rest. Near-optimal, cheap. |
| **Open-RMF** | The open-source Robotics Middleware Framework: a fleet manager for heterogeneous robots. |
| **Fleet adapter** | The bridge between RMF and a specific robot kind; reports state, consumes nav commands. |
| **Full control** | An adapter category where RMF plans paths and commands the robot directly (via Nav2). |
| **Traffic light** | An adapter category where the robot plans its own path; RMF only grants go/stop at conflicts. |
| **`rmf_traffic`** | The space-time trajectory schedule and the negotiation that deconflicts it. |
| **Negotiation** | When two reserved trajectories conflict, RMF runs a negotiation to decide who yields. |
| **Dispatcher (`rmf_task`)** | Receives task requests, runs the bidding, assigns tasks to fleets. |
| **Heartbeat** | A periodic health/identity message; staleness signals a dead or wedged robot. |

---

*If a link 404s, please open an issue so we can replace it.*
