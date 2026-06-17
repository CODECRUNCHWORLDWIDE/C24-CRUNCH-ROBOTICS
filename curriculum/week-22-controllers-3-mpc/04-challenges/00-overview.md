# Week 22 — Challenges

The exercises drill the MPC mechanics. **The challenge makes you the controls engineer who has to make MPC actually deployable.** It's not enough to track a path — you have to track it while avoiding an obstacle, respecting hard limits, *and* fitting inside a real per-step latency budget on real-ish hardware. That triple — feasible, safe, fast enough — is the entire job of shipping an MPC, and it's exactly what you'll defend at the Phase 3 milestone in Week 24.

## Index

1. **[Challenge 1 — MPC with an obstacle and a latency budget](./challenge-01-mpc-with-an-obstacle-and-a-latency-budget.md)** — extend the bicycle MPC with linearized obstacle-avoidance constraints, make it route around an obstacle blocking the figure-8, and then make it fit a hard per-step latency budget — documenting the horizon-vs-latency trade-off and the infeasibility-recovery plan. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 milestone in Week 24, where you defend your controller stack — and specifically the question "is the MPC fast enough to ship?" The skill — making an MPC respect a hard constraint *and* a hard deadline, and being honest about the trade-off between horizon (foresight) and solve time (deployability) — is exactly what separates an engineer who got an MPC working in a notebook from one who got it running on a robot near people. Anyone can write a slow MPC that tracks beautifully offline. The job is the one that's also feasible and in budget at 3 a.m. on the warehouse floor.
