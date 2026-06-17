# Week 13 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 14. Answer key is at the bottom — don't peek.

---

**Q1.** On a Jetson Orin Nano with a 30 ms perception budget, how should you choose a detection model?

- A) Always the most accurate model available.
- B) The *smallest* model that clears a measured accuracy floor inside the measured latency budget — start small and step up only if accuracy demands it.
- C) Whatever model is newest.
- D) The largest model that fits in memory.

---

**Q2.** What is ONNX, and what is it *not*?

- A) A fast inference runtime that replaces PyTorch.
- B) A portable model *interchange* format — a framework-agnostic description of the graph. It is **not** itself a fast runtime; a runtime (TensorRT/ORT/OpenVINO) consumes the ONNX.
- C) A training framework.
- D) A quantization algorithm.

---

**Q3.** You export a model to ONNX without calling `model.eval()` first. What happens?

- A) Nothing; eval mode doesn't affect export.
- B) BatchNorm/dropout export in training mode, so the ONNX silently differs from the validated model — the parity check catches it as a large diff.
- C) The export crashes.
- D) The model exports but at half size.

---

**Q4.** Why run the PyTorch-vs-ONNX parity check before deploying, and what's a passing result?

- A) To measure latency; passing is < 30 ms.
- B) To prove the export didn't change the model; passing is a max-abs-diff around `1e-6` (float reordering). A diff of `0.3` means the export broke the model — stop.
- C) To check the file size; passing is < 10 MB.
- D) It's optional decoration.

---

**Q5.** A TensorRT engine built on your RTX 4090 workstation won't load on the Jetson. Why?

- A) The ONNX was corrupted.
- B) An engine is *hardware-specific* — TensorRT autotunes kernels for the exact GPU it builds on, so you must build the engine *on the target* (the Jetson).
- C) The Jetson lacks TensorRT.
- D) The opset is wrong.

---

**Q6.** Why is FP16 considered a near-free speedup on the edge, while INT8 is a real trade?

- A) FP16 is slower but more accurate.
- B) FP16 roughly doubles throughput on Jetson tensor cores with negligible accuracy loss (one flag); INT8 is a bigger speedup but costs real accuracy and needs a calibration set to choose scales.
- C) They are identical.
- D) INT8 is free and FP16 costs accuracy.

---

**Q7.** What is a calibration set for, in INT8 quantization?

- A) To retrain the model.
- B) A representative sample of *deployment-like* inputs used to measure activation ranges and choose the INT8 scales; calibrating on the wrong data gives wrong scales and a big accuracy drop.
- C) To measure latency.
- D) To validate the ONNX export.

---

**Q8.** A YOLOv8 ONNX outputs a tensor of shape `[1, 84, 8400]`. What do the numbers mean, and what must you do before decoding?

- A) `[batch, height, width]`; resize it.
- B) `[batch, 4 box + 80 classes, 8400 anchors]`; you must **transpose** to `[8400, 84]` before indexing per-anchor, or you get garbage.
- C) `[batch, anchors, classes]`; nothing special.
- D) `[classes, batch, anchors]`; normalize it.

---

**Q9.** Your detection node subscribes to `/camera/image_raw` with the default (RELIABLE) QoS and receives nothing. Why?

- A) The model is too big.
- B) The camera publishes BEST_EFFORT; a RELIABLE subscriber can't be satisfied by a BEST_EFFORT publisher — the Week 5 silent failure. Use `qos_profile_sensor_data`.
- C) The ONNX is broken.
- D) The frame_id is empty.

---

**Q10.** Why must a detection carry the *image's* acquisition stamp rather than `now()` at publish time?

- A) `now()` is slower.
- B) The image went through preprocessing + inference + postprocessing (tens of ms); stamping with `now()` tells downstream consumers the detection happened tens of ms later than it did, injecting motion error on a moving robot.
- C) Detections can't carry a header.
- D) It doesn't matter.

---

**Q11.** You profile your 3-FPS detection pipeline and find inference is 11 ms but preprocessing is 350 ms. A teammate says "swap in a smaller model." Why is that the wrong fix?

- A) Smaller models are less accurate.
- B) Inference was never the bottleneck — preprocessing is. A smaller model saves a few ms of inference while 350 ms of preprocessing remains; you must vectorize/GPU the preprocessing instead.
- C) Smaller models don't export to ONNX.
- D) The teammate is right.

---

**Q12.** Which runtime lets the *same* `.onnx` run on CPU, NVIDIA GPU, and Apple silicon by changing one argument?

- A) TensorRT.
- B) ONNX Runtime — via execution providers (`CPUExecutionProvider`, `CUDAExecutionProvider`, `CoreMLExecutionProvider`). This is the portable Path-B fallback.
- C) OpenVINO.
- D) PyTorch.

---

**Q13.** When you profile and find Non-Max Suppression (postprocessing) is your bottleneck, what's the *structural* fix?

- A) Use a bigger image.
- B) Switch to an NMS-free detector (YOLOv10 or RT-DETR), which eliminates the NMS stage entirely — you can't vectorize your way out of NMS the way you can out of preprocessing.
- C) Increase the confidence threshold to zero.
- D) Quantize to INT8.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Pick the smallest sufficient model on the Pareto front; start small, step up only if the accuracy floor demands it. (Lecture 1 §1.)
2. **B** — ONNX is a portable interchange format, not a runtime; a runtime consumes it. PyTorch trains, ONNX transports, the runtime runs. (Lecture 1 §3.)
3. **B** — Without `model.eval()`, BatchNorm/dropout export wrong and the ONNX differs from the validated model; the parity check catches it. (Lecture 1 §4.2.)
4. **B** — The parity check proves the export didn't change the model; passing is ~`1e-6`, a diff of `0.3` is a broken export. Gate before deploy. (Lecture 1 §5.)
5. **B** — An engine is hardware-specific (kernel autotuning per GPU); build it on the target. (Lecture 2 §1.)
6. **B** — FP16 ~2× with negligible accuracy loss (one flag); INT8 bigger but costs real accuracy and needs calibration. (Lecture 2 §2–3.)
7. **B** — The calibration set measures activation ranges to choose INT8 scales; it must look like deployment data. (Lecture 2 §3.)
8. **B** — `[batch, 4+classes, anchors]`; transpose to `[anchors, 84]` before decoding or you index classes as anchors. (Lecture 1 §7.)
9. **B** — Camera is BEST_EFFORT; a RELIABLE subscriber gets nothing — the Week 5 silent failure on your detector. Use sensor QoS. (Lecture 2 §5.)
10. **B** — Stamp at acquisition; `now()` injects tens of ms of motion error downstream. (Lecture 2 §5; Week 5 §3.1.)
11. **B** — Inference wasn't the bottleneck; preprocessing was. Vectorize/GPU the preprocessing — a smaller model leaves the 350 ms untouched. (Lecture 2 §6.)
12. **B** — ONNX Runtime's execution providers run one ONNX on many backends; the portable Path-B fallback. (Lecture 2 §4.)
13. **B** — NMS-free detectors (YOLOv10/RT-DETR) delete the NMS stage; that's the structural fix when postprocessing dominates. (Lecture 1 §2; Lecture 2 §6.2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./06-homework.md).
