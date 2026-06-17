# Exercise 1 — Bring Up the RGB-D Camera and Synchronize It

**Goal:** Bring up an RGB-D camera (real RealSense, simulated, or a recorded bag), confirm every stream has the correct sensor QoS, and synchronize color + depth + camera-info with `message_filters` so you have a *matched set* to fuse — not "the latest of each," which smears color on moving objects. You will train two habits: reading `ros2 topic info -v` on a depth camera's five streams, and never trusting an unsynchronized RGB-D pair.

**Estimated time:** 50 minutes. Guided.

---

## Setup

Pick your path. The rest of the exercise is identical from Step 1 on.

**Path A — RealSense D435i (or D455).** Install the driver and launch it:

```bash
sudo apt install ros-jazzy-realsense2-camera        # if not already installed
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true enable_color:=true enable_sync:=true \
  align_depth.enable:=true enable_gyro:=true enable_accel:=true \
  unite_imu_method:=2
```

**Path B — simulated RGB-D in Gz Sim.** Add an `RgbdCamera` sensor to your week-3 robot's URDF and bridge it with `ros_gz_image`. The resources file links the sensor config; the topics come out as `/camera/...` to match.

**Path C — recorded bag (no camera, no sim).** Download the sample RealSense bag the resources point to and play it on loop:

```bash
ros2 bag play realsense_sample.bag --loop \
  --qos-profile-overrides-path qos_overrides.yaml     # force sensor QoS on playback (Week 5 §3.7)
```

Confirm the streams exist and tick:

```bash
ros2 topic list | grep camera
ros2 topic hz /camera/depth/image_rect_raw            # expect ~30 Hz
ros2 topic hz /camera/color/image_raw                 # expect ~30 Hz
```

---

## Step 1 — Audit the QoS of every stream

A depth camera is five sensor streams, and every one of them must be `BEST_EFFORT` (Week 5). Audit them:

```bash
for t in /camera/color/image_raw /camera/depth/image_rect_raw \
         /camera/aligned_depth_to_color/image_raw /camera/imu; do
  echo "=== $t ==="
  ros2 topic info "$t" -v
done
```

Read the `Reliability:` line under each PUBLISHER. You want `BEST_EFFORT` on all of them. Write down what you see — this is your "before."

> **The trap:** if you now write a subscriber with the default profile (a bare integer QoS, which `rclpy` reads as `RELIABLE`), it will silently receive nothing from a `BEST_EFFORT` publisher. That's the Week 5 reliability mismatch, and on a depth camera it presents as "the camera isn't publishing" when it is. The fix is to subscribe with `qos_profile_sensor_data`.

---

## Step 2 — Read the intrinsics and the encoding

You'll need these in Exercise 2. Capture them now:

```bash
ros2 topic echo /camera/depth/camera_info --once
```

Find the `k` array — it's the row-major intrinsics matrix `K = [fx, 0, cx, 0, fy, cy, 0, 0, 1]`. Record `fx = k[0]`, `fy = k[4]`, `cx = k[2]`, `cy = k[5]`.

Then read the depth *encoding*:

```bash
ros2 topic echo /camera/depth/image_rect_raw --field encoding --once
# Expect: 16UC1   (millimetres)   — or 32FC1 (metres) on some configs.
```

**Write the encoding down.** Exercise 2's projector branches on it, and assuming the wrong one is the 1000× unit bug.

---

## Step 3 — The wrong way: zip the latest of each

Save this as `unsynced_listener.py`. It subscribes to color and depth separately and pairs whatever's latest:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class UnsyncedListener(Node):
    def __init__(self) -> None:
        super().__init__("unsynced_listener")
        self.last_color = None
        self.create_subscription(Image, "/camera/color/image_raw",
                                 self.on_color, qos_profile_sensor_data)
        self.create_subscription(Image, "/camera/aligned_depth_to_color/image_raw",
                                 self.on_depth, qos_profile_sensor_data)

    def on_color(self, msg: Image) -> None:
        self.last_color = msg

    def on_depth(self, msg: Image) -> None:
        if self.last_color is None:
            return
        # The stamp gap between this depth frame and the "latest" color frame:
        dt = abs((msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)
                 - (self.last_color.header.stamp.sec
                    + self.last_color.header.stamp.nanosec * 1e-9))
        self.get_logger().info(f"naive pair stamp gap: {dt * 1000:.1f} ms")


def main() -> None:
    rclpy.init()
    rclpy.spin(UnsyncedListener())


if __name__ == "__main__":
    main()
```

```bash
python3 unsynced_listener.py
```

Watch the "stamp gap." It bounces around — sometimes a millisecond, sometimes 20–40 ms. **Every one of those milliseconds is color painted onto where the scene was, not where the depth says it is.** On a static scene you won't see the error; wave your hand in front of the camera and the colored cloud (Exercise 2) will smear. Stop this listener.

---

## Step 4 — The right way: `ApproximateTimeSynchronizer`

Save this as `synced_listener.py`:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import message_filters
from sensor_msgs.msg import Image, CameraInfo


class SyncedListener(Node):
    def __init__(self) -> None:
        super().__init__("synced_listener")
        color = message_filters.Subscriber(
            self, Image, "/camera/color/image_raw",
            qos_profile=qos_profile_sensor_data)
        depth = message_filters.Subscriber(
            self, Image, "/camera/aligned_depth_to_color/image_raw",
            qos_profile=qos_profile_sensor_data)
        info = message_filters.Subscriber(
            self, CameraInfo, "/camera/color/camera_info",
            qos_profile=qos_profile_sensor_data)
        # slop = 20 ms: never pair frames more than ~half a 30Hz period apart.
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [color, depth, info], queue_size=10, slop=0.02)
        self.sync.registerCallback(self.on_rgbd)
        self.n = 0

    def on_rgbd(self, color: Image, depth: Image, info: CameraInfo) -> None:
        self.n += 1
        cs = color.header.stamp.sec + color.header.stamp.nanosec * 1e-9
        ds = depth.header.stamp.sec + depth.header.stamp.nanosec * 1e-9
        if self.n % 30 == 0:
            self.get_logger().info(
                f"matched set #{self.n}: color-depth gap {abs(cs - ds) * 1000:.1f} ms, "
                f"depth encoding={depth.encoding}, fx={info.k[0]:.1f}")


def main() -> None:
    rclpy.init()
    rclpy.spin(SyncedListener())


if __name__ == "__main__":
    main()
```

```bash
python3 synced_listener.py
```

Now every printed pair has a stamp gap **under 20 ms** — guaranteed by the `slop`. The callback only fires when color, depth, and info form a matched set. That is synchronization.

```
[INFO] [synced_listener]: matched set #30: color-depth gap 4.2 ms, depth encoding=16UC1, fx=615.3
[INFO] [synced_listener]: matched set #60: color-depth gap 3.8 ms, depth encoding=16UC1, fx=615.3
```

---

## Step 5 — Confirm the optical-frame TF exists

The depth optical frame is rotated relative to your robot body (Lecture 2 §1). Confirm the static transform is being published:

```bash
ros2 run tf2_ros tf2_echo base_link camera_depth_optical_frame
```

You should see a transform with a rotation that's roughly a 90° pair (the optical-frame convention). If `tf2_echo` reports it can't find the frame, your camera URDF/static transforms aren't loaded — fix that now, or every point cloud in Exercise 2 will be sideways.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `ros2 topic info -v` shows `Reliability: BEST_EFFORT` on color, depth, aligned depth, and IMU.
- [ ] You have recorded `fx, fy, cx, cy` from `/camera/depth/camera_info` and the depth `encoding` (`16UC1` or `32FC1`).
- [ ] `unsynced_listener.py` shows a *variable* stamp gap (sometimes 20+ ms); `synced_listener.py` shows every matched set under the 20 ms slop.
- [ ] You can state, in one sentence, why the unsynchronized pairing smears color on moving objects (color is painted onto where the scene was at the older stamp).
- [ ] `tf2_echo base_link camera_depth_optical_frame` resolves — the optical-frame TF exists.

---

## Stretch

- Add the **IMU** to the synchronizer? You can't directly — the IMU runs at ~200 Hz, far faster than the 30 Hz images, so `ApproximateTime` would throw away most IMU samples. Instead, log the IMU separately and note its rate with `ros2 topic hz /camera/imu`. (Fusing IMU with images is VIO, a later concern; the point here is to see *why* you don't naïvely sync streams of wildly different rates.)
- Switch `ExactTime` for `ApproximateTime` with `enable_sync:=true` on the RealSense (which stamps color and depth identically). Confirm `ExactTime` still fires — and confirm it *stops* firing if you turn `enable_sync` off, because then the stamps no longer match exactly.
- Run `ros2 topic hz` on all three image streams simultaneously and confirm the synchronizer's output rate is ≤ the slowest input rate. Synchronization can only ever *drop* frames to align them; it never invents matched sets.

---

When this feels comfortable, move to [Exercise 2 — Depth to point cloud](./exercise-02-depth-to-pointcloud.py).
