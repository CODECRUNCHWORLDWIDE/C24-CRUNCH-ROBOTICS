# Week 13 Homework

Six problems that drive the edge-deployment skills into your fingers. The full set should take about **5 hours**. Work in your Week 13 Git repository (the same workspace as the exercises and the `crunch_detector` mini-project) so every problem produces at least one commit you can point to at the Phase 2 midterm in Week 16.

The headline deliverable is **Problem 4 — the latency-budget block-diagram writeup**, the artifact the midterm panel grades and that goes in your perception portfolio. Treat it as an engineering report, not a journal entry.

Each problem includes a **problem statement**, **acceptance criteria**, a **hint**, and an **estimated time**. Install the deps once: `pip install ultralytics onnx onnxruntime numpy matplotlib opencv-python`.

---

## Problem 1 — Export, parity-check, and read the graph

**Problem statement.** Export YOLOv8n *and* YOLOv8s to ONNX (Exercise 1). Run the parity check on both. Inspect both in Netron and record the input/output shapes and the file sizes. Confirm both pass parity.

**Acceptance criteria.**

- `yolov8n.onnx` and `yolov8s.onnx` both exist and both pass the parity check (max-abs-diff < 1e-3), recorded in `notes/week-13/export.md`.
- The input shape (`[1,3,640,640]`) and output shape (`[1,84,8400]`) are recorded for both, with file sizes.
- You note that both have the *same* output shape (same architecture family) but `s` is larger — and predict which you'd pick for a 30 ms budget before measuring.
- Committed.

**Hint.** The parity check is the gate; if either fails, you forgot `model.eval()` or hit an opset issue. Both YOLOv8n/s share the `[1,84,8400]` head shape — the difference is internal channel width, which shows in file size, not output shape.

**Estimated time.** 40 minutes.

---

## Problem 2 — Benchmark the precision/runtime matrix

**Problem statement.** Using Exercise 2's harness (and your real ONNX from Problem 1), benchmark YOLOv8n at the configurations you can run on your hardware: at minimum FP32 ONNX Runtime CPU; Path A learners add FP16 TensorRT and INT8; Path B learners compare CPU vs (if available) the CUDA execution provider. Build a latency table.

**Acceptance criteria.**

- `notes/week-13/benchmark.md` with a table: configuration | preprocess ms | inference ms | postprocess ms | total ms | FPS, each averaged over 100+ runs after warmup.
- The configurations you could actually run, honestly labeled (don't fabricate Jetson numbers if you're on Path B — document your hardware).
- A one-sentence reading: which configuration would you deploy, and does it clear a 30 ms budget on your hardware (or what hardware it *would* clear it on)?
- Committed.

**Hint.** Warm up before timing — the first inference includes one-time setup that pollutes the average. The relationships are invariant even when absolute numbers aren't: FP16 < FP32 inference; the per-stage split reveals whether inference or preprocessing dominates *on your machine*.

**Estimated time.** 50 minutes.

---

## Problem 3 — Wire the detection node and verify on the wire

**Problem statement.** Complete the Exercise 3 node (fill in the five TODOs), run it against a camera (real, Gz Sim, or `image_publisher`), and verify on the wire that the QoS, stamps, and message type are correct.

**Acceptance criteria.**

- The node publishes `/detections` (Detection2DArray) when objects are in view.
- `ros2 topic info /detections -v` shows BEST_EFFORT on the publisher (and the image subscription); pasted into `notes/week-13/node-verify.md`.
- `ros2 topic echo /detections --once` shows a detection whose `header.stamp` equals the *image's* stamp, not the current time — you verify this by comparing to the image's stamp.
- Boxes are in original-image pixels (you fed a non-640 image and the boxes are sensible).
- Committed.

**Hint.** The acquisition-stamp check is the subtle one: subscribe to both `/camera/image_raw` and `/detections`, and confirm a detection's stamp matches the image it came from (not `now()`). If they differ by tens of ms, you stamped with `now()` — the bug this whole node design exists to prevent.

**Estimated time.** 50 minutes.

---

## Problem 4 — The latency-budget block-diagram writeup (headline deliverable)

**Problem statement.** Write a one-page engineering report at `notes/week-13/latency-budget.md` that a reviewer (or interviewer) could use to judge whether your detector is deployable. Cover:

1. **The budget** — state it (30 ms for Path A; document your number and target hardware for Path B) and where it comes from (the downstream consumer's loop rate).
2. **The per-stage block diagram** — capture/preprocess/infer/postprocess/publish, in the Lecture 2 §6.1 Gantt format, with real measured numbers on your hardware.
3. **The bottleneck** — name the longest stage and explain *why* it's that long.
4. **The optimization you'd do next** — the longest non-inference bar, with the specific fix (vectorize preprocessing? FP16? smaller model? NMS-free?), justified by the §6.2 order.
5. **The precision comparison** — FP32 vs FP16 (and INT8 if you measured it), with the latency win and any accuracy delta.
6. **The verdict** — do you hit the budget, on what hardware, with what configuration?

**Acceptance criteria.**

- `notes/week-13/latency-budget.md` exists, fits ~one page (450–650 words), hits all six headings.
- The block diagram has *real measured* numbers, not estimates.
- The "next optimization" is specific and justified by the profile (the longest non-inference bar), not a guess.
- Committed.

**Hint.** This is the artifact the Week 16 panel grades and résumé flagship #1's centerpiece. The interviewer's question is always "where do your milliseconds go and what's your next optimization?" — write the report as that answer. The §6.2 optimization-order list is your guide to the "next optimization" section.

**Estimated time.** 1 hour.

---

## Problem 5 — INT8 quantization and the accuracy trade

**Problem statement.** (Path A, or Path B with ONNX Runtime's quantization tools.) Quantize YOLOv8n to INT8 with a calibration set of ~200 images drawn from a source like your robot's camera or COCO val. Compare FP16 and INT8 on latency *and* a small accuracy check (run both on the same test images and compare detection counts/scores, or compute mAP on a labeled subset).

**Acceptance criteria.**

- `notes/week-13/int8.md` with the INT8 latency vs FP16, and an honest accuracy comparison (mAP delta, or detection-agreement on a test set).
- You state where the calibration set came from and why it must resemble deployment data.
- A verdict: is INT8 worth it for your accuracy floor, or is FP16 as far as you'd go?
- Committed.

**Hint.** ONNX Runtime has `onnxruntime.quantization` (static quantization with a calibration data reader) if you're not on a Jetson. The honest answer is sometimes "INT8 saved X ms but dropped mAP by Y, and Y is too much for my safety floor" — saying that with numbers is the point, not forcing INT8.

**Estimated time.** 1 hour.

---

## Problem 6 — Detection to 3D: back-project a box center

**Problem statement.** Take a detection's box center (pixel) from your node, back-project it to a ray using the Week 12 calibrated `K`, and combine with a depth (a constant ground-plane assumption, or a real depth value if you have a depth camera) to produce a 3D point in the camera frame. This is the literal bridge from 2D detections to the 3D objects Week 16 needs.

**Acceptance criteria.**

- A script that takes a `Detection2D` box center, back-projects with `K` (Week 12 §2.1), and outputs a 3D point under a stated depth assumption.
- `notes/week-13/detection-to-3d.md` with one worked example: a box center, the ray, the depth, the resulting 3D point, and a sanity check that it's in a plausible location.
- You note the frame convention (the optical frame, Week 12 §6.1) and that the point needs transforming to the body frame before the robot acts on it.
- Committed.

**Hint.** This reuses the exact back-projection from Week 12 Problem 2, now fed by a learned detection instead of a clicked pixel. The chain — detection pixel → ray (`K⁻¹`) → 3D point (× depth) → body frame (tf2) — is how a YOLO box becomes something the arm can reach for. Getting the optical-frame convention right matters (Week 12 §6.1).

**Estimated time.** 40 minutes.

---

## Time budget recap

| Problem | Estimated time |
|--------:|--------------:|
| 1 — Export + parity + Netron | 40 min |
| 2 — Precision/runtime benchmark | 50 min |
| 3 — Wire and verify the node | 50 min |
| 4 — Latency-budget writeup (headline) | 1 h 0 min |
| 5 — INT8 quantization trade | 1 h 0 min |
| 6 — Detection to 3D | 40 min |
| **Total** | **~5 h 0 min** |

When you've finished all six, push your repo and make sure the `crunch_detector` [mini-project](./07-mini-project/00-overview.md) is in the same workspace — Week 16 fuses its detections into the perception graph. Then take the [quiz](./05-quiz.md) with your notes closed.
