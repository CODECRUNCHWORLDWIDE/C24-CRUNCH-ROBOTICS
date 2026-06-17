#!/usr/bin/env python3
# Exercise 2 — The constrained planner (well-formed AND grounded)
#
# Goal: Build the planner front-end: a planner emits a SCHEMA-CONSTRAINED skill
#       sequence (well-FORMED by construction), then a GROUNDING layer validates
#       it against the skill library and the world state (well-FOUNDED) via
#       static checks PLUS symbolic simulation of preconditions/effects. You
#       will catch the two canonical LLM planning bugs: a hallucinated object,
#       and a precondition/ordering violation.
#
# Estimated time: 50 minutes. Runnable TODAY — no GPU, no Ollama.
#
# HOW IT RUNS WITHOUT A LOCAL LLM
#
#   The planner is behind ONE function, `plan`. This file ships a deterministic
#   STUB planner that returns scripted plans (one good, two buggy) so the
#   GROUNDING logic is testable now. To use the real Llama 3.1 8B, replace the
#   stub at "# TODO 1" with an Ollama call using `format=PLAN_SCHEMA`. The rest
#   is unchanged. The contract: (instruction, world) -> list[skill call dicts].
#
#       python3 exercise-02-constrained-planner.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] A good plan grounds: every skill exists, every arg is a real object,
#       every precondition holds in sequence.
#   [ ] A plan referencing a nonexistent object ('shelf_top') is REJECTED at
#       static validation with a clear error.
#   [ ] A plan with place-before-grasp is REJECTED at symbolic simulation
#       (precondition 'holding' fails).
#   [ ] You can state which layer caught each failure (grammar / static / sim).
#
# Expected output is at the bottom of the file.

from __future__ import annotations

import copy
from dataclasses import dataclass, field

# --- The world state ---------------------------------------------------------


@dataclass
class World:
    objects: set[str] = field(default_factory=set)       # detected object ids
    locations: set[str] = field(default_factory=set)     # valid place targets
    reachable: set[str] = field(default_factory=set)     # ids within reach
    holding: str | None = None                            # object in gripper, or None
    placed: dict[str, str] = field(default_factory=dict)  # object -> location

    @property
    def gripper_empty(self) -> bool:
        return self.holding is None

    def exists(self, oid: str) -> bool:
        return oid in self.objects

    def is_location(self, lid: str) -> bool:
        return lid in self.locations

    def copy(self) -> "World":
        return copy.deepcopy(self)

    def summary(self) -> str:
        return (f"objects={sorted(self.objects)} holding={self.holding} "
                f"placed={self.placed}")


# --- The skill library: precondition + effect (the STRIPS model) -------------

def _pre_grasp(w: World, object: str) -> tuple[bool, str]:
    if not w.exists(object):
        return False, f"object '{object}' does not exist"
    if object not in w.reachable:
        return False, f"object '{object}' not reachable"
    if not w.gripper_empty:
        return False, f"gripper not empty (holding {w.holding})"
    return True, ""


def _eff_grasp(w: World, object: str) -> World:
    w = w.copy()
    w.holding = object
    return w


def _pre_place(w: World, object: str, location: str) -> tuple[bool, str]:
    if w.holding != object:
        return False, f"not holding '{object}' (holding {w.holding})"
    if not w.is_location(location):
        return False, f"location '{location}' does not exist"
    return True, ""


def _eff_place(w: World, object: str, location: str) -> World:
    w = w.copy()
    w.placed[object] = location
    w.holding = None
    return w


@dataclass
class Skill:
    name: str
    args: list[str]                  # required arg names, in order
    precondition: object             # callable(world, **args) -> (ok, why)
    effect: object                   # callable(world, **args) -> world


SKILLS = {
    "detect_objects": Skill("detect_objects", [],
                            lambda w: (True, ""), lambda w: w),
    "grasp": Skill("grasp", ["object"], _pre_grasp, _eff_grasp),
    "place": Skill("place", ["object", "location"], _pre_place, _eff_place),
}

# The schema the real LLM would be constrained by (Lecture 2 §1.2). The stub
# planner is hand-written to OBEY it, so its output is already well-formed.
PLAN_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "skill": {"type": "string", "enum": list(SKILLS.keys())},
            "args": {"type": "object"},
        },
        "required": ["skill", "args"],
    },
}


# --- The planner (stub; swap for Ollama) -------------------------------------

def plan(instruction: str, world: World, variant: str) -> list[dict]:
    """STUB planner: returns scripted, schema-valid plans to exercise grounding.

    'good'      -> a correct grounded plan.
    'phantom'   -> references a nonexistent location 'shelf_top' (static fail).
    'misorder'  -> place before grasp (symbolic-simulation fail).
    """
    # TODO 1: replace with a real constrained Ollama call:
    #   import ollama, json
    #   resp = ollama.chat(model="llama3.1:8b",
    #                      messages=[...skills + world + instruction...],
    #                      format=PLAN_SCHEMA, options={"temperature": 0.0})
    #   return json.loads(resp["message"]["content"])
    if variant == "good":
        return [
            {"skill": "grasp", "args": {"object": "cup_1"}},
            {"skill": "place", "args": {"object": "cup_1", "location": "bin_1"}},
        ]
    if variant == "phantom":
        return [
            {"skill": "grasp", "args": {"object": "cup_1"}},
            {"skill": "place", "args": {"object": "cup_1", "location": "shelf_top"}},
        ]
    if variant == "misorder":
        return [
            {"skill": "place", "args": {"object": "cup_1", "location": "bin_1"}},
            {"skill": "grasp", "args": {"object": "cup_1"}},
        ]
    return []


# --- Grounding: static validation + symbolic simulation ----------------------

def ground_plan(plan_calls: list[dict], world: World) -> tuple[bool, list[str]]:
    """Validate a (well-formed) plan against the library and world state.
    Returns (grounded, errors). Catches hallucinated args AND ordering bugs."""
    errors: list[str] = []
    sim = world.copy()
    for i, call in enumerate(plan_calls):
        name = call.get("skill")
        args = call.get("args", {})
        skill = SKILLS.get(name)
        if skill is None:
            errors.append(f"step {i}: unknown skill '{name}'")
            continue
        # Static: all required args present.
        missing = [a for a in skill.args if a not in args]
        if missing:
            errors.append(f"step {i}: {name} missing args {missing}")
            continue
        # Symbolic simulation: precondition holds in the current simulated state.
        ok, why = skill.precondition(sim, **{a: args[a] for a in skill.args})
        if not ok:
            errors.append(f"step {i}: {name}{args}: {why}")
            continue
        sim = skill.effect(sim, **{a: args[a] for a in skill.args})
    return (len(errors) == 0, errors)


def main() -> None:
    # The world after detect_objects(): one cup, one bin, both reachable.
    world = World(
        objects={"cup_1"},
        locations={"bin_1", "table_1"},
        reachable={"cup_1", "bin_1"},
    )
    print(f"world: {world.summary()}")
    print(f"valid locations: {sorted(world.locations)}\n")

    for variant in ("good", "phantom", "misorder"):
        calls = plan("clear the table", world, variant)
        grounded, errors = ground_plan(calls, world)
        print(f"--- plan variant: {variant} ---")
        for c in calls:
            print(f"   {c['skill']}{c['args']}")
        if grounded:
            print("   => GROUNDED (would execute)\n")
        else:
            print("   => REJECTED (ungrounded):")
            for e in errors:
                print(f"      - {e}")
            print()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# world: objects=['cup_1'] holding=None placed={}
# valid locations: ['bin_1', 'table_1']
#
# --- plan variant: good ---
#    grasp{'object': 'cup_1'}
#    place{'object': 'cup_1', 'location': 'bin_1'}
#    => GROUNDED (would execute)
#
# --- plan variant: phantom ---
#    grasp{'object': 'cup_1'}
#    place{'object': 'cup_1', 'location': 'shelf_top'}
#    => REJECTED (ungrounded):
#       - step 1: place{'object': 'cup_1', 'location': 'shelf_top'}: location 'shelf_top' does not exist
#
# --- plan variant: misorder ---
#    place{'object': 'cup_1', 'location': 'bin_1'}
#    grasp{'object': 'cup_1'}
#    => REJECTED (ungrounded):
#       - step 0: place{'object': 'cup_1', 'location': 'bin_1'}: not holding 'cup_1' (holding None)
#
# THE LESSON: all three plans are WELL-FORMED (schema-valid: only library skills,
# right shape). Grounding is what separates them. 'phantom' fails STATIC/symbolic
# validation (a location that doesn't exist); 'misorder' fails SYMBOLIC SIMULATION
# (place's precondition 'holding cup_1' is false because grasp hasn't run). The
# grammar could never catch either — that's why constrained != grounded.
# -----------------------------------------------------------------------------
