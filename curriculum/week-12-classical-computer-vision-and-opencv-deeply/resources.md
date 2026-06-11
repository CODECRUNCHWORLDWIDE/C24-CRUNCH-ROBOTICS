# Week 12 — Resources

Every resource here is **free**. OpenCV's docs and tutorials are open. Szeliski's *Computer Vision: Algorithms and Applications* (2nd ed.) is posted free by the author. The OpenCV calibration and feature tutorials are the official source of truth. No paywalled books are required.

OpenCV's Python API is stable across the 4.x line; we pin examples to **OpenCV 4.x** (`pip install opencv-python`). The concepts are version-independent; only occasional function signatures move between minor versions.

## Required reading (work it into your week)

- **Szeliski — *Computer Vision: Algorithms and Applications*, 2nd ed. (free PDF from the author).** The standard reference. Read Ch. 2 (image formation), Ch. 7 (feature detection/matching), Ch. 9 (motion/optical flow), Ch. 12 (stereo) as you hit each topic:
  <https://szeliski.org/Book/>
- **OpenCV — Camera Calibration tutorial** — the canonical `findChessboardCorners` → `calibrateCamera` → `undistort` walkthrough you'll follow in Exercise 1:
  <https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html>
- **OpenCV — ORB (Oriented FAST and Rotated BRIEF)** — the feature you'll use in Exercise 2 and the mini-project:
  <https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html>
- **OpenCV — Lucas-Kanade Optical Flow** — `calcOpticalFlowPyrLK`, the brightness-constancy assumption, the pyramid:
  <https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html>

## The geometry references (skim, return as needed)

- **OpenCV — Camera calibration and 3D reconstruction (the `calib3d` module overview)** — the pinhole model, the projection equations, the distortion model, all in OpenCV's exact notation:
  <https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html>
- **OpenCV — Epipolar Geometry** — the fundamental/essential matrix, the epipolar constraint, for stereo and visual odometry:
  <https://docs.opencv.org/4.x/da/de9/tutorial_py_epipolar_geometry.html>
- **OpenCV — Depth Map from Stereo Images** — `StereoBM`/`StereoSGBM`, disparity, `depth = f·b/d`:
  <https://docs.opencv.org/4.x/dd/d53/tutorial_py_depthmap.html>
- **Hartley & Zisserman — *Multiple View Geometry* (the bible; chapter notes and errata posted free).** Reach for it when you want the rigorous derivation behind an OpenCV function:
  <https://www.robots.ox.ac.uk/~vgg/hzbook/>

## The classic papers (one read each)

- **Lucas & Kanade — "An Iterative Image Registration Technique" (1981).** The optical-flow method you implement:
  <https://www.ri.cmu.edu/pub_files/pub3/lucas_bruce_d_1981_2/lucas_bruce_d_1981_2.pdf>
- **Fischler & Bolles — "Random Sample Consensus" (1981).** RANSAC, the original robust-estimation algorithm:
  <https://www.sri.com/wp-content/uploads/2021/12/ransac-publication.pdf>
- **Rublee et al. — "ORB: an efficient alternative to SIFT or SURF" (2011).** Why ORB is fast, binary, and good enough:
  <https://www.gwylab.com/download/ORB_2012.pdf>

## The 2026-current learned front-ends (read for next week's bridge)

- **DeTone et al. — "SuperPoint" + Lindenberger et al. — "LightGlue."** The learned detector+matcher that beats ORB on hard data; the stretch goal uses them:
  <https://github.com/cvg/LightGlue>
- **ORB-SLAM3 (the system where classical ORB still anchors a SOTA SLAM stack in 2026):**
  <https://github.com/UZ-SLAMLab/ORB_SLAM3>

## ROS2 vision integration

- **`cv_bridge`** — converting between `sensor_msgs/Image` and OpenCV `cv::Mat` / NumPy arrays (Python and C++):
  <https://docs.ros.org/en/jazzy/p/cv_bridge/>
- **`image_pipeline` / `camera_calibration`** — the ROS2 calibration GUI that wraps OpenCV calibration for a live camera:
  <https://docs.ros.org/en/jazzy/p/camera_calibration/>
- **`image_proc`** — the node that consumes `camera_info` and publishes rectified/undistorted images on a robot:
  <https://docs.ros.org/en/jazzy/p/image_proc/>

## Talks worth your time (free, no signup)

- **First Principles of Computer Vision (Shree Nayar, Columbia)** — the best free lecture series on image formation, features, and stereo, beautifully animated:
  <https://www.youtube.com/@firstprinciplesofcomputerv3258>
- **Cyrill Stachniss — Photogrammetry & Robotics lectures (camera model, calibration, features, epipolar geometry)** — rigorous and robotics-flavored:
  <https://www.youtube.com/@CyrillStachniss>
- **OpenCV official channel / ROSCon perception sessions** — calibration and feature-matching walkthroughs:
  <https://www.youtube.com/@OpenCV_Official>

## Tools you'll use this week

- **`opencv-python`** — `pip install opencv-python` (or `opencv-python-headless` on a server). The whole week.
- **`numpy`** — images are arrays; calibration math is matrix math.
- **`matplotlib`** — plot the flow field, the disparity map, the calibration reprojection residuals.
- **A checkerboard** — print a 9×6 (inner-corner) checkerboard, or use the Gz Sim textured plane. Measure the square size in meters; calibration needs it for metric scale.
- **`cv_bridge`** (ROS side) — `sudo apt install ros-jazzy-cv-bridge`.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Pinhole model** | The geometric model of a camera: 3D point → ray → pixel through a single center of projection. |
| **Intrinsics (K)** | The camera's internal matrix: focal lengths `fx, fy` and principal point `cx, cy`. |
| **Extrinsics ([R\|t])** | The camera's pose in the world: rotation `R` and translation `t`. |
| **Distortion coeffs** | `[k1, k2, p1, p2, k3]`: radial (`k`) and tangential (`p`) lens distortion. |
| **Reprojection error** | Mean pixel distance between detected corners and re-projected 3D points; the calibration quality metric. |
| **Undistortion** | Warping an image to remove lens distortion so straight lines stay straight. |
| **Corner** | A point with strong gradient in two directions (Harris/Shi-Tomasi); a good feature to track. |
| **ORB** | Oriented FAST keypoints + rotated BRIEF binary descriptors; fast, rotation-aware, no GPU. |
| **Descriptor** | A vector (float for SIFT, binary for ORB) summarizing the patch around a keypoint for matching. |
| **Lowe's ratio test** | Keep a match only if the best descriptor distance is much smaller than the second-best. |
| **RANSAC** | Random Sample Consensus: fit a model from minimal samples, count inliers, keep the best — outlier-robust. |
| **Homography** | A 3×3 projective map between two views of a *plane*; estimated robustly with RANSAC. |
| **Fundamental / essential matrix** | The 3×3 matrix encoding the epipolar geometry between two views (essential = calibrated). |
| **Optical flow** | The apparent motion of brightness patterns between frames; Lucas-Kanade is the sparse classic. |
| **Brightness constancy** | The assumption that a moving point keeps its intensity; the basis of optical flow. |
| **Disparity** | The horizontal pixel shift of a point between left and right rectified stereo images. |
| **Baseline (b)** | The distance between the two cameras of a stereo rig; `depth = f·b/disparity`. |

---

*If a link 404s, please open an issue so we can replace it.*
