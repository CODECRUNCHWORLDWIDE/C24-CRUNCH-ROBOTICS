# Week 24 — Challenges

The exercises build the pieces. **The challenge makes you the safety engineer who has to prove a number.** You're handed a composed, moving robot and a 200 ms budget, and you have to demonstrate — with measurement, not assertion — that your fail-safe meets it, mid-motion, repeatably.

## Index

1. **[Challenge 1 — Stop both halves under 200 ms, measured](challenge-01-estop-under-200ms.md)** — drive the composed base+arm robot, latch the E-stop mid-motion, and prove that *both* the Nav2 base action and the MoveIt2 arm trajectory stop within 200 ms. Ten trials, a reported distribution, and the abort proven under load. (~2 hours)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 milestone — where you defend your controller stack and your first hazard log to a reviewer — and for the capstone's safety case at Week 41 and the live chaos drills at Week 46. The skill it builds — turning "it stops" into "p95 = 58 ms over 10 trials, here is the script" — is exactly what separates an engineer who *claims* a robot is safe from one who can *show* it.
