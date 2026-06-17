#!/usr/bin/env python3
# Exercise 2 — PPO solves CartPole (a complete single-file PPO with four TODOs)
#
# Goal: Fill four marked TODOs to turn this scaffold into a working PPO. When they
#       are correct, CartPole-v1 is SOLVED (episodic return reaches the 500 cap)
#       in well under a minute on a laptop CPU. The scaffolding — env loop, rollout
#       buffer, logging, eval — is correct and worth reading as a reference.
#
# Estimated time: 60 minutes. Runnable.
#
# THE FOUR TODOs (all small, all in this file, search for "# TODO"):
#   TODO 1 — the GAE recursion (Lecture 1 §4)
#   TODO 2 — the probability ratio r_t(theta) (Lecture 1 §6)
#   TODO 3 — the clipped surrogate policy loss (Lecture 1 §6)
#   TODO 4 — the entropy term used in the loss (Lecture 1 §6)
#
# HOW TO RUN
#   pip install "gymnasium[classic-control]" torch numpy
#   python3 exercise-02-ppo-cartpole.py
#
# ACCEPTANCE CRITERIA
#   [ ] All four TODOs filled; the file runs without shape errors.
#   [ ] Mean episodic return reaches >= 475 (CartPole is "solved" at 475+; the cap
#       is 500) within ~50 updates.
#   [ ] approx_kl stays roughly in [0.003, 0.03] (the clip is holding); if it
#       explodes, your ratio or surrogate (TODO 2/3) is wrong.
#   [ ] entropy starts near ln(2) ~ 0.69 (two actions, near-uniform) and decays
#       slowly. A sudden collapse to ~0 means TODO 4 is wrong or missing.
#
# Expected output is at the bottom of the file.

import time

import numpy as np
import torch
import torch.nn as nn
import gymnasium as gym

# ----------------------------- hyperparameters -------------------------------
ENV_ID = "CartPole-v1"
TOTAL_UPDATES = 60
ROLLOUT_STEPS = 1024          # env steps collected per update (on-policy batch)
EPOCHS = 4                    # gradient epochs over each rollout
MINIBATCH = 256
GAMMA = 0.99
GAE_LAMBDA = 0.95
CLIP_EPS = 0.2
VALUE_COEF = 0.5
ENTROPY_COEF = 0.01
LR = 2.5e-4
MAX_GRAD_NORM = 0.5
SEED = 1

torch.manual_seed(SEED)
np.random.seed(SEED)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ----------------------------- networks --------------------------------------
class ActorCritic(nn.Module):
    """Discrete-action actor (Categorical) + a value critic. Shared nothing,
    which keeps CartPole simple and stable."""

    def __init__(self, obs_dim: int, n_actions: int, hidden: int = 64):
        super().__init__()
        self.actor = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, n_actions),
        )
        self.critic = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, 1),
        )

    def distribution(self, obs: torch.Tensor) -> torch.distributions.Categorical:
        return torch.distributions.Categorical(logits=self.actor(obs))

    def value(self, obs: torch.Tensor) -> torch.Tensor:
        return self.critic(obs).squeeze(-1)

    def act(self, obs: torch.Tensor):
        dist = self.distribution(obs)
        action = dist.sample()
        return action, dist.log_prob(action), self.value(obs)


# ----------------------------- GAE -------------------------------------------
def compute_gae(rewards, values, dones, last_value, gamma, lam):
    """Backward GAE-lambda pass. All inputs are 1D tensors of length T over a
    single rollout; `last_value` bootstraps the final step. Returns (adv, ret)."""
    T = rewards.shape[0]
    adv = torch.zeros(T, device=rewards.device)
    last_gae = 0.0
    for t in reversed(range(T)):
        next_value = last_value if t == T - 1 else values[t + 1]
        nonterminal = 1.0 - dones[t]
        delta = rewards[t] + gamma * next_value * nonterminal - values[t]
        # TODO 1: implement the GAE recursion. Combine `delta` with the discounted,
        #         masked previous advantage `last_gae`. Exactly the form from
        #         Lecture 1 §4: last_gae = delta + gamma * lam * nonterminal * last_gae
        last_gae = ...
        adv[t] = last_gae
    returns = adv + values
    return adv, returns


# ----------------------------- rollout collection ----------------------------
def collect_rollout(env, agent, obs, steps):
    """Run the current policy for `steps` env steps, storing the transitions.
    Returns the buffers and the obs to continue from, plus the bootstrap value."""
    obs_buf, act_buf, logp_buf, val_buf, rew_buf, done_buf = [], [], [], [], [], []
    ep_returns = []
    ep_ret = 0.0
    for _ in range(steps):
        obs_t = torch.as_tensor(obs, dtype=torch.float32, device=device)
        with torch.no_grad():
            action, logp, value = agent.act(obs_t.unsqueeze(0))
        a = int(action.item())
        next_obs, reward, terminated, truncated, _ = env.step(a)

        obs_buf.append(obs_t)
        act_buf.append(action.squeeze(0))
        logp_buf.append(logp.squeeze(0))
        val_buf.append(value.squeeze(0))
        rew_buf.append(float(reward))
        # IMPORTANT: only `terminated` zeroes the bootstrap. `truncated` (the time
        # limit) does NOT — the future still exists. (Lecture 1 §4.)
        done_buf.append(1.0 if terminated else 0.0)

        ep_ret += reward
        obs = next_obs
        if terminated or truncated:
            ep_returns.append(ep_ret)
            ep_ret = 0.0
            obs, _ = env.reset()

    with torch.no_grad():
        last_val = agent.value(
            torch.as_tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)
        ).squeeze(0)

    batch = {
        "obs": torch.stack(obs_buf),
        "actions": torch.stack(act_buf),
        "logprobs": torch.stack(logp_buf),
        "values": torch.stack(val_buf),
        "rewards": torch.as_tensor(rew_buf, dtype=torch.float32, device=device),
        "dones": torch.as_tensor(done_buf, dtype=torch.float32, device=device),
    }
    return batch, obs, last_val, ep_returns


# ----------------------------- PPO update ------------------------------------
def ppo_update(agent, optimizer, batch, advantages, returns):
    n = batch["obs"].shape[0]
    # Per-batch advantage normalization — a standard, high-impact stabilizer.
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    approx_kls, clip_fracs, entropies = [], [], []
    for _ in range(EPOCHS):
        idx = torch.randperm(n, device=device)
        for start in range(0, n, MINIBATCH):
            mb = idx[start:start + MINIBATCH]
            dist = agent.distribution(batch["obs"][mb])
            new_logp = dist.log_prob(batch["actions"][mb])
            entropy = dist.entropy()

            old_logp = batch["logprobs"][mb]
            # TODO 2: compute the probability ratio r_t(theta) = pi_new / pi_old.
            #         Work in log-space for stability: ratio = exp(new_logp - old_logp).
            ratio = ...

            mb_adv = advantages[mb]
            unclipped = ratio * mb_adv
            clipped = torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS) * mb_adv
            # TODO 3: the clipped-surrogate POLICY LOSS. The objective MAXIMIZES the
            #         min of the two surrogate terms, so the loss is the NEGATIVE mean
            #         of that min. (Lecture 1 §6.)
            policy_loss = ...

            value_pred = agent.value(batch["obs"][mb])
            value_loss = ((value_pred - returns[mb]) ** 2).mean()

            # TODO 4: the entropy TERM for the loss. We want to MAXIMIZE entropy, so
            #         we SUBTRACT ENTROPY_COEF * mean-entropy from the loss below.
            #         Set entropy_term to the mean entropy here.
            entropy_term = ...

            loss = policy_loss + VALUE_COEF * value_loss - ENTROPY_COEF * entropy_term

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(agent.parameters(), MAX_GRAD_NORM)
            optimizer.step()

            with torch.no_grad():
                approx_kls.append((old_logp - new_logp).mean().item())
                clip_fracs.append(
                    ((ratio - 1.0).abs() > CLIP_EPS).float().mean().item()
                )
                entropies.append(entropy.mean().item())

    # explained variance: how much of the return variance the critic captures.
    with torch.no_grad():
        y_pred = agent.value(batch["obs"])
        var_y = returns.var()
        explained_var = (
            1.0 - (returns - y_pred).var() / (var_y + 1e-8)
        ).item()
    return {
        "approx_kl": float(np.mean(approx_kls)),
        "clip_frac": float(np.mean(clip_fracs)),
        "entropy": float(np.mean(entropies)),
        "explained_var": explained_var,
    }


# ----------------------------- main ------------------------------------------
def main() -> None:
    env = gym.make(ENV_ID)
    obs_dim = env.observation_space.shape[0]
    n_actions = env.action_space.n
    agent = ActorCritic(obs_dim, n_actions).to(device)
    optimizer = torch.optim.Adam(agent.parameters(), lr=LR, eps=1e-5)

    obs, _ = env.reset(seed=SEED)
    start = time.time()
    print(f"PPO on {ENV_ID} | device={device}")
    print(f"{'upd':>4} {'ret':>7} {'kl':>7} {'clip':>6} {'ent':>6} {'ev':>6}")

    for update in range(1, TOTAL_UPDATES + 1):
        batch, obs, last_val, ep_returns = collect_rollout(
            env, agent, obs, ROLLOUT_STEPS
        )
        adv, returns = compute_gae(
            batch["rewards"], batch["values"], batch["dones"],
            last_val, GAMMA, GAE_LAMBDA,
        )
        diag = ppo_update(agent, optimizer, batch, adv, returns)

        mean_ret = float(np.mean(ep_returns)) if ep_returns else float("nan")
        if update % 5 == 0 or update == 1:
            print(f"{update:>4} {mean_ret:>7.1f} {diag['approx_kl']:>7.4f} "
                  f"{diag['clip_frac']:>6.2f} {diag['entropy']:>6.3f} "
                  f"{diag['explained_var']:>6.2f}")

        if not np.isnan(mean_ret) and mean_ret >= 475:
            print(f"\nSOLVED at update {update}: mean return {mean_ret:.1f} >= 475 "
                  f"in {time.time() - start:.1f}s")
            break

    env.close()


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed/CPU, SHAPE is stable
# -----------------------------------------------------------------------------
#
# PPO on CartPole-v1 | device=cpu
#  upd     ret      kl   clip    ent     ev
#    1    22.3  0.0098   0.08  0.690  -0.03
#    5    48.1  0.0123   0.12  0.668   0.31
#   10   121.7  0.0151   0.18  0.601   0.74
#   15   268.4  0.0142   0.16  0.512   0.88
#   20   441.0  0.0119   0.13  0.430   0.93
#
# SOLVED at update 23: mean return 487.5 >= 475 in 34.8s
#
# What "healthy" looks like, trace by trace:
#   ret  : climbs from ~20 (random) toward the 500 cap.
#   kl   : stays ~0.005-0.03. If it spikes past 0.05, your ratio/surrogate is wrong
#          (TODO 2/3) and the policy will collapse.
#   clip : 0.1-0.3 — the clip is binding sometimes, not always. ~0 = steps too small;
#          ~1 = steps too big.
#   ent  : starts ~ln(2)=0.69 (two near-equal actions) and decays slowly as the
#          policy commits. A crash to ~0 means TODO 4 is wrong/missing.
#   ev   : explained variance climbs toward 1.0 — the critic is learning the returns.
# -----------------------------------------------------------------------------
