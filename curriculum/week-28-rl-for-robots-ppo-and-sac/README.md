# Week 28 — Reinforcement Learning for Robots: PPO and SAC

This is the week the robot stops being told what to do and starts figuring it out. By Friday you will have trained a policy from scratch — no demonstrations, no labels, just a reward function and a fast simulator — that drives a manipulator to a target with better than 90% success, and you will be able to explain, on a whiteboard, every term in the PPO objective and every term in the SAC objective without notes.

We assume you finished **Week 27 (Behavior Cloning and DAgger)** and have a working teleoperation/demo-collection pipeline and a small MLP policy you trained by supervised learning. RL is the other half of the policy-learning coin: where BC copies an expert, RL *discovers* behavior by trial and error against a reward. You will feel the trade immediately — RL needs no expert, but it needs a *reward you can defend* and a *simulator fast enough* to take millions of steps. Both of those are where robot RL actually lives or dies in 2026, and both get a full treatment this week.

The one sentence to carry in before you read another line: **RL works on robots when the simulator is fast, the reward is shaped, and the curriculum is real.** A policy-gradient algorithm is twenty lines of PyTorch. The thousand lines around it — the vectorized environment, the reward terms, the normalization, the reset logic, the curriculum — are what separate a reward curve that climbs from one that flatlines at random. We teach both, in that proportion.

## Learning objectives

By the end of this week, you will be able to:

- **Derive** the policy-gradient theorem from the log-derivative trick, and explain why the naive REINFORCE estimator is unbiased but has crippling variance.
- **Implement** Generalized Advantage Estimation (GAE-λ) and explain the bias–variance knob that λ and γ control.
- **Write** the full PPO clipped-surrogate objective in PyTorch — including the value loss, the entropy bonus, and the role of the clip ratio ε — and explain *why* clipping replaces the TRPO trust region.
- **Write** the full SAC objective — the twin soft Q-functions, the squashed-Gaussian actor with the `tanh` log-prob correction, the entropy-regularized value target, and automatic temperature (α) tuning — and explain when off-policy SAC beats on-policy PPO and when it doesn't.
- **Distinguish** on-policy (PPO) from off-policy (SAC) learning by sample efficiency, stability, and parallelism, and pick the right one for a given robot task and compute budget.
- **Stand up** a GPU-parallel training run in **Isaac Lab** (or Gymnasium + a vectorized env on Path B) with hundreds of parallel environments, and read the throughput number that decides whether your project is feasible.
- **Shape** a reward for a reach task — dense distance term, action penalty, success bonus — and recognize, name, and fix a **reward-hacking** failure when the policy games your reward instead of solving your task.
- **Read** a TensorBoard run: the reward curve, the KL divergence, the clip fraction, the explained variance, the entropy — and diagnose a stalled run from those traces alone.

## Prerequisites

This week assumes you have completed **C24 weeks 1–27**, or have equivalent fluency. Specifically:

- **Week 27**: you have collected demonstrations and trained a BC policy. You understand a PyTorch training loop, optimizers, and loss curves (this is also a C5 hard prerequisite — we do not re-teach backprop).
- **PyTorch fluency**: you can write a `nn.Module`, a training loop with `optimizer.zero_grad() / loss.backward() / optimizer.step()`, and read a tensor shape error without panic.
- **ROS2 Jazzy** on Ubuntu 24.04, and a **Gz Sim** robot you can drive. The deploy step wraps the trained policy in a `rclpy` node.
- **A GPU.** Isaac Lab needs an NVIDIA GPU (RTX 30-series or better, ≥ 8 GB). On Path B you can run the Gymnasium labs CPU-only, slower, and we document the substitution. The ~USD 25/month cloud-GPU budget from the track README covers this week if your laptop can't.
- Comfort with **probability**: expectations, the score function, a Gaussian density, and entropy. We re-derive what we use, but the vocabulary should be familiar.

You do **not** need prior RL experience. We start at the policy-gradient theorem and build PPO and SAC from it. If your only exposure to RL is "the thing that played Go," this is the week it becomes an engineering tool you can wield.

## Topics covered

- **Policy gradients from scratch**: the RL objective $J(\theta) = \mathbb{E}_{\tau\sim\pi_\theta}[R(\tau)]$, the log-derivative trick, the REINFORCE estimator, why baselines reduce variance without adding bias, and the actor–critic decomposition.
- **Advantage estimation**: the value function $V^\pi$, the action-value $Q^\pi$, the advantage $A^\pi = Q^\pi - V^\pi$, TD residuals, and **GAE-λ** as the bias–variance interpolation between one-step TD and full Monte-Carlo returns.
- **PPO** (Schulman et al. 2017): the importance-sampling ratio, the clipped surrogate $L^{CLIP}$, the combined actor + value + entropy loss, the minibatch-epoch structure, and why the clip is a cheap stand-in for TRPO's KL trust region.
- **SAC** (Haarnoja et al. 2018): maximum-entropy RL, the soft Q-function, the twin-critic clipped-double-Q trick, the reparameterized squashed-Gaussian actor with the `tanh` correction term in the log-prob, the soft value target with target networks and Polyak averaging, and **automatic entropy temperature** tuning against a target entropy.
- **On-policy vs off-policy**: replay buffers, sample efficiency, the stability/variance trade, and why on-policy PPO loves thousands of parallel envs while off-policy SAC loves a replay buffer and fewer, richer envs.
- **The Gymnasium interface**: `reset()`, `step()`, the five-tuple `(obs, reward, terminated, truncated, info)`, vectorized envs (`SyncVectorEnv`, `AsyncVectorEnv`), observation/reward normalization wrappers, and the terminated-vs-truncated distinction that bootstraps your value target correctly.
- **Isaac Lab**: GPU-parallel simulation (`PhysX` on-device), the `ManagerBasedRLEnv`, thousands of environments stepping in lockstep on one GPU, the `rsl_rl` / `skrl` PPO runners, and the throughput number (steps/sec) that is the single most important feasibility metric in robot RL.
- **Reward shaping and reward hacking**: dense vs sparse rewards, potential-based shaping that preserves the optimal policy, the action/effort penalty, the success bonus, and the catalogue of reward-hacking failure modes (the policy that vibrates in place to farm a velocity reward; the reach that "succeeds" by knocking the target into the gripper).

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Policy gradients, advantage, GAE; the PPO objective    |    2h    |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Implement PPO; CartPole then a reach task              |    1h    |    2.5h   |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Wednesday | SAC: max-entropy RL, twin critics, the squashed actor  |    2h    |    1.5h   |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Thursday  | Isaac Lab; parallel sim; reward shaping & hacking      |    1h    |    1.5h   |     0h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | Train the reach policy to >90%; read the TensorBoard   |    0h    |    0h     |     1h     |    0.5h   |   1h     |     3h       |    0.5h    |     6h      |
| Saturday  | Mini-project deep work                                 |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0h      |     3h      |
| Sunday    | Quiz, review, training-report polish                   |    0h    |    0h     |     0h     |    1h     |   0h     |     1h       |    0h      |     2h      |
| **Total** |                                                        | **6h**   | **7h**    | **4h**     | **3.5h**  | **5h**   | **12h**      | **2h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview (you are here) |
| [resources.md](./resources.md) | The PPO/SAC papers, Isaac Lab docs, CleanRL, SpinningUp, and the talks worth your time |
| [lecture-notes/01-policy-gradients-and-ppo.md](./lecture-notes/01-policy-gradients-and-ppo.md) | Policy-gradient theorem, GAE, the full PPO clipped objective in PyTorch, and the diagnostics |
| [lecture-notes/02-sac-isaac-lab-and-reward-shaping.md](./lecture-notes/02-sac-isaac-lab-and-reward-shaping.md) | SAC end to end, GPU-parallel sim in Isaac Lab, reward shaping, and the reward-hacking catalogue |
| [exercises/README.md](./exercises/README.md) | Index of the three exercises |
| [exercises/exercise-01-gae-and-ppo-math.md](./exercises/exercise-01-gae-and-ppo-math.md) | Derive the PPO gradient, compute GAE by hand, predict a clip's effect — paper and a tiny numpy check |
| [exercises/exercise-02-ppo-cartpole.py](./exercises/exercise-02-ppo-cartpole.py) | A complete, runnable single-file PPO that solves `CartPole-v1`; you fill four marked TODOs |
| [exercises/exercise-03-sac-pendulum.py](./exercises/exercise-03-sac-pendulum.py) | A complete, runnable SAC that solves `Pendulum-v1`; you fill the `tanh` log-prob correction and the temperature loss |
| [challenges/README.md](./challenges/README.md) | Index of the weekly challenge |
| [challenges/challenge-01-reward-hacking-bestiary.md](./challenges/challenge-01-reward-hacking-bestiary.md) | Plant, observe, and fix three reward-hacking failures on a reach task |
| [quiz.md](./quiz.md) | 13 questions with a hidden answer key |
| [homework.md](./homework.md) | Six problems including the training-report writeup with a rubric |
| [mini-project/README.md](./mini-project/README.md) | Train a PPO reach policy in Isaac Lab to >90% success and wrap it in a ROS2 inference node |

## The "the reward curve climbed" promise

C24 uses a recurring marker for every RL exercise that ends in a policy that actually learned. It is the TensorBoard reward curve crossing your success threshold and *staying* there:

```
$ tensorboard --logdir runs/
# Open http://localhost:6006
# rollout/ep_rew_mean    : rises from ~ -40 toward +15 and plateaus
# rollout/success_rate   : crosses 0.90 before 30 min of wall time
# train/approx_kl        : hovers 0.005–0.02 (not spiking — the clip is working)
# train/clip_fraction    : 0.1–0.3 (some clipping, not everything clipped)
# train/explained_var    : climbs toward 1.0 (the critic is learning the returns)
```

If `ep_rew_mean` is flat at its random-policy value, your reward is unreachable, your learning rate is wrong, or your env is broken — and the *other* traces tell you which. A run where reward climbs but `approx_kl` explodes is a run that will collapse; you caught it early. The point of Week 28 is to make that dashboard ordinary, and to make a flat curve *legible* instead of mysterious.

## Stretch goals

If you finish the regular work early and want to push further:

- Implement **PPO with a learned state-dependent log-std** vs a global learnable log-std and compare exploration on the reach task. The state-dependent head matters more than people think on contact-rich tasks.
- Add **observation and reward normalization** (running mean/std) to the CartPole PPO and measure how much faster it converges. Normalization is the most underrated free lunch in robot RL.
- Swap SAC's twin critics for a **single** critic and watch the Q-values overestimate and the policy degrade — the clipped-double-Q trick earns its keep, and you should see it fail without it.
- Read the **DroQ / REDQ** update-to-data-ratio idea and run SAC with a higher gradient-step-per-env-step ratio on `Pendulum`. Watch sample efficiency rise and stability fall — the exact trade you'll re-meet in Week 34's sim-to-real.

## Up next

Week 29 takes the policy-learning machinery you now own and confronts the thing RL and BC both struggle with: **multimodal actions**. **Diffusion Policy** treats action prediction as iterative denoising and eats the "there are three good ways to grasp this and the MLP averages them into a bad one" problem. Push your training report and your ROS2 policy node before you start it — Week 29 reuses the same demo set and the same eval harness.

---

*If you find errors in this material, please open an issue or send a PR. Future learners will thank you.*
