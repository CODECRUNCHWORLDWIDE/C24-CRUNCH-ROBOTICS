# Week 25 — Resources

Every resource here is **free**. The grasp-mechanics foundations live in open textbooks and lecture notes; the datasets and learned planners are open-access papers with public code and project pages; the Open3D and ROS2 docs are open. No paywalled book is required for this week.

When a paper has a project page with code and a PDF, the project page is linked — it is the fastest path to both.

## Required reading (work it into your week)

- **Modern Robotics (Lynch & Park) — Chapter 12, "Grasping and Manipulation"** — the free, canonical treatment of force closure, form closure, the friction cone, and grasp wrench analysis. Read §12.1 (contact kinematics) and the closure sections. This is the spine of Lecture 1:
  <https://hades.mech.northwestern.edu/index.php/Modern_Robotics>
- **A Mathematical Introduction to Robotic Manipulation (Murray, Li, Sastry) — Chapter 5, "Multifingered Hand Kinematics"** — the classic grasp-mechanics reference, free PDF from Berkeley; the friction-cone and grasp-matrix material:
  <https://www.cse.lehigh.edu/~trink/Courses/RoboticsII/reading/murray-li-sastry-94-complete.pdf>
- **Open3D — point cloud processing tutorial** — voxel downsampling, normal estimation, and the surface geometry you sample grasps from:
  <https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html>
- **Open3D — surface normal estimation** — the `estimate_normals` API and why the orientation of the estimated normal matters for the antipodal test:
  <https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html#Vertex-normal-estimation>

## The grasp datasets (skim the project pages; you do not train this week)

- **ACRONYM — A Large-Scale Grasp Dataset Based on Simulation** (Eppner et al., 2021) — 17.7M simulated parallel-jaw grasps on ShapeNet objects; the dataset Contact-GraspNet trains on. Project page + paper:
  <https://sites.google.com/view/graspdataset>
- **GraspNet-1Billion — A Large-Scale Benchmark for General Object Grasping** (Fang et al., CVPR 2020) — a billion grasp poses on real cluttered scenes, the standard dense-grasp benchmark, with an evaluation API:
  <https://graspnet.net/>
- **The YCB Object and Model Set** — the standard physical objects (the mug, the box, the drill) that grasp papers benchmark on; useful for sanity-checking your heuristic against objects everyone uses:
  <https://www.ycbbenchmarks.com/>

## The learned planners (the 2026 landscape, deployed next week)

- **Contact-GraspNet — Efficient 6-DoF Grasp Generation in Cluttered Scenes** (Sundermeyer et al., ICRA 2021) — the segmentation-aware learned grasp planner you deploy in Week 26; read the contact-point representation, which is *exactly* the antipodal geometry of this week, learned:
  <https://research.nvidia.com/publication/2021-03_contact-graspnet-efficient-6-dof-grasp-generation-cluttered-scenes>
- **Contact-GraspNet code** (NVIDIA, open) — read the grasp representation to see this week's gripper-frame convention in a real codebase:
  <https://github.com/NVlabs/contact_graspnet>
- **GPD — Grasp Pose Detection in Point Clouds** (ten Pas et al.) — the influential pre-deep-learning sampler that generates and scores antipodal-style candidates on a cloud; the closest published cousin of your mini-project:
  <https://github.com/atenpas/gpd>
- **Dex-Net** (Mahler et al.) — the grasp-quality-CNN lineage; read the abstract for the "grasp robustness as a learned metric" framing that contrasts with this week's analytic score:
  <https://berkeleyautomation.github.io/dex-net/>

## Grasp geometry and gripper conventions

- **`moveit_msgs/Grasp` message** — how MoveIt2 represents a grasp (the grasp pose, the pre-grasp approach, the post-grasp retreat, the gripper posture); the message your planner ultimately fills:
  <https://github.com/moveit/moveit_msgs/blob/master/msg/Grasp.msg>
- **MoveIt2 — pick and place tutorial** — how a grasp pose drives a pick; the approach/retreat vectors and the gripper posture in practice:
  <https://moveit.picknik.ai/main/doc/examples/pick_place/pick_place_tutorial.html>
- **REP 103 — Standard units and coordinate conventions** — the right-hand-rule and frame conventions your gripper-frame grasp pose must obey (x-forward, y-left, z-up); a grasp orientation that ignores this is the silent failure:
  <https://www.ros.org/reps/rep-0103.html>
- **`tf2` — transforming a pose between frames** — the lookup your code uses to move a grasp from the camera/object frame into the arm's planning frame:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>

## Tools you'll use this week

- **Open3D** — `pip install open3d`. Point cloud load, voxel downsample, `estimate_normals`, and the visualizer for sanity-checking candidates.
- **NumPy** — the friction-cone test, the antipodal condition, and the SE(3) grasp-pose construction are all small NumPy.
- **rviz2** — `visualization_msgs/MarkerArray` to draw grasp candidates (arrows for approach, line for the baseline) over the cloud; the best view for the pose-is-off failure.
- **MoveIt2** — the `move_group` action interface you hand the top grasp to as a `PoseStamped`.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Force closure** | The grasp can resist *any* applied wrench, *given friction*. What a two-finger gripper achieves on a good grasp. |
| **Form closure** | The grasp constrains the object *geometrically*, no friction needed. Needs more contacts (≥ 7 for a 3D rigid body). |
| **Friction cone** | The set of contact forces a point contact can apply without slipping; half-angle `arctan(mu)` about the surface normal. |
| **Antipodal grasp** | A two-contact grasp whose contact normals are collinear with the line joining them, so closing squeezes rather than pushes. The workhorse heuristic. |
| **Grasp wrench** | The force + torque a grasp can resist, assembled from the contact forces inside the friction cones. |
| **Gripper frame** | The frame attached to the grasp: origin at the grasp point, axes for approach and finger-closing. |
| **Approach axis** | The direction the gripper moves in to reach the grasp (usually the gripper's +z or +x). |
| **Closing / baseline axis** | The direction the two fingers close along; for an antipodal grasp, the line joining the contacts. |
| **Grasp width** | The finger separation at contact; must be ≤ the gripper's max opening. |
| **Standoff / pre-grasp** | An offset pose along the approach axis where the gripper pauses before the final approach. |
| **Grasp score** | A heuristic ranking number combining antipodal quality, width fit, approach sanity, and collision-freedom. |
| **Reachability** | Whether the arm can actually plan to the grasp pose; an unreachable grasp is no grasp. |

---

*If a link 404s, please open an issue so we can replace it. The textbook chapters and the dataset project pages are canonical and reappear on the same hosts.*
