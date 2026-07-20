# Week 39 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 40. Answer key is at the bottom — don't peek.

---

**Q1.** On a Jetson Orin Nano, which resource is most often the scarce one that bottlenecks an inference graph?

- A) FLOPs (raw compute).
- B) Memory bandwidth (the CPU/GPU shared LPDDR5 bus).
- C) Disk I/O.
- D) Network throughput.

---

**Q2.** Why does a latency budget measure and gate on **p95** rather than the mean?

- A) p95 is easier to compute.
- B) The robot misses control deadlines at the tail; a 9 ms mean with a 22 ms p95 has a stall problem the mean hides.
- C) The mean is always larger than p95.
- D) ROS2 only reports p95.

---

**Q3.** You profile the depth stage: `tegrastats` shows `GR3D_FREQ 42%` during it and `nsys` shows a fat `cudaMemcpyDeviceToHost` bar. What is the right fix?

- A) Quantize the depth stage to INT8.
- B) It's memory-bound — eliminate the copy (zero-copy / composable container); a model trick won't help a stage that was waiting on memory.
- C) Prune 30% of the channels.
- D) Increase the model resolution.

---

**Q4.** Why is FP16 usually the first optimization to try on Orin, and usually "free"?

- A) FP16 increases accuracy.
- B) Orin's tensor cores execute FP16 natively at ~2x FP32, and detection/depth networks typically show unmeasurable accuracy loss in FP16.
- C) FP16 requires no engine rebuild.
- D) FP16 disables thermal throttling.

---

**Q5.** What is the purpose of the INT8 **calibration set**?

- A) To retrain the model's weights.
- B) To let TensorRT observe activation distributions on representative inputs and choose INT8 scale factors that minimize quantization error.
- C) To measure final accuracy.
- D) To warm up the GPU before benchmarking.

---

**Q6.** You quantize a warehouse robot's detector to INT8 but calibrate on COCO images. What goes wrong?

- A) Nothing — calibration data doesn't matter.
- B) The scales are tuned to a distribution the robot never sees; INT8 is accurate on COCO-like images and wrong on warehouse frames. Calibrate on representative (warehouse) frames.
- C) The engine fails to build.
- D) The model becomes FP32 again.

---

**Q7.** Why does **per-channel** weight quantization usually beat **per-tensor** for INT8?

- A) It uses fewer bits.
- B) Different output channels have different magnitudes; a single per-tensor scale must stretch to cover the largest, starving the small-magnitude channels. Per-channel gives each its own scale.
- C) Per-channel is faster to compute at inference.
- D) Per-tensor is not supported on Orin.

---

**Q8.** When should you reach for **QAT** instead of PTQ?

- A) Always — QAT is strictly better.
- B) Only when PTQ drops below the accuracy floor *and* you genuinely need INT8 (FP16 won't clear the budget) — because QAT costs a training loop.
- C) Whenever you have a GPU.
- D) Never — QAT is obsolete.

---

**Q9.** Why does **unstructured** magnitude pruning rarely speed up inference on a GPU?

- A) It removes too few weights.
- B) The resulting zeros are scattered irregularly; GPUs run dense matrix multiplies, so a 70%-zero matrix still costs the full dense multiply. It shrinks the file, not the latency.
- C) It changes the model's output shape.
- D) GPUs don't support pruning.

---

**Q10.** What must be true for NVIDIA **2:4 structured sparsity** to actually accelerate a layer on Orin?

- A) Nothing — `--sparsity=enable` accelerates any dense model.
- B) The model must be trained/fine-tuned to the 2:4 pattern (2 of every 4 weights zero); enabling sparsity on a dense model does nothing useful, and the graph-level win is usually well under the per-layer 2x.
- C) The layer must be FP32.
- D) The GPU must have no tensor cores.

---

**Q11.** A teammate reports "INT8 made the detector 2x faster!" — 22 ms to 11 ms. What is the first thing you check before believing it?

- A) Whether they used the `--best` flag.
- B) Whether the 22 ms baseline was measured under the same pinned power mode and after warm-up — a throttled or cold baseline inflates the apparent win.
- C) The ONNX opset version.
- D) Whether they committed the engine file.

---

**Q12.** On Jetson, why is hand-rolling a `cudaMemcpy` of an image host→device every frame often wasteful?

- A) `cudaMemcpy` is deprecated.
- B) CPU and GPU share the same physical LPDDR5; with mapped/unified allocation the GPU can read the CPU buffer with zero copy — the explicit copy is copying memory to itself.
- C) It always crashes on Orin.
- D) It only works in FP32.

---

**Q13.** Two ROS2 nodes on the same machine pass a multi-megabyte pointcloud between them every frame, and it dominates the profile. What is the fix?

- A) Increase the QoS depth.
- B) Load both into one process as composable nodes so the message is passed by intra-process pointer instead of being serialized through DDS.
- C) Switch to a faster DDS vendor.
- D) Reduce the pointcloud's frame rate to hide the cost.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Orin shares 8 GB LPDDR5 between CPU and GPU; graphs are frequently bandwidth-bound, which is why eliminating copies often beats reducing FLOPs. (Lecture 1 §1.)
2. **B** — You budget against the tail because the robot misses deadlines at the tail; the mean hides stalls. (Lecture 1 §2.)
3. **B** — GPU idle + a fat memcpy = memory-bound. The lever is copy elimination (zero-copy / composable container), not a model trick. (Lecture 1 §4, Lecture 2 §7.)
4. **B** — FP16 runs natively on Orin tensor cores at ~2x and costs unmeasurable accuracy for detection/depth — the free lunch, taken first. (Lecture 2 §2.1.)
5. **B** — Calibration observes activation distributions on representative inputs to pick INT8 scales; it does not retrain. (Lecture 2 §3.1.)
6. **B** — Scales are tuned to whatever distribution you show; calibrate on representative frames or INT8 is accurate on the wrong images. (Lecture 2 §3.1.)
7. **B** — Per-channel gives each output channel its own scale, so high-magnitude channels don't starve the rest — the modern default. (Lecture 2 §3.3.)
8. **B** — QAT costs a training loop; reach for it only when PTQ breaks the floor and you still need INT8. (Lecture 2 §4.2.)
9. **B** — Scattered zeros don't help dense GPU matmul; unstructured pruning shrinks the file, not the latency. (Lecture 2 §5.1.)
10. **B** — The model must be trained to the 2:4 pattern; enabling it on a dense model does nothing, and graph-level wins are modest. (Lecture 2 §5.3.)
11. **B** — Re-baseline under the same pinned conditions; a throttled/cold baseline fakes the win. (Lecture 1 §5.)
12. **B** — Unified memory means the copy is memory-to-itself; allocate mapped/unified for zero-copy. (Lecture 2 §7.1.)
13. **B** — Composable nodes pass the message by intra-process pointer, eliminating the serialization that dominates. (Lecture 2 §7.2.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
