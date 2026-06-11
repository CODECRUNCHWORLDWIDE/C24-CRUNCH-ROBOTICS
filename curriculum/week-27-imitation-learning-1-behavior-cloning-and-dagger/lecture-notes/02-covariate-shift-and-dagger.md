# Lecture 2 — Covariate Shift and DAgger: Why BC Drifts, and the Fix That Works

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain covariate shift and the compounding-error argument precisely, implement one round of DAgger, reason about the diffusion-of-error problem that motivates the methods of Weeks 29–30, evaluate a policy honestly, and wrap a learned policy in a safety leash.

Lecture 1 built a behavior-cloned policy with healthy loss curves. This lecture explains why that policy, despite its healthy curves, drifts and flails the moment it leaves the demonstration data — and what to do about it. The through-line:

> **A policy is not an ordinary supervised model: it acts, and acting changes the distribution of states it sees. Behavior cloning trains on the expert's states but is tested on its own states, and the gap between them — covariate shift — is where BC fails. DAgger closes the gap by training on the states the policy actually visits.**

---

## 1. Covariate shift: why a policy is different from a classifier

A supervised classifier is trained on data drawn from some distribution `D` and tested on data from the *same* `D`. That assumption — train and test distributions match — is the foundation of every generalization guarantee in supervised learning.

A policy breaks it. Here is the chain, and it is worth reading slowly because it is the heart of the week:

1. Behavior cloning trains the policy on `(o, a)` pairs from the **expert's** trajectories. The observations in the dataset are distributed according to the states the *expert* visited — call it `d_expert`.
2. At deployment, the policy acts. At the first state, it produces an action that is *close* to the expert's but not identical (no model is perfect).
3. That slightly-wrong action moves the robot to a slightly-different next state — a state a little *off* the expert's trajectory, a little outside `d_expert`.
4. At that off-distribution state, the policy has seen *less* training data (or none), so its action is *more* wrong.
5. The more-wrong action moves the robot *further* off-distribution, where the policy is *even more* lost.
6. Repeat. The errors **compound**, and within a few steps the policy is in a region of state space the demonstrations never covered, flailing, with no idea what to do.

This is **covariate shift**: the distribution of states the policy visits at deployment (`d_policy`) drifts away from the distribution it was trained on (`d_expert`). It is not an optimization failure — the policy minimized its training loss perfectly. It is not an overfitting failure — it generalizes fine *within* `d_expert`. It is a *distributional* failure: the policy is being evaluated on a distribution it was never trained on, and it created that distribution itself, by acting.

> **Why more epochs and a bigger network don't fix it.** Both make the policy better *on `d_expert`*. Neither gives it data about `d_policy`, the off-distribution states it actually visits. You cannot train your way out of covariate shift with the expert's data alone — you need data from the policy's own distribution, which is exactly what DAgger collects.

### 1.1 The compounding-error argument, quantified

The classic result (Ross & Bagnell) makes the compounding precise. Suppose the policy has a per-step error probability `ε` (it takes a wrong action with probability `ε`). For an ordinary supervised problem, the expected number of mistakes over a `T`-step trajectory would be `O(εT)` — linear. But because a mistake puts the policy in an unfamiliar state where it is *more* likely to err again, the actual error grows as:

```
behavior cloning:  expected mistakes ~ O(ε T²)      (quadratic in horizon)
```

The `T²` is the compounding: each mistake doesn't just cost itself, it raises the chance of every *subsequent* mistake. A policy that is 95% right per step (`ε = 0.05`) over a 50-step task does not have a 5% failure rate — the quadratic blow-up means the trajectory-level failure rate is far higher. This is why a "95% accurate" BC policy can fail most of its rollouts: per-step accuracy lies about trajectory-level success when errors compound.

DAgger's guarantee, by contrast, is `O(εT)` — linear — because it trains on the policy's own state distribution, so the policy is no longer *more* likely to err after a mistake. That improvement from `T²` to `T` is the entire reason DAgger exists.

---

## 2. The covariate-shift signature: recognizing it in the wild

You do not need the math to *diagnose* covariate shift — you need to recognize its signature in a rollout. The tell:

> **The policy tracks the expert's demonstrated behavior closely for a while, then — at the first point where it deviates a little — it drifts, and once it drifts it never recovers; and it succeeds *more* when the start state is near a demonstration's start.**

Contrast the three failure modes so you can tell them apart from a rollout, without ever seeing a loss curve:

| Failure | Rollout symptom | Loss curves | Fix |
|---|---|---|---|
| **Underfitting** | Fails *everywhere*, even from demo start states; never tracks the demo | Train + val both high | Bigger net, more epochs, fix the data pipeline |
| **Overfitting** | Tracks demos it memorized, poor on slightly novel *in-distribution* starts | Train low, val high | More data, regularization, early stopping |
| **Covariate shift** | Tracks the demo, then *drifts once it deviates* and never recovers; succeeds near demo starts | Train + val both *low* (healthy!) | DAgger (train on the policy's states) |

The covariate-shift row is the dangerous one *because the loss curves are healthy*. A learner who only watches the loss concludes "the model is fine, the robot is broken." A learner who watches the *rollout* sees the drift-and-flail signature and reaches for DAgger. This is the diagnostic skill of the week, and it is why the mini-project's eval prints *why* each trial failed, not just the success rate.

---

## 3. DAgger: training on the states the policy actually visits

DAgger — **Dataset Aggregation** — is the fix, and it is unromantic. There is no clever loss, no architecture trick. It is a loop that collects the data BC is missing: the states the policy visits, labeled with what the expert would do there.

The algorithm:

1. **Train** an initial policy `π_0` on the expert demonstrations (ordinary BC).
2. **Roll out** the current policy `π_i` in the environment. Record the *states it visits* — crucially, the off-distribution states where it drifts.
3. **Query the expert** for the correct action at *each visited state*. (The expert says "from *this* state — even though I'd never have gotten here — here's what to do.") This is the step that needs the expert *in the loop during training*, which is DAgger's cost.
4. **Aggregate** these new `(visited_state, expert_action)` pairs into the dataset: `D ← D ∪ {new pairs}`.
5. **Retrain** `π_{i+1}` on the aggregated dataset.
6. **Repeat** for a few rounds.

Each round adds data from the policy's *own* state distribution — exactly the off-distribution states BC never saw. After a round or two, the policy has seen "what to do when I've drifted left of the demo," so when it drifts left at deployment, it knows how to recover. The gap between `d_policy` and the training distribution closes, and the `O(εT²)` blow-up collapses toward `O(εT)`.

```python
def dagger_round(policy, train_ds, env, expert, n_rollouts=10):
    """One DAgger round: roll out the policy, query the expert at VISITED states,
    aggregate, return the new pairs to add to the dataset.

    expert(observation) -> the action the expert would take at that observation.
    For the reach task, the 'expert' is your scripted MoveIt2 reach or a human
    relabeling the recorded states.
    """
    new_obs, new_act = [], []
    for _ in range(n_rollouts):
        obs = env.reset()
        done = False
        while not done:
            # The POLICY drives (so we visit the policy's own state distribution)...
            action = deploy_step(policy, train_ds, obs)
            # ...but we record what the EXPERT would have done HERE.
            expert_action = expert(obs)
            new_obs.append(obs)
            new_act.append(expert_action)
            obs, done = env.step(action)
    return np.asarray(new_obs), np.asarray(new_act)


def run_dagger(expert_obs, expert_act, env, expert, rounds=3):
    """Full DAgger: BC, then aggregate the policy's visited states each round."""
    obs, act = expert_obs.copy(), expert_act.copy()
    policy, train_ds, _ = train_bc(obs, act)            # round 0: plain BC
    for i in range(rounds):
        new_obs, new_act = dagger_round(policy, train_ds, env, expert)
        obs = np.concatenate([obs, new_obs])            # AGGREGATE (don't replace)
        act = np.concatenate([act, new_act])
        policy, train_ds, _ = train_bc(obs, act)        # retrain on the union
    return policy, train_ds
```

Two details that matter:

- **Aggregate, don't replace.** The dataset *grows* each round — you keep the original demos *and* add the policy's visited states. Replacing throws away the expert's good behavior; aggregating keeps it and adds the recovery data.
- **The policy drives, the expert labels.** During the rollout, the *policy* chooses the actions (so you visit *its* distribution), but you record what the *expert* would have done at each visited state. This is the inversion that makes DAgger work: you sample states from the policy and labels from the expert.

### 3.1 The β-mixing schedule

Early on, the policy is bad, and letting it drive freely sends the robot into useless flailing states that aren't worth labeling. The original DAgger mixes expert and policy actions with a weight `β_i` that decays over rounds: round 0 executes mostly the *expert's* actions (`β` near 1), later rounds execute mostly the *policy's* (`β` near 0). This keeps early rollouts near the useful part of the state space while still gradually exposing the policy's own distribution. In practice many implementations skip the mixing (`β = 0`, pure policy rollouts) after the first round and it works fine for simple tasks; you implement the schedule as a stretch goal.

---

## 4. The diffusion-of-error problem and why it motivates Weeks 29–30

DAgger fixes covariate shift, but there is a *related* problem it does not fully solve, and naming it now sets up the next two weeks.

A policy that predicts *one action at a time* is vulnerable to **diffusion of error**: even on-distribution, tiny per-step errors accumulate over a long trajectory, and the prediction can also be *jittery* — successive single-step predictions don't commit to a coherent multi-step plan. There are two structural responses, both of which you implement later:

- **Action chunking (ACT, Week 30).** Instead of predicting one action, predict a *chunk* of the next `k` actions at once, and execute them (with temporal ensembling to smooth the boundaries). A committed chunk doesn't drift mid-chunk, and predicting a sequence reduces the compounding. This is the *direct* answer to diffusion of error.
- **Multimodal action models (Diffusion Policy, Week 29).** BC's MSE loss has a subtler flaw: when the expert's demonstrations are *multimodal* (at a fork, some demos go left and some go right), MSE regression averages them and predicts going *straight into the obstacle* — the mean of two good actions is a bad action. A diffusion model predicts a *distribution* over actions, so it can represent "left OR right" instead of collapsing to the average. This fixes a failure BC's loss has even with perfect data and no covariate shift.

You meet both problems this week in miniature — diffusion of error in the long-horizon reach, and the multimodal-averaging problem if your demos approach the block from two sides — and you solve them properly in Weeks 29–30. The lesson: BC + DAgger is the *floor*, not the ceiling. It gets a simple task working and teaches you the failure modes; the heavier methods are better answers to the *same* questions.

---

## 5. Honest evaluation: a success rate is not a vibe

A policy is evaluated by a **success rate** on a **fixed protocol**, not by "it looked good in the demo." The protocol has four parts, all pre-stated:

- **A crisp success predicate.** For the reach: the end-effector reaches within 3 cm of the block center within the time budget, with no safety clamp triggered. Decide this *before* you run, and never relax it to make a number look better.
- **A fixed set of start states.** The same block positions and arm starts for every policy you compare, including positions *not* in the demos (to actually test generalization, not memorization). If BC and BC+DAgger are evaluated on different starts, the comparison is meaningless.
- **Multiple trials / seeds.** A success rate from 3 trials is noise. Run 20 (or more), so 15/20 means something. Report the rate *and* an interval (a binomial confidence interval — 15/20 is `75% ± ~19%` at 95% confidence, which tells you 20 trials is the *minimum*, not a lot).
- **Per-trial failure annotation.** Don't just count failures — *classify* them (drifted-and-flailed = covariate shift; failed-everywhere = underfit; hit-a-clamp = safety). The classification is what turns a number into a diagnosis (Lecture 1 §5, §2 of this lecture).

```python
def evaluate(policy, train_ds, env, success_fn, n_trials=20, seeds=None):
    """A fixed eval protocol: same starts across policies, crisp success predicate,
    per-trial annotation, a success rate to report with an interval."""
    seeds = seeds or list(range(n_trials))
    successes, annotations = 0, []
    for s in seeds:
        obs = env.reset(seed=s)
        traj, done = [obs], False
        while not done:
            action = deploy_step(policy, train_ds, obs)
            obs, done = env.step(action)
            traj.append(obs)
        ok = success_fn(traj)
        successes += int(ok)
        annotations.append("SUCCESS" if ok else classify_failure(traj))
    rate = successes / n_trials
    return rate, annotations    # report rate AND the failure classification
```

This is the protocol the mini-project enforces and the challenge grades. "It looked good" fails the bar; "15/20 on the fixed protocol, the 5 failures were all covariate-shift drift from novel starts" passes it.

---

## 5.5 — The variants of DAgger, and when the expert is expensive

Plain DAgger assumes you can query the expert at *any* state, cheaply, as often as you like. For a scripted expert that is true — you call a function. For a *human* expert it is not: relabeling hundreds of visited states by hand is slow, tedious, and the bottleneck of the whole loop. The field has several responses, and knowing them tells you which to reach for when the expert is the scarce resource.

- **Batch relabeling.** Instead of querying the expert online during the rollout, record the rollout, then replay the visited states to the human afterward and collect labels in a batch. This decouples the (fast) rollout from the (slow) human labeling and lets the human label efficiently in one sitting rather than interrupting every step.
- **HG-DAgger (human-gated).** The human watches the policy roll out and *intervenes* only when the policy is about to do something wrong, providing a correction at exactly those moments. The intervention states are precisely the high-value off-distribution states, so the human's scarce attention goes where it matters most. This is how a lot of real teleop-correction data is collected in 2026.
- **EnsembleDAgger / uncertainty-gated.** Query the expert only at states where the policy is *uncertain* (estimated by an ensemble's disagreement or a learned uncertainty). Confident states don't need a label; uncertain ones do. This minimizes expert queries by spending them only where the policy doesn't already know what to do.

The common thread: plain DAgger's cost is *expert queries*, and every variant is a strategy to spend those queries more efficiently — batch them, gate them on human judgment, or gate them on policy uncertainty. For this week's scripted-expert reach task, plain DAgger is fine (the expert is free). The variants matter the moment your expert is a human, which is the moment DAgger goes from "a function call per state" to "a person's afternoon per round" — and that cost is exactly why the field invented them.

A related honesty: DAgger needs an *interactive* expert, one you can query at arbitrary states. Sometimes you only have a *fixed dataset* of expert demonstrations and no way to ask the expert about new states (the expert is gone, or it's a logged dataset). DAgger does not apply there — you cannot collect labels at the policy's visited states because there is no expert to ask. That regime (offline imitation from a fixed dataset) is its own subfield, and it is part of why Diffusion Policy and ACT matter: they squeeze more out of a *fixed* demonstration set than BC does, without needing the interactive expert DAgger requires. Knowing whether your expert is interactive or fixed decides whether DAgger is even an option.

## 6. Safety around a learned policy

A behavior-cloned policy can output garbage — an enormous joint jump from an out-of-distribution observation is exactly the kind of thing covariate shift produces. So the Week-24 leash is not optional around a learned policy; it is mandatory:

- **Clamp the policy's output.** The velocity/workspace clamp from Week 24 wraps the policy: an action exceeding the velocity, acceleration, or workspace bounds is *rejected* before it reaches the arm. A drifting policy that commands a wild joint jump gets clamped to a safe value, not executed.
- **Fall back after repeated rejections.** When the policy's action is clamped `N` times in a row (the spec's number is three), hand control to a classical controller — the Week-25 grasp planner or a scripted reach. This is the Week-32 "learned policy + classical fallback" pattern, and it is *why* you built the analytic grasp planner in Week 25: it is the fallback for exactly this.
- **The E-stop still works.** The 200 ms E-stop from Week 24 cancels the policy's motion the same way it cancels Nav2's. A learned policy is just another motion source the leash governs.

The principle, which the capstone codifies as "ship the learned policy with a leash": *a learned policy's output is a suggestion, and the safety layer decides whether to honor it.* The moment a policy drives an actuator near a person without a clamp and a fallback, you have a learned-policy hazard with no mitigation — a hazard-log row (Week 24) with an empty owner, which is a finding the safety review catches.

---

## 6.5 — A worked walkthrough of the whole loop on the reach task

Tie it together with the concrete sequence you run in the exercises and the mini-project, so the abstractions land on a real task.

1. **Collect.** Teleop 50 reaches from varied starts. Inspect: the start states spread across the workspace; the (obs, act) pairs are aligned. You have a dataset that *covers* the common starts but, inevitably, not every state the policy will reach.
2. **Train BC.** The MLP trains; train and val MSE both drop to ~0.01 and val early-stops. The loss curves are textbook-healthy. A naive engineer declares victory here.
3. **Evaluate honestly.** On the fixed protocol (20 trials, novel starts included), BC succeeds ~55%. The per-trial annotation shows the failures are *track-then-drift*: the policy heads toward the block, deviates slightly, and once off the demo manifold it wanders. The healthy loss curves did not predict this, because they were computed on the expert's states.
4. **Diagnose.** This is the covariate-shift signature (§2). Not underfitting (it tracks the demos, doesn't fail everywhere), not overfitting (val loss is low). The policy is being tested on its own drifting distribution, which BC's data never covered.
5. **DAgger, round 1.** Roll out the policy (it drifts — good, that's the data we need). At every visited state, query the expert ("from *here*, reach toward the block like so"). Aggregate these recovery examples into the dataset, which grows from ~1180 to ~2050 pairs. Retrain.
6. **Re-evaluate.** On the *same* protocol, success jumps to ~85%. The trials that drifted now recover, because the dataset now contains "what to do when I've drifted," labeled by the expert. The covariate-shift gap has narrowed.
7. **Repeat if needed.** Round 2 → ~95%, then it plateaus: the policy no longer drifts into novel states, so new rollouts visit states already in the data and the expert's labels stop adding information.
8. **Ship it leashed.** Wrap the final policy in the velocity/workspace clamp and the classical fallback (§6). Deploy the *wrapped* policy.

That eight-step loop — collect, train, evaluate honestly, diagnose, DAgger, re-evaluate, repeat, leash — is the imitation-learning workflow in miniature, and it is exactly what the `crunch_il` mini-project automates into a one-command pipeline. Every heavier method in Weeks 29–31 plugs into the same loop; only the policy class (diffusion model, transformer, VLA) changes. The loop is the skill; the architecture is the variable.

## 6.6 — Why imitation, and not just reinforcement learning?

A reasonable question after meeting covariate shift: if imitation is this fragile, why not skip it for reinforcement learning (Week 28), which learns from a reward and explores its own states? The honest comparison, because choosing the right learning paradigm is a senior decision:

- **Imitation needs demonstrations; RL needs a reward function.** A demonstration is often *easy* to provide (drive the arm to the block by hand) where a reward is *hard* to specify (what numeric reward captures "a good reach"? reward-shaping is a craft, and a misspecified reward gets gamed — the reward-hacking problem of Week 28). When demonstrations are available, imitation sidesteps the entire reward-design problem.
- **Imitation is sample-efficient; RL is sample-hungry.** BC learns from 50 demos in minutes on a CPU. RL often needs millions of environment steps and a fast simulator (Week 28's whole premise is "RL works on robots when the simulator is fast"). For a task you can demonstrate, imitation gets you a working policy far faster.
- **Imitation is bounded by the expert; RL can exceed it.** A behavior-cloned policy can, at best, match the demonstrations — it cannot discover a *better* strategy than the expert showed. RL, optimizing a reward, can find solutions no human demonstrated. When the goal is to *exceed* human performance (a faster gait, a cleverer manipulation), RL has the ceiling imitation lacks.
- **They combine.** The strongest robot-learning recipes in 2026 are *not* pure imitation or pure RL — they bootstrap with imitation (get a reasonable policy cheaply from demos) and refine with RL (improve it past the expert via reward). Imitation gives RL a good starting point so it doesn't have to explore from scratch; RL gives imitation a way past the expert's ceiling. This week's BC+DAgger is the imitation half of that recipe.

The decision rule: **if you can demonstrate the task and don't need to exceed the demonstrator, imitate; if you can specify a reward and need to discover or exceed, reinforce; if you can do both, bootstrap with imitation and refine with RL.** Imitation learning is the gentle on-ramp not because it is a toy, but because demonstrations are the cheapest, most available form of supervision for most robot tasks — and the failure mode you learned this week (covariate shift) is the price of that cheapness, and DAgger is how you pay it.

## 6.9 — Quick reference: covariate shift and DAgger

**Q: Why is a policy not an ordinary supervised model?**
It acts, and acting changes the distribution of states it sees — trained on `d_expert`, tested on `d_policy`.

**Q: What is covariate shift?**
The gap between the states the data covered and the states the policy visits; a distributional failure, not an optimization one.

**Q: Can more epochs or a bigger network fix it?**
No — both improve performance on `d_expert`; neither adds data about `d_policy`.

**Q: BC's error growth vs. DAgger's?**
BC: `O(εT²)` (compounding). DAgger: `O(εT)` (linear).

**Q: The covariate-shift rollout signature?**
Tracks the demo, drifts once it deviates, never recovers; succeeds near demo starts.

**Q: How does it differ from underfit/overfit in a rollout?**
Underfit fails everywhere; overfit fails on novel in-distribution starts; covariate shift tracks-then-drifts with healthy loss.

**Q: In a DAgger rollout, who acts and who labels?**
The policy acts (visit its states); the expert labels (correct action at each visited state).

**Q: Aggregate or replace each round?**
Aggregate — grow the dataset; replacing throws away the expert's good behavior.

**Q: What is the β schedule?**
The expert/policy mixing weight, decaying over rounds; early rounds lean on the expert.

**Q: When does DAgger not apply?**
When the expert is not interactive (a fixed dataset, no way to query at new states) — the offline regime.

**Q: What is the diffusion-of-error problem?**
Per-step errors accumulating over a trajectory; motivates action chunking (ACT).

**Q: Why does MSE fail on multimodal demos?**
It averages "go left" and "go right" into "go straight" — a non-solution; Diffusion Policy fixes it with a distribution.

**Q: What makes an eval honest?**
Pre-stated predicate, fixed starts (incl. novel), ≥ 20 seeds, a rate with an interval, per-trial classification.

**Q: Imitation or RL?**
Imitate if you can demonstrate and need not exceed the expert; reinforce if you can reward and must discover/exceed; bootstrap-then-refine if both.

## 7. Recap

You should now be able to:

- Explain covariate shift: a policy changes its own state distribution by acting, so it is tested on `d_policy` while trained on `d_expert`, and the gap is where BC fails — a distributional problem, not an optimization one.
- Reproduce the compounding-error argument: BC's `O(εT²)` vs. DAgger's `O(εT)`, and why a 95%-per-step policy can still fail most rollouts.
- Recognize the covariate-shift signature in a rollout (track-then-drift, succeeds near demo starts) and distinguish it from underfitting and overfitting *without* looking at a loss curve.
- Implement one round of DAgger: roll out the policy, query the expert at the *visited* states, aggregate (don't replace), retrain — and the β-mixing schedule.
- Name the diffusion-of-error and multimodal-averaging problems and how action chunking (ACT) and diffusion models (Diffusion Policy) answer them in Weeks 29–30.
- Evaluate a policy honestly: a crisp success predicate, a fixed set of start states (including novel ones), multiple seeds, a rate with an interval, and per-trial failure classification.
- Wrap a learned policy in the Week-24 leash: clamp the output, fall back after repeated rejections, and keep the E-stop live.

## 6.7 — Confidence intervals on a success rate: the arithmetic you owe the reader

"15/20" is not a number a reader can trust without its uncertainty, and the uncertainty on a small-sample success rate is *large* — large enough that two rates that look different may be statistically indistinguishable. You owe the reader the interval, and computing it is simple arithmetic.

A success rate is a proportion `p̂ = successes / trials` estimated from `n` Bernoulli trials. The standard 95% interval (normal approximation) is:

```
p̂ ± 1.96 * sqrt( p̂ (1 - p̂) / n )
```

For 15/20: `p̂ = 0.75`, `sqrt(0.75 × 0.25 / 20) ≈ 0.097`, so the interval is `0.75 ± 0.19` — roughly **56% to 94%**. That width is the lesson: with 20 trials, "75%" really means "somewhere between 56% and 94%, probably." So when BC scores 12/20 (60%, interval ~39–81%) and DAgger scores 15/20 (75%, interval ~56–94%), the intervals *overlap heavily* — the difference might be noise. The honest move is to *say so* and run more trials.

A few practical notes:

- **The normal approximation is poor near 0 or 1 and for tiny `n`.** When `p̂` is near 0% or 100%, or `n` is very small, use the Wilson interval or a binomial exact interval (`scipy.stats.binomtest(...).proportion_ci()`), which behave correctly at the extremes. The normal approximation is fine in the middle range with `n ≥ 20`.
- **To distinguish two policies, the trial count must beat the effect size.** If you expect a 15-point improvement, 20 trials each is borderline; 50–100 each makes a 15-point gap clearly significant. The rule of thumb: smaller true differences need more trials to detect.
- **Report the interval, not just the point.** "DAgger: 75% (95% CI 56–94%, n=20)" is honest; "DAgger: 75%" invites the reader to over-trust a noisy estimate.

This arithmetic is why the mini-project and the challenge require *intervals*, not bare rates. A robot-learning result without an interval is a result you cannot tell from noise — and a confident claim built on an indistinguishable difference is exactly the kind of result that fails to reproduce. The engineer who reports "+15 points, but the 20-trial intervals overlap, so I ran 60 and it's now clearly +18 ± 9" is the one whose numbers other people can build on.

## 6.8 — The honest failure: when imitation is the wrong tool

A final piece of senior judgment: sometimes the right answer is "imitation won't solve this," and recognizing it early saves weeks. Imitation struggles when:

- **You cannot demonstrate the task.** If a human can't teleoperate it (too fast, too precise, too many degrees of freedom to coordinate), there are no demonstrations to clone. RL or a different approach is needed.
- **The task requires exceeding the demonstrator.** BC is bounded by the expert (§6.6). If the goal is superhuman speed or precision, imitation alone caps out below it.
- **The demonstrations are wildly inconsistent.** If ten humans solve the task ten incompatible ways with no shared structure, even Diffusion Policy's multimodal modeling struggles, and the dataset is teaching contradictions.
- **The deployment distribution is fundamentally different from any achievable demonstration.** If the robot will face situations no demonstration can cover and no expert can be queried about (the offline regime, §5.5), DAgger doesn't apply and BC's covariate shift is unbounded.

Recognizing these early is the difference between a week well spent and a week spent forcing imitation onto a problem it can't solve. The honest engineer asks, before collecting 50 demos: *can I demonstrate this, do I need to exceed the demonstrator, and will I be able to query the expert at the policy's visited states?* If yes/no/yes, imitation with DAgger is the right tool and this week's pipeline solves it. If not, the answer is RL (Week 28), a generalist policy (Week 31), or a rethink — and knowing that *before* the data-collection grind is worth more than any training trick.

Next: the exercises collect demos, train the BC policy, watch it drift, and fix it with DAgger; the mini-project builds the whole pipeline with an honest eval and a safety wrapper. Continue to [the exercises](../exercises/README.md).

---

## 6.10 — One more diagnostic: the state-visitation overlay

The single most convincing piece of evidence for covariate shift — and for DAgger fixing it — is the state-visitation overlay, so it is worth describing precisely because you produce it in the challenge and the mini-project.

- Collect the *observations* from the expert demonstrations (the states the data covered).
- Collect the *observations* the BC policy actually visits during evaluation rollouts (the states it reaches).
- Collect the *observations* the DAgger policy visits.
- Project all three sets to 2D with PCA or t-SNE and plot them on the same axes, color-coded.

What you see — and what makes the argument unanswerable — is three distinct things on one plot:

- The **demo states** form a manifold — a connected region of state space that the data covered.
- The **BC rollout states** *leave* that manifold — the policy drifts into uncovered space, exactly where it has no training signal.
- The **DAgger rollout states** *stay on* the manifold — because DAgger added the previously-uncovered states to the training data, so the policy learned to recover toward the manifold.

The picture *is* the explanation: covariate shift is "the rollout wanders off the data," and the fix is "add the wandered-into states to the data." A reviewer who sees this overlay does not need the `O(εT²)` math — the geometry of the wandering is the whole story, and it is why the challenge requires the plot, not just the success rates.

## References

- *DAgger — Ross, Gordon, Bagnell (2011)* (covariate shift, the `O(εT²)` vs `O(εT)` argument): <https://arxiv.org/abs/1011.0686>
- *Efficient Reductions for Imitation Learning — Ross & Bagnell (2010)*: <https://proceedings.mlr.press/v9/ross10a.html>
- *CS285 — Imitation Learning lecture (Levine)*: <https://rail.eecs.berkeley.edu/deeprlcourse/>
- *ACT — Zhao et al. (2023)* (action chunking, the diffusion-of-error answer): <https://tonyzhaozh.github.io/aloha/>
- *Diffusion Policy — Chi et al. (2023)* (the multimodal-action answer): <https://diffusion-policy.cs.columbia.edu/>
