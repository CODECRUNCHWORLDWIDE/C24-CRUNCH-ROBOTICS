# Week 2 — Challenges

The exercises drill the happy path. **Challenges drill the failure path** — and in robotics the failure path is where you actually earn your keep. Each challenge takes 60–120 minutes and produces a portfolio-grade artifact (a documented before/after, a reproducible repro).

## Index

1. **[Challenge 1 — Induce and fix an `ExtrapolationException`](./challenge-01-induce-and-fix-extrapolation.md)** — deliberately trigger the single most common tf2 error by mismatching timestamps, then fix it with correct stamping and a buffer timeout. Document the before/after lookup behavior. (~90 min)

Challenges are optional for passing the week, but `ExtrapolationException` is the tf2 bug you will hit most in the rest of C24 — in Nav2, in MoveIt2, in your perception stack. Doing this challenge now means you diagnose that bug in five minutes for the next forty-six weeks instead of forty-five. It is the single highest-leverage hour in week 2.
