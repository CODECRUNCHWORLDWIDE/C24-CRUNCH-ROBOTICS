# Exercise 1 — The Decision Ladder and a `ResetOdometry` Service

**Goal:** Cement the topic → service → action → behavior-tree decision ladder by classifying ten real problems and defending each choice, then write a working `ResetOdometry` service server and an async client in `rclpy`. By the end you can place any communication problem on the ladder and write a service without looking anything up.

**Estimated time:** 90 minutes (30 min classification, 60 min code).

**You will need:** ROS2 Jazzy on Ubuntu 24.04, a sourced environment (`source /opt/ros/jazzy/setup.bash`), and a `colcon` workspace.

---

## Part A — Classify ten problems (30 min)

For each problem below, decide the correct rung — **Topic**, **Service**, **Action**, or **Behavior Tree** — and write one sentence of justification using the five questions (reply? result? feedback? cancel? compose?). Write your answers in a file `part-a-classification.md`. There is an answer key at the bottom of this file; do not look until you have committed to all ten.

1. Broadcast the static transform from `base_link` to the LiDAR mount.
2. Ask the battery node for the current charge percentage.
3. Rotate the robot 90° in place using closed-loop IMU yaw.
4. Stream the depth camera's point cloud at 15 Hz to three subscribers.
5. Set the active map by name, getting back confirmation it loaded.
6. Drive the robot to the charging dock, allowing the operator to cancel.
7. Patrol four waypoints; if a person blocks the path, wait, then re-plan; if blocked over 90 s, return to dock.
8. Tell the LED ring to turn red, and confirm it changed.
9. Publish wheel odometry at 50 Hz for the EKF to consume.
10. Compute the inverse kinematics for one target end-effector pose (a fast pure computation returning one joint solution).

**Rule for grading yourself:** the justification matters more than the label. "Action, because it commands actuators for several seconds and the operator must be able to cancel it" is a pass. "Action, because it feels important" is a fail.

---

## Part B — Write a `ResetOdometry` service (60 min)

You will build a service that resets a node's internal odometry estimate to a requested pose and replies with a confirmation. This is the service the challenge and the mini-project assume you can write from memory.

### Step 1 — Create the interfaces package

A service needs its `.srv` type built once. We put it in a dedicated interfaces package because interfaces should not depend on node code.

```bash
mkdir -p ~/crunch_ws/src && cd ~/crunch_ws/src
ros2 pkg create crunch_motion_interfaces \
  --build-type ament_cmake \
  --dependencies geometry_msgs
mkdir -p crunch_motion_interfaces/srv
```

Create `crunch_motion_interfaces/srv/ResetOdometry.srv`:

```
# Request: the pose to reset odometry to (usually all zeros).
geometry_msgs/Pose2D pose
---
# Response: did it work, and a human-readable message.
bool success
string message
```

In `crunch_motion_interfaces/CMakeLists.txt`, after the `find_package(ament_cmake REQUIRED)` line, add:

```cmake
find_package(rosidl_default_generators REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/ResetOdometry.srv"
  DEPENDENCIES geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)
```

In `crunch_motion_interfaces/package.xml`, add inside `<package>`:

```xml
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<depend>geometry_msgs</depend>
<member_of_group>rosidl_interface_packages</member_of_group>
<exec_depend>rosidl_default_runtime</exec_depend>
```

Build it and source:

```bash
cd ~/crunch_ws
colcon build --packages-select crunch_motion_interfaces
source install/setup.bash
```

Verify the type exists:

```bash
ros2 interface show crunch_motion_interfaces/srv/ResetOdometry
```

You should see your request/response fields printed back.

### Step 2 — Create the node package

```bash
cd ~/crunch_ws/src
ros2 pkg create crunch_motion \
  --build-type ament_python \
  --dependencies rclpy geometry_msgs crunch_motion_interfaces
```

### Step 3 — Write the server

Create `crunch_motion/crunch_motion/odometry_service.py`:

```python
"""A minimal ResetOdometry service server.

The service callback does microseconds of work and returns immediately. That
is the entire point of a service: if this needed a control loop, it would be
an action instead. Run it, then call it from the CLI or the client below.
"""

import rclpy
from rclpy.node import Node

from crunch_motion_interfaces.srv import ResetOdometry


class OdometryService(Node):
    def __init__(self) -> None:
        super().__init__("odometry_service")
        # The node's authoritative odometry estimate. A real node would also
        # publish this on a topic; here we only expose the reset service.
        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0
        self._srv = self.create_service(
            ResetOdometry, "reset_odometry", self._reset_callback
        )
        self.get_logger().info("reset_odometry service ready")

    def _reset_callback(
        self,
        request: ResetOdometry.Request,
        response: ResetOdometry.Response,
    ) -> ResetOdometry.Response:
        # Fast, non-blocking, side-effect-only. No sleeps, no loops, no I/O.
        self._x = request.pose.x
        self._y = request.pose.y
        self._theta = request.pose.theta
        response.success = True
        response.message = (
            f"odometry reset to ({self._x:.3f}, {self._y:.3f}, {self._theta:.3f})"
        )
        self.get_logger().info(response.message)
        return response


def main() -> None:
    rclpy.init()
    node = OdometryService()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
```

### Step 4 — Write the async client

Create `crunch_motion/crunch_motion/odometry_client.py`:

```python
"""An async ResetOdometry client.

Inside a node we ALWAYS call_async and handle the Future. A synchronous
call() from a callback would deadlock the executor — the one thread that
processes the response would be blocked waiting for it.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose2D

from crunch_motion_interfaces.srv import ResetOdometry


class OdometryClient(Node):
    def __init__(self) -> None:
        super().__init__("odometry_client")
        self._client = self.create_client(ResetOdometry, "reset_odometry")
        while not self._client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info("waiting for reset_odometry service...")

    def reset(self, x: float, y: float, theta: float):
        request = ResetOdometry.Request()
        request.pose = Pose2D(x=x, y=y, theta=theta)
        future = self._client.call_async(request)
        future.add_done_callback(self._on_response)
        return future

    def _on_response(self, future) -> None:
        response = future.result()
        self.get_logger().info(
            f"server replied: success={response.success}, msg='{response.message}'"
        )
        # We asked for one reset; shut down cleanly once we have the answer.
        rclpy.shutdown()


def main() -> None:
    rclpy.init()
    node = OdometryClient()
    node.reset(0.0, 0.0, 0.0)
    rclpy.spin(node)
    node.destroy_node()


if __name__ == "__main__":
    main()
```

### Step 5 — Register the entry points

In `crunch_motion/setup.py`, in the `console_scripts` list, add:

```python
entry_points={
    "console_scripts": [
        "odometry_service = crunch_motion.odometry_service:main",
        "odometry_client = crunch_motion.odometry_client:main",
    ],
},
```

### Step 6 — Build, run, verify

```bash
cd ~/crunch_ws
colcon build --packages-select crunch_motion
source install/setup.bash
```

Terminal 1 — the server:

```bash
ros2 run crunch_motion odometry_service
```

Terminal 2 — drive it from the CLI first (no client needed):

```bash
ros2 service call /reset_odometry crunch_motion_interfaces/srv/ResetOdometry \
  "{pose: {x: 1.0, y: 2.0, theta: 0.5}}"
```

Expected output in Terminal 2:

```
requester: making request: crunch_motion_interfaces.srv.ResetOdometry_Request(...)

response:
crunch_motion_interfaces.srv.ResetOdometry_Response(success=True, message='odometry reset to (1.000, 2.000, 0.500)')
```

And in Terminal 1:

```
[INFO] [odometry_service]: odometry reset to (1.000, 2.000, 0.500)
```

Now run the client node:

```bash
ros2 run crunch_motion odometry_client
```

Expected client output:

```
[INFO] [odometry_client]: server replied: success=True, msg='odometry reset to (0.000, 0.000, 0.000)'
```

---

## Acceptance criteria

- [ ] `part-a-classification.md` exists with ten labels and ten one-sentence justifications.
- [ ] `crunch_motion_interfaces` builds and `ros2 interface show` prints the `ResetOdometry` type.
- [ ] The server prints `reset_odometry service ready` and logs each reset.
- [ ] `ros2 service call` returns `success=True` with the expected message.
- [ ] The async client logs the server's reply and exits cleanly (no traceback, no hang).
- [ ] You did **not** put a `sleep` or a loop in the service callback. (If you were tempted to, that operation wanted to be an action.)

---

## Part A answer key (look only after you've committed to all ten)

1. **Topic** — a static TF broadcast is fire-and-forget streaming data; no reply needed.
2. **Service** — a fast query with a single computed answer; no progress, no cancel.
3. **Action** — commands actuators for several seconds; the caller wants feedback and *must* be able to cancel.
4. **Topic** — high-rate sensor data, many subscribers, latest frame matters, no reply.
5. **Service** — a quick state change with a confirmation; loading a named map is fast and returns one answer. (If map-loading were slow and cancellable, it would be an action — judge by duration.)
6. **Action** — long-running actuator command with explicit cancellation; this is literally Nav2's `NavigateToPose`.
7. **Behavior Tree** — orchestration of multiple actions with waiting, re-planning, a timeout, and a recovery branch.
8. **Service** — instant state change *with confirmation*; the confirmation is what tips it from a topic to a service.
9. **Topic** — periodic sensor/state stream consumed by a filter; no reply, latest value matters.
10. **Service** — a fast pure computation returning one result; no long-running work, no cancel needed.

If you scored your justifications honestly and got at least 8/10 with sound reasoning, you are ready for Exercise 2. The two most-missed are #5 and #8 (people reach for topics and forget the confirmation tips them to a service) and #10 (people assume "kinematics" means "slow," but a single IK solve is microseconds).
