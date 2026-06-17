# Week 14 — Resources

Every resource here is **free** and pinned to **ROS2 Jazzy** (the LTS we run on Ubuntu 24.04) wherever the docs are versioned. The Intel RealSense SDK and ROS2 wrapper are open. The OAK-D / DepthAI docs and the Azure Kinect SDK docs are public. The stereo-geometry material is from open courseware and the OpenCV docs. No paywalled books are linked.

If you are on Path B (no physical camera), every "driver" link below still matters for understanding the topic family — the simulated Gz Sim RGB-D camera publishes the *same* `sensor_msgs/Image` + `CameraInfo` topics, so the projection and filtering concepts transfer one-to-one.

## Required reading (work it into your week)

- **Intel RealSense ROS2 wrapper (`realsense-ros`)** — the driver you bring up in Exercise 1. Read the topic table and the launch arguments (`align_depth`, `enable_sync`, `pointcloud.enable`):
  <https://github.com/IntelRealSense/realsense-ros>
- **`image_pipeline` / `depth_image_proc`** — the ROS2 node that turns a depth image + `CameraInfo` into a `PointCloud2`. This is the production version of what you hand-roll in Exercise 2:
  <https://github.com/ros-perception/image_pipeline/tree/rolling/depth_image_proc>
- **`message_filters` — time synchronizers** — `ApproximateTimeSynchronizer`, the slop parameter, and the `ExactTime` vs `ApproximateTime` distinction you need for color+depth:
  <https://docs.ros.org/en/jazzy/p/message_filters/>
- **OpenCV — Depth Map from Stereo Images** — disparity, the block matcher, and the `Z = f·B / d` relationship in code:
  <https://docs.opencv.org/4.x/dd/d53/tutorial_py_depthmap.html>
- **REP 103 / REP 105 — units and frames** — the optical-frame-vs-body-frame convention. A depth camera publishes in `*_optical_frame` (z-forward, x-right, y-down); your robot body is x-forward, z-up. Get this wrong and the cloud is sideways:
  <https://www.ros.org/reps/rep-0103.html> and <https://www.ros.org/reps/rep-0105.html>

## Stereo geometry and depth (the theory, skim then refer)

- **Szeliski, *Computer Vision: Algorithms and Applications*, 2nd ed. (free PDF)** — Chapter 12 (stereo) and Chapter 11 (depth from triangulation). The canonical, openly-available reference:
  <https://szeliski.org/Book/>
- **Hartley & Zisserman, *Multiple View Geometry*** — epipolar geometry and the fundamental/essential matrices. Reference, not cover-to-cover:
  the chapter on epipolar geometry is widely mirrored; search "Hartley Zisserman epipolar geometry chapter".
- **Intel — "Tuning depth cameras for best performance" (white paper)** — the single best free document on *why* a RealSense depth image looks the way it does, and how the post-processing filters change it:
  <https://dev.intelrealsense.com/docs/tuning-depth-cameras-for-best-performance>
- **Intel — "Depth post-processing for Intel RealSense D400 cameras"** — decimation, spatial, temporal, hole-filling, explained by the people who wrote them:
  <https://dev.intelrealsense.com/docs/depth-post-processing>

## The cameras of 2026 (driver + datasheet per device)

- **Intel RealSense D435i / D455** — active stereo + IMU; the workhorse of academic robotics. Datasheet (range, FOV, depth accuracy spec):
  <https://www.intelrealsense.com/depth-camera-d435i/>
- **Luxonis OAK-D (DepthAI)** — stereo + on-camera inference; the ROS2 driver `depthai-ros`:
  <https://github.com/luxonis/depthai-ros>
- **Microsoft Azure Kinect DK** — time-of-flight; the SDK and the ROS2 driver. ToF physics differs from stereo — read this if your scene is indoors and textureless:
  <https://learn.microsoft.com/en-us/azure/kinect-dk/>
- **Stereolabs ZED** — passive stereo + neural depth; the ZED ROS2 wrapper. Useful contrast: neural depth fills the textureless surfaces that classical stereo drops:
  <https://www.stereolabs.com/docs/ros2/>

## Simulation (Path B — no physical camera)

- **Gz Sim RGB-D / depth camera sensor** — the simulated camera that publishes the same ROS2 topic family. Add it to your week-3 robot's URDF:
  <https://gazebosim.org/docs/harmonic/sensors/>
- **`ros_gz` image bridge** — bridging the simulated `image` and `camera_info` topics into ROS2:
  <https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_image>
- **A recorded RealSense rosbag (for projection/filter practice without a camera or sim)** — the ROS2 tutorials and the realsense-ros repo link sample bags; search the realsense-ros issues/wiki for "rosbag sample" to find a current mirror.

## Visualization

- **Foxglove — 3D panel and image panels** — the dashboard you use this week to view the point cloud and the depth image side by side, with the confidence overlay:
  <https://docs.foxglove.dev/docs/visualization/panels/3d>
- **rviz2 — PointCloud2 and DepthCloud displays** — the in-ROS viewer; the `DepthCloud` display projects depth+RGB live:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html>

## Tools you'll use this week

- **`ros2 topic info -v`** — confirm the depth/color/IMU streams have the QoS you expect (sensor profile, `BEST_EFFORT`).
- **`ros2 topic echo /camera/depth/camera_info`** — read the intrinsics `K = [fx 0 cx; 0 fy cy; 0 0 1]` you back-project with.
- **`ros2 run image_view image_view --ros-args -r image:=/camera/depth/image_rect_raw`** — quick-look the depth image (it'll look dark; depth in mm scaled to 8-bit is faint — that's normal).
- **`rs-enumerate-devices`** (RealSense SDK) — confirm the camera is seen, the firmware version, and the supported stream profiles.
- **`realsense-viewer`** (RealSense SDK) — the vendor GUI; toggle the post-processing filters here first to build intuition before you do it in ROS2.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Disparity** | `d = x_left − x_right`: how far a point shifts between the two rectified stereo images. Larger disparity = closer. |
| **Baseline (B)** | The distance between the two stereo cameras' optical centres. Larger baseline = better far-range depth. |
| **`Z = f·B / d`** | The depth equation. Depth is inversely proportional to disparity. |
| **`Z²` error law** | Depth error grows with the square of distance, because depth depends on `1/d`. |
| **Active stereo** | Stereo plus a projected IR pattern, so blank walls get texture to match. The RealSense D4xx trick. |
| **Structured light** | A known projected pattern; depth from the pattern's deformation. The original Kinect. |
| **Time-of-flight (ToF)** | Measure the photon round-trip time. The Azure Kinect. Different failure modes than stereo. |
| **Intrinsics `(fx, fy, cx, cy)`** | Focal lengths and principal point; the camera matrix `K`. What you back-project depth with. |
| **Back-projection** | `X = (u−cx)·Z/fx`, `Y = (v−cy)·Z/fy`: pixel + depth → 3D point. |
| **Optical frame** | The camera's z-forward/x-right/y-down frame (REP 103). Rotated ~90° from the body frame. |
| **Aligned depth** | Depth resampled into the *color* camera's frame so RGB and depth pixels correspond. |
| **Flying pixels** | Spurious points at depth discontinuities (object edges), floating between foreground and background. |
| **Invalid pixel** | No valid depth: `0` in `16UC1` (mm), `NaN` in `32FC1` (m). Not "zero distance" — "no measurement." |
| **`16UC1` vs `32FC1`** | Depth encodings: 16-bit unsigned millimetres vs 32-bit float metres. Mixing them up is a 1000× unit bug. |
| **Temporal filter** | An exponential moving average across frames; reduces noise on static scenes, smears moving ones. |
| **Confidence/validity map** | Per-pixel "do I trust this depth?" Read it before you trust the depth. |

---

*If a link 404s, please open an issue so we can replace it.*
