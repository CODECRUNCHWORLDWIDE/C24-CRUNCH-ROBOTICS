# Challenge 1 — Diagnose Three QoS Mismatches on a Live Graph

**Time estimate:** ~90 minutes.

## Problem statement

You are on call. A teammate's bring-up "mostly works" but three things are broken in ways nobody can explain: the perception node "doesn't see the LiDAR," the dashboard "shows a blank map until you restart it in the right order," and a safety monitor "stops getting heartbeats sometimes." All three are QoS faults — three *different* faults across three *different* topic classes.

You will run a fault-injection harness that reproduces all three on one graph, then **detect, diagnose, and prescribe the fix** for each, using only the introspection tools from this week. No reading the harness source until you've diagnosed all three from the outside — that's the whole point.

This mirrors the real skill: you rarely debug QoS in code you just wrote. You debug it on a graph someone else built, from the outside in, with `ros2 topic info -v` and a clear head.

## The harness

Save this as `faulty_graph.py`. It launches three publisher/subscriber pairs in one process, each on its own topic, each with exactly one planted QoS fault. Run it and leave it running while you diagnose from other terminals.

```python
#!/usr/bin/env python3
"""Fault-injection harness: three topics, three planted QoS faults. Do NOT read
the QoS choices below until you have diagnosed all three from the outside."""
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
from rclpy.duration import Duration
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String


class FaultyGraph(Node):
    def __init__(self) -> None:
        super().__init__("faulty_graph")

        # --- Topic 1: /scan (sensor class) -----------------------------------
        scan_pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST, depth=5,
        )
        scan_sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,   # <-- planted fault #1
            history=HistoryPolicy.KEEP_LAST, depth=5,
        )
        self.scan_pub = self.create_publisher(LaserScan, "scan", scan_pub_qos)
        self.create_subscription(LaserScan, "scan", self._on_scan, scan_sub_qos)
        self.create_timer(1.0 / 30.0, self._tick_scan)
        self.scan_rx = 0

        # --- Topic 2: /map (latched class) -----------------------------------
        map_pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,     # <-- planted fault #2
            history=HistoryPolicy.KEEP_LAST, depth=1,
        )
        map_sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST, depth=1,
        )
        self.map_pub = self.create_publisher(OccupancyGrid, "map", map_pub_qos)
        grid = OccupancyGrid()
        grid.header.frame_id = "map"
        grid.info.width = grid.info.height = 2
        grid.data = [0, 100, 100, 0]
        grid.header.stamp = self.get_clock().now().to_msg()
        self.map_pub.publish(grid)   # published ONCE, now.
        # The subscriber joins 5 s late on purpose.
        self.map_rx = 0
        threading.Timer(5.0, self._late_map_sub).start()

        # --- Topic 3: /heartbeat (command/safety class) ----------------------
        hb_pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST, depth=1,
            deadline=Duration(seconds=2),             # publisher promises every 2 s
        )
        hb_sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST, depth=1,
            deadline=Duration(seconds=1),             # <-- planted fault #3: wants 1 s
        )
        self.hb_pub = self.create_publisher(String, "heartbeat", hb_pub_qos)
        self.create_subscription(String, "heartbeat", self._on_hb, hb_sub_qos)
        self.create_timer(2.0, self._tick_hb)
        self.hb_rx = 0

    def _tick_scan(self) -> None:
        m = LaserScan()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = "laser_link"
        m.ranges = [1.0] * 90
        self.scan_pub.publish(m)

    def _on_scan(self, _msg) -> None:
        self.scan_rx += 1

    def _late_map_sub(self) -> None:
        from rclpy.qos import QoSProfile as Q
        q = Q(reliability=ReliabilityPolicy.RELIABLE,
              durability=DurabilityPolicy.TRANSIENT_LOCAL,
              history=HistoryPolicy.KEEP_LAST, depth=1)
        self.create_subscription(OccupancyGrid, "map", self._on_map, q)

    def _on_map(self, _msg) -> None:
        self.map_rx += 1

    def _tick_hb(self) -> None:
        self.hb_pub.publish(String(data="alive"))

    def _on_hb(self, _msg) -> None:
        self.hb_rx += 1


def main() -> None:
    rclpy.init()
    node = FaultyGraph()
    ex = MultiThreadedExecutor()
    ex.add_node(node)
    t = threading.Thread(target=ex.spin, daemon=True)
    t.start()
    print("faulty graph running. Diagnose from other terminals. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(5.0)
            print(f"  counters: scan_rx={node.scan_rx} map_rx={node.map_rx} "
                  f"hb_rx={node.hb_rx}")
    except KeyboardInterrupt:
        pass
    finally:
        ex.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
```

```bash
source /opt/ros/jazzy/setup.bash
python3 faulty_graph.py
```

The printed counters are your symptom panel: a counter stuck at 0 (or near it) means that topic's subscriber isn't getting data.

## Your task

For **each of the three topics** (`/scan`, `/map`, `/heartbeat`), produce a diagnosis with these four parts:

1. **Symptom** — what's observably wrong (which counter, what `ros2 topic info -v` shows, what events fire).
2. **Root cause** — which *policy* is mismatched and which side requested vs offered what. State the request–offered rule it violates.
3. **Topic class** — which of the five classes (sensor / latched / command / parameters / diagnostics) the topic belongs to.
4. **Prescription** — the exact correct QoS profile for that class, and which line of the harness to change to fix it. Write the corrected `QoSProfile(...)`.

You must reach each diagnosis using **at least two** independent signals — e.g., the stuck counter *and* `ros2 topic info -v`, or an incompatibility event *and* `ros2 doctor`. One signal is a guess; two is a diagnosis.

## Acceptance criteria

- [ ] A file `challenge-01-diagnosis.md` with a section per topic, each containing all four parts above.
- [ ] You correctly identify the policy at fault on each topic:
  - `/scan` — **reliability** mismatch (RELIABLE subscriber vs BEST_EFFORT publisher).
  - `/map` — **durability** mismatch (VOLATILE publisher vs late TRANSIENT_LOCAL subscriber; the subscriber is *compatible* but gets no replay because the publisher didn't offer durability).
  - `/heartbeat` — **deadline** mismatch (subscriber requests 1 s; publisher offers 2 s; offered period must be ≤ requested).
- [ ] For each, the prescribed profile matches the taste-test table from Lecture 1 §5.
- [ ] You captured **at least one** rmw incompatible-QoS event (register the event callbacks, or show the `ros2 doctor` warning) for the `/scan` and `/heartbeat` faults. (The `/map` fault is *compatibility-legal* — see the trap below — so it won't fire an incompatibility event; you must diagnose it by the missing durability replay.)
- [ ] A `fixed_graph.py` — your corrected copy of the harness where all three counters climb and `ros2 doctor` is clean.
- [ ] Committed to your Week 5 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The `/map` fault is the subtle one and the most realistic. The publisher is `VOLATILE`; the subscriber is `TRANSIENT_LOCAL`. By the request–offered rule, **a `VOLATILE` publisher cannot satisfy a `TRANSIENT_LOCAL` subscriber for durability** — so this *is* an incompatibility and `ros2 topic info -v` will show the mismatch. But many people expect "the late subscriber gets the old map" and are confused when it doesn't, because they fixed the *subscriber* (made it TRANSIENT_LOCAL) and forgot the *publisher* must offer durability too. **Durability is a two-sided handshake.** The fix is on the *publisher*: it must offer `TRANSIENT_LOCAL` and cache the sample. Prescribing "make the subscriber TRANSIENT_LOCAL" is the wrong fix and you must not write it.

## Stretch

- Add a fourth fault on `/cmd_vel` using a **deep history** (`KEEP_LAST(50)`) where depth 1 belongs, and explain the *behavioural* (not connection) symptom: the robot keeps executing stale velocity commands after the joystick stops. History doesn't break the connection — it breaks the *robot*. Diagnose it by observed behaviour, not by `ros2 topic info -v`.
- Re-run the whole challenge under `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and note any difference in *how* the failures present (event timing, `ros2 doctor` wording). The diagnoses are identical; the personalities differ.
- Write a 10-line shell script that, given a topic name, prints just the reliability + durability + deadline of every endpoint side by side, so a mismatch is obvious at a glance. (`ros2 topic info -v` plus `grep`/`awk` is enough.)

## Why this matters

In Week 8 you defend your QoS choices at the Phase 1 architecture review. The reviewer will not ask you to recite the policy table — they'll point at a topic on your running graph and ask "why that profile, and how would you know if it were wrong?" This challenge *is* that conversation, rehearsed. Every robotics on-call rotation eventually hands you a graph you didn't build with a fault you can't see. The engineer who can name it from `ros2 topic info -v` in five minutes is the one who gets paged less.
