# Week 30 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 31. Answer key is at the bottom — don't peek.

---

**Q1.** How does action chunking fight compounding error in imitation learning?

- A) It makes the network larger so it memorizes more.
- B) Predicting $k$ actions per inference means the policy only re-decides every $k$ steps, shrinking the effective horizon from $H$ to $H/k$ — $k\times$ fewer opportunities to compound error.
- C) It adds a reward signal.
- D) It removes the need for demonstrations.

---

**Q2.** Why is ACT trained as a CVAE rather than a plain chunk-regressing transformer?

- A) CVAEs train faster.
- B) A plain L1/L2 regressor mode-averages multimodal demonstration styles; the CVAE latent $z$ absorbs the style so that, conditioned on $z$, the chunk regression is well-posed.
- C) CVAEs don't need a GPU.
- D) The transformer requires a latent variable to function.

---

**Q3.** At ACT *inference* time, what happens to the CVAE encoder and the latent?

- A) The encoder runs and samples a random $z$.
- B) The encoder is discarded; the latent is set to the prior mean $z = 0$, and the decoder produces the chunk in one forward pass.
- C) The encoder runs but the latent is ignored.
- D) Both encoder and decoder run iteratively.

---

**Q4.** The ACT training loss is L1 reconstruction + $\beta\cdot$KL. What does the KL term do?

- A) It speeds up the reconstruction.
- B) It pulls the encoder's posterior $q(z\mid o,a)$ toward the prior $\mathcal{N}(0,I)$, regularizing the latent so that $z=0$ at inference is meaningful.
- C) It computes the action chunk directly.
- D) It replaces the reconstruction loss.

---

**Q5.** What is posterior collapse, and when does it happen?

- A) When the GPU runs out of memory.
- B) When $\beta$ is too high: the KL dominates, the posterior collapses onto the prior, $z$ carries no information, and the decoder mode-averages like plain BC.
- C) When the learning rate is too low.
- D) When the chunk size exceeds the horizon.

---

**Q6.** Why does ACT use the reparameterization trick ($z = \mu + \sigma\epsilon$)?

- A) To make sampling faster.
- B) So gradients can flow back into the encoder through the sampled latent — a plain `sample()` would block the gradient.
- C) Because the latent must be deterministic.
- D) To avoid computing the KL term.

---

**Q7.** Why is ACT inference single-pass while Diffusion Policy needs $N$ passes?

- A) ACT uses a smaller network.
- B) ACT handles multimodality with a CVAE latent at *training* time, so the deployed decoder just maps (obs, z=0) to a chunk in one pass; Diffusion Policy handles multimodality via *iterative* denoising at inference.
- C) Diffusion Policy is autoregressive.
- D) ACT doesn't predict chunks.

---

**Q8.** Temporal ensembling combines, at each timestep, the overlapping predictions for that timestep using weights $w_i = \exp(-m\cdot i)$. What does $i$ index, and what does it achieve?

- A) $i$ is the action dimension; it normalizes across joints.
- B) $i$ is the age of each overlapping prediction (0 = freshest); the weighted average smooths execution by blending overlapping chunks, removing the chunk-boundary jerk.
- C) $i$ is the diffusion timestep.
- D) $i$ is the episode index.

---

**Q9.** Why is temporal ensembling a "matched pair" with single-pass inference?

- A) Because the KL term requires it.
- B) Temporal ensembling re-predicts a fresh chunk *every timestep*, which is only affordable because ACT's inference is single-pass and cheap; a 16-step Diffusion Policy predicting every tick would be too slow.
- C) Because both use the reparameterization trick.
- D) They are unrelated.

---

**Q10.** You benchmark ACT and Diffusion Policy and get suspiciously low, nearly-equal latencies (microseconds). The most likely cause is:

- A) Both policies are genuinely that fast.
- B) You forgot `torch.cuda.synchronize()` — CUDA is async, so you measured only the kernel *launch*, not the compute.
- C) The batch size is too large.
- D) The GPU is broken.

---

**Q11.** Why report the **p99** latency, not just the median, for a control-loop policy?

- A) The median is harder to compute.
- B) A control loop misses its deadline on the *worst* tick, not the average one; a policy with a good median but a bad p99 (a long tail) can still blow the budget.
- C) p99 is always lower than the median.
- D) The median is only valid for CPU.

---

**Q12.** On your task, ACT and Diffusion Policy have nearly equal success rates, but ACT's p99 latency is 7 ms and Diffusion Policy's (16-step) is 35 ms, against a 33 ms / 30 Hz budget. Which ships, and why?

- A) Diffusion Policy, because it's more expressive.
- B) ACT — equal success, and its 7 ms p99 fits the budget with margin while Diffusion Policy's 35 ms p99 exceeds it (forcing an action-queue that adds staleness).
- C) Neither; the task is infeasible.
- D) Diffusion Policy, because latency never matters.

---

**Q13.** Under what condition would you choose Diffusion Policy over ACT despite ACT's latency advantage?

- A) Never; ACT is always better.
- B) When the task is genuinely ambiguous and the robot should sometimes resolve it differently at deploy — Diffusion Policy's deploy-time multimodality (re-sampling) is a real capability ACT gives up with $z=0$ — and the latency budget is generous.
- C) When you have less training data.
- D) When the control rate is higher.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — Chunking lets the policy re-decide every $k$ steps, shrinking the effective horizon to $H/k$ and giving $k\times$ fewer compounding opportunities. (Lecture 1 §1.)
2. **B** — The CVAE latent absorbs demonstration style so the decoder's conditional regression is well-posed, dodging the mode-averaging a plain regressor suffers. (Lecture 1 §2.)
3. **B** — The encoder is train-only; at inference $z=0$ and the decoder produces the chunk in one pass. (Lecture 1 §3, §4.4.)
4. **B** — The KL regularizes the latent toward the prior, which is what makes $z=0$ at inference sensible. (Lecture 1 §3.)
5. **B** — Posterior collapse: $\beta$ too high → KL dominates → $z$ uninformative → decoder mode-averages. (Lecture 1 §3.)
6. **B** — Reparameterization lets gradients flow into the encoder through the sampled latent; `sample()` would block them. (Lecture 1 §3.)
7. **B** — ACT moves the multimodality handling to training (CVAE), so the deployed decoder is a single (obs, z=0) → chunk pass; Diffusion Policy denoises iteratively at inference. (Lecture 1 §5.)
8. **B** — $i$ is the age of each overlapping prediction; the exponential-weighted average smooths the trajectory and removes chunk-boundary jerk. (Lecture 2 §1.2.)
9. **B** — Re-predicting every timestep (which ensembling needs) is only affordable with cheap single-pass inference. (Lecture 2 §1.4.)
10. **B** — Missing `torch.cuda.synchronize()` measures only the async kernel launch, not the compute — the classic benchmark bug. (Lecture 2 §2.1.)
11. **B** — The loop misses its deadline on the worst tick; the p99 (the tail) is what blows the budget, not the median. (Lecture 2 §2.1.)
12. **B** — Equal success → latency decides; ACT fits the budget, Diffusion Policy's p99 exceeds it and needs an action-queue with added staleness. (Lecture 2 §2.2, §3.)
13. **B** — Genuinely ambiguous tasks where deploy-time multimodality matters favor Diffusion Policy's re-sampling, if the latency budget allows. (Lecture 2 §3.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
