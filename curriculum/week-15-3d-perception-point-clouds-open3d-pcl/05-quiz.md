# Week 15 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 16. Answer key is at the bottom — don't peek.

---

**Q1.** Why do we voxel-downsample a cloud *before* running ICP — beyond just speed?

- A) It adds color to the points.
- B) It regularizes the point density to a uniform grid, which makes ICP's nearest-neighbour correspondences more reliable — uneven density biases ICP toward the dense region.
- C) It removes the need for normals.
- D) It converts the cloud to `16UC1`.

---

**Q2.** Statistical outlier removal drops a point when:

- A) The point is exactly on a plane.
- B) The point's mean distance to its `k` nearest neighbours is more than `std_ratio` standard deviations above the global average — i.e. it's isolated (a flying pixel or straggler).
- C) The point is the centroid of a voxel.
- D) The point has no color.

---

**Q3.** When you convert a `sensor_msgs/PointCloud2` to an Open3D cloud and back, what must you do that's easy to forget?

- A) Re-estimate the normals.
- B) Hold the `header` (stamp + frame_id) aside and reattach it on the way back — Open3D drops it.
- C) Convert millimetres to metres.
- D) Re-run RANSAC.

---

**Q4.** You RANSAC a ground plane and get a normal of `(0.98, 0.0, 0.1)`. What does this tell you?

- A) The floor is perfectly level.
- B) RANSAC picked a near-*vertical* plane (a wall), not the floor — the normal should be ≈ `(0, 0, 1)`. Constrain the normal to near-vertical, or your cloud is in the wrong frame.
- C) The cloud is empty.
- D) The voxel size is too large.

---

**Q5.** Why must ground segmentation come *before* Euclidean clustering?

- A) Clustering is faster on the ground points.
- B) The ground is the largest surface and connects every object to every other; until it's removed, a single ground point bridges two objects and clustering merges them.
- C) RANSAC needs the clusters first.
- D) Order doesn't matter.

---

**Q6.** In Euclidean clustering, you set `eps` too *large*. The likely symptom is:

- A) Every object becomes noise.
- B) Under-segmentation: two nearby objects merge into one cluster.
- C) The ground reappears.
- D) The cloud doubles in size.

---

**Q7.** Why does **point-to-plane** ICP typically converge in fewer iterations than **point-to-point**?

- A) It uses a GPU.
- B) It minimizes the distance from each source point to the target *surface* (using normals), letting the source slide along the surface — the freedom a real surface has — instead of pinning to discrete points.
- C) It skips the correspondence step.
- D) It downsamples more aggressively.

---

**Q8.** ICP returns a transform with `fitness = 0.22` and `inlier_rmse = 0.35 m` between two consecutive scans. You should:

- A) Trust it; ICP returned without an error.
- B) Distrust it — low fitness and high RMSE mean it did not converge to a real alignment (likely insufficient overlap or a wrong local minimum). ICP returning is not a trust signal.
- C) Increase the voxel size and trust it.
- D) Publish it as odometry anyway.

---

**Q9.** ICP from an identity initial guess converges with `fitness = 0.85` but reports a 50° rotation where the robot only turned ~5°. This is:

- A) A correct result.
- B) The wrong-local-minimum trap: a bad initial guess made ICP lock onto consistent but *wrong* correspondences. Fitness alone didn't catch it — the *implausible transform* did. Seed ICP with a better guess (constant velocity or global registration).
- C) An overlap problem.
- D) A unit bug.

---

**Q10.** You need to register two clouds in *arbitrary* poses with no initial guess. The right approach is:

- A) Run point-to-point ICP from the identity and hope.
- B) FPFH feature extraction + RANSAC-based feature matching to find a coarse alignment (the right basin), then refine with ICP.
- C) Voxel-downsample harder.
- D) Increase `max_iteration` to 10000.

---

**Q11.** A long featureless corridor is a problem for ICP because:

- A) The corridor is too dark.
- B) The geometry doesn't *constrain* along-corridor motion — ICP can slide the source down the hallway with little change in cost (degenerate geometry). The information isn't there; better ICP can't fix it.
- C) Corridors have too many points.
- D) Normals can't be estimated in corridors.

---

**Q12.** Scan-to-scan ICP odometry over 100 scans drifts even when each pairwise registration is good. Why?

- A) ICP gets slower over time.
- B) Each pairwise registration has a small residual error, and composing the transforms compounds those errors — small rotation errors rotate the entire remaining trajectory. The same compounding as wheel odometry.
- C) The point clouds shrink.
- D) Open3D has a memory leak.

---

**Q13.** What bounds the drift of pairwise ICP odometry over a long sequence?

- A) Nothing; it's unbounded by design.
- B) Loop closure (recognizing a revisited place) plus pose-graph optimization, which adds constraints that pull the accumulated drift back into consistency — the same idea as Week 7's 2D SLAM, and what FAST-LIO2 / LIO-SAM do in 3D (with an IMU for the degenerate directions).
- C) A larger voxel size.
- D) Running ICP more often.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Downsampling regularizes density to a uniform grid, which ICP's nearest-neighbour correspondences need; it's a correctness aid, not just speed. (Lecture 1 §2.)
2. **B** — SOR drops points whose mean-neighbour-distance is a statistical outlier — the isolated flying pixels and stragglers. (Lecture 1 §3.2.)
3. **B** — Open3D drops the ROS header; hold the stamp + frame_id aside and reattach on the way out, or you lie about when/where the cloud was seen. (Lecture 1 §1.1.)
4. **B** — A normal of `(0.98, 0, 0.1)` is near-horizontal-axis → a vertical plane (wall), not the floor. The floor normal is ≈ `(0,0,1)`. Constrain the normal or fix the frame. (Lecture 1 §4.)
5. **B** — The ground connects everything; one un-removed ground point bridges two objects and clustering merges them. Remove ground first. (Lecture 1 §4, §5.2.)
6. **B** — Too-large `eps` merges nearby objects (under-segmentation). Too-small over-segments or dissolves objects into noise. (Lecture 1 §5.)
7. **B** — Point-to-plane minimizes point-to-*surface* distance using normals, letting the source slide along the surface — faster, more robust than pinning to discrete points. (Lecture 2 §1.1.)
8. **B** — Low fitness + high RMSE = no real convergence. ICP returning is not a trust signal; the fitness/RMSE/plausibility triple is. (Lecture 2 §1.2.)
9. **B** — Decent fitness but an implausible transform is the wrong-local-minimum trap from a bad initial guess. Plausibility caught what fitness didn't. Seed with a better guess / global registration. (Lecture 2 §2.1, §1.2.)
10. **B** — No initial guess → global registration: FPFH + RANSAC feature matching for a coarse alignment, then ICP refines. (Lecture 2 §2.4.)
11. **B** — A corridor doesn't constrain along-track motion; ICP slides freely with little cost change (degenerate geometry). The info isn't there — fuse another sensor (IMU). (Lecture 2 §2.3.)
12. **B** — Per-pairwise residual errors compound when composed; rotation errors rotate the whole remaining path. Same compounding as wheel odometry. (Lecture 2 §3.1.)
13. **B** — Loop closure + pose-graph optimization bound the drift; with an IMU for degenerate directions, this is FAST-LIO2 / LIO-SAM. The Week-7 2D SLAM idea, in 3D. (Lecture 2 §3.3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
