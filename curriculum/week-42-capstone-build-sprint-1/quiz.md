# Week 42 — Quiz

Thirteen questions on real noise, actuator latency, EKF re-tuning, lifecycle nodes, and cold-boot determinism. Take it with your lecture notes closed. Aim for 11/13 before the Week 48 defense. Answer key at the bottom — don't peek.

---

**Q1.** Your sim IMU used `<noise type="gaussian"><stddev>0.0002</stddev></noise>` and your EKF was tuned against it. On real hardware the heading drifts much more than in sim. Which real-sensor effect, absent from that SDF model, is the most likely dominant cause?

- A) Quantization steps in the ADC.
- B) Gyro bias instability — a slowly-wandering offset that averaging does not remove.
- C) The simulator's timestep being too small.
- D) The IMU saturating at its full-scale range.

---

**Q2.** On an Allan-deviation plot of a gyro, what does the **flat bottom** of the curve give you?

- A) The angle random walk.
- B) The sample rate.
- C) The bias instability (multiply the minimum by ≈ 0.664).
- D) The scale-factor error.

---

**Q3.** You read the Allan deviation σ at τ = 1 s. That value most directly characterizes:

- A) The bias instability.
- B) The white-noise / angle-random-walk term.
- C) The temperature drift.
- D) The quantization step size.

---

**Q4.** A sensor driver fills `header.stamp` with `now()` — the time it finished processing the sample — rather than the capture time, adding a steady 40 ms. At 0.3 m/s, why can this turn a 20 cm trajectory error into a ~2 m one rather than a 1.2 cm one?

- A) Because 40 ms × 0.3 m/s = 1.2 cm, and the EKF triples every error.
- B) Because the EKF fuses measurements at the *wrong* time relative to its prediction and to other sensors, and the inconsistency compounds over many updates.
- C) Because the LiDAR cannot keep up with a 40 ms delay.
- D) Because `now()` is always wrong by exactly 2 m.

---

**Q5.** You run `ros2 topic delay /imu/data` and see a large, positive, growing number. What is the correct first response?

- A) Increase `transform_timeout` in the EKF until the warnings stop.
- B) Fix the driver to stamp with capture time; do not hide the lag by widening timeouts.
- C) Lower the IMU rate so fewer messages are late.
- D) Switch the EKF to `use_sim_time:=true`.

---

**Q6.** On real hardware, what must `use_sim_time` be on every node, and why?

- A) `true` — so all nodes share the simulator clock.
- B) `false` — otherwise a node waits on a `/clock` nobody publishes, or uses time zero, corrupting fusion.
- C) It does not matter on hardware.
- D) `true` on sensors, `false` on the EKF.

---

**Q7.** You model your actuator path as **dead time + first-order lag**. From a step command of 0.3 m/s, how do you read the dead time `Td`?

- A) The time for the measured velocity to reach 63.2% of 0.3 m/s.
- B) The time from the command until the measured velocity first exceeds ~5% of the setpoint (first observable motion).
- C) The total time to reach 0.3 m/s.
- D) The CAN bus baud rate.

---

**Q8.** In `robot_localization`, which matrix is the **primary knob** you raise to absorb a gyro's measured bias instability when you do not estimate gyro bias as an explicit state?

- A) `initial_estimate_covariance`.
- B) The per-message `angular_velocity_covariance` only.
- C) `process_noise_covariance` (the yaw / yaw-rate diagonal entries).
- D) `transform_timeout`.

---

**Q9.** When re-tuning the EKF, why replay a recorded `rosbag2` instead of re-driving the robot for each parameter change?

- A) Replaying is the only way the EKF accepts new parameters.
- B) It isolates the variable: same input data every time, so a drift change is attributable to your parameter change, not to a different drive. It is also far faster and safer.
- C) Re-driving is forbidden by the safety case.
- D) `ros2 bag play` automatically tunes the covariances.

---

**Q10.** During bring-up you push the robot forward by hand and `/odom` x **decreases**. What does this indicate, and is it a software or hardware-config problem?

- A) The IMU is broken; replace it.
- B) The encoder/odometry sign is inverted — a configuration problem to fix before trusting any fusion.
- C) Normal behavior; odometry counts backward by convention.
- D) The EKF has diverged; re-tune `process_noise_covariance`.

---

**Q11.** Why does an ad-hoc launch file that "works when I run it by hand" frequently fail to cold-boot under systemd?

- A) systemd cannot run ROS2.
- B) Ordering races (e.g. EKF starts before its driver), the network not being ready, silent partial failures, and no readiness signal — all of which a human silently fixes interactively.
- C) ROS2 launch files only work in a terminal.
- D) The DDS middleware is disabled at boot.

---

**Q12.** What does a lifecycle node's separation of `configure()` and `activate()` buy a hardened launch graph?

- A) Faster compilation.
- B) The ability to configure every node, confirm all are configured, then activate in explicit dependency order — i.e. deterministic startup.
- C) It removes the need for TF.
- D) It lets nodes share a single process.

---

**Q13.** Why use `Type=notify` (with `systemd-notify --ready` keyed on `/capstone/ready`) for the Path B service, instead of `Type=simple`?

- A) `Type=simple` cannot start ROS2.
- B) So systemd considers the service "started" only when the stack is genuinely ready to accept a goal, making the measured cold-boot time honest rather than "time to fork."
- C) `Type=notify` makes the stack boot faster.
- D) It disables the watchdog.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Bias instability is the slowly-wandering offset that no amount of averaging removes; it is the dominant heading-drift contributor and is *not* captured by the SDF's single Gaussian `stddev`. Quantization (A) and saturation (D) are real but secondary; the timestep (C) is not a sensor effect.
2. **C** — The flat bottom of the Allan curve is the bias-instability floor; multiply the minimum by ≈ 0.664 for B. The angle random walk (A) is read off the −1/2 slope, not the bottom.
3. **B** — At τ = 1 s the curve lies on the white-noise (−1/2-slope) region, so σ(1 s) characterizes the angle random walk. Bias instability is the bottom, not τ = 1 s.
4. **B** — The damage is not the 1.2 cm the robot moved in 40 ms; it is that the filter fuses each measurement at the wrong time relative to its prediction and to the *other* sensor (stamped differently wrong), and the inconsistency compounds across hundreds of updates.
5. **B** — Fix the stamps at the source. Widening `transform_timeout` (A) hides the lag that is also corrupting fusion; it treats a symptom.
6. **B** — On hardware nobody publishes `/clock`; a node on sim time blocks or uses time zero and silently corrupts fusion. It must be `false` everywhere.
7. **B** — Dead time is the pure delay before *any* motion: the time until measured velocity first crosses ~5% of the setpoint. The 63.2% point (A) gives the time constant τ, not `Td`.
8. **C** — `process_noise_covariance` (specifically the yaw / yaw-rate diagonal) is what you raise to absorb the un-removable bias instability when you do not estimate the bias as a state. The per-message covariance (B) sets measurement noise R, not process noise Q.
9. **B** — Replaying one recorded bag isolates the variable so a drift change is attributable to your parameter change, and it is faster and safer than re-driving for every tweak.
10. **B** — Forward-push-with-decreasing-x means the odometry/encoder sign is inverted. It is a config problem and must be fixed before any fusion is trustworthy; the EKF will otherwise silently integrate backwards.
11. **B** — Interactively a human restarts the racing node, waits for the network, and notices a crash. A cold boot has no human, so ordering races, network-not-ready, silent partial failure, and the absence of a readiness signal all become fatal.
12. **B** — Separating configure from activate lets the launch graph sequence startup: configure all, confirm, then activate in dependency order. That is what makes the boot deterministic.
13. **B** — `Type=notify` lets the service signal readiness explicitly (keyed on `/capstone/ready`), so systemd's "started" means "ready to accept a goal," which makes the cold-boot time you measure with `systemd-analyze` defensible rather than just "time to fork."

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially the timestamp-discipline and lifecycle material, which is where integration days are won or lost. If you scored 12 or 13, you are ready to defend your sprint number.
