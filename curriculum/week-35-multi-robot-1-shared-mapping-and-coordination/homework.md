# Week 35 Homework

Six problems that revisit the week's topics and force the multi-robot discipline into your fingers. The full set should take about **5 hours**. Work in your Week 35 Git repository (the same workspace as the exercises and the `crunchbot_multi` mini-project) so every problem produces at least one commit you can point to at the Phase 5 milestone in Week 40.

The headline deliverable is **Problem 4 — the merge-quality report**, which quantifies your shared map against ground truth and is the artifact a reviewer reads.

Each problem includes:

- A short **problem statement**.
- **Acceptance criteria** so you know when you're done.
- A **hint** if you get stuck.
- An **estimated time**.

Source ROS2 Jazzy in every terminal (`source /opt/ros/jazzy/setup.bash`) and source your overlay. Have **two robots** spawnable in Gz Sim (the `crunchbot_multi` two-robot launch) — Problems 1, 2, and 4 run against them. If the sim is heavy, the standalone grid publishers from Exercises 2 and 3 are your fallback; say so in your writeup.

---

## Problem 1 — The two-robot graph audit

**Problem statement.** Bring up your two-robot launch. Produce a markdown audit at `notes/week-35/graph-audit.md` with three parts:

1. A **topic table**: every topic, which namespace owns it, and whether it's correctly prefixed (no bare `/scan`, `/map`, `/odom`).
2. The **TF tree** (`view_frames` PDF committed, plus a text sketch) showing two parallel sub-trees under one `world`.
3. The output of `ros2 run tf2_ros tf2_echo world robotA/base_link` and `... robotB/base_link`, proving both resolve into the shared frame with the expected offsets.

**Acceptance criteria.**

- `notes/week-35/graph-audit.md` exists with all three parts.
- The topic table has at least the per-robot `scan`, `map`, `odom`, plus the shared `/tf`, `/tf_static`.
- You explicitly flag any bare (un-prefixed) topic, or argue every topic is correctly namespaced and why `/tf`/`/tf_static` are *supposed* to be shared.
- Committed (including `frames.pdf`).

**Hint.** `for ns in robotA robotB; do echo "== $ns =="; ros2 topic list | grep "/$ns/"; done`. If a bare `/map` appears, an upstream node publishes absolute `/map` and you forgot the `remappings=[("/map","map")]` (Lecture 1 §2.2).

**Estimated time.** 40 minutes.

---

## Problem 2 — Break and fix the frame prefix

**Problem statement.** Deliberately *remove* the `frame_prefix` from `robotB`'s `robot_state_publisher` (and leave its `slam_toolbox` `*_frame` params prefixed). Relaunch. Observe and document what happens to the TF tree and to `tf2_echo world robotB/base_link`. Then restore the prefix and confirm recovery.

**Acceptance criteria.**

- `notes/week-35/frame-prefix-break.md` records: the broken `view_frames` (a `base_link` with conflicting parents, or a frame named bare `base_link`), the error or wrong result from `tf2_echo`, and the restored-correct output.
- You correctly explain *why* a missing `frame_prefix` on `robot_state_publisher` but a prefixed `slam_toolbox` produces a *broken* tree (the SLAM-published `robotB/map -> robotB/odom` doesn't connect to an un-prefixed `base_link`).
- Committed.

**Hint.** The symptom is a disconnected tree: `slam_toolbox` publishes `robotB/odom -> robotB/base_link`-shaped transforms only if `base_frame` is `robotB/base_link`, but `robot_state_publisher` is publishing `base_link -> laser_link` (un-prefixed) — so `robotB/base_link` and `base_link` are two different frames and the chain breaks. This is the exact bug Lecture 1 §3 warns about.

**Estimated time.** 40 minutes.

---

## Problem 3 — Domain isolation drill

**Problem statement.** Launch your two robots on `ROS_DOMAIN_ID=7`. In a *separate* terminal exported to `ROS_DOMAIN_ID=8`, run `ros2 topic list` and confirm you see *nothing* from the robots. Then export `ROS_DOMAIN_ID=7` in that terminal and confirm the topics appear. Document the experiment and state the rule.

**Acceptance criteria.**

- `notes/week-35/domain-isolation.md` shows the empty `ros2 topic list` under domain 8 and the populated one under domain 7.
- You state the rule in one sentence: participants only discover participants in the same `ROS_DOMAIN_ID`; this is the coarse fleet-isolation knob.
- You note one real-world use: running an independent fleet (or a dev robot) on the same LAN without cross-talk.
- Committed.

**Hint.** Each terminal must `export ROS_DOMAIN_ID=N` *before* running any `ros2` command — the variable is read at participant creation. The classic self-own is forgetting to export it in one terminal, which is exactly the symptom you're demonstrating deliberately here (Lecture 1 §4).

**Estimated time.** 30 minutes.

---

## Problem 4 — The merge-quality report (headline deliverable)

**Problem statement.** Drive both robots to map a shared room (or use the Exercise 2 grids). Produce `/shared_map` from your merger. Then quantify its quality against ground truth in `notes/week-35/merge-quality.md`:

1. **Coverage** — the merged map's explored area (free + occupied cells) vs. either single robot's, showing the merge gained coverage.
2. **Wall crispness** — count occupied runs per row (the Challenge-1 double-wall metric); a correct merge has single-thickness walls, a wrong transform doubles them. Report the worst row.
3. **Transform sensitivity** — re-run the merge with the inter-robot offset deliberately off by 1, 2, and 4 cells (reuse Exercise 3) and tabulate the phantom occupied cells each error introduces. Plot or table it.
4. **The fusion-rule check** — confirm a cell where the two robots disagreed (one occupied, one free) is occupied in the merged map, and state the rule.

**Acceptance criteria.**

- `notes/week-35/merge-quality.md` exists with all four parts and real numbers (from your merger or the exercise scripts, not from memory).
- The transform-sensitivity table shows phantom occupied cells *increasing* with offset error.
- The fusion-rule check explicitly names occupied-wins and points at a real conflict cell.
- The coverage number shows the merge has *more* explored area than either robot alone (the point of merging).
- Committed.

**Hint.** Exercise 3 already computes phantom occupied cells for a given `WRONG_DELTA` — parameterize it over `{1, 2, 4}` and collect the numbers. For wall crispness on a real `/shared_map`, save the grid (`ros2 topic echo /shared_map --once`) and run a small numpy script counting `100`-runs per row.

**Estimated time.** 1 hour.

---

## Problem 5 — The non-blocking merger proof

**Problem statement.** Prove your merger never blocks on a robot. With both robots running and `/shared_map` publishing, **kill robot B's SLAM** (`ros2 lifecycle set` to deactivate, or just kill the process). The merger must keep publishing the last good `/shared_map` and log that robot B's input is stale — it must *not* hang, crash, or stop publishing. Then restart robot B's SLAM and confirm the merger picks the new map back up.

**Acceptance criteria.**

- `notes/week-35/non-blocking-merger.md` captures the merger's logs across: both-alive, robot-B-killed (still publishing, logging staleness), robot-B-restarted (fresh merge).
- The merger continues publishing `/shared_map` throughout, never blocking.
- You state in one sentence why merging from *cached* maps on a timer (not a synchronous gather) is what makes this possible (Lecture 2 §3.2).
- Committed.

**Hint.** If your merger *does* hang when robot B dies, you put the inter-robot interaction on the critical path — almost certainly a synchronous service call or a `wait_for_message`. Move to the cache-and-timer pattern from the mini-project skeleton.

**Estimated time.** 45 minutes.

---

## Problem 6 — Survey write-up: where distributed SLAM goes

**Problem statement.** Write a one-page (~400–550 word) technical brief at `notes/week-35/distributed-slam-brief.md` answering, as if for a teammate deciding what to build next: "We have a known-transform grid-merger. What does it take to drop the 'known transform' assumption?" Cover, accurately and in your own words: (1) the inter-robot loop-closure / place-recognition problem, (2) how Kimera-Multi does distributed pose-graph optimization without a central server, (3) why bad inter-robot loop closures are dangerous and how DOOR-SLAM's pairwise-consistency idea rejects them, (4) an honest statement of what your week-35 system does and does not do.

**Acceptance criteria.**

- `notes/week-35/distributed-slam-brief.md` exists, ~400–550 words, hits all four points.
- It is *honest* about your system's limits: it does shared mapping with a known/assumed inter-robot transform; it does not do place recognition or inter-robot loop closure.
- At least the Kimera-Multi and DOOR-SLAM references (from `resources.md`) are cited.
- It reads like a brief for an engineer, not a paper summary — concrete about the *decision* (build place recognition? buy a known-transform assumption with surveyed docks?).
- Committed.

**Hint.** The senior framing: "a known-transform merger is the right call when you can survey start positions (warehouse with docks); the moment you can't, you need place recognition, and that's a research-grade effort, so budget accordingly." That sentence is the whole brief in miniature (Lecture 2 §4.3).

**Estimated time.** 45 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Two-robot graph audit | 40 min |
| 2 — Break and fix the frame prefix | 40 min |
| 3 — Domain isolation drill | 30 min |
| 4 — Merge-quality report (headline) | 1 h 0 min |
| 5 — Non-blocking merger proof | 45 min |
| 6 — Distributed-SLAM brief | 45 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunchbot_multi` [mini-project](./mini-project/README.md) is in the same workspace — Week 36 builds the fleet manager on top of it. Then take the [quiz](./quiz.md) with your notes closed.
