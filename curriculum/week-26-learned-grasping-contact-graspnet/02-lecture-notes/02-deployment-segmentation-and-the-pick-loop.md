# Lecture 2 — Deployment: Segmentation, the ROS2 Inference Node, and the Pick Loop

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can build a ROS2 node that consumes a synchronized RGB-D frame, segments the target object, runs Contact-GraspNet, and publishes ranked grasps; transform the top grasp into the planning frame; filter it by IK feasibility; and drive a MoveIt2 pick. You can partition any pick failure into one of four named buckets.

Lecture 1 was the network. This lecture is everything around it that makes it pick up an object on a real robot: getting the right cloud in, grasping the right *object*, getting the pose into the planning frame, and turning a pose into motion that does not collide. Three parts: (1) segmentation-aware grasping, (2) the ROS2 inference node, (3) the MoveIt2 pick and the failure buckets.

---

## Part 1 — Segmentation-aware grasping: grasp the right thing

The naive pipeline runs Contact-GraspNet on the *entire* scene cloud. On a single isolated object that is fine. In any real scene — two objects touching, an object on a cluttered table — it is wrong in a specific, dangerous way: **the network proposes grasps that span two objects**, because locally, the gap between two adjacent objects looks exactly like a graspable concavity. You get a confident grasp that, when executed, jams a finger between the mug and the box and knocks both over.

The fix is segmentation. Before grasping, you decide *which object* you want, produce a mask for it, restrict the input cloud to that object's points, and grasp only those. Then the ranked list is grasps *for the thing you asked for*.

### 1.1 The segmentation step

In 2026 the default is a promptable segmentation model — **SAM2** — prompted by a point, a box, or a text-grounded detection. You met segmentation in week 13. The pattern:

1. Run an object detector (YOLO from week 13, or a text-grounded detector) to get a 2D box or point for the target.
2. Prompt SAM2 with that box/point to get a tight binary mask in the color image.
3. **Lift the mask to 3D:** every depth pixel inside the mask, deprojected with the camera intrinsics, becomes a point in the object cloud. Drop the rest.

```python
import numpy as np


def deproject_masked_depth(depth_m, mask, K):
    """Lift the masked region of a depth image to a 3D point cloud in the camera frame.

    Args:
        depth_m: (H, W) float32 depth in meters (0 = invalid/no return).
        mask:    (H, W) bool, True for the target object's pixels.
        K:       (3, 3) camera intrinsics [[fx,0,cx],[0,fy,cy],[0,0,1]].
    Returns:
        (M, 3) float32 points in the camera optical frame.
    """
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    ys, xs = np.nonzero(mask & (depth_m > 0.0))     # valid AND in-mask pixels
    z = depth_m[ys, xs]
    x = (xs - cx) * z / fx
    y = (ys - cy) * z / fy
    return np.stack([x, y, z], axis=-1).astype(np.float32)
```

Two details that bite:

- **Optical-frame axis convention.** The standard ROS camera optical frame is `z` forward (into the scene), `x` right, `y` down. The deprojection above produces exactly that. If your points come out mirrored or behind the camera, you have an axis-convention mismatch — check the `*_optical_frame` vs `*_link` frame on your `camera_info`.
- **Invalid depth is zero, and you must drop it.** A `depth == 0` pixel is "no return," not "0.1 mm away." Including it puts a spurious point at the camera origin and poisons the cloud. The `depth_m > 0.0` mask above is not optional.

### 1.2 Why segmentation quality drives grasp quality

Garbage mask in, garbage grasps out, in two directions. A mask that is **too tight** (eats the object's edges) starves the network of the very surface points it would grasp. A mask that is **too loose** (leaks onto neighboring objects or the table) re-introduces the spanning-grasp problem you used segmentation to avoid. In the challenge and the mini-project you will see that a 30-minute investment in a clean mask buys more grasp success than any amount of network tuning. **The network is rarely your bottleneck; the segmentation and the depth usually are.**

---

## Part 2 — The ROS2 grasp-inference node

Now wrap the network in a node. The shape:

- **Subscribe** to synchronized color, depth, and `camera_info` (use `message_filters.ApproximateTimeSynchronizer` — the three streams will not have identical stamps). These are **sensor-class topics**: `BEST_EFFORT`, `KEEP_LAST(5)` (week 5). Subscribe with the sensor profile or you will hit the silent-mismatch failure from week 5 and wonder why no frames arrive.
- **On a trigger** (a service call, or every frame if you want a stream), run: segment → deproject → preprocess (crop to workspace, voxel-downsample to a fixed point budget, statistical outlier removal from week 15) → batched GPU inference → reconstruct poses → NMS → rank.
- **Publish** ranked grasps as a `vision_msgs`-style message with a `PoseStamped`, a confidence, and a width per grasp, on a **command-class** topic (`RELIABLE`, `KEEP_LAST`, low rate — it is on-demand, not a stream).

```python
import message_filters
import numpy as np
import rclpy
import torch
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CameraInfo, Image
from geometry_msgs.msg import PoseStamped, PoseArray, Pose


class GraspInferenceNode(Node):
    """Consumes synchronized RGB-D, runs Contact-GraspNet, publishes ranked grasps."""

    def __init__(self, model, segmenter, device="cuda") -> None:
        super().__init__("grasp_inference_node")
        self.model = model.to(device).eval()
        self.segmenter = segmenter
        self.device = device
        self.bridge = CvBridge()
        self.K = None

        # Sensor-class inputs (week 5): BEST_EFFORT / KEEP_LAST(5).
        color_sub = message_filters.Subscriber(
            self, Image, "/camera/color/image_raw", qos_profile=qos_profile_sensor_data)
        depth_sub = message_filters.Subscriber(
            self, Image, "/camera/depth/image_rect_raw", qos_profile=qos_profile_sensor_data)
        info_sub = message_filters.Subscriber(
            self, CameraInfo, "/camera/color/camera_info", qos_profile=qos_profile_sensor_data)
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [color_sub, depth_sub, info_sub], queue_size=5, slop=0.05)
        self.sync.registerCallback(self.on_frame)

        # Command-class output (week 5): RELIABLE, low-rate, on-demand.
        cmd_qos = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                             history=HistoryPolicy.KEEP_LAST, depth=1)
        self.grasp_pub = self.create_publisher(PoseArray, "/grasp_poses", cmd_qos)
        self.target_label = "mug"   # set by a service in the full system

    def on_frame(self, color_msg: Image, depth_msg: Image, info_msg: CameraInfo) -> None:
        self.K = np.array(info_msg.k, dtype=np.float32).reshape(3, 3)
        color = self.bridge.imgmsg_to_cv2(color_msg, "rgb8")
        depth = self.bridge.imgmsg_to_cv2(depth_msg, "passthrough").astype(np.float32)
        if depth.max() > 100.0:          # depth came in millimeters
            depth = depth / 1000.0       # convert to meters; CGN wants meters

        # 1. Segment the target object.
        mask = self.segmenter.segment(color, label=self.target_label)  # (H,W) bool
        if mask.sum() < 200:             # too few pixels to grasp reliably
            self.get_logger().warn(f"segmentation gave {int(mask.sum())} px; skipping")
            return

        # 2. Lift to a cloud (camera optical frame).
        pts = deproject_masked_depth(depth, mask, self.K)              # (M, 3)
        pts = self.preprocess(pts)                                     # crop/voxel/outlier
        if pts.shape[0] < 256:
            self.get_logger().warn("cloud too sparse after preprocessing; skipping")
            return

        # 3. Inference.
        with torch.no_grad():
            cloud = torch.from_numpy(pts).unsqueeze(0).to(self.device)  # (1, M, 3)
            conf, approach, baseline, width = self.model(cloud)
            scores = torch.sigmoid(conf)[0]                             # (M,)
            keep = scores > 0.75
            if keep.sum() == 0:
                self.get_logger().info("no grasp above confidence 0.75")
                self.grasp_pub.publish(PoseArray(header=color_msg.header))
                return
            T = reconstruct_grasp_poses(
                cloud[0][keep],
                approach[0].permute(1, 0)[keep],
                baseline[0].permute(1, 0)[keep],
                width[0][keep],
            )                                                           # (K, 4, 4)
            kept = grasp_nms(T[:, :3, 3], approach[0].permute(1, 0)[keep], scores[keep])

        # 4. Publish ranked, in the camera optical frame; the pick node transforms.
        out = PoseArray(header=color_msg.header)
        for i in kept:
            out.poses.append(mat_to_pose(T[i].cpu().numpy()))
        self.grasp_pub.publish(out)
        self.get_logger().info(
            f"RGB-D frame: {pts.shape[0]} points -> {int(keep.sum())} grasps "
            f"> 0.75 -> {len(kept)} after NMS")

    def preprocess(self, pts: np.ndarray) -> np.ndarray:
        """Workspace crop + voxel downsample + statistical outlier removal (week 15)."""
        import open3d as o3d
        pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
        pcd = pcd.voxel_down_sample(voxel_size=0.005)
        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        return np.asarray(pcd.points, dtype=np.float32)
```

(`mat_to_pose` converts a `4x4` into a `geometry_msgs/Pose` — rotation to quaternion via the orthonormal `R`; you wrote the equivalent in week 1, and the homework asks you to verify it round-trips.)

Three deployment realities encoded above:

- **Depth units.** RealSense and many sim plugins publish depth in **millimeters** as a `uint16`; Contact-GraspNet wants **meters**. The `depth / 1000.0` guard is the most common silent bug — without it every point is 1000× too far and the grasp is nonsense.
- **Guard every stage.** Empty mask, sparse cloud, no confident grasp — each gets an explicit early return that *publishes an empty result and logs why*, rather than crashing or hanging. A grasp node that silently stalls is the worst kind of node to debug at the back of a robot.
- **The output is in the camera frame.** The node does **not** transform to `base_link`; it publishes in the camera optical frame and lets the *pick* node do the tf2 transform at execution time, with the freshest possible transform. Transforming early bakes in a stale TF.

---

## Part 3 — The MoveIt2 pick loop

You have a ranked `PoseArray` of grasps in the camera frame. Turning the top one into a successful pick is four steps: transform, IK-filter, build the trajectory, execute.

### 3.1 Transform to the planning frame

```python
import tf2_ros
from tf2_geometry_msgs import do_transform_pose
from geometry_msgs.msg import PoseStamped


def to_planning_frame(self, grasp_cam: Pose, cam_frame: str, plan_frame="base_link"):
    """Transform a grasp from the camera optical frame into the planning frame."""
    tf = self.tf_buffer.lookup_transform(
        plan_frame, cam_frame, rclpy.time.Time())   # latest available
    ps = PoseStamped(pose=grasp_cam)
    ps.header.frame_id = cam_frame
    return do_transform_pose(ps.pose, tf)            # Pose in plan_frame
```

If this throws `LookupException` or `ExtrapolationException`, your TF tree is broken or the camera frame is not connected to the arm base — a week-2 problem, not a grasping problem. The whole reason the grasp node publishes in the camera frame is so that *this* lookup uses the live transform; if the camera is hand-mounted and moving, an early transform would be stale.

### 3.2 IK-feasibility filtering

Not every confident grasp is reachable. Before you commit to a grasp, ask MoveIt2 whether an IK solution exists for the gripper pose (and for the **pre-grasp** pose a standoff back along the approach). Walk the ranked list and take the first grasp that is reachable for *both*.

```python
def first_reachable(self, grasps_plan_frame, standoff=0.10):
    """Return the highest-ranked grasp whose grasp AND pre-grasp poses are IK-feasible."""
    for pose in grasps_plan_frame:                 # already confidence-ranked
        pre = back_off_along_approach(pose, standoff)   # standoff m back along +z
        if self.ik_feasible(pre) and self.ik_feasible(pose):
            return pose, pre
    return None, None                               # nothing reachable -> fallback
```

`ik_feasible` calls MoveIt2's `compute_ik` service (or `moveit_py`'s IK) and checks for a returned solution within joint limits and free of collision. The pre-grasp check matters because a grasp can be reachable while the straight-line approach to it passes through the table or a joint limit.

### 3.3 Build and execute the pick sequence

A pick is not one motion. It is a sequence:

1. **Pre-grasp:** plan a free-space motion (`OMPL`/RRT*) to the standoff pose.
2. **Approach:** a **Cartesian** straight-line move from pre-grasp to grasp, along the approach vector — you want a straight, predictable insertion, not an arbitrary planned path that might swing the gripper through the object.
3. **Close gripper:** actuate the gripper to (slightly less than) the predicted width.
4. **Lift:** a Cartesian straight-line move up (e.g. 12 cm) to confirm the object is held.
5. **Retreat/place:** out of scope this week (next week's tasks build on it).

```python
def execute_pick(self, grasp_pose, pre_grasp_pose, grasp_width):
    """Pre-grasp (planned) -> approach (Cartesian) -> close -> lift (Cartesian)."""
    if not self.move_group.plan_and_execute(pre_grasp_pose):
        return self.fail("approach-plan")                       # bucket: planning
    if not self.cartesian_move(pre_grasp_pose, grasp_pose):
        return self.fail("approach-cartesian")                  # bucket: planning
    self.gripper.close_to(max(grasp_width - 0.005, 0.0))        # slight over-close
    lift = translate_z(grasp_pose, +0.12)
    if not self.cartesian_move(grasp_pose, lift):
        return self.fail("lift")                                # bucket: execution
    if not self.object_held():                                  # gripper not fully closed
        return self.fail("slip")                                # bucket: execution
    self.get_logger().info("pick SUCCESS")
    return True
```

The `close_to(width - 0.005)` "slight over-close" gives the gripper 5 mm of squeeze past the predicted width so it actually grips rather than barely kissing the surface — a small but real detail. `object_held()` checks the gripper did not fully close (full closure = empty gripper = slip).

---

## Part 4 — The four failure buckets

When a pick fails — and early on, most do — the single most valuable habit is to put the failure in a **named bucket** so you know where the next hour goes. Every pick failure is one of four:

| Bucket | Symptom | Where it lives | Typical fix |
|---|---|---|---|
| **Perception** | The cloud is wrong: holes (transparent), garbage depth (reflective), bad segmentation (mask leaks/eats). | Upstream of the network. | Depth completion; better mask; multi-view. |
| **Prediction** | Clean cloud, but no confident grasp, or the top grasp is geometrically silly. | The network. | Lower threshold cautiously; check the cloud is in *meters*; check the gripper-frame convention. |
| **Planning** | Confident, reachable-looking grasp, but MoveIt2 returns no plan or the pre-grasp is infeasible. | tf2 + IK + planner. | IK-filter the list; widen standoff; check TF; check collision scene. |
| **Execution** | Plan executes, but the object slips, the gripper closes empty, or the lift drops it. | The gripper + the grasp width/pose. | Over-close; check width units; check the contact-to-center sign (Lecture 1 §3). |

The discipline: **before you change anything, look at the symptom and assign the bucket.** A perception failure dressed up as a prediction failure (the transparent object — "the network gave a bad grasp" when really the cloud had a hole) is the classic misdiagnosis, and it sends people to retrain a network when they should fix a depth image. The homework's success-rate report makes you tabulate failures *by bucket*, because the bucket histogram tells you what to fix.

### 4.1 The transparent / reflective failure, named precisely

Contact-GraspNet's documented weakness is transparent and reflective objects. Now you can say *why* precisely: **structured-light and ToF depth sensors return no depth for transparent objects (the IR passes through) and garbage depth for mirror-finish objects (the IR scatters).** So the cloud has a hole or noise exactly where the object is. The network, being honest, predicts no grasp where it has no points — and that is *correct behavior given its input*. The failure is a **perception** failure, not a **prediction** failure. The fix is **depth completion** — a learned model (ClearGrasp, or Depth-Anything-v2 inpainting from week 13) that fills the hole with a plausible surface — applied *before* the cloud is built. That is exactly the challenge this week.

---

## 5. The classical fallback (the leash)

The syllabus pattern, established here and central to Phase 4: **ship the learned policy with a fallback.** When Contact-GraspNet returns no grasp above threshold — empty cloud, novel object, an honest "I don't know" — the system must not stall. It falls back to the **week-25 antipodal sampler**: a heuristic that, given any cloud with points, will propose *some* grasp (lower quality, but a grasp). The fallback is worse on average and never fails to produce an answer, which is exactly what you want as a floor.

```python
def get_grasp(self, cloud):
    """Learned grasp if confident; otherwise the week-25 antipodal heuristic."""
    grasps, scores = self.contact_graspnet(cloud)
    if len(grasps) and scores.max() > 0.75:
        return grasps[scores.argmax()], "learned"
    self.get_logger().warn("CGN unconfident; falling back to antipodal sampler")
    return self.antipodal_fallback(cloud), "fallback"   # week-25 heuristic
```

The mini-project requires this fallback and asks you to *measure the intervention rate* — what fraction of picks used the fallback. A high intervention rate is itself a signal: your perception is failing often enough that the learned policy rarely gets a clean cloud.

---

## 6. Recap

You should now be able to:

- Explain why grasping the segmented target object beats grasping the whole scene, and how a 2D mask lifts to a 3D object cloud.
- Build a ROS2 grasp-inference node with synchronized RGB-D input (correct sensor QoS), depth-unit handling, staged guards, and a ranked grasp output in the camera frame.
- Transform a grasp into the planning frame with live tf2, filter the ranked list by IK feasibility (grasp *and* pre-grasp), and build the pre-grasp → approach → close → lift sequence with planned and Cartesian segments.
- Partition any pick failure into perception / prediction / planning / execution, and name the transparent-object failure as a perception (sensor) failure with a depth-completion fix.
- Wrap the learned grasp in the week-25 antipodal fallback and measure the intervention rate.

Next: the exercises put all of this on your week-23 arm and week-14 camera. Continue to [the exercises](../03-exercises/00-overview.md).

---

## References

- *Contact-GraspNet* (Sundermeyer et al., ICRA 2021): <https://arxiv.org/abs/2103.14127>
- *MoveIt2 pick-and-place / move-group tutorials*: <https://moveit.picknik.ai/main/doc/examples/move_group_interface/move_group_interface_tutorial.html>
- *SAM2* (Meta): <https://github.com/facebookresearch/sam2>
- *ClearGrasp* (transparent-object depth completion): <https://sites.google.com/view/cleargrasp>
- *`message_filters` time synchronization*: <https://docs.ros.org/en/jazzy/p/message_filters/>
- *`tf2_geometry_msgs`*: <https://docs.ros.org/en/jazzy/p/tf2_geometry_msgs/>
- *`vision_msgs`*: <https://github.com/ros-perception/vision_msgs>
