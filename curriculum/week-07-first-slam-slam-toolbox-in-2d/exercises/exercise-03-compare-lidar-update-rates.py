#!/usr/bin/env python3
"""Exercise 3 — Compare map quality at three LiDAR update rates.

C24 Week 7, exercise 3. Standalone. Two jobs in one file:

    # ROLE A -- a throttle node: subscribe to /scan, re-publish on /scan_throttled
    # at a capped rate, so you can map the SAME recorded drive at 5, 10, and 20 Hz:
    python3 exercise-03-compare-lidar-update-rates.py throttle \
        --ros-args -p use_sim_time:=true -p target_hz:=5.0

    # ROLE B -- the analyzer: load up to three saved maps (PGM/YAML produced by
    # map_saver_cli after each mapping run) and compute quality metrics + a plot:
    python3 exercise-03-compare-lidar-update-rates.py analyze \
        ~/maps/rate_05 ~/maps/rate_10 ~/maps/rate_20

THE EXPERIMENT (controlled: same trajectory, only the scan rate changes)
------------------------------------------------------------------------
  1. Record ONE drive of the multi-room world once:
       ros2 bag record -o drive_bag /scan /tf /tf_static /odom /joint_states /clock
     Drive a full loop (exercise 1). Stop. This bag is your fixed input.
  2. For each rate R in {5, 10, 20} Hz:
       a. Launch slam_toolbox in SYNC mapping mode with scan_topic:=/scan_throttled
          (sync, because we want deterministic processing of every passed scan).
       b. Launch this script in `throttle` role with target_hz:=R.
       c. Replay the bag with /scan REMAPPED to the throttle's input:
            ros2 bag play drive_bag --clock --remap /scan:=/scan_raw
          and run the throttle subscribed to /scan_raw -> /scan_throttled.
       d. When the replay finishes, save the map:
            ros2 run nav2_map_server map_saver_cli -f ~/maps/rate_<R>
       e. Kill slam_toolbox and the throttle. Repeat for the next rate.
  3. Run `analyze` on the three saved map prefixes. Read the metrics + plot.

WHY SYNC + A BAG?  Because to compare map QUALITY across rates fairly you must
hold the trajectory fixed. A live drive is never exactly repeatable; a bag is.
Sync mapping processes every throttled scan deterministically, so the only
variable between runs is the scan rate -- which is the whole point.

METRICS (all read from the saved OccupancyGrid PGM via its YAML)
----------------------------------------------------------------
  - coverage_frac : fraction of cells that are KNOWN (free or occupied), i.e. not
    unknown. Higher rate -> denser scans -> more cells observed -> higher coverage.
  - wall_thickness : mean thickness (in cells) of occupied-cell runs across rows.
    A crisp map has ~1-2 cell walls; drift between scans SMEARS walls thicker.
  - occupied_frac : fraction of known cells that are occupied. A smeared map has
    MORE occupied cells (doubled/blurred walls) -- a coarse proxy for drift.
"""
import sys

import numpy as np


# --------------------------------------------------------------------------- #
# ROLE A -- the throttle node (needs rclpy; only imported in this role).
# --------------------------------------------------------------------------- #
def run_throttle():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import LaserScan

    class ScanThrottle(Node):
        def __init__(self):
            super().__init__("scan_throttle")
            self.declare_parameter("target_hz", 10.0)
            self.declare_parameter("in_topic", "/scan_raw")
            self.declare_parameter("out_topic", "/scan_throttled")
            self.target_hz = float(self.get_parameter("target_hz").value)
            in_topic = self.get_parameter("in_topic").value
            out_topic = self.get_parameter("out_topic").value
            self.min_period = 1.0 / self.target_hz
            self.last_pub = None

            # sensor QoS: BEST_EFFORT/KEEP_LAST for a scan stream (Week 5).
            qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                             history=HistoryPolicy.KEEP_LAST, depth=5)
            self.pub = self.create_publisher(LaserScan, out_topic, qos)
            self.sub = self.create_subscription(LaserScan, in_topic, self._on_scan, qos)
            self.n_in = 0
            self.n_out = 0
            self.get_logger().info(
                f"throttle: {in_topic} -> {out_topic} capped at {self.target_hz} Hz")

        def _on_scan(self, msg: LaserScan):
            self.n_in += 1
            stamp = rclpy.time.Time.from_msg(msg.header.stamp)
            if self.last_pub is not None:
                dt = (stamp - self.last_pub).nanoseconds * 1e-9
                if dt < self.min_period:
                    return  # drop: too soon since the last published scan
            self.last_pub = stamp
            self.n_out += 1
            self.pub.publish(msg)
            if self.n_in % 50 == 0:
                self.get_logger().info(
                    f"in={self.n_in} out={self.n_out} "
                    f"(effective {self.n_out / max(self.n_in,1):.2f} of input)")

    rclpy.init()
    node = ScanThrottle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


# --------------------------------------------------------------------------- #
# ROLE B -- the analyzer (pure numpy/matplotlib; no ROS needed).
# --------------------------------------------------------------------------- #
def load_pgm(path):
    """Minimal binary PGM (P5) reader -> 2D uint8 array. map_saver writes P5."""
    with open(path, "rb") as f:
        assert f.readline().strip() == b"P5", "expected a binary P5 PGM"
        # skip comment lines, read width height, then maxval
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        w, h = (int(x) for x in line.split())
        maxval = int(f.readline())
        data = np.frombuffer(f.read(w * h), dtype=np.uint8).reshape(h, w)
    return data, maxval


def classify(pgm, maxval, occupied_thresh=0.65, free_thresh=0.25):
    """Turn raw PGM greyscale into occupancy classes, per the map YAML thresholds.

    map_saver convention (mode: trinary): a pixel value p in [0, maxval];
    occupancy = (maxval - p)/maxval. occupancy > occupied_thresh -> occupied;
    occupancy < free_thresh -> free; else unknown.
    """
    occ = (maxval - pgm.astype(np.float32)) / maxval
    occupied = occ > occupied_thresh
    free = occ < free_thresh
    unknown = ~(occupied | free)
    return occupied, free, unknown


def mean_wall_thickness(occupied):
    """Mean run-length of consecutive occupied cells along rows (a smear proxy)."""
    lengths = []
    for row in occupied:
        run = 0
        for v in row:
            if v:
                run += 1
            elif run > 0:
                lengths.append(run)
                run = 0
        if run > 0:
            lengths.append(run)
    return float(np.mean(lengths)) if lengths else 0.0


def metrics_for(prefix):
    """Compute the three metrics for a saved map prefix (expects <prefix>.pgm)."""
    pgm, maxval = load_pgm(prefix + ".pgm")
    occupied, free, unknown = classify(pgm, maxval)
    total = occupied.size
    known = int(occupied.sum() + free.sum())
    return {
        "coverage_frac": known / total,
        "occupied_frac": (occupied.sum() / max(known, 1)),
        "wall_thickness": mean_wall_thickness(occupied),
        "shape": pgm.shape,
    }


def run_analyze(prefixes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not prefixes:
        print("usage: analyze <map_prefix_1> [<map_prefix_2> ...] "
              "(each <prefix>.pgm + <prefix>.yaml from map_saver_cli)")
        return 2

    labels, cov, occ, thick = [], [], [], []
    print(f"{'map':<20} {'coverage':>9} {'occ_frac':>9} {'wall_cells':>11} {'shape'}")
    for p in prefixes:
        m = metrics_for(p)
        name = p.rsplit("/", 1)[-1]
        labels.append(name)
        cov.append(m["coverage_frac"])
        occ.append(m["occupied_frac"])
        thick.append(m["wall_thickness"])
        print(f"{name:<20} {m['coverage_frac']:>9.3f} {m['occupied_frac']:>9.4f} "
              f"{m['wall_thickness']:>11.2f} {m['shape']}")

    fig, ax = plt.subplots(1, 3, figsize=(13, 4))
    x = np.arange(len(labels))
    ax[0].bar(x, cov);   ax[0].set_title("coverage (known fraction)")
    ax[1].bar(x, thick); ax[1].set_title("mean wall thickness (cells) -- lower=crisper")
    ax[2].bar(x, occ);   ax[2].set_title("occupied fraction (smear proxy)")
    for a in ax:
        a.set_xticks(x); a.set_xticklabels(labels, rotation=20)
    fig.suptitle("Map quality vs LiDAR update rate (same trajectory)")
    fig.tight_layout()
    out = "lidar_rate_comparison.png"
    fig.savefig(out, dpi=120)
    print(f"\nwrote {out}")
    print("\nINTERPRETATION:")
    print("  Higher rate -> higher coverage and (usually) THINNER walls, because")
    print("  there is less drift between scan matches to smear them. Look for the")
    print("  rate where coverage stops improving -- past that, you are spending CPU")
    print("  for no map-quality gain. THAT rate is your defensible choice.")
    return 0


# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("throttle", "analyze"):
        print("usage: exercise-03-compare-lidar-update-rates.py "
              "{throttle|analyze} [...]")
        return 2
    role = sys.argv[1]
    if role == "throttle":
        sys.argv = [sys.argv[0]] + sys.argv[2:]   # let rclpy parse the rest
        return run_throttle()
    else:
        return run_analyze(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------- #
# EXPECTED OUTPUT
# ---------------------------------------------------------------------------- #
#
# ROLE A (throttle) during a 20 Hz bag replay capped to 5 Hz:
#
#   [scan_throttle]: throttle: /scan_raw -> /scan_throttled capped at 5.0 Hz
#   [scan_throttle]: in=50 out=13 (effective 0.26 of input)
#   [scan_throttle]: in=100 out=25 (effective 0.25 of input)
#
#   ~0.25 means the throttle passes ~1 in 4 scans -- 5 Hz out of 20 Hz in. Good.
#
# ROLE B (analyze) over three saved maps:
#
#   map                   coverage  occ_frac  wall_cells shape
#   rate_05                  0.612    0.0418        3.10  (412, 612)
#   rate_10                  0.731    0.0361        1.94  (414, 610)
#   rate_20                  0.748    0.0357        1.71  (415, 611)
#   wrote lidar_rate_comparison.png
#
#   INTERPRETATION:
#     ...
#
# Read it: 5 Hz under-covers (0.61) and smears walls to ~3 cells thick -- the robot
# drifts between sparse scan matches. 10 Hz jumps coverage to 0.73 and walls to ~2
# cells. 20 Hz barely improves coverage (0.75) and thins walls a little more. The
# defensible engineering call: 10 Hz is the knee -- it captures almost all the map
# quality of 20 Hz at half the CPU, which you will need for the Phase 2 perception
# cycle. "I run the LiDAR at 10 Hz because at 5 Hz the corridor walls smeared to 3
# cells and at 20 Hz coverage gained 2% for double the CPU" is the sentence a review
# wants. Your exact numbers depend on your world, robot speed, and resolution; the
# SHAPE (5 Hz worst, 10 Hz knee, 20 Hz diminishing returns) is what you must produce.
