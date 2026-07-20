# Week 28 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 29. Answer key is at the bottom — don't peek.

---

**Q1.** The policy-gradient theorem replaces $\nabla_\theta \mathbb{E}[R(\tau)]$ with an expectation of $\nabla_\theta\log\pi_\theta(a\mid s)$ times a return. Which identity makes this possible, and why do the environment dynamics drop out?

- A) Bayes' rule; the dynamics are a prior that cancels.
- B) The log-derivative trick ($\nabla p = p\,\nabla\log p$); the dynamics $p(s'\mid s,a)$ don't depend on $\theta$, so their gradient is zero.
- C) The chain rule on the value function; dynamics are absorbed into $V$.
- D) Importance sampling; the dynamics are the proposal distribution.

---

**Q2.** Subtracting a state-only baseline $b(s)$ from the reward-to-go is "free" (no bias). Why?

- A) Because $b(s)$ is small relative to the return.
- B) Because $\mathbb{E}_{a\sim\pi}[\nabla_\theta\log\pi_\theta(a\mid s)\,b(s)] = b(s)\nabla_\theta\sum_a\pi(a\mid s) = b(s)\cdot 0 = 0$.
- C) Because the baseline is learned by a separate network.
- D) It is not free; baselines always add bias.

---

**Q3.** In GAE-λ, what does $\lambda = 0$ versus $\lambda = 1$ give you?

- A) $\lambda=0$ is Monte-Carlo (unbiased, high variance); $\lambda=1$ is one-step TD (biased, low variance).
- B) $\lambda=0$ is one-step TD (low variance, biased); $\lambda=1$ is Monte-Carlo (unbiased, high variance).
- C) Both give the same estimator; $\lambda$ only changes the learning rate.
- D) $\lambda$ controls the discount, not the bias–variance trade.

---

**Q4.** Your episode is cut off by a time limit (`truncated=True`) but the MDP did not actually end. For the GAE bootstrap at that step, you should:

- A) Zero the bootstrap (treat it like a termination).
- B) Bootstrap with $V(s_{t+1})$ — the future still exists; only `terminated` zeroes the bootstrap.
- C) Discard the whole episode.
- D) Set the advantage to zero.

---

**Q5.** In the PPO clipped surrogate $\min(r_t\hat{A}_t,\ \text{clip}(r_t,1-\epsilon,1+\epsilon)\hat{A}_t)$ with $\hat{A}_t > 0$, what happens once $r_t$ exceeds $1+\epsilon$?

- A) The objective keeps rewarding larger $r_t$, so the policy moves further.
- B) The objective flattens — the clipped term is selected, so there's no gradient reward for moving further. The policy can't run away on one good sample.
- C) The update is rejected and the batch is discarded.
- D) The advantage is negated.

---

**Q6.** Why does PPO use a clip instead of TRPO's KL trust region?

- A) The clip is more accurate than the KL constraint.
- B) The clip is a cheap first-order stand-in that gets most of TRPO's benefit without conjugate gradients or Fisher-vector products.
- C) TRPO does not work for continuous actions.
- D) The clip allows larger learning rates with no downside.

---

**Q7.** You're watching a PPO run: reward is climbing but `approx_kl` keeps spiking above 0.05. What does this tell you?

- A) The run is healthy; high KL means fast learning.
- B) The steps are too large; the clip isn't holding the policy in place and it's likely to collapse — lower the LR or the number of epochs.
- C) The critic has converged.
- D) The entropy coefficient is too high.

---

**Q8.** What is the role of SAC's clipped double-Q (the $\min$ of two critics) in the target?

- A) It speeds up training by averaging two estimates.
- B) It fights systematic value *overestimation* — bootstrap latches onto optimistic noise, and taking the min of two independent critics is a cheap pessimism that counters it.
- C) It is required for discrete action spaces.
- D) It replaces the need for a replay buffer.

---

**Q9.** SAC's actor squashes a Gaussian sample through `tanh`. Why must the log-probability include a correction term?

- A) `tanh` is not differentiable, so the gradient needs a fix.
- B) The change-of-variables (Jacobian of `tanh`) changes the density; skip the $-\sum\log(1-\tanh^2 u)$ correction and the entropy estimate is wrong, which corrupts temperature tuning.
- C) `tanh` saturates, so the correction prevents NaNs only.
- D) No correction is needed; the Gaussian log-prob is exact.

---

**Q10.** Why does SAC's actor use `rsample()` (reparameterized) rather than `sample()`?

- A) `rsample()` is faster.
- B) The actor loss differentiates *through* the sampled action ($a=\mu+\sigma\epsilon$), so the sample must be a differentiable function of the parameters; `sample()` blocks the gradient.
- C) `sample()` is deprecated in PyTorch.
- D) `rsample()` gives lower-variance rewards.

---

**Q11.** You have a GPU-parallel simulator that runs 4,096 environments at 150k steps/sec. For a reach task, which algorithm is usually the better *first* choice, and why?

- A) SAC, because it's more sample-efficient.
- B) PPO, because its weakness (sample inefficiency) evaporates when samples are nearly free, and its stability saves tuning days.
- C) Neither works with parallel sim.
- D) SAC, because it doesn't need a replay buffer.

---

**Q12.** A potential-based shaping term $F(s,s')=\gamma\Phi(s')-\Phi(s)$ is special because:

- A) It always speeds up learning by exactly a factor of $\gamma$.
- B) It provably leaves the *optimal policy unchanged* for any potential $\Phi$ — it only changes how fast you learn, not what you learn.
- C) It removes the need for a dense reward.
- D) It only works for navigation tasks.

---

**Q13.** Your reach reward gives velocity-toward-target reward, and the trained policy oscillates back and forth across the target without ever settling, while the reward curve rises. What is this, and what's the fix?

- A) A learning-rate problem; raise the LR.
- B) Reward hacking — "the vibrator": rewarding *velocity* lets the policy farm "toward" reward without settling. Fix: reward *position* (a potential on distance), not velocity, and gate success on being close AND slow.
- C) A critic bug; add a second value head.
- D) Normal RL behavior; it will settle with more steps.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **B** — The log-derivative trick moves the gradient inside the expectation; the dynamics are independent of $\theta$ so their gradient vanishes, leaving only $\sum\nabla\log\pi$. (Lecture 1 §2.)
2. **B** — The probabilities sum to one, so the gradient of the constant 1 is zero; the baseline term vanishes in expectation while cutting variance. (Lecture 1 §3.2.)
3. **B** — $\lambda=0$ is one-step TD (low variance, biased if the critic is wrong); $\lambda=1$ is Monte-Carlo (unbiased, high variance). 0.95 is the robot default. (Lecture 1 §4.)
4. **B** — Only `terminated` (a genuine MDP end) zeroes the bootstrap. A time-limit `truncated` step still has a future, so you bootstrap with $V(s_{t+1})$. Confusing them biases every advantage. (Lecture 1 §4.)
5. **B** — Past $1+\epsilon$ the clipped term is selected and the objective flattens — zero gradient reward for moving further. That's the clip preventing a runaway update. (Lecture 1 §6.)
6. **B** — PPO's clip is a cheap first-order approximation to TRPO's trust region; it skips the heavy constrained-optimization machinery and works in practice. (Lecture 1 §5.)
7. **B** — Spiking KL means steps too large; the policy will collapse. Lower LR or epochs. The healthy band is ~0.005–0.02. (Lecture 1 §8.)
8. **B** — Single critics overestimate because bootstrap latches onto optimistic noise; the min of two independent critics is a cheap pessimism that counters it. (Lecture 2 §1.2.)
9. **B** — The `tanh` Jacobian changes the density; the $-\sum\log(1-\tanh^2 u)$ correction keeps the log-prob (and thus entropy and temperature tuning) honest. (Lecture 2 §1.3.)
10. **B** — The actor differentiates through the action, so it needs the reparameterized $a=\mu+\sigma\epsilon$; `rsample()` provides it, `sample()` blocks the gradient. (Lecture 2 §1.3.)
11. **B** — With nearly-free samples, PPO's sample inefficiency stops mattering and its stability wins; PPO loves massively-parallel sim. SAC earns its complexity when samples are expensive. (Lecture 2 §1.6, Part 2.)
12. **B** — The Ng–Harada–Russell theorem: potential-based shaping is policy-invariant for any $\Phi$ — it speeds learning without distorting the goal. (Lecture 2 §3.2.)
13. **B** — The vibrator reward hack: rewarding velocity is farmable by oscillation. Fix by rewarding position via a potential and gating success on settled (close + slow). (Lecture 2 §3.3; Challenge 1.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
