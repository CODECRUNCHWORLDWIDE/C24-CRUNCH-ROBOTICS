# Week 21 — Challenges

The exercises drill the LQR mechanics. **The challenge makes you the controls engineer who has to prove a new method beats the incumbent.** You have a working PID from last week. Your job is to show — with numbers, on a fair test — that an LQR designed from the model and the cost does better, *and* to defend the cost you chose, the way you'll defend it at the Phase 3 milestone in Week 24.

## Index

1. **[Challenge 1 — Beat the PID on a curve](./challenge-01-beat-pid-on-a-curve.md)** — design an LQR (with integral action and gain scheduling) that tracks a figure-8 reference with lower cross-track error than your tuned Week-20 PID, at comparable or less control effort, and write the comparison report that defends your `Q`/`R` and explains where (and why) the LQR wins and where it doesn't. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 milestone in Week 24, where you defend your controller stack — including the choice of *which* controller — to a reviewer. The skill — running a fair head-to-head between two controllers, reporting honest numbers, and articulating the design trade-off in the cost rather than hand-waving "LQR is better" — is exactly what separates an engineer who *picked* a controller from one who *cargo-culted* one. The honest answer to "is LQR better here?" is sometimes "no, and here's why" — and a reviewer respects that answer far more than a rigged demo.
