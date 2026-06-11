#!/usr/bin/env python3
# Exercise 3 - Wrist-in-base listener with clear, exception-specific errors
#
# Goal: Write an rclpy node that looks up wrist_link in base_link, prints a
#       healthy "[tf_health] ... OK" line when the chain is intact, and logs a
#       CLEAR, exception-specific error when you break the tree. The whole skill
#       is distinguishing the three tf2 failure modes from each other - because
#       each one points at a different bug.
#
# Estimated time: 50 minutes.
#
# HOW TO RUN
#
#   1. Source ROS2 Jazzy:
#        source /opt/ros/jazzy/setup.bash
#
#   2. Bring up the tree from Exercises 1 + 2:
#        - base_link -> shoulder_link        (static_transform_publisher)
#        - shoulder_link -> elbow_link        (exercise-02-dynamic-broadcaster.py)
#        - elbow_link -> wrist_link           (static_transform_publisher)
#
#   3. Run THIS listener:
#        python3 exercise-03-wrist-in-base-listener.py
#
#   4. Break the tree on purpose and watch the error change:
#        - Ctrl+C the base->shoulder static publisher
#            -> wrist_link still exists, but is no longer connected to base_link
#            -> ConnectivityException
#        - Restart it, then Ctrl+C the elbow->wrist static publisher
#            -> wrist_link disappears entirely
#            -> LookupException
#        - Restart everything, then run the listener with --future
#            -> it asks for a time slightly in the future of the latest stamp
#            -> ExtrapolationException
#
# ACCEPTANCE CRITERIA
#   [ ] With the full tree up, prints "[tf_health] base_link -> wrist_link OK ..."
#       at 2 Hz with the live (x, y, z) of the wrist.
#   [ ] Killing base->shoulder produces a ConnectivityException log (NOT Lookup).
#   [ ] Killing elbow->wrist produces a LookupException log.
#   [ ] Running with --future produces an ExtrapolationException log, and the
#       message's "requested vs latest" gap is small (tens of ms).
#   [ ] Each exception is caught and logged SEPARATELY - no bare `except Exception`.

import argparse
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.time import Time

from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

TARGET_FRAME = "base_link"
SOURCE_FRAME = "wrist_link"


class WristWatcher(Node):
    """Continuously validates base_link -> wrist_link and reports tree health."""

    def __init__(self, force_future: bool) -> None:
        super().__init__("wrist_watcher")
        self.force_future = force_future
        # A 5 s cache is plenty for a single-arm tree; the default is 10 s.
        self.buffer = Buffer()
        # The listener fills the buffer from /tf and /tf_static. We never touch it
        # again - we query the buffer.
        self.listener = TransformListener(self.buffer, self)
        self.timer = self.create_timer(0.5, self.on_timer)   # 2 Hz health check
        self.ok_streak = 0
        self.get_logger().info(
            f"wrist_watcher up: validating {TARGET_FRAME} -> {SOURCE_FRAME}"
            + ("  [--future: forcing ExtrapolationException]" if force_future else ""))

    def query_time(self) -> Time:
        if self.force_future:
            # Ask 200 ms into the future of NOW. Since the broadcasters' latest
            # stamp is at best 'now', this is guaranteed to be past the newest
            # buffered sample -> ExtrapolationException. This is the deliberate
            # break that the Week 2 challenge dissects in full.
            return self.get_clock().now() + Duration(seconds=0.2)
        # Time() == Time(0) == "latest available". The correct query when you
        # just want the most recent consistent transform.
        return Time()

    def on_timer(self) -> None:
        try:
            t = self.buffer.lookup_transform(
                TARGET_FRAME, SOURCE_FRAME, self.query_time(),
                timeout=Duration(seconds=0.05))
            p = t.transform.translation
            # Edge count is fixed at 3 for this tree; we report it so the line
            # matches the mini-project's monitor format.
            self.ok_streak += 1
            self.get_logger().info(
                f"[tf_health] {TARGET_FRAME} -> {SOURCE_FRAME}  OK  "
                f"({p.x:+.3f}, {p.y:+.3f}, {p.z:+.3f})  streak={self.ok_streak}")

        except LookupException as e:
            # A frame name in the query is not in the tree at all: the elbow->wrist
            # publisher is dead (wrist_link vanished), or a typo.
            self.ok_streak = 0
            self.get_logger().error(
                f"[tf_health] LookupException - a frame is MISSING from the tree. "
                f"Run `ros2 run tf2_tools view_frames` and check {SOURCE_FRAME} exists. "
                f"detail: {e}")

        except ConnectivityException as e:
            # Both frames exist, but there is no path between them: the tree is
            # split - e.g. base->shoulder died, orphaning the wrist subtree.
            self.ok_streak = 0
            self.get_logger().error(
                f"[tf_health] ConnectivityException - {SOURCE_FRAME} and {TARGET_FRAME} "
                f"are in DIFFERENT trees. A middle edge is gone. detail: {e}")

        except ExtrapolationException as e:
            # Frames exist and connect, but the requested time is outside the
            # buffered window: future query, clock skew, or a stalled broadcaster.
            self.ok_streak = 0
            self.get_logger().warn(
                f"[tf_health] ExtrapolationException - requested a time the buffer "
                f"cannot serve. Subtract requested-vs-latest in the message below to "
                f"diagnose (small gap = future query/latency; huge gap = clock skew). "
                f"detail: {e}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--future", action="store_true",
        help="query 200 ms in the future to force an ExtrapolationException")
    # Strip ROS args (e.g. --ros-args) before our parser sees them.
    parsed, _ = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    rclpy.init()
    node = WristWatcher(force_future=parsed.future)
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


# ----------------------------------------------------------------------------
# EXPECTED OUTPUT
# ----------------------------------------------------------------------------
#
# Healthy tree (all publishers up, no --future):
#   [INFO] [wrist_watcher]: [tf_health] base_link -> wrist_link  OK  (+0.539, +0.097, +0.100)  streak=12
#   [INFO] [wrist_watcher]: [tf_health] base_link -> wrist_link  OK  (+0.550, +0.000, +0.100)  streak=13
#
# After Ctrl+C on the base->shoulder publisher (wrist subtree orphaned):
#   [ERROR] [wrist_watcher]: [tf_health] ConnectivityException - wrist_link and base_link
#           are in DIFFERENT trees. A middle edge is gone. detail: Could not find a connection
#           between 'base_link' and 'wrist_link' because they are not part of the same tree...
#
# After Ctrl+C on the elbow->wrist publisher (wrist_link gone entirely):
#   [ERROR] [wrist_watcher]: [tf_health] LookupException - a frame is MISSING from the tree...
#
# Running with --future against a healthy tree:
#   [WARN] [wrist_watcher]: [tf_health] ExtrapolationException - requested a time the buffer
#          cannot serve... Lookup would require extrapolation 0.187s into the future...
#
# ----------------------------------------------------------------------------
# WHY EACH EXCEPTION IS CAUGHT SEPARATELY
# ----------------------------------------------------------------------------
#
# A monitor that does `except Exception: log("tf error")` is useless at 3 a.m.
# The three exceptions are three different bugs:
#   - LookupException     -> a publisher is DEAD or a frame name is WRONG.
#   - ConnectivityException -> the tree is SPLIT; a middle edge is missing.
#   - ExtrapolationException -> a TIMING problem; nobody's geometry is wrong.
# Logging them distinctly is what lets you fix the right thing fast. The
# mini-project formalizes this into a continuous health report.
