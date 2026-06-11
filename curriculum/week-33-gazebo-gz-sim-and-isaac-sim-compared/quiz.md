# Week 33 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 34. Answer key is at the bottom — don't peek.

---

**Q1.** What does "Gazebo" refer to in 2026, and what is the status of Gazebo Classic?

- A) Gazebo Classic is the current version; Gz Sim is experimental.
- B) "Gazebo" means **Gz Sim** (Garden/Harmonic, formerly "Ignition"); Gazebo Classic is **end-of-life** and a migration target, not a starting point.
- C) They are the same software with two names; nothing changed.
- D) Gz Sim is a paid product; Classic is the free one.

---

**Q2.** Why does Gz Sim require a *bridge* (`ros_gz_bridge`) to work with ROS2?

- A) Because ROS2 cannot run on the same machine as a simulator.
- B) Because Gz Sim has its own pub/sub middleware (`gz-transport`) and does not speak ROS2 natively, so a bridge converts topics/types between them.
- C) Because the bridge encrypts the data.
- D) It doesn't — Gz Sim publishes ROS2 topics directly.

---

**Q3.** In Gz Sim, the physics engine is selected by `<physics type="...">` or `--physics-engine`. Which set are all selectable/available engines in the Gz ecosystem?

- A) PhysX, MuJoCo, RTX
- B) DART, Bullet, ODE (DART is the featured one)
- C) Only DART; the others require recompiling Gz from source
- D) TensorRT, ONNX, OpenVINO

---

**Q4.** Which engine is NVIDIA's, lives under Isaac Sim, and is the reason Isaac Lab can step thousands of environments at once?

- A) ODE
- B) DART
- C) PhysX (GPU-accelerated)
- D) Bullet

---

**Q5.** Why is MuJoCo the reinforcement-learning community's favorite?

- A) It is the only engine that runs on macOS.
- B) Its contact solver is fast, stable, and RL-friendly; it's now open-source — a good fit for sample-hungry learning.
- C) It is the default engine in Gz Sim.
- D) It has the most photorealistic renderer.

---

**Q6.** What is USD, and what role does it play in Isaac Sim?

- A) A physics engine.
- B) Universal Scene Description — Pixar's scene format; Isaac Sim's native world representation (stages, prims, references) that you manipulate via the Python API.
- C) A ROS2 message type.
- D) A GPU driver.

---

**Q7.** What is Isaac Lab, and what is its headline capability?

- A) A 2D plotting tool for Isaac Sim.
- B) The GPU-parallel RL/IL framework on top of Isaac Sim; it instantiates and steps **thousands of parallel environments** on the GPU, returning batched tensors.
- C) A replacement for ROS2.
- D) A photorealistic renderer with no physics.

---

**Q8.** A robot grasps reliably under DART but drops objects under Bullet, with no other change. What does this most likely reveal?

- A) A bug in your grasp code that only DART triggers.
- B) That the two engines approximate rigid-body contact differently, and your policy is **brittle to the contact model** — a sim-to-real warning, not necessarily a policy bug.
- C) That Bullet is broken and should never be used.
- D) That the robot's URDF is wrong.

---

**Q9.** You bridge `/scan` from Gz Sim, the topic exists, but your subscriber receives nothing. What is your first diagnostic move?

- A) Re-read the bridge YAML line by line.
- B) `ros2 topic info /scan -v` and diff the publisher/subscriber QoS — the bridge is just a publisher, and a `BEST_EFFORT`/`RELIABLE` mismatch is the Week 5 silent failure.
- C) Restart the whole computer.
- D) Switch to Isaac Sim.

---

**Q10.** What does a real-time factor (RTF) of 1.20 mean?

- A) The sim is running at 120% CPU.
- B) The sim advances sim-time 1.2× faster than wall-clock — faster than real time (possible when the world is cheap or the GPU is fast).
- C) The sim is 20% behind real time.
- D) The robot moves at 1.2 m/s.

---

**Q11.** For a *fair* comparison of two simulators, what must be true?

- A) Use a different robot in each to test generality.
- B) The **only** independent variable is the simulator (or engine); robot, behavior, window, and metrics are identical across runs.
- C) Run each for as long as you feel like.
- D) Use whichever metrics each sim reports natively, even if they differ.

---

**Q12.** Your teammate asks "should we use Gz Sim or Isaac Sim?" What is the correct senior answer?

- A) "Isaac — it has a higher RTF, so it's better for everything."
- B) "It depends on the purpose: Gz Sim to build/debug the autonomy stack (free, ROS-native, fast iteration); Isaac Lab to train policies / do domain randomization (GPU-parallel throughput). We use both and keep the ROS2 stack sim-agnostic."
- C) "Whichever one we already have installed."
- D) "Always Gz Sim — Isaac is never worth it."

---

**Q13.** Why does *next* week's domain randomization depend on this week's throughput lesson?

- A) It doesn't; they're unrelated.
- B) Randomizing over a thousand varied worlds is only tractable because a GPU-parallel simulator (Isaac Lab) can step many cheap worlds at once — throughput is what makes thousand-world randomization affordable.
- C) Because domain randomization requires Gazebo Classic.
- D) Because randomization needs photorealism, which only Gz Sim provides.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — "Gazebo" = Gz Sim (Garden/Harmonic); Classic is EOL. (Lecture 1 §1.1.)
2. **B** — Gz Sim uses `gz-transport`, not ROS2; the bridge converts. (Lecture 1 §1.2, §3.3.)
3. **B** — DART (featured), Bullet, ODE are the Gz-selectable engines. (Lecture 1 §2.)
4. **C** — PhysX, GPU-accelerated, under Isaac Sim; enables parallel envs. (Lecture 1 §2.4, Lecture 2 §1.3.)
5. **B** — Fast, stable, RL-friendly contact solver, now open-source. (Lecture 1 §2.5.)
6. **B** — Universal Scene Description; Isaac's native scene format (stages/prims/references). (Lecture 2 §1.1.)
7. **B** — The GPU-parallel RL/IL framework; thousands of parallel envs as batched tensors. (Lecture 2 §2.1.)
8. **B** — Engines approximate contact differently; brittleness to the contact model is a sim-to-real warning. (Lecture 1 §2, Exercise 1.)
9. **B** — `ros2 topic info -v` and a QoS diff first; the bridge is a publisher and QoS mismatch is the Week 5 silent failure. (Lecture 1 §3.3.)
10. **B** — RTF = sim-time/wall-time; 1.2 = 20% faster than real time. (Lecture 1 §3.4, Lecture 2 §3.2.)
11. **B** — Only the simulator varies; everything else fixed. (Lecture 2 §3.1.)
12. **B** — Per-purpose: Gz to build/debug, Isaac Lab to train at scale; keep the stack sim-agnostic. (Lecture 2 §3.4.)
13. **B** — GPU-parallel throughput is what makes thousand-world randomization tractable. (Lecture 2 §2.2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
