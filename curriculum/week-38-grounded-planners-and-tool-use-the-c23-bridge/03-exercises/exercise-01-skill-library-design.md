# Exercise 1 — Skill-Library Design and the Constraining Grammar

**Goal:** Design a typed skill library for a tabletop manipulator — signatures, preconditions, effects — and write the JSON schema (and, as a stretch, the GBNF grammar) that constrains a planner LLM to emit *only* valid calls to it. You will internalize the week's central distinction: **the grammar makes the output well-formed; the preconditions make it groundable.**

**Estimated time:** 50 minutes. Guided. Mostly design; a schema file at the end.

---

## Step 1 — Enumerate the skills

For the "clear the table" / "tidy the workbench" task family, list the skills the robot needs. Aim for a *small, composable* set (Lecture 1 §3.3) — 4 to 6 skills, not 20. For each, write the **signature** with typed arguments.

Start from this set and refine it:

```
detect_objects() -> list[ObjectId]
grasp(object: ObjectId) -> bool
place(object: ObjectId, location: LocationId) -> bool
navigate(waypoint: WaypointId) -> bool
```

Decide: do you need `open_gripper()` / `close_gripper()` as separate skills, or are they internal to `grasp`/`place`? (Recommendation: keep them internal — fewer, composable skills beat many fine-grained ones.) Do you need an `inspect(object)` skill for the closed-loop case? Justify each skill you add.

**Record:** your final skill list with signatures and a one-line description each.

---

## Step 2 — Preconditions and effects

For each skill, write the **precondition** (what must be true to run it) and the **effect** (what it makes true), as predicates over a world state. This is the STRIPS model (Lecture 1 §3.1) and it's what your grounding will symbolically simulate.

Fill in (the first two are done as examples):

| Skill | Precondition | Effect |
|---|---|---|
| `detect_objects()` | always | world.objects populated |
| `grasp(o)` | `exists(o) ∧ reachable(o) ∧ gripper_empty` | `holding(o) ∧ ¬gripper_empty` |
| `place(o, l)` | ? | ? |
| `navigate(wp)` | ? | ? |
| *(your additions)* | ? | ? |

<details>
<summary>Check place / navigate</summary>

- `place(o, l)`: precondition `holding(o) ∧ reachable(l)`; effect `at(o, l) ∧ gripper_empty ∧ ¬holding(o)`.
- `navigate(wp)`: precondition `exists_waypoint(wp)`; effect `robot_at(wp)` (and possibly changes what's reachable).

</details>

> **The point of preconditions:** they are *checkable booleans over world state*. If you write a precondition you can't evaluate against your actual world model, you can't ground a plan that uses the skill. Every precondition above maps to a method you can implement (`world.exists(o)`, `world.holding(o)`). Keep them that concrete.

---

## Step 3 — The JSON schema that constrains the planner

Write the JSON schema that a planner LLM's output must match (Lecture 2 §1.2). The plan is a *list* of skill calls; each call has a `skill` (from a fixed `enum`) and `args`. Save it as `plan_schema.json`:

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "skill": {
        "type": "string",
        "enum": ["detect_objects", "grasp", "place", "navigate"]
      },
      "args": {"type": "object"}
    },
    "required": ["skill", "args"]
  }
}
```

Adjust the `enum` to match *your* Step 1 skill list. Answer in writing:

- What failure does the `enum` prevent? (A skill not in your library — `wipe`, `pour` — is *unrepresentable*.)
- What failure does this schema **not** prevent? (Args that reference nonexistent objects — `args` is an open object here. That's grounding's job, Exercise 2.)

This is the "constrained ≠ grounded" lesson made concrete: the schema constrains *shape*; it cannot know `cup_1` exists.

---

## Step 4 — Tighten the args (optional but instructive)

You can tighten the schema so each skill's args are typed (e.g., `grasp` requires an `object` string). A more precise schema for one skill:

```json
{
  "if":   {"properties": {"skill": {"const": "place"}}},
  "then": {"properties": {"args": {
             "type": "object",
             "properties": {"object": {"type": "string"},
                            "location": {"type": "string"}},
             "required": ["object", "location"]}}}
}
```

Note even this can't check that `object` is a *real* object — only that it's a string. **No schema can ground**; grounding needs the world state, which the schema doesn't have. Write one sentence confirming you understand why arg-typing in the schema still doesn't make the plan grounded.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] A skill list (4–6 skills) with typed signatures and one-line descriptions, with each added skill justified.
- [ ] A precondition + effect table for every skill, each precondition expressed as a *checkable* predicate over world state.
- [ ] A `plan_schema.json` whose `enum` matches your skill list.
- [ ] A written answer: what the `enum` prevents, and what the schema *cannot* prevent (ungrounded args) — i.e., why constrained ≠ grounded.
- [ ] One sentence on why even fully-typed args in the schema don't make a plan grounded.

---

## Stretch

- **Write the GBNF grammar.** Express the same constraint as a GBNF grammar (Lecture 2 §1.1) for llama.cpp/Ollama. Compare the experience to the JSON schema — which is easier to read, which is more expressive for your skill set?
- **Add a precondition you can't yet check.** Try adding a skill like `pour(container, target)` and write its precondition. Notice which world-state predicates you'd need (`is_open(container)`, `contains_liquid(container)`) that your perception doesn't yet provide — a concrete example of "you can't ground what you can't perceive."
- **Few-shot the planner.** Write two example (instruction, world, plan) triples you'd put in the system prompt to bias the LLM toward grounded plans (Lecture 2 §5.1). Good few-shots are the cheap prompt-half of the safety case.

---

When this feels comfortable, move to [Exercise 2 — The constrained planner](./exercise-02-constrained-planner.py).
