# Week 13 — Learned 2D Perception on the Edge

Last week you built the classical floor: a calibrated camera, ORB features, RANSAC, stereo. This week you put a learned model on top of it — and you do it the way a shipping robotics engineer does, which is *not* "download the biggest model and call `.predict()`." On a Jetson Orin Nano with a 30-millisecond perception budget, the biggest model is the wrong model. The skill this week is choosing the *smallest* model that hits your latency target, exporting it out of PyTorch into a portable graph, compiling it for the specific accelerator you're deploying on, and wrapping the whole thing in a ROS2 node that publishes detections the rest of the stack can consume — all while keeping an honest accounting of milliseconds.

You start with the model families that matter in 2026: the YOLO detector line (v8 through v11), the DETR transformer detectors, the Segment Anything family (SAM/SAM2), and Depth-Anything v2 for monocular depth. You learn to read each as a point on a speed/accuracy curve, not as a brand. Then you take a small YOLO checkpoint and walk the full deployment path: PyTorch → ONNX → TensorRT FP16, measuring the latency and accuracy at each step. You quantize to INT8 and learn what calibration that needs and what accuracy it costs. You build a ROS2 inference node that consumes `/camera/image_raw` and publishes `vision_msgs/Detection2DArray` — the standard detection message every downstream consumer understands. And you profile it with the tools that tell you the truth about where your milliseconds go, because on the edge, *the latency budget is a first-class design artifact*, not an afterthought.

The one sentence to carry into the week, straight from the lecture title:

> **Choose the smallest model that hits your latency budget. Then quantize it.** A 30-millisecond perception cycle on an Orin Nano is a *design constraint*, not a target you hope to hit — and the engineer who treats it that way ships a robot that perceives in real time, while the one who reaches for the biggest model ships a robot that thinks at two frames per second.

## Learning objectives

By the end of this week, you will be able to:

- **Place** the 2026 model zoo on a speed/accuracy map: the YOLO family (v8/v10/v11), DETR-style transformer detectors, SAM/SAM2 for promptable segmentation, and Depth-Anything v2 for monocular depth — and choose the right family for a task and a compute budget.
- **Export** a PyTorch model to **ONNX**: trace/script it, set dynamic axes, verify the exported graph numerically matches the PyTorch original, and inspect it with Netron.
- **Build** a **TensorRT** engine from ONNX at FP16, understand what TensorRT does (layer fusion, kernel autotuning, precision selection), and measure the speedup and any accuracy delta vs. the ONNX/PyTorch baseline.
- **Quantize** to **INT8** with a calibration dataset, explain post-training quantization vs. quantization-aware training, and honestly report the latency win against the accuracy cost.
- **Compare** the edge runtimes — TensorRT (NVIDIA), ONNX Runtime (portable, the Path-B CPU fallback), OpenVINO (Intel) — and pick the right one for the hardware you actually have.
- **Build** a ROS2 inference node that consumes `/camera/image_raw`, runs the engine, and publishes `vision_msgs/Detection2DArray` with honest stamps and the right sensor QoS — the standard detection-node pattern.
- **Profile** an inference pipeline end to end: separate preprocessing, inference, and postprocessing time; read an `nsys`/TensorRT profile; find the bottleneck; and defend a latency budget block diagram.
- **Account** for the full perception cycle honestly — capture → preprocess → infer → postprocess → publish — and explain why the model's inference time is often *not* the bottleneck.

## Prerequisites

This week assumes you have completed **C24 weeks 1–12**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**, and the **Week 3 robot with a camera** publishing `/camera/image_raw` + `/camera/camera_info`. The detection node runs against that camera.
- The **Week 12 calibration**: your detector outputs pixels, and you back-project them with the `K` you recovered last week. Learned perception sits *on* the classical floor — that connection is the whole Phase 2 thesis.
- **Applied ML background** (the C5 prerequisite): you can train/fine-tune a CNN, read a loss curve, and reason about precision/recall. **We do not re-teach classical ML** — we teach *deployment* of models you already understand.
- **PyTorch** installed and working (`import torch`), plus `pip install onnx onnxruntime ultralytics`. TensorRT is available on the Jetson (or via the NVIDIA container); **Path B** learners use ONNX Runtime on CPU and measure the CPU-equivalent latency.
- Comfortable with the **Week 5 QoS** lesson (camera streams are `BEST_EFFORT`) and the **Week 5 message-design** lesson (stamp at acquisition time) — the detection node applies both.

You do **not** need to have trained an object detector from scratch. We take pretrained checkpoints and focus on the *deployment* path — export, compile, quantize, serve, profile — which is where real robotics perception work lives.

## Topics covered

- **The 2026 detection/segmentation/depth model zoo**: YOLOv8/v10/v11 (anchor-free, NMS-free variants, the `n/s/m/l/x` size ladder); DETR and RT-DETR (transformer detectors, set prediction, no NMS); SAM and SAM2 (promptable segmentation, the image encoder cost); Depth-Anything v2 (zero-shot monocular metric/relative depth). Reading each as a speed/accuracy point.
- **ONNX export**: `torch.onnx.export` (and the newer `dynamo` exporter), opset selection, dynamic axes (batch, spatial), the numerical-parity check against PyTorch, and inspecting the graph with Netron. Why ONNX is the *interchange* format, not a runtime.
- **TensorRT**: what an engine is, the builder pipeline (parse ONNX → optimize → serialize), layer fusion and kernel autotuning, FP16 vs FP32, the workspace size, the build-once-run-many model, and why an engine is hardware-specific (you build it *on* the target).
- **Quantization**: FP16 (nearly free on Jetson) vs INT8 (a real accuracy trade); post-training quantization (PTQ) with a calibration set vs quantization-aware training (QAT); the calibration cache; reading the accuracy delta honestly.
- **Edge runtimes compared**: TensorRT (NVIDIA, lowest latency), ONNX Runtime (portable, CPU/GPU/CoreML providers — the Path-B fallback), OpenVINO (Intel CPU/iGPU). Choosing by the hardware you have, not the hardware you wish you had.
- **The ROS2 inference node pattern**: `image_raw` (BEST_EFFORT) → `cv_bridge` → preprocess → engine → postprocess (NMS, threshold) → `vision_msgs/Detection2DArray`, with acquisition-time stamps, the `class_id`/`score`/`bbox` fields, and back-projection of box centers to rays via the Week 12 `K`.
- **Profiling and the latency budget**: separating preprocess / infer / postprocess time, `nsys` and `trtexec --profile`, the Gantt-style latency block diagram, identifying the real bottleneck (often preprocessing or the copy to GPU, not inference), and the perception-latency-budget-as-artifact discipline.
- **The honesty thread**: end-to-end cycle time on the actual hardware, the accuracy/latency Pareto front, and why "30 FPS at 640×480 on an Orin Nano" is a claim you *measure*, not assume.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                      | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The model zoo; speed/accuracy; choosing a model            |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | ONNX export; parity check; Netron; exercise 1              |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | TensorRT engines; FP16/INT8 quantization; exercise 2       |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | The ROS2 inference node; vision_msgs; exercise 3           |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Profiling; the latency budget; mini-project deep work       |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                     |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, latency-budget writeup polish               |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                            | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | The model docs, ONNX/TensorRT guides, the Jetson deployment refs, and the talks worth your time |
| [lecture-notes/01-the-model-zoo-and-onnx-export.md](./02-lecture-notes/01-the-model-zoo-and-onnx-export.md) | The 2026 model families, the speed/accuracy map, and exporting PyTorch → ONNX with a parity check |
| [lecture-notes/02-tensorrt-quantization-and-the-ros2-node.md](./02-lecture-notes/02-tensorrt-quantization-and-the-ros2-node.md) | TensorRT engines, FP16/INT8 quantization, the runtimes compared, the ROS2 inference node, and profiling |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-export-and-verify-onnx.md](./03-exercises/exercise-01-export-and-verify-onnx.md) | Export a YOLOv8n checkpoint to ONNX, verify numerical parity, inspect it in Netron |
| [exercises/exercise-02-benchmark-runtimes.py](./03-exercises/exercise-02-benchmark-runtimes.py) | Benchmark a model across precisions/runtimes; build a latency table; plot the speed/accuracy trade |
| [exercises/exercise-03-detection-node.py](./03-exercises/exercise-03-detection-node.py) | A ROS2 inference node skeleton: image in, `vision_msgs/Detection2DArray` out, honestly stamped |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-hit-the-latency-budget.md](./04-challenges/challenge-01-hit-the-latency-budget.md) | Get an end-to-end detection cycle under a fixed budget; profile, find the bottleneck, optimize |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the latency-budget block-diagram writeup |
| [mini-project/README.md](./07-mini-project/00-overview.md) | A complete edge-detection ROS2 package: export → engine → node → profiled latency budget |

## The "it ran inside the budget" promise

C24 uses a recurring marker for every edge-inference lab that ends in a measured, honest latency. It is the full cycle accounting, not just the inference number:

```
end-to-end perception cycle (640x480, Orin Nano, YOLOv8n FP16):
  capture+copy : 3.1 ms
  preprocess   : 4.8 ms     <- often the surprise bottleneck
  inference    : 11.2 ms
  postprocess  : 2.4 ms     (NMS + threshold)
  publish      : 0.6 ms
  TOTAL        : 22.1 ms  ->  45 FPS  ->  WITHIN 30 ms budget
```

A pipeline where the *inference* is fast but the *preprocessing* (resize, normalize, HWC→CHW, host→device copy) eats your budget is the single most common edge-perception surprise. The point of Week 13 is to make the full-cycle accounting ordinary — and to make a *blown* budget loud, with a profile that says exactly which stage to fix, instead of a vague "it feels slow."

## Stretch goals

If you finish the regular work early and want to push further:

- Export and deploy **Depth-Anything v2 (small)** alongside the detector, and publish a depth image — then fuse it with your detections to put each detection at a metric 3D point (the Week 12 back-projection × a learned depth).
- Quantize your detector to **INT8** with a proper calibration set drawn from your robot's own camera, and produce an honest mAP-vs-latency table: FP32, FP16, INT8. Find where the accuracy cliff is for *your* scene.
- Run **RT-DETR** (the NMS-free transformer detector) against YOLOv8 on the same images and compare both accuracy and the *postprocessing* time — RT-DETR has no NMS, which can matter when NMS is your bottleneck.
- Stand up the same engine under **ONNX Runtime with the CUDA provider** and compare its latency to native TensorRT — the portability-vs-speed trade, measured on your hardware.

## Up next

Week 14 adds **depth, stereo, and RGB-D** — RealSense/OAK-D pipelines, depth filtering, and projecting depth into point clouds. Your 2D detections from this week become *3D* objects once you fuse them with depth, which is exactly the bridge into the Week 16 fused perception node that closes Phase 2. Push your mini-project before you start it.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
