#!/usr/bin/env python3
# Exercise 3 — The bias-subtraction node (calibrate a live IMU stream)
#
# Goal: Build a rclpy node that, while the robot is held STILL, estimates the
#       stationary gyro and accel bias, then switches to a running phase that
#       subtracts the bias, fills honest covariance, and re-publishes a calibrated
#       /imu/data_calibrated -- the stream Week 10's EKF will fuse.
#
# Estimated time: 60 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone ROS2 node. Source ROS2 Jazzy and run (no package needed):
#
#       source /opt/ros/jazzy/setup.bash
#       python3 exercise-03-bias-subtraction-node.py
#
#   You need an /imu/data publisher: your week-3 robot's sim IMU, a real IMU
#   driver, or `ros2 bag play` of a recorded log. Keep the robot STILL during the
#   calibration phase (the node prints when it starts and finishes calibrating).
#
#   Verify the calibration worked:
#       ros2 topic echo /imu/data_calibrated --field angular_velocity
#       # The angular_velocity should hover near ZERO when stationary, while
#       # /imu/data (raw) shows a small constant offset (the bias).
#
# WHAT TO IMPLEMENT
#
#   Fill in the TODOs: the bias estimate at the end of calibration, the bias
#   subtraction in the running phase, and the covariance fill.
#
# ACCEPTANCE CRITERIA
#
#   [ ] During calibration the node accumulates samples and prints the estimated
#       gyro_bias and accel_bias.
#   [ ] In the running phase, stationary /imu/data_calibrated angular_velocity is
#       near zero (raw was offset by the bias).
#   [ ] The published message has angular_velocity_covariance populated and
#       orientation_covariance[0] == -1 (no orientation from a 6-DOF IMU).
#   [ ] The header (stamp + frame_id) is preserved from the input message.
#
# Expected output is at the bottom of the file.

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

GRAVITY = 9.80665  # m/s^2

# From YOUR Allan plot (Exercise 2). Defaults are plausible MEMS values; replace
# with your measured noise densities for honest covariance.
GYRO_NOISE_DENSITY = 1.2e-3   # rad/sqrt(s)
ACCEL_NOISE_DENSITY = 2.0e-3  # (m/s^2)/sqrt(s)
SAMPLE_RATE = 100.0           # Hz


class ImuBiasCorrector(Node):
    def __init__(self) -> None:
        super().__init__("imu_bias_corrector")
        self.declare_parameter("calib_samples", 3000)  # ~30 s at 100 Hz
        self.n_target = int(self.get_parameter("calib_samples").value)

        self.gyro_acc = np.zeros(3)
        self.acc_acc = np.zeros(3)
        self.count = 0
        self.gyro_bias = None
        self.accel_bias = None

        # Sensor QoS on both ends (Week 5).
        self.sub = self.create_subscription(
            Imu, "/imu/data", self.on_imu, qos_profile_sensor_data
        )
        self.pub = self.create_publisher(
            Imu, "/imu/data_calibrated", qos_profile_sensor_data
        )
        self.var_w = GYRO_NOISE_DENSITY ** 2 * SAMPLE_RATE
        self.var_a = ACCEL_NOISE_DENSITY ** 2 * SAMPLE_RATE
        self.get_logger().info(
            f"calibrating: hold the robot STILL for {self.n_target} samples..."
        )

    def on_imu(self, msg: Imu) -> None:
        g = np.array([msg.angular_velocity.x,
                      msg.angular_velocity.y,
                      msg.angular_velocity.z])
        a = np.array([msg.linear_acceleration.x,
                      msg.linear_acceleration.y,
                      msg.linear_acceleration.z])

        if self.gyro_bias is None:
            # --- Calibration phase ---
            self.gyro_acc += g
            self.acc_acc += a
            self.count += 1
            if self.count >= self.n_target:
                # TODO 1: set self.gyro_bias to the mean of the accumulated gyro.
                #         set self.accel_bias to the mean accel MINUS gravity
                #         (assume z up at rest: subtract [0,0,GRAVITY]).
                raise NotImplementedError("implement TODO 1 (compute biases)")
            return

        # --- Running phase ---
        out = Imu()
        out.header = msg.header               # preserve acquisition stamp + frame
        out.orientation = msg.orientation

        # TODO 2: subtract self.gyro_bias from g and self.accel_bias from a, and
        #         assign into out.angular_velocity.{x,y,z} and
        #         out.linear_acceleration.{x,y,z}.
        raise NotImplementedError("implement TODO 2 (subtract bias)")

        # TODO 3: fill covariance:
        #   out.angular_velocity_covariance = diag(self.var_w) (row-major 3x3)
        #   out.linear_acceleration_covariance = diag(self.var_a)
        #   out.orientation_covariance = [-1, 0,0, 0,0,0, 0,0,0]  (no orientation)
        # then self.pub.publish(out)


def main() -> None:
    rclpy.init()
    node = ImuBiasCorrector()
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
# Expected output (once the TODOs are implemented)
# -----------------------------------------------------------------------------
#
# [INFO] [imu_bias_corrector]: calibrating: hold the robot STILL for 3000 samples...
# [INFO] [imu_bias_corrector]: gyro_bias  (rad/s) = [ 0.0011 -0.0007  0.0087]
#                              accel_bias (m/s^2) = [ 0.04   -0.02    0.03 ]
#
# $ ros2 topic echo /imu/data_calibrated --field angular_velocity
# x: 0.00004
# y: -0.00002
# z: 0.00009        <-- near zero when stationary; raw /imu/data showed ~0.0087 on z
#
# The whole point: raw z-gyro reads the bias (~0.0087 rad/s ~ 0.5 deg/s) at rest;
# the calibrated stream reads ~0. Integrate the raw stream and yaw ramps 30 deg/min;
# integrate the calibrated stream and it barely moves. That drift reduction is what
# you measure in the challenge.
# -----------------------------------------------------------------------------
