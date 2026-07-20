# Week 27 — Imitation Learning 1: Behavior Cloning and DAgger

Welcome to the week your robot stops being *programmed* to do a task and starts being *shown* how. By Friday you will have collected fifty teleoperated demonstrations of a "reach for the red block" task, trained a small PyTorch policy to clone them, watched it fail in a very specific and instructive way, and fixed that failure with one round of DAgger. You will understand, in your bones, the single most important fact about imitation learning: **behavior cloning fails because the policy visits states the training data never showed it, and DAgger fixes that by asking the expert what to do in exactly those states.**

We assume you finished Week 23 (MoveIt2 on a 6-DOF arm), Week 24 (the composed graph under a safety leash), and Week 25 (grasping geometry). You have an arm that reaches poses and a sim you can drive it in. This week the arm's actions stop coming from a planner and start coming from a *learned policy* — a neural network that maps observations to actions. You also need to be comfortable in **PyTorch**: defining an `nn.Module`, writing a training loop, computing a loss, stepping an optimizer. We do not re-teach PyTorch; if you did C5 (AI/Data Science) you have this, and if you are coming from industry ML you have it cold.

The one thing to internalize before you read another line: **a behavior-cloned policy is only as good as the states its training data covered, and the moment it makes one small mistake it drifts into states the data never covered, where it has no idea what to do — and the errors compound.** This is *covariate shift*, and it is not a bug you can train away with more epochs or a bigger network. It is structural: supervised learning assumes the training and test distributions match, but a *policy* changes its own test distribution by acting, so a tiny error early shifts every subsequent state away from the data. DAgger (Dataset Aggregation) is the unromantic, effective fix: run the policy, collect the states it actually visits, ask the expert for the correct action in *those* states, add them to the dataset, retrain. It works because it closes the gap between the states the data covered and the states the policy visits.

This week is where you stop being surprised that "my policy worked in the demos but flails in deployment," and start fixing it with the tool the field actually uses.

## Learning objectives

By the end of this week, you will be able to:

- **Collect** a demonstration dataset: teleoperate a "reach for the red block" task in Gz Sim with a keyboard or gamepad, record synchronized (observation, action) pairs, and save them in a clean, reloadable format.
- **Implement** a behavior cloning policy in PyTorch — an MLP that maps observations to actions — with a correct training loop: dataloader, forward pass, MSE (or the right) loss, backward pass, optimizer step, and a held-out validation split.
- **Explain** covariate shift precisely: why a policy changes its own state distribution by acting, why a small error compounds into states the data never covered, and why this is a distributional problem, not an optimization problem.
- **Diagnose** the covariate-shift failure from the *symptom* — the policy tracks the demos until the first deviation, then drifts and flails — and distinguish it from underfitting (fails everywhere) and overfitting (great on train, poor on val even in-distribution).
- **Implement** one round of DAgger: roll out the current policy, collect the states it visits, query the expert for the correct action at those states, aggregate into the dataset, and retrain — and quantify the success-rate improvement.
- **Reason** about the diffusion-of-error problem and why action-prediction errors accumulate over a trajectory, motivating the action-chunking and multimodal methods of Weeks 29–30.
- **Evaluate** a policy honestly: a fixed eval protocol, a success predicate, multiple seeds, and a success-rate number with a confidence interval — not "it looked good."
- **Wrap** the learned policy in the Week-24 safety leash and a classical fallback, so a flailing policy is clamped and recoverable, not dangerous.

## Prerequisites

This week assumes you have completed **C24 weeks 1–26**, or have equivalent fluency. Specifically:

- ROS2 **Jazzy** on **Ubuntu 24.04**, a Gz Sim (Harmonic) world with your arm and a red block, and the composed base+arm graph from Week 24.
- **PyTorch fluency.** You can define an `nn.Module`, write `for batch in loader: optimizer.zero_grad(); loss = criterion(model(x), y); loss.backward(); optimizer.step()` from memory, and reason about a loss curve (train vs. val). We do not re-teach this. If you did **C5** you have it; otherwise spend a day on the PyTorch 60-minute blitz before Monday.
- **MoveIt2 / arm control (Week 23).** You can command the arm to a target — joint angles or an end-effector pose — programmatically. The policy's *action* is one of these.
- **Teleop (Weeks 4, 20).** You can drive the arm with a keyboard or gamepad, or scripted teleop. This is how you collect demonstrations.
- **The safety leash (Week 24).** The E-stop and the velocity/workspace clamps. A learned policy is exactly the kind of thing that needs a leash — it can output garbage, and the clamp is what keeps garbage from hurting anyone.
- **A GPU is helpful but not required.** The MLP policy this week is small enough to train on a CPU in minutes; the ~USD 25/month cloud-GPU budget is for the heavier policies of Weeks 28–31, not this one.

You do **not** need any reinforcement learning this week — that is Week 28. Imitation learning needs *demonstrations*, not a reward function, which is exactly why it is the gentle on-ramp to learned policies.

## Topics covered

- **Behavior cloning (BC).** Imitation as supervised learning: collect (observation, action) pairs from an expert, train a policy to map observations to actions with a regression (or classification) loss. The whole pipeline — and its single structural flaw.
- **Demonstration collection.** Teleop (keyboard/gamepad) vs. scripted demonstrations; what to record (observation: joint states + the block's pose or an image; action: the next joint command or end-effector delta); synchronization and honest timestamping; how many demos is "enough" (and why 50 is a starting point, not a law).
- **Covariate shift — the central concept.** Why a policy is not an ordinary supervised model: it acts, and acting changes the distribution of states it sees. The compounding-error argument (one mistake → an unfamiliar state → a bigger mistake), why it is distributional and not fixable by more epochs, and the classic `O(εT²)` error-growth intuition.
- **DAgger (Dataset Aggregation).** The fix: roll out the current policy, collect the *states it actually visits*, query the expert for the correct action at those states, aggregate into the dataset, retrain. Why this is unromantic (it needs the expert in the loop during training) but works (it covers the policy's own state distribution). The `β`-mixing schedule and why early rounds lean on the expert.
- **The PyTorch training loop, done right.** Dataset/DataLoader, train/val split, the loss for continuous actions (MSE) vs. discrete (cross-entropy), normalization of observations and actions, early stopping on val, and the loss curves that tell underfitting from overfitting from covariate shift.
- **The diffusion-of-error problem.** Why per-step action errors accumulate over a trajectory, why a policy that is 95% right per step can still fail a 50-step task, and how this motivates action chunking (Week 30, ACT) and multimodal action models (Week 29, Diffusion Policy).
- **Honest evaluation.** A fixed eval protocol (same start states, same block positions), a crisp success predicate (the gripper reaches within X cm of the block), multiple seeds, and a success rate with an interval — and why "it looked good in the demo" is not an evaluation.
- **Safety around a learned policy.** The Week-24 leash applied to a network: velocity/workspace clamps on the policy's output, the classical fallback (a scripted reach or the Week-25 grasp planner) when the policy is rejected, and why a learned policy ships with a leash, always.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                      | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Behavior cloning; demo collection; the BC pipeline         |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | The PyTorch training loop; loss curves; first BC policy    |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | Covariate shift; why BC fails; the compounding-error argument |  2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | DAgger; the expert-in-the-loop round; honest evaluation    |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | The diffusion-of-error problem; safety around the policy   |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                     |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, eval-protocol polish                         |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                            | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The imitation-learning papers (BC, DAgger), the PyTorch and robot-learning references, the demo-collection tooling, and the talks worth your time |
| [lecture-notes/01-behavior-cloning-and-the-training-loop.md](./lecture-notes/01-behavior-cloning-and-the-training-loop.md) | Imitation as supervised learning; demo collection; the PyTorch BC policy and a correct training loop; reading the loss curves |
| [lecture-notes/02-covariate-shift-and-dagger.md](./lecture-notes/02-covariate-shift-and-dagger.md) | Covariate shift and the compounding-error argument; DAgger; the diffusion-of-error problem; honest evaluation; safety around the policy |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-collect-and-inspect-demos.md](./exercises/exercise-01-collect-and-inspect-demos.md) | Collect teleop demonstrations of the reach task and inspect the (observation, action) dataset for the problems that bite BC |
| [exercises/exercise-02-train-bc-policy.py](./exercises/exercise-02-train-bc-policy.py) | A PyTorch MLP behavior-cloning policy with a correct training loop, normalization, train/val split, and loss curves |
| [exercises/exercise-03-dagger-round.py](./exercises/exercise-03-dagger-round.py) | One round of DAgger: roll out, collect visited states, query the expert, aggregate, retrain, and measure the improvement |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-bc-vs-dagger.md](./challenges/challenge-01-bc-vs-dagger.md) | Quantify BC vs. BC+DAgger success rates on a fixed eval protocol, and explain the covariate-shift gap with evidence |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the covariate-shift postmortem |
| [mini-project/README.md](./mini-project/README.md) | The `crunch_il` imitation-learning pipeline: collect → BC → eval → DAgger → eval, with a safety-wrapped policy and an honest eval report |

## The "it works in the demos, then it drifts" promise

C24 uses a recurring marker for the central failure of this week. Your first BC policy will produce exactly this trace, and recognizing it is the skill:

```
[eval] BC policy, 20 trials, success = 6/20 (30%)
[eval]   trial 3: tracked the demo for 0.8 s, then drifted left and missed
[eval]   trial 7: tracked the demo for 1.1 s, then overshot and never recovered
[eval]   trial 12: SUCCESS (start state was close to a demo start)
[eval]   covariate-shift signature: succeeds near demo starts, drifts from novel starts
[eval] BC+DAgger (1 round), 20 trials, success = 15/20 (75%)
[eval]   the drift-and-flail trials now recover — DAgger covered those states
```

If your policy fails *everywhere*, that is underfitting, not covariate shift — go back to the training loop. If it fails specifically by *tracking the demo and then drifting once it deviates*, that is the covariate-shift signature, and DAgger is the fix. The point of Week 27 is to make that signature recognizable and that fix routine.

## Stretch goals

If you finish the regular work early and want to push further:

- Plot the **state-visitation distributions** of the demos vs. the BC rollouts (project to 2D with PCA or t-SNE). You will *see* the rollouts wandering off the demo manifold — covariate shift, visualized.
- Run **multiple DAgger rounds** (3–5) and plot success rate vs. round. Watch it climb and plateau, and note where the expert queries stop adding new information.
- Implement the **β-mixing** DAgger schedule (early rounds execute a mix of expert and policy actions) and compare convergence to pure-policy rollouts.
- Add **observation noise** to the demos and retrain. A policy trained on noisy observations is often *more* robust to covariate shift (a cheap form of the data augmentation that Diffusion Policy and ACT lean on in Weeks 29–30).
- Read the **DAgger paper (Ross, Gordon, Bagnell 2011)** until you can reproduce the `O(εT)` (DAgger) vs. `O(εT²)` (BC) error-growth argument on a whiteboard.

## Up next

Week 28 leaves imitation for **reinforcement learning** — PPO and SAC — where the robot learns from a *reward* instead of demonstrations, with all the reward-shaping and sim-throughput challenges that brings. Then Weeks 29–30 return to imitation with the heavy artillery: **Diffusion Policy** (which eats the multimodal-action problem) and **ACT** (action chunking, which directly attacks the diffusion-of-error problem you meet this week). The BC-and-DAgger intuition you build now is the foundation for all of it — every one of those methods is, at heart, a better answer to "how do I imitate an expert without drifting off the data?" Push your `crunch_il` pipeline before you start; Week 29 trains a Diffusion Policy on the very same demonstrations.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
