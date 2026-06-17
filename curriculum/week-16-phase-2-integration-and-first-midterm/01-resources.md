# Week 16 — Resources

Every resource on this page is **free** and current to 2026. The ROS2 Jazzy documentation, the `vision_msgs` and `robot_localization` docs, the REP coordinate-frame standards, the profiling tools, and the systems-integration talks are all openly accessible. No paid course or paywalled book is required for this week.

Week 16 introduces almost no new API. The references here are weighted toward **systems integration, latency profiling, data association, and the architecture-review discipline** — the topics that turn seven weeks of perception components into one defensible fused node.

## Required reading (work it into your week)

- **The C24 syllabus, Week 16 and the Phase 2 milestone** — re-read it before anything else this week. The 30 ms budget, the unified `/perception/objects`, the midterm-as-hard-gate are all defined there: [`../../SYLLABUS.md`](../../SYLLABUS.md).
- **REP 105 — Coordinate frames for mobile platforms** — `map`, `odom`, `base_link` and the transform chain every component in your perception stack must agree on. The frame-mismatch integration defect is a REP-105 violation:
  <https://www.ros.org/reps/rep-0105.html>
- **`vision_msgs`** — `Detection2DArray`, `Detection3DArray`, `Detection3D`, `ObjectHypothesisWithPose`. The message types your fused node publishes; read the field semantics before you design `/perception/objects`:
  <https://github.com/ros-perception/vision_msgs>
- **`robot_localization` — `ekf_node`** — the EKF fusing IMU + wheel odom into `/odometry/filtered`; re-read the covariance and frame configuration, because honest covariances are what let the filter ignore a bad input:
  <https://docs.ros.org/en/melodic/api/robot_localization/html/index.html> (concepts stable across distros; configuration is the same on Jazzy)
- **ROS2 Jazzy — Composition (intra-process)** — the composition primitive that eliminates inter-process serialization, the single biggest lever on your latency budget:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>

## Latency profiling and timing

- **`ros2 topic delay` and `ros2 topic hz`** — the first tools you reach for: delay measures the age of messages on a topic; hz measures the rate. Your latency probe automates these:
  <https://docs.ros.org/en/jazzy/Concepts/Basic/About-Command-Line-Tools.html>
- **`ros2_tracing` (LTTng)** — the low-overhead tracing framework for ROS2; the way to find the single hop that dominates your end-to-end latency:
  <https://github.com/ros2/ros2_tracing>
- **`message_filters` time synchronizers** — `ApproximateTimeSynchronizer` for the multi-input fusion node (matching the LiDAR cluster and the camera detection by stamp):
  <https://docs.ros.org/en/jazzy/p/message_filters/>
- **NVIDIA Nsight Systems (`nsys`)** — profiling the GPU contention between the YOLO detector and any other GPU work, which is where the latency-budget blowout under load hides (Path A, Jetson):
  <https://developer.nvidia.com/nsight-systems>
- **PlotJuggler** — watch the latency distribution, the drift, and the per-component health live during a run:
  <https://github.com/facontidavide/PlotJuggler>

## Data association and multi-sensor fusion

- **A survey of detection-level sensor fusion (read the taxonomy, not every method)** — the vocabulary of early/late/deep fusion and detection-to-track association. Search "multi-sensor fusion autonomous driving survey 2023/2024"; the taxonomy is stable.
- **Camera-LiDAR calibration and projection** — projecting a 3D cluster into the image (or back-projecting a 2D box) is the core of detection-to-cluster association; the extrinsic calibration is the prerequisite:
  <https://github.com/ros-perception/image_pipeline> (the `image_geometry` package's `PinholeCameraModel.project3dToPixel`)
- **IoU and the Hungarian algorithm** — the standard tools for matching boxes/detections between two sources. `scipy.optimize.linear_sum_assignment` is the Hungarian solver you'll use:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html>

## The architecture-review discipline

- **Google SRE Book — "Reliable Product Launches at Scale"** — the launch-checklist and review discipline; the intellectual frame for defending a system to a panel against a written rubric:
  <https://sre.google/sre-book/reliable-product-launches/>
- **"How to run a design review" (engineering-org write-ups)** — search for engineering-blog treatments of the architecture-review format; the structure (context → design → trade-offs → risks → decision) is what your perception brief follows.
- **REP 103 — Standard units and conventions** — a silent unit mismatch (degrees vs radians, mm vs m) is the second-most-common integration defect after frames; the panel will check:
  <https://www.ros.org/reps/rep-0103.html>

## The components you are integrating (re-reference)

These are the canonical docs for the perception subsystems you built in Weeks 9–15 and are now composing. Bookmark them; you will re-open at least three when the parts disagree.

- **`robot_localization`** (the EKF fusing IMU + wheel odom): <https://github.com/cra-ros-pkg/robot_localization>
- **Open3D** (the point-cloud clustering and registration from Week 15): <https://www.open3d.org/docs/release/>
- **Ultralytics YOLO** (the 2D detector from Week 13) and **TensorRT** (the edge-inference runtime): <https://docs.ultralytics.com/> and <https://developer.nvidia.com/tensorrt>
- **`realsense-ros`** (the RGB-D bring-up from Week 14): <https://github.com/IntelRealSense/realsense-ros>
- **`tf2`** (the frame tree every component shares): <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>

## Talks worth watching (all free, no account)

- **"Building a Production Perception Stack with ROS2"** — search the **ROSCon 2024/2025** playlists for the perception-integration and composition talks; the latency and intra-process-comms talks are the most relevant to this week.
- **"Optimizing ROS2 for low latency"** — the composition / intra-process / zero-copy talks from the ROSCon middleware track; this is how teams hit a 30 ms budget.
- **"Sensor fusion for autonomy"** — search for the camera-LiDAR fusion talks from the major AV/AMR companies; the detection-to-track association framing transfers directly to your fused node.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Fused perception node** | The node that composes IMU/odom/LiDAR/camera into one `/perception/objects` output. |
| **End-to-end latency** | Sensor-stamp to `/perception/objects` publish — the *path*, not one model's inference time. |
| **Latency budget** | The end-to-end target (30 ms) decomposed into per-hop costs you can each measure. |
| **p95 latency** | The 95th-percentile latency; the worst common case, which is what matters, not the mean. |
| **Interface contract** | The topic/type/frame/rate/QoS agreement between two components; a disagreement is a silent failure. |
| **Data association** | Matching a 2D detection to a 3D cluster (or detection-to-track) so they become one object. |
| **Stale-perception race** | A fast consumer using a slow producer's out-of-date data; fixed by a stamp-age guard. |
| **Stamp-age guard** | A runtime check that rejects a message older than a tolerance before using it. |
| **Health gate** | De-weighting or rejecting an input flagged untrustworthy (e.g. low ICP fitness). |
| **Frame/timing mismatch** | Detections in the wrong frame, or a transform looked up at the wrong stamp. |
| **Latency-budget blowout** | The pipeline meets the budget idle but blows it under load (GPU/CPU contention). |
| **Architecture review** | The panel defense: block diagram, latency budget, contract, failure table, measured numbers. |
| **Hard gate** | A milestone you must pass to advance; the Week 16 midterm sends failures back to the offending week. |

---

*Bookmarks decay. If a link rots, search the title — the REPs, ROSCon talks, the SRE book chapters, and the ROS2 package repos are all canonical and reappear on the same hosts.*
