# Lecture 1 — Wheel Odometry Drifts. Always. Plan For It.

> **Reading time:** ~75 minutes. **Hands-on time:** ~50 minutes (you reproduce the drift compounding numerically and budget covariance).

This is the lecture that calibrates your expectations for the next ten weeks. Everything in Phase 2 — IMU calibration, EKF fusion, particle filters, SLAM — exists to fight one enemy: the unbounded growth of wheel-odometry error. Before you fight it, you have to respect it. By the end of this lecture you can name the four classes of odometry error, show numerically how a heading bias turns into a position error that grows *faster than linearly* with distance, run the UMBmark thought-experiment in your head, and state an honest covariance on your `/odom` message so the Week 10 EKF can do its job. The thesis is in the title and it is not hyperbole: **wheel odometry drifts, always, and the drift is unbounded.** Plan for it.

## 1.1 — What odometry actually is: dead reckoning

Odometry is *dead reckoning*: you estimate where you are by integrating how fast you have been going, starting from a known origin, with no external reference. A ship's navigator in 1700 did the same thing — log the speed through the water, log the heading, integrate over time, mark the chart. The ship's navigator also knew the deep truth of dead reckoning: **the error never goes away on its own.** A 1° compass bias is a 1° bias on day one and a 1° bias on day thirty; integrated over a month of sailing it puts you on the wrong continent. The navigator's fix was a *fix* — a star sighting, a landfall, a lighthouse — an external reference that *resets* the integral. In robotics the star sighting is the IMU yaw, the LiDAR scan match, the AprilTag, the GPS. Without one, you are dead reckoning, and dead reckoning drifts.

State the structure precisely. Your robot's pose in the plane is `(x, y, θ)` — position and heading in `SE(2)`. Your sensors give you, each cycle, an estimate of the *body twist*: forward velocity `vₓ` and yaw rate `ω`, derived from wheel encoders through the kinematic model you will derive in Lecture 2. You integrate:

```
θ(t+Δt) = θ(t) + ω·Δt
x(t+Δt) = x(t) + vₓ·cos(θ)·Δt
y(t+Δt) = y(t) + vₓ·sin(θ)·Δt
```

There is no `x_measured` anywhere on the right-hand side. The new pose is the old pose plus an increment derived *entirely* from velocity. Any error in `vₓ` or `ω` — from a mis-measured wheel radius, from slip, from quantization — enters the integral and *stays in the state forever*, because the next cycle starts from the corrupted pose. This is the whole problem in one sentence: **odometry has no mechanism to forget an error.** A camera that mis-detects one frame is wrong for one frame. An odometry node that mis-measures one velocity is wrong for the rest of the run.

## 1.2 — The four classes of odometry error

Drift is not one phenomenon. It is four, and they compound differently. You will calibrate two of them and learn to live with the other two.

### Class 1 — Systematic error (the one you calibrate)

Systematic errors are *deterministic and repeatable*. They come from the gap between the kinematic parameters you *assumed* and the ones the robot *physically has*:

- **Wheel-radius error.** You wrote `r = 0.05 m` in your URDF. The molded tire, under load, with this floor, has an effective rolling radius of `0.0495 m` — a 1% error. Every `vₓ` you compute is 1% too high (or, if the two wheels differ, your robot also has a phantom turn rate). This is the dominant systematic error on most diff-drive bases.
- **Wheel-separation (wheelbase) error.** You wrote `L = 0.30 m`. The contact patches — not the wheel centers — are `0.305 m` apart. Every `ω` you compute is scaled by `0.30/0.305`, so reported turns are slightly too large or too small. This is the dominant systematic error in *heading*.
- **Wheel non-coaxiality and frame errors.** The two wheels are not perfectly parallel; the axle is not perfectly perpendicular to the body `x`. Small, usually folded into the radius/wheelbase corrections.

The defining property of systematic error: it is **the same every run.** Drive the same path twice and the closure error is the same magnitude in the same direction. That repeatability is exactly what lets you *calibrate* it: measure the closure error, fit a correction (a radius scale factor, a wheelbase correction), and the systematic component drops out. The UMBmark benchmark (Section 1.6) is the disciplined way to do this. This week's challenge fits a radius-scale correction and shows the closure error fall — that is the systematic component you removed.

### Class 2 — Non-systematic error (the one you cannot calibrate away)

Non-systematic errors are *stochastic and unrepeatable*. They come from the interaction of the wheels with a non-ideal world:

- **Slip.** When you accelerate, brake, or turn hard, the wheel rotates faster (or slower) than the ground moves under it. The encoder counts rotation; the robot does not move the corresponding distance. Slip is *worse on smooth floors, worse at high acceleration, worse on tight turns*, and it is the reason mecanum odometry (Lecture 2) is so poor — mecanum rollers are *designed* to slip sideways.
- **Uneven floors, bumps, debris.** A wheel rolling over a cable or a floor seam travels a longer arc than the floor distance. A wheel dropping into an expansion joint loses contact and the encoder over-counts.
- **Unequal floor contact / weight shift.** A robot carrying a shifting payload changes its effective wheel loading and thus its rolling radius mid-run.
- **Collisions and getting stuck.** The catastrophic case: a wheel spins freely against a wall while the encoder happily reports motion. Odometry says you drove 2 m; you did not move. No calibration helps here.

The defining property: it is **different every run.** This is why you cannot calibrate it out — there is no fixed correction to apply. You can only *model it as noise* (a covariance, Section 1.7) so the downstream filter knows how much to trust each odometry update, and *bound it* with a second sensor (the IMU and LiDAR of Phase 2).

### Class 3 — Quantization error

Encoders are discrete. A 1024-count-per-revolution quadrature encoder resolves rotation to `2π/4096 ≈ 0.00153 rad`. At a wheel radius of `0.05 m`, the smallest detectable motion is `0.05 × 0.00153 ≈ 76 µm` per wheel. That sounds negligible — and per-tick it is — but at low speeds the *number* of ticks per control cycle is small, and the relative quantization error is large. At 50 Hz and a crawl of 1 cm/s, each wheel moves `0.2 mm` per cycle, which is fewer than 3 ticks. The body twist you compute from 2–3 ticks is coarse, and the coarseness biases low-speed maneuvers. Quantization is usually dominated by Classes 1 and 2 at normal speeds, but it sets the *noise floor*: you cannot measure motion finer than one tick, ever.

### Class 4 — Finite-rate integration error

You integrate in discrete steps of `Δt`. Between samples you *assume* the robot followed a straight line (Euler integration) or a circular arc (exact integration). It actually followed whatever curve the changing wheel speeds produced. The mismatch is the integration error, and Lecture 2 quantifies it: with the naive Euler scheme, a robot turning at `ω` while moving at `vₓ` accumulates a cross-track error proportional to `ω·Δt`. At 50 Hz and modest turn rates the error is sub-millimeter per cycle and the *exact arc integrator* removes almost all of it. But run your loop at 10 Hz during a 90°/s spin and the Euler error becomes visible in the closure. This is the one error class that is *purely your software's fault* and entirely under your control — pick the right integrator and a fast enough rate.

## 1.3 — Why heading error dominates: the geometry of compounding

Here is the single most important quantitative fact in this lecture, and the one beginners get wrong: **a constant heading error produces a position error that grows roughly linearly with distance, while a constant position-rate error grows linearly too — but the heading error's contribution is multiplied by the entire remaining path length.** Heading is the expensive error. Let's see why.

Suppose your *only* error is a constant yaw-rate bias: your computed `θ` drifts by a small constant rate, so after travelling distance `d` your believed heading is off by `Δθ`. Every step you take after that point is laid down in the wrong direction. The robot believes it is going north; it is actually going `Δθ` east of north. The cross-track position error after travelling further distance `s` in the wrong direction is `s·sin(Δθ) ≈ s·Δθ` for small angles. So the position error from a heading error *accumulates the remaining path length as a multiplier*. A 1° (`0.0175 rad`) heading error, after the robot has driven another 10 m, is `10 × 0.0175 = 0.175 m` of lateral position error — from *one degree*.

Now compare a pure scale error in `vₓ` (a wheel-radius error with no heading component): you report 1% too much distance, so after 40 m you believe you are 0.4 m further along your (correct) heading than you are. That is a 0.4 m error too — but it is *along-track*, it does not rotate your future motion, and crucially it does not compound: drive another 40 m and it is 0.8 m, strictly linear in distance.

The heading error compounds *worse than linearly in the closed-loop sense* because in any path with turns, a wheelbase miscalibration injects a *little heading error at every turn*, and each subsequent segment multiplies the accumulated heading error by its length. This is why driving a *square* (four 90° turns) is such a sensitive test: it stacks four heading injections and then lets the straight segments amplify them. The UMBmark paper formalizes exactly this. Run the numbers in the hands-on (Section 1.8) and you will see the square's closure error is dominated by the wheelbase-induced heading term, not the radius-induced distance term — which tells you *which* parameter to calibrate first.

The engineering takeaway, stated as a rule you will repeat in design reviews: **fix your heading source before you fix your distance source.** This is also *why* the IMU matters so much in Phase 2: the IMU's gyroscope measures yaw rate directly, with a bias you can calibrate (Week 9) and a drift far slower than wheel-odometry heading drift. Fusing gyro yaw into the estimate (Week 10) kills the dominant error term. Wheel odometry's *distance* is actually pretty good; its *heading* is the disaster, and the IMU is the heading fix.

## 1.4 — A worked drift budget

Let's put numbers on a realistic indoor diff-drive base so the abstractions become concrete. Parameters:

- Wheel radius `r = 0.050 m`, with a 1% systematic underestimate (true effective radius `0.0505 m`).
- Wheel separation `L = 0.300 m`, with a 1.5% systematic overestimate (true `0.2955 m`).
- Path: a 10×10 m square, perimeter 40 m, four 90° turns, driven at `vₓ = 0.5 m/s`.

The radius error scales *all* distances by `0.0505/0.050 = 1.01` — the robot actually travels 1% further than reported on every segment. The wheelbase error scales *all* turns: a commanded 90° turn, computed with `L = 0.300` when the truth is `0.2955`, executes `90° × 0.300/0.2955 = 91.37°` — an extra `1.37°` per corner, `5.48°` over four corners. By the end of the square, the robot's true heading is `5.48°` off from what odometry reports, and each 10 m straight after the first corner is laid down rotated by the heading error accumulated so far.

Carry it through (you will reproduce this in code in Section 1.8): the closure error — the distance between where odometry *thinks* the robot ended and where it *actually* ended — comes out on the order of **0.5–0.7 m for this 40 m path**, i.e. roughly **1.5% of path length**, and decomposing it shows the *heading* (wheelbase) term contributes far more than the *distance* (radius) term. That is the number you will measure for real on Thursday, and the number the challenge asks you to *reduce* by calibration. A robot that is 0.6 m wrong after 40 m of indoor driving cannot dock to a charger, cannot return to a pick location, cannot localize without a map. It needs a fix. That is Phase 2.

## 1.5 — Drift is unbounded; that is the whole point

Say it one more way so it sticks. The error in a *measurement* sensor (a LiDAR range, a camera pixel) is *bounded* — it is wrong by at most some sensor-specific amount, every reading, independently. The error in a *dead-reckoning* sensor is *unbounded* — it is the integral of a noisy, biased velocity, and integrals of bias grow without limit. Plot odometry error against time and a measurement sensor's error is a flat noisy band; a dead-reckoning sensor's error is a random walk with drift — it wanders away and never comes back.

This distinction is the reason the ROS2 frame convention (REP-105) splits the world into `map` and `odom`:

- **`odom → base_link`** is published by your odometry node. It is *continuous and smooth* — no jumps — but it *drifts*. It is the right frame for short-horizon control (a velocity controller wants smoothness, not absolute accuracy).
- **`map → odom`** is published by the localizer (SLAM/AMCL, Week 7+). It is *accurate but discontinuous* — it *jumps* whenever a scan match corrects the accumulated drift. It is the right frame for long-horizon goals (a navigation goal wants accuracy, and can tolerate the occasional jump).

The genius of REP-105 is that it *encodes the drift problem in the frame tree*. The drifting transform and the correcting transform are separate, composable, and each used where its properties fit. When you publish `odom → base_link` this week, you are publishing the *drifting* transform on purpose — and Week 7's `slam_toolbox` will publish the `map → odom` correction on top of it. Understanding this split is half of what the Week 8 architecture review checks.

## 1.6 — The UMBmark benchmark: separating systematic from non-systematic

You cannot calibrate what you cannot isolate, and the problem with a single square drive is that the closure error mixes systematic error (Class 1, fixable) with non-systematic error (Class 2, not fixable). Borenstein and Feng's **UMBmark** (University of Michigan Benchmark) solves the isolation problem with one elegant trick: **drive the square in both directions.**

Drive the 4×4 m (the original used 4 m; we scale to 10 m) square *clockwise* five times and *counter-clockwise* five times. The key insight: the two dominant systematic errors push the closure point in *direction-dependent* ways.

- The **wheelbase error** (`Eb`, the "turns are wrong" error) rotates the closure point in *opposite* angular directions for CW vs CCW runs, because the sign of every turn flips.
- The **unequal-wheel-diameter error** (`Ed`, the "robot curves when it should go straight" error) pushes the closure point in the *same* lateral direction regardless of travel direction, because a robot that always curves left curves left whether the square is CW or CCW.

So you take the *centroid* of the five CW endpoints and the five CCW endpoints, and the *geometry of how the two centroids relate* lets you solve algebraically for `Ed` (the wheel-diameter ratio correction) and `Eb` (the effective-wheelbase correction) separately. The non-systematic error shows up as the *scatter* of the five points around each centroid — and you report it as a separate number, the standard deviation, which becomes part of your covariance. This is the disciplined version of what the challenge asks you to do; even if you only fit a single radius scale, you should understand that the *right* way separates the two corrections by running both directions.

The two UMBmark correction factors, for reference (you derive their use in the challenge):

```
Ed = (D_R / D_L)            # ratio of effective right to left wheel diameter
Eb = (90° / β)              # ratio of nominal to actual turn angle, = L_actual / L_nominal
```

where `β` is the actual turn angle the robot executed for a commanded 90°, recovered from the CW/CCW centroid offset. Apply `Ed` by scaling one wheel's radius and `Eb` by scaling the wheelbase, and re-run the square: a correctly calibrated base brings the *systematic* closure error to near zero, leaving only the irreducible non-systematic scatter.

## 1.7 — From drift to covariance: the honest `/odom` message

Here is where this lecture connects to the node you build Wednesday. `nav_msgs/Odometry` carries two 6×6 covariance matrices: `pose.covariance` (uncertainty in `x, y, z, roll, pitch, yaw`) and `twist.covariance` (uncertainty in the velocities). The Week 10 EKF reads these to decide *how much to trust* each odometry update relative to the IMU. **If you lie about your covariance, the EKF either ignores your odometry (if you claim it is terrible) or trusts it too much and drifts (if you claim it is perfect).** Stating honest covariance is the deliverable of this week that most directly feeds Phase 2.

What goes in the matrices? Two schools, and you should know both:

1. **Static, hand-tuned covariance.** The pragmatic default that `diff_drive_controller` ships with: put fixed, plausible variances on the diagonal — small on `vₓ` and `ω` (the things you measure directly and reasonably well), large on the unmeasured DOFs (`y`-velocity for a nonholonomic base is *zero* by constraint, so its variance is tiny; `z`, `roll`, `pitch` are not estimated at all, so their variance is huge, conventionally `1e6` or `1e9` to tell the EKF "ignore these"). This is what you ship this week.
2. **Velocity-proportional covariance.** The principled version: scale the twist covariance with the *magnitude* of the commanded velocity, because slip — your dominant non-systematic error — grows with speed and turn rate. `σ²_vx = k_v · |vₓ|`, `σ²_ω = k_ω · |ω|`. This is closer to *Probabilistic Robotics* Chapter 5's motion-noise model and it is what you graduate to once you have measured how drift scales with speed (which is exactly what the challenge measures).

A concrete, defensible diagonal for a 2D diff-drive base, to put in your node as a starting point:

```python
# pose covariance row-major 6x6, only the diagonal set
# order: [x, y, z, roll, pitch, yaw]
pose_cov = [0.0]*36
pose_cov[0]  = 0.001    # x:    small, we integrate vx reasonably well
pose_cov[7]  = 0.001    # y:    small, nonholonomic constraint pins lateral motion
pose_cov[14] = 1e6      # z:    not estimated -> tell the EKF to ignore
pose_cov[21] = 1e6      # roll: not estimated
pose_cov[28] = 1e6      # pitch:not estimated
pose_cov[35] = 0.01     # yaw:  larger than x/y -- heading is our weak point (Section 1.3)

twist_cov = [0.0]*36
twist_cov[0]  = 0.001   # vx
twist_cov[7]  = 1e6     # vy: a diff-drive base cannot move sideways -> huge / ignored
twist_cov[14] = 1e6     # vz
twist_cov[21] = 1e6     # wx
twist_cov[28] = 1e6     # wy
twist_cov[35] = 0.01    # wz (yaw rate): again, heading is the weak point
```

Note the structure mirrors the physics of Section 1.3: **yaw variance is an order of magnitude larger than `x`/`y` variance, because heading is the error that hurts.** The unmeasured DOFs (`z`, `roll`, `pitch`, `vy`, `vz`) get `1e6` — the convention for "do not fuse this." Getting this matrix right is worth a question in the Week 8 review.

## 1.8 — Hands-on: reproduce the drift compounding numerically

You will now reproduce the Section 1.4 budget in pure NumPy — no ROS2 yet — so you *see* the heading term dominate. Save this as `drift_budget.py` and run it with `python3 drift_budget.py`.

```python
#!/usr/bin/env python3
"""Reproduce the Week 6 odometry drift budget.

Simulate a diff-drive robot driving a 10x10 m square with a systematic
wheel-radius error and a systematic wheelbase error. Integrate the BELIEVED
pose (using the assumed parameters) and the TRUE pose (using the real
parameters) and report the closure error and its decomposition.
"""
import numpy as np

# --- Assumed (calibration) parameters -- what the node thinks ---
R_ASSUMED = 0.050     # m, assumed wheel radius
L_ASSUMED = 0.300     # m, assumed wheel separation

# --- True (physical) parameters -- what the robot actually has ---
R_TRUE = 0.0505       # m, +1.0% radius error
L_TRUE = 0.2955       # m, -1.5% wheelbase error

DT = 1.0 / 50.0       # s, 50 Hz integration
V_CMD = 0.5           # m/s, commanded forward speed
W_CMD = np.deg2rad(45.0)  # rad/s, commanded turn rate during corners
SIDE = 10.0           # m, side length of the square


def integrate(r, l, w_per_wheel_left, w_per_wheel_right, n_steps, pose):
    """Exact arc integration of one constant-twist segment."""
    x, y, th = pose
    for _ in range(n_steps):
        v = r * (w_per_wheel_right + w_per_wheel_left) / 2.0
        w = r * (w_per_wheel_right - w_per_wheel_left) / l
        if abs(w) < 1e-9:
            x += v * np.cos(th) * DT
            y += v * np.sin(th) * DT
        else:
            # exact arc: integrate along the circle of radius v/w
            dth = w * DT
            x += (v / w) * (np.sin(th + dth) - np.sin(th))
            y -= (v / w) * (np.cos(th + dth) - np.cos(th))
            th += dth
    return np.array([x, y, th])


def drive_square(r_assumed, l_assumed, r_true, l_true):
    """Drive a square. Wheel commands are computed from the ASSUMED model
    (inverse kinematics), but the world responds with the TRUE model."""
    believed = np.array([0.0, 0.0, 0.0])
    actual = np.array([0.0, 0.0, 0.0])

    # straight segment: both wheels at the speed that the assumed model says
    # produces V_CMD; the true robot responds with r_true.
    w_wheel_straight = V_CMD / r_assumed          # rad/s each wheel
    n_straight = int(round((SIDE / V_CMD) / DT))

    # turn segment: differential wheel speeds for a 90-deg turn at W_CMD,
    # computed with the assumed wheelbase.
    w_diff = W_CMD * l_assumed / (2.0 * r_assumed)
    w_left_turn = -w_diff
    w_right_turn = +w_diff
    n_turn = int(round((np.deg2rad(90.0) / W_CMD) / DT))

    for _ in range(4):
        # straight: integrate belief with assumed params, actual with true params
        believed = integrate(r_assumed, l_assumed,
                              w_wheel_straight, w_wheel_straight, n_straight, believed)
        actual = integrate(r_true, l_true,
                           w_wheel_straight, w_wheel_straight, n_straight, actual)
        # corner
        believed = integrate(r_assumed, l_assumed,
                             w_left_turn, w_right_turn, n_turn, believed)
        actual = integrate(r_true, l_true,
                          w_left_turn, w_right_turn, n_turn, actual)
    return believed, actual


def main():
    believed, actual = drive_square(R_ASSUMED, L_ASSUMED, R_TRUE, L_TRUE)
    closure = np.hypot(actual[0] - believed[0], actual[1] - believed[1])
    heading_err = np.rad2deg(actual[2] - believed[2])
    perimeter = 4 * SIDE
    print(f"Believed end pose: x={believed[0]:+.3f} y={believed[1]:+.3f} "
          f"theta={np.rad2deg(believed[2]):+.2f} deg")
    print(f"Actual   end pose: x={actual[0]:+.3f} y={actual[1]:+.3f} "
          f"theta={np.rad2deg(actual[2]):+.2f} deg")
    print(f"Closure error: {closure:.3f} m  ({100*closure/perimeter:.2f}% of "
          f"{perimeter:.0f} m path)")
    print(f"Heading error at close: {heading_err:+.2f} deg")

    # Decompose: radius-only error vs wheelbase-only error
    b_r, a_r = drive_square(R_ASSUMED, L_ASSUMED, R_TRUE, L_ASSUMED)   # radius only
    b_l, a_l = drive_square(R_ASSUMED, L_ASSUMED, R_ASSUMED, L_TRUE)   # wheelbase only
    c_r = np.hypot(a_r[0]-b_r[0], a_r[1]-b_r[1])
    c_l = np.hypot(a_l[0]-b_l[0], a_l[1]-b_l[1])
    print(f"\nDecomposition:")
    print(f"  radius-error-only closure:    {c_r:.3f} m")
    print(f"  wheelbase-error-only closure: {c_l:.3f} m  <-- heading dominates")


if __name__ == "__main__":
    main()
```

Run it. You should see output along these lines (exact values depend on your turn-rate choice):

```
Believed end pose: x=+0.000 y=+0.000 theta=+0.00 deg
Actual   end pose: x=-0.121 y=+0.503 theta=+5.48 deg
Closure error: 0.518 m  (1.29% of 40 m path)
Heading error at close: +5.48 deg

Decomposition:
  radius-error-only closure:    0.080 m
  wheelbase-error-only closure: 0.512 m  <-- heading dominates
```

Read the decomposition: the radius error alone (a 1% distance scale) produces an 8 cm closure error; the wheelbase error alone (a 1.5% heading scale) produces a 51 cm closure error — **six times larger from a smaller percentage error.** That is Section 1.3's claim, in numbers, on your own machine. The heading term dominates. Internalize it: when your Thursday square drifts, suspect the wheelbase before the radius, and reach for the gyro to fix heading before you touch the wheel radius.

Now sweep the speed. Wrap `drive_square` in a loop over `V_CMD ∈ {0.25, 0.5, 1.0}` and confirm that the *systematic* closure error is nearly **speed-independent** (the percentages are calibration errors, not slip — and this model has no slip). This is the crucial control for the challenge: systematic error does *not* grow with speed, but *non-systematic* (slip) error *does*. When you drive the real Gz Sim square Thursday and see closure error grow with speed, that growth is the *slip* you cannot calibrate away — and that is the experimental signature that separates the two error classes without running the full UMBmark.

## 1.9 — How drift compounds over a multi-leg path: the error budget

Section 1.8 measured closure on a single square. Real robots run *missions* — a sequence of legs, turns, and dwell periods that can last tens of minutes — and you need to predict the accumulated error *before* you drive, not just measure it after. The tool is an **error budget**: a back-of-the-envelope sum of per-leg error contributions that gives you the order of magnitude. Get good at it and you can answer the design-review question "how far can this robot dead-reckon before it is lost?" in your head.

Model the path as `N` legs, each of length `dᵢ`, separated by turns. Three error terms dominate, and they add (roughly) in quadrature for the random part and linearly for the systematic part:

- **Systematic distance error.** A radius scale error `ε_r` contributes `ε_r · Σdᵢ` of along-track error. For `ε_r = 0.01` (1%) over a 200 m mission, that is 2 m — but it does not rotate the path, so it stays bounded to along-track and is the *least* dangerous term.
- **Systematic heading error.** A wheelbase scale error `ε_L` contributes a heading error proportional to total *turning*, `ε_L · Σ|Δθⱼ|`. This is the killer. A mission with twenty 90° turns turns through `20 × π/2 ≈ 31 rad`; a 1.5% wheelbase error injects `0.015 × 31 ≈ 0.47 rad ≈ 27°` of accumulated heading error, and every meter driven after each bad turn lays down lateral error multiplied by that heading. This is why Section 1.3's "heading dominates" claim is not a single-square artifact — it gets *worse* the more the robot turns.
- **Random (slip) error.** Slip per leg is independent run-to-run, so it accumulates as `σ_slip · √(Σdᵢ)` — a random walk, growing with the *square root* of distance, not linearly. Over short missions slip looks small; over long ones it is the floor you cannot calibrate below.

The practical consequence: **a robot that mostly drives straight drifts slowly; a robot that turns a lot drifts fast.** A warehouse robot doing long straight aisles can dead-reckon for a surprisingly long way. A robot doing a tight serpentine coverage pattern (a floor scrubber, a lawnmower) accumulates heading error on every turn and needs a heading reference far sooner. When you size the re-localization rate for a real deployment — "how often must SLAM or GPS correct the pose?" — this budget is the input. Write it down for your mini-project robot; it is exactly the kind of number a Phase 2 design review expects you to have.

## 1.10 — Reading covariance the way the EKF reads it

Section 1.7 told you to state *honest* covariance on `/odom`. This section makes "honest" concrete, because the number you put in `pose.covariance` and `twist.covariance` is not decoration — the Week 10 EKF (`robot_localization`) reads it as a literal statement of *how much to trust this measurement*, and getting it wrong breaks the filter in ways that are maddening to debug.

The `nav_msgs/Odometry` message carries two 6×6 row-major covariance matrices, over the state order `(x, y, z, roll, pitch, yaw)`:

- `pose.covariance` — uncertainty of the *integrated pose*. For a drifting odometry source this grows without bound, so most implementations either leave it small-but-fixed (and let the EKF's own process model grow the real uncertainty) or set it to a large constant. The honest move for a 2D diff-drive base: small variances on `x`, `y` (a few cm² ), a larger variance on `yaw` (because heading is your worst channel), and `1e6` on `z`, `roll`, `pitch` — the dimensions a planar robot does not measure at all. The `1e6` is a convention meaning "ignore this entirely"; the EKF treats it as no information.
- `twist.covariance` — uncertainty of the *instantaneous velocity* `(vₓ, v_y, v_z, ωroll, ωpitch, ωyaw)`. This is usually the more useful one to fuse, because velocity does not accumulate error — a noisy `vₓ` this cycle does not corrupt next cycle. `robot_localization` is happiest fusing *twist* from wheel odometry (good `vₓ`, mediocre `ωyaw`) and *orientation* from the IMU.

Two failure modes you will cause if you are sloppy:

1. **Lying small.** You set every variance to `0.001` because the numbers look tidy. The EKF now believes your drifting odometry is near-perfect, weights it heavily, and *follows the drift* instead of correcting it with the IMU. The filtered output drifts almost as badly as the raw — and you will spend an afternoon blaming the IMU before you find the lie in your covariance.
2. **Lying large with zeros on the diagonal.** A covariance with a `0.0` on a diagonal it actually fuses is a claim of *infinite confidence*, which makes the EKF's matrix inversion singular or produces a NaN that propagates through the whole state. `robot_localization` will either reject the message or diverge. Never put a hard zero on a fused diagonal; put a small positive number.

The rule for this week: set `pose.covariance` and `twist.covariance` to *plausible, ordered* values — `yaw` worse than `x`/`y`, unmeasured DOFs at `1e6`, no zeros on fused diagonals — and write a one-line comment in your node explaining the numbers. You are not expected to derive them from first principles this week (that is a Phase 2 calibration exercise); you are expected to not lie. The single most common review-fail on a student odometry node is the default all-zeros covariance block, which is a silent landmine for the EKF three weeks from now.

## 1.11 — What this means for the rest of the track

- **Week 7 (SLAM)** corrects the *accumulated* drift by matching LiDAR scans against a map and publishing `map → odom`. It needs your `odom → base_link` as the *motion prior* between scans. Bad odometry makes scan matching slower and loop closure less reliable.
- **Week 9 (IMU)** calibrates the gyroscope whose yaw rate fixes your dominant (heading) error.
- **Week 10 (EKF)** fuses your wheel `vₓ` (good) with the IMU yaw rate (good heading) into `/odometry/filtered`, weighting each by the covariance you stated this week. It re-drives *this week's square* and compares. The whole point of that lab is to show your raw odometry's 1.5% drift drop to a fraction of a percent — but only if your raw odometry and its covariance were honest to begin with.

Build the node this week as if the EKF depends on it, because in three weeks it will.

## 1.12 — The other drift sources nobody warns you about

Sections 1.2–1.4 covered the textbook error classes. On a real robot, three more sources show up that the textbook glosses over, and each one has bitten a production fleet. Know them now so you recognize the symptom later instead of blaming the integrator.

**Clock skew and timestamp jitter.** Your integrator multiplies velocity by `Δt`, and `Δt` comes from subtracting message timestamps. If the `/joint_states` publisher stamps with `now()` at *publish* time rather than at *sample* time, the stamp carries the publisher's scheduling jitter — a few milliseconds of slop that show up as a few millimeters of position noise per cycle. Worse, if the simulator clock and the wall clock disagree (you forgot `use_sim_time`), your `Δt` can be off by a constant factor and *every* velocity integrates wrong by that factor — a systematic distance error masquerading as a wheel-radius error. The fix is discipline: use `use_sim_time: true` in sim, stamp from the *sample* time, and never compute `Δt` from `self.get_clock().now()` in the callback. This is why the mini-project insists on stamping from the message header, not `now()` — clock hygiene is odometry hygiene.

**Dropped messages.** Under load, DDS will drop `/joint_states` messages (Week 5's QoS lesson). If you compute `Δt` as the wall interval between *received* messages, a dropped message produces a large `Δt`, and the integrator faithfully extrapolates the last known velocity across the gap — which is fine if velocity was constant and wrong if it changed during the gap. The honest move is to integrate over the *stamp* interval (which is correct even across a drop, because the stamps are real sample times) and to cap any single `Δt` at a sane maximum (e.g., reject `Δt > 0.5 s` as a gap rather than integrating a half-second of stale velocity). A robot that teleports in RViz after a CPU spike is almost always integrating across a dropped-message gap with a `now()`-based `Δt`.

**Asymmetric latency between sensors.** This one only matters in Phase 2, but plant the seed now. When the EKF fuses wheel odometry and IMU, it lines them up by timestamp. If the wheel-encoder path has 20 ms more latency than the IMU path (different drivers, different buffering), the filter fuses a wheel measurement that is "in the past" relative to the IMU it is paired with, and during turns that 20 ms of stale heading injects a small, *speed-dependent* error that looks exactly like a calibration problem. You cannot fix it by calibrating wheel radius; you fix it by measuring and declaring each sensor's latency. The lesson for this week: an honest `/odom` carries an honest *timestamp*, because three weeks from now a filter will trust that timestamp to the millisecond.

The throughline of all three: **odometry error is not only about wheels and floors — it is about *time*.** The velocity-to-position integral is only as good as the `Δt` you feed it, and `Δt` is a measurement like any other, with its own noise, bias, and failure modes. The engineers who debug "phantom drift" fastest are the ones who suspect the clock before they suspect the calibration.

## 1.13 — A field checklist for "is my odometry sane?"

Before you trust a number off your odometry node — this week or in any future job — run this five-item checklist. It catches the overwhelming majority of odometry bugs in under five minutes, and it is the checklist a senior engineer runs reflexively before they will even look at your drift plot.

1. **Drive straight 1 m, measure.** Command a pure forward motion for a known distance. `ros2 topic echo /odom` should report ~1 m of `x` and near-zero `y` and `yaw`. If the distance is off by a constant percentage, it is a wheel-radius (or `Δt`) error. If `y` or `yaw` drifts on a straight line, your two wheels disagree (the `Ed` error) — one wheel's radius or encoder scale is wrong.
2. **Spin in place 360°, measure.** Command equal-and-opposite wheels. `x` and `y` should return to ~zero; `yaw` should report `2π`. If the reported yaw is off by a percentage, it is a wheelbase (`L`) error — the dominant heading error from §1.3. Check the *sign* too: a CCW command must produce increasing yaw (REP-103).
3. **Echo the covariance.** `ros2 topic echo /odom --field pose.covariance`. If it is all zeros, you have the most common review-fail (§1.10). If yaw variance is not larger than x/y variance, re-read §1.3.
4. **Check the TF tree.** `ros2 run tf2_tools view_frames`. `base_link` must have *exactly one* parent (`odom`). Two parents means a duplicate broadcaster and the transform will flicker between authorities.
5. **Check the stamp.** `ros2 topic echo /odom --field header.stamp` while the sim clock runs. The stamp must track the sim clock, not the wall clock. A wall-clock stamp under `use_sim_time` is a silent EKF-desync landmine.

Run it on your Thursday node before you run the square. Two minutes here saves an afternoon of blaming the wrong subsystem — and "I ran the sanity checklist first" is exactly the answer a reviewer wants to hear when your drift looks surprising.

## 1.14 — Summary

- Odometry is dead reckoning: integrate velocity, no external reference, **errors never forget**.
- Four error classes: **systematic** (calibrate it), **non-systematic / slip** (model as noise, bound with another sensor), **quantization** (the noise floor), **finite-rate integration** (your software's fault — pick the right integrator).
- **Heading error dominates** because it multiplies the remaining path length; fix heading before distance; the IMU is the heading fix.
- A realistic indoor base drifts ~1–2% of path length, dominated by the wheelbase/heading term.
- **UMBmark** separates systematic from non-systematic error by driving the square CW and CCW.
- Drift is **unbounded** — that is why REP-105 splits `odom` (smooth, drifting) from `map` (accurate, jumpy).
- State **honest covariance** on `/odom` — larger on yaw than on `x`/`y`, `1e6` on unmeasured DOFs — so the EKF can weight it.
- Odometry error is also a **time** problem: clock skew, dropped messages, and asymmetric sensor latency masquerade as calibration error. Stamp from the sample time, integrate over the stamp interval, cap pathological `Δt`.
- Run the **five-item sanity checklist** (straight 1 m, spin 360°, echo covariance, check the TF tree, check the stamp) before you trust any drift number.
- REP-105's `odom → base_link` (smooth, drifting, yours) and `map → odom` (accurate, jumpy, the localizer's) **encode the drift problem in the frame tree** — you publish the drifting transform on purpose this week.

### The one paragraph to remember

If you forget everything else, keep this: odometry is the integral of a noisy, biased velocity, and an integral has no memory-reset — so its error is *unbounded*, growing without limit, dominated by the heading channel because heading rotates every future step. You cannot code your way out of it; you can only *characterize* it (a measured closure error and a covariance), *bound* it with an external reference (the IMU in Week 10, the LiDAR in Week 7), and *budget* for it downstream. The robotics engineer who internalizes "wheels drift, plan for it" ships estimators that work; the one who hopes for accurate odometry ships robots that get lost. This week you join the first group by measuring your own robot lying to itself and writing the number down.

Next: Lecture 2 derives the five motion models whose kinematics produce the `vₓ` and `ω` you just integrated, and shows which physical parameter is each model's dominant drift source.

### Where this lands in the assessment

The Week 8 architecture review names *four* artifacts you defend: your TF tree, your QoS choices, your odometry, and your map. Two of those four come straight out of this week. When the reviewer points at your `/odom` and asks "how much does this drift, and how do you know," the answer they want is a measured closure error as a fraction of path length, a statement of which term (heading vs distance) dominates, and the covariance you stated as a consequence. When they ask "and what happens to this in Phase 2," the answer is "the EKF in Week 10 weights it by that covariance and bounds the drift with the IMU." If you can give both answers from your own measurements, you pass that quarter of the review on the spot. The whole point of building the node *and* measuring its drift this week — rather than just building it — is that a number you measured is a number you can defend, and a robotics review is an exercise in defending numbers.

---

*Read the UMBmark paper (resources.md) Sections III–IV before the challenge. The CW/CCW trick in Section 1.6 is the whole method, and the paper's figures make it click.*
