#!/usr/bin/env python3
# Exercise 3 — The grounded executor (closed-loop re-planning)
#
# Goal: Build the executor that runs a GROUNDED plan skill-by-skill, RE-OBSERVES
#       the world after each skill, checks the expected effect actually happened,
#       and RE-PLANS from the real current state when a skill fails mid-plan.
#       This is the syllabus's "inject a skill failure, handle by re-planning"
#       (Inner Monologue, Lecture 2 §3).
#
# Estimated time: 55 minutes. Runnable TODAY — no GPU, no Ollama.
#
# HOW IT RUNS WITHOUT A LOCAL LLM / ROBOT
#
#   The planner and the skill executor are both stubbed and clearly marked. The
#   stub executor SUCCEEDS on most skills but is scripted to FAIL the first grasp
#   of cup_1 once (a dropped grasp), so you watch the executor detect the failed
#   effect and re-plan. Swap the planner stub for Ollama and the executor stub
#   for real MoveIt2/Nav2 calls at the "# TODO" markers.
#
#       python3 exercise-03-grounded-executor.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] A grounded plan executes skill-by-skill on the happy path.
#   [ ] When a grasp fails (effect 'holding' does not hold after execution), the
#       executor RE-PLANS from the current real state rather than blindly
#       continuing.
#   [ ] After re-planning, the task completes (the cup ends up in the bin).
#   [ ] You can explain why re-observing after each skill is necessary even when
#       the plan was perfectly grounded at planning time.
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class World:
    objects: set[str] = field(default_factory=set)
    locations: set[str] = field(default_factory=set)
    reachable: set[str] = field(default_factory=set)
    holding: str | None = None
    placed: dict[str, str] = field(default_factory=dict)

    @property
    def gripper_empty(self) -> bool:
        return self.holding is None

    def copy(self) -> "World":
        return copy.deepcopy(self)

    def remaining_on_table(self) -> list[str]:
        """Objects detected but not yet placed in the bin."""
        return [o for o in sorted(self.objects) if self.placed.get(o) != "bin_1"]

    def summary(self) -> str:
        return f"holding={self.holding} placed={self.placed}"


# --- The planner (stub; swap for Ollama). Plans for whatever is still on the
#     table, given the CURRENT world — so re-planning naturally adapts. -------

def plan(instruction: str, world: World) -> list[dict]:
    # TODO 1: replace with a constrained Ollama call over the current world.
    calls: list[dict] = []
    if world.holding is not None:
        # If we're already holding something, finish placing it first.
        calls.append({"skill": "place",
                      "args": {"object": world.holding, "location": "bin_1"}})
    for obj in world.remaining_on_table():
        if obj == world.holding:
            continue
        calls.append({"skill": "grasp", "args": {"object": obj}})
        calls.append({"skill": "place", "args": {"object": obj, "location": "bin_1"}})
    return calls


# --- The skill executor (stub; swap for MoveIt2/Nav2). Mutates the REAL world
#     and returns success. Scripted to drop the FIRST grasp of cup_1 once. ----

_dropped_once = {"cup_1": False}


def execute_skill(call: dict, world: World) -> tuple[bool, World]:
    """STUB skill execution. Returns (success, new_world). Real version calls
    MoveIt2/Nav2 through the Week-37 safety leash."""
    # TODO 2: replace with real skill dispatch (MoveIt2 grasp/place, Nav2 nav),
    #         each wrapped in the Week-37 grounding gate + clamps + fallback.
    name, args = call["skill"], call["args"]
    w = world.copy()
    if name == "grasp":
        obj = args["object"]
        # Injected failure: the first grasp of cup_1 "slips" — returns success
        # but the object is NOT actually in the gripper (effect doesn't hold).
        if obj == "cup_1" and not _dropped_once[obj]:
            _dropped_once[obj] = True
            print(f"      [robot] grasp({obj}) executed but the cup SLIPPED")
            return True, w                       # success reported, but no holding!
        w.holding = obj
        return True, w
    if name == "place":
        obj, loc = args["object"], args["location"]
        if w.holding != obj:
            return False, w                      # can't place what we're not holding
        w.placed[obj] = loc
        w.holding = None
        return True, w
    return False, w


def effect_holds(call: dict, world: World) -> bool:
    """Did the skill's expected effect actually happen in the (re-observed) world?"""
    name, args = call["skill"], call["args"]
    if name == "grasp":
        return world.holding == args["object"]   # we should now be holding it
    if name == "place":
        return world.placed.get(args["object"]) == args["location"]
    return True


def observe(world: World) -> World:
    """STUB perception: returns the true world. Real version re-runs detection."""
    # TODO 3: re-run detect_objects() and rebuild the world from perception.
    return world


def run(instruction: str, world: World, max_replans: int = 5) -> World:
    print(f"[planner] instruction: {instruction!r}")
    replans = 0
    current_plan = plan(instruction, world)
    i = 0
    while i < len(current_plan):
        call = current_plan[i]
        print(f"[exec] step {i}: {call['skill']}{call['args']}")
        success, world = execute_skill(call, world)
        world = observe(world)
        if not success or not effect_holds(call, world):
            print(f"[exec] effect did NOT hold ({world.summary()}) -> RE-PLAN")
            if replans >= max_replans:
                print("[exec] re-plan budget exhausted -> ABORT (safe stop)")
                return world
            replans += 1
            current_plan = plan(instruction, world)   # fresh plan from REAL state
            i = 0
            continue
        i += 1
    print(f"[exec] plan complete. final: {world.summary()}")
    return world


def main() -> None:
    world = World(
        objects={"cup_1", "plate_1"},
        locations={"bin_1", "table_1"},
        reachable={"cup_1", "plate_1", "bin_1"},
    )
    final = run("clear the table", world)
    done = all(final.placed.get(o) == "bin_1" for o in ("cup_1", "plate_1"))
    print(f"\nTASK {'COMPLETE' if done else 'INCOMPLETE'}: "
          f"both objects in bin_1 = {done}")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (the first grasp of cup_1 slips, triggering a re-plan)
# -----------------------------------------------------------------------------
#
# [planner] instruction: 'clear the table'
# [exec] step 0: grasp{'object': 'cup_1'}
#       [robot] grasp(cup_1) executed but the cup SLIPPED
# [exec] effect did NOT hold (holding=None placed={}) -> RE-PLAN
# [exec] step 0: grasp{'object': 'cup_1'}
# [exec] step 1: place{'object': 'cup_1', 'location': 'bin_1'}
# [exec] step 2: grasp{'object': 'plate_1'}
# [exec] step 3: place{'object': 'plate_1', 'location': 'bin_1'}
# [exec] plan complete. final: holding=None placed={'cup_1': 'bin_1', 'plate_1': 'bin_1'}
#
# TASK COMPLETE: both objects in bin_1 = True
#
# THE LESSON: the plan was perfectly GROUNDED at planning time, yet reality
# defied it — the grasp slipped. Because the executor RE-OBSERVES after each
# skill and checks the effect actually held, it detects the slip (holding=None
# when it expected holding=cup_1) and RE-PLANS from the real state instead of
# marching on to place a cup it isn't holding. Grounding-at-planning is not
# enough; closed-loop execution is why the task still completes.
# -----------------------------------------------------------------------------
