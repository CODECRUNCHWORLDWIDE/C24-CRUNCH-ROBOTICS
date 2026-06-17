# Week 30 — Exercises

Three drills that take ACT's CVAE and temporal ensembling from the lectures into your hands. Do them in order — Exercise 1 (the math) makes the CVAE loss in Exercise 2 obvious, and Exercise 3's ensembling builds on the chunks Exercise 2 produces. Budget 45–90 minutes each.

## Index

1. **[Exercise 1 — The CVAE and ensembling math on paper](./exercise-01-cvae-and-ensembling-math.md)** — derive the CVAE objective and the closed-form KL term, compute the KL for a few latents (watch the posterior-collapse boundary), and compute the temporal-ensembling weights by hand. Paper + a few lines of numpy. (~60 min)
2. **[Exercise 2 — A miniature ACT (CVAE + chunk decoder)](./exercise-02-act-cvae.py)** — a complete, runnable miniature ACT on a multimodal toy: a CVAE-trained transformer that predicts an action chunk in one pass. You fill the KL term, the reparameterization, and the inference latent ($z=0$). When correct, the chunk is coherent and the $z=0$ inference is single-pass. (~75 min, runnable)
3. **[Exercise 3 — Temporal ensembling](./exercise-03-temporal-ensembling.py)** — a complete, runnable temporal-ensembling controller. You fill the exponential weighting and the per-timestep weighted average. When correct, you measure a multiple-x jerk reduction vs raw chunk-switching. (~60 min, runnable)

## How to work the exercises

- **Do the math first.** Exercise 1 is where the KL term and the ensembling weights come from. Skip it and the code's `kl_divergence` and `exp(-m*i)` lines are incantations; do it and they're obvious.
- **Read the whole file before editing.** Both `.py` files are complete except for the marked `# TODO N:` blocks; the scaffolding (transformer, training loop, jerk measurement) is correct and worth reading as a reference.
- **Watch the right signal.** Exercise 2's lesson is in the *single-pass* inference and the coherent chunk, not just the loss. Exercise 3's lesson is the *jerk number* dropping — print it and compare.
- Each runnable exercise ends with an **expected output** block. If yours doesn't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no ROS2, no LeRobot, just PyTorch, numpy, and matplotlib on a laptop:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch numpy matplotlib
python3 exercise-02-act-cvae.py
python3 exercise-03-temporal-ensembling.py     # writes ensembling.png
```

Both run CPU-only in a couple of minutes. The point of these two is to make ACT *concrete and small* — a miniature CVAE chunk predictor and a standalone ensembler — before you train the real thing with LeRobot and benchmark it against Diffusion Policy in the mini-project.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-30` to compare.
