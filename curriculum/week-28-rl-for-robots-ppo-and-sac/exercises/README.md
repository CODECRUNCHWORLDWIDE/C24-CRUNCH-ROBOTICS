# Week 28 — Exercises

Three drills that take the PPO and SAC machinery from the lectures and put it in your hands. Do them in order — Exercise 1 (the math) is what makes Exercises 2 and 3 (the code) legible instead of magical. Budget 45–90 minutes each.

## Index

1. **[Exercise 1 — The PPO/GAE math on paper](exercise-01-gae-and-ppo-math.md)** — derive the policy gradient, compute GAE-λ by hand through a mid-episode termination, predict the effect of a clip, and check one step against a tiny numpy snippet. (~60 min, paper + a few lines of numpy)
2. **[Exercise 2 — PPO solves CartPole](exercise-02-ppo-cartpole.py)** — a complete, runnable single-file PPO. Four marked `# TODO N:` blocks (the GAE recursion, the ratio, the clipped surrogate, the entropy term) are yours to fill. When they're right, CartPole is solved (reward 500) in well under a minute on a laptop CPU. (~60 min, runnable)
3. **[Exercise 3 — SAC solves Pendulum](exercise-03-sac-pendulum.py)** — a complete, runnable single-file SAC. The marked TODOs are the parts that trip everyone: the `tanh` log-prob correction, the clipped-double-Q target, and the automatic-temperature loss. When they're right, `Pendulum-v1` is solved (return > −200) in a few minutes. (~75 min, runnable)

## How to work the exercises

- **Do the math first.** Exercise 1 takes an hour and saves you three. When Exercise 2's clipped surrogate looks like line noise, it's because you skipped the derivation. Don't.
- **Read the whole file before you edit.** Both `.py` files are complete except for the marked TODOs; the scaffolding (env loop, logging, eval) is correct and worth reading as a reference implementation.
- **Each TODO is small and local.** None is more than a few lines. If you're writing twenty lines for one TODO, re-read the hint above it — you're overcomplicating.
- **Watch the diagnostics, not just the reward.** Both files print the Lecture 1 §8 traces (KL, clip fraction, entropy, explained variance, or their SAC analogues). Learn to read them now; the mini-project depends on it.
- Each runnable exercise ends with an **expected output** block. If your numbers don't land in that range, you're not done.

## Running the Python exercises

The two `.py` files are standalone — no ROS2, no Isaac Lab, just PyTorch and Gymnasium on a laptop:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "gymnasium[classic-control]" torch numpy
python3 exercise-02-ppo-cartpole.py
python3 exercise-03-sac-pendulum.py
```

Both run CPU-only in a few minutes; a GPU makes them faster but isn't required. They write TensorBoard logs to `runs/` if you have `tensorboard` installed (optional). The point of these two is to make PPO and SAC *concrete* — small enough to hold in your head — before you scale up to thousands of environments in the mini-project.

There are no solutions checked in. The course is open source — solutions live in forks. After you finish, search GitHub for `c24-week-28` to compare.
