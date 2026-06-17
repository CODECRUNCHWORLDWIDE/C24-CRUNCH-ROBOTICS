# Week 38 — Exercises

Three drills that take you from "design a skill library and the grammar that constrains a planner to it" to "a closed-loop executor that re-plans when a skill fails." Do them in order — exercise 3 reuses the library and validation from exercises 1 and 2. The first is design-on-paper; the second and third are runnable Python written so they run **today, on a laptop, with no GPU and no Ollama** (they ship a deterministic stub planner alongside the real grounding/validation logic), and convert to the real local LLM by swapping one clearly-marked function.

## Index

1. **[Exercise 1 — Skill-library design](./exercise-01-skill-library-design.md)** — design a typed skill library with preconditions/effects, and write the JSON schema / grammar that constrains a planner to emit only valid calls to it. (~50 min, guided)
2. **[Exercise 2 — The constrained planner](./exercise-02-constrained-planner.py)** — a planner that emits a schema-constrained skill sequence and validates it (static checks + symbolic simulation) against the library and world state. Stub planner now; swap in Ollama. (~50 min, runnable)
3. **[Exercise 3 — The grounded executor](./exercise-03-grounded-executor.py)** — run a grounded plan skill-by-skill, re-observe after each, and re-plan when a skill fails mid-plan (closed loop). (~55 min, runnable)

## How to work the exercises

- Exercise 1 you do mostly on paper / in a schema file. The quality of your skill library determines how often the planner succeeds, so spend the time on clean signatures and *checkable* preconditions.
- Exercises 2 and 3 are pure Python and **run as-is** with a deterministic stub planner, so you can build and test the *grounding, validation, and re-planning* logic without waiting on a GPU or installing Ollama. The files end with an **expected output** block, and the `# TODO` markers show exactly where to wire the real Llama 3.1 8B via Ollama.
- Keep Lecture 2's "constrained ≠ grounded" distinction next to you. Every time a plan is rejected, name *which* layer caught it: the grammar (well-formed), the static validation (real referents), or the symbolic simulation (precondition/ordering).

## Running the Python exercises

```bash
python3 exercise-02-constrained-planner.py
python3 exercise-03-grounded-executor.py
```

No GPU, no Ollama, no ROS2 required for the stub path. Pure standard-library Python. The real-LLM path needs Ollama (`ollama pull llama3.1:8b`) and is gated behind the `# TODO` swap.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-38` to compare.
