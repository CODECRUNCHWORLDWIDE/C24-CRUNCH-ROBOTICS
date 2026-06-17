#!/usr/bin/env python3
# Exercise 2 — The scalar Kalman filter (watch covariance breathe)
#
# Goal: Implement a 1-D Kalman filter from scratch -- predict and update -- and
#       WATCH the covariance grow on predict (uncertainty added) and shrink on
#       update (information added). This is the whole intuition of the week in the
#       simplest possible setting, verified against a known signal.
#
# Estimated time: 60 minutes. Runnable.
#
# THE SETUP
#
#   We estimate a slowly-moving 1-D position. The "truth" is a smooth ramp. We get
#   noisy position measurements (measurement noise R). Our motion model assumes the
#   position roughly holds (a random walk), with process noise Q. The filter should:
#     * track the truth far better than the raw noisy measurements,
#     * show P GROWING during predict and SHRINKING at each update.
#
# HOW TO USE THIS FILE
#
#   Standalone. NumPy (+ Matplotlib optional):
#       pip install numpy matplotlib
#       python3 exercise-02-scalar-kalman.py
#
#   Fill in the two TODOs (predict and update). The harness then checks the filtered
#   RMSE beats the raw-measurement RMSE and that P breathes (grows on predict,
#   shrinks on update), printing PASS/FAIL.
#
# ACCEPTANCE CRITERIA
#
#   [ ] predict() grows P by Q; update() shrinks P toward R via the Kalman gain.
#   [ ] Filtered RMSE < raw-measurement RMSE (the filter helps).
#   [ ] You can point to a step where P grew (predict) and one where it shrank (update).
#
# Expected output is at the bottom of the file.

import sys

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


class ScalarKF:
    """1-D Kalman filter. State x (position), covariance P (scalar variance)."""

    def __init__(self, x0, p0, q, r):
        self.x = float(x0)      # estimate (mean)
        self.p = float(p0)      # covariance (variance)
        self.q = float(q)       # process noise
        self.r = float(r)       # measurement noise
        self.last_gain = 0.0

    def predict(self):
        """Random-walk motion model: x stays, but uncertainty GROWS by Q.

        x_pred = x           (F = 1, no control)
        p_pred = p + q       (P = F P F^T + Q  with F=1)
        """
        # TODO 1: implement the predict step (mean unchanged, p grows by q).
        raise NotImplementedError("implement TODO 1 (predict: p += q)")

    def update(self, z):
        """Fold in a measurement z (H = 1). Covariance SHRINKS.

        y = z - x                 (innovation)
        s = p + r                 (innovation covariance, H=1)
        k = p / s                 (Kalman gain)
        x = x + k * y             (correct toward measurement)
        p = (1 - k) * p           (shrink)
        """
        # TODO 2: implement the update step. Store the gain in self.last_gain.
        raise NotImplementedError("implement TODO 2 (update: gain, correct, shrink)")


def main() -> int:
    rng = np.random.default_rng(0)
    n = 200
    dt_truth = 0.02
    truth = np.cumsum(np.full(n, dt_truth))     # a smooth ramp (true position)

    r = 0.25 ** 2                                # measurement noise variance
    meas = truth + rng.normal(0.0, np.sqrt(r), n)

    q = 1e-4                                      # process noise (tune-able)
    kf = ScalarKF(x0=0.0, p0=1.0, q=q, r=r)

    est = np.empty(n)
    p_after_predict = np.empty(n)
    p_after_update = np.empty(n)

    for k in range(n):
        kf.predict()
        p_after_predict[k] = kf.p
        kf.update(meas[k])
        p_after_update[k] = kf.p
        est[k] = kf.x

    raw_rmse = np.sqrt(np.mean((meas - truth) ** 2))
    filt_rmse = np.sqrt(np.mean((est - truth) ** 2))

    # P should be larger right after predict than right after the previous update.
    breathes = np.all(p_after_predict[1:] >= p_after_update[:-1] - 1e-12)

    print(f"raw measurement RMSE : {raw_rmse:.4f}")
    print(f"filtered estimate RMSE: {filt_rmse:.4f}")
    print(f"P breathes (grows on predict, shrinks on update): {breathes}")

    if HAVE_MPL:
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        a1.plot(truth, "k", label="truth")
        a1.plot(meas, ".", ms=3, alpha=0.4, label="measurements")
        a1.plot(est, "r", label="KF estimate")
        a1.legend(); a1.set_ylabel("position")
        a2.plot(p_after_predict, label="P after predict")
        a2.plot(p_after_update, label="P after update")
        a2.legend(); a2.set_ylabel("covariance P"); a2.set_xlabel("step")
        plt.savefig("scalar_kalman.png", dpi=120)
        print("saved scalar_kalman.png")

    ok = filt_rmse < raw_rmse and breathes
    print("PASS" if ok else "FAIL: filter should beat raw RMSE and P should breathe.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())


# -----------------------------------------------------------------------------
# Expected output (once the TODOs are implemented)
# -----------------------------------------------------------------------------
#
# raw measurement RMSE : 0.24xx
# filtered estimate RMSE: 0.0xxx        <-- markedly smaller; the filter helps
# P breathes (grows on predict, shrinks on update): True
# saved scalar_kalman.png
# PASS
#
# In scalar_kalman.png, the bottom panel is the lesson: a sawtooth where P jumps UP
# at every predict (uncertainty added by the motion model) and DOWN at every update
# (information added by the measurement). That breathing IS the Kalman filter. The
# top panel shows the red estimate hugging the black truth far better than the
# scattered measurements -- two noisy things (a motion model and a measurement)
# fused into one less-noisy estimate. Scale this from 1 state to 15 and you have
# robot_localization.
# -----------------------------------------------------------------------------
