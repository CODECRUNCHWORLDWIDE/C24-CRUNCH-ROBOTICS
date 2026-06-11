# Lecture 1 — The Kalman Filter and EKF From Scratch: Bookkeeping With Covariance

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can derive the Kalman filter as recursive Bayesian estimation, write the predict and update steps and say what each does to the mean and covariance, explain how the EKF linearizes a nonlinear model with the Jacobian, and identify `Q`, `R`, the innovation, and the Kalman gain.

If you remember one sentence from this entire week, remember this one:

> **Sensor fusion is bookkeeping with covariance. The Kalman filter is a disciplined accountant: every quantity carries a stated uncertainty, prediction adds uncertainty, measurement removes it, and the only "intelligence" is weighting each new measurement against the running estimate in exact proportion to their covariances.**

There is no machine learning here, no training, no magic. The Kalman filter is the *provably optimal* estimator for a linear system with Gaussian noise, and it is optimal *because* it does the covariance bookkeeping correctly. Once you see it as accounting, `robot_localization` stops being a mysterious YAML file and becomes a tool whose every parameter you can reason about.

---

## 1. The problem: fuse noisy, partial, asynchronous sensors

Your robot has wheel encoders (good velocity, drifting position), a calibrated IMU (good angular velocity and orientation rate, drifting yaw), and — later — a LiDAR/GPS for absolute correction. None is complete; all are noisy; they arrive at different rates. You want a *single* best estimate of the robot's pose and velocity, updated continuously, that is better than any sensor alone and that *states its own uncertainty*.

That last clause is the key. We don't just want a number; we want a number *with error bars* that shrink when sensors agree and grow when they're silent. That is exactly what a Bayesian filter maintains: a **belief**, which is a probability distribution over the state. Under the assumption that everything is Gaussian, the belief is fully described by a **mean** `x̂` and a **covariance** `P`, and the recursion that updates them is the Kalman filter.

---

## 2. Recursive Bayesian estimation

The state at time `k` is `xₖ` (e.g. `[x, y, θ, v, ω]`). We never observe it directly; we observe measurements `zₖ`. The Bayes filter maintains the belief `bel(xₖ) = p(xₖ | z₁:ₖ)` — the distribution of the state given all measurements so far — by alternating two operations:

1. **Predict** (a.k.a. the motion update): push the belief forward through the motion model `p(xₖ | xₖ₋₁)`. This *spreads out* the belief, because the motion model is imperfect — you become *less* certain.
2. **Update** (a.k.a. the measurement update): fold in the new measurement via `p(zₖ | xₖ)` using Bayes' rule. This *sharpens* the belief — you become *more* certain.

The genius of the Kalman filter is that **when the motion model and measurement model are linear and all noise is Gaussian, both operations have closed forms**, and the belief stays Gaussian forever. No sampling, no integration — just matrix algebra. Let's write it.

---

## 3. The linear Kalman filter

Assume a linear motion model and a linear measurement model:

```
xₖ = F xₖ₋₁ + B uₖ + wₖ,     wₖ ~ N(0, Q)     (process noise)
zₖ = H xₖ + vₖ,              vₖ ~ N(0, R)     (measurement noise)
```

`F` is the state-transition matrix, `B u` an optional control input, `H` maps state to measurement, `Q` is the process-noise covariance, `R` the measurement-noise covariance. The filter carries `x̂` (the mean estimate) and `P` (its covariance).

### 3.1 The predict step

```
x̂⁻ = F x̂ + B u                  (project the mean forward through the motion model)
P⁻  = F P Fᵀ + Q                 (project the covariance forward, then ADD process noise)
```

Read the second line carefully — it's the heart of "prediction adds uncertainty." `F P Fᵀ` propagates the existing uncertainty through the dynamics; `+ Q` *injects new uncertainty* because the motion model isn't perfect. **`P⁻` is always larger than `P` was** (in the matrix sense). Predict, and you know less. That's correct: if you coast on the motion model with no measurements, your confidence should decay.

### 3.2 The update step

A measurement `z` arrives. The filter computes:

```
y = z − H x̂⁻                         (the INNOVATION: measurement minus prediction)
S = H P⁻ Hᵀ + R                       (the innovation covariance)
K = P⁻ Hᵀ S⁻¹                         (the KALMAN GAIN)
x̂ = x̂⁻ + K y                          (correct the mean toward the measurement)
P  = (I − K H) P⁻                     (SHRINK the covariance: information added)
```

Term by term:

- **The innovation `y`** is the "surprise" — how far the measurement is from what you predicted. If your prediction was perfect, `y = 0` and nothing changes.
- **The Kalman gain `K`** is the blend factor, and it is *entirely determined by the covariances*. Look at its structure: `K = P⁻ Hᵀ / (H P⁻ Hᵀ + R)`. When the measurement is very precise (`R` small), `K` is large and the filter moves the estimate most of the way to the measurement. When the measurement is noisy (`R` large), `K` is small and the filter mostly keeps its prediction. **The filter trusts whichever it has more confidence in** — and "confidence" is just inverse covariance.
- **The covariance update `P = (I − K H) P⁻`** *shrinks* `P` — measurement adds information, so uncertainty drops. Update, and you know more.

That's the entire filter: predict (mean forward, covariance up), update (mean toward measurement, covariance down), forever. The "fusion" of two sensors is nothing but two update steps with two different `H`/`R` pairs, each shrinking `P` toward whichever sensor is more trustworthy at that moment.

### 3.3 The 1-D intuition you'll code

Strip it to a scalar (Exercise 2): estimating a single value (say, position) from noisy measurements, with a constant-velocity-ish prediction. The update reduces to fusing two Gaussians — your prediction `N(x̂⁻, P⁻)` and your measurement `N(z, R)` — into a posterior whose mean is the *precision-weighted average*:

```
x̂ = (P⁻⁻¹ x̂⁻ + R⁻¹ z) / (P⁻⁻¹ + R⁻¹)        and       P = 1 / (P⁻⁻¹ + R⁻¹)
```

The posterior mean leans toward whichever input has smaller variance, and the posterior variance is *smaller than either input* — fusing two noisy estimates gives a less noisy one. That is the whole reason sensor fusion works, in one line. Watching `P` shrink on update and grow on predict in your own scalar code is the "aha" of the week.

---

## 4. The Extended Kalman Filter: when the world is nonlinear

The linear KF assumed `F` and `H` were matrices. But a robot's motion is *nonlinear*: a unicycle moving forward while turning has

```
xₖ = xₖ₋₁ + v·cos(θ)·Δt
yₖ = yₖ₋₁ + v·sin(θ)·Δt
θₖ = θₖ₋₁ + ω·Δt
```

Those `cos(θ)` and `sin(θ)` terms make the motion model nonlinear — there's no constant matrix `F` that captures it. The **Extended Kalman Filter** handles this by *linearizing the nonlinear model at the current estimate, every step*.

Write the nonlinear motion model as `xₖ = f(xₖ₋₁, uₖ)` and the measurement as `zₖ = h(xₖ)`. The EKF:

- Uses the *nonlinear* `f` and `h` to propagate the **mean** (no approximation there — you can evaluate `cos(θ)` exactly).
- Uses the **Jacobians** to propagate the **covariance**:

```
F = ∂f/∂x  evaluated at x̂        (the motion-model Jacobian)
H = ∂h/∂x  evaluated at x̂⁻        (the measurement Jacobian)
```

and then runs the *exact same* predict/update equations as §3, but with these locally-linear `F` and `H`. For the unicycle, the motion Jacobian is:

```
       ⎡ 1   0   −v·sin(θ)·Δt ⎤
F =    ⎢ 0   1    v·cos(θ)·Δt ⎥
       ⎣ 0   0         1      ⎦
```

— the partial derivatives of each next-state component with respect to each current-state component, evaluated at the current `θ`. You re-compute it every step because `θ` changes.

### 4.1 The honest caveat: the EKF lies about nonlinearity

The linearization is a *first-order Taylor approximation* around the current estimate. When the function is gently curved and the covariance is small, it's excellent. When the function is sharply curved or the uncertainty is large, the linearization is *wrong*, and the EKF's covariance becomes inconsistent — it reports more (or less) confidence than it deserves, and the estimate can diverge.

This is not a bug you can tune away; it's the EKF's fundamental limitation. It's exactly why Week 11 introduces the **Unscented Kalman Filter** ("the EKF lies about nonlinearity; the UKF lies less" — it propagates sample points through the *true* nonlinear function instead of linearizing) and **factor graphs** ("the factor graph stops lying" — it re-linearizes globally, iteratively). For a wheeled robot with small per-step motion and decent sensors, the EKF is more than good enough — which is why `robot_localization`'s default `ekf_node` is an EKF and why it's where we start. But know that the linearization is an approximation, and know where it breaks.

---

## 5. `Q` and `R`: where the numbers come from

The filter is only as good as its noise matrices. Two of them, two different sources:

### 5.1 `R` — measurement noise — comes from the sensor

`R` is *not* something you guess. It is the sensor's stated covariance — and you spent all of last week measuring it for the IMU. The IMU's `angular_velocity_covariance` *is* the `R` (for the angular-velocity part of an IMU update). The wheel odometry's `pose.covariance` and `twist.covariance` are the `R` for odom updates. **This is why Week 9's honest covariance mattered:** the EKF reads it directly as `R`. A wheel-odom message with a zero covariance is claiming infinite precision, and the EKF will overtrust it into a useless, jittery estimate. A senior habit: before fusing a sensor, `ros2 topic echo` its covariance field and make sure it's *honest*, not a row of zeros or a row of ones.

### 5.2 `Q` — process noise — is yours to tune

`Q` captures everything the motion model *doesn't* — wheel slip, unmodeled dynamics, the discretization error. There's no sensor to read it off; you tune it. The intuition:

- **`Q` too small** → the filter overtrusts its motion model, the predicted covariance stays small, and the filter *ignores* measurements that disagree (the estimate lags reality and can be confidently wrong).
- **`Q` too large** → the filter distrusts its own predictions, leans hard on every (noisy) measurement, and the estimate *jitters*.

Tuning `Q` is the main hands-on skill of this week's second half. The method is not superstition: drive a known trajectory, watch the output covariance and the drift, and adjust `Q` so the filter's *stated* uncertainty matches its *actual* error (a consistency check). `robot_localization` exposes `Q` as the `process_noise_covariance` — a 15×15 matrix you'll edit with a documented rationale.

---

## 6. A worked fusion: odom velocity + IMU yaw rate

Concretely, here's what the EKF does on your robot, in plain terms:

1. **Predict** (say at 30 Hz): take the last fused estimate, push it forward through the unicycle model using the last known velocity and yaw rate. The covariance grows by `Q`.
2. **Update with wheel odometry** when an `/odom` message arrives: the innovation is "measured velocity minus predicted velocity," weighted by the odom's `twist.covariance` (its `R`). Position covariance shrinks a little; velocity covariance shrinks a lot (odom is good at velocity).
3. **Update with the IMU** when an `/imu/data` message arrives: the innovation is "measured yaw rate minus predicted yaw rate" (and orientation, if you fuse it), weighted by the IMU's `angular_velocity_covariance` (its `R`, your Week 9 number). Yaw and yaw-rate covariance shrink.

The fused `/odometry/filtered` is better than either input because each update step *adds the information* that sensor has and *nothing else* — velocity from the wheels, heading rate from the gyro — with the covariances arbitrating any disagreement. That's the 4× drift improvement the week promises, and now you can explain it in covariance terms instead of hand-waving "the filter makes it better."

---

## 7. The fusion rules that fall out of the math

Two practical rules come straight from the covariance bookkeeping, and breaking them is how people make `robot_localization` *worse* than raw odometry:

- **Never fuse the same absolute quantity from two sources naively.** If both wheel odometry and the IMU claim an absolute yaw, and you fuse both as absolute measurements, you double-count and the filter becomes overconfident (its `P` shrinks faster than the information justifies). The fix: fuse *velocity* from odom and *orientation/angular-velocity* from the IMU — complementary quantities — or mark one source as `differential` so it contributes a *change*, not an absolute.
- **An absolute-pose update needs an absolute reference.** Wheel odometry's absolute `x, y` drift, so fusing them as absolute position just imports the drift. Fuse odom's *velocity* (which doesn't drift) and let an absolute source (AMCL, GPS — later weeks) provide absolute position via the `map→odom` EKF.

You'll see exactly these rules encoded in the `ekf_node` boolean `_config` matrices next lecture — they're not arbitrary; they're the covariance math made into YAML.

---

## 8. A fully worked 1-D step, with numbers

Abstract equations are slippery; let's nail one step down with actual numbers, in the scalar setting you'll code in Exercise 2. Estimate a 1-D position. The motion model is a random walk (`F = 1`), and we measure position directly (`H = 1`).

**Starting belief:** `x̂ = 2.0 m`, `P = 0.40 m²` (we're somewhat unsure).
**Noise:** process noise `Q = 0.01 m²`, measurement noise `R = 0.25 m²` (a fairly noisy sensor).
**Measurement arrives:** `z = 3.0 m`.

**Predict:**

```
x̂⁻ = F x̂ = 1 · 2.0 = 2.0
P⁻  = F P Fᵀ + Q = 0.40 + 0.01 = 0.41        (covariance grew: 0.40 → 0.41)
```

**Update:**

```
y = z − H x̂⁻ = 3.0 − 2.0 = 1.0               (innovation: the measurement surprised us by 1 m)
S = H P⁻ Hᵀ + R = 0.41 + 0.25 = 0.66          (innovation covariance)
K = P⁻ Hᵀ S⁻¹ = 0.41 / 0.66 = 0.621           (Kalman gain)
x̂ = x̂⁻ + K y = 2.0 + 0.621 · 1.0 = 2.62       (moved 62% of the way toward the measurement)
P  = (1 − K H) P⁻ = (1 − 0.621) · 0.41 = 0.155  (covariance shrank: 0.41 → 0.155)
```

Read the result. The gain `K = 0.62` says "I'm more confident in the measurement than in my prediction, so move most of the way toward it" — and indeed `R = 0.25` is smaller than `P⁻ = 0.41`. The estimate moved from 2.0 to 2.62 (toward the measured 3.0, but not all the way, because the measurement is still noisy). And the covariance dropped from 0.41 to 0.155 — the measurement *added information*.

Now imagine the measurement were *very* precise, `R = 0.01`. Then `K = 0.41/0.42 = 0.976` — the filter would jump almost entirely to the measurement (3.0), and `P` would collapse to ~0.01. And if the measurement were *garbage*, `R = 100`, then `K = 0.41/100.4 = 0.004` — the filter would barely move and keep its prediction. **The gain is the whole story, and the gain is just a ratio of covariances.** Internalize this single worked step and the 15-dimensional EKF in `robot_localization` is the same arithmetic with matrices.

---

## 9. Multi-rate, asynchronous fusion: how it actually runs on a robot

The textbook KF assumes one measurement per step. A real robot is messier and more interesting: wheel odometry arrives at, say, 50 Hz, the IMU at 100 Hz or 200 Hz, and a (later) global pose at 5 Hz — all on different clocks, all jittery. `robot_localization` handles this gracefully, and understanding how is what lets you debug it.

- **The predict step runs at a fixed `frequency`** (e.g. 30 Hz), independent of any sensor. Each tick, the filter projects the state forward by `Δt` and grows `P` by `Q`. This gives you a smooth, continuously-published estimate even between measurements.
- **Each measurement triggers its own update** when it arrives, using *that sensor's* `H` and `R`. The IMU update touches the orientation/angular-velocity states; the odom update touches the velocity states. They don't collide because each writes only the states its `_config` selects.
- **Ordering by timestamp matters.** Because measurements arrive out of order (a 100 Hz IMU sample stamped slightly before a 50 Hz odom sample may arrive after it), the filter buffers by the *header stamp* and applies them in time order. This is precisely why Week 9's "stamp at acquisition" discipline is load-bearing: a measurement stamped late is fused at the wrong point in the trajectory, and the smooth estimate develops a kink.

The mental model: **predict is a metronome; updates are events.** The metronome keeps the estimate flowing and uncertain-growing; each sensor event snaps a piece of the state back toward truth and shrinks that piece's uncertainty. A sensor that goes silent (LiDAR unplugged) simply stops sending its update events — the filter keeps predicting, `P` keeps growing, and the estimate degrades *gracefully* (and detectably, via the growing covariance) rather than freezing or crashing. That graceful degradation is a feature you'll exploit in the Week 46 chaos drill when a sensor is killed mid-task.

### 9.1 Why the filter never "double-integrates" the IMU

A subtle point that confuses newcomers: didn't Week 9 say integrating the IMU is hopeless (drift)? So why feed it to the EKF? Because the EKF does *not* dead-reckon the IMU into position. It fuses the IMU's *rates* (angular velocity, optionally linear acceleration) as **measurements that constrain the velocity/orientation states**, while the *position* states are anchored by wheel-odometry velocity and (later) absolute corrections. The IMU never drives position open-loop; it sharpens the heading and rate estimates, and the wheel velocity + absolute references keep position bounded. The filter uses each sensor only for what that sensor is *good at* — which is exactly the complementary-fusion rule of §7, enforced by the covariance bookkeeping.

---

## 10. The unicycle EKF, one predict step with numbers

Let's tie the EKF math to your actual robot. Take the planar state `x = [x, y, θ]`, with control `u = [v, ω]` (forward speed, yaw rate) from wheel odometry. The nonlinear motion model over `Δt`:

```
f(x, u) = [ x + v·cos(θ)·Δt,
            y + v·sin(θ)·Δt,
            θ + ω·Δt ]
```

Suppose `x̂ = [1.0, 0.5, 0.30 rad]`, `v = 0.5 m/s`, `ω = 0.2 rad/s`, `Δt = 0.1 s`.

**Propagate the mean through the *nonlinear* `f` (exactly — no approximation):**

```
cos(0.30) = 0.9553,  sin(0.30) = 0.2955
x̂⁻ = [ 1.0 + 0.5·0.9553·0.1,  0.5 + 0.5·0.2955·0.1,  0.30 + 0.2·0.1 ]
    = [ 1.0478,                0.5148,                0.32 ]
```

**Propagate the covariance through the *linearized* `F` (the Jacobian at `θ = 0.30`):**

```
       ⎡ 1   0   −v·sin(θ)·Δt ⎤     ⎡ 1   0   −0.5·0.2955·0.1 ⎤     ⎡ 1   0   −0.0148 ⎤
F =    ⎢ 0   1    v·cos(θ)·Δt ⎥  =  ⎢ 0   1    0.5·0.9553·0.1 ⎥  =  ⎢ 0   1    0.0478 ⎥
       ⎣ 0   0         1      ⎦     ⎣ 0   0         1         ⎦     ⎣ 0   0    1      ⎦
```

Then `P⁻ = F P Fᵀ + Q`. The off-diagonal `−0.0148` and `0.0478` terms are what couple the *heading* uncertainty into the *position* uncertainty — physically, "if I'm unsure about my heading, then after moving forward I'm unsure about where I ended up." That coupling is the entire reason heading error turns into position drift, and it's why the IMU (which sharpens `θ`) indirectly tightens position too. This is the EKF doing, automatically, the covariance bookkeeping you'd otherwise track by hand — and it's exactly what `robot_localization` computes internally for the planar sub-state when you run it on your diff-drive robot.

The takeaway: the mean rides the *true* nonlinear model (so the trajectory bends correctly), while the covariance rides the *Jacobian* (a local linear approximation, recomputed every step as `θ` changes). When `Δt` is small and turns are gentle, that approximation is excellent — which is why the EKF is the right default for a wheeled robot.

---

## 11. When the filter diverges, and how you'd know

A correctly-configured KF/EKF is *consistent*: its stated covariance `P` honestly reflects its actual error. When it isn't, the filter is either **overconfident** (P too small — it reports tight error bars while drifting badly, and stops listening to corrections) or **underconfident** (P too large — it jitters, chasing every noisy measurement). Both are config errors, and both are diagnosable:

- **Overconfident** usually means `Q` or an `R` is too small. The estimate looks smooth and certain, then drifts away from truth confidently. The tell: the actual error grows well outside the `±1σ` envelope that `P` predicts. The fix: increase the process noise (or the offending sensor's `R`) until the stated uncertainty matches reality.
- **Underconfident / jittery** means `Q` is too large or you're over-trusting a noisy sensor (its `R` too small). The estimate twitches with every measurement. The fix: lower `Q`, or give the noisy sensor an honest (larger) `R`.
- **Divergence** — the estimate runs away and never recovers — most often comes from the EKF linearization breaking (a sharp turn with large uncertainty), a grossly wrong `R` (a zero odom covariance), or double-counting an absolute quantity (§7). When the EKF genuinely can't keep up with the nonlinearity, that's the cue for the UKF or a factor graph (Week 11).

The rigorous consistency check — which you'll do in the challenge — is the **Normalized Estimation Error Squared (NEES)** intuition: over a trajectory, the actual error should be inside the filter's `±1σ` (more precisely `±2σ`) envelope roughly 95% of the time. A filter whose error sits *outside* its envelope is lying about its own confidence, and a robot that trusts a lying filter plans from a pose it shouldn't believe. "Is my filter consistent?" is a more senior question than "is my error small?", because a small error with an inconsistent covariance is luck, not engineering.

---

## 12. Two views that make the KF click

If the equations still feel like magic, here are two reframings that senior engineers carry around.

### 12.1 The KF is recursive weighted least squares

Forget the Bayesian story for a moment. Suppose you have two independent noisy measurements of the same quantity, `z₁` with variance `σ₁²` and `z₂` with variance `σ₂²`. The least-squares (maximum-likelihood) estimate that minimizes the squared error weighted by precision is:

```
x̂ = (z₁/σ₁² + z₂/σ₂²) / (1/σ₁² + 1/σ₂²)
```

— the *precision-weighted average*. That is *exactly* the Kalman update from §3.3, with the "prediction" playing the role of `z₁` and the "measurement" playing the role of `z₂`. The Kalman filter is nothing more than recursive weighted least squares, where at each step the previous estimate (with its covariance) is one "measurement" and the new sensor reading is another. Every time you see `K = P⁻/(P⁻ + R)`, read it as "weight each by its precision and renormalize." The optimality of the KF *is* the optimality of weighted least squares under Gaussian noise — a result you may already trust from statistics.

### 12.2 The complementary filter is a hand-tuned KF

There's an even simpler fusion you'll meet (and that `imu_filter_madgwick` from Week 9 is a cousin of): the **complementary filter**. To fuse a drifty-but-smooth source (integrated gyro) with a noisy-but-bounded source (accelerometer tilt), you take:

```
θ_fused = α · (θ_prev + gyro·Δt) + (1 − α) · θ_accel,    α ≈ 0.98
```

— mostly trust the gyro short-term, gently pull toward the accelerometer long-term. This is a fixed-gain version of the Kalman filter: `α` is a hand-chosen, *constant* Kalman gain instead of one computed from covariances each step. The complementary filter is cheaper and has no covariance bookkeeping, which is why it's popular on microcontrollers — but it can't adapt its trust when a sensor's reliability changes, and it gives you no uncertainty estimate. The KF/EKF *computes* the optimal `α` (the gain `K`) every step from the covariances, and hands you a covariance you can act on. When someone asks "why not just use a complementary filter?", the answer is: "for a constant-reliability, single-quantity fusion, sure — but the EKF adapts its gain and tells me its uncertainty, which I need for a 15-state robot pose." Knowing the complementary filter is the KF's fixed-gain ancestor makes both click.

---

## 13. Recap

You should now be able to:

- Frame fusion as recursive Bayesian estimation: a belief (mean + covariance) updated by predict and update steps.
- Write the linear KF predict (`x̂⁻ = Fx̂`, `P⁻ = FPFᵀ + Q`) and update (`K = P⁻HᵀS⁻¹`, `x̂ = x̂⁻ + Ky`, `P = (I−KH)P⁻`) and say what each does to the covariance.
- Explain the innovation, the Kalman gain as a covariance-determined blend, and why fusing two Gaussians yields a tighter one.
- Describe how the EKF linearizes nonlinear `f`/`h` via Jacobians, and the honest caveat that the linearization can lie.
- Say where `R` comes from (the sensor's covariance — your Week 9 numbers) and how to tune `Q`.
- State the two fusion rules (don't double-count absolutes; fuse complementary quantities) and tie them to the covariance math.
- Walk a full predict+update with numbers, derive the unicycle motion Jacobian, and reason about filter consistency/divergence.
- Recognize the KF as recursive weighted least squares and the complementary filter as its fixed-gain ancestor.

A closing thought to carry into the lab: the Kalman filter is the rare piece of robotics that is *provably* optimal — not a heuristic, not a model you train, but the mathematically best estimator for its assumptions. That optimality is a gift and a responsibility. The gift: when your covariances are honest, the filter cannot be beaten. The responsibility: the filter trusts you completely, so a dishonest covariance (a zero on `/odom`, a guessed IMU number) is a lie it will faithfully propagate into a confident, wrong estimate. Everything you measured in Week 9 — the Allan noise density, the honest covariance — exists so that this week's filter can be the optimal estimator it's designed to be. Garbage covariance in, garbage estimate out, with mathematical certainty. That's why "bookkeeping with covariance" is the whole game.

One more orientation for the week ahead. You will *not* implement the EKF on your robot — `robot_localization` does that, correctly and battle-tested, and re-implementing it would be a mistake. But you implemented the *scalar* version in Exercise 2, by hand, and you worked the matrix steps by hand in this lecture, *so that the YAML you write next is not a magic incantation*. When you set a process-noise value or a boolean in `imu0_config`, you'll know exactly which term of the predict/update it touches and what it does to the covariance. That is the difference between configuring `robot_localization` and *understanding* it — and it's the difference a reviewer or interviewer probes the instant they point at your config and ask "why?". The derivation you just read is the answer key to every one of those questions.

The bridge to remember: **`R` is the sensor's honesty (you read it), `Q` is your humility about the motion model (you tune it), and the gain `K` arbitrates between them automatically.** Hold those three sentences and the entire next lecture — every parameter in the `ekf_node` YAML — reduces to "which of `R`, `Q`, or the boolean field-selection am I setting, and what does the covariance math say it does?" There is no magic; there is only the bookkeeping, configured.

A final caution about the filter's assumptions, so you know its edges. The KF is optimal *under linear-Gaussian assumptions*; the EKF extends it to *mildly* nonlinear systems by linearizing. Three things break it, and recognizing them is what tells you when to escalate to Week 11's tools:

- **Strong nonlinearity** (sharp turns, large per-step motion) makes the linearization inaccurate; the covariance becomes inconsistent. → Unscented KF or factor graph.
- **Non-Gaussian, multimodal beliefs** (the robot could be in one of two corridors) cannot be represented by a single mean+covariance at all. → Particle filter / AMCL.
- **A bad initial estimate** can put the linearization point so far from truth that the EKF never recovers (divergence). → Good initialization, or a global relocalizer.

For a wheeled robot fusing odom + IMU with small per-step motion and unimodal uncertainty, none of these bite, which is exactly why the EKF is the right tool this week. But know the edges — "the EKF lies about nonlinearity, the UKF lies less, the factor graph stops lying" (Week 11) is the map of what to reach for when the EKF's assumptions fail. Choosing the right estimator for the structure of the problem is the senior skill; the EKF is the workhorse you start from.

The mental model to leave with: a filter is a *claim about the world expressed as a probability distribution*, updated by evidence. The KF/EKF makes the cheapest useful claim — a single Gaussian — and updates it with linear-algebra efficiency. When the world is too weird for one Gaussian (multimodal, sharply nonlinear), you pay more compute for a richer claim (particles, sigma points, factors). Robotics estimation is, at bottom, the art of choosing the cheapest probabilistic claim that still captures the situation — and then doing the covariance bookkeeping honestly. You've now got the cheapest one in hand; the rest of Phase 2 adds the richer ones for when it isn't enough.

Next: how all of this is configured in `robot_localization`'s `ekf_node` — the inputs, the boolean matrices, the frames, and the tuning. Continue to [Lecture 2 — robot_localization in Practice](./02-robot-localization-in-practice.md).

---

## References

- *Probabilistic Robotics* (Thrun/Burgard/Fox), Ch. 3 — Bayes filter, KF, EKF derivations.
- *Kalman and Bayesian Filters in Python* (Labbe) — free, interactive: <https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python>
- *How a Kalman filter works, in pictures* (Bzarg): <https://www.bzarg.com/p/how-a-kalman-filter-works-in-pictures/>
- *Cyrill Stachniss — KF & EKF lecture*: <https://www.ipb.uni-bonn.de/sensors-state-estimation/>
- *robot_localization — preparing sensor data* (where R/frames come from): <https://docs.ros.org/en/melodic/api/robot_localization/html/preparing_sensor_data.html>
- *`nav_msgs/Odometry`* — pose/twist covariance the EKF reads as R: <https://docs.ros.org/en/jazzy/p/nav_msgs/msg/Odometry.html>

---

*Practice prompt before the exercises:* given a scalar KF with `P⁻ = 0.5`, `R = 0.1`, and a measurement innovation `y = 0.4`, compute the gain `K`, the corrected mean change `K·y`, and the updated `P`. Then redo it with `R = 5.0` and explain why the estimate barely moved. If those two cases feel obvious, you understand the Kalman gain.
