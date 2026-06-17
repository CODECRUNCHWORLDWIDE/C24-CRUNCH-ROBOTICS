# Exercise 1 — Sensor QoS on the Week-3 Robot

**Goal:** Take the sensor topics on your week-3 differential-drive robot, set them to the correct sensor profile (`BEST_EFFORT` / `KEEP_LAST` / depth 5), and *prove* with `ros2 topic info -v` that the publisher and every subscriber actually agree. You will train the single most important diagnostic habit of the week: reading the two QoS blocks and diffing them by eye.

**Estimated time:** 45 minutes. Guided.

---

## Setup

You need the **week-3 robot** spawning in Gz Sim and publishing `/scan` and `/imu/data`. Verify in two terminals (source your overlay in each):

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash          # your week-3 workspace overlay
ros2 launch crunchbot_bringup robot.launch.py     # whatever brings up your week-3 sim
```

```bash
ros2 topic list | grep -E "scan|imu"
# /imu/data
# /scan
```

**Fallback if your sim is broken.** Run the standalone sensor publisher below in one terminal. Every step works against it identically. Save it as `scan_pub.py` and run `python3 scan_pub.py`.

```python
#!/usr/bin/env python3
"""Standalone BEST_EFFORT LaserScan publisher — a stand-in for the week-3 LiDAR."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class FakeLidar(Node):
    def __init__(self) -> None:
        super().__init__("fake_lidar")
        # qos_profile_sensor_data == BEST_EFFORT / VOLATILE / KEEP_LAST(5).
        self.pub = self.create_publisher(LaserScan, "scan", qos_profile_sensor_data)
        self.timer = self.create_timer(1.0 / 30.0, self.tick)   # 30 Hz
        self.n = 360

    def tick(self) -> None:
        msg = LaserScan()
        # Stamp at acquisition time, set an honest frame_id (Lecture 2 §3).
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "laser_link"
        msg.angle_min = -math.pi
        msg.angle_max = math.pi
        msg.angle_increment = 2.0 * math.pi / self.n
        msg.range_min = 0.1
        msg.range_max = 12.0
        msg.ranges = [5.0] * self.n
        self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = FakeLidar()
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

## Step 1 — Look before you touch

Before you change a single line, photograph the current state. Run:

```bash
ros2 topic info /scan -v
```

Read the `QoS profile:` block under the **PUBLISHER**. On a stock `ros_gz_bridge` LiDAR this is often *wrong* — `RELIABLE` instead of `BEST_EFFORT`. Write down what you see. This is your "before."

If your robot already publishes `/scan` as `BEST_EFFORT` (a well-configured sim does), good — then this step is about the *subscriber* side, which is where the bug usually lives.

---

## Step 2 — Subscribe with the default profile and watch it fail (or stall)

Save this as `bad_listener.py`. It subscribes with the **default** profile (an integer depth, which `rclpy` interprets as `RELIABLE` / `KEEP_LAST(10)`):

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class BadListener(Node):
    def __init__(self) -> None:
        super().__init__("bad_listener")
        # Passing a bare int == KEEP_LAST(10) with the DEFAULT reliability (RELIABLE).
        self.sub = self.create_subscription(LaserScan, "scan", self.cb, 10)
        self.count = 0

    def cb(self, msg: LaserScan) -> None:
        self.count += 1
        self.get_logger().info(f"got scan #{self.count}")


def main() -> None:
    rclpy.init()
    node = BadListener()
    rclpy.spin(node)


if __name__ == "__main__":
    main()
```

Run it against a `BEST_EFFORT` publisher:

```bash
python3 bad_listener.py
```

If the publisher is `BEST_EFFORT`, **nothing prints.** The callback never fires. There is no error. This is the silent failure. Confirm the diagnosis:

```bash
ros2 topic info /scan -v
```

You will see one PUBLISHER (`BEST_EFFORT`) and one SUBSCRIPTION (`RELIABLE`). Two endpoints, both present, **incompatible**. The §3 request–offered rule: a `BEST_EFFORT` publisher cannot satisfy a `RELIABLE` subscriber. Stop `bad_listener.py`.

> If your robot's `/scan` is `RELIABLE`, `bad_listener.py` *will* receive — because `RELIABLE` satisfies a `RELIABLE` request. That doesn't mean it's correct; it means your sensor is paying the reliability tax it shouldn't. You'll fix the publisher in Step 4.

---

## Step 3 — Subscribe with the sensor profile

Save this as `good_listener.py`. The only difference is the QoS:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class GoodListener(Node):
    def __init__(self) -> None:
        super().__init__("good_listener")
        # Match the sensor publisher's BEST_EFFORT offer.
        self.sub = self.create_subscription(
            LaserScan, "scan", self.cb, qos_profile_sensor_data
        )
        self.count = 0

    def cb(self, msg: LaserScan) -> None:
        self.count += 1
        if self.count % 30 == 0:    # once a second at 30 Hz
            self.get_logger().info(
                f"scan #{self.count}: {len(msg.ranges)} beams, frame_id={msg.header.frame_id}"
            )


def main() -> None:
    rclpy.init()
    node = GoodListener()
    rclpy.spin(node)


if __name__ == "__main__":
    main()
```

```bash
python3 good_listener.py
```

Now the callback fires. You should see roughly one line per second:

```
[INFO] [good_listener]: scan #30: 360 beams, frame_id=laser_link
[INFO] [good_listener]: scan #60: 360 beams, frame_id=laser_link
```

---

## Step 4 — Verify both endpoints agree

With `good_listener.py` still running:

```bash
ros2 topic info /scan -v
```

You are looking for the **connection-formed promise** from the week README — both endpoints printing the *same* QoS:

```
Type: sensor_msgs/msg/LaserScan

Publisher count: 1

Node name: fake_lidar
Endpoint type: PUBLISHER
QoS profile:
  Reliability: BEST_EFFORT
  History (Depth): KEEP_LAST (5)
  Durability: VOLATILE
  Lifespan: Infinite
  Deadline: Infinite
  Liveliness: AUTOMATIC
  Liveliness lease duration: Infinite

Subscription count: 1

Node name: good_listener
Endpoint type: SUBSCRIPTION
QoS profile:
  Reliability: BEST_EFFORT
  History (Depth): KEEP_LAST (5)
  Durability: VOLATILE
  ...
```

**Both say `BEST_EFFORT`. Both say `KEEP_LAST (5)`. Connection formed.** That is the line we want to make ordinary.

If your *robot's* publisher was `RELIABLE` (the stock-bridge case), this is where you fix it. For a `ros_gz_bridge`, the bridge YAML lets you set the QoS override; for a sensor plugin, the QoS is set where the publisher is created. Re-run `ros2 topic info /scan -v` and confirm the publisher now reads `BEST_EFFORT`.

---

## Step 5 — Do the same for `/imu/data`

Repeat steps 2–4 for `/imu/data` (type `sensor_msgs/msg/Imu`). Change `LaserScan` to `Imu` and the topic name. IMU is the same *class* as LiDAR — a sensor stream — so it gets the same profile. Confirm with:

```bash
ros2 topic info /imu/data -v
```

Both endpoints should read `BEST_EFFORT` / `KEEP_LAST (5)`.

---

## Step 6 — Confirm `ros2 doctor` is clean

```bash
ros2 doctor
```

You want `All <N> checks passed`. If `ros2 doctor` flags a QoS-incompatibility warning, you missed an endpoint somewhere — go find it with `ros2 topic info -v`.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `ros2 topic info /scan -v` shows the PUBLISHER and the SUBSCRIPTION **both** reading `Reliability: BEST_EFFORT` and `History (Depth): KEEP_LAST (5)`.
- [ ] `ros2 topic info /imu/data -v` shows the same agreement for the IMU.
- [ ] `good_listener.py` prints a scan line every ~30 callbacks; `bad_listener.py` prints nothing against a `BEST_EFFORT` publisher.
- [ ] You can state, in one sentence, *why* `bad_listener.py` received nothing (a `BEST_EFFORT` publisher cannot satisfy a `RELIABLE` subscriber).
- [ ] `ros2 doctor` reports all checks passed.

---

## Stretch

- Set a **100 ms deadline** on `good_listener.py`'s subscription QoS and register a deadline-missed callback (Lecture 1 §2.4). Kill the publisher and watch the callback fire — you've built a sensor watchdog in the QoS layer.
- Run `ros2 topic hz /scan` while `good_listener.py` runs. Confirm ~30 Hz. Then start three more `good_listener.py` instances. Does the rate hold? (`BEST_EFFORT` fan-out is cheap; this is *why* sensors use it.)
- Switch `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` (restart everything) and re-run `ros2 topic info /scan -v`. The QoS is identical — QoS is portable across vendors. Confirm that for yourself.

---

When this feels comfortable, move to [Exercise 2 — The latched map](./exercise-02-latched-map.py).
