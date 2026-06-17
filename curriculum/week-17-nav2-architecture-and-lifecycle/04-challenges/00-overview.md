# Week 17 — Challenges

The exercises drill the mechanics. **The challenge makes you the on-call engineer.** You're handed a Nav2 bring-up that "comes up but won't navigate," and you have to diagnose *why* across four subsystems — lifecycle, costmap, TF, and the behavior tree — without the luxury of having written the broken launch yourself.

## Index

1. **[Challenge 1 — The stuck stack](./challenge-01-the-stuck-stack.md)** — a bring-up with four planted faults (a server that won't activate, a costmap that won't load the map, a missing TF frame, and a BT stuck in recovery). Use `ros2 lifecycle get`, `view_frames`, a costmap echo, and Groot 2 to find all four, then prescribe the fix for each. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 work that follows — every week from here forward stacks more servers onto Nav2, and the engineer who can diagnose a stuck bring-up in five minutes is the one who keeps the integration moving. The skill — reading a stack you didn't launch and naming what's wrong from the lifecycle states out — is exactly what separates a junior who "ran the Nav2 tutorial" from a senior who can bring up navigation on a new robot at 3 a.m.
