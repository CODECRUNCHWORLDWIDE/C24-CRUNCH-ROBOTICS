# Week 9 — Resources

Every resource here is **free** and, where versioned, pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04). The IMU error-model and Allan-variance references are open standards (IEEE), free tools, or vendor datasheets. No paywalled books are linked.

## Required reading (work it into your week)

- **`sensor_msgs/Imu` message definition** — the message you calibrate; note the three `*_covariance` 3×3 arrays:
  <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/Imu.html>
- **`imu_tools` (`imu_filter_madgwick`, `imu_complementary_filter`)** — the standard ROS2 IMU filtering stack; read how it expects calibrated input:
  <https://github.com/CCNYRoboticsLab/imu_tools>
- **REP 145 — Conventions for IMU sensor drivers** — frame, units, and what a well-behaved IMU driver publishes:
  <https://www.ros.org/reps/rep-0145.html>
- **`allan_variance_ros`** — the de-facto ROS tool for computing IMU Allan variance from a bag; read its README for the parameter outputs you'll reproduce by hand:
  <https://github.com/ori-drs/allan_variance_ros>

## Allan variance and IMU noise (the heart of the week)

- **Vectornav — "IMU Specifications Explained"** — the clearest free explainer of noise density, bias instability, and random walk, with the Allan plot annotated:
  <https://www.vectornav.com/resources/inertial-navigation-primer/specifications--and--error-budgets/specs-imuspecs>
- **IEEE Std 952 / 647 (gyro & accel noise terminology)** — the standard that defines angle random walk, bias instability, and rate random walk; skim the terminology section. (Search "IEEE 952 Allan variance gyroscope".)
- **"An introduction to inertial navigation" (Woodman, Cambridge TR-696)** — a free, readable technical report on IMU error propagation and why double-integration of accel diverges:
  <https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-696.pdf>
- **Kalibr IMU noise model wiki** — the canonical statement of the continuous-time noise-density vs. discrete-time relationship you'll use to fill in covariance:
  <https://github.com/ethz-asl/kalibr/wiki/IMU-Noise-Model>

## Sensor datasheets (read at least one)

- **Bosch BNO085 / BNO055 datasheet** — the IMU on many Crunch Path-A builds; find its gyro noise density and zero-rate offset and compare to your measured Allan numbers:
  search "BNO085 datasheet" on the Bosch Sensortec / CEVA / Adafruit pages.
- **TDK/InvenSense ICM-20948 / MPU-9250 datasheet** — common alternative 9-DOF IMU; same exercise.

## API references (the ones you'll have open all week)

- **`rclpy` API reference** — `Node`, `create_subscription`, `create_publisher`:
  <https://docs.ros.org/en/jazzy/p/rclpy/>
- **`sensor_msgs/Imu`** — fields and covariance layout (row-major 3×3, `-1` in `[0]` means "unknown"):
  <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/Imu.html>
- **NumPy** Allan-variance building blocks: `numpy.cumsum`, `numpy.var`, log-spaced `numpy.logspace`:
  <https://numpy.org/doc/stable/>

## Tools you'll use this week

- **`ros2 bag record /imu/data`** — record your 30-minute stationary log (use `--qos-profile-overrides-path` if your IMU is `BEST_EFFORT`, per Week 5).
- **`ros2 topic echo /imu/data --field angular_velocity`** — sanity-check the raw stream.
- **`ros2 topic hz /imu/data`** — confirm the rate; you need it to convert Allan τ to samples.
- **Matplotlib** — the log-log Allan deviation plot. `pip install matplotlib`.
- **`allan_variance_ros`** — the reference tool to check your hand computation against (stretch).
- **PlotJuggler** — `ros2 run plotjuggler plotjuggler` — to watch raw vs. calibrated angular velocity side by side.

## Talks worth your time (free, no signup)

- **Cyrill Stachniss — "Sensors and State Estimation" lectures (Uni Bonn)** — free YouTube series; the IMU-modeling and Allan-variance lecture is exactly this week at a graduate level:
  <https://www.ipb.uni-bonn.de/sensors-state-estimation/>
- **ROSCon state-estimation sessions** — the OSRF archive; search for `robot_localization` and IMU-calibration talks:
  <https://roscon.ros.org/>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **IMU** | Inertial Measurement Unit — gyroscope (angular rate) + accelerometer (specific force), often + magnetometer. |
| **Bias** | A (slowly varying) constant offset added to the true signal; the dominant integrable error. |
| **Zero-rate offset (ZRO)** | The gyroscope's bias — what it reads when truly stationary. |
| **Scale factor** | A multiplicative gain error: `meas = (1+s)·true`. |
| **Misalignment** | Cross-axis coupling: the sensor axes aren't perfectly orthogonal/aligned to the body frame. |
| **White noise** | Zero-mean, uncorrelated sample-to-sample noise; the high-frequency jitter. |
| **Allan variance / deviation** | A time-domain statistic vs. averaging time τ that separates noise types by their slope on a log-log plot. |
| **Angle random walk (ARW)** | Gyro white-noise integrated into angle; the −½ slope; units °/√h or rad/√s. |
| **Velocity random walk (VRW)** | Accel white-noise integrated into velocity; the accel analogue of ARW. |
| **Bias instability** | The flat floor of the Allan plot; the lowest noise you can average down to before bias drift dominates. |
| **Rate random walk (RRW)** | The +½ slope; slow random drift of the bias itself. |
| **Noise density** | White-noise spectral density; the parameter `robot_localization`/Kalibr wants (per √Hz). |
| **Dead reckoning** | Estimating pose by integrating motion alone, with no external reference; drifts unboundedly. |
| **ZUPT** | Zero-velocity update — using detected stationary intervals to re-estimate bias / reset velocity. |
| **Covariance** | The estimator's stated uncertainty; the `*_covariance` fields of `sensor_msgs/Imu`. |

---

*If a link 404s, please open an issue so we can replace it.*
