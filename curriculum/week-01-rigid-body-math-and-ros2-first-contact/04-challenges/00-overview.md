# Week 1 — Challenges

The exercises drill the mechanics. **The challenge makes you prove the headline claim of the week** — that Euler angles fail where rotations themselves do not — with your own code, numerically, so you never again take "quaternions don't gimbal-lock" on faith.

## Index

1. **[Challenge 1 — Build a gimbal-lock demonstrator](./challenge-01-gimbal-lock-demonstrator.md)** — drive a rotation through pitch = ±90° and show, with numbers and a plot, that the ZYX Euler decomposition becomes singular while the quaternion sails through untouched. (~90 min)

Challenges are optional for passing the week, but this one is the single best inoculation against the most common orientation bug in robotics. The day your robot pitches to vertical and its Euler-based controller goes berserk, you'll have already seen exactly why — and built the fix. Do it.
