# Week 27 — Challenges

The exercises drill the pipeline. **The challenge makes you the ML engineer who has to prove an improvement.** You're asked not just to run BC and DAgger, but to *quantify* the gap between them on a fair protocol and explain it with evidence — the way you'd defend a result in a design review.

## Index

1. **[Challenge 1 — Quantify BC vs. BC+DAgger, and explain the gap](./challenge-01-bc-vs-dagger.md)** — run behavior cloning and one-plus rounds of DAgger on the same task, evaluate both on a *fixed* protocol (same starts, novel ones included, 20+ trials), report success rates with intervals, classify the failures, and explain the covariate-shift gap with state-visitation evidence. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for Weeks 29–30, where you compare Diffusion Policy and ACT against this BC+DAgger baseline on the *same* demonstrations. That comparison is only meaningful if your BC+DAgger numbers come from an honest, fixed protocol — otherwise "the diffusion policy is better" is a vibe. The skill — running a fair head-to-head, reporting a rate with an interval, and classifying *why* the failures happen — is exactly what separates an engineer who "got a policy working" from one who can tell you which method to ship and why.
