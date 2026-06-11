# Exercise 2 — The top-level bring-up launch file
#
# Goal: Complete robot.launch.py so that ONE command brings up the robot,
#       its sensors, slam_toolbox, and rviz2 with a saved layout:
#
#           ros2 launch crunchbot_bringup robot.launch.py \
#               world:=warehouse slam:=true rviz:=true
#
#       This file is the top-level entry point of the crunchbot_bringup
#       package you created in exercise 1. Replace the skeleton
#       launch/robot.launch.py with the contents of THIS file, fill in the
#       three TODOs, then bring the robot up.
#
# Estimated time: 75 minutes.
#
# PREREQUISITES (from exercise 1 and earlier weeks)
#
#   - crunchbot_bringup package exists with description.launch.py working.
#   - You have written launch/gz_sim.launch.py (Gz Sim server + spawn +
#     ros_gz_bridge), launch/slam.launch.py (slam_toolbox), and
#     launch/rviz.launch.py (rviz2 -d <config>). Stubs for these are
#     described in the HINTS at the bottom; write them as separate files.
#   - config/slam_toolbox.yaml exists, keyed 'slam_toolbox:'.
#   - rviz/bringup.rviz is a saved rviz2 layout (save one from rviz2's
#     File > Save Config As after you have it laid out the way you like).
#
# HOW TO USE THIS FILE
#
#   1. Copy this file to crunchbot_bringup/launch/robot.launch.py.
#   2. Fill in TODO 1, TODO 2, TODO 3.
#   3. Build and source:
#         colcon build --packages-select crunchbot_bringup --symlink-install
#         source install/setup.bash
#   4. Run:
#         ros2 launch crunchbot_bringup robot.launch.py
#   5. Verify with ros2 node list, ros2 topic list, view_frames.
#
# ACCEPTANCE CRITERIA
#
#   [ ] ros2 launch crunchbot_bringup robot.launch.py --show-args lists all
#       five arguments (world, slam, rviz, use_sim_time, namespace) with
#       descriptions.
#   [ ] One command brings up robot_state_publisher, Gz Sim, the bridge,
#       slam_toolbox, and rviz2 with the saved layout.
#   [ ] slam:=false starts NO slam_toolbox node and publishes no /map.
#   [ ] rviz:=false starts NO rviz2.
#   [ ] view_frames shows ONE connected tree rooted at map: map -> odom ->
#       base_link -> {laser, imu, wheels}.
#   [ ] ros2 doctor reports no QoS mismatch warnings.
#
# SMOKE OUTPUT (target)
#
#   $ ros2 node list
#   /robot_state_publisher
#   /ros_gz_bridge
#   /slam_toolbox
#   /rviz2
#   $ ros2 run tf2_ros tf2_echo map base_link
#   At time ...
#   - Translation: [..., ..., 0.000]
#   - Rotation: in Quaternion [..., ..., ..., ...]

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace, SetParameter
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg = FindPackageShare('crunchbot_bringup')

    # --- Operator-facing arguments (the robot's command-line interface) ---
    declare_world = DeclareLaunchArgument(
        'world', default_value='warehouse',
        description='World name under worlds/ to load in Gz Sim.')
    declare_slam = DeclareLaunchArgument(
        'slam', default_value='true',
        description='Start slam_toolbox in mapping mode.')
    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='true',
        description='Start rviz2 with the saved bringup layout.')
    declare_sim = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use the Gz Sim /clock instead of wall time.')
    declare_ns = DeclareLaunchArgument(
        'namespace', default_value='',
        description='Namespace for the whole stack (empty = single robot at root).')

    world = LaunchConfiguration('world')
    slam = LaunchConfiguration('slam')
    rviz = LaunchConfiguration('rviz')
    use_sim_time = LaunchConfiguration('use_sim_time')
    namespace = LaunchConfiguration('namespace')

    # Helper so each include is a one-liner. Pass the subsystem filename,
    # an optional condition, and the launch_arguments to thread down.
    def include(filename, condition=None, launch_arguments=None):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([pkg, 'launch', filename])),
            condition=condition,
            launch_arguments=(launch_arguments or {}).items())

    # ------------------------------------------------------------------
    # TODO 1 — The robot description include.
    #   Always runs. Threads use_sim_time down. Use the `include` helper:
    #
    #       description = include('description.launch.py',
    #                             launch_arguments={'use_sim_time': use_sim_time})
    # ------------------------------------------------------------------
    description = None  # YOUR CODE HERE

    # ------------------------------------------------------------------
    # TODO 2 — The Gz Sim include.
    #   Always runs. Threads BOTH world and use_sim_time down. gz_sim.launch.py
    #   starts the Gz server, spawns the robot from /robot_description, and
    #   starts the ros_gz_bridge. It owns the odom->base_link transform via the
    #   DiffDrive plugin (do NOT also run your week-6 odom node here).
    # ------------------------------------------------------------------
    gz = None  # YOUR CODE HERE

    # ------------------------------------------------------------------
    # TODO 3 — The SLAM and rviz2 includes, each gated by its flag.
    #   slam runs only IfCondition(slam); rviz runs only IfCondition(rviz).
    #   slam threads use_sim_time; rviz threads use_sim_time. Use
    #   condition=IfCondition(...) on each.
    # ------------------------------------------------------------------
    slam_include = None  # YOUR CODE HERE
    rviz_include = None   # YOUR CODE HERE

    # Group everything under the namespace. With namespace:='' this is a no-op
    # prefix; with namespace:='robot1' the whole stack is prefixed. TF topics
    # stay global because the subsystem nodes remap /tf and /tf_static back to
    # absolute names (see lecture 2, section 2.5).
    stack = GroupAction([
        PushRosNamespace(namespace),
        description,
        gz,
        slam_include,
        rviz_include,
    ])

    return LaunchDescription([
        # SetParameter must come first so it applies to every node launched after.
        SetParameter(name='use_sim_time', value=use_sim_time),
        declare_world, declare_slam, declare_rviz, declare_sim, declare_ns,
        stack,
    ])


# ===========================================================================
# HINTS — peek only if stuck.
# ===========================================================================
#
# HINT — TODO 1:
#
#   description = include(
#       'description.launch.py',
#       launch_arguments={'use_sim_time': use_sim_time})
#
# HINT — TODO 2:
#
#   gz = include(
#       'gz_sim.launch.py',
#       launch_arguments={'world': world, 'use_sim_time': use_sim_time})
#
# HINT — TODO 3:
#
#   slam_include = include(
#       'slam.launch.py',
#       condition=IfCondition(slam),
#       launch_arguments={'use_sim_time': use_sim_time})
#
#   rviz_include = include(
#       'rviz.launch.py',
#       condition=IfCondition(rviz),
#       launch_arguments={'use_sim_time': use_sim_time})
#
# ---------------------------------------------------------------------------
# STUB — launch/slam.launch.py (write this as its own file):
#
#   from launch import LaunchDescription
#   from launch.actions import DeclareLaunchArgument
#   from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
#   from launch_ros.actions import Node
#   from launch_ros.substitutions import FindPackageShare
#
#   def generate_launch_description():
#       use_sim_time = LaunchConfiguration('use_sim_time')
#       params = PathJoinSubstitution([
#           FindPackageShare('crunchbot_bringup'), 'config', 'slam_toolbox.yaml'])
#       return LaunchDescription([
#           DeclareLaunchArgument('use_sim_time', default_value='true'),
#           Node(package='slam_toolbox', executable='async_slam_toolbox_node',
#                name='slam_toolbox', output='screen',
#                parameters=[params, {'use_sim_time': use_sim_time}],
#                remappings=[('/tf', '/tf'), ('/tf_static', '/tf_static')]),
#       ])
#
# ---------------------------------------------------------------------------
# STUB — launch/rviz.launch.py (write this as its own file):
#
#   from launch import LaunchDescription
#   from launch.actions import DeclareLaunchArgument
#   from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
#   from launch_ros.actions import Node
#   from launch_ros.substitutions import FindPackageShare
#
#   def generate_launch_description():
#       use_sim_time = LaunchConfiguration('use_sim_time')
#       rviz_cfg = PathJoinSubstitution([
#           FindPackageShare('crunchbot_bringup'), 'rviz', 'bringup.rviz'])
#       return LaunchDescription([
#           DeclareLaunchArgument('use_sim_time', default_value='true'),
#           Node(package='rviz2', executable='rviz2', name='rviz2',
#                output='screen', arguments=['-d', rviz_cfg],
#                parameters=[{'use_sim_time': use_sim_time}]),
#       ])
#
# ---------------------------------------------------------------------------
# REFLECTION QUESTIONS — answer in results-ex02.md after the bring-up works:
#
#   1. With slam:=false, which TF edge disappears, and what node owned it?
#   2. The SetParameter('use_sim_time', ...) is first in the list. What goes
#      wrong if you put it LAST instead?
#   3. The slam.launch.py stub remaps /tf to /tf even though it looks like a
#      no-op. With namespace:='robot1', what does this remap actually do?
#   4. Run `ros2 doctor`. If it reports a QoS mismatch on /scan, which side
#      (publisher or subscriber) is wrong, and what is the week-5 fix?
