# Exercise 1 — Export a YOLOv8n Checkpoint to ONNX and Verify It

**Goal:** Walk the first leg of the deployment path. You'll take a pretrained YOLOv8n, export it to ONNX, run the PyTorch-vs-ONNX **parity check** (the go/no-go gate from Lecture 1 §5), and inspect the exported graph in Netron so you know the output tensor layout your postprocessing must honor. By the end you have a verified `.onnx` ready for Exercise 2's benchmark and Exercise 3's node.

**Estimated time:** 50 minutes. Guided.

---

## Setup

```bash
pip install ultralytics onnx onnxruntime numpy
pip install netron        # or use the web app at https://netron.app
```

The first run downloads `yolov8n.pt` (~6 MB) from Ultralytics. After that, everything is offline.

---

## Step 1 — Export the model to ONNX

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")          # downloads on first run
model.export(format="onnx", imgsz=640, opset=17, dynamic=False, simplify=True)
# -> writes yolov8n.onnx next to the checkpoint
```

`simplify=True` cleans up the graph (constant folding); `opset=17` is a safe 2026 default; `dynamic=False` fixes the input at 640×640 so TensorRT can optimize hardest later. Confirm the file exists:

```bash
ls -lh yolov8n.onnx
```

---

## Step 2 — The parity check (the gate)

This is the step you never skip. Prove the ONNX produces the same output as the PyTorch original, numerically, before trusting it. Save as `parity.py`:

```python
import numpy as np
import torch
import onnxruntime as ort
from ultralytics import YOLO

# 1. PyTorch reference output. Pull the underlying torch module and eval() it.
model = YOLO("yolov8n.pt")
torch_model = model.model.eval()           # <-- eval() is mandatory (Lecture 1 §4.2)

dummy = torch.randn(1, 3, 640, 640)
with torch.no_grad():
    torch_out = torch_model(dummy)
    # YOLOv8 returns a tuple/list; take the detection tensor.
    torch_out = (torch_out[0] if isinstance(torch_out, (list, tuple)) else torch_out)
    torch_out = torch_out.cpu().numpy()

# 2. ONNX output via ONNX Runtime.
sess = ort.InferenceSession("yolov8n.onnx", providers=["CPUExecutionProvider"])
input_name = sess.get_inputs()[0].name
onnx_out = sess.run(None, {input_name: dummy.numpy()})[0]

# 3. Compare.
print("PyTorch output shape:", torch_out.shape)
print("ONNX    output shape:", onnx_out.shape)
max_abs = float(np.max(np.abs(torch_out - onnx_out)))
print(f"max abs diff: {max_abs:.2e}")
if max_abs < 1e-3:
    print("PARITY OK — ONNX matches PyTorch; safe to deploy.")
else:
    print("PARITY FAIL — the export changed the model. DO NOT DEPLOY. "
          "Check model.eval() and the opset.")
```

```bash
python3 parity.py
```

You want:

```
PyTorch output shape: (1, 84, 8400)
ONNX    output shape: (1, 84, 8400)
max abs diff: 3.81e-06
PARITY OK — ONNX matches PyTorch; safe to deploy.
```

A `max abs diff` around `1e-6` is parity (float reordering). A diff of `0.3` means the export changed your model — almost always a missing `model.eval()` or an opset issue. **This is the gate: an export you haven't parity-checked is an export you can't trust.**

---

## Step 3 — Inspect the graph in Netron

```bash
netron yolov8n.onnx          # opens a browser; or drag the file onto https://netron.app
```

Find and write down:

- **The input node:** name (`images`) and shape (`[1, 3, 640, 640]`). This is what your node must feed.
- **The output node:** name and shape (`[1, 84, 8400]`). Recall the decode (Lecture 1 §7): `84 = 4 box + 80 classes`, `8400` anchors. **This shape is the contract your postprocessing honors** — and it's channels-first, so you transpose to `[8400, 84]` before decoding.
- **Any surprise op:** scroll for a stray `Resize`, `Cast`, or an op you don't recognize. On a clean YOLOv8 export there won't be; the habit of looking is what saves you on a custom model.

---

## Step 4 — Confirm the decode on real output

Run the ONNX on a real image and confirm the decode produces sane detections. Save as `decode_check.py`:

```python
import numpy as np
import cv2
import onnxruntime as ort

def preprocess(img, size=640):
    """Letterbox-free simple resize for the check (Exercise 3 does proper letterbox)."""
    resized = cv2.resize(img, (size, size))
    blob = resized[:, :, ::-1].transpose(2, 0, 1)        # BGR->RGB, HWC->CHW
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    return blob[None]                                    # add batch dim

img = cv2.imread("test.jpg")                            # any image with objects
sess = ort.InferenceSession("yolov8n.onnx", providers=["CPUExecutionProvider"])
out = sess.run(None, {sess.get_inputs()[0].name: preprocess(img)})[0]  # (1,84,8400)

pred = out[0].transpose(1, 0)                           # -> (8400, 84)  TRANSPOSE!
boxes, scores_all = pred[:, :4], pred[:, 4:]
class_ids = scores_all.argmax(1)
scores = scores_all.max(1)
keep = scores > 0.25
print(f"candidate detections above 0.25: {keep.sum()}")
print(f"top score: {scores.max():.3f}  class: {class_ids[scores.argmax()]}")
```

On an image with clear objects you should see a handful-to-dozens of candidates above threshold and a top score near 1.0 on a confident detection. If you see *thousands* of candidates or garbage scores, you forgot the `transpose` — the single most common decode bug.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `yolov8n.onnx` exists, exported at opset 17, 640×640, simplified.
- [ ] The parity check prints `max abs diff` < `1e-3` and `PARITY OK`.
- [ ] You inspected the graph in Netron and recorded the input shape (`[1,3,640,640]`) and output shape (`[1,84,8400]`).
- [ ] The decode check produces a sane number of candidate detections (not thousands of garbage) and a high top score on a confident object.
- [ ] You can state what `84` and `8400` mean and why you must `transpose` before decoding.

---

## Stretch

- Export with `dynamic=True` and confirm in Netron that the batch (and maybe spatial) dims become symbolic. Note the trade: dynamic shapes are flexible but let TensorRT optimize less hard.
- Export YOLOv8**s** as well and compare the ONNX file sizes and the Netron graphs. The `s` model is the same architecture, more channels — you'll benchmark both in Exercise 2.
- Try `opset=20` and `opset=12` and see which ops change. Some runtimes are picky about opset; knowing how to move it is a real deployment skill.

---

When this feels comfortable, move to [Exercise 2 — Benchmark runtimes](./exercise-02-benchmark-runtimes.py).
