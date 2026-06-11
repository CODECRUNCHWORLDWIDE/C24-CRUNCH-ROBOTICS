# Challenge 1 — Build a Gimbal-Lock Demonstrator

**Time estimate:** ~90 minutes.

## Problem statement

Everyone *says* "Euler angles gimbal-lock and quaternions don't." This challenge makes you **prove it numerically**, on your own, so the claim becomes something you've measured rather than something you've memorized. You will construct a sequence of rotations that passes through pitch = 90°, decompose each into ZYX Euler angles, and show two things:

1. The Euler decomposition becomes **singular** near pitch = ±90°: roll and yaw become wildly, discontinuously sensitive to tiny perturbations of the rotation, because a degree of freedom is lost.
2. The **quaternion** (and the rotation matrix) representation passes through pitch = 90° with no discontinuity and no loss of precision whatsoever.

This is the experiment that converts "I was told quaternions are better" into "I watched Euler angles blow up and quaternions stay smooth on my own screen."

## Background you need

The ZYX intrinsic decomposition of a rotation matrix `R` (yaw about z, then pitch about y', then roll about x'') recovers:

```
pitch =  asin(-R[2,0])
roll  =  atan2( R[2,1], R[2,2] )
yaw   =  atan2( R[1,0], R[0,0] )
```

The `atan2` arguments for roll and yaw both collapse toward zero as `pitch → ±90°` (where `R[2,0] → ∓1`), so roll and yaw are computed as `atan2(≈0, ≈0)` — numerically meaningless, and they trade off against each other freely. That trade-off *is* the lost degree of freedom.

## Your task

Write a script `gimbal_lock_demo.py` that does the following.

### Part A — The smooth path in matrix/quaternion space

Construct a one-parameter family of rotations that sweeps pitch from `−100°` to `+100°` while holding a *fixed combined yaw+roll motion* (so the lost DOF actually matters). For example, build each rotation as `R(t) = Rz(yaw(t)) · Ry(pitch(t)) · Rx(roll(t))` where `pitch(t)` ramps through 90° and `yaw(t) = roll(t)` ramp together. Store each as a quaternion (via your `crunch_rotations` library or scipy) and as a matrix.

Show that consecutive quaternions are **close** (small angular distance between successive samples) all the way through pitch = 90° — i.e. the *actual rotation* moves smoothly. Quantify "close" as the geodesic angle `2·acos(|q_t · q_{t+1}|)` and plot it versus `t`. It should be small and continuous everywhere.

### Part B — The blow-up in Euler space

For the same sweep, decompose each `R(t)` to ZYX Euler with the formulas above. Plot `roll(t)`, `pitch(t)`, `yaw(t)`. You will see:

- `pitch(t)` ramps smoothly (it's the one that's well-conditioned).
- `roll(t)` and `yaw(t)` **jump or swing wildly** as the sweep crosses pitch = 90°, even though the underlying rotation barely moved between samples. That discontinuity is gimbal lock, on your screen.

### Part C — The sensitivity experiment (the clincher)

Take a single rotation at exactly pitch = 90° (or 89.999°). Perturb the *matrix* by a tiny amount (add `1e-6 · random` and re-orthonormalize, or perturb the axis-angle by `1e-6`). Re-decompose to Euler. Show that a `1e-6` perturbation of the rotation causes a **degrees-scale** change in roll and yaw, while the same perturbation causes only a `~1e-6` change in the quaternion. Print the amplification factor (output Euler change / input perturbation) — it should be enormous near the singularity and near `1` for the quaternion.

## Acceptance criteria

- [ ] A script `gimbal_lock_demo.py` that runs to completion and produces (or saves) the three plots from Parts A, B, C — or, if you're headless, prints the numeric series and the sensitivity amplification factor.
- [ ] A short `gimbal-lock-findings.md` (≈300–400 words) that states, with numbers from your run:
  - The maximum quaternion geodesic step through the sweep (small, continuous).
  - The maximum Euler roll/yaw jump through the sweep (large, near pitch 90°).
  - The sensitivity amplification factor near pitch 90° for Euler vs. for the quaternion.
- [ ] You correctly explain *why*: the ZYX decomposition's roll and yaw are `atan2(≈0, ≈0)` at pitch = 90°, the lost DOF, while the quaternion has no singularity.
- [ ] Committed to your Week 1 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

A common mistake is to sweep pitch through 90° but hold yaw and roll at **zero** — then the Euler angles *look* fine because there's no combined motion for the lost DOF to corrupt. The singularity only bites when there's a yaw+roll motion that the decomposition *must* split but *can't*. Make `yaw(t)` and `roll(t)` actually move together; that's what exposes the lock. If your Part B plots look smooth, this is why.

## Stretch

- Repeat with the **XYZ** Euler convention instead of ZYX and show the singularity moves to a different angle (it's a property of *every* three-angle parameterization, not of ZYX specifically — Euler's theorem guarantees no three-number chart on SO(3) is globally singularity-free).
- Animate the demonstrator as a live rviz2 `PoseStamped` (reuse Exercise 3): drive the pose through pitch = 90° and watch rviz2 render the *quaternion* path smoothly even as your simultaneously-printed Euler readout goes haywire. A vivid demo for the Week 8 review.
- Implement a tiny "Euler PD controller" on yaw and show it commands a nonsensical correction at pitch = 90° (because the yaw error is undefined there), then show the quaternion-error controller behaves. This is the real-world consequence, made concrete.

## Why this matters

In Phase 2 you build attitude estimators (Week 9) and in Phase 3 you build controllers (Weeks 20–22). Both *store state*. The engineer who stores attitude as Euler angles ships a robot that misbehaves the first time it points straight up — a forklift mast, a camera gimbal, an arm reaching overhead. The engineer who did this challenge stores quaternions, converts to Euler only for the operator's display, and never gets that 3 a.m. page. This 90 minutes is cheap insurance against a whole class of bug.
