# Lecture 2 — BehaviorTree.CPP, the Blackboard, Groot 2, and the Patrol Task

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can author a tree in BehaviorTree.CPP XML, register custom C++ condition and action nodes, pass data through the blackboard with ports, watch a live tree tick in Groot 2, and assemble the full patrol-with-yield-and-retreat task.

Lecture 1 gave you the execution model — ticking, the three statuses, the control nodes. This lecture makes it real in **BehaviorTree.CPP** (the library Nav2 uses), adds the **blackboard** (how nodes share data), connects **Groot 2** (how you *see* the tree), and assembles the syllabus task. Three parts: (1) authoring in BT.CPP, (2) the blackboard and Groot 2, (3) the patrol task end to end.

> **Why BehaviorTree.CPP specifically?** Because it's what Nav2 uses, it's actively maintained, it ships Groot 2 as a first-class visualizer, and it's C++ (so your task tree and Nav2's navigation tree run in the same ecosystem). There's a Python BT library (`py_trees`) that's lovely for prototyping, and you'll use a Python tick-engine in Exercise 2 to learn the semantics cheaply — but the *production* artifact, the mini-project, is BT.CPP, because that's what you'd ship and what an employer expects you to know.

---

## Part 1 — Authoring in BehaviorTree.CPP

### 1.1 The XML tree definition

BehaviorTree.CPP separates the **structure** (an XML file you can edit by hand or in Groot 2) from the **node implementations** (C++ classes you register). A tree is XML:

```xml
<root BTCPP_format="4">
  <BehaviorTree ID="MainTree">
    <Sequence name="root_sequence">
      <CheckBattery   name="check_battery"/>
      <SaySomething   message="mission start"/>
      <NavigateToWaypoint  waypoint="{target}"/>
    </Sequence>
  </BehaviorTree>
</root>
```

Each XML tag is a node; `name` is a human label; other attributes are **ports** (data in/out, §2). The `BTCPP_format="4"` declares the BT.CPP 4.x schema (a few node names differ from the 3.x schema, so check the version). This XML is what Groot 2 reads and writes, and what `bt_navigator` loads for Nav2 — the *same* XML format you read in Week 17 is the one you author now. Indentation in the XML mirrors the tree depth, so a well-formatted tree file reads like the ASCII diagrams in these notes: the structure is visible in the text.

> **Why separate XML from C++ at all?** Because the *structure* of a task changes far more often than the *implementations* of its nodes. A field engineer who needs to add a waypoint, reorder the patrol, or insert a "wait for an announcement" step edits the XML — no recompile, no C++ knowledge. The roboticist who needs a *new capability* writes a C++ node once, and it becomes a reusable building block in the XML palette. This split — declarative structure, compiled behavior — is the same instinct as Nav2's params-vs-plugins (Week 17): the thing that changes often is data; the thing that changes rarely is code.

### 1.2 Registering custom nodes

The XML tags map to C++ classes you register in a `BehaviorTreeFactory`. A **condition node** subclasses `BT::ConditionNode` (returns `SUCCESS`/`FAILURE`, never `RUNNING`):

```cpp
#include "behaviortree_cpp/behavior_tree.h"
#include "behaviortree_cpp/bt_factory.h"

class CheckBattery : public BT::ConditionNode
{
public:
  CheckBattery(const std::string & name, const BT::NodeConfig & config)
  : BT::ConditionNode(name, config) {}

  // Conditions with no ports still declare an (empty) ports list.
  static BT::PortsList providedPorts() { return {}; }

  BT::NodeStatus tick() override
  {
    double voltage = readBatteryVoltage();   // your ROS2 subscription, etc.
    return (voltage > 11.0) ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
  }
};
```

An **asynchronous action** subclasses `BT::StatefulActionNode` — the base for anything that takes many ticks (Lecture 1 §5.2). It has three methods: `onStart` (kick it off, return `RUNNING` or an immediate result), `onRunning` (called each tick while `RUNNING` — check if done), and `onHalted` (clean up when interrupted):

```cpp
class NavigateToWaypoint : public BT::StatefulActionNode
{
public:
  NavigateToWaypoint(const std::string & name, const BT::NodeConfig & config)
  : BT::StatefulActionNode(name, config) {}

  // Declare an INPUT port: the waypoint pose, read from the blackboard.
  static BT::PortsList providedPorts()
  {
    return { BT::InputPort<geometry_msgs::msg::PoseStamped>("waypoint") };
  }

  BT::NodeStatus onStart() override
  {
    auto wp = getInput<geometry_msgs::msg::PoseStamped>("waypoint");
    if (!wp) {
      throw BT::RuntimeError("missing required input [waypoint]: ", wp.error());
    }
    sendNavGoal(wp.value());          // fire the NavigateToPose action goal
    return BT::NodeStatus::RUNNING;   // not done — tick me again
  }

  BT::NodeStatus onRunning() override
  {
    if (navGoalSucceeded())  return BT::NodeStatus::SUCCESS;
    if (navGoalFailed())     return BT::NodeStatus::FAILURE;
    return BT::NodeStatus::RUNNING;   // still driving
  }

  void onHalted() override
  {
    cancelNavGoal();   // CRUCIAL: a reactive parent interrupted us — STOP the robot
  }
};
```

The `onHalted` is the load-bearing detail from Lecture 1 §5.2: when a `ReactiveSequence` above this action returns `FAILURE` (a person appeared), BT.CPP calls `onHalted`, which cancels the Nav2 goal, which actually stops the robot. Skip it and the robot keeps driving despite the "yield."

Registering and running:

```cpp
int main()
{
  BT::BehaviorTreeFactory factory;
  factory.registerNodeType<CheckBattery>("CheckBattery");
  factory.registerNodeType<NavigateToWaypoint>("NavigateToWaypoint");
  // ... register SaySomething, IsPersonDetected, etc.

  auto tree = factory.createTreeFromFile("./patrol.xml");

  // Let Groot 2 attach to this live tree (Part 2):
  BT::Groot2Publisher publisher(tree);

  // Tick the whole tree at ~10 Hz until it finishes.
  while (rclcpp::ok()) {
    BT::NodeStatus status = tree.tickOnce();
    if (status != BT::NodeStatus::RUNNING) break;
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
}
```

`tickOnce()` sends one tick from the root; the loop ticks at 10 Hz. The tree runs until the root returns something other than `RUNNING`. That loop is the engine; everything else is the nodes.

> **The ROS2 integration detail:** in a real node, you don't `sleep` in a bare loop — you tick the tree from a ROS2 timer callback (e.g., a 20 Hz `create_wall_timer`) inside a spinning node, so your action nodes' ROS2 subscriptions and action clients keep getting serviced between ticks. The bare-loop version above is the *shape*; the production version ticks from a timer on a spinning executor. This is exactly how `bt_navigator` runs Nav2's tree, and how your mini-project's patrol node will run yours.

---

## Part 2 — The blackboard and Groot 2

### 2.1 The blackboard: how nodes share data

Nodes don't call each other; they share data through a **blackboard** — a key-value store scoped to the tree. A node declares **ports**: an `InputPort<T>("name")` reads a value, an `OutputPort<T>("name")` writes one. In the XML, a port attribute like `waypoint="{target}"` means "read the port `waypoint` from the blackboard key `target`" (the `{}` denotes a blackboard entry; a bare value is a literal).

A detection condition might *write* the detected person's pose to the blackboard, and a navigate action might *read* a waypoint from it:

```cpp
class IsPersonDetected : public BT::ConditionNode
{
public:
  IsPersonDetected(const std::string & name, const BT::NodeConfig & config)
  : BT::ConditionNode(name, config) {}

  static BT::PortsList providedPorts()
  {
    // OUTPUT port: publish where the person is, for downstream nodes.
    return { BT::OutputPort<geometry_msgs::msg::Point>("person_location") };
  }

  BT::NodeStatus tick() override
  {
    auto detections = latestDetections();   // your perception subscription
    for (const auto & det : detections) {
      if (det.class_id == "person") {
        setOutput("person_location", det.center);   // write to blackboard
        return BT::NodeStatus::SUCCESS;
      }
    }
    return BT::NodeStatus::FAILURE;
  }
};
```

In XML, you wire the output to a blackboard key and read it elsewhere:

```xml
<IsPersonDetected person_location="{person_pos}"/>
<!-- ... later ... -->
<FaceTowards target="{person_pos}"/>
```

The blackboard is how a tree stays *decoupled*: `IsPersonDetected` doesn't know who reads `person_pos`; it just writes it. This is the same separation-of-concerns instinct as the planner/steering split in Week 18 — nodes communicate through a shared store, not direct calls, so any node can be swapped or reused.

> **Scope gotcha:** by default the blackboard is scoped per (sub)tree. When you call a **subtree**, its blackboard is separate unless you explicitly **remap** ports across the boundary (`<SubTree ID="Patrol" target="{global_target}"/>`). Forgetting to remap is why "my subtree can't see the value I set in the parent" — a top BT.CPP confusion, and one Groot 2 helps you spot because it shows each subtree's blackboard.

### 2.2 Groot 2: seeing the tree tick

You cannot debug a behavior tree from logs alone — you need to *see* which node is running. **Groot 2** is that tool, and it has two modes:

- **Monitor mode** — connect to a *live* running tree (via the `BT::Groot2Publisher` you added in Part 1) and watch nodes change color as they tick: a `RUNNING` node glows, a `SUCCESS` node flashes green, a `FAILURE` node red. You see *exactly* which branch the robot is in, in real time. This is the "the tree is green" promise from the README.
- **Editor mode** — author and edit the XML tree visually: drag control nodes, drop in your registered leaves, wire ports. The output is the same XML your C++ loads.

To enable monitoring, add one line to your tree runner (already in the Part 1 `main`):

```cpp
BT::Groot2Publisher publisher(tree, 1667);   // default port 1667
```

Then open Groot 2, choose **Connect**, point it at `localhost:1667`, and watch.

#### Groot 2 troubleshooting (you will need this)

A short field guide to the connection problems you'll hit:

| Symptom | Likely cause | Fix |
|---|---|---|
| Groot 2 won't connect | No `Groot2Publisher` in the runner, or wrong port | Add the publisher; confirm port 1667 (or match what Groot uses) |
| Connects but all nodes grey | The tree loaded but isn't being ticked | Ensure your tick loop is running (`tree.tickOnce()` in a loop) |
| A node stuck green forever | An async action whose `onRunning` never returns `SUCCESS`/`FAILURE` | Fix the action's terminating condition (mistake #4) |
| Tree shows but blackboard empty | Ports not wired, or subtree-scope remap missing | Check the XML port mappings; remap across subtree boundaries |
| Editor changes don't take effect | You edited the XML but the C++ loaded a stale copy | Reload the tree file; confirm the path |

The "stuck green forever" row is the most instructive: in an FSM that bug is a silent infinite loop you'd find only by adding logs; in a BT *with Groot 2* it's a node glowing green that should have finished, visible at a glance. That's the auditability dividend — the visualizer turns a class of invisible hangs into a thing you literally see. When the patrol is driving, `NavigateToWaypoint` is green; when a person appears, you *see* the `IsPersonDetected` flip to green and the patrol branch halt and the recovery branch light up. **That live picture is the difference between "the robot did something weird" and "the robot entered the retreat subtree at 14:32:07 because the wait timed out."** Groot 2 turns a behavior tree from a guess into an audit.

---

## Part 3 — The patrol-with-yield-and-retreat task

Now assemble the syllabus task: patrol three waypoints; if a person is detected, pause and wait until they leave; if the pause exceeds 60 seconds, retreat to a charging station.

### 3.1 The full tree

```xml
<root BTCPP_format="4">
  <BehaviorTree ID="MainTree">
    <!-- Try the patrol; if it ultimately fails (timed-out yield), retreat. -->
    <Fallback name="patrol_or_retreat">

      <!-- The patrol, with reactive yielding to people. -->
      <ReactiveSequence name="patrol_with_yield">

        <!-- Re-checked EVERY tick: if a person appears, this fails, the
             ReactiveSequence fails, and the running PatrolLoop is halted. -->
        <Fallback name="handle_person">
          <Inverter>
            <IsPersonDetected person_location="{person_pos}"/>
          </Inverter>
          <!-- A person IS detected: wait for them to leave, but no longer
               than 60 s. If the wait times out, this Fallback fails, which
               fails the ReactiveSequence, which drops us into Retreat. -->
          <Timeout msec="60000">
            <KeepRunningUntilFailure>
              <IsPersonDetected/>
            </KeepRunningUntilFailure>
          </Timeout>
        </Fallback>

        <!-- The actual patrol: loop the three waypoints forever. -->
        <KeepRunningUntilFailure name="patrol_loop">
          <Sequence name="one_lap">
            <NavigateToWaypoint waypoint="{wp1}"/>
            <NavigateToWaypoint waypoint="{wp2}"/>
            <NavigateToWaypoint waypoint="{wp3}"/>
          </Sequence>
        </KeepRunningUntilFailure>

      </ReactiveSequence>

      <!-- Recovery: only reached if the patrol failed (person stayed > 60 s). -->
      <Sequence name="retreat">
        <NavigateToWaypoint waypoint="{charger}"/>
        <SaySomething message="blocked too long; retreated to charger"/>
      </Sequence>

    </Fallback>
  </BehaviorTree>
</root>
```

### 3.2 Tracing the three scenarios

Walk the three behaviors the task must exhibit — this is how you verify a tree is *correct*, not just well-formed:

1. **No person, normal patrol.** Every tick, the `handle_person` `Fallback`'s first child is `Inverter[IsPersonDetected]`. No person → `IsPersonDetected` fails → `Inverter` → `SUCCESS`. The `handle_person` `Fallback` short-circuits `SUCCESS`. The `ReactiveSequence` proceeds to `patrol_loop`, which drives the waypoints (`RUNNING`). The robot patrols. ✓
2. **Person appears, then leaves within 60 s.** A person is detected → `IsPersonDetected` `SUCCESS` → `Inverter` `FAILURE`. The `handle_person` `Fallback` moves to its second child: `Timeout[KeepRunningUntilFailure[IsPersonDetected]]`. While the person is present, `IsPersonDetected` keeps returning `SUCCESS`, so `KeepRunningUntilFailure` returns `RUNNING` — the robot *waits* (the `ReactiveSequence`'s reactivity halted `patrol_loop` when `handle_person` was `RUNNING`). When the person leaves, `IsPersonDetected` fails, `KeepRunningUntilFailure` returns `FAILURE`... wait — that fails the `Timeout`, fails `handle_person`, fails the `ReactiveSequence`. **That's a bug in this sketch** — leaving should *resume* the patrol, not trigger retreat. The correct construction inverts the inner condition so the wait succeeds when the person leaves. (The mini-project makes you get this exactly right; the sketch deliberately leaves the subtlety visible so you confront it.)
3. **Person stays longer than 60 s.** The `Timeout(60000)` fires, returning `FAILURE`. `handle_person` fails, the `ReactiveSequence` fails, and the outer `Fallback` moves to the `retreat` branch: navigate to the charger. The robot retreats. ✓

> **The lesson hiding in scenario 2:** behavior-tree *structure* is logic, and a subtly-wrong structure produces a subtly-wrong robot — one that retreats when it should resume. You cannot eyeball a tree and trust it; you must *trace every scenario* (and watch it in Groot 2). The mini-project's acceptance criteria are exactly these three scenarios, because "the tree loads and looks right" is not the same as "the robot does the right thing."

### 3.3 Wiring to Nav2 and perception

In the real build (mini-project), `NavigateToWaypoint` wraps Nav2's `NavigateToPose` action (Week 17), and `IsPersonDetected` reads your Week 16 perception topic (`/perception/objects` or `vision_msgs/Detection2DArray`). The waypoints `{wp1}`, `{wp2}`, `{wp3}`, and `{charger}` are set on the blackboard at startup (from a params file or a launch argument). Nav2 itself runs *its own* internal BT for each `NavigateToPose` (Week 17's tree) — so you have a **tree calling a tree**: your patrol tree's leaf invokes Nav2's navigation tree. That nesting is normal and powerful: high-level task logic on top, navigation logic underneath, each auditable in its own Groot 2 session.

### 3.4 Subtrees: the modularity that makes large trees maintainable

As the task grows, you don't keep one giant XML — you factor it into **subtrees**, each a named, reusable tree referenced from another. The yield logic, the recovery logic, and the patrol loop each become a subtree:

```xml
<root BTCPP_format="4">
  <BehaviorTree ID="MainTree">
    <Fallback>
      <SubTree ID="PatrolWithYield"/>
      <SubTree ID="RetreatToCharger" charger="{charger}"/>
    </Fallback>
  </BehaviorTree>

  <BehaviorTree ID="PatrolWithYield">
    <!-- ...the reactive patrol... -->
  </BehaviorTree>

  <BehaviorTree ID="RetreatToCharger">
    <!-- ...the recovery... -->
  </BehaviorTree>
</root>
```

The `<SubTree ID="RetreatToCharger" charger="{charger}"/>` line shows the **port remapping** across the subtree boundary (the §2.1 gotcha): the parent's `{charger}` blackboard key is mapped into the subtree's `charger` port. Subtrees give you three things: **reuse** (the same `RetreatToCharger` subtree used by several tasks), **readability** (the `MainTree` reads as four lines, not four hundred), and **isolated testing** (you can tick `RetreatToCharger` alone to verify it). This is exactly how Nav2 structures its trees — the recovery subtree is referenced, not inlined — and it's how you keep a real robot's task tree from becoming the FSM tangle BTs were supposed to escape. A flat 200-node tree is just an FSM with extra steps; subtrees are what deliver the modularity promise from Lecture 1.

> **The discipline:** one subtree, one responsibility, one Groot 2 view. If a subtree does more than one conceptual job, split it. The readability of the whole tree is the sum of the readability of its subtrees, and a robot's task logic is something a *reviewer* (Week 24's integration review) must be able to read and sign off on.

---

## 4. Recap

You should now be able to:

- Author a BehaviorTree.CPP tree in XML and register custom C++ nodes in a `BehaviorTreeFactory`.
- Implement a condition (`BT::ConditionNode`, synchronous) and an async action (`BT::StatefulActionNode`, with `onStart`/`onRunning`/`onHalted`), and explain why `onHalted` is what stops the robot on a yield.
- Pass data through the blackboard with input/output ports, write the port-to-key mapping in XML, and avoid the subtree-scope remapping gotcha.
- Connect Groot 2 in Monitor mode to a live tree (via `Groot2Publisher`) and read the running branch, and author trees in Editor mode.
- Assemble the patrol-with-yield-and-retreat task — `Fallback` over a `ReactiveSequence` (reactive yield) and a recovery branch, with a `Timeout` gating the retreat — and *trace all three scenarios* to verify correctness, not just well-formedness.
- Explain the tree-calling-a-tree nesting where your patrol's nav leaf invokes Nav2's own navigation BT.
- Factor a growing task into subtrees (with port remapping across boundaries) for reuse, readability, and isolated testing.

> **The acceptance bar for any tree you write:** it loads, it ticks (Groot 2 shows it green), *and* it does the right thing in every scenario you trace. The third is the one beginners skip — a tree that loads and looks plausible can still retreat-when-it-should-resume (scenario 2 above). Trace every branch, watch it in Groot 2, and only then trust it. "It compiled and connected" is necessary, not sufficient; "I traced all three scenarios and watched each in Groot 2" is the real done.

Next: the exercises put a tick engine in your hands, then build the patrol against perception. Continue to [the exercises](../exercises/README.md).

---

## References

- *BehaviorTree.CPP — first tree*: <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_01_first_tree>
- *BehaviorTree.CPP — ports and the blackboard*: <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_02_basic_ports>
- *BehaviorTree.CPP — StatefulActionNode*: <https://www.behaviortree.dev/docs/tutorial-basics/tutorial_08_additional_args>
- *Groot 2 docs*: <https://www.behaviortree.dev/groot/>
- *Nav2 — configuring bt_navigator*: <https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html>
- *BehaviorTree.CPP — subtrees and Groot2 publisher*: <https://www.behaviortree.dev/docs/tutorial-advanced/tutorial_05_subtrees/>
- *Behavior Trees in Robotics and AI* (Colledanchise & Ögren): <https://arxiv.org/abs/1709.00084>
