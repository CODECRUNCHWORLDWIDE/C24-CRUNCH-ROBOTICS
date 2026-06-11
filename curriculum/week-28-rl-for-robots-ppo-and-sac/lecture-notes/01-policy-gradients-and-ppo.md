# Lecture 1 — Policy Gradients and PPO: From the Log-Derivative Trick to a Clipped Surrogate

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can derive the policy gradient, explain why a baseline cuts variance without adding bias, compute GAE-λ by hand, and write the full PPO objective — clipped surrogate + value loss + entropy bonus — in PyTorch, naming the role of every term.

If you remember one sentence from this lecture, remember this one:

> **A policy-gradient algorithm pushes up the log-probability of actions that did better than expected and pushes down the log-probability of actions that did worse — and every refinement from REINFORCE to PPO is about estimating "better than expected" with less variance and taking steps that don't destroy the policy.**

Behavior cloning (Week 27) needed an expert. RL needs only a reward and an environment to poke at. That is the trade: you give up the expert and you take on two new obligations — a reward function the policy can't cheat, and a simulator fast enough to learn from. This lecture builds the algorithm; Lecture 2 builds the simulator and the reward.

---

## 1. The RL objective

A policy $\pi_\theta(a \mid s)$ is a neural network with parameters $\theta$ that maps a state $s$ to a distribution over actions $a$. The agent acts, the environment responds, and over an episode you get a **trajectory** $\tau = (s_0, a_0, r_0, s_1, a_1, r_1, \dots)$. The discounted return of a trajectory is

$$
R(\tau) = \sum_{t=0}^{T} \gamma^t r_t, \qquad \gamma \in [0, 1).
$$

The discount $\gamma$ (typically 0.99 for robot tasks) says "a reward now is worth slightly more than the same reward later," and — just as importantly — it keeps the infinite-horizon sum finite and the variance bounded. The objective is to maximize the *expected* return over trajectories the policy generates:

$$
J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta}\big[ R(\tau) \big].
$$

We want $\nabla_\theta J(\theta)$ so we can do gradient *ascent*. The obstacle: the distribution we're taking the expectation over *depends on $\theta$*. You cannot just differentiate inside the expectation, because changing $\theta$ changes which trajectories are likely. The fix is one of the most useful identities in machine learning.

---

## 2. The log-derivative trick and the policy-gradient theorem

The trick is this elementary identity:

$$
\nabla_\theta p_\theta(x) = p_\theta(x)\, \nabla_\theta \log p_\theta(x),
$$

which is just the chain rule on $\log$, rearranged. Apply it to the objective. The probability of a trajectory factorizes — the dynamics $p(s_{t+1}\mid s_t,a_t)$ don't depend on $\theta$, only the policy does:

$$
p_\theta(\tau) = p(s_0) \prod_{t} \pi_\theta(a_t \mid s_t)\, p(s_{t+1}\mid s_t, a_t).
$$

Taking $\log$ turns the product into a sum, and the dynamics terms have zero gradient w.r.t. $\theta$, so:

$$
\nabla_\theta \log p_\theta(\tau) = \sum_t \nabla_\theta \log \pi_\theta(a_t \mid s_t).
$$

Putting it together gives the **policy-gradient theorem**:

$$
\nabla_\theta J(\theta) = \mathbb{E}_{\tau \sim \pi_\theta}\!\left[ \left( \sum_t \nabla_\theta \log \pi_\theta(a_t\mid s_t) \right) R(\tau) \right].
$$

This is **REINFORCE**. Read it as an instruction: for each action, scale the gradient of its log-probability by the return that followed. Good trajectories pull their actions' probabilities up; bad ones push them down. It is *unbiased* — the expectation is exactly the true gradient — and you can estimate it with a sample average over trajectories. So why isn't this the whole course?

---

## 3. Why REINFORCE is unusable, and the two fixes

REINFORCE has **catastrophic variance**. Two reasons, and each has a clean fix.

### 3.1 Reward-to-go (causality)

An action at time $t$ cannot affect rewards earned *before* $t$. So multiplying $\nabla\log\pi(a_t)$ by the *whole-trajectory* return $R(\tau)$ injects noise from the past that the action had nothing to do with. Replace $R(\tau)$ with the **reward-to-go** $\hat{R}_t = \sum_{t'\ge t}\gamma^{t'-t} r_{t'}$. Still unbiased, lower variance:

$$
\nabla_\theta J = \mathbb{E}\!\left[ \sum_t \nabla_\theta \log\pi_\theta(a_t\mid s_t)\, \hat{R}_t \right].
$$

### 3.2 Baselines (the second free lunch)

Subtract a state-dependent **baseline** $b(s_t)$ from the reward-to-go. The magic: any baseline that depends only on the state (not the action) leaves the gradient *unbiased*, because

$$
\mathbb{E}_{a\sim\pi}\big[\nabla_\theta \log\pi_\theta(a\mid s)\, b(s)\big] = b(s)\,\nabla_\theta \underbrace{\textstyle\sum_a \pi_\theta(a\mid s)}_{=\,1} = b(s)\cdot 0 = 0.
$$

The probabilities sum to one; the gradient of a constant is zero; the baseline term vanishes in expectation. But it slashes variance, because now you scale $\nabla\log\pi$ by *how much better than baseline* the action did, not by the raw return. The best baseline is the value function $V^\pi(s)$ — the expected return from $s$. With $b(s)=V^\pi(s)$, the scaling factor becomes the **advantage**:

$$
A^\pi(s_t, a_t) = Q^\pi(s_t, a_t) - V^\pi(s_t) = \hat{R}_t - V^\pi(s_t).
$$

The advantage is the single most important quantity in this lecture. *Positive advantage → this action beat the average from here → push its probability up.* This is the **actor–critic** architecture: the **actor** is $\pi_\theta$, the **critic** is a second network $V_\phi$ that estimates $V^\pi$ and supplies the baseline.

---

## 4. Generalized Advantage Estimation (GAE-λ)

We don't know $A^\pi$ exactly; we estimate it. There's a spectrum of estimators, parameterized by how many real reward steps you use before falling back on the critic's bootstrap.

Define the **TD residual** with the learned value $V_\phi$:

$$
\delta_t = r_t + \gamma V_\phi(s_{t+1}) - V_\phi(s_t).
$$

- The **one-step** advantage estimate is just $\delta_t$ — low variance (one real reward, the rest is the critic's guess) but **biased** if the critic is wrong.
- The **Monte-Carlo** estimate is $\hat{R}_t - V_\phi(s_t)$ — unbiased but **high variance** (it sums all the noisy future rewards).

**GAE-λ** interpolates between them with an exponential weighting:

$$
\hat{A}_t^{\text{GAE}(\gamma,\lambda)} = \sum_{l=0}^{\infty} (\gamma\lambda)^l\, \delta_{t+l}.
$$

- $\lambda = 0$ recovers the one-step (low variance, biased) estimate.
- $\lambda = 1$ recovers the Monte-Carlo (unbiased, high variance) estimate.
- $\lambda \approx 0.95$ is the robot-RL default: mostly unbiased, with the variance tamed.

In code it's a single backward pass over the rollout — the recursive form is what you implement:

```python
def compute_gae(rewards, values, dones, last_value, gamma=0.99, lam=0.95):
    """rewards, values, dones: 1D tensors over a rollout of length T.
    `values` has length T; `last_value` is V(s_T) for bootstrapping.
    Returns advantages and returns (= advantages + values), both length T."""
    T = len(rewards)
    advantages = torch.zeros(T)
    last_gae = 0.0
    for t in reversed(range(T)):
        next_value = last_value if t == T - 1 else values[t + 1]
        next_nonterminal = 1.0 - dones[t]              # 0 if episode ended at t
        delta = rewards[t] + gamma * next_value * next_nonterminal - values[t]
        last_gae = delta + gamma * lam * next_nonterminal * last_gae
        advantages[t] = last_gae
    returns = advantages + values                       # the critic's regression target
    return advantages, returns
```

Two details that bite everyone:

- The `next_nonterminal` mask is why **terminated** matters. If the episode *terminated* (the MDP genuinely ended — the pole fell, the goal was reached), there is no future, so you must **not** bootstrap $V(s_{t+1})$ — the mask zeroes it. If the episode was merely **truncated** by a time limit, the future *does* exist and you *should* bootstrap. Confusing the two is a silent bug that quietly biases every advantage. (Gymnasium splits these into two booleans precisely so you get this right.)
- `returns = advantages + values` is the regression target for the critic: $\hat{R}_t = \hat{A}_t + V_\phi(s_t)$. The critic learns to predict these returns; the actor uses the advantages.

---

## 5. The trust-region problem PPO solves

You have an advantage estimate and a gradient. Why not just do `loss = -(logprob * advantage).mean()` and step? Because **the advantage was computed under the *old* policy**, and a single large gradient step can move the policy so far that the data you collected is no longer representative — the estimate becomes garbage and the policy collapses. RL is not supervised learning: your data distribution moves with your parameters.

The principled fix is **TRPO** (Trust Region Policy Optimization): maximize a surrogate objective subject to a hard constraint that the new policy stays within a KL-divergence ball of the old one. It works, but it requires conjugate gradients and a Fisher-vector product — heavy machinery. **PPO is the observation that you can get 95% of TRPO's benefit with a first-order trick: just *clip* the objective so the policy can't move too far, and skip the constrained optimization entirely.** That trick is why PPO, not TRPO, is the workhorse of robot RL in 2026.

---

## 6. The PPO clipped surrogate objective

Define the **probability ratio** between the new and old policies on the same state–action pair:

$$
r_t(\theta) = \frac{\pi_\theta(a_t\mid s_t)}{\pi_{\theta_{\text{old}}}(a_t\mid s_t)}.
$$

At the start of an update epoch, $r_t = 1$ (new = old). As you take gradient steps, it drifts. The **clipped surrogate** is:

$$
L^{\text{CLIP}}(\theta) = \mathbb{E}_t\Big[ \min\big( r_t(\theta)\,\hat{A}_t,\; \text{clip}(r_t(\theta),\, 1-\epsilon,\, 1+\epsilon)\,\hat{A}_t \big) \Big].
$$

Walk through what the `min` and `clip` do, because this is the heart of the algorithm:

- When $\hat{A}_t > 0$ (a good action), you want to increase $r_t$ — push the action's probability up. But the `clip` caps the benefit at $r_t = 1+\epsilon$. Past that, the objective flattens: there is **no gradient reward for moving further**. The policy can't run away on one good sample.
- When $\hat{A}_t < 0$ (a bad action), you want to *decrease* $r_t$. The `min` with the clipped term means once $r_t$ has dropped to $1-\epsilon$, again the objective flattens — you don't over-punish on one sample.
- The `min` is the conservative choice: it takes the *smaller* (pessimistic) of the clipped and unclipped surrogate, so clipping only ever *removes* incentive to move far, never adds it.

$\epsilon$ is typically **0.2**. This single scalar replaces TRPO's entire trust-region apparatus. It is not exactly a KL constraint, but in practice it keeps the per-update KL small, which is all you needed.

### The full PPO loss

PPO trains three things at once. The complete objective (the thing you minimize, hence the signs):

$$
L(\theta,\phi) = \underbrace{-\,L^{\text{CLIP}}(\theta)}_{\text{policy}} \;+\; c_1 \underbrace{\big(V_\phi(s_t) - \hat{R}_t\big)^2}_{\text{value loss}} \;-\; c_2 \underbrace{\mathcal{H}[\pi_\theta(\cdot\mid s_t)]}_{\text{entropy bonus}}.
$$

- The **value loss** is plain regression: the critic predicts the GAE returns. $c_1 \approx 0.5$.
- The **entropy bonus** rewards a policy for staying stochastic, which sustains exploration and stops premature collapse to a deterministic (and probably wrong) policy. $c_2 \approx 0.0$–$0.01$; subtracted because we minimize.

Here is the full update in PyTorch — this is the spine of `exercise-02`:

```python
def ppo_update(policy, value_net, opt, obs, actions, old_logprobs,
               advantages, returns, clip_eps=0.2, c1=0.5, c2=0.01,
               epochs=4, minibatch_size=256):
    # Normalize advantages per-batch: a standard, high-impact stabilizer.
    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    n = obs.shape[0]
    for _ in range(epochs):
        idx = torch.randperm(n)
        for start in range(0, n, minibatch_size):
            mb = idx[start:start + minibatch_size]

            dist = policy.distribution(obs[mb])          # e.g. Normal(mu, sigma)
            new_logprobs = dist.log_prob(actions[mb]).sum(-1)
            entropy = dist.entropy().sum(-1).mean()

            ratio = torch.exp(new_logprobs - old_logprobs[mb])   # r_t(theta)
            unclipped = ratio * advantages[mb]
            clipped = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * advantages[mb]
            policy_loss = -torch.min(unclipped, clipped).mean()  # the CLIP objective

            value_pred = value_net(obs[mb]).squeeze(-1)
            value_loss = ((value_pred - returns[mb]) ** 2).mean()

            loss = policy_loss + c1 * value_loss - c2 * entropy

            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(policy.parameters()) + list(value_net.parameters()), 0.5)
            opt.step()
```

The structure to internalize: **collect a big rollout under $\pi_{\text{old}}$, then take several epochs of minibatch updates on that fixed batch.** Reusing the batch for a few epochs is where the sample efficiency comes from; the clip is what makes that reuse safe. After the epochs, you throw the batch away and collect fresh data — that's what makes PPO **on-policy**.

---

## 7. The continuous-action policy head

CartPole has discrete actions (left/right), so the policy is a `Categorical`. Robots have continuous actions (joint torques, end-effector deltas), so the policy is a **Gaussian**: the network outputs a mean $\mu_\theta(s)$, and the standard deviation is either a separate head or a single global learnable `log_std` parameter.

```python
class GaussianPolicy(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden=256):
        super().__init__()
        self.mu = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, act_dim),
        )
        # A global, state-independent log-std is the common PPO default.
        self.log_std = nn.Parameter(torch.zeros(act_dim))

    def distribution(self, obs):
        mu = self.mu(obs)
        std = torch.exp(self.log_std)
        return torch.distributions.Normal(mu, std)

    def forward(self, obs):
        dist = self.distribution(obs)
        action = dist.sample()
        logprob = dist.log_prob(action).sum(-1)   # sum over action dims (independent)
        return action, logprob
```

Note `.sum(-1)`: a multi-dimensional action's log-prob is the sum of per-dimension log-probs, because we model the dimensions as independent Gaussians. Forgetting that `.sum(-1)` is a classic shape bug that silently trains on the wrong objective.

(Robots add one more wrinkle — actions are bounded, so you squash the Gaussian through a `tanh`. PPO often gets away with a plain Gaussian + clipping the action at the env boundary; SAC, in Lecture 2, does the `tanh` properly with a log-prob correction. We flag it here so the difference is on your radar.)

---

## 8. Reading the dashboard: diagnosing a run from its traces

A senior RL engineer does not stare at the reward curve alone. Five traces tell you what's happening:

| TensorBoard scalar | Healthy | What a bad value means |
|---|---|---|
| `rollout/ep_rew_mean` | Rises, then plateaus near the reward ceiling | Flat at random-policy value → reward unreachable, LR wrong, or env broken |
| `train/approx_kl` | 0.005–0.02 per update | Spiking > 0.05 → steps too big; the clip isn't holding; lower LR or epochs |
| `train/clip_fraction` | 0.1–0.3 | ~0 → clip never binds (steps tiny, slow); ~1 → everything clipped (steps huge) |
| `train/explained_variance` | Climbs toward 1.0 | Near 0 or negative → the critic isn't learning the returns; check value LR / target |
| `train/entropy` | High early, decays slowly | Collapses to ~0 fast → premature determinism; raise the entropy coefficient $c_2$ |

`approx_kl` is computed cheaply as the mean of `(old_logprob - new_logprob)` over the batch (a first-order KL estimate). `explained_variance` is $1 - \text{Var}(\hat{R}-V)/\text{Var}(\hat{R})$: if the critic explains the returns, it's near 1; if it's no better than predicting the mean, it's near 0. **Learn to glance at these five and know within thirty seconds whether a run is healthy.** That skill is the difference between a productive afternoon and a wasted weekend of GPU time.

---

## 9. A worked numerical example (you'll redo this in Exercise 1)

Tiny rollout, $\gamma = 1.0$, $\lambda = 1.0$ (pure Monte-Carlo to keep arithmetic clean). Three steps, no termination until the end:

| $t$ | $r_t$ | $V_\phi(s_t)$ |
|---|---|---|
| 0 | 1 | 0.5 |
| 1 | 1 | 1.5 |
| 2 | 1 | 0.8 |

Reward-to-go: $\hat{R}_0 = 3$, $\hat{R}_1 = 2$, $\hat{R}_2 = 1$. Advantages $\hat{A}_t = \hat{R}_t - V_\phi(s_t)$: $\hat{A}_0 = 2.5$, $\hat{A}_1 = 0.5$, $\hat{A}_2 = 0.2$. All positive — every action did better than the critic expected, so PPO pushes all three actions' probabilities up, *most* at $t=0$. Now suppose on the next update the ratio for $t=0$ climbs to $r_0 = 1.4$ with $\epsilon = 0.2$: the unclipped term is $1.4 \times 2.5 = 3.5$, the clipped term is $1.2 \times 2.5 = 3.0$, and the `min` picks $3.0$ — the extra push past $1+\epsilon$ earns nothing. That is the clip doing its job: the policy banked the improvement up to $1.2\times$ and was denied the reckless rest. Exercise 1 makes you do this with GAE-λ < 1 and a termination in the middle, which is where the masking earns its keep.

---

## 10. The PPO hyperparameters that actually matter

PPO has a reputation for being finicky, but in practice a small set of knobs carries the weight. Here is the senior shortlist, with sane robot-RL defaults and what each does when you're wrong:

| Hyperparameter | Default | Effect / failure when wrong |
|---|---|---|
| Learning rate | 3e-4 (often annealed to 0) | Too high → KL spikes, policy collapses; too low → glacial. The first thing to tune. |
| Clip ε | 0.2 | Larger → bigger, riskier steps; smaller → slower, safer. Rarely worth changing from 0.2. |
| GAE λ | 0.95 | Lower → more bias (trust the critic); higher → more variance. 0.95 is the robust default. |
| Discount γ | 0.99 | Lower → myopic; too high (→1) → high-variance, hard credit assignment over long horizons. |
| Epochs per rollout | 3–10 | More → more data reuse (sample-efficient) but more off-policy drift; watch the KL. |
| Rollout length | 2048+ per env | Short → noisy advantages; long → stale data within a batch. Scale with num_envs. |
| Entropy coef $c_2$ | 0.0–0.01 | Too low → premature collapse; too high → policy stays random and won't commit. |
| Num parallel envs | 100s–1000s (Isaac Lab) | More throughput; PPO loves this (Lecture 2). |

The single most important practical lesson — from the famous "37 Implementation Details of PPO" blog — is that **PPO's reputation for fragility is mostly about implementation details, not hyperparameters.** Advantage normalization, value-loss clipping, orthogonal weight init, observation normalization, gradient clipping, and the correct terminated/truncated handling matter *more* than fine-tuning the learning rate. Get the details right (they're all in `exercise-02`'s scaffolding) and PPO is remarkably robust. Get them wrong and no learning rate saves you. That asymmetry — details over hyperparameters — is the thing experienced RL engineers know that beginners don't.

### Annealing and normalization (the two free wins)

Two cheap additions that consistently help and cost almost nothing:

- **Learning-rate annealing**: linearly decay the LR to 0 over training. Early on you want big steps; late, small refinements. One line, reliably helps.
- **Observation normalization**: maintain a running mean/std of observations and normalize before the network sees them. Neural nets train far better on roughly-unit-scale inputs, and robot observations (positions in meters, velocities in rad/s, forces in newtons) are wildly different scales. This is the single most underrated free lunch in robot RL, and it's a stretch goal in the exercises precisely so you measure the difference yourself.

---

## 11. Recap

You should now be able to:

- Derive the policy gradient via the log-derivative trick and explain why it's unbiased.
- Explain reward-to-go and baselines as variance reduction that preserves the gradient, and define the advantage.
- Implement GAE-λ, including the terminated-vs-truncated bootstrap mask, and state what $\lambda$ trades off.
- Write the PPO clipped surrogate and explain why the `min`+`clip` replaces TRPO's trust region.
- Assemble the full PPO loss (clip + value + entropy) and the collect-then-multi-epoch update structure.
- Read the five diagnostic traces and call a run healthy or doomed in thirty seconds.

Next: SAC — the off-policy, maximum-entropy alternative that's more sample-efficient and harder to get right — plus the GPU-parallel simulator and the reward-shaping discipline that make robot RL actually feasible. Continue to [Lecture 2 — SAC, Isaac Lab, and Reward Shaping](./02-sac-isaac-lab-and-reward-shaping.md).

---

## References

- *Proximal Policy Optimization Algorithms* — Schulman et al. (2017): <https://arxiv.org/abs/1707.06347>
- *High-Dimensional Continuous Control Using Generalized Advantage Estimation* — Schulman et al. (2015): <https://arxiv.org/abs/1506.02438>
- *Trust Region Policy Optimization* — Schulman et al. (2015): <https://arxiv.org/abs/1502.05477>
- *OpenAI Spinning Up — Intro to Policy Optimization*: <https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html>
- *CleanRL `ppo_continuous_action.py`* (the reference implementation): <https://github.com/vwxyzjn/cleanrl>
- *The 37 Implementation Details of Proximal Policy Optimization* — Huang et al. (the famous reproducibility blog): <https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/>
