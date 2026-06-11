#!/usr/bin/env python3
# Exercise 3 — A Diffusion Policy on a 2D multimodal toy task
#
# Goal: Fill the marked TODOs to turn this scaffold into a working Diffusion Policy
#       with observation conditioning, ACTION CHUNKING, and DDIM sampling. The toy
#       task is multimodal on purpose: from the start, the demonstrations go AROUND a
#       central obstacle either LEFT or RIGHT to reach the goal. A BC policy averages
#       the two and drives INTO the obstacle. The Diffusion Policy keeps both modes.
#       The output plot shows the predicted first-action distribution at the junction:
#       TWO clusters (left/right), not one blob in the middle.
#
# Estimated time: 75 minutes. Runnable.
#
# THE TODOs (search for "# TODO"):
#   TODO 1 — the observation-conditioned epsilon-prediction loss (Lecture 2 §4)
#   TODO 2 — the DDIM clean-sample estimate inside the action sampler (Lecture 1 §4.2)
#
# HOW TO RUN
#   pip install torch numpy matplotlib
#   python3 exercise-03-diffusion-policy.py     # writes diffusion_policy_dist.png
#
# ACCEPTANCE CRITERIA
#   [ ] Both TODOs filled; the file runs and writes diffusion_policy_dist.png.
#   [ ] Training loss falls steadily.
#   [ ] The action-distribution scatter at the junction state shows TWO clusters
#       (one steering left, one steering right). A single central blob means the
#       conditioning leaked or TODO 1/2 is wrong.
#   [ ] A receding-horizon rollout reaches the goal region without driving through
#       the obstacle on most seeds.
#
# Expected output is at the bottom of the file.

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.manual_seed(0)
np.random.seed(0)

T_DIFF = 100                  # diffusion steps (training); DDIM sub-samples at inference
T_P = 8                       # prediction horizon (chunk length)
ACT_DIM = 2                   # 2D velocity command
OBS_DIM = 2                   # 2D position
N_DEMOS = 4000
EPOCHS = 3000
BATCH = 256
LR = 1e-3

betas = torch.linspace(1e-4, 0.02, T_DIFF)
alphas = 1.0 - betas
alpha_bar = torch.cumprod(alphas, dim=0)

OBSTACLE = torch.tensor([0.0, 0.5])           # a blob in the middle of the path
GOAL = torch.tensor([0.0, 1.0])


def make_demo():
    """One demonstration: from the start near (0, 0), go LEFT or RIGHT around the
    obstacle to the goal at (0, 1). Returns (obs_chunk_start, action_chunk).
    The multimodality is the random left/right choice."""
    side = -1.0 if np.random.rand() < 0.5 else 1.0          # the modal choice
    pos = torch.tensor([0.0, 0.0]) + 0.05 * torch.randn(2)
    obs0 = pos.clone()
    actions = []
    waypoints = [torch.tensor([side * 0.5, 0.5]), GOAL]      # detour, then goal
    wp_idx = 0
    for _ in range(T_P):
        target = waypoints[min(wp_idx, len(waypoints) - 1)]
        vel = (target - pos)
        vel = vel / (vel.norm() + 1e-6) * 0.2
        pos = pos + vel
        actions.append(vel)
        if (pos - waypoints[wp_idx]).norm() < 0.15 and wp_idx < len(waypoints) - 1:
            wp_idx += 1
    return obs0, torch.stack(actions)                        # obs (2,), actions (T_P, 2)


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t):
        half = self.dim // 2
        freqs = torch.exp(-math.log(10000) * torch.arange(half) / (half - 1))
        args = t[:, None].float() * freqs[None]
        return torch.cat([torch.sin(args), torch.cos(args)], dim=-1)


class CondEpsNet(nn.Module):
    """Predicts the noise on a flattened action chunk, conditioned on the observation
    embedding and the diffusion timestep. (A small MLP stands in for the 1D U-Net;
    the conditioning principle from Lecture 2 §1 and §4 is identical.)"""

    def __init__(self, hidden=256, time_dim=64, obs_embed=64):
        super().__init__()
        self.time_embed = SinusoidalTimeEmbedding(time_dim)
        self.obs_encoder = nn.Sequential(nn.Linear(OBS_DIM, obs_embed), nn.SiLU())
        chunk = T_P * ACT_DIM
        self.net = nn.Sequential(
            nn.Linear(chunk + time_dim + obs_embed, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, chunk),
        )

    def forward(self, noised_chunk, t, obs):
        # noised_chunk: (B, T_P, ACT_DIM); obs: (B, OBS_DIM)
        B = noised_chunk.shape[0]
        flat = noised_chunk.reshape(B, -1)
        cond = torch.cat([self.obs_encoder(obs), self.time_embed(t)], dim=-1)
        out = self.net(torch.cat([flat, cond], dim=-1))
        return out.reshape(B, T_P, ACT_DIM)


def train():
    demos = [make_demo() for _ in range(N_DEMOS)]
    obs = torch.stack([d[0] for d in demos])
    acts = torch.stack([d[1] for d in demos])
    model = CondEpsNet()
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    for epoch in range(EPOCHS):
        idx = torch.randint(0, N_DEMOS, (BATCH,))
        o, a0 = obs[idx], acts[idx]
        t = torch.randint(0, T_DIFF, (BATCH,))
        eps = torch.randn_like(a0)
        ab = alpha_bar[t].view(BATCH, 1, 1)
        noised = torch.sqrt(ab) * a0 + torch.sqrt(1 - ab) * eps

        eps_pred = model(noised, t, o)

        # TODO 1: the observation-conditioned epsilon-prediction loss. It is the same
        #   simplified DDPM MSE as Exercise 2, but the network is conditioned on `o`.
        #   loss = mean((eps_pred - eps)^2)   (Lecture 2 §4; Lecture 1 §3).
        loss = ...

        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % 300 == 0:
            print(f"epoch {epoch:>4}  loss {loss.item():.4f}")
    return model


@torch.no_grad()
def ddim_action_chunk(model, obs, n_steps=16):
    """DDIM-denoise an action chunk conditioned on obs. obs: (B, OBS_DIM)."""
    B = obs.shape[0]
    step_seq = torch.linspace(T_DIFF - 1, 0, n_steps).long()
    x = torch.randn(B, T_P, ACT_DIM)
    for i in range(n_steps):
        t = step_seq[i]
        t_next = step_seq[i + 1] if i + 1 < n_steps else torch.tensor(0)
        ab_t = alpha_bar[t]
        ab_next = alpha_bar[t_next] if t_next > 0 else torch.tensor(1.0)
        eps = model(x, torch.full((B,), int(t)), obs)

        # TODO 2: the DDIM clean-sample estimate, then the jump to t_next.
        #   x0_pred = (x - sqrt(1 - ab_t) * eps) / sqrt(ab_t)     (Lecture 1 §4.2)
        #   x = sqrt(ab_next) * x0_pred + sqrt(1 - ab_next) * eps
        x0_pred = ...
        x = torch.sqrt(ab_next) * x0_pred + torch.sqrt(1 - ab_next) * eps
    return x


def main():
    print("training a Diffusion Policy on a multimodal (go-around-left-or-right) task...")
    model = train()

    # --- the multimodality scatter at the junction (the start) state ---
    junction = torch.zeros(512, OBS_DIM)                    # 512 copies of the start state
    chunks = ddim_action_chunk(model, junction, n_steps=16)
    first_act = chunks[:, 0, :].numpy()                     # the FIRST action of each chunk

    left = float((first_act[:, 0] < -0.02).mean())
    right = float((first_act[:, 0] > 0.02).mean())
    print(f"first-action mass:  steer-left={left:.2f}  steer-right={right:.2f}")

    plt.figure(figsize=(6, 6))
    plt.scatter(first_act[:, 0], first_act[:, 1], s=6, alpha=0.3, label="diffusion samples")
    plt.scatter([0.0], [first_act[:, 1].mean()], c="r", s=120, marker="x",
                label="BC mean prediction (drives into obstacle)")
    plt.title("Predicted first action at the junction: TWO modes (left/right)")
    plt.xlabel("action x (steer)"); plt.ylabel("action y (forward)")
    plt.legend(); plt.tight_layout(); plt.savefig("diffusion_policy_dist.png", dpi=110)
    print("wrote diffusion_policy_dist.png")

    # --- a receding-horizon rollout (execute first T_a, re-plan) ---
    T_a = 4
    pos = torch.zeros(1, OBS_DIM)
    reached, hit_obstacle = False, False
    for _ in range(20):
        chunk = ddim_action_chunk(pos, n_steps=16) if False else ddim_action_chunk(model, pos, 16)
        for k in range(T_a):
            pos = pos + chunk[:, k, :]
            if (pos[0] - OBSTACLE).norm() < 0.12:
                hit_obstacle = True
            if (pos[0] - GOAL).norm() < 0.2:
                reached = True
                break
        if reached:
            break
    print(f"rollout: reached_goal={reached}  hit_obstacle={hit_obstacle}  final_pos={pos[0].tolist()}")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed
# -----------------------------------------------------------------------------
#
# training a Diffusion Policy on a multimodal (go-around-left-or-right) task...
# epoch    0  loss 1.0331
# epoch  300  loss 0.2890
# ...
# epoch 2700  loss 0.1604
# first-action mass:  steer-left=0.49  steer-right=0.50
# wrote diffusion_policy_dist.png
# rollout: reached_goal=True  hit_obstacle=False  final_pos=[~0.0, ~1.0]
#
# THE LESSON: at the junction, the predicted first action splits into TWO clusters —
# about half steer LEFT, half steer RIGHT. That is the multimodality the demonstrations
# contain, faithfully reproduced. The red X marks where a BC policy's deterministic mean
# prediction lands: steering ~0 (straight ahead) — INTO the obstacle. That is the
# multimodal-action problem (Lecture 1 §1), and the scatter is the "the distribution had
# two modes" promise from the week README, made literal.
#
# If your scatter is a SINGLE central blob: the model collapsed to the mean — check
# TODO 1 (conditioned loss) and TODO 2 (DDIM estimate), and confirm your demos actually
# contain both modes (the make_demo() left/right coin flip).
# -----------------------------------------------------------------------------
