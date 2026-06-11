#!/usr/bin/env python3
# Exercise 3 — The costmap monitor (decode the OccupancyGrid, watch inflation)
#
# Goal: Subscribe to BOTH Nav2 costmaps, decode the nav_msgs/OccupancyGrid into a
#       cost histogram, and report what fraction of the map is free / inflated /
#       lethal / unknown. Then re-tune inflation_radius LIVE and watch the inflated
#       fraction grow — building intuition for what a costmap actually IS.
#
# Estimated time: 40 minutes. Runnable (needs a running Nav2 stack publishing costmaps).
#
# WHAT A COSTMAP CELL MEANS (Lecture 1 §3, Lecture 2 §1)
#
#   Nav2 publishes the costmap as an OccupancyGrid whose .data is int8 per cell.
#   The mapping (after Nav2's cost->occupancy translation on the topic) is:
#     0          -> FREE
#     1..98      -> INFLATED (decaying cost spread out from obstacles)
#     99         -> INSCRIBED (robot center here definitely collides)
#     100        -> LETHAL (an actual obstacle)
#     -1         -> UNKNOWN
#   (Internally the costmap is 0..254; on the OccupancyGrid topic it's rescaled to
#    0..100 with -1 unknown. We bin on the published 0..100 scale.)
#
# HOW TO USE THIS FILE
#
#   1. Bring up Nav2 (Exercise 1) so /global_costmap/costmap and
#      /local_costmap/costmap are published.
#   2. Source ROS2 Jazzy and run:
#
#        source /opt/ros/jazzy/setup.bash
#        python3 exercise-03-costmap-monitor.py
#
#   3. In another terminal, grow the inflation and force a rebuild:
#        ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.9
#        ros2 service call /global_costmap/clear_entirely_global_costmap \
#             nav2_msgs/srv/ClearEntireCostmap "{}"
#      Watch the monitor's INFLATED fraction jump.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The monitor prints a histogram for BOTH costmaps with their frame_id.
#   [ ] The global costmap's frame is 'map'; the local costmap's frame is 'odom'.
#   [ ] Raising inflation_radius and clearing the costmap visibly increases the
#       global costmap's INFLATED fraction in the next report.
#   [ ] You can explain why the FREE fraction shrinks when inflation grows.
#
# Expected output is at the bottom of the file.

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from nav_msgs.msg import OccupancyGrid


def costmap_qos() -> QoSProfile:
    """Nav2 publishes costmaps RELIABLE / TRANSIENT_LOCAL / KEEP_LAST(1) (latched).
    Subscribe TRANSIENT_LOCAL so a late-joining monitor still gets the current grid.
    """
    return QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
        history=HistoryPolicy.KEEP_LAST,
        depth=1,
    )


def bin_cells(data) -> dict:
    """Bin OccupancyGrid cells into cost classes. Returns counts and percentages."""
    counts = {"free": 0, "inflated": 0, "inscribed": 0, "lethal": 0, "unknown": 0}
    for c in data:
        if c < 0:
            counts["unknown"] += 1
        elif c == 0:
            counts["free"] += 1
        elif c < 99:
            counts["inflated"] += 1
        elif c == 99:
            counts["inscribed"] += 1
        else:  # 100
            counts["lethal"] += 1
    total = max(1, len(data))
    pct = {k: 100.0 * v / total for k, v in counts.items()}
    return {"counts": counts, "pct": pct, "total": total}


class CostmapMonitor(Node):
    def __init__(self) -> None:
        super().__init__("costmap_monitor")
        self._reports = {}
        self.create_subscription(
            OccupancyGrid, "/global_costmap/costmap",
            lambda m: self._on_grid("global", m), costmap_qos())
        self.create_subscription(
            OccupancyGrid, "/local_costmap/costmap",
            lambda m: self._on_grid("local", m), costmap_qos())
        # Print a consolidated report every 2 s.
        self.create_timer(2.0, self._report)

    def _on_grid(self, which: str, msg: OccupancyGrid) -> None:
        stats = bin_cells(msg.data)
        stats["frame_id"] = msg.header.frame_id
        stats["w"] = msg.info.width
        stats["h"] = msg.info.height
        stats["res"] = msg.info.resolution
        self._reports[which] = stats

    def _report(self) -> None:
        if not self._reports:
            self.get_logger().info("waiting for costmaps... is Nav2 up?")
            return
        print("\n================= COSTMAP REPORT =================")
        for which in ("global", "local"):
            s = self._reports.get(which)
            if s is None:
                print(f"[{which}] (no data yet)")
                continue
            p = s["pct"]
            print(
                f"[{which:6}] frame={s['frame_id']:5} "
                f"{s['w']}x{s['h']} @ {s['res']:.3f} m/cell  "
                f"free={p['free']:5.1f}%  inflated={p['inflated']:5.1f}%  "
                f"inscribed={p['inscribed']:4.1f}%  lethal={p['lethal']:4.1f}%  "
                f"unknown={p['unknown']:5.1f}%"
            )
        print("=================================================")


def main() -> None:
    rclpy.init()
    node = CostmapMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (default inflation_radius ~0.55)
# -----------------------------------------------------------------------------
#
# ================= COSTMAP REPORT =================
# [global] frame=map   200x200 @ 0.050 m/cell  free= 71.3%  inflated= 18.9%  inscribed= 1.2%  lethal= 5.1%  unknown=  3.5%
# [local ] frame=odom  100x100 @ 0.050 m/cell  free= 88.0%  inflated=  9.5%  inscribed= 0.6%  lethal= 1.9%  unknown=  0.0%
# =================================================
#
# Expected output AFTER: inflation_radius -> 0.9, then clear the global costmap
# -----------------------------------------------------------------------------
#
# ================= COSTMAP REPORT =================
# [global] frame=map   200x200 @ 0.050 m/cell  free= 52.7%  inflated= 37.5%  inscribed= 1.2%  lethal= 5.1%  unknown=  3.5%
# [local ] frame=odom  100x100 @ 0.050 m/cell  free= 88.0%  inflated=  9.5%  inscribed= 0.6%  lethal= 1.9%  unknown=  0.0%
# =================================================
#
# The lethal fraction barely moves (the walls didn't change). The INFLATED fraction
# jumps and the FREE fraction shrinks: a bigger inflation_radius spreads cost further
# from every wall, so more free cells become inflated. That is WHY a too-large radius
# blocks a doorway the robot physically fits through — the doorway cells all became
# inflated and the planner avoids them. Numbers depend on your map; the SHAPE is the
# lesson: inflation trades free space for clearance.
# -----------------------------------------------------------------------------
