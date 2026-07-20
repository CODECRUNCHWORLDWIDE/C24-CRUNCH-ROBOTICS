# Week 29 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 30. Answer key is at the bottom — don't peek.

---

**Q1.** At a state where two equally-good actions are demonstrated, why does a Gaussian-MLP behavior-cloning policy trained with MSE predict a *bad* action?

- A) MSE training is unstable and diverges.
- B) MSE regression drives the prediction toward the conditional mean $\mathbb{E}[a\mid s]$, which for a bimodal target sits in the low-probability valley between the modes — an action neither demonstrator took.
- C) The network is too small.
- D) BC cannot represent continuous actions.

---

**Q2.** The multimodal-action problem is best described as:

- A) A tuning problem fixable with a lower learning rate.
- B) A data problem fixable with more demonstrations.
- C) A *representational* problem — a unimodal output distribution cannot represent a multimodal target, and more data makes it worse by sharpening the modes.
- D) A hardware problem.

---

**Q3.** In DDPM, the closed-form $q(x_t\mid x_0) = \mathcal{N}(\sqrt{\bar\alpha_t}x_0,\ (1-\bar\alpha_t)I)$ matters because:

- A) It makes sampling deterministic.
- B) It lets you jump to any noise level $t$ in one shot when building a training example — no need to iterate the per-step process.
- C) It removes the need for a neural network.
- D) It only holds for $t=1$.

---

**Q4.** What does the DDPM network $\epsilon_\theta(x_t, t)$ predict?

- A) The clean sample $x_0$ directly.
- B) The noise $\epsilon$ that was added to produce $x_t$.
- C) The reward of the action.
- D) The next state.

---

**Q5.** Why does a plain MSE *regression* loss (predict the noise) yield a *multimodal* generator at sampling time?

- A) The loss has a special multimodal term.
- B) The multimodality comes from sampling: the random starting noise and per-step noise select which mode the denoising trajectory commits to, so 512 samples form clusters, not a mean.
- C) It doesn't; diffusion is also unimodal.
- D) Because the network has more parameters.

---

**Q6.** DDIM versus DDPM sampling:

- A) DDIM is stochastic and slower.
- B) DDIM is deterministic and produces the same marginals in *far fewer* steps (e.g. 16 vs 100), which is what makes Diffusion Policy fast enough to deploy.
- C) DDIM requires retraining the model.
- D) DDIM only works for images.

---

**Q7.** For a robot controller, why is the DDIM denoising-step count called "the latency knob"?

- A) It changes the learning rate.
- B) Fewer steps = fewer network forward passes per decision = faster inference (more reactive controller), traded against a little sample quality. A 30 Hz loop can't afford 100 passes per decision.
- C) It changes the action-chunk length.
- D) It has no effect on latency.

---

**Q8.** In Diffusion Policy, which is diffused (noised), and which is the fixed condition?

- A) Both observations and actions are diffused jointly.
- B) Only the *actions* (the chunk) are diffused; the *observation* embedding is the fixed condition, encoded once and reused across denoising steps.
- C) Only the observations are diffused.
- D) Neither; Diffusion Policy doesn't use diffusion.

---

**Q9.** Why predict a *chunk* of $T_p$ future actions instead of one action at a time?

- A) It's faster to compute.
- B) A chunk is temporally consistent (the actions come from one denoising process over the whole sequence), giving smooth, committed motion and letting the policy express a decision that unfolds over time. One-at-a-time is myopic and jittery.
- C) It uses less memory.
- D) Single-action prediction is impossible with diffusion.

---

**Q10.** In receding-horizon execution, you predict $T_p$ actions but execute only the first $T_a < T_p$. Why not execute the whole chunk?

- A) The later actions are always wrong.
- B) Executing the whole chunk means flying blind for $T_p$ steps — disturbances are ignored until it runs out. Executing $T_a$ then re-observing keeps the policy reactive (MPC-style: plan long, commit short, re-plan often).
- C) The model can only output $T_a$ actions reliably.
- D) It saves GPU memory.

---

**Q11.** The action-queue deployment pattern (pop one action per control tick, re-plan when the queue drains) exists to:

- A) Make the policy stochastic.
- B) Decouple the slow inference rate (re-plan every $T_a$ ticks) from the fast control rate (emit every tick), so a 40-ms-inference policy can run a 30 Hz controller.
- C) Reduce the number of demonstrations needed.
- D) Improve training stability.

---

**Q12.** FiLM (Feature-wise Linear Modulation) in the 1D U-Net backbone is used to:

- A) Replace the convolution layers.
- B) Condition the conv features on the observation+timestep by producing a per-channel scale and shift ($\gamma\odot h + \beta$).
- C) Compute the diffusion loss.
- D) Sample actions deterministically.

---

**Q13.** You deploy a Diffusion Policy and the arm barely moves, with no error. The two most likely causes are:

- A) The GPU is too slow; the QoS is wrong.
- B) An observation mismatch (the node assembles the obs in a different order/scale than training) or a forgotten action un-normalization (actions stay tiny). Both are silent.
- C) The DDIM step count is too high; the learning rate was wrong.
- D) The replay buffer is empty.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — MSE drives toward the conditional mean; for a bimodal target the mean is the invalid valley between the modes. (Lecture 1 §1.)
2. **C** — It's representational: a unimodal output can't represent a multimodal target, and more data sharpens the modes and deepens the valley. (Lecture 1 §1.)
3. **B** — The closed form lets you sample $x_t$ for any $t$ directly, so building a training example needs no iteration. (Lecture 1 §2.2.)
4. **B** — The network predicts the noise $\epsilon$ (ε-prediction), not the clean sample. (Lecture 1 §2.3, §3.)
5. **B** — The multimodality is a property of *sampling* (random noise selects a mode), not of the loss; the loss is plain MSE. (Lecture 1 §3.)
6. **B** — DDIM is deterministic and few-step, matching DDPM's marginals; that's what makes the policy deployable. (Lecture 1 §4.)
7. **B** — Step count = forward passes per decision = inference latency; a real-time loop can't afford 100 passes. (Lecture 1 §4.2.)
8. **B** — Only actions are diffused; the observation is the fixed condition, encoded once and reused across denoising steps. (Lecture 2 §1, §4.)
9. **B** — A chunk is temporally consistent and expresses time-unfolding decisions; one-at-a-time is myopic and jittery. (Lecture 2 §3.1.)
10. **B** — Executing the whole chunk is stale and ignores disturbances; receding-horizon ($T_a$ then re-plan) stays reactive, exactly like MPC. (Lecture 2 §3.2.)
11. **B** — The queue decouples slow inference from fast control so a slow-denoise policy still emits an action every tick. (Lecture 2 §3.3.)
12. **B** — FiLM conditions conv features via a per-channel scale and shift derived from the obs+timestep. (Lecture 2 §2.1.)
13. **B** — The two classic silent deploy bugs: an obs-layout/scale mismatch, or a forgotten action un-normalization. (Lecture 2 §4, §5.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
