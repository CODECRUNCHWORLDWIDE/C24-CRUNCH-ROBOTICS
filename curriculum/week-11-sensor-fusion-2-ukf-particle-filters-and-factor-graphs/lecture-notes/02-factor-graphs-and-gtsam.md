# Lecture 2 — Factor Graphs and GTSAM: The Estimator That Stops Lying

> **Duration:** ~2 hours of reading + hands-on.
> **Outcome:** You can explain the difference between a filter and a smoother precisely, describe a factor graph as variables + factors and why MAP estimation on it is nonlinear least squares, build and solve a factor graph in GTSAM's Python bindings by hand, read the marginal covariances, and explain why every modern SLAM back-end is a factor graph and why iSAM2 makes it fast enough to run online.

Lecture 1 ended on a cliff: the UKF and the particle filter are both *filters*, and a filter throws the past away. This lecture is about what you do when you can't afford to. If you remember one sentence:

> **A filter compresses all history into one belief and is constant-time but cannot revisit the past. A smoother keeps the constraints and re-optimizes the whole trajectory, so a loop closure discovered now can correct a pose from five minutes ago. The factor graph is the data structure that makes smoothing tractable, and it is the structure under every modern SLAM system.**

---

## 1. Filters vs. smoothers: the central distinction of estimation

Set up the contrast carefully, because it is the conceptual core of the week.

A **filter** (Kalman, EKF, UKF, particle) maintains a belief over only the *current* state. Each step it does `predict` (push the belief forward through the motion model) and `update` (correct with the latest measurement). Crucially, it relies on the **Markov assumption**: the current state summarizes everything you need from the past. To stay constant-time, the filter *marginalizes out* old states — it integrates them away into the current belief. That marginalization is irreversible. Once pose `x₅` has been folded into the belief at `x₆`, there is no `x₅` to correct anymore. If at `x₁₀₀` you drive past your starting point and recognize it (a **loop closure**), a filter can use that to correct `x₁₀₀`, but it cannot reach back and straighten out the drift that accumulated in `x₅` through `x₉₉`. The information is gone.

A **smoother** keeps the constraints around. It maintains the *whole trajectory* `x₀ … xₜ` as variables, and every measurement is stored as a **constraint** (a factor) relating the variables it touches. When a loop closure arrives, the smoother adds it as one more constraint and **re-optimizes the entire trajectory**, distributing the correction backward through every pose. The drift that the filter baked in permanently, the smoother *undoes*. The price: it is not constant-time — a naive batch smoother re-solves a growing problem every step.

```
FILTER (forward-only, constant time)        SMOOTHER (keeps constraints, re-optimizes)

  x0 → x1 → x2 → ... → xt                      x0 ── x1 ── x2 ── ... ── xt
  (each step marginalizes the past)             │                        │
  loop closure corrects only xt                 └────── loop closure ────┘
                                                (correction flows to ALL poses)
```

Where do our four estimators sit? The EKF and UKF are filters (Gaussian belief, forward-only). The particle filter is a filter (nonparametric belief, forward-only). The **factor graph optimizer is a smoother** — and the magic of the last fifteen years of SLAM research is making it *incremental*, so you get most of the smoother's accuracy at close to a filter's cost. That is iSAM2 (§7).

> **The taste test you will defend at the Phase 2 midterm:** use a filter when you need a bounded-time current-state estimate and you'll never need to revisit the past (a control loop reading fused odometry at 100 Hz — that's the Week 10 EKF, and it's the right call). Use a smoother when global consistency across a long trajectory matters and loop closures must propagate backward (SLAM — that's a factor graph). Both are correct tools; using the wrong one is the mistake.

There's a deeper reason the filter's marginalization is lossy, worth one paragraph because it explains why "just keep filtering" eventually fails. When a filter marginalizes out an old pose, that pose's uncertainty doesn't vanish — it gets *folded into correlations* among the remaining states. In the information (inverse-covariance) form, marginalizing a variable connected to several others creates **fill-in**: new off-diagonal terms linking everything the marginalized variable touched. The filter can't afford to track all those correlations exactly, so it approximates — and in the EKF's case, it approximates *at the same time as it linearizes*, compounding both errors. The result is the slow, silent covariance corruption you saw with the EKF in Lecture 1. A smoother sidesteps this entirely: it never marginalizes, so it never approximates the correlations away. It pays for that with a bigger problem to solve, and iSAM2 is the trick that makes solving it cheap. So the filter-vs-smoother choice is, at bottom, a choice between *approximating the past* (cheap, eventually wrong) and *keeping the past* (exact, more expensive) — and knowing which you can afford is the senior call.

---

## 2. What is a factor graph?

A **factor graph** is a bipartite graph with two kinds of nodes:

- **Variable nodes** — the unknowns you want to estimate. In SLAM these are robot poses (`x₀, x₁, …`) and sometimes landmark positions (`l₀, l₁, …`).
- **Factor nodes** — constraints, each connecting one or more variables. A factor is a *probabilistic statement* about the variables it touches: "I measured the relative pose between `x₀` and `x₁` to be this, with this uncertainty."

Edges connect each factor to exactly the variables it constrains. Three factor types cover most of SLAM:

- A **prior factor** ties one variable to an absolute value with some uncertainty: "`x₀` is at the origin, and I'm quite sure." Without at least one prior, the whole graph floats — there's no anchor to the world frame, and the problem is under-determined (any rigid transform of the solution fits equally well). Every factor graph needs at least one prior to be solvable.
- A **between factor** is a *relative* constraint between two pose variables: "the transform from `x₀` to `x₁` is this." Odometry produces a between factor every step. A **loop closure** is *also* a between factor — between two poses far apart in time that turn out to be near each other in space.
- A **measurement/landmark factor** relates a pose to a landmark: "from `x₃` I observed landmark `l₀` at this range and bearing."

```
  prior          between(odom)      between(odom)
   │                  │                  │
  (x0) ──────────── (x1) ──────────── (x2)
   │                                     │
   └──────── between (loop closure) ─────┘
```

### 2.1 Why MAP estimation on a factor graph is least squares

Each factor encodes a probability `p(measurement | variables)`. Assuming Gaussian noise — which we almost always do — each factor's negative log-likelihood is a *squared, covariance-weighted error*:

```
−log p  ∝  ‖ error(variables) ‖²_Σ⁻¹   =   error(variables)ᵀ Σ⁻¹ error(variables)
```

The **maximum a posteriori (MAP)** estimate maximizes the product of all factor probabilities, which (taking the negative log) means **minimizing the sum of all the squared, weighted factor errors**:

```
x* = argmin_x  Σ_factors  ‖ errorᵢ(x) ‖²_Σᵢ⁻¹
```

That is a **nonlinear least-squares** problem. The error functions are nonlinear (poses live on a manifold, `SE(2)`/`SE(3)`), so we solve it iteratively — Gauss-Newton or Levenberg-Marquardt — linearizing each factor at the current estimate, solving the resulting sparse linear system, stepping, and repeating until convergence. The graph's **sparsity** (each factor touches only a few variables) is what makes this tractable even for thousands of poses: the linear system is sparse, and a good variable ordering keeps the factorization cheap. This is the whole reason factor graphs won — they expose the sparsity that makes large-scale smoothing solvable.

---

## 3. GTSAM: building a factor graph by hand

**GTSAM** (Georgia Tech Smoothing And Mapping) is the reference factor-graph library. We use its Python bindings (`pip install gtsam`). The workflow is always the same four objects:

1. A `NonlinearFactorGraph` — you add factors to it.
2. **Noise models** — the `Σ` for each factor (`gtsam.noiseModel.Diagonal.Sigmas([...])`).
3. A `Values` — your *initial guess* for every variable (the optimizer needs a starting point).
4. An **optimizer** — `LevenbergMarquardtOptimizer` — which returns the optimized `Values`.

Here is a complete, runnable two-pose example. This is exactly the structure of Exercise 3 — a prior, two poses, one between factor — and it is the smallest factor graph that teaches the whole workflow.

```python
import gtsam
import numpy as np
from gtsam import Pose2, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X     # X(0), X(1), ... are pose-variable keys


def build_two_pose_graph():
    graph = NonlinearFactorGraph()

    # Noise models: standard deviations on (x, y, theta).
    prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.1, 0.1, 0.05]))
    odom_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.2, 0.2, 0.1]))

    # Prior: anchor x0 at the origin. Without this the graph floats.
    graph.add(gtsam.PriorFactorPose2(X(0), Pose2(0.0, 0.0, 0.0), prior_noise))

    # Between factor: odometry says we moved +2 m in x with no rotation.
    graph.add(gtsam.BetweenFactorPose2(
        X(0), X(1), Pose2(2.0, 0.0, 0.0), odom_noise))

    return graph


def solve(graph, initial):
    params = gtsam.LevenbergMarquardtParams()
    optimizer = gtsam.LevenbergMarquardtOptimizer(graph, initial, params)
    result = optimizer.optimize()
    return result


if __name__ == "__main__":
    graph = build_two_pose_graph()

    # Initial guess: deliberately WRONG so we can watch the optimizer fix it.
    initial = Values()
    initial.insert(X(0), Pose2(0.3, 0.2, 0.1))     # should converge to (0,0,0)
    initial.insert(X(1), Pose2(2.3, 0.1, -0.2))    # should converge to (2,0,0)

    print(f"initial error: {graph.error(initial):.4e}")
    result = solve(graph, initial)
    print(f"final   error: {graph.error(result):.4e}")

    p0 = result.atPose2(X(0))
    p1 = result.atPose2(X(1))
    print(f"optimized x0: ({p0.x():.4f}, {p0.y():.4f}, {p0.theta():.4f})")
    print(f"optimized x1: ({p1.x():.4f}, {p1.y():.4f}, {p1.theta():.4f})")
```

Run it and you should see the optimizer drive a large initial error to essentially zero, landing `x0` on the origin (the prior wins) and `x1` at `(2, 0, 0)` (the prior + odometry agree):

```
initial error: 9.1180e+00
final   error: 1.2436e-13
optimized x0: (0.0000, 0.0000, 0.0000)
optimized x1: (2.0000, 0.0000, 0.0000)
```

This is the **"the estimate converged" promise** for factor graphs: on a consistent, noise-free graph, the final error is numerically zero and the answer matches your hand calculation. Exercise 3 makes you do that hand calculation first and confirm GTSAM agrees.

### 3.1 The hand calculation, worked

You should be able to predict that answer *before* running GTSAM, and on a graph this small you can do it in your head — which is exactly the habit that catches a mis-specified graph. There are two factors and two unknowns (`x0`, `x1`). The total cost is:

```
J(x0, x1) = ‖ x0 − (0,0,0) ‖²_prior  +  ‖ (x0⁻¹ ∘ x1) − (2,0,0) ‖²_odom
```

The first term is minimized when `x0 = (0,0,0)`. Given that, the second term is minimized when the *relative* pose from `x0` to `x1` equals `(2,0,0)` — i.e. `x1 = (2,0,0)`. Both terms hit zero simultaneously, so the global minimum is `J = 0` at `x0=(0,0,0)`, `x1=(2,0,0)`, with no trade-off between them. That is why the final error is numerically zero: the two factors *agree*, so there is a configuration that satisfies both exactly.

Now imagine the factors *disagreed* — say the prior said `x0=(0,0,0)` but a *second* prior said `x0=(0.4,0,0)`. Then no configuration satisfies both, the minimum cost is positive, and `x0` settles at a covariance-weighted compromise between `0` and `0.4` (closer to whichever prior has the smaller sigma). That positive residual error is the graph telling you its constraints are inconsistent — which, for real noisy data, they always are a little. **The skill is reading the final error: ~0 means consistent constraints; a large residual on a graph you expected to be consistent means a bug or a bad measurement.** That reading is the factor-graph analogue of the filter's NEES check from Lecture 1.

---

## 4. Noise models and what they mean

The noise model is the factor's covariance, and getting it honest is as important here as it was for the EKF. GTSAM gives you several constructors:

- `gtsam.noiseModel.Diagonal.Sigmas([sx, sy, stheta])` — independent per-axis standard deviations. The everyday choice; you pass *sigmas (std-devs), not variances*. A common bug is passing variances and getting an over- or under-confident factor.
- `gtsam.noiseModel.Gaussian.Covariance(Sigma)` — a full covariance matrix when axes are correlated.
- `gtsam.noiseModel.Isotropic.Sigma(dim, s)` — the same sigma on every axis.
- `gtsam.noiseModel.Robust.Create(gtsam.noiseModel.mEstimator.Huber.Create(k), base)` — wraps a base model in a **robust kernel** (Huber, Cauchy, Tukey) that down-weights gross outliers.

That last one matters enormously for loop closures. A **false loop closure** — the place-recognition front-end says "you're back at pose 3" when you are not — is a single, gross, wrong constraint. With a plain Gaussian noise model, least squares treats it as gospel and drags the whole trajectory off the truth to satisfy it. With a Huber kernel, the optimizer recognizes that one factor's error is an outlier and down-weights it, so the good constraints win. **In any real pose graph with automatic loop closures, the loop-closure factors get robust noise models.** The stretch goal in this week's exercises has you plant a bad loop closure and watch Huber save the trajectory.

---

## 5. Marginals: reading the uncertainty back out

The optimizer gives you the *mean* trajectory. To get each pose's *covariance* — the uncertainty the smoother assigns — you ask for the **marginals**:

```python
marginals = gtsam.Marginals(graph, result)
cov_x1 = marginals.marginalCovariance(X(1))     # 3x3 covariance on (x, y, theta)
print("x1 covariance:\n", cov_x1)
```

This is the smoother's analogue of the filter's `Σ`. A pose far from any prior, constrained only by a chain of noisy odometry, has a large marginal covariance — the optimizer is telling you it's unsure where that pose is in the world frame. A pose pinned by both odometry *and* a loop closure has a much smaller marginal. Watching the marginals shrink when you add a loop closure is the quantitative version of "the loop closure tightened the map," and your mini-project should report it.

> **A caution on marginals:** computing `Marginals` requires factorizing the full information matrix, which is the *expensive* part of the optimize-then-report cycle. For a small pose graph it's free; for a 10,000-pose map it is not, and production systems only compute the marginals they actually need (the current pose, the poses involved in a candidate loop closure) rather than all of them. Don't reflexively dump every pose's covariance every cycle — that's a real way to blow your latency budget, and the Week 16 reviewer will notice.

---

## 6. Landmark factors and bundle adjustment: the same machinery, one more variable type

So far our graphs have only pose variables and pose-to-pose factors. Real SLAM also estimates the *world* — landmarks the robot observes — and that fits the exact same framework with one addition: a **landmark variable** and a **measurement factor** that relates a pose to a landmark.

Picture the robot at pose `x₃` observing a landmark `l₀` (a corner, a tag, a tracked feature) at a measured range and bearing. That observation is a factor connecting `x₃` and `l₀`: "from where `x₃` is, `l₀` should appear at this range-bearing; here's how wrong that is for the current estimates of both." GTSAM ships `BearingRangeFactor2D` for exactly this:

```python
import gtsam
from gtsam import Pose2, Point2
from gtsam.symbol_shorthand import X, L     # X for poses, L for landmarks

graph = gtsam.NonlinearFactorGraph()
meas_noise = gtsam.noiseModel.Diagonal.Sigmas([0.1, 0.2])   # [bearing(rad), range(m)]

# From pose x3, landmark l0 was seen at bearing 0.3 rad, range 4.0 m.
graph.add(gtsam.BearingRangeFactor2D(
    X(3), L(0),
    gtsam.Rot2.fromAngle(0.3),   # measured bearing
    4.0,                         # measured range
    meas_noise))
```

Now the optimizer solves for poses *and* landmark positions jointly: every pose is constrained by odometry and by the landmarks it sees, every landmark is constrained by the poses that see it, and the whole thing settles into the configuration that best explains all the measurements. A landmark seen from many poses gets pinned tightly; a pose that sees many well-known landmarks gets pinned tightly. This mutual constraint is what makes feature-based SLAM work.

When the "measurement" is a camera **reprojection** — a 3D point projected through a calibrated camera into a 2D pixel — this same structure is called **bundle adjustment**, the workhorse of visual SLAM and structure-from-motion. The variables are camera poses (`Pose3`) and 3D points; the factors are reprojection-error factors (`GenericProjectionFactorCal3_S2` in GTSAM); the optimizer minimizes the sum of squared pixel reprojection errors. ORB-SLAM3's local and global optimization (Lecture 1's promised callback) is bundle adjustment — a factor graph where the factors are "this 3D point should project to this pixel in this camera." You'll meet the camera projection model itself in Week 12; the point here is that *it's the same factor graph*, just with projection factors instead of between factors. Learn the machinery once and it generalizes from pose-graph SLAM to full visual-inertial bundle adjustment.

This is the deep reason factor graphs took over robotics: **poses, landmarks, IMU preintegration, GPS, camera reprojection, and even some control problems all express as variables + factors.** A single optimizer (and a single library, GTSAM) handles all of them. The skill you're building this week — "what are my variables, what are my factors, what are their noise models?" — is the skill that unlocks the entire modern estimation stack.

---

## 7. iSAM2: making the smoother run online

The catch with batch optimization is cost: re-solving the whole graph from scratch every time a factor arrives is `O(n)` or worse per step, and `n` grows forever. For a robot that runs for hours, that's untenable. **iSAM2** (incremental Smoothing And Mapping, version 2) is the algorithm that fixes it, and it is why factor-graph SLAM runs in real time in 2026.

The idea: when you add a new factor, *most* of the graph doesn't change. iSAM2 organizes the problem as a **Bayes tree** (a directed structure derived from the graph's elimination ordering) and, when new factors arrive, re-linearizes and re-solves only the *part of the tree affected by the new information* — typically a small, recent subset of poses. Poses far in the past, untouched by the new factor, stay fixed. You get the accuracy of the full smoother but pay roughly constant cost per step in the common case, with occasional larger updates when a loop closure ripples further back.

The GTSAM API mirrors the batch one, but you call `update()` incrementally instead of optimizing from scratch:

```python
import gtsam
from gtsam import Pose2, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X

isam = gtsam.ISAM2()

# Step 0: add the prior and the first pose.
graph = NonlinearFactorGraph()
initial = Values()
prior_noise = gtsam.noiseModel.Diagonal.Sigmas([0.1, 0.1, 0.05])
graph.add(gtsam.PriorFactorPose2(X(0), Pose2(0, 0, 0), prior_noise))
initial.insert(X(0), Pose2(0, 0, 0))
isam.update(graph, initial)
estimate = isam.calculateEstimate()

# Step 1..N: each step adds only the NEW factors and the NEW variable.
odom_noise = gtsam.noiseModel.Diagonal.Sigmas([0.2, 0.2, 0.1])
for k in range(1, 5):
    graph = NonlinearFactorGraph()       # a FRESH small graph each step
    initial = Values()
    graph.add(gtsam.BetweenFactorPose2(
        X(k - 1), X(k), Pose2(1.0, 0.0, 0.0), odom_noise))
    # Seed the new variable from the previous estimate composed with odometry.
    prev = estimate.atPose2(X(k - 1))
    initial.insert(X(k), prev.compose(Pose2(1.0, 0.0, 0.0)))
    isam.update(graph, initial)          # incremental: only re-solves what changed
    estimate = isam.calculateEstimate()

print("final pose:", estimate.atPose2(X(4)))
```

The stretch goal in Exercise 3 asks you to convert your batch graph to exactly this incremental form and confirm you get the same answer at a fraction of the per-step cost. That conversion — batch to incremental — is the single most important practical step between "I understand factor graphs" and "I can ship factor-graph SLAM."

---

## 8. The bridge: why every modern SLAM back-end is a factor graph

This is where the whole week pays off. You ran `slam_toolbox` in Week 7 and AMCL in Exercise 1 without seeing their guts. Here is what they actually are:

- **`slam_toolbox`** is a **pose-graph SLAM** system. Its front-end does scan matching to produce *between factors* (consecutive-scan odometry and loop closures); its back-end is a factor-graph optimizer (it uses Ceres/g2o-style sparse optimization, the same math as GTSAM). The "map" you saved was a *by-product* — the real state is the optimized pose graph, and the occupancy grid is rendered from it. When `slam_toolbox` "closes a loop and the map snaps straight," that is the back-end re-optimizing the factor graph exactly as in §3.
- **GTSAM-based LIO** (LiDAR-Inertial Odometry — LIO-SAM, the GTSAM-based stacks you'll meet in Phase 2's 3D perception work) builds a factor graph with IMU-preintegration factors, LiDAR-odometry between factors, and GPS priors, and solves it with iSAM2. Same structure, more factor types.
- **ORB-SLAM3's** local bundle adjustment and its loop-closing/full-BA are factor-graph optimizations over camera poses and 3D map points — bundle adjustment *is* a factor graph where the factors are reprojection errors.

So the punchline of Lecture 1's title — "modern SLAM front-ends emit factors, not means" — is now concrete. A SLAM front-end's job is to *manufacture factors* (from scans, images, IMU). The back-end's job is to *optimize the factor graph* those factors define. Filtering-based SLAM (the old EKF-SLAM) marginalized poses away and couldn't undo drift; factor-graph SLAM keeps them and re-optimizes, which is why it won. You will not write a full SLAM system this week — but after the mini-project, where you ingest real `nav_msgs/Odometry` and loop closures into a GTSAM graph and publish an optimized trajectory, you will have built the back-end of one, by hand.

---

## 9. The estimation-method decision tree

When someone hands you an estimation problem, walk this tree:

```
Do you need to revisit/correct past states (loop closures, global consistency)?
│
├─ No  → a FILTER is fine.
│   │
│   ├─ Belief unimodal & roughly Gaussian?
│   │   ├─ Mild nonlinearity      → EKF (cheapest; Week 10).
│   │   └─ Strong nonlinearity    → UKF (no Jacobians; Lecture 1 §3).
│   └─ Belief multimodal / global localization → PARTICLE FILTER / AMCL.
│
└─ Yes → a SMOOTHER. Build a FACTOR GRAPH.
    │
    ├─ Batch / offline / small      → LevenbergMarquardt (Lecture 2 §3).
    └─ Online / large / incremental → iSAM2 (Lecture 2 §7).
```

Tape this next to Lecture 1's UKF-vs-EKF guidance. Between the two, you can pick the right estimator for any problem in Phase 2 and defend the choice — which is exactly what the midterm reviewer will ask you to do.

---

## 10. The five mistakes that break a first factor graph

When you build your first GTSAM graph in Exercise 3 and the mini-project, these are the five errors that account for nearly every "it didn't converge" or "the answer is garbage" — listed so you recognize them on sight:

1. **No prior.** The graph floats. The optimizer either fails outright (singular system) or returns a solution shifted by an arbitrary rigid transform. *Fix:* add exactly one `PriorFactorPose2` to anchor the first pose.

2. **Sigmas vs. variances.** `noiseModel.Diagonal.Sigmas([...])` takes *standard deviations*, not variances. Passing variances (e.g. `0.04` where you meant `sigma=0.2`) makes the factor wildly over- or under-confident. *Fix:* always pass std-devs; if you have a covariance, use `Gaussian.Covariance(Σ)` instead.

3. **A bad initial guess.** Levenberg-Marquardt is a *local* optimizer; on a nonlinear pose graph, a wild initial `Values` can land it in a bad local minimum (a pose flipped 180°, a tangled trajectory). *Fix:* seed each new pose from the previous estimate composed with the odometry, never from the origin.

4. **A non-robust loop closure.** One false loop closure under a plain Gaussian model destroys the whole trajectory (Challenge 1's trap). *Fix:* wrap loop-closure noise models in a Huber kernel.

5. **Wrong relative-pose convention.** `BetweenFactorPose2(a, b, rel)` expects `rel` to be the transform *from a's frame to b's frame* (`a.between(b)`), not `b.between(a)` and not the absolute pose of `b`. Getting the direction backward inverts every constraint. *Fix:* compute `rel = pose_a.between(pose_b)` and test it on a noise-free pair where you know the answer.

Every one of these produces a *specific* symptom — a singular solve, an over-tight covariance, a flipped pose, a corrupted trajectory, an inverted map. Learning to map symptom → mistake is the same diagnostic skill you built for QoS in Week 5, applied to estimation.

---

## 11. Recap

You should now be able to:

- State the filter-vs-smoother distinction precisely: a filter marginalizes the past (constant-time, can't revisit); a smoother keeps constraints (re-optimizes, gets the whole trajectory right).
- Describe a factor graph as variables + factors, and explain why MAP estimation on it is sparse nonlinear least squares.
- Build a factor graph in GTSAM — prior, between factors, noise models — solve it with Levenberg-Marquardt, and read the marginals.
- Use a robust (Huber) noise model on loop-closure factors and explain why a bad loop closure destroys a plain-Gaussian solve.
- Convert a batch solve to incremental iSAM2 and say why that's what makes online factor-graph SLAM possible.
- Explain why `slam_toolbox`, GTSAM-LIO, and ORB-SLAM3 are all factor graphs under the hood.

Next: the exercises put all three estimators in your hands — AMCL on your map, a UKF-vs-EKF bake-off, and your first solved GTSAM graph. Continue to [the exercises](../exercises/README.md).

---

## References

- Dellaert & Kaess — *Factor Graphs for Robot Perception* (the canonical intro): <https://www.cs.cmu.edu/~kaess/pub/Dellaert17fnt.pdf>
- GTSAM Python examples (`Pose2SLAMExample`, `OdometryExample`): <https://github.com/borglab/gtsam/tree/develop/python/gtsam/examples>
- GTSAM tutorials and Doxygen: <https://gtsam.org/tutorials/intro.html>
- Kaess et al. — "iSAM2: Incremental Smoothing and Mapping Using the Bayes Tree" (IJRR 2012): <https://www.cs.cmu.edu/~kaess/pub/Kaess12ijrr.pdf>
- `slam_toolbox` (pose-graph SLAM you ran in Week 7): <https://github.com/SteveMacenski/slam_toolbox>
- Barfoot — *State Estimation for Robotics*, batch estimation chapters: <http://asrl.utias.utoronto.ca/~tdb/bib/barfoot_ser_17.pdf>
