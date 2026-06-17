# Week 11 — Challenges

The exercises drill each estimator in isolation. **The challenge makes you the SLAM back-end engineer.** You're handed a noisy odometry trajectory and one loop closure, and you have to turn it into a globally-consistent map by building and solving a real pose graph — the same job `slam_toolbox`'s back-end does, except you write it.

## Index

1. **[Challenge 1 — A pose graph from noisy odometry + one loop closure](./challenge-01-pose-graph-from-odometry.md)** — given a drifting odometry trajectory that should have returned to its start, build a GTSAM pose graph, add the loop-closure constraint, optimize, and quantify how much the loop closure reduced the drift. Then plant a *false* loop closure and prove a robust noise model survives it. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 2 midterm in Week 16, where you defend your estimation choices to a panel. The reviewer will ask "filter or smoother, and why?" and "what does a loop closure actually do to your covariance?" — this challenge *is* that conversation, rehearsed with real numbers. The engineer who can build a pose graph from scratch and explain why the loop closure tightened it is the one who can debug a SLAM stack when it drifts at 3 a.m.
