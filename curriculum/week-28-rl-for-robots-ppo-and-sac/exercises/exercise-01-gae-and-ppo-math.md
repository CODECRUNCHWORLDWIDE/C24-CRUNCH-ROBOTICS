# Exercise 1 — The PPO/GAE Math on Paper

**Goal:** Make the policy-gradient and PPO math *yours*, not a black box. You will derive the gradient, compute GAE-λ by hand through a mid-episode termination (where the bootstrap mask earns its keep), predict the effect of a clip on a step, and confirm one of your hand calculations against a five-line numpy snippet. After this, the code in Exercises 2 and 3 reads like prose.

**Estimated time:** 60 minutes. Paper, then a few lines of numpy.

---

## Part A — Derive the policy gradient (15 min)

Starting from $J(\theta) = \mathbb{E}_{\tau\sim\pi_\theta}[R(\tau)]$, derive

$$
\nabla_\theta J(\theta) = \mathbb{E}_{\tau}\!\left[ \sum_t \nabla_\theta \log\pi_\theta(a_t\mid s_t)\, \hat{A}_t \right]
$$

filling in every step yourself. You must explicitly:

1. Apply the **log-derivative trick** $\nabla p = p\,\nabla\log p$ to move the gradient inside the expectation.
2. Show that $\nabla_\theta \log p_\theta(\tau) = \sum_t \nabla_\theta\log\pi_\theta(a_t\mid s_t)$ — i.e., that the **dynamics terms drop out** because they don't depend on $\theta$. State *why* in one sentence.
3. Argue the **baseline** $b(s_t)$ can be subtracted from the reward-to-go without biasing the gradient, by showing $\mathbb{E}_{a\sim\pi}[\nabla_\theta\log\pi_\theta(a\mid s)\,b(s)] = 0$.

**Acceptance:** A written derivation (photo of paper, or LaTeX/markdown) with all three steps and the one-sentence justifications. The baseline argument must invoke $\sum_a \pi(a\mid s) = 1$.

---

## Part B — Compute GAE-λ by hand through a termination (25 min)

Here is a four-step rollout from a single environment. The episode **terminates at $t = 2$** (the `done` flag), then a *new* episode's step is at $t = 3$. Use $\gamma = 0.99$, $\lambda = 0.95$. The critic's value estimates $V_\phi(s_t)$ are given. For the bootstrap after the last step, use $V_\phi(s_4) = 0.50$.

| $t$ | $r_t$ | $V_\phi(s_t)$ | `done`$_t$ |
|---|---|---|---|
| 0 | 0.0 | 0.80 | 0 |
| 1 | 0.0 | 0.90 | 0 |
| 2 | 1.0 | 0.40 | **1** |
| 3 | 0.0 | 0.70 | 0 |

Compute, showing every number:

1. The TD residual $\delta_t = r_t + \gamma V_\phi(s_{t+1})(1-\text{done}_t) - V_\phi(s_t)$ for each $t$. **Watch $t=2$**: because `done`$_2 = 1$, the bootstrap term is zeroed — there is no future across a termination.
2. The GAE advantages via the recursion $\hat{A}_t = \delta_t + \gamma\lambda(1-\text{done}_t)\hat{A}_{t+1}$, computed **backward** from $t=3$. The `done` mask at $t=2$ must stop the advantage from $t=3$ leaking backward across the episode boundary.
3. The critic regression targets $\hat{R}_t = \hat{A}_t + V_\phi(s_t)$.

**Acceptance:** The four $\delta_t$, four $\hat{A}_t$, and four $\hat{R}_t$, with the arithmetic shown. You must explicitly note *where* the `done`$_2$ mask changed the result versus if you'd ignored it — that's the whole lesson.

---

## Part C — Predict a clip's effect (10 min)

Take the advantage you computed for $t=2$ in Part B (call it $\hat{A}_2$; it should be positive). Suppose after some gradient steps the probability ratio at that state is $r_2(\theta) = 1.35$, with clip $\epsilon = 0.2$.

1. Compute the **unclipped** surrogate term $r_2\,\hat{A}_2$.
2. Compute the **clipped** surrogate term $\text{clip}(r_2, 0.8, 1.2)\,\hat{A}_2$.
3. State which one $L^{\text{CLIP}}$'s `min` selects, and explain in one sentence what that means for the gradient at this state (hint: a flat objective has zero gradient).
4. Now suppose instead $\hat{A}_2$ were **negative** and $r_2 = 0.5$. Redo (1)–(3) and confirm the clip protects against over-*decreasing* a probability too.

**Acceptance:** Both cases worked, with the correct `min` selection and the "what it means for the gradient" sentence for each.

---

## Part D — Check yourself in numpy (10 min)

Confirm your Part B GAE numbers with this snippet. Fill the one marked line, run it, and verify it matches your hand calculation to three decimals.

```python
import numpy as np

rewards = np.array([0.0, 0.0, 1.0, 0.0])
values  = np.array([0.80, 0.90, 0.40, 0.70])
dones   = np.array([0.0, 0.0, 1.0, 0.0])
last_value = 0.50
gamma, lam = 0.99, 0.95

T = len(rewards)
adv = np.zeros(T)
last_gae = 0.0
for t in reversed(range(T)):
    next_value = last_value if t == T - 1 else values[t + 1]
    nonterminal = 1.0 - dones[t]
    delta = rewards[t] + gamma * next_value * nonterminal - values[t]
    # TODO 1: write the GAE recursion for last_gae using delta, gamma, lam,
    #         nonterminal, and the previous last_gae. (One line — see Lecture 1 §4.)
    last_gae = ...
    adv[t] = last_gae

returns = adv + values
print("advantages:", np.round(adv, 4))
print("returns:   ", np.round(returns, 4))
```

**Acceptance:** The TODO filled correctly (`last_gae = delta + gamma * lam * nonterminal * last_gae`), the printed advantages matching your hand calculation, and a one-sentence note confirming the `done`$_2$ mask makes $\hat{A}_2 = \delta_2$ (no leak from $t=3$).

---

## Why this matters

When the mini-project's reward curve flatlines, the engineers who debug it fastest are the ones who can compute an advantage by hand and *know* what a healthy KL looks like. The math is not academic decoration — it is the mental model you debug with. The single most common Week-28 bug we see is a botched termination mask that biases every advantage; you just did the calculation that makes that bug obvious on sight.

When this feels comfortable, move to [Exercise 2 — PPO solves CartPole](exercise-02-ppo-cartpole.py).
