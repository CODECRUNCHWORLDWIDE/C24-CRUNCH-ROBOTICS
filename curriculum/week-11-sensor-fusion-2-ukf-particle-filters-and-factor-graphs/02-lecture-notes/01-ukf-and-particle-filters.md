# Lecture 1 — The UKF Lies Less, and the Particle Filter Stops Assuming Gaussians

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can derive the Unscented Transform, run a UKF predict/update cycle without computing a single Jacobian, check whether a filter is *consistent* with NEES and NIS, explain the particle-filter loop including low-variance resampling, and describe exactly what AMCL is doing to localize your robot against the Week 7 map.

If you remember one sentence from this lecture, remember this one:

> **The EKF approximates the nonlinear *function* (with a Jacobian). The UKF approximates the *distribution* (with sigma points). It is almost always easier and more accurate to approximate a Gaussian than to approximate an arbitrary nonlinear map — and the particle filter takes that idea to its conclusion by not assuming a Gaussian at all.**

Last week's EKF works, and we are not throwing it away. But you saw its cost: every step, it replaces your motion and measurement models with their first-order Taylor expansion around the current mean. When the heading covariance is large or the measurement is a bearing, that linearization is *biased*, and — worse — it underestimates the resulting covariance. A filter that is overconfident drifts into divergence, and it does so quietly. This lecture builds the two estimators that handle that nonlinearity honestly.

---

## 1. Why linearization hurts: a concrete picture

Take a 2D point with a Gaussian distribution in polar-ish coordinates — say a range `r` and bearing `θ` — and transform it to Cartesian `(x, y) = (r cos θ, r sin θ)`. The true transformed distribution is *banana-shaped*: a curved arc, because the bearing uncertainty sweeps the point along a circle. 

The **EKF** answers "what is the transformed mean and covariance?" by linearizing: it computes the Jacobian of `(r cos θ, r sin θ)` at the mean, and pushes the covariance through that linear map. The result is an ellipse — and a *wrong* ellipse, because a straight-line approximation of a curved transform misplaces the mean and shrinks the spread. The EKF's covariance is too small. It thinks it knows more than it does.

The **Unscented Transform** answers the same question differently. Instead of approximating the function, it picks a small set of deterministic sample points — *sigma points* — that exactly capture the input mean and covariance, pushes *those points* through the true nonlinear function, and then computes the sample mean and covariance of the transformed points. No Jacobian. The transformed mean lands on the banana's centroid, and the covariance captures the real spread. For the same computational order as the EKF, you get a second-order-accurate estimate of the mean and a better covariance.

That is the whole idea. Now we make it precise.

---

## 2. The Unscented Transform, step by step

Let the input be an `n`-dimensional Gaussian with mean `μ` (an `n`-vector) and covariance `Σ` (an `n×n` SPD matrix). We want the mean and covariance of `y = f(x)` for a nonlinear `f`.

### 2.1 Choose the sigma points

We pick `2n + 1` sigma points. The first sits at the mean; the rest sit symmetrically at `±` the columns of the matrix square root of a scaled covariance:

```
χ₀ = μ
χᵢ     = μ + (√((n + λ) Σ))ᵢ      for i = 1 .. n
χᵢ₊ₙ   = μ - (√((n + λ) Σ))ᵢ      for i = 1 .. n
```

`(√M)ᵢ` is the `i`-th column of a matrix square root of `M` — in practice the lower-triangular Cholesky factor `L` where `L Lᵀ = M`. The scaling `λ` (lambda) controls how far from the mean the points spread:

```
λ = α² (n + κ) − n
```

with the **scaled-unscented parameters**:

- **α** (alpha) — controls the spread; small (e.g. `1e-3`) keeps the sigma points close to the mean to avoid sampling non-local nonlinearity. Default `1e-3`.
- **κ** (kappa) — a secondary scaling, usually `0` or `3 − n`. Default `0`.
- **β** (beta) — incorporates prior knowledge of the distribution; for a Gaussian, `β = 2` is optimal. It only affects the covariance weights.

### 2.2 The weights

Each sigma point gets two weights — one for reconstructing the mean, one for the covariance:

```
Wₘ₀ = λ / (n + λ)
Wc₀ = λ / (n + λ) + (1 − α² + β)
Wₘᵢ = Wcᵢ = 1 / (2(n + λ))      for i = 1 .. 2n
```

Note the mean and covariance weights differ only for the center point, and only by the `(1 − α² + β)` term — that is where `β`'s Gaussian correction enters.

### 2.3 Propagate and recover

Push every sigma point through `f`, then take weighted moments:

```
yᵢ = f(χᵢ)                                  for i = 0 .. 2n
ȳ  = Σ Wₘᵢ yᵢ                               (predicted mean)
Pᵧ = Σ Wcᵢ (yᵢ − ȳ)(yᵢ − ȳ)ᵀ  +  Q         (predicted covariance, Q = process noise)
```

That is the Unscented Transform in full. Here it is in NumPy — this exact function is the spine of the UKF you build in Exercise 2:

```python
import numpy as np


def unscented_transform(mu, Sigma, f, Q=None, alpha=1e-3, beta=2.0, kappa=0.0):
    """Push a Gaussian (mu, Sigma) through nonlinear f via sigma points.

    Returns (y_mean, y_cov, sigma_pts, y_pts) so callers (the UKF update) can
    reuse the propagated points for cross-covariance.
    """
    n = mu.shape[0]
    lam = alpha**2 * (n + kappa) - n

    # Mean and covariance weights.
    wm = np.full(2 * n + 1, 1.0 / (2.0 * (n + lam)))
    wc = wm.copy()
    wm[0] = lam / (n + lam)
    wc[0] = lam / (n + lam) + (1.0 - alpha**2 + beta)

    # Matrix square root of (n + lam) * Sigma via Cholesky (lower triangular).
    L = np.linalg.cholesky((n + lam) * Sigma)

    # The 2n+1 sigma points: center, then +/- each column of L.
    sigma_pts = np.zeros((2 * n + 1, n))
    sigma_pts[0] = mu
    for i in range(n):
        sigma_pts[i + 1] = mu + L[:, i]
        sigma_pts[i + 1 + n] = mu - L[:, i]

    # Propagate.
    y_pts = np.array([f(pt) for pt in sigma_pts])

    # Recover weighted mean and covariance.
    y_mean = wm @ y_pts
    dy = y_pts - y_mean
    y_cov = (wc[:, None, None] * np.einsum("ki,kj->kij", dy, dy)).sum(axis=0)
    if Q is not None:
        y_cov = y_cov + Q
    return y_mean, y_cov, sigma_pts, y_pts, wm, wc
```

A subtle but important detail: when your state has an **angle** in it (a heading `θ`), you cannot naively average the propagated points, because angles wrap at `±π`. Averaging `+179°` and `−179°` the naive way gives `0°`, which is exactly wrong — the true mean is `±180°`. Production UKFs (and `robot_localization`'s `Ukf.cpp`) handle this by computing the angular mean through `atan2(Σ sin, Σ cos)` or by keeping the angle on the manifold. We flag it now because it is the single most common UKF bug, and Exercise 2 makes you handle it.

---

## 3. The UKF predict/update cycle

A UKF wraps the Unscented Transform into the same two-phase rhythm as the Kalman filter: **predict** through the motion model, **update** through the measurement model.

### 3.1 Predict

Given the prior `(μ, Σ)` and the motion model `g(x, u)` with process noise `Q`:

```
(μ̄, Σ̄, χ, _, wm, wc) = unscented_transform(μ, Σ, lambda x: g(x, u), Q)
```

`μ̄` and `Σ̄` are the predicted (a priori) mean and covariance. No Jacobian of `g` ever appears.

### 3.2 Update

Given a measurement `z` with measurement model `h(x)` and measurement noise `R`:

1. Push the *predicted* sigma points through `h` to get predicted measurements `Ẑᵢ = h(χ̄ᵢ)`, their mean `ẑ`, and innovation covariance `S = Σ Wcᵢ (Ẑᵢ − ẑ)(Ẑᵢ − ẑ)ᵀ + R`.
2. Compute the **cross-covariance** between state and measurement:
   `Pₓz = Σ Wcᵢ (χ̄ᵢ − μ̄)(Ẑᵢ − ẑ)ᵀ`.
3. Kalman gain `K = Pₓz S⁻¹`.
4. Correct: `μ = μ̄ + K (z − ẑ)`, `Σ = Σ̄ − K S Kᵀ`.

That cross-covariance step is the UKF's analogue of the EKF's `P Hᵀ`, but computed from sample points instead of a Jacobian `H`. The whole update touches `h` only by *evaluating* it at sigma points — never differentiating it. This is why the UKF shines when `h` is annoying to differentiate (a range-bearing model, a camera projection, a quaternion measurement): you write the forward model and you are done.

```python
def ukf_update(mu_bar, Sigma_bar, sigma_pts_pred, wm, wc, h, z, R):
    """One UKF correction step. sigma_pts_pred are the predicted state sigma points."""
    # Push predicted sigma points through the measurement model.
    Z = np.array([h(pt) for pt in sigma_pts_pred])
    z_hat = wm @ Z
    dz = Z - z_hat

    S = (wc[:, None, None] * np.einsum("ki,kj->kij", dz, dz)).sum(axis=0) + R

    dx = sigma_pts_pred - mu_bar
    P_xz = (wc[:, None, None] * np.einsum("ki,kj->kij", dx, dz)).sum(axis=0)

    K = P_xz @ np.linalg.inv(S)
    innovation = z - z_hat
    mu = mu_bar + K @ innovation
    Sigma = Sigma_bar - K @ S @ K.T
    return mu, Sigma, innovation, S
```

### 3.3 When the UKF is worth it

Honest field guidance for 2026: **the UKF is not a free upgrade you apply everywhere.** For mildly nonlinear systems — fusing wheel odometry and IMU into a planar pose, the Week 10 problem — the EKF and UKF give nearly identical results, and the EKF is simpler and slightly cheaper. Reach for the UKF when:

- The measurement model is strongly nonlinear (range-bearing to a landmark, a camera projection, a magnetometer).
- The state carries large heading uncertainty (the linearization of `cos θ`, `sin θ` is poor over a wide angle).
- Computing the Jacobian is error-prone or expensive, and you'd rather just write the forward model.

`robot_localization` exposes a `ukf_node` with *the same configuration shape* as the `ekf_node` you already used — swapping `ekf_node` for `ukf_node` in your launch file is a one-line change, and the homework asks you to do exactly that and measure whether it matters on your robot.

---

## 4. Is the filter telling the truth? NEES and NIS

A filter outputs a mean *and a covariance*. The mean is an estimate; the covariance is the filter's *claim about how good that estimate is*. A filter can be accurate-but-overconfident (small covariance, true error larger than claimed) — and that is the dangerous failure mode, because downstream consumers trust the covariance. Two metrics catch it.

### 4.1 NEES — Normalized Estimation Error Squared

When you have ground truth `x` (in sim, you do), NEES measures whether the actual error matches the claimed covariance:

```
NEES = (x − μ)ᵀ Σ⁻¹ (x − μ)
```

For a consistent filter with an `n`-dimensional state, NEES is chi-squared distributed with `n` degrees of freedom, so its expected value is `n`. Average NEES over many runs (or many timesteps) and it should sit near `n`, inside the two-sided 95% chi-squared bound. **NEES persistently above the bound means the filter is overconfident** (the true error is bigger than Σ claims) — the classic EKF-divergence signature. NEES below means it is conservative (pessimistic but safe).

```python
from scipy.stats import chi2


def nees(x_true, mu, Sigma):
    e = x_true - mu
    return float(e @ np.linalg.inv(Sigma) @ e)


def nees_bounds(dof, n_runs, conf=0.95):
    """Two-sided chi-squared bound on the AVERAGE NEES over n_runs samples."""
    lo = chi2.ppf((1 - conf) / 2, dof * n_runs) / n_runs
    hi = chi2.ppf((1 + conf) / 2, dof * n_runs) / n_runs
    return lo, hi
```

### 4.2 NIS — Normalized Innovation Squared

NIS is NEES's cousin that needs no ground truth — it works on a real robot. It uses the *innovation* `ν = z − ẑ` and its covariance `S` (both of which the update step already computed):

```
NIS = νᵀ S⁻¹ ν
```

NIS is chi-squared with `m` degrees of freedom, where `m` is the measurement dimension, and should average near `m`. Because you can compute NIS online without truth, it is the standard *runtime* consistency monitor: a NIS that walks out of its bound is your filter telling you, on the live robot, that its noise models are wrong. We use NEES in Exercise 2 (we have sim ground truth) and mention NIS as the deployment version.

---

## 5. Particle filters: dropping the Gaussian assumption

The UKF still assumes the belief is Gaussian. For a unimodal, roughly-symmetric belief that is fine. But consider *global localization*: you turn the robot on in a building it has a map of, and it has no idea where it is. The belief is *multimodal* — "I could be in any of these four similar-looking corridors." No Gaussian captures that. You need a representation that can hold several hypotheses at once.

The **particle filter** represents the belief as a set of `N` weighted samples — particles — each a complete hypothesis of the state. The cloud's density *is* the probability distribution. Many particles where the robot probably is, few where it probably isn't. This is **nonparametric**: the representation makes no shape assumption, so it handles multimodal and non-Gaussian beliefs naturally.

### 5.1 The SIR loop

The standard algorithm is **Sequential Importance Resampling (SIR)**, three steps per timestep:

1. **Sample (predict).** For each particle, draw a new pose from the motion model: apply the control `u` with noise. The cloud spreads.
2. **Weight (correct).** For each particle, compute the likelihood of the measurement `z` given that particle's pose: `wᵢ = p(z | xᵢ)`. Particles consistent with the sensor reading get high weight; particles inconsistent with it get low weight. Normalize so the weights sum to 1.
3. **Resample.** Draw `N` new particles from the current set *with replacement, in proportion to weight*. High-weight particles get copied multiple times; low-weight particles die out. The cloud concentrates where the evidence points.

```python
def particle_filter_step(particles, weights, u, z, motion_model, meas_likelihood):
    """One SIR step. particles: (N, state_dim); weights: (N,)."""
    N = particles.shape[0]

    # 1. Sample: push each particle through the noisy motion model.
    particles = np.array([motion_model(p, u) for p in particles])

    # 2. Weight: likelihood of the measurement under each particle.
    weights = weights * np.array([meas_likelihood(z, p) for p in particles])
    weights += 1e-300                      # guard against all-zero underflow
    weights /= weights.sum()               # normalize

    # 3. Resample only when the cloud has degenerated (see N_eff below).
    n_eff = 1.0 / np.sum(weights**2)
    if n_eff < N / 2.0:
        particles, weights = low_variance_resample(particles, weights)
    return particles, weights
```

### 5.2 Degeneracy and the effective sample size

After a few steps, the weights concentrate: one particle ends up with nearly all the weight and the rest contribute nothing. This is **degeneracy**, and it wastes your whole cloud on representing one hypothesis. The **effective sample size**

```
N_eff = 1 / Σ wᵢ²
```

measures how many particles are "really" contributing. `N_eff = N` means uniform weights (healthy); `N_eff = 1` means one particle owns everything (degenerate). The standard fix is to resample only when `N_eff` drops below a threshold (commonly `N/2`), as in the code above — resampling every step throws away diversity you don't need to.

### 5.3 Low-variance (systematic) resampling

*How* you resample matters. Naive resampling — draw `N` independent uniform numbers and pick the corresponding particles — adds sampling noise and can, by bad luck, drop particles that should have survived. **Low-variance resampling** draws a single random offset and steps through the cumulative-weight distribution at even intervals. It touches every region of the cloud proportionally, runs in `O(N)`, and is what AMCL actually uses:

```python
def low_variance_resample(particles, weights):
    """Systematic resampling: one random start, N evenly-spaced draws. O(N)."""
    N = len(weights)
    positions = (np.arange(N) + np.random.uniform()) / N
    cumsum = np.cumsum(weights)
    cumsum[-1] = 1.0                       # guard against float roundoff
    idx = np.searchsorted(cumsum, positions)
    resampled = particles[idx]
    return resampled, np.full(N, 1.0 / N)
```

### 5.4 The two failure modes

- **Particle deprivation.** After resampling, no particle survives near the true state (because none was sampled there). The filter becomes confidently wrong and *cannot recover*, because resampling only ever selects from existing particles. The fix: inject a few random particles every step (AMCL's `recovery_alpha` parameters), or use enough particles that the true state is always covered.
- **Sample impoverishment.** Repeated resampling without enough motion noise collapses the cloud onto a handful of identical particles — all diversity gone. The fix: add a little noise on resampling (roughening), or tune the motion model so the predict step keeps the cloud spread.

---

## 6. AMCL: the particle filter you actually run

**Adaptive Monte Carlo Localization** is the particle filter, specialized to *localizing a robot against a known occupancy grid* — exactly your Week 7 map. It is the localization half of the navigation stack, and in Exercise 1 you run it for real. Three pieces make it AMCL rather than a generic PF:

### 6.1 The sample motion model

AMCL's predict step uses the **odometry motion model**: it reads the robot's odometry delta (rotate–translate–rotate) and applies it to each particle with noise governed by five parameters `alpha1..alpha5`. These encode how much you trust your odometry: `alpha1` is rotation noise from rotation, `alpha2` rotation noise from translation, `alpha3` translation noise from translation, `alpha4` translation noise from rotation, and `alpha5` (for omni models) strafe. **Tuning these honestly is the heart of making AMCL work** — too small and the cloud is overconfident and loses the true pose; too large and it never converges. They should reflect your *actual* odometry quality from Week 6.

### 6.2 The likelihood-field measurement model

For each particle, AMCL scores how well the laser scan, taken *from that particle's pose*, matches the map. The default **likelihood field model** precomputes, for every map cell, the distance to the nearest obstacle, then scores each beam's endpoint by a Gaussian on that distance. Particles whose hypothesized pose makes the scan line up with map obstacles get high weight. The key parameters: `z_hit` (weight of the "beam hit the right obstacle" Gaussian), `z_rand` (weight of a uniform random-noise term that prevents a single bad beam from zeroing a particle), and `sigma_hit` (the Gaussian width).

### 6.3 Adaptive particle count and recovery

The "Adaptive" in AMCL is **KLD-sampling**: it uses *more* particles when the belief is spread out (global localization, just after startup) and *fewer* once it has converged to a tight cluster, between `min_particles` and `max_particles`. This keeps it cheap when localized and robust when lost. For the **kidnapped-robot problem** — the robot is picked up and moved, so the filter is confidently wrong — AMCL injects random particles when the average measurement likelihood drops (governed by `recovery_alpha_slow` and `recovery_alpha_fast`), giving the cloud a chance to rediscover the true pose.

### 6.4 Initializing and watching it converge

You initialize AMCL by publishing `/initialpose` — in rviz2, the **2D Pose Estimate** button. The cloud spawns around your guess. As the robot drives and scans, the cloud tightens onto the true pose. In rviz2 the `PoseArray` display shows the particles as little arrows; watching that arrow cloud collapse from a fuzzy blob to a tight dart *is* the particle filter converging, and it is one of the most satisfying things to watch in robotics. Exercise 1 has you do this, then deliberately set a wrong `/initialpose` to trigger — and recover from — the kidnapped-robot failure.

---

## 7. Where this leaves us

You now have two estimators beyond the EKF:

- The **UKF** keeps the Gaussian belief but propagates it through the true nonlinear model with sigma points — more accurate on strong nonlinearity, no Jacobians, and a one-line swap in `robot_localization`.
- The **particle filter** drops the Gaussian assumption to handle multimodal beliefs, and in its AMCL form is the standard way to localize against a known map.

But notice what *both* of them still do: they are **filters**. Every step they compress all the history into a single belief — a mean and covariance, or a particle cloud — and throw the raw past away. That compression is what makes them constant-time, and it is also what makes them suboptimal: once you've marginalized out an old pose, you can never go back and correct it when a *later* measurement (a loop closure) reveals it was wrong. To do that — to keep the past around and re-optimize the whole trajectory when new evidence arrives — you need a different structure entirely.

That structure is the **factor graph**, and it is the subject of Lecture 2. Continue to [Lecture 2 — Factor Graphs and GTSAM](./02-factor-graphs-and-gtsam.md).

---

## References

- Thrun, Burgard, Fox — *Probabilistic Robotics*, Ch. 3 (UKF) and Ch. 4 (particle filters): <https://docs.ufpr.br/~danielsantos/ProbabilisticRobotics.pdf>
- Julier & Uhlmann — "A New Extension of the Kalman Filter to Nonlinear Systems" (1997): <https://www.cs.unc.edu/~welch/kalman/media/pdf/Julier1997_SPIE_KF.pdf>
- Van der Merwe & Wan — "The (Square-Root) Unscented Kalman Filter": <https://cse.sc.edu/~terejanu/files/tutorialUKF.pdf>
- `nav2_amcl` configuration (the parameters in §6): <https://docs.nav2.org/configuration/packages/configuring-amcl.html>
- `robot_localization` `ukf_node` (the UKF in a real ROS package): <https://github.com/cra-ros-pkg/robot_localization>
- Barfoot — *State Estimation for Robotics*, Ch. 4 (sigma-point methods): <http://asrl.utias.utoronto.ca/~tdb/bib/barfoot_ser_17.pdf>
