# Exercise 1 — Read an EKF Config

**Goal:** Given a real `robot_localization` `ekf.yaml`, predict — *before running anything* — exactly what state fields it fuses from each sensor, which TF transform it publishes, whether it's planar, and whether it contains the classic double-publish or double-count footgun. You will train the skill that separates someone who copy-pastes a config from someone who *reads* one: turning the boolean matrices back into the covariance decisions they encode.

**Estimated time:** 45 minutes. Guided.

---

## Setup

No robot required for the reading; you'll optionally verify against a live EKF at the end. Here is the config to analyze. Read it slowly.

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0
    two_d_mode: true
    publish_tf: true
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom

    odom0: /odom
    odom0_config: [false, false, false,
                   false, false, false,
                   true,  true,  false,
                   false, false, true,
                   false, false, false]
    odom0_differential: false

    imu0: /imu/data_calibrated
    imu0_config: [false, false, false,
                  false, false, true,
                  false, false, false,
                  false, false, true,
                  true,  false, false]
    imu0_differential: false
    imu0_remove_gravitational_acceleration: true
```

The `_config` matrix order is, row by row (15 elements):

```
[ x,     y,     z,
  roll,  pitch, yaw,
  vx,    vy,    vz,
  vroll, vpitch,vyaw,
  ax,    ay,    az  ]
```

---

## Step 1 — Decode `odom0_config`

Map each `true` to its state field:

- Row 1 (`x,y,z`): all `false` → **absolute position NOT fused** from odom. Why? (Lecture 1 §7: wheel position drifts.)
- Row 2 (`roll,pitch,yaw`): all `false` → orientation not from odom.
- Row 3 (`vx,vy,vz`): `vx,vy` `true` → **linear velocity fused**. Why? (Velocity doesn't drift; it's what the wheels actually measure.)
- Row 4 (`vroll,vpitch,vyaw`): `vyaw` `true` → **yaw rate fused** from odom.
- Row 5 (accel): none.

Write one sentence: *"From wheel odometry, this EKF takes ____ and ____."* (Answer: linear velocity `vx, vy` and yaw rate `vyaw`.)

---

## Step 2 — Decode `imu0_config`

- Row 2 (`yaw`): `true` → **absolute yaw fused** from the IMU.
- Row 4 (`vyaw`): `true` → **yaw rate fused** from the IMU.
- Row 5 (`ax`): `true` → forward linear acceleration fused.

Write: *"From the IMU, this EKF takes ____, ____, and ____."* (Answer: absolute yaw, yaw rate, and forward accel `ax`.)

---

## Step 3 — Check for the double-count footgun

Now the diagnostic question: **is any absolute quantity fused from two sources?**

- Absolute position: odom `false`, IMU `false` → fine (nothing fuses absolute x,y — correct; an absolute source like AMCL would, in a second EKF).
- Absolute yaw: odom `false`, IMU `true` → fused from *exactly one* source (the IMU). **Good.**
- Yaw rate: odom `true`, IMU `true` → fused from *both*. **Is this a problem?**

Here's the subtlety: fusing the same *rate* from two sources is generally OK (they're independent noisy measurements of the same rate, and the filter correctly combines them — more information). Fusing the same *absolute* quantity from two drifting sources is the dangerous case (double-counting drift, overconfidence). This config fuses yaw rate from both (acceptable) and absolute yaw from only the IMU (correct). **No footgun.** State why.

---

## Step 4 — Identify the TF it publishes

- `publish_tf: true`, `world_frame: odom` → this EKF publishes the **`odom → base_link`** transform.
- So: **your wheel-odometry node must NOT also broadcast `odom→base_link`**, or you get the two-publisher conflict (Lecture 2 §2). It should publish the `/odom` *topic* only.

Write: *"This EKF owns `odom→base_link`; the wheel-odom node must publish the topic but not the transform."*

---

## Step 5 — Confirm planar mode

`two_d_mode: true` → `z`, `roll`, `pitch` and their rates are forced to zero. Correct for a diff-drive ground robot. State what would go wrong if it were `false` (the filter chases altitude/tilt noise and feeds garbage into the planar estimate).

---

## Step 6 (optional) — Verify against a live EKF

If you have the robot up:

```bash
ros2 launch crunch_localization ekf.launch.py
ros2 param dump /ekf_filter_node | grep -A2 odom0_config    # confirm what's loaded
ros2 run tf2_tools view_frames                              # exactly one odom->base_link?
ros2 topic echo /odometry/filtered --field pose.pose        # fused pose flowing?
```

`view_frames` showing a single `odom→base_link` arrow confirms your Step 4 reading.

---

## Acceptance criteria

You can mark this exercise done when you can state, from the YAML alone:

- [ ] What `odom0` contributes (linear velocity + yaw rate) and *why* absolute position is excluded.
- [ ] What `imu0` contributes (absolute yaw + yaw rate + forward accel).
- [ ] Whether any *absolute* quantity is double-counted (no — absolute yaw is IMU-only).
- [ ] Which transform the EKF publishes (`odom→base_link`) and the constraint that implies (one publisher).
- [ ] Why `two_d_mode: true` is correct here.

---

## Stretch

- **Plant a footgun and spot it.** Edit a copy so `odom0_config` *also* fuses absolute `yaw` (row 2, position 6 → `true`). Now absolute yaw comes from *two* sources. Explain the failure: overconfidence and possible divergence as the two drifting yaws get double-counted. This is the edit that turns a good config into a bad one with one boolean.
- **Add a second EKF.** Sketch the `world_frame: map` EKF that would publish `map→odom`, fed by `odom0`, `imu0`, *and* a global `pose0` (AMCL, later). Note that it must *not* also publish `odom→base_link` — the two EKFs split the transform chain.
- **Covariance check.** Add the commands to verify the *inputs'* covariance are honest (`/odom` pose.covariance non-zero; IMU angular_velocity_covariance = your Week 9 numbers) — the `R` the filter will use.

---

When this feels comfortable, move to [Exercise 2 — The scalar Kalman filter](exercise-02-scalar-kalman.py).
