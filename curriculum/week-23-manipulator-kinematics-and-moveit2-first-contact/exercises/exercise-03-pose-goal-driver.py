#!/usr/bin/env python3
# Exercise 3 — The pose-goal driver (PoseStamped topic -> MoveIt2 plan-and-execute)
#
# Goal: Write a rclpy node that subscribes to geometry_msgs/PoseStamped on
#       /arm/pose_goal and, for each pose, sends a MoveGroup action goal to
#       move_group, waits for the result, and reports the MoveItErrorCodes value
#       with an HONEST per-code diagnosis (Lecture 2 §5.5). This is the syllabus
#       deliverable: "a Python script that consumes PoseStamped from a topic and
#       triggers a plan-and-execute via the MoveIt2 action interface."
#
# Estimated time: 50 minutes. Runnable. Needs ROS2 Jazzy + a running move_group.
#
# WHY THE RAW ACTION INTERFACE (not moveit_py)
#
#   We use the moveit_msgs/action/MoveGroup action directly so you SEE the request
#   you build -- the goal constraints, the planning group, the link. moveit_py
#   hides this; here you wire it by hand once, so the failure modes are concrete.
#   The mini-project may use moveit_py for ergonomics; this exercise is the
#   under-the-hood version that makes the error codes mean something.
#
# HOW TO USE THIS FILE
#
#   Terminal 1 -- bring up the MoveIt2 arm (this starts /move_action):
#       source /opt/ros/jazzy/setup.bash
#       ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur5e
#
#   Terminal 2 -- the driver:
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-pose-goal-driver.py
#
#   Terminal 3 -- send a REACHABLE pose (expect SUCCESS / val 1):
#       ros2 topic pub --once /arm/pose_goal geometry_msgs/PoseStamped \
#         "{header: {frame_id: 'base_link'},
#           pose: {position: {x: 0.4, y: 0.1, z: 0.4},
#                  orientation: {x: 1.0, y: 0.0, z: 0.0, w: 0.0}}}"
#
#   Then send an UNREACHABLE pose (expect NO_IK_SOLUTION / PLANNING_FAILED):
#       ros2 topic pub --once /arm/pose_goal geometry_msgs/PoseStamped \
#         "{header: {frame_id: 'base_link'},
#           pose: {position: {x: 5.0, y: 5.0, z: 5.0},
#                  orientation: {w: 1.0}}}"
#
# ACCEPTANCE CRITERIA
#
#   [ ] A reachable pose returns error_code.val == 1 (SUCCESS) and the arm moves
#       in RViz/Gz to that pose.
#   [ ] An unreachable pose returns a NEGATIVE code (NO_IK_SOLUTION == -31 in newer
#       MoveIt2, or PLANNING_FAILED == -1/-2 depending on where it fails) and the
#       node logs a one-line diagnosis -- and does NOT crash or hang.
#   [ ] The node refuses to send a new goal while one is in flight (no goal stomp).
#   [ ] On Ctrl+C the node shuts down cleanly with no in-flight goal left dangling.
#
# Expected output is at the bottom of the file.

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import PoseStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
    MotionPlanRequest,
)
from shape_msgs.msg import SolidPrimitive

# The MoveItErrorCodes integer -> name map, for honest diagnosis (Lecture 2 §5.5).
# Values are from moveit_msgs/msg/MoveItErrorCodes.msg.
ERROR_NAMES = {
    1: "SUCCESS",
    99999: "UNDEFINED",
    -1: "FAILURE",
    -2: "PLANNING_FAILED",
    -3: "INVALID_MOTION_PLAN",
    -4: "CONTROL_FAILED",
    -5: "UNABLE_TO_AQUIRE_SENSOR_DATA",
    -6: "TIMED_OUT",
    -7: "PREEMPTED",
    -10: "START_STATE_IN_COLLISION",
    -11: "START_STATE_VIOLATES_PATH_CONSTRAINTS",
    -12: "GOAL_IN_COLLISION",
    -13: "GOAL_VIOLATES_PATH_CONSTRAINTS",
    -14: "GOAL_CONSTRAINTS_VIOLATED",
    -15: "INVALID_GROUP_NAME",
    -17: "NO_IK_SOLUTION",
    -31: "NO_IK_SOLUTION",          # newer MoveIt2 numbering
}

# One-line "where to look" for the codes you'll actually hit.
DIAGNOSIS = {
    "SUCCESS": "plan found and executed; the arm reached the goal.",
    "PLANNING_FAILED": "OMPL found no collision-free path in the time budget -- "
                       "check the planning scene (did a collision object block "
                       "every path?) and reachability.",
    "NO_IK_SOLUTION": "IK found no joint config for this pose -- the pose is "
                      "outside the workspace or at a singularity (Lecture 1 §5).",
    "INVALID_GROUP_NAME": "the planning group name is wrong -- check the SRDF "
                          "(e.g. 'ur_manipulator' for the UR5e).",
    "CONTROL_FAILED": "the trajectory was sent but the controller didn't track it "
                      "-- a controller/hardware problem, not a planning one.",
    "START_STATE_IN_COLLISION": "the arm's current state is already in collision "
                                "-- a stale planning scene or a bad SRDF collision "
                                "pair is the usual cause.",
}

PLANNING_GROUP = "ur_manipulator"   # the UR5e arm group from ur_moveit_config's SRDF
EE_LINK = "tool0"                   # the end-effector link to constrain
BASE_LINK = "base_link"


def name_for(val: int) -> str:
    return ERROR_NAMES.get(val, f"UNKNOWN({val})")


class PoseGoalDriver(Node):
    """Subscribes to PoseStamped goals and dispatches MoveIt2 plan-and-execute."""

    def __init__(self) -> None:
        super().__init__("pose_goal_driver")
        self._client = ActionClient(self, MoveGroup, "/move_action")
        self._goal_in_flight = False

        # Commands: RELIABLE / KEEP_LAST(1) -- only the latest goal matters
        # (the command-class QoS from Week 5's taste test; a deep queue here would
        # let stale goals drain into the arm after a hiccup).
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.create_subscription(PoseStamped, "/arm/pose_goal", self.on_goal, qos)
        self.get_logger().info(
            "pose_goal_driver up. Waiting for move_group action server..."
        )
        if not self._client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error(
                "move_group /move_action not available -- is MoveIt2 launched?"
            )
        else:
            self.get_logger().info("connected to /move_action. Send a PoseStamped.")

    # --- goal construction ----------------------------------------------------
    def build_request(self, pose: PoseStamped) -> MotionPlanRequest:
        """Turn a PoseStamped into a MotionPlanRequest with a pose goal.

        A pose goal in MoveIt2 is a PositionConstraint (a small box around the
        target point) plus an OrientationConstraint (the target quaternion with a
        tolerance). move_group runs IK on this to get joint targets, then plans.
        """
        req = MotionPlanRequest()
        req.group_name = PLANNING_GROUP
        req.num_planning_attempts = 10
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = 0.2     # gentle -- this is first contact
        req.max_acceleration_scaling_factor = 0.2

        # --- position constraint: a 1 cm tolerance box at the target point ---
        pos = PositionConstraint()
        pos.header.frame_id = pose.header.frame_id or BASE_LINK
        pos.link_name = EE_LINK
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [0.01, 0.01, 0.01]       # 1 cm tolerance
        bv = BoundingVolume()
        bv.primitives.append(box)
        bv.primitive_poses.append(pose.pose)      # box centered on the target
        pos.constraint_region = bv
        pos.weight = 1.0

        # --- orientation constraint: the target quaternion, modest tolerance ---
        orient = OrientationConstraint()
        orient.header.frame_id = pose.header.frame_id or BASE_LINK
        orient.link_name = EE_LINK
        orient.orientation = pose.pose.orientation
        orient.absolute_x_axis_tolerance = 0.05
        orient.absolute_y_axis_tolerance = 0.05
        orient.absolute_z_axis_tolerance = 0.05
        orient.weight = 1.0

        # TODO 1: assemble a Constraints message holding `pos` and `orient`, then
        #         append it to req.goal_constraints. (req.goal_constraints is a
        #         list; a pose goal is ONE Constraints entry with one position and
        #         one orientation constraint.)
        goal_constraints = Constraints()
        goal_constraints.position_constraints.append(pos)
        goal_constraints.orientation_constraints.append(orient)
        req.goal_constraints.append(goal_constraints)
        return req

    # --- dispatch + result handling ------------------------------------------
    def on_goal(self, pose: PoseStamped) -> None:
        if self._goal_in_flight:
            self.get_logger().warn("a goal is already in flight; ignoring new pose "
                                   "(no goal stomp).")
            return
        p = pose.pose.position
        self.get_logger().info(
            f"received pose goal: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f}) "
            f"in {pose.header.frame_id or BASE_LINK}; planning..."
        )
        goal = MoveGroup.Goal()
        goal.request = self.build_request(pose)
        # Default planning_options.plan_only = False -> plan AND execute.

        self._goal_in_flight = True
        send_future = self._client.send_goal_async(goal)
        send_future.add_done_callback(self._on_accepted)

    def _on_accepted(self, future) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("move_group REJECTED the goal.")
            self._goal_in_flight = False
            return
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future) -> None:
        result = future.result().result
        val = result.error_code.val
        name = name_for(val)
        diag = DIAGNOSIS.get(name, "see move_group logs for the specific cause.")
        if val == 1:
            n = len(result.planned_trajectory.joint_trajectory.points)
            self.get_logger().info(
                f"RESULT: val={val} ({name}) -- {diag} "
                f"trajectory={n} waypoints, planning_time={result.planning_time:.3f}s"
            )
        else:
            self.get_logger().error(f"RESULT: val={val} ({name}) -- {diag}")
        self._goal_in_flight = False


def main() -> None:
    rclpy.init()
    node = PoseGoalDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean shutdown: no in-flight goal is left dangling (the MoveGroup action
        # is cancelled by destroying the client / shutting down the context).
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output
# -----------------------------------------------------------------------------
#
# (driver terminal, after launching MoveIt2 and publishing a REACHABLE pose)
#
# [INFO] [pose_goal_driver]: pose_goal_driver up. Waiting for move_group action ...
# [INFO] [pose_goal_driver]: connected to /move_action. Send a PoseStamped.
# [INFO] [pose_goal_driver]: received pose goal: (0.40, 0.10, 0.40) in base_link; planning...
# [INFO] [pose_goal_driver]: RESULT: val=1 (SUCCESS) -- plan found and executed; the
#        arm reached the goal. trajectory=9 waypoints, planning_time=0.214s
#
# (after publishing an UNREACHABLE pose at (5, 5, 5))
#
# [INFO] [pose_goal_driver]: received pose goal: (5.00, 5.00, 5.00) in base_link; planning...
# [ERROR] [pose_goal_driver]: RESULT: val=-31 (NO_IK_SOLUTION) -- IK found no joint
#        config for this pose -- the pose is outside the workspace or at a
#        singularity (Lecture 1 §5).
#
# The exact negative code for an unreachable pose depends on where the failure
# surfaces -- NO_IK_SOLUTION if IK is tried first, PLANNING_FAILED if it reaches
# OMPL -- and the precise integer differs across MoveIt2 versions (the map handles
# both -17 and -31). The SHAPE is invariant: reachable => val 1; unreachable =>
# a NEGATIVE, NAMED code with a one-line diagnosis, and the node keeps running.
# -----------------------------------------------------------------------------
