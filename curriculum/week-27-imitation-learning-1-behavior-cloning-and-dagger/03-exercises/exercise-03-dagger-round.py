#!/usr/bin/env python3
# Exercise 3 — One round of DAgger (and watch the drift get fixed)
#
# Goal: Take the behavior-cloned policy from Exercise 2, roll it out (so it visits
#       its OWN state distribution), query the expert at the VISITED states,
#       aggregate those (state, expert_action) pairs into the dataset, retrain, and
#       measure the success-rate jump. This is the covariate-shift fix, made real.
#
# Estimated time: 45 minutes. Runnable. CPU is fine.
#
# THE DAgger LOOP (Lecture 2 §3)
#
#   1. Train BC on the expert demos (round 0).
#   2. Roll out the POLICY (visit its own state distribution, including drift).
#   3. Query the EXPERT at every VISITED state ("what would you do from here?").
#   4. AGGREGATE the new (visited_state, expert_action) pairs into the dataset.
#   5. Retrain. Repeat.
#
#   The key inversion: the POLICY chooses actions during the rollout (so we sample
#   ITS states), but we record the EXPERT's action at each state (so we get the
#   right label for the state the policy actually reached).
#
# HOW TO USE THIS FILE
#
#       pip install torch numpy matplotlib
#       python3 exercise-03-dagger-round.py            # BC -> drift -> DAgger -> recover
#       python3 exercise-03-dagger-round.py --rounds 4 # several rounds; watch it climb
#
# ACCEPTANCE CRITERIA
#
#   [ ] After 1 DAgger round, the success rate from NOVEL starts is clearly higher
#       than plain BC (the drift-and-flail trials now recover).
#   [ ] Each round AGGREGATES (the dataset grows; it does not replace the demos).
#   [ ] success_vs_round.png shows success climbing with DAgger rounds.
#   [ ] You can state why DAgger works where more BC epochs would not (it adds data
#       from the policy's OWN state distribution).
#
# This file reuses the env, expert, policy, and training loop from exercise 2.

import argparse
import numpy as np
import torch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Reuse exercise 2's components. (In a repo you'd import them; inlined here so the
# file is standalone-runnable.)
from importlib.machinery import SourceFileLoader
import os
_ex2_path = os.path.join(os.path.dirname(__file__), "exercise-02-train-bc-policy.py")
if os.path.exists(_ex2_path):
    ex2 = SourceFileLoader("ex2", _ex2_path).load_module()
    ReachEnv = ex2.ReachEnv
    expert_action = ex2.expert_action
    collect_expert_demos = ex2.collect_expert_demos
    train_bc = ex2.train_bc
    deploy_step = ex2.deploy_step
    evaluate = ex2.evaluate
else:
    raise SystemExit("Run this next to exercise-02-train-bc-policy.py "
                     "(it provides the env, expert, policy, and training loop).")


def dagger_collect(model, train_ds, n_rollouts=15, seed=500):
    """Roll out the POLICY, query the EXPERT at every VISITED state.
    Returns (new_obs, new_act) -- the policy's own states, expert-labeled."""
    new_obs, new_act = [], []
    for r in range(n_rollouts):
        env = ReachEnv()
        obs = env.reset(seed=seed + r)
        done = False
        while not done:
            # The POLICY drives: we visit the policy's own (possibly drifted) states.
            action = deploy_step(model, train_ds, obs)
            # The EXPERT labels: what it WOULD do from this state.
            new_obs.append(obs.copy())
            new_act.append(expert_action(obs).copy())
            obs, done = env.step(action)
    return np.array(new_obs), np.array(new_act)


def run_dagger(rounds=3):
    # Round 0: plain BC on the expert demos.
    obs, act = collect_expert_demos(n_demos=50, seed=0)
    model, train_ds, _ = train_bc(obs, act)
    rate0, drift0 = evaluate(model, train_ds, n_trials=20)
    print(f"round 0 (plain BC):  success={rate0*100:.0f}%  "
          f"dataset={len(obs)} pairs  (drift fails={drift0})")
    rates = [rate0]
    sizes = [len(obs)]

    for i in range(1, rounds + 1):
        # Collect the policy's visited states, expert-labeled, and AGGREGATE.
        new_obs, new_act = dagger_collect(model, train_ds, seed=500 + 100 * i)
        obs = np.concatenate([obs, new_obs])      # GROW the dataset (don't replace)
        act = np.concatenate([act, new_act])
        model, train_ds, _ = train_bc(obs, act)   # retrain on the union
        rate, drift = evaluate(model, train_ds, n_trials=20)
        print(f"round {i} (DAgger):    success={rate*100:.0f}%  "
              f"dataset={len(obs)} pairs  (drift fails={drift})")
        rates.append(rate)
        sizes.append(len(obs))

    plt.plot(range(len(rates)), [r * 100 for r in rates], marker="o")
    plt.xlabel("DAgger round (0 = plain BC)")
    plt.ylabel("success rate (%) from novel starts")
    plt.title("DAgger closes the covariate-shift gap")
    plt.ylim(0, 105)
    plt.savefig("success_vs_round.png")
    print("saved success_vs_round.png")
    return rates, sizes


def main():
    parser = argparse.ArgumentParser(description="One+ rounds of DAgger.")
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args()
    run_dagger(rounds=args.rounds)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (approximate; depends on seed)
# -----------------------------------------------------------------------------
#
# round 0 (plain BC):  success=55%  dataset=1180 pairs  (drift fails=7)
# round 1 (DAgger):    success=85%  dataset=2050 pairs  (drift fails=2)
# round 2 (DAgger):    success=95%  dataset=2900 pairs  (drift fails=1)
# saved success_vs_round.png
#
# THE LESSON: round 0 is the same drifting BC policy from Exercise 2. After ONE
# DAgger round, success jumps sharply, because the dataset now contains the OFF-
# DISTRIBUTION states the policy drifted into, labeled with the expert's recovery
# action. The drift-and-flail trials recover. The dataset GREW (aggregated, not
# replaced). More plain-BC epochs on the original 1180 pairs would NOT do this --
# they have no data about the policy's own drifted states. That is the whole point
# of DAgger: it samples states from the policy and labels from the expert, closing
# the covariate-shift gap that more training on the expert's states cannot.
# -----------------------------------------------------------------------------
