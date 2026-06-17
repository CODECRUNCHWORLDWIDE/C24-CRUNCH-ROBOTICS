# Week 19 Homework

Six problems that revisit the week's topics and put behavior-tree authoring into your fingers. The full set should take about **5 hours**. Work in your Week 19 Git repository (the same workspace as the exercises and the `crunchbot_patrol` mini-project) so every problem produces at least one commit you can point to in the Phase 3 integration in Week 24.

The headline deliverable is **Problem 4 — the fail-safe-as-a-visible-branch declaration**, this week's Phase-3 fail-safe. Treat it as the artifact a safety reviewer reads, not a journal entry.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Problems 1–3 use the Python tick engine from the exercises (no ROS2 needed). Problems 5–6 use BehaviorTree.CPP and, ideally, a running Nav2 + perception stack; if your sim is broken, the Python engine is your fallback — say so in your writeup.

---

## Problem 1 — Convert an FSM to a BT

**Problem statement.** Take this FSM and re-express it as a behavior tree (draw it and implement it in the Exercise-2 engine): States `SEARCH`, `APPROACH`, `GRASP`, `RETREAT`. Transitions: `SEARCH→APPROACH` on object-found; `APPROACH→GRASP` on object-reached; `GRASP→RETREAT` on grasp-done; any state `→RETREAT` on battery-low. Write the tree in `notes/week-19/fsm-to-bt.md` (the tree diagram + the engine code) and explain how the "any state → RETREAT on battery-low" requirement maps to *one* node instead of four transitions.

**Acceptance criteria.**

- `notes/week-19/fsm-to-bt.md` has the FSM, the equivalent BT diagram, and runnable engine code.
- The battery-low guard is a *single* node (a `Sequence`-guard or a `Parallel` monitor), not replicated per state.
- A one-sentence statement of why the BT version is easier to extend.
- Committed.

**Hint.** Put the battery check at the top of the main `Sequence` so failing it fails the whole task and a `Fallback` routes to retreat — from anywhere, with one node. That's the modularity win from Lecture 1 §1.0.1.

**Estimated time.** 45 minutes.

---

## Problem 2 — Reactive vs. memory, measured

**Problem statement.** Build two versions of a "drive to waypoint, but stop if path blocks" tree: one with a plain `Sequence`, one with a `ReactiveSequence`. Script the path to block at tick 3 (while the drive action is `RUNNING`). For each, record on which tick the robot actually stops. Document in `notes/week-19/reactive-vs-memory.md`.

**Acceptance criteria.**

- Both trees implemented and run in the engine.
- You show the `Sequence` version stops *late* (only when the drive leg finishes) while the `ReactiveSequence` stops *immediately* on tick 3.
- A one-sentence rule for when to use each.
- Committed.

**Hint.** Make the drive action take 6 ticks. The plain `Sequence` won't re-check the condition until the drive returns (tick 6), so it stops 3 ticks late; the `ReactiveSequence` stops at tick 3. This is the bug from the Challenge, demonstrated on purpose.

**Estimated time.** 40 minutes.

---

## Problem 3 — Get scenario 2 right

**Problem statement.** Take the Exercise-3 patrol and deliberately *break* scenario 2 (person leaves within the timeout should *resume*, not retreat) by mis-structuring the wait subtree, then fix it. Document both the broken and fixed structures in `notes/week-19/scenario-2.md`, with the per-tick trace showing the broken version retreating and the fixed version resuming.

**Acceptance criteria.**

- `notes/week-19/scenario-2.md` shows a broken structure that retreats when the person leaves, and the fixed structure that resumes.
- You correctly identify that the wait must *succeed* (not fail) when the person leaves, so the patrol resumes.
- The fixed version passes all three Exercise-3 scenario self-checks.
- Committed.

**Hint.** The subtlety: `WaitForPersonToLeave` returns `SUCCESS` when the person is gone. If you instead wrap it so that "person gone" produces a `FAILURE` (e.g., an extra `Inverter`), the fallback routes to retreat. Trace it carefully — this is exactly the Lecture 2 §3.2 trap.

**Estimated time.** 45 minutes.

---

## Problem 4 — The fail-safe-as-a-visible-branch declaration (headline deliverable)

**Problem statement.** This is the syllabus's Phase-3 fail-safe for this week, framed around BT auditability: *the patrol must yield to people and retreat if blocked too long — and that fail-safe must be a visible, testable branch, not hidden callback code.* Write a one-page declaration at `notes/week-19/failsafe-yield-and-retreat.md` against this template:

1. **Hazard** — one sentence: what physically goes wrong if the robot doesn't yield to a person, or stalls forever in a doorway.
2. **The fail-safe as tree structure** — point to the *exact nodes* that implement it: the `ReactiveSequence` + `Inverter[IsPersonDetected]` (the yield) and the `Timeout(60s)` + `Fallback`→retreat (the recovery). Quote the XML/structure.
3. **Detection latency** — at your tick rate (e.g., 20 Hz), how fast does the yield fire after a person is detected? State the number (e.g., ≤50 ms) and how it follows from the tick rate.
4. **Why it's auditable** — explain that a reviewer can *see* the fail-safe in the tree and *watch* it fire in Groot 2, versus an FSM where the same logic is smeared across callbacks.
5. **Residual risk** — what this does *not* cover (e.g., perception misses the person; the nav goal's `onHalted` fails to cancel and the robot coasts; a person appears in a blind spot).
6. **Test evidence** — the three scenarios passing (no person / person leaves / person stays), and ideally a Groot 2 screenshot of the yield firing.

**Acceptance criteria.**

- `notes/week-19/failsafe-yield-and-retreat.md` exists, fits on roughly one page (350–550 words), and hits all six headings.
- The "fail-safe as tree structure" section names the *specific* nodes, not "the tree handles it."
- The detection-latency section states a concrete number derived from the tick rate.
- The residual-risk section names at least one real gap (the `onHalted`-fails case is the strongest, tying back to Lecture 2 §1.2).
- Committed.

**Hint.** The strongest residual risk is the one from Lecture 2 §1.2: the tree "yields" (the action node halts) but if `NavigateToWaypoint::onHalted` doesn't cancel the Nav2 goal, the robot keeps driving. Your fail-safe is only as real as your action's halt handler — name that explicitly.

**Estimated time.** 1 hour.

---

## Problem 5 — Author a custom condition node in BehaviorTree.CPP

**Problem statement.** In a BT.CPP package, write a custom `IsBatteryLow` condition node that reads a battery topic (`sensor_msgs/BatteryState` or a `std_msgs/Float32` you publish) and returns `SUCCESS` when below a threshold. Register it, put it in a tiny tree that retreats when the battery is low, and run it with a Groot2 publisher. Confirm in Groot 2 that the condition flips when you publish a low value.

**Acceptance criteria.**

- The `IsBatteryLow` node compiles and is registered in a `BehaviorTreeFactory`.
- A tree using it loads and ticks; Groot 2 connects and shows the node flipping when you publish a low battery value.
- `notes/week-19/custom-condition.md` documents the node and a Groot 2 screenshot.
- Committed.

**Hint.** Keep the condition side-effect-free: a separate ROS2 subscription updates a member variable; the `tick()` just reads it and compares (Lecture 1 §6.2, mistake #3). Publish test values with `ros2 topic pub`.

**Estimated time.** 50 minutes.

---

## Problem 6 — Wire the patrol to one real Nav2 waypoint

**Problem statement.** Take your mini-project patrol tree (or a minimal version) and replace one `NavigateToWaypoint` leaf with Nav2's real `NavigateToPose` BT action node. Run it against your week-7 map in Gz Sim so the robot actually drives to one real waypoint, and confirm `onHalted` cancels the goal when you inject a yield (publish a person detection). Document in `notes/week-19/real-nav-leaf.md`.

**Acceptance criteria.**

- The patrol drives to a real waypoint via Nav2's `NavigateToPose`.
- Injecting a person detection halts the patrol and the robot *stops* (the Nav2 goal is cancelled, confirmed by `/cmd_vel` going to zero).
- `notes/week-19/real-nav-leaf.md` documents the run with the before/after `/cmd_vel`.
- Committed.

**Hint.** Nav2 ships BT nodes including `NavigateToPose` you can drop straight into your tree XML. The key test is the `onHalted` path: when your reactive guard fails, the Nav2 action must be cancelled — watch `/cmd_vel` go to zero, not coast. If it coasts, your halt isn't cancelling the goal.

**Estimated time.** 50 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — FSM to BT | 45 min |
| 2 — Reactive vs. memory | 40 min |
| 3 — Get scenario 2 right | 45 min |
| 4 — Fail-safe declaration (headline) | 1 h 0 min |
| 5 — Custom condition node | 50 min |
| 6 — Real Nav2 waypoint leaf | 50 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_patrol` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 24's integration imports it. Then take the [quiz](./05-quiz.md) with your notes closed.
