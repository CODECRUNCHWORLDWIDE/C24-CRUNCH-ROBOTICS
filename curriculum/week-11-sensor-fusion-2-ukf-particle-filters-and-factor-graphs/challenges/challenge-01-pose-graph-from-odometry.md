# Challenge 1 — A Pose Graph from Noisy Odometry + One Loop Closure

**Time estimate:** ~90 minutes.

## Problem statement

A robot drove a square loop and returned to where it started. Its wheel odometry, like all wheel odometry (Week 6), *drifted* — and worse, it has a small rotation-calibration bias, so the dead-reckoned trajectory spirals away and the final pose lands almost a meter from the origin it should have returned to. You are the SLAM back-end engineer. You're handed the noisy odometry and a single **loop-closure** constraint (the front-end recognized the start location when the robot came back around). Your job: build a GTSAM pose graph, optimize it, and **quantify how much the loop closure reduced the trajectory error** — then prove your back-end survives a *false* loop closure with a robust noise model.

This is exactly what `slam_toolbox`'s back-end does (Lecture 2 §7): the front-end manufactures factors (odometry + loop closures), the back-end optimizes the graph. You're writing the back-end.

## The harness

Save this as `loop_harness.py`. It generates a true square-loop trajectory, noisy biased odometry, and the data you'll optimize. **Do not change the data-generation block** — that's the "robot" you're given.

```python
#!/usr/bin/env python3
"""Generates a true square-loop trajectory + noisy, rotation-biased odometry.
You build and optimize the pose graph from `odom` and the loop closure."""
import numpy as np
import gtsam
from gtsam import Pose2, NonlinearFactorGraph, Values
from gtsam.symbol_shorthand import X

SEED = 1


def make_world(seed=SEED):
    """Returns (true_poses, noisy_odometry). DO NOT MODIFY — this is your robot."""
    rng = np.random.default_rng(seed)
    moves = [(2.0, 0.0, 0.0), (2.0, 0.0, np.pi / 2)] * 4   # 8 legs, closes the loop
    true = [Pose2(0, 0, 0)]
    for m in moves:
        true.append(true[-1].compose(Pose2(*m)))
    odom = []
    for i in range(len(true) - 1):
        rel = true[i].between(true[i + 1])
        # 0.04 rad/leg rotation BIAS (calibration error) + translation/rotation noise.
        noise = Pose2(rng.normal(0, 0.10), rng.normal(0, 0.10), 0.04 + rng.normal(0, 0.03))
        odom.append(rel.compose(noise))
    return true, odom


def dead_reckon(odom):
    """Compose the noisy odometry into a drifting trajectory (the initial guess)."""
    poses = [Pose2(0, 0, 0)]
    for o in odom:
        poses.append(poses[-1].compose(o))
    return poses


def ate(result, true, n):
    """Absolute Trajectory Error: RMS position error vs ground truth."""
    errs = [np.hypot(result.atPose2(X(i)).x() - true[i].x(),
                     result.atPose2(X(i)).y() - true[i].y())
            for i in range(n)]
    return float(np.sqrt(np.mean(np.array(errs) ** 2)))


if __name__ == "__main__":
    true, odom = make_world()
    dr = dead_reckon(odom)
    N = len(true)
    print(f"poses: {N}")
    print(f"true final pose:        ({true[-1].x():.2f}, {true[-1].y():.2f})  "
          "(the loop closes — back at origin)")
    print(f"dead-reckoned final:    ({dr[-1].x():.2f}, {dr[-1].y():.2f})  "
          "(drifted — this is the problem)")
    # YOUR CODE: build the graph, optimize open and with loop closure, report ATE.
```

```bash
source /opt/ros/jazzy/setup.bash      # only needed if you use ROS; pure GTSAM doesn't
python3 loop_harness.py
```

You should see the dead-reckoned final pose land well away from the origin — that's the drift you're going to fix.

## Your task

Write `pose_graph_solve.py` that imports `make_world`, `dead_reckon`, and `ate` from the harness and does the following:

1. **Build the open chain.** A `NonlinearFactorGraph` with a prior on `X(0)` at the origin and a `BetweenFactorPose2` for every odometry step. Optimize it with Levenberg-Marquardt, using the dead-reckoned trajectory as the initial `Values`. Report `ate(...)` — this is your baseline.
2. **Add the loop closure.** Rebuild the graph and add **one** `BetweenFactorPose2(X(0), X(N-1), ...)` encoding "the last pose is back at the start." Use the *true* closing relative pose `true[0].between(true[-1])` as the measurement (the front-end gave you a good loop closure). Optimize and report `ate(...)` again.
3. **Quantify the improvement.** Print the open-chain ATE, the loop-closure ATE, and the percentage reduction. The loop closure must *measurably* reduce the trajectory error.
4. **Report the marginals.** Print `trace(marginalCovariance(X(k)))` for the pose halfway around the loop (`X(N//2)`), open vs. loop-closed. The loop closure should shrink it — the pose furthest from the prior benefits most.

## Acceptance criteria

- [ ] A file `pose_graph_solve.py` that builds both graphs and prints open-chain ATE, loop-closed ATE, and the percentage reduction.
- [ ] The loop closure reduces ATE by a clear margin (on `SEED=1` you should see roughly **0.6 m → 0.12 m**, an ~80% reduction; exact numbers depend on your gtsam build).
- [ ] You report the `X(N//2)` marginal-covariance trace open vs. loop-closed and confirm the loop closure shrank it.
- [ ] A short `challenge-01-writeup.md` answering: *(a)* why the open chain drifts even though every individual odometry factor is "correct"; *(b)* what the loop closure physically constrains; *(c)* why the correction propagates to poses in the *middle* of the loop, not just the endpoint (the smoother re-distributes error across all variables — Lecture 2 §1).
- [ ] Committed to your Week 11 repo under `challenges/challenge-01/`.

## The trap: the false loop closure (do this after the good one works)

Real loop-closure front-ends make mistakes — perceptual aliasing makes two different corridors look identical, and the front-end emits a *wrong* loop closure. Add a **second, false** loop closure: `BetweenFactorPose2(X(2), X(6), Pose2(5.0, 5.0, 0.0), ...)` — a constraint that is simply not true. With a plain Gaussian noise model, least squares believes it and drags the whole trajectory off the truth (your ATE will *rise*, possibly above the open-chain baseline). That is the failure mode.

Now wrap the loop-closure noise models in a **robust kernel** (Lecture 2 §4):

```python
base = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.05, 0.05, 0.03]))
huber = gtsam.noiseModel.mEstimator.Huber.Create(1.345)
robust_loop = gtsam.noiseModel.Robust.Create(huber, base)
# use robust_loop for BOTH loop-closure factors
```

Re-optimize. The Huber kernel recognizes the false closure as an outlier and down-weights it; the good closure and the odometry win, and your ATE drops back near the good-loop-closure number. **Demonstrate both: ATE with the false closure under a plain Gaussian (bad) and under Huber (recovered), in your writeup.** This is the single most important robustness lesson in pose-graph SLAM — and the reason every production back-end uses robust kernels on automatic loop closures.

## Stretch

- **Incremental (iSAM2).** Re-solve the *good* graph with `gtsam.ISAM2`: add the prior + `X(0)`, `update()`; then each odometry step adds one between factor + one variable, `update()`; finally add the loop closure, `update()`. Confirm you get the same final ATE as the batch solve, and note that the loop-closure `update()` is the one that triggers the large back-propagation (the Bayes tree re-optimizes the affected poses).
- **Sweep the bias.** Set the rotation bias to `0.0` (no calibration error) and re-run. With no systematic drift, the open chain is already nearly consistent and the loop closure barely helps — proving that loop closures earn their keep precisely when there's *accumulated* error to undo.
- **Two loop closures, both true.** Add a mid-loop true closure as well as the end closure. More constraints → lower ATE and tighter marginals everywhere. This is why dense loop-closure detection matters for map quality.

## Why this matters

In Week 16 you defend your perception and estimation stack to a panel. They will point at your SLAM map and ask "how do you know your loop closures are good, and what happens when one is wrong?" The honest answer — "the back-end is a robustly-weighted pose graph; a single bad closure is down-weighted by a Huber kernel, and here's the ATE with and without it" — is the difference between a learner who *used* SLAM and an engineer who *understands* it. Every robotics on-call rotation eventually hands you a map that drifted because a loop closure was bad. The engineer who can name it and fix the noise model is the one who gets paged less.
