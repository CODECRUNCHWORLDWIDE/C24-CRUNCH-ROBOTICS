#!/usr/bin/env python3
# Exercise 2 — A toy 1D diffusion model that learns a BIMODAL distribution
#
# Goal: Fill two marked TODOs to turn this scaffold into a working DDPM on a 1D
#       toy. The data is a MIXTURE of two Gaussians (modes at -2 and +2). A model
#       that minimizes MSE to predict the *mean* would collapse to ~0 (the invalid
#       middle). A diffusion model recovers BOTH modes. You will SEE the difference
#       in the output plot — this is the multimodal-action problem in miniature.
#
# Estimated time: 60 minutes. Runnable.
#
# THE TWO TODOs (search for "# TODO"):
#   TODO 1 — the closed-form noising x_t = sqrt(ab)*x0 + sqrt(1-ab)*eps (Lecture 1 §2.2)
#   TODO 2 — the simplified epsilon-prediction MSE loss (Lecture 1 §3)
#
# HOW TO RUN
#   pip install torch numpy matplotlib
#   python3 exercise-02-toy-diffusion.py        # writes toy_diffusion.png
#
# ACCEPTANCE CRITERIA
#   [ ] Both TODOs filled; the file runs and writes toy_diffusion.png.
#   [ ] The training loss falls (roughly from ~1.0 toward ~0.3-0.5; it won't hit 0 —
#       predicting noise has irreducible error).
#   [ ] The sampled-distribution histogram in the plot shows TWO peaks near -2 and +2
#       (the modes), NOT one peak at 0. A single peak at 0 means TODO 1 or 2 is wrong.
#   [ ] You can state why a plain MSE regressor would have predicted ~0 here.
#
# Expected output is at the bottom of the file.

import math

import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.manual_seed(0)
np.random.seed(0)

T = 100                                      # diffusion steps
N_TRAIN = 20000
EPOCHS = 2000
BATCH = 512
LR = 1e-3

# Noise schedule (linear betas) and the cumulative-product alpha_bar.
betas = torch.linspace(1e-4, 0.02, T)
alphas = 1.0 - betas
alpha_bar = torch.cumprod(alphas, dim=0)     # (T,)


def sample_data(n: int) -> torch.Tensor:
    """A bimodal target: half the mass at -2, half at +2 (each a tight Gaussian)."""
    modes = torch.where(torch.rand(n) < 0.5, -2.0, 2.0)
    return (modes + 0.25 * torch.randn(n)).unsqueeze(-1)     # (n, 1)


class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(-math.log(10000) * torch.arange(half) / (half - 1))
        args = t[:, None].float() * freqs[None]
        return torch.cat([torch.sin(args), torch.cos(args)], dim=-1)


class EpsNet(nn.Module):
    """Predicts the noise added to a 1D sample, given the sample and the timestep."""

    def __init__(self, hidden: int = 128, time_dim: int = 32):
        super().__init__()
        self.time_embed = SinusoidalTimeEmbedding(time_dim)
        self.net = nn.Sequential(
            nn.Linear(1 + time_dim, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        te = self.time_embed(t)
        return self.net(torch.cat([x, te], dim=-1))


def train() -> EpsNet:
    data = sample_data(N_TRAIN)
    model = EpsNet()
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    for epoch in range(EPOCHS):
        idx = torch.randint(0, N_TRAIN, (BATCH,))
        x0 = data[idx]                                       # (B, 1) clean samples
        t = torch.randint(0, T, (BATCH,))                    # random timestep per sample
        eps = torch.randn_like(x0)                           # the noise to predict
        ab = alpha_bar[t].unsqueeze(-1)                      # (B, 1)

        # TODO 1: the closed-form noising. Build x_t from x0, eps, and ab using
        #   x_t = sqrt(ab) * x0 + sqrt(1 - ab) * eps   (Lecture 1 §2.2).
        x_t = ...

        eps_pred = model(x_t, t)

        # TODO 2: the simplified DDPM loss — MSE between the predicted and true noise.
        #   loss = mean((eps_pred - eps)^2)   (Lecture 1 §3).
        loss = ...

        opt.zero_grad()
        loss.backward()
        opt.step()

        if epoch % 200 == 0:
            print(f"epoch {epoch:>4}  loss {loss.item():.4f}")
    return model


@torch.no_grad()
def ddpm_sample(model: EpsNet, n: int) -> torch.Tensor:
    """Generate n samples by running the reverse process T steps from pure noise."""
    x = torch.randn(n, 1)
    for t in reversed(range(T)):
        tt = torch.full((n,), t)
        eps = model(x, tt)
        a, ab, b = alphas[t], alpha_bar[t], betas[t]
        mean = (x - b / torch.sqrt(1 - ab) * eps) / torch.sqrt(a)
        x = mean + (torch.sqrt(b) * torch.randn_like(x) if t > 0 else 0.0)
    return x


def main() -> None:
    print("training a toy 1D diffusion model on a bimodal target (-2 and +2)...")
    model = train()

    real = sample_data(5000).squeeze(-1).numpy()
    gen = ddpm_sample(model, 5000).squeeze(-1).numpy()

    plt.figure(figsize=(7, 4))
    plt.hist(real, bins=80, density=True, alpha=0.5, label="real (bimodal)")
    plt.hist(gen, bins=80, density=True, alpha=0.5, label="diffusion samples")
    plt.axvline(0.0, color="r", ls="--", lw=1, label="MSE-regressor prediction (~0, WRONG)")
    plt.legend(); plt.title("Diffusion recovers both modes; an MSE regressor predicts the mean")
    plt.xlabel("x"); plt.tight_layout(); plt.savefig("toy_diffusion.png", dpi=110)
    print("wrote toy_diffusion.png")

    # Quantify: fraction of generated samples in each mode's basin.
    left = float((gen < -1).mean())
    right = float((gen > 1).mean())
    middle = float((np.abs(gen) <= 1).mean())
    print(f"generated mass:  left(~-2)={left:.2f}  right(~+2)={right:.2f}  middle(~0)={middle:.2f}")
    print("A plain MSE regressor would put ALL its mass at the middle (~0) — the invalid mean.")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed
# -----------------------------------------------------------------------------
#
# training a toy 1D diffusion model on a bimodal target (-2 and +2)...
# epoch    0  loss 1.0214
# epoch  200  loss 0.5132
# epoch  400  loss 0.4380
# ...
# epoch 1800  loss 0.3661
# wrote toy_diffusion.png
# generated mass:  left(~-2)=0.49  right(~+2)=0.48  middle(~0)=0.03
# A plain MSE regressor would put ALL its mass at the middle (~0) — the invalid mean.
#
# THE LESSON: the histogram has TWO peaks near -2 and +2. The diffusion model learned
# the bimodal distribution. A network trained to MINIMIZE MSE against this data would
# predict E[x] ~ 0 (the dashed red line) — squarely in the empty valley between the
# modes, which is exactly the WRONG action a Gaussian-MLP behavior-cloning policy
# outputs at a multimodal state (Lecture 1 §1). This 1D toy is that failure, visible.
#
# If your histogram has a SINGLE peak at 0: TODO 1 (noising) or TODO 2 (loss) is wrong —
# the model collapsed to predicting the mean instead of learning to denoise.
# -----------------------------------------------------------------------------
