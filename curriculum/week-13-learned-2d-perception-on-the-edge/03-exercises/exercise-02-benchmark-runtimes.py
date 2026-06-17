#!/usr/bin/env python3
# Exercise 2 — Benchmark a model across precisions/runtimes; build a latency table
#
# Goal: Produce the MEASURED latency data that drives a model-selection decision
#       (Lecture 1 §1). You will time the full perception cycle broken into stages
#       (preprocess / inference / postprocess), the way Lecture 2 §6 demands, and
#       build a table you could defend at a design review. The headline lesson:
#       you cannot pick a model from a spec sheet — you measure it on YOUR hardware,
#       and the per-stage breakdown often surprises you (preprocessing rivals
#       inference).
#
# WHAT IT BENCHMARKS
#
#   * If a real `yolov8n.onnx` (from Exercise 1) is present, it benchmarks that
#     under ONNX Runtime with whatever execution providers are available.
#   * Otherwise it builds a small synthetic conv-net ONNX in memory so the
#     METHODOLOGY runs anywhere — the per-stage timing harness is the point, and it
#     is identical whether the model is a toy or YOLOv8n on a Jetson.
#
# HOW TO USE THIS FILE
#
#       pip install onnxruntime onnx numpy
#       python3 exercise-02-benchmark-runtimes.py
#       # with a real model from Exercise 1:
#       python3 exercise-02-benchmark-runtimes.py --onnx yolov8n.onnx --size 640
#
# ACCEPTANCE CRITERIA
#
#   [ ] Prints a per-stage latency table: preprocess / inference / postprocess /
#       total, averaged over many runs after warmup.
#   [ ] Reports which ONNX Runtime execution providers are active (CPU on Path B;
#       CUDA/TensorRT if you have onnxruntime-gpu on Path A).
#   [ ] You warm up before timing (the first inference includes one-time setup).
#   [ ] You can read the table and name the bottleneck stage.
#   [ ] You can explain why the ABSOLUTE numbers differ between your machine and a
#       Jetson, but the SHAPE of the breakdown (which stage dominates) is the
#       transferable insight.
#
# Expected output shape is at the bottom of the file.

import argparse
import time

import numpy as np
import onnxruntime as ort


def build_synthetic_onnx(path, size):
    """Build a small conv-net ONNX in memory so the harness runs with no model.

    This is NOT a detector — it exists to exercise the timing methodology. On a
    real deployment you'd point --onnx at your exported YOLOv8n.
    """
    import onnx
    from onnx import helper, TensorProto
    import onnx.numpy_helper as nh

    rng = np.random.default_rng(13)
    x = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, size, size])
    # Two conv+relu blocks to give the CPU something to chew on.
    w1 = nh.from_array(rng.standard_normal((16, 3, 3, 3)).astype(np.float32), "w1")
    w2 = nh.from_array(rng.standard_normal((16, 16, 3, 3)).astype(np.float32), "w2")
    out_dim = size - 4
    y = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 16, out_dim, out_dim])
    nodes = [
        helper.make_node("Conv", ["input", "w1"], ["c1"], kernel_shape=[3, 3]),
        helper.make_node("Relu", ["c1"], ["r1"]),
        helper.make_node("Conv", ["r1", "w2"], ["c2"], kernel_shape=[3, 3]),
        helper.make_node("Relu", ["c2"], ["output"]),
    ]
    graph = helper.make_graph(nodes, "synthetic", [x], [y], [w1, w2])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 9
    onnx.save(model, path)


def preprocess(raw_hwc, size):
    """The classic preprocessing: resize, BGR->RGB, HWC->CHW, normalize, add batch.

    We time THIS because it is a frequent bottleneck (Lecture 2 §6) and people
    forget it counts against the budget.
    """
    import cv2
    resized = cv2.resize(raw_hwc, (size, size))
    blob = resized[:, :, ::-1].transpose(2, 0, 1)
    blob = np.ascontiguousarray(blob, dtype=np.float32) / 255.0
    return blob[None]


def postprocess(output):
    """A stand-in postprocess: argmax/threshold over the output, to time the stage."""
    flat = output.reshape(output.shape[0], -1)
    return float(flat.max()), int(flat.argmax())


def bench(onnx_path, size, runs=100, warmup=10):
    sess = ort.InferenceSession(onnx_path, providers=ort.get_available_providers())
    input_name = sess.get_inputs()[0].name
    providers = sess.get_providers()

    # A fake raw camera frame (HWC, uint8) to preprocess each iteration.
    raw = (np.random.default_rng(0).integers(0, 255, (480, 640, 3))).astype(np.uint8)

    # Warmup — the first few inferences include one-time graph/kernel setup.
    pre = preprocess(raw, size)
    for _ in range(warmup):
        sess.run(None, {input_name: pre})

    t_pre = t_inf = t_post = 0.0
    for _ in range(runs):
        a = time.perf_counter()
        tensor = preprocess(raw, size)
        b = time.perf_counter()
        out = sess.run(None, {input_name: tensor})[0]
        c = time.perf_counter()
        postprocess(out)
        d = time.perf_counter()
        t_pre += b - a
        t_inf += c - b
        t_post += d - c

    n = float(runs)
    return {
        "providers": providers,
        "preprocess_ms": 1e3 * t_pre / n,
        "inference_ms": 1e3 * t_inf / n,
        "postprocess_ms": 1e3 * t_post / n,
        "total_ms": 1e3 * (t_pre + t_inf + t_post) / n,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", default=None, help="path to a real .onnx (e.g. yolov8n.onnx)")
    parser.add_argument("--size", type=int, default=160, help="input HxW (640 for YOLOv8)")
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()

    onnx_path = args.onnx
    if onnx_path is None:
        onnx_path = "/tmp/c24_synthetic.onnx"
        build_synthetic_onnx(onnx_path, args.size)
        print(f"(no --onnx given; built a synthetic conv-net at {args.size}x{args.size} "
              "to exercise the timing harness)\n")

    r = bench(onnx_path, args.size, runs=args.runs)

    print("==================== latency breakdown ====================")
    print(f"model: {onnx_path}   input: {args.size}x{args.size}   runs: {args.runs}")
    print(f"execution providers active: {r['providers']}")
    print(f"  preprocess  : {r['preprocess_ms']:6.2f} ms")
    print(f"  inference   : {r['inference_ms']:6.2f} ms")
    print(f"  postprocess : {r['postprocess_ms']:6.2f} ms")
    print(f"  TOTAL       : {r['total_ms']:6.2f} ms  ->  {1000.0/r['total_ms']:.1f} FPS")
    # Name the bottleneck.
    stages = {"preprocess": r["preprocess_ms"], "inference": r["inference_ms"],
              "postprocess": r["postprocess_ms"]}
    worst = max(stages, key=stages.get)
    print(f"  bottleneck  : {worst} ({stages[worst]:.2f} ms) <- optimize this first")
    print("===========================================================")
    print("Lesson: you MEASURE on your hardware; you don't read a spec sheet. The "
          "absolute numbers differ wildly between this machine and a Jetson Orin "
          "Nano, but the methodology and the bottleneck-finding are identical. On a "
          "real YOLOv8n you'll often find preprocessing rivals inference — the "
          "surprise Lecture 2 §6 warns about.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (SHAPE; absolute ms depend entirely on your hardware)
# -----------------------------------------------------------------------------
#
# ==================== latency breakdown ====================
# model: /tmp/c24_synthetic.onnx   input: 160x160   runs: 100
# execution providers active: ['CPUExecutionProvider']
#   preprocess  :   0.xx ms
#   inference   :   x.xx ms
#   postprocess :   0.xx ms
#   TOTAL       :   x.xx ms  ->  xxx.x FPS
#   bottleneck  : inference (x.xx ms) <- optimize this first
# ===========================================================
# Lesson: you MEASURE on your hardware ...
#
# With a REAL yolov8n.onnx at 640x640 on a CPU (Path B) you'll see inference in the
# tens of ms and preprocessing several ms; on a Jetson Orin Nano FP16 (Path A,
# native TensorRT) inference drops to ~11 ms and preprocessing can become the
# bottleneck. The INVARIANT: warm up, time each stage separately, name the worst
# bar. That discipline is the whole exercise; the numbers are hardware-specific.
# -----------------------------------------------------------------------------
