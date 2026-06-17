# Week 37 — Exercises

Three drills that take you from "run a VLM by hand and watch it ground" to "a gated VLA loop that rejects a hallucination and falls back." Do them in order — exercise 3 reuses the grounding gate you build in exercise 2. The first is hands-on with a real VLM/VLA; the second and third are runnable Python written so they run **today, on a laptop, with no GPU and no weights** (they ship a deterministic stub VLA and stub detector), and convert to the real models by swapping two clearly-marked functions.

## Index

1. **[Exercise 1 — Prompt and ground](./exercise-01-prompt-and-ground.md)** — run a VLM (or your VLA) on real images + instructions, observe implicit grounding succeed and fail, and learn to read where it's confidently wrong. (~45 min, guided, needs a model)
2. **[Exercise 2 — Open-vocab grounding](./exercise-02-open-vocab-grounding.py)** — the explicit grounding the gate consumes: instruction → target phrase → detected box + confidence. Runs on a stub detector now; swap in OWL-ViT for the real thing. (~50 min, runnable)
3. **[Exercise 3 — The VLA policy loop](./exercise-03-vla-policy-loop.py)** — the full loop with a verification gate that accepts when grounding agrees, rejects when it disagrees, and falls back to the classical planner after 3 rejections. (~55 min, runnable)

## How to work the exercises

- Exercise 1 needs a model you can run a forward pass on — your week-31 OpenVLA, an open VLM, or even a hosted VLM API for the grounding-observation part. If you have no model access this week, read the exercise and do its *analysis* portion against the example outputs given.
- Exercises 2 and 3 are pure Python and **run as-is** with stubs, so you can build and test the *gate and fallback logic* without waiting on a GPU. The stubs are deterministic and the files end with an **expected output** block. The `# TODO` markers show exactly where to wire the real OWL-ViT and the real VLA — that's the homework/mini-project step.
- Keep the failure taxonomy (Lecture 2 §4) next to you. Every time the loop rejects, name *which* failure mode the rejection corresponds to.

## Running the Python exercises

```bash
python3 exercise-02-open-vocab-grounding.py
python3 exercise-03-vla-policy-loop.py
```

No GPU, no weights, no ROS2 required for the stub path. `numpy` is the only dependency. The real-model path needs `transformers` + a GPU and is gated behind the `# TODO` swaps.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-37` to compare.
