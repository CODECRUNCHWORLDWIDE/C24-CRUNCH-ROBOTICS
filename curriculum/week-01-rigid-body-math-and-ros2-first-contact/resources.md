# Week 1 — Resources

Every resource here is **free** and, where versioned, pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04). The rotation-math references are open courseware, free textbooks, or canonical papers. No paywalled books are linked.

When a link is versioned, the Jazzy URL is given. If you are on a newer distro later, swap `jazzy` for your distro name — the math is eternal; only the API-reference URLs move.

## Required reading (work it into your week)

- **ROS2 Jazzy installation (Ubuntu, deb packages)** — do this Wednesday, exactly as written:
  <https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html>
- **Configuring your ROS2 environment** — sourcing, `ROS_DOMAIN_ID`, the overlay/underlay model:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Configuring-ROS2-Environment.html>
- **Understanding nodes / topics** — the conceptual core of the pub/sub graph:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes.html>
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics.html>
- **Writing a simple publisher (Python)** — the template your Thursday node is built from:
  <https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html>

## Rotation math (the heart of the week)

You do not need to read all of these. Pick the one whose voice fits you and read it deeply; skim the rest.

- **3Blue1Brown — "Quaternions and 3D rotation, explained interactively"** — the single best geometric intuition for quaternions, free, interactive:
  <https://eater.net/quaternions>
- **3Blue1Brown — "Visualizing quaternions"** (the companion video):
  <https://www.youtube.com/watch?v=d4EgbgTm0Bg>
- **"Quaternion kinematics for the error-state Kalman filter"** (Joan Solà) — the canonical, rigorous, free PDF reference for quaternion conventions; §1–2 this week, the rest pays off in Phase 2:
  <https://arxiv.org/abs/1711.02508>
- **Modern Robotics (Lynch & Park), Chapter 3 — Rigid-Body Motions** — the free textbook this whole track leans on; §3.1–3.2 cover SO(3), the exponential map, and Rodrigues:
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **"Why I no longer recommend Euler angles" / gimbal-lock explainers** — search the Wikipedia *Gimbal lock* article and the *Euler angles* article for the ZYX convention and the singularity at pitch = ±90°:
  <https://en.wikipedia.org/wiki/Gimbal_lock>

## API references (the ones you'll have open all week)

- **`rclpy` API reference** — `Node`, `create_publisher`, `create_timer`, `spin`:
  <https://docs.ros.org/en/jazzy/p/rclpy/>
- **`geometry_msgs/PoseStamped`** — the message your publisher emits:
  <https://docs.ros.org/en/jazzy/p/geometry_msgs/msg/PoseStamped.html>
- **`scipy.spatial.transform.Rotation`** — the trusted reference implementation you verify against:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.html>
- **`tf_transformations`** — the ROS2 thin wrapper over `transforms3d` for quat/Euler/matrix conversions:
  <https://github.com/DLu/tf_transformations>

## Tools you'll use this week

- **`rviz2`** — `ros2 run rviz2 rviz2`. Your first visualization. Set the Fixed Frame, add a Pose display.
- **`ros2 topic echo /tumbling_pose`** — see the raw quaternion stream your node publishes.
- **`ros2 topic hz /tumbling_pose`** — confirm you're actually at 50 Hz.
- **`ros2 doctor`** — sanity-check the install before you blame your code.
- **`colcon build` / `colcon build --symlink-install`** — build your workspace; `--symlink-install` lets you edit Python without rebuilding.
- **NumPy** — `pip install numpy scipy` (or `apt install python3-numpy python3-scipy`). The math substrate for every exercise.

## The "why ROS1 is dead" reading

- **"Why ROS 2?" (design article)** — the official rationale: no master, DDS, real-time, multi-robot:
  <https://design.ros2.org/articles/why_ros2.html>
- **ROS2 architecture / `rmw` layering** — the stack you'll see in Lecture 2's diagram:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Different-Middleware-Vendors.html>

## Talks worth your time (free, no signup)

- **ROSCon talk archive** — the OSRF posts every talk free; search for the "ROS2 in 90 minutes" and "intro to tf2" sessions:
  <https://roscon.ros.org/>
- **ETH Zürich Robotics — "State Estimation and Localization" lecture series** — the rotation-representation lectures are free on YouTube and are exactly this week's math at a graduate level if you want to go deeper.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **SO(3)** | The special-orthogonal group in 3D — all 3×3 rotation matrices (`RᵀR = I`, `det R = +1`). |
| **SO(2)** | The 2D version — rotations of the plane, the unit circle of angles. |
| **Rotation matrix** | A 3×3 orthonormal matrix with `det = +1` that rotates a vector: `v' = R v`. |
| **Axis-angle** | A unit axis `k` and an angle `θ`; every 3D rotation is one rotation about one axis (Euler's theorem). |
| **Rodrigues' formula** | Closed form for the rotation matrix from axis-angle: `R = I + sinθ[k]× + (1−cosθ)[k]×²`. |
| **`[ω]×`** | The skew-symmetric "cross-product matrix" of a vector; `[ω]× v = ω × v`. |
| **Quaternion** | A 4-tuple `(w, x, y, z)`; a *unit* quaternion encodes a 3D rotation. |
| **Double cover** | `q` and `−q` represent the *same* rotation — the quaternions cover SO(3) twice. |
| **Hamilton product** | Quaternion multiplication; composes rotations; non-commutative. |
| **SLERP** | Spherical linear interpolation — constant-speed great-circle path between two quaternions. |
| **Euler angles** | Three sequential angles (e.g. ZYX yaw-pitch-roll); intuitive, ambiguous, gimbal-locks. |
| **Gimbal lock** | Loss of one rotational degree of freedom in an Euler representation at pitch = ±90°. |
| **Node** | A single ROS2 process-participant that publishes/subscribes/serves. |
| **Topic** | A named, typed pub/sub channel between nodes. |
| **`rclpy`** | The Python ROS2 client library. |
| **DDS** | Data Distribution Service — the pub/sub middleware under ROS2 (no master). |
| **`colcon`** | The ROS2 build tool for workspaces. |
| **Overlay** | A sourced workspace layered on top of the base ROS2 install. |

---

*If a link 404s, please open an issue so we can replace it.*
