#!/usr/bin/env python3
"""Exercise 2 — The perception latency probe.

Measure the END-TO-END perception latency of your fused node — sensor stamp to
/perception/objects publish — and report the p50/p95/p99 distribution. This is
the number you defend at the midterm. "It feels fast" is not a number; this is.

THE MEASUREMENT (Lecture 1, Part 1.4)

  Latency = (time the fused output is published) - (the SENSOR acquisition stamp
  carried through the pipeline in header.stamp). For this to be meaningful, every
  stage must PRESERVE the sensor stamp (Week 5 §3.1). If any stage re-stamps with
  now(), the measurement reads ~0 and is meaningless.

  We report PERCENTILES, not the mean: a p99 of 80 ms with a p50 of 18 ms is a
  WORSE system than a flat 28 ms, because the tail is where a moving object's
  detection goes stale. The panel asks for p95.

--------------------------------------------------------------------------------
RUN
--------------------------------------------------------------------------------
Against the live composed stack (the real way):
    source install/setup.bash
    ros2 launch crunch_perception perception.launch.py &   # your fused node
    python3 exercise-02-perception-latency-probe.py
    # ... let it collect for ~30 s, then Ctrl+C for the report.

Standalone in demo mode (spawns a synthetic fused publisher with known latency):
    python3 exercise-02-perception-latency-probe.py --demo
    # Expect: measured latency ~ the injected latency, budget verdict PASS.

Force a budget blowout to confirm the FAIL path:
    python3 exercise-02-perception-latency-probe.py --demo --inject-ms 45
    # Expect: p95 ~45 ms, budget verdict FAIL (over the 30 ms target).

--------------------------------------------------------------------------------
EXPECTED OUTPUT (demo, default injected latency ~22 ms)
--------------------------------------------------------------------------------
[latency_probe] collected 300 samples over 10.0 s
[latency_probe] end-to-end latency: p50=21.8 p95=24.1 p99=25.6 ms
[latency_probe] budget: target 30.0 ms, p95 24.1 ms -> PASS (5.9 ms headroom)

ACCEPTANCE CRITERIA
  [ ] --demo reports a measured latency ~ the injected latency and a PASS verdict.
  [ ] --inject-ms 45 reports p95 ~45 ms and a FAIL verdict (over budget).
  [ ] You can state the endpoints of the measurement (sensor stamp -> publish) and
      why you report p95, not the mean.
  [ ] Against your live stack, you have a real p95 number for the midterm.
"""

import argparse
import sys
import threading
import time

import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Header
from vision_msgs.msg import Detection3DArray, Detection3D, ObjectHypothesisWithPose

BUDGET_MS = 30.0


class LatencyProbe(Node):
    """Subscribe to /perception/objects and measure stamp->receipt latency."""

    def __init__(self, topic: str = "/perception/objects") -> None:
        super().__init__("latency_probe")
        self.samples: list[float] = []
        qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST, depth=10)
        self.create_subscription(Detection3DArray, topic, self.on_objects, qos)

    def on_objects(self, msg: Detection3DArray) -> None:
        # header.stamp is the SENSOR acquisition time carried through the pipeline.
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        now = self.get_clock().now().nanoseconds * 1e-9
        latency_ms = (now - stamp) * 1000.0
        if 0.0 <= latency_ms < 10000.0:        # sanity: drop absurd values
            self.samples.append(latency_ms)

    def report(self) -> bool:
        if not self.samples:
            self.get_logger().error(
                "NO SAMPLES. Either /perception/objects isn't publishing, the QoS "
                "doesn't match, or every stage re-stamped with now() (latency ~0, "
                "filtered out). Check ros2 topic info -v and the stamp discipline.")
            return False
        a = np.array(self.samples)
        p50, p95, p99 = np.percentile(a, [50, 95, 99])
        self.get_logger().info(f"collected {len(a)} samples")
        self.get_logger().info(
            f"end-to-end latency: p50={p50:.1f} p95={p95:.1f} p99={p99:.1f} ms")
        if p95 <= BUDGET_MS:
            self.get_logger().info(
                f"budget: target {BUDGET_MS:.1f} ms, p95 {p95:.1f} ms -> PASS "
                f"({BUDGET_MS - p95:.1f} ms headroom)")
            return True
        self.get_logger().error(
            f"budget: target {BUDGET_MS:.1f} ms, p95 {p95:.1f} ms -> FAIL "
            f"(over by {p95 - BUDGET_MS:.1f} ms). The latency block diagram tells "
            f"you which hop on the critical path to cut.")
        return False


class DemoFusedPublisher(Node):
    """Synthetic /perception/objects publisher with a KNOWN injected latency, so
    the probe can be validated without the real stack."""

    def __init__(self, inject_ms: float) -> None:
        super().__init__("demo_fused_publisher")
        self.inject_s = inject_ms / 1000.0
        self.rng = np.random.default_rng(16)
        qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST, depth=10)
        self.pub = self.create_publisher(Detection3DArray, "/perception/objects", qos)
        self.create_timer(1.0 / 30.0, self.tick)   # 30 Hz

    def tick(self) -> None:
        msg = Detection3DArray()
        msg.header = Header()
        # The KEY: stamp with a time `inject_ms` in the PAST, simulating a sensor
        # acquisition that the pipeline took `inject_ms` to turn into this output.
        # A little jitter so the percentiles are non-degenerate.
        jitter = self.rng.normal(0, self.inject_s * 0.08)
        past = self.get_clock().now().nanoseconds * 1e-9 - self.inject_s - jitter
        msg.header.stamp.sec = int(past)
        msg.header.stamp.nanosec = int((past - int(past)) * 1e9)
        msg.header.frame_id = "map"
        det = Detection3D()
        hyp = ObjectHypothesisWithPose()
        hyp.hypothesis.class_id = "cup"
        hyp.hypothesis.score = 0.91
        det.results.append(hyp)
        msg.detections.append(det)
        self.pub.publish(msg)


def run_demo(inject_ms: float, seconds: float = 10.0) -> int:
    rclpy.init()
    pub = DemoFusedPublisher(inject_ms)
    probe = LatencyProbe()
    ex = rclpy.executors.MultiThreadedExecutor()
    ex.add_node(pub)
    ex.add_node(probe)
    t = threading.Thread(target=ex.spin, daemon=True)
    t.start()
    time.sleep(seconds)
    ex.shutdown()
    ok = probe.report()
    pub.destroy_node()
    probe.destroy_node()
    rclpy.shutdown()
    return 0 if ok else 1


def run_live(topic: str) -> int:
    rclpy.init()
    probe = LatencyProbe(topic)
    probe.get_logger().info(f"measuring {topic}; Ctrl+C to print the report.")
    try:
        rclpy.spin(probe)
    except KeyboardInterrupt:
        pass
    ok = probe.report()
    probe.destroy_node()
    rclpy.shutdown()
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Perception latency probe.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--inject-ms", type=float, default=22.0,
                        help="demo: injected end-to-end latency in ms")
    parser.add_argument("--topic", default="/perception/objects")
    args = parser.parse_args()
    if args.demo:
        sys.exit(run_demo(args.inject_ms))
    sys.exit(run_live(args.topic))


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--demo --inject-ms 45 — the blown budget)
# -----------------------------------------------------------------------------
#
# [latency_probe] collected 3XX samples
# [latency_probe] end-to-end latency: p50=45.0 p95=4X.X p99=4X.X ms
# [latency_probe] budget: target 30.0 ms, p95 4X.X ms -> FAIL (over by 1X.X ms).
#                 The latency block diagram tells you which hop on the critical
#                 path to cut.
#
# The lesson: the number is the number. If p95 is over budget, you don't argue —
# you go to the latency block diagram (Exercise 1), find the dominant hop on the
# critical path, and cut THAT one. Measuring honestly is the whole point.
# -----------------------------------------------------------------------------
