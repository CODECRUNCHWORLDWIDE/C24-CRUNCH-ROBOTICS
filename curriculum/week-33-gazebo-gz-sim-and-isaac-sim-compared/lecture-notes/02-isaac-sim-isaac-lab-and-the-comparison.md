# Lecture 2 — Isaac Sim, Isaac Lab, USD, and the Comparison Framework

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain Isaac Sim's architecture (USD + RTX + PhysX) and Isaac Lab's GPU-parallel role, bridge Isaac to ROS2, and run a *fair* Gz-vs-Isaac comparison that produces defensible numbers.

Lecture 1 opened up Gz Sim — the simulator you build and debug in. This lecture opens up the other one, the simulator you *train* in, and then gives you the framework to compare the two without bias. Three parts: (1) Isaac Sim's architecture, (2) Isaac Lab and the GPU-parallel story, (3) the comparison framework — bridges, fair measurement, and the selection table.

If you remember one sentence from this lecture, remember this one:

> **Isaac Sim is not a "better Gazebo" — it is a tool built for a different job (GPU-parallel training and photorealistic perception), and the senior skill is choosing per purpose and keeping your ROS2 stack sim-agnostic so the choice stays cheap.**

---

## Part 1 — Isaac Sim: USD, RTX, and PhysX

NVIDIA Isaac Sim is a robotics simulator built on the **Omniverse** platform. Three pillars distinguish it from Gz Sim, and you need each. Where Gz Sim's design goals were "free, open, ROS-native, runs anywhere," Isaac Sim's were "photorealistic, GPU-accelerated, scalable to massive parallel training." Those different goals are *why* the two sims feel so different to use — and why neither is a drop-in replacement for the other. Keep that framing as you read: you are not learning a "better Gazebo," you are learning a tool built for a different job.

The three pillars, in one line each, before we take them in turn:

- **USD** is *how the scene is described* (the world format).
- **RTX** is *how the scene is rendered* (photorealistic, for perception).
- **PhysX (GPU)** is *how the scene is simulated* (parallel, for training at scale).

Gz Sim has an analogue of each (SDF, OGRE2, DART/Bullet), but Isaac's three are built for fidelity and GPU-parallel scale, which is the whole reason it exists as a separate tool.

### 1.1 USD — Universal Scene Description

Where Gz Sim's native format is SDF, Isaac Sim's is **USD (Universal Scene Description)** — Pixar's open scene format, designed for film and adopted across 3D tooling. Three concepts:

- A **stage** is the scene — the whole world, like an SDF `<world>`.
- A **prim** ("primitive") is a node in the stage's scene graph — a mesh, a light, a camera, a robot, a joint. Everything is a prim, addressed by a path like `/World/crunchbot/base_link`.
- **Attributes** hang off prims — a prim's pose, color, mass, and any custom data are attributes you read and write.
- **Layers and references** let scenes compose and override non-destructively — you can reference a robot USD into many worlds and override just its pose, which is part of why USD scales to large, varied scenes.
- **Composition arcs** (references, payloads, variants) are USD's superpower: you can swap a whole sub-scene (a "variant") without editing the base, which is how large studios — and large robot fleets — manage scene variation at scale.

The practical consequence for you: in Isaac Sim you manipulate the world by **getting and setting prims on the stage**, usually through the Python API. Setting a robot's joint targets, reading a sensor, adding a randomized texture (next week) — all are operations on prims. USD is more powerful than SDF and also less familiar; Exercise 3 is your first contact.

A concrete feel for "everything is a prim addressed by a path": after you import the week-3 robot, the stage looks like a filesystem of prims:

```
/World
/World/ground_plane
/World/crunchbot
/World/crunchbot/base_link
/World/crunchbot/base_link/visual
/World/crunchbot/left_wheel_joint
/World/crunchbot/lidar          <- a sensor prim
/World/light_dome
```

You operate on them by path. Getting and setting a prim is the basic verb of Isaac scripting:

```python
from pxr import UsdGeom
import omni.usd

stage = omni.usd.get_context().get_stage()
prim = stage.GetPrimAtPath("/World/crunchbot/base_link")   # fetch a prim
xform = UsdGeom.Xformable(prim)                              # treat it as transformable
# set/read attributes (pose, material, etc.) via the prim's USD attributes
```

The mental shift from SDF is this: in Gz Sim you mostly *declare* the world in XML and let plugins run it; in Isaac Sim you frequently *script* the world imperatively, fetching and mutating prims at runtime. That is more code but also more power — runtime randomization (next week) is just "fetch the material prim and set a new texture," done per environment, per reset.

### 1.1.1 The `SimulationApp` lifecycle (the gotcha that wastes everyone's first hour)

Isaac Sim's Python has one rule that trips up every newcomer: **you must create the `SimulationApp` *before* importing any `omni.*` or `isaacsim.*` module.** Those modules don't exist until the app boots them. So a standalone Isaac script always opens like this:

```python
from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})   # MUST be first

# Only NOW can you import the rest:
from isaacsim.core.api import World
import omni.usd
# ... build the scene, step, then ...
simulation_app.close()
```

Import an `omni.*` module before the `SimulationApp` line and you get an immediate, confusing `ImportError`. This is why Exercise 3's Path A runs *inside* Isaac's bundled interpreter (`./python.sh script.py`) — that interpreter has the boot machinery wired up. It is the single most common "why won't my Isaac script even start" issue, and now you'll recognize it.

### 1.2 The RTX renderer — photorealism that matters for perception

Isaac Sim renders through **NVIDIA RTX** — real, ray-traced rendering with physically based materials, accurate lighting, reflections, and shadows. This is a genuine step beyond Gz Sim's OGRE2 rasterizer, and it matters for exactly one reason that's relevant to this course: **learned perception trained on rendered images transfers better when the rendering is closer to real cameras.** If you are training a vision policy (or doing visual domain randomization next week), photorealism reduces the visual sim-to-real gap. If you are debugging a Nav2 costmap, you do not care and Gz Sim's renderer is fine. Photorealism is a tool for the perception/learning job, not a universal good.

### 1.3 PhysX on the GPU

Isaac Sim's physics is **PhysX**, and its superpower (Lecture 1 §2.4) is **GPU acceleration**. PhysX can simulate many rigid bodies — and crucially, many *independent copies of a scene* — in parallel on the GPU. A single robot stepping on the GPU is not the point (Gz Sim on a CPU is competitive for one robot). The point is **thousands of robots in thousands of worlds, stepped together**, which is what Part 2 is about and what makes Isaac the training simulator.

### 1.4 The cost of all this

Honesty, senior-engineer style: Isaac Sim is **heavy.** It needs an NVIDIA RTX GPU, a large install, and meaningful VRAM; it boots slowly; and the USD/Omniverse learning curve is real. For a quick "does my behavior tree transition correctly" check, launching Isaac Sim is using a freight train to cross the street. That weight is *worth it* when you need GPU-parallel training or photorealistic perception data, and *not worth it* otherwise. This asymmetry is the heart of the selection table in Part 3. (And it is why **Path B** learners without an NVIDIA GPU substitute the "two Gz Sim engines" experiment and treat the Isaac material as read-and-reason — you lose the hands-on, not the concept.)

### 1.5 USD vs SDF, head to head

Since you now know both scene formats, a direct comparison crystallizes why each sim chose what it did:

| Aspect | SDF (Gz Sim) | USD (Isaac Sim) |
|---|---|---|
| Origin | Robotics-specific (OSRF) | Film/3D (Pixar), general-purpose |
| Format | XML | Binary/text "crate" + Python-scriptable |
| Composition | `<include>` a model | Layers + references, non-destructive override |
| Editing model | Declare in XML, plugins run it | Often scripted imperatively at runtime |
| Tooling ecosystem | ROS/robotics tools | Huge 3D-content ecosystem (DCC tools) |
| Robotics maturity | Native, batteries-included | Powerful, but you assemble more yourself |

The trade is real: **SDF is simpler and robotics-native; USD is more powerful and composition-friendly but has a steeper ramp.** SDF "just describes a robot in a world"; USD can describe a film set, and a robot is one more prim in it. For your purposes the takeaway is the cross-import hazard you met in Exercise 3: kinematics (links, joints, meshes) survive the URDF/SDF→USD trip, but the *plugins and sensor wiring do not* — because SDF's sensor plugins and USD's sensor prims are different mechanisms. You re-author sensors per sim. Knowing this prevents the classic "I imported my robot into Isaac and the LiDAR stopped working" confusion: the LiDAR didn't break, it was never imported — it's a plugin, and plugins don't cross the format boundary.

### 1.6 Why "Omniverse" keeps showing up

You'll see "Omniverse" all over the Isaac docs, so place it: **Omniverse is NVIDIA's broader platform for USD-based 3D collaboration and simulation**, and Isaac Sim is the *robotics application* built on it. The RTX renderer, the USD runtime, the physics, and the extension system all come from Omniverse; Isaac Sim adds the robot-specific pieces (sensors, the ROS2 bridge, robot importers, Isaac Lab). You don't need to master Omniverse-the-platform — you need to know that when a doc says "Omniverse extension" or "Omniverse Kit," it means the underlying app framework Isaac Sim is one instance of. Mentally: Omniverse is the engine, Isaac Sim is the robotics car built on it.

---

## Part 2 — Isaac Lab and the GPU-parallel story

### 2.1 What Isaac Lab is

**Isaac Lab** is the open-source **robot-learning framework built on top of Isaac Sim** (the successor to the older Isaac Gym / OmniIsaacGymEnvs line). It provides: a clean environment API (Gymnasium-style), a library of robot tasks, sensor and randomization utilities, and — the headline — **tensorized parallel environments**. You define one environment; Isaac Lab instantiates `N` copies on the GPU and steps all `N` in lockstep, returning observations/rewards as batched tensors. Your RL algorithm (PPO, SAC — Week 28) consumes the batch directly.

### 2.2 Why parallelism is the whole game for RL

Recall the Week 28 axiom: **RL works on robots when the simulator is fast.** On-policy RL like PPO is *sample-hungry* — it needs millions of environment steps. If each step is a real-time-ish physics tick of one world, a useful policy takes days. Isaac Lab collapses that by stepping thousands of worlds at once on the GPU:

```
single-world CPU sim:   ~1,000 steps/s  ->  1M steps ≈ 17 minutes (if perfectly busy)
4,096-env GPU (Isaac):  ~1,000,000+ steps/s (total) -> 1M steps ≈ ~1 second of stepping
```

The numbers are illustrative, not a benchmark, but the *shape* is the point: GPU parallelism turns "millions of samples" from a days-long problem into a minutes-long one. That is why Week 28's PPO lab used parallel environments to hit 90% success in under 30 minutes, and why **next week's domain randomization** — which deliberately needs *many varied worlds* — is tractable. Domain randomization over a thousand randomized worlds is not extra cost on top of training; in a parallel simulator it *is* the training. That synergy is the reason this week precedes next week.

### 2.2.1 What a tensorized environment actually returns

The mental model that makes Isaac Lab click: a normal Gymnasium env returns *one* observation per step; an Isaac Lab env returns a **batch of `N`** — one row per parallel environment — as GPU tensors. Conceptually:

```python
# A normal single env (Gymnasium):
obs, reward, done, info = env.step(action)
#   obs:    shape (obs_dim,)        action: shape (act_dim,)

# An Isaac Lab vectorized env:
obs, reward, done, info = env.step(actions)
#   obs:    shape (N, obs_dim)      actions: shape (N, act_dim)   N = e.g. 4096
#   reward: shape (N,)              done:    shape (N,)
#   ...all GPU tensors, stepped in lockstep, never leaving the GPU
```

Two consequences follow. First, **the data never round-trips to the CPU** during training — observations, the policy forward pass, and the action all live on the GPU, which is *why* it is fast (CPU↔GPU transfer is the usual bottleneck). Second, **each of the `N` environments can be randomized differently** on reset — env 0 gets one friction, env 1 another — which is the exact mechanism next week uses to train across a distribution of worlds *for free* as part of the same batched step. The parallelism and the randomizability are the same feature viewed two ways.

### 2.2.2 The honest caveat: it's not free

Isaac Lab's throughput is real but it comes with strings, and a senior engineer names them: your *environment* must be written in the tensorized, GPU-friendly way (you can't drop arbitrary Python physics in the loop without killing the parallelism); resets, observations, and rewards all have to be batched tensor operations; and debugging a vectorized env is harder than debugging one world (a bug in env 2,337 of 4,096 is not fun to find). The payoff justifies the constraints when you genuinely need millions of samples — but it is *why* you still reach for Gz Sim's one-world simplicity when you're developing the task logic, and only move to Isaac Lab once the task is defined and you need to *train* it at scale.

### 2.2.3 A back-of-envelope: when is the GPU worth it?

A useful sanity check before you reach for Isaac Lab: estimate your *sample budget*. On-policy PPO for a moderate manipulation/locomotion task often needs on the order of `10^7` to `10^8` environment steps to converge. Do the arithmetic:

- At ~1,000 steps/s (one CPU world), `10^7` steps is ~3 hours and `10^8` is ~28 hours — painful but survivable for one experiment, brutal for a hyperparameter sweep.
- At ~10^6 steps/s (a few thousand GPU envs), `10^7` steps is ~10 seconds of stepping and `10^8` is ~2 minutes — you can run a *sweep* in the time the CPU runs one experiment.

So the rule of thumb: **if your task needs ≳ 10^7 samples and you'll run more than one experiment, the GPU pays for its setup cost many times over.** If your task is a one-off that converges in 10^5–10^6 samples, or you're still defining the task, the CPU world (Gz Sim + Gymnasium) is simpler and fast enough. Estimating the sample budget *before* choosing the sim is a senior move — it converts "Isaac feels faster" into "Isaac saves me 26 hours per sweep," which is the kind of number that wins the planning argument.

### 2.3 The bridge to ROS2

Like Gz Sim, Isaac Sim does **not** speak ROS2 natively — it has its own internals, so you bridge. The **`isaacsim.ros2.bridge`** extension publishes Isaac sensors and TF onto ROS2 topics, wired through **OmniGraph action graphs** (a visual/programmatic dataflow): you add an "ROS2 Publish LaserScan" node, point it at the LiDAR prim, point it at a topic, and it publishes `sensor_msgs/LaserScan`. The same QoS reality from Week 5 and Lecture 1 §3.3 applies — a bridged sensor topic has a QoS, and a mismatch with your subscriber is the same silent failure. Whether you bridge from Gz or from Isaac, your autonomy nodes don't change: they subscribe to `/scan` and `/cmd_vel` and never know which simulator is upstream. **That sim-agnosticism is exactly what makes a fair comparison possible** — you hold the entire ROS2 stack fixed and swap only what's behind the bridge.

---

## Part 3 — The comparison framework

This is the deliverable skill of the week: comparing two simulators *fairly* and reporting it like an engineer, not a fan.

### 3.1 The rule: hold everything fixed but the simulator

A comparison is only valid if the **only** independent variable is the simulator (or the physics engine). Same robot description (your week-3 base), same behavior (one patrol / waypoint routine), same goals, same measurement window, same metrics. If you run a different robot or a different behavior in each sim, you have produced two anecdotes that cannot be compared. The README's "same robot, same behavior" promise is this rule. Practically, the sim-agnostic ROS2 stack from Part 2.3 makes it achievable: your behavior tree, your bridge contract, and your measurement node are identical; only the simulator behind the bridge changes.

### 3.2 The four metrics that matter

| Metric | What it measures | How to capture |
|---|---|---|
| **Real-time factor (RTF)** | sim-time / wall-time — how fast the sim runs | `gz stats` (Gz) / Isaac's perf overlay; or compute from `/clock` (Exercise 2) |
| **Step-time** | wall-clock per physics step — the throughput primitive | same sources; lower is faster |
| **Sensor fidelity** | does `/scan`, `/imu` publish at the right rate with sensible noise? | `ros2 topic hz`, compare scan statistics across sims |
| **Contact behavior** | how do collisions/grasps resolve — sink, bounce, stick? | observe + count contacts; the engine-dependent one |

RTF and step-time are the **throughput** axis; sensor fidelity and contact behavior are the **fidelity** axis. The whole week's argument is that you trade between these. Exercise 2 computes RTF and step-time from `/clock` precisely so you can measure them identically across sims that report performance differently.

### 3.2.1 Why measure from `/clock` instead of each sim's native readout

Both simulators *do* report their own performance — `gz stats` for Gz, a perf overlay for Isaac. So why does Exercise 2 compute RTF and step-time from the ROS2 `/clock` topic instead? Because **a fair comparison needs the same measuring instrument on both subjects.** `gz stats` and Isaac's overlay define and round their numbers slightly differently, run at different update rates, and aren't both available headless. If you read RTF from `gz stats` for one sim and from Isaac's overlay for the other, you have introduced the measurement tool as a second variable — and now you can't tell whether a difference is the *sim* or the *instrument*. Computing both metrics from `/clock` (which both sims publish when `use_sim_time` is on) means the *same code* measures *both* sims. That is the methodological point behind the Exercise-2 node, and it is exactly the kind of rigor a reviewer looks for: "how did you measure that, and was it the same way for both?"

### 3.2.2 Bridging Isaac to ROS2, concretely

So you can picture the Isaac side of the bridge (the Gz side you saw in Lecture 1 §3.3): in Isaac Sim you build an **OmniGraph action graph** — a dataflow of nodes — that reads a sensor prim and publishes a ROS2 message. Conceptually the graph for a LiDAR is:

```
[On Playback Tick] -> [Isaac Read LiDAR (prim=/World/crunchbot/lidar)]
                           -> [ROS2 Publish LaserScan (topic=/scan, frame=laser_link)]
[Read Sim Time] ----------> [ROS2 Publish Clock (topic=/clock)]
[Read TF prims] ----------> [ROS2 Publish Transform Tree (topic=/tf)]
```

You assemble this once (in the GUI or via the Python OmniGraph API). After it runs, `/scan`, `/clock`, and `/tf` appear on the ROS2 graph — *identical in name and type* to what the Gz bridge produced. That identity is the whole game: your patrol behavior tree, your Nav2 stack, and your Exercise-2 measurement node subscribe to the same topics and **cannot tell which simulator is upstream.** Swapping Gz for Isaac becomes "relaunch with the other sim + its bridge," with zero changes to the autonomy stack. Hold that picture — it is what makes Section 3.1's "change only the simulator" physically achievable rather than aspirational.

### 3.3 The throughput-vs-fidelity trade, made concrete

- **Gz Sim** typically gives you RTF ≈ 1 for one robot on a CPU, ROS-native introspection, fast iteration, and "good enough" sensors. It is *not* built to step thousands of worlds. Its job is **integration and debugging.**
- **Isaac Sim** gives you photorealistic sensors and — via Isaac Lab — *massive* parallel throughput on the GPU, at the cost of weight, GPU requirement, and a steeper learning curve. Its job is **training at scale and high-fidelity perception data.**

Neither dominates. The classic mistake is using one expensive high-fidelity world for RL (slow, sample-starved) or using a thousand cheap low-fidelity worlds for a final integration sign-off (fast, but you signed off on physics that don't match reality). **Match the tool to the job.**

It helps to draw the trade as a curve. Picture the x-axis as throughput (worlds-per-second you can step) and the y-axis as fidelity (how close one world is to reality). Every simulator/config is a point:

```
fidelity
   ^
   |   Isaac Sim (1 world, RTX, high fidelity)  *
   |
   |        Gz Sim (1 world, DART)        *
   |
   |                                            * Isaac Lab (4096 envs, lower per-world fidelity)
   |   Gz Sim (1 world, big step, low fidelity) *
   +----------------------------------------------> throughput
```

You cannot have the top-right corner (perfectly realistic *and* massively parallel) — that's the fundamental trade. **You choose the corner that matches the job:** top-left (high fidelity, low throughput) for a final integration sign-off; bottom-right (lower fidelity, huge throughput) for RL training; and you move between them as the project phase changes. Drawing this curve and marking where each of your measured runs falls is, quite literally, the homework's "place each sim on the throughput-vs-fidelity curve" — and it is the clearest one-picture summary of the entire week.

### 3.4 The selection table — the artifact you'll defend

The deliverable of this week, and the homework headline, is a table like this — *filled with your own numbers* where you measured them:

| Axis | Gz Sim (Garden/Harmonic) | Isaac Sim / Isaac Lab |
|---|---|---|
| **Cost / hardware** | Free, CPU-fine | Free software, **NVIDIA GPU required** |
| **ROS2 integration** | Native via `ros_gz` (first-class) | Via `isaacsim.ros2.bridge` (good, heavier) |
| **Physics engines** | DART / Bullet / ODE (selectable) | PhysX (GPU-capable) |
| **Rendering** | OGRE2 (fast, adequate) | RTX ray-traced (photorealistic) |
| **Parallel envs** | No (one world) | **Yes — thousands on GPU** (Isaac Lab) |
| **Throughput (1 robot)** | RTF ≈ 1 on CPU | RTF ≥ 1, GPU |
| **Throughput (N envs for RL)** | Poor | **Excellent** |
| **Iteration / boot speed** | Fast | Slow (heavy) |
| **Best for** | Build/debug the autonomy stack | Train policies, photoreal perception, DR |
| **This course** | Phases 1–4 + integration | Phase 4 RL + this/next week's training |

When a teammate asks "which sim should we use?", the senior answer is never one word. It is: **"For what? If you're debugging the Nav2 stack, Gz Sim — it's free, ROS-native, and fast to iterate. If you're training a PPO policy or doing domain randomization over a thousand worlds, Isaac Lab — it's the only one that gives you the GPU-parallel throughput. We use both, and we keep our ROS2 stack sim-agnostic so switching is cheap."** That sentence — and the table that backs it — is what you produce this week.

---

## Part 4 — Reading a comparison table like an engineer

Producing the numbers is half the job; *interpreting* them without bias is the other half. Suppose your Exercise-2 runs yield this (Path A example):

```
sim / engine        RTF     step(ms)   /scan Hz   scan var   contact note
gz_dart             0.98    1.6        9.8        0.012      sits flush, stable
isaac_physx         1.21    0.9        10.0       0.021      slight settle on spawn
```

A naive reading: "Isaac wins — higher RTF, lower step-time." A senior reading walks each cell and asks *what it means for a decision*:

- **RTF 0.98 vs 1.21.** Isaac steps faster *for this one robot* on this GPU. But this number says **nothing** about parallel-env throughput (the axis that actually matters for RL) — and a higher single-robot RTF does not make Isaac the right tool for *debugging*, where boot time and iteration speed dominate. So this cell informs the *training* decision, not the *debugging* decision.
- **Step-time 1.6 vs 0.9 ms.** Consistent with the RTF, and on the GPU. Again: a *throughput* signal, relevant to "can I train fast," not "can I iterate fast."
- **/scan Hz 9.8 vs 10.0.** Both essentially hit the 10 Hz target — sensor *rate* fidelity is comparable. Neither sim is dropping scans. This cell says "for rate, they're equivalent."
- **scan var 0.012 vs 0.021.** Isaac's scan has *higher* variance — its sensor/noise model differs. This is not "worse"; it may be *more realistic* (real LiDAR is noisier than Gz's clean model). For a perception policy, that higher-fidelity noise could *help* sim-to-real; for a geometric SLAM check, it's just noise. Interpretation depends on the *consumer*.
- **Contact note.** Isaac shows a slight settle on spawn (a PhysX initialization transient); Gz sits flush. Minor, but it's the kind of engine-specific behavior that a brittle policy could trip on.

The disciplined conclusion from *this* table: **"Isaac is faster and its sensor noise is closer to real, which argues for using it to *train* a perception policy; Gz is flush, stable, and iterates faster, which argues for using it to *build and debug* the stack. Recommend Gz for integration, Isaac Lab for the RL/perception training — and keep the stack sim-agnostic so we use both."** That is a per-purpose recommendation grounded in specific cells — exactly what the challenge and homework grade, and the opposite of "Isaac had a higher number so use Isaac."

### 4.1 The Path B reading

If you ran two Gz engines instead (no NVIDIA GPU), the same discipline applies to DART vs Bullet: the differing cells (step-time, contact behavior, scan variance) tell you the *engines* approximate differently, and you reason — from Lecture 2's Isaac sections — about what the Gz-vs-Isaac axis (RTX rendering, GPU-parallel envs) *would* have added. You lose the hands-on Isaac numbers, not the interpretive skill, and your write-up says so explicitly. A Path B comparison that honestly marks "reasoned, not measured" for the GPU-parallel and photorealism axes is fully credible.

### 4.2 Common Isaac/Gz misconceptions, cleared up

The ones that show up in design reviews:

- **"Isaac Sim replaces Gz Sim."** No. They serve different jobs. Most teams run both: Gz to build/debug, Isaac to train. "Replace" is the wrong frame; "complement" is right.
- **"A higher RTF means a better simulator."** No. RTF on one robot is a single-world throughput number; it says nothing about parallel-env throughput (RL), fidelity, or iteration speed. One number, one axis.
- **"Isaac is more realistic, full stop."** Realism is per-sensor. Isaac's RTX camera is more realistic; its physics is *different*, not universally more realistic. Match the fidelity claim to the sensor.
- **"USD is just Isaac's version of SDF."** USD is a far more general scene format (film-grade, scriptable, composable). SDF is robotics-specific and simpler. They overlap in "describe a robot in a world" but USD does much more.
- **"The ROS2 bridge makes the sims interchangeable for free."** The *topic interface* is interchangeable (same `/scan`, `/cmd_vel`), which is what enables fair comparison — but the *sensor plugins/prims behind it* are sim-specific and must be re-authored. Interchangeable at the topic boundary, not below it.
- **"Domain randomization needs Isaac."** Not strictly — you can randomize per-episode in Gz Sim (Path B next week). Isaac makes *large-scale* randomization tractable via parallel envs; it isn't a hard requirement, it's a throughput multiplier.

### 4.3 The one-question decision tree

When you must pick a sim for a task, one question usually settles it:

```
What am I doing with this sim right now?
│
├─ Building/debugging the autonomy stack (Nav2, BTs, integration)
│     -> Gz Sim. Free, ROS-native, fast iteration. Don't pay Isaac's weight.
│
├─ Training a policy that needs millions of samples (PPO/SAC) or DR over many worlds
│     -> Isaac Lab. Only it gives GPU-parallel throughput.
│
├─ Generating photorealistic images to train/eval a vision policy
│     -> Isaac Sim. RTX closes the visual sim-to-real gap.
│
└─ A quick physics/contact sanity check on one robot
      -> Gz Sim (and swap the engine to probe contact brittleness).
```

It is almost never "one sim for everything." It is "this sim for this job," and the tree above is the senior reflex behind that answer.

---

## 5. Recap

You should now be able to:

- Explain Isaac Sim's three pillars: USD scene description (stages/prims/references), the RTX ray-traced renderer (photorealism for perception), and GPU-capable PhysX.
- Navigate a USD stage as a tree of prims addressed by path, and know the `SimulationApp`-before-imports rule.
- Compare USD and SDF head to head, and explain why sensor plugins/prims do not survive a cross-import.
- Explain Isaac Lab as the GPU-parallel RL/IL framework, what a tensorized env returns (an `N`-batch), and *why* parallel environments enable sample-hungry RL and next week's domain randomization.
- State the honest caveat that Isaac Lab's throughput requires GPU-friendly, tensorized env code — and why you still develop the task in Gz Sim.
- Bridge either simulator to ROS2 (the Isaac OmniGraph action graph), and keep your autonomy stack sim-agnostic so a comparison can hold everything but the simulator fixed.
- Explain why you measure RTF/step-time from `/clock` (one instrument for both sims) rather than each sim's native readout.
- Run a fair comparison on four metrics (RTF, step-time, sensor fidelity, contact behavior) and place each sim on the throughput-vs-fidelity curve.
- *Interpret* a comparison table per-cell and produce a per-purpose recommendation, not a single universal winner.
- Produce and defend a sim-selection table, answering "which sim?" with "for what?".

The synthesis of both lectures: a simulator is a physics engine plus a renderer plus a sensor model plus a bridge, and "which simulator" is really "which point on the throughput-vs-fidelity curve, for which job." Gz Sim and Isaac Sim sit at different points and serve different jobs; the senior skill is not loyalty to one but the judgment to pick per purpose, the rigor to measure fairly, and the discipline to keep your ROS2 stack sim-agnostic so the choice stays cheap to revisit. That judgment, backed by a measured table, is what you carry into the rest of Phase 5 — and it is exactly what next week's domain randomization depends on, because randomizing over many worlds is only affordable on the throughput side of the curve you just learned to measure.

Next: the exercises put a real robot in both worlds and make you measure. Continue to [the exercises](../exercises/README.md).

---

## References

- *Isaac Sim documentation*: <https://docs.isaacsim.omniverse.nvidia.com/latest/index.html>
- *Isaac Lab documentation*: <https://isaac-sim.github.io/IsaacLab/>
- *Isaac Sim ROS2 bridge tutorials*: <https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/index.html>
- *OpenUSD*: <https://openusd.org/release/index.html>
- *NVIDIA PhysX*: <https://nvidia-omniverse.github.io/PhysX/physx/>
- *Gz Sim performance / `gz stats`*: <https://gazebosim.org/docs>
