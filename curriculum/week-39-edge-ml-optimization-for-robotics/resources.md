# Week 39 — Resources

Every resource here is **free**. NVIDIA's TensorRT and Jetson docs are public; ONNX is an open standard; the quantization and pruning literature is on arXiv. No paywalled books are linked. Versions are pinned to **TensorRT 10.x** and **JetPack 6.x** (the 2026 LTS line for Orin); swap version numbers if you are on a newer JetPack, but the concepts are stable.

## Required reading (work it into your week)

- **TensorRT Developer Guide — Working with INT8** — the canonical PTQ + calibration reference. Read the calibration and the explicit-quantization sections twice:
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/work-with-int8.html>
- **TensorRT — Performance Best Practices** — layer fusion, builder flags, the "why didn't my layer fuse" checklist:
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/best-practices.html>
- **ONNX Runtime — Graph Optimizations and Execution Providers** — the CUDA and TensorRT EPs, and how ORT and TRT relate:
  <https://onnxruntime.ai/docs/performance/model-optimizations/>
- **Jetson Orin — Power and Performance (`nvpmodel`, `jetson_clocks`, `tegrastats`)** — the power-mode and clock truth on the device:
  <https://docs.nvidia.com/jetson/archives/r36.3/DeveloperGuide/SD/PlatformPowerAndPerformance.html>
- **NVIDIA Nsight Systems user guide (the `nsys` profiler)** — how to capture and read a system timeline:
  <https://docs.nvidia.com/nsight-systems/UserGuide/index.html>

## The papers (skim for the idea, not the proofs)

You will not implement these from scratch. But you should be able to say, in one sentence, what each contributed.

- **Jacob et al., "Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference" (2017)** — the foundational PTQ/QAT paper; the fake-quant + straight-through-estimator trick:
  <https://arxiv.org/abs/1712.05877>
- **Han et al., "Deep Compression: Pruning, Quantization, Huffman Coding" (2016)** — where structured compression as a discipline starts:
  <https://arxiv.org/abs/1510.00149>
- **Hinton et al., "Distilling the Knowledge in a Neural Network" (2015)** — the soft-label distillation idea, still the baseline in 2026:
  <https://arxiv.org/abs/1503.02531>
- **Mishra et al., "Accelerating Sparse Deep Neural Networks" (2021, NVIDIA)** — the 2:4 structured-sparsity scheme that Ampere/Orin tensor cores accelerate:
  <https://arxiv.org/abs/2104.08378>
- **Yang et al., "Depth Anything V2" (2024)** — the depth model you may distill; read for the teacher-learner setup:
  <https://arxiv.org/abs/2406.09414>

## API references (open all week)

- **`trtexec` command-line wrapper** — your fastest path to an engine and a per-layer profile (`--fp16`, `--int8`, `--best`, `--dumpProfile`, `--exportProfile`):
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/command-line-program.html>
- **TensorRT Python API** — `Builder`, `BuilderConfig`, `IInt8Calibrator`, `Runtime`:
  <https://docs.nvidia.com/deeplearning/tensorrt/latest/_static/python-api/index.html>
- **PyTorch — `torch.onnx.export` and the quantization toolkit** (`torch.ao.quantization`, fake-quant for QAT):
  <https://pytorch.org/docs/stable/onnx.html>
- **NVIDIA `pytorch-quantization` / TensorRT Model Optimizer** — the supported QAT path for TRT deployment in 2026:
  <https://github.com/NVIDIA/TensorRT-Model-Optimizer>
- **`image_transport` and `composable nodes` in ROS2** — the zero-copy and intra-process-comms story:
  <https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Composition.html>

## Robotics-specific deployment (read the code that does it right)

- **`isaac_ros` (NVIDIA Isaac ROS)** — production TensorRT-backed perception nodes (`isaac_ros_dnn_inference`, `isaac_ros_tensor_rt`); read how they wrap an engine in a composable node:
  <https://nvidia-isaac-ros.github.io/>
- **`ros2_control` real-time guidance** — why the control loop must not share a thread with inference:
  <https://control.ros.org/jazzy/doc/ros2_control/doc/index.html>
- **`vision_msgs`** — the `Detection2DArray` / `Detection3DArray` your inference node should publish:
  <https://github.com/ros-perception/vision_msgs>

## Tools you'll use this week

- **`trtexec`** — build engines, benchmark, dump per-layer profiles. Ships with TensorRT.
- **`nsys profile`** — system-wide timeline; capture CUDA kernels, memcpys, and your ROS2 callbacks in one view.
- **`tegrastats`** — the Jetson-only truth on CPU/GPU/EMC load, power rails, and thermal throttle. Run it in a side terminal during every benchmark.
- **`nvpmodel -m <N>` / `jetson_clocks`** — set the power mode (and pin clocks) so your numbers are reproducible. Always record which mode you measured in.
- **`polygraphy`** — TensorRT's debugging Swiss-army knife; compare ONNX-Runtime vs TRT outputs layer by layer to catch a quantization regression:
  <https://github.com/NVIDIA/TensorRT/tree/main/tools/Polygraphy>
- **Foxglove** — the message-timestamp latency panel for the end-to-end ROS2 cycle.

## Talks worth your time (free, no signup)

- **GTC sessions on TensorRT and Jetson deployment** — NVIDIA posts the recordings free; search the on-demand catalog for "TensorRT INT8" and "Jetson Orin optimization":
  <https://www.nvidia.com/gtc/on-demand/>
- **ROSCon — edge-inference and `isaac_ros` sessions** — the OSRF archive; search for the perception-on-Jetson talks:
  <https://roscon.ros.org/>

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **FP32 / FP16 / INT8** | 32-bit float / 16-bit float / 8-bit integer arithmetic. Lower precision = faster + smaller, with an accuracy risk. |
| **PTQ** | Post-Training Quantization — quantize an already-trained model using a calibration set, no retraining. |
| **QAT** | Quantization-Aware Training — insert fake-quant ops and fine-tune so the model learns to tolerate quantization. |
| **Calibration set** | A small, representative sample of real inputs used to pick INT8 scale factors. |
| **Layer fusion** | TensorRT merging e.g. conv+bias+ReLU into one kernel to cut launch overhead and memory traffic. |
| **2:4 sparsity** | A structured pattern (2 of every 4 weights zero) that Ampere/Orin tensor cores execute at ~2x. |
| **Distillation** | Training a small "learner" to mimic a large "teacher" model's soft outputs. |
| **Unified memory** | Jetson's CPU and GPU share physical RAM; a host↔device copy can be elided (zero-copy) if you allocate right. |
| **Composable node** | A ROS2 node loaded into a shared process so messages pass by pointer (intra-process comms), not by serialization. |
| **`trtexec`** | The TensorRT CLI that builds and benchmarks an engine and dumps a per-layer profile. |
| **p50 / p95** | The 50th / 95th percentile latency. You budget against p95, not the mean. |
| **mAP** | mean Average Precision — the detector accuracy metric you watch when quantizing. |
| **Throttle** | The Jetson clocking itself down under thermal/power limits; the silent killer of "it was fast yesterday." |

---

*If a link 404s, please open an issue so we can replace it.*
