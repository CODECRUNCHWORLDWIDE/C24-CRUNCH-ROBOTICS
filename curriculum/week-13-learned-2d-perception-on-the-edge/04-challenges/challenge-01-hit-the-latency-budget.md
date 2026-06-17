# Challenge 1 — Hit the Latency Budget

**Time estimate:** ~90 minutes.

## Problem statement

You inherited a detection pipeline. It works — it finds objects correctly — but it runs at **3 frames per second**, and the controller needs detections inside a **30 ms** budget (33 FPS). A teammate's instinct is "the model is too big, swap in a smaller one." You are the edge engineer, and you know better than to optimize before profiling. Your job: **profile the pipeline per-stage, find where the milliseconds actually go, fix the right stage, and prove with a latency block diagram that you cleared the 30 ms budget.**

The lesson is the whole point of Lecture 2 §6: **the model's inference time is frequently not the bottleneck**, and an engineer who reaches for a smaller model before profiling is optimizing blind.

## The harness

Save this as `slow_pipeline.py`. It's a detection pipeline with the inference *stubbed* to a realistic fixed latency (so the challenge is hardware-independent) and a **deliberately slow preprocessing stage** — the kind of naive implementation that's depressingly common. **Do not read which stage is slow before profiling it** — find it the right way.

```python
#!/usr/bin/env python3
"""A detection pipeline that misses a 30 ms budget. Profile it, find the
bottleneck, fix it. The inference is stubbed to a fixed latency so the challenge
is hardware-independent; the preprocessing is real (and a problem)."""
import time
import numpy as np
import cv2

INPUT_SIZE = 320
INFER_MS = 11.0          # stubbed inference latency (a realistic FP16 YOLOv8n)


def slow_preprocess(img, size=INPUT_SIZE):
    """Resize, BGR->RGB, HWC->CHW, normalize — implemented the NAIVE way."""
    resized = cv2.resize(img, (size, size))
    out = np.empty((3, size, size), np.float32)
    # The anti-pattern: a per-pixel Python loop. Correct, but catastrophically slow.
    for c in range(3):
        for i in range(size):
            for j in range(size):
                out[c, i, j] = resized[i, j, 2 - c] / 255.0   # BGR->RGB + normalize
    return out[None]


def stub_infer(blob):
    """Stand-in for the real engine: a fixed, realistic inference latency."""
    time.sleep(INFER_MS / 1000.0)
    return None


def postprocess(_raw):
    """Trivial postprocess for this harness."""
    return []


def run_cycle(img, preprocess_fn):
    t0 = time.perf_counter()
    blob = preprocess_fn(img)
    t1 = time.perf_counter()
    raw = stub_infer(blob)
    t2 = time.perf_counter()
    postprocess(raw)
    t3 = time.perf_counter()
    return {
        "preprocess_ms": 1e3 * (t1 - t0),
        "inference_ms": 1e3 * (t2 - t1),
        "postprocess_ms": 1e3 * (t3 - t2),
        "total_ms": 1e3 * (t3 - t0),
    }


if __name__ == "__main__":
    img = np.random.randint(0, 255, (720, 1280, 3), np.uint8)
    # Profile the slow pipeline.
    runs = [run_cycle(img, slow_preprocess) for _ in range(5)]
    avg = {k: np.mean([r[k] for r in runs]) for k in runs[0]}
    print("SLOW pipeline (avg over 5):")
    for k, v in avg.items():
        print(f"  {k:14s}: {v:7.1f} ms")
    print(f"  -> {1000.0/avg['total_ms']:.1f} FPS  "
          f"({'MISSES' if avg['total_ms'] > 30 else 'within'} the 30 ms budget)")
```

```bash
pip install opencv-python numpy
python3 slow_pipeline.py
```

You'll see the pipeline miss the budget badly. Now find out *why*.

## Your task

1. **Profile per-stage.** Run the harness and read the per-stage breakdown. Identify the bottleneck stage — do *not* assume it's inference. (It isn't.)
2. **Diagnose the root cause.** Look at the bottleneck stage's code. Why is it slow? (The preprocessing does a per-pixel Python loop — `O(size²·3)` Python-level operations, which is catastrophic compared to vectorized NumPy.)
3. **Fix the right stage.** Write a `fast_preprocess` that does the same thing with vectorized NumPy/OpenCV (resize, slice-reverse for BGR→RGB, `transpose`, divide). The output must be *numerically identical* to the slow version — verify that.
4. **Re-profile and prove it.** Run the fixed pipeline, confirm it clears the 30 ms budget, and produce a **latency block diagram** (the Lecture 2 §6.1 format) for both the before and after.

## Acceptance criteria

- [ ] A `fast_pipeline.py` with a vectorized `fast_preprocess` whose output is `np.allclose` to `slow_preprocess`'s (same result, faster).
- [ ] A profile showing the SLOW pipeline misses the budget with preprocessing as the dominant stage (hundreds of ms), and the FAST pipeline clears it (preprocessing well under 1 ms, total ≈ inference + small overhead).
- [ ] The speedup is dramatic (on a typical machine, ~25–30× on the total cycle, since preprocessing went from ~350 ms to <1 ms).
- [ ] A `challenge-01-writeup.md` with: the before/after per-stage numbers, a latency block diagram for each, and a paragraph on *why profiling-before-optimizing matters* — specifically, why "swap in a smaller model" (the teammate's instinct) would NOT have fixed this, since inference was never the bottleneck.
- [ ] Committed to your Week 13 repo under `challenges/challenge-01/`.

## The trap (read after a first attempt)

The teammate's instinct — "the model is too big, use a smaller one" — is the trap, and it's worth dwelling on because it's the most common real-world mistake. Swapping YOLOv8s for YOLOv8n might save a few ms of *inference*, but inference was 11 ms of a 360 ms cycle. The 349 ms in preprocessing would still be there, and the pipeline would still run at ~3 FPS. **You cannot optimize what you haven't measured, and the measurement pointed at a stage nobody suspected.** This is why Lecture 2 §6.2 lists the optimization order with "profile first" implicit in every step: the right fix is determined by the profile, not by intuition about which component "feels heavy." A smaller model is item 3 on the list; vectorizing preprocessing is item 2, and here it's the *only* thing that matters.

## Stretch

- **Add a real model.** Replace `stub_infer` with a real `yolov8n.onnx` under ONNX Runtime (from Exercise 1). Now your inference number is real, and you can see how the preprocessing fix interacts with actual inference time on *your* hardware.
- **GPU preprocessing.** If you have a GPU, move the resize/normalize onto it (CUDA or a fused operation) and measure the further win — the §6.2 item-2 fix taken to its conclusion. On a Jetson this is often what makes a 35 ms pipeline a 22 ms one.
- **The async version.** Make the pipeline pipeline: preprocess frame N+1 while inferring on frame N, overlapping the stages. Measure the throughput gain (latency per frame stays, but FPS rises because stages overlap). This is the production trick for squeezing more frames through a fixed-latency engine.
- **Postprocess stress.** Crank the number of candidate boxes so NMS becomes the bottleneck, then show that an NMS-free detector (RT-DETR/YOLOv10, Lecture 1 §2) is the *structural* fix — you can't vectorize your way out of NMS the way you can out of preprocessing.

## Why this matters

In Week 16 the "30 ms perception cycle on an Orin Nano" is a *hard gate* — fail it and you go back. In Week 39 the entire week is edge-ML optimization. The reviewer at both will point at your pipeline and ask "where do your milliseconds go, and what's your next optimization?" The latency block diagram with the bottleneck circled is the answer that proves you understand your own system. And in every edge-robotics job, the difference between a robot that perceives at 30 FPS and one that perceives at 3 FPS is exactly this skill: profile, find the real bottleneck, fix the right thing. The engineer who guesses optimizes the 11 ms and ships a 3 FPS robot; the engineer who profiles fixes the 350 ms and ships a 30 FPS one.
