# Exercise 1 — DDPM/DDIM Math on Paper

**Goal:** Make the diffusion math *yours*. You will derive the closed-form one-shot noising from the per-step recursion (where $\bar\alpha_t$ comes from), write the simplified ε-loss, derive the DDIM clean-sample estimate, and reason about the denoising-step count. After this, every `torch.sqrt(alpha_bar[t])` in the code reads as obvious arithmetic, not magic.

**Estimated time:** 60 minutes. Paper, then a few lines of numpy.

---

## Part A — Derive the closed-form $q(x_t\mid x_0)$ (20 min)

Start from the per-step forward process $x_t = \sqrt{\alpha_t}\,x_{t-1} + \sqrt{1-\alpha_t}\,\epsilon_{t-1}$, with $\alpha_t = 1-\beta_t$ and each $\epsilon\sim\mathcal{N}(0,I)$ independent.

1. Expand one step: substitute $x_{t-1} = \sqrt{\alpha_{t-1}}\,x_{t-2} + \sqrt{1-\alpha_{t-1}}\,\epsilon_{t-2}$ into the expression for $x_t$.
2. Use the fact that **the sum of two independent Gaussians is Gaussian** — $\sqrt{a}\,\epsilon_1 + \sqrt{b}\,\epsilon_2$ has the same distribution as $\sqrt{a+b}\,\bar\epsilon$ for a single $\bar\epsilon\sim\mathcal{N}(0,I)$ — to merge the two noise terms.
3. Continue by induction to show

$$
x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1-\bar\alpha_t}\,\epsilon, \qquad \bar\alpha_t = \prod_{s=1}^{t}\alpha_s.
$$

**Acceptance:** A written derivation showing at least the two-step expansion and the noise-merging step explicitly, ending at the closed form. State in one sentence *why* this matters for training (you can jump to any $t$ in one shot — no iteration needed to build a training example).

---

## Part B — The simplified loss (10 min)

Write the simplified DDPM training loss in your own notation and answer:

1. What does the network $\epsilon_\theta$ take as input, and what does it output? (Two inputs, one output.)
2. Why is the loss just an MSE, and what is being regressed against what?
3. In one sentence: why does a *regression* loss produce a *multimodal* generator at sampling time? (Hint: the multimodality comes from the random starting noise + per-step noise selecting a mode, not from the loss.)

**Acceptance:** The loss written correctly ($\|\epsilon - \epsilon_\theta(\sqrt{\bar\alpha_t}x_0 + \sqrt{1-\bar\alpha_t}\epsilon,\ t)\|^2$) and all three answers.

---

## Part C — Numerical noising schedule (15 min)

Take $T = 4$ with $\beta = [0.1, 0.2, 0.3, 0.4]$. Compute by hand, showing every number:

1. $\alpha = 1 - \beta$ for each $t$.
2. The cumulative product $\bar\alpha_t = \prod_{s\le t}\alpha_s$ for $t = 1,2,3,4$.
3. For a scalar clean action $x_0 = 2.0$ and noise $\epsilon = 1.0$, the noised sample $x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1-\bar\alpha_t}\,\epsilon$ for each $t$.
4. Confirm $\bar\alpha_4$ is small (so $x_4$ is mostly noise) and $\bar\alpha_1$ is near $\alpha_1$ (so $x_1$ is mostly signal). State what this means for sampling (you start denoising from near-pure-noise).

**Acceptance:** The four $\bar\alpha_t$ values (≈ 0.9, 0.72, 0.504, 0.3024) and the four $x_t$ values, arithmetic shown.

---

## Part D — The DDIM clean-sample estimate and step count (15 min)

1. Given a noised sample $x_t$ and a noise prediction $\epsilon_\theta(x_t, t)$, derive the DDIM estimate of the clean sample by *solving the closed form for $x_0$*:

$$
\hat{x}_0 = \frac{x_t - \sqrt{1-\bar\alpha_t}\,\epsilon_\theta(x_t, t)}{\sqrt{\bar\alpha_t}}.
$$

Show the one line of algebra (it's just rearranging Part A's closed form for $x_0$).

2. Using your Part C $x_2 = 2.124$ (from $x_0=2.0$, $\epsilon=1.0$, $\bar\alpha_2=0.504$) and a *perfect* noise prediction $\epsilon_\theta = 1.0$, confirm $\hat{x}_0 = 2.0$ exactly. Then redo with an *imperfect* $\epsilon_\theta = 0.8$ and report the error in $\hat{x}_0$.

3. Explain in two sentences why DDIM can use ~16 steps where DDPM uses ~100, and why the step count is the **deployment latency knob** for a robot controller. (Reference: a robot controlling at 30 Hz cannot afford 100 forward passes per decision.)

**Acceptance:** The $\hat{x}_0$ derivation, the two numerical checks (perfect → 2.0, imperfect → a stated error), and the two-sentence latency explanation.

---

## Part E — Check yourself in numpy (optional, 5 min)

```python
import numpy as np
betas = np.array([0.1, 0.2, 0.3, 0.4])
alphas = 1 - betas
alpha_bar = np.cumprod(alphas)
print("alpha_bar:", np.round(alpha_bar, 4))   # expect [0.9, 0.72, 0.504, 0.3024]

x0, eps = 2.0, 1.0
xt = np.sqrt(alpha_bar) * x0 + np.sqrt(1 - alpha_bar) * eps
print("x_t:", np.round(xt, 4))

# DDIM clean-sample estimate at t=2 (index 1 -> alpha_bar=0.72; use t=2 = index 2 = 0.504):
ab = alpha_bar[2]
x0_hat = (xt[2] - np.sqrt(1 - ab) * eps) / np.sqrt(ab)
print("x0_hat (perfect eps):", round(x0_hat, 4))   # expect ~2.0
```

**Acceptance:** The printed `alpha_bar` matches your Part C; `x0_hat` with the perfect noise recovers ~2.0.

---

## Why this matters

The mini-project's hardest bug is "the policy barely moves" — almost always a normalization or a $\bar\alpha$/step-count mistake, and the engineers who debug it in minutes are the ones who can compute a noising schedule by hand and know what a healthy $\hat{x}_0$ looks like. You just did the calculation that makes those bugs obvious on sight.

When this feels comfortable, move to [Exercise 2 — A toy 1D diffusion model](exercise-02-toy-diffusion.py).
