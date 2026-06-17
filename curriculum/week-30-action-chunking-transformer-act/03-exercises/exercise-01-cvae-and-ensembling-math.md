# Exercise 1 — The CVAE and Ensembling Math on Paper

**Goal:** Make ACT's two pieces of math *yours*. You will derive the CVAE objective and the closed-form KL term, compute the KL for several latents (and find the posterior-collapse boundary), and compute the temporal-ensembling weights by hand. After this, `kl_divergence(mu, logvar)` and `exp(-m*i)` in the code read as obvious arithmetic.

**Estimated time:** 60 minutes. Paper, then a few lines of numpy.

---

## Part A — Derive the CVAE objective (15 min)

The VAE maximizes the ELBO. For ACT, everything is conditioned on the observation $o$, and the data is the action chunk $a$.

1. Write the ELBO for the conditional model $p(a\mid o) \ge \mathbb{E}_{q(z\mid o,a)}[\log p(a\mid o, z)] - D_{\mathrm{KL}}(q(z\mid o,a)\,\|\,p(z\mid o))$, with the prior $p(z\mid o) = \mathcal{N}(0, I)$.
2. Explain in one sentence why the **encoder** $q_\phi(z\mid o, a)$ is allowed to see the *demonstrated action chunk* $a$ at training time, and why that's fine even though it's unavailable at inference.
3. State the negated, minimized loss ACT uses: $\mathcal{L} = \text{L1}(a, \hat{a}(o,z)) + \beta\,D_{\mathrm{KL}}$, and explain what each term does and why ACT uses L1 (not L2) for reconstruction.

**Acceptance:** The ELBO written out, the one-sentence encoder justification (it's a training-time device; at inference $z=0$), and the loss with both terms explained.

---

## Part B — Derive the closed-form KL (10 min)

For a diagonal-Gaussian posterior $q(z) = \mathcal{N}(\mu, \sigma^2)$ and a standard-normal prior $\mathcal{N}(0, I)$, derive the per-dimension KL:

$$
D_{\mathrm{KL}}\big(\mathcal{N}(\mu, \sigma^2)\,\|\,\mathcal{N}(0,1)\big) = -\tfrac{1}{2}\big(1 + \log\sigma^2 - \mu^2 - \sigma^2\big).
$$

Start from the definition $D_{\mathrm{KL}} = \int q\log(q/p)$ and use the Gaussian moments $\mathbb{E}_q[z] = \mu$, $\mathbb{E}_q[z^2] = \mu^2 + \sigma^2$. Show the key steps.

**Acceptance:** The derivation reaching the closed form, with the moment substitutions shown. (You may cite the standard result for the integral of $\log$ of a Gaussian, but show how the $\mu^2$ and $\sigma^2$ terms appear.)

---

## Part C — Compute the KL and find the collapse boundary (15 min)

Compute the total KL (sum over dims) for these encoder outputs, showing arithmetic:

1. $\mu = [0.5, -1.0]$, $\log\sigma^2 = [0.0, -0.69]$ (so $\sigma^2 = [1.0, 0.5]$). (You should get ~0.72 nats — verify against Lecture 1 §6.)
2. $\mu = [0, 0]$, $\log\sigma^2 = [0, 0]$ (so $\sigma^2 = [1, 1]$). What is the KL, and what does it mean? (This is the *prior* — the collapsed state.)
3. $\mu = [3.0, 3.0]$, $\log\sigma^2 = [-4, -4]$ (a sharp, far-from-prior posterior). Compute the KL.

Then answer: with $\beta = 10$, compare the contribution of case (3)'s KL to a typical L1 reconstruction of ~0.3. Which term dominates? What happens to the latent if $\beta$ is set so high that the optimizer drives the posterior to case (2)?

**Acceptance:** The three KL values, and the explanation that case (2) is **posterior collapse** ($z$ carries no information; the decoder mode-averages) — and that too-large $\beta$ pushes the encoder toward it.

---

## Part D — Temporal-ensembling weights by hand (15 min)

At a given timestep, four overlapping chunks propose an action: ages $i = 0, 1, 2, 3$ (0 = freshest). Use decay $m = 0.1$ and weights $w_i = \exp(-m\cdot i)$.

1. Compute the four weights $w_0, w_1, w_2, w_3$ and the normalized weights $w_i / \sum_j w_j$.
2. Given the four proposed scalar actions $\hat{a}^{(0)} = 1.0$, $\hat{a}^{(1)} = 1.1$, $\hat{a}^{(2)} = 0.8$, $\hat{a}^{(3)} = 1.4$, compute the ensembled action $a = \sum_i w_i \hat{a}^{(i)} / \sum_i w_i$.
3. Now recompute with $m = 2.0$ (heavy decay) and with $m = 0.001$ (near-uniform). State which $m$ is more *reactive* (trusts the newest prediction) and which is *smoother* (averages all), and connect it to the jerk-vs-reactivity trade from Lecture 2 §1.3.

**Acceptance:** The weights and normalized weights for $m=0.1$, the ensembled action, and the recomputation showing $m=2.0$ ≈ "use the newest" (reactive) vs $m=0.001$ ≈ "average all" (smooth).

---

## Part E — Check yourself in numpy (optional, 5 min)

```python
import numpy as np

def kl(mu, logvar):
    return float(np.sum(-0.5 * (1 + logvar - mu**2 - np.exp(logvar))))

print("case 1 KL:", round(kl(np.array([0.5, -1.0]), np.array([0.0, -0.69])), 3))  # ~0.72
print("case 2 KL:", round(kl(np.array([0.0, 0.0]), np.array([0.0, 0.0])), 3))     # 0.0 (collapse)

m, ages = 0.1, np.arange(4)
w = np.exp(-m * ages)
acts = np.array([1.0, 1.1, 0.8, 1.4])
print("ensembled:", round(float((w * acts).sum() / w.sum()), 4))
```

**Acceptance:** `case 1 KL` ≈ 0.72, `case 2 KL` = 0.0, and the ensembled action matching your Part D hand calculation.

---

## Why this matters

The mini-project's two subtle failures are "ACT mode-averages like BC" (a $\beta$ / posterior-collapse problem) and "execution is jerky" (a temporal-ensembling $m$ problem). The engineers who fix them fast are the ones who can compute a KL by hand and know what collapse looks like in the numbers, and who can reason about the ensembling weights without running anything. You just did both calculations.

When this feels comfortable, move to [Exercise 2 — A miniature ACT](./exercise-02-act-cvae.py).
