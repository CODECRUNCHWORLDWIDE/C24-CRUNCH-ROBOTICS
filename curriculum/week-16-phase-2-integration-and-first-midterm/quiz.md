# Week 16 — Quiz

Thirteen questions on composing the perception stack, the latency budget, frames and timing, data association, the robustness gates, and the midterm defense. Take it with your lecture notes closed. Aim for 11/13 before you defend the milestone. Answer key at the bottom — don't peek.

---

**Q1.** The end-to-end perception latency of a graph with a 12 ms YOLO branch and an 8 ms clustering branch running *in parallel*, plus 3 ms fusion and 2 ms publish, is:

- A) 25 ms (the sum of all hops).
- B) ~17 ms — the critical path is `max(branches) + fusion + publish` = max(12+transport, 8+transport) + 3 + 2.
- C) 12 ms (just the YOLO inference).
- D) 8 ms (just the clustering).

---

**Q2.** Why report perception latency as **p95**, not the mean?

- A) The mean is harder to compute.
- B) A mean of 18 ms with a p99 of 80 ms is a worse system than a flat 28 ms — the tail is where a moving object's detection goes stale and the grasp targets where it was. The panel asks for the worst common case.
- C) p95 is always smaller than the mean.
- D) The mean isn't a real statistic.

---

**Q3.** A student reports "my perception is 12 ms" — the YOLO inference time. The panel asks "from the sensor stamp, under load, p95?" The student's number was wrong because:

- A) 12 ms is too fast to be real.
- B) Inference time of one hop is not the end-to-end path latency, and idle is not under load. The forgotten hops (acquisition, transport, association, transform, publish) and the GPU contention under load make the real number larger.
- C) YOLO can't run in 12 ms.
- D) The mean and p95 are the same.

---

**Q4.** To put a detection acquired at time `t` into the `map` frame, you look up the `map ← sensor` transform at:

- A) `now()` — always use the latest transform.
- B) Time `t` (the detection's acquisition stamp), via tf2 time-travel — because the robot moved between `t` and `now()`, and the transform at `now()` is for where the robot *is*, not where it *was* when it saw the object.
- C) The midpoint of `t` and `now()`.
- D) It doesn't matter which time.

---

**Q5.** `/perception/clusters` publishes at 8 Hz; the fusion node ticks at 20 Hz. What's the risk, and the fix?

- A) No risk; faster is always fine.
- B) The stale-perception race — on a slow frame the "latest" cluster the fusion grabs is ~125 ms old. Fix: a stamp-age guard at the point of use that rejects a cluster older than tolerance.
- C) The clusters arrive too fast.
- D) A QoS mismatch.

---

**Q6.** A LiDAR cluster has no matching 2D detection (out of the camera's FOV). Your fusion node should:

- A) Drop it — without a class it's useless.
- B) Publish it as a 3D object with class `unknown` — an unclassified obstacle is still an obstacle the planner must avoid.
- C) Invent a class from the nearest detection.
- D) Crash.

---

**Q7.** Why use the **Hungarian algorithm** for detection-to-cluster association instead of greedy nearest-match?

- A) It's faster than greedy.
- B) Greedy matching produces double-matches and is order-dependent; the Hungarian solver finds the globally optimal assignment with each cluster matched to at most one detection.
- C) Greedy doesn't work with IoU.
- D) The Hungarian algorithm needs no IoU matrix.

---

**Q8.** Your ICP odometry hits a degenerate corridor and returns a wrong transform. How does your fused node keep it from corrupting the state estimate?

- A) It can't; a bad input always corrupts the estimate.
- B) The ICP-health gate inflates the odometry covariance when fitness is low, so the EKF automatically de-weights the bad measurement — an honest covariance lets the filter ignore garbage without a hard reject.
- C) It restarts the EKF.
- D) It drops to wheel odometry only, permanently.

---

**Q9.** Why is composing seven weeks of perception components into one node a *midterm* and not just another lab?

- A) It's longer.
- B) Integration is where the components *disagree* — frame, timing, rate, and association defects only appear when the whole graph is live; the midterm composes everything to surface the weak component, and it's a hard gate.
- C) It uses more topics.
- D) The panel likes round numbers.

---

**Q10.** Which is **not** one of the four perception-integration defects?

- A) The frame/timing mismatch (detections in the wrong frame or transformed at the wrong stamp).
- B) The stale-perception race (a fast consumer using a slow producer's stale data).
- C) A compiler optimization bug in `rclcpp`.
- D) The latency-budget blowout under load (idle 30 ms, 70 ms under GPU/CPU contention).

---

**Q11.** The interface-contract table records, per seam: topic, type, frame, rate, and QoS. Which column most directly guards against the stale-perception race?

- A) Topic.
- B) Type.
- C) Rate — a slow producer feeding a fast consumer is the race; the rate column flags it.
- D) QoS.

---

**Q12.** The Week 16 midterm is a "hard gate." What does that mean?

- A) The quiz is harder.
- B) A failure sends you back to the offending week to fix the weak component before advancing — the composition is diagnostic, finding the weakness now (resubmittable) instead of at the capstone (costly).
- C) You only get one attempt ever.
- D) It's graded pass/fail with no feedback.

---

**Q13.** The strongest way to defend a latency number to the panel is:

- A) Assert it confidently and move on.
- B) Pin the endpoints (sensor stamp → publish, p95, under load), know where it fails first (which hop / which scene), and offer the script: "here's the probe, run it yourself" — a reproducible number is unassailable.
- C) Round it down to a nicer figure.
- D) Compare it to a competitor's number.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Parallel branches: the critical path is `max(branches) + fusion + publish`, not the sum. Drawing the diagram reveals the parallelism. (Lecture 1 §1.3, §1.8.)
2. **B** — p95 (the worst common case) is what matters; a fat tail is where detections go stale. The panel asks for the percentile, not the mean. (Lecture 1 §1.4.)
3. **B** — One hop's inference time isn't the path's end-to-end latency, and idle isn't under load. The forgotten hops and the contention make the real number larger. (Lecture 1 §1.3, §1.4.)
4. **B** — Look up the transform at the detection's acquisition stamp via tf2 time-travel; `now()` uses the current robot pose for a past observation and injects motion-proportional error. (Lecture 1 §1.5.)
5. **B** — A slow producer + fast consumer is the stale-perception race; the fix is a stamp-age guard at the point of use. (Lecture 1 §1.6.)
6. **B** — Publish a no-match cluster as `unknown`; an unclassified obstacle is still an obstacle. Dropping it is a perception bug. (Lecture 2 §2.1.2.)
7. **B** — Greedy double-matches and is order-dependent; the Hungarian solver gives the globally optimal one-to-one assignment. (Lecture 2 §2.1.1.)
8. **B** — The ICP-health gate inflates the odom covariance on low fitness; the EKF de-weights it automatically. An honest covariance is how the filter ignores garbage. (Lecture 2 §2.2.)
9. **B** — Integration surfaces the disagreements between components, which only appear live; the midterm composes everything to find the weak component, and it's a hard gate. (README; Lecture 2 §2.6.)
10. **C** — The four defects are frame/timing, stale-perception, data-association, and latency-blowout. A compiler bug in `rclcpp` is not one of them. (Lecture 1 §1.7.)
11. **C** — The rate column flags a slow-producer/fast-consumer seam, which is the stale-perception race. (Lecture 1 §1.2.)
12. **B** — A hard gate sends failures back to the offending week; the composition is diagnostic, surfacing the weakness now rather than at the capstone. (Lecture 2 §2.6.)
13. **B** — Pin the endpoints, know the failure boundary, and offer the reproducible script. A number you can reproduce on demand is unassailable. (Lecture 2 §2.5.)

</details>

---

If you scored under 9, re-read the lectures for the questions you missed — especially Lecture 1 on the latency budget and Lecture 2 on data association and the defense. If you scored 11 or higher, you're ready to defend the milestone: head to the [homework](./homework.md) and the [mini-project](./mini-project/README.md).
