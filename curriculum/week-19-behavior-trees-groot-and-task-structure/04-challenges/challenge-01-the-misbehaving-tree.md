# Challenge 1 — The Misbehaving Tree: Three Structural Bugs in a Patrol

**Time estimate:** ~90 minutes.

## Problem statement

You are on call. A teammate's patrol robot "mostly works" but does three unsettling things nobody can explain: it sometimes **finishes driving to the next waypoint before it stops for a person standing in front of it**; when a person lingers, it **waits forever and never retreats**; and occasionally it **stops when no one is there and drives right at people**. All three are **structural** bugs in the behavior tree — wrong control nodes, a missing decorator, an inverted condition — not bugs in any leaf's code.

You will run the faulty tree (in the Exercise-2/3 Python engine, or in BehaviorTree.CPP if you've built the mini-project), reproduce all three misbehaviors, then **diagnose and fix** each from the tree structure and Groot 2. This mirrors the real skill: you debug task logic you didn't write, from the outside, by *watching which branch the tree is in*.

## The faulty tree

Here is the broken patrol, in the Python engine's structure (the bugs are below; **don't read them until you've diagnosed each from the behavior**):

```python
# faulty_patrol.py — three planted structural bugs. Diagnose, then fix.
from exercise_03_patrol_blackboard import (
    Blackboard, Condition, Inverter, ReactiveSequence, Fallback,
    PatrolLoop, WaitForPersonToLeave, Retreat, Status,
)

# A plain (memory) Sequence, NOT reactive — needed for one of the bugs.
class Sequence:
    def __init__(self, children): self.children = children; self.current = 0
    def tick(self):
        while self.current < len(self.children):
            s = self.children[self.current].tick()
            if s == Status.RUNNING: return Status.RUNNING
            if s == Status.FAILURE: self.current = 0; return Status.FAILURE
            self.current += 1
        self.current = 0
        return Status.SUCCESS
    def halt(self):
        for c in self.children: c.halt()
        self.current = 0


def build_faulty_tree(bb):
    handle_person = Fallback([
        # BUG #3: the Inverter is MISSING here. The guard now passes (SUCCESS)
        # only when a person IS present, inverting the yield logic.
        Condition(lambda: bb["person_present"]),
        # BUG #2: the WaitForPersonToLeave is NOT wrapped in a Timeout, so the
        # robot waits forever and never retreats.
        WaitForPersonToLeave(bb),
    ])

    # BUG #1: a plain Sequence (memory), not a ReactiveSequence. The person check
    # is not re-evaluated while PatrolLoop runs, so the robot finishes the current
    # drive leg before noticing the person.
    patrol = Sequence([
        handle_person,
        PatrolLoop(bb),
    ])

    return Fallback([patrol, Retreat(bb)])
```

Run it through the Exercise-3 simulation driver (scenarios 1–3) and watch each misbehavior appear.

## Your task

For **each of the three bugs**, produce a diagnosis with these four parts:

1. **Symptom** — what's observably wrong (which scenario fails, what the robot does, what Groot 2 / the per-tick trace shows).
2. **Root cause** — which node is wrong and *why* it produces that symptom, stated mechanically (e.g., "a plain `Sequence` has memory, so it doesn't re-tick the person check while `PatrolLoop` runs `RUNNING`; the check is only evaluated at the start of each leg").
3. **The correct structure** — the node that should be there instead.
4. **Fix** — the corrected line, and how you'd *confirm* the fix (which scenario now passes).

You must reach each diagnosis using **at least two** independent signals — e.g., a failing scenario assertion *and* the per-tick trace (or Groot 2 showing the wrong branch green). One signal is a guess; two is a diagnosis.

## Acceptance criteria

- [ ] A file `challenge-01-diagnosis.md` with a section per bug, each containing all four parts above.
- [ ] You correctly identify each bug:
  - **#1** — plain `Sequence` instead of `ReactiveSequence`: the yield is not reactive, so the robot finishes the current drive leg before stopping for a person. **Symptom:** late yield.
  - **#2** — missing `Timeout` around the wait: the robot waits forever and never retreats. **Symptom:** scenario 3 never retreats.
  - **#3** — missing `Inverter` on the person condition: the guard logic is inverted, so the patrol runs only when a person IS present and stops when none is. **Symptom:** drives at people, stops when clear.
- [ ] For each bug you quote the failing scenario (the assertion that fires, or the per-tick trace showing the wrong behavior).
- [ ] A `fixed_patrol.py` where all three Exercise-3 scenario self-checks pass.
- [ ] Committed to your Week 19 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The trap is that bugs #1 and #3 produce *similar-looking* symptoms ("the robot's yielding is wrong") but have **opposite** root causes, and fixing one without the other leaves you confused. Bug #3 (missing `Inverter`) makes the robot stop when clear and drive when blocked — the logic is *backwards*. Bug #1 (non-reactive) makes the robot's yield *late* — the logic is right but the *timing* is wrong. If you fix the `Inverter` and the robot *still* yields late, don't assume your fix failed — re-check the control node: you fixed the polarity (#3) but not the reactivity (#1). **Two of these bugs are in the same subtree and mask each other's exact symptom; fix one, re-run all scenarios, then fix the next.** Diagnosing "the yield is broken" and stopping is the incomplete junior answer — there are *two distinct* yield bugs with two distinct fixes.

Also note: bug #2 (missing `Timeout`) has *no symptom at all* in scenarios 1 and 2 — it only manifests in scenario 3 (person stays). A bug that's invisible in two of three scenarios is exactly why you must trace *every* scenario, not just the happy path. "It works when I tested it" usually means "I didn't test the scenario where it breaks."

## Stretch

- Add a **Groot 2 monitor** to a BehaviorTree.CPP version of the faulty tree and *screenshot* each bug firing — the `Sequence` staying green through a person appearing (#1), the wait node green forever (#2), the wrong branch green when clear (#3). A picture of the bug is the strongest possible diagnosis.
- Introduce a fourth, subtler bug: a condition with a **side effect** (it increments a counter every tick). Show that under the `ReactiveSequence` it fires every tick and corrupts state — the "conditions must be side-effect-free" rule (Lecture 1 §6.2, mistake #3).
- Write a tiny test harness that runs all three scenarios and prints a pass/fail table, so fixing the tree becomes a red-to-green loop instead of manual tracing. This is how you'd actually develop a real task tree.

## Why this matters

In Week 24's Phase 3 integration and the capstone, your task tree is reviewed and must *demonstrably* do the right thing in every scenario — including the safety-critical ones (yield to a person, retreat when blocked). A tree that "looks right" but yields late, or never retreats, is a safety defect a reviewer will (and should) catch. This challenge *is* that review, rehearsed: take a tree you didn't write, run every scenario, watch Groot 2, and name the structural bug. Every robotics on-call rotation eventually hands you a misbehaving robot whose task logic is a tree someone else authored — and the engineer who can read the tree and name the bug in five minutes is the one who keeps the robot safe.
