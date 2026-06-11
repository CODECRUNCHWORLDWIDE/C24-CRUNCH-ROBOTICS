#!/usr/bin/env python3
# Exercise 3 — The patrol with yield and retreat (blackboard-driven simulation)
#
# Goal: Build the FULL syllabus task in the Exercise-2 tick engine: patrol three
#       waypoints; if a person is detected, PAUSE and wait until they leave; if the
#       pause exceeds the timeout, RETREAT to a charger. A blackboard carries the
#       waypoints and the person state. Self-checks verify ALL THREE scenarios.
#
# Estimated time: 50 minutes. Runnable. Pure Python 3.12 (reuses the Ex-2 engine
# semantics, reimplemented here so this file is standalone).
#
# THE THREE SCENARIOS THE TASK MUST EXHIBIT (Lecture 2 §3.2)
#   1. No person: patrol the waypoints, loop forever.
#   2. Person appears then LEAVES within the timeout: pause, then RESUME the patrol.
#   3. Person STAYS past the timeout: RETREAT to the charger.
# Getting scenario 2 right (resume, not retreat) is the subtle part the lecture
# flagged; this file gets it right and the self-check proves it.
#
# HOW TO USE THIS FILE
#
#       python3 exercise-03-patrol-blackboard.py
#       python3 exercise-03-patrol-blackboard.py --person-at 5 --person-leaves 12
#       python3 exercise-03-patrol-blackboard.py --person-at 5 --person-leaves 999 \
#               --timeout 20    # person never leaves -> retreat
#
# ACCEPTANCE CRITERIA
#   [ ] Scenario 1 (no person): the robot visits waypoints and never retreats.
#   [ ] Scenario 2 (person leaves in time): the robot pauses then RESUMES patrol.
#   [ ] Scenario 3 (person stays): the robot RETREATS to the charger.
#   [ ] All three self-checks pass; ends with "[OK] all self-checks passed".
#
# Expected output is at the bottom of the file.

from __future__ import annotations
import argparse
from enum import Enum
from typing import Callable, List


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


# --------------------------------------------------------------------------- #
# Blackboard: the shared key-value store (Lecture 2 §2.1)
# --------------------------------------------------------------------------- #
class Blackboard(dict):
    pass


# --------------------------------------------------------------------------- #
# Engine (compact reimplementation of Exercise 2's semantics)
# --------------------------------------------------------------------------- #
class Node:
    def tick(self) -> Status: raise NotImplementedError
    def halt(self) -> None: pass


class Condition(Node):
    def __init__(self, fn: Callable[[], bool]): self.fn = fn
    def tick(self) -> Status:
        return Status.SUCCESS if self.fn() else Status.FAILURE


class Inverter(Node):
    def __init__(self, child: Node): self.child = child
    def tick(self) -> Status:
        s = self.child.tick()
        if s == Status.SUCCESS: return Status.FAILURE
        if s == Status.FAILURE: return Status.SUCCESS
        return Status.RUNNING
    def halt(self): self.child.halt()


class ReactiveSequence(Node):
    def __init__(self, children: List[Node]): self.children = children
    def tick(self) -> Status:
        for i, c in enumerate(self.children):
            s = c.tick()
            if s == Status.FAILURE:
                for later in self.children[i + 1:]:
                    later.halt()
                return Status.FAILURE
            if s == Status.RUNNING:
                return Status.RUNNING
        return Status.SUCCESS
    def halt(self):
        for c in self.children: c.halt()


class Fallback(Node):
    def __init__(self, children: List[Node]):
        self.children = children; self.current = 0
    def tick(self) -> Status:
        while self.current < len(self.children):
            s = self.children[self.current].tick()
            if s == Status.RUNNING: return Status.RUNNING
            if s == Status.SUCCESS: self.current = 0; return Status.SUCCESS
            self.current += 1
        self.current = 0
        return Status.FAILURE
    def halt(self):
        for c in self.children: c.halt()
        self.current = 0


class PatrolLoop(Node):
    """Drive the waypoints in order, looping. Each waypoint takes `drive_ticks`.
    Returns RUNNING forever (a patrol never 'succeeds'); halts cleanly on yield."""

    def __init__(self, bb: Blackboard, drive_ticks: int = 3):
        self.bb = bb
        self.drive_ticks = drive_ticks
        self.wp_index = 0
        self.progress = 0

    def tick(self) -> Status:
        wps = self.bb["waypoints"]
        self.progress += 1
        if self.progress >= self.drive_ticks:
            self.bb["last_visited"] = wps[self.wp_index]
            self.bb.setdefault("visits", []).append(wps[self.wp_index])
            self.wp_index = (self.wp_index + 1) % len(wps)
            self.progress = 0
        return Status.RUNNING

    def halt(self):
        # The robot stops where it is; on resume it continues toward the same wp.
        # (Progress is preserved so we resume mid-leg, not restart the leg.)
        self.bb["patrol_halted"] = True


class WaitForPersonToLeave(Node):
    """RUNNING while a person is present; SUCCESS when they leave. Wrapped in a
    Timeout that turns 'stayed too long' into FAILURE -> retreat."""

    def __init__(self, bb: Blackboard):
        self.bb = bb

    def tick(self) -> Status:
        return Status.RUNNING if self.bb["person_present"] else Status.SUCCESS

    def halt(self):
        pass


class Timeout(Node):
    def __init__(self, child: Node, max_ticks: int):
        self.child = child; self.max_ticks = max_ticks; self.elapsed = 0
    def tick(self) -> Status:
        self.elapsed += 1
        if self.elapsed > self.max_ticks:
            self.child.halt(); self.elapsed = 0
            return Status.FAILURE
        s = self.child.tick()
        if s != Status.RUNNING:
            self.elapsed = 0
        return s
    def halt(self):
        self.child.halt(); self.elapsed = 0


class Retreat(Node):
    def __init__(self, bb: Blackboard, drive_ticks: int = 2):
        self.bb = bb; self.drive_ticks = drive_ticks; self.progress = 0
    def tick(self) -> Status:
        self.progress += 1
        if self.progress >= self.drive_ticks:
            self.bb["retreated"] = True
            self.bb["last_visited"] = self.bb["charger"]
            return Status.SUCCESS
        return Status.RUNNING
    def halt(self):
        self.progress = 0


# --------------------------------------------------------------------------- #
# Build the patrol-with-yield-and-retreat tree
# --------------------------------------------------------------------------- #
def build_tree(bb: Blackboard, timeout_ticks: int) -> Node:
    # handle_person: if no person -> SUCCESS (patrol continues); if person ->
    # wait (Timeout) until they leave (SUCCESS) or the timeout fires (FAILURE).
    handle_person = Fallback([
        Inverter(Condition(lambda: bb["person_present"])),   # no person -> SUCCESS
        Timeout(WaitForPersonToLeave(bb), timeout_ticks),    # person -> wait, gated
    ])

    patrol_with_yield = ReactiveSequence([
        handle_person,         # re-checked every tick: yields the instant a person appears
        PatrolLoop(bb),        # drives the waypoints
    ])

    # Fallback: try the patrol; if it ultimately fails (timeout), retreat.
    return Fallback([patrol_with_yield, Retreat(bb)])


# --------------------------------------------------------------------------- #
# Simulation driver
# --------------------------------------------------------------------------- #
def run(person_at: int, person_leaves: int, timeout_ticks: int,
        total_ticks: int, verbose: bool = False) -> Blackboard:
    bb = Blackboard()
    bb["waypoints"] = ["wp1", "wp2", "wp3"]
    bb["charger"] = "charger"
    bb["person_present"] = False
    bb["retreated"] = False

    tree = build_tree(bb, timeout_ticks)

    for t in range(1, total_ticks + 1):
        # Script the person appearing and leaving.
        bb["person_present"] = (person_at <= t < person_leaves)
        status = tree.tick()
        if verbose:
            print(f"tick {t:3d}: person={bb['person_present']!s:5} "
                  f"root={status.value:7} last_visited={bb.get('last_visited')}")
        if bb["retreated"]:
            if verbose:
                print(f"  -> retreated at tick {t}")
            break
    return bb


# --------------------------------------------------------------------------- #
# Main + self-checks
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Patrol with yield and retreat.")
    parser.add_argument("--person-at", type=int, default=6)
    parser.add_argument("--person-leaves", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--ticks", type=int, default=40)
    args = parser.parse_args()

    print("=== Scenario 1: no person, normal patrol ===")
    bb1 = run(person_at=999, person_leaves=999, timeout_ticks=args.timeout,
              total_ticks=20, verbose=True)
    assert not bb1["retreated"], "scenario 1: must NOT retreat"
    assert len(bb1.get("visits", [])) >= 3, "scenario 1: must visit waypoints"
    print("[OK] Scenario 1: patrolled the waypoints, never retreated.\n")

    print("=== Scenario 2: person leaves within the timeout -> resume ===")
    bb2 = run(person_at=5, person_leaves=9, timeout_ticks=args.timeout,
              total_ticks=30, verbose=True)
    assert not bb2["retreated"], "scenario 2: should RESUME, not retreat"
    visits_after = [v for v in bb2.get("visits", [])]
    assert len(visits_after) >= 3, "scenario 2: patrol should resume and keep visiting"
    print("[OK] Scenario 2: paused while the person was present, then RESUMED patrol.\n")

    print("=== Scenario 3: person stays past the timeout -> retreat ===")
    bb3 = run(person_at=4, person_leaves=999, timeout_ticks=args.timeout,
              total_ticks=40, verbose=True)
    assert bb3["retreated"], "scenario 3: MUST retreat after the timeout"
    assert bb3["last_visited"] == "charger", "scenario 3: must end at the charger"
    print("[OK] Scenario 3: person stayed too long, robot retreated to the charger.\n")

    print("[OK] all self-checks passed.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (abbreviated; per-tick lines vary, the SHAPE is invariant)
# -----------------------------------------------------------------------------
#
# === Scenario 1: no person, normal patrol ===
# tick   1: person=False root=RUNNING last_visited=None
# ...
# [OK] Scenario 1: patrolled the waypoints, never retreated.
#
# === Scenario 2: person leaves within the timeout -> resume ===
# tick   5: person=True  root=RUNNING last_visited=wp1     <- yields, waits
# tick   9: person=False root=RUNNING last_visited=wp1     <- person gone, RESUMES
# ...
# [OK] Scenario 2: paused while the person was present, then RESUMED patrol.
#
# === Scenario 3: person stays past the timeout -> retreat ===
# tick   4: person=True  root=RUNNING ...                  <- yields, waits
# (timeout fires)
#   -> retreated at tick N
# [OK] Scenario 3: person stayed too long, robot retreated to the charger.
#
# [OK] all self-checks passed.
#
# The three scenarios ARE the acceptance criteria. A tree that loads and "looks
# right" can still retreat-when-it-should-resume (scenario 2) — the subtlety
# Lecture 2 §3.2 flagged. The self-checks force the correct behavior. When you
# build this in BehaviorTree.CPP (the mini-project), these same three scenarios
# are how you verify the real tree against your real Nav2 + perception stack.
# -----------------------------------------------------------------------------
