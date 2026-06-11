# Challenge 1 — Diagnose Three Depth Failures on a Live Stream

**Time estimate:** ~90 minutes.

## Problem statement

You are on call. A teammate's perception node "works in the lab but does dumb things in the hallway": it stops for nothing, it grasps at air near object edges, and once it reported a wall at 1500 metres. All three are depth failures — three *different* failures across three *different* failure classes from Lecture 1 — and none of them throws an exception. Your job is to find each one from its **signature**, explain the physics or encoding behind it, and prescribe the fix.

You will run a fault-injection harness that publishes a depth stream with all three faults, then **detect, diagnose, and prescribe the fix** for each, using only depth introspection and the projected cloud. No reading the harness fault list until you've diagnosed all three from the outside — that's the whole point. This mirrors the real skill: you rarely debug depth in code you just wrote; you debug it on a stream someone else produced, from the cloud inward.

## The harness

Save this as `faulty_depth.py`. It publishes a synthetic depth stream (`/faulty/depth/image_rect_raw`) and the matching `CameraInfo` (`/faulty/depth/camera_info`), with three planted faults. Run it and leave it running while you diagnose from other terminals. Do **not** read the fault comments until you've made your three diagnoses.

```python
#!/usr/bin/env python3
"""Fault-injection harness: a depth stream with three planted failures.
Do NOT read the fault choices below until you have diagnosed all three from the
projected cloud / depth image from the outside."""
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Header


class FaultyDepth(Node):
    def __init__(self) -> None:
        super().__init__("faulty_depth")
        self.h, self.w = 240, 320
        self.fx = self.fy = 240.0
        self.cx, self.cy = self.w / 2.0, self.h / 2.0
        self.depth_pub = self.create_publisher(
            Image, "/faulty/depth/image_rect_raw", qos_profile_sensor_data)
        self.info_pub = self.create_publisher(
            CameraInfo, "/faulty/depth/camera_info", qos_profile_sensor_data)
        self.rng = np.random.default_rng(0)
        self.create_timer(1.0 / 30.0, self.tick)

    def scene(self) -> np.ndarray:
        """Base scene: a wall at 1.2 m, a box at 0.7 m, floor ramp. (metres)"""
        d = np.full((self.h, self.w), 1.2, dtype=np.float32)
        d[self.h // 3 : 2 * self.h // 3, self.w // 3 : 2 * self.w // 3] = 0.7  # box
        d += self.rng.normal(0, 0.004, size=d.shape)                          # noise

        # --- Planted fault #1: a "glass" panel (top-left) reads as the FAR
        #     wall BEHIND it (2.5 m), not as a hole. The camera sees through
        #     the glass; nothing tells downstream this region is unmeasurable.
        d[:60, :60] = 2.5

        # --- Planted fault #2: flying pixels at the box's right edge — a skirt
        #     of points smeared between the box (0.7) and the wall (1.2).
        edge = 2 * self.w // 3
        for k in range(6):
            d[self.h // 3 : 2 * self.h // 3, edge + k] = 0.7 + 0.083 * (k + 1)
        return d

    def tick(self) -> None:
        d_m = self.scene()
        # --- Planted fault #3: published as 16UC1 MILLIMETRES, but the header
        #     ENCODING is mislabeled "32FC1". A consumer that trusts the
        #     encoding reads mm as if they were metres -> 1000x.
        depth_mm = (d_m * 1000.0).astype(np.uint16)
        msg = Image()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "faulty_depth_optical_frame"
        msg.height, msg.width = self.h, self.w
        msg.encoding = "32FC1"                 # <-- LIE: data is really 16UC1 mm
        msg.step = self.w * 2                  # ...and the step says 2 bytes/px (16-bit)
        msg.data = depth_mm.tobytes()
        self.depth_pub.publish(msg)

        info = CameraInfo()
        info.header = msg.header
        info.height, info.width = self.h, self.w
        info.k = [self.fx, 0.0, self.cx, 0.0, self.fy, self.cy, 0.0, 0.0, 1.0]
        self.info_pub.publish(info)


def main() -> None:
    rclpy.init()
    node = FaultyDepth()
    node.get_logger().info("faulty depth running. Diagnose from other terminals.")
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

```bash
source /opt/ros/jazzy/setup.bash
python3 faulty_depth.py
```

Your tools: project the cloud (your Exercise 2 projector, pointed at `/faulty/...`), view it in rviz2, and inspect the raw depth with `ros2 topic echo --field encoding`, `--field step`, and a small NumPy script that reads `/faulty/depth/image_rect_raw` and prints `min/max/dtype`.

## Your task

For **each of the three faults**, produce a diagnosis with these four parts:

1. **Symptom** — what's observably wrong (in the cloud, in rviz2, or in the raw-array stats).
2. **Failure class** — which Lecture-1 category it is (glass/specular hole, flying pixels at a discontinuity, or an encoding/unit bug) and the physics or encoding behind it.
3. **Why it's silent** — why no exception or error fires, and why a naïve consumer is fooled.
4. **Prescription** — the exact fix, in code or config (mask-and-flag the unmeasurable region; edge-aware filter / discontinuity reject; read the true encoding from `step`/data, not the lying header label).

You must reach each diagnosis using **at least two** independent signals — e.g., the cloud appearance *and* the raw-array `min/max`, or the rviz2 skirt *and* the per-pixel depth gradient. One signal is a guess; two is a diagnosis.

## Acceptance criteria

- [ ] A file `challenge-01-diagnosis.md` with a section per fault, each containing all four parts.
- [ ] You correctly identify each fault:
  - **Glass panel** — reads as the far surface behind it (2.5 m), not a hole. The camera sees *through* the glass; downstream treats the fabricated "wall behind the glass" as free space up to 2.5 m and drives into the glass. **Class: transparent-surface failure.**
  - **Flying pixels** — a 6-pixel skirt ramping 0.7 → 1.2 m at the box's right edge: points floating in empty space between the box and the wall. **Class: depth-discontinuity / flying pixels.**
  - **Unit/encoding bug** — the header says `32FC1` but the bytes are `16UC1` millimetres (`step = 2·width` gives it away — `32FC1` would be `4·width`). A consumer trusting the label reads mm as metres → everything 1000× too far. **Class: encoding/unit bug.**
- [ ] For the glass and flying-pixel faults, you show **at least one** quantitative signal (e.g. the depth gradient at the edge for flying pixels; the connected-region depth jump for the glass).
- [ ] For the unit bug, you show that `step / width = 2` proves the data is 16-bit, contradicting the `32FC1` label — you diagnosed it from the *bytes*, not the *label*.
- [ ] A `fixed_consumer.py` — a depth consumer that (a) detects the true encoding from `step`, (b) rejects flying pixels by a discontinuity gradient threshold, and (c) flags the glass region as *unmeasurable* (drops it, does not treat it as free space). Run against the harness, its output cloud is clean and the glass region is empty/flagged rather than a fake far wall.
- [ ] Committed to your Week 14 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The glass fault is the dangerous one and the most realistic. It does **not** present as a hole — that would be honest. It presents as a *plausible* surface at 2.5 m (whatever the IR happened to bounce off behind the glass), so a naïve consumer treats the space up to 2.5 m as free and drives into the glass. The fix is **not** "fill the hole" (there is no hole) and **not** "trust the 2.5 m" (it's fabricated). The fix is to recognize that this region is *unmeasurable* — in the real world you detect it with a confidence map, a multi-return check, or a secondary sensor (ultrasonic). Prescribing "just use the 2.5 m reading" is the wrong fix and you must not write it; the whole hazard is that the reading *looks* valid.

## Stretch

- Add a fourth fault: set the box region to `0` (an honest hole) and show your `fixed_consumer.py` distinguishes the *honest* hole (drop, mark unknown) from the *dishonest* glass reading (a fake far surface). The difference between "I don't know" and "I'm confidently wrong" is the entire safety story of depth.
- Re-run with the harness publishing `32FC1` *correctly* (real metres) and confirm your `step`-based encoding detector still reads it right — your fix must not break the honest case.
- Write a 10-line script that, given a depth topic, prints `encoding`, `step`, `step/width`, and `min/max` of the raw array side by side, so an encoding/unit bug is obvious at a glance.

## Why this matters

At the Week 16 midterm you defend your perception stack to a panel. They will not ask you to recite the four depth technologies — they'll point at your point cloud and ask "what here is real, what did the camera invent, and how does your stack know the difference?" This challenge *is* that conversation, rehearsed. Every robotics deployment eventually hands you a depth stream that confidently reports geometry that isn't there. The engineer who can name the glass, the flying pixels, and the unit bug from the cloud in five minutes is the one whose robot doesn't drive into the glass door on demo day.
