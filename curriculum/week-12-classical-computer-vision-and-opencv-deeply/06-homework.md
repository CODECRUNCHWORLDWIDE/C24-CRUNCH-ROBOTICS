# Week 12 Homework

Six problems that drive classical CV into your fingers. The full set should take about **5 hours**. Work in your Week 12 Git repository (the same workspace as the exercises and the `crunch_vo` mini-project) so every problem produces at least one commit you can point to at the Phase 2 midterm in Week 16.

The headline deliverable is **Problem 4 — the calibration-quality writeup**, the artifact a reviewer reads to decide whether your camera is a measurement device they can trust. Treat it as an engineering report, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**. Install OpenCV once: `pip install opencv-python numpy matplotlib`. Problems 1–2 want a real or Gz Sim camera.

---

## Problem 1 — Calibrate, then break the calibration on purpose

**Problem statement.** Calibrate your camera (Exercise 1) to a good reprojection error (< 0.5 px). Then *deliberately* recalibrate two bad ways: (a) with only 5 frontal, centered views; (b) with the wrong square size (claim 50 mm when it's 25 mm). Record the `K`, distortion, and reprojection error for all three runs in `notes/week-12/calibration-runs.md`.

**Acceptance criteria.**

- Three calibration runs recorded: good, too-few-views, wrong-square-size.
- You correctly note that the wrong-square-size run gives a *fine* reprojection error and a *fine* `K` but wrong metric extrinsics (translations off by the size ratio) — reprojection error does *not* catch a scale error.
- You note that the too-few-views run has poorly-constrained distortion (and likely higher reprojection error).
- Committed.

**Hint.** Reprojection error measures *self-consistency* of the model against the detected corners — it can't tell you the board was actually a different size. That's why metric scale is a separate failure mode you check by measuring a known distance in the world. This subtlety is exactly what the Problem 4 writeup should call out.

**Estimated time.** 45 minutes.

---

## Problem 2 — Back-project a detection to a ray and onto the ground plane

**Problem statement.** Using your calibrated `K`, take a pixel (e.g. the center of a bounding box, or just click a point in an image), back-project it to a ray (Lecture 1 §2.1), and intersect that ray with the ground plane (assume the camera height and tilt are known, or use a flat `z=0` plane in the camera frame for simplicity) to get a 3D point. Verify the geometry on a known target.

**Acceptance criteria.**

- A script that back-projects a chosen pixel to a unit ray and intersects it with a ground plane to produce a 3D point.
- A sanity check: a pixel at the principal point gives a ray ≈ `(0,0,1)`; a target at a known real-world distance back-projects to approximately that distance.
- `notes/week-12/backproject.md` records the math and one worked example.
- Committed.

**Hint.** The ground-plane intersection is: given ray direction `d` and camera height `h` over a plane with normal `n`, the point is `t·d` where `t = h / (n·d)` (with appropriate signs for your frame convention). Get the convention right on a known target before trusting it — this is the operation that turns a Week 13 detection into a reachable 3D point.

**Estimated time.** 50 minutes.

---

## Problem 3 — ORB vs SIFT on a hard pair

**Problem statement.** Take two images of the same scene with a *large* viewpoint change (rotate the camera 30°+, or move it a meter). Run ORB and SIFT on both, match each with the ratio test + RANSAC, and compare inlier counts and the recovered homography quality. Report which front-end held up.

**Acceptance criteria.**

- A script that runs both ORB and SIFT (`cv2.SIFT_create`) on the same hard pair, with the ratio test + RANSAC for each.
- `notes/week-12/orb-vs-sift.md` reports the inlier counts and a one-paragraph verdict: on a hard viewpoint change, SIFT usually keeps more inliers (more robust descriptor) but is slower; ORB is faster. State the trade-off in terms of the *latency budget* you'll formalize next week.
- Committed.

**Hint.** Make the pair genuinely hard — a small rotation won't separate them. The point is to *feel* where ORB starts to lose, which is exactly the regime where the learned SuperPoint+LightGlue front-end (and next week's whole topic) earns its compute.

**Estimated time.** 45 minutes.

---

## Problem 4 — The calibration-quality writeup (headline deliverable)

**Problem statement.** Write a one-page engineering report at `notes/week-12/calibration-quality.md` that a teammate could use to decide whether to trust your camera as a measurement device. Cover:

1. **The calibration result** — your final `K`, distortion coefficients, and reprojection error, with the GOOD/OK/BAD band.
2. **What the reprojection error does and does not catch** — it measures model self-consistency; it does *not* catch a wrong square size (scale error) or a systematically biased target. (Use your Problem 1 findings.)
3. **The undistortion proof** — the straight-line test result on a known straight edge.
4. **The back-projection sanity check** — the principal-point ray ≈ `(0,0,1)` and a known-distance target check (Problem 2).
5. **A trust verdict** — would you let this camera's measurements drive a 3D reach for the arm? Why or why not?
6. **One process recommendation** — e.g. "every camera ships with its `camera_info`; `image_proc` rectifies before any geometry; recalibrate after any lens disturbance."

**Acceptance criteria.**

- `notes/week-12/calibration-quality.md` exists, fits on roughly one page (450–650 words), and hits all six headings.
- The "what reprojection error doesn't catch" section is *specific* (names the scale-error blind spot from Problem 1), not hand-wavy.
- The trust verdict is justified by evidence (the actual numbers), not vibes.
- Committed.

**Hint.** This is the camera analogue of the Week 5 QoS postmortem and the Week 11 filter-vs-smoother memo — a short, evidence-backed artifact a reviewer reads in two minutes to decide if your work is trustworthy. The Week 16 reviewer *will* ask "how do you know your camera is calibrated well enough?" Write the answer here.

**Estimated time.** 1 hour.

---

## Problem 5 — Velocity from flow on a real (or sim) drive

**Problem statement.** Record a short forward-drive clip from your robot's camera (or Gz Sim), run the Exercise 3 flow-velocity estimator on it, and compare the per-frame flow velocity to the robot's `/odom`. On a clean drive they should roughly agree; document the agreement and any divergence.

**Acceptance criteria.**

- A script that runs LK flow on the recorded frames and estimates per-frame forward velocity.
- `notes/week-12/flow-on-real-drive.md` with a plot or table of flow velocity vs `/odom` velocity over the clip, and a one-paragraph reading (do they agree? where do they diverge, and why?).
- You note the limitations honestly: flow velocity needs a known scene depth or ground-plane assumption, so it's approximate on a real cluttered scene.
- Committed.

**Hint.** On a real drive the scene isn't a clean fronto-parallel plane, so the radial-scale trick from Exercise 3 is rougher. Restrict the tracked features to the ground plane (lower image region) or just report the qualitative agreement. The point is to see flow and odometry track each other on real data — the foundation of the Challenge 1 slip-detector.

**Estimated time.** 45 minutes.

---

## Problem 6 — Stereo depth on a public pair

**Problem statement.** Take a rectified stereo pair (a public one from the Middlebury or KITTI stereo datasets, or a Gz Sim stereo rig), compute the disparity with `cv2.StereoSGBM`, convert it to metric depth with `depth = f·b/d`, and visualize the depth map. Identify where stereo fails on your pair.

**Acceptance criteria.**

- A script that computes disparity and converts to depth using the pair's known `f` and baseline `b`.
- `notes/week-12/stereo-depth.md` with the depth-map visualization and a labeled note of at least two failure regions (textureless area, repeated pattern, occlusion, or beyond-range), tying each to the Lecture 2 §5.1 failure modes.
- A spot-check: a point at a known distance in the scene gets approximately the right depth.
- Committed.

**Hint.** `StereoSGBM` outputs fixed-point disparity scaled by 16 — divide by 16 before the depth formula. Guard the divide-by-zero where disparity is 0 (no valid match). The failure regions you find are precisely why Week 14 (active depth) and Week 13 (learned depth) exist.

**Estimated time.** 35 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Calibrate, then break it | 45 min |
| 2 — Back-project to a ray + ground plane | 50 min |
| 3 — ORB vs SIFT on a hard pair | 45 min |
| 4 — Calibration-quality writeup (headline) | 1 h 0 min |
| 5 — Flow velocity on a real drive | 45 min |
| 6 — Stereo depth on a public pair | 35 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_vo` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 16 fuses its output. Then take the [quiz](./05-quiz.md) with your notes closed.
