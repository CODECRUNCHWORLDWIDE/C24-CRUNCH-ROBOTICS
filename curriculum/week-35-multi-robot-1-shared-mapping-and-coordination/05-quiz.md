# Week 35 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 36. Answer key is at the bottom — don't peek.

---

**Q1.** Two copies of the same robot launch file run in one graph with no changes. Name the three axes on which they collide.

- A) CPU, memory, and disk.
- B) Topic names, TF frame names, and node names.
- C) Reliability, durability, and history.
- D) IP address, MAC address, and port.

---

**Q2.** A node hard-codes its publisher topic as `/cmd_vel` (with a leading slash) and is launched under namespace `robotA`. What is the resolved topic name?

- A) `/robotA/cmd_vel` — the namespace prefixes it.
- B) `/cmd_vel` — the leading slash makes it absolute, defeating the namespace.
- C) `/robotA/robotA/cmd_vel` — double-prefixed.
- D) The node fails to start.

---

**Q3.** You namespaced both robots perfectly, yet `view_frames` shows one `base_link` with two parents. Why, and what fixes it?

- A) The domains differ; set `ROS_DOMAIN_ID`.
- B) Namespacing prefixes topic names but not TF frame names (which live inside the message data); fix it with a `frame_prefix` at the broadcaster.
- C) The QoS is mismatched; set `TRANSIENT_LOCAL`.
- D) Nothing is wrong; tf2 always shows two parents for two robots.

---

**Q4.** Why do two `slam_toolbox` robots have two unrelated `map` frames even after frame-prefixing them to `robotA/map` and `robotB/map`?

- A) `slam_toolbox` is buggy.
- B) Each robot's `map` is the origin of *its own* first scan — two different physical points; prefixing names them honestly but doesn't relate them.
- C) The maps are the same; the names just differ.
- D) Because they're on different `ROS_DOMAIN_ID`s.

---

**Q5.** What is the role of the shared `world` frame in the two-robot tree?

- A) It replaces both robots' `map` frames.
- B) It's a neutral root; `world -> robotA/map` and `world -> robotB/map` tie both robots' maps into one frame the merged map lives in.
- C) It's only used by rviz2 and has no effect on the merge.
- D) It's the same as `robotA/map`.

---

**Q6.** For the shared-mapping system, should the two robots and the merger share a `ROS_DOMAIN_ID`?

- A) No — they must be isolated for safety.
- B) Yes — the merger must discover both robots' `/map` topics to consume them.
- C) It doesn't matter; discovery ignores domains.
- D) Only the merger needs a domain; the robots don't.

---

**Q7.** When merging two overlapping occupancy-grid cells where robot A saw occupied (100) and robot B saw free (0), the merged value should be:

- A) 50 — the average.
- B) 0 — free, trust the more recent observation.
- C) 100 — occupied wins; over-reporting obstacles is the safe-direction bias.
- D) -1 — unknown, because they disagree.

---

**Q8.** Why must you account for each grid's `info.origin` when merging, not just the `data` array?

- A) `info.origin` sets the color in rviz2.
- B) The grid is an array *plus where its corner sits in the world*; ignoring `info.origin` merges the maps shifted.
- C) `info.origin` is always zero, so it can be ignored.
- D) It only matters for 3D maps.

---

**Q9.** In rviz2 the merged map of a known rectangular room shows two parallel walls 0.3 m apart where there should be one. The most likely cause is:

- A) The fusion rule averaged instead of occupied-wins.
- B) A wrong or stale inter-robot transform — robot B's copy of the wall is offset from robot A's copy of the same wall by 0.3 m.
- C) The LiDAR is `RELIABLE` instead of `BEST_EFFORT`.
- D) The robots are on different domains.

---

**Q10.** Why must a robot never block its control loop on a synchronous call to another robot?

- A) Synchronous calls are deprecated in ROS2.
- B) The inter-robot network is slow and occasionally gone; a robot that blocks its safety loop on a peer's reply drives into a wall while waiting.
- C) Services can't cross namespaces.
- D) It would violate the type-hash check.

---

**Q11.** The merger subscribes to both `/map` topics but merges on its own 2 s timer from cached maps. What consistency model is this, and why is it the honest choice?

- A) Strong consistency — every consumer always sees the current map.
- B) Eventual consistency — each consumer's view converges over time; it's honest because a reliable, zero-latency fleet network does not exist.
- C) No consistency — the maps are random.
- D) Causal consistency — messages are globally ordered.

---

**Q12.** The static `world -> robotB/map` transform is published on `/tf_static`. Why must `/tf_static` be `TRANSIENT_LOCAL`?

- A) So the merger publishes faster.
- B) So a merger (or `tf2_echo`) that starts *after* the static transform was published still receives it; a `VOLATILE` `/tf_static` would silently leave late listeners unable to relate the two maps.
- C) `/tf_static` must be `BEST_EFFORT` for low latency.
- D) It doesn't matter; static transforms re-publish at 10 Hz.

---

**Q13.** What is the gap between your week-35 grid-merger (known transform) and a research-grade system like Kimera-Multi?

- A) Kimera-Multi uses a faster programming language.
- B) Kimera-Multi *estimates* the inter-robot transform via place recognition and inter-robot loop closures (rejecting bad matches), rather than assuming a known offset.
- C) There is no gap; they're the same.
- D) Kimera-Multi merges grids; yours merges submaps.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Topics, TF frames, node names. Namespace fixes topic/node names; a frame prefix fixes TF frames. (Lecture 1 §1.)
2. **B** — A leading slash makes the name absolute; it ignores the namespace and resolves to the global `/cmd_vel`. This is *the* multi-robot trap. (Lecture 1 §2.)
3. **B** — Namespacing prefixes topic names, not TF frame names (frames are message *contents*). Fix with `frame_prefix` on `robot_state_publisher` and the `*_frame` params on `slam_toolbox`. (Lecture 1 §3.)
4. **B** — Each robot's `map` is the origin of its own first scan, two unrelated physical points. Prefixing names them honestly; it does not relate them. (Lecture 1 §5.)
5. **B** — `world` is a neutral root; the two `world -> robot/map` transforms tie both maps into one frame, which is where the merged grid lives. (Lecture 1 §6.)
6. **B** — Same domain. The merger must discover both robots' `/map` topics; participants only discover others in the same `ROS_DOMAIN_ID`. (Lecture 1 §4.)
7. **C** — Occupied wins. Over-reporting obstacles is conservative in the safe direction; averaging gives unusable gray mush. (Lecture 2 §1.4.)
8. **B** — A grid is an array *plus* its origin pose; ignoring `info.origin` merges the maps shifted. (Lecture 2 §1.1, §1.3.)
9. **B** — Doubled walls are the signature of a wrong/stale inter-robot transform: B's copy of a shared wall lands offset from A's copy. (Lecture 2 §2.3.)
10. **B** — The inter-robot network is slow and unreliable; blocking a safety loop on a peer is how a robot crashes while waiting. Coordination is asynchronous and best-effort. (Lecture 2 §3.1.)
11. **B** — Eventual consistency. It's the only honest fleet model because a reliable zero-latency network doesn't exist (the distributed-computing fallacies). (Lecture 2 §3.2.)
12. **B** — `TRANSIENT_LOCAL` so late listeners get the latched static transform; a `VOLATILE` `/tf_static` silently fails late joiners — the week-5 durability lesson at the multi-robot layer. (Lecture 2 §2.2.)
13. **B** — Kimera-Multi *estimates* the inter-robot transform via place recognition + inter-robot loop closures with outlier rejection; you *assumed* it. That estimation is the gap. (Lecture 2 §4.2–4.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
