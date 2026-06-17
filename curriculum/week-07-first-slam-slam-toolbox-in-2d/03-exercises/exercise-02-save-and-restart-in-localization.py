#!/usr/bin/env python3
"""Exercise 2 — Serialize the live map, restart in localization mode, measure convergence.

C24 Week 7, exercise 2. Standalone (no colcon package); the mini-project packages
the production version. Two jobs in one file, selected by a positional command:

    # PART A -- while a mapping run from exercise 1 is LIVE, serialize the graph:
    python3 exercise-02-save-and-restart-in-localization.py serialize \
        --ros-args -p use_sim_time:=true -p filename:=/home/you/maps/crunch_world

    # PART B -- after you relaunch slam_toolbox in LOCALIZATION mode against that
    # saved graph, measure how fast and how accurately the SLAM pose converges to
    # the Gz Sim ground-truth pose:
    python3 exercise-02-save-and-restart-in-localization.py measure \
        --ros-args -p use_sim_time:=true

WHAT PART A DOES (serialize)
---------------------------
  Calls the /slam_toolbox/serialize_map service (Lecture 2, section 2.4, Format 2),
  which writes <filename>.posegraph + <filename>.data -- the FULL pose graph that
  localization mode needs. (The PGM/YAML for Nav2 you still save separately with
  map_saver_cli; this service is the slam_toolbox-native format.)

WHAT PART B DOES (measure)
--------------------------
  Subscribes to:
    - the SLAM pose, read from the map -> base_link transform (compose
      map->odom from slam_toolbox with odom->base_link from your Week 6 node), and
    - the Gz Sim GROUND-TRUTH pose on /ground_truth/pose (a geometry_msgs/
      PoseStamped you bridge from Gz's model-pose topic via ros_gz_bridge).
  Every cycle it computes the position error |p_slam - p_truth| and the heading
  error, and reports the TIME from start until the error first drops below a
  convergence threshold (default 0.10 m) -- the AMCL-style "I found myself" moment.

HOW TO RESTART IN LOCALIZATION MODE (between Part A and Part B)
--------------------------------------------------------------
  1. Kill the mapping slam_toolbox (Ctrl-C in its terminal).
  2. Edit config/localization_params.yaml: mode: localization, and
     map_file_name: /home/you/maps/crunch_world   (NO extension).
  3. ros2 launch crunch_slam localization.launch.py
  4. In RViz, use "2D Pose Estimate" to give a rough initial pose (or set
     map_start_pose in the YAML). Then drive a little.
  5. Run Part B of this script; drive the robot; read the convergence time.

GROUND-TRUTH BRIDGE (one-time setup)
------------------------------------
  Bridge Gz's pose info to a ROS PoseStamped on /ground_truth/pose. The simplest
  reliable path is the ros_gz_bridge with a pose_v message; this script also
  accepts a nav_msgs/Odometry on /ground_truth/odom if that is what you bridged
  (set ground_truth_topic accordingly).
"""
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from slam_toolbox.srv import SerializePoseGraph

import tf2_ros


# --------------------------------------------------------------------------- #
# PART A -- serialize the live graph through the slam_toolbox service.
# --------------------------------------------------------------------------- #
class SerializeClient(Node):
    def __init__(self):
        super().__init__("serialize_client")
        self.declare_parameter("filename", "/tmp/crunch_world")
        self.filename = self.get_parameter("filename").value
        self.cli = self.create_client(SerializePoseGraph, "/slam_toolbox/serialize_map")

    def run(self):
        if not self.cli.wait_for_service(timeout_sec=10.0):
            self.get_logger().error(
                "/slam_toolbox/serialize_map not available -- is a mapping run live?"
            )
            return 1
        req = SerializePoseGraph.Request()
        req.filename = self.filename
        future = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=15.0)
        if future.result() is None:
            self.get_logger().error("serialize_map call timed out")
            return 1
        # The service result code is 0 on success in slam_toolbox.
        self.get_logger().info(
            f"serialize_map result={future.result().result} -> "
            f"{self.filename}.posegraph + {self.filename}.data"
        )
        return 0


# --------------------------------------------------------------------------- #
# PART B -- measure localization convergence vs Gz Sim ground truth.
# --------------------------------------------------------------------------- #
def yaw_from_quat(q) -> float:
    """Extract planar yaw from a geometry_msgs/Quaternion."""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


def ang_diff(a: float, b: float) -> float:
    """Smallest signed difference a - b, wrapped to (-pi, pi]."""
    d = a - b
    return math.atan2(math.sin(d), math.cos(d))


class ConvergenceMonitor(Node):
    def __init__(self):
        super().__init__("convergence_monitor")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("ground_truth_topic", "/ground_truth/pose")
        self.declare_parameter("ground_truth_is_odom", False)
        self.declare_parameter("converge_threshold_m", 0.10)

        self.map_frame = self.get_parameter("map_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        gt_topic = self.get_parameter("ground_truth_topic").value
        gt_is_odom = self.get_parameter("ground_truth_is_odom").value
        self.thresh = self.get_parameter("converge_threshold_m").value

        # TF: we read the SLAM pose as map -> base_link (the COMPOSITION of
        # slam_toolbox's map->odom and your Week 6 odom->base_link; tf2 composes it).
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.truth = None  # (x, y, yaw)
        if gt_is_odom:
            self.create_subscription(Odometry, gt_topic, self._on_truth_odom, 10)
        else:
            self.create_subscription(PoseStamped, gt_topic, self._on_truth_pose, 10)

        self.t0 = self.get_clock().now()
        self.converged_at = None
        self.timer = self.create_timer(0.2, self._tick)   # 5 Hz reporting
        self.get_logger().info(
            f"convergence monitor up: threshold={self.thresh} m, "
            f"reading SLAM pose from {self.map_frame}->{self.base_frame}, "
            f"ground truth from {gt_topic}"
        )

    def _on_truth_pose(self, msg: PoseStamped):
        self.truth = (msg.pose.position.x, msg.pose.position.y,
                      yaw_from_quat(msg.pose.orientation))

    def _on_truth_odom(self, msg: Odometry):
        p = msg.pose.pose
        self.truth = (p.position.x, p.position.y, yaw_from_quat(p.orientation))

    def _slam_pose(self):
        """Look up map -> base_link. Returns (x, y, yaw) or None if not yet available."""
        try:
            tf = self.tf_buffer.lookup_transform(
                self.map_frame, self.base_frame, rclpy.time.Time(),
                timeout=Duration(seconds=0.1))
        except tf2_ros.TransformException:
            return None
        t = tf.transform.translation
        return (t.x, t.y, yaw_from_quat(tf.transform.rotation))

    def _tick(self):
        if self.truth is None:
            self.get_logger().warn("no ground truth yet (check the bridge / topic)",
                                   throttle_duration_sec=2.0)
            return
        slam = self._slam_pose()
        if slam is None:
            self.get_logger().warn("no map->base_link yet (is localization running?)",
                                   throttle_duration_sec=2.0)
            return

        pos_err = math.hypot(slam[0] - self.truth[0], slam[1] - self.truth[1])
        yaw_err = math.degrees(ang_diff(slam[2], self.truth[2]))
        elapsed = (self.get_clock().now() - self.t0).nanoseconds * 1e-9

        if self.converged_at is None and pos_err < self.thresh:
            self.converged_at = elapsed
            self.get_logger().info(
                f"*** CONVERGED at t={elapsed:.2f} s: pos_err={pos_err*100:.1f} cm ***")

        tag = "converged" if self.converged_at is not None else "converging"
        self.get_logger().info(
            f"[{tag}] t={elapsed:5.1f}s  pos_err={pos_err*100:6.1f} cm  "
            f"yaw_err={yaw_err:+6.1f} deg",
            throttle_duration_sec=0.5)


# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("serialize", "measure"):
        print("usage: exercise-02-save-and-restart-in-localization.py "
              "{serialize|measure} [--ros-args ...]")
        return 2
    cmd = sys.argv[1]
    # strip the positional command so rclpy sees only its own args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    rclpy.init()
    try:
        if cmd == "serialize":
            node = SerializeClient()
            rc = node.run()
            node.destroy_node()
            return rc
        else:  # measure
            node = ConvergenceMonitor()
            try:
                rclpy.spin(node)
            except KeyboardInterrupt:
                pass
            finally:
                node.destroy_node()
            return 0
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------- #
# EXPECTED OUTPUT
# ---------------------------------------------------------------------------- #
#
# PART A (serialize), with a mapping run live:
#
#   [serialize_client]: serialize_map result=0 ->
#       /home/you/maps/crunch_world.posegraph + /home/you/maps/crunch_world.data
#
#   Confirm the files exist:
#       ls -l ~/maps/crunch_world.posegraph ~/maps/crunch_world.data
#
# PART B (measure), after relaunching in localization mode and setting an initial
# pose roughly near the true start, then driving a couple of metres:
#
#   [convergence_monitor]: convergence monitor up: threshold=0.1 m, ...
#   [convergence_monitor]: [converging] t=  0.4s  pos_err=  62.0 cm  yaw_err= +11.3 deg
#   [convergence_monitor]: [converging] t=  1.0s  pos_err=  21.4 cm  yaw_err=  +4.1 deg
#   [convergence_monitor]: *** CONVERGED at t=1.60 s: pos_err=8.7 cm ***
#   [convergence_monitor]: [converged ] t=  2.0s  pos_err=   5.2 cm  yaw_err=  -1.2 deg
#   [convergence_monitor]: [converged ] t=  4.0s  pos_err=   3.9 cm  yaw_err=  +0.6 deg
#
# A correct localization restart converges to a few centimetres within ~1-3 s of
# motion. If pos_err stays large and never drops, the usual causes are:
#   - the initial pose guess was too far off (set it closer in RViz "2D Pose Est");
#   - map_file_name points at the wrong path or is missing the .posegraph/.data;
#   - use_sim_time mismatch (the map->base_link lookup keeps failing);
#   - the world has a SYMMETRIC region and localization latched onto the wrong copy
#     (a real failure mode -- the same ambiguity that causes false loop closures in
#     mapping; Lecture 1, section 1.6).
#
# If "no map->base_link yet" never clears: slam_toolbox is not publishing map->odom
# (localization mode not actually running, or no scans), OR your Week 6 node is not
# publishing odom->base_link. tf2_echo map base_link is the one-line diagnosis.
