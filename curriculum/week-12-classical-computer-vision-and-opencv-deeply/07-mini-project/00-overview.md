# Mini-Project — `crunch_vo`: A Monocular Visual-Odometry ROS2 Node

> Build a ROS2 node that consumes a calibrated camera stream (`/camera/image_raw` + `/camera/camera_info`), tracks ORB features frame-to-frame, recovers the camera's relative motion with a RANSAC essential matrix, and publishes the accumulated trajectory as a `nav_msgs/Path` in a `camera_odom` frame. This is **monocular visual odometry** — the front end of every visual-SLAM system — built from the classical pieces you learned this week, with the honest scale ambiguity documented.

This is the week's flagship. The exercises taught the pieces — calibration, ORB matching, RANSAC, flow. The mini-project assembles the matching-and-geometry pieces into a running visual-odometry node: images in, camera trajectory out. After this, "ORB-SLAM3 tracks ORB features and recovers pose from the essential matrix" is not a sentence you read; it is the loop you wrote.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** Visual odometry is one of the relative-motion sources you'll fuse in the **Week 16 perception graph** (its frame-to-frame `R, t` is a between factor for the Week 11 pose-graph back-end), and the ORB+RANSAC front end is the literal mechanism inside ORB-SLAM3, which you'll meet again in the Phase 2 SLAM work. The capstone's drift-bounded state estimate can take visual odometry as one of its inputs. Build the front end well now.

---

## What you will build

A small ament-python package `crunch_vo` with three deliverables:

1. **`crunch_vo/vo_core.py`** — a pure-Python, ROS-free `MonocularVO` class. It holds the camera intrinsics `K` and exposes `process_frame(gray_image) -> (R_rel, t_rel, n_inliers)`: it detects ORB features, matches against the previous frame with the ratio test, recovers the essential matrix with RANSAC, decomposes it into a relative rotation and (up-to-scale) translation, and accumulates the global pose. Fully unit-testable on synthetic image pairs with no ROS.
2. **`crunch_vo/vo_node.py`** — the ROS2 node. It subscribes to `/camera/image_raw` (converting with `cv_bridge`) and `/camera/camera_info` (to get `K`), feeds each frame to `MonocularVO`, and publishes the accumulated trajectory on `/vo/path` (`nav_msgs/Path`) in a `camera_odom` frame, plus the current pose on `/vo/pose` (`geometry_msgs/PoseStamped`). It also publishes the per-frame inlier count on a diagnostics topic so you can see when tracking degrades.
3. **A demo + tests** — a synthetic-image-pair demo (warp a textured scene by a known motion, confirm the recovered `R` matches), plus `pytest` tests on `vo_core` (a known pure-translation pair recovers a translation; a known rotation recovers that rotation; a textureless pair returns a low inlier count and is flagged, not crashed).

By the end you have a public repo of ~300–400 lines of Python that runs as a live VO node and that any future crunchbot package can reuse as a visual-motion source.

---

## Why a ROS-free core class

Same discipline as the Week 5 `crunchbot_qos` and Week 11 `crunch_posegraph` projects: **all the OpenCV/geometry logic lives in a plain Python class with no ROS imports**, and the node is a thin `cv_bridge` adapter. This buys you:

- **Testability.** `pytest` runs `MonocularVO` on synthetic image pairs in milliseconds — no `rclpy`, no camera, no DDS. The geometry (the hard part) is tested in isolation.
- **Reusability.** The same core runs offline on a recorded bag or a folder of images, in a notebook for tuning, or inside the live node.
- **Clarity.** When tracking fails on the robot, you know instantly whether the bug is in the geometry (test the core) or the plumbing (the node).

---

## Package layout

```
crunch_vo/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_vo
├── crunch_vo/
│   ├── __init__.py
│   ├── vo_core.py          # ORB + RANSAC essential matrix (ROS-free, the heart)
│   ├── vo_node.py          # the ROS2 node (cv_bridge adapter)
│   └── demo_pairs.py       # synthetic image-pair generator for the demo + tests
├── launch/
│   └── vo.launch.py
└── test/
    ├── test_vo_geometry.py     # known motion -> recovered R/t
    └── test_vo_degenerate.py   # textureless pair -> low inliers, flagged not crashed
```

---

## Deliverable 1 — `vo_core.py` (the geometry)

This is the heart. It must:

- Construct with the camera intrinsics `K` (a 3×3 NumPy array).
- Hold the previous frame's keypoints + descriptors and the accumulated global pose (`R_global`, `t_global`).
- `process_frame(gray)`:
  1. Detect ORB features (`cv2.ORB_create`) and compute descriptors.
  2. On the first frame, store and return identity (no motion yet).
  3. On subsequent frames: match against the previous frame (`BFMatcher(NORM_HAMMING)`, `knnMatch`, Lowe's ratio test).
  4. If too few matches survive, return a "tracking lost" signal (low inlier count) — do **not** crash.
  5. Recover the essential matrix with RANSAC (`cv2.findEssentialMat(..., method=cv2.RANSAC)`) and decompose it (`cv2.recoverPose`) into `R_rel`, `t_rel` (unit translation — scale is unobservable).
  6. Accumulate into the global pose and return `(R_rel, t_rel, n_inliers)`.

Here is the spine to start from; fill in the matching and accumulation yourself:

```python
"""crunch_vo.vo_core — monocular visual odometry from ORB + RANSAC essential matrix.

ROS-free so it is unit-testable on synthetic image pairs without rclpy.
"""
from __future__ import annotations

import cv2
import numpy as np

MIN_MATCHES = 20          # below this, tracking is unreliable -> flag, don't crash


class MonocularVO:
    def __init__(self, K: np.ndarray) -> None:
        self.K = K
        self.orb = cv2.ORB_create(nfeatures=1500)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.prev_kp = None
        self.prev_des = None
        self.R_global = np.eye(3)
        self.t_global = np.zeros((3, 1))

    def process_frame(self, gray: np.ndarray):
        kp, des = self.orb.detectAndCompute(gray, None)

        if self.prev_des is None or des is None or len(kp) < MIN_MATCHES:
            self.prev_kp, self.prev_des = kp, des
            return np.eye(3), np.zeros((3, 1)), 0

        # Match previous -> current with Lowe's ratio test.
        knn = self.bf.knnMatch(self.prev_des, des, k=2)
        good = [m for m, n in knn if len([m, n]) == 2 and m.distance < 0.75 * n.distance]

        if len(good) < MIN_MATCHES:
            self.prev_kp, self.prev_des = kp, des
            return np.eye(3), np.zeros((3, 1)), len(good)   # tracking weak

        pts_prev = np.float32([self.prev_kp[m.queryIdx].pt for m in good])
        pts_cur = np.float32([kp[m.trainIdx].pt for m in good])

        E, mask = cv2.findEssentialMat(
            pts_prev, pts_cur, self.K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None or E.shape != (3, 3):
            self.prev_kp, self.prev_des = kp, des
            return np.eye(3), np.zeros((3, 1)), 0

        n_inliers, R_rel, t_rel, _ = cv2.recoverPose(E, pts_prev, pts_cur, self.K, mask=mask)

        # Accumulate global pose. Translation is UP TO SCALE (monocular ambiguity):
        # t_rel is a unit vector; without an external scale (wheel odom, IMU, known
        # baseline) the absolute distance is unknown. Document this in your README.
        self.t_global = self.t_global + self.R_global @ t_rel
        self.R_global = R_rel @ self.R_global

        self.prev_kp, self.prev_des = kp, des
        return R_rel, t_rel, n_inliers
```

> **The scale ambiguity is not a bug — it's the physics.** A monocular camera cannot distinguish a small nearby motion from a large far one; the translation it recovers is a *direction*, not a distance. Real systems fix scale by fusing wheel odometry, IMU, or a known object size. Your README **must** document this; pretending monocular VO gives metric translation is the classic beginner error.

---

## Deliverable 2 — `vo_node.py` (the ROS2 node)

A thin `rclpy` node that:

1. Subscribes to `/camera/camera_info` (latched-style; grab `K` from the first message — it's the Week 5 lesson that `camera_info` is the metadata every consumer needs).
2. Subscribes to `/camera/image_raw` with a sensor QoS (`BEST_EFFORT` — it's a camera stream; Week 5). Converts each `sensor_msgs/Image` to a grayscale NumPy array with `cv_bridge`.
3. Feeds each frame to `MonocularVO.process_frame`, accumulates the trajectory, and publishes:
   - `/vo/path` (`nav_msgs/Path`) — the accumulated trajectory in a `camera_odom` frame, every pose honestly stamped (Week 5: acquisition-time stamp from the image header, not publish time).
   - `/vo/pose` (`geometry_msgs/PoseStamped`) — the current pose.
   - `/vo/inliers` (`std_msgs/Int32` or a diagnostics message) — the per-frame inlier count, so an operator sees tracking quality.
4. Logs a warning when the inlier count drops below a threshold (tracking degrading — a textureless wall, motion blur).

The node must **not** import OpenCV's geometry directly beyond `cv_bridge` conversion — it talks to `MonocularVO`. Carry the image's acquisition stamp through to every published pose.

---

## Deliverable 3 — the demo and tests

- **`demo_pairs.py`** — generate a textured scene and warp it by a *known* camera motion (a pure rotation, then a pure forward translation), so you have ground truth to test the recovered `R, t` against. Reuse the Exercise 2 scene generator.
- **`test_vo_geometry.py`** — `pytest`: feed `MonocularVO` a known pure-rotation pair and assert the recovered `R` matches (within a degree or two); feed a forward-translation pair and assert the recovered translation *direction* matches (sign and dominant axis).
- **`test_vo_degenerate.py`** — feed a *textureless* pair (a flat gray image) and assert the core returns a low inlier count and the "tracking lost" signal **without crashing**. Graceful degradation on bad input is a deployment requirement, not a nicety.

---

## Rules

- **You may** read the OpenCV docs, the ORB-SLAM3 source for inspiration, and the lecture notes.
- **You must not** import `cv2` anywhere except `vo_core.py` and `demo_pairs.py` (and tests). The node does `cv_bridge` conversion only and talks to `MonocularVO`. If `grep -rn "import cv2" --include=*.py | grep -vE "vo_core|demo_pairs|test"` returns the node, you've broken the layering.
- **You must not** claim metric translation from monocular VO. The README documents the scale ambiguity.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy, `opencv-python`, `cv_bridge`.
- Every published pose carries `frame_id="camera_odom"` and the image's acquisition stamp.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-12-crunch-vo-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_vo` succeeds with no warnings.
- [ ] `vo_core.py` implements `process_frame` returning `(R_rel, t_rel, n_inliers)` and degrades gracefully on too-few-matches.
- [ ] `grep -rn "import cv2" --include=*.py` finds matches **only** in `vo_core.py`, `demo_pairs.py`, and tests — not in `vo_node.py`.
- [ ] `colcon test --packages-select crunch_vo` passes: a known rotation/translation is recovered; a textureless pair is flagged, not crashed.
- [ ] Running `vo.launch.py` against a moving camera (real or Gz Sim) publishes `/vo/path`; rviz2's Path display shows the camera trajectory growing as the camera moves.
- [ ] The README documents the **monocular scale ambiguity** explicitly and shows how you'd recover scale (fuse wheel odom / IMU).
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **VO geometry correctness** | 25 | ORB → ratio test → RANSAC essential matrix → `recoverPose` is correct; the global pose accumulates right; known synthetic motions are recovered. |
| **Layering discipline** | 15 | The `grep` check is clean; `vo_node` does only `cv_bridge` + `MonocularVO`; the core is reusable and ROS-free. |
| **Graceful degradation** | 15 | Too-few-matches and textureless frames return a flag, never crash; the inlier count is published; a warning fires on weak tracking. |
| **Scale-ambiguity honesty** | 15 | The README correctly explains why monocular translation is up-to-scale and how to recover scale; no false metric claims. |
| **ROS node plumbing** | 15 | `camera_info` → `K`; sensor QoS on the image; poses stamped at acquisition time in `camera_odom`; `/vo/path` published. |
| **Tests & demo** | 15 | Geometry and degeneracy tests pass; the demo shows a recovered trajectory; README has a screenshot and the run commands. |

**90+** is portfolio-grade and ready to feed the Week 16 perception graph. **70–89** works but has a coupling leak or a missing degeneracy guard. **Below 70** means the geometry is wrong or the node crashes on bad input — fix that first.

---

## Stretch goals

- **Fuse scale from wheel odometry.** Subscribe to `/odom`, take its per-frame translation magnitude, and scale the VO translation to metric. Now your VO trajectory is metric and comparable to wheel odometry — and you can see VO catch a wheel slip (the Challenge 1 idea, inside the node).
- **Feed the pose-graph back end.** Emit each frame-to-frame `R, t` as a between factor into the Week 11 `crunch_posegraph` backend. You now have a (tiny) visual-SLAM front-end + back-end pair.
- **Swap ORB for SuperPoint+LightGlue.** On a hard sequence (low texture, big motion) where ORB tracking drops out, swap in the learned front-end and compare the inlier counts and trajectory continuity. This is the literal Week 12 → Week 13 bridge.
- **Keyframe selection.** Only run VO between *keyframes* (frames with enough parallax), not every frame — the standard trick to reduce drift and compute. Document the drift improvement.

---

## How this connects to the rest of C24

- **Week 13 (learned perception)** replaces the ORB *tile* with a learned front-end; the RANSAC + `recoverPose` geometry stays. Your node is the place to A/B them.
- **Week 15 (3D perception)** registers point clouds with ICP to get relative transforms — the LiDAR analogue of this camera VO. Both feed the same pose-graph back end.
- **Week 16 (Phase 2 midterm)** fuses VO + wheel odom + IMU + LiDAR into one drift-bounded estimate. Your VO is one honest input to that fusion, with its scale recovered from the others.

When you've finished, push the repo and take the [quiz](../05-quiz.md).
