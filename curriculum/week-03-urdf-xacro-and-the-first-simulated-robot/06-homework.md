# Week 3 Homework

Five practice problems that revisit and stress the week's topics. The full set should take about **4.5 hours**. Work inside your `crunchbot_ws` ROS2 workspace (the same workspace the exercises and mini-project use) so every problem produces at least one Git commit you can point to later.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

These are not busywork. Problem 1 makes the inertia validator a real, tested tool you will reuse all phase. Problem 4 forces you to confront the explode-on-spawn failure on purpose, in a controlled way, so it never surprises you in anger. Problem 5 is the reflection that makes the rest stick.

> **The Week 3 standard.** Every problem that ends in a robot must spawn clean — print the `Spawn entity ... success` line and sit still on the ground plane when no command is sent. A robot that drifts, sinks, vibrates, or explodes is not "mostly working"; it is a description bug. Treat it the way Week 1 treated a build warning.

---

## Problem 1 — A tested inertia toolbox

**Problem statement.** Take the `inertia.py` helper from Lecture 1 §1.5 and the `sanity_check` validator from §1.6, and turn them into a real, tested Python module `crunchbot_description/crunchbot_description/inertia.py` with a `pytest` test file alongside it. The module must expose:

```python
def box_inertia(mass: float, x: float, y: float, z: float) -> Inertia: ...
def cylinder_inertia(mass: float, radius: float, length: float) -> Inertia: ...
def sphere_inertia(mass: float, radius: float) -> Inertia: ...
def sanity_check(mass, ixx, iyy, izz, char_len) -> list[str]: ...
```

Write at least **eight** tests:

1. The chassis box (`2.0, 0.4, 0.3, 0.1`) produces `Izz ≈ 0.04167` (assert within `1e-4`).
2. The wheel cylinder (`0.3, 0.05, 0.04`) produces `Izz ≈ 0.000375`.
3. The caster sphere (`0.05, 0.025`) produces `Ixx == Iyy == Izz ≈ 1.25e-5`.
4. Every primitive's tensor passes `sanity_check` with the right characteristic length (zero problems returned).
5. A hand-built tensor that **violates the triangle inequality** (e.g. `ixx=0.001, iyy=0.001, izz=0.010`) is rejected.
6. A negative mass is rejected.
7. A zero diagonal entry is rejected.
8. A tensor off by 1000× from `m·r²` is flagged by the order-of-magnitude check.

**Acceptance criteria.**

- The module lives in the `crunchbot_description` package and imports cleanly.
- `pytest` (or `colcon test`) runs the suite green: at least 8 tests, all passing.
- The three primitive functions return the exact values from Lecture 1 §1.5 (within `1e-4`).
- The validator correctly **rejects** the three bad-tensor cases.
- Committed with a sensible message.

**Hint.** You already have the source in the lecture; the work is wrapping it as a package module and writing the assertions. For the float comparisons use `pytest.approx`: `assert i.izz == pytest.approx(0.04167, abs=1e-4)`. For the rejection tests, assert the returned list is **non-empty** and contains the expected substring (`"triangle inequality"`).

**Estimated time.** 50 minutes.

---

## Problem 2 — A third caster, by hand and by macro

**Problem statement.** Your crunchbot has two casters (front and rear, or both rear, depending on your design). Add a **third** caster as a deliberate exercise in doing it two ways:

1. First, add it **by hand** — write the full `<link>` (visual sphere, collision sphere, inertial with a hand-typed tensor you computed with a calculator) and the `<joint type="fixed">` directly in a scratch URDF.
2. Then delete the hand-written version and add the same caster by **calling your existing `xacro:macro`** with the new mount position.

Write a 150-word note in `notes/week-03-caster-two-ways.md` comparing the two: how long each took, which one you'd trust in six months, and what specifically the macro guarantees that the hand version does not.

**Acceptance criteria.**

- Both versions expand with `xacro` and pass `check_urdf` (do them one at a time).
- The macro version produces an `<inertial>` numerically identical (within rounding) to your correct hand computation — prove it by diffing the expanded URDF blocks.
- The note exists, is ~150 words, and names at least one concrete failure the macro prevents (units, triangle inequality, copy-paste drift).
- Committed.

**Hint.** `xacro crunchbot.urdf.xacro > /tmp/expanded.urdf` then `grep -A2 caster /tmp/expanded.urdf` to compare the generated inertial blocks. The macro should call your `sphere_inertia`-equivalent xacro math so the tensor falls out of mass and radius automatically.

**Estimated time.** 45 minutes.

---

## Problem 3 — Verify every sensor topic, with QoS in mind

**Problem statement.** With crunchbot spawned and the bridge running, write a small `rclpy` node `homework/p3_topic_audit/topic_audit.py` that subscribes to `/scan` (`sensor_msgs/LaserScan`), `/imu` (`sensor_msgs/Imu`), and `/odom` (`nav_msgs/Odometry`), and prints, once per second for ten seconds:

- The measured **publish rate** of each topic (messages received in the last second).
- For `/scan`: the number of range readings and the min/max range observed.
- For `/imu`: the angular velocity about z (yaw rate) and the linear acceleration in z (should sit near `+9.81` at rest, since the IMU measures the reaction to gravity).
- For `/odom`: the current `x`, `y`, and yaw.

Run it while the robot sits still, then again while you drive it with `ros2 topic pub /cmd_vel`. Save both outputs to `notes/p3-topic-audit.md`.

**Acceptance criteria.**

- All three topics report a non-zero, sane rate (LiDAR near its configured update rate, IMU faster, odom near 50 Hz).
- At rest, `/imu` linear-z reads close to `+9.81 m/s²` (within ~0.3) and yaw rate near 0.
- While driving in a circle (`linear.x` and `angular.z` both non-zero), the `/imu` yaw rate is clearly non-zero and `/odom` x/y change.
- Both captured outputs are in the note, with one sentence each explaining what changed and why.
- Committed.

**Hint.** Count messages in a `dict[str, int]` from each callback, then a 1 Hz timer reads and resets the counters. For the at-rest gravity reading: a stationary accelerometer reads the *specific force* opposing gravity, so z is `~+9.81`, not `0` — that surprises people every time. Remember `use_sim_time: true` on this node, and that on Jazzy you publish `/cmd_vel` as `TwistStamped` (`ros2 topic pub /cmd_vel geometry_msgs/msg/TwistStamped "{twist: {linear: {x: 0.2}, angular: {z: 0.4}}}" -r 10`).

**Estimated time.** 1 hour.

---

## Problem 4 — Break it on purpose, then fix it

**Problem statement.** Make a throwaway copy of your crunchbot description. Then, **one at a time**, inject each of the four explode-on-spawn causes from Lecture 1 §1.7, spawn, observe, and record the symptom — then revert before injecting the next:

1. **Bad inertia** — multiply the chassis `Ixx/Iyy/Izz` by 1000.
2. **Bad mass** — set a wheel `<mass>` to `0.0`.
3. **Self-collision** — move a wheel's `<origin>` inward so its collision cylinder interpenetrates the chassis collision box at rest.
4. **Degenerate joint** — set a wheel joint's `<axis>` to `xyz="0 0 0"`.

For each, write down: the exact symptom you saw (trembles instantly? settles then jumps? wheel spins to infinity? sinks?), how fast it happened (first frame vs. after settling), and which diagnostic step from the §1.7 workflow caught it fastest.

**Acceptance criteria.**

- A table in `notes/p4-four-causes.md` with one row per cause: *injected change · observed symptom · time-to-failure · which check caught it*.
- Your descriptions match the lecture's differential (instant trembling for inertia/mass; settle-then-jump for collision/joint).
- After the experiment, your **real** crunchbot still spawns clean (prove it: paste the `Spawn entity ... success` line).
- Committed. (Commit the notes, not the broken URDFs.)

**Hint.** Do this in a scratch file (`/tmp/exploding.urdf.xacro`) so you never risk your real description. `check_urdf` will catch the degenerate-axis and zero-mass cases *before* you spawn — note when it does, because that's the cheap path. Spawn paused if you can, so you can inspect the static pose for the self-collision case.

**Estimated time.** 1 hour.

---

## Problem 5 — Mini design-review write-up

**Problem statement.** Write a 350–450 word document at `notes/week-03-design-review.md` that you could hand to a reviewer in place of walking them through your robot live. It must answer:

1. **The tree.** What is your root link, and what are the links and joints hanging off it? Paste the output of `ros2 run tf2_tools view_frames` description (or list the frames) and confirm it is a single tree with no orphans.
2. **The mass budget.** A table of every link, its mass, and its characteristic size, with a one-line justification that each mass is plausible (chassis 1–5 kg, wheel 0.1–0.5 kg, caster 20–80 g).
3. **The kinematic constants that must agree.** State your `wheel_separation` and `wheel_radius`, and confirm the DiffDrive plugin parameters match the URDF geometry exactly. Explain in one sentence what drifts if they don't.
4. **The bridge.** List every bridged topic, its ROS type, its Gz type, and its direction (`ROS_TO_GZ` / `GZ_TO_ROS` / bidirectional). Confirm `/clock` is bridged and every node uses `use_sim_time: true`.
5. **The fail-safe smell test.** In one paragraph: how do you *know* your robot spawned correctly? What is the single observation that, if false, means you have a description bug rather than a control bug?

**Acceptance criteria.**

- File exists, 350–450 words, each numbered section addressed.
- The mass budget table is complete (one row per link) and every mass passes the plausibility check.
- The kinematic-constants section explicitly states the two numbers and confirms they match.
- The bridge section lists every topic with type and direction.
- Committed.

**Hint.** This is the document Week 8's architecture review will ask for, scaled down. Writing it now — while the robot is small and you remember every choice — is far easier than reconstructing it later. Future-you, six weeks from now, debugging an odometry drift, will be grateful you wrote down the wheel constants.

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 | 50 min |
| 2 | 45 min |
| 3 | 1 h 0 min |
| 4 | 1 h 0 min |
| 5 | 45 min |
| **Total** | **~4 h 20 min** |

---

## Rubric

If you are submitting this for review (or grading yourself honestly), score against this:

| Criterion | Weight | What "great" looks like |
|----------|-------:|-------------------------|
| Inertia toolbox correctness | 25% | All 8+ tests pass; the validator rejects every bad-tensor case; values match Lecture 1 §1.5 exactly |
| Robot still spawns clean | 20% | After all the breaking in P4, the real crunchbot spawns with `success` and sits still |
| Topic audit honesty | 20% | All three topics report sane rates; the at-rest `+9.81` gravity reading is present and explained |
| Failure-mode literacy | 20% | The P4 table matches the lecture's differential; you can say which check caught each cause fastest |
| Design-review clarity | 15% | A reviewer could understand your robot from the write-up alone, without seeing it run |

---

When you've finished all five, push your `crunchbot_ws` and continue into the [crunchbot mini-project](./07-mini-project/00-overview.md) — the homework's inertia toolbox and design-review write-up both feed directly into it.
