# Exercise 1 — Read an Allan Plot

**Goal:** Given an Allan-deviation log-log plot, identify the three noise regions by their slopes and read off the two numbers an estimator needs — the random walk `N` and the bias instability `B`. You will train the single most important interpretive skill of the week: turning a curve into the parameters that go straight into next week's EKF.

**Estimated time:** 45 minutes. Guided.

---

## Setup

No code this exercise — it's reading a plot. You'll generate the plot in Exercise 2; here we reason about a representative one so the *interpretation* is solid before you compute your own.

Consider this Allan-deviation curve for a MEMS gyro's z-axis (yaw rate), sampled at 100 Hz, log-log axes (τ in seconds on x, σ(τ) in rad/s on y). Sketch it from this description, or imagine it:

```
σ(τ)
(rad/s)
 1e-2 ┤\
      │ \                                      ← left: steep falling line
 1e-3 ┤  \___
      │      \____                             ← knee, flattening
 1e-4 ┤          \____           ____/         ← flat floor (minimum), then rising
      │               \_________/
 1e-5 ┤
      └────┬─────┬─────┬─────┬─────┬──── τ (s)
         0.01   0.1    1     10   100   1000
```

Three regimes, left to right:

- **Left, steeply falling** — slope ≈ **−1/2**.
- **Bottom, flat** — slope ≈ **0**, a clear minimum.
- **Right, rising** — slope ≈ **+1/2**.

---

## Step 1 — Identify the random walk (the −½ slope)

The left, falling part of the curve is **angle random walk (ARW)** — the gyro's white noise, which averages *down* as you integrate longer (hence the falling slope). On a log-log plot, white noise is a straight line of slope −½.

**Read `N` off it:** extend the −½ line to **τ = 1 s** and read the σ value there. Suppose the line passes through `σ = 1.2e-3 rad/s` at τ = 1 s. Then:

```
N (ARW) ≈ 1.2e-3 rad/√s
```

Convert to the conventional °/√h if you like: `1.2e-3 rad/√s × (180/π) × √3600 ≈ 4.1 °/√h`. Both are the same number; estimators usually want it in SI (rad/√s).

> **Why τ = 1 s?** The −½ line's value at τ = 1 s is, by the definition of the Allan variance, exactly the random-walk coefficient `N`. It's a convention that makes the read-off trivial: find the line, go to τ = 1, read y.

---

## Step 2 — Identify the bias instability (the flat floor)

The flat bottom of the curve is the **bias instability** — the lowest noise the sensor reaches, the floor past which averaging longer stops helping (because slow bias drift starts to dominate). Read the minimum σ value; suppose `σ_min = 8.0e-5 rad/s`. The bias instability `B` is that minimum scaled by the standard factor 0.664:

```
B ≈ σ_min / 0.664 = 8.0e-5 / 0.664 ≈ 1.2e-4 rad/s ≈ 0.0069 °/s
```

This number tells you two things: (1) the best your bias estimate can possibly be, and (2) how fast bias drifts, which sets the *process noise* on the bias state if you estimate it online in a filter.

---

## Step 3 — Identify the rate random walk (the +½ slope)

The right, rising part is **rate random walk (RRW)** — the slow random drift of the bias itself, which makes longer averaging *worse*, hence the +½ slope. You read its coefficient `K` at τ = 3 s on the +½ line. For a wheeled robot you'll rarely use `K` directly, but recognizing the rising slope tells you "averaging past the minimum hurts," which sets your bias-estimation window length: stop the window near the Allan minimum.

---

## Step 4 — Translate to estimator inputs

Now turn the two key numbers into what Week 10 wants:

- **Gyro noise density** for `robot_localization` / Madgwick: this is `N` (the ARW), in rad/√s → `1.2e-3`.
- **Angular-velocity covariance diagonal** for the `sensor_msgs/Imu` message: `σ²_ω = N² · f₀ = (1.2e-3)² × 100 ≈ 1.44e-4 (rad/s)²`.
- **Bias process noise** (if you estimate bias online): driven by `B` → `~1.2e-4 rad/s`.

Write these down. They are the numbers your covariance code (Lecture 2 §3.2) and next week's EKF config will consume.

---

## Acceptance criteria

You can mark this exercise done when, for the representative plot above, you can state:

- [ ] Which region is random walk (−½), bias instability (flat), and rate random walk (+½).
- [ ] The value of `N` read at τ = 1 s on the −½ line, with units.
- [ ] The value of `B` from the flat minimum (with the 0.664 factor).
- [ ] The angular-velocity covariance diagonal `σ²_ω = N²·f₀` you'd put in the IMU message.
- [ ] In one sentence: why averaging *longer* helps on the left of the plot but *hurts* on the right.

---

## Stretch

- Find your **actual IMU's datasheet** (BNO085, ICM-20948, etc.), locate its quoted "rate noise density" and "zero-rate offset," and predict where the Allan minimum should land. In Exercise 2 you'll compute the real plot and compare to the datasheet — they're often within a factor of 2, and the discrepancy is informative.
- Sketch how the plot would change for a *better* (tactical-grade) IMU vs. a *cheaper* (consumer) one: the whole curve shifts down, and the minimum moves right (you can average longer before bias drift dominates).

---

When this feels comfortable, move to [Exercise 2 — Compute the Allan variance](./exercise-02-allan-variance.py).
