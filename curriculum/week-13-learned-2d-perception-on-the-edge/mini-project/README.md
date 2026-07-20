# Mini-Project — `crunch_detector`: An Edge Detection Package with a Defended Latency Budget

> Build a complete ROS2 detection package: export a YOLOv8n to ONNX, compile it (TensorRT FP16 on Path A / ONNX Runtime on Path B), wrap it in a node that publishes `vision_msgs/Detection2DArray` with the correct QoS and acquisition-time stamps, and produce a **profiled latency block diagram** that proves the cycle fits a stated budget. This is the syllabus's "real-time perception node inside 30 ms" deliverable, built end to end — the artifact that goes at the top of your perception portfolio.

This is the week's flagship and one of the three flagship portfolio projects of the whole track (the syllabus names "the 30-ms perception cycle" as résumé project #1). The exercises taught the pieces — export, benchmark, the node skeleton. The mini-project assembles them into a deployable package *and* the latency analysis that proves it's real-time, because on the edge a detector you can't defend the latency of is a detector you can't ship.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** This node is a core input to the **Week 16 fused perception graph** (its 2D detections become 3D objects once combined with the Week 14 depth), it's the detector the **Week 39 edge-optimization** week profiles and quantizes further, and it's one of the three **portfolio flagships** you polish in Week 47. Its latency block diagram is exactly the artifact the Week 16 midterm panel grades. Build it to portfolio quality now.

---

## What you will build

A small ament-python package `crunch_detector` with four deliverables:

1. **An export + build pipeline** (`scripts/export.py`, `scripts/build_engine.py` or notes for Path A) — exports YOLOv8n to ONNX with the parity check, and (Path A) builds a TensorRT FP16 engine on the Jetson. Documented so it reproduces.
2. **`crunch_detector/runtime.py`** — a ROS-free `InferenceRuntime` abstraction with two backends: `OrtRuntime` (ONNX Runtime, CPU/GPU — Path B and portable) and `TrtRuntime` (TensorRT engine — Path A). The node depends on the abstraction, not a specific backend, so the same node runs on both paths.
3. **`crunch_detector/detector_node.py`** — the ROS2 node: `/camera/image_raw` (BEST_EFFORT) → letterbox preprocess → runtime → decode + NMS + rescale → `vision_msgs/Detection2DArray` on `/detections`, with acquisition-time stamps and a per-frame inlier/latency diagnostic. Built on the Exercise 3 skeleton.
4. **The latency budget artifact** — a `latency_report.md` with the per-stage block diagram on your actual hardware, the precision comparison (FP32 vs FP16, and INT8 if you go there), and a defended statement of whether you hit the budget and what your next optimization would be.

By the end you have a public repo that runs a real detector on a camera and a latency report you can show a reviewer.

---

## Why a runtime abstraction

The single most important design decision: **the node talks to an `InferenceRuntime` interface, not to TensorRT or ONNX Runtime directly.** This is the same layering discipline as the Week 11 `crunch_posegraph` backend and the Week 12 `crunch_vo` core. It buys you:

- **Path A / Path B from one codebase.** Path A loads `TrtRuntime`; Path B loads `OrtRuntime`. The node, the QoS, the stamping, the postprocessing — all identical. No `#ifdef`, no fork.
- **Testability.** You can unit-test the decode/NMS/rescale logic with a fake runtime that returns canned tensors, no GPU and no ROS needed.
- **Honest benchmarking.** You can swap the backend and re-run the same latency harness, producing the FP32/FP16/runtime comparison that the report demands.

```python
"""crunch_detector.runtime — backend-agnostic inference. The node depends on this."""
from __future__ import annotations
import numpy as np


class InferenceRuntime:
    """Interface. A backend implements infer(tensor) -> np.ndarray."""
    def infer(self, tensor: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class OrtRuntime(InferenceRuntime):
    """ONNX Runtime backend — Path B (CPU) and portable (CUDA provider on Path A)."""
    def __init__(self, onnx_path: str, providers=None):
        import onnxruntime as ort
        providers = providers or ["CPUExecutionProvider"]
        self.sess = ort.InferenceSession(onnx_path, providers=providers)
        self.input_name = self.sess.get_inputs()[0].name

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        return self.sess.run(None, {self.input_name: tensor})[0]


class TrtRuntime(InferenceRuntime):
    """TensorRT backend — Path A (Jetson). Loads a prebuilt engine.

    Sketch — fill in the device-buffer allocation and the execute call against the
    TensorRT Python runtime (create_execution_context, set_tensor_address, etc.).
    """
    def __init__(self, engine_path: str):
        import tensorrt as trt
        import pycuda.autoinit  # noqa: F401
        logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(logger) as rt:
            self.engine = rt.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        # TODO: allocate host/device buffers for the input and output bindings.

    def infer(self, tensor: np.ndarray) -> np.ndarray:
        # TODO: H2D copy, context.execute_v2, D2H copy, return the output array.
        raise NotImplementedError("wire the TensorRT execute path on the Jetson")
```

---

## Package layout

```
crunch_detector/
├── package.xml
├── setup.py
├── setup.cfg
├── resource/crunch_detector
├── crunch_detector/
│   ├── __init__.py
│   ├── runtime.py            # InferenceRuntime + OrtRuntime + TrtRuntime
│   ├── postprocess.py        # letterbox, decode, NMS, rescale (ROS-free, testable)
│   └── detector_node.py      # the ROS2 node
├── scripts/
│   ├── export.py             # YOLOv8n -> ONNX + parity check
│   └── build_engine.py       # ONNX -> TensorRT FP16 engine (Path A)
├── launch/
│   └── detector.launch.py
└── test/
    ├── test_postprocess.py   # decode/NMS/rescale on canned tensors (no ROS, no GPU)
    └── test_runtime.py       # OrtRuntime parity / smoke test
```

---

## Deliverable details

### The export + build pipeline (`scripts/`)

- `export.py` runs `YOLO("yolov8n.pt").export(format="onnx", imgsz=640, opset=17, simplify=True)` and then the **parity check** from Exercise 1, failing loudly if `max_abs_diff > 1e-3`. Reproducibility: anyone can run it and get the same ONNX.
- `build_engine.py` (Path A) builds the FP16 engine *on the Jetson* with the TensorRT Python API (Lecture 2 §1.1), or documents the `trtexec` command. Path B skips this and runs the ONNX directly.

### `postprocess.py` (ROS-free, the testable heart)

`letterbox(img)`, `decode(output)`, `nms(boxes, scores)`, and `rescale(boxes, scale, pad)` — exactly the Exercise 3 logic, factored out so it's unit-testable on canned `(1, 84, 8400)` tensors with no ROS and no GPU. This is where the subtle bugs live (the transpose, the letterbox-undo), so it's the most-tested file. The acceptance test for `postprocess.py` is concrete: feed it a synthetic tensor with one planted high-score anchor at a known box, and assert the decoded detection lands at the expected *original-image* pixel after the letterbox-undo. If the transpose is wrong you get thousands of garbage detections; if the rescale is wrong the box is in the wrong place; either way the test fails loudly, which is the point of factoring it out.

### `test_postprocess.py` — what good tests look like here

The tests are not an afterthought; they're how you catch the two bugs that silently corrupt a detector:

- **The transpose test.** Build a `(1, 84, 8400)` tensor with all-low scores except one anchor with a high score for a known class and a known box. Assert `decode` returns exactly one detection with that class and box. Forget the transpose and you index classes as anchors — the test catches it.
- **The letterbox-undo test.** Letterbox a non-square image (say 1280×720), run a known box through `decode` + `rescale`, and assert the output box is in the *original* 1280×720 pixel coordinates, not the 640×640 network space. This is the bug that makes "the model looks bad" when really the coordinates are off.
- **The empty test.** Feed an all-low-score tensor and assert `decode` returns an empty list without crashing — the graceful-degradation requirement.

These run in milliseconds with no ROS and no GPU, which is exactly why `postprocess.py` is ROS-free. The hard-to-get-right geometry is tested in isolation; the node plumbing is tested separately on the real graph.

### `detector_node.py` (the node)

The Exercise 3 node, productionized: a configurable model path, the runtime selected by a parameter (`ort` vs `trt`), the sensor QoS on both ends, the acquisition-time stamp, and a `/detector/latency` diagnostic publishing the per-frame per-stage timing so you can watch the budget live.

### `latency_report.md` (the portfolio artifact)

The deliverable that makes this portfolio-grade:

- A **per-stage block diagram** (capture/preprocess/infer/postprocess/publish) on *your* hardware, in the Lecture 2 §6.1 format.
- A **precision/runtime comparison table**: FP32 vs FP16 (and INT8 if you go there), or CPU vs GPU on Path B/A, with the mAP delta where you can measure it.
- A **budget verdict**: state your budget (30 ms for Path A; document the Path-B number and target hardware), whether you hit it, and — the senior move — **what your next optimization would be**, justified by the longest non-inference bar.

---

## Rules

- **You may** read the Ultralytics, ONNX, and TensorRT docs and the lecture notes.
- **You must not** import `onnxruntime` or `tensorrt` anywhere except `runtime.py`. The node and postprocess depend on the `InferenceRuntime` interface. If `grep -rn "import onnxruntime\|import tensorrt" --include=*.py | grep -vE "runtime|test|scripts"` returns the node, you've broken the layering.
- **You must** run the parity check in `export.py` and fail on mismatch — never deploy an unverified export.
- **You must** use sensor QoS on the image sub and detection pub, and carry the acquisition stamp (the Week 5 lessons).
- Python 3.12, `rclpy` on Jazzy, `ultralytics`/`onnx`/`onnxruntime`; TensorRT on Path A.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-13-crunch-detector-<yourhandle>`.
- [ ] `colcon build --packages-select crunch_detector` succeeds with no warnings.
- [ ] `scripts/export.py` produces a parity-checked `yolov8n.onnx` (fails loudly on mismatch).
- [ ] `grep -rn "import onnxruntime\|import tensorrt" --include=*.py` finds matches **only** in `runtime.py` (and `scripts`/`test`).
- [ ] `colcon test` passes: `test_postprocess.py` covers the decode transpose, NMS, and letterbox-undo on canned tensors; `test_runtime.py` smoke-tests `OrtRuntime`.
- [ ] Running `detector.launch.py` against a camera publishes `/detections` (Detection2DArray) with BEST_EFFORT QoS and the image's acquisition stamp.
- [ ] `latency_report.md` has the per-stage block diagram on your hardware, the precision/runtime comparison, the budget verdict, and your stated next optimization.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **Export + parity** | 15 | The export reproduces; the parity check runs and gates deployment; the ONNX is verified. |
| **Runtime abstraction** | 15 | The `grep` check is clean; the node runs on both OrtRuntime and (Path A) TrtRuntime from one codebase. |
| **Postprocess correctness** | 20 | Decode (transpose), NMS, and letterbox-undo are correct and unit-tested on canned tensors; boxes land in original-image pixels. |
| **Node plumbing** | 15 | Sensor QoS on both ends; acquisition-time stamp; vision_msgs; graceful empty-detection handling; latency diagnostic. |
| **Latency report** | 25 | The per-stage block diagram is real and on your hardware; the precision comparison is honest; the budget verdict and next-optimization are defended with the profile. |
| **Tests & docs** | 10 | Tests green; README with run commands, the report, and a screenshot of detections in rviz2/Foxglove. |

**90+** is portfolio-grade and ready to be résumé flagship #1. **70–89** works but the latency report is thin or a coupling leaks. **Below 70** means the detector runs but you can't defend its latency — which is the entire point of edge deployment, so fix that first.

---

## Stretch goals

- **INT8 the detector** with a calibration set drawn from your robot's own camera, and add the INT8 row to the report with the honest mAP delta (Lecture 2 §3). Find the accuracy cliff for *your* scene.
- **3D detections.** Back-project each box center with the Week 12 `K` and combine with a depth (a constant ground-plane assumption, or the Week 14 depth camera) to publish `vision_msgs/Detection3DArray`. This is the literal bridge to the Week 16 fused perception node.
- **Depth-Anything alongside.** Export and run Depth-Anything v2 (small) as a second runtime, publish a depth image, and fuse it with detections — a dense-depth + detection pipeline from a single RGB camera.
- **The async node.** Run inference in its own callback group under a multi-threaded executor (Lecture 2 §5.2) and confirm the node drops stale frames instead of queuing them — prove it with `ros2 topic hz` under load.

---

## Pre-ship checklist

Before you call the detector deployable, walk this list — it's the bring-up validation discipline from Week 8, applied to a learned-perception node:

- [ ] The ONNX passed the FP32 parity check (the export didn't change the model).
- [ ] The engine was built *on the target* (Path A), or the ONNX runs under the documented runtime (Path B).
- [ ] `ros2 topic info /detections -v` shows BEST_EFFORT on both the image sub and the detection pub.
- [ ] A detection's `header.stamp` equals the source image's stamp (verified on the wire, not assumed).
- [ ] Boxes land in original-image pixels (the letterbox-undo is correct) — checked against a known object.
- [ ] The node publishes an empty array (not a gap) when nothing is detected, and never crashes on a blank frame.
- [ ] The latency report shows the per-stage breakdown on your hardware and states the budget verdict.
- [ ] The inference runtime is swappable (Ort ↔ Trt) without touching the node — the `grep` check is clean.

A detector that fails any of these isn't done — it's a demo. The checklist is what turns "it detected a cup once" into "it's a node I'd put on a robot."

---

## How this connects to the rest of C24

- **Week 14 (depth/RGB-D)** gives you the depth that turns these 2D boxes into 3D objects.
- **Week 16 (Phase 2 midterm)** fuses this detector with LiDAR, IMU, and depth into one `/perception/objects` topic inside a 30 ms cycle — and grades the latency block diagram you built here.
- **Week 39 (edge ML optimization)** profiles this exact detector, applies INT8/sparsity, and produces the integrated-graph latency Gantt.
- **Week 47 (portfolio)** polishes this as résumé flagship #1: "the 30 ms perception cycle, on-Jetson, with profiling artifacts."

When you've finished, push the repo and take the [quiz](../quiz.md).
