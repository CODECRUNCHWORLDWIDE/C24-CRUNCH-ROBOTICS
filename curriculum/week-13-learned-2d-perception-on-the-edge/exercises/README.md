# Week 13 — Exercises

Three drills that walk the edge-deployment path. Each takes 45–60 minutes. Do them in order — Exercise 1 (export) produces the ONNX that Exercise 2 (benchmark) and Exercise 3 (the node) consume. Exercises 1 and 2 are standalone (no ROS); Exercise 3 is a ROS2 node skeleton.

## Index

1. **[Exercise 1 — Export a YOLOv8n checkpoint to ONNX and verify it](exercise-01-export-and-verify-onnx.md)** — download a pretrained YOLOv8n, export to ONNX, run the PyTorch-vs-ONNX parity check, and inspect the graph in Netron. (~50 min, guided)
2. **[Exercise 2 — Benchmark a model across precisions and runtimes](exercise-02-benchmark-runtimes.py)** — time a model under different configurations, build a latency table, and produce the speed/accuracy data that drives a model-selection decision. (~50 min, runnable)
3. **[Exercise 3 — A ROS2 detection node](exercise-03-detection-node.py)** — a `vision_msgs/Detection2DArray` publisher skeleton with the correct QoS, acquisition-time stamps, and the decode/NMS/rescale postprocessing. (~55 min, fill-in-the-blank)

## How to work the exercises

- Install the deps once: `pip install ultralytics onnx onnxruntime numpy matplotlib`. For Path A on a Jetson, also have TensorRT (it ships with JetPack); Path B runs everything on CPU via ONNX Runtime and that's fine — you measure the latency you get.
- Exercise 1 downloads a ~6 MB `yolov8n.pt` on first run (needs internet once). Everything after runs offline.
- **Read the "it ran inside the budget" promise from the week README before you start.** The deliverable is always a *measured, per-stage* latency, not a vibe. A pipeline you haven't profiled per-stage is a pipeline you don't understand.
- Each runnable exercise (`.py`) ends with an **expected output** block. Exact milliseconds depend on your hardware (that's the point — Path A and Path B get very different numbers); the *shape* of the result and the relationships (FP16 faster than FP32, preprocessing sometimes rivaling inference) are invariant.

## Running the Python exercises

```bash
pip install ultralytics onnx onnxruntime numpy matplotlib
python3 exercise-02-benchmark-runtimes.py
# Exercise 3 is a ROS2 node — run under a sourced ROS2 Jazzy workspace:
#   ros2 run <your_pkg> detection_node     (or python3 directly with rclpy installed)
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-13` to compare.
