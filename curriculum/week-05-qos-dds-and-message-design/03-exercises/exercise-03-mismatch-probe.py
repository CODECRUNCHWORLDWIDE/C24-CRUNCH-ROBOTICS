#!/usr/bin/env python3
# Exercise 3 — The mismatch probe (catch the silent QoS failure in your own logs)
#
# Goal: Deliberately mismatch a publisher and a subscriber, then register the rmw
#       incompatible-QoS event callbacks on BOTH sides so the silent failure
#       becomes LOUD. You will turn the worst failure mode in ROS2 into a log line.
#
# Estimated time: 45 minutes. Runnable.
#
# THE FAILURE WE INDUCE
#
#   Publisher offers : BEST_EFFORT   (a sensor-style publisher)
#   Subscriber wants : RELIABLE      (the default profile)
#
#   Per the request–offered rule (Lecture 1 §3): a BEST_EFFORT publisher CANNOT
#   satisfy a RELIABLE subscriber. The two endpoints discover each other (SEDP
#   runs), but no data link forms. Normally this is SILENT. This program makes it
#   loud by listening for the QoS incompatibility events that rmw fires and that
#   "almost nobody is listening for."
#
# HOW TO USE THIS FILE
#
#   Standalone. Source ROS2 Jazzy and run:
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-mismatch-probe.py
#
#   It runs a publisher and a subscriber in one process under a
#   MultiThreadedExecutor, with deliberately mismatched reliability. Watch:
#     * the incompatible-QoS event callbacks fire on BOTH endpoints,
#     * the subscriber's data callback NEVER fires,
#     * the program reports the diagnosis and exits 0 (the mismatch was detected).
#
#   Then flip MATCH = True and run again: the events do NOT fire, data flows, the
#   subscriber's callback fires, and the program reports "data flowed."
#
#   Cross-check on the wire while it runs (second terminal):
#       ros2 topic info /probe -v
#       # PUBLISHER reliability vs SUBSCRIPTION reliability — see them disagree.
#
# ACCEPTANCE CRITERIA
#
#   [ ] With MATCH = False: both incompatible-QoS callbacks fire, the data
#       callback fires 0 times, the program prints "MISMATCH DETECTED".
#   [ ] With MATCH = True: no incompatibility events, data callback fires,
#       program prints "DATA FLOWED".
#   [ ] You can name the offending policy (Reliability) and the rule it broke.
#   [ ] `ros2 topic info /probe -v` confirms the two reliability values disagree.
#
# Expected output is at the bottom of the file.

import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
# In ROS2 Jazzy these live in rclpy.event_handler. (rclpy.qos_event still works as
# a deprecated alias but emits a DeprecationWarning — use the new module.)
from rclpy.event_handler import (
    PublisherEventCallbacks,
    SubscriptionEventCallbacks,
)
from std_msgs.msg import String

# Flip to True to see the compatible case succeed.
MATCH = False

TOPIC = "probe"

# The QoS-incompatibility reason codes the policy_kind field can carry. We map a
# couple of the common ones to readable names for the log.
POLICY_NAMES = {
    1: "INVALID",
    2: "DURABILITY",
    4: "DEADLINE",
    8: "LIVELINESS",
    16: "RELIABILITY",
    32: "HISTORY",
}


def policy_name(kind: int) -> str:
    return POLICY_NAMES.get(kind, f"policy_kind={kind}")


class ProbePublisher(Node):
    """Always offers BEST_EFFORT. (When MATCH, the subscriber requests BEST_EFFORT too.)"""

    def __init__(self) -> None:
        super().__init__("probe_publisher")
        self.incompatible_events = 0

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        # The load-bearing line of this exercise: register the event callback that
        # fires when a DISCOVERED remote endpoint requests a QoS we can't satisfy.
        callbacks = PublisherEventCallbacks(
            incompatible_qos=self.on_incompatible_qos
        )
        self.pub = self.create_publisher(
            String, TOPIC, qos, event_callbacks=callbacks
        )
        self.timer = self.create_timer(0.5, self.tick)
        self.seq = 0

    def on_incompatible_qos(self, event) -> None:
        self.incompatible_events += 1
        self.get_logger().error(
            f"[PUBLISHER] INCOMPATIBLE QOS — a subscriber requested a policy I do "
            f"not offer. last_policy={policy_name(event.last_policy_kind)}, "
            f"total_count={event.total_count}"
        )

    def tick(self) -> None:
        self.seq += 1
        self.pub.publish(String(data=f"sample {self.seq}"))


class ProbeSubscriber(Node):
    """Requests RELIABLE when MATCH is False (the mismatch), BEST_EFFORT when True."""

    def __init__(self) -> None:
        super().__init__("probe_subscriber")
        self.incompatible_events = 0
        self.data_callbacks = 0

        reliability = (
            ReliabilityPolicy.BEST_EFFORT if MATCH else ReliabilityPolicy.RELIABLE
        )
        qos = QoSProfile(
            reliability=reliability,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        callbacks = SubscriptionEventCallbacks(
            incompatible_qos=self.on_incompatible_qos
        )
        self.sub = self.create_subscription(
            String, TOPIC, self.on_data, qos, event_callbacks=callbacks
        )

    def on_incompatible_qos(self, event) -> None:
        self.incompatible_events += 1
        self.get_logger().error(
            f"[SUBSCRIBER] INCOMPATIBLE QOS — I requested a policy the publisher "
            f"does not offer. last_policy={policy_name(event.last_policy_kind)}, "
            f"total_count={event.total_count}"
        )

    def on_data(self, msg: String) -> None:
        self.data_callbacks += 1
        self.get_logger().info(f"[SUBSCRIBER] data callback: '{msg.data}'")


def main() -> None:
    rclpy.init()
    executor = MultiThreadedExecutor()

    publisher = ProbePublisher()
    subscriber = ProbeSubscriber()
    executor.add_node(publisher)
    executor.add_node(subscriber)

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    mode = "MATCH (BEST_EFFORT <- BEST_EFFORT)" if MATCH else \
        "MISMATCH (BEST_EFFORT publisher <- RELIABLE subscriber)"
    print(f"[probe] running in {mode} mode for 4 seconds...")
    time.sleep(4.0)

    executor.shutdown()

    print("\n==================== DIAGNOSIS ====================")
    print(f"publisher  incompatible-QoS events: {publisher.incompatible_events}")
    print(f"subscriber incompatible-QoS events: {subscriber.incompatible_events}")
    print(f"subscriber data callbacks fired   : {subscriber.data_callbacks}")

    if not MATCH:
        ok = (
            subscriber.data_callbacks == 0
            and (publisher.incompatible_events > 0 or subscriber.incompatible_events > 0)
        )
        if ok:
            print("MISMATCH DETECTED: the RELIABILITY policy broke the request–offered "
                  "rule (BEST_EFFORT offer cannot satisfy a RELIABLE request). "
                  "No data flowed — and now you have it in the log, not as a mystery.")
        else:
            print("UNEXPECTED: with a mismatch, expected 0 data callbacks and >=1 "
                  "incompatibility event. Check your rmw version and try again.")
    else:
        if subscriber.data_callbacks > 0 and subscriber.incompatible_events == 0:
            print("DATA FLOWED: compatible QoS, no incompatibility events. This is what "
                  "a correctly-matched topic looks like.")
        else:
            print("UNEXPECTED: with MATCH=True, expected data callbacks and no events.")
    print("===================================================")

    publisher.destroy_node()
    subscriber.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (MATCH = False — the deliberate mismatch)
# -----------------------------------------------------------------------------
#
# [probe] running in MISMATCH (BEST_EFFORT publisher <- RELIABLE subscriber) mode ...
# [ERROR] [probe_publisher]: [PUBLISHER] INCOMPATIBLE QOS — a subscriber requested a
#         policy I do not offer. last_policy=RELIABILITY, total_count=1
# [ERROR] [probe_subscriber]: [SUBSCRIBER] INCOMPATIBLE QOS — I requested a policy the
#         publisher does not offer. last_policy=RELIABILITY, total_count=1
#
# ==================== DIAGNOSIS ====================
# publisher  incompatible-QoS events: 1
# subscriber incompatible-QoS events: 1
# subscriber data callbacks fired   : 0
# MISMATCH DETECTED: the RELIABILITY policy broke the request–offered rule ...
# ===================================================
#
# Expected output (MATCH = True)
# -----------------------------------------------------------------------------
#
# [probe] running in MATCH (BEST_EFFORT <- BEST_EFFORT) mode for 4 seconds...
# [INFO] [probe_subscriber]: [SUBSCRIBER] data callback: 'sample 1'
# [INFO] [probe_subscriber]: [SUBSCRIBER] data callback: 'sample 2'
# ...
# ==================== DIAGNOSIS ====================
# publisher  incompatible-QoS events: 0
# subscriber incompatible-QoS events: 0
# subscriber data callbacks fired   : 7
# DATA FLOWED: compatible QoS, no incompatibility events. ...
# ===================================================
#
# NOTE: exact event counts depend on your rmw vendor and timing, but the SHAPE is
# invariant: mismatch => 0 data callbacks + >=1 incompatibility event; match =>
# data flows + 0 events. That is the silent failure, made loud.
# -----------------------------------------------------------------------------
