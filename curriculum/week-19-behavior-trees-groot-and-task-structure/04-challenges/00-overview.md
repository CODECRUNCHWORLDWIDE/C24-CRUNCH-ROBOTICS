# Week 19 — Challenges

The exercises drill the tree mechanics. **The challenge makes you the on-call engineer.** You're handed a patrol behavior tree that "mostly works" but misbehaves in three specific, structural ways, and you have to diagnose *why* from the tree structure and Groot 2 — without the luxury of having authored the broken tree yourself.

## Index

1. **[Challenge 1 — The misbehaving tree](./challenge-01-the-misbehaving-tree.md)** — a patrol tree with three planted structural bugs (a non-reactive yield that finishes driving before noticing a person, a missing timeout so the robot waits forever, and an inverted condition that yields backwards). Diagnose each from the tree and Groot 2, then fix it. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 integration (Week 24) and the capstone, where your task tree is reviewed and must demonstrably do the right thing in every scenario. The skill — reading a tree you didn't author, watching it tick in Groot 2, and naming the structural bug — is exactly what separates a junior who "can draw a behavior tree" from a senior who can debug a robot's task logic at 3 a.m. by *watching which branch it's in*.
