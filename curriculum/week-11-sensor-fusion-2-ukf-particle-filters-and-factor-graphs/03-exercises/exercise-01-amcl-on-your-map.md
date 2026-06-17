# Exercise 1 — AMCL on Your Week 7 Map

**Goal:** Run `nav2_amcl` — the particle filter from Lecture 1 §6 — against the map you saved in Week 7. You will serve the map, initialize the particle cloud with `/initialpose`, watch the cloud converge in rviz2 from a fuzzy blob to a tight dart, and then deliberately break localization (the kidnapped-robot problem) and recover it. By the end, AMCL is no longer a black box: you can see the particles, name the parameters that move them, and explain why the cloud tightens.

**Estimated time:** 60 minutes. Guided.

---

## Setup

You need three things from earlier weeks:

1. The **Week 7 map**: `map.yaml` and its `map.pgm` (or `.png`), saved from `slam_toolbox`.
2. The **multi-room Gz Sim world** the map was built from, and your Week 3 diff-drive robot that publishes `/scan`, `/odom`, and the `odom → base_link` TF.
3. AMCL and the map server installed:

```bash
sudo apt install ros-jazzy-nav2-amcl ros-jazzy-nav2-map-server ros-jazzy-nav2-lifecycle-manager
```

Source ROS2 Jazzy and your overlay in every terminal:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

---

## Step 1 — Serve the map

AMCL localizes against a *served* map, so start the map server first. It publishes `/map` latched (`RELIABLE` + `TRANSIENT_LOCAL` — exactly the Week 5 latched-state profile, which is why a late-joining AMCL still gets the map):

```bash
ros2 run nav2_map_server map_server --ros-args \
  -p yaml_filename:=$HOME/maps/my_week7_map.yaml \
  -p use_sim_time:=true
```

Map-server and AMCL are **lifecycle nodes** (Week 4) — they start *unconfigured* and must be transitioned to `active`. The easy way is a lifecycle manager that activates both:

```bash
ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args \
  -p use_sim_time:=true \
  -p autostart:=true \
  -p node_names:="['map_server', 'amcl']"
```

Confirm the map is being published:

```bash
ros2 topic info /map -v
# Publisher count: 1 ; Durability: TRANSIENT_LOCAL  (the latched-map profile)
```

---

## Step 2 — Launch AMCL with sane parameters

Save this as `amcl_params.yaml`. The comments call out the Lecture 1 §6 parameters that matter:

```yaml
amcl:
  ros__parameters:
    use_sim_time: true
    base_frame_id: "base_link"
    odom_frame_id: "odom"
    global_frame_id: "map"
    scan_topic: "scan"

    # --- particle count (the "Adaptive" / KLD part) ---
    min_particles: 500
    max_particles: 2000

    # --- odometry sample motion model (your Week 6 odometry quality) ---
    robot_model_type: "nav2_amcl::DifferentialMotionModel"
    alpha1: 0.2     # rotation noise from rotation
    alpha2: 0.2     # rotation noise from translation
    alpha3: 0.2     # translation noise from translation
    alpha4: 0.2     # translation noise from rotation

    # --- likelihood-field measurement model ---
    laser_model_type: "likelihood_field"
    z_hit: 0.5      # weight of the "beam hit the mapped obstacle" Gaussian
    z_rand: 0.5     # weight of the uniform random term (robustness to bad beams)
    sigma_hit: 0.2  # Gaussian width on hit distance (m)
    laser_max_range: 12.0

    # --- when to run an update (don't update if the robot hasn't moved) ---
    update_min_d: 0.25      # meters of motion before an update
    update_min_a: 0.2       # radians of rotation before an update

    # --- kidnapped-robot recovery (random-particle injection) ---
    recovery_alpha_slow: 0.001
    recovery_alpha_fast: 0.1
```

```bash
ros2 run nav2_amcl amcl --ros-args --params-file amcl_params.yaml
```

(If you used the lifecycle manager in Step 1, AMCL is already in the `node_names` list and will be activated for you.)

---

## Step 3 — Visualize the particle cloud in rviz2

```bash
rviz2
```

Add three displays:

- **Map** on `/map` (so you see what AMCL is matching against).
- **LaserScan** on `/scan` (BEST_EFFORT — set the display's reliability to *Best Effort* or it shows nothing; that's the Week 5 mismatch lesson on rviz2's side).
- **PoseArray** on `/particle_cloud` (this is the AMCL particle cloud — each arrow is one particle/hypothesis).

Set the **Fixed Frame** to `map`. At first the `PoseArray` may be empty or scattered — AMCL hasn't been told where the robot is.

---

## Step 4 — Initialize and watch convergence

Click the **2D Pose Estimate** button in rviz2 and click-drag on the map roughly where the robot actually is, pointing in its heading direction. This publishes `/initialpose`. The particle cloud spawns around your guess as a fuzzy blob.

Now drive the robot (teleop, or your Week 4 action server):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Watch the `PoseArray`. As the robot moves and the laser matches the map, the cloud **tightens** — the predict step spreads it, the measurement update reweights it toward poses where the scan lines up with map obstacles, and resampling concentrates it. Within a few meters of driving the fuzzy blob collapses to a tight dart over the true pose. **That collapse is the particle filter converging.** Confirm AMCL is publishing the `map → odom` correction transform:

```bash
ros2 run tf2_ros tf2_echo map odom
```

---

## Step 5 — The kidnapped-robot problem

Now break it on purpose, the way Lecture 1 §6.3 describes. Two ways to "kidnap" the robot:

- **Easy:** click **2D Pose Estimate** somewhere *completely wrong* (a different room). You've told AMCL a confident lie. The cloud spawns in the wrong place.
- **Realistic:** in Gz Sim, teleport the robot model to a new pose without telling AMCL (or just drive it far while AMCL's `recovery_alpha` is too low to react).

Drive the robot. Watch the scan *not match* the map at the cloud's location. With the `recovery_alpha_slow`/`recovery_alpha_fast` parameters set (Step 2), AMCL detects that the average measurement likelihood has dropped and **injects random particles** across the map. Some land near the true pose; the measurement update rewards them; the cloud migrates and re-converges on the correct location. Watch this happen in the `PoseArray` — particles scatter, then a new tight cluster forms in the right room.

Set `recovery_alpha_slow: 0.0` and `recovery_alpha_fast: 0.0`, restart, and repeat the kidnap: now AMCL **cannot recover** — that's particle deprivation (Lecture 1 §5.4) with the recovery mechanism disabled. Seeing both behaviors is the point.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `ros2 topic info /map -v` shows the map served with `TRANSIENT_LOCAL` durability, and rviz2's Map display shows your Week 7 map.
- [ ] After a `/initialpose` and a few meters of driving, the `/particle_cloud` `PoseArray` visibly collapses to a tight cluster on the true pose, and `tf2_echo map odom` shows a stable correction transform.
- [ ] You can name what `alpha3`, `z_hit`, and `max_particles` each do, in one sentence each.
- [ ] You triggered the kidnapped-robot problem and watched AMCL recover via random-particle injection with `recovery_alpha_*` enabled.
- [ ] You confirmed AMCL *cannot* recover with `recovery_alpha_*` set to 0 — demonstrating particle deprivation.

---

## Stretch

- Set `max_particles: 5000`, then `max_particles: 50`, and qualitatively compare convergence speed and CPU (`top` on the amcl process). Find the smallest `max_particles` that still localizes reliably on your map — that's the number you'd ship.
- Crank `alpha3` (translation noise) to `2.0` and to `0.01`. At `2.0` the cloud never tightens (overconfident-in-noise); at `0.01` it can lose the true pose on a slip (overconfident-in-odometry). The honest middle is your Week 6 odometry quality.
- Run `ros2 topic hz /particle_cloud` and confirm AMCL only updates after `update_min_d` meters of motion — it does *not* burn CPU while the robot sits still. That gating is why AMCL is cheap when parked.

---

When this feels comfortable, move to [Exercise 2 — UKF vs EKF](./exercise-02-ukf-vs-ekf.py).
