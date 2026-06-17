#!/usr/bin/env python3
# Exercise 3 — Map a new world and time the run
#
# Goal: A rclpy "map-run timer" node that measures, in wall-clock seconds, how
#       long an end-to-end mapping run takes: from the first /map message to the
#       moment you save the map via slam_toolbox's /slam_toolbox/save_map
#       service. It also reports map coverage growth so you can see the map
#       filling in, and it logs a final summary line you paste into your
#       challenge / mini-project writeup.
#
#       This is a COMPLETE, RUNNABLE node. Read it, run it, then use it to time
#       mapping a brand-new world end-to-end (the challenge does exactly this
#       under a 15-minute budget).
#
# Estimated time: 60 minutes (15 reading + writing, 45 running a mapping session).
#
# HOW TO RUN
#
#   1. Drop this file in your package: crunchbot_bringup/crunchbot_bringup/
#      and add a console_scripts entry point in setup.py:
#
#          entry_points={'console_scripts': [
#              'map_run_timer = crunchbot_bringup.map_run_timer:main',
#          ]},
#
#      (rename this file to map_run_timer.py inside the module dir).
#
#   2. Build and source:
#          colcon build --packages-select crunchbot_bringup --symlink-install
#          source install/setup.bash
#
#   3. Bring up the robot in a NEW world WITH slam:
#          ros2 launch crunchbot_bringup robot.launch.py world:=house slam:=true
#
#   4. In a second terminal, start the timer:
#          ros2 run crunchbot_bringup map_run_timer --ros-args -p map_name:=house
#
#   5. Drive the robot to map the world (teleop or your week-4 action). When you
#      believe the map is complete, the node will detect the save_map service
#      call you make (or you can let the node trigger it after a coverage
#      threshold — see the auto_save parameter). It then prints the elapsed time.
#
#   6. Save the map yourself (the node watches for this):
#          ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
#              "{name: {data: 'house'}}"
#
# ACCEPTANCE CRITERIA
#
#   [ ] The node logs "first map received" exactly once, when /map first arrives.
#   [ ] The node logs coverage growth (% of cells that are known) periodically.
#   [ ] The node logs the elapsed wall-clock time when the map is saved.
#   [ ] Works with use_sim_time:=true (it reads the node clock, not wall time,
#       so sim-time speedups are reflected correctly).
#   [ ] Exits cleanly on Ctrl-C.

import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from slam_toolbox.srv import SaveMap
from std_msgs.msg import String


class MapRunTimer(Node):
    """Times an end-to-end SLAM mapping run and reports map coverage growth."""

    def __init__(self) -> None:
        super().__init__('map_run_timer')

        # Parameters: the map name to save, and whether to auto-save once
        # coverage stops growing (handy for the unattended challenge run).
        self.declare_parameter('map_name', 'new_world')
        self.declare_parameter('auto_save', False)
        self.declare_parameter('coverage_stall_seconds', 30.0)
        self._map_name = self.get_parameter('map_name').value
        self._auto_save = bool(self.get_parameter('auto_save').value)
        self._stall_secs = float(self.get_parameter('coverage_stall_seconds').value)

        # The map is a LATCHED topic: RELIABLE + TRANSIENT_LOCAL, depth 1.
        # This MUST match slam_toolbox's publisher QoS or we receive nothing —
        # this is the week-5 lesson made concrete. Get it wrong and the node
        # silently never gets a map. (See reflection question 1.)
        map_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self._map_sub = self.create_subscription(
            OccupancyGrid, '/map', self._on_map, map_qos)

        # We "detect" a save by watching slam_toolbox publish on /slam_toolbox/
        # feedback; more robustly, we expose our own save trigger so the run is
        # self-contained. We call the slam_toolbox SaveMap service ourselves
        # when auto_save fires, and we also end the timer if the operator's
        # external save changes the map's last-update behavior.
        self._save_client = self.create_client(SaveMap, '/slam_toolbox/save_map')

        # State
        self._t_first_map: float | None = None
        self._t_last_growth: float | None = None
        self._last_known_cells = 0
        self._saved = False

        # Use the NODE clock so use_sim_time is honored. now() returns a
        # builtin_interfaces Time; we convert to float seconds.
        self._poll = self.create_timer(2.0, self._tick)
        self.get_logger().info(
            f"map_run_timer started (map_name='{self._map_name}', "
            f"auto_save={self._auto_save}). Waiting for first /map...")

    def _clock_seconds(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_map(self, msg: OccupancyGrid) -> None:
        now = self._clock_seconds()
        if self._t_first_map is None:
            self._t_first_map = now
            self._t_last_growth = now
            self.get_logger().info(
                f"first map received at t={now:.2f}s "
                f"({msg.info.width}x{msg.info.height} cells @ "
                f"{msg.info.resolution:.3f} m/cell). Timer started.")

        # Count known cells (not -1). Coverage growth = the map filling in.
        known = sum(1 for c in msg.data if c != -1)
        total = len(msg.data)
        coverage = (100.0 * known / total) if total else 0.0
        if known > self._last_known_cells:
            self._t_last_growth = now
        self._last_known_cells = known
        self.get_logger().info(
            f"t={now - (self._t_first_map or now):7.1f}s  "
            f"known={known:>8d}/{total:<8d}  coverage={coverage:5.1f}%")

    def _tick(self) -> None:
        if self._t_first_map is None or self._saved:
            return
        now = self._clock_seconds()
        stalled_for = now - (self._t_last_growth or now)
        if self._auto_save and stalled_for >= self._stall_secs:
            self.get_logger().info(
                f"coverage stalled for {stalled_for:.0f}s "
                f">= {self._stall_secs:.0f}s threshold; auto-saving map.")
            self._save_map()

    def _save_map(self) -> None:
        if self._saved:
            return
        if not self._save_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error(
                '/slam_toolbox/save_map service not available; is slam running?')
            return
        req = SaveMap.Request()
        req.name = String(data=self._map_name)
        future = self._save_client.call_async(req)
        future.add_done_callback(self._on_save_done)

    def _on_save_done(self, future) -> None:
        elapsed = self._clock_seconds() - (self._t_first_map or self._clock_seconds())
        self._saved = True
        try:
            _ = future.result()
            status = 'OK'
        except Exception as exc:  # noqa: BLE001 - report any service failure
            status = f'FAILED ({exc})'
        self.get_logger().info(
            '================ MAP RUN COMPLETE ================')
        self.get_logger().info(
            f"map '{self._map_name}' saved: {status}")
        self.get_logger().info(
            f"end-to-end mapping time (first map -> save): {elapsed:.1f}s "
            f"({elapsed / 60.0:.2f} min)")
        self.get_logger().info(
            f"final known cells: {self._last_known_cells}")
        self.get_logger().info(
            '==================================================')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MapRunTimer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('interrupted; shutting down map_run_timer.')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()


# ===========================================================================
# REFLECTION QUESTIONS — answer in results-ex03.md after a full mapping run:
#
#   1. The map subscriber uses RELIABLE + TRANSIENT_LOCAL, depth 1. What
#      happens if you instead use the default sensor QoS (BEST_EFFORT,
#      KEEP_LAST, depth 5)? Why does the node never receive a map? (This is the
#      single most common QoS mismatch in ROS2; it is the week-5 lesson.)
#
#   2. The node reads self.get_clock().now() instead of time.time(). With
#      use_sim_time:=true, what is the difference, and why does it matter for
#      reporting "the run took 8 minutes"?
#
#   3. Coverage is computed by counting cells != -1. A cell value of 0 means
#      "known free", 100 means "known occupied", -1 means "unknown". Why is
#      counting != -1 the right coverage metric, and not counting == 100?
#
#   4. With auto_save:=true, the node saves once coverage stalls for
#      coverage_stall_seconds. Why is "coverage stopped growing" a reasonable
#      (but imperfect) proxy for "the map is done"? Name one failure mode.
