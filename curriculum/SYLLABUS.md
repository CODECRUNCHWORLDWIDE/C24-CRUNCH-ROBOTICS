# C24 · Crunch Robotics — Syllabus

**48 weeks · mastery tier · ~1,728 hours full-time · ~36 hours/week**

A complete, week-by-week breakdown of the Crunch Robotics curriculum, organized into six eight-week phases, ending in an integrated mobile-manipulator capstone with a graded safety case and chaos drill. Every weekly lab is specific. Every weekly artifact is portfolio-bound.

> Phase ordering rationale lives in [`CHARTER.md`](./CHARTER.md). Track entry requirements and post-track pathways live in [`README.md`](./README.md). The umbrella quality bar for any Crunch Labs track lives in [`../CRUNCH-LABS-CHARTER.md`](../CRUNCH-LABS-CHARTER.md).

---

## Phase map

| Phase | Weeks | Theme | Phase outcome |
|---|---|---|---|
| **1 · Foundations** | 1–8 | Robotics math, ROS2 deeply, first simulated robot, first SLAM | TurtleBot in Gz Sim with clean TF tree and a saved map |
| **2 · Perception** | 9–16 | Classical + learned CV, depth, 3D, sensor fusion, on-Jetson inference | A real-time, fused perception node inside 30 ms |
| **3 · Planning & Control** | 17–24 | Nav2, samplers, behavior trees, PID → LQR → MPC, manipulator kinematics | Autonomous nav of a multi-room map + MPC-controlled arm reach |
| **4 · Manipulation & Learning** | 25–32 | MoveIt2, grasping, imitation, RL, Diffusion Policy, ACT | A learned policy that does a constrained pick-and-place |
| **5 · Sim2Real & Multi-Robot** | 33–40 | Isaac Sim, domain randomization, fleet ops, vision-language policies | Language-conditioned task; two-robot shared map |
| **6 · Capstone** | 41–48 | Integration, safety case, chaos drills, fleet ops, interview prep | Graded mobile-manipulator capstone with safety case |

---

## Phase 1 — Foundations (weeks 1–8)

The first eight weeks build the vocabulary. You leave Phase 1 with a TurtleBot moving in Gz Sim under your own ROS2 nodes, a publishable TF tree, a saved Cartographer map, and the linear-algebra fluency to talk about all of it. No physical hardware required.

### Week 1 — Rigid-body math and ROS2 first contact
- **Topics:** 2D and 3D rotations; rotation matrices; quaternions; axis-angle; Euler angles and their failure modes; the SO(3) group; right-hand rule. ROS2 architecture overview: nodes, topics, the DDS layer, why ROS1 is dead.
- **Lecture:** "Rotations are a group, not a bag of numbers." Quaternion algebra, why we use them, why ZYX Euler is a debugging nightmare.
- **Hands-on lab:** Install ROS2 Jazzy on Ubuntu 24.04 (or WSL2). Write a `rclpy` publisher that emits `geometry_msgs/PoseStamped` at 50 Hz with a rotating quaternion. Visualize in `rviz2`. Convert your own quaternion to a rotation matrix in code; verify against `tf_transformations`.
- **Skills earned:** ROS2 install hygiene; rclpy publisher; quaternion sanity; rviz2 first contact.

### Week 2 — SE(3), twists, and tf2
- **Topics:** Homogeneous transforms; the SE(3) group; twists and exponential coordinates; adjoints; the tf2 tree as a representation of SE(3) at every joint.
- **Lecture:** "Every transform problem is a tree problem." How tf2 buffers, lookups, time-travel, and broadcasters work. The static vs. dynamic transform distinction.
- **Hands-on lab:** Build a four-link tf2 tree for a manipulator base → shoulder → elbow → wrist using a `static_transform_publisher` per joint and a dynamic broadcaster for one rotating joint. Write a node that listens for `wrist` in `base` frame and logs error when the tree is broken.
- **Skills earned:** SE(3) by hand; tf2 mental model; lookup timing and `extrapolation_exception` debugging.

### Week 3 — URDF, xacro, and the first simulated robot
- **Topics:** URDF schema; xacro macros; joint types; collision vs. visual meshes; inertials and why they matter; Gz Sim plugins for differential drive, IMU, and LiDAR.
- **Lecture:** "A URDF is a kinematic claim, not a CAD file." How to inspect a URDF, check inertia tensors, and avoid the "robot explodes on spawn" failure mode.
- **Hands-on lab:** Build a differential-drive robot URDF in xacro with a chassis, two driven wheels, two casters, a 2D LiDAR, and an IMU. Spawn it in Gz Sim. Drive it with `ros2 topic pub /cmd_vel`. Confirm the IMU and LiDAR topics populate.
- **Skills earned:** URDF/xacro authoring; Gz Sim launch files; sensor plugins; the "did I spawn the robot correctly" smell test.

### Week 4 — ROS2 in depth: actions, services, lifecycle, executors
- **Topics:** Services (request/response); actions (long-running, cancellable, with feedback); the managed-node lifecycle; single-threaded vs. multi-threaded executors; callback groups; composition (component nodes in one process).
- **Lecture:** "Use a topic, until you can't. Then use a service. Then use an action. Then use a behavior tree." How to choose. Why lifecycle nodes matter for safety-critical systems.
- **Hands-on lab:** Write a `Spin90Degrees` action server that rotates the simulated robot 90° using closed-loop IMU yaw. Implement preemption (cancel mid-rotation). Run it under a multi-threaded executor with a separate callback group for the cancellation handler.
- **Skills earned:** Action authoring; multi-threaded executor design; lifecycle hygiene; the action vs. service vs. topic taste test.

### Week 5 — QoS, DDS, and message design
- **Topics:** QoS policies: reliability, durability, history, depth, deadline, liveliness; DDS discovery; CycloneDDS vs. Fast-DDS; ROS2 message design idioms (header stamping, frame_id, message versioning).
- **Lecture:** "QoS is not optional. The defaults are wrong for half of your topics." When to use `BEST_EFFORT` + `KEEP_LAST(1)` (sensor streams). When to use `RELIABLE` + `TRANSIENT_LOCAL` (latched maps, parameters).
- **Hands-on lab:** Take your week-3 robot, set sensor topics to `BEST_EFFORT/KEEP_LAST/depth=5`, set the map topic to `RELIABLE/TRANSIENT_LOCAL/depth=1`. Use `ros2 doctor` and `ros2 topic info -v` to verify. Intentionally introduce a QoS mismatch and observe the silent failure. Write a one-page postmortem.
- **Skills earned:** QoS literacy; DDS introspection; the most under-taught failure mode in ROS2.

### Week 6 — Kinematics of mobile bases
- **Topics:** Differential-drive forward and inverse kinematics; unicycle vs. bicycle model; Ackermann; omnidirectional / mecanum kinematics; odometry from wheel encoders; odometry error growth.
- **Lecture:** "Wheel odometry drifts. Always. Plan for it." Where the drift comes from (slip, wheel-radius error, calibration), how it compounds, and why we need IMU fusion.
- **Hands-on lab:** Implement diff-drive forward kinematics by hand in a `rclpy` node — consume `/joint_states`, publish `/odom` + `odom→base_link` TF. Drive a 10×10 m square at three different speeds. Plot drift in PlotJuggler. Quantify the error.
- **Skills earned:** Diff-drive kinematics from first principles; odometry publishing; PlotJuggler fluency.

### Week 7 — First SLAM: slam_toolbox in 2D
- **Topics:** Occupancy grid representation; scan matching; loop closure; the `slam_toolbox` architecture; localization vs. mapping vs. lifelong mapping modes.
- **Lecture:** "SLAM is a loopy estimation problem dressed up as a map." How scan-matching front-ends produce constraints, how back-ends optimize them, why loop closures save you.
- **Hands-on lab:** Drive your simulated diff-drive robot through a multi-room Gz Sim world running `slam_toolbox` in mapping mode. Close a loop. Save the map. Restart in localization mode and verify AMCL-style pose initialization. Compare map quality at three different lidar update rates.
- **Skills earned:** slam_toolbox configuration; map saving; the localization-vs.-mapping mental model.

### Week 8 — Phase 1 integration + architecture review
- **Topics:** Launch file composition; parameter management; namespaces; remapping; the "minimal robot bring-up" pattern.
- **Lecture:** "Your launch file is your README for operators." How a senior robotics engineer reads a `launch/` directory.
- **Hands-on lab:** Package weeks 3–7 into one `bringup` package. One launch file brings up the robot, sensors, slam_toolbox, and rviz2 with a saved layout. Map a new world from scratch in under fifteen minutes, end-to-end.
- **Skills earned:** Launch-file authoring; parameter discipline; the bring-up package pattern.
- **Phase 1 milestone:** Architecture review. Defend your TF tree, your QoS choices, your odometry, and your map. Reviewer signs the rubric.

---

## Phase 2 — Perception (weeks 9–16)

Eight weeks of seeing the world properly. By the end, your robot fuses IMU + wheel odometry + LiDAR + RGB-D into a bounded-drift state estimate, detects objects with a learned model, and processes point clouds in real time. Recommended hardware kicks in: Jetson Orin Nano (or Path B sim equivalent).

### Week 9 — IMU calibration and integration
- **Topics:** Accelerometer and gyroscope models; bias, scale factor, noise; Allan variance; static and dynamic calibration; integration drift; mid-stance bias correction.
- **Lecture:** "An uncalibrated IMU is a random number generator with branding." Allan-variance plots and how to read them.
- **Hands-on lab:** Take 30 minutes of stationary IMU data (real BNO085 or simulated). Compute the Allan variance plot. Estimate biases. Apply correction in a `rclpy` node that re-publishes `/imu/data` with bias subtracted. Verify integrated yaw drift drops by a measurable factor.
- **Skills earned:** IMU calibration; Allan variance; bias subtraction.

### Week 10 — Sensor fusion 1: EKF and robot_localization
- **Topics:** Bayesian filter recap; Kalman filter derivation; Extended Kalman Filter for nonlinear motion models; the `robot_localization` package; `ekf_node` configuration.
- **Lecture:** "Sensor fusion is bookkeeping with covariance." Why `robot_localization` wants every sensor's covariance honestly stated.
- **Hands-on lab:** Configure `robot_localization`'s `ekf_node` to fuse wheel odometry + IMU into a single `/odometry/filtered`. Drive the same square as week 6. Compare drift to raw odometry. Tune process noise. Document the tuning rationale.
- **Skills earned:** EKF intuition; robot_localization configuration; covariance bookkeeping.

### Week 11 — Sensor fusion 2: UKF, particle filters, and factor graphs
- **Topics:** Unscented Kalman Filter; particle filters and AMCL; introduction to factor graphs (GTSAM); when to use each.
- **Lecture:** "The EKF lies about nonlinearity. The UKF lies less. The factor graph stops lying." Why modern SLAM front-ends emit factors, not means.
- **Hands-on lab:** Run AMCL against your week-7 map. Initialize the particle filter manually (`/initialpose`) and watch convergence in rviz2. Then build a toy two-pose factor graph in GTSAM Python bindings — two pose nodes, one between factor, one prior — and solve it. Confirm the optimum matches your hand calculation.
- **Skills earned:** AMCL operation; first GTSAM factor graph; the "filter vs. smoother" mental model.

### Week 12 — Classical computer vision and OpenCV deeply
- **Topics:** Image formation; pinhole camera model; intrinsics and distortion; calibration with a checkerboard; corners, descriptors (ORB, SIFT/SuperPoint at a glance), optical flow (Lucas-Kanade); stereo depth; RANSAC for outlier rejection.
- **Lecture:** "Classical CV did not go away. It is the floor under your learned model." Why ORB features still anchor ORB-SLAM3.
- **Hands-on lab:** Calibrate a USB camera (real) or a simulated camera (Gz Sim) using OpenCV. Then implement Lucas-Kanade optical flow on a 30-second drive video; visualize flow vectors; estimate forward velocity from flow alone; compare to wheel odometry.
- **Skills earned:** Camera calibration; OpenCV fluency; optical-flow odometry as a sanity check.

### Week 13 — Learned 2D perception on the edge
- **Topics:** YOLOv8/YOLOv10 family; DETR; SAM/SAM2; Depth-Anything v2; on-device inference with TensorRT, ONNX Runtime, OpenVINO; ROS2 wrapper patterns for inference nodes.
- **Lecture:** "Choose the smallest model that hits your latency budget. Then quantize it." How to read a TensorRT profile.
- **Hands-on lab:** Take a YOLOv8n checkpoint, export to ONNX, convert to TensorRT FP16, deploy as a ROS2 node consuming `/camera/image_raw` and publishing `vision_msgs/Detection2DArray`. Hit 30 FPS at 640×480 on a Jetson Orin Nano (or measure CPU equivalent on Path B). Profile with `nsys`.
- **Skills earned:** ONNX export; TensorRT engine build; ROS2 inference node; profiling on Jetson.

### Week 14 — Depth, stereo, and RGB-D perception
- **Topics:** Stereo geometry; disparity to depth; structured-light vs. ToF; RealSense / Azure Kinect / OAK-D pipelines; depth filtering (temporal, spatial, hole-filling); RGB-D as a fused topic.
- **Lecture:** "Every depth camera lies in a different way." How to interpret a depth confidence map.
- **Hands-on lab:** Bring up a RealSense D435i (or simulated equivalent) in ROS2. Publish synchronized RGB + depth + IMU. Project the depth into a point cloud using camera intrinsics. Visualize in rviz2 and Foxglove. Compare temporal-filter on vs. off.
- **Skills earned:** RGB-D bring-up; depth-to-point-cloud projection; Foxglove workflow.

### Week 15 — 3D perception: point clouds, Open3D, PCL
- **Topics:** Point cloud data structures; voxel grids; passthrough filters; statistical outlier removal; ground segmentation (RANSAC plane); Euclidean clustering for object proposals; ICP (point-to-point, point-to-plane).
- **Lecture:** "A point cloud is a list. A registered point cloud is a relationship." Why ICP is everywhere and where it fails.
- **Hands-on lab:** Take two consecutive LiDAR scans from a public dataset (Newer College or KITTI). Voxel-downsample, remove ground, cluster. Register the two scans with point-to-plane ICP in Open3D. Quantify registration error. Then run on a 100-scan sequence and report drift.
- **Skills earned:** Open3D fluency; ICP from the inside; drift quantification on a real dataset.

### Week 16 — Phase 2 integration + first midterm
- **Topics:** End-to-end perception graph design; topic timing diagrams; the perception latency budget; midterm architecture-review format.
- **Lecture:** "Perception is a pipeline. Pipelines have budgets. Defend yours." How to draw a latency block diagram.
- **Hands-on lab:** Compose weeks 9–15 into one fused perception node: IMU + wheel odom into EKF; LiDAR into 3D clustering; RGB-D camera into a YOLO detector. Publish a unified `/perception/objects` topic with detected objects in `map` frame. Hit a 30 ms end-to-end cycle on Orin Nano (or document why not on Path B).
- **Phase 2 milestone — first midterm:** A live architecture-review session. Defend your perception stack to a panel against a written rubric. Failures here send you back to the offending week; this is a hard gate.

---

## Phase 3 — Planning & Control (weeks 17–24)

Eight weeks of "now that we know where we are and what's around us, what do we do?" Planning at the navigation level (Nav2), planning at the manipulator level (MoveIt2 + OMPL), behavior trees as the integration glue, and controllers from PID to MPC. Safety stance starts here: every lab declares a fail-safe.

### Week 17 — Nav2 architecture and lifecycle
- **Topics:** The Nav2 stack: planner, controller, behavior, smoother, recovery, lifecycle manager; costmaps (2D, 3D); plugin architecture; the BT-driven navigation pattern.
- **Lecture:** "Nav2 is the most important reusable codebase in mobile robotics. Learn it like a senior engineer learns Linux." How the navigation BT is read.
- **Hands-on lab:** Bring up Nav2 on your week-7 map. Send goals from rviz2. Inspect the costmap layers in real time. Then write a custom behavior plugin that pauses navigation when an external `/operator/hold` topic latches `true`. Verify it cleanly resumes.
- **Skills earned:** Nav2 launch hygiene; costmap introspection; first custom plugin.
- **Fail-safe declared:** What does the robot do if the planner crashes mid-goal?

### Week 18 — Path planning: A*, Dijkstra, lattice, RRT*
- **Topics:** Graph search (A*, Dijkstra, D* Lite); state lattice planners; sampling-based planners (RRT, RRT*, BIT*); admissible heuristics; replanning under dynamic obstacles.
- **Lecture:** "Choose your planner by the structure of your state space." Why RRT* dominates manipulation and A* dominates flat ground.
- **Hands-on lab:** Implement A* by hand on an occupancy grid (Python, no library). Compare path quality and runtime against the Nav2 NavFn planner on the same map. Then drop in `SMAC Hybrid-A*` for an Ackermann-like vehicle and compare turn radius.
- **Skills earned:** A* from scratch; Nav2 planner swap; the planner-selection taste test.

### Week 19 — Behavior trees, Groot, and task structure
- **Topics:** Behavior trees vs. state machines; BT.CPP; control nodes (sequence, fallback, parallel); decorators; condition nodes; ticking semantics; Groot 2 for visualization.
- **Lecture:** "A behavior tree is a state machine you can audit." Why every modern mobile robot ships one.
- **Hands-on lab:** Author a behavior tree for "patrol three waypoints, but if a person is detected, pause and wait until they leave" using BT.CPP and the perception node from week 16. Visualize in Groot 2. Add a recovery branch for "if pause exceeds 60 s, retreat to charging station."
- **Skills earned:** BT authoring; Groot 2; the patrol-with-yield pattern.

### Week 20 — Controllers part 1: PID and feedforward
- **Topics:** PID anatomy; tuning (Ziegler-Nichols, manual, optimization-based); integrator wind-up; derivative kick; feedforward terms; the difference between regulation and tracking.
- **Lecture:** "PID is not obsolete. PID is the floor under everything." When to add D, when to remove D.
- **Hands-on lab:** Write a PID controller for diff-drive yaw rate that consumes IMU yaw and outputs `/cmd_vel`. Tune for three target step responses (45°, 90°, 180°). Plot rise time, overshoot, settling. Then add a feedforward term proportional to commanded angular velocity; quantify improvement.
- **Skills earned:** PID tuning by feel; step-response analysis; the feedforward habit.

### Week 21 — Controllers part 2: LQR
- **Topics:** State-space form; controllability, observability; the LQR cost function; the algebraic Riccati equation; gain scheduling; Kalman duality with LQE.
- **Lecture:** "LQR is PID with adult supervision." When the system is linear and the cost is quadratic, LQR is the optimal feedback law. When it isn't, LQR is still a great baseline.
- **Hands-on lab:** Linearize a diff-drive model around `v = 0.5 m/s`. Solve the LQR gain numerically with `scipy.linalg.solve_continuous_are`. Implement the controller in ROS2. Compare path-tracking error against the week-20 PID on a curved trajectory.
- **Skills earned:** State-space modeling; numerical LQR; the LQR-vs-PID comparison.

### Week 22 — Controllers part 3: MPC
- **Topics:** Model Predictive Control; receding horizon; quadratic programming; OSQP, acados, do-mpc; constraint handling (velocity, acceleration, obstacles); the MPC tuning trade-offs.
- **Lecture:** "MPC is the controller that respects the laws of physics you actually have to obey." Why warehouse AMRs ship MPC.
- **Hands-on lab:** Implement a kinematic-bicycle MPC for path tracking with `do-mpc`. Track a figure-8 reference at 1 m/s with hard velocity and steering-rate limits. Compare to LQR. Profile the solve time on the Orin Nano; document the latency budget.
- **Skills earned:** First production-shape MPC; constraint formulation; latency-aware control.

### Week 23 — Manipulator kinematics and MoveIt2 first contact
- **Topics:** Forward kinematics of a 6-DOF arm; the DH parameter convention and its modern alternatives; inverse kinematics (closed-form, numerical, IKFast); MoveIt2 architecture; the `move_group` node.
- **Lecture:** "An arm is a chain. The chain has a Jacobian. The Jacobian is the door to everything." Velocity IK, manipulability, singularities.
- **Hands-on lab:** Take a public 6-DOF URDF (UR5 or MyCobot 280). Bring it up in MoveIt2 + Gz Sim. Send goal poses from rviz2. Then write a Python script that consumes `geometry_msgs/PoseStamped` from a topic and triggers a plan-and-execute via the MoveIt2 action interface.
- **Skills earned:** MoveIt2 bring-up; pose-goal planning; manipulator Jacobian intuition.

### Week 24 — Phase 3 integration + safety primer
- **Topics:** Putting Nav2 and MoveIt2 in the same launch graph; namespace discipline for multi-controller systems; an introduction to functional safety: hazard log, fail-safe categories, software vs. hardware E-stop.
- **Lecture:** "Every controller has a known failure mode. Write it down before you ship." The hazard-log practice.
- **Hands-on lab:** Compose Nav2 + MoveIt2 + a small BT into one launch graph: the robot drives to a table, the arm reaches a pose, the robot returns. Add a `/safety/estop` topic that, when latched, cancels both the Nav2 action and the MoveIt2 trajectory within 200 ms. Document the timing.
- **Phase 3 milestone:** Reviewer signs off the controller stack and the first hazard log.

---

## Phase 4 — Manipulation & Learning (weeks 25–32)

Eight weeks where the robot starts to *learn*. We do grasping properly, we run imitation learning on a real task, we train a Diffusion Policy and an ACT, and we leave the phase with a learned policy that completes a constrained pick-and-place with a documented classical fallback.

### Week 25 — Grasping foundations
- **Topics:** Grasp taxonomies (force closure, form closure); analytic grasp planners; grasp datasets (ACRONYM, GraspNet-1Billion); the gripper-frame convention; antipodal grasp scoring.
- **Lecture:** "A grasp is a pose plus a width plus a confidence." Why most grasp failures are pose errors, not policy errors.
- **Hands-on lab:** Take a tabletop point cloud (Open3D-rendered or RealSense capture). Sample antipodal grasp candidates with a heuristic. Score them. Visualize the top-10 in rviz2 with gripper-mesh overlays. Verify the best grasp is reachable by the week-23 MoveIt2 setup.
- **Skills earned:** Grasp candidate generation; gripper-frame transforms; antipodal scoring.

### Week 26 — Learned grasping: Contact-GraspNet
- **Topics:** Contact-GraspNet architecture; training data, runtime data; the segmentation-aware grasp head; failure modes on transparent and reflective objects.
- **Lecture:** "Learned grasping is segmentation + geometry + a small network." Why the data matters more than the architecture.
- **Hands-on lab:** Deploy a pre-trained Contact-GraspNet checkpoint as a ROS2 node consuming an RGB-D frame. Publish ranked grasp poses as `vision_msgs/`-style messages. Pipe the top grasp into MoveIt2. Pick up three objects in Gz Sim (mug, box, tool). Quantify success rate.
- **Skills earned:** Pretrained-policy deployment; learned-grasp pipeline; the first integrated perception → policy → motion loop.

### Week 27 — Imitation learning 1: Behavior Cloning and DAgger
- **Topics:** Behavior Cloning; covariate shift; DAgger; demonstration collection (teleop, scripted); the diffusion-of-error problem.
- **Lecture:** "BC fails because the policy visits states the data never saw. DAgger fixes that by asking the expert about those states." Why DAgger is unromantic but works.
- **Hands-on lab:** Collect 50 teleoperated demonstrations of a "reach for the red block" task in Gz Sim using a keyboard or gamepad. Train a small MLP behavior cloning policy. Roll out. Observe failure. Implement one DAgger round. Quantify success-rate improvement.
- **Skills earned:** Demo collection pipeline; BC training loop; the covariate-shift smell test.

### Week 28 — Reinforcement learning for robots: PPO and SAC
- **Topics:** Policy gradients recap; PPO; SAC; reward shaping; the gym/Gymnasium interface; the Isaac Lab simulation environment; the reward-hacking problem.
- **Lecture:** "RL works on robots when the simulator is fast, the reward is shaped, and the curriculum is real." The sim-throughput-matters axiom.
- **Hands-on lab:** Train a PPO policy in Isaac Lab (or Gymnasium + Gz Sim on Path B) for a reach task. Use 100 parallel environments. Reach 90% success in under 30 minutes of wall time. Inspect the reward curve in TensorBoard.
- **Skills earned:** Parallel-sim RL; PPO hyperparameter intuition; the wall-time vs. sample-efficiency trade-off.

### Week 29 — Diffusion Policy
- **Topics:** Diffusion Policy architecture (Chi et al.); action-chunk prediction; receding-horizon execution; observation encoders; CFG-style conditioning; latency considerations.
- **Lecture:** "Diffusion Policy ate the multimodal-action problem." Why a noise-prediction model beats a Gaussian-MLP policy on real tasks.
- **Hands-on lab:** Train a Diffusion Policy on the week-27 demos (you may augment to 200 trajectories). Compare success rate against BC and BC+DAgger on the same eval set. Visualize the action distribution at a known multimodal state.
- **Skills earned:** Diffusion Policy training; action-chunk evaluation; multimodal-action visualization.

### Week 30 — Action Chunking Transformer (ACT)
- **Topics:** ACT architecture (Zhao et al.); chunked action prediction; the temporal-ensembling trick; observation tokenization; deployment latency.
- **Lecture:** "ACT is the most deployment-friendly imitation architecture today." Why temporal ensembling smooths execution.
- **Hands-on lab:** Train ACT on the same demonstrations as week 29. Benchmark inference latency on the Jetson Orin. Compare success rate vs. Diffusion Policy at fixed latency budget. Produce a one-page comparison table.
- **Skills earned:** ACT training; inference profiling; deployment-latency-aware policy choice.

### Week 31 — Generalist policies: Octo and OpenVLA
- **Topics:** Octo (Open-X Embodiment); OpenVLA; the cross-embodiment dataset story; the prompt-as-task pattern; the limits of zero-shot transfer.
- **Lecture:** "Generalist robot models are real, smaller than you think, and finetuning is mandatory." How a robotics startup uses OpenVLA in 2026.
- **Hands-on lab:** Take an open-weight OpenVLA checkpoint. Fine-tune on the week-29 demos for one epoch on a cloud GPU. Compare zero-shot vs. fine-tuned success rate. Document the failure modes.
- **Skills earned:** VLA fine-tuning; zero-shot vs. fine-tuned evaluation; an honest VLA failure analysis.

### Week 32 — Phase 4 integration + second midterm
- **Topics:** The learned-policy + classical-fallback pattern; safety scaffolds around learned policies; trajectory clamping; predictive safety filters; the midterm architecture review.
- **Lecture:** "Ship the learned policy with a leash." How a predictive safety filter wraps a learned action.
- **Hands-on lab:** Take your best policy from weeks 27–31. Wrap it with a runtime safety filter that rejects actions exceeding velocity, acceleration, or workspace bounds. Add a `/policy/fallback` branch in the BT that takes over with the classical motion planner if the policy is rejected three times in a row. Measure intervention rate.
- **Phase 4 milestone — second midterm:** Defend your learned-policy stack to a panel. Required artifacts: training pipeline, eval protocol, safety wrapper, fallback path, hazard log update.

---

## Phase 5 — Sim2Real, Multi-Robot, AI-Powered Robotics (weeks 33–40)

Eight weeks of "your sim policy isn't real," "your robot isn't alone," and "your robot has to understand English." This phase is where C23 (Crunch Agents) pays off if you took it.

### Week 33 — Gazebo, Gz Sim, and Isaac Sim compared
- **Topics:** Gazebo Classic vs. Gz Sim (Garden/Harmonic); NVIDIA Isaac Sim and Isaac Lab; physics back-ends (Bullet, ODE, PhysX, MuJoCo); the simulation throughput vs. fidelity trade-off; ROS2 bridges (`ros_gz`, `omni.isaac.ros2_bridge`).
- **Lecture:** "Choose your sim by what you're optimizing for." When Gz Sim wins (free, ROS-native), when Isaac Sim wins (GPU-parallel training).
- **Hands-on lab:** Stand up the same robot URDF in Gz Sim and Isaac Sim (or Path B: two configs of Gz Sim with PhysX vs. ODE). Run the same patrol BT in each. Compare contact behavior, sensor fidelity, and step-time. One-page write-up.
- **Skills earned:** Multi-sim fluency; the sim-selection table.

### Week 34 — Domain randomization and sim-to-real strategy
- **Topics:** Visual domain randomization; dynamics randomization; sensor noise injection; the canonical Sadeghi-Levine pattern; the Tobin et al. randomization recipe; randomization for manipulation vs. navigation.
- **Lecture:** "Sim-to-real is not magic. It is a curriculum of distributions." Why training over 1,000 randomized worlds beats fidelity-chasing a single one.
- **Hands-on lab:** Augment the week-28 PPO training with visual + dynamics randomization. Train for 30 minutes. Roll out on a held-out "real-style" eval world with mismatched textures, lighting, and friction. Quantify the gap closure.
- **Skills earned:** Randomization scripting; eval-world authoring; the gap-closure metric.

### Week 35 — Multi-robot 1: shared mapping and coordination
- **Topics:** Distributed SLAM (multi-robot Cartographer, Kimera-Multi at a glance); shared map merging; topic namespacing; ROS2 discovery domains; latency-bounded coordination.
- **Lecture:** "Two robots are not one robot, twice. They share state under uncertainty." Why coordination is a distributed-systems problem.
- **Hands-on lab:** Spawn two diff-drive robots in Gz Sim in separate namespaces. Run independent SLAM per robot. Periodically merge the two maps into a shared map served on a third namespace. Visualize all three in rviz2.
- **Skills earned:** Multi-robot namespacing; map merging; the discovery-domain pattern.

### Week 36 — Multi-robot 2: task allocation and fleet management
- **Topics:** Task allocation (auction-based, market-based, optimization-based); the Open-RMF stack; fleet adapters; conflict-resolution at narrow passages.
- **Lecture:** "Open-RMF is what an open-source fleet manager looks like in 2026." How a fleet adapter plugs into a heterogeneous fleet.
- **Hands-on lab:** Wire two simulated robots into Open-RMF. Submit five delivery tasks via the fleet API. Observe negotiation at a shared corridor. Inject a "robot stalls" event and verify reallocation.
- **Skills earned:** Open-RMF bring-up; fleet-task lifecycle; reallocation drills.

### Week 37 — Vision-language models for robotics
- **Topics:** RT-2, RT-X, OpenVLA, PaLI-X for robotics; vision-language pretraining; grounding language to actions; the "VLA as a policy" pattern; latency reality on edge compute.
- **Lecture:** "VLMs put a natural-language steering wheel on your robot. Steering is still not driving." Where VLAs work, where they hallucinate.
- **Hands-on lab:** Take the week-31 fine-tuned OpenVLA. Wire it into the mobile manipulator: text instruction in, action chunks out, behavior tree dispatches. Evaluate on three instructions: "bring the red cup," "move the blue block to the left," "pick up the tool." Document failure modes.
- **Skills earned:** VLA-as-policy integration; language-conditioned eval; honest failure documentation.

### Week 38 — Grounded planners and tool use (the C23 bridge)
- **Topics:** LLM-as-planner; grounded planning (SayCan-style); structured tool use for robots; the "planner + skill library" architecture; safety constraints in language space.
- **Lecture:** "When the policy is a language model, the safety case is half-prompt, half-runtime." Why prompts alone are insufficient.
- **Hands-on lab:** Build a grounded planner that takes "clear the table" and emits a skill sequence (`detect_objects → grasp → place → repeat`). Use a local small LLM (Llama 3.1 8B via Ollama or vLLM) as the planner; constrain output with grammar. Wire skills to the week-32 stack. Demonstrate.
- **Skills earned:** Grounded-planner authoring; constrained-grammar output; the skill-library pattern.

### Week 39 — Edge ML optimization for robotics
- **Topics:** TensorRT advanced (FP16, INT8, sparsity); ONNX Runtime; model distillation; quantization-aware training; mixed-precision; the latency budget as a first-class artifact.
- **Lecture:** "On Orin Nano, every millisecond is a design constraint." How a robotics engineer profiles a pipeline.
- **Hands-on lab:** Take the YOLO detector from week 13, the Diffusion Policy from week 29, and the VLA wrapper from week 37. Profile the integrated graph on Jetson Orin (or sim). Produce a Gantt-style latency block diagram. Apply one optimization (INT8 quant of the detector). Document the speedup and the accuracy delta.
- **Skills earned:** TRT advanced flags; integrated-graph profiling; the latency Gantt.

### Week 40 — Phase 5 integration + capstone milestone
- **Topics:** The capstone problem statement is unsealed. Pre-flight checks. The chaos-drill template. The safety-case template.
- **Lecture:** "Read the capstone spec like a contract. Then write back what you heard." The capstone-kickoff ritual.
- **Hands-on lab:** Stand up the full system end-to-end in sim: mobile base + arm, perception + planner + controller + VLA policy, behavior tree, safety wrapper, telemetry. Run one "happy-path" execution of a language-conditioned pick-and-place. Submit a 5-minute video walkthrough.
- **Phase 5 milestone:** Capstone sim milestone signed off. You have eight weeks to make it real (or to make sim production-grade if you are on Path B).

---

## Phase 6 — Capstone (weeks 41–48)

Eight weeks. One robot. One safety case. Two chaos drills. One interview. One portfolio. This is the only phase where the syllabus thins out — because the capstone is the syllabus.

### Week 41 — Capstone integration sprint + safety case
- **Topics:** Hardware bring-up checklist (Path A) or sim-production-grade checklist (Path B). The safety case as an artifact: hazard log, FMEA, ISO 13482 / ISO 10218 framing.
- **Hands-on lab:** Author a portfolio-quality safety case for the capstone robot. Include: intended use, foreseeable misuse, hazard list, risk assessment, mitigations (software E-stop, hardware E-stop, software watchdog, perception confidence gates), residual risk, validation plan.
- **Skills earned:** Safety-case authoring; ISO framing; FMEA practice.

### Week 42 — Capstone build sprint 1
- **Topics:** Move from sim to hardware (Path A) or harden the sim deployment (Path B). Real-sensor noise vs. simulated noise; real-actuator latency; the first integration day.
- **Hands-on lab:** Path A: bring the robot up on hardware. Drive a 20-meter trajectory under your stack. Path B: harden the launch graph; add a telemetry subscriber; verify a clean cold-boot in under 60 seconds.
- **Skills earned:** Hardware integration day (or sim production hardening).

### Week 43 — Capstone build sprint 2 + telemetry and fleet ops
- **Topics:** Telemetry (Prometheus + OpenTelemetry + Foxglove); OTA updates for robots (extends C7 patterns); the operator dashboard; remote teleop assist.
- **Hands-on lab:** Wire robot telemetry into a Foxglove dashboard. Stream pose, costmap, policy actions, safety filter triggers, and a CPU/GPU load panel. Implement a one-click "remote teleop takeover" button that pauses autonomy and grants teleop.
- **Skills earned:** Fleet-ops dashboard; teleop-assist plumbing; production telemetry.

### Week 44 — Capstone build sprint 3 + language-conditioned task tuning
- **Topics:** Fine-tuning the VLA policy on capstone-specific demos; eval-set curation; the "twenty-instructions" evaluation suite.
- **Hands-on lab:** Curate a twenty-instruction eval suite for the capstone ("bring me the red cup from the left bench" and nineteen others). Run baseline. Fine-tune the policy on 50 capstone-specific demos. Re-run. Report per-instruction success rate.
- **Skills earned:** Eval-suite design; per-instruction reporting; honest improvement tracking.

### Week 45 — Capstone build sprint 4 + interview-prep ramp
- **Topics:** Robotics-startup system design (whiteboard); robotics technical interviews (coding + math + sensors); the "five technical projects" résumé conversation.
- **Hands-on lab:** Run two mock interviews with a peer: one system-design ("design an autonomy stack for a warehouse AMR"), one technical ("explain how an EKF works and write the predict step on the board"). Self-grade against a rubric.
- **Skills earned:** Interview muscle memory; defense of your own stack under questioning.

### Week 46 — Gameday: the chaos drill
- **Topics:** Chaos engineering for robots; the two intentional failures; the postmortem template.
- **Hands-on lab:** Live-graded chaos drill, two parts.
  - **Drill 1 — Sensor dropout mid-task:** the LiDAR is killed (`ros2 daemon stop` plus a process-kill) mid-execution of a language-conditioned task. The robot must detect the dropout, degrade gracefully, alert the operator dashboard, and complete or safely abort.
  - **Drill 2 — Planner deadlock at a doorway:** a narrow corridor is partially blocked by a moved obstacle. The planner cycles. The robot must detect the cycle, replan around, request operator assist, or safely abort. Time to recover is measured.
- **Hands-on lab (continued):** Write two postmortems, one per drill, against the postmortem template: timeline, root cause, contributing factors, what worked, what didn't, action items.
- **Skills earned:** Chaos drill survival; postmortem authorship.

### Week 47 — Mock interview + portfolio polish
- **Topics:** The robotics-startup loop; the "tell me about your capstone" five-minute pitch; portfolio polish (README, video, architecture diagram, safety case appendix).
- **Hands-on lab:** Full-loop mock interview with an instructor or senior-engineer reviewer. Then polish your three flagship portfolio projects: the perception cycle from week 16, the learned-policy stack from week 32, and the capstone from week 48. Each gets a polished README, a < 3-minute walkthrough video, and a Mermaid architecture diagram.
- **Skills earned:** Interview-loop endurance; portfolio polish.

### Week 48 — Capstone defense
- **Topics:** The final defense. A panel reads your safety case, watches your two videos (sim + real, or sim + sim-hardened on Path B), reviews your chaos-drill postmortems, and asks live questions.
- **Hands-on lab:** Capstone defense (90 minutes). Required deliverables (all public, all on GitHub):
  1. The integrated repo (everything from week 1 forward) with a top-level README.
  2. A Mermaid architecture diagram of the autonomy stack.
  3. Two videos: sim run, real run (or two sim runs on Path B labelled clearly).
  4. The signed safety case.
  5. Two chaos-drill postmortems.
  6. The operator-dashboard recording.
  7. The polished portfolio (three projects).
- **Phase 6 milestone — track completion:** Panel signs off. You are now a Crunch Robotics graduate.

---

## Capstone specification — Autonomous Mobile Manipulator with Language-Conditioned Pick-and-Place

The capstone is **one substantial integrated robot**, not three loosely-related deliverables. Specifically:

> Build (or simulate) a wheeled-base + 6-DOF-arm robot that takes a natural-language instruction (e.g., *"bring me the red cup from the left bench"*) and executes it via a perception → planner → controller → policy stack. The autonomy runs on a Jetson Orin (Path A) or in Gz/Isaac Sim with a documented hardware target (Path B). Telemetry streams to an operator dashboard. The robot passes a documented safety case for shared-space operation and survives two chaos drills.

### Required system properties

1. **Perception:** Fused IMU + LiDAR + RGB-D state estimate; 2D and 3D object detection; latency ≤ 50 ms end-to-end.
2. **Planning:** Nav2 for the base; MoveIt2 for the arm; a behavior tree at the top.
3. **Control:** PID at minimum for the base; MPC bonus; MoveIt2-managed for the arm.
4. **Policy:** A vision-language model (OpenVLA or equivalent open-weight) that selects the grasp pose from the language instruction.
5. **Safety:** Software E-stop topic with 200 ms latch; runtime velocity / workspace clamps; classical fallback when the learned policy is rejected three times in a row; hardware E-stop documented (Path A) or simulated and documented (Path B).
6. **Telemetry:** Foxglove dashboard streaming pose, costmap, policy actions, safety filter status, CPU/GPU load. Remote teleop takeover button.
7. **Fleet readiness:** The robot reports its identity, capabilities, and health on a `/fleet/heartbeat` topic at 1 Hz, conformant to a documented schema (Open-RMF-style).
8. **OTA-ready:** A documented update procedure that does not brick the robot. (Wire-extension from C7.)

### Deliverables

- **Repository** at `github.com/<org>/<your-handle>-crunch-robotics-capstone`, public, GPL-3.0.
- **Architecture diagram** (Mermaid in-repo + PNG export).
- **Two videos** (sim + real for Path A; or sim + sim-hardened on a documented hardware target for Path B), each ≤ 5 minutes, with voiceover.
- **Safety case** (8–15 pages) including hazard list, FMEA, mitigations, validation plan, residual risk.
- **Two chaos-drill postmortems** — sensor-dropout-mid-task and planner-deadlock-at-doorway — each 2–4 pages.
- **Operator-dashboard screen recording** (3 minutes).
- **Portfolio** — three polished projects under [`portfolio.md`](./portfolio.md).
- **Public retro** — a one-page "what I'd do differently" written at week 48.

### Acceptance criteria (live-graded at week 48)

A capstone passes if and only if:
- The robot completes at least **15 of 20** language-conditioned instructions from the eval suite.
- The fused state estimate **drifts < 0.5 m over a 20-meter trajectory**.
- The safety case is signed by a peer reviewer and the instructor panel.
- The two chaos drills are recovered with **operator-detectable** events on the dashboard within **60 seconds** each, and the postmortems pass the rubric.
- The system **cold-boots** to operational state in **< 60 seconds**.

A capstone fails if any of the above is missing or if a safety-relevant defect is unaddressed in the safety case.

---

## Assessment matrix

| Instrument | Count | Weight | Notes |
|---|---:|---:|---|
| Weekly quizzes | 48 | 10% | 10 questions each, answer key in `quiz.md` |
| Weekly labs | 48 | 25% | Pass/fail against per-week acceptance rubric |
| Architecture-review writeups | 2 | 10% | Midterm 1 (week 16) and midterm 2 (week 32) |
| Phase-milestone reviews | 6 | 10% | One per phase, signed by reviewer |
| Capstone sim milestone | 1 | 10% | Week 40 |
| Capstone final defense | 1 | 20% | Week 48, panel-graded |
| Safety-case writeup | 1 | 5% | Week 41 artifact, portfolio-bound |
| Gameday / chaos drill | 1 | 5% | Week 46, live-graded |
| Mock robotics-startup interview | 1 | 5% | Week 47 |

Pass threshold: **75%** overall, with **no phase milestone unsigned** and **no failing capstone deliverable**.

---

## Career engineering pack

The track ends with a portfolio-grade body of work designed to walk you into a robotics-startup interview as a peer engineer.

### `interview-prep/`

- **Robotics system design** — 12 problems (warehouse AMR, last-mile delivery, surgical assist, autonomous forklift, drone inspection, etc.) with reference solutions and grading rubrics.
- **Robotics technical** — 30 problems across kinematics, controls, sensor fusion, SLAM math, behavior-tree design, and ROS2 internals.
- **Behavioral / portfolio walkthrough** — the "tell me about a robotics project" preparation, 5 anchor stories.

### `production-runbook.md`

- What an on-call shift on a robot fleet looks like.
- Alert taxonomy (P0 / P1 / P2) calibrated to robot fleets.
- Runbooks for: sensor dropout, planner deadlock, policy regression, OTA-update rollback, single-robot quarantine, fleet-wide pause.
- Postmortem template.

### `portfolio.md`

The three flagship projects to put on a résumé:

1. **The 30-ms perception cycle** (from week 16): fused, real-time, on-Jetson, with profiling artifacts.
2. **The learned-policy + classical-fallback stack** (from week 32): training pipeline + safety wrapper + eval set.
3. **The capstone**: the integrated mobile manipulator with safety case and chaos-drill postmortems.

Each gets a polished README, a Mermaid architecture diagram, a 3-minute walkthrough video, and a live deploy link (or runnable container image) where applicable.

### `safety-case-template/`

A reusable scaffold for the safety-case artifact, framed against ISO 13482 (personal-care robots) and ISO 10218 (industrial manipulators). Includes hazard-log template, FMEA template, mitigations checklist, validation-plan template, and residual-risk-acceptance form. This template is itself a portfolio piece.

---

## License

Licensed under **GPL-3.0-or-later**. See [`LICENSE`](./LICENSE). Curriculum maintained by the Code Crunch Club curriculum council and the Crunch Robotics maintainer team.

— *C24 · Crunch Robotics. Live as of 2026-05-13.*
