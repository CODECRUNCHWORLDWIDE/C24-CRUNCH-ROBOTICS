# Week 26 — Challenges

The exercises drill the pipeline on cooperative objects. **The challenge hands you the object that breaks it** — a transparent one — and makes you diagnose *why* the confident-looking pipeline returns nothing, then fix it upstream of the network where the real problem lives.

## Index

1. **[Challenge 1 — The transparent-object failure](challenge-01-transparent-object-failure.md)** — reproduce Contact-GraspNet's documented failure on a glass/clear object, prove with the depth image that it is a *perception* (sensor) failure and not a *prediction* (network) failure, then mitigate it with depth completion and re-grasp. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 4 midterm in Week 32, where you defend a learned-policy stack *including its failure envelope*. The skill — knowing that a learned model failing is often the sensor's fault, and being able to prove which — is exactly what separates a junior who "ran Contact-GraspNet" from a senior who can ship it. Do it.
