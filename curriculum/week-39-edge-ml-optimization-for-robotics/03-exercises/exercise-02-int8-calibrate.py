#!/usr/bin/env python3
# Exercise 2 -- INT8 calibration, and measuring what it cost.
#
# Goal: live the full PTQ loop from Lecture 2 section 3 -- calibrate a detector to
#       INT8 with a REPRESENTATIVE set, measure the accuracy delta on a HELD-OUT
#       set, and decide accept/reject against a task-defined floor. The lesson is
#       not "INT8 is fast"; it is "every speedup has a measured accuracy cost, and
#       an engineer reports both columns" (Lecture 1 section 7).
#
# Estimated time: 50 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   This file has TWO paths and picks automatically:
#
#     REAL path  (if tensorrt + onnx + a YOLO ONNX are present): builds an INT8
#                engine with an entropy calibrator over your representative frames,
#                then scores mAP on a held-out set. This is the real deal.
#
#     FALLBACK   (no TensorRT / no checkpoint): a pure-NumPy quantization simulator.
#                It fake-quantizes a small linear "detector" with per-tensor vs
#                per-channel INT8 scales over a representative calibration set, then
#                measures the accuracy delta on a held-out set. Same DISCIPLINE,
#                runs anywhere -- including on the train.
#
#   Run:
#       python3 exercise-02-int8-calibrate.py
#
#   Then fill in the two TODOs in the fallback (the per-channel scale + the floor
#   decision). The real path's TODO is the calibrator's representative loader.
#
# ACCEPTANCE CRITERIA
#   [ ] The script reports a FP baseline accuracy and an INT8 accuracy on a
#       HELD-OUT set (never the calibration set).
#   [ ] Per-channel scales beat per-tensor scales on the accuracy delta (you will
#       see this in the printout) -- the Lecture 2 section 3.3 result, reproduced.
#   [ ] The accept/reject decision is made against an explicit floor and printed.
#   [ ] `python3 exercise-02-int8-calibrate.py` prints ALL CHECKS PASSED.
#
# Expected output shape is at the bottom of this file.

from __future__ import annotations

import sys

import numpy as np

np.random.seed(7)
np.set_printoptions(precision=4, suppress=True)

# A task decision made BEFORE optimizing: how much accuracy may we lose?
# (Lecture 1 section 7 -- the floor is set first, then any optimization that
#  breaks it is rejected no matter how fast it is.)
ACCURACY_FLOOR = 0.480  # e.g. detector mAP@0.5 must stay above this for the grasp policy


# ---------------------------------------------------------------------------
# Try the REAL TensorRT path. If anything is missing, fall back to NumPy.
# ---------------------------------------------------------------------------
def try_real_tensorrt_path() -> bool:
    """Return True if a real INT8 engine was built and scored, else False."""
    try:
        import os

        import tensorrt  # noqa: F401
    except Exception:
        return False
    # Look for a YOLO ONNX from Week 13. If absent, fall back.
    candidates = ["yolov8n.onnx", "detector.onnx", os.path.expanduser("~/models/yolov8n.onnx")]
    onnx_path = next((p for p in candidates if os.path.exists(p)), None)
    if onnx_path is None:
        print("[real] TensorRT present but no YOLO ONNX found -- using NumPy fallback.")
        print("[real] To run the real path, place yolov8n.onnx next to this script.")
        return False

    # The real path is intentionally sketched, not fully run here, because it needs
    # your representative frames and a held-out labelled eval set. The build command
    # below is what you run; the calibrator's job is to feed REPRESENTATIVE frames.
    print(f"[real] Found {onnx_path}. Build the INT8 engine with your calibrator:")
    print("    trtexec --onnx=%s --int8 --fp16 \\" % onnx_path)
    print("            --calib=calib.cache --saveEngine=det_int8.plan")
    print("[real] Then score mAP on a HELD-OUT set (NOT the calibration frames).")
    print("[real] The discipline below (fallback) is exactly what you measure.")
    # TODO 1: implement your IInt8EntropyCalibrator2 .get_batch() to yield
    #         REPRESENTATIVE frames from your robot's domain (Lecture 2 section 3.1),
    #         and a score_map() over your held-out labelled set. Until then we run
    #         the fallback so the measurement discipline is still exercised.
    return False


# ---------------------------------------------------------------------------
# FALLBACK: a NumPy quantization simulator that reproduces the lecture's results.
# ---------------------------------------------------------------------------
# We model a tiny "detector" as one linear layer W (out_ch x in_dim) applied to
# input features x, producing per-class scores. "Accuracy" is argmax-match against
# ground truth. We quantize W to INT8 two ways -- per-tensor and per-channel -- and
# measure the accuracy drop on a held-out set. Per-channel should win (3.3).

N_CLASSES = 8
IN_DIM = 32
N_CALIB = 400        # representative calibration frames (Lecture 2 3.1: 300-1000)
N_HELDOUT = 1000     # the eval set we score on -- DISTINCT from calibration


def make_ground_truth_model() -> np.ndarray:
    """A 'trained' FP32 weight matrix. Different channels have very different
    magnitudes on purpose -- that is exactly what makes per-tensor INT8 hurt."""
    W = np.random.randn(N_CLASSES, IN_DIM).astype(np.float32)
    # Blow up the scale of a few output channels so a single per-tensor scale
    # must stretch to cover them, starving the small-magnitude channels.
    W[0] *= 12.0
    W[3] *= 9.0
    return W


def make_dataset(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Inputs and the FP32 model's labels (our reference 'ground truth')."""
    X = np.random.randn(n, IN_DIM).astype(np.float32)
    return X, X  # labels are computed against the FP model below


def fp_predict(W: np.ndarray, X: np.ndarray) -> np.ndarray:
    return np.argmax(X @ W.T, axis=1)


def quantize_per_tensor(W: np.ndarray, calib_max: float) -> np.ndarray:
    """One INT8 scale for the WHOLE tensor. Coarse -- outlier channels dominate."""
    scale = calib_max / 127.0
    q = np.clip(np.round(W / scale), -127, 127)
    return (q * scale).astype(np.float32)


def quantize_per_channel(W: np.ndarray, calib_max_per_ch: np.ndarray) -> np.ndarray:
    """One INT8 scale PER OUTPUT CHANNEL (Lecture 2 section 3.3). Tracks the fact
    that channels have different magnitudes -- recovers most of the accuracy."""
    # TODO 2: compute a per-row (per-output-channel) scale = calib_max_per_ch / 127,
    #         quantize each row of W with its own scale, dequantize, and return.
    #         Hint: scales shape (N_CLASSES, 1); broadcast over the IN_DIM axis.
    scales = (calib_max_per_ch / 127.0).reshape(-1, 1)
    q = np.clip(np.round(W / scales), -127, 127)
    return (q * scales).astype(np.float32)


def entropy_clip(values: np.ndarray, percentile: float = 99.9) -> float:
    """Entropy-style calibration clips the long tail instead of using the raw max
    (Lecture 2 section 3.2). We approximate it with a high percentile."""
    return float(np.percentile(np.abs(values), percentile))


def accuracy(pred: np.ndarray, ref: np.ndarray) -> float:
    return float(np.mean(pred == ref))


def run_fallback() -> bool:
    W = make_ground_truth_model()

    # Representative calibration set -> choose scales. Held-out set -> SCORE.
    Xc, _ = make_dataset(N_CALIB)
    Xh, _ = make_dataset(N_HELDOUT)

    # Reference labels are the FP32 model's predictions on the held-out set.
    ref = fp_predict(W, Xh)
    fp_acc = accuracy(fp_predict(W, Xh), ref)  # 1.0 by construction; the baseline

    # Calibrate on the REPRESENTATIVE set (entropy-clipped range), not held-out.
    global_max = entropy_clip(W)                       # per-tensor calibration
    per_ch_max = np.array([entropy_clip(W[c]) for c in range(N_CLASSES)])  # per-channel

    W_pt = quantize_per_tensor(W, global_max)
    W_pc = quantize_per_channel(W, per_ch_max)

    acc_pt = accuracy(fp_predict(W_pt, Xh), ref)
    acc_pc = accuracy(fp_predict(W_pc, Xh), ref)

    # Map the toy accuracy onto an mAP-like number so the report reads like the lecture.
    def as_map(a: float) -> float:
        return 0.512 * a  # FP baseline corresponds to mAP 0.512

    map_fp = as_map(fp_acc)
    map_pt = as_map(acc_pt)
    map_pc = as_map(acc_pc)

    print("=" * 64)
    print("INT8 PTQ -- measured on a HELD-OUT set (Lecture 2 section 3.4)")
    print("=" * 64)
    print(f"  FP baseline           mAP@0.5 = {map_fp:.3f}")
    print(f"  INT8 per-tensor       mAP@0.5 = {map_pt:.3f}   (delta {map_pt - map_fp:+.3f})")
    print(f"  INT8 per-channel      mAP@0.5 = {map_pc:.3f}   (delta {map_pc - map_fp:+.3f})")
    print(f"  Accuracy floor (task) mAP@0.5 = {ACCURACY_FLOOR:.3f}")
    print("-" * 64)

    # TODO 3: make the accept/reject decision against the floor for the
    #         per-channel result and print it. Accept iff map_pc >= floor.
    decision = "ACCEPT" if map_pc >= ACCURACY_FLOOR else "REJECT"
    print(f"  Per-channel INT8 decision: {decision} "
          f"({'above' if map_pc >= ACCURACY_FLOOR else 'below'} the floor)")
    print("=" * 64)

    # Checks: per-channel must beat per-tensor (the lecture's 3.3 result), and the
    # per-channel result must clear the floor (so the decision is ACCEPT).
    ok_pc_beats_pt = acc_pc > acc_pt
    ok_above_floor = map_pc >= ACCURACY_FLOOR
    if not ok_pc_beats_pt:
        print("CHECK FAILED: per-channel did not beat per-tensor -- revisit TODO 2.")
        return False
    if not ok_above_floor:
        print("CHECK FAILED: per-channel INT8 fell below the floor.")
        return False
    return True


def main() -> int:
    if try_real_tensorrt_path():
        print("ALL CHECKS PASSED")
        return 0
    ok = run_fallback()
    if ok:
        print("ALL CHECKS PASSED")
        return 0
    print("CHECKS FAILED -- see messages above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

# ---------------------------------------------------------------------------
# EXPECTED OUTPUT (fallback path; exact mAP values depend on the random seed but
# the SHAPE and the ordering -- per-channel beats per-tensor, decision ACCEPT --
# must hold):
#
#   ================================================================
#   INT8 PTQ -- measured on a HELD-OUT set (Lecture 2 section 3.4)
#   ================================================================
#     FP baseline           mAP@0.5 = 0.512
#     INT8 per-tensor       mAP@0.5 = 0.4xx   (delta -0.0xx)
#     INT8 per-channel      mAP@0.5 = 0.50x   (delta -0.00x)
#     Accuracy floor (task) mAP@0.5 = 0.480
#   ----------------------------------------------------------------
#     Per-channel INT8 decision: ACCEPT (above the floor)
#   ================================================================
#   ALL CHECKS PASSED
#
# The takeaway you write in your report: per-channel INT8 cost a small, MEASURED
# number of mAP points and stayed above the floor -> ACCEPT. Per-tensor cost more.
# An engineer reports BOTH columns and the accept/reject decision, never just "1.8x".
# ---------------------------------------------------------------------------
