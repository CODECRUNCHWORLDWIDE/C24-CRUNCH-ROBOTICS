# Exercise 1 — Profile the Integrated Graph

**Type:** Guided, hands-on, on the target hardware.
**Estimated time:** ~60 minutes.
**Outcome:** A Gantt-style latency block diagram of your perception→policy graph with a measured p95 per stage, and a one-sentence diagnosis (compute- or memory-bound) for the worst offender.

This is the exercise that earns you the right to optimize. You do not touch a single model until you have this diagram, because without it every optimization is a guess (Lecture 1 §1).

---

## Setup

You need three stages standing up *together* in one graph:

1. The **Week 13 detector** (YOLOv8n → ONNX → TensorRT), consuming `/camera/image_raw`, publishing `vision_msgs/Detection2DArray`.
2. A **depth + projection stage** — depth image → pointcloud in `map` frame (Week 14/15 work). If you don't have it, the minimal stand-in is a node that takes a `sensor_msgs/Image` depth map and projects it with the camera intrinsics.
3. The **Week 29 Diffusion Policy** inference path (or the Week 37 VLA wrapper) consuming the fused `/perception/objects` and emitting an action chunk.

If any of these is lost, the mini-project's `crunchbot_latency` package ships stand-in nodes with the right message shapes so you can still profile a representative graph. Path B learners: run the same graph on your x86+GPU with `nvidia-smi -pl <watts>` capping power to mimic the edge constraint, and say so in your report.

Pin the device first — every number below depends on it:

```bash
sudo nvpmodel -m 0      # the power mode you intend to ship in — RECORD which one
sudo jetson_clocks      # lock clocks at max for the mode (reproducibility)
```

---

## Step 1 — `tegrastats`: is the hardware healthy?

In a side terminal, before profiling anything:

```bash
sudo tegrastats --interval 500 | tee /tmp/tegrastats.log
```

Run your graph for ~30 seconds. Then read the log and answer, in your report:

- Is `GR3D_FREQ` pinned near 99%, or sitting low (GPU starved)?
- Did `tj@` climb toward the throttle point? (If yes, your later numbers are suspect — let it cool and re-run.)
- Is `VDD_IN` pinned at the mode's cap (power-bound) or has headroom?
- Is RAM near the 8 GB ceiling (risking swap)?

**You cannot interpret any latency number until you've answered these.** A slow stage on a throttling device is a thermal problem, not a model problem.

## Step 2 — Annotate your stages with NVTX

So your ROS2 stages appear as labeled bars in `nsys`, wrap each stage's hot function:

```python
import nvtx

@nvtx.annotate("preprocess", color="blue")
def preprocess(self, image_msg): ...

@nvtx.annotate("detector_infer", color="green")
def detect(self, tensor): ...

@nvtx.annotate("depth_project", color="orange")
def project(self, depth_msg): ...

@nvtx.annotate("policy_infer", color="red")
def policy(self, objects): ...
```

## Step 3 — `nsys`: which stage owns the cycle?

```bash
nsys profile -t cuda,nvtx,osrt -o cycle_trace --force-overwrite true \
  ros2 launch crunchbot_perception integrated_graph.launch.py
# run a few hundred cycles, Ctrl-C, then:
nsys stats cycle_trace.nsys-rep
```

In the GUI (or the stats text), find:

- The **critical path** — the chain of bars that sums to your cycle time. Stages *not* on it are off-budget concerns.
- Any **wide `cudaMemcpy` bar** — a host↔device copy you may be able to eliminate (Lecture 2 §7).
- **Gaps between GPU bars** — CPU-side stages (preprocess, projection) or queue waits.

## Step 4 — `trtexec`: which layer inside the worst stage?

For the stage `nsys` flagged (probably the detector), dump the per-layer profile:

```bash
trtexec --loadEngine=det_fp16.plan --dumpProfile --exportProfile=det_prof.json \
        --iterations=200 --warmUp=500
```

Note the top-3 layers by time and whether the "should-fuse" Conv blocks actually fused (Lecture 2 §2.3).

## Step 5 — Foxglove: the true end-to-end p95

Add the cycle-latency publisher (Lecture 1 §3.4) — stamp at acquisition, compute age at the end of the graph — and plot `/perception/cycle_latency_ms` in Foxglove with a p95 overlay. Run 500+ cycles. This is the number your budget table's "measured p95" column uses.

---

## Deliverable

Produce `latency-profile.md` containing:

1. **The pinned conditions** — power mode, `jetson_clocks` on/off, ambient note, Path A or B (and cap if B).
2. **The `tegrastats` health summary** — the four answers from Step 1.
3. **A Gantt-style block diagram** — ASCII is fine — of the per-stage p95s laid end to end across the cycle. For example:

   ```text
   cycle = 88.3 ms p95  (budget 50 — FAIL)
   |capture 2.8|preprocess 3.9|====detector 24.8====|==depth+proj 17.2==|fusion 4.6|===policy 13.8===|safety 1.4|  ...gaps...
   ```

4. **The worst offender + diagnosis** — one sentence: which stage, and compute-bound or memory-bound, *with the evidence* (the `GR3D_FREQ` reading during that stage and/or the memcpy bar width).

## Acceptance criteria

- [ ] The power mode is pinned and recorded; numbers come from 500+ warmed-up cycles.
- [ ] `latency-profile.md` has a per-stage p95 for every stage, from real `nsys`/Foxglove output.
- [ ] The worst offender is named with a compute- vs memory-bound diagnosis backed by a `tegrastats`/`nsys` observation, not a guess.
- [ ] The end-to-end p95 from Foxglove matches (within reason) the sum of the stage bars — if it doesn't, you have un-accounted-for queue time, and you say so.

**Hint.** If `GR3D_FREQ` reads low (e.g. 40%) during your worst stage, it is memory-bound — do *not* reach for INT8; look for a copy to eliminate (Lecture 2 §7). If it's pinned at 99%, it's compute-bound and a precision change is your lever. Getting this diagnosis right is the whole point; everything in exercise 2 and the mini-project depends on it.
