# Week 26 — Resources

Every resource here is **free**. The Contact-GraspNet paper and code are open (NVIDIA, BSD-style license). The datasets (ACRONYM, GraspNet-1Billion) are public for research. The MoveIt2 and ROS2 docs are open and pinned to **Jazzy** where versioned. SAM2 is open-weight (Meta). No paywalled books are linked.

PyTorch references are pinned to **2.x**; the APIs we use (`torch.nn`, `torch.cuda.amp`, `Dataset`/`DataLoader`) are stable across the 2.x line. Where a repo has moved, the canonical mirror is given.

## Required reading (work it into your week)

- **Contact-GraspNet (Sundermeyer et al., ICRA 2021)** — the paper. Read §3 (the contact representation and the heads) twice, Monday and Wednesday:
  <https://arxiv.org/abs/2103.14127>
- **Contact-GraspNet — official code** (NVIDIA Labs). The model definition and the inference script are the ground truth for the pose-reconstruction math:
  <https://github.com/NVlabs/contact_graspnet>
- **PyTorch port of Contact-GraspNet** — a maintained `torch` re-implementation you can actually load on Jazzy + PyTorch 2.x without the original TF1 stack:
  <https://github.com/elchun/contact_graspnet_pytorch>
- **PointNet++ (Qi et al., NeurIPS 2017)** — the backbone. You need §3 (set abstraction, feature propagation) to read the architecture:
  <https://arxiv.org/abs/1706.02413>
- **MoveIt2 — Pick and Place / Pose-goal planning** — how the grasp becomes motion:
  <https://moveit.picknik.ai/main/doc/examples/moveit_cpp/moveitcpp_tutorial.html>

## The datasets (skim the README, don't download all of it)

You will not train this week, so you do not need the full datasets. Read the schema so you understand the checkpoint you load.

- **ACRONYM (Eppner et al., 2021)** — the six-million simulated-grasp dataset Contact-GraspNet trains on, built on ShapeNet meshes:
  <https://github.com/NVlabs/acronym>
- **GraspNet-1Billion (Fang et al., CVPR 2020)** — the other big grasp benchmark; dense per-point grasp annotations on real RGB-D scenes. Read it for the contrast in the quiz:
  <https://graspnet.net/>
- **ShapeNet** — the mesh source behind ACRONYM; you only need to know what it is:
  <https://shapenet.org/>

## Segmentation (for segmentation-aware grasping)

- **Segment Anything 2 (SAM2, Meta)** — open-weight promptable segmentation; the standard 2026 way to get an object mask for grasping:
  <https://github.com/facebookresearch/sam2>
- **`segment-anything` ROS2 wrappers** — community nodes that publish masks; read one before you write yours:
  <https://github.com/facebookresearch/segment-anything>

## Depth completion / transparent objects (for the challenge)

- **ClearGrasp (Sajjan et al., ICRA 2020)** — the canonical transparent-object depth-completion paper; the reason your mug-of-glass fails and how to fix it:
  <https://sites.google.com/view/cleargrasp>
- **Depth-Anything v2** — a strong monocular-depth model you can use to inpaint the holes a transparent object leaves in a depth image (you met it in week 13):
  <https://github.com/DepthAnything/Depth-Anything-V2>

## API references (the ones you'll have open all week)

- **`torch.nn`** — layers, `Module`, loss functions:
  <https://pytorch.org/docs/stable/nn.html>
- **PyTorch3D `ops`** — `knn_points`, `sample_farthest_points` (if you use the PyTorch3D set-abstraction ops instead of a CUDA kernel):
  <https://pytorch3d.readthedocs.io/en/latest/modules/ops.html>
- **Open3D** — point-cloud I/O, voxel downsample, outlier removal, gripper-mesh viz:
  <https://www.open3d.org/docs/release/>
- **`vision_msgs`** — the message family for detections and (with a small wrapper) grasps:
  <https://github.com/ros-perception/vision_msgs>
- **`tf2_geometry_msgs`** — transforming a `PoseStamped` between frames:
  <https://docs.ros.org/en/jazzy/p/tf2_geometry_msgs/>

## MoveIt2 specifics (the pick)

- **MoveIt2 — Move Group Python interface** (plan and execute to a pose from Python):
  <https://moveit.picknik.ai/main/doc/api/python_api/index.html>
- **MoveIt2 — Cartesian paths** (the straight-line approach and lift segments):
  <https://moveit.picknik.ai/main/doc/examples/move_group_interface/move_group_interface_tutorial.html>
- **`moveit_py`** — the Python bindings used in the exercises:
  <https://moveit.picknik.ai/main/doc/examples/jupyter_notebook_prototyping/jupyter_notebook_prototyping_tutorial.html>

## Talks worth your time (free, no signup)

- **Contact-GraspNet — author talk (ICRA 2021)** — search the ICRA 2021 program / the author's page for the 12-minute presentation; the contact-point animation makes the representation click:
  <https://arxiv.org/abs/2103.14127>
- **NVIDIA Isaac — manipulation & grasping sessions (GTC, free)** — the deployment-side reality of learned grasping:
  <https://www.nvidia.com/gtc/>
- **ROSCon manipulation track** — MoveIt2 pick-and-place and grasp-integration talks, posted free:
  <https://roscon.ros.org/>

## Tools you'll use this week

- **`rviz2`** with the `MarkerArray` display — render proposed grasps as gripper-mesh markers, color by confidence.
- **`Open3D` visualizer** — fast offline check of a cloud + the top-k grasps before you touch ROS2.
- **`message_filters`** (`ApproximateTimeSynchronizer`) — sync color + depth + `camera_info` in the inference node.
- **`ros2 topic hz /grasp_poses`** — confirm the grasp node publishes at the rate you expect (it is a low-rate, on-demand topic, not a stream).
- **`nvidia-smi`** — watch GPU memory while you batch inference; Contact-GraspNet fits easily on 8 GB.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Contact point** | A point on the object surface where a gripper finger will touch. CGN predicts grasps *at* observed points. |
| **Baseline direction** | The vector between the two gripper fingers (the closing axis). Half the grasp parameterization. |
| **Approach direction** | The vector the gripper moves *along* to reach the grasp (the wrist's "forward"). Orthogonal to baseline. |
| **Grasp width** | The opening between the fingers at the grasp, in meters. The third regressed quantity. |
| **PointNet++** | A hierarchical point-cloud network: set-abstraction (downsample + local features) then feature-propagation (upsample back to all points). |
| **Set abstraction** | A PointNet++ layer: farthest-point-sample centroids, group neighbors, run a shared MLP, pool. |
| **ACRONYM** | The 6M-grasp simulated training dataset (ShapeNet meshes + physics-checked grasps). |
| **GraspNet-1Billion** | A competing benchmark with dense real-RGB-D grasp annotations. |
| **Antipodal** | A grasp where two contact normals point at each other within the friction cone — the classical grasp condition. |
| **Force closure** | The grasp can resist any external wrench; the formal "it won't slip" condition. |
| **NMS (grasp)** | Non-maximum suppression over grasps: drop lower-confidence grasps near a higher-confidence one. |
| **Pre-grasp pose** | The pose a fixed standoff back along the approach vector; you plan here, then move in. |
| **Depth completion** | Filling holes in a depth image (e.g. where a transparent object returned nothing) with a learned model. |
| **Grasp frame** | The convention defining where the gripper origin sits relative to the contact/center; must match MoveIt2's EE frame. |

---

*If a link 404s, please open an issue so we can replace it.*
