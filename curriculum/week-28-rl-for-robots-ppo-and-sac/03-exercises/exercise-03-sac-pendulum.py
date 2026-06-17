#!/usr/bin/env python3
# Exercise 3 — SAC solves Pendulum (a complete single-file SAC with the tricky TODOs)
#
# Goal: Fill the marked TODOs — the parts of SAC that trip EVERYONE the first time —
#       to turn this scaffold into a working Soft Actor-Critic. When correct,
#       Pendulum-v1 is SOLVED (episodic return rises from ~ -1200 toward > -200) in
#       a few minutes on a laptop CPU.
#
# Estimated time: 75 minutes. Runnable.
#
# THE TODOs (all in this file, search for "# TODO"):
#   TODO 1 — the tanh log-prob correction in the squashed-Gaussian actor (Lecture 2 §1.3)
#   TODO 2 — the clipped-double-Q soft target (Lecture 2 §1.2)
#   TODO 3 — the actor loss (entropy-regularized; Lecture 2 §1.3)
#   TODO 4 — the automatic-temperature (alpha) loss (Lecture 2 §1.4)
#
# HOW TO RUN
#   pip install "gymnasium[classic-control]" torch numpy
#   python3 exercise-03-sac-pendulum.py
#
# ACCEPTANCE CRITERIA
#   [ ] All TODOs filled; the file runs without shape errors.
#   [ ] Mean episodic return rises from ~ -1200 (random) past -200 within ~15k steps.
#   [ ] alpha (temperature) starts ~0.2 and ADAPTS (does not stay pinned) — if it
#       runs away to a huge value or collapses to ~0, TODO 1 or TODO 4 is wrong.
#   [ ] You can state why rsample() (not sample()) is used in the actor.
#
# Expected output is at the bottom of the file.

import math
import time
from collections import deque
import random

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import gymnasium as gym

# ----------------------------- hyperparameters -------------------------------
ENV_ID = "Pendulum-v1"
TOTAL_STEPS = 20000
START_STEPS = 1000           # pure random actions to seed the replay buffer
BATCH_SIZE = 256
BUFFER_SIZE = 100_000
GAMMA = 0.99
TAU = 0.005                  # Polyak averaging coefficient for target nets
LR = 3e-4
HIDDEN = 256
LOG_STD_MIN, LOG_STD_MAX = -20, 2
SEED = 1

torch.manual_seed(SEED)
np.random.seed(SEED)
random.seed(SEED)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ----------------------------- replay buffer ---------------------------------
class ReplayBuffer:
    def __init__(self, capacity: int):
        self.buf = deque(maxlen=capacity)

    def add(self, s, a, r, s2, done):
        self.buf.append((s, a, r, s2, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buf, batch_size)
        s, a, r, s2, d = zip(*batch)
        to = lambda x: torch.as_tensor(np.array(x), dtype=torch.float32, device=device)
        return (to(s), to(a), to(r).unsqueeze(-1), to(s2), to(d).unsqueeze(-1))

    def __len__(self):
        return len(self.buf)


# ----------------------------- networks --------------------------------------
class SquashedGaussianActor(nn.Module):
    """Outputs a Gaussian, reparameterized-sampled, squashed through tanh to the
    action bounds. The tanh changes the density — hence the log-prob correction."""

    def __init__(self, obs_dim, act_dim, act_limit):
        super().__init__()
        self.act_limit = act_limit
        self.net = nn.Sequential(
            nn.Linear(obs_dim, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
        )
        self.mu_head = nn.Linear(HIDDEN, act_dim)
        self.log_std_head = nn.Linear(HIDDEN, act_dim)

    def sample(self, obs):
        h = self.net(obs)
        mu = self.mu_head(h)
        log_std = torch.clamp(self.log_std_head(h), LOG_STD_MIN, LOG_STD_MAX)
        std = log_std.exp()
        normal = torch.distributions.Normal(mu, std)
        # rsample(): the REPARAMETERIZATION trick. u = mu + std * eps, so gradients
        # flow through the sampled action — the actor loss needs this. sample() would
        # detach and the actor would never learn.
        u = normal.rsample()
        a = torch.tanh(u)

        logp_u = normal.log_prob(u).sum(-1, keepdim=True)
        # TODO 1: the tanh log-prob correction. Squashing a = tanh(u) changes the
        #   density, so subtract sum_i log(1 - tanh(u_i)^2) from logp_u. Use the
        #   numerically stable identity (avoids log(0) when tanh saturates):
        #       correction = (2*(log(2) - u - softplus(-2*u))).sum(-1, keepdim=True)
        #   then  logp = logp_u - correction.  (Lecture 2 §1.3.)
        correction = ...
        logp = logp_u - correction

        return a * self.act_limit, logp


class QNet(nn.Module):
    """Q(s, a): concatenates state and action, outputs a scalar value."""

    def __init__(self, obs_dim, act_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim + act_dim, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, 1),
        )

    def forward(self, s, a):
        return self.net(torch.cat([s, a], dim=-1))


# ----------------------------- SAC core --------------------------------------
def main() -> None:
    env = gym.make(ENV_ID)
    obs_dim = env.observation_space.shape[0]
    act_dim = env.action_space.shape[0]
    act_limit = float(env.action_space.high[0])

    actor = SquashedGaussianActor(obs_dim, act_dim, act_limit).to(device)
    q1 = QNet(obs_dim, act_dim).to(device)
    q2 = QNet(obs_dim, act_dim).to(device)
    q1_targ = QNet(obs_dim, act_dim).to(device)
    q2_targ = QNet(obs_dim, act_dim).to(device)
    q1_targ.load_state_dict(q1.state_dict())
    q2_targ.load_state_dict(q2.state_dict())

    actor_opt = torch.optim.Adam(actor.parameters(), lr=LR)
    q_opt = torch.optim.Adam(list(q1.parameters()) + list(q2.parameters()), lr=LR)

    # Automatic temperature: optimize log_alpha toward a target entropy.
    target_entropy = -float(act_dim)            # the standard -dim(A) heuristic
    log_alpha = torch.zeros(1, requires_grad=True, device=device)
    alpha_opt = torch.optim.Adam([log_alpha], lr=LR)

    buffer = ReplayBuffer(BUFFER_SIZE)
    obs, _ = env.reset(seed=SEED)
    ep_ret, ep_rets = 0.0, deque(maxlen=10)
    start = time.time()
    print(f"SAC on {ENV_ID} | device={device}")
    print(f"{'step':>6} {'ret':>9} {'alpha':>7} {'q1loss':>8} {'aloss':>8}")

    last_diag = {}
    for step in range(1, TOTAL_STEPS + 1):
        if step < START_STEPS:
            a = env.action_space.sample()
        else:
            with torch.no_grad():
                a_t, _ = actor.sample(
                    torch.as_tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)
                )
            a = a_t.squeeze(0).cpu().numpy()

        next_obs, reward, terminated, truncated, _ = env.step(a)
        # Pendulum has no terminal state; only truncation (time limit). So `done`
        # for bootstrapping is `terminated` (always False here) — never truncated.
        buffer.add(obs, a, reward, next_obs, float(terminated))
        ep_ret += reward
        obs = next_obs
        if terminated or truncated:
            ep_rets.append(ep_ret)
            ep_ret = 0.0
            obs, _ = env.reset()

        if len(buffer) >= BATCH_SIZE and step >= START_STEPS:
            s, act, r, s2, d = buffer.sample(BATCH_SIZE)
            alpha = log_alpha.exp()

            # --- critic update ---
            with torch.no_grad():
                a2, logp_a2 = actor.sample(s2)
                q1_t = q1_targ(s2, a2)
                q2_t = q2_targ(s2, a2)
                # TODO 2: the soft target. Take the MIN of the twin target critics
                #   (clipped double-Q), subtract the entropy term alpha*logp_a2, then
                #   form the Bellman target with the (1 - d) bootstrap mask:
                #       min_q = torch.min(q1_t, q2_t)
                #       target = r + GAMMA * (1 - d) * (min_q - alpha * logp_a2)
                #   (Lecture 2 §1.2.)
                target = ...
            q1_loss = ((q1(s, act) - target) ** 2).mean()
            q2_loss = ((q2(s, act) - target) ** 2).mean()
            q_loss = q1_loss + q2_loss
            q_opt.zero_grad()
            q_loss.backward()
            q_opt.step()

            # --- actor update ---
            a_pi, logp_pi = actor.sample(s)
            min_q_pi = torch.min(q1(s, a_pi), q2(s, a_pi))
            # TODO 3: the actor loss. The actor MAXIMIZES (min_q - alpha*logp), so the
            #   loss is the mean of (alpha.detach() * logp_pi - min_q_pi). Detach alpha
            #   here — the temperature is trained by its own loss (TODO 4), not this one.
            actor_loss = ...
            actor_opt.zero_grad()
            actor_loss.backward()
            actor_opt.step()

            # --- temperature update ---
            # TODO 4: the alpha loss. Drive entropy toward target_entropy:
            #       alpha_loss = -(log_alpha * (logp_pi + target_entropy).detach()).mean()
            #   (Lecture 2 §1.4.) Note logp_pi is detached inside the parentheses.
            alpha_loss = ...
            alpha_opt.zero_grad()
            alpha_loss.backward()
            alpha_opt.step()

            # --- Polyak target updates ---
            with torch.no_grad():
                for net, targ in ((q1, q1_targ), (q2, q2_targ)):
                    for p, p_t in zip(net.parameters(), targ.parameters()):
                        p_t.mul_(1 - TAU).add_(TAU * p)

            last_diag = {
                "alpha": float(alpha.item()),
                "q1loss": float(q1_loss.item()),
                "aloss": float(actor_loss.item()),
            }

        if step % 2000 == 0 and last_diag:
            mean_ret = float(np.mean(ep_rets)) if ep_rets else float("nan")
            print(f"{step:>6} {mean_ret:>9.1f} {last_diag['alpha']:>7.3f} "
                  f"{last_diag['q1loss']:>8.2f} {last_diag['aloss']:>8.2f}")

    mean_ret = float(np.mean(ep_rets)) if ep_rets else float("nan")
    solved = "SOLVED" if mean_ret > -200 else "not solved (try more steps)"
    print(f"\n{solved}: final mean return {mean_ret:.1f} in {time.time() - start:.1f}s")
    env.close()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed/CPU, SHAPE is stable
# -----------------------------------------------------------------------------
#
# SAC on Pendulum-v1 | device=cpu
#   step       ret   alpha   q1loss    aloss
#   2000   -1187.4   0.241    18.33    24.10
#   4000    -902.1   0.198     9.71    11.42
#   6000    -512.8   0.171     4.05     3.88
#  10000    -243.6   0.142     1.92    -1.30
#  14000    -176.2   0.121     1.10    -6.55
#  20000    -148.9   0.108     0.84    -9.21
#
# SOLVED: final mean return -148.9 in 71.2s
#
# What "healthy" looks like:
#   ret    : rises from ~ -1200 (random) toward > -200. Pendulum's best is ~ -130.
#   alpha  : starts ~0.2-0.25 and DRIFTS DOWN smoothly as the policy gets confident.
#            If alpha explodes or pins at 0, TODO 1 (tanh correction) or TODO 4 is wrong —
#            a wrong log-prob makes the entropy estimate garbage and alpha chases it.
#   q1loss : large early, decays. The twin critics + min target keep it from
#            overestimating; a single critic would see q-loss creep up and ret stall.
#   aloss  : the entropy-regularized actor objective; it goes negative as min_q grows.
#
# WHY rsample(): the actor loss differentiates THROUGH the sampled action, so the
# sample must be a differentiable function of (mu, std): u = mu + std*eps. rsample()
# gives that; sample() blocks the gradient and the actor never learns.
# -----------------------------------------------------------------------------
