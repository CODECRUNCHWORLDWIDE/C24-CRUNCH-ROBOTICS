#!/usr/bin/env python3
# Exercise 3 — Closed-loop yaw PID on the diff-drive robot (with feedforward)
#
# Goal: Close a real control loop on the week-3 robot. A PID consumes the IMU yaw,
#       computes an angular-velocity command, adds a velocity feedforward term,
#       and publishes /cmd_vel. You will drive the robot to three yaw setpoints
#       (45, 90, 180 degrees) and log the step response so you can measure rise
#       time, overshoot and settling (Exercise 1's analyze_step works on the log).
#
# Estimated time: 50 minutes. Runnable.
#
# TWO MODES
#
#   Real robot (default): subscribes /imu/data, publishes /cmd_vel. Bring up your
#   week-3 robot in Gz Sim first.
#
#       source /opt/ros/jazzy/setup.bash
#       ros2 launch crunchbot_bringup robot.launch.py    # your week-3 sim
#       python3 exercise-03-yaw-rate-pid.py
#
#   Built-in simulator (no ROS / broken sim): a yaw plant integrates the commanded
#   angular velocity with first-order lag. Every learning objective still lands.
#
#       python3 exercise-03-yaw-rate-pid.py --sim
#
# WHAT TO OBSERVE
#
#   * The robot turns to each setpoint and HOLDS it (integral kills the offset).
#   * With FEEDFORWARD on, the approach is faster and lags less than feedback alone.
#   * The step-response log (yaw_step_<deg>.csv) feeds Exercise 1's analyze_step.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The robot (or sim) reaches each of 45/90/180 deg within ~1 deg steady-state.
#   [ ] A CSV per setpoint is written; analyze_step reports overshoot <= ~15%.
#   [ ] Turning USE_FEEDFORWARD off makes the approach visibly laggier (compare logs).
#   [ ] You can state why the feedforward term helps tracking but not regulation.
#
# Expected output is at the bottom of the file.

import argparse
import csv
import math
import sys
import time

# Flip to False to see how much the velocity feedforward was buying you.
USE_FEEDFORWARD = True

# Control loop rate and actuator limit (rad/s) for the base's angular velocity.
RATE_HZ = 50.0
DT = 1.0 / RATE_HZ
W_MAX = 1.5             # max |angular velocity| the base can do
SETPOINTS_DEG = [45.0, 90.0, 180.0]
SETTLE_TIME_S = 4.0    # how long to hold each setpoint before logging the next


def wrap_to_pi(a: float) -> float:
    """Wrap an angle to (-pi, pi]. Essential: yaw error must take the short way."""
    return math.atan2(math.sin(a), math.cos(a))


class YawController:
    """PID on yaw (regulation) + velocity feedforward on the reference yaw RATE.

    For a pure step setpoint the reference rate is ~0 except at the step, so the
    feedforward mostly helps when the setpoint MOVES (tracking). We include it so
    you can A/B it, and so the same controller works when you later feed it a
    yaw-rate trajectory instead of steps.
    """

    def __init__(self, kp, ki, kd, dt, tf=0.02, kv=1.0):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.kv = kv
        self.alpha = dt / (tf + dt) if tf > 0 else 1.0
        self.kb = 1.0 / ki if ki > 0 else 0.0
        self.integral = 0.0
        self.prev_meas = 0.0
        self.df = 0.0
        self.prev_setpoint = 0.0

    def reset(self):
        self.integral = 0.0
        self.df = 0.0

    def update(self, setpoint_yaw, measured_yaw):
        # Error on the circle: take the short way around.
        error = wrap_to_pi(setpoint_yaw - measured_yaw)

        p = self.kp * error
        # Derivative on measurement (no kick), filtered (no noise blowup).
        raw_d = -wrap_to_pi(measured_yaw - self.prev_meas) / self.dt
        self.df += self.alpha * (raw_d - self.df)
        d = self.kd * self.df

        # Feedforward: command from the reference RATE (finite-diff of the setpoint).
        ref_rate = wrap_to_pi(setpoint_yaw - self.prev_setpoint) / self.dt
        u_ff = self.kv * ref_rate if USE_FEEDFORWARD else 0.0

        u_unsat = u_ff + p + self.ki * self.integral + d
        u = max(-W_MAX, min(W_MAX, u_unsat))
        # Anti-windup, with the feedforward excluded from the back-calc reference.
        self.integral += (error + self.kb * (u - u_unsat)) * self.dt

        self.prev_meas = measured_yaw
        self.prev_setpoint = setpoint_yaw
        return u


# ---------------------------------------------------------------------------
# Built-in yaw plant (used with --sim or when rclpy is unavailable).
# ---------------------------------------------------------------------------
class YawSimPlant:
    """yaw_dot tracks commanded w with first-order lag tau; light damping/noise."""

    def __init__(self, tau=0.15):
        self.yaw = 0.0
        self.w = 0.0
        self.tau = tau

    def step(self, w_cmd, dt):
        # Actuator lag: actual angular velocity chases the command.
        self.w += (w_cmd - self.w) * (dt / self.tau)
        self.yaw = wrap_to_pi(self.yaw + self.w * dt)
        return self.yaw


def run_sim(gains):
    ctrl = YawController(*gains, dt=DT)
    plant = YawSimPlant()
    print(f"[sim] yaw PID, feedforward={'ON' if USE_FEEDFORWARD else 'OFF'}")
    for sp_deg in SETPOINTS_DEG:
        sp = math.radians(sp_deg)
        ctrl.reset()
        rows = []
        t = 0.0
        n = int(SETTLE_TIME_S / DT)
        meas = plant.yaw
        for _ in range(n):
            u = ctrl.update(sp, meas)
            meas = plant.step(u, DT)
            rows.append((t, math.degrees(sp), math.degrees(meas), u))
            t += DT
        final = math.degrees(meas)
        err = abs(sp_deg - final)
        fname = f"yaw_step_{int(sp_deg)}.csv"
        _write_csv(fname, rows)
        print(f"  setpoint {sp_deg:5.0f} deg -> final {final:7.2f} deg "
              f"(err {err:4.2f} deg)  log={fname}  {'OK' if err < 1.5 else 'CHECK'}")


def _write_csv(fname, rows):
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "setpoint_deg", "yaw_deg", "cmd_w"])
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Real-robot path: rclpy node consuming /imu/data, publishing /cmd_vel.
# ---------------------------------------------------------------------------
def run_robot(gains):
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from geometry_msgs.msg import Twist

    def yaw_from_quat(q):
        # ZYX yaw from a quaternion (x, y, z, w).
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny, cosy)

    class YawNode(Node):
        def __init__(self):
            super().__init__("yaw_rate_pid")
            self.ctrl = YawController(*gains, dt=DT)
            self.meas_yaw = 0.0
            self.have_imu = False
            self.setpoints = list(SETPOINTS_DEG)
            self.sp = math.radians(self.setpoints.pop(0))
            self.sp_deadline = time.time() + SETTLE_TIME_S
            self.rows = []
            self.t0 = time.time()
            # Sensor QoS (Week 5!): the IMU is BEST_EFFORT.
            self.create_subscription(Imu, "/imu/data", self.on_imu, qos_profile_sensor_data)
            self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
            self.create_timer(DT, self.on_tick)
            self.get_logger().info(
                f"yaw PID up; feedforward={'ON' if USE_FEEDFORWARD else 'OFF'}; "
                f"first setpoint {math.degrees(self.sp):.0f} deg")

        def on_imu(self, msg: Imu):
            self.meas_yaw = yaw_from_quat(msg.orientation)
            self.have_imu = True

        def on_tick(self):
            if not self.have_imu:
                return
            u = self.ctrl.update(self.sp, self.meas_yaw)
            tw = Twist()
            tw.angular.z = u
            self.cmd_pub.publish(tw)
            self.rows.append((time.time() - self.t0, math.degrees(self.sp),
                              math.degrees(self.meas_yaw), u))
            if time.time() >= self.sp_deadline:
                final = math.degrees(self.meas_yaw)
                fname = f"yaw_step_{int(math.degrees(self.sp))}.csv"
                _write_csv(fname, self.rows)
                self.get_logger().info(
                    f"setpoint {math.degrees(self.sp):.0f} deg -> final {final:.2f} deg; "
                    f"log={fname}")
                self.rows = []
                if not self.setpoints:
                    tw = Twist()
                    self.cmd_pub.publish(tw)   # stop
                    self.get_logger().info("done; all setpoints driven.")
                    raise KeyboardInterrupt
                self.sp = math.radians(self.setpoints.pop(0))
                self.ctrl.reset()
                self.sp_deadline = time.time() + SETTLE_TIME_S

    rclpy.init()
    node = YawNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Closed-loop yaw PID + feedforward.")
    parser.add_argument("--sim", action="store_true",
                        help="use the built-in yaw plant instead of the real robot.")
    args = parser.parse_args()

    # TODO 1: replace these with the gains you tuned. A reasonable starting point
    #   for the sim plant is Kp~3.0, Ki~0.5, Kd~0.4. Tune against the CSV logs the
    #   same way you tuned Exercise 1, using analyze_step.
    gains = (3.0, 0.5, 0.4)

    if args.sim:
        run_sim(gains)
        return
    try:
        run_robot(gains)
    except ImportError:
        print("rclpy not available; falling back to the built-in simulator (--sim).")
        run_sim(gains)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--sim, tuned gains, feedforward ON)
# -----------------------------------------------------------------------------
#
# [sim] yaw PID, feedforward=ON
#   setpoint    45 deg ->  final   44.7 deg (err 0.3 deg)  log=yaw_step_45.csv  OK
#   setpoint    90 deg ->  final   89.6 deg (err 0.4 deg)  log=yaw_step_90.csv  OK
#   setpoint   180 deg ->  final  179.5 deg (err 0.5 deg)  log=yaw_step_180.csv OK
#
# Then run Exercise 1's analyze_step on each CSV to get rise/overshoot/settling.
#
# Set USE_FEEDFORWARD = False and re-run: the final values are still reached (the
# integral guarantees that for a STEP), but if you feed a MOVING yaw reference the
# difference is dramatic — feedback alone lags the moving target, feedforward
# cancels the lag. That is the regulation-vs-tracking lesson, on your own robot.
# -----------------------------------------------------------------------------
