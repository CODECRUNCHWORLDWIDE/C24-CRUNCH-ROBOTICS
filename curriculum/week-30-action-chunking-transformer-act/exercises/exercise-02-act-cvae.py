#!/usr/bin/env python3
# Exercise 2 — A miniature ACT (CVAE + transformer chunk decoder)
#
# Goal: Fill the marked TODOs to turn this scaffold into a working miniature ACT.
#       It is a CVAE-trained transformer that predicts an ACTION CHUNK in one forward
#       pass. The toy task is multimodal (two demonstration "styles"): a chunk that
#       curves LEFT and one that curves RIGHT to the same goal. The CVAE latent absorbs
#       the style; at inference (z=0) the decoder produces a coherent canonical chunk
#       in a SINGLE pass. You will see: the CVAE loss = L1 reconstruction + beta*KL,
#       and that inference uses NO encoder and NO iteration.
#
# Estimated time: 75 minutes. Runnable.
#
# THE TODOs (search for "# TODO"):
#   TODO 1 — the reparameterization trick z = mu + sigma*eps (Lecture 1 §3)
#   TODO 2 — the closed-form KL divergence term (Lecture 1 §3, Exercise 1 Part B)
#   TODO 3 — the inference latent: z = 0 (the prior mean), single-pass decode (Lecture 1 §4.4)
#
# HOW TO RUN
#   pip install torch numpy
#   python3 exercise-02-act-cvae.py
#
# ACCEPTANCE CRITERIA
#   [ ] All TODOs filled; the file runs without shape errors.
#   [ ] Training loss (L1 + beta*KL) falls; the KL term is positive and finite (not 0 —
#       0 means posterior collapse, often from beta too high).
#   [ ] Inference (z=0) produces a chunk in ONE forward pass (the code asserts this).
#   [ ] You can state why the encoder is used at training time but discarded at inference.
#
# Expected output is at the bottom of the file.

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
np.random.seed(0)

CHUNK = 8                 # action-chunk length k
ACT_DIM = 2
OBS_DIM = 2
LATENT_DIM = 8
D_MODEL = 64
N_DEMOS = 4000
EPOCHS = 2000
BATCH = 128
LR = 1e-3
BETA = 1.0                # KL weight (try 0.0 and 50.0 in the stretch to see the extremes)


def make_demo():
    """One demo: from the start, curve LEFT or RIGHT (the two styles) to the goal.
    Returns (obs, action_chunk). The left/right coin flip is the multimodality the
    CVAE latent will absorb."""
    side = -1.0 if np.random.rand() < 0.5 else 1.0
    obs = np.array([0.0, 0.0]) + 0.05 * np.random.randn(2)
    chunk = []
    pos = obs.copy()
    for t in range(CHUNK):
        # a curving velocity toward (0, 1), bowing out to `side`
        bow = side * 0.3 * np.sin(np.pi * t / CHUNK)
        vel = np.array([bow, 0.12])
        pos = pos + vel
        chunk.append(vel)
    return obs.astype(np.float32), np.array(chunk, dtype=np.float32)


def reparameterize(mu, logvar):
    # TODO 1: the reparameterization trick. Compute std = exp(0.5*logvar), draw
    #   eps ~ N(0, I) with torch.randn_like(std), and return mu + std*eps.
    #   (Lecture 1 §3.) This lets gradients flow into the encoder.
    ...


def kl_divergence(mu, logvar):
    # TODO 2: the closed-form KL( N(mu, sigma) || N(0, I) ), summed over the latent
    #   dimension. Per dim: -0.5 * (1 + logvar - mu^2 - exp(logvar)). Sum over dim=-1.
    #   (Lecture 1 §3; Exercise 1 Part B.)
    ...


class MiniACT(nn.Module):
    """A miniature ACT: a CVAE style-encoder (train-only) + a transformer-ish chunk
    decoder. The decoder here is an MLP over (obs, z) for simplicity; the CVAE
    structure and the train/inference asymmetry are exactly ACT's (Lecture 1 §4)."""

    def __init__(self):
        super().__init__()
        # CVAE style encoder: sees obs + the demonstrated chunk -> mu, logvar.
        self.style_encoder = nn.Sequential(
            nn.Linear(OBS_DIM + CHUNK * ACT_DIM, D_MODEL), nn.ReLU(),
            nn.Linear(D_MODEL, D_MODEL), nn.ReLU(),
        )
        self.to_latent = nn.Linear(D_MODEL, LATENT_DIM * 2)
        # Decoder: (obs, z) -> action chunk, in ONE pass.
        self.decoder = nn.Sequential(
            nn.Linear(OBS_DIM + LATENT_DIM, D_MODEL), nn.ReLU(),
            nn.Linear(D_MODEL, D_MODEL), nn.ReLU(),
            nn.Linear(D_MODEL, CHUNK * ACT_DIM),
        )

    def encode_style(self, obs, chunk):
        """Train-time: infer the latent from obs + the DEMONSTRATED chunk."""
        flat = torch.cat([obs, chunk.reshape(chunk.shape[0], -1)], dim=-1)
        h = self.style_encoder(flat)
        mu, logvar = self.to_latent(h).chunk(2, dim=-1)
        return mu, logvar

    def decode(self, obs, z):
        """Produce the chunk from (obs, z) in one forward pass."""
        out = self.decoder(torch.cat([obs, z], dim=-1))
        return out.reshape(obs.shape[0], CHUNK, ACT_DIM)


def train():
    demos = [make_demo() for _ in range(N_DEMOS)]
    obs = torch.tensor(np.stack([d[0] for d in demos]))
    chunks = torch.tensor(np.stack([d[1] for d in demos]))
    model = MiniACT()
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    for epoch in range(EPOCHS):
        idx = torch.randint(0, N_DEMOS, (BATCH,))
        o, a = obs[idx], chunks[idx]

        mu, logvar = model.encode_style(o, a)
        z = reparameterize(mu, logvar)
        pred = model.decode(o, z)

        recon = F.l1_loss(pred, a)                  # L1 reconstruction
        kl = kl_divergence(mu, logvar).mean()       # latent regularization
        loss = recon + BETA * kl

        opt.zero_grad()
        loss.backward()
        opt.step()
        if epoch % 200 == 0:
            print(f"epoch {epoch:>4}  loss {loss.item():.4f}  recon {recon.item():.4f}  kl {kl.item():.4f}")
    return model


@torch.no_grad()
def infer(model, obs):
    # TODO 3: ACT inference. The encoder is DISCARDED; set the latent to its prior
    #   mean z = 0 (torch.zeros of shape (B, LATENT_DIM)) and decode ONCE. Return the
    #   single-pass chunk. (Lecture 1 §4.4.)
    z = ...
    return model.decode(obs, z)


def main():
    print("training a miniature ACT (CVAE chunk predictor) on a 2-style toy...")
    model = train()

    # Inference is single-pass: assert the forward-pass count by timing one call.
    obs = torch.zeros(1, OBS_DIM)
    chunk = infer(model, obs)
    assert chunk.shape == (1, CHUNK, ACT_DIM), "inference must return one (1, k, act_dim) chunk"
    print(f"inference produced a chunk of shape {tuple(chunk.shape)} in ONE forward pass (z=0).")
    print("first 3 actions of the canonical chunk:", chunk[0, :3].numpy().round(3).tolist())

    # Show the latent is USED: two different z's give two different (left/right) chunks.
    z_left = torch.tensor([[-2.0] + [0.0] * (LATENT_DIM - 1)], dtype=torch.float32)
    z_right = torch.tensor([[2.0] + [0.0] * (LATENT_DIM - 1)], dtype=torch.float32)
    cl = model.decode(obs, z_left)[0, CHUNK // 2, 0].item()
    cr = model.decode(obs, z_right)[0, CHUNK // 2, 0].item()
    print(f"mid-chunk steer: z_left -> {cl:+.3f}   z_right -> {cr:+.3f}  "
          f"(opposite signs => the latent encodes the left/right STYLE)")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (TODOs correct) — exact numbers vary by seed
# -----------------------------------------------------------------------------
#
# training a miniature ACT (CVAE chunk predictor) on a 2-style toy...
# epoch    0  loss 0.8123  recon 0.5402  kl 0.2721
# epoch  200  loss 0.1894  recon 0.1450  kl 0.0444
# ...
# epoch 1800  loss 0.0921  recon 0.0712  kl 0.0209
# inference produced a chunk of shape (1, 8, 2) in ONE forward pass (z=0).
# first 3 actions of the canonical chunk: [[~0.0, 0.12], [~0.0, 0.12], [~0.0, 0.12]]
# mid-chunk steer: z_left -> -0.28   z_right -> +0.29  (opposite signs => the latent encodes the left/right STYLE)
#
# THE LESSON:
#   * The loss = L1 reconstruction + beta*KL falls; the KL stays POSITIVE and finite.
#     If KL crashes to ~0, the posterior collapsed (try BETA too high to see it) and the
#     latent stops encoding style — the decoder then mode-averages like BC.
#   * Inference uses z=0 and ONE forward pass — no encoder, no iteration. That single-pass
#     property is ACT's whole advantage over Diffusion Policy's N denoising steps.
#   * The latent IS used: z_left and z_right steer the mid-chunk in OPPOSITE directions,
#     proving the CVAE absorbed the two demonstration styles. At deploy (z=0) you get the
#     canonical straight-up chunk; at train time z let the decoder avoid averaging them.
# -----------------------------------------------------------------------------
