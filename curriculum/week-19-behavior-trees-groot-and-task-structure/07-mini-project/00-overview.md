# Mini-Project — `crunchbot_patrol`: The Patrol-with-Yield Task in BehaviorTree.CPP

> Build the full syllabus task as a real BehaviorTree.CPP package: patrol three waypoints; if a person is detected (from your Week 16 perception node), pause and wait until they leave; if the pause exceeds 60 seconds, retreat to a charging station. Author the tree in BT.CPP XML, implement the custom condition and action nodes in C++, wire the nav leaves to Nav2's `NavigateToPose`, drive it against your week-7 map, and audit the whole thing live in Groot 2.

This is the artifact that turns "I read Nav2's behavior tree" into "I author and ship a robot's task logic." After this week, a behavior tree is a thing you *build* — custom nodes, a blackboard, a reactive yield, a timeout-gated recovery — and Groot 2 is a tool you *use* to verify it. This is the integration glue the whole of Phase 3 has been building toward.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This package is a direct input to the **Week 24 Phase 3 integration** (Nav2 + MoveIt2 + a small BT in one launch graph) and a seed of the **capstone's task tree** (Week 40, Week 48). The yield-and-retreat fail-safe you build here is exactly the kind of auditable safety branch the capstone's safety case (Week 41) is graded on. Build it well now; you'll defend it twice.

This is the third "build the production thing" mini-project of Phase 3, and the pattern is deliberate: Week 17 you built a Nav2 bring-up and a plugin; Week 18 you built a planner library and a Nav2 planner plugin; this week you build the *task tree* that ties them together. By Week 24 these three packages compose into one autonomy stack — your bring-up, your planner, your task tree — which is the Phase 3 integration milestone. Keep all three repos; you'll launch them together in five weeks.

---

## What you will build

A `colcon` package `crunchbot_patrol` (C++ `ament_cmake`, because BT.CPP nodes are C++) with three deliverables:

1. **The custom nodes** — C++ implementations of `IsPersonDetected` (condition, reads your perception topic), `NavigateToWaypoint` (async action wrapping Nav2's `NavigateToPose`, with a real `onHalted`), `WaitForPersonToLeave` (async action), and `SaySomething`/`SetWaypoints` (small helpers). Registered in a `BehaviorTreeFactory`.
2. **The patrol tree** — `behavior_trees/patrol_with_yield.xml`: a `Fallback` over a `ReactiveSequence` (the reactive yield) and a retreat branch, with a `Timeout(60s)` gating the retreat — structured so it does the *right* thing in all three scenarios (no person / person leaves / person stays).
3. **The patrol node** — a ROS2 node that loads the tree, sets the waypoints and charger on the blackboard from params, ticks the tree at ~20 Hz from a timer on a spinning executor, and runs a `Groot2Publisher` so you can monitor it live.

By the end you have a public repo of ~500–800 lines (C++ nodes + XML + the patrol node + a test) that drives a real patrol on your week-7 map and audits in Groot 2.

The single most important line in the whole package is `NavigateToWaypoint::onHalted()` cancelling the Nav2 goal. Everything else is structure; that one method is the difference between a robot that *yields* and a robot that *says it yields while driving into a person*. Treat it as the safety-critical code it is — write it first, test it explicitly, and don't trust the tree until you've watched `/cmd_vel` go to zero on a yield.

> **Path B note (sim-only learners):** everything in this mini-project runs fully in Gz Sim — the perception node can read simulated detections, and the "person" can be a simulated obstacle or a published detection you toggle with `ros2 topic pub`. No hardware is required, and the capstone (Week 48) grades this same task tree in simulation. If you can't run the full perception stack, a stub `IsPersonDetected` that reads a `/test/person_present` (`std_msgs/Bool`) you publish manually is an acceptable stand-in for developing and demonstrating the tree logic — just note the substitution, exactly as the syllabus's Path B allows.

---

## Why a behavior tree and not a state machine for this

You *could* write this patrol as a state machine. Don't — and the mini-project exists to make you feel why. As you add the yield, then the timeout-retreat, then (stretch) a battery monitor, the FSM version needs a new transition from every interruptible state, and it tangles. The BT version slots each in as a node or subtree, and the existing branches are untouched. By the end of this build you'll have *lived* the modularity argument from Lecture 1 — and you'll have a tree a reviewer can read and Groot 2 can audit, which a hand-rolled FSM can't offer.

The auditability is the part that matters most for the capstone. When a safety reviewer (Week 41) asks "show me where the robot decides to yield, and prove it stops in time," you point at the `ReactiveSequence` and the `IsPersonDetected` guard in the XML, state the tick rate (so the reaction latency follows), and *watch it fire in Groot 2*. With an FSM, the same answer is "the yield logic is spread across these four callbacks, trust me." One of those answers passes a safety review; the other doesn't. The behavior tree isn't just easier to write — it's easier to *defend*, and defending your safety logic is half of what Phase 6 grades.

---

## Package layout

```
crunchbot_patrol/
├── package.xml
├── CMakeLists.txt
├── include/crunchbot_patrol/
│   ├── is_person_detected.hpp
│   ├── navigate_to_waypoint.hpp
│   └── wait_for_person.hpp
├── src/
│   ├── is_person_detected.cpp       # BT::ConditionNode, reads perception topic
│   ├── navigate_to_waypoint.cpp     # BT::StatefulActionNode wrapping NavigateToPose
│   ├── wait_for_person.cpp          # BT::StatefulActionNode
│   └── patrol_node.cpp              # loads the tree, ticks it, Groot2Publisher
├── behavior_trees/
│   └── patrol_with_yield.xml        # the task tree
├── config/
│   └── patrol_params.yaml           # waypoints, charger, timeout, tick rate
├── launch/
│   └── patrol.launch.py             # bring up Nav2 + perception + the patrol node
└── test/
    └── test_patrol_logic.cpp        # unit-test the three-scenario logic
```

---

## Deliverable 1 — the custom nodes

The three load-bearing nodes:

**`IsPersonDetected`** (`BT::ConditionNode`) — subscribes to your Week 16 perception topic (`vision_msgs/Detection2DArray` or `/perception/objects`), caches the latest detections in a member variable (a separate ROS2 callback, *not* in `tick()`), and `tick()` returns `SUCCESS` if a person is in frame, `FAILURE` otherwise. **Side-effect-free `tick()`** (Lecture 1 §6.2) — it only reads the cached value, because the `ReactiveSequence` re-ticks it every cycle.

**`NavigateToWaypoint`** (`BT::StatefulActionNode`) — reads a waypoint from the blackboard (`InputPort<geometry_msgs::msg::PoseStamped>`), and:
- `onStart()`: sends a `NavigateToPose` goal to Nav2, returns `RUNNING`.
- `onRunning()`: returns `SUCCESS` on arrival, `FAILURE` on abort, `RUNNING` otherwise.
- `onHalted()`: **cancels the Nav2 goal** — this is the load-bearing line (Lecture 2 §1.2). When the reactive yield interrupts, this is what actually stops the robot. Without it, the robot coasts to the waypoint despite "yielding."

**`WaitForPersonToLeave`** (`BT::StatefulActionNode`) — returns `RUNNING` while `IsPersonDetected` is true, `SUCCESS` when the person leaves. Wrapped in a `Timeout(60s)` in the XML so "stayed too long" becomes `FAILURE` → retreat.

> **The `onHalted` is graded.** The single most common way this mini-project "works in Groot 2 but the robot doesn't stop" is a missing or wrong `onHalted`. Test it explicitly: trigger a yield and confirm `/cmd_vel` goes to zero, not coasts.

---

## Deliverable 2 — the patrol tree

`behavior_trees/patrol_with_yield.xml` is the task tree. It must do the *right* thing in all three scenarios (the Lecture 2 §3.2 trap — getting scenario 2 to *resume*, not retreat, is the design work):

1. **No person** → patrol the waypoints, looping.
2. **Person appears then leaves within 60 s** → pause, then *resume* the patrol.
3. **Person stays past 60 s** → retreat to the charger.

The structure: a `Fallback` over (a) a `ReactiveSequence` containing the person-guard and the patrol loop, and (b) a retreat branch. The person-guard is a `Fallback[ Inverter[IsPersonDetected], Timeout(60s)[wait] ]` — no person passes immediately; a present person waits until they leave (success) or the timeout fires (failure → retreat). **Author it, then trace all three scenarios on paper, then verify each in Groot 2.** "Loads and looks right" is not done; "does the right thing in all three scenarios, verified in Groot 2" is done.

---

## Deliverable 3 — the patrol node and Groot 2

`patrol_node.cpp` is a ROS2 node that:
- Loads `patrol_with_yield.xml` via a `BehaviorTreeFactory` with the custom nodes registered.
- Reads the waypoints, charger, and 60 s timeout from `config/patrol_params.yaml`, sets them on the blackboard.
- Ticks the tree at ~20 Hz **from a timer callback on a spinning executor** (Lecture 2 §1.1) — *not* a bare sleep loop — so the action nodes' subscriptions and action clients keep getting serviced.
- Runs a `BT::Groot2Publisher` on port 1667 so Groot 2 can attach.

Then you connect Groot 2 in Monitor mode and *watch* the patrol: the `NavigateToWaypoint` green while driving, the `IsPersonDetected` flipping when a person appears, the patrol branch halting and the wait branch lighting up, and — if the person stays — the retreat branch firing after 60 s. That live audit is the deliverable's proof.

---

## Rules

- **You may** read the BT.CPP docs, the Nav2 BT-node source, your Week 17 `crunchbot_nav`, and your Week 16 perception node.
- **You must not** implement the yield by spawning a node that fights for `/cmd_vel` — the yield is the *tree* halting the nav action (via `onHalted`), which cancels the Nav2 goal. The reactivity must be in the tree, not in a side node.
- **You must not** put expensive work or side effects in a condition's `tick()` — perception caching happens in a separate callback.
- **You must not** depend on anything outside ROS2 Jazzy + Nav2 + BehaviorTree.CPP.
- C++17, `rclcpp`, `ament_cmake`, BT.CPP 4.x. Jazzy.
- The tree must do the right thing in *all three* scenarios, demonstrated.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-19-crunchbot-patrol-<yourhandle>`.
- [ ] `colcon build --packages-select crunchbot_patrol` succeeds.
- [ ] The patrol runs against your week-7 map in Gz Sim: the robot visits the three waypoints and loops.
- [ ] **Scenario 1 (no person):** the robot patrols and never retreats.
- [ ] **Scenario 2 (person appears then leaves within 60 s):** the robot pauses (stops — confirm `/cmd_vel` zero) and then *resumes* the patrol (not retreat).
- [ ] **Scenario 3 (person stays past 60 s):** the robot retreats to the charger.
- [ ] `onHalted` cancels the Nav2 goal: when the robot yields, `/cmd_vel` goes to zero, the robot does not coast.
- [ ] Groot 2 connects in Monitor mode and you can show (screenshot or recording) the yield firing and the retreat branch firing.
- [ ] `colcon test` passes, including `test_patrol_logic` covering the three scenarios' tree logic.
- [ ] A `README.md` with the run commands, the tree diagram, and a paragraph on why this is a BT not an FSM.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Custom nodes** | 25 | `IsPersonDetected` (side-effect-free), `NavigateToWaypoint` (correct `onStart`/`onRunning`/`onHalted`), `WaitForPersonToLeave` all correct and registered. |
| **The `onHalted` / yield** | 20 | The yield actually stops the robot (`/cmd_vel` zero, no coast) because `onHalted` cancels the Nav2 goal. This is the safety-critical line. |
| **Tree correctness** | 25 | All three scenarios behave correctly — especially scenario 2 *resumes* (the §3.2 trap), and scenario 3 retreats after the timeout. |
| **Perception integration** | 10 | `IsPersonDetected` reads the real Week-16 topic; the patrol reacts to a real detection. |
| **Groot 2 audit** | 10 | Monitor mode connects; the yield and retreat are shown firing live. |
| **Tests & hygiene** | 10 | `test_patrol_logic` covers the three scenarios; clean CMake; clear README; no `build/`/`install/` checked in. |

**90+** is portfolio-grade and ready to fold into Week 24's integration and the capstone task tree. **70–89** works but has a rough edge (scenario 2 retreats instead of resuming, or the yield coasts). **Below 70** means the yield doesn't actually stop the robot — fix `onHalted` first; it's the whole point.

---

## Common pitfalls (read before you start)

A field guide to where this mini-project usually goes wrong, so you don't lose an evening to a known trap:

- **The yield "works" in Groot 2 but the robot keeps driving.** Your `NavigateToWaypoint::onHalted` isn't cancelling the Nav2 goal. The tree halts the action node (Groot 2 shows it), but the underlying `NavigateToPose` goal is still active, so the robot finishes driving. This is *the* most common failure and it's the safety-critical one — test it explicitly by watching `/cmd_vel` go to zero on a yield.
- **Scenario 2 retreats instead of resuming.** The wait subtree's success/failure polarity is wrong (Lecture 2 §3.2). "Person left" must make the wait *succeed* so the patrol resumes; if it fails, the `Fallback` routes to retreat. Trace the scenario on paper before you trust the XML.
- **The condition node chokes the tree.** You did expensive work (or had a side effect) in `IsPersonDetected::tick()`. Because the `ReactiveSequence` re-ticks it every cycle, the work runs at 20 Hz. Move the perception read into a separate ROS2 callback that updates a member; `tick()` only reads it.
- **Groot 2 won't connect.** No `Groot2Publisher` in the patrol node, or you ticked the tree in a bare loop that blocks the executor so subscriptions never get serviced. Tick from a timer on a spinning executor (Lecture 2 §1.1).
- **The blackboard value isn't visible in a subtree.** You factored into subtrees but didn't remap the port across the boundary (Lecture 2 §2.1). Add the explicit `<SubTree ID="..." key="{parent_key}"/>` remap.

## Worked verification protocol

Don't declare the mini-project done until you've run this exact protocol and it passes — it's the same shape as the capstone's acceptance test:

1. **Bring up** Nav2 + perception + the patrol node; confirm every server `active [3]` and Groot 2 connects.
2. **Scenario 1:** no person. Watch the robot visit `wp1 → wp2 → wp3 → wp1...` and never enter the retreat branch (Groot 2: retreat subtree stays grey).
3. **Scenario 2:** publish a person detection, watch the patrol halt (`/cmd_vel` → 0) and the wait branch go green; clear the detection within 60 s, watch the patrol *resume* (Groot 2: patrol branch green again, retreat never entered).
4. **Scenario 3:** publish a person detection and *leave it set* past 60 s; watch the `Timeout` fire and the retreat branch go green, and the robot drive to the charger.
5. **Capture** a Groot 2 screenshot/recording of each scenario for the README.

If all five pass, you have a portfolio-grade task tree. If any fails, the pitfalls above name the likely cause.

## Stretch goals

- **Battery monitor in parallel.** Add a `Parallel` that runs the patrol and a battery-monitor subtree concurrently, so a low battery interrupts the patrol from a sibling branch (Lecture 1 §3.3) — a continuous safety monitor, not a between-waypoints check.
- **Subtree factoring.** Refactor the tree into named subtrees (`PatrolWithYield`, `RetreatToCharger`) with port remapping (Lecture 2 §3.4), and show each is independently testable.
- **Operator-hold integration.** Wire in your Week 17 `OperatorHold` behavior as a node the patrol can invoke, so an operator can pause the patrol on demand — composing two weeks' work.
- **CI job.** A GitHub Actions workflow that builds the package and runs `colcon test` in a headless Jazzy + Nav2 + BT.CPP container. Green check on every push.

---

## How this connects to the rest of C24

- **Week 17 (Nav2)** — your `NavigateToWaypoint` leaf calls Nav2's `NavigateToPose`; your patrol tree sits *above* Nav2's navigation tree (a tree calling a tree).
- **Week 18 (planners)** — the planner inside each `NavigateToPose` is the one you now understand from the inside.
- **Week 24 (Phase 3 integration)** — your patrol tree is the task-level glue that ties Nav2 + MoveIt2 + perception into one coherent behavior, reviewed against the hazard log.
- **Weeks 40/41/48 (capstone)** — the capstone robot ships a task tree exactly like this, and the safety case grades whether the yield-and-retreat fail-safe is real and auditable. This mini-project is that fail-safe, built five weeks early. Push it, keep the repo, extend it in the capstone.

## A note on testing tree logic without the robot

You don't need the full sim running to develop the *tree logic*. The smart workflow, mirroring the exercises:

1. **Prototype the structure in the Python tick engine** (Exercise 2/3) — it's faster to iterate on "does scenario 2 resume?" in Python than in a full C++ rebuild + sim launch.
2. **Port the verified structure to BT.CPP XML** once the logic is right.
3. **Unit-test the C++ tree logic** (`test_patrol_logic.cpp`) with stubbed nodes that return scripted statuses, so the three scenarios are CI-checkable without Nav2 or perception.
4. **Only then** wire the real nodes and run the full sim for the integration check.

This separation — verify logic cheaply, integrate last — is how you avoid the trap of debugging tree structure *and* Nav2 *and* perception all at once. When the integrated run misbehaves, you already *know* the tree logic is correct (you tested it in isolation), so the bug is in a node's implementation or the wiring, which narrows the search enormously. It's the same "test the algorithm, then the integration" discipline as Week 18's planners.

This is the artifact that, more than any other in Phase 3, demonstrates you can *structure a robot's task* — not just make a robot do one thing, but compose perception, navigation, and recovery into auditable behavior. Put it near the top of your portfolio.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
