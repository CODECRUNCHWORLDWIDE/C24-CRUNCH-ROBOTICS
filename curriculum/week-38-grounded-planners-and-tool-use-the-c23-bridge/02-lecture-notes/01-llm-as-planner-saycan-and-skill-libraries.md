# Lecture 1 — LLM-as-Planner: SayCan, Skill Libraries, and the C23 Bridge

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain why an LLM is a good *planner* and a bad *controller*, articulate SayCan's Say×Can decomposition and why neither factor alone suffices, design a typed skill library with preconditions and effects, and see the straight line from C23's tool-use pattern to a robot's skill API.

If you remember one sentence from this entire week, remember this one:

> **An LLM is excellent at deciding *what* to do ("to clear the table, pick up each object and put it in the bin") and terrible at deciding *how* to do it (the exact gripper trajectory). So you let it plan over a library of skills it can call but not author — and you ground every call against the real world before a motor turns.**

This is the architectural inversion from Week 37. There, the language model *was* the policy: instruction in, motor deltas out. That works for a single primitive action but it does not compose — a VLA does not reliably chain "grasp, then place, then grasp the next, then place" across a multi-step task, and it has no notion of "I've now cleared three of five objects." This week the LLM operates one level up: it emits a *plan* — a sequence of skill calls — and the skills (which you built in weeks 23–37) handle the *how*. This is the **task-and-motion-planning (TAMP)** split: the LLM does task planning, your skills do motion. And it's the **C23 bridge**: an LLM calling a library of tools is exactly the agent pattern C23 taught, with the tools now being robot skills.

The shift in one picture, because it frames the whole week:

```
  WEEK 37 (VLA-as-policy):     instruction ──► VLA ──► motor action      (one step)
  WEEK 38 (LLM-as-planner):    instruction ──► LLM ──► [skill, skill, ...] ──► each skill
                                                                              may BE a VLA
```

The VLA answered "what motor action now?"; the planner answers "what *sequence of skills*?" — and each skill in that sequence might itself be executed by a VLA (or a MoveIt2 grasp, or a Nav2 goal). The planner is the *conductor*; the skills (VLAs, planners, controllers) are the *players*. A multi-step task like "clear the table" needs a conductor, because no single VLA query coherently sequences five grasps and five places while tracking progress. That's the gap this week fills, and it's why the AI-robotics phase ends here: you now have language at *both* altitudes — actions (week 37) and plans (week 38) — each with its own grounding and its own leash.

---

## 1. Why an LLM plans well and controls badly

Be precise about the division of labor, because getting it wrong is the week's biggest mistake. The two mistakes, both common:

- **Asking the LLM to do control** — "have the LLM output joint angles / a trajectory." It can't; it has no kinematics, no real-time loop. The output is garbage that ignores the robot's actual dynamics.
- **Hand-coding the task decomposition** — "I'll write the steps for 'clear the table' myself." Then you've gained nothing from the LLM; every new task needs a programmer, which is the pre-LLM status quo.

The correct line is between them: LLM decomposes the task into skills; skills (your code) do the control. Cross that line in either direction and the system fails — either the LLM produces unexecutable motor commands, or you've rebuilt a hand-coded robot with an LLM bolted on for show.

Keep that line in mind through the whole week; every design decision is, at bottom, "is this the LLM's job or a skill's job?"

**LLMs are good at task decomposition.** "Clear the table," "make me a coffee," "tidy the workbench" — decomposing these into ordered sub-steps is a *language* task, and LLMs have read millions of instructions, recipes, and how-tos. Ask Llama 3.1 "how do I clear a table?" and it gives a sensible sequence. That sequence-generation is what you harvest.

This is genuinely the LLM's strength, not a workaround: the "common sense" that says "to clear a table, remove each object" is exactly the web-scale world knowledge a from-scratch system would have to be hand-coded with. A pre-LLM robot needed a programmer to enumerate the steps for every task; an LLM-planned robot reads the steps off its training. That's the leap — task knowledge that used to be hand-authored is now generated — and it's why "tell the robot a new task in English" is suddenly possible. You're not coaxing the LLM into doing something it's bad at; you're using it for precisely the thing it's best at, and delegating the thing it's worst at (control) to the skills.

**LLMs are bad at low-level control.** The LLM has no real-time sensor loop, no kinematics, no millisecond control. It cannot output a smooth 50 Hz joint trajectory; even as a VLA emitting action chunks (week 37) it's slow and needs a leash. Asking an LLM for motor commands is asking the wrong organ.

So: **the LLM plans; the skills execute.** The LLM emits `grasp(cup_1)`; your week-23/26 grasp skill — MoveIt2, a learned or analytic grasp, the collision checking — executes it. The LLM never sees a joint angle. This separation is not a limitation to engineer around; it is the correct architecture, and it's why a small *8B* model (not a frontier model) is enough to plan — the hard part (control) was already solved by your skills.

The division of labor as a table, because it decides your whole architecture:

| Concern | Who handles it | Why |
|---|---|---|
| Task decomposition ("clear → grasp each, place each") | LLM | A language task it's read millions of |
| Choosing the next skill | LLM (proposes) + grounding (disposes) | Usefulness from the LLM, feasibility from the world |
| Grasp pose / trajectory | Skill (MoveIt2 / VLA) | Kinematics, collisions, control — the LLM can't |
| Collision / joint limits | Skill (MoveIt2) | Physics the LLM doesn't model |
| Real-time safety (E-stop, clamps) | Fast control loop | Milliseconds, independent of the LLM |

Read the right column: every row the LLM owns is a *language/reasoning* task; every row it doesn't is a *physics/real-time* task. The architecture is just "put each concern where it belongs," and the reason it works is that the physics rows were *already solved* by weeks 17–37. The LLM is the new piece, and it's the *easy* piece precisely because the hard pieces are done.

---

## 2. SayCan: the grounded-planning insight

The foundational idea (SayCan, 2022) is deceptively simple and you must internalize it, because it's the reason a naive "just ask the LLM for a plan" fails. Before SayCan, the obvious approach was "prompt a big LLM with the task, parse its plan, run it." It fails in exactly the way you'd now predict: the LLM, knowing nothing about the actual robot or scene, produces plans full of actions the robot can't perform. SayCan's contribution was recognizing that the *language* model and the *physical* feasibility are two separate signals that must be combined, not one signal you can get from the LLM alone.

An LLM, asked "what's the next step to clear the table?", proposes steps ranked by **language likelihood** — what's a *useful, sensible* thing to say next. Call this **Say**. But the LLM has no idea what the robot *can actually do right now*: it might propose "wipe the table with a sponge" when there is no sponge, or "pick up the cup" when the cup is across the room and unreachable. The LLM's proposals are *useful* but not necessarily *possible*.

Separately, the robot has an **affordance** model: for each skill, how feasible is it *right now*? Is the object present? Is it reachable? Does the precondition hold? Call this **Can** — a value/feasibility score per skill, grounded in the actual scene. But the affordance model alone is mute: it can tell you "grasp(cup) is feasible, grasp(plate) is feasible, navigate(door) is feasible" but not which one *advances the task*.

Think of it as two people with complementary blindnesses. The LLM is a brilliant strategist who has never seen the room — it knows *what* should happen but not what's *actually there*. The affordance model is a careful technician who knows exactly what's in the room and what's reachable — but has no idea what you're trying to accomplish. Neither can do the job alone: the strategist plans for a room that may not exist, the technician fiddles with whatever's nearby. Put them together — strategist proposes, technician vetoes the infeasible — and you get plans that are both sensible *and* executable. That pairing is SayCan, and it's the same pairing as Week 37's VLA (proposer) plus grounding gate (vetoer). You've seen this movie; this week it plays at the planning altitude.

The SayCan insight: **multiply them.** Score each candidate skill by `Say(skill | instruction) × Can(skill | state)` and pick the highest. The LLM contributes *usefulness*; the affordance model contributes *possibility*; the product is a skill that is both useful for the task *and* actually executable now.

Why *multiply* and not, say, average or take the max? Because multiplication has the right *veto* behavior: if either factor is near zero, the product is near zero. A skill that's useful (Say high) but impossible (Can ≈ 0) gets a near-zero product — vetoed by impossibility. A skill that's possible (Can high) but useless (Say ≈ 0) gets a near-zero product — vetoed by irrelevance. Only a skill that scores well on *both* survives. Averaging would let a very-useful-but-impossible skill through on the strength of its usefulness alone (exactly the failure you're trying to prevent); multiplication won't. The product is an AND, not an OR, and AND is what you want: useful *and* possible.

Neither factor alone works:

- **Say alone** → useful-but-impossible plans (grasp the cup that isn't there). A planner with only the LLM is *eloquent and wrong*: it produces beautifully-reasoned plans referencing things that aren't in the room.
- **Can alone** → possible-but-aimless actions (it can grasp *something*, but which advances "clear the table"?). A planner with only affordances is *capable and purposeless*: it knows what it *could* do but not what it *should* do for the task.

The two failure modes are mirror images, and the product fixes both: the LLM supplies *purpose* (which skills advance the instruction), the affordance/grounding check supplies *feasibility* (which of those are actually possible now). You need a planner that is *both* purposeful and feasible, and that requires *both* factors — which is the whole reason SayCan's contribution was the multiplication, not either half.

```
   instruction "clear the table"
        │
        ▼
   ┌─────────────┐        ┌────────────────────┐
   │  LLM (Say)  │        │  affordances (Can) │
   │ what's      │        │ what's possible    │
   │ useful?     │        │ right now?         │
   └──────┬──────┘        └─────────┬──────────┘
          │  P(skill|instruction)   │  feasibility(skill|state)
          └────────────┬────────────┘
                       ▼
              argmax  Say × Can
                       │
                       ▼
              next skill: grasp(cup_1)
```

In 2026 practice you rarely implement SayCan's exact value-function affordance scoring; the *modern* form is: the LLM proposes a plan (constrained to your skill library, Lecture 2), and a **runtime grounding/validation** layer plays the role of "Can" — rejecting any skill call whose object doesn't exist or whose precondition fails (Lecture 2 §2). The principle is identical: **the LLM proposes; an independent, world-grounded check disposes.** Same instinct as Week 37's grounding gate — never let the language model's confidence be the only thing between an instruction and the actuators.

It's worth seeing the original SayCan and the modern form side by side, because they're the same idea at two levels of mechanism:

| | Original SayCan (2022) | Modern form (2026, this week) |
|---|---|---|
| "Say" | LLM scores each skill's language-likelihood | LLM emits a constrained plan over skills |
| "Can" | A learned value function scores affordance | Runtime grounding/validation (precondition + existence checks) |
| Combine | Multiply per-skill scores, pick argmax | Reject any plan step that fails grounding; repair |
| Why it works | Useful × possible beats either alone | Same: LLM usefulness gated by world feasibility |

The modern form is *more practical* because you don't need to train an affordance value function — you already have the world state (from perception) and the skill preconditions, so "Can" is a *deterministic check*, not a learned model. That's a real simplification: a deterministic precondition check is auditable, testable, and can't itself hallucinate, where a learned affordance scorer is another model that can be wrong. For a safety case, "the precondition `holding(o)` is a hard boolean over the world state" is a far stronger statement than "an affordance network scored it feasible." The modern form trades SayCan's elegance for the robustness of an explicit check, which is the right trade for a robot you have to certify.

### 2.1 Why the LLM can't just "be careful"

A reasonable objection: if you prompt the LLM well enough — give it the skills, the world state, tell it to only use real objects — won't it just produce grounded plans? Mostly, yes. But "mostly" is the problem. An LLM is a probability distribution over text; even a great prompt at temperature 0 occasionally emits a plan referencing an object that isn't there, or an ordering that violates a precondition, because the model has no *hard* constraint forcing groundedness — the prompt is a strong suggestion, not a contract (the half-prompt/half-runtime thesis, Lecture 2 §5). On a chatbot, the occasional bad output is a bad answer you regenerate. On a robot, the occasional bad output is a gripper reaching for a phantom. So you don't *rely* on the LLM being careful; you *check* every plan it produces against the world, and you let the check — not the prompt — be the thing that guarantees safety. The LLM's care reduces how often the check fires; the check is what makes the guarantee.

---

## 3. The skill library

The skill library is the planner's vocabulary — the set of things it's allowed to ask for. Designing it well is most of the engineering. Get the library right and an 8B model plans reliably over it; get it wrong (fuzzy skills, missing preconditions, fat special-cases) and even a frontier model produces ungroundable plans. The library, not the model, is the lever — which is the same data-over-architecture lesson from the VLA week (week 37 §2.1), restated for planning: you control the skill set; you don't control the LLM's weights; so spend your effort where you have control.

### 3.1 What a skill is

A skill is a **parameterized, composable robot capability** with four parts:

- A **typed signature** — `grasp(object: ObjectId) -> bool`, `place(object: ObjectId, location: LocationId) -> bool`, `navigate(waypoint: WaypointId) -> bool`, `detect_objects() -> list[ObjectId]`. The types matter: they let you validate that the LLM passed a real object id, not a free-text guess.
- A **precondition** — what must be true to run it. `grasp(o)` requires `o` exists, is reachable, and the gripper is empty. `place(o, l)` requires the gripper holds `o` and `l` is reachable.
- An **effect** — what it makes true. `grasp(o)` makes `holding(o)` true and `gripper_empty` false. `place(o, l)` makes `at(o, l)` true and `gripper_empty` true.
- An **implementation** — the actual code: `grasp` runs the week-26 learned grasp or the week-23 MoveIt2 plan; `navigate` sends a Nav2 goal. The LLM never sees this; it sees only the signature.

The separation of *signature* (what the LLM sees) from *implementation* (what runs) is doing real work. The LLM plans over an abstract interface — "grasp this object" — without knowing or caring whether grasping is a learned VLA policy, an analytic antipodal grasp, or a MoveIt2 plan. That means you can *swap the implementation* (upgrade `grasp` from analytic to learned) without changing a single plan the LLM produces, and you can *test the planner* against stub implementations (the exercises do exactly this) without a robot. The signature is the contract; the implementation is replaceable. This is ordinary good software design (program to an interface), and it's why the same skill library survives from this week's stub exercises to the capstone's real robot — the signatures don't change, only what's behind them.

This is the **STRIPS/PDDL** flavor of action modeling (precondition, effect), and it's not academic decoration — the preconditions and effects are exactly what you check during grounding (Lecture 2 §2) and what let you *symbolically simulate* a plan before executing it (does each skill's precondition hold given the prior skills' effects?).

Why model preconditions and effects at all, when the LLM "knows" how the world works? Because the LLM's knowledge is *implicit and unreliable*, and the precondition/effect model is *explicit and checkable*:

- The LLM "knows" you must grasp before you place — usually. But it will, some fraction of the time, emit place-before-grasp anyway (an ordering hallucination). You cannot rely on the LLM to never make this mistake.
- The precondition `holding(o)` on `place(o, l)` turns "the LLM usually orders correctly" into "the system *provably* rejects any plan that places before grasping." Implicit-usually becomes explicit-always.

That conversion — from the model's soft knowledge to a hard, checkable constraint — is the entire value of the STRIPS model. The LLM proposes using its soft world-knowledge; the precondition/effect model *verifies* using hard logic. Same Say-proposes/Can-disposes split as SayCan (§2), now mechanized as symbolic simulation.

A practical guideline for writing preconditions: include *everything the skill physically requires*, even things that "obviously" hold. It's tempting to skip `gripper_empty` on `grasp` because "of course the gripper is empty before grasping" — but an LLM plan that does `grasp(cup_1)` then `grasp(plate_1)` without a `place` in between violates exactly that "obvious" precondition (you can't grasp a second thing while holding the first), and only the explicit `gripper_empty` check catches it. The preconditions that feel redundant are often the ones that catch the LLM's subtler ordering bugs. Err toward completeness: a precondition you didn't write is a check you don't have, and a check you don't have is a bug class that reaches the actuators.

### 3.2 The skill library *is* the C23 tool API

If you took C23, this is a homecoming. In C23 you gave an agent a set of **tools** — typed functions it could call (`search(query)`, `send_email(to, body)`) — and the LLM planned over them with structured/function-calling output, and you *validated* its calls before executing. A robot skill library is *exactly* that, with the tools being physical:

| C23 agent | C24 robot |
|---|---|
| Tool: `search(query: str)` | Skill: `grasp(object: ObjectId)` |
| Tool signature in the prompt / function schema | Skill signature in the grammar / function schema |
| LLM emits a tool call | LLM emits a skill call |
| Validate args before executing | Ground the call against the world before executing |
| Tool returns a result the LLM reads | Skill returns success/failure the planner re-plans on |

Everything you learned about tool use, structured output, and not-trusting-the-LLM's-raw-text transfers directly. The new parts are *physical grounding* (the tool's argument is a real object in space, not a string) and *irreversibility* (a bad `send_email` is embarrassing; a bad `grasp` can break something or someone). The bridge is real, and it's why C23 is a strong-recommend prerequisite.

Two consequences of the physical-and-irreversible difference shape everything in Lecture 2:

- **Physical grounding means the validator needs the *world*, not just a schema.** A C23 tool call `search("cats")` is valid if "cats" is a string; a robot call `grasp("cup_1")` is valid only if `cup_1` *exists in the scene right now*. The validator must consult perception (the world state), not just check types. That's why grounding (Lecture 2 §2) is more than schema validation.
- **Irreversibility means the cost of a wrong call is asymmetric and high.** A wrong `send_email` is undone with an apology; a wrong `pour` floods a laptop, a wrong `grasp` near a person is a safety event. So the robot validator must be *stricter* than a text-agent validator, with hard gates for irreversible actions (Lecture 2 §5) that a text agent wouldn't bother with. The stakes are higher, so the leash is tighter.

If you internalized "validate the tool call before executing it" from C23, this week is "validate it *against the physical world*, and gate it *harder* because you can't undo a grasp." Same skeleton, higher stakes, and the higher stakes are the whole reason the runtime grounding matters so much more here than it did for a chatbot's tools.

### 3.3 Design principles for the skill set

- **Small and well-defined beats large and fuzzy.** A planner with 8 clear, composable skills outperforms one with 40 overlapping ones. The LLM picks the wrong skill less when the choices are distinct.
- **Compose, don't special-case.** Prefer `grasp(o) + place(o, l)` over a monolithic `move_object(o, l)` — composable primitives let the planner handle situations you didn't anticipate (grasp, inspect, regrasp, place).
- **Parameterize over real referents.** A skill's arguments are *ids* of real things (`cup_1`, `bin_1`), populated by `detect_objects()`, not free-text the LLM invents. This is the single biggest defense against hallucinated objects (Lecture 2 §2).
- **Make preconditions explicit and checkable.** If you can't write a skill's precondition as a boolean over world state, you can't ground a plan that uses it.

A useful test for whether your skill set is well-designed: **can the LLM, given only the signatures and one-line descriptions, plan a task you didn't anticipate?** If your skills are clean composable primitives (`grasp`, `place`, `navigate`), the answer is yes — the LLM can compose them for "stack the blocks" even if you only tested "clear the table." If your skills are fat special-cases (`clear_the_table()`, `stack_the_blocks()`), the LLM can only do exactly what you pre-built, and you've gained nothing over hard-coding. The whole *point* of the LLM planner is to handle tasks you didn't enumerate, and that only works if the skills compose. A good skill library is a small set of orthogonal verbs; a bad one is a big set of pre-baked tasks. Aim for verbs.

There's a tension with the precondition rule, worth naming: the more you decompose into primitives, the more preconditions you must write and check. `move_object(o, l)` has one precondition; `grasp(o) + place(o, l)` has two and an ordering constraint between them. The composability is worth the extra precondition bookkeeping — but it *is* extra bookkeeping, and skimping on it (a skill with a vague or unwritten precondition) is where ungrounded plans sneak through. Decompose into primitives, *and* write every primitive's precondition; don't do the first without the second.

### 3.4 A worked skill library

For the "clear the table" task:

```python
# The skill library — typed signatures, preconditions, effects.
# The LLM plans over these; the implementations call the real stack.

SKILLS = {
    "detect_objects": Skill(
        signature="detect_objects() -> list[ObjectId]",
        precondition=lambda w: True,                 # always available
        effect=lambda w: w.with_objects_detected(),  # populates world.objects
        impl=run_detection,                          # YOLO/OWL-ViT (weeks 13, 37)
    ),
    "grasp": Skill(
        signature="grasp(object: ObjectId) -> bool",
        precondition=lambda w, o: w.exists(o) and w.reachable(o) and w.gripper_empty,
        effect=lambda w, o: w.set_holding(o),
        impl=run_grasp,                              # MoveIt2 / learned grasp (wk 26)
    ),
    "place": Skill(
        signature="place(object: ObjectId, location: LocationId) -> bool",
        precondition=lambda w, o, l: w.holding(o) and w.reachable(l),
        effect=lambda w, o, l: w.set_at(o, l),
        impl=run_place,
    ),
    "navigate": Skill(
        signature="navigate(waypoint: WaypointId) -> bool",
        precondition=lambda w, wp: w.exists_waypoint(wp),
        effect=lambda w, wp: w.set_robot_at(wp),
        impl=run_nav2_goal,                          # Nav2 (weeks 17-24)
    ),
}
```

The LLM is told the *signatures* (and maybe one-line descriptions); it emits calls like `grasp("cup_1")`; the precondition/effect/impl are yours. That's the whole library.

### 3.5 The world-state model: the substrate everything checks against

A skill library is useless without a **world-state model** — the structured representation of "what's true right now" that preconditions are checked against. It's the bridge between perception (weeks 9–16, 37) and planning. Minimally it tracks:

- **Objects** — the ids of detected objects (`cup_1`, `plate_1`), populated by `detect_objects()`, each with a pose and (ideally) a class/attributes for grounding ("the *red* cup").
- **Locations / waypoints** — the named places a `place` or `navigate` can target (`bin_1`, `table_1`, `pantry`), from the map / nav graph.
- **Reachability** — which objects/locations are within the arm's or base's reach *right now* (the affordance substrate).
- **Robot state** — what the gripper holds (`holding`), where the base is, etc. — the part that mutates as skills execute.

This world model is what symbolic simulation (Lecture 2 §2.2) mutates as it walks a plan: `grasp(cup_1)` sets `holding = cup_1` in the *simulated* world, so the next `place(cup_1, bin_1)`'s precondition `holding(cup_1)` checks against the updated state. The model is the difference between "the LLM said grasp then place" and "the system verified that, after grasping, the place's precondition holds." Without an explicit world model, you cannot ground anything — you'd be checking the plan against nothing.

Crucially, the world model is *populated by perception*, which means it's only as good as your detection. If `detect_objects()` misses the cup, the world model has no `cup_1`, and a perfectly-reasonable "bring the cup" plan gets rejected as ungrounded (object doesn't exist) — a *correct* rejection given the (incomplete) world model, but one whose root cause is perception, not planning. This is why a grounded planner's failures sometimes trace back to the perception weeks: a planning failure and a perception failure can look identical ("it won't grasp the cup") and have different fixes. The world model is where perception meets planning, and where you debug which side is at fault.

---

## 4. From instruction to plan: the loop shape

The end-to-end shape (detailed and made safe in Lecture 2):

1. **Perceive the world.** Run `detect_objects()` to populate the world state: which objects exist, where, what's reachable. This is the "Can" substrate — you can't ground a plan against a world you haven't observed.
2. **Prompt the planner.** Give the LLM the instruction, the skill signatures, and the current world state (the detected objects, the locations). Ask for a plan as a constrained skill sequence (Lecture 2 §1).
3. **Get a constrained plan.** The LLM emits a sequence of skill calls, well-*formed* by grammar (no prose, no invented skills).
4. **Ground it.** Validate every call against the library and the world state; symbolically simulate preconditions/effects (Lecture 2 §2). Reject or repair if ungrounded.
5. **Execute, skill by skill.** Run each grounded skill through the real stack (with the Week-37 per-skill safety leash). After each, re-observe; if a skill failed or the world changed unexpectedly, **re-plan** (Lecture 2 §3, closed-loop).

Notice the two grounding checkpoints in that loop, at two altitudes. Step 4 grounds the *plan* (do the skills' preconditions hold, do the objects exist?) — catching a hallucinated plan before any motion. Step 5's per-skill leash grounds each *action* (is the VLA's grasp targeting the right object, within limits?) — catching a hallucinated motor command at execution. Both are necessary because they catch different failures: step 4 catches "the plan is nonsense" (place before grasp, grasp a phantom); step 5 catches "the plan is sound but this skill's *execution* is reaching for the wrong cup." A planner with only step 4 would dispatch a sound plan whose `grasp(cup_1)` the VLA then executes onto the wrong object; a system with only step 5 would faithfully execute an absurd plan one bad-but-individually-checked skill at a time. You need grounding at *both* the plan level and the action level, which is precisely why this week (plan grounding) builds *on top of* Week 37 (action grounding) rather than replacing it.

The infrequency of planning is a feature: you plan once per task (seconds), then execute many skills (each its own control loop). The slow LLM is fine because it's off the control path — it's a planner, not a controller. That's the whole reason an 8B local model is enough.

Contrast this with the Week 37 VLA, to cement where each language model sits:

- **The VLA (week 37)** is on the *action* path: it queries every few hundred ms and emits motor deltas. Its latency directly limits how reactively the robot moves, so you fight it with chunking and async.
- **The planner (this week)** is on the *task* path: it queries once per task and emits a skill sequence. Its seconds-scale latency is invisible because the skills it emits take tens of seconds to execute. You don't fight its latency; you barely notice it.

This is why the planner can be a bigger, slower, more capable reasoner than the VLA and still be cheaper *in practice* — it runs far less often. A robot might query the VLA fifty times to execute one skill, and query the planner once to decide the whole sequence of skills. The planner's "expensive" call is amortized over a minute of robot activity; the VLA's "cheap" call happens constantly. Altitude determines latency tolerance: the higher the language model sits, the less its latency matters.

---

## 5. A worked example: "clear the table"

Instruction: "clear the table." World after `detect_objects()`: `cup_1 @ (0.4,-0.1)`, `plate_1 @ (0.5, 0.1)`, `bin_1 @ (0.7, 0.0)` (the bin is the target).

The LLM, prompted with the skills and this world, emits (constrained):

```json
[
  {"skill": "grasp",  "args": {"object": "cup_1"}},
  {"skill": "place",  "args": {"object": "cup_1",   "location": "bin_1"}},
  {"skill": "grasp",  "args": {"object": "plate_1"}},
  {"skill": "place",  "args": {"object": "plate_1", "location": "bin_1"}}
]
```

Grounding (symbolic simulation over the world state):

- `grasp(cup_1)`: cup_1 exists ✓, reachable ✓, gripper empty ✓ → after: holding(cup_1).
- `place(cup_1, bin_1)`: holding(cup_1) ✓, bin_1 reachable ✓ → after: at(cup_1, bin_1), gripper empty.
- `grasp(plate_1)`: exists ✓, reachable ✓, gripper empty ✓ → after: holding(plate_1).
- `place(plate_1, bin_1)`: holding(plate_1) ✓, bin_1 reachable ✓ → after: at(plate_1, bin_1).

Every precondition holds in sequence → **grounded** → execute. This is the happy path the mini-project demonstrates.

Trace what the symbolic simulation is actually doing, because it's the load-bearing mechanism: it maintains a *copy* of the world state and applies each skill's effect to that copy, so when it checks step N's precondition, it's checking against the world *as it would be after steps 1..N-1 have run*. That's why it catches ordering: after the simulated `grasp(cup_1)`, the simulated world has `holding = cup_1`, so the subsequent `place(cup_1, bin_1)`'s precondition `holding(cup_1)` passes. Reverse the two, and when the simulation reaches `place` first, the simulated `holding` is still empty, so the precondition fails. The simulation never touches a real motor; it's pure bookkeeping over a world-state copy, and it catches every precondition/ordering bug in microseconds, before the first real motion. That's an enormous amount of safety for almost no compute — which is exactly why it's the right place to spend your rigor.

Now the failures the LLM is prone to, and why grounding exists. Three classes you will see, each caught by a different check:

- **Hallucinated referent.** It emits `place(cup_1, shelf_top)` — there is no `shelf_top` in the world. The LLM *invented a location*. Static validation catches it (`shelf_top` not in world state) before the arm reaches for a phantom shelf.
- **Ordering violation.** It emits `place(cup_1, bin_1)` *before* `grasp(cup_1)` — individually valid calls, broken order. Symbolic simulation catches it: when it reaches `place`, the precondition `holding(cup_1)` is false because `grasp` hasn't run.
- **Infeasible-but-symbolically-fine.** It emits `grasp(cup_1)` when `cup_1` is across the room and unreachable — exists, but the affordance precondition `reachable(cup_1)` fails. The affordance check (the "Can" of SayCan) catches it where a pure existence check would not.

**These are exactly the bugs an LLM produces, and exactly what grounding is for.** None of them is caught by the LLM being smart or the prompt being good — each is caught by an explicit, world-grounded check. A planner without these checks ships all three to the actuators with full confidence. Lecture 2 builds the machinery that catches each, and the challenge makes you red-team your own planner to produce all three on purpose and prove your checks catch them.

The deeper point: an LLM planner *will* produce these errors at some rate, no matter how good the model or the prompt — that's the nature of a probabilistic text generator applied to a task with hard physical constraints. Your job is not to make the LLM perfect (impossible); it's to make the *system* safe despite an imperfect LLM, by checking every plan against the world before executing it. The LLM is allowed to be wrong; the system is not allowed to *act* on the wrongness. That separation — fallible proposer, infallible checker — is the architecture of the whole week, and it is the same architecture as Week 37's VLA-plus-gate, one level up.

## 6. An alternative representation: Code-as-Policies

Worth knowing because you'll meet it: instead of a flat list of skill calls (a *plan*), some systems have the LLM emit **code** that calls the skill API — a small Python-like program with loops and conditionals (Code-as-Policies, Liang et al.). "Clear the table" becomes roughly:

```python
objects = detect_objects()
for obj in objects:
    if reachable(obj):
        grasp(obj)
        place(obj, "bin_1")
```

The appeal: code naturally expresses loops ("for each object"), conditionals ("if reachable"), and reuse, which a flat plan can't. The cost: you're now letting an LLM emit *executable code*, which is harder to ground and gate than a flat list — you must sandbox it, validate the skill calls it makes at runtime, and reason about its control flow. For a small, well-defined task family, a flat constrained plan (what this week builds) is easier to make safe — you can symbolically simulate a flat list; you cannot easily symbolically simulate arbitrary code with loops. For open-ended tasks where loops and conditionals are essential, code-as-policies is more expressive at the cost of more grounding work.

The trade-off, then: **flat plans are easier to ground; code is more expressive.** This week builds flat plans because the grounding story is cleaner and the safety case is stronger — exactly what you want while learning the pattern and what a certifiable robot wants. Reach for code-as-policies when the task genuinely needs control flow the flat plan can't express, and budget the extra grounding work it demands. Either way, the principle holds: whatever the LLM emits — a flat plan or a program — the skill calls inside it get grounded against the world before they touch a motor. The representation changes; the "fallible proposer, infallible checker" architecture does not.

---

## 7. Recap

You should now be able to:

- Explain the LLM-as-planner inversion: the LLM decides *what* (task decomposition, its strength), the skills handle *how* (control, their strength) — the TAMP split.
- State SayCan's Say×Can decomposition, why Say-alone gives useful-but-impossible plans and Can-alone gives possible-but-aimless actions, and how the modern form replaces the affordance value function with runtime grounding/validation.
- Design a skill: a typed signature, a precondition, an effect, and a hidden implementation that calls the real stack.
- See the C23 bridge: a skill library is a tool API; the agent tool-use loop is the planner loop; with physical grounding and irreversibility as the new concerns.
- Trace the instruction → perceive → prompt → constrained plan → ground → execute → re-plan loop, and explain why the slow LLM is fine off the control path.
- Recognize the three canonical LLM planning bugs (hallucinated referent, violated precondition/ordering, infeasible-given-affordances) and which check catches each.
- Design a skill library of composable verb-primitives with checkable preconditions, so the planner can handle tasks you didn't enumerate.

The one-sentence summary of the lecture: **the LLM is a fallible proposer of plans over a skill library; an explicit, world-grounded checker is the infallible disposer; and the architecture's whole job is to let the proposer's usefulness through while the checker stops its mistakes from reaching the actuators.** Hold that, and Lecture 2's constrained decoding, grounding, and safety gates are all just the *implementation* of "check every plan against the world before executing it."

A final note on why this caps Phase 5. Over the last weeks you put language at every altitude of the stack: at the *action* level (week 37, the VLA emits a motor action), and now at the *task* level (this week, the LLM emits a plan of skills). Both share the same hard-won lesson — a language model is a powerful, fallible proposer that must be grounded and gated, never trusted raw. The capstone (weeks 41–48) integrates both: a planner decides the skill sequence, and the skills (some VLA-driven) execute it, every layer grounded, every layer leashed. You're not learning a new safety idea each week; you're learning the *same* idea — proposer plus independent checker — applied at one more altitude. That repetition is the point: by the capstone, "ground it and leash it" should be reflexive, because it's the one rule that makes a language-driven robot safe to put in a room with a person.

Next: how to *constrain* the LLM's output so it can only emit valid skill calls, how to *ground* and repair a plan, how to wire the executor with closed-loop re-planning, how to deploy a local 8B planner, and how to make the safety case for a language-driven robot. Continue to [Lecture 2 — Grounding, Constrained Output, and Safety](./02-grounding-constrained-output-and-safety.md).

---

## References

- *SayCan ("Do As I Can, Not As I Say")*: <https://say-can.github.io/> · <https://arxiv.org/abs/2204.01691>
- *Code as Policies*: <https://code-as-policies.github.io/>
- *Inner Monologue (closed-loop re-planning)*: <https://innermonologue.github.io/>
- *ProgPrompt (skill API as prompt)*: <https://progprompt.github.io/>
- *ReAct (the agent reason-act loop, the C23 substrate)*: <https://arxiv.org/abs/2210.03629>
- *Llama 3.1 8B (the local planner)*: <https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct>
