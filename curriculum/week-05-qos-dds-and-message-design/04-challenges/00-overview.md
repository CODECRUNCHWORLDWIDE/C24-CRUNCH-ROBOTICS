# Week 5 — Challenges

The exercises drill the mechanics. **The challenge makes you the on-call engineer.** You're handed a running graph that's misbehaving, and you have to diagnose *why* without the luxury of having written the broken code yourself — the way it always happens in the real world.

## Index

1. **[Challenge 1 — Diagnose three QoS mismatches on a live graph](./challenge-01-diagnose-three-mismatches.md)** — a script spins up a graph with three different planted QoS faults across three topic classes. Use `ros2 doctor`, `ros2 topic info -v`, and the rmw incompatibility events to find all three, then prescribe the correct profile for each. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 1 architecture review in Week 8, where you defend your QoS choices to a reviewer. Do it. The skill — reading a graph you didn't build and naming what's wrong in under five minutes — is exactly what separates a junior who "knows QoS" from a senior who can debug a robot at 3 a.m.
