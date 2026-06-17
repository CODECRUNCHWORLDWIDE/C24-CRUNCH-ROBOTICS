# Week 28 — Resources

Every resource here is **free**. The PPO and SAC papers are on arXiv. Isaac Lab is open source (BSD-3) with public docs. CleanRL and SpinningUp are open-source reference implementations explicitly built for learning. No paywalled books are linked.

Pin yourself to **Isaac Lab** (the current NVIDIA RL framework, successor to the deprecated Isaac Gym / OmniIsaacGymEnvs) and **Gymnasium** (the maintained successor to OpenAI Gym — the `gym` package is dead; import `gymnasium as gym`). Where a version matters, the 2026-current one is noted.

## Required reading (work it into your week)

- **Proximal Policy Optimization Algorithms** — Schulman, Wolski, Dhariwal, Radford, Klimov (2017). The PPO paper. Read §3 (the clipped objective) twice:
  <https://arxiv.org/abs/1707.06347>
- **High-Dimensional Continuous Control Using Generalized Advantage Estimation** — Schulman et al. (2015). The GAE-λ paper; §3 is the bias–variance derivation:
  <https://arxiv.org/abs/1506.02438>
- **Soft Actor-Critic: Off-Policy Maximum Entropy Deep RL with a Stochastic Actor** — Haarnoja et al. (2018). The SAC paper; the squashed-Gaussian `tanh` correction is Appendix C:
  <https://arxiv.org/abs/1801.01290>
- **Soft Actor-Critic Algorithms and Applications** — Haarnoja et al. (2018). The follow-up that adds **automatic temperature tuning** (the α loss you implement Wednesday):
  <https://arxiv.org/abs/1812.05905>
- **OpenAI Spinning Up — Intro to Policy Optimization & VPG/PPO/SAC pages** — the single best from-scratch derivation of the policy gradient online, with code that matches the math:
  <https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html>

## The implementations to read (code that gets it right)

- **CleanRL** — single-file, dependency-light, *educational* RL. The `ppo.py`, `ppo_continuous_action.py`, and `sac_continuous_action.py` files are the reference for this week's exercises. Read them line by line:
  <https://github.com/vwxyzjn/cleanrl>
- **CleanRL docs** — every file has a matching docs page with the loss equations beside the code, plus reproduced benchmark curves:
  <https://docs.cleanrl.dev/>
- **Stable-Baselines3** — the batteries-included PPO/SAC you'd reach for in a hurry; read its `PPO` and `SAC` for the "production" structuring (callbacks, vec-env, normalization):
  <https://stable-baselines3.readthedocs.io/>

## Isaac Lab (GPU-parallel sim — the Thursday/Friday platform)

- **Isaac Lab documentation** — installation, the `ManagerBasedRLEnv`, the environment registry, and the training scripts:
  <https://isaac-sim.github.io/IsaacLab/>
- **Isaac Lab — RL training quickstart** (`scripts/reinforcement_learning/`) — how to launch a PPO run with `rsl_rl` or `skrl` and where TensorBoard logs land:
  <https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/rl_existing_scripts.html>
- **`rsl_rl`** — ETH/NVIDIA's fast GPU PPO runner, the default for legged and manipulation tasks in Isaac Lab:
  <https://github.com/leggedrobotics/rsl_rl>
- **`skrl`** — a modular RL library with first-class Isaac Lab support; both PPO and SAC runners:
  <https://skrl.readthedocs.io/>
- **Path B note:** if you cannot run Isaac Lab, every concept transfers to **Gymnasium** vectorized envs (`gymnasium.make_vec(...)`) on CPU/GPU. Slower, but the math, the diagnostics, and the reward-shaping lessons are identical. The mini-project documents the substitution explicitly.

## Gymnasium (the interface every exercise uses)

- **Gymnasium documentation** — the maintained Gym successor. `reset()`, `step()`, the `(obs, reward, terminated, truncated, info)` five-tuple, and the vector API:
  <https://gymnasium.farama.org/>
- **Gymnasium — handling terminated vs truncated** — the distinction that makes your value bootstrap correct; misreading it is a top-five RL bug:
  <https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/>
- **Gymnasium wrappers** — `NormalizeObservation`, `NormalizeReward`, `RecordEpisodeStatistics` — the wrappers the exercises lean on:
  <https://gymnasium.farama.org/api/wrappers/>

## Reward shaping and reward hacking

- **Policy Invariance Under Reward Transformations** — Ng, Harada, Russell (1999). The potential-based-shaping theorem: why $F(s,s')=\gamma\Phi(s')-\Phi(s)$ leaves the optimal policy unchanged:
  <https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf>
- **Faulty Reward Functions in the Wild** — OpenAI (2016). The canonical reward-hacking demo (the boat that spins to farm points instead of finishing the race). Required intuition for the challenge:
  <https://openai.com/research/faulty-reward-functions>
- **Concrete Problems in AI Safety** — Amodei et al. (2016). §3 (reward hacking) is the taxonomy your challenge bestiary is graded against:
  <https://arxiv.org/abs/1606.06565>

## Talks worth your time (free, no signup)

- **Pieter Abbeel — Deep RL bootcamp / Foundations of Deep RL** — the lecture series that teaches policy gradients and actor–critic from the ground up; the PG and SAC lectures map directly to Lecture 1 and 2:
  <https://www.youtube.com/playlist?list=PLkFD6_40KJIwhWJpGazJ9VSj9CFMkb79A>
- **NVIDIA Isaac Lab / GTC robot-learning sessions** — the GPU-parallel-sim throughput story straight from the team that built it; search the free GTC on-demand catalog:
  <https://www.nvidia.com/gtc/>
- **RSS / CoRL keynotes on sim-to-real and parallel RL** — the robot-learning community's flagship venues post talks free:
  <https://roboticsconference.org/>

## Tools you'll use this week

- **`gymnasium`** — `pip install "gymnasium[classic-control]"`. CartPole and Pendulum live here.
- **`torch`** — PyTorch ≥ 2.3, CUDA build if you have an NVIDIA GPU.
- **`tensorboard`** — `pip install tensorboard`; `tensorboard --logdir runs/`. Your RL dashboard.
- **Isaac Lab** — installed per the official docs (pip install or the source clone); needs an NVIDIA GPU + recent driver.
- **`stable-baselines3`** — `pip install stable-baselines3` for the "reach for a known-good baseline" moments.

## Glossary cheat sheet

Keep this open in a tab.

| Term | Plain English |
|------|---------------|
| **Policy $\pi_\theta(a\|s)$** | The thing you're learning: a distribution over actions given a state. |
| **Return $R(\tau)$** | Discounted sum of rewards along a trajectory $\tau$. |
| **Value $V^\pi(s)$** | Expected return from state $s$ under policy $\pi$. The critic learns this. |
| **Q-function $Q^\pi(s,a)$** | Expected return from taking $a$ in $s$, then following $\pi$. |
| **Advantage $A^\pi(s,a)$** | $Q^\pi - V^\pi$: how much better than average action $a$ is in state $s$. |
| **GAE-λ** | Generalized Advantage Estimation: a $\lambda$-weighted blend of $n$-step TD residuals trading bias for variance. |
| **On-policy** | Learns only from data the *current* policy generated (PPO). Throws data away each update. |
| **Off-policy** | Learns from a replay buffer of *past* data (SAC). Sample-efficient. |
| **Clip ratio ε** | PPO's surrogate-clipping bound (typically 0.2); caps how far one update moves the policy. |
| **Entropy bonus** | A reward for keeping the policy stochastic; sustains exploration. |
| **Max-entropy RL** | SAC's framing: maximize reward *and* entropy, weighted by temperature α. |
| **Temperature α** | SAC's reward-vs-entropy trade-off weight; auto-tuned to a target entropy. |
| **Twin critics** | SAC's two Q-nets; the min of the two fights overestimation (clipped double-Q). |
| **Polyak / soft update** | Target network update $\bar\theta \leftarrow \tau\theta + (1-\tau)\bar\theta$ with small $\tau$. |
| **Reparameterization trick** | Sampling $a=\mu+\sigma\odot\epsilon$ so gradients flow through the sample (SAC actor). |
| **Reward hacking** | The policy maximizing your reward *without* doing the task you meant. |
| **terminated vs truncated** | terminated = the MDP ended (success/failure); truncated = a time limit cut it off. Bootstrap on truncated, not terminated. |

---

*If a link 404s, please open an issue so we can replace it.*
