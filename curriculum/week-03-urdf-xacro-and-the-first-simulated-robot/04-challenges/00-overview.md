# Week 3 — Challenges

One challenge this week. It is harder and more open-ended than the exercises, and it is the most realistic thing you do all week: a teammate hands you a robot description that detonates on spawn, and you have to diagnose and fix it under the four-cause differential from Lecture 1 — then write up what you found.

## Index

1. **[Challenge 1 — Fix the exploding robot](./challenge-01-fix-the-exploding-robot.md)** — a provided URDF with bad inertials and missing/overlapping collision geometry explodes the instant it spawns. Diagnose every fault, repair it, and document the inertia-tensor sanity checks you applied. (~2 hours)

## How to work the challenge

- Treat it like an on-call ticket: reproduce the failure first, form a hypothesis from the symptom, then test the hypothesis.
- Use the diagnosis workflow from Lecture 1 §1.7 *in order*. Do not start randomly editing numbers — that is how you turn one bug into three.
- Keep a running log as you go. The writeup is half the grade, and the writeup is just your log, cleaned up.
- "It spawns now" is not done. "It spawns, sits perfectly still, drives smoothly, and I can name every fault I fixed and the check that would have caught it" is done.

Submit your repaired URDF, your diagnosis writeup, and a short screen recording (or a sequence of screenshots) showing the robot spawning cleanly and sitting still.
