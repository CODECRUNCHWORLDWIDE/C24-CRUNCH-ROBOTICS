# Exercise 1 — Diff-drive forward kinematics by hand in an `rclpy` node

**Goal:** Write an `rclpy` node that subscribes to `/joint_states`, reads the two wheel joints, and turns their angular velocities into a body twist `(vₓ, ω)` using the diff-drive forward kinematics you derived in Lecture 2 — `vₓ = r(φ̇_R + φ̇_L)/2` and `ω = r(φ̇_R − φ̇_L)/L`. No `diff_drive_controller`, no `tf2`, no `nav_msgs` yet. Just the two equations, computed correctly, printed to the log. This is the load-bearing derivation the rest of the week stands on, so we do it by hand and verify the numbers against a known input.

**Estimated time:** ~75 minutes. Guided, with starter and solution code.

---

## Why this exercise exists

You will spend the next ten weeks fusing, filtering, and correcting the body twist this node produces. If the twist is wrong here — a sign error on `ω`, a wheel-radius typo, the left and right joints swapped — every downstream estimate inherits the bug and you will chase it through an EKF and a SLAM graph where it is ten times harder to see. So we isolate the kinematics, feed them a known input, and confirm the output matches a hand calculation *before* we attach the integrator, the message, or the TF. This is the same discipline as a unit test: pin the smallest correct unit first.

---

## Setup

You need ROS2 Jazzy sourced and your Week 3 diff-drive robot able to spawn in Gz Sim. Verify the basics:

```bash
source /opt/ros/jazzy/setup.bash
ros2 --version          # should report jazzy
ros2 pkg list | grep sensor_msgs   # sensor_msgs is present
```

Bring up your Week 3 robot in Gz Sim and confirm `/joint_states` carries the two wheel joints with nonzero velocity when you drive it:

```bash
# terminal 1: your week-3 launch
ros2 launch crunchbot_bringup robot.launch.py

# terminal 2: drive it forward and turn
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.4}}"

# terminal 3: confirm the joint states populate
ros2 topic echo /joint_states --once
```

You should see a `sensor_msgs/JointState` with a `name` array containing your wheel joints (commonly `left_wheel_joint` and `right_wheel_joint`) and a `velocity` array with nonzero entries. **Note the exact joint names** — you will need them, and they differ between URDFs.

> **If your sim is down**, this exercise ships a standalone fallback publisher at the bottom (Step 5). It emits a `JointState` with a known, constant wheel velocity so you can develop the kinematics without the simulator. Use it, then re-run against the live robot once the sim is back.

---

## Step 1 — Scaffold the node

Create a working directory and a single file. We are deliberately *not* making a colcon package yet — that is the mini-project's job. Run this node directly with `python3`.

```bash
mkdir -p ~/crunch/week06 && cd ~/crunch/week06
touch diff_drive_fk.py
chmod +x diff_drive_fk.py
```

---

## Step 2 — The starter

Open `diff_drive_fk.py` and paste the starter. The kinematics are stubbed out with a `TODO` you will fill in. **The starter does not compute a correct twist** — it is the skeleton you complete.

```python
#!/usr/bin/env python3
"""Exercise 1 STARTER — diff-drive forward kinematics from /joint_states.

Fill in the two lines marked TODO. Do NOT add an integrator, a TF, or a
nav_msgs/Odometry message yet -- this exercise stops at the body twist.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class DiffDriveForwardKinematics(Node):
    def __init__(self):
        super().__init__("diff_drive_fk")

        # Kinematic parameters -- declared so you can override them on the
        # command line without editing the file (ROS2 parameter discipline).
        self.declare_parameter("wheel_radius", 0.05)        # r [m]
        self.declare_parameter("wheel_separation", 0.30)    # L [m]
        self.declare_parameter("left_joint", "left_wheel_joint")
        self.declare_parameter("right_joint", "right_wheel_joint")

        self.r = self.get_parameter("wheel_radius").value
        self.L = self.get_parameter("wheel_separation").value
        self.left_name = self.get_parameter("left_joint").value
        self.right_name = self.get_parameter("right_joint").value

        self.sub = self.create_subscription(
            JointState, "/joint_states", self.on_joint_states, 10
        )
        self.get_logger().info(
            f"diff_drive_fk up: r={self.r} L={self.L} "
            f"left='{self.left_name}' right='{self.right_name}'"
        )

    def on_joint_states(self, msg: JointState):
        # Map joint name -> velocity. velocity[] may be empty on some
        # publishers; we handle that in the solution, not here.
        try:
            li = msg.name.index(self.left_name)
            ri = msg.name.index(self.right_name)
        except ValueError:
            self.get_logger().warn(
                f"wheel joints not in /joint_states names={list(msg.name)}",
                throttle_duration_sec=2.0,
            )
            return

        phidot_L = msg.velocity[li]   # rad/s, left wheel angular velocity
        phidot_R = msg.velocity[ri]   # rad/s, right wheel angular velocity

        # TODO: compute body forward velocity vx and yaw rate w from the
        #       diff-drive forward kinematics (Lecture 2, section 2.3):
        #           vx = r * (phidot_R + phidot_L) / 2
        #           w  = r * (phidot_R - phidot_L) / L
        vx = 0.0   # <-- replace
        w = 0.0    # <-- replace

        self.get_logger().info(
            f"phidot_L={phidot_L:+.3f} phidot_R={phidot_R:+.3f}  ->  "
            f"vx={vx:+.3f} m/s  w={w:+.3f} rad/s",
            throttle_duration_sec=0.5,
        )


def main():
    rclpy.init()
    node = DiffDriveForwardKinematics()
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

Run it against the driving robot:

```bash
source /opt/ros/jazzy/setup.bash
python3 diff_drive_fk.py --ros-args \
  -p left_joint:=left_wheel_joint -p right_joint:=right_wheel_joint
```

With the `TODO` unfilled you will see `vx=+0.000 w=+0.000` regardless of how the wheels spin. That is the bug you fix in Step 3.

---

## Step 3 — Fill in the kinematics

Replace the two `TODO` lines with the forward kinematics. This is the entire point of the exercise:

```python
        vx = self.r * (phidot_R + phidot_L) / 2.0
        w = self.r * (phidot_R - phidot_L) / self.L
```

Re-run. Now when you `ros2 topic pub /cmd_vel "{linear: {x: 0.3}, angular: {z: 0.4}}"`, the node should report `vx ≈ +0.300 m/s` and `w ≈ +0.400 rad/s` — recovering the command you sent, because forward-then-inverse-then-forward kinematics is the identity for a square Jacobian (Lecture 2, §2.4).

> **Watch the sign of `ω`.** If `vx` comes out right but `ω` has the wrong sign, your `left_joint` and `right_joint` parameters are swapped. The fix is to swap the two parameters, *not* to negate the equation — negating hides the real bug and bites you when someone reuses the node on a robot whose joints are named the other way.

---

## Step 4 — Verify against a hand calculation

Stop driving in circles and command a *pure* motion you can check by hand. Drive straight first:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

With `r = 0.05`, a `vₓ = 0.2 m/s` command requires both wheels at `φ̇ = vₓ/r = 0.2/0.05 = 4.0 rad/s`. Confirm the node reports `vx ≈ +0.200` and `w ≈ 0.000`. Then command a pure spin:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.5}}"
```

A pure `ω = 0.5 rad/s` with `L = 0.30` requires `φ̇_R = +ω·L/(2r) = 0.5·0.30/(2·0.05) = +1.5 rad/s` and `φ̇_L = −1.5 rad/s`. The node should report `vx ≈ 0.000` and `w ≈ +0.500`. **Do this calculation on paper before you read the node's output.** Matching your hand number to the node's output is the verification that you understand the kinematics, not just that they typecheck.

---

## Step 5 — The fallback joint-state publisher (if your sim is down)

If Gz Sim is unavailable, run this alongside the node. It publishes a `JointState` at 50 Hz with constant wheel velocities matching a known command, so you can verify the kinematics with no simulator. Save as `fake_joint_states.py` and run it in a separate terminal.

```python
#!/usr/bin/env python3
"""Standalone /joint_states publisher for Exercise 1 when the sim is down.

Publishes a constant-velocity JointState that corresponds to a known command:
the inverse kinematics of vx=0.2 m/s, w=0.5 rad/s with r=0.05, L=0.30.
The FK node should recover vx=+0.200, w=+0.500.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class FakeJointStates(Node):
    def __init__(self):
        super().__init__("fake_joint_states")
        self.pub = self.create_publisher(JointState, "/joint_states", 10)

        r, L = 0.05, 0.30
        vx, w = 0.2, 0.5                       # the command we encode
        # inverse kinematics (Lecture 2, section 2.4):
        self.phidot_R = (vx + w * L / 2.0) / r  # +5.5 rad/s
        self.phidot_L = (vx - w * L / 2.0) / r  # +2.5 rad/s

        self.timer = self.create_timer(0.02, self.tick)   # 50 Hz
        self.get_logger().info(
            f"faking joint_states: phidot_L={self.phidot_L:.3f} "
            f"phidot_R={self.phidot_R:.3f} rad/s "
            f"(expect FK node to report vx=+0.200 w=+0.500)"
        )

    def tick(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = ["left_wheel_joint", "right_wheel_joint"]
        msg.velocity = [self.phidot_L, self.phidot_R]
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = FakeJointStates()
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

Run the fallback and the FK node together:

```bash
# terminal 1
python3 fake_joint_states.py
# terminal 2
python3 diff_drive_fk.py
```

---

## The full solution

Here is `diff_drive_fk.py` complete, with the one robustness fix the starter omitted — handling an *empty* `velocity[]` array by differencing `position[]` instead. Real `JointState` publishers (including some Gz Sim configs) populate `position` but not `velocity`; a shippable node handles both.

```python
#!/usr/bin/env python3
"""Exercise 1 SOLUTION — diff-drive forward kinematics from /joint_states.

Computes the body twist (vx, w) from the two wheel-joint angular velocities.
Falls back to differencing wheel POSITION across messages when the publisher
leaves velocity[] empty.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class DiffDriveForwardKinematics(Node):
    def __init__(self):
        super().__init__("diff_drive_fk")
        self.declare_parameter("wheel_radius", 0.05)
        self.declare_parameter("wheel_separation", 0.30)
        self.declare_parameter("left_joint", "left_wheel_joint")
        self.declare_parameter("right_joint", "right_wheel_joint")

        self.r = self.get_parameter("wheel_radius").value
        self.L = self.get_parameter("wheel_separation").value
        self.left_name = self.get_parameter("left_joint").value
        self.right_name = self.get_parameter("right_joint").value

        self.last_pos = None      # (phi_L, phi_R) from the previous message
        self.last_stamp = None    # rclpy.time.Time of the previous message

        self.sub = self.create_subscription(
            JointState, "/joint_states", self.on_joint_states, 10
        )
        self.get_logger().info(
            f"diff_drive_fk up: r={self.r} L={self.L} "
            f"left='{self.left_name}' right='{self.right_name}'"
        )

    def _wheel_velocities(self, msg, li, ri):
        """Return (phidot_L, phidot_R). Prefer velocity[]; fall back to
        differencing position[] across consecutive messages."""
        if msg.velocity and len(msg.velocity) > max(li, ri):
            return msg.velocity[li], msg.velocity[ri]

        # velocity[] empty -> difference position over the message dt
        if not (msg.position and len(msg.position) > max(li, ri)):
            return None
        stamp = rclpy.time.Time.from_msg(msg.header.stamp)
        pos = (msg.position[li], msg.position[ri])
        if self.last_pos is None or self.last_stamp is None:
            self.last_pos, self.last_stamp = pos, stamp
            return None
        dt = (stamp - self.last_stamp).nanoseconds * 1e-9
        if dt <= 0.0:
            return None
        phidot_L = (pos[0] - self.last_pos[0]) / dt
        phidot_R = (pos[1] - self.last_pos[1]) / dt
        self.last_pos, self.last_stamp = pos, stamp
        return phidot_L, phidot_R

    def on_joint_states(self, msg: JointState):
        try:
            li = msg.name.index(self.left_name)
            ri = msg.name.index(self.right_name)
        except ValueError:
            self.get_logger().warn(
                f"wheel joints not in /joint_states names={list(msg.name)}",
                throttle_duration_sec=2.0,
            )
            return

        vels = self._wheel_velocities(msg, li, ri)
        if vels is None:
            return
        phidot_L, phidot_R = vels

        # --- diff-drive forward kinematics (Lecture 2, section 2.3) ---
        vx = self.r * (phidot_R + phidot_L) / 2.0
        w = self.r * (phidot_R - phidot_L) / self.L

        self.get_logger().info(
            f"phidot_L={phidot_L:+.3f} phidot_R={phidot_R:+.3f}  ->  "
            f"vx={vx:+.3f} m/s  w={w:+.3f} rad/s",
            throttle_duration_sec=0.5,
        )


def main():
    rclpy.init()
    node = DiffDriveForwardKinematics()
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

---

## Expected output

Driving forward at `0.2 m/s` (or running the fallback's straight equivalent), the node logs lines shaped like this:

```
[INFO] [diff_drive_fk]: diff_drive_fk up: r=0.05 L=0.3 left='left_wheel_joint' right='right_wheel_joint'
[INFO] [diff_drive_fk]: phidot_L=+4.000 phidot_R=+4.000  ->  vx=+0.200 m/s  w=+0.000 rad/s
```

Commanding the pure spin from Step 4 (`ω = 0.5 rad/s`):

```
[INFO] [diff_drive_fk]: phidot_L=-1.500 phidot_R=+1.500  ->  vx=+0.000 m/s  w=+0.500 rad/s
```

Running the fallback publisher (`vₓ = 0.2`, `ω = 0.5`):

```
[INFO] [diff_drive_fk]: phidot_L=+2.500 phidot_R=+5.500  ->  vx=+0.200 m/s  w=+0.500 rad/s
```

If your `vₓ` matches but `ω` is negated, swap the joint parameters. If both are scaled by a constant factor, your `wheel_radius` is wrong. If `ω` alone is scaled, your `wheel_separation` is wrong. These three failure signatures map one-to-one onto the parameter that is off — memorize them, because they are exactly the calibration errors of Lecture 1.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] The node subscribes to `/joint_states`, finds the two wheel joints by name, and logs `vx` and `w`.
- [ ] Driving straight at a known speed produces a `vx` that matches `r · φ̇` and a `w` near zero.
- [ ] A pure spin produces a `w` that matches `r(φ̇_R − φ̇_L)/L` and a `vx` near zero, with the **correct sign**.
- [ ] You did the hand calculation in Step 4 *before* reading the node's output, and the numbers matched.
- [ ] The node accepts `wheel_radius`, `wheel_separation`, `left_joint`, and `right_joint` as ROS2 parameters (no hard-coded joint names).
- [ ] You can state, in one sentence each, which parameter is wrong for each of the three failure signatures above.

---

## Stretch

- Add a `--ros-args -p use_position_fallback:=true` path and test it against a publisher that leaves `velocity[]` empty (Gz Sim's `joint_state_publisher` can be configured either way).
- Publish the computed twist as a `geometry_msgs/TwistStamped` on `/diff_drive/twist` so you can plot it in PlotJuggler. (This is the bridge to Exercise 2, which integrates the twist into a pose.)
- Print the instantaneous center of rotation radius `R_ICR = vₓ/ω` (guard `|ω| > 1e-6`) and confirm it goes to infinity on a straight and to zero on a spin-in-place (Lecture 2, §2.3).

---

When the kinematics feel solid, move to [Exercise 2 — Publish `/odom` and the `odom → base_link` TF](exercise-02-odom-and-tf-publisher.py), which integrates this twist into a pose and broadcasts it.
