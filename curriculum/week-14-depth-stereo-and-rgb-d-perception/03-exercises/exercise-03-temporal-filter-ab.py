#!/usr/bin/env python3
# Exercise 3 — Temporal filter A/B (quantify what filtering buys and costs)
#
# Goal: Run a depth TEMPORAL filter on vs. off against a known flat plane and
#       measure the noise reduction with an RMS-flatness metric, so you can state
#       the cost/benefit of the filter in NUMBERS, not adjectives. Then see the
#       cost: run the same filter on a MOVING scene and watch it smear.
#
# Estimated time: 45 minutes. Runnable.
#
# THE FILTER (Lecture 2, Part 4.1)
#
#   The temporal filter is an exponential moving average across frames:
#       depth_t = alpha * depth_raw + (1 - alpha) * depth_{t-1}
#   with a "persistence" that holds the last valid value over a transient hole.
#   On a STATIC scene it averages out per-frame jitter (big win). On a MOVING
#   scene it drags a ghost of the previous depth (the cost). It is NOT free.
#
# THE METRIC
#
#   For a known flat plane, fit a plane to the points and report the RMS of the
#   residuals (how far each point is from the fitted plane). Lower RMS = flatter
#   = less noise. We report RMS with the filter OFF and ON; the ratio is the win.
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run.
#
#   PART A — --demo (no camera): synthesize a noisy flat plane over many frames,
#   measure RMS flatness filter-OFF vs filter-ON, and report the improvement.
#   Then synthesize a MOVING plane and show the filter LAGS it.
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-temporal-filter-ab.py            # runs --demo
#
#   PART B — live: point it at a depth topic aimed at a real flat wall/floor and
#   measure the real noise reduction your camera's temporal filter buys.
#
#       python3 exercise-03-temporal-filter-ab.py --live \
#           --depth-topic /camera/depth/image_rect_raw \
#           --info-topic  /camera/depth/camera_info
#
# ACCEPTANCE CRITERIA
#
#   [ ] --demo reports filter-ON RMS noticeably LOWER than filter-OFF on the
#       static plane (improvement ratio > 1.5x), and prints PASS.
#   [ ] --demo shows the filter LAGS the moving plane (mean depth error during
#       motion is larger ON than OFF) — the cost, demonstrated.
#   [ ] You can state, in one sentence, when to use the temporal filter (static
#       camera + static workspace) and when it hurts (fast motion).
#
# Expected output is at the bottom of the file.

import argparse
import sys

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


class TemporalFilter:
    """Per-pixel exponential moving average with hole persistence."""

    def __init__(self, alpha: float = 0.4) -> None:
        self.alpha = alpha
        self.state = None  # last filtered frame (metres), NaN where never seen

    def apply(self, depth_m: np.ndarray) -> np.ndarray:
        if self.state is None:
            self.state = depth_m.copy()
            return self.state
        valid = np.isfinite(depth_m)
        out = self.state.copy()
        # Where the new frame is valid, blend; where it's a hole, persist old.
        blended = self.alpha * depth_m + (1.0 - self.alpha) * self.state
        # If the old state was NaN there, just take the new value.
        old_nan = ~np.isfinite(self.state)
        out[valid & ~old_nan] = blended[valid & ~old_nan]
        out[valid & old_nan] = depth_m[valid & old_nan]
        self.state = out
        return out


def plane_rms(depth_m: np.ndarray, fx=120.0, fy=120.0) -> float:
    """Fit a plane to the back-projected points and return the residual RMS (m).

    A flatter surface (less noise) gives a smaller RMS. This is our noise metric.
    """
    h, w = depth_m.shape
    cx, cy = w / 2.0, h / 2.0
    u = np.arange(w, dtype=np.float32)
    v = np.arange(h, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)
    z = depth_m
    valid = np.isfinite(z) & (z > 0)
    x = ((uu - cx) * z / fx)[valid]
    y = ((vv - cy) * z / fy)[valid]
    zz = z[valid]
    # Fit z = a*x + b*y + c by least squares, then take residual RMS.
    A = np.stack((x, y, np.ones_like(x)), axis=-1)
    coef, *_ = np.linalg.lstsq(A, zz, rcond=None)
    resid = zz - A @ coef
    return float(np.sqrt(np.mean(resid ** 2)))


def synth_noisy_plane(rng, h=120, w=160, z0=1.0, noise=0.006) -> np.ndarray:
    """A frontal flat plane at z0 metres with Gaussian per-pixel noise."""
    return (z0 + rng.normal(0.0, noise, size=(h, w))).astype(np.float32)


def run_demo() -> int:
    rng = np.random.default_rng(14)
    N = 40

    # --- A) STATIC plane: measure RMS filter-OFF vs filter-ON over N frames. ---
    off_rms, on_rms = [], []
    filt = TemporalFilter(alpha=0.3)
    for _ in range(N):
        raw = synth_noisy_plane(rng, z0=1.0, noise=0.006)
        off_rms.append(plane_rms(raw))
        on_rms.append(plane_rms(filt.apply(raw)))

    # Compare the last frames (after the filter has converged).
    off_mean = float(np.mean(off_rms[-10:]))
    on_mean = float(np.mean(on_rms[-10:]))
    ratio = off_mean / on_mean if on_mean > 0 else float("inf")
    print(f"[demo] STATIC plane (noise sigma 6 mm):")
    print(f"[demo]   filter OFF: RMS flatness = {off_mean * 1000:.2f} mm")
    print(f"[demo]   filter ON : RMS flatness = {on_mean * 1000:.2f} mm")
    print(f"[demo]   improvement ratio = {ratio:.2f}x  (filter averages out jitter)")

    # --- B) MOVING plane: the filter LAGS, injecting depth error. ---
    filt2 = TemporalFilter(alpha=0.3)
    err_off, err_on = [], []
    for i in range(N):
        z0 = 1.0 + 0.01 * i               # plane recedes 1 cm / frame (motion)
        raw = synth_noisy_plane(rng, z0=z0, noise=0.006)
        filtered = filt2.apply(raw)
        # Mean depth error vs the TRUE current distance z0.
        err_off.append(abs(np.nanmean(raw) - z0))
        err_on.append(abs(np.nanmean(filtered) - z0))
    moving_off = float(np.mean(err_off[-10:]))
    moving_on = float(np.mean(err_on[-10:]))
    print(f"[demo] MOVING plane (receding 1 cm/frame):")
    print(f"[demo]   filter OFF: mean depth error = {moving_off * 1000:.1f} mm")
    print(f"[demo]   filter ON : mean depth error = {moving_on * 1000:.1f} mm  (LAGS)")

    ok = ratio > 1.5 and moving_on > moving_off
    if ok:
        print("PASS: the temporal filter cuts static-scene noise (good) but lags "
              "moving scenes (the cost). Use it for a static camera + static "
              "workspace; avoid it on a fast-moving robot.")
        return 0
    print("FAIL: expected the filter to reduce static noise > 1.5x AND lag the "
          "moving scene. Check the alpha and the metric.")
    return 1


# --------------------------------------------------------------------------- #
# PART B — --live: filter a real camera's depth and report the RMS win.
# --------------------------------------------------------------------------- #

class LiveFilterAB(Node):
    def __init__(self, depth_topic: str, info_topic: str) -> None:
        super().__init__("temporal_filter_ab")
        self.fx = self.fy = 120.0
        self.filt = TemporalFilter(alpha=0.3)
        self.off_hist, self.on_hist = [], []
        self.create_subscription(CameraInfo, info_topic, self.on_info,
                                 qos_profile_sensor_data)
        self.create_subscription(Image, depth_topic, self.on_depth,
                                 qos_profile_sensor_data)

    def on_info(self, msg: CameraInfo) -> None:
        self.fx, self.fy = msg.k[0], msg.k[4]

    def on_depth(self, msg: Image) -> None:
        raw = np.frombuffer(
            msg.data, dtype=np.uint16 if msg.encoding == "16UC1" else np.float32
        ).reshape(msg.height, msg.width).astype(np.float32)
        if msg.encoding == "16UC1":
            raw = raw / 1000.0
        raw[raw <= 0] = np.nan
        self.off_hist.append(plane_rms(raw, self.fx, self.fy))
        self.on_hist.append(plane_rms(self.filt.apply(raw), self.fx, self.fy))
        if len(self.on_hist) % 30 == 0:
            off = np.nanmean(self.off_hist[-10:])
            on = np.nanmean(self.on_hist[-10:])
            self.get_logger().info(
                f"aim at a FLAT wall: RMS off={off * 1000:.2f} mm "
                f"on={on * 1000:.2f} mm  ratio={off / on:.2f}x")


def run_live(depth_topic: str, info_topic: str) -> None:
    rclpy.init()
    node = LiveFilterAB(depth_topic, info_topic)
    node.get_logger().info("point the camera at a flat wall/floor; watch the RMS ratio.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Temporal-filter A/B on depth.")
    parser.add_argument("--live", action="store_true")
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
# Expected output (--demo)
# -----------------------------------------------------------------------------
#
# [demo] STATIC plane (noise sigma 6 mm):
# [demo]   filter OFF: RMS flatness = 6.0X mm
# [demo]   filter ON : RMS flatness = 2.X mm
# [demo]   improvement ratio = 2.XXx  (filter averages out jitter)
# [demo] MOVING plane (receding 1 cm/frame):
# [demo]   filter OFF: mean depth error = 0.X mm
# [demo]   filter ON : mean depth error = X.X mm  (LAGS)
# PASS: the temporal filter cuts static-scene noise (good) but lags moving
#       scenes (the cost). Use it for a static camera + static workspace; avoid
#       it on a fast-moving robot.
#
# The exact numbers vary with the RNG seed and alpha, but the SHAPE is invariant:
# static -> the filter wins (lower RMS); moving -> the filter loses (lags). That
# is the cost/benefit you must be able to state in numbers, not adjectives.
# -----------------------------------------------------------------------------
