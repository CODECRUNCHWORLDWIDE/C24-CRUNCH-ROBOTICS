#!/usr/bin/env python3
# Exercise 2 — A minimal behavior-tree tick engine, with a self-check
#
# Goal: A COMPLETE, CORRECT minimal BT engine implementing the semantics from
#       Lecture 1: the three statuses, Sequence (with memory), Fallback,
#       ReactiveSequence, Parallel, and the Inverter / Timeout decorators. A
#       self-checking harness PROVES each control node behaves per the lecture —
#       especially that ReactiveSequence re-ticks and HALTS, where Sequence does not.
#
# Estimated time: 45 minutes. Runnable. Pure Python 3.12, no dependencies.
#
# WHY BUILD THE ENGINE? Because the semantics are subtle (memory vs. reactive,
# halting), and you only trust them once you've implemented them. BehaviorTree.CPP
# does exactly this in C++; here you do it in 200 lines of Python to learn it cheaply.
#
# HOW TO USE THIS FILE
#
#       python3 exercise-02-tick-engine.py
#
# It builds several trees, ticks them, and asserts the resulting behavior matches
# the lecture. It ends with "[OK] all self-checks passed".
#
# ACCEPTANCE CRITERIA
#
#   [ ] Running it prints the per-node semantics demos and ends with all checks OK.
#   [ ] The ReactiveSequence demo shows the action HALTED when the condition fails,
#       while the Sequence demo shows the action NOT halted (memory) — the core
#       distinction from Lecture 1 §3.4.
#   [ ] You can point to where halt() is called and explain why it stops the robot.
#
# Expected output is at the bottom of the file.

from __future__ import annotations
from enum import Enum
from typing import Callable, List, Optional


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


# --------------------------------------------------------------------------- #
# Base node
# --------------------------------------------------------------------------- #
class Node:
    def __init__(self, name: str):
        self.name = name

    def tick(self) -> Status:
        raise NotImplementedError

    def halt(self) -> None:
        """Called when this node is interrupted (e.g., by a reactive parent)."""
        pass


# --------------------------------------------------------------------------- #
# Leaves
# --------------------------------------------------------------------------- #
class Condition(Node):
    """A synchronous condition: returns SUCCESS/FAILURE from a predicate, never RUNNING."""

    def __init__(self, name: str, predicate: Callable[[], bool]):
        super().__init__(name)
        self.predicate = predicate

    def tick(self) -> Status:
        return Status.SUCCESS if self.predicate() else Status.FAILURE


class Action(Node):
    """An async action: returns RUNNING for `duration` ticks, then a terminal status.
    Tracks whether it was halted, so the self-checks can verify reactive interruption.
    """

    def __init__(self, name: str, duration: int, result: Status = Status.SUCCESS):
        super().__init__(name)
        self.duration = duration
        self.result = result
        self.ticks_run = 0
        self.was_halted = False
        self.running = False

    def tick(self) -> Status:
        self.running = True
        self.ticks_run += 1
        if self.ticks_run >= self.duration:
            self.running = False
            return self.result
        return Status.RUNNING

    def halt(self) -> None:
        # THIS is what stops the robot: a reactive parent interrupted us.
        if self.running:
            self.was_halted = True
        self.running = False
        self.ticks_run = 0   # reset so a restart begins cleanly


# --------------------------------------------------------------------------- #
# Control nodes
# --------------------------------------------------------------------------- #
class Sequence(Node):
    """Sequence WITH MEMORY: resume at the running child on re-tick; AND semantics."""

    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children
        self.current = 0

    def tick(self) -> Status:
        while self.current < len(self.children):
            status = self.children[self.current].tick()
            if status == Status.RUNNING:
                return Status.RUNNING
            if status == Status.FAILURE:
                self._reset()
                return Status.FAILURE
            self.current += 1   # child succeeded; advance (memory)
        self._reset()
        return Status.SUCCESS

    def _reset(self):
        self.current = 0

    def halt(self):
        for c in self.children:
            c.halt()
        self._reset()


class Fallback(Node):
    """Fallback: try children in order; succeed on first SUCCESS; OR semantics."""

    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children
        self.current = 0

    def tick(self) -> Status:
        while self.current < len(self.children):
            status = self.children[self.current].tick()
            if status == Status.RUNNING:
                return Status.RUNNING
            if status == Status.SUCCESS:
                self._reset()
                return Status.SUCCESS
            self.current += 1   # child failed; try the next
        self._reset()
        return Status.FAILURE

    def _reset(self):
        self.current = 0

    def halt(self):
        for c in self.children:
            c.halt()
        self._reset()


class ReactiveSequence(Node):
    """ReactiveSequence: re-tick ALL children from the left every tick. If a child
    fails, HALT any later running children. This is the yield-enabling node."""

    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children

    def tick(self) -> Status:
        for i, child in enumerate(self.children):
            status = child.tick()
            if status == Status.FAILURE:
                # Halt every child AFTER this one that might be running.
                for later in self.children[i + 1:]:
                    later.halt()
                return Status.FAILURE
            if status == Status.RUNNING:
                # Halt children after a running one? No — they haven't ticked.
                return Status.RUNNING
            # SUCCESS: continue to the next child this same tick.
        return Status.SUCCESS

    def halt(self):
        for c in self.children:
            c.halt()


class Parallel(Node):
    """Parallel: tick all children; succeed at success_threshold; fail at failure_threshold."""

    def __init__(self, name: str, children: List[Node],
                 success_threshold: int, failure_threshold: int):
        super().__init__(name)
        self.children = children
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold

    def tick(self) -> Status:
        successes = failures = 0
        for c in self.children:
            s = c.tick()
            if s == Status.SUCCESS:
                successes += 1
            elif s == Status.FAILURE:
                failures += 1
        if successes >= self.success_threshold:
            self.halt()
            return Status.SUCCESS
        if failures >= self.failure_threshold:
            self.halt()
            return Status.FAILURE
        return Status.RUNNING

    def halt(self):
        for c in self.children:
            c.halt()


# --------------------------------------------------------------------------- #
# Decorators
# --------------------------------------------------------------------------- #
class Inverter(Node):
    """Flip SUCCESS <-> FAILURE; pass RUNNING through."""

    def __init__(self, name: str, child: Node):
        super().__init__(name)
        self.child = child

    def tick(self) -> Status:
        s = self.child.tick()
        if s == Status.SUCCESS:
            return Status.FAILURE
        if s == Status.FAILURE:
            return Status.SUCCESS
        return Status.RUNNING

    def halt(self):
        self.child.halt()


class Timeout(Node):
    """Return FAILURE (and halt the child) if it runs longer than `max_ticks`."""

    def __init__(self, name: str, child: Node, max_ticks: int):
        super().__init__(name)
        self.child = child
        self.max_ticks = max_ticks
        self.elapsed = 0

    def tick(self) -> Status:
        self.elapsed += 1
        if self.elapsed > self.max_ticks:
            self.child.halt()
            self.elapsed = 0
            return Status.FAILURE
        s = self.child.tick()
        if s != Status.RUNNING:
            self.elapsed = 0
        return s

    def halt(self):
        self.child.halt()
        self.elapsed = 0


# --------------------------------------------------------------------------- #
# Self-checks
# --------------------------------------------------------------------------- #
def tick_until_done(root: Node, max_ticks: int = 50):
    """Tick the root until it returns a terminal status; return (status, ticks)."""
    for t in range(1, max_ticks + 1):
        s = root.tick()
        if s != Status.RUNNING:
            return s, t
    return Status.RUNNING, max_ticks


def main():
    # --- Sequence has memory: condition NOT re-checked after it passes ---------
    check_count = {"n": 0}

    def battery_ok():
        check_count["n"] += 1
        return True

    drive = Action("Drive", duration=4)
    seq = Sequence("seq", [Condition("Battery", battery_ok), drive])
    status, ticks = tick_until_done(seq)
    print(f"Sequence: status={status.value} after {ticks} ticks; "
          f"battery checked {check_count['n']} time(s)")
    assert status == Status.SUCCESS
    assert check_count["n"] == 1, "Sequence (memory) should check the battery ONCE"
    assert not drive.was_halted, "Sequence should NOT halt the drive"
    print("[OK] Sequence has memory: condition checked once, action not halted.")

    # --- ReactiveSequence re-checks AND halts the action ----------------------
    # The condition is true for ticks 1-2, false on tick 3+.
    state = {"tick": 0}

    def path_clear():
        state["tick"] += 1
        return state["tick"] < 3   # clear on ticks 1,2; blocked on 3+

    react_drive = Action("Drive", duration=10)
    rseq = ReactiveSequence("rseq", [Condition("PathClear", path_clear), react_drive])
    # Tick a few times manually to observe the halt.
    statuses = [rseq.tick() for _ in range(4)]
    print(f"ReactiveSequence statuses over 4 ticks: {[s.value for s in statuses]}")
    assert statuses[0] == Status.RUNNING and statuses[1] == Status.RUNNING
    assert statuses[2] == Status.FAILURE, "should FAIL when path blocks on tick 3"
    assert react_drive.was_halted, "ReactiveSequence MUST halt the running action"
    print("[OK] ReactiveSequence re-checks the condition AND halts the action (the yield).")

    # --- Fallback runs the recovery only on primary failure -------------------
    primary = Action("Primary", duration=1, result=Status.FAILURE)
    recovery = Action("Recovery", duration=2, result=Status.SUCCESS)
    fb = Fallback("fb", [primary, recovery])
    status, ticks = tick_until_done(fb)
    print(f"Fallback: status={status.value} after {ticks} ticks")
    assert status == Status.SUCCESS, "recovery should make the fallback succeed"
    print("[OK] Fallback runs recovery only after the primary fails, then succeeds.")

    # --- Inverter flips a condition -------------------------------------------
    inv = Inverter("inv", Condition("Always", lambda: True))
    assert inv.tick() == Status.FAILURE
    print("[OK] Inverter flips SUCCESS -> FAILURE.")

    # --- Timeout fires and halts ----------------------------------------------
    waiter = Action("Wait", duration=100)   # never finishes on its own
    to = Timeout("to", waiter, max_ticks=3)
    statuses = [to.tick() for _ in range(4)]
    print(f"Timeout statuses over 4 ticks: {[s.value for s in statuses]}")
    assert statuses[3] == Status.FAILURE, "Timeout should FAIL after max_ticks"
    assert waiter.was_halted, "Timeout must halt the child it timed out"
    print("[OK] Timeout fails after max_ticks and halts the child (the retreat trigger).")

    print("\n[OK] all self-checks passed.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# Sequence: status=SUCCESS after 4 ticks; battery checked 1 time(s)
# [OK] Sequence has memory: condition checked once, action not halted.
# ReactiveSequence statuses over 4 ticks: ['RUNNING', 'RUNNING', 'FAILURE', 'FAILURE']
# [OK] ReactiveSequence re-checks the condition AND halts the action (the yield).
# Fallback: status=SUCCESS after 2 ticks
# [OK] Fallback runs recovery only after the primary fails, then succeeds.
# [OK] Inverter flips SUCCESS -> FAILURE.
# Timeout statuses over 4 ticks: ['RUNNING', 'RUNNING', 'RUNNING', 'FAILURE']
# [OK] Timeout fails after max_ticks and halts the child (the retreat trigger).
#
# [OK] all self-checks passed.
#
# The two load-bearing results: (1) Sequence checks the condition ONCE (memory) and
# does NOT halt the action; (2) ReactiveSequence re-checks EVERY tick and HALTS the
# action when the condition fails. That halt is what stops the robot on a yield —
# the difference between a robot that yields and one that finishes driving into a
# person. Build this in your bones now; the C++ mini-project relies on it.
# -----------------------------------------------------------------------------
