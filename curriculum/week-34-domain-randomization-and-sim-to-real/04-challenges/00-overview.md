# Week 34 — Challenges

The exercises give you the recipe, the sampler, and the gap metric. **The challenge is the syllabus lab:** augment the Week 28 PPO with real randomization, evaluate on a held-out "real-style" world, and report the gap you closed — the evidence that sim-to-real worked.

## Index

1. **[Challenge 1 — Close the gap](./challenge-01-close-the-gap.md)** — train two policies (nominal and randomized) on the Week 28 task, evaluate both on a held-out world neither trained on, and produce the gap-closure table with its sanity line. (~3–4 h, including one randomized training run)

Challenges are optional for passing the week, but this one *is* the week's deliverable — the syllabus says "augment the week-28 PPO with visual + dynamics randomization; roll out on a held-out real-style eval world; quantify the gap closure." The skill it builds — producing an honest, defensible sim-to-real result rather than claiming "it transfers" — is exactly what the Phase 5 milestone (Week 40) and the capstone safety case (Week 41) demand. Any sim-trained capstone result that lacks a gap number is not credible; this challenge teaches you to produce one.
