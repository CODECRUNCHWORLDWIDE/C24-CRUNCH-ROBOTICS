# Week 10 — Challenges

The exercises drill the mechanics. **The challenge makes you tune a real filter and defend the result** — adjust the process noise on a live robot, prove the fused estimate beats raw odometry, and write the tuning rationale a reviewer will read at the Phase 2 midterm.

## Index

1. **[Challenge 1 — Tune the EKF and quantify the fusion](challenge-01-tune-and-quantify-fusion.md)** — drive the Week 6 square, tune `process_noise_covariance` with a documented method, and report the raw-vs-fused drift improvement with a plot and a number. (~120 min)

Challenges are optional for passing the week, but this one produces *the* artifact for the Week 16 midterm and for a real robotics interview: a tuned filter with a before/after drift number and a rationale that isn't superstition. When a panel asks "why those process-noise values?", this challenge is your answer, rehearsed. Do it.
