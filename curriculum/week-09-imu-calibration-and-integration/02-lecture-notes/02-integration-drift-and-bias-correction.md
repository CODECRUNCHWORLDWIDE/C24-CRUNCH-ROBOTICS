# Lecture 2 — Integration Drift, Bias Correction, and Honest Covariance

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can integrate calibrated gyro data into an orientation estimate, build a `rclpy` node that estimates and subtracts the stationary bias and re-publishes a calibrated `/imu/data`, quantify the drift reduction, and populate the `sensor_msgs/Imu` covariance fields honestly from your Allan numbers.

Lecture 1 characterized the IMU's errors. This lecture *removes* what you can (bias subtraction), *integrates* the result correctly (quaternion kinematics), and *states the rest honestly* (covariance) so next week's EKF can trust the IMU exactly as much as it should. Three parts: (1) integrating angular velocity into orientation, (2) the bias-subtraction node, (3) honest covariance.

---

## Part 1 — Integrating angular velocity into orientation

### 1.1 The quaternion kinematic equation

You have a gyro giving body-frame angular velocity `ω = [ωx, ωy, ωz]` at, say, 100 Hz. You want orientation `q` (a unit quaternion, in your `crunch_rotations` `(w,x,y,z)` convention from Week 1). The kinematic relationship is:

```
q̇ = ½ · q ⊗ (0, ω)
```

where `⊗` is the Hamilton product and `(0, ω)` is the pure quaternion built from the angular-velocity vector. Read it as: the rate of change of orientation is half the current orientation times the angular velocity, expressed as a quaternion. The factor of ½ is the same half-angle that appeared in Week 1 — quaternions live on the double cover, and the kinematics inherit the half.

### 1.2 Discrete integration

You don't have `q̇` in closed form; you have samples `ωₖ` at timestep `Δt`. The simplest integrator is first-order (Euler):

```
q_{k+1} = normalize( q_k  +  ½ · q_k ⊗ (0, ωₖ) · Δt )
```

This works but accumulates a small norm error each step, which is why you **re-normalize every step**. A better integrator, exact for constant `ω` over the step, uses the rotation-vector exponential:

```
Δθ = ωₖ · Δt                      (the incremental rotation vector)
Δq = ( cos(‖Δθ‖/2),  (Δθ/‖Δθ‖)·sin(‖Δθ‖/2) )    (axis-angle → quaternion, Week 1 §5.2)
q_{k+1} = normalize( q_k ⊗ Δq )
```

This is the **exponential map** integrator — it builds the incremental rotation as a proper quaternion via the half-angle formula and composes it. It's the right default: norm-preserving by construction, exact for constant rate, and it reuses exactly the `axis_angle_to_quat` you wrote in Week 1. Here it is in code, leaning on `crunch_rotations`:

```python
import numpy as np
from crunch_rotations.quaternion import quat_mul, quat_normalize
from crunch_rotations.conversions import axis_angle_to_quat


def integrate_gyro(q, omega, dt):
    """Advance orientation quaternion q by angular velocity omega over dt.

    q     : (w, x, y, z) unit quaternion (current orientation)
    omega : (wx, wy, wz) body-frame angular velocity, rad/s, BIAS-CORRECTED
    dt    : timestep, seconds
    returns the new (w, x, y, z) quaternion.
    """
    omega = np.asarray(omega, float)
    angle = np.linalg.norm(omega) * dt
    if angle < 1e-12:
        return quat_normalize(q)             # no rotation this step
    axis = omega / np.linalg.norm(omega)
    dq = axis_angle_to_quat(axis, angle)     # incremental rotation
    return quat_normalize(quat_mul(q, dq))   # compose, re-normalize
```

The single most important word in that docstring is **BIAS-CORRECTED**. Feed it the raw gyro and you integrate the bias into a drifting ramp. Feed it `ω − b_g` and the ramp largely disappears. That subtraction is Part 2.

### 1.3 Why this drifts anyway (and why that's fine)

Even with perfect bias subtraction, integrated yaw drifts slowly — the residual is the random walk and the bias *instability* (Lecture 1 §4). There is no integrator clever enough to fix that; it's information that isn't in the gyro. The job this week is to make the drift *as small as the sensor physically allows* (by removing bias) and then *state how much remains* (covariance), so that next week the EKF can lean on wheel odometry and any other sources to bound it. You're not eliminating drift — you're minimizing it and quantifying it.

---

## Part 2 — The bias-subtraction node

### 2.1 Estimating the bias

The bias of a stationary gyro is just the mean of a stationary window — the true rate is zero, so the average reading *is* the offset (the white noise averages to zero over enough samples). The recipe:

1. Hold the robot **truly stationary** (no vibration, no one bumping the table).
2. Collect `N` samples (a few thousand — 30 s at 100 Hz is 3000, plenty).
3. The per-axis mean of the gyro is `b_g`; the per-axis mean of the accel, *minus* the gravity vector, is `b_a`.

The longer the window, the better the estimate — the standard error of the mean falls as `1/√N`, and Lecture 1's Allan plot told you the floor (bias instability) past which a longer window stops helping. A 30–120 s window is the sweet spot.

### 2.2 The node

A clean design separates two phases: a **calibration phase** that accumulates the stationary mean, and a **running phase** that subtracts it and re-publishes. The node subscribes to raw `/imu/data` (sensor QoS — `BEST_EFFORT`, from Week 5) and publishes calibrated `/imu/data_calibrated`.

```python
#!/usr/bin/env python3
"""Estimate stationary gyro/accel bias, then re-publish calibrated /imu/data."""
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

GRAVITY = 9.80665  # m/s^2


class ImuBiasCorrector(Node):
    def __init__(self) -> None:
        super().__init__("imu_bias_corrector")
        self.declare_parameter("calib_samples", 3000)   # ~30 s at 100 Hz
        self.n_target = self.get_parameter("calib_samples").value

        self.gyro_acc = np.zeros(3)
        self.acc_acc = np.zeros(3)
        self.count = 0
        self.gyro_bias = None
        self.accel_bias = None

        # Sensor QoS on both ends (Week 5): IMU is BEST_EFFORT / KEEP_LAST.
        self.sub = self.create_subscription(
            Imu, "/imu/data", self.on_imu, qos_profile_sensor_data
        )
        self.pub = self.create_publisher(
            Imu, "/imu/data_calibrated", qos_profile_sensor_data
        )
        self.get_logger().info(
            f"calibrating: hold the robot STILL for {self.n_target} samples..."
        )

    def on_imu(self, msg: Imu) -> None:
        g = np.array([msg.angular_velocity.x,
                      msg.angular_velocity.y,
                      msg.angular_velocity.z])
        a = np.array([msg.linear_acceleration.x,
                      msg.linear_acceleration.y,
                      msg.linear_acceleration.z])

        if self.gyro_bias is None:
            # --- Calibration phase: accumulate the stationary mean. ---
            self.gyro_acc += g
            self.acc_acc += a
            self.count += 1
            if self.count >= self.n_target:
                self.gyro_bias = self.gyro_acc / self.count
                accel_mean = self.acc_acc / self.count
                # Remove gravity from the accel mean. Assume z is up at rest;
                # a robust version uses the measured gravity DIRECTION.
                gravity_vec = np.array([0.0, 0.0, GRAVITY])
                self.accel_bias = accel_mean - gravity_vec
                self.get_logger().info(
                    f"gyro_bias  (rad/s) = {self.gyro_bias}\n"
                    f"accel_bias (m/s^2) = {self.accel_bias}"
                )
            return

        # --- Running phase: subtract bias, re-publish, preserve stamp/frame. ---
        out = Imu()
        out.header = msg.header                      # keep acquisition stamp + frame
        out.orientation = msg.orientation
        out.angular_velocity.x = g[0] - self.gyro_bias[0]
        out.angular_velocity.y = g[1] - self.gyro_bias[1]
        out.angular_velocity.z = g[2] - self.gyro_bias[2]
        out.linear_acceleration.x = a[0] - self.accel_bias[0]
        out.linear_acceleration.y = a[1] - self.accel_bias[1]
        out.linear_acceleration.z = a[2] - self.accel_bias[2]
        # Covariance is set in Part 3.
        self.pub.publish(out)


def main() -> None:
    rclpy.init()
    node = ImuBiasCorrector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

Three things to notice, because they're the bugs people actually hit:

- **Preserve the header.** `out.header = msg.header` carries the *acquisition* stamp and `frame_id` through unchanged (Week 1 / Week 5 idiom). A calibrated message stamped at *publish* time would lie to the EKF about *when* the measurement happened.
- **Gravity removal is frame-sensitive.** The naive `[0,0,g]` assumes the IMU's z-axis points up at rest. If your IMU is mounted tilted, you must use the *measured* gravity direction (normalize the stationary accel mean and scale to `g`), or you'll bake the mounting tilt into the accel bias. The robust version measures the gravity direction; the simple version assumes z-up and documents the assumption.
- **"Stationary" must be real.** If the robot vibrates, a fan blows on it, or someone leans on the bench during calibration, your "bias" includes that motion and the correction is wrong. The challenge's drift test is your check: a bad calibration shows up as *no* drift reduction.

### 2.3 Measuring that it worked

The proof is the drift comparison. Integrate yaw from the *raw* gyro and from the *calibrated* gyro over the same stationary window, and compare the final angle. Raw should ramp (bias); calibrated should stay near zero:

```python
# pseudo: over a stationary log
yaw_raw, yaw_cal = 0.0, 0.0
for k in range(len(samples)):
    yaw_raw += gyro_z_raw[k] * dt
    yaw_cal += (gyro_z_raw[k] - gyro_bias_z) * dt
print(f"raw drift  = {np.degrees(yaw_raw):.1f} deg")
print(f"calib drift = {np.degrees(yaw_cal):.1f} deg")
print(f"reduction   = {abs(yaw_raw / yaw_cal):.1f}x")
```

A healthy result is a 10×–50× reduction. If the factor is ~1, the calibration didn't take (window too short, or not actually stationary). That's the week's headline number.

---

## Part 3 — Honest covariance

### 3.1 What the covariance fields are

A `sensor_msgs/Imu` carries three 3×3 row-major covariance arrays:

```
float64[9] orientation_covariance
float64[9] angular_velocity_covariance
float64[9] linear_acceleration_covariance
```

These are the sensor's *honest statement of its own uncertainty*. The downstream EKF (Week 10) reads them to decide how much to *trust* each measurement: small covariance → "believe me, weight me heavily"; large covariance → "I'm noisy, lean on other sensors." **Getting these wrong is the most common cause of a badly-tuned filter** — too-small covariance makes the EKF overtrust a noisy IMU and the estimate jitters; too-large makes it ignore a good IMU and the estimate lags.

There's also a ROS convention you must respect: if the IMU does **not** produce orientation (a raw 6-DOF gyro+accel), set `orientation_covariance[0] = -1.0` to signal "orientation unknown, don't use it." Stuffing zeros there tells the EKF "I have a perfectly certain orientation of identity," which is a lie that wrecks the fusion.

### 3.2 Filling them from the Allan numbers

This is where Lecture 1 pays off. The diagonal of `angular_velocity_covariance` is the **variance** of the angular-velocity measurement — and the gyro noise density `N` from your Allan plot gives it directly. For a measurement at sample rate `f₀`, the discrete per-sample variance is:

```
σ²_ω = N² · f₀          (N is the continuous noise density in rad/√s; multiply by bandwidth)
```

So the angular-velocity covariance diagonal is `[σ²_ω, σ²_ω, σ²_ω]` (per axis; use the per-axis Allan numbers if they differ). The accelerometer's `linear_acceleration_covariance` is filled the same way from the accel velocity-random-walk number. Off-diagonal terms are usually left zero (axes assumed uncorrelated, which is close enough for MEMS).

```python
import numpy as np

def fill_imu_covariance(msg, gyro_noise_density, accel_noise_density, sample_rate):
    """Populate IMU covariance diagonals from Allan-variance noise densities."""
    var_w = gyro_noise_density ** 2 * sample_rate       # (rad/s)^2
    var_a = accel_noise_density ** 2 * sample_rate       # (m/s^2)^2

    # row-major 3x3, diagonal only.
    msg.angular_velocity_covariance = [
        var_w, 0.0, 0.0,  0.0, var_w, 0.0,  0.0, 0.0, var_w
    ]
    msg.linear_acceleration_covariance = [
        var_a, 0.0, 0.0,  0.0, var_a, 0.0,  0.0, 0.0, var_a
    ]
    # 6-DOF IMU produces no orientation: signal "unknown" with -1 in [0].
    msg.orientation_covariance = [-1.0, 0.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 0.0]
    return msg
```

### 3.3 The discipline

> **Measure your covariance; never invent it.** The numbers come from *your* Allan plot of *your* sensor, not from a datasheet typical and not from a round number that "looked about right." When the Week 10 EKF behaves — when `/odometry/filtered` is smooth and bounded — it's because the IMU told the truth about its own uncertainty. When it misbehaves, the covariance is the first thing to check. This is the bookkeeping-with-covariance mindset that the entire sensor-fusion arc rests on, and it starts here, this week, with the IMU being honest about itself.

---

## Part 4 — Putting it together: the calibration pipeline

The full Week-9 pipeline, which the mini-project assembles:

```
30-min stationary log ──► Allan variance ──► (N gyro, B gyro, N accel, ...)
        │                                              │
        └──► stationary mean ──► (gyro_bias, accel_bias)
                                       │                │
                                       ▼                ▼
   live /imu/data ──► ImuBiasCorrector ──► subtract bias + fill covariance ──► /imu/data_calibrated
                                                                                      │
                                                                                      ▼
                                                                         (Week 10: robot_localization EKF)
```

Every arrow is something you build this week: the Allan analysis, the bias estimate, the live corrector, the honest covariance. The output — a calibrated, honestly-described IMU stream — is the single most important input to next week's fusion.

---

## Part 5 — Mid-stance bias correction (the ZUPT idea)

Bias is not truly constant — it drifts with temperature and time (the rate-random-walk from Lecture 1). A bias you measured at boot is stale an hour later when the chip has warmed up. The professional answer is to *re-estimate bias whenever the robot is known to be stationary*, a technique borrowed from pedestrian and legged-robot navigation called the **Zero-Velocity Update (ZUPT)**, sometimes "mid-stance correction" because legged robots get a free stationary interval each time a foot is planted.

The idea: detect when the robot is *actually still* — the variance of the accel and gyro magnitude over a short window drops below a threshold — and during those intervals, (a) re-estimate the gyro bias as the current stationary mean, and (b) optionally reset accumulated velocity to zero (since you *know* it's zero). For a wheeled robot, the stationary intervals are whenever `/cmd_vel` is zero and the wheels report no motion. A simple detector:

```python
def is_stationary(gyro_window, accel_window, gyro_thresh=0.02, accel_thresh=0.3):
    """True if the robot is still: low variance on both gyro and accel magnitude."""
    import numpy as np
    g_var = np.var(np.linalg.norm(gyro_window, axis=1))
    a_var = np.var(np.linalg.norm(accel_window, axis=1))
    return g_var < gyro_thresh and a_var < accel_thresh
```

When `is_stationary` fires for long enough, update the bias estimate (an exponential moving average toward the new stationary mean works well, so a single noisy stationary patch doesn't yank the bias). This keeps the calibration *fresh* — the bias tracks temperature drift instead of going stale after boot — and it's the difference between an IMU that's calibrated *once* and one that stays calibrated. It's a stretch goal this week and a building block of the more sophisticated estimators in Phase 2, but the concept matters now: **calibration is not a one-time event; the best systems recalibrate continuously whenever the world hands them a known reference (a standstill).** That's the same theme as gravity bounding roll/pitch — exploit every free reference you get.

The caution: a *false* stationary detection (the robot is creeping slowly and you call it still) corrupts the bias with real motion, exactly the failure mode from the bias-subtraction section. Tune the thresholds conservatively — better to miss a stationary interval than to recalibrate on motion. When in doubt, gate ZUPT on an independent signal (zero `/cmd_vel` *and* low IMU variance), not on the IMU variance alone.

---

## Part 6 — Where this sits in the bigger estimation picture

It's worth a paragraph to place this week's work in the arc, because IMU calibration is rarely an end in itself — it's the *input conditioning* for everything that estimates pose.

This week you produced a calibrated IMU stream with honest covariance. **You did not produce a pose estimate.** That's deliberate. An IMU alone cannot give a bounded pose (the drift is unfixable by calibration — you only minimized it and quantified the residual). The *fusion* that turns this conditioned IMU into a bounded estimate is Week 10's job, and it works precisely because you handed it (a) data with the gross bias removed, so the EKF's job is small corrections rather than fighting a ramp, and (b) an honest covariance, so the EKF knows exactly how much to trust the IMU versus the wheels.

Think of the relationship as a contract. The IMU's side of the contract is: "I will publish rates with my best-effort bias removed, stamped at acquisition, with a covariance that honestly states my residual noise." The EKF's side is: "Given honest inputs, I will produce the optimal bounded estimate." Break the IMU's side — ship a stale bias, a publish-time stamp, or a fabricated covariance — and the EKF, which trusts you completely, produces a confidently wrong estimate. **The discipline of this week is the discipline of honoring that contract.** Every later sensor (LiDAR, camera, GPS) joins the same fusion under the same contract, and the habits you build calibrating the IMU — characterize, condition, state-the-uncertainty — are the habits you'll apply to all of them.

So when the work this week feels like a lot of careful bookkeeping for "just the IMU," remember: you're not calibrating one sensor, you're learning the *posture* every sensor must adopt to be trustworthy in a fused estimate. That posture is the whole of Phase 2.

---

## 5. Recap

You should now be able to:

- Integrate body-frame angular velocity into orientation with the exponential-map quaternion integrator, reusing `crunch_rotations`.
- Explain why even calibrated integration drifts (residual random walk + bias instability) and why that's acceptable given downstream fusion.
- Build a `rclpy` node that estimates the stationary bias, subtracts it, preserves the header, and re-publishes a calibrated IMU.
- Handle the gravity-removal frame trap and the "must actually be stationary" pitfall.
- Measure the drift-reduction factor and read a ~1× factor as a failed calibration.
- Populate the `sensor_msgs/Imu` covariance fields from Allan noise densities, including the `-1` orientation-unknown convention.

Next: the exercises put the Allan plot and the bias node on your own data. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *Quaternion kinematics for the error-state Kalman filter* (Solà) — `q̇ = ½ q ⊗ (0,ω)` and integration: <https://arxiv.org/abs/1711.02508>
- *Kalibr IMU noise model* — noise density → discrete covariance: <https://github.com/ethz-asl/kalibr/wiki/IMU-Noise-Model>
- *`sensor_msgs/Imu`* — covariance layout and the `-1` convention: <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/Imu.html>
- *`imu_tools` (Madgwick/complementary filters)*: <https://github.com/CCNYRoboticsLab/imu_tools>
- *robot_localization — preparing sensor data* (covariance expectations): <https://docs.ros.org/en/melodic/api/robot_localization/html/preparing_sensor_data.html>
- *REP 145 — IMU driver conventions*: <https://www.ros.org/reps/rep-0145.html>
