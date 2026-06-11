# Week 19 — Resources

Every resource here is **free**. BehaviorTree.CPP and Groot 2 are open source (and the docs are open). The Nav2 BT docs are open. The canonical BT textbook (Colledanchise & Ögren) is available as an open-access preprint. No paywalled books are linked.

BehaviorTree.CPP is at major version 4.x as of 2026, and Nav2 on Jazzy uses it. The concepts — ticking, the three statuses, the control nodes, the blackboard — are stable across versions; a few node names changed between BT.CPP 3 and 4 (e.g., `SequenceStar` → `SequenceWithMemory`), so prefer the 4.x docs.

## Required reading (work it into your week)

- **BehaviorTree.CPP — main docs** — the library Nav2 uses; start at "Learn the basics":
  <https://www.behaviortree.dev/docs/learn-the-basics/BT_basics>
- **BehaviorTree.CPP — the node types** ( control, decorator, condition, action) and their semantics:
  <https://www.behaviortree.dev/docs/nodes-library/nodes-library>
- **BehaviorTree.CPP — the blackboard and ports** (passing data between nodes):
  <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_02_basic_ports>
- **Groot 2 — docs** (connect to a live tree, monitor, edit):
  <https://www.behaviortree.dev/groot/>
- **Nav2 — Behavior Trees overview** (the trees you read in Week 17, now as authoring reference):
  <https://docs.nav2.org/behavior_trees/index.html>

## The canonical text (read once, it's short and excellent)

- **Colledanchise & Ögren — *Behavior Trees in Robotics and AI: An Introduction*** — the definitive BT book; the open-access arXiv version is complete:
  <https://arxiv.org/abs/1709.00084>
- **The "BTs vs FSMs" framing** — Chapter 1–2 of the above; the state-explosion argument and the modularity argument live there.

## Reference docs (you'll have these open all week)

- **BehaviorTree.CPP — `StatefulActionNode`** (the base for async actions that return `RUNNING`):
  <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_08_additional_args>
- **BehaviorTree.CPP — reactive vs. sequential control** (`ReactiveSequence` vs `Sequence`):
  <https://www.behaviortree.dev/docs/nodes-library/control-nodes/>
- **BehaviorTree.CPP — XML format** (the tree definition language you author in):
  <https://www.behaviortree.dev/docs/learn-the-basics/xml_format>
- **Nav2 — list of BT nodes** (the Nav2-specific action/condition nodes: `NavigateToPose`, `IsBatteryLow`, `Spin`, ...):
  <https://docs.nav2.org/behavior_trees/overview/nav2_specific_nodes.html>
- **Nav2 — `bt_navigator` config** (how to point it at your own tree XML):
  <https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html>

## API references

- **`BT::BehaviorTreeFactory`** (register nodes, load XML, create the tree):
  <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_01_first_tree>
- **`BT::Groot2Publisher`** (the publisher that lets Groot 2 connect to your live tree):
  <https://www.behaviortree.dev/docs/tutorial-advanced/tutorial_05_subtrees/>
- **`vision_msgs/Detection2DArray`** (the perception type the patrol reacts to):
  <https://github.com/ros-perception/vision_msgs>
- **`nav2_msgs/action/NavigateToPose`** (the action the patrol's nav leaf calls):
  <https://github.com/ros-navigation/navigation2/blob/main/nav2_msgs/action/NavigateToPose.action>

## Tools you'll use this week

- **Groot 2** — `sudo snap install groot2` (or the AppImage). Monitor mode connects to a live tree; Editor mode authors XML.
- **`ros2 run nav2_bt_navigator ...`** — run a tree; or run BT.CPP standalone from a small C++ executable.
- **`BT::Groot2Publisher`** — add it to your tree-runner so Groot 2 can attach (default port 1667).
- **rviz2** — visualize the robot patrolling its waypoints while the tree ticks.
- **`ros2 topic echo`** — watch the perception topic the `IsPersonDetected` condition reads.

## Talks worth your time (free, no signup)

- **"Behavior Trees in robotics" (Ögren / Colledanchise)** — the authors' talks on the theory; search the BT.CPP and ROSCon archives:
  <https://roscon.ros.org/>
- **BehaviorTree.CPP / Davide Faconti talks** — the maintainer's ROSCon talks on BT.CPP and Groot 2 design:
  <https://www.behaviortree.dev/>
- **Nav2 BT deep-dives** (Steve Macenski) — how Nav2 uses BTs for navigation, posted free by the OSRF:
  <https://roscon.ros.org/>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Tick** | The signal sent from the root down the tree each cycle; a node "ticks" when it's evaluated. |
| **`SUCCESS` / `FAILURE` / `RUNNING`** | The three statuses a node returns. `RUNNING` = "not done yet, tick me again." |
| **`Sequence`** | Control node: tick children in order; fail if any fails; succeed if all succeed (logical AND). |
| **`Fallback` / `Selector`** | Control node: tick children in order; succeed if any succeeds; fail if all fail (logical OR). |
| **`Parallel`** | Control node: tick all children; succeed/fail when a threshold of them does. |
| **`ReactiveSequence`** | A `Sequence` that re-ticks earlier children every tick — lets a condition interrupt a running action. |
| **Decorator** | A node with one child that modifies its result or ticking (`Inverter`, `Retry`, `Timeout`, `RateController`). |
| **Condition node** | A leaf that checks something and returns `SUCCESS`/`FAILURE` synchronously (no `RUNNING`). |
| **Action node** | A leaf that *does* something; an async action returns `RUNNING` until it completes. |
| **`StatefulActionNode`** | The BT.CPP base for an async action: `onStart`, `onRunning`, `onHalted`. |
| **Blackboard** | The shared key-value store nodes read/write to pass data (a waypoint, a detection). |
| **Port** | A typed input/output a node declares to read from / write to the blackboard. |
| **BehaviorTree.CPP** | The C++ BT library Nav2 uses; you author trees in XML and register C++ nodes. |
| **Groot 2** | The GUI to monitor a live tree (watch it tick) and to author/edit trees. |
| **Subtree** | A reusable tree referenced by name inside another tree — BT modularity. |

---

*If a link 404s, please open an issue so we can replace it.*
