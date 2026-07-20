# Week 10 — Resources

Every resource here is **free** and, where versioned, pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04). The `robot_localization` package is open source; the Kalman-filter references are free courseware, open books, or canonical papers; the REPs are public. No paywalled books are linked.

## Required reading (work it into your week)

- **`robot_localization` documentation** — the canonical reference for `ekf_node`, the config matrices, and the frames:
  <https://docs.ros.org/en/melodic/api/robot_localization/html/index.html>
  (The concepts are distro-stable; the package on Jazzy is `ros-jazzy-robot-localization`.)
- **`robot_localization` — Preparing your sensor data** — the single most important page: what covariance and frames the EKF expects from odom and IMU:
  <https://docs.ros.org/en/melodic/api/robot_localization/html/preparing_sensor_data.html>
- **`robot_localization` — Configuring `ekf_node`** — every parameter, including the 15-element boolean `_config` matrices and `two_d_mode`:
  <https://docs.ros.org/en/melodic/api/robot_localization/html/state_estimation_nodes.html>
- **REP 105 — Coordinate Frames for Mobile Platforms** — `map → odom → base_link`, who publishes what, the LTS source of truth:
  <https://www.ros.org/reps/rep-0105.html>

## Kalman filter and EKF (the heart of the week)

- **"Kalman and Bayesian Filters in Python" (Roger Labbe)** — the best free, interactive, code-first KF/EKF book; chapters 4–11 are exactly this week:
  <https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python>
- **Probabilistic Robotics (Thrun, Burgard, Fox), Ch. 3** — the rigorous derivation of the Bayes filter, KF, and EKF; the field's standard text (a free PDF circulates from the authors' course pages):
  search "Probabilistic Robotics Thrun chapter 3 pdf".
- **Cyrill Stachniss — "Kalman Filter & EKF" lecture (Uni Bonn)** — free YouTube; the clearest 90-minute derivation of predict/update and linearization:
  <https://www.ipb.uni-bonn.de/sensors-state-estimation/>
- **"How a Kalman filter works, in pictures" (Bzarg)** — the famous visual intuition for the covariance update:
  <https://www.bzarg.com/p/how-a-kalman-filter-works-in-pictures/>

## API references (the ones you'll have open all week)

- **`nav_msgs/Odometry`** — the wheel-odom message; note the 6×6 pose and twist covariances (row-major):
  <https://docs.ros.org/en/jazzy/p/nav_msgs/msg/Odometry.html>
- **`sensor_msgs/Imu`** — the IMU message and its 3×3 covariances (the `-1` orientation convention from Week 9):
  <https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/Imu.html>
- **`geometry_msgs/TransformStamped` / tf2** — what the EKF broadcasts for `odom→base_link`:
  <https://docs.ros.org/en/jazzy/p/geometry_msgs/msg/TransformStamped.html>

## Tools you'll use this week

- **`ros2 run tf2_tools view_frames`** — generate the TF tree PDF; confirm the EKF owns `odom→base_link` and nobody else does.
- **`ros2 topic echo /odometry/filtered`** — the fused output; watch the pose and its covariance.
- **`ros2 topic echo /odom --field pose.covariance`** — confirm your wheel odom states an honest covariance (a 6×6 of zeros is a lie the EKF will choke on).
- **PlotJuggler** — `ros2 run plotjuggler plotjuggler` — plot raw `/odom` vs fused `/odometry/filtered` x/y to *see* the drift difference.
- **`ros2 launch robot_localization ...`** — the standard way to bring up `ekf_node` with a YAML.
- **`ros2 param dump /ekf_filter_node`** — read back the live EKF config to confirm what's actually loaded.

## Talks worth your time (free, no signup)

- **Tom Moore — "`robot_localization`" ROSCon talk** — by the package's author; the definitive "how to configure it without footguns" session, free in the OSRF archive:
  <https://roscon.ros.org/>
- **ROSCon state-estimation track** — search the archive for EKF/UKF and Nav2-localization deep-dives.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **State `x`** | The quantities the filter estimates (here: pose + velocity + accel, up to 15 of them). |
| **Belief** | The filter's estimate plus its covariance — a Gaussian over the state. |
| **Predict step** | Push the state forward through the motion model; covariance *grows* (uncertainty added). |
| **Update step** | Correct the prediction with a measurement; covariance *shrinks* (information added). |
| **`F`** | The state-transition (motion-model) matrix / Jacobian of `f`. |
| **`H`** | The measurement matrix / Jacobian of `h` — maps state to what a sensor sees. |
| **`Q`** | Process-noise covariance — how much you trust the motion model. |
| **`R`** | Measurement-noise covariance — how much you trust the sensor (its reported covariance). |
| **`P`** | The state covariance — the filter's stated uncertainty. |
| **Innovation** | `z − H x̂⁻`, the measurement minus the prediction; the "surprise." |
| **Kalman gain `K`** | The optimal blend factor between prediction and measurement, set entirely by covariances. |
| **EKF** | Extended Kalman Filter — KF with nonlinear `f`/`h` linearized via Jacobians each step. |
| **`ekf_node`** | `robot_localization`'s EKF node. |
| **`_config` matrix** | The 15-boolean grid per input selecting which state fields that sensor fuses. |
| **`two_d_mode`** | EKF flag that zeros z, roll, pitch — correct for planar ground robots. |
| **REP 105** | The `map → odom → base_link` frame convention. |
| **`/odometry/filtered`** | The EKF's fused output odometry topic. |

---

*If a link 404s, please open an issue so we can replace it.*
