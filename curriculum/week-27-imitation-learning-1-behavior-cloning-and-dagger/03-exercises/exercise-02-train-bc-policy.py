#!/usr/bin/env python3
# Exercise 2 — Train a behavior-cloning policy (PyTorch), and watch where it breaks
#
# Goal: Implement a PyTorch MLP behavior-cloning policy with a CORRECT training
#       loop -- normalization fit on train only, train/val split, MSE loss, early
#       stopping -- then roll it out and see the covariate-shift drift the loss
#       curves cannot show you.
#
# Estimated time: 50 minutes. Runnable. CPU is fine.
#
# WHAT IT TRAINS ON
#
#   A synthetic 2D "reach" environment: a point agent must move to a block. The
#   scripted EXPERT moves straight toward the block. We collect expert demos from
#   VARIED starts, behavior-clone them, then roll the policy out from NOVEL starts
#   and watch it drift -- the covariate-shift signature, reproducible with no
#   robot, no Gz Sim, no GPU. Swap in your real reach task once this loop works.
#
# HOW TO USE THIS FILE
#
#       pip install torch numpy matplotlib
#       python3 exercise-02-train-bc-policy.py
#
# ACCEPTANCE CRITERIA
#
#   [ ] The training loop runs: train and val MSE both DECREASE and the val loss
#       early-stops (healthy supervised curves).
#   [ ] Despite healthy loss curves, the BC policy's success rate from NOVEL
#       starts is well below 100% -- it drifts. This is covariate shift, invisible
#       to the loss.
#   [ ] You can point at a failing rollout and see the track-then-drift signature.
#   [ ] loss_curve.png and a printed success rate are produced.
#
# Expected output is at the bottom of the file.

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Headless-safe plotting.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# The synthetic 2D reach environment + a scripted expert.
# Observation = [agent_x, agent_y, block_x, block_y]  (4-d)
# Action      = [dx, dy]  (a small step; the expert steps toward the block)  (2-d)
# ---------------------------------------------------------------------------
STEP = 0.05
SUCCESS_RADIUS = 0.08
MAX_STEPS = 60


class ReachEnv:
    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, seed=None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.agent = self.rng.uniform(-1.0, 1.0, size=2)
        self.block = self.rng.uniform(-1.0, 1.0, size=2)
        self.t = 0
        return self._obs()

    def _obs(self):
        return np.concatenate([self.agent, self.block]).astype(np.float32)

    def step(self, action):
        self.agent = self.agent + np.clip(action, -STEP, STEP)
        self.t += 1
        done = (np.linalg.norm(self.agent - self.block) < SUCCESS_RADIUS
                or self.t >= MAX_STEPS)
        return self._obs(), done

    def succeeded(self):
        return np.linalg.norm(self.agent - self.block) < SUCCESS_RADIUS


def expert_action(obs):
    """The expert moves a fixed step straight toward the block."""
    agent, block = obs[:2], obs[2:]
    d = block - agent
    n = np.linalg.norm(d) + 1e-9
    return (np.clip(d / n, -1, 1) * STEP).astype(np.float32)


def collect_expert_demos(n_demos=50, seed=0):
    """Roll out the expert from varied starts; return (obs, act) arrays."""
    env = ReachEnv(seed=seed)
    obs_list, act_list = [], []
    for i in range(n_demos):
        obs = env.reset(seed=seed + i)
        done = False
        while not done:
            a = expert_action(obs)
            obs_list.append(obs.copy())
            act_list.append(a.copy())
            obs, done = env.step(a)
    return np.array(obs_list), np.array(act_list)


# ---------------------------------------------------------------------------
# The BC policy, dataset, and training loop (Lecture 1 §3-4).
# ---------------------------------------------------------------------------
class BCPolicy(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, act_dim),
        )

    def forward(self, x):
        return self.net(x)


class DemoDataset(Dataset):
    def __init__(self, obs, act, stats=None):
        if stats is None:
            self.obs_mean, self.obs_std = obs.mean(0), obs.std(0) + 1e-6
            self.act_mean, self.act_std = act.mean(0), act.std(0) + 1e-6
        else:
            self.obs_mean, self.obs_std, self.act_mean, self.act_std = stats
        self.obs = (obs - self.obs_mean) / self.obs_std
        self.act = (act - self.act_mean) / self.act_std

    def stats(self):
        return (self.obs_mean, self.obs_std, self.act_mean, self.act_std)

    def __len__(self):
        return len(self.obs)

    def __getitem__(self, i):
        return (torch.tensor(self.obs[i], dtype=torch.float32),
                torch.tensor(self.act[i], dtype=torch.float32))


def train_bc(obs, act, epochs=300, batch=64, lr=1e-3, val_frac=0.2, seed=0):
    n = len(obs)
    idx = np.random.default_rng(seed).permutation(n)
    n_val = int(val_frac * n)
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    train_ds = DemoDataset(obs[train_idx], act[train_idx])         # fit norm on train
    stats = train_ds.stats()
    val_o = torch.tensor((obs[val_idx] - stats[0]) / stats[1], dtype=torch.float32)
    val_a = torch.tensor((act[val_idx] - stats[2]) / stats[3], dtype=torch.float32)

    loader = DataLoader(train_ds, batch_size=batch, shuffle=True)
    model = BCPolicy(obs.shape[1], act.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    crit = nn.MSELoss()

    best_val, best_state, patience, since = float("inf"), None, 30, 0
    history = []
    for _ in range(epochs):
        model.train()
        tl = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = crit(model(xb), yb)
            loss.backward()
            opt.step()
            tl += loss.item() * len(xb)
        tl /= len(train_ds)
        model.eval()
        with torch.no_grad():
            vl = crit(model(val_o), val_a).item()
        history.append((tl, vl))
        if vl < best_val:
            best_val, best_state, since = vl, model.state_dict(), 0
        else:
            since += 1
            if since >= patience:
                break
    model.load_state_dict(best_state)
    return model, train_ds, history


def deploy_step(model, train_ds, obs):
    s = train_ds.stats()
    obs_n = (obs - s[0]) / s[1]
    with torch.no_grad():
        act_n = model(torch.tensor(obs_n, dtype=torch.float32)).numpy()
    return (act_n * s[3] + s[2]).astype(np.float32)


def evaluate(model, train_ds, n_trials=20, seed=1000):
    """Fixed protocol: NOVEL start seeds (disjoint from training), crisp success."""
    succ, drift_fails = 0, 0
    for s in range(seed, seed + n_trials):
        env = ReachEnv()
        obs = env.reset(seed=s)
        start_dist = np.linalg.norm(obs[:2] - obs[2:])
        done = False
        while not done:
            obs, done = env.step(deploy_step(model, train_ds, obs))
        if env.succeeded():
            succ += 1
        else:
            # If it got CLOSER then stalled/drifted, it's the covariate-shift signature.
            end_dist = np.linalg.norm(obs[:2] - obs[2:])
            if end_dist < start_dist:
                drift_fails += 1
    return succ / n_trials, drift_fails


def main():
    obs, act = collect_expert_demos(n_demos=50, seed=0)
    print(f"collected {len(obs)} (obs, act) pairs from 50 expert demos")

    model, train_ds, history = train_bc(obs, act)
    tl, vl = history[-1]
    print(f"final train MSE={tl:.4f}  val MSE={vl:.4f}  (both low -> healthy curves)")

    rate, drift = evaluate(model, train_ds, n_trials=20)
    print(f"BC success from NOVEL starts: {rate*100:.0f}%  "
          f"({drift} failures were track-then-drift = covariate shift)")

    # Plot the (healthy) loss curves -- which CANNOT show the covariate shift.
    hist = np.array(history)
    plt.plot(hist[:, 0], label="train MSE")
    plt.plot(hist[:, 1], label="val MSE")
    plt.xlabel("epoch"); plt.ylabel("MSE"); plt.legend()
    plt.title("BC loss curves (healthy) -- yet the policy drifts (covariate shift)")
    plt.savefig("loss_curve.png")
    print("saved loss_curve.png")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (approximate; depends on seed)
# -----------------------------------------------------------------------------
#
# collected 1180 (obs, act) pairs from 50 expert demos
# final train MSE=0.012  val MSE=0.014  (both low -> healthy curves)
# BC success from NOVEL starts: 55%  (7 failures were track-then-drift = covariate shift)
# saved loss_curve.png
#
# THE LESSON: the loss curves are healthy (train and val MSE both low), yet the
# policy fails roughly half its NOVEL-start rollouts, and most failures are the
# track-then-drift signature. The loss is computed on the EXPERT's states; the
# policy is tested on its OWN states. That gap is covariate shift, and no amount
# of extra epochs on this data closes it -- you need DAgger (Exercise 3).
# -----------------------------------------------------------------------------
