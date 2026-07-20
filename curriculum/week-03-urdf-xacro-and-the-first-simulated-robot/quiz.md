# Week 3 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 4. Most are multiple choice; a few ask you to compute or to spot the bug. Answer key is at the bottom — don't peek.

This quiz is graded on the same standard as a design review: there is one *best* answer, and "it compiles" or "it spawned" is not the bar. The bar is "it is physically honest and it will still be honest in six months."

---

**Q1.** Which statement best captures what a URDF *is*?

- A) A 3D model of the robot, like an `.stl` or `.dae`, written in XML instead of binary.
- B) A structured claim about the robot's kinematics and dynamics — where joints are, which way they turn, mass, and how that mass is distributed.
- C) A configuration file read only by rviz2 to know what color to draw each link.
- D) The serialized output of the physics engine after the first simulation step.

---

**Q2.** A link in your URDF has a `<visual>` and a `<collision>` block but **no** `<inertial>` block. You load it into rviz2 and it looks perfect. You spawn it into Gz Sim and it behaves erratically. Why?

- A) rviz2 and Gz Sim use incompatible mesh formats; the visual must be a `.dae` for Gz.
- B) rviz2 never reads the `<inertial>` block, so the missing inertial is invisible there; Gz Sim's physics integrator needs it and substitutes a degenerate default when it's absent.
- C) The `<collision>` block must always come before the `<visual>` block, and Gz Sim enforces the ordering.
- D) Nothing is wrong; a missing `<inertial>` is always lumped silently into the parent link with no consequence.

---

**Q3.** You have a solid box chassis: mass `m = 2.0 kg`, dimensions `0.4 m (x) × 0.3 m (y) × 0.1 m (z)`. Using the closed-form equations, what is `Izz` (the moment about the vertical axis)?

- A) `0.0167 kg·m²`
- B) `0.0283 kg·m²`
- C) `0.0417 kg·m²`
- D) `1.0 kg·m²`

---

**Q4.** Which of the following sets of principal moments **cannot** correspond to any real rigid body?

- A) `Ixx = 0.010`, `Iyy = 0.020`, `Izz = 0.025`
- B) `Ixx = 0.050`, `Iyy = 0.050`, `Izz = 0.090`
- C) `Ixx = 0.001`, `Iyy = 0.001`, `Izz = 0.010`
- D) `Ixx = 0.030`, `Iyy = 0.030`, `Izz = 0.040`

---

**Q5.** Your robot trembles and then flings its parts across the world within the **first simulation step** after spawn. Which of the four explode-on-spawn causes is by far the most likely?

- A) Self-colliding collision geometry (Cause 3).
- B) A degenerate joint with a zero axis (Cause 4).
- C) A bad inertia tensor — the factor-of-1000 classic (Cause 1).
- D) The bridge isn't running, so `/clock` never arrives.

---

**Q6.** Which joint type is correct for a **driven wheel** on a differential-drive base?

- A) `fixed` — the wheel is rigidly attached to the chassis.
- B) `revolute` — a hinge with `lower` and `upper` angle limits.
- C) `continuous` — a revolute joint with no angle limit; it can spin forever.
- D) `prismatic` — a linear slider along the wheel's axis.

---

**Q7.** In the wheel joint below, what is the purpose of `rpy="-1.5708 0 0"` in the `<origin>`?

```xml
<joint name="left_wheel_joint" type="continuous">
  <parent link="base_link"/>
  <child link="left_wheel"/>
  <origin xyz="0.0 0.18 0.0" rpy="-1.5708 0 0"/>
  <axis xyz="0 0 1"/>
</joint>
```

- A) It tilts the wheel 90° so the cylinder's natural symmetry (z) axis points along the robot's +y, making it stand up like a wheel and roll about the declared `<axis>`.
- B) It is cosmetic; rviz2 needs it to draw the wheel but the physics engine ignores it.
- C) It converts the angle from degrees to radians at load time.
- D) It offsets the wheel's center of mass so the robot leans left.

---

**Q8.** A teammate says: "I can see `/scan` when I run `gz topic -l`, but `ros2 topic list` doesn't show it. The simulator is broken." What's the actual problem?

- A) The LiDAR sensor plugin crashed; Gz is showing a stale cached topic.
- B) ROS2 and Gz Sim are two separate middleware universes; a Gz topic is invisible to ROS2 until you bridge it with `ros_gz_bridge`.
- C) `ros2 topic list` only shows topics with at least one subscriber; add a subscriber and it will appear.
- D) The `ROS_DOMAIN_ID` is set differently in the two terminals.

---

**Q9.** You publish to `/cmd_vel` from a `rclpy` node on ROS2 Jazzy. The robot doesn't move, and `gz topic -e -t /cmd_vel` shows nothing arriving on the Gz side. The DiffDrive plugin and joint names are confirmed correct. What is the single most likely cause?

- A) The wheel inertia tensor is wrong.
- B) You published `geometry_msgs/msg/Twist`, but on Jazzy `/cmd_vel` is `geometry_msgs/msg/TwistStamped`, so the bridge type/direction doesn't match.
- C) The chassis mass is too high for the wheels to move.
- D) `use_sim_time` is set to `false` on the simulator.

---

**Q10.** The DiffDrive plugin declares `<wheel_radius>0.05</wheel_radius>`, but the URDF wheel cylinder actually has `radius="0.06"`. The robot spawns clean and drives. What goes wrong?

- A) Nothing — the plugin reads the radius from the URDF and ignores its own parameter.
- B) The robot refuses to move because the two radii disagree.
- C) The plugin commands wheel speeds for a 0.05 m wheel, but the real wheel covers more ground per revolution, so the reported odometry disagrees with actual motion — odometry drifts even with zero wheel slip.
- D) The wheel explodes because the collision radius is larger than the inertial radius.

---

**Q11.** Why do we run **every** ROS2 node this week with `use_sim_time: true`?

- A) It makes the nodes start faster.
- B) So node timestamps come from the simulator's `/clock`, not wall-clock; otherwise sensor stamps and the simulated world disagree about what time it is.
- C) It is required to load the DiffDrive plugin.
- D) It disables the garbage collector so timing is deterministic.

---

**Q12.** What is the correct order of the explode-on-spawn diagnosis workflow, *before* you spawn into physics?

- A) Spawn first, watch it explode, then guess.
- B) Expand the xacro to URDF and run `check_urdf`; read every `<mass>`; run the inertia sanity check (positive diagonals, triangle inequality, order of magnitude) — only then spawn.
- C) Restart the computer, reinstall Gz Sim, then spawn.
- D) Increase all masses by 10× until it stops exploding.

---

**Q13.** Compute it. A caster ball is a solid sphere with `radius = 0.025 m` and `mass = 0.05 kg`. What is each diagonal entry of its inertia tensor (`Ixx = Iyy = Izz`)?

- A) `1.25e-5 kg·m²`
- B) `1.25e-2 kg·m²`
- C) `3.13e-3 kg·m²`
- D) `0.05 kg·m²`

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — A URDF asserts kinematics and dynamics; the mesh (`.stl`/`.dae`) is the model. The whole point of Lecture 1: it is a *claim*, not a CAD file. The physics engine reads the claim literally.

2. **B** — rviz2 draws the `<visual>` block and never reads `<inertial>`, so a robot can look perfect there while being dynamically broken. Gz Sim's integrator needs the inertial; when it's missing it substitutes a degenerate default with tiny mass/inertia, which behaves erratically. Every dynamic link gets all three blocks.

3. **C** — `Izz = (1/12)·m·(w² + d²) = (1/12)·2·(0.4² + 0.3²) = (1/12)·2·0.25 = 0.04167 kg·m²`. A is `Ixx`, B is `Iyy`. D is the factor-of-many disaster — over an order of magnitude too big.

4. **C** — Triangle inequality: `Ixx + Iyy ≥ Izz` must hold for all three pairings. For C, `Ixx + Iyy = 0.002 < Izz = 0.010` — violated, so it corresponds to no physical mass distribution. (A: `0.030 ≥ 0.025` ✓ and the others hold. B: `0.100 ≥ 0.090` ✓. D: `0.060 ≥ 0.040` ✓.)

5. **C** — Instant, first-step detonation is the signature of a bad inertia tensor (Cause 1), the ~70% case. Self-collision (Cause 3) and joint problems (Cause 4) tend to show after the robot settles for a moment. D wouldn't make it explode — it would make it sit still and never receive commands.

6. **C** — A drive wheel spins without limit, so it is `continuous` (revolute with no `<limit>`). `revolute` is for limited hinges (an elbow); `fixed` adds no DOF; `prismatic` is a linear slider.

7. **A** — The cylinder's natural symmetry axis is its local z, for which we computed `Izz` as the spin moment. Rotating −90° about x stands the wheel up so that local z points along +y (the rolling axis), and `<axis xyz="0 0 1"/>` then spins about exactly that axis. This keeps the inertia simple and the kinematics aligned. The physics engine very much does read the origin.

8. **B** — Two universes plus a bridge. `gz topic -l` lists the Gz side; `ros2 topic list` lists the ROS side; they are different middlewares. A topic is invisible across the gap until `ros_gz_bridge` translates it. Nothing is broken.

9. **B** — On Jazzy `/cmd_vel` is `geometry_msgs/msg/TwistStamped`, not `Twist`. If the bridge entry or your publisher uses the wrong type, nothing crosses the bridge — ROS publishes, Gz hears silence. Bridge `TwistStamped <-> gz.msgs.Twist`, `ROS_TO_GZ`.

10. **C** — The plugin uses its *own* `<wheel_radius>` for the inverse kinematics and odometry, so a mismatch with the real cylinder makes commanded ground speed and reported odometry disagree. The result is drift that looks like wheel slip but isn't — pure bookkeeping error. Keep the two numbers identical. (This is exactly the motivation for Week 6.)

11. **B** — `use_sim_time: true` makes nodes take time from the simulator's `/clock` (`rosgraph_msgs/Clock`, bridged from Gz). Without it, sensor stamps use wall-clock while the world advances on sim-clock, and every time-based operation (tf lookups, filters) breaks. This is the second-most-common bug after forgetting to bridge a topic.

12. **B** — Parse before physics. `check_urdf` catches structural errors (broken tree, duplicate names) cheaply. Then audit masses and run the four sanity checks. Spawning is the *last* step, not the first; a detonating robot is the most expensive debugger.

13. **A** — `I = (2/5)·m·r² = 0.4 · 0.05 · 0.025² = 0.4 · 0.05 · 0.000625 = 1.25e-5 kg·m²`. Genuinely tiny, and *correctly* tiny — a 50 g marble really is easy to spin. Small isn't wrong; *inconsistent with mass and size* is wrong.

</details>

---

If you scored under 9, re-read the lecture for the questions you missed — especially anything about the inertia tensor or the two-universe bridge model, because every later week leans on both. If you scored 12 or 13, you're ready for the [homework](./homework.md) and the [crunchbot mini-project](./mini-project/README.md).
