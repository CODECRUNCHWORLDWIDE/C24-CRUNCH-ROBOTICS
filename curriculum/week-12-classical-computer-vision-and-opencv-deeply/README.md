# Week 12 — Classical Computer Vision and OpenCV, Deeply

Next week you start bolting learned models onto your robot — YOLO, SAM, Depth-Anything. This week is the floor those models stand on. Before a neural network ever sees a pixel, something turned photons into a stamped, undistorted, metrically-meaningful image, and something has to relate that image to the 3D world the robot lives in. That something is classical computer vision, and it did not go away when deep learning arrived — it became the substrate. ORB-SLAM3 still tracks ORB features. Visual-inertial odometry still runs Lucas-Kanade. Every learned depth model is still calibrated against a pinhole camera model you have to understand to interpret its output. RANSAC — a 1981 algorithm — is still how you reject the outliers a learned matcher produces.

This week you build that substrate by hand. You start at image formation and the pinhole camera model, calibrate a real (or simulated) camera until you can map pixels to rays and back, and learn what camera distortion is and how to undo it. Then you meet the feature pipeline that anchors classical visual odometry and SLAM: corners, descriptors (ORB up close, SIFT and the learned SuperPoint at a glance), and the matching that turns two images into a geometric relationship. You implement Lucas-Kanade optical flow and use it to *estimate the robot's forward velocity from a video alone* — a sanity check against wheel odometry that costs nothing and catches a wheel-slip bug a learned model never would. You learn stereo geometry well enough to turn a disparity into a depth. And threaded through all of it: RANSAC, the robust-estimation idea you already met as the Huber kernel in the Week 11 pose graph, here in its original form.

The one sentence to carry into the week, straight from the lecture title:

> **Classical CV did not go away. It is the floor under your learned model.** ORB features still anchor ORB-SLAM3; RANSAC still rejects the matches your neural net got wrong; the pinhole model still turns every pixel your detector fires on into a ray in the world. Learn the floor and the learned models stop being magic.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the pinhole camera model: the intrinsic matrix `K` (focal lengths, principal point), the extrinsics `[R | t]`, the full projection `p = K [R | t] X`, and the back-projection of a pixel to a ray — and explain why a calibrated camera is a *measurement device*, not a picture-taker.
- **Calibrate** a real USB camera (or a Gz Sim camera) with a checkerboard in OpenCV: collect views, run `cv2.calibrateCamera`, recover `K` and the distortion coefficients, read the reprojection error as a quality metric, and undistort an image.
- **Explain** radial and tangential distortion, why a wide-angle lens bends straight lines, and what the distortion coefficients `[k1, k2, p1, p2, k3]` each do.
- **Detect and describe** features: Harris/Shi-Tomasi corners, ORB keypoints and binary descriptors, and articulate where SIFT and the learned SuperPoint/LightGlue front-ends fit in 2026 — and why ORB-SLAM3 still uses ORB.
- **Match** descriptors with a brute-force or FLANN matcher, apply Lowe's ratio test, and reject the surviving outliers with RANSAC on a fundamental/homography model.
- **Implement** Lucas-Kanade optical flow (`cv2.calcOpticalFlowPyrLK`), visualize the flow field, and *estimate forward velocity from flow alone*, then compare it to wheel odometry as an independent sanity check.
- **Compute** stereo depth: the epipolar geometry, disparity, and the `depth = f · baseline / disparity` relationship — and state where stereo fails (textureless walls, repeated patterns, occlusion).
- **Apply** RANSAC as a general robust-estimation tool: fit a model to data with gross outliers (a homography, a line, a fundamental matrix) and recover the inliers — the same idea as the Week 11 robust kernel, in its original geometric form.

## Prerequisites

This week assumes you have completed **C24 weeks 1–11**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or container / WSL2), and the **Week 3 robot** with a camera. If your diff-drive URDF doesn't have a camera plugin yet, add one this week — the calibration and optical-flow labs need `/camera/image_raw` and `/camera/camera_info`.
- **Python + NumPy** fluency, and `pip install opencv-python` working. We use OpenCV's Python bindings throughout; the concepts transfer one-to-one to `rclcpp` + `cv_bridge` for the C++ side.
- **Linear algebra** from Phase 1: matrix multiplication, homogeneous coordinates, what a `3×3` rotation and a `3×1` translation mean. The projection equation is just matrix algebra in homogeneous coordinates.
- The **Week 11 robust-estimation intuition**: you used a Huber kernel to reject an outlier loop closure. RANSAC is the same idea (down-weight/discard the data that doesn't fit the model) in a different, sampling-based form. We lean on that connection.
- Comfortable reading an image as a NumPy array (`H × W × 3`, BGR in OpenCV), and the basic image ops (grayscale conversion, resize, drawing).

You do **not** need prior computer-vision coursework. We start at "what is a pixel, geometrically" and build to stereo depth. If you've only ever used a camera as a thing that produces a JPEG, this is the week it becomes a calibrated sensor.

## Topics covered

- **Image formation and the pinhole camera model**: the camera obscura, the image plane, the focal length, the principal point; the intrinsic matrix `K`; homogeneous coordinates and the projection `p ∼ K [R | t] X`; back-projecting a pixel to a 3D ray.
- **Camera calibration**: the checkerboard target, `cv2.findChessboardCorners` + `cv2.cornerSubPix`, `cv2.calibrateCamera`, interpreting the returned `K` and `distCoeffs`, the **reprojection error** as the one-number quality metric, and `cv2.undistort` / `cv2.initUndistortRectifyMap`.
- **Lens distortion**: radial (`k1, k2, k3`) and tangential (`p1, p2`) distortion, the barrel/pincushion picture, why fisheye needs its own model, and the visual test (do straight lines stay straight after undistortion?).
- **Features and descriptors**: gradients, the Harris corner response, Shi-Tomasi (`goodFeaturesToTrack`); **ORB** (FAST keypoints + BRIEF binary descriptors, rotation-aware), SIFT as the float-descriptor classic, and a 2026-honest note on **SuperPoint + LightGlue** as the learned front-ends that beat ORB on hard data — and where ORB still wins (speed, no GPU, ORB-SLAM3).
- **Feature matching and robust geometry**: brute-force vs. FLANN matching, the Hamming distance for binary descriptors, **Lowe's ratio test**, the fundamental and essential matrices, the homography, and **RANSAC** (`cv2.findHomography(..., cv2.RANSAC)`, `cv2.findEssentialMat`) for outlier-robust model fitting.
- **Optical flow**: the brightness-constancy assumption and the aperture problem; **Lucas-Kanade** sparse flow (`cv2.calcOpticalFlowPyrLK`) with image pyramids; dense Farnebäck flow at a glance; estimating ego-motion (forward velocity) from the flow field and comparing it to wheel odometry.
- **Stereo geometry and depth**: the epipolar constraint, rectification, **disparity** (`cv2.StereoBM` / `cv2.StereoSGBM`), the `depth = f · b / d` relationship, and the failure modes (low texture, repetition, occlusion) that motivate next week's learned and active-depth approaches.
- **The classical-CV-as-substrate thesis**: where each piece reappears in a modern stack — ORB in ORB-SLAM3, LK in VIO, the pinhole model under every learned depth estimator, RANSAC under every learned matcher — so you read next week's learned perception as built *on* this floor, not replacing it.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                    | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Pinhole model; intrinsics; distortion; calibration       |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Calibrate a camera; undistort; exercise 1                |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Corners, ORB, matching, RANSAC; exercise 2               |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Optical flow; velocity from flow; stereo depth           |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Flow-odometry vs wheel odometry; mini-project deep work   |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                   |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, writeup polish                             |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                          | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The OpenCV docs, the Szeliski textbook, the calibration tutorials, and the talks worth your time |
| [lecture-notes/01-pinhole-calibration-and-distortion.md](./lecture-notes/01-pinhole-calibration-and-distortion.md) | Image formation, the pinhole model, intrinsics/extrinsics, calibration, and distortion |
| [lecture-notes/02-features-flow-and-stereo.md](./lecture-notes/02-features-flow-and-stereo.md) | Corners, ORB, matching + RANSAC, Lucas-Kanade flow, ego-motion from flow, and stereo depth |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-calibrate-a-camera.md](./exercises/exercise-01-calibrate-a-camera.md) | Calibrate a real or Gz Sim camera, read the reprojection error, undistort an image |
| [exercises/exercise-02-orb-match-ransac.py](./exercises/exercise-02-orb-match-ransac.py) | Detect ORB features, match two views, reject outliers with RANSAC, count inliers |
| [exercises/exercise-03-lk-flow-velocity.py](./exercises/exercise-03-lk-flow-velocity.py) | Lucas-Kanade flow on a synthetic drive; estimate forward velocity from flow |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-flow-vs-wheel-odometry.md](./challenges/challenge-01-flow-vs-wheel-odometry.md) | Estimate velocity from optical flow on a drive video and diagnose a planted wheel-slip event |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the calibration-quality writeup |
| [mini-project/README.md](./mini-project/README.md) | A ROS2 monocular visual-odometry node: ORB + matching + RANSAC essential matrix → pose delta |

## The "the geometry closed" promise

C24 uses a recurring marker for every vision lab that ends in a believable geometric answer. For calibration it is a low, honest reprojection error:

```
calibrated 14 views. K = [[612.3, 0, 318.9], [0, 611.8, 241.2], [0, 0, 1]]
mean reprojection error: 0.27 px   ->  GOOD (< 0.5 px)
```

For matching it is a healthy inlier ratio after RANSAC:

```
ORB matches: 412  ->  after Lowe ratio: 188  ->  RANSAC inliers: 171 (91%)
```

A reprojection error of 3 pixels means your calibration is wrong (bad views, a mis-sized board, a moving target) — and every downstream measurement built on it is wrong too. A RANSAC inlier ratio of 15% means your matches are mostly noise and the recovered geometry is meaningless. The point of Week 12 is to make those *good* numbers ordinary, and to make a *bad* number loud — because a quietly-miscalibrated camera corrupts your whole perception stack three weeks later.

## Stretch goals

If you finish the regular work early and want to push further:

- Swap ORB for the learned **SuperPoint + LightGlue** front-end (there are permissively-licensed ONNX exports) on a hard image pair — low texture, big viewpoint change — where ORB struggles, and compare inlier counts. This previews next week's learned perception and shows you *why* the field moved.
- Recover the **essential matrix** from your matched ORB features (`cv2.findEssentialMat` + `cv2.recoverPose`) and get a *relative camera rotation+translation (up to scale)* between two frames — that's monocular visual odometry, the mini-project in miniature.
- Calibrate a **fisheye** lens with `cv2.fisheye.calibrate` and compare the undistortion to the standard model. Wide-FOV cameras are everywhere on robots; the standard model fails on them.
- Run **dense Farnebäck flow** alongside the sparse LK flow on the same video and compare the ego-motion estimate. Dense is slower but fills textureless regions where sparse LK has nothing to track.

## Up next

Week 13 takes this floor and builds learned 2D perception on top: YOLO, DETR, SAM, Depth-Anything, exported to ONNX and TensorRT and deployed as a ROS2 inference node inside a latency budget. Every one of those models outputs pixels you'll relate to the world with the pinhole model you calibrated here, and a chunk of them you'll make robust with the RANSAC you learned here. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
