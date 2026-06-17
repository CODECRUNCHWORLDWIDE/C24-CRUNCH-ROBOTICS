# Week 4 Homework

Six problems that revisit the week's topics from angles the exercises didn't cover. The full set should take about **5 hours**. Work in your Week 4 Git repo so each problem leaves at least one commit you can point to in review.

Each problem has a **statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — The ladder, defended in writing

**Statement.** Pick three capabilities from your eventual crunchbot — one that should be a topic, one a service, one an action — that were *not* in Exercise 1's list. For each, write a short paragraph (`notes/ladder-defense.md`) naming the rung and defending it against the rung above and below it. Example shape: "X is a service, not a topic, because the caller needs confirmation; not an action, because the work is sub-millisecond and never needs cancelling."

**Acceptance criteria.**
- `notes/ladder-defense.md` exists with three capabilities, three labels, and three defences that explicitly rule out the adjacent rungs.

**Hint.** The defence that rules out the *adjacent* rungs is the hard part and the valuable part. Anyone can say "this is an action." The skill is "this is an action and not a service because…".

**Estimated time.** 30 minutes.

---

## Problem 2 — Reproduce the deadlock and write the postmortem

**Statement.** Run your Exercise 2 server (single-threaded, default callback group). Send a goal large enough to take several seconds, then cancel it mid-execution. Observe that the cancel is not honored and the robot keeps turning. Write a one-page postmortem (`notes/cancel-deadlock-postmortem.md`) with: what you observed, the exact chain of "A waits for B, B can't run because A holds the only thread," and the two-part fix (multi-threaded executor + callback-group assignment).

**Acceptance criteria.**
- The postmortem names *both* root causes (the blocked execute callback and the same-group serialization) and *both* parts of the fix.
- It includes the terminal output showing the cancel being ignored.

**Hint.** The postmortem is more valuable if you also explain why naively adding a `MultiThreadedExecutor` *without* changing callback groups does not fully fix it.

**Estimated time.** 45 minutes.

---

## Problem 3 — Make the controller honest about the ±π wrap

**Statement.** In a standalone `pytest` file (`homework/test_angular_distance.py`), write tests for `shortest_angular_distance(frm, to)` (lift the function from Exercise 2). Cover: a small positive error, a small negative error, an error just under +π, an error just over -π (i.e. the wrap), `frm == to` (zero), and `frm` and `to` on opposite sides of the ±π discontinuity (e.g. `frm = 3.0`, `to = -3.0`, where the shortest path is the short way around, not 6 radians). Assert the result is always in `(-π, π]`.

**Acceptance criteria.**
- At least six test cases, all passing under `pytest homework/test_angular_distance.py`.
- One test specifically exercises the `frm = 3.0, to = -3.0` wrap and asserts the magnitude is small (≈ 0.283 rad), not ≈ 6 rad.

**Hint.** If your function returns ≈ 6 rad for `(3.0, -3.0)`, your wrap normalization is wrong — the robot would spin the long way around. That bug is exactly why this test exists.

**Estimated time.** 40 minutes.

---

## Problem 4 — A state-aware goal callback

**Statement.** Write a minimal `rclpy` action server (any trivial action — a 1-second countdown is fine, define a tiny `.action` or reuse `Spin90`) whose `goal_callback` rejects goals unless an internal `self._ready` flag is `True`. Add a service `set_ready` (`std_srvs/SetBool`) that flips the flag. Demonstrate from the CLI: send a goal (rejected), call `set_ready` with `true`, send the goal again (accepted). This is the gate mechanism the lifecycle challenge formalizes.

**Acceptance criteria.**
- A terminal transcript (`notes/goal-gate.md`) showing: goal rejected → `set_ready true` → goal accepted.
- The `goal_callback` returns `GoalResponse.REJECT` based on state, with a logged reason.

**Hint.** `std_srvs/srv/SetBool` is already built into ROS2; you don't need to define it. `ros2 service call /set_ready std_srvs/srv/SetBool "{data: true}"`.

**Estimated time.** 45 minutes.

---

## Problem 5 — Drive transitions from a launch file

**Statement.** Take your challenge lifecycle node (or a fresh minimal `LifecycleNode`). Write a launch file `launch/bringup.launch.py` that starts the node *and* uses `launch_ros` lifecycle events (or a small manager node) to drive it from `unconfigured → inactive → active` automatically on launch. Verify with `ros2 lifecycle get` that the node is `active` shortly after launch with no manual `ros2 lifecycle set` commands.

**Acceptance criteria.**
- `ros2 launch <pkg> bringup.launch.py` leaves the node in `active` with no manual transitions.
- The launch file logs each transition as it happens.

**Hint.** `launch_ros.event_handlers.OnStateTransition` and `launch_ros.events.lifecycle.ChangeState` let you chain transitions in a launch file; or write a tiny manager node that calls the `change_state` service in order. Either is acceptable.

**Estimated time.** 60 minutes.

---

## Problem 6 — When NOT to compose

**Statement.** Write a short note (`notes/composition-tradeoffs.md`) answering: (a) what concrete benefit intra-process composition gives you, and for which kind of message it matters most; (b) one concrete scenario where you would deliberately *not* compose two nodes into one process, and what you gain by keeping them separate. Ground both in your motion-primitives package — would you compose the lifecycle manager into the same container as the primitives? Why or why not?

**Acceptance criteria.**
- The note names the zero-copy intra-process benefit and ties it to large messages (point clouds, images), not small ones (a `Twist`).
- It names fault isolation as the cost of composition and gives one scenario where isolation wins.
- It takes a defended position on whether the lifecycle manager belongs in the primitives' container.

**Hint.** The honest answer for the lifecycle manager: keep it separate, because a supervisor that shares a process with the nodes it supervises cannot restart them if their process dies — it dies with them.

**Estimated time.** 30 minutes.

---

## Rubric (per problem and overall)

Each problem is graded on a 4-point scale:

| Score | Meaning |
|------:|---------|
| **4** | Meets every acceptance criterion; reasoning is correct and concrete; code runs clean. |
| **3** | Meets the criteria with a minor gap (a missing edge-case test, a thin justification). |
| **2** | Partially complete; the core idea is present but a key criterion is unmet (e.g. the deadlock postmortem names only one root cause). |
| **1** | Attempted but the central concept is wrong (e.g. a "service" that loops for ten seconds, a goal gate that doesn't actually gate). |
| **0** | Not attempted. |

**Overall pass bar:** 18 / 24 across the six problems, with **no problem below 2**. A zero or a one on the deadlock postmortem (P2) or the goal gate (P4) is an automatic re-do — those are the load-bearing concepts the mini-project depends on.

**Deliverables checklist.**

- [ ] `notes/ladder-defense.md` (P1)
- [ ] `notes/cancel-deadlock-postmortem.md` + terminal output (P2)
- [ ] `homework/test_angular_distance.py` passing (P3)
- [ ] `notes/goal-gate.md` transcript + the gated server code (P4)
- [ ] `launch/bringup.launch.py` driving auto-transitions (P5)
- [ ] `notes/composition-tradeoffs.md` (P6)
- [ ] Each is its own commit with a clear message.
