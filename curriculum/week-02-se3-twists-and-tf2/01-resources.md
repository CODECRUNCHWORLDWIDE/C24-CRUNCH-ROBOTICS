# Week 2 — Resources

Every resource on this page is **free** unless explicitly marked. The ROS2 docs are open. *Modern Robotics* is published free by the authors. The tf2 source is on GitHub. We do not link paywalled material without saying so.

These are curated and current as of 2026. ROS2 Jazzy is the LTS release we target (Ubuntu 24.04, support through 2029). Where a doc page tracks "Rolling," we note it; pin your mental model to Jazzy.

## Required reading (work it into your week)

- **tf2 concepts** — the canonical mental model of frames, the buffer, and lookups:
  <https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html>
- **tf2 tutorials (Jazzy)** — broadcaster, listener, static broadcaster, time-travel, all in Python and C++:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>
- **Modern Robotics, Chapter 3 — "Rigid-Body Motions"** (Lynch & Park) — SE(3), twists, the exponential map, the adjoint, done right and free:
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **REP 103 — Standard Units of Measure and Coordinate Conventions** — the right-handed, x-forward, z-up convention every ROS robot uses:
  <https://www.ros.org/reps/rep-0103.html>
- **REP 105 — Coordinate Frames for Mobile Platforms** — the `map → odom → base_link` convention you will live inside all year:
  <https://www.ros.org/reps/rep-0105.html>

## The SE(3) and Lie-theory references

You will not memorize these. You read the relevant section the first time you hit a sign error.

- **"A micro Lie theory for state estimation in robotics"** (Solà, Deray, Atchuthan, 2018/2021) — the single best concise reference for SE(3), the exp/log maps, and adjoints, with worked Jacobians:
  <https://arxiv.org/abs/1812.01537>
- **Modern Robotics — full free PDF and video lectures** (Northwestern, Coursera mirror is also free to audit):
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **"A Tutorial on SE(3) transformation parameterizations and on-manifold optimization"** (Blanco-Claraco) — heavier, optimization-flavored, useful when you hit GTSAM in week 11:
  <https://arxiv.org/abs/2103.15980>

## Official ROS2 / tf2 docs

- **tf2 — the design paper** ("tf: The transform library", Foote, TePRA 2013) — why tf2 buffers a time window and interpolates:
  <https://ieeexplore.ieee.org/document/6556373>
- **`tf2_ros` Python API** — `Buffer`, `TransformListener`, `TransformBroadcaster`, `StaticTransformBroadcaster`:
  <https://docs.ros.org/en/jazzy/p/tf2_ros/>
- **`tf2_ros` C++ API**:
  <https://docs.ros.org/en/jazzy/p/tf2_ros/generated/index.html>
- **`geometry_msgs/TransformStamped`** — the message every transform is published as:
  <https://docs.ros.org/en/jazzy/p/geometry_msgs/interfaces/msg/TransformStamped.html>
- **tf2 debugging** — the official "how do I debug tf2" page:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html>

## The tf2 source (read it; it is good code)

You learn more from one hour reading `geometry2` than from three tutorials. The tree walk lives in `BufferCore::lookupTransform`.

- **`ros2/geometry2`** — the tf2 monorepo: `tf2`, `tf2_ros`, `tf2_tools`, `tf2_geometry_msgs`:
  <https://github.com/ros2/geometry2>
- **`BufferCore` — the actual tree walk and time interpolation**:
  <https://github.com/ros2/geometry2/blob/rolling/tf2/src/buffer_core.cpp>
- **`static_transform_publisher` source** — what the CLI tool actually does:
  <https://github.com/ros2/geometry2/blob/rolling/tf2_ros/src/static_transform_broadcaster_program.cpp>

## Tools you'll use this week

- **`ros2 run tf2_tools view_frames`** — renders the live TF forest to `frames.pdf`. Your first move when a lookup fails.
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html>
- **`ros2 run tf2_ros tf2_echo <target> <source>`** — prints the live transform between two frames, once per second.
- **`ros2 run tf2_ros tf2_monitor`** — reports the rate and delay of every published transform; the tool that catches a slow or stale broadcaster.
- **`rviz2`** — the **TF** display draws every frame as an axis triad with its name; turn it on first.
- **`ros2 topic echo /tf` / `ros2 topic echo /tf_static`** — see the raw `TFMessage`. `/tf_static` is latched (`TRANSIENT_LOCAL` QoS); a late subscriber still gets the last value.
- **`tf_transformations`** — the Python helper for quaternion ↔ matrix ↔ Euler. Installed with `sudo apt install ros-jazzy-tf-transformations`. (Wraps `transforms3d`.)

## Python libraries we touch this week

- **`rclpy`** — the ROS2 Python client library. Ships with Jazzy.
- **`tf2_ros`** — the tf2 Python bindings. `sudo apt install ros-jazzy-tf2-ros-py`.
- **`numpy`** — every transform is a `np.ndarray`. Ships in the ROS2 Python environment.
- **`tf_transformations`** — quaternion/matrix conversions. `sudo apt install ros-jazzy-tf-transformations`.
- **`transforms3d`** — what `tf_transformations` wraps; sometimes cleaner to call directly. `pip install transforms3d`.
- **`scipy.spatial.transform.Rotation`** — an alternative, well-tested rotation library; we cross-check against it. Ships with SciPy.

## C++ we read this week

- **`tf2_ros::Buffer`, `tf2_ros::TransformListener`** — the C++ listener pattern Nav2 and MoveIt2 use:
  <https://docs.ros.org/en/jazzy/p/tf2_ros/generated/index.html>
- **`tf2::Transform`, `tf2::Quaternion`, `tf2::Vector3`** — the `tf2` math types (`tf2/LinearMath/Transform.hpp`):
  <https://github.com/ros2/geometry2/tree/rolling/tf2/include/tf2/LinearMath>

## Videos and talks (free, no signup)

- **Modern Robotics — Chapter 3 video lectures** (Northwestern, Kevin Lynch) — watch the "Rigid-Body Motions" playlist; ~90 minutes total, the clearest SE(3) explanation on video:
  <https://www.youtube.com/playlist?list=PLggLP4f-rq02vX0OQQ5vrCxbJrzamYDfx>
- **"3Blue1Brown — Quaternions and 3D rotation"** — geometric intuition for the rotation half; pairs with week 1:
  <https://www.youtube.com/watch?v=d4EgbgTm0Bg>
- **ROSCon talks archive** — search "tf2" for the maintainer talks on common failure modes:
  <https://roscon.ros.org/>

## Reference cards to keep in a tab

- **`geometry_msgs` message catalogue** — `Transform`, `TransformStamped`, `Pose`, `Twist`, `Vector3`, `Quaternion`:
  <https://docs.ros.org/en/jazzy/p/geometry_msgs/>
- **REP 105 frame diagram** — `map → odom → base_link → sensor_frames`; commit it to memory.

## Glossary cheat sheet

Keep this open in a tab. We use these terms precisely all week.

| Term | Plain English |
|------|---------------|
| **SO(3)** | The group of 3D rotations. 3×3 matrices `R` with `R.T @ R = I` and `det(R) = 1`. |
| **SE(3)** | The group of rigid-body motions. 4×4 matrices `[[R, t], [0, 1]]`. Rotation + translation. |
| **Homogeneous transform** | The 4×4 matrix form of an SE(3) element. Lets you compose rotation + translation by matrix multiply. |
| **Twist** | A 6-vector `[v, ω]` (ROS order) describing instantaneous rigid-body velocity: linear `v` and angular `ω`. The Lie algebra se(3). |
| **se(3)** | The Lie algebra of SE(3): the tangent space at the identity. Twists live here. |
| **Exponential map** | `exp: se(3) → SE(3)`. Turns a twist (×time) into a finite transform. The bridge from velocity to pose. |
| **Logarithm map** | `log: SE(3) → se(3)`. The inverse of `exp`. Turns a transform into the twist that generates it. |
| **Adjoint `Ad_T`** | The 6×6 matrix that transforms a twist from one frame to another. Points use `T`; twists use `Ad_T`. |
| **Frame** | A named coordinate system. In tf2, a node in the tree (e.g., `base_link`, `wrist`). |
| **tf2 buffer** | The time-windowed store of transforms. A listener fills it; a lookup queries it. |
| **Static transform** | A transform that never changes (bolt-on sensor). Published once on `/tf_static`, latched. |
| **Dynamic transform** | A transform that changes over time (a moving joint). Re-published on `/tf`, typically 10–100 Hz. |
| **`TransformStamped`** | The message carrying one parent→child transform plus a `header.stamp` and `frame_id`/`child_frame_id`. |
| **`lookup_transform`** | The query: "give me the transform from `source` to `target` at time `t`." Walks the tree, interpolates in time. |
| **`ExtrapolationException`** | The lookup asked for a time outside the buffered window. The single most common tf2 error. |
| **`LookupException`** | A named frame does not exist in the buffer. |
| **`ConnectivityException`** | Both frames exist but are not connected — two separate trees. |

---

*If a link 404s, please open an issue so we can replace it.*
