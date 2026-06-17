#!/usr/bin/env python3
# Exercise 2 — The latched map (TRANSIENT_LOCAL durability)
#
# Goal: Prove that a RELIABLE / TRANSIENT_LOCAL / depth-1 publisher delivers its
#       last sample to a subscriber that joins LATE — exactly the behaviour a map
#       server needs, and exactly what VOLATILE (the default) gets wrong.
#
# Estimated time: 40 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   This file is standalone. No colcon package required. Source ROS2 Jazzy and run.
#
#   PART A — one process, late subscriber (the quick proof):
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-02-latched-map.py
#
#     A publisher publishes ONE map, then 3 seconds later a subscriber is created.
#     With TRANSIENT_LOCAL the late subscriber STILL receives the cached map. The
#     program prints PASS and exits 0. Flip USE_TRANSIENT_LOCAL to False and the
#     late subscriber gets nothing; the program prints FAIL and exits 1.
#
#   PART B — two terminals, the realistic late-join (do this after Part A passes):
#
#       # Terminal 1: publish the map once and keep it latched.
#       python3 exercise-02-latched-map.py --role publisher
#
#       # Terminal 2 (start it 10+ seconds later): subscribe and receive the map.
#       python3 exercise-02-latched-map.py --role subscriber
#
#     The subscriber joins long after the single publish, yet receives the map.
#     That is durability. Verify on the wire too:
#
#       ros2 topic info /map -v
#       # Both endpoints must read Durability: TRANSIENT_LOCAL.
#
# ACCEPTANCE CRITERIA
#
#   [ ] Part A prints "PASS: late subscriber received the latched map" and exits 0.
#   [ ] Flipping USE_TRANSIENT_LOCAL = False makes Part A print FAIL and exit 1 —
#       you have reproduced the VOLATILE silent failure on purpose.
#   [ ] In Part B, a subscriber started 10 s after the single publish still
#       receives the map.
#   [ ] `ros2 topic info /map -v` shows BOTH endpoints as TRANSIENT_LOCAL.
#
# Inline notes are throughout. The expected output is at the bottom of the file.

import argparse
import sys
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from nav_msgs.msg import OccupancyGrid

# Flip this to False to reproduce the VOLATILE silent failure on purpose.
USE_TRANSIENT_LOCAL = True


def map_qos() -> QoSProfile:
    """The latched-map profile: RELIABLE / TRANSIENT_LOCAL / KEEP_LAST(1).

    There is no built-in `qos_profile_map`; you construct it. This is exactly what
    Nav2's map_server and slam_toolbox publish /map with.
    """
    durability = (
        DurabilityPolicy.TRANSIENT_LOCAL
        if USE_TRANSIENT_LOCAL
        else DurabilityPolicy.VOLATILE
    )
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=durability,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


def make_map(width: int = 4, height: int = 4) -> OccupancyGrid:
    """A tiny 4x4 occupancy grid, stamped and framed honestly (Lecture 2 §3)."""
    grid = OccupancyGrid()
    grid.header.frame_id = "map"
    grid.info.resolution = 0.05
    grid.info.width = width
    grid.info.height = height
    grid.info.origin.orientation.w = 1.0
    # 0 = free, 100 = occupied, -1 = unknown. Border occupied, interior free.
    cells = []
    for y in range(height):
        for x in range(width):
            edge = x in (0, width - 1) or y in (0, height - 1)
            cells.append(100 if edge else 0)
    grid.data = cells
    return grid


class MapPublisher(Node):
    """Publishes ONE map, once, then stops. Durability does the rest."""

    def __init__(self) -> None:
        super().__init__("map_publisher")
        self.pub = self.create_publisher(OccupancyGrid, "map", map_qos())
        grid = make_map()
        grid.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(grid)
        self.get_logger().info(
            f"published map once: {grid.info.width}x{grid.info.height} "
            f"({len(grid.data)} cells), durability="
            f"{'TRANSIENT_LOCAL' if USE_TRANSIENT_LOCAL else 'VOLATILE'}"
        )


class LateMapSubscriber(Node):
    """Subscribes AFTER the publish. With TRANSIENT_LOCAL it still gets the map."""

    def __init__(self) -> None:
        super().__init__("late_map_subscriber")
        self.received = threading.Event()
        self.last_cells = 0
        self.sub = self.create_subscription(OccupancyGrid, "map", self.cb, map_qos())

    def cb(self, msg: OccupancyGrid) -> None:
        self.last_cells = len(msg.data)
        self.get_logger().info(
            f"RECEIVED latched map: {msg.info.width}x{msg.info.height} "
            f"({self.last_cells} cells), frame_id={msg.header.frame_id}"
        )
        self.received.set()


def run_part_a() -> int:
    """One process. Publish, wait, then create a late subscriber. Returns exit code."""
    rclpy.init()
    executor = MultiThreadedExecutor()

    publisher = MapPublisher()
    executor.add_node(publisher)

    # Spin the publisher in a background thread so the publish actually goes out
    # and the writer keeps the sample cached for late readers.
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    print("[part A] map published; waiting 3 s before the subscriber joins...")
    time.sleep(3.0)

    subscriber = LateMapSubscriber()
    executor.add_node(subscriber)

    # Give the SEDP handshake + durability replay time to complete.
    got = subscriber.received.wait(timeout=5.0)

    exit_code = 0
    if got:
        print(f"PASS: late subscriber received the latched map "
              f"({subscriber.last_cells} cells).")
    else:
        print("FAIL: late subscriber received NOTHING. "
              "If USE_TRANSIENT_LOCAL is False this is the expected VOLATILE "
              "silent failure. If it is True, check ros2 topic info /map -v.")
        exit_code = 1

    executor.shutdown()
    publisher.destroy_node()
    subscriber.destroy_node()
    rclpy.shutdown()
    return exit_code


def run_publisher_only() -> None:
    """Part B publisher: publish once and stay alive so the sample stays latched."""
    rclpy.init()
    node = MapPublisher()
    node.get_logger().info("staying alive to keep the map latched; Ctrl+C to stop.")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def run_subscriber_only() -> None:
    """Part B subscriber: join late and receive the latched map."""
    rclpy.init()
    node = LateMapSubscriber()
    node.get_logger().info("subscribed; waiting for the latched map...")
    try:
        # Spin until we get it, then a moment more, then exit cleanly.
        while rclpy.ok() and not node.received.is_set():
            rclpy.spin_once(node, timeout_sec=0.5)
        if node.received.is_set():
            node.get_logger().info("done — durability delivered the map.")
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="TRANSIENT_LOCAL latched-map demo.")
    parser.add_argument(
        "--role",
        choices=["both", "publisher", "subscriber"],
        default="both",
        help="both = Part A (one process); publisher/subscriber = Part B (two terminals).",
    )
    args = parser.parse_args()

    if args.role == "both":
        sys.exit(run_part_a())
    elif args.role == "publisher":
        run_publisher_only()
    else:
        run_subscriber_only()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (Part A, USE_TRANSIENT_LOCAL = True)
# -----------------------------------------------------------------------------
#
# [INFO] [map_publisher]: published map once: 4x4 (16 cells), durability=TRANSIENT_LOCAL
# [part A] map published; waiting 3 s before the subscriber joins...
# [INFO] [late_map_subscriber]: RECEIVED latched map: 4x4 (16 cells), frame_id=map
# PASS: late subscriber received the latched map (16 cells).
#
# Expected output (Part A, USE_TRANSIENT_LOCAL = False)
# -----------------------------------------------------------------------------
#
# [INFO] [map_publisher]: published map once: 4x4 (16 cells), durability=VOLATILE
# [part A] map published; waiting 3 s before the subscriber joins...
# FAIL: late subscriber received NOTHING. If USE_TRANSIENT_LOCAL is False this is
#       the expected VOLATILE silent failure. ...
#
# That FAIL is the lesson: with VOLATILE, a subscriber that joins after the single
# publish gets nothing, forever — the canonical "my map server looks broken but
# isn't" afternoon. TRANSIENT_LOCAL is the one-line fix.
# -----------------------------------------------------------------------------
