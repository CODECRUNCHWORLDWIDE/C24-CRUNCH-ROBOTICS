# Week 38 — Grounded Planners and Tool Use (the C23 Bridge)

Last week the language model *was* the policy — instruction in, action chunk out. This week the language model steps up a level: instead of emitting motor commands, it emits a **plan** — a sequence of skills the robot already knows how to execute. "Clear the table" becomes `detect_objects → grasp(cup) → place(bin) → grasp(plate) → place(bin) → ...`. By Friday you will build a **grounded planner**: a local small LLM (Llama 3.1 8B via Ollama or vLLM) that takes a high-level instruction and a description of the world, emits a skill sequence constrained to your actual skill library, validates that every skill call is *grounded* (the objects exist, the skill is applicable), and dispatches it to the Week-32/37 stack. This is the **C23 bridge** — everything Crunch Agents taught you about tool use, structured output, and grounding, now wired to a gripper.

We assume you have the skill stack: MoveIt2 grasping (weeks 23–26), the VLA-as-policy and its safety leash (week 37), the behavior tree integration (week 19), the learned-policy + classical-fallback pattern (week 32). And — strongly — that you took **C23 (Crunch Agents)**, because this week leans on grounded planning, structured tool use, and small-model deployment that C23 covers properly. If you didn't take C23, the lecture notes teach the minimum inline, but expect the planning and grammar-constraint material to be denser for you.

The sentence to internalize before you read another line: **when the planner is a language model, the safety case is half-prompt, half-runtime — and the prompt half is the smaller half.** A language model will happily plan `grasp(the_moon)` or `place(cup, ceiling)` because nothing in its training forbids it. A prompt that says "only use valid skills" *reduces* but does not *prevent* invalid plans — the model still hallucinates a skill you don't have, an object that isn't there, a sequence that grasps an object it never picked up. The engineering this week is the **runtime grounding**: every skill the planner emits is checked against the real skill library (does this skill exist? are its arguments valid?) and the real world state (does this object exist? is it reachable?) *before* a single motor turns. Constrained-grammar decoding makes the output well-*formed*; runtime grounding makes it well-*founded*. You need both.

This is the week your robot stops needing a programmer for every new task and starts taking instructions — and the week you learn that a planner without grounding is a very confident way to drive a gripper into a wall.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** the LLM-as-planner pattern and the SayCan insight: an LLM proposes *what's useful* (the language-likelihood of a skill), an *affordance* model scores *what's possible* (the robot's value/feasibility for that skill), and you act on the product — neither alone is enough.
- **Design** a **skill library**: a set of parameterized, composable robot skills (`detect_objects`, `grasp(object)`, `place(object, location)`, `navigate(waypoint)`), each with a precondition, an effect, and a typed signature the planner can target.
- **Constrain** an LLM's output with a **grammar** (GBNF / JSON-schema / structured decoding) so it can *only* emit syntactically valid skill calls — no prose, no invented JSON, no skill outside the library.
- **Ground** a plan at runtime: validate each emitted skill call against the skill library (skill exists, arguments typed correctly) and the world state (referenced objects exist and are reachable), and reject/repair an ungrounded plan before execution.
- **Implement** the planner + skill-library architecture: instruction + world-state → constrained LLM → validated skill sequence → executor that runs each skill through the Week-32/37 stack, with the per-skill safety leash from Week 37 wrapping each call.
- **Deploy** a local small LLM (Llama 3.1 8B) via **Ollama** or **vLLM** as the planner, with structured/grammar-constrained output, and reason about its latency and the local-vs-API trade-off for a robot.
- **Apply** safety constraints in language space: a forbidden-action list, precondition checks, a human-confirmation gate for irreversible actions, and the closed-loop re-planning that recovers when a skill fails mid-plan.
- **Demonstrate** the syllabus task: "clear the table" → a grounded skill sequence, executed, with at least one injected failure (a skill fails) handled by re-planning.

## Prerequisites

This week assumes you have completed **C24 weeks 1–37**, and strongly recommends **C23 (Crunch Agents)**. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**; a machine that can run a quantized 8B LLM locally (Ollama on CPU is slow-but-works; a GPU or the cloud credit is better), or access to a local-network LLM server.
- The **skill stack**: a working grasp (weeks 23–26), the **Week-37 `crunch_vla` node** (the VLA-as-policy with its gate and fallback), the **behavior tree** (week 19), the **classical fallback** (week 32).
- **C23-level fluency** (or willingness to absorb it inline): what an agent/tool-use loop is, structured output, why grounding matters for LLM-driven systems.
- Comfort with JSON schemas, Python `pydantic`-style validation, and calling a local LLM (Ollama/vLLM HTTP API or the `ollama` Python client).

You do **not** need to have built a robot LLM planner before. We start at the skill library and the SayCan idea and build up to a grounded, constrained, closed-loop planner.

## Topics covered

- **LLM-as-planner.** The shift from "LLM emits actions" (week 37) to "LLM emits a plan over skills"; why high-level task decomposition is what LLMs are *good* at and low-level control is what they're *bad* at; the task-and-motion-planning (TAMP) framing.
- **SayCan and grounded planning.** The Say (language likelihood — what's *useful* to say next) × Can (affordance/value — what's *possible* for the robot) decomposition; why an LLM alone proposes useful-but-impossible actions and an affordance model alone is mute; acting on the product.
- **The skill library.** Parameterized skills with preconditions and effects; the typed skill signature; composability; the skill library as the planner's "API surface" (the C23 tool-use pattern); why a small, well-defined skill set beats a huge fuzzy one.
- **Constrained-grammar output.** GBNF grammars (llama.cpp/Ollama), JSON-schema-constrained decoding (vLLM `guided_json`, Outlines), and function-calling/tool-use APIs; making the LLM emit *only* well-formed skill calls so you never parse free-text into a robot command.
- **Runtime grounding and validation.** Checking each skill call against the library (exists? typed args?) and the world state (object exists? reachable? precondition met?); the difference between *syntactically valid* (grammar) and *grounded* (validation); plan repair / re-prompting on an ungrounded plan.
- **The planner + executor architecture.** Instruction + world-state → constrained LLM → plan → validate/ground → execute skill-by-skill through the Week-32/37 stack, with each skill wrapped in the Week-37 safety leash; closed-loop re-planning when a skill fails.
- **Local small-LLM deployment.** Ollama and vLLM for an 8B model; quantization; the latency reality of a local planner (it plans in seconds, not milliseconds — which is fine, because planning is infrequent); the local-vs-cloud trade-off for a robot that must work offline.
- **Safety in language space.** Forbidden-action lists; precondition gates; human-confirmation for irreversible/high-risk skills; the "half-prompt, half-runtime" safety case — and why the runtime half (validation, gates) is the load-bearing half.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | LLM-as-planner; SayCan; the skill library          |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Constrained-grammar output; skill signatures       |    1.5h  |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Runtime grounding; validation; plan repair         |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Planner + executor; closed-loop re-planning        |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Local LLM deploy; safety in language space; the demo |  0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                             |    0h    |    0h     |     0h     |    0h     |   0h     |     2h       |    0h      |     2h      |
| Sunday    | Quiz, review, demo polish                          |    0h    |    0h     |     0h     |    1h     |   0h     |     2h       |    0h      |     3h      |
| **Total** |                                                    | **6.5h** | **6.5h**  | **4h**     | **4h**    | **5h**   | **9h**       | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | SayCan/grounded-planning papers, the C23 bridge material, constrained-decoding tools, local-LLM deployment, and the talks worth your time |
| [lecture-notes/01-llm-as-planner-saycan-and-skill-libraries.md](./lecture-notes/01-llm-as-planner-saycan-and-skill-libraries.md) | LLM-as-planner, SayCan's Say×Can, the skill library, and the C23 tool-use lineage |
| [lecture-notes/02-grounding-constrained-output-and-safety.md](./lecture-notes/02-grounding-constrained-output-and-safety.md) | Constrained-grammar output, runtime grounding/validation, the executor, closed-loop re-planning, local deploy, and safety in language space |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-skill-library-design.md](./exercises/exercise-01-skill-library-design.md) | Design a typed skill library with preconditions/effects; write the grammar that constrains the planner to it |
| [exercises/exercise-02-constrained-planner.py](./exercises/exercise-02-constrained-planner.py) | A planner that emits a JSON-schema-constrained skill sequence and validates it against the library + world state |
| [exercises/exercise-03-grounded-executor.py](./exercises/exercise-03-grounded-executor.py) | The executor: run a plan skill-by-skill, ground each against world state, re-plan on a skill failure |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-ungrounded-plan.md](./challenges/challenge-01-ungrounded-plan.md) | Make the planner emit plausible-but-ungrounded plans; build the validator that catches each class of ungroundedness |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the grounded-planner demo write-up |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_planner`: a local-LLM grounded planner with a skill library, grammar constraint, runtime grounding, and closed-loop re-planning |

## The "grounded before it grasps" promise

C24 uses a recurring marker for every exercise that ends in a plan actually executing safely. For this week it is the grounded dispatch:

```
[planner] instruction: "clear the table"
[planner] world: {cup_1 @ (0.4,-0.1), plate_1 @ (0.5,0.1), bin_1 @ (0.7,0.0)}
[planner] proposed plan: [detect_objects(), grasp(cup_1), place(cup_1, bin_1), grasp(plate_1), place(plate_1, bin_1)]
[ground] grasp(cup_1): skill OK; cup_1 exists; reachable  -> OK
[ground] place(cup_1, bin_1): skill OK; both exist; bin_1 reachable  -> OK
[ground] full plan GROUNDED  -> executing skill 1/5
```

versus the rejection that saves you:

```
[planner] proposed plan: [grasp(cup_1), place(cup_1, shelf_top), grasp(spoon_1), ...]
[ground] place(cup_1, shelf_top): object 'shelf_top' NOT in world state  -> REJECT (ungrounded)
[ground] grasp(spoon_1): object 'spoon_1' NOT in world state  -> REJECT (hallucinated object)
[planner] plan ungrounded; re-prompting with the validation errors...
```

If the planner emits a skill against an object that doesn't exist and your executor runs it, the robot reaches for a phantom. The point of Week 38 is to make the *grounded* line ordinary and the *ungrounded* line **loud, caught, and fed back to the planner for repair** — never executed.

## Stretch goals

If you finish the regular work early and want to push further:

- Swap the planner LLM: run the same instructions on **Llama 3.1 8B** and a smaller model (3B) and a larger one (70B, if you have the compute), and measure plan quality vs. latency. Smaller models hallucinate skills more; quantify it.
- Add a **human-confirmation gate** for an irreversible skill (`pour`, `cut`, `delete`): the planner must request confirmation, and the executor blocks until a human approves. The seed of the capstone's operator-in-the-loop.
- Implement **plan repair via re-prompting**: when validation fails, feed the *specific* errors back to the LLM ("skill `place` got an unknown location `shelf_top`; valid locations are [...]") and let it fix the plan, up to N retries. Measure how often repair succeeds vs. needing a fallback.
- Compare **grammar-constrained** vs. **function-calling-API** output for the same planner. Which gives more reliably valid skill calls on an 8B model? (Grammar usually wins on small models — measure it.)

## Up next

Week 38 closes Phase 5. **Week 39 (edge ML optimization)** takes the whole AI stack you've now built — the YOLO detector (week 13), the Diffusion Policy (week 29), the VLA wrapper (week 37), and this planner — and asks how it all fits in a latency budget on a Jetson Orin. The planner's seconds-scale latency and the perception's millisecond-scale latency have to coexist; Week 39 is where you profile and optimize the integrated graph. Then **Week 40** unseals the capstone. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
