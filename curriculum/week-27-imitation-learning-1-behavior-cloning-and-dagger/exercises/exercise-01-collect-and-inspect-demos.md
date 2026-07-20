# Exercise 1 — Collect and Inspect Demos

**Goal:** Collect teleoperated demonstrations of the "reach for the red block" task (or generate scripted ones), and then *inspect* the resulting (observation, action) dataset for the three problems that quietly break behavior cloning before you ever train: misaligned pairs, narrow start-state coverage, and unnormalized scales. The inspection is the point — a dataset bug looks exactly like a modeling bug, and the only difference is whether you looked.

**Estimated time:** 45 minutes. Guided.

---

## Step 1 — Collect 50 demonstrations

You have two ways to get demos. Pick one (teleop is more instructive; scripted is faster).

**Teleop (recommended).** Bring up the arm + red block in Gz Sim. Drive the arm to the block with `teleop_twist_keyboard` (or a gamepad via `teleop_twist_joy`). Record with `ros2 bag`:

```bash
ros2 bag record /joint_states /red_block/pose /arm_controller/commands -o demo_run
# Drive the arm to the block, stop the bag. Repeat from VARIED start poses.
```

Do this **50 times, from varied start arm poses and varied block positions.** Variety is the whole game (Step 3) — 50 demos all from the same start teach a policy that only works from that start.

**Scripted (faster).** Use your Week-23 MoveIt2 reach or the Week-25 grasp planner as the expert; record its observations and actions to the same format. Cleaner, but no human recovery behavior.

Either way, produce a dataset: an array of observations (shape `[N, obs_dim]`) and actions (shape `[N, act_dim]`), saved as `.npy` or the LeRobot format.

> If your sim isn't ready, the synthetic 2D reach environment in Exercise 2 generates demos with a scripted expert — use it to do Steps 2–4 now and come back to real teleop later.

---

## Step 2 — Check for misaligned pairs

The first silent killer: the action recorded at time `t` must be the action the expert took *at the observation at time `t`* — not the previous step's action, not the next's. A one-step offset teaches the policy to predict the action for the wrong state.

Inspect: for a handful of pairs, confirm the action plausibly *follows* from the observation. Plot a demo's observations and actions on the same time axis. If the action "leads" or "lags" the observation by a step, you have a sync bug (the Week 5 stamping lesson). Fix it at the recording layer — pair by timestamp, not by arrival order.

```python
import numpy as np
obs = np.load("demo_obs.npy")   # [N, obs_dim]
act = np.load("demo_act.npy")   # [N, act_dim]
assert len(obs) == len(act), "obs/act length mismatch -- a sync bug"
# Eyeball a few: does act[i] plausibly move from obs[i] toward the block?
for i in range(0, len(obs), len(obs) // 5):
    print(f"t={i}  obs(arm,block)={obs[i].round(2)}  act={act[i].round(2)}")
```

---

## Step 3 — Check start-state coverage

The second silent killer: narrow coverage. Plot the *start states* of all 50 demos (the first observation of each). Do they spread across the workspace, or cluster in one spot?

```python
import matplotlib.pyplot as plt
starts = np.array([demo[0] for demo in demos])   # first obs of each demo
plt.scatter(starts[:, 0], starts[:, 1])          # e.g., arm-x vs arm-y at start
plt.title("Start-state coverage (want spread, not a cluster)")
plt.savefig("start_coverage.png")
```

If the starts cluster, your policy will succeed only near that cluster and drift everywhere else — covariate shift baked in at collection time. Go collect more demos from the *uncovered* regions. (This is also exactly what DAgger automates later: it discovers the uncovered states the policy actually visits.)

---

## Step 4 — Check the scales (do you need normalization?)

The third silent killer: mixed scales. Print the per-dimension mean and std of the observations and actions.

```python
print("obs mean:", obs.mean(0).round(3), "  obs std:", obs.std(0).round(3))
print("act mean:", act.mean(0).round(3), "  act std:", act.std(0).round(3))
```

If one observation dimension is in radians (±3) and another in meters (±0.5), or the action dimensions vary wildly in scale, the MSE loss will be dominated by the largest-scale dimension and the policy will ignore the rest. This is *why* the training loop normalizes (Lecture 1 §3) — confirm here that your data needs it.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You have a dataset of ~50 demonstrations as `[N, obs_dim]` observations and `[N, act_dim]` actions (real teleop or scripted), saved to disk.
- [ ] `notes/demo-inspection.md` records: (a) a confirmation the (obs, act) pairs are aligned (no off-by-one), (b) the start-state coverage plot with a one-line judgment (spread or clustered?), and (c) the per-dimension obs/act scales.
- [ ] If the starts clustered, you collected more from the uncovered regions (or noted it as a known limitation DAgger will address).
- [ ] You can state, in one sentence, which of the three problems your dataset had (if any) and how you'd know it was a *data* bug and not a *model* bug.

---

## Stretch

- Project the full set of demo *observations* (not just starts) to 2D with PCA and plot the cloud. This is the "demonstration manifold" — the region of state space your policy will be confident in. Everything outside it is where covariate shift lives, and you'll overlay the BC rollouts on it in Exercise 3 to *see* them wander off.
- Collect 10 *extra* demos that include deliberate small mistakes-and-recoveries (drift left, then correct back to the block). A BC policy trained with recovery demonstrations is more robust to covariate shift — a poor-man's DAgger you do at collection time.

---

When your dataset is clean and you understand its coverage, move to [Exercise 2 — Train a BC policy](exercise-02-train-bc-policy.py).
