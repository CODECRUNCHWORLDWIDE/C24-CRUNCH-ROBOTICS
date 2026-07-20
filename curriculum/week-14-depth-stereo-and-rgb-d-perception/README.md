# Week 14 — Depth, Stereo, and RGB-D Perception

Welcome to the week your robot grows a third dimension. For thirteen weeks it has lived in a flat world: a 2D LiDAR scan, an occupancy grid, a camera that sees color but not distance. This week you bolt a depth camera onto it and learn the uncomfortable truth that **every depth camera lies, and each one lies in a different way.** By Friday you will bring up a RealSense D435i (or a simulated equivalent) in ROS2, publish time-synchronized RGB + depth + IMU, project that depth into a metric point cloud using the camera intrinsics, visualize it in rviz2 and Foxglove, and be able to look at a depth confidence map and say exactly *where* the camera is making things up.

We assume you finished Week 13 — you have a YOLOv8 ROS2 inference node consuming `/camera/image_raw` and publishing `vision_msgs/Detection2DArray`, and you can read a TensorRT profile. We also assume the QoS literacy from Week 5 is in your fingers: a depth camera publishes three high-rate sensor streams, and if you subscribe to any of them with the default `RELIABLE` profile against a `BEST_EFFORT` publisher you will spend an afternoon convinced the camera is broken when it is your QoS. If that sentence didn't make you wince, re-read Week 5 before you start.

The one thing to internalize before you read another line: **a depth image is not a measurement of distance — it is the *output of a stereo or time-of-flight algorithm* that produces a distance estimate, complete with a noise model, a valid range, and systematic failure modes that depend on the surface, the lighting, and the geometry.** A glass door reads as infinite depth. A black absorptive surface reads as a hole. A repeating texture (a tiled floor, a brick wall) makes a stereo matcher hallucinate a plane that isn't there. The edge of an object smears depth across the discontinuity — "flying pixels" that float in space between the foreground and the background. A robot that trusts every depth pixel equally will plan a path into a glass wall it cannot see, or stop dead for a flying pixel that isn't an obstacle. This week is where you stop trusting the depth image and start *interrogating* it.

This is also the week perception stops being a single image and becomes a *registered, intrinsics-calibrated, metric 3D measurement* — the input to next week's point-cloud processing (Open3D, PCL, ICP) and, four weeks out, to the fused perception node you defend at the Week 16 midterm.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the stereo depth equation `Z = f·B / d` from similar triangles, and explain why depth precision degrades with the *square* of distance — and what that means for where you place a depth camera on a robot.
- **Distinguish** the three depth-sensing technologies in 2026 — passive/active stereo, structured light, and time-of-flight (ToF) — by their physics, their failure modes, and the surfaces that defeat each one.
- **Bring up** an Intel RealSense D435i (or a simulated RGB-D camera in Gz Sim) in ROS2 Jazzy, publishing color, depth, the camera-info intrinsics, and the on-board IMU, with the correct QoS on every stream.
- **Synchronize** color and depth (and IMU) across topics using `message_filters` `ApproximateTimeSynchronizer`, and explain why naïvely zipping the latest message of each topic injects timing error.
- **Project** a depth image into a metric point cloud, by hand, using the pinhole intrinsics `(fx, fy, cx, cy)` — and verify your hand-rolled cloud against `depth_image_proc`'s output.
- **Read** a depth confidence/validity map and identify, on a real scene, where the camera is reporting fabricated depth: glass, specular surfaces, black objects, textureless walls, and the flying pixels at depth discontinuities.
- **Apply** the depth post-processing filters that ship with the RealSense SDK — decimation, spatial (edge-preserving), temporal, and hole-filling — and quantify, with a metric, what each one costs and buys.
- **Align** depth to the color frame (and vice versa) using the extrinsics between the two cameras, and explain why an unaligned RGB-D point cloud paints color onto the wrong points.

## Prerequisites

This week assumes you have completed **C24 weeks 1–13**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04** (or the same in a container / WSL2). `ros2 --version` works; you can write an `rclpy` publisher and subscriber from memory.
- **Week 5 QoS literacy.** You can read `ros2 topic info -v`, you know `qos_profile_sensor_data` is `BEST_EFFORT`/`VOLATILE`/`KEEP_LAST(5)`, and you know why subscribing to a sensor stream with the default profile silently fails.
- **Week 12 camera model.** You calibrated a camera, you know the pinhole model and the intrinsics matrix `K`, and you know what radial/tangential distortion is. This week reuses `(fx, fy, cx, cy)` constantly — if "intrinsics" is fuzzy, re-read Week 12 §camera-model.
- **Week 2 tf2.** A depth camera publishes in an optical frame (`camera_color_optical_frame`), which is *rotated* relative to the robot body frame. You must be comfortable with the REP-103 optical-vs-body frame convention or every point cloud will appear sideways.
- **NumPy fluency.** The point-cloud projection is vectorized NumPy. A Python `for` loop over 300k pixels will run at 0.5 Hz and you will think the algorithm is wrong when it is just slow.

You do **not** need to own a depth camera. Every exercise has a **Path B** that runs against a simulated RGB-D camera in Gz Sim (the `gz::sim::systems::DepthCamera` / `RgbdCamera` sensor), or against a recorded `rosbag` of a RealSense stream that we point you to. The concepts — projection, synchronization, filtering, confidence — are identical; only the bring-up command changes.

## Topics covered

- **Stereo geometry.** Epipolar geometry, the rectified stereo pair, disparity `d = x_left − x_right`, the depth equation `Z = f·B / d`, the disparity-to-depth `Q` matrix, sub-pixel disparity, and why depth error grows as `Z²`.
- **The three depth technologies.** Passive stereo (two cameras, ambient light); active stereo (stereo + a projected IR pattern to give texture to blank surfaces — the RealSense D4xx approach); structured light (a known projected pattern, the original Kinect); time-of-flight (measure photon round-trip — the Azure Kinect, many phone sensors). Their range, their resolution, their failure surfaces, and how to pick one.
- **The cameras of 2026.** Intel RealSense D435i / D455 (active stereo + IMU), the Luxonis OAK-D series (stereo + on-camera inference), Microsoft Azure Kinect DK and its successors (ToF), and the Stereolabs ZED (passive stereo + neural depth). What each publishes, what each costs, and the ROS2 driver for each.
- **The RGB-D ROS2 topic family.** `/camera/color/image_raw`, `/camera/depth/image_rect_raw`, `/camera/depth/camera_info`, `/camera/color/camera_info`, the aligned `/camera/aligned_depth_to_color/image_raw`, `/camera/depth/color/points`, and the IMU `/camera/imu`. What each is, what its encoding is (`16UC1` millimetres vs `32FC1` metres — a classic unit bug), and its correct QoS.
- **Time synchronization.** `message_filters`, `ExactTime` vs `ApproximateTime` synchronizers, the slop parameter, hardware vs software sync, and why an unsynchronized RGB-D pair smears color onto moving objects.
- **Depth-to-point-cloud projection.** The back-projection `X = (u − cx)·Z / fx`, `Y = (v − cy)·Z / fy`, `Z = depth(u,v)`, vectorized in NumPy; the `sensor_msgs/PointCloud2` layout; `depth_image_proc` as the production node that does this; and how to color the cloud from the aligned RGB image.
- **Depth filtering.** The RealSense post-processing block: decimation (downsample + fill), the disparity transform, spatial edge-preserving filter, temporal filter (exponential moving average with a persistence control), and hole-filling. What each filter does to the noise, the edges, and the latency.
- **Reading the lie.** The depth confidence/validity map, the invalid-pixel sentinel (`0` in `16UC1`, `NaN` in `32FC1`), flying pixels at discontinuities, the glass/specular/black-surface failure triad, and multi-path error in ToF.
- **Alignment and extrinsics.** Why depth and color come from physically different sensors with an extrinsic transform between them; `align_depth` in the driver; and the optical-frame TF that puts the cloud right-side-up in rviz2.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                        | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Stereo geometry; the depth equation; the three technologies |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | RGB-D bring-up; the topic family; QoS; synchronization      |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Depth-to-point-cloud projection; intrinsics; alignment      |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Filtering; reading the confidence map; the failure triad    |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Foxglove workflow; temporal-filter A/B; mini-project start   |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                       |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, write-up polish                               |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | RealSense / OAK-D / Azure Kinect docs, the stereo-geometry references, `depth_image_proc`, and the talks worth your time |
| [lecture-notes/01-stereo-geometry-and-depth-technologies.md](./lecture-notes/01-stereo-geometry-and-depth-technologies.md) | The stereo depth equation from first principles, the `Z²` error law, and the passive-stereo / active-stereo / structured-light / ToF taxonomy with their failure surfaces |
| [lecture-notes/02-rgbd-bringup-projection-and-filtering.md](./lecture-notes/02-rgbd-bringup-projection-and-filtering.md) | The ROS2 RGB-D topic family, synchronization, depth-to-point-cloud projection by hand, the filter chain, and reading the confidence map |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-bringup-and-synchronize.md](./exercises/exercise-01-bringup-and-synchronize.md) | Bring up the RGB-D camera (real or sim), set correct QoS on every stream, and synchronize color+depth with `message_filters` |
| [exercises/exercise-02-depth-to-pointcloud.py](./exercises/exercise-02-depth-to-pointcloud.py) | Project a depth image into a metric `PointCloud2` by hand with the intrinsics, and verify it against `depth_image_proc` |
| [exercises/exercise-03-temporal-filter-ab.py](./exercises/exercise-03-temporal-filter-ab.py) | Run the depth temporal filter on vs. off and quantify the noise reduction with a flatness metric on a known plane |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-diagnose-three-depth-failures.md](./challenges/challenge-01-diagnose-three-depth-failures.md) | Identify and explain three planted depth failures — glass, flying pixels, and a unit bug — on a live RGB-D stream |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the depth-camera characterization write-up |
| [mini-project/README.md](./mini-project/README.md) | The `crunchbot_rgbd` bring-up package: synchronized, filtered, colored point cloud with a confidence-gated output topic |

## The "metric and right-side-up" promise

C24 uses a recurring marker for every exercise that ends in a depth measurement you can trust. When you project a depth image to a cloud and view it in rviz2 with the robot's TF tree, a *correct* result looks like this: the floor is a flat plane at `z ≈ 0` in `base_link`, a wall one metre away is a flat plane at `x ≈ 1.0`, and a 30 cm box on the floor measures 30 cm tall — not 28, not 33.

```
$ ros2 run crunchbot_rgbd measure_plane --frame base_link --topic /camera/depth/color/points
floor plane: normal=(0.00, 0.00, 1.00), height=+0.01 m, rms=0.004 m   [FLAT, level]
wall @ x:   normal=(1.00, 0.00, 0.00), distance=0.998 m, rms=0.006 m   [METRIC]
```

If the floor is tilted, the cloud is sideways, or the box measures 33 cm, you are not done. A point cloud that *looks* roughly right but is off by 10% is the canonical RGB-D failure — usually an intrinsics error, a `16UC1`-millimetres-read-as-metres unit bug, or an optical-frame TF that's missing. The point of Week 14 is to make "metric and right-side-up" ordinary, and to make every deviation a thing you can name.

## Stretch goals

If you finish the regular work early and want to push further:

- Derive the disparity-to-depth `Q` matrix from the stereo intrinsics and baseline, and confirm that `Q · [x, y, d, 1]ᵀ` reproduces the same `(X, Y, Z)` as your per-pixel back-projection. The `Q` matrix is how OpenCV's `reprojectImageTo3D` does it in one matrix multiply.
- Measure your camera's **depth-error-vs-distance** curve empirically: place a flat target at 0.5, 1.0, 2.0, 3.0, 4.0 m, fit a plane at each, and plot the RMS error. Confirm it grows roughly as `Z²`, and find the distance where your camera's error exceeds your robot's obstacle-tolerance budget — that is the camera's useful range *for your robot*.
- Stand up the **OAK-D** alongside (or instead of) the RealSense and compare: the OAK runs the YOLO detector *on the camera*, so the detection arrives already associated with depth. Note what that buys you for the Week 16 fused perception node.
- Read the **`depth_image_proc` source** for `point_cloud_xyzrgb` and confirm that its math is exactly your back-projection — then read how it handles the `register` (alignment) step, because that is the part most people get wrong by hand.

## Up next

Week 15 takes the metric point cloud you produce this week and does *3D perception* on it: voxel downsampling, ground-plane segmentation with RANSAC, Euclidean clustering for object proposals, and ICP registration between scans — in Open3D and PCL. Your mini-project's confidence-gated cloud is the exact input next week assumes. Push it before you start.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
