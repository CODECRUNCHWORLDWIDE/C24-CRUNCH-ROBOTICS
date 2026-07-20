# Week 42 — Resources

Everything here is free or open-source. ROS2 docs are open. The `robot_localization`, `allan_variance_ros`, and GTSAM repos are public. The two paywalled textbooks (Barfoot, Thrun) are linked for reference but every technique this week is also covered by a free source listed below. No resource is required reading unless marked **Required**.

## Required reading (work it into your week)

- **`robot_localization` — Preparing Your Data** (the page everyone skips and then regrets):
  <https://docs.ros.org/en/jazzy/p/robot_localization/preparing_sensor_data.html>
  The covariance, frame, and sign conventions your real sensors must satisfy before the EKF will behave. Read it before integration day, not after.
- **`robot_localization` — Configuring** — the parameter reference for `ekf_node`:
  <https://docs.ros.org/en/jazzy/p/robot_localization/configuring_robot_localization.html>
  `process_noise_covariance`, the per-sensor `_config` masks, `differential`, `relative`, `two_d_mode`, `transform_timeout`. This is the page you re-tune from on Tuesday.
- **ROS2 Jazzy — Managed (Lifecycle) Nodes**:
  <https://docs.ros.org/en/jazzy/Tutorials/Demos/Managed-Nodes.html>
  The `unconfigured → inactive → active` state machine your Path B launch graph is built on.
- **ROS2 Jazzy — Launch event handlers**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Using-Event-Handlers.html>
  `RegisterEventHandler`, `OnProcessStart`, `OnStateTransition`. The ordering primitives for a deterministic cold boot.

## Sensor noise and the Allan deviation

- **`allan_variance_ros`** (ori-drs, Oxford Dynamic Robot Systems) — the de-facto open tool for computing IMU Allan deviation from a `rosbag2`:
  <https://github.com/ori-drs/allan_variance_ros>
  Outputs the random-walk and bias-instability coefficients in the exact units `robot_localization` and Kalibr want.
- **VectorNav — "IMU Specifications in Detail"** — the clearest free explanation of what each datasheet noise term means physically:
  <https://www.vectornav.com/resources/inertial-navigation-primer/specifications--and--error-budgets/specs-imuspecs>
- **IEEE Std 952-2020** (referenced, not linked-for-free) — the standard that defines the Allan-variance method for inertial sensors. Know it exists; the `allan_variance_ros` README cites it.
- **El-Sheimy, Hou, Niu — "Analysis and Modeling of Inertial Sensors Using Allan Variance"** (IEEE TIM, 2008) — the canonical tutorial paper; a free PDF circulates from several university course pages. Search the title.

## State estimation references

- **Barfoot — *State Estimation for Robotics*** (Cambridge). The author hosts a **free PDF** of the full book:
  <http://asrl.utias.utoronto.ca/~tdb/bib/barfoot_ser_17.pdf>
  Chapter 3 (linear-Gaussian estimation) and Chapter 4 (nonlinear) are the theory behind your EKF re-tune.
- **GTSAM — fixed-lag smoothing**:
  <https://github.com/borglab/gtsam/tree/develop/gtsam_unstable/nonlinear>
  For the stretch goal: a `BatchFixedLagSmoother` you can run alongside the EKF on the same bag.
- **Thrun, Burgard, Fox — *Probabilistic Robotics*** (MIT Press; reference). Chapter 3 (Gaussian filters) is the standard treatment of the EKF predict/update split you are re-tuning.

## Timestamps, time, and TF

- **ROS2 Jazzy — Time and `use_sim_time`**:
  <https://design.ros2.org/articles/clock_and_time.html>
  Why a node that reads `now()` instead of the message header stamp will lie to your EKF.
- **`tf2` — debugging and `tf2_monitor`**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html>
  `ros2 run tf2_ros tf2_monitor` prints per-transform delay — the fastest way to catch the timestamp lag that wrecks drift.

## Actuators, drivers, and CAN

- **ros2_control — Jazzy**:
  <https://control.ros.org/jazzy/index.html>
  The hardware-interface and controller-manager framework most real bases use. The `ros2_control` update loop period is one of the latencies you measure this week.
- **ODrive ROS2 driver**:
  <https://github.com/odriverobotics/ros_odrive>
  A representative real motor-controller driver; its CAN transport is a realistic source of the actuator delay you characterize.

## Lifecycle, launch, and systemd

- **ROS2 Jazzy — Creating a launch file**:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Creating-Launch-Files.html>
- **Nav2 — Lifecycle and Bringup**:
  <https://docs.nav2.org/configuration/packages/configuring-lifecycle.html>
  How a production navigation stack sequences its lifecycle nodes — the pattern to copy for Path B.
- **`robot_upstart` / systemd for ROS2**:
  <https://github.com/clearpathrobotics/robot_upstart>
  Clearpath's generator for systemd units that bring a ROS2 graph up on boot. Even if you write the unit by hand, read how they handle ordering and the `network-online.target` dependency.
- **systemd `Type=notify` and `WatchdogSec`** — the freedesktop man page:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>
  The mechanism that lets your launch wrapper tell systemd "I am actually ready," which is what makes a cold-boot time *measurable* rather than guessed.

## Telemetry and diagnostics

- **`diagnostics` / `diagnostic_updater` (Jazzy)**:
  <https://github.com/ros/diagnostics>
  `DiagnosticArray`, `diagnostic_updater`, and `diagnostic_aggregator` — the standard ROS2 way to publish node and sensor health. Your heartbeat aggregator builds on it.
- **`topic_tools` and `ros2 topic hz`**:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html>
  The CLI rate check you script into your bring-up health check.
- **Foxglove (preview for Week 43)**:
  <https://foxglove.dev/docs>
  Linked now so you know where the heartbeat topic is headed. Do not build the dashboard this week.

## Sim-to-real (2026)

- **NVIDIA Isaac Sim 4.x — sim-to-real domain randomization**:
  <https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/index.html>
  If you ran domain randomization in the earlier weeks, this is the current (2026) reference for it.
- **Gz Sim (Harmonic / Ionic) sensor noise models**:
  <https://gazebosim.org/docs>
  The `<noise>` SDF tags you set in sim — the thing this week proves were optimistic.
- **"Sim-to-Real Transfer in Robotics" — a living survey** (arXiv, updated through 2025): search arXiv for the latest revision of *"A Survey on Sim-to-Real Transfer for Deep Reinforcement Learning in Robotics."* Read the section on the reality gap in dynamics, which is exactly your actuator-latency problem.

## Tools you'll use this week

- **`ros2 bag` (rosbag2)** — record the static IMU bag, the trajectory run, and the cold boot. `ros2 bag record -a` then `ros2 bag info`.
- **`tf2_monitor`, `tf2_echo`** — TF health and delay.
- **`ros2 topic hz` / `ros2 topic delay`** — per-topic rate and end-to-end delay.
- **`ros2 lifecycle` CLI** — `ros2 lifecycle get`, `set`, `list` for driving managed nodes by hand during bring-up.
- **NumPy + Matplotlib** — for the Allan-deviation plot and the drift plot.
- **`systemd-analyze` / `journalctl`** — for the cold-boot timeline on Path B.

## Videos (free, no signup)

- **"ROS2 Lifecycle Nodes Explained"** — official ROSCon talk archive on the OSRF / Open Robotics YouTube channel:
  <https://www.youtube.com/@OpenRoboticsOrg>
  (If a specific link rots, search "ROSCon lifecycle nodes" on that channel.)
- **"Tuning robot_localization"** — the maintainer (Tom Moore) has given this talk several times at ROSCon; the slides and recordings are linked from the package docs above.

## Open-source projects to read this week

You learn more from one hour reading a real bring-up than from three tutorials. Pick one:

- **`linorobot2`** — a complete, readable ROS2 differential-drive bring-up (URDF, `ros2_control`, `robot_localization`, Nav2):
  <https://github.com/linorobot/linorobot2>
- **`turtlebot4` robot bringup** — Clearpath's production-quality launch graph and systemd integration:
  <https://github.com/turtlebot/turtlebot4>
- **`nav2_bringup`** — how the Nav2 team sequences lifecycle nodes and gates readiness:
  <https://github.com/ros-navigation/navigation2/tree/main/nav2_bringup>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Allan deviation** | A plot of sensor noise vs. averaging time; its slopes give you random-walk and bias-instability coefficients. |
| **Bias instability** | The slowly-wandering DC offset of a real sensor that no amount of averaging removes. The flat bottom of the Allan curve. |
| **Random walk** | The integrated white noise that makes an IMU's integrated angle/velocity drift; the −1/2-slope part of the Allan curve. |
| **Dead time** | The delay between commanding an actuator and the first observable motion. |
| **Transport delay** | Latency added by the bus (CAN, Ethernet) and the controller's own loop, on top of dead time. |
| **`process_noise_covariance` (Q)** | How much you let the EKF's prediction drift between measurements. The main knob you re-tune for real data. |
| **`use_sim_time`** | A node parameter; when true the node reads the `/clock` topic instead of the wall clock. Must be `false` on real hardware. |
| **Lifecycle node** | A ROS2 node with an explicit `configure/activate/deactivate/cleanup` state machine, so a launch graph can sequence and gate it. |
| **Cold boot** | Power-on to "ready to accept a goal," with nothing pre-warmed. The Path B metric. |
| **Terminal drift** | The distance between where the fused estimate *says* the robot ended and where it *actually* ended. The Path A metric. |
| **Heartbeat** | A periodic aggregate-health message an operator dashboard subscribes to. |

---

*If a link 404s, please open an issue so we can replace it.*
