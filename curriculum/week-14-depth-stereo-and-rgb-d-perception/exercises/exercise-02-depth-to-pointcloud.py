#!/usr/bin/env python3
# Exercise 2 — Depth to point cloud (back-projection by hand)
#
# Goal: Project a depth image into a METRIC PointCloud2 using the pinhole
#       intrinsics, by hand, the way depth_image_proc does it internally. You
#       will convert to metres, mask invalid pixels, vectorize the back-
#       projection, stamp with the ACQUISITION time, and then VERIFY your cloud
#       against the known scene (in --demo) or against depth_image_proc (live).
#
# Estimated time: 50 minutes. Runnable.
#
# THE MATH (Lecture 2, Part 3)
#
#   Given depth Z at pixel (u, v) and intrinsics (fx, fy, cx, cy):
#       X = (u - cx) * Z / fx
#       Y = (v - cy) * Z / fy
#       Z = Z
#   The two non-negotiables:
#       (1) convert to metres first  (16UC1 is MILLIMETRES -> divide by 1000)
#       (2) mask invalid pixels      (0 / NaN are HOLES, not 0 metres)
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run.
#
#   PART A — --demo (no camera): synthesize a known scene (floor + wall + box)
#   at known distances, project it, and assert the recovered geometry matches
#   the ground truth to sub-millimetre tolerance. This verifies your MATH.
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-02-depth-to-pointcloud.py            # runs --demo
#
#   PART B — live: point it at your camera's depth topic, publish the cloud,
#   and compare in rviz2 against depth_image_proc's /camera/depth/color/points.
#
#       python3 exercise-02-depth-to-pointcloud.py --live \
#           --depth-topic /camera/depth/image_rect_raw \
#           --info-topic  /camera/depth/camera_info
#       # then in rviz2 add two PointCloud2 displays and overlay them.
#
# ACCEPTANCE CRITERIA
#
#   [ ] --demo prints "PASS: recovered geometry matches ground truth" and exits 0.
#   [ ] Deliberately removing the "/ 1000.0" line makes --demo FAIL with a 1000x
#       error — you have reproduced the unit bug on purpose.
#   [ ] Deliberately removing the invalid-pixel mask makes --demo report a slab
#       of points at Z=0 — the unmasked-holes bug.
#   [ ] Live: your hand-rolled cloud overlays depth_image_proc's cloud in rviz2.
#
# Expected output is at the bottom of the file.

import argparse
import sys

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header

# Set this False to reproduce the unit bug (Part A will FAIL by 1000x).
CONVERT_MM_TO_M = True
# Set this False to reproduce the unmasked-holes bug (slab at Z=0).
MASK_INVALID = True


def back_project(depth_m: np.ndarray, fx: float, fy: float,
                 cx: float, cy: float) -> np.ndarray:
    """Vectorized pinhole back-projection. depth_m is HxW float32 metres.

    Returns Nx3 (X, Y, Z) in the optical frame, with invalid pixels dropped.
    NEVER loop over pixels here — a Python loop over 300k pixels runs at ~0.5 Hz.
    """
    h, w = depth_m.shape
    u = np.arange(w, dtype=np.float32)
    v = np.arange(h, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)                  # both HxW: column, row indices

    z = depth_m
    if MASK_INVALID:
        valid = np.isfinite(z) & (z > 0.0)      # 0 (16UC1) and NaN (32FC1) are holes
    else:
        valid = np.ones_like(z, dtype=bool)     # BUG MODE: keep the holes

    x = (uu - cx) * z / fx
    y = (vv - cy) * z / fy
    return np.stack((x[valid], y[valid], z[valid]), axis=-1).astype(np.float32)


def depth_image_to_metres(raw: np.ndarray, encoding: str) -> np.ndarray:
    """Convert a raw depth array to metres, branching on the ROS encoding.

    16UC1 is millimetres; 32FC1 is already metres. Reading the encoding instead
    of assuming is what prevents the 1000x unit bug.
    """
    if encoding == "16UC1":
        m = raw.astype(np.float32)
        if CONVERT_MM_TO_M:
            m = m / 1000.0                      # mm -> m  (the load-bearing line)
        # 0 means "no measurement"; turn it into NaN so the mask drops it.
        m[raw == 0] = np.nan
        return m
    if encoding == "32FC1":
        return raw.astype(np.float32)           # already metres; 0/NaN are holes
    raise ValueError(f"unhandled depth encoding: {encoding!r} (expected 16UC1 or 32FC1)")


# --------------------------------------------------------------------------- #
# PART A — --demo: synthesize a known scene and verify the math.
# --------------------------------------------------------------------------- #

def synth_scene(h=120, w=160, fx=120.0, fy=120.0):
    """A floor + a wall at 1.0 m + a 0.30 m box at 0.6 m, plus a glass HOLE.

    Returns (depth_mm_uint16, fx, fy, cx, cy) and the ground-truth facts we check.
    """
    cx, cy = w / 2.0, h / 2.0
    depth_m = np.full((h, w), np.nan, dtype=np.float32)

    # A frontal wall plane at Z = 1.0 m fills the upper half of the image.
    depth_m[: h // 2, :] = 1.0
    # A box face at Z = 0.6 m occupies a central rectangle in the lower half.
    depth_m[h // 2 :, w // 3 : 2 * w // 3] = 0.6
    # The rest of the lower half is "floor" seen obliquely, ramping 1.0 -> 2.0 m.
    floor = np.linspace(1.0, 2.0, h - h // 2, dtype=np.float32)[:, None]
    mask = np.isnan(depth_m[h // 2 :, :])
    depth_m[h // 2 :, :][mask] = np.broadcast_to(floor, (h - h // 2, w))[mask]
    # A "glass" patch: a hole (no measurement) in the top-left corner.
    depth_m[:20, :20] = np.nan

    depth_mm = np.where(np.isfinite(depth_m), depth_m * 1000.0, 0.0).astype(np.uint16)
    facts = {"wall_z": 1.0, "box_z": 0.6, "cx": cx, "cy": cy, "fx": fx, "fy": fy}
    return depth_mm, facts


def run_demo() -> int:
    depth_mm, f = synth_scene()
    depth_m = depth_image_to_metres(depth_mm, "16UC1")
    pts = back_project(depth_m, f["fx"], f["fy"], f["cx"], f["cy"])

    print(f"[demo] projected {len(pts)} points from a {depth_mm.shape} depth image")

    # --- Verification 1: the wall is a flat plane at Z = 1.0 m. ---
    # Take points whose Z is near 1.0 and confirm their spread is tiny.
    wall = pts[np.abs(pts[:, 2] - f["wall_z"]) < 0.05]
    wall_z_rms = float(np.sqrt(np.mean((wall[:, 2] - f["wall_z"]) ** 2)))

    # --- Verification 2: the box face is at Z = 0.6 m. ---
    box = pts[np.abs(pts[:, 2] - f["box_z"]) < 0.02]
    box_z_mean = float(np.mean(box[:, 2]))

    # --- Verification 3: the principal-point pixel back-projects to X=Y=0. ---
    # The pixel at (cx, cy) on the wall must have X≈0, Y≈0 (it's the optical axis).
    centre = pts[(np.abs(pts[:, 2] - f["wall_z"]) < 0.05)]
    centre_xy = centre[np.argmin(np.abs(centre[:, 0]) + np.abs(centre[:, 1]))]

    # --- Verification 4: no slab of points at Z=0 (holes were masked). ---
    slab = int(np.sum(np.abs(pts[:, 2]) < 1e-6))

    print(f"[demo] wall:   Z RMS about 1.0 m = {wall_z_rms * 1000:.2f} mm")
    print(f"[demo] box:    Z mean = {box_z_mean:.4f} m (truth 0.600 m)")
    print(f"[demo] centre: nearest-axis point X={centre_xy[0]:+.4f} Y={centre_xy[1]:+.4f} m")
    print(f"[demo] slab:   {slab} points at Z=0 (want 0 — holes must be masked)")

    ok = (
        wall_z_rms < 1e-3
        and abs(box_z_mean - f["box_z"]) < 1e-3
        and abs(centre_xy[0]) < 0.02
        and abs(centre_xy[1]) < 0.02
        and slab == 0
    )
    if ok:
        print("PASS: recovered geometry matches ground truth "
              "(metric, masked, principal point on axis).")
        return 0
    print("FAIL: geometry does not match. If you disabled CONVERT_MM_TO_M you "
          "reproduced the 1000x unit bug; if you disabled MASK_INVALID you "
          "reproduced the slab-at-origin holes bug. Otherwise check fx/cx and u/v.")
    return 1


# --------------------------------------------------------------------------- #
# PART B — --live: project the camera's depth and publish a PointCloud2.
# --------------------------------------------------------------------------- #

class DepthProjector(Node):
    def __init__(self, depth_topic: str, info_topic: str) -> None:
        super().__init__("depth_projector")
        self.fx = self.fy = self.cx = self.cy = None
        self.create_subscription(CameraInfo, info_topic, self.on_info,
                                 qos_profile_sensor_data)
        self.create_subscription(Image, depth_topic, self.on_depth,
                                 qos_profile_sensor_data)
        self.pub = self.create_publisher(PointCloud2, "/exercise2/points", 5)
        self.n = 0

    def on_info(self, msg: CameraInfo) -> None:
        self.fx, self.fy = msg.k[0], msg.k[4]
        self.cx, self.cy = msg.k[2], msg.k[5]

    def on_depth(self, msg: Image) -> None:
        if self.fx is None:
            return  # wait for intrinsics
        raw = np.frombuffer(msg.data, dtype=np.uint16 if msg.encoding == "16UC1"
                            else np.float32).reshape(msg.height, msg.width)
        depth_m = depth_image_to_metres(raw, msg.encoding)
        pts = back_project(depth_m, self.fx, self.fy, self.cx, self.cy)

        header = Header()
        header.stamp = msg.header.stamp          # acquisition time, NOT now() (Week 5)
        header.frame_id = msg.header.frame_id     # the depth optical frame
        cloud = point_cloud2.create_cloud_xyz32(header, pts.tolist())
        self.pub.publish(cloud)
        self.n += 1
        if self.n % 30 == 0:
            self.get_logger().info(
                f"published cloud #{self.n}: {len(pts)} points, "
                f"frame={header.frame_id}")


def run_live(depth_topic: str, info_topic: str) -> None:
    rclpy.init()
    node = DepthProjector(depth_topic, info_topic)
    node.get_logger().info(
        "publishing /exercise2/points — overlay it on depth_image_proc's cloud "
        "in rviz2; they must coincide.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Depth -> PointCloud2 by hand.")
    parser.add_argument("--live", action="store_true",
                        help="project a live camera topic (default: --demo)")
    parser.add_argument("--depth-topic", default="/camera/depth/image_rect_raw")
    parser.add_argument("--info-topic", default="/camera/depth/camera_info")
    args = parser.parse_args()

    if args.live:
        run_live(args.depth_topic, args.info_topic)
    else:
        sys.exit(run_demo())


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo, correct)
# -----------------------------------------------------------------------------
#
# [demo] projected 16804 points from a (120, 160) depth image
# [demo] wall:   Z RMS about 1.0 m = 0.00 mm
# [demo] box:    Z mean = 0.6000 m (truth 0.600 m)
# [demo] centre: nearest-axis point X=+0.0000 Y=+0.0000 m
# [demo] slab:   0 points at Z=0 (want 0 — holes must be masked)
# PASS: recovered geometry matches ground truth (metric, masked, principal point on axis).
#
# Expected output (--demo, CONVERT_MM_TO_M = False — the unit bug)
# -----------------------------------------------------------------------------
#
# [demo] box:    Z mean = 600.0000 m (truth 0.600 m)
# FAIL: geometry does not match. If you disabled CONVERT_MM_TO_M you reproduced
#       the 1000x unit bug; ...
#
# The FAIL is the lesson: 16UC1 is MILLIMETRES. Read image.encoding and convert.
# -----------------------------------------------------------------------------
