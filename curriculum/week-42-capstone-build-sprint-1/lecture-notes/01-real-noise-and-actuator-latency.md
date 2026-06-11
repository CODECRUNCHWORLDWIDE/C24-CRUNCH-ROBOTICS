# Lecture 1 — Real Sensor Noise, Real Actuator Latency, and Re-Tuning the Estimator

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain how the noise a real sensor emits differs from the noise you simulated, compute an Allan deviation from a static `rosbag2`, measure command-to-motion actuator latency, and re-tune your `robot_localization` EKF for *measured* characteristics instead of guessed ones.

If you only remember one thing from this lecture, remember this:

> **In simulation you chose the noise. On hardware the noise chooses you.** Your sim noise was white, zero-mean, and exactly the standard deviation you typed into the SDF. Real noise is biased, correlated, quantized, occasionally missing, and timestamped slightly wrong. Every one of those four words is a separate failure mode your EKF has never seen.

---

## 1. The lie simulation told you

When you set up your robot in Gz Sim (or Isaac Sim) back in the sim-to-real weeks, your IMU noise looked like this in the SDF:

```xml
<sensor name="imu_sensor" type="imu">
  <imu>
    <angular_velocity>
      <x>
        <noise type="gaussian">
          <mean>0.0</mean>
          <stddev>0.0002</stddev>
          <bias_mean>0.0000075</bias_mean>
          <bias_stddev>0.0000008</bias_stddev>
        </noise>
      </x>
      <!-- y, z similar -->
    </angular_velocity>
  </imu>
</sensor>
```

That is a *generative model*. The simulator draws a fresh sample from `N(mean, stddev²)` every step, adds a slowly-walking bias, and hands you a clean measurement. It is white, it is Gaussian, and it is exactly stationary. Your EKF was tuned against it and your EKF loved it, because your EKF's entire mathematical foundation *assumes* white, zero-mean, Gaussian measurement noise with a known covariance. In sim, that assumption is literally true by construction.

Now plug in a real BMI088 or MPU-9250. Here is what actually comes out, none of which the SDF model captured:

1. **Bias instability.** The gyro's zero-rate output is not a constant you can calibrate out once. It *wanders* — over seconds to minutes, with a magnitude that does not shrink no matter how long you average. This is the single biggest contributor to heading drift, and it is the term the SDF's single `bias_stddev` number does not model.
2. **Random walk (angle/velocity).** Integrate white noise and you get a random walk; integrate a rate gyro's white noise and your *heading* random-walks. Over a 20-meter trajectory at, say, 0.3 m/s — about 67 seconds — even a good MEMS gyro accumulates noticeable heading error from random walk alone.
3. **Quantization.** A real sensor reports through a finite-width ADC. At small motions you see *steps*, not a smooth signal. Your sim emitted `float64` to the last bit.
4. **Axis misalignment and scale-factor error.** The chip's axes are not perfectly orthogonal to your robot frame, and a commanded 1.000 rad/s reads as 0.993 rad/s. Sim axes were perfect.
5. **Temperature drift.** Bias and scale factor both move with die temperature. The first ten minutes after power-on, while the board warms up, are the *worst* ten minutes, and they are exactly when you do your bring-up.
6. **Saturation and clipping.** Spin fast enough and a real gyro rails at its full-scale range. Sim happily reported 50 rad/s.
7. **Dropout and timestamp jitter.** Real drivers occasionally miss a sample, deliver two in a burst, or stamp a message with the *arrival* time instead of the *capture* time. We treat this in §4 because it is the most damaging and the least obvious.

The same story holds for every sensor. Wheel odometry has slip, quantized encoder ticks, and a wheelbase you measured with a tape and got wrong by 4 mm. LiDAR has range-dependent noise, intensity-dependent dropout on dark surfaces, and motion distortion if you do not de-skew. The depth camera has a flying-pixel problem at depth discontinuities and a bias that grows with the square of range. **None of this is in your sim.** That is fine — sim is for building the stack. This week is for measuring the gap.

---

## 2. The Allan deviation: the one plot you must compute

The datasheet gives you a "gyro noise density" number and an "in-run bias stability" number and calls it a day. Those two numbers are *exactly* the two coefficients your EKF wants — but datasheet numbers are typical-part, room-temperature, marketing-reviewed values. The honest move is to compute them yourself from *your* IMU on *your* board, and the tool for that is the **Allan deviation**.

The idea is simple. Record the sensor sitting perfectly still for a long time (an hour is the standard; 30 minutes is the floor). Now ask: if I average the signal over a window of length τ, how much does that average wander from one window to the next? Plot that wandering (the Allan deviation, σ(τ)) against τ on log-log axes and you get a characteristic curve:

```
 σ(τ)
  │
  │  *                                    slope +1/2: rate ramp
  │   *                              *     (and other long-term terms)
  │    *                        *
  │     *                  *
  │  -1/2 *           *
  │ slope  *      *  ← flat bottom: bias instability
  │  (white  *  *      (read B here; multiply by ~0.664)
  │   noise)  **
  └──────────────────────────────────────────── τ (s, log scale)
         0.1    1    10    100    1000
```

Two readings matter:

- **The −1/2 slope on the left** is dominated by white noise. Read σ at τ = 1 s and that value (in rad/s for a gyro) is your **angle random walk** coefficient, which feeds the gyro's *measurement* noise.
- **The flat bottom** is the **bias instability** B. The minimum of the curve, multiplied by the scaling constant 0.664, gives B in the gyro's units. This feeds the *process* noise of any bias state you estimate — or, if you do not estimate bias explicitly, it tells you how much heading drift you have *no way to remove* and therefore how much you must inflate `process_noise_covariance` to stay consistent.

You can compute this with the open `allan_variance_ros` package, and you should — but write the 30-line version yourself once so the plot is not a black box. Record the bag first:

```bash
# Robot powered, perfectly still, on a solid surface. Let it warm up 10 min first.
ros2 bag record -o imu_static_1hr /imu/data_raw --max-bag-duration 0
# ... wait an hour, then Ctrl-C.
ros2 bag info imu_static_1hr
```

Then the math, in NumPy, using the overlapping-Allan-variance estimator:

```python
#!/usr/bin/env python3
"""allan.py - overlapping Allan deviation for one IMU axis from a flat array.

Feed it the gyro-x samples (rad/s) and the sample rate. Returns (taus, sigmas).
This is the same estimator allan_variance_ros uses; we write it out so the
plot is not a black box.
"""
import numpy as np


def allan_deviation(samples: np.ndarray, fs: float, num_taus: int = 50):
    """Overlapping Allan deviation.

    Args:
        samples: 1-D array of sensor readings (e.g. gyro-x in rad/s).
        fs:      sample rate in Hz.
        num_taus: number of averaging times to evaluate (log-spaced).

    Returns:
        (taus, sigmas): averaging times (s) and Allan deviations (same unit
        as samples).
    """
    n = len(samples)
    # theta = integrated angle (rad), the cumulative sum of rate / fs.
    theta = np.cumsum(samples) / fs

    # m = cluster size in samples; log-spaced from 1 to n//3.
    max_m = (n - 1) // 3
    ms = np.unique(np.floor(np.logspace(0, np.log10(max_m), num_taus)).astype(int))
    taus = ms / fs

    sigmas = np.empty_like(taus, dtype=float)
    for i, m in enumerate(ms):
        # Overlapping estimator: differences of theta separated by 2m, 1 step apart.
        d = theta[2 * m:] - 2.0 * theta[m:-m] + theta[:-2 * m]
        sigmas[i] = np.sqrt(np.mean(d ** 2) / (2.0 * (m / fs) ** 2))
    return taus, sigmas


if __name__ == "__main__":
    import sys
    import matplotlib.pyplot as plt

    # Load gyro-x samples extracted from the bag (one float per line).
    gyro_x = np.loadtxt(sys.argv[1])
    fs = float(sys.argv[2]) if len(sys.argv) > 2 else 200.0

    taus, sigmas = allan_deviation(gyro_x, fs)

    # Angle random walk N: read sigma at tau = 1 s, it lies on the -1/2 line.
    idx1 = int(np.argmin(np.abs(taus - 1.0)))
    arw = sigmas[idx1]  # rad/s at 1 s -> rad/sqrt(s) when scaled by sqrt(tau)=1
    # Bias instability B: minimum of the curve times 0.664.
    bias_instability = sigmas.min() * 0.664

    print(f"angle random walk   N ~= {arw:.3e} rad/s   (sigma at tau=1s)")
    print(f"bias instability    B ~= {bias_instability:.3e} rad/s")

    plt.loglog(taus, sigmas, "o-")
    plt.axhline(bias_instability / 0.664, ls="--", color="gray",
                label=f"B floor ~ {bias_instability:.2e}")
    plt.xlabel("averaging time tau (s)")
    plt.ylabel("Allan deviation sigma(tau) (rad/s)")
    plt.title("Gyro X Allan deviation")
    plt.grid(True, which="both", ls=":")
    plt.legend()
    plt.savefig("allan_gyro_x.png", dpi=130)
    print("wrote allan_gyro_x.png")
```

To get `gyro_x` out of the bag in Jazzy, the rosbag2 Python API reads it directly:

```python
#!/usr/bin/env python3
"""extract_gyro.py - pull gyro-x out of a rosbag2 of sensor_msgs/Imu."""
import sys
import numpy as np
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Imu


def read_gyro_x(bag_uri: str, topic: str = "/imu/data_raw") -> np.ndarray:
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=bag_uri, storage_id="mcap"),
        ConverterOptions(input_serialization_format="cdr",
                         output_serialization_format="cdr"),
    )
    values = []
    while reader.has_next():
        tname, data, _stamp = reader.read_next()
        if tname != topic:
            continue
        msg = deserialize_message(data, Imu)
        values.append(msg.angular_velocity.x)
    return np.asarray(values, dtype=float)


if __name__ == "__main__":
    arr = read_gyro_x(sys.argv[1])
    np.savetxt("gyro_x.txt", arr)
    print(f"extracted {len(arr)} samples -> gyro_x.txt")
```

Run them, read the two numbers off the plot, and write them down. You will use them in §5. If your computed angle random walk is within a factor of two of the datasheet's noise density (converted to the same units), your IMU is healthy. If it is ten times worse, you have a mechanical or EMI problem — a loose mount, a switching regulator next to the chip — and you should fix *that* before you touch the EKF.

---

## 3. Real actuator latency: dead time, ramps, and transport delay

Your controller — Nav2's regulated pure pursuit, MPPI, or your own — publishes `geometry_msgs/Twist` on `/cmd_vel` and *assumes the robot starts moving at that velocity immediately*. In sim, it does. On hardware, between your `cmd_vel` and the wheels actually turning, there is:

1. **Driver dispatch**: the ROS2 node receives the `Twist`, converts to per-wheel setpoints, and writes to the bus. Sub-millisecond, but real.
2. **Transport delay**: the setpoint travels over CAN (or USB-serial, or EtherCAT) to the motor controller. On a busy CAN bus at 500 kbps, this is several milliseconds and *jittery*.
3. **Controller loop latency**: the motor controller runs its own current/velocity loop at, say, 8 kHz, but only updates its setpoint when the new command arrives — up to one loop period of latency, plus the loop's own rise time.
4. **Mechanical dead time**: backlash, belt slack, and static friction mean the wheel does not move until commanded torque exceeds stiction. This is *dead time* — pure delay with no output at all.
5. **Velocity ramp**: once moving, the wheel accelerates toward the setpoint with a first-order (roughly) response governed by motor torque and robot inertia. This is the *time constant* τ.

The whole path is well-modeled as **dead time + first-order lag**: a pure delay `Td` followed by an exponential approach with time constant `τ`. You measure both from a step response. Command a step from 0 to 0.3 m/s, record the commanded `cmd_vel` and the *measured* velocity (from wheel odometry or the controller's velocity feedback), and align them by timestamp:

```python
#!/usr/bin/env python3
"""actuator_latency.py - estimate dead time and time constant from a step.

Subscribes to the commanded Twist and the measured odom velocity, records a
step, and fits Td (dead time) and tau (first-order time constant).

Run, then issue a single step:
    ros2 topic pub --once /cmd_vel geometry_msgs/Twist '{linear: {x: 0.3}}'
"""
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class StepRecorder(Node):
    def __init__(self):
        super().__init__("actuator_latency")
        self.cmd_t, self.cmd_v = [], []
        self.meas_t, self.meas_v = [], []
        self.create_subscription(Twist, "/cmd_vel", self._cmd_cb, 10)
        self.create_subscription(Odometry, "/odom", self._odom_cb, 50)
        self.get_logger().info("recording... publish a step to /cmd_vel, "
                               "then Ctrl-C to fit.")

    def _stamp(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _cmd_cb(self, msg: Twist):
        self.cmd_t.append(self._stamp())
        self.cmd_v.append(msg.linear.x)

    def _odom_cb(self, msg: Odometry):
        self.meas_t.append(self._stamp())
        self.meas_v.append(msg.twist.twist.linear.x)

    def fit(self):
        cmd_t = np.asarray(self.cmd_t)
        cmd_v = np.asarray(self.cmd_v)
        t = np.asarray(self.meas_t)
        v = np.asarray(self.meas_v)
        if len(cmd_t) == 0 or len(t) < 5:
            self.get_logger().warn("not enough data to fit")
            return
        # The step time is when commanded velocity first jumps above 0.05 m/s.
        step_idx = int(np.argmax(cmd_v > 0.05))
        t0 = cmd_t[step_idx]
        v_final = cmd_v[step_idx]
        # Dead time: measured velocity first exceeds 5% of the setpoint.
        moving = np.where(v > 0.05 * v_final)[0]
        if len(moving) == 0:
            self.get_logger().warn("robot never moved; check enable/E-stop")
            return
        t_move = t[moving[0]]
        dead_time = t_move - t0
        # Time constant: time from first motion to 63.2% of v_final.
        target = 0.632 * v_final
        reached = np.where(v >= target)[0]
        tau = (t[reached[0]] - t_move) if len(reached) else float("nan")
        self.get_logger().info(
            f"dead_time Td = {dead_time*1000:.1f} ms   tau = {tau*1000:.1f} ms   "
            f"v_final = {v_final:.3f} m/s")


def main():
    rclpy.init()
    node = StepRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.fit()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
```

A small differential base typically lands at `Td` of 20–60 ms and `τ` of 80–250 ms. Why does it matter for *drift*? Because your controller commanded a turn and the robot started turning 40 ms late and reached the commanded rate 150 ms later than the model assumed. Over a path with many small corrections, those mismatches integrate into position error. The fix is not always to model the delay in the controller (though MPC can); often it is enough to *know* the number so that when your terminal drift is 0.6 m you can attribute 0.2 m of it to actuator lag rather than blaming the EKF and re-tuning forever.

---

## 4. Timestamp discipline: the 40-millisecond error that becomes 2 meters

Here is the most expensive bug on integration day, and it produces *zero* warnings.

Your EKF fuses an IMU at 200 Hz and wheel odometry at 50 Hz. To fuse them correctly it must know *when each measurement was taken*, to align them on a common timeline and propagate the state between them. It reads that time from the message **header stamp** (`msg.header.stamp`). If your sensor driver fills the header with `now()` — the wall-clock time at which the driver *received and processed* the sample — instead of the time the sample was actually *captured*, every measurement carries a small, variable, positive timestamp error.

Suppose that error is 40 ms (a realistic USB + driver-processing latency). At 0.3 m/s the robot moves 12 mm in 40 ms — sounds harmless. But the EKF does not see "12 mm"; it sees a measurement that disagrees with its prediction by an amount consistent with the *wrong* time, and it corrects the state in the wrong direction. With odometry and IMU stamped *differently wrong* (different drivers, different latencies), the filter's two information sources are misaligned relative to each other, and the inconsistency compounds turn after turn. A 40 ms relative timestamp error routinely turns a 20 cm trajectory error into a 1–2 m one. This is not hyperbole; it is the single most common reason a stack that drifts 0.3 m in sim drifts 2 m on hardware.

How to catch it:

```bash
# Per-transform delay in the TF tree. Anything above ~50 ms is suspect.
ros2 run tf2_ros tf2_monitor odom base_link

# End-to-end delay on a topic: header stamp vs. arrival time.
ros2 topic delay /imu/data
ros2 topic delay /odom
```

`ros2 topic delay` prints the difference between `header.stamp` and the time the message was received. If it is large and *positive and growing*, your stamps are wall-clock-on-arrival and you have the bug. The fix lives in the driver: stamp with the hardware capture time, or at minimum subtract the measured driver latency. Many community drivers expose a `frame_id` and `use_header_stamp`-style parameter precisely for this.

Two more timestamp rules for integration day:

- **`use_sim_time` must be `false` everywhere on real hardware.** If even one node still has `use_sim_time:=true`, it reads `/clock` — which nobody is publishing — and either blocks forever waiting for time or uses time zero. Grep your launch files. This is a five-minute check that saves an hour of confusion.
- **One clock source.** If your compute and your sensor MCU each keep their own clock and you do not synchronize them (chrony/PTP for Ethernet sensors, or hardware-trigger timestamping), the two clocks drift relative to each other and you reintroduce the §4 problem through the back door. For this week, synchronizing to within a few milliseconds is enough; PTP is a Week-43-and-beyond concern.

---

## 5. Re-tuning the EKF for *measured* data

Now you have numbers: the gyro's random walk and bias instability from §2, the actuator dead time from §3, and confidence that your timestamps are clean from §4. Time to re-tune `robot_localization`.

The mistake everyone makes is to treat the EKF config they used in sim as correct and only nudge it. It is not correct — it was tuned for white Gaussian noise that no longer exists. Re-derive the two covariance families from your measurements.

**Measurement noise (R) comes from the sensors, via their published covariances.** `robot_localization` reads the covariance fields *in each message*. Your job is to make those fields honest:

- For the IMU, set the `angular_velocity_covariance` and `linear_acceleration_covariance` diagonals from your measured noise, not the driver's zeros. A gyro with angle random walk `N` rad/s has a per-sample variance of roughly `N² · fs` — but the simplest defensible move is to set the diagonal to the measured static variance of each axis (the variance of the samples in your 1-hour bag).
- For wheel odometry, the velocity covariance should reflect slip. Measure it: drive a known straight 5 m, compare odom-reported distance to tape, and inflate the variance until the EKF stops over-trusting odometry on turns.

**Process noise (Q) is the `process_noise_covariance` matrix** — the knob that says how much you let the prediction drift between measurements. This is where bias instability lands. If you do *not* estimate gyro bias as a state, you must inflate the yaw-related `process_noise_covariance` entries to account for the bias you cannot remove; the bias-instability number B tells you how much. Too small and the filter becomes overconfident and diverges on a long run; too large and it ignores your sensors and wanders. Here is a re-tuned `ekf.yaml` skeleton for a 2D differential base, annotated with *why* each value is what it is:

```yaml
# ekf.yaml - re-tuned for MEASURED sensor characteristics (Week 42).
ekf_filter_node:
  ros__parameters:
    frequency: 50.0           # match your odom rate; do not exceed your slowest critical sensor by much
    sensor_timeout: 0.1       # if a sensor is silent this long, predict-only
    two_d_mode: true          # ground robot: zero out z, roll, pitch
    publish_tf: true
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom         # ekf_local fuses to odom; a second instance does map
    transform_timeout: 0.05   # tolerate small TF lag; too large hides the timestamp bug

    # --- Wheel odometry: trust velocity, distrust absolute pose (it drifts) ---
    odom0: /odom
    odom0_config: [false, false, false,    # x, y, z position - do NOT fuse absolute, it drifts
                   false, false, false,    # roll, pitch, yaw - leave heading to the IMU
                   true,  true,  false,    # vx, vy, vz - fuse linear velocity
                   false, false, true,     # wx, wy, wz - fuse yaw rate from wheels as a check
                   false, false, false]
    odom0_differential: false
    odom0_relative: false
    odom0_queue_size: 10

    # --- IMU: trust yaw rate and yaw, distrust accel-derived position ---
    imu0: /imu/data
    imu0_config: [false, false, false,
                  false, false, true,      # yaw - fuse absolute heading (if magnetometer-corrected)
                  false, false, false,
                  false, false, true,      # yaw rate - the IMU's strongest signal
                  true,  false, false]     # ax - optional; only if your IMU accel is clean
    imu0_differential: false
    imu0_relative: true        # start heading at zero rather than the magnetometer's offset
    imu0_remove_gravitational_acceleration: true
    imu0_queue_size: 10

    # --- Process noise Q ---
    # Diagonal order: x, y, z, roll, pitch, yaw, vx, vy, vz, vroll, vpitch, vyaw, ax, ay, az
    # The yaw and vyaw entries are INFLATED relative to the sim defaults to absorb
    # the measured gyro bias instability B (see Allan-deviation step). If your run
    # over-rotates and drifts, raise yaw/vyaw; if it lags and feels sluggish, lower them.
    process_noise_covariance: [0.02, 0,    0,    0,    0,    0,     0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0.02, 0,    0,    0,    0,     0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0.01, 0,    0,    0,     0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0.01, 0,    0,     0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0.01, 0,     0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0.06,  0,    0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0.04, 0,    0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0.04, 0,    0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0.02, 0,     0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0.01,  0,     0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0,     0.01,  0,     0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0,     0,     0.08,  0,    0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0,     0,     0,     0.02, 0,    0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0,     0,     0,     0,    0.02, 0,
                               0,    0,    0,    0,    0,    0,     0,    0,    0,    0,     0,     0,     0,    0,    0.02]
```

The two entries to internalize are the yaw process noise (`0.06`, row 6) and the yaw-rate process noise (`0.08`, row 12). Those are the ones you raise to absorb bias instability and lower if the filter becomes sluggish. Everything else is comparatively forgiving on a ground robot in `two_d_mode`.

A re-tuning loop that actually converges, rather than thrashing:

1. **Record once, replay many.** Drive your trajectory once with `ros2 bag record -a`. Then re-tune offline by replaying the bag with `ros2 bag play` against the EKF. You are not re-driving the robot fifty times; you are replaying one honest dataset. This is the single most important workflow tip in this lecture.
2. **Change one thing.** Raise yaw process noise, replay, measure terminal drift. Note it. Revert. Change the next thing. Keep a table.
3. **Watch the covariance, not just the path.** Plot the trace of the EKF's covariance over the run. A healthy filter's covariance grows between measurements and shrinks at each update, staying bounded. A diverging filter's covariance grows without bound — that is your signal that Q is too large or a sensor is feeding garbage.
4. **Stop when drift is bounded and the covariance is honest.** "Bounded" means: the reported covariance at the end of the run is consistent with the *actual* terminal error you measured with the tape. An overconfident filter (small covariance, large real error) is worse than a drifting one, because downstream code will trust it.

---

## 6. Putting it together for integration day

The discipline of this lecture is a sequence, and the sequence matters:

1. Record the static IMU bag; compute the Allan deviation; write down N and B. *(Sensor characterization.)*
2. Run the step test; write down `Td` and `τ`. *(Actuator characterization.)*
3. Run `ros2 topic delay` and `tf2_monitor`; confirm stamps are honest and `use_sim_time:=false`. *(Timestamp discipline.)*
4. Set the message covariances from §2's measurements; re-tune `process_noise_covariance` from §5 against a *replayed* bag. *(Estimator re-tune.)*
5. Only now drive the live 20-meter trajectory and measure terminal drift. *(The result.)*

Skip any step and you will spend integration day chasing a symptom whose cause you never measured. The engineers who finish this week early are not faster typists — they are the ones who measured before they tuned. The estimator cannot be better than the data you feed it, and the data is exactly as good as your characterization of it.

In Lecture 2 we take this characterized, re-tuned stack and either bring it up on real hardware end to end (Path A) or harden it into a production deployment that cold-boots deterministically (Path B). The numbers you wrote down here are the inputs to both.

---

## Key takeaways

- **Simulated noise is white Gaussian by construction; real noise is biased, correlated, quantized, and occasionally missing.** Your EKF was tuned for the former and must be re-tuned for the latter.
- **Compute the Allan deviation yourself.** It gives you the angle random walk (white-noise term) and bias instability (the un-removable drift), which are the exact coefficients the EKF wants.
- **Real actuators have dead time + a velocity ramp + transport delay.** Measure `Td` and `τ` from a step so you can attribute drift correctly instead of blaming the filter.
- **A 40 ms timestamp error becomes meters of drift.** Stamp with capture time, run `ros2 topic delay`, and set `use_sim_time:=false` everywhere on hardware.
- **Re-tune against a replayed bag, change one thing at a time, and watch the covariance trace, not just the path.** Stop when drift is bounded *and* the reported covariance is honest about it.
