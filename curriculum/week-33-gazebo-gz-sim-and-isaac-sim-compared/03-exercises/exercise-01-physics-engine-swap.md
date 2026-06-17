# Exercise 1 — Swap the Physics Engine Under Gz Sim

**Goal:** Prove to yourself, with measurements, that **the physics engine is a choice and changing it changes behavior** — by running your *identical* week-3 robot in Gz Sim under two engines (DART and Bullet) and recording the step-time and contact differences. This is the cheapest possible version of the week's central experiment: hold the robot fixed, vary the physics, measure.

**Estimated time:** 45 minutes. Guided.

---

## Setup

You need your **week-3 robot** and a simple world in Gz Sim Harmonic (ROS2 Jazzy). Confirm it spawns and drives:

```bash
source /opt/ros/jazzy/setup.bash
gz sim -r crunch_world.sdf            # your world including the robot
# in another terminal, drive it briefly to confirm motion + contact with the floor
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
```

If you have no world file, the Gz Sim `shapes.sdf`/`diff_drive.sdf` demo worlds plus an `include` of your robot model work fine — the point is *your robot*, not a specific world.

---

## Step 1 — Identify the current engine

Gz Sim's default featured engine is **DART** unless you said otherwise. Confirm what you're running:

```bash
gz sim --versions                      # Gz version
# The engine is selected by the world's <physics type="..."> OR the CLI flag below.
```

Open your world's `<physics>` block (Lecture 1 §3.1). If it says `type="dart"` (or there's no explicit engine and you didn't pass a flag), you're on DART. Write that down as run A.

---

## Step 2 — Measure run A (DART)

Launch with DART and watch `gz stats` for ~30 seconds while the robot drives a short pattern:

```bash
gz sim -r crunch_world.sdf
# another terminal:
gz stats          # prints real-time factor and step-time live; let it settle, record
```

Record, for run A:

- **Real-time factor** (steady-state, robot driving).
- **Step-time** (ms per step) from `gz stats`.
- A qualitative **contact note**: does the robot sit flush on the floor, sink slightly, jitter, bounce when it bumps a wall?

You can also use the Exercise-2 metrics node here instead of `gz stats` — it computes RTF/step-time from `/clock` and works identically across engines, which is exactly why you built it.

---

## Step 3 — Switch to Bullet and measure run B

Two ways to switch the engine. Either edit the world:

```xml
<physics name="1ms" type="bullet">     <!-- was "dart" -->
  <max_step_size>0.001</max_step_size>
  <real_time_factor>1.0</real_time_factor>
</physics>
```

…or pass the engine on the CLI (no world edit):

```bash
gz sim -r crunch_world.sdf --physics-engine gz-physics-bullet-featherstone-plugin
```

Run the **same** drive pattern for the **same** ~30 s and record run B's RTF, step-time, and contact note.

---

## Step 4 — Compare

Put A and B side by side:

| Run | Engine | RTF | Step-time (ms) | Contact note |
|-----|--------|-----|----------------|--------------|
| A | DART | | | |
| B | Bullet | | | |

You should see **at least one column differ.** Step-time often differs (the engines have different solver costs); contact behavior frequently differs (different friction/restitution models). The robot, the world, the commands, and the measurement window were identical — **the only thing you changed was the physics engine, and the behavior moved.** That's the lesson: "the simulator" includes an engine choice, and that choice has consequences your policy can be brittle to.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You ran your *identical* week-3 robot under two Gz Sim engines (DART and Bullet) with the same world, commands, and window.
- [ ] You recorded RTF and step-time for both, from `gz stats` or the Exercise-2 node.
- [ ] You wrote a one-line contact note for each, and at least one metric or behavior differs between the runs.
- [ ] You can state, in one sentence, why "my grasp works under DART but fails under Bullet" is a sim-to-real warning, not necessarily a policy bug.

---

## Stretch

- Add **ODE** as a third run (`--physics-engine gz-physics-ode-plugin` if available) and note its characteristic softer contacts (Lecture 1 §2.1).
- Halve `<max_step_size>` to `0.0005` and re-measure: step-time roughly doubles, RTF drops, fidelity improves. You just moved along the throughput/fidelity curve *within one engine* — the same knob, at a finer grain, that distinguishes Gz from Isaac.
- Drive the robot into a wall under each engine and compare the bounce/penetration. Contact at impact is where engines disagree most visibly.

---

When the engine-as-a-parameter idea is concrete, move to [Exercise 2 — Measure a simulator from ROS2](./exercise-02-sim-metrics.py).
