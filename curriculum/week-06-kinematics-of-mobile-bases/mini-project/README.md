# Mini-Project — The crunchbot odometry node

> Build the production `crunchbot_odometry` ROS2 package: a configurable diff-drive odometry node that consumes `/joint_states`, integrates the body twist with the exact-arc `SE(2)` integrator, publishes `nav_msgs/Odometry` on `/odom` with honest covariance, and broadcasts the `odom → base_link` transform. Ship it with a parameter file, a launch file, a PlotJuggler layout that visualizes drift against ground truth, and a one-page calibration writeup. **This node is not a throwaway.** It becomes the wheel-odometry input to the `robot_localization` EKF in Phase 2 (Week 10), and it is one of the four artifacts you defend at the Week 8 architecture review. Build it like it ships, because it does.

This is the canonical "first real ROS2 node a robotics shop would code-review" exercise. The exercises taught you the kinematics and the integrator in isolation; the mini-project assembles them into a package with the discipline a reviewer expects — declared parameters with sane defaults, a launch file, honest covariance, frame conventions per REP-103/105, and a reproducible drift measurement. By the end you have a small, well-documented, calibrated odometry source that the rest of the track builds on.

**Estimated time:** ~9.5 hours (split across Wednesday, Friday, Saturday in the suggested schedule).

---

## What you will build

A colcon package `crunchbot_odometry` containing:

1. **`crunchbot_odometry/odometry_node.py`** — the node. Subscribes to `/joint_states`, computes diff-drive forward kinematics, integrates with the exact-arc integrator, publishes `/odom` and the `odom → base_link` TF with honest, parameterized covariance.
2. **`crunchbot_odometry/drive_square.py`** — the open-loop square-driver from Exercise 3, packaged, with the ground-truth comparison and CSV logging.
3. **`config/odometry.yaml`** — every kinematic and frame parameter, externalized. No magic numbers in the node.
4. **`launch/odometry.launch.py`** — brings up the odometry node with the parameter file, optionally remapping the ground-truth bridge.
5. **`plotjuggler/drift_layout.xml`** — a saved PlotJuggler layout that shows, on one screen: `x`, `y`, `yaw` time series (odom vs ground truth), and the `XY` trajectory overlay. Load it, stream the live topics, drive the square, and watch the drift open up.
6. **`CALIBRATION.md`** — the one-page writeup: your measured drift, your fitted correction, your before/after closure error, and the honest covariance you settled on.
7. **`test/test_kinematics.py`** — `pytest` unit tests for the kinematics and integrator (no ROS2 spin required — pure functions).

You ship **one package** with a clean `package.xml`, a working `setup.py`/`setup.cfg` (ament_python), and a top-level `README.md` an operator could follow.

---

## Why this compounds

This is the explicit "compounds on Week N" note: **the `/odom` topic and its covariance produced here are the wheel-odometry input to the Week 10 EKF.** In Week 10 you will configure `robot_localization`'s `ekf_node` to fuse this `/odom` with the calibrated IMU from Week 9, re-drive *this exact square*, and show the fused drift drop below your raw drift. That comparison only works if:

- Your `/odom` frames are correct (`odom → base_link`, REP-105). The EKF will silently reject odometry on the wrong frame.
- Your covariance is **honest** (Lecture 1, §1.7). If you claim zero covariance, the EKF trusts your drifting odometry over the good IMU and the fusion is *worse* than the IMU alone. If you claim huge covariance, the EKF ignores your odometry and the fusion gains nothing from the wheels.
- Your timestamps come from the `/joint_states` message, not `now()`. The EKF synchronizes inputs by stamp; a `now()` stamp drifts against the IMU stamp and the filter desyncs.

A reviewer at Week 8 will ask you to defend exactly these three properties. Build them in from the start.

---

## Rules

- **You may** read the ROS2 docs, REP-103/105, the `diff_drive_controller` source (to compare your design against the production reference), the lecture notes, and your Week 6 exercises.
- **You may NOT** use `diff_drive_controller` or any existing odometry package *as your node*. The point is to write the kinematics and integrator yourself, once, correctly, so you understand what the shipped controller does. You may read it; you may not import it.
- **You may NOT** use `tf_transformations` or `scipy.spatial.transform` for the yaw→quaternion conversion. Hand-roll the planar `q = (0,0,sin(θ/2),cos(θ/2))` — it is the `SO(2)→SO(3)` embedding from Week 1 and you should be able to write it from memory.
- ROS2 **Jazzy**, **Ubuntu 24.04**, Gz Sim **Harmonic**. `ament_python` package. Python 3.12.
- Every kinematic and frame value is a **declared ROS2 parameter** loaded from `config/odometry.yaml`. Zero magic numbers in the node body.
- The node publishes `/odom` with `RELIABLE` QoS (it is a state estimate, not a sensor stream — Week 5) and broadcasts TF via `tf2_ros.TransformBroadcaster`.

---

## Step-by-step

### Step 1 — Scaffold the package (~45 min)

```bash
cd ~/crunch_ws/src
ros2 pkg create --build-type ament_python crunchbot_odometry \
  --dependencies rclpy sensor_msgs nav_msgs geometry_msgs tf2_ros
```

Lay out the directories: `crunchbot_odometry/` (the Python module), `config/`, `launch/`, `plotjuggler/`, `test/`. Wire `setup.py` to install the `config/`, `launch/`, and `plotjuggler/` directories via `data_files`, and register two console entry points: `odometry_node` and `drive_square`.

```python
# setup.py entry_points (abbreviated)
entry_points={
    "console_scripts": [
        "odometry_node = crunchbot_odometry.odometry_node:main",
        "drive_square = crunchbot_odometry.drive_square:main",
    ],
},
```

Build and confirm the package is found:

```bash
cd ~/crunch_ws && colcon build --packages-select crunchbot_odometry
source install/setup.bash
ros2 pkg executables crunchbot_odometry   # lists odometry_node and drive_square
```

### Step 2 — Port the odometry node (~90 min)

Move your Exercise 2 node into `crunchbot_odometry/odometry_node.py` and harden it:

- Pull **all** parameters from `config/odometry.yaml`: `wheel_radius`, `wheel_separation`, `left_joint`, `right_joint`, `odom_frame`, `base_frame`, `publish_tf`, and the **covariance diagonals** (`pose_cov_diag`, `twist_cov_diag` — six floats each, so a reviewer can tune covariance without touching code).
- Keep the **velocity[]/position[] fallback** from Exercise 1/2 so the node works against any `JointState` publisher.
- Use the **exact-arc integrator** with the `|ω| > ε` guard.
- Stamp every message and transform with the **`/joint_states` header stamp**, not `now()`.
- Add a **lifecycle-friendly shutdown**: clean `destroy_node()`, no exceptions on Ctrl+C. (Full lifecycle-node conversion is a stretch goal.)

A skeleton of the parameter loading:

```python
self.declare_parameter("wheel_radius", 0.05)
self.declare_parameter("wheel_separation", 0.30)
self.declare_parameter("pose_cov_diag", [0.001, 0.001, 1e6, 1e6, 1e6, 0.01])
self.declare_parameter("twist_cov_diag", [0.001, 1e6, 1e6, 1e6, 1e6, 0.01])
# ... build the 36-element covariance from the 6-element diagonal:
pose_cov = [0.0] * 36
for i, v in enumerate(self.get_parameter("pose_cov_diag").value):
    pose_cov[i * 7] = v
```

### Step 3 — The parameter file (~20 min)

`config/odometry.yaml`:

```yaml
odometry_node:
  ros__parameters:
    wheel_radius: 0.05
    wheel_separation: 0.30
    left_joint: "left_wheel_joint"
    right_joint: "right_wheel_joint"
    odom_frame: "odom"
    base_frame: "base_link"
    publish_tf: true
    # covariance diagonals: [x, y, z, roll, pitch, yaw] and [vx, vy, vz, wx, wy, wz]
    pose_cov_diag:  [0.001, 0.001, 1000000.0, 1000000.0, 1000000.0, 0.01]
    twist_cov_diag: [0.001, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 0.01]
```

### Step 4 — The launch file (~30 min)

`launch/odometry.launch.py` starts the node with the parameter file and (optionally) the `ros_gz_bridge` for ground truth:

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg = get_package_share_directory("crunchbot_odometry")
    params = os.path.join(pkg, "config", "odometry.yaml")
    return LaunchDescription([
        Node(
            package="crunchbot_odometry",
            executable="odometry_node",
            name="odometry_node",
            parameters=[params],
            output="screen",
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=[
                "/model/crunchbot/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry",
            ],
            remappings=[("/model/crunchbot/odometry", "/ground_truth/odom")],
            output="screen",
        ),
    ])
```

### Step 5 — Unit-test the kinematics (~45 min)

Factor the kinematics and integrator into pure functions (no ROS2) so they are testable without spinning a node. `test/test_kinematics.py`:

```python
import math
from crunchbot_odometry.kinematics import forward_kinematics, integrate_exact_arc


def test_straight_recovers_command():
    # both wheels equal -> pure forward, zero yaw rate
    vx, w = forward_kinematics(phidot_L=4.0, phidot_R=4.0, r=0.05, L=0.30)
    assert math.isclose(vx, 0.2, abs_tol=1e-9)
    assert math.isclose(w, 0.0, abs_tol=1e-9)


def test_spin_in_place():
    # equal and opposite -> zero forward, pure yaw rate
    vx, w = forward_kinematics(phidot_L=-1.5, phidot_R=1.5, r=0.05, L=0.30)
    assert math.isclose(vx, 0.0, abs_tol=1e-9)
    assert math.isclose(w, 0.05 * 3.0 / 0.30, abs_tol=1e-9)   # = 0.5 rad/s


def test_exact_arc_closes_a_circle():
    # drive a full circle: after 2*pi/w seconds the pose returns to start
    x = y = th = 0.0
    vx, w, dt = 0.5, 0.5, 0.001
    steps = int(round((2 * math.pi / w) / dt))
    for _ in range(steps):
        x, y, th = integrate_exact_arc(x, y, th, vx, w, dt)
    assert math.hypot(x, y) < 1e-2     # back near the origin


def test_straight_limit_no_divide_by_zero():
    # w = 0 must not raise and must move straight along +x
    x, y, th = integrate_exact_arc(0.0, 0.0, 0.0, vx=0.2, w=0.0, dt=1.0)
    assert math.isclose(x, 0.2, abs_tol=1e-9)
    assert math.isclose(y, 0.0, abs_tol=1e-9)
```

Run with `colcon test --packages-select crunchbot_odometry` and confirm green.

### Step 6 — Drive the square and build the PlotJuggler layout (~120 min)

Bring up the robot, the odometry node, and the ground-truth bridge:

```bash
ros2 launch crunchbot_odometry odometry.launch.py
ros2 run crunchbot_odometry drive_square --ros-args -p speed:=0.5
```

Open PlotJuggler, connect the ROS2 streamer, and build the layout: a 2×2 grid with `x` (odom vs gt), `y` (odom vs gt), `yaw` (odom vs gt), and the `XY` overlay. Save it to `plotjuggler/drift_layout.xml`. The acceptance bar is that **anyone can load your layout, stream the live topics, and immediately see the drift** without configuring a single plot.

### Step 7 — Calibrate and write it up (~90 min)

Run the challenge's calibration (or at least a single radius/wheelbase scale fit), apply it via `config/odometry.yaml`, re-drive, and record the before/after closure error in `CALIBRATION.md`. Settle on the covariance you will hand to Week 10's EKF and justify it in one paragraph.

---

## Acceptance criteria

The rubric. Each box maps to a deliverable.

### Correctness (40%)

- [ ] `ros2 launch crunchbot_odometry odometry.launch.py` brings up the node with parameters from `config/odometry.yaml`; no hard-coded kinematic values in the node.
- [ ] `/odom` publishes a fully-populated `nav_msgs/Odometry` (pose, twist, both covariances) stamped with the **`/joint_states` time**, on `RELIABLE` QoS.
- [ ] `ros2 run tf2_tools view_frames` shows `odom → base_link` singly-parented; `tf2_echo odom base_link` tracks the integrated pose.
- [ ] Driving straight at a known speed integrates the correct distance; a pure spin integrates the correct yaw with the **correct sign**.
- [ ] `colcon test` passes all `test_kinematics.py` cases, including the divide-by-zero guard and the circle-closure test.

### Engineering quality (30%)

- [ ] The kinematics and integrator are pure functions in a `kinematics.py` module, unit-tested without ROS2.
- [ ] Covariance is parameterized (six-float diagonals) and honest: yaw variance larger than x/y, `1e6` on unmeasured DOFs.
- [ ] The exact-arc integrator is used (not Euler), with the `|ω| > ε` straight-line branch.
- [ ] `package.xml` declares every dependency; `setup.py` installs `config/`, `launch/`, and `plotjuggler/`.
- [ ] The top-level `README.md` lets an operator bring the node up in under five minutes.

### Measurement & calibration (30%)

- [ ] A reproducible square-drive run logs odom vs ground truth to CSV and prints closure error and drift as a fraction of path length.
- [ ] `plotjuggler/drift_layout.xml` loads and shows x/y/yaw/XY (odom vs ground truth) on one screen.
- [ ] `CALIBRATION.md` reports the measured drift, the fitted correction, the before/after closure error (with the correction measurably reducing it), and the chosen covariance with a one-paragraph justification tied to the Week 10 EKF.

---

## Stretch goals (no extra grade, real signal at the Week 8 review)

- **Lifecycle node.** Convert the odometry node to a `rclpy.lifecycle.LifecycleNode` with `on_configure`/`on_activate` transitions, so a launch sequence can bring it up in a controlled order (Week 4 material applied).
- **Velocity-proportional covariance.** Replace the static diagonal with `σ²_vx = k_v·|vx|`, `σ²_w = k_w·|w|` fit from your slip data (challenge stretch). This is the covariance the EKF wants.
- **A `crunchbot_odometry`-vs-`diff_drive_controller` bake-off.** Run the production `diff_drive_controller` alongside your node on the same robot and compare the two `/odom` streams in PlotJuggler. They should track within numerical noise; where they differ, find out why (wheel-speed saturation handling, integrator choice).
- **REP-105 completeness.** Add a static `base_link → base_footprint` transform and confirm the full tree (`map`-less for now) is consistent with what Nav2 will expect in Phase 3.

---

## Submission

Push `crunchbot_odometry/` to your Week 6 repository. The instructor reviews by:

1. `colcon build` and `colcon test` — must be green.
2. `ros2 launch crunchbot_odometry odometry.launch.py` against the reviewer's copy of the Week 3 robot — `/odom` and the TF must populate.
3. Loading `plotjuggler/drift_layout.xml` and driving the square — the drift must be visible.
4. Reading `CALIBRATION.md` and re-checking the before/after closure numbers reproduce.

A submission whose covariance is dishonest (zeros, or `1e6` everywhere) is the most common review-fail — the reviewer will ask you to defend it against the Week 10 EKF's needs, and "it compiled" is not a defense. State your covariance like you will have to live with it for ten weeks, because you will.
