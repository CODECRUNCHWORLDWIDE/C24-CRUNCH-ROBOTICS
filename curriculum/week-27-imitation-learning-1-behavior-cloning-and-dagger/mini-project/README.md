# Mini-Project — `crunch_il`: A Behavior-Cloning + DAgger Pipeline With an Honest Eval

> Build a reusable imitation-learning pipeline that collects demonstrations of the reach task, trains a behavior-cloning policy in PyTorch, evaluates it on a fixed protocol, runs DAgger to close the covariate-shift gap, re-evaluates, and ships the policy wrapped in the Week-24 safety leash — with an honest eval report (success rates with intervals, failures classified) that a reviewer can reproduce.

This is the artifact that turns this week's two lectures into a tool. After this week, "teach the robot a task from demonstrations" is a *pipeline* you run — collect, clone, evaluate, DAgger, re-evaluate — with a number at the end that you can defend, not a one-off script that worked once. When Diffusion Policy (Week 29) and ACT (Week 30) arrive, this pipeline is the baseline they are measured against, and the demonstrations it collects are the data they train on.

**Estimated time:** ~12 hours, split across Thursday, Friday, and Saturday in the suggested schedule.

**Compounds forward:** The demonstrations `crunch_il` collects are reused by **Week 29 (Diffusion Policy)** and **Week 30 (ACT)** — both train on these exact demos and compare against this BC+DAgger baseline. The safety wrapper is the **Week-32 "learned policy + classical fallback"** pattern. The eval protocol is the one you'll reuse for every learned policy in Phase 4. Build it well now; you lean on it for the rest of the phase.

---

## What you will build

A small package `crunch_il` with a runnable end-to-end pipeline:

```bash
# 1. Collect demos (teleop in Gz Sim, or the synthetic expert for fast iteration).
python3 -m crunch_il.collect --demos 50 --out demos.npz

# 2. Train BC, evaluate, run DAgger, re-evaluate, and write the report.
python3 -m crunch_il.run --demos demos.npz --dagger-rounds 2 --report report.md
```

The pipeline:

1. **Collects** demonstrations of the reach task and saves them in a clean, reloadable format (observations, actions, and the start states, with honest timestamps).
2. **Trains** a PyTorch BC policy with a correct training loop (normalization fit on train only, train/val split, MSE loss, early stopping) and saves the model *with its normalization stats*.
3. **Evaluates** the BC policy on a *fixed protocol* (pre-stated success predicate, fixed start states including novel ones, ≥ 20 trials), reporting a success rate with a confidence interval and a per-trial failure classification.
4. **Runs DAgger** for N rounds: roll out the policy, query the expert at the visited states, aggregate, retrain.
5. **Re-evaluates** on the *same* protocol and reports the BC vs. BC+DAgger comparison with intervals.
6. **Wraps** the final policy in the Week-24 safety leash (velocity/workspace clamp + classical fallback after three rejections) for deployment.
7. **Writes** an honest eval report: the protocol, both success rates with intervals, the failure classifications, and a state-visitation plot showing the covariate-shift gap closing.

By the end you have a public repo, a reusable pipeline, a saved policy + its norm stats, and a report a skeptic can reproduce.

---

## Why a pipeline, not a script

You could train one BC policy and call it done. Don't — because a single run tells you nothing reproducible. A pipeline gives you:

- **A fixed eval protocol, reused.** The same protocol scores BC, BC+DAgger, and (in Weeks 29–30) Diffusion Policy and ACT. A comparison is only meaningful if every method faces the same protocol.
- **Honest numbers.** Success rates with confidence intervals, not "it looked good." A reviewer reruns the pipeline and gets the same shape of number.
- **The safety wrapper, by default.** The policy ships leashed — clamped and with a fallback — because a learned policy near a person is exactly what the leash exists for.
- **Reusable demos.** The demonstrations are saved in a format Weeks 29–30 can load, so the heavier methods train on the same data and the comparison is apples-to-apples.

---

## Package layout

```
crunch_il/
├── package.xml                    # if you wrap it as a ROS2 package
├── setup.py
├── crunch_il/
│   ├── __init__.py
│   ├── env.py                     # the reach env (Gz Sim bridge, or the synthetic env)
│   ├── policy.py                  # the PyTorch BC policy (nn.Module) + DemoDataset
│   ├── train.py                   # the training loop (norm, split, early stop)
│   ├── collect.py                 # demo collection (teleop record, or scripted expert)
│   ├── dagger.py                  # the DAgger loop (rollout, expert-label, aggregate)
│   ├── evaluate.py                # the fixed eval protocol + failure classification
│   ├── safety_wrap.py             # velocity/workspace clamp + classical fallback
│   └── run.py                     # the end-to-end orchestrator + report writer
├── eval-protocol.md               # the PRE-STATED protocol (predicate, starts, trials)
└── test/
    ├── test_policy.py             # unit tests: shapes, normalization round-trip
    ├── test_dagger.py             # unit tests: aggregation grows the dataset; labels are expert's
    └── test_evaluate.py           # unit tests: success predicate, interval computation
```

---

## Functional requirements

### R1 — Demo collection with honest timestamps

`collect.py` records the reach task — teleop in Gz Sim (record `/joint_states`, the block pose, and the expert's command) or the synthetic scripted expert — into a reloadable `.npz`. Observations and actions are *paired at the same timestep* (no off-by-one), and the start states are saved so the eval protocol can reuse and extend them.

### R2 — A BC policy trained correctly

`policy.py` + `train.py` implement the PyTorch MLP policy and a training loop with: normalization fit on the *training split only*, a held-out validation split, MSE loss (continuous actions), early stopping on validation loss, and the model saved *with its normalization stats*. Loading the model un-normalizes the predicted action at deployment.

### R3 — A fixed, pre-stated eval protocol

`evaluate.py` enforces the protocol from `eval-protocol.md` (written *before* any results): a crisp success predicate, a fixed set of start states including ones *not* in the demos, ≥ 20 trials. It returns a success rate, a 95% confidence interval, and a per-trial failure classification (drift / underfit / safety-clamp).

### R4 — DAgger that aggregates

`dagger.py` runs N rounds: roll out the *policy* (visit its own states), query the *expert* at every visited state, *aggregate* the new (state, expert-action) pairs into the dataset (grow it, never replace), and retrain. A unit test asserts the dataset grows each round and the new labels are the expert's, not the policy's.

### R5 — BC vs. BC+DAgger, honestly compared

`run.py` evaluates BC and BC+DAgger on the *same* protocol and reports both success rates with intervals. If the intervals overlap, the report says so (and the pipeline can run more trials). The report includes a state-visitation plot showing BC rollouts off the demo manifold and DAgger rollouts on it.

### R6 — The policy ships leashed

`safety_wrap.py` wraps the final policy: a velocity/workspace clamp rejects out-of-bounds actions, and a classical fallback (a scripted reach or the Week-25 grasp planner) takes over after the policy's action is clamped three times in a row. The deployed policy is the *wrapped* one, never the raw network.

### R7 — A reproducible report

`run.py --report report.md` writes: the pre-stated protocol, the BC and BC+DAgger success rates with intervals, the failure classifications, the state-visitation plot, and a one-paragraph mechanistic explanation of the covariate-shift gap and how DAgger closed it. A reviewer reruns the pipeline and reproduces the numbers within the intervals.

---

## Rules

- **You may** reuse the ROS2 / PyTorch docs, the LeRobot dataset format, your exercise code, and the Week-24 safety wrapper and Week-25 grasp planner (as the fallback).
- **You must** use PyTorch for the policy and a correct training loop (normalization on train only, validation split, early stopping, stats saved with the model).
- **You must** pre-state the eval protocol in `eval-protocol.md` *before* you train, and score BC and BC+DAgger on it identically. A protocol decided after seeing results is an automatic fail.
- **You must** report success rates *with confidence intervals*, not bare rates. 15/20 without an interval is not an honest number.
- **You must** ship the policy *leashed* — the deployed policy is the safety-wrapped one. A raw network driving the arm with no clamp fails R6.
- **You must not** relax the success predicate after seeing the results to make a number look better.
- Python 3.12 (Ubuntu 24.04), `rclpy` on Jazzy (if wrapped as ROS2), PyTorch (CPU fine), NumPy, Matplotlib.

---

## Acceptance criteria

- [ ] A public GitHub repo named `c24-week-27-crunch-il-<yourhandle>`.
- [ ] `python3 -m crunch_il.collect` produces a reloadable demo dataset with aligned (obs, act) pairs and saved start states.
- [ ] `python3 -m crunch_il.run` trains BC, evaluates, runs DAgger, re-evaluates, and writes the report — end to end, one command.
- [ ] The BC training loop normalizes on train only, uses a validation split and early stopping, and saves the model *with* its normalization stats.
- [ ] `eval-protocol.md` is committed and dated *before* the results; BC and BC+DAgger are scored on it identically.
- [ ] The report shows BC and BC+DAgger success rates *with 95% confidence intervals* and per-trial failure classifications.
- [ ] DAgger aggregates (the dataset grows each round); the success rate improves and the report shows the state-visitation plot.
- [ ] The deployed policy is the *safety-wrapped* one (clamp + fallback); a demonstration shows a drifting action being clamped.
- [ ] `colcon test` (or `pytest`) passes the policy, DAgger, and evaluate unit tests.
- [ ] A `README.md` with the run commands, the headline BC-vs-DAgger numbers, and a paragraph explaining the covariate-shift gap mechanistically.
- [ ] Committed and pushed.

---

## Grading rubric (100 points)

| Area | Points | What we look for |
|---|---:|---|
| **BC pipeline correctness** | 20 | Correct training loop: norm on train only, val split, early stopping, stats saved with the model; no normalization-at-deploy bug. |
| **The fixed eval protocol** | 20 | Pre-stated predicate + starts (incl. novel) + ≥ 20 trials; BC and DAgger scored identically; rates reported with intervals. |
| **DAgger** | 20 | Aggregates (grows the dataset); policy chooses, expert labels; measurable success-rate improvement; tests assert the aggregation. |
| **Honest comparison + evidence** | 15 | BC vs. DAgger with intervals; the state-visitation plot showing the gap close; mechanistic explanation, not adjectives. |
| **Safety wrapper** | 15 | Deployed policy is leashed (clamp + fallback after 3 rejections); a clamped drifting action demonstrated. |
| **Reproducibility + hygiene** | 10 | One-command pipeline; report reproduces within intervals; tests green; clean repo. |

A submission whose **eval protocol was decided after seeing results**, or that **reports bare rates with no intervals**, or whose **deployed policy is the raw network with no leash**, caps at 55 points regardless of polish. The honest protocol, the intervals, and the leash are the load-bearing properties — the rubric weights them accordingly.

---

## Stretch goals

- **Multiple DAgger rounds with a plateau plot** (homework P3) baked into the report: success rate vs. round, with the plateau identified.
- **The β-mixing schedule** (Lecture 2 §3.1): early rounds execute a mix of expert and policy actions; compare convergence to pure-policy rollouts.
- **The LeRobot dataset format.** Save the demos in LeRobot's format so Weeks 29–30 (Diffusion Policy, ACT) load them with no conversion — making the cross-method comparison truly apples-to-apples.
- **CI job.** A GitHub Actions workflow that runs the pipeline on the synthetic env (no GPU, no robot) and asserts BC+DAgger beats plain BC by a margin — a regression test for the whole pipeline.

---

## Common pitfalls (read before you start, re-read when stuck)

These are the failures that eat the most hours on this pipeline. Knowing them in advance is half the cure.

- **The policy "trained great" but deploys garbage.** A normalization bug: you trained on normalized inputs but deployed on raw ones, or used the deployment data's stats instead of the training stats. The policy must see the same transform at train and deploy.
- **You declared victory at the loss curves.** Train and val MSE are both low, so you shipped — and the policy drifts. Healthy loss curves cannot reveal covariate shift; you must *evaluate the rollout*, not just the loss.
- **The (obs, act) pairs are misaligned.** An off-by-one teaches the wrong mapping. The "broken policy" is actually a data bug. Eyeball a few pairs before training.
- **DAgger replaces instead of aggregates.** Each round you overwrote the dataset with policy rollouts and threw away the expert demos. The dataset must *grow*. Now the policy forgot the good behavior.
- **The eval protocol was decided after seeing results.** You relaxed the success predicate or chose favorable start states once you saw the numbers. That is not a protocol; it is a rationalization. Pre-state it, date it, score both policies on it.
- **Bare success rates, no intervals.** "15/20 beats 12/20" with no interval — but at 20 trials those intervals overlap and it might be noise. Report the interval; run more trials if inconclusive.
- **You compared BC and DAgger on different starts.** The comparison is meaningless if the protocols differ. Same starts, same predicate, both policies.
- **The deployed policy is the raw network.** No clamp, no fallback. A drifting policy commands a wild joint jump straight to the arm. Deploy the *wrapped* policy, always.
- **The action representation mismatches.** Trained on deltas, deployed as absolutes (or a frame mismatch). The arm moves consistently wrong. The policy must predict what it executes.

Each pitfall maps to a lecture section. When the pipeline misbehaves, walk the Lecture-1 §8.5 debugging checklist — rule out the mundane bugs (alignment, normalization, action representation) *before* concluding "covariate shift," because DAgger won't fix a normalization bug.

## How this connects to the rest of C24

- **Week 28 (RL)** learns from a reward instead of demonstrations; the eval protocol you built here is the one you'll reuse to compare the RL policy against this imitation baseline.
- **Week 29 (Diffusion Policy)** trains on *these exact demos* and compares against this BC+DAgger baseline — and fixes the multimodal-averaging failure (homework P6) that BC's MSE loss cannot.
- **Week 30 (ACT)** trains on the same demos and directly attacks the diffusion-of-error problem (homework P2) with action chunking.
- **Week 32 (learned policy + classical fallback)** generalizes the safety wrapper you built here into the phase milestone's safety scaffold.

## Definition of done (the one-line self-check)

Before you call the pipeline finished, confirm each in one line:

- **`collect`** produces aligned (obs, act) pairs with saved start states.
- **`train`** normalizes on train only, uses a val split + early stopping, and saves the model *with* its norm stats.
- **`eval-protocol.md`** is committed and dated *before* the results; BC and DAgger are scored on it identically.
- **The report** shows both success rates *with 95% confidence intervals* and per-trial failure classifications.
- **DAgger** aggregates (the dataset grows each round); success improves; the state-visitation plot is included.
- **The deployed policy** is the safety-wrapped one (clamp + fallback); a clamped drifting action is demonstrated.
- **`run.py`** does collect → train → eval → DAgger → eval → report in one command.
- **The tests** (`test_policy.py`, `test_dagger.py`, `test_evaluate.py`) are green.

If any line is "no," that part isn't done. The two that fail submissions most often:

- A protocol decided *after* seeing results (a rationalization, not a protocol). Pre-state and date it.
- Bare success rates with *no intervals* (a number you cannot tell from noise). Report the 95% interval.

Get those two right and the rest follows; get them wrong and a polished pipeline still fails the bar.

When you've finished, push the repo and take the [quiz](../quiz.md).
