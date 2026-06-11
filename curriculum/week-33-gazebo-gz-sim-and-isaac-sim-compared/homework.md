# Week 33 Homework

Six problems that force the multi-sim fluency into your fingers. The full set should take about **5 hours**. Work in your Week 33 Git repository (the same workspace as the exercises and the `crunchbot_sim_compare` mini-project) so every problem produces at least one commit.

The headline deliverable is **Problem 4 — the sim-selection comparison write-up**, the syllabus artifact ("one-page write-up"). Treat it as the design-review document a lead reads, not a journal entry.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`). Have your **week-3 differential-drive robot** spawnable in Gz Sim — Problems 1, 2, 4, and 6 run against it. Path B (no NVIDIA GPU) substitutes two Gz engines for Gz-vs-Isaac throughout, as documented in Exercise 3; say so in your writeups.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**.

---

## Problem 1 — Identify what's actually running

**Problem statement.** Bring up your week-3 robot in Gz Sim. Determine and document, in `notes/week-33/whats-running.md`: the Gz Sim version, the active physics engine, the render engine, and the list of bridged ROS2 topics with their types. Then explain, in two sentences, why a node subscribing to a bridged sensor topic must mind its QoS.

**Acceptance criteria.**

- `notes/week-33/whats-running.md` records Gz version, physics engine, render engine, and the bridged topic↔type list (from `ros2 topic list` + `ros2 topic info`).
- The QoS explanation correctly connects bridged sensor topics to the Week 5 silent-failure (a `RELIABLE` subscriber against a `BEST_EFFORT` bridge gets nothing).
- Committed.

**Hint.** `gz sim --versions`, the world's `<physics type=...>` block, and `ros2 topic list -t` for types. If you never set the engine, you're on DART.

**Estimated time.** 35 minutes.

---

## Problem 2 — The engine-swap measurement

**Problem statement.** Using Exercise 1's procedure and the Exercise-2 metrics node, run your robot driving the same short pattern under **two** Gz physics engines (DART and Bullet). Record RTF, mean step-time, `/scan` Hz, and a contact note for each in `notes/week-33/engine-swap.md`.

**Acceptance criteria.**

- A table with both engines and all four columns, measured with the Exercise-2 node (not eyeballed).
- At least one metric differs between engines, with a one-sentence explanation of why.
- The robot, world, drive pattern, and window were identical across the two runs (state this explicitly).
- Committed.

**Hint.** `gz sim -r world.sdf --physics-engine gz-physics-bullet-featherstone-plugin` to switch without editing the world. Keep the Exercise-2 node running across both and just restart the sim.

**Estimated time.** 45 minutes.

---

## Problem 3 — USD vs SDF vs URDF, in your own words

**Problem statement.** Write a one-page explainer at `notes/week-33/scene-formats.md` comparing the three scene/robot description formats you've now met: **URDF** (the robot description you author), **SDF** (Gz Sim's native world format), and **USD** (Isaac Sim's native format). For each: what it describes, which simulator consumes it natively, and one strength/limitation. Then state precisely what does and does **not** transfer when you cross-import a robot from Gz's world into Isaac's stage.

**Acceptance criteria.**

- `notes/week-33/scene-formats.md` covers all three formats with the described-by / consumed-by / strength columns.
- It correctly states that **kinematics (links/joints/meshes) transfer but sensor plugins do not** when cross-importing URDF/SDF → USD (sensor plugins are sim-specific and re-authored).
- It names which format Isaac manipulates via prims/stages.
- Committed.

**Hint.** Pull from Lecture 2 §1.1 (USD stages/prims) and Exercise 3's "KEY POINT" about the lossy cross-import. The sensor-plugin non-transfer is the load-bearing claim.

**Estimated time.** 40 minutes.

---

## Problem 4 — The sim-selection comparison write-up (headline deliverable)

**Problem statement.** This is the syllabus deliverable. Using the challenge's data (or run a fresh comparison: same robot, same patrol, two sims on Path A or two engines on Path B), write the one-page sim-selection document at `notes/week-33/sim-selection.md` against this template:

1. **Setup** — the fixed robot, the fixed behavior, the window, and the measurement tool (so the comparison is demonstrably fair).
2. **The table** — RTF, step-time, sensor fidelity, contact behavior, for both sims/engines.
3. **The trade-off** — where each sim sits on the throughput-vs-fidelity curve; what each gave up.
4. **The recommendation** — a simulator for **each** of two purposes: (a) debug the autonomy stack, (b) train a policy with domain randomization next week. Justify with a metric or capability.
5. **Honest limits** — on Path B, which Isaac-only capabilities you reasoned about rather than measured (RTX rendering, GPU-parallel envs) and why that's acceptable.

**Acceptance criteria.**

- `notes/week-33/sim-selection.md` exists, ~400–600 words, hitting all five headings.
- The table has all four metrics for both points, captured with a consistent tool.
- The recommendation is **per-purpose** (two purposes, two justified answers) — not a single universal winner.
- The fairness of the comparison is explicit (same robot/behavior/window/tool).
- Committed.

**Hint.** The single most common failure is recommending one sim for everything because it had a higher RTF. Re-read the challenge's "trap": throughput on one robot says nothing about parallel-env throughput or iteration speed. State the purpose, then the tool.

**Estimated time.** 1 hour.

---

## Problem 5 — The throughput-vs-fidelity argument

**Problem statement.** In `notes/week-33/throughput-vs-fidelity.md`, argue both halves of the trade-off with a concrete scenario each: (a) why using one expensive high-fidelity world for PPO training is the *wrong* tool (relate to Week 28's sample-hunger and Lecture 2's parallel-env numbers); (b) why using a thousand cheap low-fidelity worlds for a *final integration sign-off* is the wrong tool (relate to contact-model brittleness and the capstone). Conclude with the one-sentence rule.

**Acceptance criteria.**

- Both scenarios are argued with a specific reason (sample-hunger + throughput for (a); fidelity/sign-off risk for (b)).
- The conclusion states the "match the tool to the job" rule in one sentence.
- At least one quantitative reference (the parallel-env throughput shape from Lecture 2 §2.2, or a step-time you measured).
- Committed.

**Hint.** Lecture 2 §2.2 gives the illustrative throughput numbers; Lecture 1 §2 gives the contact-model-brittleness angle. This problem is your conceptual bridge into Week 34.

**Estimated time.** 40 minutes.

---

## Problem 6 — Boot-time and iteration cost

**Problem statement.** Measure something the four physics metrics hide: **iteration cost.** Time "launch command → first `/scan` on ROS2" for Gz Sim (and, Path A, Isaac Sim). Record both in `notes/week-33/boot-time.md` and argue how boot/iteration time should factor into the sim-selection decision alongside RTF and fidelity.

**Acceptance criteria.**

- `notes/week-33/boot-time.md` reports launch-to-first-scan for at least Gz Sim (Path A: also Isaac).
- A paragraph arguing why iteration speed matters for debugging (where you relaunch dozens of times a day) even when raw RTF favors the slower-booting sim.
- Committed.

**Hint.** A simple stopwatch or `time` around the launch plus `ros2 topic echo --once /scan` works. Isaac Sim's slow boot is a real reason Gz stays the debugging default even when Isaac steps faster — that's the point this problem makes concrete.

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Identify what's running | 35 min |
| 2 — Engine-swap measurement | 45 min |
| 3 — USD vs SDF vs URDF | 40 min |
| 4 — Sim-selection write-up (headline) | 1 h 0 min |
| 5 — Throughput-vs-fidelity argument | 40 min |
| 6 — Boot-time and iteration cost | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_sim_compare` [mini-project](./mini-project/README.md) is in the same workspace — Week 34 extends it into a domain-randomization harness. Then take the [quiz](./quiz.md) with your notes closed.
