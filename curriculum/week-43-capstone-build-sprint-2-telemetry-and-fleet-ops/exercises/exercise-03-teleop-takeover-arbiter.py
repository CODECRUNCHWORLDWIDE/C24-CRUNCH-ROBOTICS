#!/usr/bin/env python3
"""Exercise 3 — the control-authority arbiter (one-click teleop takeover).

A single lifecycle-managed node owns the base command topic ``/cmd_vel_out``.
It subscribes to two sources — ``/cmd_vel_auto`` (autonomy) and
``/cmd_vel_teleop`` (operator) — and forwards exactly one, chosen by a latched
control-authority state. Flipping authority is *atomic* and always passes through
a one-cycle safe-stop, so the robot never sees overlapping commands and never
coasts blind.

A ``/control/takeover`` Bool topic is the "button": ``true`` -> TELEOP,
``false`` -> AUTONOMY. The current authority is republished latched on
``/control/authority`` (std_msgs/String), which drives both the dashboard banner
(Foxglove Indicator) and the autonomy behavior tree's yield condition
(``AutonomyHasAuthority`` in Lecture 2).

Why a lifecycle node: while ``inactive`` (boot, OTA trial) the arbiter forwards
NOTHING — a half-booted robot must not drive. Only ``activate`` arms it.

Run:
    python3 exercise-03-teleop-takeover-arbiter.py --ros-args -p control_period:=0.05
    ros2 lifecycle set /control_arbiter configure
    ros2 lifecycle set /control_arbiter activate
    # take over / hand back:
    ros2 topic pub -1 /control/takeover std_msgs/Bool "{data: true}"
    ros2 topic pub -1 /control/takeover std_msgs/Bool "{data: false}"
"""
from __future__ import annotations

from enum import Enum

import rclpy
from geometry_msgs.msg import Twist
from rclpy.lifecycle import LifecycleNode, LifecycleState, TransitionCallbackReturn
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, String


class Authority(str, Enum):
    AUTONOMY = "AUTONOMY"
    TELEOP = "TELEOP"


def _latched(depth: int = 1) -> QoSProfile:
    qos = QoSProfile(depth=depth)
    qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
    return qos


class ControlArbiter(LifecycleNode):
    """Owns /cmd_vel_out. Forwards exactly one source per the latched authority."""

    def __init__(self) -> None:
        super().__init__("control_arbiter")
        self.declare_parameter("control_period", 0.05)   # 20 Hz default
        self.declare_parameter("teleop_watchdog", 0.5)   # s of silence -> safe-stop

        self._authority = Authority.AUTONOMY
        self._active = False                  # set true only between activate/deactivate
        self._latest_auto = Twist()
        self._latest_teleop = Twist()
        self._last_teleop_stamp = 0.0
        self._flip_safe_stop_cycles = 0       # >0 forces a zero output for that many ticks

        # Handles created in on_configure, torn down in on_cleanup.
        self._cmd_out_pub = None
        self._authority_pub = None
        self._timer = None

    # ---- lifecycle transitions -------------------------------------------
    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._cmd_out_pub = self.create_lifecycle_publisher(Twist, "/cmd_vel_out", 10)
        self._authority_pub = self.create_lifecycle_publisher(
            String, "/control/authority", _latched()
        )
        self.create_subscription(Twist, "/cmd_vel_auto", self._on_auto, 10)
        self.create_subscription(Twist, "/cmd_vel_teleop", self._on_teleop, 10)
        self.create_subscription(Bool, "/control/takeover", self._on_takeover, _latched())

        period = float(self.get_parameter("control_period").value)
        self._timer = self.create_timer(period, self._tick)

        self._publish_authority()  # announce AUTONOMY as the boot default
        self.get_logger().info("configured; authority=AUTONOMY (inactive, not driving)")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = True
        # Arm from a known-safe state: zero the output before we start forwarding.
        self._flip_safe_stop_cycles = 1
        self.get_logger().info("ACTIVATED; arbiter is now driving the base")
        return super().on_activate(state)

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._active = False
        self._cmd_out_pub.publish(Twist())   # leave the base stopped, definitively
        self.get_logger().info("DEACTIVATED; base commanded to stop, no longer driving")
        return super().on_deactivate(state)

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._teardown()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        self._teardown()
        return TransitionCallbackReturn.SUCCESS

    def _teardown(self) -> None:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        for handle in (self._cmd_out_pub, self._authority_pub):
            if handle is not None:
                self.destroy_publisher(handle)
        self._cmd_out_pub = None
        self._authority_pub = None

    # ---- command sources --------------------------------------------------
    def _on_auto(self, msg: Twist) -> None:
        self._latest_auto = msg

    def _on_teleop(self, msg: Twist) -> None:
        self._latest_teleop = msg
        self._last_teleop_stamp = self._now()

    def _on_takeover(self, msg: Bool) -> None:
        self.request_authority(Authority.TELEOP if msg.data else Authority.AUTONOMY)

    # ---- the atomic flip --------------------------------------------------
    def request_authority(self, who: Authority) -> None:
        if who == self._authority:
            return                            # idempotent
        # The one-cycle safe-stop happens on the NEXT tick(s) before forwarding.
        self._flip_safe_stop_cycles = 1
        self._authority = who
        self._publish_authority()
        self.get_logger().warn(f"control authority -> {who.value} (safe-stop one cycle)")

    def _publish_authority(self) -> None:
        if self._authority_pub is not None:
            self._authority_pub.publish(String(data=self._authority.value))

    # ---- the control loop -------------------------------------------------
    def _tick(self) -> None:
        if not self._active or self._cmd_out_pub is None:
            return  # inactive: forward nothing. A half-booted robot does not drive.

        # 1. Honor a pending safe-stop: one zero cycle on every flip / arm.
        if self._flip_safe_stop_cycles > 0:
            self._flip_safe_stop_cycles -= 1
            self._cmd_out_pub.publish(Twist())
            return

        # 2. Forward the source that currently holds authority.
        if self._authority == Authority.AUTONOMY:
            self._cmd_out_pub.publish(self._latest_auto)
            return

        # 3. TELEOP: enforce the link watchdog. A robot driven by a dead link halts.
        watchdog = float(self.get_parameter("teleop_watchdog").value)
        if self._now() - self._last_teleop_stamp > watchdog:
            self._cmd_out_pub.publish(Twist())   # safe-stop on stale teleop
            return
        self._cmd_out_pub.publish(self._latest_teleop)

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9


def main() -> None:
    rclpy.init()
    node = ControlArbiter()
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


# ---------------------------------------------------------------------------
# Wiring notes
# ---------------------------------------------------------------------------
# * Re-point autonomy and teleop at the *source* topics, not /cmd_vel directly:
#     - your Nav2 controller -> remap cmd_vel:=/cmd_vel_auto
#     - teleop_twist_keyboard/joy -> remap cmd_vel:=/cmd_vel_teleop
#   and remap the *base driver* to subscribe /cmd_vel_out. Now the arbiter is the
#   ONLY publisher to the base; the two-publisher race is structurally impossible.
#
# * The dashboard banner: add a Foxglove Indicator on /control/authority
#   (latched String) — green for AUTONOMY, blue for TELEOP. It updates the instant
#   the flip happens because /control/authority is published in request_authority().
#
# * Autonomy yields via the AutonomyHasAuthority BT.CPP condition node (Lecture 2):
#   it subscribes the same /control/authority and returns FAILURE while != AUTONOMY,
#   halting the navigation subtree so autonomy STOPS COMPUTING commands, not just
#   stops being forwarded.
#
# * Challenge 1 verifies: flip to TELEOP, drive, flip back, and assert that across
#   each transition /cmd_vel_out went through exactly one zero Twist and never
#   carried two sources in one cycle. Record the whole thing as an MCAP and scrub it.
