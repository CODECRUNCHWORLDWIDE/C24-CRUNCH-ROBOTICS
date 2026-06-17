# Week 29 — Exercises

Three drills that take DDPM, DDIM, and the full Diffusion Policy from the lectures into your hands. Do them in order — Exercise 1 (the math) makes Exercise 2 (a toy diffusion model) read like prose, and Exercise 2 makes Exercise 3 (an actual policy) tractable. Budget 45–90 minutes each.

## Index

1. **[Exercise 1 — DDPM/DDIM math on paper](./exercise-01-ddpm-ddim-math.md)** — derive the closed-form $q(x_t\mid x_0)$ from the per-step recursion, write the simplified ε-loss, derive the DDIM clean-sample estimate, and predict the effect of the denoising-step count. Paper + a few lines of numpy. (~60 min)
2. **[Exercise 2 — A toy 1D diffusion model](./exercise-02-toy-diffusion.py)** — a complete, runnable diffusion model that learns a **bimodal** 1D distribution. You fill the closed-form noising and the ε-prediction loss. When correct, sampling produces two clusters — the multimodality a Gaussian fit would miss. (~60 min, runnable)
3. **[Exercise 3 — A Diffusion Policy on a multimodal toy task](./exercise-03-diffusion-policy.py)** — a complete, runnable conditioned Diffusion Policy on a 2D task with action chunking and receding-horizon execution. You fill the observation-conditioned ε-loss and the DDIM action sampler. When correct, the policy reaches the goal *and* its action distribution at the junction is bimodal. (~75 min, runnable)

## How to work the exercises

- **Do the math first.** Exercise 1 is where $\bar\alpha_t$ comes from. Skip it and the code's `torch.sqrt(ab)` lines are incantations; do it and they're obvious.
- **Read the whole file before editing.** Both `.py` files are complete except for the marked `# TODO N:` blocks; the scaffolding (schedule, sampling loop, plotting) is correct and worth reading as a reference.
- **Look at the plots, not just the loss.** Both files render the learned distribution. A falling loss with a *unimodal* sample plot means your conditioning leaked or your data is unimodal — the plot is the ground truth, not the loss number.
- Each runnable exercise ends with an **expected output** block describing the plots and numbers. If yours don't match, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no ROS2, no Isaac Lab, just PyTorch, numpy, and matplotlib on a laptop:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch numpy matplotlib
python3 exercise-02-toy-diffusion.py        # writes toy_diffusion.png
python3 exercise-03-diffusion-policy.py     # writes diffusion_policy_dist.png
```

Both run CPU-only in a couple of minutes. The point of these two is to make diffusion *concrete and small* — a 1D bimodal distribution and a 2D toy task you can see — before you scale to images and real demos in the mini-project.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-29` to compare.
