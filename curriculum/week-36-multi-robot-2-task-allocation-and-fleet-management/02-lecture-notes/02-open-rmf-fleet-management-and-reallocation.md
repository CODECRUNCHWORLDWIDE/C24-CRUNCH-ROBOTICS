# Lecture 2 — Open-RMF, Fleet Management, and Reallocation

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can describe the Open-RMF architecture and name what each component does, plug a Nav2-driven robot into RMF with a fleet adapter, submit tasks through the fleet API, explain how the traffic schedule deconflicts a narrow corridor, and verify that a stalled robot's task is reallocated.

Lecture 1 gave you the math — how to decide who does what. This lecture gives you the **system** — the piece of production software that runs that math continuously across a heterogeneous fleet, deconflicts the robots in shared space, and survives a robot dying. That system, in 2026, is **Open-RMF**: the open-source Robotics Middleware Framework, maintained under the Open Source Robotics organization, deployed in hospitals and commercial buildings to coordinate robots from *different vendors* on *one map*.

The sentence to carry through this lecture:

> **Open-RMF is what an open-source fleet manager looks like in 2026: a traffic scheduler, a task dispatcher, and a set of vendor-specific adapters, glued by ROS2, that lets robots that were never designed to know about each other share corridors and tasks without colliding.**

A fleet manager is not "a bigger Nav2." Nav2 plans *one robot's* path on *one robot's* costmap. A fleet manager reasons about *all* the robots' paths in shared space-time, decides who yields at the pinch point, decides who gets the next delivery, and notices when one of them stops moving. That is a distributed-systems job, and Open-RMF is the open implementation you should know cold before you walk into a fleet-ops interview.

---

## Part 1 — The Open-RMF architecture

RMF is several cooperating ROS2 components. The first time you read this it's an alphabet soup; by the end of the week it's a mental map you can draw. Here is the soup, top to bottom.

```
        ┌──────────────────────────────────────────────────────────┐
        │   rmf_api_server  (web gateway: REST + websocket, JSON)   │
        │   tasks in, fleet state out — what a dashboard talks to    │
        └───────────────────────────┬──────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │   rmf_task / dispatcher  (receives requests, runs bidding, │
        │                           assigns tasks to fleets)         │
        └───────────────────────────┬──────────────────────────────┘
                                     │
        ┌────────────────────────────▼─────────────────────────────┐
        │   rmf_traffic_schedule  (the space-time schedule node;     │
        │                          holds every reserved trajectory)  │
        │   rmf_traffic           (the deconfliction / negotiation)  │
        └───────────────────────────┬──────────────────────────────┘
                                     │
   ┌─────────────────────────────────┼─────────────────────────────────┐
   │  fleet adapter A (full control)  │  fleet adapter B (traffic light) │
   │   - reports robot state          │   - robot plans its own path     │
   │   - drives robot via Nav2        │   - RMF only grants go/stop      │
   └──────────────┬──────────────────┴──────────────────┬──────────────┘
                  │                                       │
          robot1 (Nav2 base)                      robot2 (vendor base)
```

### 1.1 `rmf_traffic` and the traffic schedule

The heart of RMF is the **traffic schedule**: a shared, central database of every robot's *reserved trajectory through space and time*. Not just "where is robot 1 now" but "robot 1 will be in cell (12,7) from t=4.0s to t=4.8s." Every fleet adapter submits its robots' planned trajectories to the schedule node (`rmf_traffic_schedule`). Because the schedule knows everyone's future, it can detect when two reserved trajectories **conflict** — they want the same space at the same time — *before* the robots get there.

The schedule is the thing that makes RMF more than N independent Nav2 stacks. Nav2 avoids obstacles it can *see*; RMF avoids conflicts it can *predict*, because it has every robot's plan in one place. This is the same insight as Lecture 1's cost matrix: centralize the global picture, then reason about it jointly.

### 1.2 `rmf_task` — the dispatcher

The **dispatcher** receives task requests (deliveries, patrols, cleaning loops), runs a **bidding** process across the fleets that *can* do the task, and assigns it to the best bidder. This is Lecture 1's auction, productionized: when a delivery comes in, each capable fleet computes a cost (estimated completion time given its robots' current commitments) and bids; the dispatcher awards to the lowest bid. It also tracks the **task lifecycle**: `queued → assigned → underway → completed` (or `failed` / `canceled`), which is exactly the state machine your reallocation logic keys off.

### 1.3 Fleet adapters — the vendor bridge

A **fleet adapter** is the per-robot-kind shim that lets RMF talk to a specific robot. It translates between RMF's world (abstract tasks, traffic reservations, the nav graph) and the robot's world (its own driver, its own navigation). There are **three control categories**, and knowing which one you're using is the single most important architectural decision:

- **Full control.** RMF plans the robot's path on the shared nav graph and *commands the robot to follow it*, segment by segment. The robot is a "dumb" follower; RMF owns navigation. This is what you use when the robot exposes a Nav2-style "go to this pose" interface and nothing smarter. The `EasyFullControl` API (Python and C++) is the modern, low-boilerplate way to write one. **This is the category you'll use this week** because your robots are Nav2-driven.
- **Traffic light.** The robot plans and executes its *own* navigation (it has its own onboard autonomy). RMF does not command paths; it only grants **go / stop / slow** at points where the robot would conflict with another robot. The robot asks "may I proceed through this intersection?" and RMF answers. Used for vendor robots with capable onboard stacks that you can't (or shouldn't) override.
- **Read-only.** RMF cannot command the robot at all; it only *observes* the robot's reported state and incorporates it into the schedule as a moving obstacle to plan *other* robots around. Used for robots you have zero control authority over (a third-party AMR, a human-driven forklift broadcasting its pose).

A **heterogeneous fleet** mixes these. A hospital might run its own delivery robots under full control, a vendor's cleaning robot under traffic light, and treat a contractor's pallet jack as read-only. RMF coordinates all three on one schedule. That is the whole reason RMF exists: **one fleet manager, many robot kinds, one shared space.**

How to choose the control category for a robot, in one rule of thumb:

- **Can you command its navigation directly (Nav2-style goal)?** → Full control. RMF plans and drives. (Your robots this week.)
- **Does it have its own autonomy you can't/shouldn't override, but it'll ask permission at conflicts?** → Traffic light. RMF grants go/stop.
- **Can you only *observe* it (a third-party robot, a human-driven vehicle)?** → Read-only. RMF plans the *others* around it as a moving obstacle.

The decision is about *how much command authority you have* over the robot, not about the robot's quality. A great vendor robot you can't command is read-only; a cheap robot you fully control is full-control. Authority, not capability, sets the category — and getting this wrong (trying to full-control a robot whose autonomy fights you) is a classic integration failure.

### 1.4 The nav graph and the building map

RMF doesn't plan on a raw occupancy grid. It plans on a **nav graph**: a hand-authored (via `rmf_traffic_editor`) graph of **waypoints** connected by **lanes**, annotated with directions, speed limits, doors, lifts, and which fleets may use which lanes. This is a deliberate abstraction: in a structured environment (a building, a warehouse), you *want* robots on defined lanes, not free-roaming, because lanes make conflicts predictable and deconfliction tractable. The building map ties the nav graph to the physical floor plan and the per-fleet metric maps.

### 1.5 The API server

`rmf_api_server` is the **web gateway**: a REST + websocket service speaking JSON, defined by `rmf_api_msgs`. Tasks come *in* as JSON task requests; fleet and task state stream *out* over the websocket. This is what a web dashboard (or your operator UI in Week 43) talks to — and what the `dispatch_delivery` CLI tool POSTs to. Everything below the API server is ROS2; the API server is the boundary where the fleet meets the outside world.

Why a JSON/web boundary instead of exposing ROS2 directly? Because the consumers of a fleet manager — a web dashboard, a warehouse management system, a delivery app — are not ROS2 systems. They speak HTTP and JSON. The API server is the *translation layer* that lets a non-robotics system (an inventory database deciding "robot, fetch SKU-4471 to dock 3") submit a task without knowing anything about DDS, QoS, or topics. This separation also means the fleet's *internals* can change (swap a fleet adapter, retune the schedule) without breaking the external API contract — the same reason any system puts a stable API in front of a changing implementation. For the capstone, your `/fleet/heartbeat` schema and any task-submission interface are the C24 analogue of this boundary: a documented contract the outside world talks to.

---

## Part 2 — Bringing a fleet up

You will use the reference demos and adapt them. The fast path is the `rmf_demos` office world, which ships two fleets.

### 2.1 Install and launch the reference

```bash
sudo apt install ros-jazzy-rmf-demos ros-jazzy-rmf-demos-fleet-adapter \
                 ros-jazzy-rmf-demos-maps ros-jazzy-rmf-traffic-ros2 \
                 ros-jazzy-rmf-task-ros2 ros-jazzy-rmf-fleet-adapter

# Launch the office world: Gz Sim + two fleets + schedule + dispatcher + API server.
ros2 launch rmf_demos_gz office.launch.xml
```

Confirm the stack is up:

```bash
ros2 node list | grep -E "rmf|fleet|dispatcher|schedule"
# .../rmf_traffic_schedule
# .../rmf_dispatcher_node
# .../tinyRobot_fleet_adapter        (one fleet)
# .../deliveryRobot_fleet_adapter    (another fleet)
```

Watch every robot's RMF-reported state:

```bash
ros2 topic echo /fleet_states
# Each robot: name, mode (IDLE/MOVING/...), battery_percent, location, task_id
```

### 2.2 Submit a task through the API

The clean way (matches the syllabus "submit tasks via the fleet API") is the demo dispatch tools, which POST a JSON task request to `rmf_api_server`:

```bash
# Dispatch a delivery: pick up at the pantry, drop at a desk.
ros2 run rmf_demos_tasks dispatch_delivery \
  -p pantry -ph coke_dispenser \
  -d hardware_2 -dh coke_ingestor \
  --use_sim_time

# Dispatch a simpler patrol (good for first contact):
ros2 run rmf_demos_tasks dispatch_patrol -p north_west south_east -n 1 --use_sim_time
```

Under the hood this is a JSON request like:

```json
{
  "type": "dispatch_task_request",
  "request": {
    "category": "delivery",
    "description": {
      "pickup":  {"place": "pantry",      "handler": "coke_dispenser", "payload": []},
      "dropoff": {"place": "hardware_2",   "handler": "coke_ingestor",  "payload": []}
    }
  }
}
```

The dispatcher receives it, runs bidding across the fleets that can do a `delivery`, and assigns it to the lowest-cost bidder. Watch `/fleet_states` and you'll see a robot's mode change to `MOVING` and its `task_id` populate. **That assignment is Lecture 1's auction, running for real.**

### 2.3 Writing a fleet adapter (the EasyFullControl shape)

For your own Nav2 robot, you write a **full-control** adapter. `EasyFullControl` reduces this to: (1) configure the fleet (nav graph, robot kinematics, battery model), (2) provide a callback that, given a destination, commands the robot's Nav2 to go there, and (3) provide a callback that reports the robot's current position and battery. Conceptually:

```python
# Conceptual shape of a full-control adapter using rmf_adapter (Python).
# This is the structure, not a drop-in; the exercise points at the live API.
import rmf_adapter.easy_full_control as easy

def make_fleet():
    # 1) Configure the fleet from a config file (nav graph, kinematics, battery).
    fleet_config = easy.FleetConfiguration.from_config_files(
        "fleet_config.yaml", "nav_graph.yaml"
    )
    adapter = easy.EasyFullControl.make(fleet_config, ...)

    # 2) navigate callback: RMF hands you a destination; you drive Nav2 there.
    def navigate(destination, execution):
        # Send a NavigateToPose goal to THIS robot's Nav2 action server.
        send_nav2_goal(destination.position)         # (x, y, yaw)
        # When Nav2 reports success, call execution.finished().
        on_nav2_done(lambda: execution.finished())

    # 3) the adapter periodically asks the robot for its state (pose + battery),
    #    which you read from /amcl_pose (or /odom) and a battery topic.
    return adapter
```

The honest note for 2026: the `rmf_adapter` Python API has evolved across releases, and the exact symbols shift. **Do not memorize the API; understand the contract** — RMF needs three things from you: *where is the robot*, *make the robot go here*, *tell me when it arrived*. Any version of the adapter is those three callbacks. Read the version of `rmf_fleet_adapter_python` you actually installed; the *shape* above is invariant.

---

## Part 3 — Conflict resolution: the shared corridor

This is the part that separates a fleet manager from N independent robots. Two robots, one narrow corridor, both want it at overlapping times.

### 3.1 How the schedule detects the conflict

Each robot's fleet adapter submits its planned trajectory to `rmf_traffic_schedule`. When robot 1 reserves "corridor cells, t=10–14s" and robot 2 tries to reserve "the same cells, t=11–15s," the schedule sees the **space-time overlap** and flags a conflict. Note the key word *time*: two robots using the same corridor at *different* times is fine — the schedule only conflicts on overlap. This is why RMF reasons in space-time, not just space; a 2D costmap can't express "you may use this space, but not yet."

### 3.2 The negotiation

On a detected conflict, `rmf_traffic` opens a **negotiation**. The conflicting participants propose alternative trajectories (wait here, take a different lane, slow down) and the negotiation searches for a jointly feasible set with the lowest combined cost. The outcome is one of:

- **One robot yields** — waits at a hold point (or slows) until the corridor clears, then proceeds. The robot with the higher cost-to-yield typically proceeds; the cheaper-to-delay one waits. This is the common outcome in a single corridor.
- **One robot reroutes** — if an alternative lane exists, the negotiation may route one robot around, so neither waits.
- **Both adjust timing** — staggered entry so they pass a wider section.

The decision is **cost-based**, not first-come-first-served: the negotiation minimizes total disruption, so it may make the robot that arrived *first* wait if that's globally cheaper. This sometimes surprises people watching the demo ("why did the one already there stop?") — because the schedule optimizes the *pair*, not either robot alone. Same lesson as the greedy-vs-Hungarian story in Lecture 1: joint optimization beats locally-greedy.

Why is the schedule allowed to make a robot wait that "got there first"? Because first-come-first-served is itself a *greedy* policy, and you saw in Lecture 1 §2 how greedy can be globally ruinous. Concretely: if robot A is doing a low-priority patrol and robot B is mid-delivery on a deadline, making A (which arrived first) yield to B costs A a few seconds of patrol and saves B's deadline — globally cheaper, even though A was "there first." A first-come scheduler would freeze B behind A and miss the deadline to honor an arbitrary ordering. The negotiation's cost function encodes "whose delay hurts least," and that's the right thing to optimize. The same instinct that rejects greedy task allocation rejects first-come deconfliction.

A subtlety worth flagging: the negotiation needs *room* to find a solution. If the map offers no passing place and no alternative lane, the negotiation's search space is empty — there is no jointly-feasible set of trajectories — and you get a deadlock (§3.4). The negotiation is only as good as the map's flexibility; a rich nav graph (passing bays, one-way lanes) gives the negotiation options, and a starved one (a single bidirectional corridor) gives it none. This is why deadlock fixes are map fixes (the challenge's whole point): you're not fixing the negotiation, you're giving it room to work.

### 3.3 Reading a negotiation

You observe conflicts and negotiations through RMF's debug/visualization tooling and the schedule topics. In the demo, the `rmf` rviz/web visualization draws each robot's reserved trajectory; when a negotiation runs, you can see one robot's trajectory grow a *wait* segment. From the terminal, the schedule node and the fleet adapters log negotiation events. The challenge this week (`challenge-01-corridor-deadlock.md`) walks you through forcing a corridor conflict and reading which robot yielded and why.

### 3.4 When deconfliction fails: deadlock

Deconfliction can *fail* — most classically a **deadlock**: robot 1 waits for robot 2 to clear a corridor, robot 2 waits for robot 1 to clear the *other end*, neither moves. A well-configured nav graph (with passing places, one-way lanes at pinch points, and adequate hold points) prevents most deadlocks by construction; the negotiation prevents the rest by having one robot reroute or back off. But a badly authored map (a single bidirectional corridor with no passing place and tasks that send robots through it in opposite directions) *will* deadlock, and the symptom is two robots frozen nose-to-nose with the schedule unable to find a feasible joint plan. The fix is almost always **map-level** (add a passing place, make the pinch one-way), not code-level — a critical lesson the challenge drives home.

---

## Part 4 — Failure handling and reallocation

The syllabus lab: "inject a robot-stalls event and verify reallocation." This is the capability that makes a fleet *robust* rather than merely *coordinated*.

### 4.1 Detecting a dead or wedged robot

A robot can fail two ways, and they need different detection:

- **Process/comms death** — the robot's adapter stops reporting. RMF's robot state goes stale: no `/fleet_states` update for that robot. This is detectable by a **timeout** on the state report (the heartbeat lesson, §5).
- **Wedged-but-alive** — the robot still reports state, but it isn't making progress on its task (stuck against an obstacle, planner cycling, motor fault). This needs a **progress** check: the task's expected-completion-time is blown, or the robot's position hasn't advanced. RMF tracks task progress; a task `underway` whose robot isn't moving toward the goal is a stall.

The two failure modes map onto the two detection mechanisms cleanly:

| Failure | Symptom | Detector | QoS mechanism (Week 5) |
|---|---|---|---|
| Process/comms death | No state updates at all | Staleness timeout on last-seen | Missed `deadline` + lost liveliness lease |
| Wedged-but-alive | State updates, no progress | Progress/ETA check on the task | (heartbeat alone won't catch — needs progress) |

This is why a heartbeat *and* a progress check are both needed: the heartbeat catches the robot that went *silent*, but a robot that keeps heartbeating while stuck against a wall is *not* silent — it needs the progress check to catch. A fleet manager that only watched heartbeats would happily believe a wedged-but-chatty robot is fine while its task never completes. Both terminate in the same place: the task the robot was doing must be considered **failed/orphaned** and re-dispatched.

### 4.2 Reallocation

When a robot's task is orphaned, the dispatcher re-runs bidding for that task across the *remaining healthy* fleet — exactly the SSI re-auction from Lecture 1 §4.3. The orphaned task goes back to `queued`, the dispatcher bids it out, and a healthy robot picks it up. Note how cleanly the Lecture 1 math pays off here: because the allocator was *incremental* (auction-based), re-allocating one orphaned task is one cheap auction, not a full re-solve of the whole fleet's assignment. Had you built a one-shot Hungarian allocator with no incremental path, a single robot dying would force you to re-solve the entire assignment — churning every other robot off its in-progress task. The auction's incrementality is exactly what makes graceful reallocation possible. The whole point of the week's "the fleet reallocated" promise:

```
[dispatcher] task delivery_3 ASSIGNED to robot2
[dispatcher] robot2 state STALE (last report 3.1s ago > 2.0s threshold)
[dispatcher] task delivery_3 ORPHANED — re-bidding among {robot1, robot3}
[dispatcher] task delivery_3 RE-ASSIGNED to robot1 (bid 4.2 < robot3 bid 6.8)
```

The **time bound** matters and is measured: how many seconds from "robot stalled" to "another robot picked up the task"? That latency is your detection threshold plus the bid+assign time plus the new robot's travel start. A fleet that *eventually* reallocates but takes two minutes is a bad fleet; the drill measures and bounds it. (This same recovery, on the capstone robot, is one half of the Week 46 chaos drill.)

### 4.3 What you can't always recover

Be honest about the limits. Reallocation cleanly handles a *not-yet-started* or *resumable* task (drive to pickup, grasp, deliver). It does **not** magically recover a task that left the world in a bad state — a robot that died holding a payload mid-corridor is now an *obstacle* the survivors must plan around, and the payload may need a human. A mature fleet manager distinguishes "reallocate the task" from "the failed robot is now a hazard to clear," and your reallocation logic should at minimum *flag* the second case rather than pretend it doesn't exist. This is the kind of nuance the Phase milestone reviewer probes.

Categorize the recoverability of an orphaned task before you reallocate it:

- **Not yet started** → fully recoverable. Re-bid it; a healthy robot does it from scratch. No residue.
- **Started but resumable** → re-bid with the partial progress noted (e.g., "pickup done, dropoff pending"); a healthy robot finishes the remainder. The world is in a known state.
- **Started and left the world in an unknown/bad state** → *not* cleanly recoverable. The dead robot may be blocking a corridor, holding a payload, or have half-completed an irreversible action. Flag for an operator; the survivors must at least plan *around* the dead robot as an obstacle.

A toy reallocator pretends every task is in the first category. A real one tracks which category an orphaned task is in and refuses to silently re-auction a category-three task — because re-running a "deliver the payload" task when the payload is stuck under a dead robot just sends a second robot to fail the same way. The exercise's "started task is flagged, not re-auctioned" rule is exactly this distinction in miniature.

---

## Part 5 — The fleet heartbeat (the Week 5 lesson, applied)

The capstone requires every robot to report identity, capabilities, and health on `/fleet/heartbeat` at 1 Hz, "conformant to a documented schema (Open-RMF-style)." You design that schema this week, and it is where Week 5's QoS literacy becomes load-bearing.

### 5.1 The schema

A heartbeat carries enough for a fleet manager to make allocation and health decisions:

```
# crunch_fleet_msgs/msg/Heartbeat.msg  (the shape; you'll define it for real)
std_msgs/Header header          # stamp at SEND time (this is a liveness signal)
string robot_id                 # "robot1" — stable identity
string fleet_id                 # "crunch_delivery"
string[] capabilities           # ["navigate", "grasp", "carry_10kg"]
float32 battery_percent         # 0..100
uint8 nav_state                 # 0=IDLE 1=MOVING 2=PAUSED 3=ERROR
string current_task_id          # "" if idle
geometry_msgs/Pose location     # in map frame
```

Identity (`robot_id`, `fleet_id`) lets the manager track *who*. Capabilities let the dispatcher bid only the robots that *can* do a task (don't auction a grasp task to a robot with no arm — set its cost to ∞, Lecture 1 §1.2). Health (`battery_percent`, `nav_state`) lets it pull a low-battery robot out of bidding and detect an `ERROR` state. The task id closes the loop with the dispatcher.

### 5.2 The QoS — and why liveliness matters here

Back to Week 5's taste test. A heartbeat is *almost* a diagnostics/telemetry topic, but with a twist: its **whole purpose is to detect a dead publisher.** So:

- **Reliability:** `RELIABLE` — you don't want to miss a heartbeat to a dropped UDP packet and false-alarm a healthy robot.
- **Durability:** `TRANSIENT_LOCAL` with depth 1 — a fleet manager that connects late immediately sees the current state of every robot (the "latest sticky" pattern, Week 5 Class 5).
- **Liveliness:** `MANUAL_BY_TOPIC` with a **lease just over the period** (e.g., 1 Hz heartbeat → ~2 s lease). This is the load-bearing choice. With `AUTOMATIC` liveliness, a robot whose publishing thread *wedged* but whose process is still alive would *still be reported live* — and lie to the fleet manager. `MANUAL_BY_TOPIC` requires the node to actively assert liveliness by publishing; if the publish loop wedges, the lease expires and the manager gets a liveliness-lost event. **This is exactly the Week 5 §3.6 lesson, and the capstone's heartbeat is its canonical use.**
- **Deadline:** set a deadline ~2× the period so the manager gets a `deadline_missed` event the moment a robot goes quiet — a second, independent staleness signal layered on liveliness.

So the failure detector is two-layered and *free* at the middleware level: a missed deadline (no message in 2 s) and a lost liveliness lease (publisher wedged) both fire events your dispatcher subscribes to, turning "robot died" into a callback rather than a polling loop you forgot to write. The mini-project builds exactly this.

---

## 6. Recap

You should now be able to:

- Draw the Open-RMF architecture and say what `rmf_traffic`, `rmf_traffic_schedule`, `rmf_task`/dispatcher, the fleet adapters, the nav graph, and `rmf_api_server` each do.
- Distinguish the three fleet-adapter control categories (full control / traffic light / read-only) and pick the right one for a given robot's level of onboard autonomy.
- Launch the `rmf_demos` reference fleet, submit a delivery via the API, and watch the dispatcher's bidding assign it.
- Explain how the space-time traffic schedule detects a corridor conflict and how a cost-based negotiation resolves it (yield / reroute / stagger), including why the first-arriving robot may be the one told to wait.
- Detect a stalled robot (state staleness vs. lack-of-progress), reallocate its orphaned task via re-bidding, measure the recovery latency, and name what reallocation *can't* recover.
- Design a fleet heartbeat schema and justify its QoS — including why `MANUAL_BY_TOPIC` liveliness is the correct choice for catching a wedged-but-alive robot.
- Categorize an orphaned task's recoverability (not-started / resumable / bad-state) and reallocate only what's safely reallocatable, flagging the rest.
- Explain the API server as the JSON/web boundary that lets non-ROS2 systems submit tasks, and relate it to the capstone's documented fleet interface.
- Choose a fleet-adapter category by *command authority* (not robot quality), and reason about a heterogeneous fleet mixing all three.

Pulling the two lectures together: **task allocation is the math (who does what), fleet management is the system that runs that math live (Open-RMF), and both reduce to the same instinct — centralize the global picture, reason about it jointly, and degrade gracefully when a part fails.** The cost matrix and the traffic schedule are the same idea (a global view to optimize over); the auction re-bid and the task reallocation are the same idea (incremental recovery); the heartbeat and the progress check are the same idea (detect failure as a signal, not a guess). A fleet is a distributed system with wheels, and you now have the vocabulary to architect and defend one.

One last framing for the interview you'll have someday. A robotics-startup interviewer who asks "design a fleet manager" is not looking for "I'd run the RMF demo." They want to hear the *decomposition*: a scheduler (who does what — task allocation), a deconfliction layer (who goes where, when — the traffic schedule), and a failure detector with reallocation (what happens when one dies — the heartbeat plus re-bidding). Name those three subsystems, explain each with the math and the system from these two lectures, and you've answered the question like a senior engineer. The Open-RMF specifics are the *evidence* you've thought about it for real; the three-subsystem decomposition is the *answer*. That decomposition is the durable thing to carry out of this week — frameworks change, but "schedule, deconflict, recover" is what a fleet manager always is.

Next: the exercises put the allocation math on a running graph and the fleet manager on your robots. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *The ROS 2 Multi-Robot Book (Open-RMF)*: <https://osrf.github.io/ros2multirobotbook/>
- *Open-RMF traffic management chapter*: <https://osrf.github.io/ros2multirobotbook/traffic-management.html>
- *Open-RMF fleet integration chapter (adapters)*: <https://osrf.github.io/ros2multirobotbook/integration_fleets.html>
- *`rmf_traffic` (schedule + negotiation source)*: <https://github.com/open-rmf/rmf_traffic>
- *`rmf_task` (dispatcher + bidding)*: <https://github.com/open-rmf/rmf_task>
- *`rmf_fleet_adapter_python` (EasyFullControl)*: <https://github.com/open-rmf/rmf_ros2/tree/main/rmf_fleet_adapter_python>
- *`rmf_demos` (reference fleets, dispatch tools)*: <https://github.com/open-rmf/rmf_demos>
- *QoS liveliness/deadline (Week 5 §3.6 demo)*: <https://docs.ros.org/en/jazzy/Tutorials/Demos/Quality-of-Service.html>
