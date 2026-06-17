# Week 27 — Exercises

Three drills that take you from raw demonstrations to a BC policy that drifts to a DAgger policy that doesn't. Do them in order — exercise 3 needs the policy and the dataset from exercise 2, which needs the demos (or the synthetic stand-in) from exercise 1.

## Index

1. **[Exercise 1 — Collect and inspect demos](./exercise-01-collect-and-inspect-demos.md)** — collect (or generate) teleop demonstrations of the reach task, and *inspect* the (observation, action) dataset for the problems that quietly break BC: misaligned pairs, narrow start-state coverage, unnormalized scales. (~45 min, guided)
2. **[Exercise 2 — Train a BC policy](./exercise-02-train-bc-policy.py)** — a PyTorch MLP behavior-cloning policy with a correct training loop: normalization fit on train only, train/val split, MSE loss, early stopping, and loss curves you can read. (~50 min, runnable)
3. **[Exercise 3 — One DAgger round](./exercise-03-dagger-round.py)** — roll out the BC policy, watch it drift, collect the states it visits, relabel them with the expert, aggregate, retrain, and measure the success-rate jump. (~45 min, runnable)

## How to work the exercises

- Have **PyTorch** and **NumPy** installed: `pip install torch numpy matplotlib`. A CPU is fine — this week's MLP trains in minutes.
- Exercises 2 and 3 ship a **synthetic 2D reach environment** (a point "arm" reaching a "block") with a scripted expert, so you can run the *full BC → drift → DAgger loop* with no Gz Sim and no real arm. The lessons (covariate shift, the DAgger fix) are identical; the synthetic env just makes them fast and reproducible. Swap in your Gz Sim reach task once the loop works.
- **Watch the rollout, not just the loss.** The covariate-shift signature (track-then-drift) is visible in a rollout and invisible in the loss curves. Exercise 2 plots both; learn to read the rollout.
- Each runnable exercise (`.py`) ends with an **expected output** block. The exact numbers depend on your seed; the *shape* — BC drifts, DAgger recovers — is invariant.

## Running the Python exercises

The two `.py` files are standalone — no `colcon` package, no robot required. Run them directly:

```bash
pip install torch numpy matplotlib
python3 exercise-02-train-bc-policy.py            # trains BC on the synthetic env
python3 exercise-03-dagger-round.py               # BC -> drift -> DAgger -> recover
```

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-27` to compare.
