# Week 11 — Quiz

Thirteen questions. Take it with your lecture notes closed. Aim for 11/13 before moving to Week 12. Answer key is at the bottom — don't peek.

---

**Q1.** The fundamental difference between how the EKF and the UKF handle nonlinearity is:

- A) The EKF approximates the nonlinear *function* with a Jacobian; the UKF approximates the *distribution* by propagating sigma points through the true function.
- B) The UKF is linear; the EKF is nonlinear.
- C) The EKF uses particles; the UKF uses a Gaussian.
- D) They are identical; "UKF" is just a faster implementation of the EKF.

---

**Q2.** For an `n`-dimensional state, how many sigma points does the standard Unscented Transform use, and where do they sit?

- A) `n` points, all at the mean.
- B) `2n + 1` points: one at the mean, and `±` the columns of the matrix square root of the scaled covariance.
- C) `n²` points on a grid.
- D) A random sample of 1000 points.

---

**Q3.** You are fusing wheel odometry and IMU into a planar pose — mild nonlinearity. Should you switch from your Week 10 EKF to a UKF?

- A) Yes, always; the UKF is strictly better.
- B) It rarely matters — for mild nonlinearity the EKF and UKF give nearly identical results, and the EKF is simpler and slightly cheaper. Reach for the UKF on *strong* nonlinearity (range-bearing, large heading uncertainty).
- C) No; the UKF cannot handle odometry.
- D) Only if you switch DDS vendors.

---

**Q4.** A filter reports a state estimate and a covariance. Its NEES, averaged over many steps, sits persistently *above* the chi-squared upper bound. What does this mean?

- A) The filter is conservative (pessimistic but safe).
- B) The filter is overconfident — the true error is larger than the covariance claims. This is the classic divergence signature.
- C) The filter has converged perfectly.
- D) NEES above the bound is always fine.

---

**Q5.** What is the key advantage of NIS over NEES as a consistency check on a *deployed* robot?

- A) NIS is more accurate.
- B) NIS uses the innovation and its covariance, so it needs no ground truth — it works on a real robot, whereas NEES needs the true state.
- C) NIS is chi-squared and NEES is not.
- D) There is no difference.

---

**Q6.** Why does a particle filter handle *global localization* (the robot doesn't know where it is) when an EKF or UKF cannot?

- A) Particle filters are faster.
- B) The belief is *multimodal* — "I could be in any of these similar corridors" — and a particle cloud represents multiple hypotheses, while a single Gaussian cannot.
- C) Particle filters don't need a map.
- D) EKFs cannot represent position at all.

---

**Q7.** In a particle filter, the effective sample size `N_eff = 1 / Σ wᵢ²` drops toward 1. What is happening, and what's the standard response?

- A) The filter converged perfectly; do nothing.
- B) Degeneracy — one particle owns nearly all the weight. Resample (typically when `N_eff < N/2`) to redistribute particles toward the high-likelihood region.
- C) The map is wrong; reload it.
- D) Increase the measurement noise to infinity.

---

**Q8.** AMCL is "kidnapped" — the robot is teleported, so the cloud is confidently wrong. With `recovery_alpha_*` set to 0, AMCL cannot recover. Why?

- A) The map server crashed.
- B) Resampling only ever selects from *existing* particles; if none is near the true pose, the filter can never rediscover it (particle deprivation). Random-particle injection (`recovery_alpha_*`) is what fixes it.
- C) The QoS is mismatched.
- D) AMCL never recovers from anything.

---

**Q9.** The single most important difference between a *filter* (EKF/UKF/PF) and a *smoother* (factor graph) is:

- A) Filters are written in C++; smoothers in Python.
- B) A filter marginalizes the past into the current belief (constant-time, cannot revisit old states); a smoother keeps the constraints and re-optimizes the whole trajectory, so a loop closure now can correct a pose from minutes ago.
- C) Smoothers don't use covariance.
- D) Filters are always more accurate.

---

**Q10.** Why does a factor graph with no prior factor fail to optimize?

- A) GTSAM requires exactly one prior by API.
- B) The graph *floats* — with only relative (between) constraints, any rigid transform of the solution fits equally well, so the problem is under-determined. At least one prior anchors it to the world frame.
- C) Between factors are invalid without a prior.
- D) The optimizer is too slow without a prior.

---

**Q11.** Maximum-a-posteriori estimation on a factor graph with Gaussian noise models is equivalent to:

- A) A linear program.
- B) Minimizing the sum of squared, covariance-weighted factor errors — i.e. sparse nonlinear least squares, solved by Gauss-Newton or Levenberg-Marquardt.
- C) A particle filter.
- D) Matrix inversion of the full covariance.

---

**Q12.** A place-recognition front-end emits a *false* loop closure (a gross-outlier constraint). With a plain Gaussian noise model on the loop factor, what happens, and what's the fix?

- A) Nothing — least squares ignores outliers automatically.
- B) Least squares believes the bad factor and drags the whole trajectory off the truth. The fix is a *robust* (Huber/Cauchy) noise model that down-weights the outlier so the good constraints win.
- C) The graph refuses to connect.
- D) The fix is to add more bad loop closures to average them out.

---

**Q13.** Why is iSAM2 important — what does it make possible that batch Levenberg-Marquardt does not?

- A) It makes the answer more accurate than batch.
- B) It re-optimizes only the part of the factor graph affected by new information (via the Bayes tree), giving roughly constant per-step cost — which is what makes factor-graph SLAM run *online* on a robot that operates for hours.
- C) It removes the need for a prior.
- D) It converts the smoother into a filter.

---

## Answer key

<details>
<summary>Click to reveal answers</summary>

1. **A** — The EKF linearizes the *function* (Jacobian); the UKF approximates the *distribution* (sigma points through the true function). Approximating a Gaussian is usually easier and more accurate than approximating an arbitrary nonlinear map. (Lecture 1 §1.)
2. **B** — `2n + 1` sigma points: one at the mean, the rest at `±` the columns of the matrix square root (Cholesky) of `(n + λ)Σ`. (Lecture 1 §2.1.)
3. **B** — For mild nonlinearity the EKF and UKF are nearly identical and the EKF is cheaper. The UKF earns its keep on strong nonlinearity (range-bearing, large heading uncertainty) and where Jacobians are painful. (Lecture 1 §3.3.)
4. **B** — Persistent NEES above the bound = overconfident: the true error exceeds the claimed covariance. That is the dangerous failure mode and the EKF-divergence signature. (Lecture 1 §4.1.)
5. **B** — NIS uses the innovation `ν` and its covariance `S`, both computed during the update, so it needs no ground truth — it is the runtime consistency monitor on a real robot. (Lecture 1 §4.2.)
6. **B** — Global localization has a *multimodal* belief; a particle cloud holds multiple hypotheses simultaneously, which no single Gaussian (EKF/UKF) can. (Lecture 1 §5.)
7. **B** — Falling `N_eff` is degeneracy (one particle owns the weight). Resample when `N_eff < N/2` (commonly), using low-variance resampling, to redistribute particles. (Lecture 1 §5.2.)
8. **B** — Resampling only selects from existing particles; with none near the true pose and no random injection, the filter can't recover (particle deprivation). `recovery_alpha_*` injects random particles to fix it. (Lecture 1 §5.4, §6.3.)
9. **B** — A filter marginalizes the past (constant-time, can't revisit); a smoother keeps constraints and re-optimizes the whole trajectory, so a loop closure propagates corrections backward. (Lecture 2 §1.)
10. **B** — With only relative constraints the graph floats; any rigid transform fits equally. A prior anchors it to the world frame; at least one is required. (Lecture 2 §2.)
11. **B** — Gaussian factors make MAP = minimizing the sum of squared weighted errors = sparse nonlinear least squares (Gauss-Newton / Levenberg-Marquardt). Sparsity is what makes it scale. (Lecture 2 §2.1.)
12. **B** — A plain Gaussian model trusts the outlier and corrupts the trajectory. A robust (Huber/Cauchy) kernel down-weights the gross error so good constraints win — standard practice on automatic loop closures. (Lecture 2 §4.)
13. **B** — iSAM2 re-optimizes only the part of the graph affected by new information (Bayes tree), giving roughly constant per-step cost — the reason factor-graph SLAM runs online. (Lecture 2 §7.)

</details>

---

If you scored under 9, re-read the lecture sections cited in the answers you missed. If you scored 11 or higher, you're ready for the [homework](./homework.md).
