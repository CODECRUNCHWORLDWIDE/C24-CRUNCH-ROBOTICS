# Week 39 — Edge ML Optimization for Robotics

Welcome to the week where milliseconds stop being a metric and start being a *design constraint*. By Friday you will be able to take a perception-to-policy graph that "works" on a workstation, profile it honestly on a Jetson Orin, find the single most expensive millisecond, and buy it back with the right optimization — INT8 quantization, FP16, layer fusion, a composable container, or a smaller model — while knowing *exactly* what accuracy you traded to get it.

You have spent thirty-eight weeks building the pieces: the YOLO detector from Week 13, the Diffusion Policy from Week 29, the VLA wrapper from Week 37. Every one of them ran "fast enough" in isolation on a desktop GPU. This week you stand them up *together* on the hardware the robot actually carries — an Orin Nano with 8 GB shared between CPU and GPU and a power budget you cannot exceed — and discover that the sum of three "fast enough" components is a graph that misses its 50 ms end-to-end budget by 3x. That is the normal first measurement. The skill is what you do next.

The one sentence to internalize before you read another line: **on edge compute, you do not optimize what feels slow — you optimize what the profiler proves is slow, and you re-measure after every change.** Robotics engineers who guess waste days speeding up a node that was never on the critical path. The profiler is `nsys` and `trtexec` and a Foxglove latency panel, not your intuition. This week trains the measure-first reflex until it is the only reflex you have.

This is the last technical-content week before the capstone phase. After this, the syllabus thins out and the work becomes integration, safety, and defense. Treat this week as the one that makes your capstone *fit on the robot*.

## Learning objectives

By the end of this week, you will be able to:

- **Profile** an integrated ROS2 perception-and-policy graph on a Jetson Orin (or a documented x86 + discrete-GPU stand-in) with `nsys`, `trtexec`, `tegrastats`, and a node-level Foxglove latency panel — and produce a Gantt-style block diagram of where every millisecond goes.
- **Build** a TensorRT engine from an ONNX model, choosing FP32 / FP16 / INT8 deliberately, and read a `trtexec` profile to see which layers fused and which fell back to a slow kernel.
- **Quantize** a detector to INT8 with post-training quantization (PTQ) using a representative calibration set, measure the mAP drop, and decide whether the speedup is worth the accuracy cost for *your* task.
- **Explain** the difference between post-training quantization and quantization-aware training (QAT), when each is appropriate, and why QAT recovers accuracy that PTQ cannot.
- **Apply** structured and unstructured pruning, knowledge distillation, and 2:4 structured sparsity, and state honestly which of these actually pays off on Orin-class hardware in 2026 and which is academic.
- **Reason** about the memory hierarchy that makes or breaks edge inference: unified memory on Jetson, zero-copy vs. host-device copies, the cost of a pointcloud crossing a process boundary, and why a composable-node container often buys more than any model trick.
- **Treat** the latency budget as a first-class, version-controlled artifact: a table that allocates the 50 ms cycle across perception, planning, control, and policy, with a measured p50/p95 per stage and a hard fail when the sum regresses.
- **Decide**, given a latency budget and an accuracy floor, the *smallest* model and the *cheapest* precision that clears both — the actual job of a robotics ML engineer on the edge.

## Prerequisites

This week assumes you have completed C24 Weeks 1–38, and specifically:

- The **Week 13 learned-2D-perception node** — a YOLOv8n exported to ONNX and run through TensorRT. You will reuse this checkpoint; have it, or re-export it Monday morning.
- The **Week 29 Diffusion Policy** and the **Week 37 OpenVLA wrapper** — at least their inference paths, even if you run them in sim. This week profiles the *integrated* graph, so all three need to load.
- Comfort with **ONNX** as an interchange format and the `torch.onnx.export` / `onnxruntime` basics from the AI/DS prerequisite track.
- Access to a **Jetson Orin Nano (8 GB)** with JetPack 6.x (Path A), *or* a documented x86 machine with an NVIDIA GPU and the same TensorRT version (Path B) where you simulate the edge constraint by capping power and clocks. Both paths clear the week.
- The `nvidia-jetpack`, `tensorrt`, `onnx`, `onnxruntime-gpu`, and `pycuda` packages installed, and `trtexec` on your `PATH`.

You do **not** need to have trained any of these models from scratch — you are optimizing *deployment*, not training. If your Week 13/29/37 artifacts are lost, the exercises provide standalone ONNX models so you are never blocked.

## Topics covered

- **The latency budget as an artifact.** Allocating a 50 ms end-to-end cycle across perception, planning, control, and policy; measuring p50/p95 per stage; the regression gate that fails CI when the sum creeps up.
- **Profiling on the edge.** `tegrastats` (the Jetson power/clock/thermal truth), `nsys` (the system-wide timeline), `trtexec --dumpProfile` (per-layer kernel timing), and a ROS2 message-timestamp latency panel in Foxglove. The measure-first discipline.
- **TensorRT precision modes.** FP32 baseline, FP16 (the free lunch on Orin's tensor cores), INT8 (the real win, with a real cost), and the build flags (`--fp16`, `--int8`, `--best`) that select them. Layer fusion and what `trtexec` tells you fused.
- **Post-training quantization (PTQ).** The calibration set, the calibrator (entropy / min-max), the per-tensor vs. per-channel scale choice, and how to measure the mAP delta on a held-out eval set.
- **Quantization-aware training (QAT).** Fake-quant nodes, the straight-through estimator, why QAT recovers the accuracy PTQ loses, and the cost (a training loop) that makes it a last resort, not a first one.
- **Pruning and sparsity.** Unstructured magnitude pruning (great on paper, rarely accelerates on GPU), structured channel pruning (real speedup, real retraining), and NVIDIA 2:4 structured sparsity (hardware-accelerated on Ampere/Orin tensor cores).
- **Knowledge distillation.** Training a small student to mimic a large teacher's soft outputs; when distillation beats "just train the small model"; the Depth-Anything-v2-to-small story as a worked case.
- **The memory hierarchy.** Jetson unified memory, `cudaHostAlloc` / mapped memory, zero-copy, the host↔device copy tax, and why moving a pointcloud between two ROS2 processes can cost more than the inference itself — the composable-container fix.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The latency budget; profiling with nsys/tegrastats/trtexec     |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | TensorRT FP16/INT8; building engines; reading layer profiles   |    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0h      |     5.5h    |
| Wednesday | PTQ calibration + mAP delta; the detector quant exercise       |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     1h       |    0.5h    |     6.5h    |
| Thursday  | QAT, pruning, distillation, 2:4 sparsity; the memory hierarchy |    1h    |    1.5h   |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7.5h    |
| Friday    | Composable containers; the Gantt; budget-as-artifact challenge |    0h    |    0h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     5h      |
| Saturday  | Mini-project deep work — the integrated-graph optimization     |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, latency-report polish                            |    0h    |    0h     |     0h     |    1h     |   0h     |     1.5h     |    0h      |     2.5h    |
| **Total** |                                                                | **6h**   | **6.5h**  | **4h**     | **3.5h**  | **6h**   | **9.5h**     | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview (you are here) |
| [resources.md](./01-resources.md) | TensorRT, ONNX, Jetson, quantization, and pruning references, all current to 2026 |
| [lecture-notes/01-the-latency-budget-and-profiling-the-edge.md](./02-lecture-notes/01-the-latency-budget-and-profiling-the-edge.md) | The latency budget as an artifact, and how to profile a graph on Jetson without guessing |
| [lecture-notes/02-quantization-pruning-distillation-and-memory.md](./02-lecture-notes/02-quantization-pruning-distillation-and-memory.md) | TensorRT precision, PTQ/QAT, pruning, distillation, 2:4 sparsity, and the memory hierarchy |
| [exercises/README.md](./03-exercises/00-overview.md) | Index of the three exercises |
| [exercises/exercise-01-profile-the-graph.md](./03-exercises/exercise-01-profile-the-graph.md) | Profile the integrated graph and build a Gantt-style latency block diagram |
| [exercises/exercise-02-int8-calibrate.py](./03-exercises/exercise-02-int8-calibrate.py) | Calibrate a detector to INT8 with a representative set and measure the accuracy delta |
| [exercises/exercise-03-latency-budget.py](./03-exercises/exercise-03-latency-budget.py) | A runnable latency-budget checker that fails when the per-stage sum regresses |
| [challenges/README.md](./04-challenges/00-overview.md) | Index of the weekly challenge |
| [challenges/challenge-01-hit-the-budget.md](./04-challenges/challenge-01-hit-the-budget.md) | Take a graph 3x over budget and bring it under 50 ms with a documented accuracy cost |
| [quiz.md](./05-quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./06-homework.md) | Six problems including the version-controlled latency-budget artifact |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The `crunchbot_latency` profiling + budget package, end to end |

## The "it fits on the robot" promise

Every week in C24 ends in something concrete. This week's marker is a single line at the top of your latency report:

```
End-to-end perception→policy cycle on Orin Nano (15 W mode):
  baseline:  148 ms p95   (FAIL — budget is 50 ms)
  optimized:  44 ms p95   (PASS — INT8 detector, FP16 policy, composable container)
  accuracy cost: detector mAP@0.5 0.512 → 0.498  (-1.4 pts, within the 3-pt floor)
```

If you cannot produce that line — a measured before, a measured after, and the *named* accuracy you paid — you are not done. A speedup with no accuracy number is not an engineering result; it is a guess that got lucky.

## Stretch goals

If you finish the regular work early:

- Profile the **same** INT8 engine on three Jetson power modes (`nvpmodel -m 0/1/2`) and plot the latency/power Pareto front. The cheapest mode that clears your budget is the one that ships.
- Try **2:4 structured sparsity** on the detector backbone (`--sparsity=enable` in `trtexec`) and measure whether Orin's tensor cores actually accelerate it for *your* layer shapes. Many do not.
- Convert the Diffusion Policy's denoising loop to FP16 and measure the action-quality delta on the Week 29 multimodal eval state. Diffusion is more precision-sensitive than detection — find out how much.
- Distill the Depth-Anything-v2 model down a size class and measure both the latency win and the depth-RMSE cost on a held-out RGB-D sequence.

## Up next

**Week 40 — Phase 5 integration + capstone milestone.** The capstone problem statement is unsealed and you stand up the *whole* system end-to-end in sim. The optimized graph you produce this week is exactly what makes that integration fit its budget — so push your latency report and your `crunchbot_latency` package before you start, because Week 40 assumes the graph already fits.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
