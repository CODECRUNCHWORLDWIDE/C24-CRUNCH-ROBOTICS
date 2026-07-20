# Exercise 1 — Draw the Interface Contract and the Latency Budget

**Type:** Guided (Markdown deliverable). **Estimated time:** 90 minutes.

This is the most important 90 minutes of the week, and it involves almost no robot code. You will turn your composed perception graph into the two artifacts that defend your entire midterm: an **interface-contract table** (every seam's topic/type/frame/rate/QoS) and a **latency block diagram** with a measured budget per hop and the critical-path total. Half of midterm failures are not engineering failures — they are *defense* failures, where the learner can't produce the contract or the budget when the panel asks. This exercise is the insurance.

The deliverable is a single Markdown file, `perception-architecture.md` (the start of your homework's architecture brief), committed to your Week 16 repo. A peer reviews it against your running graph. Where your table diverges from reality, you fix the table; where the graph is wrong, you fix the graph.

---

## Step 0 — Bring up your perception graph

Compose what you have from Weeks 9–15: the EKF (`/odometry/filtered`), the 3D clustering (`/perception/clusters`), the YOLO detector (`/perception/detections_2d`), and the fusion stub (or, if you haven't built fusion yet, just the inputs). Confirm the topics exist:

```bash
ros2 topic list | grep -E "odometry|perception|points|image|imu"
```

You are documenting *what is actually running*, not what you wish were running. If a topic isn't there, note it as a gap.

---

## Step 1 — Build the interface-contract table

Create `perception-architecture.md`. Its first centerpiece is a table with exactly five columns, one row per seam (every producer→consumer edge in your graph):

| Column | What goes in it |
|---|---|
| **Topic** | The topic name on the edge. |
| **Type** | The message type (`vision_msgs/Detection3DArray`, etc.). |
| **Frame** | The `frame_id` the data is in (from `ros2 topic echo --field header.frame_id`). |
| **Rate** | The measured rate (`ros2 topic hz`), not the nominal one. |
| **QoS** | The reliability + durability (`ros2 topic info -v`). |

You owe **one row per seam** — at least the eight from Lecture 1 §1.2. Every cell from *real introspection*, not memory. Two rows filled in as the worked example:

| Topic | Type | Frame | Rate | QoS |
|---|---|---|---|---|
| `/perception/clusters` | `vision_msgs/Detection3DArray` | `map` | 9.1 Hz (measured) | reliable, keep-last 5 |
| `/perception/detections_2d` | `vision_msgs/Detection2DArray` | `camera_color_optical_frame` | 29.8 Hz (measured) | reliable, keep-last 5 |

For each row, ask the two questions the panel will:
- **Is the frame right?** Detections that fuse must reach a common frame. A cluster in `map` and a detection in the optical frame need a transform between them — note where it happens.
- **Is the rate a problem?** A slow producer feeding a fast consumer is the stale-perception race. Flag any seam where the consumer ticks faster than the producer publishes.

A **"Contract findings"** subsection below the table lists every mismatch: a seam in the wrong frame, a QoS mismatch (Week 5), a rate that sets up a stale race. Findings are good — better found here than at the review.

---

## Step 2 — Draw the latency block diagram

Below the table, draw the data flow as a latency block diagram (ASCII, Mermaid, or a clean photo of a hand-drawing). Every hop from sensor stamp to `/perception/objects` publish, with a *measured* cost. Use `ros2 topic delay` and the Exercise-2 probe to get real numbers; use placeholders only where you genuinely can't measure yet (and flag them).

```
[camera acq + driver]  --3ms-->  [YOLO inference]  --12ms-->  [fusion]  --3ms-->  [publish]  --2ms-->
[cloud acq + driver]   --3ms-->  [clustering]      --8ms----------^
```

Then compute and state the **critical path** explicitly:

- 2D branch total: ___ ms
- 3D branch total: ___ ms
- Critical path = `max(branches)` + fusion + publish = ___ ms

**The critical path is `max(branches) + tail`, not the sum** (Lecture 1 §1.3). If you write the sum, you've misunderstood the parallelism, and the panel will catch it.

---

## Step 3 — State the budget verdict

Below the diagram, one short section:

- **The target:** 30 ms (or your Path-B documented target).
- **The measured critical path:** ___ ms (idle) / ___ ms (p95 under load — from Exercise 2).
- **The verdict:** inside / over budget, and by how much.
- **If over: which hop to cut.** The budget tells you — the *dominant hop on the critical path*. Cutting a hop on the shorter branch doesn't help. Name the hop and the lever (quantize YOLO to INT8, intra-process composition, drop resolution).

This section is the single most likely thing the panel probes. "What's your latency and where does it go?" — and you point at this diagram.

---

## Step 4 — Peer review

Hand `perception-architecture.md` and your running graph to a peer. The reviewer checks:

- Does every contract-table cell match `ros2 topic info -v` / `hz` / `echo` on the live graph?
- Is any seam in the wrong frame or a QoS mismatch (Week 5)?
- Is the critical path computed as `max(branches) + tail`, not the sum?
- Does the budget verdict name the right hop to cut if over?

You fix every divergence. The reviewer signs off when the table matches the graph and the budget is honest.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `perception-architecture.md` has an interface-contract table with one row per seam, every cell from real introspection.
- [ ] A "Contract findings" subsection lists every frame/QoS/rate mismatch (or argues there are none, with evidence).
- [ ] A latency block diagram with a measured (or flagged-placeholder) cost per hop.
- [ ] The critical path is computed correctly as `max(branches) + fusion + publish`, with the branch totals shown.
- [ ] A budget verdict: target, measured critical path, over/under, and (if over) the specific hop to cut.
- [ ] A peer reviewed it against your live graph and signed off.

---

## Why this exercise matters

In a real shop, an architecture review is where a senior engineer's design either survives contact with a skeptical room or doesn't. This exercise is that review, rehearsed against your own perception stack. The contract table answers every "why that frame / QoS / rate?" question; the latency diagram answers "where does the time go?"; and together they are the document that turns a vague "perception is fast and works" into a defensible, measured, owned description of your pipeline. The hour it costs is the cheapest insurance in the midterm — and the file you write here is the spine of the architecture brief you defend on Thursday.
