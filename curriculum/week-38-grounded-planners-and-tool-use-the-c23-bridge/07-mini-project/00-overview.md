# Mini-Project — `crunch_planner`: A Grounded, Constrained, Closed-Loop LLM Planner

> Build the node the syllabus asks for: a grounded planner that takes "clear the table," runs a **local small LLM (Llama 3.1 8B via Ollama or vLLM)** constrained to your skill library, **grounds** every emitted skill call against the world state, dispatches the grounded plan skill-by-skill to the Week-32/37 stack, and **re-plans** when a skill fails. Demonstrate it on "clear the table" with an injected skill failure recovered by re-planning.

This is the artifact that turns this week's two lectures — and the whole C23 bridge — into the system the syllabus names: "build a grounded planner that takes 'clear the table' and emits a skill sequence; use a local small LLM as the planner; constrain output with a grammar; wire skills to the week-32 stack; demonstrate." It is the top of the autonomy stack: above perception, above control, above the VLA — the layer that turns an instruction into a sequence of the things the robot already knows how to do.

**Estimated time:** ~9 hours, split across Thursday, Friday, Saturday, and Sunday in the suggested schedule.

**Compounds forward:** This planner is the **task layer of the capstone**. The capstone's "behavior tree at the top" dispatches a plan; this is what produces that plan from language. The skill library you define here is the capstone's skill set; the grounding and safety gates are documented mitigations in the Week-41 safety case; the closed-loop re-planning is what survives the Week-46 chaos drill (planner-deadlock-at-doorway is recovered by re-planning). Build it well now; you'll extend, not replace, it.

---

## What you will build

A small ament-python package `crunch_planner` with three deliverables:

1. **`crunch_planner/skills.py`** — the skill library: typed skills with preconditions, effects, and implementations that call the real stack (MoveIt2 grasp, Nav2 navigate, the Week-37 `crunch_vla` for grasp/place). The single source of truth for what the robot can do.
2. **`crunch_planner/planner.py`** — the constrained planner + grounding. Builds the prompt (skill signatures + world state), calls the local LLM with schema-constrained output, validates (static + symbolic simulation + affordance + safety gate), and repairs via re-prompting. Returns a grounded plan or a safe-stop.
3. **`crunch_planner/executor.py`** + a demo — the closed-loop executor: run each grounded skill (through the Week-37 leash), re-observe, check the effect, re-plan from the real state on failure. A `launch/clear_table.launch.py` (or a script) demonstrates "clear the table" end-to-end with an injected skill failure.

By the end you have a public repo of ~400–500 lines (excluding the LLM) demonstrating an end-to-end language-to-action planner with grounding, constrained decoding, safety gates, and closed-loop recovery — the capstone-grade centerpiece of the AI-robotics phase and the close of Phase 5.

---

## Why grounding and the executor are separate from the LLM call

You *could* fold everything into one "call the LLM and run the plan" function. Don't. Separate the layers:

- **`skills.py`** is the contract; it changes when the robot's capabilities change, not when the LLM does.
- **`planner.py`**'s grounding is the safety-relevant code; it must be unit-testable without a GPU or Ollama (Exercise 2's stub path proves this), and auditable in a safety case as the place where "the LLM proposes, the runtime disposes" happens.
- **`executor.py`**'s closed loop is the robustness code; it changes when the failure model changes, not when the LLM does.

The LLM is the *least* stable part (you'll swap Llama 3.1 for whatever's best next quarter); the grounding and executor are the stable, safety-critical parts. Keep them apart so the safety-critical code doesn't churn every time you change the model.

---

## Package layout

```
crunch_planner/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_planner
├── crunch_planner/
│   ├── __init__.py
│   ├── skills.py            # the skill library (signatures, pre/effect, impl)
│   ├── world.py             # the world-state model (objects, locations, reachable)
│   ├── llm_backend.py       # the local LLM wrapper (Ollama/vLLM) behind one iface
│   ├── planner.py           # prompt + constrained call + grounding + repair
│   ├── safety.py            # forbidden-action list + human-confirmation gate
│   └── executor.py          # closed-loop execute / re-observe / re-plan
├── launch/
│   └── clear_table.launch.py
└── test/
    ├── test_grounding.py    # static + symbolic-sim validation (no LLM, no GPU)
    └── test_executor.py     # re-plan triggers on a failed effect (no LLM)
```

If you build a `crunch_planner_msgs` interfaces package, define the instruction and the plan/decision log as real `.msg` types. A `std_msgs/String` instruction + JSON status is an acceptable minimum.

---

## Deliverable 1 — the skill library (`skills.py`)

The robot's API surface (Lecture 1 §3). Define at least `detect_objects`, `grasp(object)`, `place(object, location)`, `navigate(waypoint)`, each with:

- A **typed signature** and a one-line description (these go in the LLM prompt).
- A **precondition** — a *checkable boolean* over world state (`exists ∧ reachable ∧ gripper_empty` for grasp).
- An **effect** — the world-state change.
- An **implementation** — the real dispatch: `grasp` calls MoveIt2 / the Week-37 `crunch_vla` (with its gate + fallback); `navigate` sends a Nav2 goal; `place` likewise.

The precondition/effect pairs are what `planner.py` symbolically simulates and what `test_grounding.py` tests — no robot needed.

---

## Deliverable 2 — the planner + grounding (`planner.py`)

The front-end (Lecture 2 §1–2):

1. Build the prompt: a system prompt with the skill signatures + descriptions + a forbidden-action statement (the prompt half), and a user prompt with the instruction and the current world state.
2. Call `llm_backend.plan()` with **schema-constrained output** (`format=PLAN_SCHEMA` for Ollama; `guided_json` for vLLM) and **temperature 0** (deterministic, reproducible).
3. **Ground** the well-formed plan: static validation (skill exists, args are real typed referents), symbolic simulation (preconditions hold in sequence), affordance check (referenced objects reachable), safety gate (no forbidden action without confirmation).
4. On an ungrounded plan, **repair**: re-prompt with the *specific* errors, up to N retries; if still ungrounded, return a **safe-stop** (do nothing / ask a human). Never return an ungrounded plan.

`llm_backend.plan(instruction, world) -> list[skill_call]` is the one function that touches the LLM; everything else is testable without it.

---

## Deliverable 3 — the executor + the demo (`executor.py`)

The closed loop (Lecture 2 §3):

1. Ground a plan via `planner`.
2. Execute each skill via its `impl` — **through the Week-37 safety leash** (the grounding gate + clamps + classical fallback on each grasp/place).
3. **Re-observe** after each skill (re-run `detect_objects`); check the skill's expected **effect** actually holds.
4. If a skill failed or the effect doesn't hold, **re-plan from the current real world state** (not the stale plan) and continue. Cap re-plans; on exhaustion, safe-stop.

The demo (`launch/clear_table.launch.py` or a script): run "clear the table" on a tabletop with ≥ 2 objects, **inject a skill failure** (a dropped grasp, or a moved object), and show the executor detect it and re-plan to completion. Print the full trace:

```
[planner] "clear the table" | world: {cup_1, plate_1, bin_1}
[planner] plan GROUNDED: [grasp(cup_1), place(cup_1,bin_1), grasp(plate_1), place(plate_1,bin_1)]
[exec] grasp(cup_1) ... cup SLIPPED; effect not held -> RE-PLAN
[planner] re-plan from real state {cup_1 on table, plate_1 on table}
[exec] grasp(cup_1) ok; place(cup_1,bin_1) ok; grasp(plate_1) ok; place(plate_1,bin_1) ok
[exec] TASK COMPLETE: table cleared (re-plans: 1)
```

---

## Rules

- **You may** use Ollama / vLLM with Llama 3.1 8B (or a comparable open small model), grammar/schema constraint, pydantic/jsonschema validation, and your existing ROS2 + MoveIt2 + Nav2 + Week-37 stack.
- **You must not** dispatch an *ungrounded* plan to the executor. The whole project's reason to exist is that nothing ungrounded reaches the actuators.
- **You must not** dispatch a skill action without the Week-37 per-skill leash on grasp/place — two levels of grounding (plan + action) are both required.
- **You must** use a *local* LLM (the syllabus requirement), schema/grammar-constrained, temperature 0.
- **You must** demonstrate closed-loop re-planning on an injected failure.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy. The grounding/executor tests must pass without a GPU or Ollama.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-38-crunch-planner-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_planner` succeeds with no warnings.
- [ ] `skills.py` defines ≥ 4 typed skills with checkable preconditions, effects, and real-stack implementations.
- [ ] `planner.py` calls a *local* LLM with schema/grammar-constrained, temperature-0 output, and grounds every plan (static + symbolic + affordance + safety) before returning it.
- [ ] An ungrounded plan (hallucinated object or bad ordering) is caught and **repaired via re-prompting** (or safe-stopped), demonstrated in a trace.
- [ ] `executor.py` runs the closed loop: re-observe, check effect, re-plan on failure; each grasp/place goes through the Week-37 leash.
- [ ] The demo runs "clear the table" with an injected skill failure recovered by re-planning, to completion.
- [ ] `colcon test --packages-select crunch_planner` passes, with at least:
  - `test_grounding.py`: grounds a good plan; rejects a hallucinated-object plan (static); rejects a place-before-grasp plan (symbolic) — all without an LLM.
  - `test_executor.py`: a failed effect triggers a re-plan; the task completes after recovery.
- [ ] A `README.md` with the skill library, the architecture diagram, the local-LLM setup, the safety-gate description, and a recorded demo trace.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Skill library** | 15 | ≥ 4 typed, composable skills; checkable preconditions/effects; real-stack impls. |
| **Constrained planning** | 20 | Local LLM; schema/grammar constraint so only library skills emit; temperature 0; the prompt half (signatures, forbidden-action) present. |
| **Grounding** | 25 | Static + symbolic-simulation + affordance + safety gate; nothing ungrounded reaches the executor; repair-via-reprompt with a safe-stop fallback; isolated and tested without an LLM. |
| **Closed-loop executor** | 20 | Re-observe + effect-check + re-plan; each skill wears the Week-37 leash; injected-failure recovery demonstrated. |
| **Demo + tests** | 15 | "clear the table" completes with an injected failure recovered; `colcon test` green without a GPU. |
| **Docs & hygiene** | 5 | Clear README with a recorded trace; sensible commits; no model weights checked in. |

**90+** is portfolio-grade and ready to be the capstone's task layer. **70–89** works but has a soft grounding layer or no closed-loop recovery. **Below 70** means an ungrounded plan can reach the executor, or there's no re-planning — fix grounding and the closed loop first.

---

## Stretch goals

- **LLM proposes, classical planner orders.** Use the LLM only to choose the *goal* (objects → bin), and a classical search over preconditions/effects to *order* the skills. Compare reliability: does this eliminate ordering errors entirely?
- **Human-confirmation gate.** Add an irreversible skill (`pour`) that the executor blocks on until a human confirms. Demonstrate the block and the approval.
- **Model comparison.** Run the demo with Llama 3.1 8B and a 3B model. Measure plan quality (grounded-on-first-try rate) and latency. Quantify how much more the smaller model hallucinates — the data behind "small is enough, but not too small."
- **Foxglove plan panel.** Stream the current plan and per-skill status to Foxglove so an operator sees the plan, the grounding verdict, and the re-plans live — a preview of the Week-43 dashboard.

---

## A note on testing without a robot or an LLM

The grading explicitly requires `colcon test` to pass *without* a GPU or Ollama, and that's not an accident — it's the design principle in action. The safety-relevant code (grounding, the executor's re-plan logic, the gates) must be pure functions of their inputs (a plan, a world state, counters), so you can test them exhaustively with synthetic plans and worlds, no LLM and no robot. The exercises proved this is possible: Exercise 2's `ground_plan` and Exercise 3's closed loop both run deterministically on stubs. If your `gate`/grounding code *can't* be tested without an LLM, it's too entangled with the LLM call — refactor until the checker is a pure function the tests can hammer with a good plan, a hallucinated-object plan, and a misordered plan, asserting the right verdict on each. The LLM is the part you can't unit-test (it's stochastic and heavy); the grounding is the part you *must* unit-test (it's safety-critical). Keeping them separable is what makes both possible.

## How this connects to the rest of C24

- **Week 39 (edge ML)** profiles this planner's seconds-scale latency alongside the millisecond-scale perception and the VLA, in one latency budget on the Orin. The planner is the slowest stage and the most latency-tolerant — Week 39 quantifies why that's fine.
- **Week 40 (Phase 5 milestone)** the language-conditioned pick-and-place end-to-end uses this planner as the task layer.
- **Week 41 (safety case)** the grounding and safety gates are documented mitigations.
- **Week 46 (chaos drill)** the planner-deadlock-at-doorway drill is recovered by this executor's closed-loop re-planning. You built the recovery here. Push it, keep the repo, make it the capstone's brain.

## A closing note on what makes this capstone-grade

This mini-project is the highest layer of the autonomy stack you've built over 38 weeks, and a reviewer grades it on one question: **can an ungrounded or unsafe plan reach the actuators?** If the answer is ever yes — a hallucinated object grasped, a place-before-grasp executed, an irreversible action run without confirmation — the project fails its reason to exist, no matter how impressive the happy-path demo. The discipline a reviewer (and a capstone panel) looks for is layered: constrained decoding so the LLM can't emit a non-library skill, grounding so an ungrounded plan can't reach the executor, the per-skill leash so a sound plan's drifted action can't reach the motors, the safety gates so an irreversible action can't run unconfirmed, and the closed loop so a failed skill triggers a re-plan instead of a cascade. Each layer catches what the others can't.

The anti-pattern — a slick "clear the table" demo with no grounding tests, no injected-failure recovery, and the safety logic tangled into the LLM call where it can't be audited — gets a low grade precisely because it's the overconfidence the whole week (and the whole AI-robotics phase) warns against. The deliverable is not "the planner works"; it's "the planner is *grounded*, *gated*, and *recovers*, and here is the evidence that nothing ungrounded ever reaches the actuators." That evidence — a grounding trace, a caught hallucination, an injected-failure recovery, a measured zero-ungrounded-plans-executed rate — is what turns this from a demo into the task layer of a robot you could defend in a safety case. Build the evidence, not just the demo; the evidence is the portfolio piece.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
