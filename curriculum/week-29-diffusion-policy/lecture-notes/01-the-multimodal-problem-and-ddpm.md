# Lecture 1 — The Multimodal-Action Problem and DDPM: Why a Noise-Prediction Model Beats a Gaussian

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can state the multimodal-action problem precisely, derive the DDPM forward and reverse processes including the closed-form $q(x_t\mid x_0)$, write the simplified ε-prediction loss, and explain how DDIM produces the same samples in far fewer steps.

If you remember one sentence from this lecture, remember this one:

> **A Gaussian policy minimizing mean-squared error against multimodal demonstrations is forced to predict the *mean* of the modes — and the mean of two good actions is usually a bad action. Diffusion Policy escapes this because a denoising model can represent *any* distribution, not just a single blob.**

Week 27's behavior cloning trained a network to output an action given a state, by regressing toward the demonstrated action with MSE. Week 28's RL actor was a Gaussian too. Both share a hidden assumption: that the right action is *unimodal* — one blob with a mean and a spread. On real manipulation data, that assumption is false constantly, and this lecture is about why, and what to do instead.

---

## 1. The multimodal-action problem

Picture a robot pushing a T-shaped block to a goal (the canonical Diffusion Policy task). At a junction, two demonstrators did two different, *equally valid* things: one pushed from the left, one from the right. Your demonstration set contains both. Now you train a Gaussian-MLP behavior-cloning policy with MSE loss on this data. What does it learn at the junction?

It learns the **mean** of "push left" and "push right" — which is "push straight into the block's edge," a third action that *neither* demonstrator took and that *fails*. MSE regression, by its very definition, drives the prediction toward the conditional mean $\mathbb{E}[a\mid s]$. When $p(a\mid s)$ has two modes, that mean sits in the *valley between them*, where probability is low and behavior is bad.

This is not a tuning problem. You cannot fix it with a bigger network or more data or a lower learning rate — *more* data makes it worse, because it sharpens the two modes and deepens the valley the mean falls into. The problem is **representational**: a unimodal output distribution cannot represent a multimodal target, full stop.

The fixes people tried before diffusion:

- **Mixture density networks** (predict $K$ Gaussians + weights): works for a few modes but you must guess $K$, and training is unstable.
- **Action discretization** (bin the action space, predict a categorical — BeT): handles multimodality but loses precision and explodes in high dimensions.
- **Energy-based models / implicit BC** (learn an energy landscape, optimize at inference): expressive but training (contrastive, with negatives) is finicky.

**Diffusion Policy** is the approach that won, because diffusion models represent arbitrary distributions *and* train stably with a plain regression loss. To understand why, you have to understand DDPM.

---

## 2. DDPM: turning generation into denoising

A **denoising diffusion probabilistic model** learns to generate samples by reversing a gradual noising process. There are two processes: a fixed **forward** process that destroys data into noise, and a learned **reverse** process that reconstructs data from noise.

### 2.1 The forward (noising) process

Take a clean data point $x_0$ (for us, an action chunk). Over $T$ steps, add a little Gaussian noise each step according to a **variance schedule** $\beta_1, \dots, \beta_T$ (small, increasing values, e.g. $10^{-4}$ to $0.02$):

$$
q(x_t \mid x_{t-1}) = \mathcal{N}\!\big(x_t;\ \sqrt{1-\beta_t}\,x_{t-1},\ \beta_t I\big).
$$

Each step scales the previous sample down slightly and adds noise. After enough steps, $x_T$ is essentially pure standard Gaussian noise — all structure destroyed. This process has **no learnable parameters**; it's a fixed corruption.

### 2.2 The closed form (the trick that makes training cheap)

You do *not* want to apply $t$ noising steps one at a time during training. The beautiful property of Gaussian noising is that you can jump to any timestep $t$ in **one shot**. Define $\alpha_t = 1-\beta_t$ and $\bar\alpha_t = \prod_{s=1}^t \alpha_s$. Then:

$$
q(x_t \mid x_0) = \mathcal{N}\!\big(x_t;\ \sqrt{\bar\alpha_t}\,x_0,\ (1-\bar\alpha_t)I\big),
$$

which means you can sample $x_t$ directly with the reparameterization

$$
x_t = \sqrt{\bar\alpha_t}\,x_0 + \sqrt{1-\bar\alpha_t}\,\epsilon, \qquad \epsilon \sim \mathcal{N}(0, I).
$$

Read this carefully — it's the engine of the whole method. To make a training example at timestep $t$, you sample one $\epsilon$, scale the clean action by $\sqrt{\bar\alpha_t}$, add $\sqrt{1-\bar\alpha_t}\,\epsilon$, and you have $x_t$. As $t\to T$, $\bar\alpha_t\to 0$ and $x_t\to\epsilon$ (pure noise); at $t=0$, $\bar\alpha_0 = 1$ and $x_t = x_0$ (clean). Exercise 1 makes you derive this closed form from the per-step recursion — do it, because it's where the $\bar\alpha$ comes from and why training needs no iteration.

### 2.3 The reverse (denoising) process

Generation runs the process *backward*: start from noise $x_T \sim \mathcal{N}(0,I)$ and iteratively denoise toward $x_0$. The reverse step is also Gaussian (for small $\beta_t$), with a mean we must *learn*:

$$
p_\theta(x_{t-1}\mid x_t) = \mathcal{N}\!\big(x_{t-1};\ \mu_\theta(x_t, t),\ \Sigma_t\big).
$$

DDPM's key reparameterization (Ho et al.): instead of predicting the mean directly, **predict the noise $\epsilon$ that was added**. A network $\epsilon_\theta(x_t, t)$ takes the noisy sample and the timestep and outputs its estimate of $\epsilon$. Given $\epsilon_\theta$, the reverse mean has a closed form:

$$
\mu_\theta(x_t, t) = \frac{1}{\sqrt{\alpha_t}}\left( x_t - \frac{\beta_t}{\sqrt{1-\bar\alpha_t}}\,\epsilon_\theta(x_t, t) \right).
$$

You don't need to memorize that formula — the library (`diffusers`' scheduler) computes it. What you must internalize: **the network's only job is to predict the noise.** Everything else is fixed schedule arithmetic.

---

## 3. The training loss (one line, and it's just MSE)

Here is the payoff. After the full variational derivation, Ho et al. show the training objective simplifies to a plain mean-squared error between the true noise and the predicted noise:

$$
L_{\text{simple}} = \mathbb{E}_{x_0,\ t,\ \epsilon}\Big[ \big\| \epsilon - \epsilon_\theta\big(\sqrt{\bar\alpha_t}\,x_0 + \sqrt{1-\bar\alpha_t}\,\epsilon,\ t\big) \big\|^2 \Big].
$$

That's the whole loss. Sample a clean datum $x_0$, sample a random timestep $t\sim\text{Uniform}(1,T)$, sample noise $\epsilon$, form $x_t$ via the closed form, ask the network to predict $\epsilon$, and minimize the squared error. In PyTorch:

```python
def diffusion_loss(model, x0, alpha_bar, T):
    """x0: (B, ...) clean data. alpha_bar: precomputed cumulative-product schedule
    of length T. Returns the simplified DDPM training loss."""
    B = x0.shape[0]
    t = torch.randint(0, T, (B,), device=x0.device)           # random timestep per sample
    eps = torch.randn_like(x0)                                 # the noise to predict
    ab = alpha_bar[t].view(B, *([1] * (x0.dim() - 1)))         # broadcast to x0's shape
    x_t = torch.sqrt(ab) * x0 + torch.sqrt(1 - ab) * eps       # the closed-form noising
    eps_pred = model(x_t, t)                                   # network predicts the noise
    return torch.nn.functional.mse_loss(eps_pred, eps)
```

Notice what is *not* here: no adversarial game (unlike GANs), no contrastive negatives (unlike EBMs), no mode-count guess (unlike MDNs). It's regression. That stability is *why* diffusion won the multimodal-policy contest — you get the expressiveness of an arbitrary distribution with the training simplicity of MSE. The expressiveness comes from the *iterative* sampling, not from a complicated loss.

### Why this represents multimodality

Here is the intuition for why a regression loss yields a multimodal generator. At a multimodal state, the *clean* actions $x_0$ in your batch are sometimes "left" and sometimes "right." For a heavily-noised $x_t$ (large $t$), both look like noise and the network learns to denoise toward the *overall* structure. But as sampling proceeds to small $t$, the network's prediction depends sharply on *which* noisy sample it's denoising — a sample that's drifted toward "left" gets denoised further left; one that drifted "right" goes right. The randomness of the starting noise $x_T$ and the per-step noise *selects a mode*, and the network commits to it. Run sampling 512 times from different noise seeds and you get a *distribution* over outputs — two clusters, not one mean. That's the multimodality the Gaussian-MLP could never produce, and you'll watch it happen in Exercise 2 on a 1D bimodal toy.

---

## 4. Sampling: DDPM vs DDIM

### 4.1 DDPM sampling (the slow, stochastic one)

To generate, start from $x_T\sim\mathcal{N}(0,I)$ and apply the reverse step $T$ times, adding a bit of fresh noise at each step (it's a *stochastic* process):

```python
@torch.no_grad()
def ddpm_sample(model, shape, betas, device):
    alphas = 1.0 - betas
    alpha_bar = torch.cumprod(alphas, dim=0)
    x = torch.randn(shape, device=device)                     # start from pure noise
    for t in reversed(range(len(betas))):
        eps = model(x, torch.full((shape[0],), t, device=device))
        a, ab, b = alphas[t], alpha_bar[t], betas[t]
        mean = (x - b / torch.sqrt(1 - ab) * eps) / torch.sqrt(a)
        if t > 0:
            x = mean + torch.sqrt(b) * torch.randn_like(x)    # stochastic step
        else:
            x = mean                                          # last step is the clean sample
    return x
```

The problem for robots: $T$ is typically **100** (or more). Running 100 network forward passes for *every* control decision is far too slow for a real-time loop. A robot deciding at 10 Hz cannot afford a 100-step denoise per decision. This is where DDIM saves the method.

### 4.2 DDIM sampling (the fast, deterministic one)

**DDIM** (Song et al.) reformulates the reverse process as **non-Markovian and deterministic**: it produces samples whose *marginal distributions match DDPM's* but lets you take **large strides** through the timestep schedule — denoise in 10–16 steps instead of 100, with negligible quality loss. The DDIM update, given the noise prediction, first estimates the clean sample $\hat{x}_0$ and then jumps to the next (sub-sampled) timestep:

$$
\hat{x}_0 = \frac{x_t - \sqrt{1-\bar\alpha_t}\,\epsilon_\theta(x_t, t)}{\sqrt{\bar\alpha_t}}, \qquad
x_{t-1} = \sqrt{\bar\alpha_{t-1}}\,\hat{x}_0 + \sqrt{1-\bar\alpha_{t-1}}\,\epsilon_\theta(x_t, t).
$$

(The fully general DDIM has a stochasticity knob $\eta$; $\eta=0$ is the deterministic case we use, $\eta=1$ recovers DDPM.) The two practical consequences:

- **Determinism**: same noise seed → same action. For a controller this is a *feature* — reproducible, no per-step jitter. (Contrast SAC, where you *wanted* stochasticity for exploration; at *deployment* you want determinism.)
- **Few steps**: the denoising step count becomes a **latency knob** you tune. Fewer steps = faster inference = more reactive controller, traded against a little sample quality. This is the single most important deployment decision for Diffusion Policy, and you'll tune it directly in the mini-project.

```python
@torch.no_grad()
def ddim_sample(model, shape, alpha_bar, device, n_steps=16):
    """Deterministic DDIM. Sub-sample the timestep schedule into n_steps strides."""
    T = len(alpha_bar)
    step_seq = torch.linspace(T - 1, 0, n_steps).long()       # e.g. 16 strides over 100
    x = torch.randn(shape, device=device)
    for i in range(n_steps):
        t = step_seq[i]
        t_next = step_seq[i + 1] if i + 1 < n_steps else torch.tensor(0)
        ab_t = alpha_bar[t]
        ab_next = alpha_bar[t_next] if t_next > 0 else torch.tensor(1.0, device=device)
        eps = model(x, torch.full((shape[0],), t, device=device))
        x0_pred = (x - torch.sqrt(1 - ab_t) * eps) / torch.sqrt(ab_t)   # estimate clean
        x = torch.sqrt(ab_next) * x0_pred + torch.sqrt(1 - ab_next) * eps  # jump
    return x
```

---

## 5. The timestep embedding

The network needs to know *which* noise level it's denoising — denoising at $t=95$ (almost pure noise) is a different job than at $t=3$ (almost clean). The timestep $t$ is fed in via a **sinusoidal position embedding** (the same idea as transformer positions), passed through a small MLP, and injected into the network. You'll see this in every diffusion backbone:

```python
class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(
            -math.log(10000) * torch.arange(half, device=t.device) / (half - 1)
        )
        args = t[:, None].float() * freqs[None]
        return torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
```

The timestep embedding is what lets a *single* network handle all noise levels — without it, you'd need $T$ separate networks. It's small but load-bearing; forget it and the model can't tell coarse denoising from fine.

---

## 6. The noise schedule, and why it matters

The $\beta_t$ schedule (how much noise is added per forward step) is a *design choice*, not a learned quantity, and it has real consequences for sample quality:

- **Linear schedule** (Ho et al.'s original): $\beta_t$ rises linearly from a small value (e.g. $10^{-4}$) to a larger one (e.g. $0.02$) over $T$ steps. Simple and the default for many policy applications.
- **Cosine schedule** (Nichol & Dhariwal): $\bar\alpha_t$ follows a cosine curve so noise is added more gradually at the start and end. This keeps more *signal* in the middle timesteps, which empirically improves sample quality — useful when the action dimension is small (a few joints) and every bit of structure matters.

The practical guidance: **start with whatever your library's scheduler defaults to** (`diffusers`' `DDPMScheduler` defaults are sensible), and only tune the schedule if sample quality is your bottleneck. For Diffusion Policy on low-dimensional actions, the schedule is rarely the thing that's broken — normalization and the DDIM step count are far more common culprits. But know that the schedule is a knob, because the first time someone says "we switched to a cosine schedule and it helped," you want to know what they changed.

One non-obvious consequence: the schedule and the number of *training* timesteps $T$ are coupled to the number of *sampling* steps. You train with $T = 100$ (say), and at inference you can use all 100 (DDPM) or sub-sample to 16 (DDIM). But if you trained with $T = 10$, you can't sample with 50 — you can only ever sub-sample *down* from the training $T$, never up. So train with a reasonably large $T$ (100 is standard) to keep your sampling-step options open, then choose the deployment step count by the latency budget.

---

## 7. Where diffusion sits among generative models

It's worth one paragraph to place diffusion against the other generative families you may know, because the comparison clarifies *why* it won the policy contest:

- **GANs** generate in one shot (fast) but train via an adversarial game that is notoriously unstable and prone to mode *collapse* — exactly the failure you can't afford in a multimodal policy. Diffusion trades GAN's one-shot speed for multi-step sampling, but buys stable training and full mode coverage.
- **VAEs** train stably and cover modes, but tend to produce blurry/averaged samples because of the Gaussian decoder and the reconstruction objective — a softer version of the same mode-averaging problem. (ACT, next week, uses a *conditional* VAE and works around this with the latent + chunking; it's a different trade.)
- **Normalizing flows** give exact likelihoods but constrain the architecture (invertible layers), limiting expressiveness.
- **Autoregressive models** generate one dimension at a time — accurate but slow for high-dimensional, continuous action chunks.

Diffusion's niche: **stable regression training (like a VAE) + full mode coverage (unlike a GAN) + arbitrary-distribution expressiveness (unlike a Gaussian)**, at the cost of multi-step sampling (which DDIM then mostly buys back). For a robot policy that must represent multimodal actions and train without babysitting, that's the winning combination — and it's why the field converged on it.

---

## 8. The score-matching view (one paragraph that makes DDIM click)

There's a deeper way to see what the network learns, and it pays off when you read the DDIM math. The noise prediction $\epsilon_\theta(x_t, t)$ is, up to a scale factor, an estimate of the **score** — the gradient of the log-density of the noised data, $\nabla_{x_t}\log q(x_t)$. Specifically, $\nabla_{x_t}\log q(x_t) \approx -\epsilon_\theta(x_t,t)/\sqrt{1-\bar\alpha_t}$. The score points "uphill" toward higher-density (more data-like) regions. So denoising is **gradient ascent on the data log-density**: each reverse step nudges the sample toward where real data lives. This is why diffusion covers all the modes — the score field has a "hill" at *each* mode, and which hill a sample climbs depends on where its noise put it. It's also the unifying view (score-based generative modeling, Yang Song) that makes DDIM's deterministic trajectory natural: DDIM is following the score field's *probability-flow ODE* deterministically, rather than the noisy stochastic process DDPM follows. You don't need this to implement Diffusion Policy, but it's the sentence that makes a senior practitioner nod, and it demystifies why the same trained network supports both samplers.

---

## 9. Practical training details that decide whether it works

The math is clean; the practice has a handful of details that separate a working Diffusion Policy from one that "trains but doesn't act":

- **Normalize the data.** The forward process drives data toward $\mathcal{N}(0,I)$, so the model assumes your actions are roughly unit-scale. Normalize actions to ~$[-1,1]$ (per-dimension min-max or standardization) before training, and *un-normalize* sampled actions before sending them to the robot. The most common "the policy barely moves" bug is a forgotten un-normalization at deploy.
- **Choose $T$ generously.** Train with $T=100$ (standard) so you can sub-sample to any DDIM step count at inference. You can't sample with more steps than you trained with.
- **EMA the weights.** Keep an exponential-moving-average copy of the network weights and *sample* from the EMA, not the live weights. Diffusion models are notoriously improved by weight EMA — it's nearly free and consistently helps sample quality. (LeRobot and the reference repo both do this by default.)
- **Predict $\epsilon$, $x_0$, or $v$.** We derived $\epsilon$-prediction (the original). Some implementations predict the clean sample $x_0$ directly, or a "velocity" $v$ parameterization; they're equivalent in principle but differ in numerical conditioning. For low-dimensional robot actions, $\epsilon$-prediction is the standard and what your exercises use — just know the alternatives exist when you read library code.
- **Watch the sample, not the loss.** A falling diffusion loss does *not* guarantee good samples — the loss is an average over all noise levels, and a model can have a low average loss while sampling poorly. Periodically *sample* during training and look at the output distribution; that's the ground truth.

---

## 10. A worked numerical example (you'll redo this in Exercise 1)

Take $T = 4$ with a linear $\beta$ schedule $\beta = [0.1, 0.2, 0.3, 0.4]$. Then $\alpha = [0.9, 0.8, 0.7, 0.6]$ and the cumulative product $\bar\alpha = [0.9,\ 0.72,\ 0.504,\ 0.3024]$. Now take a scalar clean action $x_0 = 2.0$ and a noise draw $\epsilon = 1.0$. The closed-form noised sample at $t=2$ (using 0-indexed $\bar\alpha_2 = 0.504$):

$$
x_2 = \sqrt{0.504}\cdot 2.0 + \sqrt{1-0.504}\cdot 1.0 = 0.710\cdot 2.0 + 0.704\cdot 1.0 = 1.420 + 0.704 = 2.124.
$$

If the network predicted $\epsilon_\theta(x_2, 2) = 0.9$ (close to the true 1.0), the loss contribution is $(1.0 - 0.9)^2 = 0.01$. And the estimated clean sample for a DDIM step would be $\hat{x}_0 = (2.124 - 0.704\cdot 0.9)/0.710 = (2.124 - 0.634)/0.710 = 2.099$ — close to the true $x_0 = 2.0$, as it should be when the noise prediction is good. Exercise 1 makes you do this across all four timesteps and confirm $\bar\alpha_T$ is near zero so $x_T$ is near pure noise.

Here is the noising across all four timesteps, so you can see the signal fade:

| $t$ | $\bar\alpha_t$ | $\sqrt{\bar\alpha_t}$ (signal weight) | $\sqrt{1-\bar\alpha_t}$ (noise weight) | $x_t = \sqrt{\bar\alpha_t}\cdot 2.0 + \sqrt{1-\bar\alpha_t}\cdot 1.0$ |
|---:|---:|---:|---:|---:|
| 1 | 0.900 | 0.949 | 0.316 | 2.214 |
| 2 | 0.720 | 0.849 | 0.529 | 2.227 |
| 3 | 0.504 | 0.710 | 0.704 | 2.124 |
| 4 | 0.302 | 0.550 | 0.836 | 1.936 |

Watch the two weight columns trade places: at $t=1$ the signal weight (0.949) dwarfs the noise weight (0.316) — $x_1$ is almost the clean action. By $t=4$ the noise weight (0.836) exceeds the signal weight (0.550) — $x_4$ is more noise than signal. Push $T$ higher (100 in practice) and $\bar\alpha_T \to 0$, so $x_T$ is *pure* noise, which is exactly why sampling can start from $\mathcal{N}(0,I)$: by the final forward timestep, all trace of the original action is gone, and the reverse process has to reconstruct it from nothing but the learned denoiser. The whole method hinges on this fade being *gradual* and *reversible* — each forward step removes a little structure that the matched reverse step can learn to put back.

A note on the reverse direction with these numbers: starting from $x_4 = 1.936$ and a good noise prediction, the first reverse step estimates $\hat{x}_0 = (1.936 - 0.836\cdot 1.0)/0.550 = 2.0$ — it recovers the clean action immediately *when the prediction is perfect*. In reality the prediction is imperfect at every step, which is why you take *several* steps: each step corrects a little, and the iteration converges toward a clean sample. DDIM is the art of taking *few, well-chosen* steps instead of all $T$.

---

## 11. Frequently-tangled points (clear them up now)

A few questions that reliably confuse people the first time, answered crisply:

- **"Is the noise different at each diffusion step?"** During *training*, you sample one $\epsilon$ and one timestep $t$ per example — you don't iterate. During *DDPM sampling*, yes, fresh noise is added at each reverse step (it's stochastic). During *DDIM sampling*, no — it's deterministic; the only randomness is the initial $x_T$.
- **"Does the model see the timestep?"** Yes, always — via the sinusoidal embedding. Denoising at high noise (large $t$) is a coarser job than at low noise (small $t$); the same network handles both *because* it's told which $t$ it's at.
- **"Why predict noise instead of the clean action?"** They're mathematically interchangeable (you can convert between $\epsilon$-prediction, $x_0$-prediction, and $v$-prediction). $\epsilon$-prediction was the original and tends to be well-conditioned across noise levels. The choice is a numerical-stability preference, not a capability difference.
- **"How is this different from just adding dropout/noise to a regressor?"** Fundamentally. A noisy regressor still has a *unimodal* output distribution (one mean, some spread). Diffusion's output distribution is *arbitrary* — it can have two sharp modes with empty space between, which is exactly what the multimodal-action problem demands and what no amount of regressor noise gives you.
- **"Is more diffusion steps always better quality?"** Up to a point. Quality rises with steps and then saturates — often by ~16 DDIM steps for low-dimensional actions. Past saturation you're paying latency for nothing. This is why the step count is a *tuned* knob, not "set it as high as you can."

If any of these were fuzzy, re-read the relevant section — they're the conceptual handholds the exercises assume.

---

## 12. The complete training loop, in one place

To consolidate, here is the entire DDPM training procedure as runnable pseudocode — every line maps to a piece of the math above, and it's the spine of Exercise 2:

```python
# Precompute the schedule once.
betas = torch.linspace(1e-4, 0.02, T)          # the variance schedule
alphas = 1.0 - betas
alpha_bar = torch.cumprod(alphas, dim=0)        # the cumulative product (§2.2)

for step in range(num_train_steps):
    x0 = sample_clean_data(batch_size)          # clean actions (or action chunks)
    t = torch.randint(0, T, (batch_size,))      # a random timestep per example
    eps = torch.randn_like(x0)                  # the noise to predict

    # The closed-form one-shot noising (§2.2): jump straight to timestep t.
    ab = alpha_bar[t].view(batch_size, *([1] * (x0.dim() - 1)))
    x_t = torch.sqrt(ab) * x0 + torch.sqrt(1 - ab) * eps

    eps_pred = model(x_t, t)                     # the network predicts the noise
    loss = F.mse_loss(eps_pred, eps)            # the simplified loss (§3)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    ema.update(model)                            # EMA the weights for sampling (§9)
```

Five lines of actual algorithm (the schedule, the timestep draw, the noising, the prediction, the MSE), wrapped in standard training boilerplate. There is no adversarial step, no contrastive negative, no mode-count to guess. *That* is the simplicity that, combined with the multi-step sampling's expressiveness, made diffusion the method that solved the multimodal-policy problem. When you write Exercise 2, you'll fill in exactly the two load-bearing lines — the noising and the loss — and watch a bimodal distribution emerge from this loop.

---

## 11. Recap

You should now be able to:

- State the multimodal-action problem and explain why MSE-regressed BC predicts the (invalid) mean of multimodal demos — a *representational* failure, not a tuning one.
- Write the DDPM forward process and derive the closed-form $q(x_t\mid x_0)$ with $\bar\alpha_t$.
- Explain ε-prediction and write the simplified MSE training loss, and articulate why a regression loss yields a multimodal generator.
- Run DDPM sampling and explain why its ~100 steps are too slow for control.
- Use DDIM to sample deterministically in 10–16 steps, and explain why the step count is the deployment latency knob.
- Explain the role of the sinusoidal timestep embedding.

Next: how this denoising machinery becomes a *robot policy* — conditioning on observations, predicting action chunks, executing receding-horizon, and deploying inside a real-time ROS2 control loop. Continue to [Lecture 2 — Diffusion Policy: Chunking, Receding Horizon, and Deployment](./02-diffusion-policy-chunking-and-deployment.md).

---

## References

- *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion* — Chi et al. (2023): <https://arxiv.org/abs/2303.04137>
- *Denoising Diffusion Probabilistic Models* — Ho, Jain, Abbeel (2020): <https://arxiv.org/abs/2006.11239>
- *Denoising Diffusion Implicit Models* — Song, Meng, Ermon (2021): <https://arxiv.org/abs/2010.02502>
- *Implicit Behavioral Cloning* — Florence et al. (2022): <https://arxiv.org/abs/2109.00137>
- *Lilian Weng — What are Diffusion Models?*: <https://lilianweng.github.io/posts/2021-07-11-diffusion-models/>
- *The Annotated Diffusion Model* (Hugging Face): <https://huggingface.co/blog/annotated-diffusion>
