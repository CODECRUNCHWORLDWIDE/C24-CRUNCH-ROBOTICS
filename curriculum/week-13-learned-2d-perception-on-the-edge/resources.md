# Week 13 — Resources

Every resource here is **free**. The model docs (Ultralytics YOLO, Meta SAM2, Depth-Anything), the ONNX docs, the NVIDIA TensorRT and Jetson docs, and the ONNX Runtime / OpenVINO docs are all open. The pretrained checkpoints are downloadable at no cost. No paywalled material is required.

Versions move fast in this corner of the field. Where a version matters we pin it; where the concept is stable (ONNX export, TensorRT engine build, the latency-budget discipline) the specific version doesn't.

## Required reading (work it into your week)

- **Ultralytics YOLO docs — Export** (`model.export(format="onnx")`, `format="engine"`): the one-command path you'll use in Exercise 1, plus the supported formats table:
  <https://docs.ultralytics.com/modes/export/>
- **ONNX — Exporting a PyTorch model** (`torch.onnx.export`, dynamic axes, opset, the `dynamo` exporter):
  <https://pytorch.org/docs/stable/onnx.html>
- **NVIDIA — TensorRT Quick Start / Developer Guide** (the engine builder, FP16/INT8, `trtexec`):
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/quick-start-guide.html>
- **NVIDIA — TensorRT INT8 quantization & calibration** (PTQ, the calibration cache, the accuracy trade):
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/work-with-int8.html>

## The model families (read the one you'll deploy)

- **YOLOv8 / v11 (Ultralytics)** — the detector you export and deploy; the `n/s/m/l/x` size ladder and the speed/accuracy table:
  <https://docs.ultralytics.com/models/yolo11/>
- **RT-DETR (Ultralytics / Baidu)** — the NMS-free transformer detector for the no-NMS comparison:
  <https://docs.ultralytics.com/models/rtdetr/>
- **Segment Anything 2 (SAM2, Meta)** — promptable segmentation; read the image-encoder cost section:
  <https://github.com/facebookresearch/sam2>
- **Depth-Anything V2** — zero-shot monocular depth, the stretch-goal model:
  <https://github.com/DepthAnything/Depth-Anything-V2>
- **DETR (the original transformer detector, for context)**:
  <https://github.com/facebookresearch/detr>

## Runtimes and tooling

- **ONNX Runtime — execution providers** (CPU, CUDA, TensorRT, CoreML — the portable runtime and the Path-B CPU fallback):
  <https://onnxruntime.ai/docs/execution-providers/>
- **OpenVINO — get started** (Intel CPU/iGPU/NPU inference, for Intel-based robots):
  <https://docs.openvino.ai/>
- **Netron** — the graph viewer for inspecting your exported ONNX:
  <https://netron.app/>
- **NVIDIA Nsight Systems (`nsys`)** — the profiler for finding where the milliseconds go:
  <https://developer.nvidia.com/nsight-systems>

## Jetson deployment

- **NVIDIA Jetson Orin Nano — developer guide / JetPack** (the target hardware; TensorRT ships with JetPack):
  <https://developer.nvidia.com/embedded/jetpack>
- **`jetson-stats` / `jtop`** — monitor GPU/CPU/power on the Jetson while you profile:
  <https://github.com/rbonghi/jetson_stats>
- **`isaac_ros` / NVIDIA Isaac ROS** — NVIDIA's hardware-accelerated ROS2 perception nodes; read how their detection nodes are structured:
  <https://nvidia-isaac-ros.github.io/>

## ROS2 vision messages

- **`vision_msgs`** — `Detection2DArray`, `Detection2D`, `ObjectHypothesisWithPose`, `BoundingBox2D`; the standard detection message you publish:
  <https://github.com/ros-perception/vision_msgs>
- **`cv_bridge`** — `sensor_msgs/Image` ↔ OpenCV/NumPy:
  <https://docs.ros.org/en/jazzy/p/cv_bridge/>
- **`image_transport`** — compressed image transport for cameras over the wire:
  <https://docs.ros.org/en/jazzy/p/image_transport/>

## Talks / references worth your time (free, no signup)

- **NVIDIA GTC sessions on TensorRT + Jetson edge inference** — the OEM's own deployment walkthroughs (free with a developer account):
  <https://www.nvidia.com/gtc/>
- **Ultralytics YouTube — export & deploy series** — practical YOLO → ONNX → TensorRT:
  <https://www.youtube.com/@Ultralytics>
- **ROSCon perception & edge-AI sessions** — Isaac ROS and edge-inference talks, posted free by OSRF:
  <https://roscon.ros.org/>

## Tools you'll use this week

- **`ultralytics`** — `pip install ultralytics`. Pretrained YOLO + one-command export.
- **`onnx`, `onnxruntime`** — `pip install onnx onnxruntime` (or `onnxruntime-gpu`). Export verification + the portable runtime.
- **`torch`** — the source of the model; `torch.onnx.export`.
- **`tensorrt` / `trtexec`** — ships with JetPack on the Jetson; build engines and benchmark.
- **`nsys`** (Nsight Systems) and **`jtop`** — profiling and hardware monitoring on the Jetson.
- **`netron`** — `pip install netron` or the web app; inspect the exported graph.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **ONNX** | Open Neural Network Exchange — a portable model *interchange* format (not a runtime). |
| **TensorRT** | NVIDIA's inference compiler+runtime; turns an ONNX graph into an optimized hardware-specific *engine*. |
| **Engine** | A serialized, hardware-specific TensorRT plan; built once on the target, run many times. |
| **FP16** | Half-precision floats; near-free 2× speedup on Jetson with negligible accuracy loss. |
| **INT8** | 8-bit integer inference; bigger speedup, real accuracy cost, needs calibration. |
| **PTQ** | Post-Training Quantization — quantize a trained model using a calibration set, no retraining. |
| **QAT** | Quantization-Aware Training — simulate quantization during training for better INT8 accuracy. |
| **Calibration set** | A representative sample of inputs used to choose INT8 scales. |
| **Layer fusion** | TensorRT merging ops (conv+bn+relu) into one kernel to cut memory traffic. |
| **NMS** | Non-Max Suppression — postprocessing that removes duplicate overlapping boxes. |
| **mAP** | mean Average Precision — the standard detection accuracy metric. |
| **YOLO** | The real-time single-stage detector family (v8/v10/v11); the edge-robotics default. |
| **DETR / RT-DETR** | Transformer detectors using set prediction; RT-DETR is NMS-free and real-time. |
| **SAM / SAM2** | Segment Anything — promptable segmentation; heavy image encoder. |
| **Depth-Anything** | Zero-shot monocular depth estimation. |
| **`Detection2DArray`** | The ROS2 `vision_msgs` standard array of 2D detections. |
| **Latency budget** | The per-stage time allocation (capture/preprocess/infer/postprocess/publish) the cycle must fit in. |
| **Execution provider** | An ONNX Runtime backend (CPU, CUDA, TensorRT, CoreML). |

---

*If a link 404s, please open an issue so we can replace it.*
