# Week 20 — Challenges

The exercises drill the mechanics. **The challenge makes you the controls engineer with a spec sheet and a deadline.** You're handed a single robot and three different step targets, and you must tune *one* controller that meets a written specification on all three — then defend why your gains are where they are, the way you'll defend them at the Phase 3 milestone in Week 24.

## Index

1. **[Challenge 1 — Tune one controller to three step responses](./challenge-01-tune-three-step-responses.md)** — tune a single yaw PID + feedforward so that 45°, 90°, and 180° step commands all land inside a rise/overshoot/settling/steady-state spec, then write the tuning log that justifies every gain and explains the anti-windup behavior visible on the 180° step. (~90 min)

Challenges are optional for passing the week, but this one is the single best preparation for the Phase 3 milestone in Week 24, where you defend your controller stack to a reviewer. Do it. The skill — making *one* set of gains work across a range of operating conditions, and explaining the trade-offs instead of hand-waving — is exactly what separates someone who "got the demo to work once" from an engineer who can ship a controller that holds up across the whole envelope. A controller that's only tuned for one setpoint is a controller that will surprise you in the field.
