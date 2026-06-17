# Lecture 1 — IMU Error Models and Allan Variance: Reading a Random Number Generator

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can write the gyroscope and accelerometer measurement models, name the physical origin of every error term, compute an Allan-variance plot from a stationary log, and read the random walk, bias instability, and rate random walk straight off it.

If you remember one sentence from this entire week, remember this one:

> **An uncalibrated IMU is a random number generator with branding. Calibration is the act of replacing "I have no idea what this sensor is telling me" with a measurement model whose error terms you have characterized and whose remaining uncertainty you can state honestly.**

The IMU is the cheapest, fastest, most-always-available sensor on a robot — and the most dangerous to trust naively, because its errors *integrate*. A camera that's 1% wrong gives you a 1%-wrong image. A gyroscope that's 0.5°/s biased gives you, after one minute of integration, *thirty degrees* of phantom rotation. The error doesn't stay small; it ramps. This lecture teaches you to characterize that error before it eats your state estimate.

---

## 1. What an IMU actually measures

A 6-DOF IMU contains two MEMS sensors, each a tiny vibrating or capacitive structure on silicon:

- A **3-axis gyroscope** measures **angular rate** `ω` (rad/s) about each body axis. It does *not* measure orientation — you get orientation by integrating rate over time, which is where drift enters.
- A **3-axis accelerometer** measures **specific force** `f` (m/s²) — the difference between true acceleration and gravity, in the body frame. At rest it reads `+g` upward (≈ 9.81 m/s² along whichever axis points up), because the table is pushing the chip up against gravity. This is the famous "an accelerometer at rest reads `+1g`, not zero" fact; internalize it now or you'll fight a sign for an hour.

A 9-DOF IMU adds a magnetometer (heading reference), but magnetometers are so easily corrupted by the robot's own motors and ferrous structure that many robotics stacks ignore them. We focus on the 6-DOF gyro+accel this week.

The crucial property: **the gyro and accel both give you *rates and forces*, not *poses*.** Orientation and position are integrals of what the IMU measures, and integration is exactly where small errors become large ones.

---

## 2. The measurement model

Here is the model that turns "random number generator" into "characterized sensor." For the gyroscope, the measured angular rate relates to the true rate by:

```
ω_meas = (I + S_g) · ω_true  +  M_g · ω_true  +  b_g(t)  +  n_g
```

Term by term:

- **`(I + S_g)·ω_true`** — the true rate, corrupted by a **scale-factor** error `S_g` (a diagonal gain error; a sensor reading 1% high has `S_g ≈ 0.01·I`).
- **`M_g·ω_true`** — **misalignment**: the off-diagonal cross-axis coupling, because the three MEMS axes aren't perfectly orthogonal or perfectly aligned to the body frame. Often `S_g` and `M_g` are folded into one 3×3 matrix.
- **`b_g(t)`** — the **bias**, a slowly time-varying offset. This is the dominant integrable error. Split it into a constant part (the zero-rate offset you measure at rest) and a slow random walk `b_g(t)` that drifts with temperature and time.
- **`n_g`** — **white noise**, zero-mean, uncorrelated sample to sample. The high-frequency jitter you see when you `echo` a stationary IMU.

The accelerometer model is identical in form:

```
a_meas = (I + S_a) · (a_true − g_body)  +  M_a · (...)  +  b_a(t)  +  n_a
```

with `g_body` the gravity vector rotated into the body frame. The same four error families: scale, misalignment, bias, noise.

### Which error dominates, and when

- For a **stationary or slow** robot, **bias** dominates the integrated error. A constant bias becomes a linear ramp in orientation (gyro) or a quadratic ramp in position (accel, double-integrated). This is why bias subtraction is the single highest-leverage calibration step and the focus of this week's lab.
- **Scale factor and misalignment** matter when the robot moves *fast* — they multiply the true signal, so at rest they contribute nothing (true rate is ≈ 0). You estimate these with a *dynamic* or *six-position* calibration, not a stationary log.
- **White noise** is irreducible per-sample, but it *averages down* — that's the whole point of the Allan plot, and the reason a filter can do better than any single sample.

---

## 3. Why integration is the enemy

Let's make the drift concrete, because the numbers are shocking the first time.

**Gyro → orientation.** A gyro bias `b_g` integrated over time `t` gives a phantom angle `θ_drift = b_g · t`. A cheap MEMS gyro has a bias on the order of `0.5°/s` *after warm-up*. Over one minute:

```
θ_drift = 0.5 °/s × 60 s = 30°
```

Thirty degrees of yaw error per minute, from bias alone, before you even consider noise. That is why an IMU cannot navigate by itself — and why Week 10 fuses it with wheel odometry.

**Accel → position.** Acceleration integrates *twice* to position. A constant accel bias `b_a` gives a position error:

```
p_drift = ½ · b_a · t²
```

The `t²` is brutal. A tiny `0.05 m/s²` bias (≈ 5 milli-g) gives, after just 10 seconds:

```
p_drift = ½ × 0.05 × 10² = 2.5 m
```

2.5 meters of phantom position in ten seconds. **This is why pure-inertial position dead-reckoning is hopeless** for ground robots, and why nobody integrates accelerometers to get position on a wheeled robot — you use wheel odometry for position and the IMU for orientation and as a high-rate motion prior.

### The one thing gravity gives you for free

There is a silver lining. The accelerometer, at rest, *sees gravity* — a constant `9.81 m/s²` vector pointing down. That gives you an absolute reference for **roll and pitch**: if the chip is tilted, the gravity vector tilts in the body frame, and you can read off the tilt. Roll and pitch are therefore **bounded** — they don't drift, because gravity continuously corrects them (this is what a complementary or Madgwick filter exploits).

**Yaw has no such reference.** Rotating about the vertical axis doesn't change where gravity points in the body frame, so the accelerometer is blind to yaw. Without a magnetometer or an external heading source, **yaw drifts unboundedly** while roll and pitch stay bounded. This asymmetry — bounded roll/pitch, unbounded yaw — is the single most important practical fact about IMU orientation estimation. Remember it.

---

## 4. Allan variance: separating the noise types

You now know the error *families*. Allan variance is the tool that *measures* them from data — specifically, it separates white noise from bias drift by looking at how the signal's variance behaves as you average over longer and longer windows.

### 4.1 The intuition

Take a long stationary gyro log. Average it over windows of length τ. For a *purely white-noise* signal, averaging over a longer window reduces the variance — the noise averages out, so the Allan deviation *falls* as τ grows (slope −½ on a log-log plot). But the bias *random walk* does the opposite: over longer windows the bias has drifted more, so the variance *grows* (slope +½). Somewhere in between is a **minimum** — the **bias instability**, the best you can ever do by averaging. Past that point, averaging longer *hurts* because bias drift dominates.

That's the whole idea: **different noise sources have different signatures versus averaging time**, and the Allan plot pulls them apart by their slopes.

### 4.2 The computation

The Allan variance at averaging time τ is, for a signal sampled at rate `f₀` (period `τ₀ = 1/f₀`):

1. Group the data into bins of `m` samples each, where `τ = m·τ₀`.
2. Compute the average of each bin: `ȳₖ(τ)`.
3. The Allan variance is the mean-squared difference of *consecutive* bin averages:

```
σ²(τ) = ⟨ ( ȳₖ₊₁(τ) − ȳₖ(τ) )² ⟩ / 2
```

The **Allan deviation** is `σ(τ) = √σ²(τ)`. You sweep `m` (hence `τ`) over many log-spaced values and plot `σ(τ)` vs. `τ` on log-log axes. The "overlapping" Allan variance (which the exercise computes) reuses overlapping bins for better statistics at large τ — same idea, more samples.

A clean NumPy core for the overlapping Allan deviation:

```python
import numpy as np

def allan_deviation(data: np.ndarray, fs: float, taus=None):
    """Overlapping Allan deviation of a 1-D rate signal.

    data : raw samples (e.g. one gyro axis in rad/s), stationary.
    fs   : sample rate in Hz.
    returns (taus, adev).
    """
    n = len(data)
    tau0 = 1.0 / fs
    # Integrate the rate to get angle (theta): Allan variance is defined on the
    # integrated quantity for rate sensors.
    theta = np.cumsum(data) * tau0

    max_m = (n - 1) // 2
    if taus is None:
        ms = np.unique(np.floor(np.logspace(0, np.log10(max_m), 100)).astype(int))
    else:
        ms = np.unique((np.asarray(taus) / tau0).astype(int))
    ms = ms[(ms >= 1) & (ms <= max_m)]

    adev = np.empty(len(ms))
    out_taus = ms * tau0
    for i, m in enumerate(ms):
        # Overlapping estimator on the integrated angle.
        diff = theta[2 * m:] - 2 * theta[m:-m] + theta[:-2 * m]
        sigma2 = np.sum(diff ** 2) / (2 * m ** 2 * (n - 2 * m))
        adev[i] = np.sqrt(sigma2)
    return out_taus, adev
```

Note we **integrate the rate to angle** (`cumsum`) first — Allan variance for a *rate* sensor is conventionally computed on the integrated quantity, which is why the second-difference of `theta` appears. (For an accelerometer you'd integrate specific force to velocity.) Get this wrong and your slopes come out shifted; the exercise has the reference output to check against.

### 4.3 Reading the plot

Once you have `σ(τ)` vs `τ` on log-log axes, here is the decoder ring:

| Feature on the plot | Slope | Noise type | What you read off |
|---|---|---|---|
| Left side, falling | **−½** | **Angle/Velocity Random Walk** (white noise) | `N` = the value of `σ` at **τ = 1 s** (the −½ line extrapolated to τ = 1). Units: rad/√s (gyro). |
| Bottom, flat | **0** | **Bias Instability** | `B` ≈ `σ_min / 0.664` (the flat minimum, scaled by the standard 0.664 factor). |
| Right side, rising | **+½** | **Rate Random Walk** (bias drift) | `K` = the value of the +½ line extrapolated to **τ = 3 s**. |

The two numbers you actually need for an estimator are:

- **`N` — the random walk / noise density.** This becomes the IMU's per-axis noise input to `robot_localization` and Madgwick filters. Read it as `σ` at τ = 1 s on the −½ slope. (Continuous-time noise density is `N`; the discrete per-sample noise is `N·√f₀`.)
- **`B` — the bias instability.** The floor of the plot tells you how good your bias estimate can get and how fast bias drifts — it sets the *process noise* on the bias state in a filter that estimates bias online.

> **The practical payoff:** the Allan plot turns "the datasheet says some number I don't trust" into "I measured *my* sensor's noise density and bias instability from *my* 30-minute log." Those measured numbers go straight into next week's EKF. A senior estimation engineer never ships a filter tuned on datasheet typicals when they could measure the actual unit.

---

## 5. Static vs. dynamic calibration

Not every error can be measured at rest. Know which is which.

**Static (at rest) — what you can do with a stationary log:**

- **Bias.** Average a long stationary window; the mean of each axis *is* the bias (the true rate is zero, so whatever it reads is offset + noise, and the noise averages out). For the accel, subtract the known gravity vector first.
- **Noise characterization.** The Allan plot, as above. Needs only stationary data.

**Dynamic (requires motion) — what a stationary log *cannot* give you:**

- **Scale factor.** You only see a gain error when the true signal is non-zero. Rotate the IMU through a *known* angle (e.g. exactly 360° on a turntable) and compare the integrated gyro angle to the truth; the ratio is `1 + scale`.
- **Misalignment.** Cross-axis coupling shows up only under rotation/acceleration along one axis producing a reading on another.
- **The six-position test.** Place the accel flat, inverted, and on each of its four sides; each orientation gives a known gravity projection, and the six equations solve for the full 3×3 scale+misalignment matrix plus the 3-vector bias. This is the standard accel calibration and a stretch goal this week.

For a wheeled robot whose IMU mostly experiences modest rates, **bias is 90% of the win**, which is why this week's required lab is bias subtraction and the dynamic calibrations are stretch.

---

## 6. A worked numeric example

Suppose your 30-minute log of the z-axis gyro (yaw rate), sampled at 100 Hz, gives:

- A stationary mean of `+0.0087 rad/s` → that's your **bias** `b_gz ≈ 0.50 °/s`.
- An Allan plot whose −½ line passes through `σ = 0.0012 rad/√s` at τ = 1 s → **`N` (ARW) ≈ 0.0012 rad/√s ≈ 0.07 °/√s`**.
- A flat minimum at `σ_min = 8.0e-5 rad/s` → **bias instability `B ≈ 8.0e-5 / 0.664 ≈ 1.2e-4 rad/s ≈ 0.0069 °/s`**.

Now you can predict the drift: with the raw signal, the `0.50°/s` bias gives `30°/min` of yaw drift (§3). After subtracting the measured bias, the *residual* drift is governed by the bias instability (`~0.007°/s`) and the random walk — roughly **`0.4°` over the same minute**, a ~70× improvement. That predicted ratio is what you'll *measure* in the challenge, and it's why the lab's "drift dropped by a factor" promise is achievable, not aspirational.

---

## 6b. The six-position accelerometer calibration, worked

The accelerometer's full calibration — scale, misalignment, and bias — is solvable from six static orientations, and the math is worth seeing because it's the standard recipe and a stretch goal this week. The model is:

```
a_meas = T · a_true + b_a            where  a_true = −g  (specific force at rest is −gravity)
```

`T` is the 3×3 combined scale+misalignment matrix and `b_a` the bias 3-vector — twelve unknowns total (9 + 3). At rest, `a_true` has magnitude `g` and points opposite gravity. Place the IMU in six precise orientations (z-up, z-down, x-up, x-down, y-up, y-down). In each, the true specific force is a known vector of magnitude `g` along one axis, e.g.:

```
z-up:    a_true = [0, 0, +g]        z-down:  a_true = [0, 0, −g]
x-up:    a_true = [+g, 0, 0]        x-down:  a_true = [−g, 0, 0]
y-up:    a_true = [0, +g, 0]        y-down:  a_true = [0, −g, 0]
```

Each orientation gives three scalar equations (`a_meas = T·a_true + b_a`), so six orientations give eighteen equations for twelve unknowns — an over-determined least-squares problem you solve with `numpy.linalg.lstsq`. The cleanest formulation stacks the six measured 3-vectors and the six known `a_true` vectors and solves for `[T | b_a]` in one shot. Once you have `T` and `b_a`, the corrected reading is `a_corrected = T⁻¹ (a_meas − b_a)`.

Two practical notes. First, the *orientations must be precise* — a few degrees of tilt on your "flat" surface injects error into `T`, so use a machinist's square or a known-flat reference. Second, you can do a *bias-only* version with just two opposing orientations per axis (z-up and z-down average out gravity, leaving the bias), which is the quick calibration; the full six-position solve adds scale and misalignment. For a wheeled robot, bias-only is usually enough (§5), which is why the full solve is stretch — but every estimation engineer should have done it once to understand what a "calibrated accelerometer" actually means.

---

## 6c. Why the gyro and accel calibrations are asymmetric

A subtlety that catches people: you calibrate gyro *bias* trivially (stationary mean) but gyro *scale* needs a turntable, while accel *bias and scale together* fall out of the six-position static test. Why the asymmetry?

Because **gravity is a free, known, constant reference for the accelerometer but there is no equivalent for the gyroscope.** At rest, the accelerometer sees a `g`-magnitude vector of known direction (down), so static orientations alone constrain both its scale and bias — gravity *is* the known input. The gyroscope at rest sees *zero* true rate, so a stationary log constrains only its bias (the offset on a zero input); to see a scale error you must apply a *known non-zero rate*, which means motion (a turntable through a known angle). This is the same reason roll/pitch are observable at rest (gravity) but yaw is not (§3): the accelerometer has a free reference, the gyroscope doesn't. Once you see it as "gravity is a free calibration signal for the accel only," the whole static-vs-dynamic split stops being a list to memorize and becomes a single idea.

---

## 6d. Recording a clean log: the procedure that makes or breaks everything

The Allan analysis and the bias estimate are only as good as the stationary log they're computed from. A sloppy recording produces confident, precise, *wrong* numbers — the worst kind. The procedure:

- **Duration.** At least 30 minutes, ideally a few hours for the bias-instability floor to be well-resolved. The longest τ you can analyze is roughly *half* the log length, and you want the Allan minimum (which can sit at τ of tens to hundreds of seconds for a MEMS gyro) comfortably inside the data. A 2-minute log can't reveal a bias instability at τ = 100 s.
- **Truly stationary.** Solid surface, nothing touching the IMU, no fans, no foot traffic, no HVAC vibration coupling through a bench. A surprising amount of "sensor noise" is actually building vibration. If you can, record on the floor on foam, not on a desk.
- **Thermal soak.** The bias drifts as the chip warms from cold. For the *cleanest* Allan plot, let the IMU run for 10–20 minutes before you start recording so it's thermally settled. For studying *bias drift itself*, deliberately record from cold and watch the bias ramp (a homework stretch).
- **Constant sample rate.** Allan variance assumes uniform sampling. If your IMU's rate jitters or you drop samples (a `BEST_EFFORT` topic on a loaded machine — Week 5!), the τ axis is wrong. Confirm the rate with `ros2 topic hz` and record with a QoS that doesn't drop. Check `count ≈ rate × duration` afterward.

Get these right and your `N` and `B` are trustworthy numbers you can stake a filter on. Get them wrong and you'll spend Week 10 wondering why your honestly-derived covariance produces a bad EKF — when the real problem was a vibrating bench in Week 9.

---

## 6e. Reading a *real* Allan plot (it's never as clean as the textbook)

The textbook plot has three pristine straight segments. A real plot from your sensor will be lumpier, and recognizing the deviations is part of the skill:

- **Periodic bumps** — a hump riding on the curve at a particular τ often means a *periodic disturbance* at that frequency: a cooling fan, a switching power supply, the building's 50/60 Hz mains coupling in. The Allan variance sees periodic signals as a bump near the period. If you see one, hunt the source before trusting the floor.
- **A floor that never flattens** — if the −½ slope just keeps falling with no clear minimum, your log is too short to reveal the bias instability; record longer.
- **A rising +½ tail that dominates early** — a sensor with strong temperature sensitivity recorded during warm-up shows rate-random-walk encroaching at smaller τ than a thermally-soaked one. This is the thermal-soak point above, visible in the plot.
- **Per-axis differences** — the three axes rarely have identical `N` and `B`; manufacturing variation is real. Report all three, and use per-axis covariance in the EKF rather than assuming one number for all.

The practical rule: extract `N` from the cleanest part of the −½ slope (usually τ from ~0.1 s to a few seconds), and read `B` from the lowest clear point of the floor. Don't fit a line through a region corrupted by a periodic bump. When in doubt, cross-check against `allan_variance_ros` (the reference tool) and the datasheet — agreement within a factor of ~2 is normal and reassuring; a 10× gap means something's wrong with the recording or the computation.

---

## 6f. From noise density to discrete covariance: the units that trip everyone

The single most error-prone step in the whole week is converting the Allan `N` (a *continuous-time* noise density) into the *discrete-time* variance the IMU message and the EKF actually want. Get the units wrong and your filter is mistuned by orders of magnitude while every individual number looks plausible. Here is the relationship, stated carefully.

The gyro angle random walk `N` has units of `rad/√s` — angle per square-root-of-time, because it's white *rate* noise integrated into angle. The continuous-time *rate* noise spectral density is `N` (in `rad/s/√Hz`, numerically the same). When you sample at rate `f₀` (bandwidth ≈ `f₀/2`, but the convention folds the factor in), the **discrete per-sample variance** of the angular-rate measurement is:

```
σ²_ω = N² · f₀          units: (rad/s)²
```

Worked: `N = 1.2e-3 rad/√s`, `f₀ = 100 Hz` → `σ²_ω = (1.2e-3)² × 100 = 1.44e-4 (rad/s)²`, so `σ_ω = 0.012 rad/s`. That `1.44e-4` is the number that goes on the diagonal of `angular_velocity_covariance` (Lecture 2 §3). The accelerometer's velocity-random-walk `N_a` (in `(m/s²)/√Hz`) converts identically: `σ²_a = N_a² · f₀`.

The two classic unit mistakes:

- **Forgetting the `√` in random walk.** `N` is per *square-root* second. People who treat it as per-second get a covariance off by a factor of `f₀` (here 100×), which makes the EKF wildly over- or under-trust the IMU.
- **Mixing °/√h with rad/√s.** Datasheets love `°/√h`; estimators want `rad/√s`. The conversion is `1 °/√h = (π/180) / 60 rad/√s ≈ 8.7e-5 rad/√s`. A `0.07 °/√h` datasheet spec is `~6e-6 rad/√s` — a 10,000× difference from the raw number if you forget to convert. Always carry units explicitly; never plug a bare number into a covariance field.

Because this conversion is so easy to botch, the mini-project tests the covariance fill against the formula on known inputs — so a unit slip is caught by an assertion, not by a mysteriously bad filter next week. Treat the units with the same suspicion you treat quaternion component order (Week 1): the math is easy, the *bookkeeping* is where the bug lives.

---

## 6g. A grades-of-IMU sense of scale

To calibrate well you need a feel for what "good" and "bad" mean, because a number in isolation is meaningless. Here is a rough sense of the spectrum, by grade, for *gyroscope* bias instability and angle random walk — the two numbers you'll read off your Allan plot:

| Grade | Typical bias instability | Typical ARW | Where you find it |
|---|---|---|---|
| Consumer MEMS | 5–50 °/h | 0.3–3 °/√h | Phones, hobby drones, a BNO085 on a hobby robot |
| Industrial MEMS | 1–10 °/h | 0.1–0.5 °/√h | A good robotics IMU (ICM-class), AMRs |
| Tactical | 0.1–1 °/h | 0.02–0.1 °/√h | Stabilized platforms, some autonomy stacks |
| Navigation | < 0.01 °/h | < 0.002 °/√h | Aircraft INS, fiber-optic gyros, $$$$ |

The point of the table is *calibration sanity-checking*, not memorization. If your Allan analysis of a consumer BNO085 reports a bias instability of `0.01 °/h` (navigation-grade!), you've made a units error or your log is too short to resolve the floor — a $30 chip is not a $30,000 INS. If it reports `500 °/h`, your bench was vibrating. A *consumer* MEMS gyro landing in the 5–50 °/h band with ARW around 0.5–2 °/√h is exactly what you should see, and seeing it tells you the whole pipeline — recording, computation, units — is sound. Always sanity-check your measured numbers against the grade of hardware you actually have; the most dangerous calibration is a precise, confident, physically-impossible one.

This also explains *why fusion is mandatory* for a wheeled robot on consumer hardware: a 10 °/h bias-instability gyro drifts far too fast to navigate on alone, no matter how well you calibrate it. Calibration gets you to the *floor* of what the hardware allows; fusion (Week 10) is what bounds the drift below that floor by bringing in the wheels and, later, absolute references. Knowing your IMU's grade tells you how much work fusion has to do — and on consumer hardware, the answer is "a lot," which is the whole reason Phase 2 spends three weeks on it.

---

## 7. Recap

You should now be able to:

- Write the gyro and accel measurement models and name the origin of each term (scale, misalignment, bias, white noise).
- Explain why bias dominates the integrated error for a slow robot, and why accel double-integration diverges as `t²`.
- State the bounded-roll/pitch vs. unbounded-yaw asymmetry and why gravity causes it.
- Compute an overlapping Allan deviation from a stationary log (integrating rate to angle first).
- Read random walk (−½ slope, `N` at τ=1 s), bias instability (flat floor), and rate random walk (+½ slope) off the plot.
- Distinguish what a static log gives you (bias, noise) from what needs motion (scale, misalignment).
- Solve the six-position accelerometer calibration as a least-squares problem and explain why gyro and accel calibrations are asymmetric (gravity is a free reference for the accel only).
- Record a clean stationary log, read a *real* (lumpy) Allan plot, convert noise density to discrete covariance with the units right, and sanity-check measured numbers against the IMU's grade.

A parting principle that survives the whole track: **measure your sensor; never assume it.** The datasheet quotes a population typical; your unit is one draw from that population, aged, mounted, and warmed in your specific way. The thirty minutes it takes to record a log and run an Allan analysis turns "I think the IMU is about this noisy" into "I measured this unit at this noise density on this date" — and that measured number is what makes every downstream estimator trustworthy. Engineers who skip this ship filters tuned on fiction; engineers who do it ship filters tuned on their actual hardware. The discipline is cheap and the payoff compounds through every week that touches state estimation.

Next: how to subtract that bias in a live node, integrate the calibrated gyro into orientation, and state the remaining uncertainty as honest covariance. Continue to [Lecture 2 — Integration Drift and Bias Correction](./02-integration-drift-and-bias-correction.md).

---

## References

- *An Introduction to Inertial Navigation* (Woodman, Cambridge UCAM-CL-TR-696): <https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-696.pdf>
- *Kalibr IMU noise model wiki* (noise density ↔ discrete): <https://github.com/ethz-asl/kalibr/wiki/IMU-Noise-Model>
- *`allan_variance_ros`* — reference Allan tool for ROS: <https://github.com/ori-drs/allan_variance_ros>
- *VectorNav — IMU specifications explained*: <https://www.vectornav.com/resources/inertial-navigation-primer/specifications--and--error-budgets/specs-imuspecs>
- *`sensor_msgs/Imu`* — message + covariance layout: <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/Imu.html>
- *REP 145 — IMU driver conventions*: <https://www.ros.org/reps/rep-0145.html>
- *IEEE Std 952 — gyro noise terminology* (ARW, bias instability, RRW definitions): search "IEEE 952 Allan variance gyroscope".
- *Cyrill Stachniss — sensors & state estimation lectures*: <https://www.ipb.uni-bonn.de/sensors-state-estimation/>
- *`imu_tools` — Madgwick/complementary filters* (the standard ROS2 IMU filtering stack): <https://github.com/CCNYRoboticsLab/imu_tools>

---

*Practice prompt before the exercises:* given a gyro Allan plot whose −½ line passes through `2.0e-3 rad/√s` at τ=1 s, a flat floor at `1.0e-4 rad/s`, and a sample rate of 200 Hz, compute (a) the noise density `N`, (b) the bias instability `B`, and (c) the `angular_velocity_covariance` diagonal you'd put in the IMU message. If you can do all three with the units right, you're ready for the Allan exercise.
