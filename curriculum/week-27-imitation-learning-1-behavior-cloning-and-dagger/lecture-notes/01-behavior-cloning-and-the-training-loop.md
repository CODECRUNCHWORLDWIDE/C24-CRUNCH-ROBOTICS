# Lecture 1 — Behavior Cloning: Imitation as Supervised Learning, and the Training Loop That Does It Right

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can collect a demonstration dataset, define a PyTorch behavior-cloning policy, write a correct training loop with normalization and a validation split, and read the loss curves that tell you whether you have a model worth deploying — or one that will drift the moment it leaves the data.

If you remember one sentence from this lecture, remember this one:

> **Behavior cloning is supervised learning applied to control: collect (observation, action) pairs from an expert, and train a network to predict the expert's action from the observation. It is the simplest way to make a robot learn a task — and its simplicity hides the structural flaw you will spend the rest of the week fixing.**

You spent Phase 3 *programming* the robot: a planner computed a path, a controller tracked it, a behavior tree sequenced them. This week the robot learns a task from *demonstrations*. That shift — from programmed to shown — is the entire premise of learned policies, and behavior cloning is the gentlest version of it: no reward function (that's reinforcement learning, Week 28), no exploration, just "here is what the expert did; do that."

---

## 1. Imitation as supervised learning

A **policy** is a function `π` from an observation to an action: `a = π(o)`. For the reach task, the observation might be the arm's joint angles plus the red block's position, and the action might be the next joint command (or an end-effector delta). Behavior cloning trains `π` to imitate an expert by treating the demonstrations as a labeled dataset:

- **Input (`o`):** the observation at time `t`.
- **Label (`a`):** the action the expert took at time `t`.

That is *exactly* a supervised learning problem. The demonstrations are `(o, a)` pairs; the policy is a regression model (for continuous actions) or a classifier (for discrete ones); the loss measures how far the policy's predicted action is from the expert's. Train it like any supervised model, and you have a behavior-cloned policy.

This framing is the strength and the trap. The strength: you get to use all of supervised learning — PyTorch, MSE loss, Adam, dropout, the works. The trap: supervised learning assumes the training and test data come from the *same distribution*, and a policy *violates that assumption by acting* (Lecture 2). For now, hold that thought; build the BC pipeline first, because you cannot understand why it fails until you have made it work.

---

## 2. Collecting demonstrations

A policy is only as good as its data, and for BC the data is demonstrations. There are two ways to get them.

**Teleoperation.** A human drives the robot through the task — keyboard, gamepad, a VR controller, or a leader arm — while you record the observations and the human's actions. This is how most real robot-learning datasets are collected (the ALOHA and LeRobot datasets are teleop). It captures *human* solutions, including the subtle corrections a scripted policy wouldn't make.

**Scripted demonstrations.** A hand-written controller (your Week-23 MoveIt2 reach, or the Week-25 grasp planner) performs the task, and you record *its* observations and actions. Cleaner and faster than teleop, but it only ever shows the scripted solution — no human nuance, no recovery behaviors.

For this week's "reach for the red block" you collect ~50 teleop demonstrations. Why 50? It is enough to cover the common start states for a simple reach and small enough to collect in an hour — a *starting point*, not a law. The right number is "enough to cover the states the policy will visit," which is precisely the quantity covariate shift makes hard to know in advance (and DAgger turns into an iterative process).

### 2.1 What to record

Record, synchronized, at each timestep:

- **The observation.** For the reach task: the arm joint angles (`sensor_msgs/JointState`) and the block's pose (sim ground truth, or a detection from your Week-13 detector). Keep it small and informative.
- **The action.** The command the expert issued: the *next* joint position, or the end-effector velocity/delta. Be precise about whether the action is absolute (the target) or relative (the delta) — the policy must predict the same thing it will later execute.

Synchronization matters, and it is the Week 5 stamping lesson again: pair each observation with the action taken *at that observation*, using honest timestamps, not "whatever was latest when I got around to logging." A misaligned (o, a) pair teaches the policy to predict the action for the *wrong* state — a silent data bug that looks like a modeling problem.

```python
# Recording a demo (sketch): pair each observation with the expert's action.
# Record with ros2 bag during teleop, or log directly:
demo = []   # list of (observation_vector, action_vector)

def on_step(joint_state, block_pose, expert_action):
    obs = np.concatenate([joint_state.position,            # arm joints
                          [block_pose.position.x,
                           block_pose.position.y,
                           block_pose.position.z]])         # block xyz
    act = np.asarray(expert_action)                         # next joint cmd / delta
    demo.append((obs, act))                                 # paired at the SAME t
```

### 2.2 Inspecting the dataset before you train

Before training, look at the data — the single most skipped step and the source of most "my policy is broken" hours. Plot the action distribution (are the actions reasonable? is one joint always zero?), check for misaligned pairs (does the action at time `t` plausibly follow from the observation at `t`?), and check coverage (do the demos start from a *variety* of states, or always the same one?). A dataset that always starts from the same arm pose teaches a policy that only works from that pose — covariate shift baked in at collection time. Exercise 1 is exactly this inspection.

---

## 3. The behavior-cloning policy in PyTorch

For a reach task with a low-dimensional observation, an MLP policy is enough. Here is the network and the dataset:

```python
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class BCPolicy(nn.Module):
    """Maps an observation vector to an action vector. A small MLP is plenty for
    a low-dimensional reach task; you scale up (CNN/transformer) for image obs."""

    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, act_dim),
        )

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.net(obs)


class DemoDataset(Dataset):
    """Wraps (observation, action) pairs. Normalization is applied in __init__ so
    the network sees zero-mean, unit-variance inputs (and you store the stats to
    un-normalize the predicted action at deployment)."""

    def __init__(self, obs: np.ndarray, act: np.ndarray) -> None:
        self.obs_mean, self.obs_std = obs.mean(0), obs.std(0) + 1e-6
        self.act_mean, self.act_std = act.mean(0), act.std(0) + 1e-6
        self.obs = (obs - self.obs_mean) / self.obs_std
        self.act = (act - self.act_mean) / self.act_std

    def __len__(self) -> int:
        return len(self.obs)

    def __getitem__(self, i: int):
        return (torch.tensor(self.obs[i], dtype=torch.float32),
                torch.tensor(self.act[i], dtype=torch.float32))
```

Two design points that beginners get wrong:

- **Normalize the observations *and* the actions.** A raw observation might mix joint angles (radians, ±3) with positions (meters, ±1); a raw action might span very different scales per dimension. Without normalization the loss is dominated by the largest-scale dimension and the network ignores the rest. Store the normalization stats (mean, std) — you need them to un-normalize the policy's predicted action when you deploy it.
- **Choose the loss for the action type.** Continuous actions (joint targets, velocities) → **MSE** (`nn.MSELoss`). Discrete actions (a small set of moves) → **cross-entropy** (`nn.CrossEntropyLoss`). The reach task's joint commands are continuous, so MSE — but know that MSE has a hidden flaw (§5, the multimodal problem) that motivates Week 29.

---

## 4. The training loop, done right

The loop is the standard supervised loop, with the disciplines that separate a policy worth deploying from one that overfits or underfits silently:

```python
def train_bc(obs: np.ndarray, act: np.ndarray, epochs: int = 200,
             batch: int = 64, lr: float = 1e-3, val_frac: float = 0.2):
    """Train a BC policy with a held-out validation split and early stopping."""
    n = len(obs)
    idx = np.random.default_rng(0).permutation(n)
    n_val = int(val_frac * n)
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    # Fit normalization on TRAIN only; apply to both (no val leakage).
    train_ds = DemoDataset(obs[train_idx], act[train_idx])
    val_obs = (obs[val_idx] - train_ds.obs_mean) / train_ds.obs_std
    val_act = (act[val_idx] - train_ds.act_mean) / train_ds.act_std

    loader = DataLoader(train_ds, batch_size=batch, shuffle=True)
    model = BCPolicy(obs.shape[1], act.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    val_o = torch.tensor(val_obs, dtype=torch.float32)
    val_a = torch.tensor(val_act, dtype=torch.float32)

    best_val, best_state, patience, since = float("inf"), None, 20, 0
    history = []
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for xb, yb in loader:
            opt.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            opt.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_ds)

        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(val_o), val_a).item()
        history.append((train_loss, val_loss))

        if val_loss < best_val:        # early stopping on validation loss
            best_val, best_state, since = val_loss, model.state_dict(), 0
        else:
            since += 1
            if since >= patience:
                break

    model.load_state_dict(best_state)
    return model, train_ds, history     # return the norm stats with the model
```

The disciplines that matter:

- **Hold out a validation split, and fit normalization on train only.** Normalizing on the full dataset leaks val statistics into training. Fit `mean`/`std` on the training split, apply them to val.
- **Early-stop on validation loss.** Train loss always decreases; val loss tells you when the model stops generalizing. Stop when val loss stops improving (patience).
- **Return the normalization stats with the model.** At deployment you normalize the live observation with the *training* stats and un-normalize the predicted action. Forgetting this is a classic "trained great, deploys garbage" bug — the policy is fed unnormalized inputs it never saw.

---

## 5. Reading the loss curves: underfit, overfit, and what BC's curves can't tell you

The train/val loss curves diagnose two of the three things that can go wrong — and crucially, *not* the third, which is the whole point of this week.

- **Underfitting:** both train and val loss are high and flat. The model isn't capturing the demos at all — too small, too few epochs, a bug in the loss or the data. Symptom in deployment: the policy fails *everywhere*, even from demo start states. Fix: bigger network, more epochs, check the data pipeline.
- **Overfitting:** train loss low, val loss high and rising. The model memorized the training pairs but doesn't generalize even *within* the demo distribution. Fix: more data, regularization (dropout, weight decay), early stopping.
- **The thing the curves *cannot* show:** a policy can have *low train loss and low val loss* — a textbook-healthy supervised model — and still fail catastrophically in deployment. Why? Because train and val are both drawn from the *expert's* state distribution, and the policy at deployment visits its *own* state distribution, which drifts away the moment it errs. **Covariate shift is invisible to the loss curves**, because the loss is computed on the wrong distribution. This is the single most important thing to understand about BC, and it is why a healthy-looking BC policy can still drift-and-flail. Lecture 2 is entirely about this.

> **The lesson:** good loss curves are *necessary but not sufficient*. They rule out underfitting and overfitting. They say *nothing* about covariate shift, because they are evaluated on the expert's states, not the policy's. A BC policy that "looks great in training" and "flails in deployment" is not a contradiction — it is the expected outcome, and DAgger is the fix.

---

## 6. Deploying the policy: the inference loop and the safety leash

Deployment is a loop: read the observation, normalize it with the training stats, run the policy, un-normalize the action, clamp it, execute it, repeat.

```python
def deploy_step(model, train_ds, observation: np.ndarray) -> np.ndarray:
    """One policy step at deployment. Normalize with TRAINING stats, predict,
    un-normalize, and (in the full loop) clamp before executing."""
    obs_n = (observation - train_ds.obs_mean) / train_ds.obs_std
    with torch.no_grad():
        act_n = model(torch.tensor(obs_n, dtype=torch.float32)).numpy()
    action = act_n * train_ds.act_std + train_ds.act_mean    # un-normalize
    return action
```

Three deployment disciplines:

- **Use the training normalization stats.** Not the deployment data's — the policy was trained on training-normalized inputs and must see the same transform.
- **Clamp the action.** A learned policy can output garbage — an enormous joint jump, a velocity past the limit. The Week-24 velocity/workspace clamp wraps the policy's output: an out-of-bounds action is rejected before it reaches the arm. *A learned policy ships with a leash, always.* This is not optional; a network's output near a person is exactly the thing the safety wrapper exists to clamp.
- **Have a fallback.** When the policy's action is rejected (clamped) repeatedly, fall back to a classical controller — the Week-25 grasp planner or a scripted reach. The Week-32 "learned policy + classical fallback" pattern starts here.

---

## 7. A worked example: the reach-task observation and action

To make it concrete, here is the full spec for this week's task, so you build the dataset right.

**Observation (`obs_dim = 9`):** 6 arm joint angles + the block's (x, y, z) in the arm's base frame. Nine numbers, stamped at acquisition time. (If you use an image observation instead, the MLP becomes a small CNN — but start with the low-dimensional version; it trains in minutes on a CPU and isolates the imitation-learning lesson from the perception lesson.)

**Action (`act_dim = 6`):** the *next* target joint angles (absolute), or the joint *deltas* (relative). Pick one and be consistent — the policy predicts what it will execute. Absolute targets are simpler to deploy (set the joint target); deltas often generalize better but compound error faster (a small delta error accumulates over the trajectory — foreshadowing §5 of Lecture 2).

**Success predicate:** the gripper's end-effector reaches within, say, 3 cm of the block's center within a time budget. Crisp, measurable, pre-stated — the basis for the honest evaluation in Lecture 2.

With this spec, the dataset is `N` rows of `(9-vector obs, 6-vector act)`, the policy is `BCPolicy(obs_dim=9, act_dim=6)`, and the training loop above trains it. Exercise 2 is exactly this.

### 7.1 — How much data, and the data-quality-over-quantity rule

"How many demonstrations?" is the question every new robot-learning engineer asks, and the honest answer is "enough to cover the states the policy will visit" — which, as covariate shift (Lecture 2) makes clear, you cannot know in advance. But there are useful rules of thumb:

- **Fifty is a reasonable starting point for a simple reach,** not because 50 is magic but because it is enough to cover the common start states and small enough to collect in an hour. Scale up for harder tasks.
- **Coverage beats count.** Fifty demonstrations from *varied* start states teach far more than five hundred from the *same* start. A policy can only be confident where it has seen data; clustered demos produce a policy confident in one spot and lost everywhere else — covariate shift baked in at collection time (§2.2). This is why Exercise 1 makes you *plot the start-state coverage* before training.
- **Quality beats quantity.** A demonstration with a mistake-and-recovery in it (the expert drifts, then corrects) teaches the policy *how to recover* — a poor-man's DAgger at collection time. Clean, perfect demos teach only the perfect path and leave the policy helpless when it deviates. Counterintuitively, slightly imperfect demonstrations can produce a *more robust* policy than flawless ones.
- **Diminishing returns set in.** The hundredth demo from a region you have already covered adds almost nothing. The marginal value of a demo is highest in regions you have *not* covered — which is the exact insight DAgger automates by collecting data from the policy's own visited (uncovered) states.

The practical workflow: collect ~50 varied demos, train, *look at where the policy fails*, and either collect targeted demos in the failure regions or run DAgger (which does this targeting automatically). "Collect more data" is rarely the answer; "collect data *where the policy is failing*" almost always is. That distinction — targeted coverage over raw count — is the difference between a data-collection strategy and a data-collection grind.

---

## 7.5 — Observation and action representation choices that decide everything

Two design decisions, made before you write a line of training code, shape the policy more than the network architecture does. Get them wrong and no amount of training fixes it; get them right and a tiny MLP works.

**State observation vs. image observation.** The reach task above uses a *state* observation — joint angles plus the block's pose, nine numbers. This is the right starting point because it isolates the imitation-learning lesson (covariate shift, DAgger) from the perception lesson (extracting state from pixels). But real robot policies often take an *image* observation, because the block's pose is itself the output of a perception system that can be wrong, and an end-to-end image policy sidesteps that. The cost is data: an image policy needs a CNN (or a pretrained visual encoder), far more demonstrations, and a GPU. The honest progression — and the one this track follows — is *state first* (this week), *images later* (Diffusion Policy and ACT in Weeks 29–30 take image observations). Starting with state observations is not a simplification you'll regret; it is the controlled experiment that lets you attribute a failure to imitation rather than perception.

**Absolute action vs. relative (delta) action.** The action can be the *absolute* target (the next joint angles) or a *relative* delta (how much to change each joint). The choice has real consequences:

- **Absolute targets** are simpler to deploy (set the joint target and let the low-level controller go there) and don't accumulate error — each prediction is independent of the last. But they tie the policy to absolute positions, so it generalizes poorly if the task shifts in space.
- **Relative deltas** often generalize better (the policy learns "move toward the block," which transfers across block positions) but they *compound error*: a small systematic delta bias accumulates over the trajectory, and the policy can drift even on-distribution. This is a preview of the diffusion-of-error problem (Lecture 2 §4).

Pick one, be consistent between training and deployment (the policy must predict the same thing it executes), and write it down. A policy trained on deltas but deployed as if predicting absolutes is a silent representation bug that looks like a broken policy. For this week's reach, absolute joint targets are the simpler, recommended choice; deltas are a stretch-goal comparison.

**The frame the action lives in.** If the action is an end-effector delta, *which frame* — the base frame, the tool frame, the camera frame? An end-effector "move 1 cm forward" means something different in each. This is the Week-2 / Week-5 frame discipline applied to a learned action: the policy's output is a vector in *some* frame, and that frame must be the same at training and deployment, or the arm moves in a consistently-rotated wrong direction. A frame-confused action policy fails the same way a frame-confused grasp does (Week 25 §1.1) — confidently, in the wrong direction.

## 8.7 — Quick reference: behavior cloning

**Q: What is behavior cloning?**
Supervised learning on (observation, action) pairs: predict the expert's action from the observation.

**Q: Teleop vs. scripted demos?**
Teleop captures human nuance and recovery; scripted is cleaner and faster but shows only the scripted solution.

**Q: What must be true of an (obs, act) pair?**
Aligned at the same timestep — the action is what the expert did at that observation, not the next step's.

**Q: Why normalize, and fit on which split?**
Mixed scales let one dimension dominate MSE; fit on train only (no val leakage); store stats to un-normalize at deploy.

**Q: Which loss for continuous vs. discrete actions?**
MSE for continuous (joint targets, velocities); cross-entropy for discrete.

**Q: What do you early-stop on?**
Validation loss — train loss always falls; val tells you when generalization stops.

**Q: What three things can the loss curves diagnose?**
Underfit (both high), overfit (train low, val high), and... not covariate shift — that is invisible to the loss.

**Q: Absolute vs. relative actions?**
Absolute: simpler to deploy, no accumulation. Relative: generalizes better, but compounds error. Be consistent train↔deploy.

**Q: Why does a learned policy deploy with a clamp and fallback?**
It can output garbage; clamp rejects out-of-bounds actions, fallback takes over after repeated rejections.

**Q: State observation or image?**
Start with state (isolates the IL lesson from perception); images come with Diffusion Policy and ACT.

**Q: How much data?**
Enough to cover the visited states — coverage and quality beat raw count; targeted beats more.

**Q: First thing to check when a BC policy misbehaves?**
The mundane bugs (alignment, normalization, action representation) before concluding "covariate shift."

## 8. Recap

You should now be able to:

- Frame imitation as supervised learning: demonstrations are `(o, a)` pairs, the policy is a regression model, the loss measures action error.
- Collect demonstrations by teleop or scripting, record synchronized and honestly-timestamped `(o, a)` pairs, and *inspect* the dataset before training.
- Define a PyTorch MLP behavior-cloning policy and a `Dataset` that normalizes observations and actions.
- Write a correct training loop: train/val split, normalization fit on train only, MSE (or cross-entropy) loss, early stopping on val, and the normalization stats returned with the model.
- Read the loss curves to rule out underfitting and overfitting — and understand that they *cannot* reveal covariate shift, because they are evaluated on the expert's states, not the policy's.
- Deploy the policy with the training normalization, a safety clamp, and a fallback.
- Choose observation and action representations (state-first, absolute-vs-delta, the action's frame) and keep them consistent train↔deploy.
- Debug a misbehaving policy by ruling out the mundane bugs before reaching for the covariate-shift diagnosis.

## 8.5 — Debugging a BC policy: a checklist before you blame the method

When a BC policy misbehaves, work this checklist *before* concluding "BC doesn't work" — most failures are mundane bugs, not the deep covariate-shift problem:

- **Is the data aligned?** Off-by-one (obs, act) pairing teaches the wrong mapping (§2.1). Eyeball a few pairs: does the action plausibly follow from the observation?
- **Is normalization applied consistently?** Trained on normalized inputs but deployed on raw ones (or with deployment-data stats instead of training stats) is the classic "trained great, deploys garbage" bug. The policy must see the same transform at train and deploy.
- **Does the action representation match?** Trained on deltas but deployed as absolutes (or a frame mismatch on an end-effector action) makes the arm move consistently wrong (§7.5). The policy must predict what it executes.
- **Are the loss curves healthy?** If train loss is high → underfit (bigger net, more epochs). If val rises while train falls → overfit (more data, regularization, early stopping). If both are low → the model is fine on the expert's data; the failure is *downstream* of training.
- **Does it fail everywhere or only after deviating?** Fails everywhere (even from demo starts) → underfit or a deploy bug. Tracks-then-drifts, succeeds near demo starts → covariate shift (Lecture 2), and *only now* is BC's structural flaw the answer.

The order matters: the first four are bugs you fix, and they masquerade as the fifth. A learner who jumps to "covariate shift!" on the first failure often has an alignment or normalization bug instead, and DAgger won't fix a normalization bug. Rule out the mundane causes, *then* diagnose covariate shift — and when the policy has healthy loss curves and the track-then-drift signature, you have genuinely earned the covariate-shift diagnosis and DAgger is the right tool. This checklist is the difference between "BC is broken" (usually false) and "this BC policy has a normalization bug" or "this BC policy has covariate shift" (usually one of these, and they have different fixes).

Next up: *why* a healthy-looking BC policy still fails — covariate shift and the compounding-error argument — and the fix the field actually uses, DAgger. Continue to [Lecture 2 — Covariate Shift and DAgger](./02-covariate-shift-and-dagger.md).

---

## References

- *DAgger — Ross, Gordon, Bagnell (2011)*: <https://arxiv.org/abs/1011.0686>
- *CS285 — Imitation Learning lecture (Levine)*: <https://rail.eecs.berkeley.edu/deeprlcourse/>
- *ALVINN — Pomerleau (1988)*, the original behavior-cloning robot: <https://proceedings.neurips.cc/paper/1988/hash/812b4ba287f5ee0bc9d43bbf5bbe87fb-Abstract.html>
- *PyTorch — Datasets & DataLoaders*: <https://pytorch.org/tutorials/beginner/basics/data_tutorial.html>
- *LeRobot (BC reference implementation + dataset format)*: <https://github.com/huggingface/lerobot>
