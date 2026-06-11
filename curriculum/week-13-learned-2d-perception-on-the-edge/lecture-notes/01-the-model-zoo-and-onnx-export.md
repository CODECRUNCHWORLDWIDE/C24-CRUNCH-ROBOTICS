# Lecture 1 — The 2026 Model Zoo and the ONNX Export Path

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can place the current detection/segmentation/depth models on a speed/accuracy map and pick the right one for a task and a compute budget; and you can export a PyTorch model to ONNX, verify it numerically matches the original, and inspect the exported graph.

If you remember one sentence from this lecture, remember this one:

> **Choose the smallest model that hits your latency budget — not the most accurate model, the smallest *sufficient* one — and then make it portable by exporting it to ONNX. The model you train in PyTorch is not the model you deploy; deployment starts with the export.**

A learner coming from C5 (the AI/DS track) knows how to *train* a detector. This week is about everything that happens *after* training, which is where robotics perception actually lives. And it starts with two decisions: which model, and how to get it off your GPU workstation and onto a 15-watt Jetson.

---

## 1. The model-selection mindset: it's a Pareto front, not a leaderboard

The instinct from coursework is "use the most accurate model." On a robot that instinct is wrong, because accuracy is not free — it costs latency, and on the edge latency is the binding constraint. The right mental model is a **Pareto front**: a curve of models trading accuracy (mAP) against speed (FPS or ms). You do *not* want the most accurate point; you want **the cheapest point that clears your accuracy floor and fits your latency budget.**

```
 mAP
  ▲
  │              ● YOLOv8x  (accurate, slow)
  │           ●  YOLOv8l
  │        ●  YOLOv8m
  │     ●  YOLOv8s     ← often the sweet spot for an Orin Nano
  │  ●  YOLOv8n        ← when latency is brutal
  │
  └───────────────────────────────► inference time (ms)
```

The decision procedure a senior engineer runs:

1. **State the latency budget.** "The perception cycle must complete in 30 ms so the controller gets fresh detections at the loop rate." That number is a *contract*, set by the downstream consumer, not by the model.
2. **State the accuracy floor.** "I need to detect a person at 10 m with > 0.9 recall." Below that floor the robot is unsafe; above it, more accuracy is wasted compute.
3. **Pick the smallest model on the Pareto front that clears both.** Start small (YOLOv8n), measure, and step *up* the ladder only if the accuracy floor isn't met — never start at `x` and hope to trim later.

This is the same budgeting discipline you used for QoS depth (Week 5) and the RANSAC iteration count (Week 12): the constraint comes first, the choice follows. "I used the biggest model" is not an engineering decision; "I used the smallest model that cleared a measured 0.92 recall inside a measured 22 ms" is.

---

## 2. The 2026 detection/segmentation/depth zoo

You don't need every model — you need to know the *families* and where each sits.

### 2.1 The YOLO family — the edge-robotics default

The **YOLO** (You Only Look Once) line is the single-stage, real-time detector family, and on a robot it's almost always your starting point. As of 2026 the relevant versions:

- **YOLOv8** — the mature, ubiquitous baseline (Ultralytics). Anchor-free, with a clean export path. The `n/s/m/l/x` ladder lets you pick a point on the Pareto front by *size*.
- **YOLOv10** — added an **NMS-free** training scheme (dual-label assignment), so there's no non-max-suppression postprocessing step — which matters when NMS is your latency bottleneck.
- **YOLOv11** — the current Ultralytics flagship; better accuracy-per-FLOP than v8 at the same size.

For a robot, **YOLOv8n or YOLOv8s** is the workhorse: small, fast, well-supported, exports to ONNX/TensorRT in one command. You'll deploy exactly this in the exercises.

### 2.2 DETR and RT-DETR — the transformer detectors

**DETR** (DEtection TRansformer) reframed detection as *set prediction*: a transformer directly predicts a fixed set of boxes, no anchors, no NMS. The original DETR was slow to train and run; **RT-DETR** (Real-Time DETR) made it fast enough for the edge. The key property for you: **RT-DETR is NMS-free**, so its postprocessing is trivial. When you profile a YOLO pipeline and find NMS eating 5 ms, RT-DETR is the alternative that deletes that stage. The trade: transformer detectors can be heavier in the backbone and trickier to quantize.

### 2.3 SAM / SAM2 — promptable segmentation

**Segment Anything** (SAM, and the video-capable **SAM2**) produce *segmentation masks* from prompts (a point, a box, or "everything"). It's not a real-time per-frame detector — its image encoder is heavy — but it's the tool when you need *masks* rather than boxes (precise grasping geometry, Week 25). The deployment lesson: SAM's encoder runs *once* per image and is the cost; the mask decoder per prompt is cheap. On a robot you run the encoder at a low rate and prompt it on demand, not every frame.

### 2.4 Depth-Anything v2 — monocular depth

**Depth-Anything v2** estimates depth from a *single* image — no stereo rig, no active sensor. It's zero-shot (works on scenes it never trained on) and comes in size variants. For a robot it's the way to get a dense depth map from a plain camera, complementing (not replacing) the stereo from Week 12 and the active depth from Week 14. The stretch goal deploys it; the headline is that a *single* RGB camera can now produce usable depth, which reshapes what a cheap robot can perceive.

### 2.5 The selection table

| Need | Reach for | Why |
|---|---|---|
| Real-time boxes on the edge | YOLOv8n/s, YOLOv11 | Fast, small, one-command export, the default |
| Boxes with no NMS bottleneck | YOLOv10, RT-DETR | NMS-free postprocessing |
| Precise masks (grasping) | SAM2 | Promptable segmentation; encoder once, prompt cheap |
| Dense depth from one camera | Depth-Anything v2 | Zero-shot monocular depth |
| Highest accuracy, latency no object | YOLOv8x, DETR | Top of the Pareto front (rarely the robot answer) |

---

## 3. From PyTorch to deployment: why export at all?

You trained (or downloaded) a model in PyTorch. Why not just run PyTorch on the robot? Three reasons:

1. **PyTorch is a research framework, not a deployment runtime.** It carries the autograd machinery, Python overhead, and a large dependency footprint you don't want on a 15-watt edge device.
2. **The accelerator wants a static graph.** TensorRT, ONNX Runtime, and OpenVINO optimize a *fixed* computation graph — fusing layers, picking kernels, choosing precision. PyTorch's dynamic eager execution doesn't give them that to optimize.
3. **Portability.** The same exported model runs on NVIDIA (TensorRT), Intel (OpenVINO), or CPU (ONNX Runtime). You export *once* and deploy to whatever hardware the robot has.

The bridge is **ONNX** — the Open Neural Network Exchange. ONNX is an *interchange format*: a portable, framework-agnostic description of the computation graph. You export PyTorch → ONNX, then a runtime (TensorRT/ORT/OpenVINO) consumes the ONNX. **ONNX is not itself fast** — it's the lingua franca that lets a fast runtime ingest your model. Getting this distinction right is the foundation of the whole week: *PyTorch trains, ONNX transports, TensorRT runs.*

---

## 4. Exporting to ONNX

There are two paths, and you should know both.

### 4.1 The one-command path (Ultralytics)

For a YOLO model, Ultralytics wraps the export:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")          # a pretrained checkpoint
# Export to ONNX with a fixed input size and a chosen opset.
model.export(format="onnx", imgsz=640, opset=17, dynamic=False, simplify=True)
# -> writes yolov8n.onnx
```

`simplify=True` runs onnx-simplifier to fold constants and clean up the graph (smaller, faster to compile). For TensorRT you can go straight to an engine with `format="engine"` *on the Jetson* (the engine is hardware-specific — more in Lecture 2). This one-liner is what you'll use in Exercise 1; it hides the `torch.onnx.export` call below.

### 4.2 The general path (`torch.onnx.export`)

For any PyTorch model, the underlying API is `torch.onnx.export`. You must know it because not every model has an Ultralytics wrapper:

```python
import torch

model.eval()                                   # ALWAYS eval mode — disables dropout/BN updates
dummy = torch.randn(1, 3, 640, 640)            # a representative input shape

torch.onnx.export(
    model,
    dummy,
    "model.onnx",
    input_names=["images"],
    output_names=["output"],
    opset_version=17,
    dynamic_axes={                              # let batch (and optionally HxW) vary
        "images": {0: "batch"},
        "output": {0: "batch"},
    },
)
```

Three things that bite people, all worth internalizing:

- **`model.eval()` is mandatory.** Export in training mode and BatchNorm/dropout behave wrong; your exported model silently differs from the one you validated. This is the single most common export bug.
- **The opset version** is the ONNX operator-set version. Newer opsets support more ops; your runtime must support the opset you export. Opset 17 is a safe 2026 default; if TensorRT rejects an op, dropping or raising the opset often fixes it.
- **Dynamic axes** let dimensions vary at runtime (variable batch size, variable image size). If you export with a *fixed* shape and then feed a different size, it fails. Declare `dynamic_axes` for anything that will change — but note that *fully* static shapes let TensorRT optimize harder, so fix what you can.

PyTorch 2.x also ships a newer **`dynamo`-based exporter** (`torch.onnx.export(..., dynamo=True)`) that traces through `torch.compile`'s graph capture and handles more dynamic Python control flow. It's the direction the ecosystem is heading; the classic tracer above is still the workhorse and what most deployment guides assume in 2026.

---

## 5. The parity check: prove the export didn't change the model

This is the step beginners skip and seniors never do. An export can silently change your model's outputs — a wrong opset, an unsupported op approximated, a training-mode BatchNorm. **You must verify the ONNX model produces the same outputs as the PyTorch original**, numerically, before you trust it. This is the "it ran inside the budget" promise's quality gate: an export you haven't parity-checked is an export you can't trust.

```python
import numpy as np
import torch
import onnxruntime as ort

# 1. Reference output from PyTorch.
model.eval()
dummy = torch.randn(1, 3, 640, 640)
with torch.no_grad():
    torch_out = model(dummy).cpu().numpy()

# 2. Output from the exported ONNX, run through ONNX Runtime.
sess = ort.InferenceSession("model.onnx", providers=["CPUExecutionProvider"])
onnx_out = sess.run(None, {"images": dummy.numpy()})[0]

# 3. Compare. They should match to floating-point tolerance.
max_abs_diff = np.max(np.abs(torch_out - onnx_out))
print(f"max abs diff PyTorch vs ONNX: {max_abs_diff:.2e}")
assert np.allclose(torch_out, onnx_out, atol=1e-4), "EXPORT MISMATCH — do not deploy"
print("parity OK: ONNX matches PyTorch within tolerance")
```

A `max_abs_diff` of `1e-6` is parity (the tiny residual is float reordering). A diff of `0.3` means the export *changed your model* — stop and fix it before going further, because everything downstream (TensorRT build, quantization, deployment) inherits the broken graph. Exercise 1 makes you run exactly this check and read the number.

> **Why the order matters.** Parity-check at FP32 *first*, before TensorRT or quantization. That way, when you later see an accuracy drop after INT8 quantization, you *know* it came from quantization and not from a broken export — you've isolated the variable. Debugging a deployment is debugging a pipeline; check each stage against the last so a regression has exactly one possible cause.

---

## 6. Inspecting the graph with Netron

Once exported, *look at* the graph. **Netron** (web app or `pip install netron`) renders the ONNX graph node by node, showing input/output shapes, op types, and the data flow. It's the `ros2 topic info -v` of model deployment — the tool that turns "it doesn't work" into "ah, the output shape is `[1, 84, 8400]`, that's `[batch, 4+classes, anchors]`, so I need to transpose before NMS."

What to check in Netron:

- **Input shape and name** — does it match what your node will feed? (`images`, `[1,3,640,640]`.)
- **Output shape and name** — a YOLOv8 detection head outputs `[1, 84, 8400]` (84 = 4 box + 80 classes; 8400 anchors). Knowing this is what lets you write correct postprocessing.
- **Unexpected ops** — a stray `Cast`, a giant `Resize`, an op TensorRT won't support. Catching these in Netron saves an hour of cryptic build errors later.

Reading the graph is not optional decoration; the output tensor's exact layout *is* the contract your postprocessing code must honor, and Netron is how you read that contract.

---

## 7. Decoding the detector output: from raw tensor to boxes

The exported graph gives you a raw tensor, not boxes. Turning `[1, 84, 8400]` into a list of `(x, y, w, h, class, score)` detections is **postprocessing**, and you must understand it because (a) it's where bugs hide and (b) it's a real chunk of your latency budget. Walk the YOLOv8 output:

- The shape `[1, 84, 8400]` is `[batch, 4 + num_classes, num_anchors]`. For COCO, `num_classes = 80`, so `84 = 4 (box) + 80 (class scores)`, across `8400` candidate anchor positions.
- The first 4 rows are the box `(cx, cy, w, h)` in the *network's* input coordinates (640×640). The next 80 rows are per-class confidence scores for each anchor.
- For each of the 8400 anchors: take the max class score, threshold it (e.g. keep score > 0.25), and you have a candidate detection.

```python
import numpy as np

def decode_yolov8(output, conf_thresh=0.25):
    """output: (84, 8400) for one image. Returns candidate (cx,cy,w,h,score,cls)."""
    output = output.transpose(1, 0)          # -> (8400, 84): one row per anchor
    boxes = output[:, :4]                    # (8400, 4) cx,cy,w,h
    scores_all = output[:, 4:]               # (8400, 80) class scores
    class_ids = scores_all.argmax(axis=1)    # best class per anchor
    scores = scores_all.max(axis=1)          # its score
    keep = scores > conf_thresh              # threshold
    return boxes[keep], scores[keep], class_ids[keep]
```

That `transpose(1, 0)` is the single most common postprocessing bug — the raw tensor is `(84, 8400)` (channels first), and if you forget to transpose you index classes as anchors and get garbage. This is *exactly* the kind of thing Netron's output-shape readout (§6) tells you, which is why reading the graph first saves you the debugging.

### 7.1 Non-Max Suppression (NMS)

After thresholding you still have many *overlapping* boxes for the same object — the network fires several nearby anchors on one cup. **Non-Max Suppression** collapses them: sort by score, keep the highest, remove every box that overlaps it by more than an IoU threshold, repeat.

```python
import cv2

def nms(boxes_xywh, scores, iou_thresh=0.45, conf_thresh=0.25):
    """boxes_xywh: (N,4) center form. Returns indices to keep."""
    # cv2.dnn.NMSBoxes wants (x, y, w, h) top-left form.
    xywh = boxes_xywh.copy()
    xywh[:, 0] -= xywh[:, 2] / 2             # cx -> left
    xywh[:, 1] -= xywh[:, 3] / 2             # cy -> top
    idxs = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), conf_thresh, iou_thresh)
    return np.array(idxs).flatten() if len(idxs) else np.array([], dtype=int)
```

NMS matters for your latency budget for two reasons. First, it runs over thousands of candidates and, in pure Python, can be *slow* — it's a frequent profiling surprise (Lecture 2 §6). Second, this is precisely the stage that **YOLOv10 and RT-DETR eliminate** (Lecture 1 §2.1–2.2): their NMS-free designs skip this entirely. When you profile and find NMS dominating, switching to an NMS-free detector is the structural fix, not a micro-optimization. Knowing the decode-and-NMS path is what lets you make that call instead of guessing.

One more coordinate gotcha: the boxes come out in the *network's* 640×640 space, but your camera image is (say) 1280×720, and you resized it (often with letterbox padding) to feed the network. You must **invert that scaling** to map boxes back to the original image pixels before publishing — and *then* back-project with the Week 12 `K`. Getting the letterbox-undo wrong puts every detection in slightly the wrong place, a bug that looks like "the model is bad" but is really a coordinate-transform error.

---

## 8. Recap

You should now be able to:

- Frame model selection as a Pareto front: pick the *smallest sufficient* model that clears a measured accuracy floor inside a measured latency budget, not the most accurate one.
- Place the 2026 zoo — YOLOv8/v10/v11, DETR/RT-DETR, SAM/SAM2, Depth-Anything v2 — and choose a family for a task.
- Explain why you export at all (PyTorch trains, ONNX transports, the runtime runs) and what ONNX is (an interchange format, not a runtime).
- Export a model with `model.export` or `torch.onnx.export`, set the opset and dynamic axes, and avoid the `model.eval()` and shape-mismatch traps.
- Run the PyTorch-vs-ONNX parity check and read the max-abs-diff as a go/no-go gate.
- Inspect the exported graph in Netron and read the output tensor layout that your postprocessing must honor.

But first, two more sections that save you hours of debugging: the deployment workflow as a whole, and the export mistakes everyone makes once.

---

## 8. The deployment workflow, end to end

Step back and see the whole pipeline, because each stage feeds the next and a bug in an early stage masquerades as a bug in a late one:

```
TRAIN (PyTorch, workstation)
  │  model.eval(); validate mAP
  ▼
EXPORT (torch.onnx.export / model.export)
  │  parity-check vs PyTorch  ← gate: FP32 ONNX == PyTorch
  ▼
INSPECT (Netron)
  │  confirm input/output shapes, no surprise ops
  ▼
COMPILE (TensorRT, ON THE TARGET)   ← Lecture 2
  │  FP16, then maybe INT8 + calibration
  ▼
WRAP (ROS2 node)                    ← Lecture 2
  │  sensor QoS, acquisition stamp, vision_msgs
  ▼
PROFILE (nsys / trtexec / per-stage timers)  ← Lecture 2
  │  latency budget block diagram
  ▼
DEPLOY
```

The golden rule that makes this debuggable: **validate at each arrow against the previous stage.** PyTorch mAP → parity-check the ONNX → confirm shapes in Netron → check FP16 mAP against FP32 → check INT8 against FP16. When a regression appears, it has *one* possible source — the stage you just crossed — instead of being a mystery spread across the whole pipeline. This is the same isolate-the-variable discipline you used to debug a QoS mismatch (Week 5) and a factor-graph (Week 11): change one thing, check it, move on. A deployment pipeline debugged any other way is an afternoon you don't get back.

---

## 9. The export mistakes everyone makes once

When you export in Exercise 1, these account for nearly every "the exported model is wrong":

1. **Forgot `model.eval()`.** BatchNorm and dropout stay in training mode; the exported graph differs from the validated model. *Symptom:* parity check fails with a large diff. *Fix:* `model.eval()` before export, always.

2. **Wrong opset for the runtime.** You export at opset 20 and TensorRT (or an older ORT) doesn't support an op. *Symptom:* the *build* fails with an unsupported-op error, not the export. *Fix:* drop to opset 17, or update the runtime.

3. **Static shape, dynamic input.** Exported fixed at 640×640, then fed a 1280×720 image without resizing. *Symptom:* a shape-mismatch error at inference. *Fix:* resize in preprocessing to the export shape, or declare `dynamic_axes`.

4. **Skipped the parity check.** Deployed straight from export, then chased a phantom accuracy bug through TensorRT and quantization. *Symptom:* low accuracy with no obvious cause. *Fix:* parity-check at FP32 ONNX *before* anything else, so later regressions have one source.

5. **Misread the output layout.** Indexed `[1, 84, 8400]` as `[anchors, channels]` instead of `[channels, anchors]`. *Symptom:* garbage detections everywhere. *Fix:* read the shape in Netron, transpose correctly (§7).

Each has a *distinct* symptom — parity fail, build fail, shape error, phantom accuracy bug, garbage boxes. Mapping symptom → cause is the deployment-debugging muscle this week builds, the same diagnostic discipline as Weeks 5, 11, and 12.

Next: the ONNX you exported is portable but not yet fast. We compile it into a TensorRT engine, quantize it, compare the runtimes, wrap it in a ROS2 node, and profile the whole cycle against a budget. Continue to [Lecture 2 — TensorRT, Quantization, and the ROS2 Node](./02-tensorrt-quantization-and-the-ros2-node.md).

---

## Export reference card

Tape this next to your monitor for the week:

```
Export (YOLO):    model.export(format="onnx", imgsz=640, opset=17, simplify=True)
Export (general): torch.onnx.export(model.eval(), dummy, "m.onnx",
                      input_names=["images"], output_names=["output"],
                      opset_version=17, dynamic_axes={"images": {0: "batch"}})
Parity check:     np.allclose(torch_out, onnx_out, atol=1e-4)   # gate before deploy
Inspect:          netron m.onnx   (read input/output SHAPES)
YOLOv8 output:    [1, 84, 8400] = [batch, 4+classes, anchors]   # TRANSPOSE before decode
Decode:           transpose -> threshold scores -> NMS -> rescale to image px
Golden rule:      validate each stage against the previous (one bug, one source)
```

The four you must know cold: `model.eval()` before export, the parity check as a gate, the `[1, 84, 8400]` layout, and "build the engine on the target" (next lecture). Everything else you can look up; those four are where the time gets lost.

One last framing to carry into Lecture 2: everything here served *portability* — a single ONNX artifact that runs anywhere. Lecture 2 spends that portability on *speed*, compiling the portable graph into a hardware-specific engine. The two are in tension (portable vs. fast), and a senior engineer holds both: develop and validate portably, deploy specifically. That's why the workflow exports first and compiles second, never the reverse.

---

## References

- Ultralytics YOLO — Export modes: <https://docs.ultralytics.com/modes/export/>
- PyTorch — `torch.onnx` export: <https://pytorch.org/docs/stable/onnx.html>
- ONNX — the format and operators: <https://onnx.ai/>
- RT-DETR (NMS-free transformer detector): <https://docs.ultralytics.com/models/rtdetr/>
- Depth-Anything V2: <https://github.com/DepthAnything/Depth-Anything-V2>
- Netron (graph viewer): <https://netron.app/>
