# C24 · Crunch Robotics — Charter

This charter explains why **Crunch Robotics** exists as a distinct mastery-tier track in Crunch Labs, why it is forty-eight weeks long, why the topics fall in the order they do, and which stances are non-negotiable. It sits beneath the umbrella [Crunch Labs Charter](../CRUNCH-LABS-CHARTER.md) and inherits every quality bar set there.

---

## Why robotics is its own track — not a sequel to C7

C7 (Crunch Wire — Embedded Systems) teaches a single device thinking. One microcontroller, one bus, one firmware image, one network. The engineering virtues are determinism, power, footprint, and OTA discipline. A C7 graduate can ship a connected sensor, a battery-powered actuator, or an edge inference box.

Robotics is a different problem class. A robot is a **federation of actuators, sensors, and compute** that must agree on a shared state of the world, plan an action, execute it under uncertainty, and not hurt anybody. The hard parts are perception under noise, planning under partial information, control under latency, and learning under a sim-to-real gap. None of that is in scope for C7, and none of it should be retrofitted into C7.

Putting robotics into the embedded track would do two disservices: it would dilute C7 (whose audience is firmware engineers) and it would short-change robotics (which deserves twelve months of intentional work). Crunch Robotics gets its own number, its own sub-brand (`Robotics`, accent `#DC2626` cinnabar), its own LICENSE, and its own capstone.

C7 graduates *are* a primary audience for C24 — but the path is **C7 → C24**, not **C7 contains C24**.

---

## Why forty-eight weeks

Robotics is genuinely a year of work. The discipline is wide:

- A semester of math and ROS2 plumbing before a single learned policy.
- A semester of perception — classical CV, learned models, sensor fusion, 3D — before any planner is asked to consume it.
- A semester of planning, control, and manipulation, each of which is a standalone field.
- A semester of sim-to-real, multi-robot, AI-powered robotics, and a real capstone.

We have seen the alternative: short robotics courses that teach `ros2 topic pub`, train a YOLO model, point at Nav2, and graduate the learner. Those courses produce people who cannot debug a TF tree, who cannot write an EKF, who cannot tune a controller, and who cannot construct a safety case. They will fail their first robotics-startup interview and they will not enjoy the job that comes after.

Forty-eight weeks is the minimum honest length for *mastery-tier* robotics. Anything shorter is either a survey (acceptable, but call it that) or a specialization on top of an existing robotics engineer (also acceptable, but a different audience). C24 is for the engineer who wants to **ship robots in production**.

---

## Why this topic order

Most introductory robotics curricula teach **control first** because the math is clean (a PID loop has a closed-form, a state-space controller has a textbook), then run out of weeks before they reach perception. Their graduates can stabilize an inverted pendulum but cannot tell you what the robot is looking at.

C24 inverts this:

1. **Math + ROS2 first (weeks 1–8).** You cannot reason about a robot in any meaningful way without rigid-body transforms, twists, Jacobians, and the SE(3) group — and you cannot collaborate with anybody in the field without ROS2. So we teach the math and the middleware, drive a robot in simulation, and run a first SLAM end-to-end. After eight weeks the learner has a vocabulary.
2. **Perception second (weeks 9–16).** You cannot plan if you do not know where you are or what is around you. Sensor fusion (IMU + wheel odometry + LiDAR + depth), classical CV, learned CV, point clouds, and on-Jetson inference are all in this phase.
3. **Planning and control third (weeks 17–24).** Now the planner has clean state to consume. Nav2, A*, RRT*, behavior trees, then PID → LQR → MPC. Manipulator kinematics is introduced here so the next phase has a chassis to stand on.
4. **Manipulation and learning fourth (weeks 25–32).** MoveIt2, grasping, imitation learning, RL, Diffusion Policy, ACT, and the first language-conditioned task.
5. **Sim2real and multi-robot fifth (weeks 33–40).** Isaac Sim, domain randomization, fleet coordination, vision-language policies, and an honest accounting of where the sim-to-real gap hurts.
6. **Capstone sixth (weeks 41–48).** Eight weeks to integrate everything into one autonomous mobile manipulator, with two chaos drills, a safety case, and a fleet-operations dashboard.

The result is a learner who, by the time they touch a controller, already knows what state the controller is regulating against — because they built the perception stack that produced that state.

---

## Open-source-first, vendor-aware

Crunch Robotics is built on **ROS2** (Humble, Iron, and Jazzy depending on lab), **Gazebo**, **MoveIt2**, **Nav2**, **OpenCV**, **PyTorch**, **Open3D**, **PCL**, **Cartographer**, **ORB-SLAM3**, **GTSAM**, **OMPL**, **Foxglove Studio**, **PlotJuggler**, and **micro-ROS**. Every one of these is free, open, and runnable on a laptop.

NVIDIA **Isaac Sim** and **Isaac Lab** are taught — they are the strongest GPU-accelerated simulation environment on the market and the only sane way to train a Diffusion Policy or PPO controller at scale. They are also proprietary. We name that fact in lecture, we teach the open-source alternative (Gz Sim, Gymnasium) alongside, and we *never* require a learner to depend on Isaac Sim to graduate. The alternate path (laptop + Gz Sim + simulated mobile manipulator) clears the capstone bar.

This is the same stance the umbrella Crunch Labs Charter sets: **open-source first, vendor-aware, never vendor-locked**.

---

## Hardware affordability — the alternate path is real

Robotics is the most hardware-expensive track in Crunch Labs. A full physical build (TurtleBot 4 Lite or DIY differential drive + Jetson Orin Nano + 6-DOF arm) runs roughly USD 1,500 to USD 3,500. We refuse to make that the only path. Every weekly lab has a **sim-only** variant. The capstone is **gradable in simulation** with no penalty — the evaluation rubric scores autonomy stack quality, safety case construction, and chaos-drill recovery, not whether a real robot was bought.

A learner in a country where importing a Jetson is impossible can complete C24 on a laptop with a discrete GPU and Isaac Sim's free tier. That is a deliberate design choice, not a workaround.

---

## Relationship to neighboring tracks

- **C7 (Wire — Embedded)** is a strict prerequisite for the hardware-aware parts of C24 (motor controllers, micro-ROS, CAN, real-time loops). A learner without C7 may proceed if they have equivalent industry experience, but they should not skip the C7 reading list.
- **C5 (AI / Data Science)** provides the classical ML and deep learning foundation. C24 assumes the learner can train a CNN, fine-tune a transformer, and reason about overfitting. We do not re-teach those.
- **C23 (Crunch Agents)** is **strongly recommended** before the AI-powered-robotics phase (weeks 33–40). The language-conditioned manipulation labs draw on grounded planners, structured tool use, and small-model deployment — all of which C23 covers properly. A learner without C23 will succeed but will spend more time on the AI/agent side of the policy layer.
- **C22 (Crunch Mesh)** is useful but not required for the fleet-operations and telemetry weeks. We teach the minimum distributed-systems vocabulary inline.

A learner on **Pathway D (Robotics Engineer)** in the umbrella charter therefore goes **C1 → C7 → C24**, optionally with **C5** and **C23** as side trips before week 33.

---

## The safety stance

A robot can hurt a human. A robot in a warehouse can hurt three humans, an inventory database, and a delivery schedule simultaneously. We treat **functional safety** as an engineering discipline, not an afterthought sticker.

- **Week 41** opens the capstone phase with a full safety-case writeup, framed against ISO 13482 (personal-care robots) and ISO 10218 (industrial manipulators). The writeup is a graded artifact.
- **Every lab from week 17 onward** must declare a fail-safe behavior. "What does the robot do when this code crashes?" is a question we ask in every architecture review.
- **Emergency-stop chains** are wired into every physical-robot lab and simulated in every sim-only lab. Software E-stop is taught; hardware E-stop is taught; the difference between them is taught.
- **Chaos drills** in the capstone phase intentionally break a sensor mid-task and intentionally deadlock the planner at a doorway. Recovery is graded.

The graduating engineer should be able to walk into a safety review at a robotics startup and not embarrass themselves. That bar is non-negotiable.

---

## Production-engineering depth

Every lab in this track must be specific enough that a hiring manager could read it and know what the learner did. We do not assign "explore SLAM." We assign:

> Implement KISS-ICP on a real LiDAR scan from the Newer College Dataset; benchmark translational drift over 100 m; compare against `cartographer_ros` on the same trace; produce a one-page failure-mode comparison.

The capstone is **one** integrated robot — an autonomous mobile manipulator with language-conditioned pick-and-place — not three loosely-related deliverables. Depth over breadth.

---

## Status

This charter is live as of **2026-05-13**. It is owned by the Code Crunch Club curriculum council and the C24 maintainer team. Amendments to topic ordering, hardware policy, or the open-source-first stance require a curriculum-council vote.

Licensed GPL-3.0 like the rest of the academy.

— *Code Crunch Club curriculum council, on behalf of the Crunch Robotics maintainers.*
