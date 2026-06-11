# Week 34 — Exercises

Three drills that build from "decide what to randomize" to "compute the gap you closed." Do them in order — Exercise 2's config and sampler feed the challenge's training run, and Exercise 3's gap metric is how you'll score it. Run them against your **Week 28 PPO task** so the randomization augments a policy you already understand.

## Index

1. **[Exercise 1 — Build two randomization recipes](exercise-01-randomization-recipe.md)** — for a grasp task and a nav task, decide *what* to randomize and *how wide*, and justify each choice against the family-to-exposure rule. (~45 min, guided)
2. **[Exercise 2 — Implement a randomization config + sampler](exercise-02-domain-randomization-config.py)** — a seedable `DomainRandomizer` that draws one fresh world per episode from a YAML-style config, with validation that every sample stays in range. (~60 min, runnable)
3. **[Exercise 3 — The gap-closure metric](exercise-03-gap-metric.py)** — compute the sim-to-real gap-closure number from nominal-vs-randomized held-out evals, including the sanity check that catches a contaminated held-out set. (~50 min, runnable)

## How to work the exercises

- **Exercise 1 is paper-and-judgment** — no code. It's the design step the other two implement. Don't skip it; randomizing the wrong family is the week's most common waste of compute.
- **Exercise 2 needs only NumPy** — the sampler is simulator-independent on purpose, so you can build and test it without a GPU. Wiring it into Isaac Lab / Gz Sim is the challenge.
- **Exercise 3 needs only NumPy** — it operates on eval *results* (success counts), so you can develop and unit-test the gap math before you have a trained policy. Then feed it real eval numbers in the challenge.
- Each runnable exercise (`.py`) ends with an **expected output** block. The exact numbers depend on seeds/data; the *shape* (a validated sample set, a gap table) is what must match.

## Running the Python exercises

Both standalone, NumPy only:

```bash
python3 exercise-02-domain-randomization-config.py     # builds + validates a config/sampler
python3 exercise-03-gap-metric.py                      # computes a gap-closure table (self-test)
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-34` to compare.
