# Week 39 — Challenges

One challenge this week, and it is the real one: take a graph that is multiples over budget and bring it under the 50 ms cycle target with a *documented, measured* accuracy cost. This is the capstone-grade version of the week's whole thesis.

## Index

1. **[Challenge 1 — Hit the budget](challenge-01-hit-the-budget.md)** — start from a profiled graph that is ~3x over the 50 ms cycle target, climb the optimization ladder per-stage by what the profile says, and produce the before/after latency report with both columns (latency win *and* named accuracy cost) for every change. (~3 hours)

## How to work the challenge

- **Profile first.** You may not apply any optimization to a stage the profiler did not flag (Lecture 1 §1). The challenge is graded partly on whether your fixes matched the diagnosis.
- **Climb the ladder cheapest-first** (Lecture 2 §1). FP16 and composable containers before INT8; INT8 before QAT/pruning.
- **Both columns, every change.** A speedup with no accuracy number is a non-answer (Lecture 1 §7).
- **Re-measure the whole graph after each change** — never trust the sum of individually-fixed stages.
