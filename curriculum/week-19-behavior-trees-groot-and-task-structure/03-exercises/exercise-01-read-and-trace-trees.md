# Exercise 1 — Read and Trace Trees by Hand

**Goal:** Build the single most important behavior-tree skill: reading a tree and predicting *exactly* what the robot will do, tick by tick, before you run it. You will trace five small trees by hand, write down the tick sequence and the resulting behavior, then verify against the tick engine (Exercise 2) and, optionally, Groot 2.

**Estimated time:** 50 minutes. Guided.

---

## How to trace a tree

For each tree, you'll produce a **trace table**: for each tick, which leaves get ticked and what status each node returns, ending in the root's status. Use the rules from Lecture 1:

- `Sequence` (memory): tick children left-to-right; fail on first `FAILURE`; on re-ticks, *resume at the running/next child* (don't re-tick succeeded children).
- `Fallback`: tick left-to-right; succeed on first `SUCCESS`; fail only if all fail.
- `ReactiveSequence`: re-tick *all* children from the left *every* tick; a child's `FAILURE` halts later running children.
- `Inverter`: flip `SUCCESS` ↔ `FAILURE`; pass `RUNNING` through.
- `Timeout(t)`: return `FAILURE` if the child runs longer than `t`.

---

## Tree 1 — Basic Sequence

```
Sequence
├── CheckBattery   (returns SUCCESS)
└── DriveForward   (returns RUNNING for 3 ticks, then SUCCESS)
```

**Predict:** what does the root return on ticks 1, 2, 3, 4? Does `CheckBattery` get re-ticked on tick 2? Write the trace table.

<details><summary>Answer</summary>

| Tick | CheckBattery | DriveForward | Root (Sequence) |
|---|---|---|---|
| 1 | SUCCESS | RUNNING | RUNNING |
| 2 | *(not ticked — memory)* | RUNNING | RUNNING |
| 3 | *(not ticked)* | RUNNING | RUNNING |
| 4 | *(not ticked)* | SUCCESS | SUCCESS |

A plain `Sequence` has memory: after `CheckBattery` succeeds on tick 1, it resumes at `DriveForward` and does *not* re-check the battery. This is the behavior you do *not* want for a reactive yield.

</details>

---

## Tree 2 — Fallback recovery

```
Fallback
├── DriveToGoal    (returns FAILURE on tick 1 — path blocked)
└── SpinRecovery   (returns RUNNING for 2 ticks, then SUCCESS)
```

**Predict:** which child runs, and what does the root return on each tick?

<details><summary>Answer</summary>

| Tick | DriveToGoal | SpinRecovery | Root (Fallback) |
|---|---|---|---|
| 1 | FAILURE | RUNNING | RUNNING |
| 2 | *(not re-ticked — memory)* | RUNNING | RUNNING |
| 3 | *(not re-ticked)* | SUCCESS | SUCCESS |

The `Fallback` only ticks `SpinRecovery` *because* `DriveToGoal` failed. The recovery runs to completion and the root succeeds.

</details>

---

## Tree 3 — Reactive yield (the key tree)

```
ReactiveSequence
├── IsPathClear     (SUCCESS on ticks 1-2, FAILURE on tick 3, SUCCESS on tick 4+)
└── DriveForward    (RUNNING while ticked)
```

**Predict:** what happens on tick 3 when `IsPathClear` fails? Is `DriveForward` halted? What does the root return on tick 4?

<details><summary>Answer</summary>

| Tick | IsPathClear | DriveForward | Root (ReactiveSequence) |
|---|---|---|---|
| 1 | SUCCESS | RUNNING | RUNNING |
| 2 | SUCCESS | RUNNING | RUNNING |
| 3 | FAILURE | **HALTED** | FAILURE |
| 4 | SUCCESS | RUNNING (restarted) | RUNNING |

This is the whole point of `ReactiveSequence`: `IsPathClear` is re-checked *every* tick. On tick 3 it fails, so the `ReactiveSequence` returns `FAILURE` and **halts** the running `DriveForward` (the robot stops). On tick 4 the path clears, the sequence restarts, and driving resumes. Compare to Tree 1 — a plain `Sequence` would never have re-checked the condition.

</details>

---

## Tree 4 — Inverter + condition

```
ReactiveSequence
├── Inverter
│   └── IsPersonDetected   (FAILURE when no person, SUCCESS when person present)
└── Patrol                 (RUNNING)
```

**Predict:** with no person, does `Patrol` run? When a person appears, what happens?

<details><summary>Answer</summary>

- **No person:** `IsPersonDetected` → `FAILURE`; `Inverter` flips to `SUCCESS`; the `ReactiveSequence` proceeds to `Patrol` (`RUNNING`). The robot patrols.
- **Person appears:** `IsPersonDetected` → `SUCCESS`; `Inverter` flips to `FAILURE`; the `ReactiveSequence` returns `FAILURE` and halts `Patrol`. The robot stops (yields).

The `Inverter` turns "is a person detected" into the guard "is *no* person detected" so the patrol runs only when the path is person-free. This is the yield pattern's core.

</details>

---

## Tree 5 — Timeout to recovery

```
Fallback
├── Timeout(60s)
│   └── WaitForPersonToLeave   (RUNNING while person present)
└── RetreatToCharger           (RUNNING then SUCCESS)
```

**Predict:** if the person leaves at 30 s, what happens? If they stay past 60 s?

<details><summary>Answer</summary>

- **Person leaves at 30 s:** `WaitForPersonToLeave` returns `SUCCESS` (person gone) before the timeout, so `Timeout` returns `SUCCESS`, the `Fallback` succeeds, and `RetreatToCharger` is *never* reached. (In the real patrol this success resumes the patrol.)
- **Person stays past 60 s:** `Timeout(60s)` fires, returning `FAILURE` (it halts the wait). The `Fallback` moves to `RetreatToCharger`, which runs. The robot retreats.

This is the fail-safe as pure tree structure: a `Timeout` decorator plus a `Fallback` branch. No special-case code — the safety behavior is *in the tree*, visible and testable.

</details>

---

## Step — Verify with the tick engine

Take Tree 3 (the reactive yield) and reproduce it in Exercise 2's tick engine. Script `IsPathClear` to fail on tick 3, run it, and confirm the engine's trace matches your hand-trace — especially that `DriveForward` is halted on tick 3. If they disagree, *your hand-trace was wrong* (the engine is the reference) — figure out which rule you misapplied.

## Step (optional) — Verify in Groot 2

Author Tree 3 in Groot 2's editor. Even without a running C++ tree, drawing it forces you to place the `ReactiveSequence` and reason about which nodes re-tick. If you run the mini-project's tree later, connect Groot 2 in Monitor mode and *watch* the reactive yield fire — the `IsPathClear` node flipping red and `DriveForward` halting, in real time.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You produced a trace table for all five trees and your answers match the revealed ones (or you can explain a defensible difference).
- [ ] You can state, in one sentence, why Tree 3's `ReactiveSequence` yields but Tree 1's `Sequence` would not.
- [ ] You reproduced Tree 3 in the Exercise 2 tick engine and the engine's trace matched your hand-trace (`DriveForward` halted on the condition's failure tick).
- [ ] You can point to the exact node in Tree 5 that *is* the fail-safe (the `Timeout`, routing the `Fallback` to retreat).

---

## Stretch

- Trace a tree with a `Parallel` node running `Patrol` and `MonitorBattery` with `failure_count=1`; predict what happens when `MonitorBattery` fails mid-patrol.
- Build a deliberately *wrong* tree: put the reactive yield under a plain `Sequence` instead of `ReactiveSequence`, trace it, and show the robot finishes driving to the waypoint *before* noticing the person — the bug you'll diagnose in the Challenge.
- Author a five-waypoint patrol (loop with `Repeat`) and trace one full lap plus a yield mid-lap; confirm the patrol resumes at the *right* waypoint after the yield.

---

When this feels comfortable, move to [Exercise 2 — The tick engine](./exercise-02-tick-engine.py).
