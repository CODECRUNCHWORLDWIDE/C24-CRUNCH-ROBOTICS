# Week 25 — Grasping Foundations

Welcome to Phase 4, and to the week your arm stops reaching a pose you typed in and starts reaching a *grasp* it computed from the shape of an object. By Friday you will be able to look at a tabletop point cloud and generate, score, and rank grasp candidates by hand — no learned model, no black box — and you will understand, in your fingers, why most grasp failures are not policy failures but *pose* failures. You will read a grasp the way a senior manipulation engineer reads one: as **a pose, plus a width, plus a confidence**, expressed in a gripper frame you can point at on the TF tree.

We assume you finished Week 23 (MoveIt2 on a 6-DOF arm) and Week 24 (the composed base+arm graph under a safety leash). Your arm plans and executes to a pose goal, and the composed graph stops on a latched E-stop. This week the pose goal stops being a constant and starts being the output of a grasp planner. If your Week-23 MoveIt2 setup can't plan to a `geometry_msgs/PoseStamped` you publish, fix that first — the lab this week ends by handing your best computed grasp to exactly that interface.

The one thing to internalize before you read another line: **a grasp is a geometric claim about contact, and the geometry is most of the battle.** A learned grasp network (Week 26's Contact-GraspNet) is segmentation + geometry + a small network — but the *geometry* is the part that decides whether the fingers actually close on the object without pushing it away, and it is the part that is true whether or not you ever train a model. This week is the geometry: force closure and form closure (when is a grasp *stable*?), antipodal grasps (the workhorse heuristic), the gripper-frame convention (where is the grasp, exactly?), and grasp scoring (which candidate do I try first?). Get this right and the learned grasping of next week is a refinement; get it wrong and no network saves you, because the network is trying to predict the same geometry you didn't understand.

This week is where you stop treating a grasp as a magic pose and start treating it as a contact configuration you can reason about, generate, score, and defend.

## Learning objectives

By the end of this week, you will be able to:

- **Define** force closure and form closure precisely, state the difference, and determine for a simple 2D grasp whether a candidate achieves force closure given the contact points and the friction coefficient.
- **Explain** the friction-cone model of a point contact, why a grasp's contact normals must point "into" the friction cones to resist an applied wrench, and how the friction coefficient bounds which grasps are stable.
- **Generate** antipodal grasp candidates on a tabletop point cloud: sample surface points, estimate normals, find antipodal pairs whose connecting line lies within both friction cones, and reject pairs the gripper cannot span.
- **Score and rank** grasp candidates with a heuristic that combines antipodal quality, approach-direction sanity, gripper-width fit, and collision-freedom — and explain why ranking matters more than finding "the one grasp."
- **Express** a grasp in the gripper-frame convention — the approach axis, the closing axis, the grasp point, and the width — and transform it into the arm's planning frame so MoveIt2 can reach it.
- **Situate** your heuristic against the grasp datasets and learned planners that dominate 2026 — ACRONYM, GraspNet-1Billion, Contact-GraspNet — and articulate what the data buys that the heuristic cannot, and where the heuristic still wins.
- **Diagnose** the canonical grasp failures — the pose is off (the most common), the width is wrong, the approach collides, the object is reflective/transparent and the cloud is wrong — and tell a pose failure from a policy failure.
- **Hand** a ranked, reachable grasp to MoveIt2 as a `PoseStamped` and verify the arm can plan to it from the Week-23 setup.

## Prerequisites

This week assumes you have completed **C24 weeks 1–24**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**. `ros2 --version` works; you can build a `colcon` workspace.
- **Python with NumPy and Open3D.** You can load a point cloud, downsample it, and estimate normals. If you did Week 15 (Open3D, ICP), you have this; if not, the lecture's Open3D snippets are self-contained enough to follow.
- **MoveIt2 on a 6-DOF arm (Week 23).** Your arm plans and executes to a `geometry_msgs/PoseStamped` goal. This week's grasp becomes that goal.
- **The composed graph and the safety leash (Week 24).** The grasp is executed by the composed base+arm under the E-stop you measured. "Arm strikes during a grasp" is a hazard-log row from last week; this week makes the grasp that row guards real.
- **TF2 fluency (Weeks 2, 5).** You can transform a pose between frames and you know why a stamped pose carries an honest `frame_id`. The gripper-frame transform is the load-bearing skill of the lab.
- **Linear algebra (Week 1).** Rotation matrices, the SE(3) group, the cross product. A grasp orientation is a rotation you build from three axes.

You do **not** need a learned grasp model this week — that is Week 26. We build the geometry from first principles so that when the network arrives, you know what it is approximating.

## Topics covered

- **Grasp taxonomies.** Force closure (the grasp can resist *any* applied wrench, given friction) vs. form closure (the grasp constrains the object *geometrically*, no friction needed). Why form closure needs more contacts and force closure is what a two-finger gripper actually achieves.
- **The contact model.** Point contact with friction; the friction cone (half-angle `arctan(mu)`); the wrench a contact can apply; why a grasp's contact forces must lie inside the friction cones to be stable.
- **Antipodal grasps.** The two-finger workhorse: a pair of contact points whose surface normals are (anti-)parallel and collinear with the line joining them, so the closing motion squeezes the object rather than pushing it away. The antipodal condition stated with the friction cone, and the sampling algorithm that finds candidates on a cloud.
- **The gripper-frame convention.** A grasp as a frame: the grasp point (origin), the approach axis (how the gripper comes in), the closing/baseline axis (the direction the fingers close), and the standoff. Building the SE(3) grasp pose from the antipodal pair and the surface geometry, and transforming it into the planning frame.
- **Grasp scoring and ranking.** A heuristic score combining antipodal quality (how centered in the friction cones), gripper-width fit, approach-direction sanity (don't approach through the table), and collision-freedom. Why you generate *many* candidates and rank them, and try the top-K, not "the one."
- **Grasp datasets and learned planners (the 2026 landscape).** ACRONYM (simulated grasps on ShapeNet objects), GraspNet-1Billion (real + simulated, the dense-grasp benchmark), and Contact-GraspNet (the learned planner you deploy next week). What the data captures that a heuristic cannot — multimodal grasps, learned object priors — and where the heuristic still earns its keep (no model, no GPU, fully explainable).
- **Grasp failure modes.** The pose is off (the dominant failure — a few millimeters or a few degrees and the fingers miss or knock the object). The width is wrong. The approach collides with the table or the object. The object is transparent or reflective and the depth cloud is garbage (the failure that bites learned planners hardest). Telling a pose failure from a policy failure.
- **Reachability.** A perfect grasp the arm can't reach is no grasp. Checking a candidate against the arm's workspace and MoveIt2's planner before you commit, and pruning unreachable candidates from the ranking.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|-------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Force/form closure; the contact model; friction cones       |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Antipodal grasps; sampling candidates on a cloud            |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | The gripper-frame convention; building the grasp pose       |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Scoring, ranking, reachability; the datasets landscape      |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Hand the grasp to MoveIt2; the failure-mode taxonomy        |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                      |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, top-grasp visualization polish               |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                             | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The grasp-mechanics references, the dataset and planner papers, the Open3D and gripper-geometry docs, and the talks worth your time |
| [lecture-notes/01-grasp-mechanics-force-closure-antipodal.md](./lecture-notes/01-grasp-mechanics-force-closure-antipodal.md) | Force/form closure, the friction-cone contact model, antipodal grasps, and the candidate-sampling algorithm |
| [lecture-notes/02-gripper-frame-scoring-and-the-landscape.md](./lecture-notes/02-gripper-frame-scoring-and-the-landscape.md) | The gripper-frame convention, building and transforming the grasp pose, scoring/ranking/reachability, and the 2026 dataset + learned-planner landscape |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-force-closure-by-hand.md](./exercises/exercise-01-force-closure-by-hand.md) | Determine force closure for 2D grasps by hand, with the friction cone, then check your answers in code |
| [exercises/exercise-02-antipodal-sampler.py](./exercises/exercise-02-antipodal-sampler.py) | Sample and score antipodal grasp candidates on a tabletop point cloud; print a ranked top-10 |
| [exercises/exercise-03-grasp-to-pose.py](./exercises/exercise-03-grasp-to-pose.py) | Turn an antipodal pair into a gripper-frame SE(3) grasp pose and a `PoseStamped` for MoveIt2 |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-grasp-three-objects.md](./challenges/challenge-01-grasp-three-objects.md) | Generate, rank, and visualize reachable grasps for three different objects, and defend why the top grasp is the top grasp |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the grasp-failure postmortem |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_grasp` analytic grasp planner: cloud in, ranked reachable grasps out, top-10 visualized in rviz2 |

## The "a grasp is a pose, a width, and a confidence" promise

C24 uses a recurring marker for every grasp this week: every grasp candidate your code emits prints as exactly those three things, in a named frame:

```
grasp #1  pose=(0.412, -0.085, 0.231) quat=(0.00, 0.71, 0.00, 0.71)  width=0.058 m  conf=0.91  frame=base_link  REACHABLE
```

If a candidate has no width, the gripper doesn't know how far to open. If it has no confidence, you can't rank it. If it has no frame, MoveIt2 can't reach it. A grasp missing any of the three is not a grasp — it's a wish. The point of Week 25 is to make that complete, ranked, framed line ordinary, and to make the *pose* in it the thing you trust the most because you understand the geometry behind it.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement a **3-finger form-closure** check for a simple polygon and contrast the number of contacts it needs with the 2-contact force-closure grasp. Form closure is the "no friction needed" guarantee, and it costs contacts.
- Add **surface curvature** to your scoring: penalize grasps centered on high-curvature regions (edges, corners) where the contact model is least reliable, and reward flat-ish faces. Estimate curvature from the local normal variation in Open3D.
- Render a **gripper mesh** at the top grasp in rviz2 (a `visualization_msgs/Marker` of your gripper's collision geometry) so you can *see* whether the fingers clear the object and the table. This is the single best debugging view for the pose-is-off failure.
- Download a handful of **ACRONYM** grasps for a mug and compare their poses to the grasps your heuristic generates on the same mug's cloud. Where does the learned/simulated grasp set find grasps your heuristic misses?

## Up next

Week 26 takes the grasp geometry you built here and replaces the heuristic with a learned planner — **Contact-GraspNet** — deployed as a ROS2 node that consumes an RGB-D frame and emits ranked grasp poses you pipe into the same MoveIt2 interface you used this week. The lesson of next week only lands if this week's geometry is solid: the network predicts the contacts and approaches you learned to reason about by hand. Push your `crunch_grasp` planner before you start it — Week 26 compares its grasps against yours.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
