# Week 35 — Multi-Robot 1: Shared Mapping and Coordination

Welcome to the week your single-robot mental model breaks. Every assumption you have built over thirty-four weeks — one TF tree, one `/map`, one `ROS_DOMAIN_ID`, one clock you implicitly trust — assumed a robot that is alone in the universe. This week there are two. By Friday you will run two diff-drive robots in one Gz Sim world, each building its own map under its own namespace, and a third process that periodically merges those two maps into a shared occupancy grid that both robots can consult. You will do it without the namespaces colliding, without discovery cross-talk, and without pretending the network is instantaneous.

The single idea to carry in before you read another line: **two robots are not one robot, twice.** They share state — a map, each other's poses, a notion of who owns which corridor — and they share it *under uncertainty and latency*. Robot A's belief about where Robot B is, is always a little stale and a little wrong. Every multi-robot bug you will ever file is downstream of forgetting that. Coordination is not a robotics problem bolted onto your stack; it is a **distributed-systems problem** wearing a LiDAR. The map-merge you build this week is, underneath, a conflict-resolution problem between two estimators that disagree about the same physical wall.

We assume your **week-7 `slam_toolbox`** setup still works on a single robot, that you can bring up a diff-drive robot in Gz Sim from your week-8 `crunchbot_bringup` package, and that your QoS literacy from week 5 is intact — because namespaced multi-robot graphs are where a forgotten `TRANSIENT_LOCAL` on a latched map costs you an entire afternoon, two robots deep.

## Learning objectives

By the end of this week, you will be able to:

- **Namespace** a complete robot stack — nodes, topics, TF frames, and parameters — so that two instances of the *same* launch file coexist in one graph with zero collisions, and explain the difference between a topic namespace and a TF frame prefix.
- **Isolate** robot graphs with `ROS_DOMAIN_ID` and `ROS_AUTOMATIC_DISCOVERY_RANGE`, and decide deliberately when two robots should share a domain (they must coordinate) versus when they should not (independent fleets on one LAN).
- **Run** independent `slam_toolbox` instances per robot, each producing a namespaced `/<robot>/map`, and reason about why each robot's `map` frame is its *own* origin, not a shared world frame.
- **Merge** two occupancy grids into one shared `/shared_map` given a known (or estimated) relative transform between the two robots' map frames, handling resolution, origin offset, and the free/occupied/unknown cell-fusion rules correctly.
- **Publish** the inter-robot transform that ties `robotA/map` and `robotB/map` into a common frame, and explain why a wrong or stale relative transform produces a "double-walled" merged map.
- **Characterize** the latency-bounded-coordination problem: why you never block one robot on a synchronous call to another, and how a periodic, best-effort, eventually-consistent map exchange beats a tight RPC.
- **Survey** the distributed-SLAM landscape of 2026 — multi-robot Cartographer, Kimera-Multi, the place-recognition / inter-robot-loop-closure problem — well enough to know what you are *not* building this week and why a real fleet needs it.

## Prerequisites

This week assumes you have completed **C24 weeks 1–34**, or have equivalent ROS2 + SLAM fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or container / WSL2). `ros2 --version` works; you can `colcon build` a workspace.
- Your **week-7 `slam_toolbox`** mapping setup runs on a single robot and saves a map.
- Your **week-8 `crunchbot_bringup`** package launches a single diff-drive robot in Gz Sim with a clean TF tree, and imports `crunchbot_qos` for its profiles.
- You are fluent with **QoS** (week 5): you know that `/map` is `RELIABLE` + `TRANSIENT_LOCAL`, and you can read `ros2 topic info -v` to confirm two endpoints agree.
- You can read and write a **launch file** that takes arguments, sets a namespace, and remaps topics — the week-8 launch hygiene.

You do **not** need prior distributed-systems coursework. We teach the minimum vocabulary — eventual consistency, latency bounds, conflict resolution — inline, exactly where the robot forces it on you.

## Topics covered

- **Namespacing a full stack**: the `namespace=` argument to `Node` and `GroupAction`/`PushRosNamespace` in launch; relative vs. absolute topic names (`scan` vs. `/scan` vs. `/robotA/scan`); why a leading slash defeats namespacing; the `tf_prefix` problem and why ROS2 solved it with frame *prefixing* in the broadcaster, not a global parameter.
- **The two `map` frames problem**: each robot's `slam_toolbox` defines `map` as the origin of *that robot's* first scan; two robots have two unrelated `map` frames; the shared map needs a third frame (`world` or `shared_map`) and a transform from each robot's `map` into it.
- **Discovery isolation and sharing**: `ROS_DOMAIN_ID` as the coarse isolation knob; `ROS_AUTOMATIC_DISCOVERY_RANGE` for localhost-only experiments; when coordinating robots must share a domain, and the partitioning options (DDS partitions, namespaces) when they share a domain but not all topics.
- **Occupancy-grid merging**: the `nav_msgs/OccupancyGrid` representation (resolution, width, height, origin, row-major `int8[]` data with 0/100/-1 semantics); transforming one grid into another's frame; the cell-fusion rule (occupied wins over free wins over unknown) and why naive averaging produces gray mush.
- **The inter-robot transform**: assuming a known relative pose (the "robots started at known offsets" simplification we use this week) versus estimating it from a shared landmark or an inter-robot loop closure (what Kimera-Multi does); publishing `world -> robotA/map` and `world -> robotB/map` as static or slowly-updated transforms.
- **Latency-bounded coordination**: why an inter-robot call is never on the critical path; the periodic-exchange pattern (each robot publishes its map on a latched topic; a merger node consumes both at its own cadence); eventual consistency as the only honest consistency model for a robot fleet on Wi-Fi.
- **The distributed-SLAM landscape (survey)**: multi-robot Cartographer's grid-merge approach; Kimera-Multi's distributed pose-graph optimization with inter-robot loop closures; the place-recognition bottleneck; why true distributed SLAM is a phase-6-and-beyond topic and the grid-merge you build is the honest, deployable 80%.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Namespacing a full stack; two `map` frames; discovery  |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Two robots in one world; per-robot SLAM exercises       |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Occupancy-grid merge math; the inter-robot transform   |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Latency-bounded coordination; distributed-SLAM survey   |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Wiring the merger; live three-namespace rviz2          |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, write-up polish                          |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The multi-robot ROS2 docs, namespacing guides, map-merge packages, and the distributed-SLAM papers worth your time |
| [lecture-notes/01-namespacing-discovery-and-two-map-frames.md](./lecture-notes/01-namespacing-discovery-and-two-map-frames.md) | Namespacing a full stack, discovery isolation, and the two-`map`-frames problem |
| [lecture-notes/02-shared-mapping-merging-and-coordination.md](./lecture-notes/02-shared-mapping-merging-and-coordination.md) | Occupancy-grid merging, the inter-robot transform, latency-bounded coordination, and the distributed-SLAM survey |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-namespaced-bringup.md](./exercises/exercise-01-namespaced-bringup.md) | Bring up two robots from one launch file under `robotA`/`robotB` namespaces; prove zero topic and TF collisions |
| [exercises/exercise-02-merge-two-grids.py](./exercises/exercise-02-merge-two-grids.py) | Merge two `OccupancyGrid`s with a known relative transform into one `/shared_map`, with correct cell fusion |
| [exercises/exercise-03-stale-transform-probe.py](./exercises/exercise-03-stale-transform-probe.py) | Inject a wrong/stale inter-robot transform and watch the merged map "double-wall"; quantify the error |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-two-robot-shared-map.md](./challenges/challenge-01-two-robot-shared-map.md) | Stand up the full two-robot-plus-merger system and recover when one robot's map frame drifts |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the namespaced-bring-up write-up and the merge-quality report |
| [mini-project/README.md](./mini-project/README.md) | The `crunchbot_multi` package: namespaced two-robot bring-up + a live map-merger node + rviz2 layout |

## The "both maps, one frame" promise

C24 uses a recurring marker for every multi-robot exercise that ends in two robots genuinely sharing state. For this week it is the moment `ros2 topic echo /shared_map --field info` shows one grid whose extent covers *both* robots' explored area, and rviz2 shows the two robots' footprints inside that single grid, in the same frame:

```
$ ros2 run tf2_ros tf2_echo world robotA/base_link
At time ...
- Translation: [ 1.20,  0.50,  0.00]
- Rotation: in Quaternion [...]
$ ros2 run tf2_ros tf2_echo world robotB/base_link
At time ...
- Translation: [-2.10,  3.40,  0.00]
- Rotation: in Quaternion [...]
```

If both robots resolve into the *same* `world` frame and the `/shared_map` covers both, you are done. If `tf2_echo world robotB/base_link` throws `LookupException`, your inter-robot transform isn't published and the merge is a lie — two grids painted on top of each other with no shared origin. The point of the week is to make that single `world` frame ordinary, and to make a *missing* one loud instead of a silently-wrong merge.

## Stretch goals

If you finish the regular work early and want to push further:

- Replace the *known* relative transform with an **estimated** one: have both robots drive past a shared AprilTag, detect it in each robot's frame, and solve for `robotA/map -> robotB/map` from the two detections. This is the poor man's inter-robot loop closure.
- Run the open-source **`m-explore-ros2` `multirobot_map_merge`** node against your two `slam_toolbox` instances and compare its merged grid to your hand-rolled merger. Note where its feature-based alignment beats your known-transform assumption and where it fails.
- Scale to **three** robots. The merge math generalizes, but the discovery traffic and the rviz2 layout do not — feel where N² discovery starts to bite and why the week-5 discovery-server pattern returns here.
- Read the **Kimera-Multi** paper (Tian et al.) until you can explain, in two sentences, how it does *distributed* pose-graph optimization without a central server, and why inter-robot loop closures are the hard part.

## Up next

Week 36 takes the shared-state machinery you built here and asks the next question: now that two robots share a map, *who does what?* Task allocation — auction-based, market-based, optimization-based — and fleet management with Open-RMF. The namespacing and the latency-bounded-coordination discipline from this week are load-bearing for it. Push your mini-project before you start.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
