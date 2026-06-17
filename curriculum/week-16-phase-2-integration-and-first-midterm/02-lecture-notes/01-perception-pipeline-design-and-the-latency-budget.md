# Lecture 1 — Perception Is a Pipeline, Pipelines Have Budgets, Defend Yours

> **Reading time:** ~75 minutes. **Hands-on time:** ~60 minutes (you turn your perception graph into an interface-contract table and a latency block diagram with a measured budget, both of which you reuse for the rest of the track).

For seven weeks you built perception components and tested each one alone. This week you compose them into one fused node, and the first thing you discover is the thing every robotics engineer discovers: **a perception stack is not a pile of correct components. It is a *pipeline*, and a pipeline has two properties a pile does not — a set of *contracts* between its stages, and a *latency budget* that the whole path must meet.** The components were the easy part. The contracts and the budget are where the midterm is won and lost.

This lecture is about designing the pipeline and defending its budget. The next lecture is about the data association that fuses the streams and the architecture review that grades you. Both are unglamorous. Both are where Phase 2 ends — at a hard gate where a panel asks for a number and you either have it or you don't.

## 1.1 — The end-to-end perception graph

Open a blank page and draw the data flow, because you cannot reason about a pipeline you have not drawn. The C24 fused perception node composes four input streams into one output:

```
  IMU ─────────┐
               ├──► EKF (robot_localization) ──► /odometry/filtered
  wheel odom ──┘            │                         │
                            └──► map→odom, odom→base_link TF
                                          │
  LiDAR / RGB-D cloud ──► 3D clustering ──┴──► 3D detections (Detection3DArray, map frame)
                                                        │
  camera image ──► YOLO (TensorRT) ──► 2D detections ───┤
                                                        ▼
                                          FUSION (data association)
                                                        │
                                                        ▼
                                          /perception/objects  (Detection3DArray, map frame)
```

Four sensor inputs, three processing branches (state estimation, 3D detection, 2D detection), one fusion stage, one output. Read the graph and the integration risk lights up immediately: **everything routes through the EKF's transforms.** The 3D detections need `map → odom → base_link → lidar` to put a cluster in the `map` frame; the 2D detections need the camera extrinsic on top of that; the fusion needs both branches in the *same* frame at the *same* stamp. The EKF is the high-fan-in, high-fan-out node, and it is where the frame/timing defects cluster — which tells you, before you write a line, where to spend Tuesday's integration hours.

## 1.2 — The interface contract: topic, type, frame, rate, QoS

A pipeline's stages talk over topics, and *every seam is a contract*. The contract has five fields, and a disagreement in any one is a silent failure (Week 5 taught you this for QoS; it generalizes). Write the contract down — the **interface contract table** — before you compose, because composition fails at the seams, not inside the components.

Here is the interface contract for the fused perception graph:

| Producer | Consumer | Topic | Type | Frame | Rate | QoS |
|---|---|---|---|---|---|---|
| IMU driver | EKF | `/imu/data` | `sensor_msgs/Imu` | `imu_link` | ~200 Hz | best-effort, keep-last 10 |
| wheel odom | EKF | `/wheel/odometry` | `nav_msgs/Odometry` | `odom`→`base_link` | ~50 Hz | reliable, keep-last 10 |
| EKF | clustering, fusion | `/odometry/filtered` | `nav_msgs/Odometry` | `odom`→`base_link` | ≥ 30 Hz | reliable, keep-last 10 |
| LiDAR/RGB-D | clustering | `/crunchbot/points` | `sensor_msgs/PointCloud2` | `lidar`/`camera_optical` | ≥ 10 Hz | best-effort, keep-last 5 |
| clustering | fusion | `/perception/clusters` | `vision_msgs/Detection3DArray` | `map` | ≥ 8 Hz | reliable, keep-last 5 |
| camera | YOLO | `/camera/color/image_raw` | `sensor_msgs/Image` | `camera_optical` | ~30 Hz | best-effort, keep-last 5 |
| YOLO | fusion | `/perception/detections_2d` | `vision_msgs/Detection2DArray` | `camera_optical` | ~30 Hz | reliable, keep-last 5 |
| fusion | Phase 3 | `/perception/objects` | `vision_msgs/Detection3DArray` | `map` | ≥ 8 Hz | reliable, keep-last 10 |

Read each column for the defect it guards against:

- **The frame column** is where the frame/timing mismatch hides. The clustering publishes in `map`, but the cloud arrives in the camera optical frame — there *must* be a valid `tf2` chain to transform it, and you *must* look up that transform at the cloud's stamp, not `now()` (more in §1.5). The YOLO detection is in the camera optical frame; fusing it with a `map`-frame cluster means transforming one into the other.
- **The rate column** is where the stale-perception race hides. The clusters publish at 8 Hz, but the fusion ticks faster; a detection can be ~125 ms old by the time fusion uses it. The consumer needs a stamp-age guard (§1.6).
- **The QoS column** is where the silent-drop defects hide. `/perception/objects` is `reliable` because a dropped object detection is a missed obstacle; the sensor streams are `best-effort` because the next frame fixes a drop (Week 5's taste test, applied).

The discipline: derive the contract table from the graph *before* you compose, and treat every row as a bilateral agreement both producer and consumer must honor. When the fused object lands in the wrong place, the bug is almost always a frame-column disagreement nobody wrote down. When fusion grabs stale data, it's a rate-column disagreement nobody wrote down. The table is how you write them down; the pre-flight-style check (Exercise 1) is how you verify them at bring-up.

## 1.3 — The latency budget: a sum of hops, not a wish

The syllabus says "30 ms end-to-end cycle." That is not a vibe — it is a *budget*, and a budget is a sum of line items. You cannot defend a budget you have not decomposed, and "it feels fast" is not a line item. The latency block diagram draws every hop from sensor stamp to `/perception/objects` publish, with a measured cost per hop:

```
  [sensor acquisition + driver]   camera exposure -> /image_raw published     ~3 ms
            │
  [transport: image -> YOLO]      DDS / intra-process                          ~1 ms
            │
  [YOLO inference (TensorRT)]      640x480 on Orin Nano                        ~12 ms
            │
  [transport: detection -> fusion]                                            ~1 ms
            │  (in parallel:)
  [cloud -> clustering]            voxel + ground + cluster                    ~8 ms
            │
  [fusion: data association]       project + IoU match + transform             ~3 ms
            │
  [transform to map + publish]     tf2 lookup + serialize                      ~2 ms
            ▼
  /perception/objects published
  ─────────────────────────────────────────────────────────────────────────────────
  END-TO-END (critical path) = max(YOLO path, cloud path) + fusion + publish ≈ 18 ms
```

Two things this diagram teaches that a single number never could:

**The end-to-end latency is the *critical path*, not the sum of everything.** The YOLO branch (12 ms) and the clustering branch (8 ms) run *in parallel* — the fusion waits for the slower of the two, not both. So the budget is `max(branches) + fusion + publish`, not `sum(all hops)`. Drawing the diagram is what reveals the parallelism; a single "30 ms" number hides it.

**"Inference time" is not "end-to-end latency."** The most common midterm failure is a student who measured YOLO's inference at 12 ms and reports "12 ms perception." The panel asks "from the sensor stamp?" and the real number — acquisition + transport + inference + association + transform + publish — is 18–25 ms. The *hop you forgot* is the one the panel finds. The block diagram forces you to account for every hop, so there's no forgotten one.

The budget is also where you find the *blowout under load* (§1.7): each hop measured idle is optimistic, because under load the YOLO and the clustering contend for the GPU/CPU and both inflate. The honest budget is measured with the whole graph live, which is exactly why this is an integration-week measurement, not a Week-13 one.

## 1.4 — Measuring end-to-end latency honestly

The budget's line items are *measurements*, and a measurement implies a script. The end-to-end perception latency is the difference between two timestamps you can read off the messages: the *sensor stamp* on the input and the *publish stamp* on `/perception/objects`. The trick is carrying the original sensor stamp *through* the pipeline so the output knows when its input was acquired.

```python
# The pattern: every stage PRESERVES the originating sensor stamp (Week 5 §3.1),
# so the fused output's header.stamp is the SENSOR's acquisition time, not now().
# Then the latency is (now - output.header.stamp) measured at publish, OR the
# probe subscribes to the output and compares output.header.stamp to the wall
# clock at receipt.

import rclpy
from rclpy.node import Node
from vision_msgs.msg import Detection3DArray
import numpy as np


class LatencyProbe(Node):
    def __init__(self):
        super().__init__("latency_probe")
        self.samples = []
        self.create_subscription(Detection3DArray, "/perception/objects",
                                 self.on_objects, 10)

    def on_objects(self, msg: Detection3DArray):
        # header.stamp is the SENSOR acquisition time, carried through the pipeline.
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        now = self.get_clock().now().nanoseconds * 1e-9
        self.samples.append((now - stamp) * 1000.0)   # ms

    def report(self):
        a = np.array(self.samples)
        self.get_logger().info(
            f"end-to-end latency: p50={np.percentile(a,50):.1f} "
            f"p95={np.percentile(a,95):.1f} p99={np.percentile(a,99):.1f} ms "
            f"over {len(a)} samples")
```

The non-negotiables:

1. **Carry the sensor stamp through every stage.** If any stage re-stamps with `now()`, the measurement is meaningless — you'd be measuring zero. The whole pipeline must preserve `header.stamp = the original sensor acquisition time` (Week 5 §3.1). This is also a *correctness* requirement, not just a measurement one: tf2 and the consumers downstream need the honest stamp.
2. **Report p95/p99, not the mean.** A mean of 18 ms with a p99 of 80 ms is a *worse* perception system than a flat 28 ms, because the 80 ms tail is where a fast-moving object's detection goes stale and the grasp targets where it *was*. The panel will ask for the percentile; default to p95 (the worst common case) and have p99 ready.
3. **Measure with the whole graph live, under load.** Idle numbers lie. The 30 ms budget is implicitly "during a run, with the YOLO and the clustering both working." Exercise 2 is this probe, and the mini-project runs it as the milestone measurement.

## 1.5 — Frame discipline: the transform and the stamp you look it up at

The frame/timing mismatch is the subtlest perception-integration defect, and it has two halves people conflate. Putting a detection in the `map` frame requires (a) a valid `tf2` chain and (b) looking the transform up *at the right time*.

**The chain.** `map → odom → base_link → lidar_link` (and `→ camera_optical` for the camera). The EKF publishes `map → odom`; the wheel odom publishes `odom → base_link`; the URDF static transforms publish `base_link → sensor`. If any link is missing or stale, `tf2` throws `LookupException` (the loud failure — you'll catch it) or, worse, the chain is *there* but wrong, and the detection lands confidently in the wrong place. REP 105 is the law here.

**The stamp.** Here is the half people get wrong. A detection was acquired at time `t` (the sensor stamp). To transform it into `map`, you must look up the transform *at time `t`*, not at `now()` — because the robot moved between `t` and `now()`, and the `map → base_link` transform at `now()` is for where the robot *is*, not where it *was* when it saw the object.

```python
# WRONG: look up the transform at "now" for a detection acquired in the past.
tf = tf_buffer.lookup_transform("map", det.header.frame_id,
                                rclpy.time.Time())          # latest available
# This transforms the OLD detection with the CURRENT robot pose -> wrong place.

# RIGHT: look up the transform at the detection's acquisition stamp.
tf = tf_buffer.lookup_transform("map", det.header.frame_id,
                                det.header.stamp,            # time-travel to t
                                timeout=Duration(seconds=0.1))
# tf2's time-travel gives the transform AS IT WAS when the detection was made.
```

This is what tf2's "time travel" (Week 2) is *for*. On a robot moving 1 m/s, looking up the transform at `now()` instead of the detection stamp injects motion-proportional error — centimetres per 10 ms of staleness — that puts the object in the wrong `map`-frame cell. The panel may well ask "at what stamp do you transform your detections?" and "the detection's acquisition stamp, via tf2 time-travel" is the senior answer; "the latest transform" is the answer that fails.

## 1.6 — The stale-perception race and the stamp-age guard

The rate column of the contract table (§1.2) sets up a race: the clustering publishes at 8 Hz (125 ms period), the fusion ticks faster, so on a slow frame the "latest" cluster the fusion grabs is 150 ms old. The object may have moved; the detection is stale; the fused object is wrong.

The pre-flight-style check verifies the *rate* once at bring-up, but the rate being correct does *not* prevent a single late frame from being used stale. The runtime guard is a **stamp-age check at the point of use**:

```python
def fresh_enough(msg_stamp, clock, max_age_s=0.15) -> bool:
    """Reject a message older than max_age_s. The stale-perception guard."""
    age = clock.now() - rclpy.time.Time.from_msg(msg_stamp)
    return age.nanoseconds * 1e-9 <= max_age_s


def on_fuse(self, clusters, detections_2d):
    if not fresh_enough(clusters.header.stamp, self.get_clock()):
        self.stale_rejections += 1
        return            # don't fuse a stale cluster; wait for the next one
    ...
```

The `max_age_s` is set from the consumer's tolerance: a fusion node feeding a 1 m/s robot's planner can tolerate ~150 ms (15 cm of motion); a fast manipulation loop wants tighter. Reporting `stale_rejections` in the node's telemetry (the "0 stale detections rejected this window" line in the README's milestone report) is how you *show* the guard is working — and a non-zero count is a signal that a producer is too slow, which is a real finding, not noise.

## 1.7 — The four perception-integration defects

The pre-flight check and the runtime guards exist to catch four canonical defects. Know them, because each maps to a specific fix, and the panel will name them.

**1. The frame/timing mismatch.** Detections in the wrong frame, or transformed at the wrong stamp (§1.5). Symptom: objects appear in the wrong place in `map`, often shifted in the direction of robot motion. Fix: valid `tf2` chain (REP 105) + look up the transform at the detection's acquisition stamp via time-travel.

**2. The stale-perception race.** A fast consumer uses a slow producer's out-of-date data (§1.6). Symptom: the fused object lags a moving object; the grasp targets where it *was*. Fix: a stamp-age guard at the point of use, plus reporting the rejection count.

**3. The data-association failure.** The 2D camera detection and the 3D cluster of the *same* object never get fused (no-match), or two objects get merged (double-match), or the two are in different frames at different stamps so the association math is comparing apples to oracles. Symptom: an object has a 3D box but no class label (LiDAR-only), or a class label on the wrong box. Fix: the association in Lecture 2 — project into a common frame at a common stamp, IoU/nearest-match, handle no-match and double-match explicitly.

**4. The latency-budget blowout under load.** The pipeline meets 30 ms idle but blows it to 70 ms when the YOLO and the clustering contend for the GPU/CPU (§1.3). Symptom: latency p95 fine in a quiet test, terrible during a real run. Fix: measure under load (not idle), intra-process composition to cut transport, and — if needed — schedule the contending work (quantize the detector, move clustering off the GPU, or pipeline the stages).

The lesson: **the integration defects are not bugs in your components; they are disagreements *between* your components, and they only appear when the graph is live.** That is why this is a composition week and a midterm, not another component week. The component that passed its unit test in Week 13 may still blow the budget in composition — and finding that out *this* week, at a resubmittable midterm, is far cheaper than finding it out at the Week 40 capstone milestone.

## 1.8 — A worked latency budget for the fused node

Talk is cheap; here is the budget built out for the C24 fused node on an Orin Nano (Path A), at the precision the exercise demands. Study the *critical path* — it's `max(branches) + tail`, not the sum.

| Hop | Cost (ms) | Branch | Notes |
|---|---:|---|---|
| Camera acquisition + driver | 3 | 2D | exposure to `/image_raw` |
| Transport image → YOLO | 1 | 2D | intra-process if composed |
| YOLO inference (TensorRT FP16, 640×480) | 12 | 2D | the dominant 2D-branch hop |
| Transport detection → fusion | 1 | 2D | |
| Cloud acquisition + driver | 3 | 3D | RealSense depth → `/points` |
| Voxel + ground + cluster (Open3D) | 8 | 3D | the dominant 3D-branch hop |
| Transport clusters → fusion | 1 | 3D | |
| Fusion: project + IoU + associate | 3 | join | both branches present |
| Transform to `map` + serialize + publish | 2 | tail | tf2 time-travel lookup |

- **2D branch total:** 3 + 1 + 12 + 1 = **17 ms**
- **3D branch total:** 3 + 8 + 1 = **12 ms**
- **Critical path:** `max(17, 12)` + 3 (fusion) + 2 (publish) = **22 ms** — inside the 30 ms budget, with 8 ms of headroom.

Now the honest part: those are idle hops. Under load, YOLO and clustering contend, and the real p95 might be 28 ms — still inside, but the headroom is gone. If the measured p95 were 35 ms, the budget tells you *where* to cut: the YOLO hop dominates, so quantize it to INT8 (Week 13's lever) or drop the resolution, because shaving the 8 ms clustering hop wouldn't help the critical path (it's on the shorter branch). **The budget doesn't just tell you the number; it tells you which hop to optimize.** That is why you draw it before you optimize, and why "make it faster" without the diagram is guessing.

## 1.9 — From the budget to the defense

The latency budget and the interface contract are not Week-16 throwaways; they are the spine of your midterm defense (Lecture 2) and the perception layer of your capstone:

- The **interface contract table** answers the panel's "why that QoS / frame / rate?" questions before they're asked.
- The **latency block diagram** answers "what's your end-to-end latency, and where does it go?" with a decomposed number.
- The **four-defect framing** answers "what happens when X fails?" — you point at the guard that catches it.

A midterm that fails almost always fails because the student treated perception as a pile of components and could not produce the contract or the budget when the panel asked. The hour you spend drawing the contract table and the latency diagram this week is the cheapest insurance in Phase 2 — and the diagrams you draw are *reused* at Week 40 (the capstone's ≤ 50 ms perception requirement is this budget, scaled) and Week 48 (the defense is this defense, harder).

## 1.10.5 — Designing `/perception/objects`: the message that carries the contract

The unified output topic is the interface to all of Phase 3, so its message design (Week 5's discipline) is load-bearing. You publish `vision_msgs/Detection3DArray`, and each `Detection3D` must carry enough that a *downstream* consumer — Nav2, the behavior tree, a grasp planner — can act without re-deriving anything. The fields that matter:

- **`header`** — stamped with the originating sensor's *acquisition* time (so latency is measurable and tf2 lookups are honest), `frame_id = map` (so every consumer shares one frame). Non-negotiable; a `now()`-stamped, optical-frame output breaks every consumer.
- **`bbox`** (a `BoundingBox3D`) — the object's center pose, size, and orientation, from the cluster's oriented bounding box (Week 15). This is the *where* and *how big*.
- **`results`** (a list of `ObjectHypothesisWithPose`) — the class id and confidence, from the associated YOLO detection. This is the *what*. A LiDAR-only object carries a single hypothesis with class `unknown` and score 0 — present, but honestly unclassified.
- **`id`** — a stable identifier if you track objects across frames (the mini-project stretch), so a consumer can follow "the red cup" over time rather than re-discovering it each frame.

The design principle from Week 5 applies directly: **compose standard types, stamp honestly, and don't make a consumer re-derive what you already know.** A `Detection3DArray` in `map` with class, position, size, and confidence per object is a complete, self-describing perception output — a planner reads it and acts. The anti-pattern is a custom message that's structurally `Detection3DArray` but incompatible with the tooling (rviz2's detection display, the Nav2 obstacle layers that consume `vision_msgs`), buying you nothing and costing every integration. Reach for the standard type, fill it honestly, and the seam to Phase 3 is clean.

There's also a versioning consideration (Week 5 §3.4): once Phase 3 depends on `/perception/objects`, its message shape is an API. If you later add a field (a velocity estimate, a tracking id), the type hash changes and every consumer must rebuild — so design the message *now*, at the midterm, with the fields Phase 3 will need, rather than churning it every week. The reviewer may ask "what does your perception publish, and is it stable for Phase 3 to build on?" — and a thought-through `Detection3DArray` is the answer.

## 1.11 — Cutting the budget: the levers, in order of value

When your measured p95 is over budget, you don't guess — the latency block diagram tells you the dominant hop on the critical path, and you reach for the levers in order of value-per-effort. The ROS2-perception toolkit, from cheapest to most invasive:

**1. Intra-process composition (biggest lever, smallest effort).** If your nodes run in separate processes, every topic message is *serialized*, sent over DDS, and *deserialized* — for a 640×480 image or a 300k-point cloud, that's milliseconds of pure overhead per hop, several times in the path. Loading the nodes into one process as composable components lets ROS2 pass messages by pointer (intra-process comms, zero-copy for some types), eliminating the serialization. This often reclaims 5–15 ms with no algorithm change — just a launch-file restructure. It's the first thing to try and the highest value.

**2. Quantize the dominant inference (big lever, moderate effort).** If the YOLO hop dominates (it usually does), the Week-13 levers apply: TensorRT INT8 quantization (vs FP16) roughly halves inference time for a small accuracy cost; dropping the input resolution (640→416) cuts it further. The budget says whether the detector is on the critical path; if it is, this is where the time is.

**3. Move work off the contended resource (moderate lever).** If YOLO (GPU) and clustering (CPU or GPU) contend, schedule them so they don't fight — run clustering on the CPU while the GPU does inference, or pipeline the stages so they overlap rather than serialize. The budget-blowout-under-load defect (§1.7) is exactly this contention, and the fix is resource separation.

**4. Decimate the inputs (cheap lever, quality cost).** Downsample the cloud harder (a bigger voxel) or the image (lower resolution) *before* the expensive stage. Fewer points/pixels = less work everywhere downstream. The cost is resolution, so you only decimate to the point your task tolerates (Week 14's filter-chain logic).

**5. Drop a hop entirely (last resort).** If a stage isn't earning its latency — a filter whose benefit you can't measure, a transform that could be precomputed — cut it. Every hop you remove is latency you reclaim, but only cut what you've measured as low-value.

The discipline: **the budget tells you *which* hop to cut, and this list tells you *how*, in order of value.** Cutting a hop on the shorter (non-critical) branch is wasted effort — it doesn't change `max(branches)`. Optimizing the dominant critical-path hop with the highest-value lever (usually: compose intra-process, then quantize the detector) is how teams get from 45 ms to 28 ms. "Make it faster" without the diagram is guessing; "the critical path is the 18 ms YOLO hop, I'll quantize it to INT8 and compose the graph intra-process" is engineering.

## 1.12 — Why this is harder than it looks: the composition tax

A closing reality check, because the most common Week-16 surprise is that *the parts were all fast, and the whole is slow.* This is the **composition tax**, and it has three sources you must anticipate:

**Serialization between processes.** Covered above — every inter-process hop pays a serialize/deserialize cost that's invisible when you test a component alone (it publishes to nothing) but real when it's one stage of a pipeline. A node that "runs at 30 ms" in isolation may add 5 ms of transport when wired in.

**Resource contention.** Each component tested alone had the whole GPU/CPU. Composed, they share it. The YOLO that ran at 12 ms with the GPU to itself runs at 18 ms when the clustering is also using the GPU, and the clustering that ran at 8 ms runs at 12 ms when YOLO is hammering the CPU for pre/post-processing. The sum of isolated latencies *understates* the composed latency, sometimes badly. This is why you measure under load (§1.4), not idle.

**Scheduling and callback contention.** In a single-threaded executor (Week 4), all callbacks share one thread — a slow callback blocks the others, so a 20 ms clustering callback delays the next image callback. The fix is a multi-threaded executor with sensible callback groups (Week 4 again), so the branches run concurrently. A perception graph on a single-threaded executor will serialize work that should parallelize, and your `max(branches)` becomes `sum(branches)` by accident.

The lesson: **the latency budget is a property of the composed graph under load on the real executor, not a sum of component benchmarks.** This is why the 30 ms cycle is an *integration-week* deliverable and a *midterm* — it can only be measured (and only fails) when everything runs together. A student who benchmarks each component alone, sums the numbers, and reports "23 ms" will be ambushed by the composition tax when the panel asks for the measured, under-load, composed number. Measure the whole, under load, on the executor you ship — and budget for the tax.

## 1.12.5 — The executor and callback-group design that makes parallelism real

Section 1.12 named "scheduling and callback contention" as a source of the composition tax; it deserves its own treatment, because it's the most overlooked cause of a blown budget and the fix is pure ROS2 architecture (Week 4), not algorithms.

Recall the latency budget assumes the YOLO branch and the clustering branch run *in parallel*, so the critical path is `max(branches)`. That parallelism is not automatic — it depends on your executor. On a **single-threaded executor**, every callback in the process runs on one thread, one at a time. So if the clustering callback takes 9 ms, it *blocks* the image callback that should be feeding YOLO for those 9 ms, and your two branches serialize: `max(14, 9)` silently becomes something closer to `14 + 9`, and your budget blows for no algorithmic reason.

The fix is a **multi-threaded executor with callback groups** (Week 4):

```python
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

# Put the YOLO branch and the clustering branch in SEPARATE callback groups so
# they can run concurrently on different threads of a MultiThreadedExecutor.
self.yolo_group = MutuallyExclusiveCallbackGroup()
self.cluster_group = MutuallyExclusiveCallbackGroup()
self.create_subscription(Image, "/camera/color/image_raw", self.on_image,
                         qos, callback_group=self.yolo_group)
self.create_subscription(PointCloud2, "/crunchbot/points", self.on_cloud,
                         qos, callback_group=self.cluster_group)
# ... run under MultiThreadedExecutor(num_threads=4)
```

Two design rules:

- **Independent branches go in separate callback groups** so they run concurrently. The image-processing and cloud-processing callbacks don't share state, so they can and should run on different threads — that's what makes the budget's parallelism real.
- **A callback that mutates shared state needs a `MutuallyExclusiveCallbackGroup`** (or a lock) so two threads don't corrupt it. The fusion callback, which reads from both branches, is the place to be careful: it needs the latest of each branch's output, accessed safely.

The lesson: **the latency budget's `max(branches)` is a claim about concurrency, and concurrency is an executor-and-callback-group decision.** A perception node that draws a parallel budget but runs on a single-threaded executor is making a promise its architecture doesn't keep, and the measured p95 will expose it. When the panel asks "your budget says these run in parallel — how?", the answer is "separate callback groups on a multi-threaded executor," and a node that can't answer that is a node whose budget is aspirational. This is Week 4's executor discipline, now load-bearing for Week 16's latency claim — the foundations compound.

## 1.12.55 — A note on graceful degradation as a design property

One framing that ties the robustness gates (Lecture 2) to the pipeline design: a well-designed perception pipeline *degrades gracefully* — when one input fails, the output gets *worse*, not *wrong*. This is a design property you build in, not a behavior you hope for.

Concretely: when the LiDAR drops out, a graceful pipeline keeps publishing — the 2D detections still flow, the EKF coasts on IMU+wheel-odom, the 3D detections pause but the fused output continues with what it has (and marks the missing modality honestly). A *brittle* pipeline, by contrast, blocks or crashes when one input stops — a synchronizer that waits forever for the dead LiDAR, a fusion callback that assumes both inputs are present and throws when one isn't.

The design moves that buy graceful degradation: the stamp-age gate (stop using a dead input's stale data, don't block on it); honest covariances (let the EKF de-weight a degraded input automatically); and a fusion node that handles "I have a cluster but no detection" and "I have a detection but no cluster" as *normal cases*, not errors (the §2.1.2 no-match handling). Build these in and your pipeline survives a sensor dropout as a degraded-but-running system; skip them and a single failed input takes down the whole perception output. The panel's "what happens when X fails?" question is really asking "did you design for graceful degradation, or did you assume everything always works?" — and the gates and the no-match handling are how you answer "I designed for it."

## 1.12.56 — Throughput vs. latency: two numbers, don't confuse them

A precision point that trips people up: **throughput (how many frames per second the pipeline produces) and latency (how long one frame takes from sensor to output) are different numbers, and the budget is about latency, not throughput.** A pipeline can produce 30 outputs per second (good throughput) while each output is 100 ms old (bad latency), if the stages are pipelined — stage 1 works on frame N+3 while stage 4 finishes frame N. The throughput is the slowest stage's rate; the latency is the sum along the path.

For a robot, *latency* is usually what matters, because a 100 ms-old detection means the grasp targets where the object was 100 ms ago. So when the syllabus says "30 ms cycle," read it as *latency* (sensor-stamp to publish), and measure it as such (Exercise 2 measures the age of the output, which is latency). A pipeline that hits 30 FPS throughput but 80 ms latency has *not* met the budget — and confusing the two is a way to report a passing number that isn't. Pin which you're measuring: throughput is `1/period`, latency is `now − sensor_stamp`. The budget is the latter.

## 1.12.6 — The one-paragraph mental model to carry forward

Compress this lecture into one model: **a perception stack is a pipeline, and a pipeline has two properties a pile of components doesn't — a *contract* at every seam (topic/type/frame/rate/QoS) and a *latency budget* that the whole path must meet under load.** The contracts are where the integration defects hide (frame/timing, stale-perception, data-association), and the budget is the `max(branches) + tail` critical path you measure (sensor-stamp to publish, p95, under load), decompose, and cut at the dominant hop. The components were the easy part; the contracts and the budget are the integration, and they only fail when the graph is live — which is why this is a composition week and a midterm.

That model is the whole of Phase-2 integration and the rehearsal for every later gate. Draw the graph, write the contract, budget the latency, transform at the right stamp, guard the stale race — and the fused node composes cleanly, measures honestly, and defends calmly. Skip the contracts or fake the budget, and the composition tax and the panel's questions find you. Carry the pipeline-with-contracts-and-a-budget model, and perception integration stops being "wire the parts and hope" and becomes a thing you design and defend.

## 1.13 — Summary and the move to the defense

A perception stack is a pipeline, and a pipeline has contracts and a budget that a pile of components does not. Draw the end-to-end graph. Write the interface contract for every seam — topic, type, frame, rate, QoS — and verify it at bring-up. Draw the latency block diagram — every hop from sensor stamp to publish, with a measured cost — and find the critical path, which is `max(branches) + tail`, not the sum. Measure the end-to-end latency honestly: sensor stamp to publish, p95, with the whole graph live, under load. Transform detections at their *acquisition stamp* via tf2 time-travel, not at `now()`. Guard the stale-perception race with a stamp-age check at the point of use. And know the four integration defects — frame/timing, stale-perception, data-association, budget-blowout — because each maps to a fix and the panel will name them.

That budget and that contract tell you exactly what to compose and exactly how you'll be measured. Lecture 2 is the fusion that joins the streams — data association — and the architecture review that grades you: the perception brief, the panel's questions, and how to defend a number. You have drawn the pipeline. Now you fuse it and defend it.

---

**References**

- C24 syllabus, Week 16 + Phase 2 milestone — `SYLLABUS.md`.
- REP 105 — Coordinate frames for mobile platforms: <https://www.ros.org/reps/rep-0105.html>
- REP 103 — Standard units and conventions: <https://www.ros.org/reps/rep-0103.html>
- `vision_msgs` (Detection2DArray / Detection3DArray): <https://github.com/ros-perception/vision_msgs>
- ROS2 Jazzy — Composition (intra-process): <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>
- `tf2` time-travel and the lookup model: <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html>
- `ros2_tracing` (LTTng) for latency profiling: <https://github.com/ros2/ros2_tracing>
