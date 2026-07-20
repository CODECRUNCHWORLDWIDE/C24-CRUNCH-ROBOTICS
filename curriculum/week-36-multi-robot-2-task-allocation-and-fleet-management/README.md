# Week 36 — Multi-Robot 2: Task Allocation and Fleet Management

Last week you got two robots to *share a map* without colliding. That was the easy half. This week you face the question every warehouse, hospital, and last-mile company eventually has to answer: **given a fleet of N robots and a queue of M tasks, who does what, in what order, and what happens when one of them dies mid-job?** By Friday you will be able to assign tasks optimally with the Hungarian algorithm, run a live auction when the world keeps changing, stand up the open-source fleet manager that the field actually uses in 2026 — **Open-RMF** — and prove your fleet reallocates a stalled robot's work without a human in the loop.

We assume Week 35 is behind you: two diff-drive robots spawn in Gz Sim under separate namespaces, each runs its own SLAM, and you can merge their maps onto a third namespace. If that bring-up is broken, fix it first — every exercise this week runs a multi-robot graph, and a flaky namespace is the worst possible thing to debug *on top of* a flaky fleet manager.

The one thing to internalize before you read another line: **task allocation is an optimization problem wearing a robotics costume, and fleet management is a distributed-systems problem wearing a robotics costume.** The robots are almost incidental. A fleet manager is a scheduler, a conflict resolver, and a failure detector — the same three jobs a Kubernetes control plane does, except the pods have wheels and a narrow corridor they all want to drive through at once. If you treat "which robot picks up task 7" as a routing question you'll write `min(distance)` and ship a fleet that deadlocks at the first doorway. If you treat it as an *assignment* problem with a *cost matrix* and a *conflict layer*, you ship something that scales.

This week is where you stop thinking of two robots as one robot, twice, and start thinking of a fleet as a system with its own failure modes.

## Learning objectives

By the end of this week, you will be able to:

- **Formulate** multi-robot task allocation (MRTA) as a cost-matrix assignment problem, and place a given problem in Gerkey & Matarić's taxonomy (ST-SR-IA vs. ST-SR-TA vs. MT-MR, instantaneous vs. time-extended).
- **Implement** the **Hungarian algorithm** (Kuhn–Munkres) for the optimal one-shot assignment of N robots to N tasks, and explain why a greedy `argmin` is *not* optimal and where it fails.
- **Implement** a **market-based / auction** allocator (single-item and sequential-single-item, SSI) that re-bids as tasks arrive and robots drop out — and articulate the optimality-vs-responsiveness trade-off against the Hungarian baseline.
- **Explain** the Open-RMF architecture in 2026 terms: the core (`rmf_traffic`, `rmf_traffic_schedule`), the fleet adapters (full-control vs. traffic-light vs. read-only), the task dispatcher (`rmf_task`), and the API gateway (`rmf_api_server` / `api.web`).
- **Wire** a heterogeneous two-robot fleet into Open-RMF with a fleet adapter each, submit delivery tasks through the fleet API, and watch the traffic schedule negotiate a shared corridor.
- **Diagnose** a fleet-level conflict: read the `rmf_traffic` schedule, identify a negotiation at a narrow passage, and explain how the scheduler resolves it (who yields, who proceeds, and why).
- **Inject** a failure — a robot that stalls mid-task — and verify the dispatcher *reallocates* the orphaned task to a healthy robot within a bounded time, with the event observable on the API/heartbeat.
- **Design** a fleet heartbeat schema (the capstone's `/fleet/heartbeat` at 1 Hz) carrying identity, capabilities, and health, and reason about its QoS the way Week 5 taught you.

## Prerequisites

This week assumes you have completed **C24 weeks 1–35**, or have equivalent ROS2 + multi-robot fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works; `ros2 doctor` runs clean.
- The **Week 35 two-robot bring-up**: two diff-drive robots in Gz Sim under namespaces (`/robot1`, `/robot2`), each running SLAM, with a working map merge. You can drive each independently with `ros2 topic pub /robot1/cmd_vel ...`.
- **Nav2** fluency from Phase 3 (weeks 17–24): you can send a `NavigateToPose` goal and read a costmap. Open-RMF drives the base *through* Nav2, so a broken Nav2 is a broken fleet.
- **QoS literacy from Week 5.** The heartbeat and fleet-state topics have a *class* (Lecture 1's taste test) and you will be expected to justify their profiles.
- Comfort with `scipy` and `numpy` — the assignment exercises are pure Python before they're ROS2 nodes.

You do **not** need prior Open-RMF experience. We start at the assignment problem on paper and build up to a running fleet. If you have only ever sent one robot one goal, this is the week that scales the mental model to N.

## Topics covered

- **The MRTA problem and its taxonomy.** Single-task robots / single-robot tasks / instantaneous assignment (ST-SR-IA) vs. time-extended (ST-SR-TA); the cost matrix; the difference between *who* does a task and *when*.
- **Optimal assignment: the Hungarian algorithm.** Why greedy `argmin` is sub-optimal, the cost-matrix formulation, `scipy.optimize.linear_sum_assignment`, rectangular (N≠M) padding, and the O(n³) complexity that bounds how big a one-shot solve can be.
- **Market-based allocation.** Auctions as a distributed alternative to a central solver; single-item auctions; **sequential single-item (SSI)** auctions and why they recover most of the optimality of a combinatorial auction at a fraction of the cost; bidding rules; re-auctioning on task arrival and robot dropout.
- **The Open-RMF stack (2026).** `rmf_traffic` (the schedule + negotiation), `rmf_traffic_schedule` node, `rmf_task` (the dispatcher and bidding), `rmf_fleet_adapter`, the three fleet-adapter control categories (full-control, traffic-light, read-only), `nav_graphs`, and the `rmf_api_server` web gateway.
- **Fleet adapters.** What a fleet adapter is, how `EasyFullControl` plugs a Nav2-driven robot into RMF, how the adapter reports robot state and consumes navigation commands, and what a heterogeneous fleet (different robot kinds, different adapters) looks like.
- **Conflict resolution and the traffic schedule.** How `rmf_traffic` represents reserved space-time trajectories, how a narrow-corridor conflict triggers a *negotiation*, the deconfliction outcome (yield / reroute / wait), and how to read it.
- **Failure handling and reallocation.** Task lifecycle (queued → assigned → underway → completed / failed); how a stalled or lost robot is detected; how the dispatcher re-bids the orphaned task; the reallocation drill and its time bound.
- **The fleet heartbeat.** Designing the `/fleet/heartbeat` schema (identity, capabilities, battery, nav state, current task), its 1 Hz cadence, its `MANUAL_BY_TOPIC` liveliness, and how a fleet manager uses it to detect a wedged-but-not-dead robot (the Week 5 lesson, applied).

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | MRTA taxonomy; cost matrices; the Hungarian algorithm |  2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | Market/auction allocation; SSI; the optimality trade-off |  1.5h |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Open-RMF architecture; fleet adapters; bring-up    |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Traffic schedule; corridor negotiation; reallocation |  1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Heartbeat schema; the reallocation drill           |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                             |    0h    |    0h     |     0h     |    0h     |   0h     |     2h       |    0h      |     2h      |
| Sunday    | Quiz, review, drill write-up polish                |    0h    |    0h     |     0h     |    1h     |   0h     |     2h       |    0h      |     3h      |
| **Total** |                                                    | **6.5h** | **7h**    | **4h**     | **4h**    | **5h**   | **9h**       | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The Open-RMF docs, the MRTA taxonomy papers, the auction literature, and the talks worth your time |
| [lecture-notes/01-task-allocation-hungarian-and-markets.md](./lecture-notes/01-task-allocation-hungarian-and-markets.md) | The MRTA taxonomy, the Hungarian algorithm, market/auction allocation, and the optimality trade-off |
| [lecture-notes/02-open-rmf-fleet-management-and-reallocation.md](./lecture-notes/02-open-rmf-fleet-management-and-reallocation.md) | The Open-RMF architecture, fleet adapters, the traffic schedule, conflict negotiation, and failure reallocation |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-cost-matrix-on-paper.md](./exercises/exercise-01-cost-matrix-on-paper.md) | Build a cost matrix from robot/task poses, solve it greedily and Hungarian, and prove greedy is sub-optimal |
| [exercises/exercise-02-hungarian-allocator.py](./exercises/exercise-02-hungarian-allocator.py) | A runnable Hungarian allocator node: cost matrix from poses, optimal assignment, rectangular padding |
| [exercises/exercise-03-ssi-auction.py](./exercises/exercise-03-ssi-auction.py) | A sequential-single-item auction allocator that re-bids on task arrival and robot dropout |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-corridor-deadlock.md](./challenges/challenge-01-corridor-deadlock.md) | Make two robots contend for one corridor under your allocator; detect the deadlock and prescribe the deconfliction |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the reallocation-drill write-up |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_fleet` dispatcher: cost-matrix allocation + a heartbeat-driven failure detector + a reallocation drill |

## The "the fleet reallocated" promise

C24 uses a recurring marker for every exercise that ends in a fleet actually recovering from a failure. For this week it is the reallocation event:

```
[dispatcher] task delivery_3 ASSIGNED to robot2
[dispatcher] robot2 heartbeat STALE (last seen 3.1s ago > 2.0s lease)
[dispatcher] task delivery_3 ORPHANED — re-bidding
[dispatcher] task delivery_3 RE-ASSIGNED to robot1 (bid 4.2 < robot3 bid 6.8)
```

If a robot dies and its task sits orphaned forever, your fleet manager is a single point of failure with extra steps. The point of Week 36 is to make that reallocation line *ordinary* — and to make the orphaned-forever case *loud* and *measured* (how many seconds to recover?).

## Stretch goals

If you finish the regular work early and want to push further:

- Implement a **combinatorial auction** (bid on *bundles* of tasks) for a small problem and compare its allocation quality and solve time to SSI. Confirm SSI gets ≥ 90% of the optimal at a fraction of the compute — the reason nobody runs full combinatorial auctions on a live fleet.
- Read the **`rmf_traffic` negotiation** source until you can describe the schedule's space-time trajectory representation and the negotiation rooms: <https://github.com/open-rmf/rmf_traffic>.
- Stand up a **third robot of a different kind** (a different footprint / max speed) and a second fleet adapter, and submit a mixed task batch. Confirm the dispatcher bids across the heterogeneous fleet correctly.
- Wire your `/fleet/heartbeat` into a tiny **Foxglove** panel that turns red when a robot's heartbeat goes stale — a preview of the Week 43 operator dashboard.

## Up next

Week 37 takes the fleet you can now coordinate and asks the next question: **how does a human tell a robot what to do in plain English?** Vision-language models for robotics. The heartbeat schema and the task-lifecycle vocabulary you build this week become the substrate that a language instruction eventually dispatches onto. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
