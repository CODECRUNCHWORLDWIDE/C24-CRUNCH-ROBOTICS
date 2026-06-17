# Week 38 Homework

Six problems that drive the grounded-planning discipline into your fingers and close out Phase 5. The full set should take about **5 hours**. Work in your Week 38 Git repository (the same workspace as the exercises and the `crunch_planner` mini-project) so every problem produces at least one commit you can point to at the Phase 5 milestone in Week 40.

The headline deliverable is **Problem 4 — the grounded-planner demo write-up**, the syllabus's "demonstrate" requirement for "clear the table." Treat it as a section of your future capstone safety case, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

Have a local LLM available (`ollama pull llama3.1:8b`) and your skill stack. If you lack the compute this week, the substitution — run against the Exercise-2/3 stub planner extended with your scenarios — is noted per problem; the *methodology* is the graded part either way.

---

## Problem 1 — Deploy the local planner

**Problem statement.** Stand up Llama 3.1 8B locally via Ollama (or vLLM). Send it your skill signatures + a world description + an instruction, with **schema-constrained output** and **temperature 0**, and capture a valid skill-call plan. Record the setup and one plan in `notes/week-38/local-llm.md`.

**Acceptance criteria.**
- The install/run commands (`ollama pull llama3.1:8b`, the Python call with `format=<schema>`).
- One captured plan that is schema-valid (only library skills, right shape).
- The planning **latency** (wall-clock seconds for one plan) and a one-sentence note on why seconds is acceptable for a planner.
- Committed.

**Hint.** Ollama's `format=<json schema>` does the constraint; set `options={"temperature": 0.0}` for reproducibility. If you can't run a local LLM, document the procedure against the Ollama structured-outputs docs and use the Exercise-2 stub for the plan, labeled as a substitution.

**Estimated time.** 45 minutes.

---

## Problem 2 — Constrained vs. unconstrained

**Problem statement.** Run the *same* instruction + world through the LLM **without** the schema constraint (free-text) and **with** it. Compare: how parseable is the free-text output? How many runs produce a non-library skill or malformed structure unconstrained vs. constrained? Write it up in `notes/week-38/constrained-vs-not.md`.

**Acceptance criteria.**
- Side-by-side: ≥ 3 unconstrained outputs (free text) and ≥ 3 constrained outputs (schema-valid) for the same prompt.
- A count of how many unconstrained runs were *not* cleanly parseable into a plan, vs. constrained (should be 0 malformed).
- One sentence: what the constraint guarantees, and what it still does *not* (grounding).
- Committed.

**Hint.** Unconstrained, an 8B model will often add prose ("Sure! Here's a plan:") or invent a skill. That's the failure the constraint eliminates. If using the stub, simulate by generating "free-text-like" strings vs. schema-valid dicts and showing the parsing difference.

**Estimated time.** 40 minutes.

---

## Problem 3 — Ground a batch of plans

**Problem statement.** Take 5 plans (real LLM output, or hand-written to span the classes) against a fixed world and run them through your grounding layer (static + symbolic simulation + affordance). For each, report grounded/rejected and the catching layer. Include at least one hallucinated-object plan and one ordering-violation plan. Write it up in `notes/week-38/grounding-batch.md`.

**Acceptance criteria.**
- A table: plan → grounded? → catching layer (static / symbolic / affordance) → error message.
- At least one hallucinated-object rejection (static) and one ordering-violation rejection (symbolic).
- One sentence distinguishing what static validation catches vs. what symbolic simulation catches.
- Committed.

**Hint.** Reuse `ground_plan` from Exercise 2. The hallucinated-object plan fails static; the ordering plan fails symbolic; an unreachable-object plan fails the affordance check. Make sure your world has an unreachable object to exercise the affordance layer.

**Estimated time.** 45 minutes.

---

## Problem 4 — The grounded-planner demo (headline deliverable)

**Problem statement.** This is the syllabus deliverable: "build a grounded planner that takes 'clear the table' and emits a skill sequence ... demonstrate." Run your `crunch_planner` (or a minimal version) on "clear the table" with ≥ 2 objects, **inject one skill failure** (a dropped grasp or a moved object), and capture the full trace from instruction to completion. Write it up at `notes/week-38/clear-table-demo.md` against this template:

1. **Setup** — the skill library, the world (objects, locations), the LLM (model + temperature).
2. **The plan** — the instruction, the constrained plan the LLM emitted, and the grounding verdict (with the symbolic-simulation trace showing each precondition holding).
3. **Execution** — the skill-by-skill execution trace.
4. **The injected failure** — what you injected, when, and how the executor detected it (which effect didn't hold).
5. **The recovery** — the re-plan from the real state and the completion.
6. **Safety + reflection** — which gates fired (or would have), the count of ungrounded plans that reached the executor (must be 0), and one improvement.

**Acceptance criteria.**
- `notes/week-38/clear-table-demo.md` exists, hits all six headings, ~500–700 words.
- The grounding trace shows preconditions holding in sequence (symbolic simulation), not just "grounded: yes."
- The injected failure is detected by a *failed effect check*, not by luck, and recovered by re-planning.
- The count of ungrounded plans reaching the executor is stated (0).
- Committed.

**Hint.** If you can't run the full robot stack, run the Exercise-3 executor (stub skills) with the real planner (or stub planner) and inject the failure there — the *closed-loop logic* is the graded skill, clearly labeled if stubbed. Quote the real trace lines.

**Estimated time.** 1 hour 15 minutes.

---

## Problem 5 — A safety gate for an irreversible skill

**Problem statement.** Add an irreversible skill to your library (`pour(container, target)` or `drop_from_height(object)`) and a **human-confirmation gate** (Lecture 2 §5.3): the planner may *propose* it, but the executor blocks until a human approves. Demonstrate the block and an approval. Write it up in `notes/week-38/confirmation-gate.md`.

**Acceptance criteria.**
- The irreversible skill is in the library and on the confirmation list.
- A trace showing the executor *blocking* on the skill pending confirmation, and proceeding only after (simulated) approval.
- One sentence on why this gate is a *runtime* mechanism the planner cannot override, not a prompt instruction.
- Committed.

**Hint.** The gate is a hard check in the executor: `if skill in IRREVERSIBLE and not confirm(): block`. A prompt saying "always confirm before pouring" is the *prompt half* — it reduces but doesn't guarantee; the executor gate is the *runtime half* — it guarantees. Make both, but the trace must show the runtime gate.

**Estimated time.** 40 minutes.

---

## Problem 6 — The C23 retrospective

**Problem statement.** Write a one-page reflection at `notes/week-38/c23-bridge.md` mapping what you built this week back to C23 (Crunch Agents) concepts: tool use, structured/constrained output, grounding, and the agent loop. For each C23 concept, state its C24 robot analogue and the *new* concern that robots add (physical grounding, irreversibility, real-time failure). If you didn't take C23, map it to the lecture material instead.

**Acceptance criteria.**
- `notes/week-38/c23-bridge.md` maps ≥ 4 C23 concepts to their C24 analogues in a table.
- For each, the *new* robot-specific concern is named (e.g., "a bad `send_email` is embarrassing; a bad `grasp` can injure").
- One paragraph: the single most important difference between an agent that manipulates text and one that manipulates the physical world.
- Committed.

**Hint.** Lecture 1 §3.2 has the C23↔C24 table to start from; extend it with your own experience. The headline difference is *consequence*: text agents are reversible and cheap to be wrong; robot agents are irreversible and can hurt people — which is why the runtime grounding/gates matter so much more.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Deploy the local planner | 45 min |
| 2 — Constrained vs. unconstrained | 40 min |
| 3 — Ground a batch of plans | 45 min |
| 4 — Clear-table demo (headline) | 1 h 15 min |
| 5 — Irreversible-skill gate | 40 min |
| 6 — C23 retrospective | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_planner` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — the capstone reuses it as the task layer. This closes Phase 5: next week (39) profiles the whole AI stack on the edge, and Week 40 unseals the capstone. Then take the [quiz](./05-quiz.md) with your notes closed.
