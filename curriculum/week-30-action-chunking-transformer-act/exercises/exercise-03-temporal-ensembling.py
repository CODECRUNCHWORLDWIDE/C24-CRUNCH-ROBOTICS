#!/usr/bin/env python3
# Exercise 3 — Temporal ensembling (turn overlapping chunks into smooth commands)
#
# Goal: Fill two marked TODOs to implement temporal ensembling, then MEASURE the jerk
#       reduction vs raw chunk-switching. A policy that predicts a fresh chunk every
#       timestep has, at each timestep, several OVERLAPPING predictions for "now"
#       (the freshest plus the tails of older chunks). Ensembling averages them with
#       weights w_i = exp(-m*i). You will see a multiple-x drop in jerk.
#
# Estimated time: 60 minutes. Runnable.
#
# THE TWO TODOs (search for "# TODO"):
#   TODO 1 — the exponential weights w_i = exp(-m * age) (Lecture 2 §1.2)
#   TODO 2 — the per-timestep weighted average of the overlapping proposals (Lecture 2 §1.2)
#
# HOW TO RUN
#   pip install numpy matplotlib
#   python3 exercise-03-temporal-ensembling.py     # writes ensembling.png
#
# ACCEPTANCE CRITERIA
#   [ ] Both TODOs filled; the file runs and writes ensembling.png.
#   [ ] The ensembled-trajectory jerk is clearly LOWER than the raw chunk-switching jerk
#       (typically 2-5x lower).
#   [ ] You can explain why averaging overlapping chunks removes the chunk-boundary
#       discontinuity that raw switching has.
#   [ ] Sweeping m: large m -> reactive/jerkier (trust newest); small m -> smooth/laggy.
#
# Expected output is at the bottom of the file.

import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

np.random.seed(0)

CHUNK = 16          # action-chunk length k
HORIZON = 60        # timesteps in the episode
ACT_DIM = 1         # scalar action for a clean 1D visualization


def fake_policy(t):
    """Simulate a policy that predicts a CHUNK at timestep t. The 'true' command is a
    smooth sine; each predicted chunk is that sine plus per-chunk prediction NOISE.
    Different chunks disagree slightly -> chunk-boundary jerk if you don't ensemble.
    Returns a (CHUNK,) array of predicted actions for steps t..t+CHUNK-1."""
    steps = np.arange(t, t + CHUNK)
    true_cmd = np.sin(0.15 * steps)
    chunk_noise = 0.08 * np.random.randn()        # one offset per chunk (the disagreement)
    jitter = 0.02 * np.random.randn(CHUNK)
    return true_cmd + chunk_noise + jitter


class TemporalEnsembler:
    """Predict a fresh chunk EVERY timestep; emit an exponentially-weighted average of
    all overlapping predictions for the current timestep."""

    def __init__(self, chunk_size, m=0.1):
        self.k, self.m = chunk_size, m
        self.buffer = {}     # target_timestep -> list of (age_offset, action)
        self.t = 0

    def step(self, fresh_chunk):
        # Register each action of the fresh chunk for its target timestep. The action
        # at index `offset` targets timestep self.t + offset; `offset` is also its age
        # by the time that timestep arrives (it was predicted `offset` steps earlier).
        for offset in range(self.k):
            self.buffer.setdefault(self.t + offset, []).append((offset, fresh_chunk[offset]))

        proposals = self.buffer.pop(self.t)        # [(age, action), ...] for NOW
        ages = np.array([age for age, _ in proposals], dtype=float)
        actions = np.array([a for _, a in proposals], dtype=float)

        # TODO 1: the exponential weights. w = exp(-m * ages). (Lecture 2 §1.2.)
        w = ...

        # TODO 2: the normalized weighted average of the proposals.
        #   action = sum(w * actions) / sum(w). (Lecture 2 §1.2.)
        action = ...

        self.t += 1
        return action


def run_raw_switching():
    """Baseline: execute non-overlapping chunks back-to-back (predict at 0, k, 2k, ...).
    The seam at each chunk boundary is where the jerk lives."""
    traj = []
    t = 0
    while t < HORIZON:
        chunk = fake_policy(t)
        for a in chunk:
            if t >= HORIZON:
                break
            traj.append(a)
            t += 1
    return np.array(traj[:HORIZON])


def run_ensembled(m):
    """Predict a fresh chunk EVERY timestep and ensemble."""
    ens = TemporalEnsembler(CHUNK, m=m)
    traj = []
    for t in range(HORIZON):
        chunk = fake_policy(t)
        traj.append(ens.step(chunk))
    return np.array(traj)


def jerk(traj):
    """A simple jerk proxy: sum of squared second differences (acceleration changes)."""
    return float(np.sum(np.diff(traj, n=2) ** 2))


def main():
    raw = run_raw_switching()
    ens = run_ensembled(m=0.1)

    j_raw, j_ens = jerk(raw), jerk(ens)
    print(f"raw chunk-switching jerk : {j_raw:.4f}")
    print(f"temporal-ensembled jerk  : {j_ens:.4f}   ({j_raw / max(j_ens, 1e-9):.1f}x smoother)")

    # Sweep m to show the reactivity/smoothness trade.
    print("\nm sweep (jerk):")
    for m in [0.001, 0.05, 0.5, 5.0]:
        print(f"  m={m:>6}:  jerk={jerk(run_ensembled(m)):.4f}")
    print("  (large m -> trust newest chunk -> reactive but jerkier;")
    print("   small m -> average all overlaps -> smooth but laggy)")

    plt.figure(figsize=(9, 4))
    plt.plot(raw, label=f"raw chunk-switching (jerk={j_raw:.3f})", alpha=0.7)
    plt.plot(ens, label=f"temporal-ensembled m=0.1 (jerk={j_ens:.3f})", lw=2)
    plt.title("Temporal ensembling removes the chunk-boundary jerk")
    plt.xlabel("timestep"); plt.ylabel("action"); plt.legend()
    plt.tight_layout(); plt.savefig("ensembling.png", dpi=110)
    print("\nwrote ensembling.png")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed
# -----------------------------------------------------------------------------
#
# raw chunk-switching jerk : 0.0461
# temporal-ensembled jerk  : 0.0123   (3.7x smoother)
#
# m sweep (jerk):
#   m= 0.001:  jerk=0.0098
#   m=  0.05:  jerk=0.0115
#   m=   0.5:  jerk=0.0204
#   m=   5.0:  jerk=0.0379
#   (large m -> trust newest chunk -> reactive but jerkier;
#    small m -> average all overlaps -> smooth but laggy)
#
# wrote ensembling.png
#
# THE LESSON: raw chunk-switching has a SEAM at every chunk boundary — consecutive
# chunks, predicted from different states, disagree slightly, and the discontinuity is
# jerk. Temporal ensembling has NO seam: every timestep's action blends several
# overlapping predictions that mostly OVERLAP with the previous timestep's blend, so
# consecutive actions change gradually. The m sweep shows the trade: small m averages
# everything (smoothest, but old predictions add lag); large m trusts only the newest
# (most reactive, but recovers the jerk). This smoothing is AFFORDABLE for ACT precisely
# because its inference is single-pass, so re-predicting every timestep is cheap
# (Lecture 2 §1.4) — temporal ensembling and single-pass inference are a matched pair.
# -----------------------------------------------------------------------------
