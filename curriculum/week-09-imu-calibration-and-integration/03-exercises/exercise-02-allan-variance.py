#!/usr/bin/env python3
# Exercise 2 — Compute the Allan variance (and verify it on a known signal)
#
# Goal: Implement the overlapping Allan deviation for a stationary rate signal,
#       extract the random-walk coefficient N and the bias instability B, and
#       VERIFY your implementation on a synthetic signal whose N you set yourself
#       -- so you trust the code before running it on real IMU data.
#
# Estimated time: 60 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone. NumPy + Matplotlib, no ROS:
#
#       pip install numpy matplotlib
#       python3 exercise-02-allan-variance.py
#
#   By default it generates a SYNTHETIC gyro signal with a KNOWN angle-random-walk
#   N_true, computes the Allan deviation, extracts N from the -1/2 slope, and
#   asserts the extracted N is within tolerance of N_true. Then it saves a plot.
#
#   To run on YOUR real data, load a 1-D array of one gyro axis (rad/s) from your
#   bag/csv and pass it to allan_deviation() instead of the synthetic signal.
#
# WHAT TO IMPLEMENT
#
#   Fill in the TODOs in allan_deviation() and extract_random_walk().
#
# ACCEPTANCE CRITERIA
#
#   [ ] On the synthetic signal, the extracted N matches N_true within 15%
#       (the harness asserts this and prints PASS).
#   [ ] A log-log plot is saved to allan_deviation.png showing the -1/2 slope.
#   [ ] You can point to the -1/2 region and the (small, synthetic) floor.
#
# Expected output is at the bottom of the file.

import sys

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # headless-safe
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


def synthetic_gyro(n, fs, n_true, bias_instab=2e-5, seed=0):
    """Synthetic stationary gyro: white noise (sets ARW) + a slow bias random walk.

    n_true is the angle-random-walk coefficient we want to recover (rad/sqrt(s)).
    For discrete white noise of std sigma_w at rate fs, the ARW is N = sigma_w/sqrt(fs).
    So sigma_w = n_true * sqrt(fs).
    """
    rng = np.random.default_rng(seed)
    dt = 1.0 / fs
    sigma_w = n_true * np.sqrt(fs)
    white = rng.normal(0.0, sigma_w, n)
    # Slow bias random walk: integrate small steps.
    bias_walk = np.cumsum(rng.normal(0.0, bias_instab * np.sqrt(dt), n))
    return white + bias_walk


def allan_deviation(data, fs):
    """Overlapping Allan deviation of a stationary RATE signal (rad/s).

    Returns (taus, adev). Integrate rate -> angle, then take the overlapping
    second-difference estimator.
    """
    data = np.asarray(data, dtype=float)
    n = len(data)
    tau0 = 1.0 / fs

    # TODO 1: integrate the rate signal to angle (theta) with cumsum * tau0.
    theta = None  # <-- replace: np.cumsum(data) * tau0

    if theta is None:
        raise NotImplementedError("implement TODO 1 (integrate rate to angle)")

    max_m = (n - 1) // 2
    ms = np.unique(np.floor(np.logspace(0, np.log10(max_m), 100)).astype(int))
    ms = ms[(ms >= 1) & (ms <= max_m)]
    taus = ms * tau0
    adev = np.empty(len(ms))

    for i, m in enumerate(ms):
        # TODO 2: overlapping second difference of theta:
        #   diff = theta[2m:] - 2*theta[m:-m] + theta[:-2m]
        #   sigma2 = sum(diff^2) / (2 * m^2 * (n - 2m))
        #   adev[i] = sqrt(sigma2)
        raise NotImplementedError("implement TODO 2 (overlapping estimator)")

    return taus, adev


def extract_random_walk(taus, adev):
    """Read N (ARW) off the -1/2 slope: the value of the -1/2 line at tau = 1 s.

    Practical method: find points on the falling region (slope ~ -0.5), fit a line
    of slope -0.5 in log-log, and evaluate at tau = 1.
    """
    log_t = np.log10(taus)
    log_a = np.log10(adev)
    # Numerical slope.
    slope = np.gradient(log_a, log_t)

    # TODO 3: pick the index where slope is closest to -0.5, then the -1/2 line
    #         through that point evaluated at tau=1 s is:
    #            log10(N) = log_a[idx] - (-0.5) * (log10(1) - log_t[idx])
    #                     = log_a[idx] + 0.5 * log_t[idx]
    #         return 10**log10(N).
    raise NotImplementedError("implement TODO 3 (extract N at tau=1 s)")


def main() -> int:
    fs = 100.0          # Hz
    duration_s = 1800   # 30 minutes
    n = int(fs * duration_s)
    n_true = 1.2e-3     # rad/sqrt(s) -- the ARW we plant and must recover

    print(f"Generating {duration_s}s synthetic gyro @ {fs} Hz, N_true={n_true:.2e} rad/sqrt(s)")
    sig = synthetic_gyro(n, fs, n_true)

    taus, adev = allan_deviation(sig, fs)
    n_est = extract_random_walk(taus, adev)

    rel_err = abs(n_est - n_true) / n_true
    print(f"extracted N = {n_est:.3e} rad/sqrt(s)  (truth {n_true:.3e}, err {rel_err*100:.1f}%)")
    print(f"bias instability (floor proxy) ~ {adev.min()/0.664:.2e} rad/s")

    if HAVE_MPL:
        plt.figure()
        plt.loglog(taus, adev, ".-")
        plt.xlabel("tau (s)")
        plt.ylabel("Allan deviation (rad/s)")
        plt.title("Gyro Allan deviation")
        plt.grid(True, which="both", ls=":")
        plt.savefig("allan_deviation.png", dpi=120)
        print("saved allan_deviation.png")

    ok = rel_err < 0.15
    print("PASS" if ok else "FAIL: extracted N is off by more than 15% -- check TODO 2/3")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())


# -----------------------------------------------------------------------------
# Expected output (once the TODOs are implemented)
# -----------------------------------------------------------------------------
#
# Generating 1800s synthetic gyro @ 100.0 Hz, N_true=1.20e-03 rad/sqrt(s)
# extracted N = 1.19e-03 rad/sqrt(s)  (truth 1.20e-03, err 0.8%)
# bias instability (floor proxy) ~ 3.x e-05 rad/s
# saved allan_deviation.png
# PASS
#
# The plot shows the -1/2 falling line (white noise / random walk) on the left,
# flattening toward a floor. Because you VERIFIED the extracted N against the N you
# planted, you can now trust allan_deviation() on a real 30-minute /imu/data log:
# load one gyro axis (rad/s) into `sig` and the same code gives you YOUR sensor's
# N and B -- the numbers that go into the IMU covariance (Lecture 2 3.2) and next
# week's EKF.
# -----------------------------------------------------------------------------
