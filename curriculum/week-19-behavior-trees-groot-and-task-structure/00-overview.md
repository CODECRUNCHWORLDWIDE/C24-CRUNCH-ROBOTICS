# Week 19 — Behavior Trees, Groot, and Task Structure

Welcome to the week where the robot stops being a pile of capabilities and becomes a *task*. You have a perception node (Phase 2), a Nav2 stack (Week 17), and planners you understand from the inside (Week 18). This week you learn the glue that turns "the robot can navigate" and "the robot can detect a person" into "the robot patrols three waypoints, yields to people, and retreats to charge if it's blocked too long." That glue is the **behavior tree** — the integration pattern every modern mobile robot ships — and the tool that makes it auditable is **Groot 2**.

We assume you finished Week 17 — you read the default Nav2 behavior tree, you know `bt_navigator` ticks it, and you wrote an `OperatorHold` behavior plugin. That's the warm-up. This week you *author* trees from scratch with **BehaviorTree.CPP** (the C++ library Nav2 itself uses), wire in your own condition and action nodes, drive a real task against your perception node, and watch it all tick live in Groot 2.

The one idea to internalize before you read another line: **a behavior tree is a state machine you can audit.** Every roboticist's first instinct for "do A, then B, but if C happens do D" is a finite state machine — and FSMs are fine until they aren't. The moment you have a dozen states and forty transitions, an FSM becomes an unreadable tangle where adding one behavior means rewiring half the graph, and *nobody* can look at it and say what the robot will do. A behavior tree solves the same problem with a *tree* of composable control nodes (sequence, fallback, parallel) and *reusable* leaves (conditions, actions) that **tick** top-down every cycle. The structure is readable, the leaves are reusable, and — crucially — you can open it in Groot 2 and *watch which node is running right now*. That auditability is why every serious mobile robot in 2026 ships a behavior tree, not a hand-rolled FSM.

This week continues Phase 3's safety stance. The fail-safe is built into the task itself: the patrol must **yield to people** and, if blocked too long, **retreat to a charging station** instead of stalling forever in a doorway. A behavior tree makes that fail-safe a *branch you can see and test*, not a special case buried in callback code.

## Learning objectives

By the end of this week, you will be able to:

- **Contrast** behavior trees with finite state machines — why BTs scale to complex tasks where FSMs tangle, the reactivity that re-ticking gives you, and the cost (a tick-based mental model) you pay for it.
- **Explain** BT ticking semantics: how a tick propagates from the root, the three return statuses (`SUCCESS`, `FAILURE`, `RUNNING`), and how `RUNNING` is what makes a BT able to wait on a long-running action without blocking.
- **Use** the control nodes correctly — `Sequence` (do all, in order), `Fallback`/`Selector` (try until one succeeds), `Parallel` (run several, succeed/fail on a threshold) — and the reactive variants that re-check earlier children every tick.
- **Apply** decorators (`Inverter`, `Retry`, `RepeatUntilSuccessful`, `Timeout`, `RateController`) and **condition nodes** to shape control flow without writing new control logic.
- **Author** a behavior tree in **BehaviorTree.CPP** XML, register custom C++ action and condition nodes, pass data through the **blackboard**, and tick the tree to completion.
- **Visualize and debug** a live tree in **Groot 2** — connect to a running tree, watch nodes change color as they tick, and read the blackboard — and author/edit a tree in Groot 2's editor.
- **Build** the syllabus task: a patrol of three waypoints that pauses and waits when a person is detected (using the perception node from Week 16), with a recovery branch that retreats to a charging station if the pause exceeds 60 seconds.
- **Declare and implement** a fail-safe as a *visible BT branch*: the yield-and-retreat behavior is a subtree you can point to, test in isolation, and audit in Groot 2 — not a hidden callback.

## Prerequisites

This week assumes you have completed **C24 weeks 1–18**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**, with **Nav2** and **BehaviorTree.CPP** installed (`sudo apt install ros-jazzy-behaviortree-cpp ros-jazzy-nav2-behavior-tree`).
- **Groot 2** available (`sudo snap install groot2`, or the AppImage from the BehaviorTree.dev site) — the monitoring and editing tool.
- The **Week 17 `crunchbot_nav` bring-up** — you can launch Nav2 on your week-7 map, send a `NavigateToPose` goal, and your `OperatorHold` plugin loads.
- The **Week 16 perception node** publishing detections (`vision_msgs/Detection2DArray` or your `/perception/objects` topic) so the patrol can react to a detected person.
- Comfort with a **C++ `ament_cmake` package** and `pluginlib` (Week 17) — BT.CPP nodes are C++ and registered the same way.
- Action-client fluency (Week 4, Week 17) — BT action-leaves call ROS2 actions like `NavigateToPose`.

You do **not** need prior behavior-tree theory. We start from the FSM contrast and build to a full reactive patrol. If you've only ever *read* Nav2's tree (Week 17) without writing one, this is the week authoring becomes load-bearing.

## Topics covered

- **BTs vs. FSMs**: the state-explosion problem in FSMs, why BTs compose, the reactivity of re-ticking, and the honest trade-offs (BTs are not always the answer — a two-state toggle is fine as an FSM).
- **Ticking semantics**: the tick propagating from the root every cycle; the three statuses (`SUCCESS`, `FAILURE`, `RUNNING`); why `RUNNING` is the key innovation that lets a tree wait on a navigation action without blocking the tick.
- **Control nodes**: `Sequence` (AND), `Fallback`/`Selector` (OR), `Parallel` (M-of-N), and the **reactive** variants (`ReactiveSequence`, `ReactiveFallback`) that re-evaluate earlier children every tick — the foundation of "yield the moment a person appears."
- **Decorators**: `Inverter`, `ForceSuccess`/`ForceFailure`, `Retry`/`RetryUntilSuccessful`, `Repeat`, `Timeout`, `Delay`, and `RateController` (the same one Nav2's tree uses to throttle replanning).
- **Condition and action nodes**: synchronous conditions (`IsPersonDetected`, `IsBatteryLow`), asynchronous stateful actions (`NavigateToWaypoint`, `Wait`), and how an action returns `RUNNING` until it finishes.
- **BehaviorTree.CPP**: defining nodes in C++, the `BT::SyncActionNode` / `BT::StatefulActionNode` / `BT::ConditionNode` base classes, registering them in a `BehaviorTreeFactory`, loading a tree from XML, and ticking it.
- **The blackboard**: the shared key-value store that passes data between nodes (a waypoint into a `NavigateToWaypoint`, a detection out of `IsPersonDetected`), input/output ports, and port remapping.
- **Groot 2**: connecting to a live tree over the BT.CPP Groot2 publisher, watching nodes tick (green = running, etc.), reading the blackboard, and authoring/editing trees in the visual editor.
- **The patrol-with-yield task**: the full syllabus build — three-waypoint patrol, pause-and-wait on person detection, retreat-to-charging recovery on a 60 s timeout — as a tree you author, run against perception, and audit in Groot 2.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | BTs vs. FSMs; ticking; statuses; control nodes        |   2h     |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Decorators; conditions; reactive sequences; the blackboard |  1h |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | BehaviorTree.CPP authoring; custom nodes; Groot 2      |   2h     |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | The patrol-with-yield task; perception integration    |   1h     |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | The retreat-on-timeout recovery; Groot 2 audit        |   0h     |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                               |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, tree-audit write-up polish             |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                      | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The BehaviorTree.CPP docs, the Groot 2 docs, the Nav2 BT reference, the canonical BT book, and the talks worth your time |
| [lecture-notes/01-behavior-trees-vs-state-machines.md](./02-lecture-notes/01-behavior-trees-vs-state-machines.md) | BTs vs FSMs, ticking semantics, the three statuses, the control nodes, decorators, and conditions |
| [lecture-notes/02-behaviortree-cpp-groot-and-the-patrol-task.md](./02-lecture-notes/02-behaviortree-cpp-groot-and-the-patrol-task.md) | Authoring in BehaviorTree.CPP, custom C++ nodes, the blackboard, Groot 2, and the patrol-with-yield task |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-read-and-trace-trees.md](./03-exercises/exercise-01-read-and-trace-trees.md) | Trace five small trees by hand, predict the tick sequence, then verify in Groot 2 |
| [exercises/exercise-02-tick-engine.py](./03-exercises/exercise-02-tick-engine.py) | A runnable, correct minimal BT tick engine (Sequence/Fallback/Parallel/decorators) with a self-checking harness |
| [exercises/exercise-03-patrol-blackboard.py](./03-exercises/exercise-03-patrol-blackboard.py) | A runnable patrol-with-yield simulation showing reactive yielding and the 60 s retreat, blackboard-driven |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-the-misbehaving-tree.md](./04-challenges/challenge-01-the-misbehaving-tree.md) | A patrol tree with three structural bugs (a non-reactive yield, a missing timeout, an inverted condition) — diagnose and fix using Groot 2 |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the fail-safe-as-a-visible-branch declaration |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunchbot_patrol` package: the full BT.CPP patrol-with-yield-and-retreat, wired to Nav2 + perception, audited in Groot 2 |

## The "the tree is green" promise

C24 uses a recurring marker for every exercise that ends in a tree actually running. For behavior trees, that marker is **Groot 2 showing the live tick**:

```
Connect Groot 2 to the running tree (Monitor mode, port 1667).
The root PipelineSequence is green (RUNNING).
NavigateToWaypoint is green (RUNNING) — the robot is driving to waypoint 2.
IsPersonDetected is red (FAILURE) — no person, so the patrol continues.
```

If Groot 2 can't connect, or every node is grey, your tree isn't ticking — check that you registered the Groot2 publisher and that the tree actually loaded. If a node is *stuck* green forever, you have an action that never returns (the BT equivalent of a hang). The point of Week 19 is to make "watch the tree tick in Groot 2" ordinary — so that when a robot misbehaves, you *see* which branch it's in instead of guessing from logs.

## Stretch goals

If you finish the regular work early and want to push further:

- Replace your patrol's `NavigateToWaypoint` leaf with Nav2's real `NavigateToPose` BT action node and run the patrol on your actual week-7 map in Gz Sim — the full integration.
- Add a **`Parallel`** node that runs the patrol *and* a battery-monitor subtree at once, so a low battery interrupts the patrol from a concurrent branch rather than a condition checked between waypoints.
- Author the same patrol tree two ways — once as an FSM (`smach` or a hand-rolled state machine) and once as a BT — and write a one-page comparison of which was easier to *extend* when you added the retreat behavior. This is the BT-vs-FSM lesson, earned.
- Read BehaviorTree.CPP's **scripting** feature (the `Script` node and the small expression language) and use it to set a blackboard variable inline instead of writing a whole action node.

## Up next

Week 20 turns to **controllers** — PID and feedforward — the layer beneath the behavior tree that actually moves the wheels smoothly. Your patrol tree commands *what* to do; the controller decides *how* to do it without overshooting. The BT/controller split mirrors the planner/controller split you've now seen twice. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
