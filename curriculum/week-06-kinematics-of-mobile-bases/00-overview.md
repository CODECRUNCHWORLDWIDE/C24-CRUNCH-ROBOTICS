# Week 6 — Kinematics of Mobile Bases

Welcome to **C24 · Crunch Robotics**, Week 6. Week 1 gave you the rigid-body math and `SE(3)`. Week 2 built your TF tree. Week 3 turned a URDF into a robot in Gz Sim. Week 4 taught you actions, lifecycle, and executors. Week 5 made you fluent in QoS and DDS so your topics actually flow. This week we finally answer the question that every wheeled robot has to answer about *itself*: **"Where am I, and how do I know?"**

The honest answer — the one you will spend the next ten weeks learning to live with — is *"I think I'm here, plus or minus a growing error I can't observe directly."* That is odometry. By Friday you will have derived differential-drive forward kinematics from first principles, written an `rclpy` node that consumes `/joint_states` and publishes `/odom` plus the `odom → base_link` transform, driven a 10×10 m square at three speeds, and plotted the drift in PlotJuggler. You will be able to look at the closure error of that square and say, with numbers, *exactly how much your robot lied to itself* — and you will understand why nobody ships a robot on wheel odometry alone.

This is the last "pure modelling" week before SLAM. Week 7 hands you `slam_toolbox`, which corrects the drift you measure this week with scan matching. Week 9 calibrates the IMU you will fuse in Week 10. The odometry node you build this week is **not a throwaway** — it becomes the wheel-odometry input to the EKF in Phase 2, and it is one of the four artifacts you defend at the Week 8 architecture review. Build it like it ships, because it does.

The central engineering truth of the week, stated up front so you can hold it the whole way through: **wheel odometry drifts, always, and the drift is unbounded.** It is not a bug you can fix with better code. It is a structural consequence of *dead reckoning* — integrating velocity to get position with no external reference. Every source of error (wheel-radius mismatch, wheelbase miscalibration, slip, quantization, finite sample rate) feeds an integral that never resets. A 1% systematic radius error doesn't stay 1%; over a 40 m path it becomes 40 cm of position error, and the *heading* error it induces compounds *quadratically* with distance because a small constant yaw bias rotates your whole world. The mature move is not to pretend you can eliminate drift. It is to *characterize* it, *bound* it with a second sensor, and *budget* for it in everything downstream. This week you learn to characterize it. The rest of Phase 2 teaches you to bound it.

The second truth: **forward kinematics is integration, inverse kinematics is algebra, and they are not inverses of each other in the way beginners expect.** Forward kinematics takes wheel velocities and integrates them through a motion model to get a pose — that is the odometry direction, and it is lossy because integration loses information about what actually happened between samples. Inverse kinematics takes a desired body velocity `(vₓ, ω)` and solves for the wheel velocities that produce it — that is the *control* direction, and it is exact for the rigid model. A differential-drive robot can be commanded to any `(v, ω)` instantly (inverse kinematics is unconstrained); but it cannot move sideways (it is *nonholonomic*), which is a constraint that lives in the forward model, not the inverse one. Confusing these two directions is the single most common source of "my robot drives in circles" bugs, and we will keep them rigorously separate.

The third truth: **the motion model is a choice, and the choice has consequences you will feel for the rest of the track.** Differential-drive, unicycle, bicycle, Ackermann, and mecanum are five different answers to "how does commanded velocity become motion," each with a different constraint structure, a different parameter set to calibrate, and a different failure mode. A diff-drive robot's dominant error is wheel-radius asymmetry. An Ackermann car's dominant error is steering-angle bias. A mecanum base's dominant error is roller slip, which is *worse* than diff-drive slip because all four wheels are always partially slipping by design. Pick the wrong model for your platform and your odometry is wrong before you write a line of code. We compare all five so that when you meet a real platform you can name its model and predict its drift signature on sight.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** differential-drive forward kinematics from the rigid-body constraint that both wheels share one chassis, expressing body twist `(vₓ, ω)` as a function of left/right wheel angular velocities, wheel radius `r`, and wheel separation `L`.
- **Derive** differential-drive inverse kinematics — the wheel velocities that realize a commanded `(vₓ, ω)` — and explain why the diff-drive Jacobian is square and invertible while the omnidirectional one is not.
- **Distinguish** the unicycle, differential-drive, bicycle, Ackermann, and mecanum models by their constraint structure (holonomic vs. nonholonomic), their degrees of freedom, their parameter sets, and their dominant odometry error sources.
- **Integrate** a body twist into a pose using both the zeroth-order (rectangular) and exact (arc / `SE(2)` exponential) integration schemes, and state when the difference between them matters.
- **Implement** an `rclpy` odometry node that subscribes to `/joint_states`, computes the pose increment per cycle, and publishes a `nav_msgs/Odometry` message plus the `odom → base_link` transform on `/tf` with correct frame ids, timestamps, and covariance.
- **Explain** where wheel odometry drift comes from — systematic error (radius/wheelbase calibration), non-systematic error (slip, uneven floors, collisions), quantization, and finite sample rate — and how each compounds over a path.
- **Quantify** drift empirically by driving a closed loop (a 10×10 m square) and measuring closure error, then express the error as a fraction of distance travelled.
- **Visualize** odometry and ground truth simultaneously in PlotJuggler, building a reusable layout that shows `x`, `y`, `yaw`, and `XY` trajectory side by side.
- **Calibrate** a systematic error (e.g., an effective-wheel-radius scale factor or the UMBmark wheelbase correction) and demonstrate, with numbers, that closure error drops.
- **Budget** for drift in a downstream design — state honest covariance on `/odom` so the Week 10 EKF can weight it correctly.

## Prerequisites

- **Weeks 1 through 5** of C24 complete. You can write an `rclpy` node, build a colcon workspace, author a URDF in xacro, spawn it in Gz Sim, and reason about QoS. You are comfortable with `ros2 topic echo`, `ros2 topic hz`, and `ros2 run`. This week assumes you are not surprised by the ROS2 plumbing — we spend our attention on the math and the modelling.
- **The rigid-body math from Week 1.** You can multiply rotation matrices, you know what `SO(2)` and `SE(2)` are, you can read a homogeneous transform, and you remember that rotations do not commute. We use `SE(2)` (planar pose) constantly this week and `SE(3)` only for the TF message construction.
- **A working ROS2 Jazzy install on Ubuntu 24.04** (or the Path B container). `ros2 --version` reports Jazzy. `gz sim --version` reports Harmonic. Your Week 3 diff-drive robot still spawns and drives under `ros2 topic pub /cmd_vel`.
- **PlotJuggler installed** — `sudo apt install ros-jazzy-plotjuggler-ros`. We use it as the primary visualization tool this week; it is the fastest way in the ecosystem to plot a time series off a live topic.
- **A Python scientific stack** — `numpy`, `matplotlib`, and `scipy` available in the same environment you run ROS2 from. The kinematics derivations are checked numerically; the drift plots are rendered with matplotlib for the homework writeup.
- Nothing else. We start from your Week 3 robot and a blank `crunchbot_odometry` package, and we end with a calibrated odometry source that feeds Phase 2.

## Topics covered

- **The wheel constraint.** A wheel rolling without slipping converts angular velocity to ground velocity: `v = r·ω̇`. The no-slip and no-skid constraints. Why a passive caster contributes a constraint of zero (it is free to swivel) and a driven wheel contributes one.
- **Differential-drive forward kinematics.** Body linear velocity `vₓ = r(ω̇_R + ω̇_L)/2`, body angular velocity `ω = r(ω̇_R − ω̇_L)/L`. The instantaneous center of rotation (ICR). Why a diff-drive robot's ICR always lies on the wheel axle line.
- **Differential-drive inverse kinematics.** Solving `(vₓ, ω)` for `(ω̇_L, ω̇_R)`. The 2×2 kinematic matrix and its inverse. Wheel-speed saturation and how `diff_drive_controller` handles it.
- **The unicycle model.** The minimal `(vₓ, ω)` abstraction that diff-drive, bicycle, and Ackermann all reduce to at the body level. Why Nav2 plans in unicycle space and lets the controller translate.
- **The bicycle model.** Front-steer, rear-drive. The steering angle `δ`, the wheelbase `ℓ`, the slip-free turning radius `R = ℓ / tan δ`. Kinematic vs. dynamic bicycle.
- **The Ackermann model.** Why a real car's two front wheels steer at *different* angles, the Ackermann steering geometry, and why `ackermann_msgs/AckermannDrive` carries one "virtual" steering angle.
- **Omnidirectional / mecanum kinematics.** The 45° roller, the 4-wheel mecanum Jacobian (3×4, non-square), holonomic motion, and why mecanum odometry is *worse* than diff-drive despite the extra wheels.
- **Pose integration.** Euler (rectangular) integration vs. exact arc integration vs. the `SE(2)` matrix exponential. Quantifying the integration error and when 50 Hz makes it negligible.
- **Odometry message construction.** `nav_msgs/Odometry` fields, the `odom → base_link` TF, frame conventions (REP-103, REP-105), header stamping, twist vs. pose covariance, and the `tf2_ros.TransformBroadcaster`.
- **Drift taxonomy.** Systematic error (radius, wheelbase), non-systematic error (slip, bumps), quantization, finite-rate integration. The UMBmark benchmark. How heading error dominates position error over distance.
- **Calibration.** The effective-radius scale factor, the wheelbase correction, the UMBmark CW/CCW square test, and how to fit a single correction that measurably reduces closure error.

## Weekly schedule

The schedule adds up to approximately **36 hours**. Treat it as a target, not a contract. The drift-measurement labs are best run when you can babysit a 5-minute Gz Sim drive without interruption — do not start a square-drive run with ten minutes left in your day.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Wheel constraint, diff-drive forward/inverse kinematics     |   2h     |   1.5h    |    0h      |   0.5h    |   1h     |    0h        |   0.5h     |   5.5h      |
| Tuesday   | Unicycle, bicycle, Ackermann, mecanum models compared       |   2h     |   1.5h    |    0h      |   0.5h    |   1h     |    0h        |   0.5h     |   5.5h      |
| Wednesday | Pose integration, `/odom` + TF, the odometry node           |   1.5h   |   1.5h    |    0h      |   0.5h    |   1h     |    0.5h      |   0.5h     |   5.5h      |
| Thursday  | Drift taxonomy, PlotJuggler, drive the square, challenge     |   0.5h   |   0h      |    2h      |   0.5h    |   1h     |    2h        |   0.5h     |   6.5h      |
| Friday    | Mini-project — crunchbot odometry node + drift layout        |   0h     |   0h      |    1h      |   0.5h    |   1h     |    3h        |   0.5h     |   6h        |
| Saturday  | Mini-project deep work, calibration, results writeup         |   0h     |   0h      |    0h      |   0h      |   0h     |    3h        |   0h       |   3h        |
| Sunday    | Quiz, review, polish                                         |   0h     |   0h      |    0h      |   1h      |   1h     |    1h        |   0h       |   3h        |
| **Total** |                                                             | **6h**   | **4.5h**  | **3h**     | **3.5h**  | **6h**   | **9.5h**     | **2.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | Siegwart/Nourbakhsh, the REP-103/105 specs, the `diff_drive_controller` docs, the UMBmark paper, PlotJuggler docs, and the talks worth your time |
| [lecture-notes/01-wheel-odometry-drifts-always.md](./02-lecture-notes/01-wheel-odometry-drifts-always.md) | Why odometry drifts: dead reckoning, the four error classes, how heading error dominates, the UMBmark benchmark, and how to budget covariance |
| [lecture-notes/02-diff-drive-unicycle-bicycle-ackermann-mecanum.md](./02-lecture-notes/02-diff-drive-unicycle-bicycle-ackermann-mecanum.md) | The five motion models derived and compared: constraints, Jacobians, forward/inverse kinematics, and each model's dominant drift source |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-diff-drive-forward-kinematics.md](./03-exercises/exercise-01-diff-drive-forward-kinematics.md) | Guided: implement diff-drive forward kinematics by hand in an `rclpy` node consuming `/joint_states`, with starter and solution code |
| [exercises/exercise-02-odom-and-tf-publisher.py](./03-exercises/exercise-02-odom-and-tf-publisher.py) | Runnable: publish `nav_msgs/Odometry` and the `odom → base_link` TF from your kinematics |
| [exercises/exercise-03-drive-square-and-measure-drift.py](./03-exercises/exercise-03-drive-square-and-measure-drift.py) | Runnable: drive a 10×10 m square at three speeds, log odom vs. ground truth, compute closure error |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the challenge |
| [challenges/challenge-01-quantify-and-calibrate-drift.md](./04-challenges/challenge-01-quantify-and-calibrate-drift.md) | Quantify how drift scales with speed and turn rate, then fit and test one calibration correction that reduces closure error |
| [mini-project/README.md](./07-mini-project/00-overview.md) | Full spec for the **crunchbot odometry node**: `joint_states → /odom + TF`, configurable kinematics, PlotJuggler drift layout — the wheel-odom source for the Phase 2 EKF |
| [quiz.md](./05-quiz.md) | 13 questions on kinematics, integration, drift, and odometry publishing, with an answer key |
| [homework.md](./06-homework.md) | Five practice problems with deliverables and a rubric |

## The "drift you can defend" promise

C24 treats your odometry the way Week 7 of C9 treats a benchmark: **a claim is worthless without a number.** "My odometry is pretty good" is not an engineering statement. "My closure error over a 40 m square is 0.6 m, which is 1.5% of path length, and it scales linearly with commanded speed and superlinearly with turn rate" *is* an engineering statement, and it is the one you will be able to make by Sunday. Every drift claim in your homework and mini-project must be backed by a measured closure error and a PlotJuggler or matplotlib plot. The phrase "should be accurate" never appears in a robotics engineer's design review; the phrase "drifts 1.5% of path length, dominated by heading error, fits a 0.98 radius-scale correction" does.

## A note on what's not here

Week 6 introduces *modelling* and *characterization* of wheel odometry. It does **not** introduce:

- **Sensor fusion.** Fusing the odometry you build this week with an IMU into a bounded-drift estimate is Week 10's `robot_localization` lab. This week you build the *input* to that filter and state its covariance honestly. We deliberately do not correct the drift this week beyond a single systematic calibration — the whole point is to *feel* the unbounded error before you learn to bound it.
- **SLAM.** Scan-matching against a map to correct pose is Week 7 (`slam_toolbox`). Odometry is the *prior* a SLAM front-end refines; you cannot understand why loop closure matters until you have measured how badly odometry drifts without it.
- **Dynamics.** This week is purely *kinematic* — we relate velocities to velocities and integrate, with no forces, masses, or tire models. The dynamic bicycle model, slip angles, and tire force curves are Phase 3 control material. Kinematic models are correct at the low speeds and low accelerations of an indoor mobile base; we say exactly where they break.
- **Control.** Closing a loop on pose (driving *to* a goal) is Nav2 and the controllers of Phase 3. This week we *open-loop* command velocities and *measure* the resulting drift. The square we drive is timed and open-loop on purpose — closed-loop control would hide the very drift we are trying to expose.
- **Visual / wheel-IMU odometry.** Optical-flow odometry is Week 12; legged and Mecanum-specific slip estimation are later electives. We mention them so you know the landscape.

The point of Week 6 is a sharp, narrow skill: derive a motion model correctly, turn it into a publishing odometry node a reviewer would sign off on, and measure its drift honestly enough that the next ten weeks of fusion and SLAM have a number to beat.

## Up next

Continue to **Week 7 — First SLAM: `slam_toolbox` in 2D** once you have shipped this week's mini-project with a measured closure error. Week 7 drives the *same* diff-drive robot through a multi-room world and uses scan matching to correct the drift you measured this week — and you will finally see, in RViz, the map snap into place when a loop closes. The habit you build this week — *model honestly, integrate carefully, measure the drift, state the covariance* — is the habit that makes every estimation week land. SLAM only matters because odometry drifts, and you only believe odometry drifts because this week you measured it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
