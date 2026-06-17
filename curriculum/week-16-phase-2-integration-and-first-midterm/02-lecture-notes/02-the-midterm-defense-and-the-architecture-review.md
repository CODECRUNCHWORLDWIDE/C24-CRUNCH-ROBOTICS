# Lecture 2 — Data Association, the Robustness Gates, and the Midterm Architecture Review

> **Reading time:** ~80 minutes. **Hands-on time:** ~70 minutes (you write the detection-to-cluster association, wire the robustness gates, and draft the one-page perception architecture brief you'll defend at the midterm).

Lecture 1 designed the pipeline and budgeted its latency. This lecture does two things: it fuses the streams the pipeline carries (data association — turning a 2D detection and a 3D cluster of the *same* object into one fused object), and it prepares you to defend the whole stack to a panel (the architecture review that gates Phase 2). The fusion is the last piece of engineering; the review is the gate. Both are where the midterm is decided.

## 2.1 — Data association: from two detections to one object

Your pipeline produces two views of the world: 3D clusters from the LiDAR/RGB-D (where things *are*, with size and shape, but no class) and 2D detections from YOLO (what things *are*, with a class and confidence, but in the image plane, no metric position). A fused object needs both: the red *cup* (class, from YOLO) *at map(1.82, −0.41, 0.74)* (position, from the cluster). **Data association** is the matching that pairs them.

The two standard approaches:

**Project the cluster into the image, then IoU-match.** Take each 3D cluster, transform it into the camera optical frame *at the detection's stamp*, project its bounding box through the camera intrinsics into the image plane (the `project3dToPixel` from `image_geometry`), and compute the IoU (intersection-over-union) of that projected box with each YOLO box. The cluster and the detection with the highest IoU above a threshold are the same object. This is the most common approach and the one Exercise 3 builds.

```python
from image_geometry import PinholeCameraModel

def project_cluster_to_image(cluster_3d, tf_to_camera, cam_model: PinholeCameraModel):
    """Transform a 3D cluster into the camera frame (at the right stamp) and
    project its corners to a 2D image box. Returns (u_min, v_min, u_max, v_max)."""
    corners_cam = [tf_to_camera @ corner for corner in cluster_3d.corners()]
    pix = [cam_model.project3dToPixel((c.x, c.y, c.z)) for c in corners_cam
           if c.z > 0]                      # only points in front of the camera
    us, vs = zip(*pix)
    return min(us), min(vs), max(us), max(vs)

def iou(box_a, box_b) -> float:
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter + 1e-9)
```

**Back-project the 2D box's ray and nearest-cluster-match.** The alternative: cast a ray from the camera through the 2D box's center, and match it to the cluster whose centroid is nearest that ray. Cheaper (no projection of every cluster) but less discriminating when objects overlap in the image.

### 2.1.1 The matching is an assignment problem

With multiple clusters and multiple detections, you don't greedily match — you solve the *assignment problem*. Build the IoU matrix (clusters × detections), and find the matching that maximizes total IoU subject to "each cluster matches at most one detection," with the **Hungarian algorithm** (`scipy.optimize.linear_sum_assignment`). Greedy matching produces double-matches and order-dependent results; the Hungarian solver is the correct tool and it's one function call.

```python
from scipy.optimize import linear_sum_assignment
import numpy as np

def associate(clusters, detections, projected_boxes, iou_threshold=0.3):
    """Hungarian assignment of clusters to detections by IoU. Returns matches and
    the unmatched of each (the no-match cases you MUST handle)."""
    cost = np.zeros((len(clusters), len(detections)))
    for i, pbox in enumerate(projected_boxes):
        for j, det in enumerate(detections):
            cost[i, j] = -iou(pbox, det_box(det))   # negative: maximize IoU
    rows, cols = linear_sum_assignment(cost)
    matches, unmatched_clusters, unmatched_dets = [], [], []
    matched_c, matched_d = set(), set()
    for i, j in zip(rows, cols):
        if -cost[i, j] >= iou_threshold:            # only keep good matches
            matches.append((i, j)); matched_c.add(i); matched_d.add(j)
    unmatched_clusters = [i for i in range(len(clusters)) if i not in matched_c]
    unmatched_dets = [j for j in range(len(detections)) if j not in matched_d]
    return matches, unmatched_clusters, unmatched_dets
```

### 2.1.2 The data-association failure modes (handle them explicitly)

- **No-match (a cluster with no detection).** A LiDAR cluster the camera didn't classify — out of the camera's FOV, too small, or YOLO missed it. **You publish it as a 3D object with class `unknown`**, not drop it. An unclassified obstacle is still an obstacle the planner must avoid. The README's milestone report shows "1 LiDAR-only" — that's a correctly-handled no-match.
- **No-match (a detection with no cluster).** YOLO saw something the LiDAR didn't cluster — too far, transparent (Week 14's glass), or a false positive. You typically don't publish a 3D object (no metric position), but you log it, because a persistent unmatched detection is a finding (the LiDAR is blind to something the camera sees).
- **Double-match.** Two clusters project onto one detection (an object split by clustering — Week 15's over-segmentation) or two detections onto one cluster (two objects merged — under-segmentation). The Hungarian solver prevents the *assignment* double-match, but the *underlying* segmentation error is the real bug, upstream. The association exposes it; the fix is in the clustering.
- **Frame/time disagreement.** The cluster is in `map` at stamp `t₁`, the detection in the optical frame at `t₂`. If you project the cluster using the transform at the *wrong* stamp, the projected box is offset and the IoU is wrong — the Lecture-1 §1.5 frame/timing defect, surfacing in the association. **You must transform the cluster into the camera frame at the *detection's* stamp**, or synchronize the two inputs (Week 14's `message_filters`) so `t₁ ≈ t₂`.

The senior stance: **data association is where the frame and timing discipline pays off or fails.** A perfect IoU matcher fed mis-stamped, mis-framed boxes produces garbage matches. Get the frames and stamps right (Lecture 1) and the association is a clean assignment problem; get them wrong and no matcher saves you.

## 2.2 — The robustness gates: one bad input must not corrupt the output

The fused node has four inputs, and any one can go bad: the IMU can saturate, the LiDAR can drop out, the ICP can hit a degenerate corridor and return a wrong transform (Week 15), the camera can be blinded. A perception node that *trusts every input equally* corrupts its whole output when one input lies. The robustness gates are how one bad input gets *de-weighted* instead of *believed*.

**The stamp-age gate (Lecture 1 §1.6).** Reject any input older than a tolerance. Stops the stale-perception race.

**The ICP health gate (Week 15).** The `crunchbot_perception3d` odometry publishes its ICP fitness. When fitness is low (a degenerate or low-overlap scan), the gate *inflates the odometry covariance* it hands the EKF, so the EKF automatically de-weights that measurement. This is the elegance of the EKF: **you don't have to discard a bad input; you tell the filter how much to trust it (via the covariance), and an honest covariance makes the filter ignore garbage on its own.**

```python
def gated_covariance(base_cov, fitness, min_fitness=0.7):
    """Inflate the covariance when ICP fitness is low, so the EKF de-weights it.
    An honest covariance is how the filter ignores a bad input without a hard reject."""
    scale = 1.0 if fitness >= min_fitness else 100.0
    return [c * scale for c in base_cov]
```

**The detection confidence gate.** A YOLO detection below a confidence threshold isn't fused (Week 13 + 14's confidence discipline). A low-confidence class label on a real cluster is worse than no label — it's a *wrong* label the planner might act on.

The principle across all three: **a fused estimate is only as trustworthy as its weakest *honestly-weighted* input.** The gates don't make bad inputs good; they make the node *know* an input is bad and weight it accordingly. The panel will ask "what happens when the LiDAR drops out?" and the answer is "the stamp-age gate stops feeding stale clusters, the ICP health gate inflates the odom covariance, and the EKF coasts on the IMU+wheel-odom with degraded but bounded accuracy — here's the telemetry that shows it." That's a senior answer; "it would break" is not.

## 2.1.5 — Tracking: turning per-frame detections into persistent objects

Data association as described (§2.1) fuses a 2D and 3D detection *within one frame*. There's a second association problem, *across* frames: is the cup I see now the *same* cup I saw last frame, or a new one? Answering it is **tracking**, and while it's a stretch for this week, the concept matters because the capstone's "bring me *the* red cup" needs a stable identity, not a fresh detection each frame.

Tracking is, again, an assignment problem — but now between this frame's objects and last frame's *tracks*. The standard approach:

1. **Predict** each existing track's position into the current frame (a constant-velocity assumption, or a small Kalman filter per track).
2. **Associate** the current detections to the predicted tracks (Hungarian assignment, by distance or IoU — the same machinery as §2.1).
3. **Update** matched tracks with the new detection, **spawn** new tracks for unmatched detections, and **age out** tracks that go unmatched for several frames (the object left, or was occluded).

The result is each object carrying a stable `id` across frames, so a consumer can follow "track 7, the red cup" over time. This is the `id` field of the `Detection3D` message, and it's what lets a behavior tree say "go to the cup I detected" rather than re-detecting every tick.

Two failure modes worth naming: an **identity switch** (two objects cross and their ids swap — the association matched the wrong track), and a **fragmented track** (an object briefly occluded gets a new id when it reappears, because its old track aged out). Production trackers (SORT, ByteTrack, and their 3D cousins) exist precisely to manage these. You don't build a tracker this week — per-frame detection is enough for the midterm — but knowing that tracking is "association across frames, with predict-update-spawn-age," and that it's how a per-frame detector becomes a persistent-object perception system, is the bridge from this week's node to the capstone's needs. When the panel asks "how does the robot follow a specific object over time?", the answer is tracking, and you can describe it even if you haven't built it.

## 2.2.5 — Synchronizing the two streams before you associate

The data association in §2.1 quietly assumed the cluster and the detection describe the world at the *same instant*. They don't, unless you make them. The clustering publishes at ~8 Hz, the YOLO at ~30 Hz, on independent timelines — so the "latest" cluster and the "latest" detection can be 100+ ms apart, and on a moving object that's a different scene. Associating a cluster from `t₁` with a detection from `t₂ ≠ t₁` is the frame/time-disagreement failure (§2.1.2), and it produces wrong matches that no IoU threshold fixes.

The fix is the Week-14 tool, applied at the fusion node: an `ApproximateTimeSynchronizer` over the cluster topic and the detection topic, so the association callback only fires on a *matched set* whose stamps agree within a slop:

```python
import message_filters
from vision_msgs.msg import Detection2DArray, Detection3DArray

clusters_sub = message_filters.Subscriber(node, Detection3DArray,
                                          "/perception/clusters")
dets_sub = message_filters.Subscriber(node, Detection2DArray,
                                      "/perception/detections_2d")
sync = message_filters.ApproximateTimeSynchronizer(
    [clusters_sub, dets_sub], queue_size=10, slop=0.05)   # 50 ms
sync.registerCallback(on_fuse)
```

The slop is a trade-off you must reason about. Too tight (10 ms) and the 8 Hz clusters rarely align with the 30 Hz detections within the window, so fusion starves and most objects publish LiDAR-only. Too loose (200 ms) and you fuse a cluster and a detection of a moving object that have genuinely drifted apart, producing a wrong association. The principled value: a little more than half the *slower* stream's period (8 Hz → 125 ms period → ~50–60 ms slop), so matched sets form regularly but the time spread stays small enough that a slow-moving object hasn't moved much within it.

The deeper point: **data association and synchronization are two halves of the same operation.** You can't associate two views of the world that describe *different* moments; synchronization is what guarantees they describe the *same* moment, so the IoU you compute is comparing apples to apples. A fusion node that associates without synchronizing works on a static scene and fails the instant anything moves — exactly the kind of bug that passes a desk test and fails the live demo at the midterm. Synchronize first; associate second.

## 2.2.6 — Early, late, and deep fusion: where your design sits

The detection-to-cluster association you build is one point on a spectrum of sensor-fusion architectures, and naming the spectrum helps you defend your choice. There are three broad strategies, distinguished by *when* the sensors' information is combined:

**Early fusion (raw-level).** Combine the raw sensor data before any detection — e.g., paint the LiDAR points with camera color (an RGB point cloud) and run a single detector on the fused representation. Strength: the detector sees all modalities at once and can exploit correlations. Weakness: it demands tight spatial and temporal calibration (the frame/timing discipline, at the rawest level) and a detector built for the fused representation.

**Late fusion (detection-level).** Each sensor runs its *own* detector independently, and you fuse the *outputs* — the 3D clusters and the 2D detections — by association. **This is what you build this week.** Strength: modular (each detector is independent and swappable), robust (one sensor failing doesn't break the other's detection), and it reuses the per-sensor detectors you already built (Weeks 13, 15). Weakness: information is lost before fusion (the detectors don't help each other), and the association can fail (the §2.1.2 cases).

**Deep fusion (feature-level).** A learned network fuses intermediate *features* from each sensor — combining early fusion's information-sharing with some of late fusion's modularity. This is where state-of-the-art AV perception lives (the BEVFusion family and its successors), but it requires training a fusion network end to end.

Your week's node is **late fusion**, and that's the right choice for C24: it's modular, it reuses your existing detectors, it's robust to single-sensor failure (the LiDAR-only `unknown` object), and it's interpretable (you can point at exactly where the 2D and 3D detections met). When the panel asks "why detection-level fusion and not early or deep?", the answer is exactly this: modularity, robustness, reuse, and interpretability — and on a robot where you must *debug* the perception and *defend* it, those properties beat the marginal accuracy of a deep-fusion network you can't introspect. Knowing where your design sits on the spectrum, and why you chose it, is the kind of architectural self-awareness that distinguishes a defensible stack from a stack that "just happened to be built that way."

## 2.2.7 — Calibrating the camera-LiDAR extrinsic, the prerequisite nobody mentions

Detection-to-cluster association (§2.1) projects a 3D cluster into the image, and that projection needs the **extrinsic transform between the camera and the LiDAR** — where the camera sits relative to the LiDAR, as an SE(3) transform. If this extrinsic is wrong, every projected cluster lands in the wrong place in the image, every IoU is wrong, and the association silently fails. It's the unglamorous prerequisite that makes or breaks the whole fusion.

Where does this extrinsic come from? Three sources, in decreasing convenience:

- **The URDF.** If your camera and LiDAR are both in the robot's URDF with their mounting positions, the static transforms give you the extrinsic for free, via tf2. This is the common case for a well-modeled robot, and it's why the frame tree (Week 2) matters here.
- **Targetless calibration.** If you don't have an accurate URDF, calibration tools find the extrinsic by matching features the two sensors both see (edges, planes) across many frames. More work, but it handles a robot whose CAD model doesn't match reality.
- **Target-based calibration.** The classic approach: show both sensors a known target (a checkerboard the camera sees, with a shape the LiDAR can localize) and solve for the transform that aligns them. The most accurate, the most setup.

The failure signature of a bad extrinsic: the projected clusters are *consistently* offset from the detections — every cup's projected box is shifted the same direction by the same amount. That consistency is the tell (a frame/timing error is motion-dependent; an extrinsic error is constant), and it points at the camera-LiDAR transform, not the association logic. A panel may ask "how do you know your camera and LiDAR are aligned?" — and "the URDF static transforms, verified by checking that a known object's projected cluster lands on its detection" is the answer. The association is only as good as the extrinsic it projects through; getting that transform right is the silent prerequisite the whole fusion rests on.

## 2.3 — The architecture review: how a panel reads a perception stack

The Phase 2 midterm is a live architecture review. A panel — instructors and/or senior engineers who did *not* build your stack — reads your perception node and asks you to defend it. This is the same format as the Week 32 second midterm, the Week 40 capstone milestone, and the Week 48 defense, so learning to survive it now pays off four times.

A panel reads a perception stack in a predictable order, and knowing the order lets you prepare:

1. **The block diagram.** First they want the data flow: what are the inputs, what are the stages, what's the output. If you can't draw it in thirty seconds, you don't understand your own stack. (You drew this in Lecture 1.)
2. **The interface contracts.** Then they probe the seams: "why `best-effort` on `/points`?" "what frame is `/perception/objects` in?" "what rate does the fusion tick at vs. the clusters publish at?" (Your contract table answers these.)
3. **The latency budget.** Then the number: "what's your end-to-end latency, p95, under load, sensor-stamp to publish?" and "where does the time go?" (Your latency block diagram answers this.)
4. **The failure modes.** Then they stress it: "what happens when the LiDAR drops out / the ICP fails / two cups are on the bench / a detection is stale?" (Your robustness gates and your four-defect framing answer these.)
5. **The numbers.** Finally the measured evidence: the latency distribution, the drift, the association rate. (Your measurements answer these — and "I measured it, here's the script, run it yourself" is the strongest possible answer.)

The failure mode that ends midterms is *not* a weak component — it's a student who can't produce these five things on demand. The student who says "perception is fast and it works" and the student who says "p95 is 28 ms, here's the budget, the critical path is the YOLO hop, the LiDAR-dropout case coasts on the EKF, here's the drift number" are equally good *engineers* — but only the second one passes the gate, because the gate grades the *defense*, not the code.

## 2.3.6 — Reading a stack you didn't build: the reviewer's skill, in reverse

The architecture review puts you on the defending side, but learning to *be* the reviewer sharpens your defense, because you learn what a reviewer looks for. When you review a peer's stack (Challenge 1 has you do exactly this), work the five-layer order in reverse-skeptical mode:

- **The diagram:** does the data flow make sense, or is there a cycle, a missing transform, a stage that can't have the input it needs? A diagram that doesn't close is a design that doesn't work.
- **The contracts:** pick the riskiest seam (usually the one feeding the fusion) and ask "what frame, what rate, what QoS?" If the answer is vague, the seam is a latent bug.
- **The budget:** ask for the *measured* p95, not the design target. "We designed for 30 ms" is not "we measured 28 ms." If they can't produce the measured number, the budget is aspirational.
- **The failures:** name a failure they didn't list ("what if two clusters project onto one detection?") and watch whether they have a handled answer or improvise one. The improvised answer is the unhandled case.
- **The numbers:** ask them to run a script. A number they can reproduce on demand is real; a number on a slide is a claim.

Doing this *to* a peer teaches you what a reviewer does *to you*, and the lesson reflects back: the questions you find yourself asking a peer are the questions you should pre-answer in your own brief. The best preparation for being reviewed is reviewing — you discover the soft spots in someone else's stack, recognize the same soft spots in your own, and harden them before your turn. This is why Challenge 1 has you both present and review: the two roles are the same skill, and you can't defend a stack well until you've learned to attack one.

## 2.4 — The perception architecture brief

The artifact that wins the review is a one-page **perception architecture brief**, written *before* the review, that answers the panel's five questions before they ask. You build it this week (the homework headline deliverable), and it has five sections — one per panel concern:

**1. The block diagram.** The data flow from Lecture 1 §1.1, as a Mermaid diagram or a clean hand-drawing: inputs, stages, output, with the topic names on the edges.

**2. The interface contract table.** The Lecture 1 §1.2 table: every seam's topic, type, frame, rate, QoS. This is the document that answers every "why that QoS / frame / rate?" question.

**3. The latency budget.** The Lecture 1 §1.8 block diagram with measured per-hop costs and the critical-path total. The measured p50/p95/p99. The honest "under load" caveat.

**4. The failure-mode table.** One row per failure: the input that fails, the symptom, the gate that catches it, the degraded behavior. Like an FMEA for perception:

| Failure | Symptom | Gate | Degraded behavior |
|---|---|---|---|
| LiDAR dropout | no `/points` | stamp-age gate stops stale clusters | EKF coasts on IMU+wheel-odom; 3D detections pause |
| ICP degenerate (corridor) | low fitness | health gate inflates odom covariance | EKF de-weights LiDAR odom; drift grows but bounded |
| Two cups on the bench | ambiguous association | (planner-level) | publish both as separate objects; disambiguation is downstream |
| Stale detection | old cluster stamp | stamp-age guard rejects it | wait for next frame; rejection counted in telemetry |
| Budget blowout under load | p95 > 30 ms | (design-level) | quantize YOLO / intra-process; the budget says which hop |

**5. The measured numbers.** Latency p50/p95/p99, drift (m / path length), association rate (% of objects with 2D+3D fusion), and the scripts that produce them. Numbers with scripts, not adjectives.

A brief like this is the difference between a midterm you defend clause by clause and a midterm you hope nobody probes. Write it this week, defend it at the review, and *reuse it* at Week 40 (the capstone perception layer) and Week 48 (the final defense).

## 2.5 — Defending a number under questioning

The hardest moment of the review is when the panel pushes on a number. Three rules for defending one:

**Know the endpoints.** "My latency is 28 ms" invites "of what?" The defensible form is "sensor stamp to `/perception/objects` publish, p95, with the whole graph live." Pin the endpoints (Lecture 1 §1.4) so the number is unambiguous and reproducible.

**Know where it fails first.** "My drift is 0.18 m over 12 m" invites "where does it get worse?" The senior answer: "in the corridor sections where the LiDAR ICP is degenerate — the IMU constrains it, but if I drove a longer featureless stretch the drift would grow; here's the per-step error plot." Knowing the *failure boundary* of your number is what separates measuring from understanding.

**Offer the script.** The strongest possible defense of a number is "here's the script that measures it; run it yourself." A number you can reproduce on demand is unassailable; a number you assert is a claim the panel can poke. The exercises and mini-project build exactly these scripts (the latency probe, the drift measurement) so you *have* them at the review.

The anti-pattern is the defensive crouch: a vague number, hedged, that you can't reproduce and don't know the failure boundary of. The panel smells it immediately, and it's the tell of a student who measured once, got a number they liked, and stopped. Measure honestly, know your failure boundary, bring the script — and the number defends itself.

## 2.6 — The hard gate: consequences and preparation

The Week 16 midterm is a *hard gate*. The syllabus is explicit: "Failures here send you back to the offending week; this is a hard gate." That is more consequential than a weekly quiz, and it changes how you prepare.

**What "back to the offending week" means.** If your defense reveals that your EKF covariances are dishonest (Week 10), or your YOLO node blows the latency budget (Week 13), or your point-cloud clustering merges objects through the floor (Week 15), you go back and fix *that week* before advancing. The midterm is diagnostic — it finds the weak component by composing everything and seeing what breaks. This is a *feature*: the composition surfaces the weakness now, at a resubmittable gate, instead of at the Week 40 capstone milestone where it costs weeks.

**How to prepare.** Three moves:

1. **Self-assess against the brief before the review.** For each of the five brief sections, ask "can I defend this to someone who didn't build it?" An empty or hand-wavy section is a finding *you* should catch before the panel does.
2. **Rehearse the failure-mode questions.** The panel *will* ask "what happens when X fails." Walk your failure-mode table out loud, with a peer playing the panel (Challenge 1 is exactly this rehearsal). The question you can't answer in rehearsal is the one that fails you live.
3. **Measure before you present, not during.** Run the latency probe and the drift measurement *before* the review and have the numbers (and the scripts) ready. A student who measures live, under pressure, with a half-working graph, fails on stage. A student who measured Saturday and brings the report defends calmly.

The midterm is a conversation you can rehearse, against a rubric you can read in advance, with a brief you write beforehand. The students who fail treated it as a surprise; the students who pass treated it as a contract — read the rubric, write the brief, measure the numbers, rehearse the questions. This week is the preparation; the review is the confirmation.

## 2.7 — How this rehearses the capstone

Everything about this midterm is a rehearsal for Phase 6, by design:

- The **fused perception node** is the *exact* perception layer of the Week 40 capstone milestone. You're not building it twice; you're building it once, here, and hardening it there.
- The **30 ms budget** becomes the capstone spec's "≤ 50 ms end-to-end" perception requirement. The budget you draw here, you re-measure there.
- The **drift you bound** becomes the capstone's "< 0.5 m over 20 m" acceptance number. The drift discipline starts here.
- The **architecture-review format** is identical to Weeks 32, 40, and 48. The brief you write here is the template for all three.

A capstone that fails at Week 48 very often failed at Week 16 first — the team never learned to compose, contract, budget, and defend, so the same weaknesses that were resubmittable here became fatal there. Pass this gate *well* — not just pass it — and you carry a validated perception layer, a measurement habit, and a rehearsed defense all the way to graduation.

## 2.3.5 — The questions behind the questions

When a panel asks a question, they're rarely just testing whether you know a fact — they're probing whether you *understand* your system. Reading the question behind the question lets you answer what they actually want to know.

- **"Why that QoS?"** is really *"do you understand the trade-offs your seams make, or did you copy defaults?"* Answer from the Week-5 taste test (reliability vs. latency, durability for late joiners), not "that's what the tutorial used."
- **"What's your latency?"** is really *"can you measure what you claim, and do you know where it goes?"* Answer with the endpoints, the percentile, the critical-path hop — a decomposed number, not a single figure.
- **"What happens when X fails?"** is really *"did you design for failure, or assume everything works?"* Answer with the specific gate and the degraded-but-bounded behavior, demonstrated if possible.
- **"How does the arm know where the cup is?"** is really *"is your frame/timing discipline correct end to end?"* Answer with the chain (`map → base_link → camera`, transform at the detection stamp), because a wrong answer here means every detection is mislocated.
- **"What would you improve?"** is really *"do you understand your system's limits?"* Answer by naming a real limit with a plan — the honesty that §2.7.5 makes the strongest defense.

The meta-skill: **listen for what the panel is actually trying to assess, and answer that.** A learner who hears "why that QoS?" and recites the QoS table has answered the surface question; one who hears "do you understand your seams?" and explains the trade-off has answered the real one. The questions are a probe of understanding, and understanding — not recall — is what the gate measures. When you prepare for the question bank (Challenge 1), prepare not just the answer but *what the question is really asking*, and your defense shifts from "reciting facts" to "demonstrating that I understand the system I built." That shift is the difference between passing and passing well.

## 2.6.5 — Two reviews, two outcomes: a tale from the cohort

It helps to see the difference between a prepared defense and an improvised one, because the gap looks small the week before and decisive on review day. Two composite students, drawn from past cohorts.

**Student Improvise.** They built a genuinely good fused node. The clustering was clean, the YOLO was fast, the demo ran. They walked into the review with the running graph and a confident "it works." Then the panel asked the question bank. "End-to-end latency, p95, under load?" — they'd measured YOLO's inference (14 ms, idle) and said "about 14 ms." The panel pressed: "from the sensor stamp, with clustering running?" They didn't have it; they guessed "maybe 20?" "At what stamp do you transform detections to `map`?" — `now()`, it turned out, so a follow-up drive showed the cup detection 6 cm off, live, in front of the panel. "What happens when the LiDAR drops out?" — "I think the EKF keeps going?" — they weren't sure, because they'd never tested it. The node was good; the defense was not, and the midterm grades the defense. They went back to fix the frame/timing defect and re-measure, and re-defended a week later.

**Student Prepared.** They built an equally good node — and then spent Wednesday and Thursday writing the architecture brief and rehearsing the question bank with a peer (Challenge 1). When the panel asked for latency, they said "p95 is 27 ms, sensor-stamp to publish, under load — here's the probe, the critical path is the 14 ms YOLO hop, I've got 3 ms of headroom." When asked about the transform stamp, "the detection's acquisition stamp via tf2 time-travel; here's the rviz2 view showing detections landing correctly while driving." When asked about LiDAR dropout, they killed the LiDAR live and narrated the dashboard: "stamp-age gate stops stale clusters, the EKF coasts on IMU and wheel odom, drift grows but stays bounded — here's the health topic showing it." They signed the rubric that afternoon.

The two students were equally skilled engineers with equally good nodes. The difference was a brief written at the cheapest moment and a rehearsal that surfaced the unanswerable questions before the panel did. That brief and that rehearsal are the deliverables of this week's challenge and homework — and they're the difference between signing the midterm on the first attempt and re-doing a week's work in front of the panel.

## 2.6.6 — The rubric, demystified

The panel grades against a written rubric, and you should read it the way you'd read a contract (the habit you'll formalize at Week 40). The Phase 2 architecture-review rubric weights roughly:

- **Composition (can you stand the whole stack up, one command, and show it running?)** — the entry ticket. A stack that needs manual `ros2 run` choreography or doesn't run end-to-end caps your score immediately.
- **The interface contract (do you know your seams?)** — answered by your contract table. "Why that frame / QoS / rate" questions.
- **The latency budget (is it measured, decomposed, under load?)** — answered by your block diagram and probe. The single most-weighted technical item, because it's the syllabus's headline number.
- **Frame and timing correctness (detections in `map`, transformed at the right stamp?)** — a near-automatic probe; getting it wrong is a visible, demonstrable defect.
- **Robustness (what happens when an input fails?)** — answered by your failure-mode table and a live demonstration.
- **The defense itself (can you answer the question bank with numbers, not adjectives?)** — the meta-criterion that ties it together.

Knowing the rubric weights tells you where to spend your preparation: the latency budget and the frame/timing correctness are the highest-leverage things to get *demonstrably* right, because they're the most objectively gradable (a number is a number; a transform is right or wrong). The "it works" demo is necessary but not sufficient — it's the entry ticket, not the grade. Read the rubric, map each item to a section of your brief, and self-grade before the panel does.

## 2.7.5 — Honesty as a defense strategy

A counterintuitive but load-bearing point: **the most defensible posture in front of a panel is honesty about your stack's limits.** A student who claims their perception is flawless invites the panel to find the flaw (they always can), and being caught in an overclaim is worse than the flaw itself. A student who says "my drift is 0.18 m on this trajectory, but it degrades in long corridors where the ICP is degenerate — I haven't fused the IMU yet to constrain that, and that's my top Phase-3 action item" has *pre-empted* the panel's hardest question by naming the limit first.

This is the same principle as the safety-case honesty you'll meet at Week 41: a robotics engineer who claims zero risk is not trusted; one who states bounded, justified residual risk is. At the perception review, an engineer who claims perfect perception is not trusted; one who states measured performance *and its failure boundary* is. The panel is not looking for a flawless stack — they know there isn't one. They're looking for an engineer who *understands* their stack, including where it breaks. Naming your limits, with numbers and a plan, is not weakness in the defense — it is the strongest possible demonstration that you understand what you built. The overclaim is the tell of a junior; the honest, bounded, planned account is the tell of a senior. Be the senior.

## 2.7.6 — A walk-through of the full defense, beginning to end

To make the abstract concrete, here is how a strong defense actually flows, narrated, so you can model yours on it. The panel sits down; you have your running graph, your brief, and your scripts open.

**Opening (you drive the first two minutes).** "This is my fused perception node. Four inputs — IMU and wheel odom into the EKF, LiDAR into 3D clustering, the camera into YOLO — fuse into one `/perception/objects` in the map frame. Here's the block diagram." You point at the diagram, trace the data flow, name the output. You've established the architecture before they've asked, which sets the tone: you understand your system.

**The contract probe.** Panel: "Why is `/perception/objects` reliable and `/scan` best-effort?" You: "Sensor streams are best-effort because the next frame fixes a drop and reliability would add head-of-line blocking — that's the Week-5 taste test. The fused output is reliable because a dropped object detection is a missed obstacle the planner needs." You've answered from principle, not memorization.

**The latency probe.** Panel: "What's your end-to-end latency?" You: "27 ms p95, sensor-stamp to publish, under load — measured with this probe, which I can run now. The critical path is the 14 ms YOLO hop; the clustering branch is 9 ms and runs in parallel, so it's `max(14, 9) + 3 fusion + 2 publish`. I have 3 ms of headroom." You run the probe live; the number appears. Unassailable.

**The frame/timing probe.** Panel: "Show me a detection in the map frame and tell me what stamp you transform at." You: "I transform at the detection's acquisition stamp via tf2 time-travel — here's a detection landing at map(1.8, -0.4) while the robot drives; if I used `now()` instead it would shift 5 cm in the direction of motion, here's that version for contrast." You've demonstrated the correct behavior *and* the failure you avoided.

**The robustness probe.** Panel: "Kill the LiDAR." You kill it live. "Watch the health topic: lidar fitness drops, the stamp-age gate stops feeding stale clusters, the EKF covariance for the LiDAR odom inflates, and the filtered estimate coasts on IMU plus wheel odom — drift grows but stays bounded. The 3D detections pause until the LiDAR's back; the 2D detector keeps running." The graph degraded gracefully, observably, and you narrated it.

**The close.** Panel: "Anything you'd improve?" You: "My biggest limit is drift in long corridors where the LiDAR ICP is degenerate — I haven't fused the IMU heading into the odometry yet, which is my top Phase-3 action item. And the YOLO hop is my latency bottleneck; if I needed more headroom I'd quantize it to INT8." You named your limits, with a plan, before they had to dig for them.

That defense passes not because the node is flawless but because *every answer is a measured number or a demonstrated behavior, and the limits are named honestly with a plan.* The panel signs the rubric because they're convinced you understand your stack — which is exactly what the gate is for. Model your defense on this flow: drive the open, answer from principle, demonstrate live, name your limits. It's a performance you can rehearse, and Challenge 1 is the rehearsal.

## 2.7.7 — The one-paragraph mental model to carry forward

Compress this lecture into one model: **the fused node turns two views (the 3D *where* and the 2D *what*) into one object via synchronized, frame-correct, Hungarian-assigned association — with the no-match cases handled honestly and the robustness gates ensuring one bad input is *weighted*, not *believed* — and then you defend the whole thing to a panel with a brief, measured numbers, and named limits.** The fusion is the last engineering; the defense is the gate. Both reward the same discipline: get the frames and stamps right, weight your inputs honestly, measure what you claim, and know where your stack breaks.

And the discipline is portable far beyond this midterm. "Synchronize, then associate; weight inputs honestly; measure the path not the hop; know your failure boundary; defend with reproducible numbers" is the working method of a perception engineer on any team, any robot, any year. The specific algorithms (YOLO, ICP, the EKF) will change; the method will not. That is why the midterm grades the method — the contract table, the latency budget, the failure analysis, the honest defense — and not just the code: the code is this year's, the method is your career's.

That model is the rehearsal for every later gate. The brief you write, the numbers you measure, the honesty about limits — these are the same at Week 32, Week 40, and Week 48, each higher-stakes. A capstone that fails at Week 48 usually failed at Week 16 first, because the team never learned to compose, contract, budget, and defend. Carry the fuse-honestly-and-defend-with-numbers model, pass this gate *well* rather than merely passing it, and you carry a validated perception layer, a measurement habit, and a rehearsed defense all the way to graduation.

One closing reframe to carry past this week: the midterm is not an obstacle the curriculum puts in your way — it is the curriculum *doing you a favor*, at the cheapest possible moment. By composing seven weeks of perception and forcing a defense, it surfaces every weak component, every dishonest covariance, every un-measured latency claim, while fixing them is still a one-week resubmission. The same weaknesses, undiscovered, become fatal at the capstone, where there's no resubmission and the stakes are graduation. So treat the gate as diagnostic, not adversarial: a failed defense that pinpoints "your EKF covariances are dishonest, your latency is un-measured, your detections are mis-framed" is a *gift* — it tells you exactly what to fix before it can hurt you. The students who resent the gate fight it; the students who use it walk into Phase 3 with a perception stack they know is sound, because the gate proved it. Be the second kind, and the first hard gate becomes the thing that makes the rest of the track possible.

## 2.8 — Summary

Data association fuses the two views — the 3D cluster (where) and the 2D detection (what) — into one object, via projection + IoU + the Hungarian assignment, with the no-match (publish LiDAR-only as `unknown`), double-match (upstream segmentation bug), and frame/time-disagreement (transform at the detection's stamp) cases handled explicitly. The robustness gates — stamp-age, ICP health (inflate covariance), detection confidence — ensure one bad input is *honestly weighted*, not believed, so the fused estimate doesn't corrupt. The midterm is a live architecture review that reads your stack in five layers (diagram, contracts, budget, failures, numbers); you win it with a one-page perception architecture brief written beforehand, and you defend a number by pinning its endpoints, knowing its failure boundary, and offering the script. The midterm is a hard gate — failures go back to the offending week — but it's a gate you can rehearse, and it's the rehearsal for the capstone perception layer you'll defend at Week 48.

The five-layer review order — diagram, contracts, budget, failures, numbers — is the lens a panel reads your stack through and the lens you should self-assess with before the review. Write the brief that pre-answers each layer, rehearse the question bank until the unanswerable question surfaces in practice instead of on stage, measure the two numbers (latency p95, drift) you'll be asked for, and name your limits before the panel digs for them. Do that, and the hard gate becomes a confirmation rather than a discovery — and you carry the method forward to the three reviews that follow.

Next: the exercises build the latency budget, the latency probe, and the data-association node; the challenge rehearses the panel defense; and the mini-project is the fused node, measured and defended. Continue to [the exercises](../03-exercises/00-overview.md).

---

**References**

- C24 syllabus, Week 16 + Phase 2 milestone + assessment matrix — `SYLLABUS.md`.
- `vision_msgs` (Detection2DArray / Detection3DArray): <https://github.com/ros-perception/vision_msgs>
- `image_geometry` (`PinholeCameraModel.project3dToPixel`): <https://github.com/ros-perception/image_pipeline>
- `scipy.optimize.linear_sum_assignment` (Hungarian algorithm): <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html>
- `robot_localization` (EKF covariance configuration): <https://github.com/cra-ros-pkg/robot_localization>
- Google SRE Book — "Reliable Product Launches at Scale" (the review discipline): <https://sre.google/sre-book/reliable-product-launches/>
- REP 105 — Coordinate frames: <https://www.ros.org/reps/rep-0105.html>
