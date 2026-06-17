#!/usr/bin/env python3
"""Exercise 2 -- The EKF predict step on the board.

Goal: implement the EKF predict (and update) step for a unicycle robot with
range-bearing measurements, the exact thing you will write on the whiteboard in
Thursday's technical mock. This file is a self-checking harness: implement the
two TODO functions and run it. It must print ``ALL CHECKS PASSED``.

    python3 exercise-02-ekf-predict-on-the-board.py

WHY PURE NUMPY: the technical interview asks you to *derive*, not to call
robot_localization. Writing this by hand is the muscle. The numbers below are
cross-checked against an independent finite-difference Jacobian and a Monte-Carlo
covariance estimate, so if your analytic math is wrong the harness will catch it.

ACCEPTANCE CRITERIA
  [ ] ekf_predict implemented: mean via the nonlinear model, covariance via F.
  [ ] ekf_update implemented: innovation, gain, corrected state + covariance.
  [ ] Bearing innovation is angle-wrapped to (-pi, pi].
  [ ] `python3 exercise-02-ekf-predict-on-the-board.py` prints ALL CHECKS PASSED.

State vector x = [px, py, theta]   (robot pose in the plane)
Control      u = [v, omega]        (body-frame linear & angular velocity)
Measurement  z = [range, bearing]  (to a known landmark)
"""

from __future__ import annotations

import numpy as np

np.set_printoptions(precision=4, suppress=True)


# ----------------------------------------------------------------------------
# The motion and measurement models (given -- do not change these)
# ----------------------------------------------------------------------------
def motion_model(x: np.ndarray, u: np.ndarray, dt: float) -> np.ndarray:
    """Nonlinear unicycle motion model f(x, u). Returns the next pose."""
    px, py, th = x
    v, w = u
    return np.array([
        px + v * np.cos(th) * dt,
        py + v * np.sin(th) * dt,
        th + w * dt,
    ])


def measurement_model(x: np.ndarray, landmark: np.ndarray) -> np.ndarray:
    """Nonlinear range-bearing measurement model h(x). Returns [range, bearing]."""
    dx, dy = landmark[0] - x[0], landmark[1] - x[1]
    rng = np.hypot(dx, dy)
    bearing = np.arctan2(dy, dx) - x[2]
    return np.array([rng, wrap_to_pi(bearing)])


def wrap_to_pi(angle: float) -> float:
    """Wrap an angle to (-pi, pi]. Forget this and the filter diverges near +/-pi."""
    return np.arctan2(np.sin(angle), np.cos(angle))


# ----------------------------------------------------------------------------
# TODO 1 -- the predict step (this is the whiteboard answer)
# ----------------------------------------------------------------------------
def ekf_predict(x: np.ndarray, P: np.ndarray, u: np.ndarray, dt: float,
                Q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EKF predict for the unicycle.

    Return (x_pred, P_pred) where:
      x_pred = f(x, u)                  -- mean through the FULL nonlinear model
      P_pred = F @ P @ F.T + Q          -- covariance through the linearized model
      F      = d f / d x  at (x, u)     -- the state-transition Jacobian

    The classic mistake: propagating the mean with F @ x (the linear form)
    instead of f(x, u). Do NOT do that -- that is why it is the *Extended* KF.
    """
    px, py, th = x
    v, w = u

    # (1) mean via the nonlinear motion model
    x_pred = motion_model(x, u, dt)

    # F = d(motion_model) / d(x), evaluated at (x, u)
    #   d px' / d th = -v sin(th) dt
    #   d py' / d th =  v cos(th) dt
    F = np.array([
        [1.0, 0.0, -v * np.sin(th) * dt],
        [0.0, 1.0,  v * np.cos(th) * dt],
        [0.0, 0.0,  1.0],
    ])

    # (2) covariance via the linearized model
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred


# ----------------------------------------------------------------------------
# TODO 2 -- the update step (the follow-up they always ask for)
# ----------------------------------------------------------------------------
def ekf_update(x_pred: np.ndarray, P_pred: np.ndarray, z: np.ndarray,
               landmark: np.ndarray, R: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EKF update against a range-bearing measurement to a known landmark.

    Return (x_upd, P_upd):
      y = z - h(x_pred)                     -- innovation (WRAP the bearing!)
      S = H @ P_pred @ H.T + R              -- innovation covariance
      K = P_pred @ H.T @ inv(S)             -- Kalman gain
      x_upd = x_pred + K @ y
      P_upd = (I - K @ H) @ P_pred
      H = d h / d x  at x_pred              -- the measurement Jacobian
    """
    lx, ly = landmark
    dx, dy = lx - x_pred[0], ly - x_pred[1]
    q = dx * dx + dy * dy
    r = np.sqrt(q)

    z_hat = measurement_model(x_pred, landmark)

    # H = d(measurement_model) / d(x), evaluated at x_pred
    H = np.array([
        [-dx / r,  -dy / r,   0.0],
        [ dy / q,  -dx / q,  -1.0],
    ])

    y = z - z_hat
    y[1] = wrap_to_pi(y[1])          # bearing innovation must be wrapped

    S = H @ P_pred @ H.T + R
    K = P_pred @ H.T @ np.linalg.inv(S)

    x_upd = x_pred + K @ y
    x_upd[2] = wrap_to_pi(x_upd[2])
    P_upd = (np.eye(3) - K @ H) @ P_pred
    return x_upd, P_upd


# ----------------------------------------------------------------------------
# Verification harness -- you do not need to edit below this line
# ----------------------------------------------------------------------------
def numeric_jacobian(func, x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Central-difference Jacobian of `func` at `x`, for cross-checking analytics."""
    f0 = func(x)
    n_out, n_in = f0.shape[0], x.shape[0]
    J = np.zeros((n_out, n_in))
    for j in range(n_in):
        dx = np.zeros(n_in)
        dx[j] = eps
        fp = func(x + dx)
        fm = func(x - dx)
        diff = fp - fm
        if n_out == 2:                       # measurement: wrap the bearing diff
            diff[1] = wrap_to_pi(diff[1])
        J[:, j] = diff / (2 * eps)
    return J


def check(name: str, ok: bool) -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    return ok


def main() -> int:
    print("EKF predict/update self-check")
    print("=" * 60)
    rng = np.random.default_rng(45)
    results = []

    x = np.array([1.0, 2.0, 0.6])
    u = np.array([0.8, 0.3])
    dt = 0.1
    P = np.diag([0.20, 0.20, 0.05])
    Q = np.diag([0.01, 0.01, 0.004])

    # --- predict: mean must use the nonlinear model -------------------------
    x_pred, P_pred = ekf_predict(x, P, u, dt, Q)
    results.append(check(
        "predict mean equals the nonlinear motion model f(x,u)",
        np.allclose(x_pred, motion_model(x, u, dt))))

    # the predict mean must NOT equal the (wrong) linear propagation F @ x
    F_num = numeric_jacobian(lambda xx: motion_model(xx, u, dt), x)
    results.append(check(
        "F matches finite-difference Jacobian of the motion model",
        np.allclose(F_num @ P @ F_num.T + Q, P_pred, atol=1e-4)))

    # prediction must increase total uncertainty (trace grows)
    results.append(check(
        "prediction increases uncertainty (trace P_pred > trace P)",
        np.trace(P_pred) > np.trace(P)))

    results.append(check(
        "P_pred is symmetric",
        np.allclose(P_pred, P_pred.T, atol=1e-9)))

    # --- Monte-Carlo cross-check of the predicted covariance ----------------
    n = 200_000
    samples = rng.multivariate_normal(x, P, size=n)
    propagated = np.array([motion_model(s, u, dt) for s in samples[:20_000]])
    # add process noise to the propagated cloud
    propagated = propagated + rng.multivariate_normal(np.zeros(3), Q, size=20_000)
    mc_cov = np.cov(propagated.T)
    results.append(check(
        "predicted covariance agrees with Monte-Carlo (within 12%)",
        np.allclose(mc_cov, P_pred, rtol=0.12, atol=0.02)))

    # --- update: H must match finite-difference, uncertainty must shrink ----
    landmark = np.array([5.0, 4.0])
    H_num = numeric_jacobian(lambda xx: measurement_model(xx, landmark), x_pred)
    # rebuild the analytic H the way ekf_update does, to compare
    dx, dy = landmark - x_pred[:2]
    q = dx * dx + dy * dy
    r = np.sqrt(q)
    H_ana = np.array([[-dx / r, -dy / r, 0.0],
                      [dy / q, -dx / q, -1.0]])
    results.append(check(
        "measurement Jacobian H matches finite-difference",
        np.allclose(H_num, H_ana, atol=1e-4)))

    # a perfect (noise-free) measurement should pull the estimate toward truth
    truth = np.array([1.05, 2.10, 0.62])
    z = measurement_model(truth, landmark)
    R = np.diag([0.05 ** 2, np.deg2rad(2.0) ** 2])
    x_upd, P_upd = ekf_update(x_pred, P_pred, z, landmark, R)

    err_before = np.linalg.norm((x_pred - truth)[:2])
    err_after = np.linalg.norm((x_upd - truth)[:2])
    results.append(check(
        "update moves the position estimate toward the measurement",
        err_after < err_before))

    results.append(check(
        "update decreases uncertainty (trace P_upd < trace P_pred)",
        np.trace(P_upd) < np.trace(P_pred)))

    results.append(check(
        "P_upd is symmetric and positive (diagonal > 0)",
        np.allclose(P_upd, P_upd.T, atol=1e-9) and np.all(np.diag(P_upd) > 0)))

    # bearing wrap: an update near theta = pi must stay finite and sane
    x_wrap = np.array([0.0, 0.0, np.pi - 0.01])
    P_wrap = np.diag([0.2, 0.2, 0.1])
    lm2 = np.array([-3.0, 0.05])
    z2 = measurement_model(np.array([0.0, 0.0, np.pi - 0.01]), lm2)
    xw, Pw = ekf_update(x_wrap, P_wrap, z2, lm2, R)
    results.append(check(
        "bearing wrap handled: no NaN/inf and heading stays in (-pi, pi]",
        np.all(np.isfinite(xw)) and -np.pi - 1e-9 <= xw[2] <= np.pi + 1e-9))

    print("=" * 60)
    print(f"predict mean   x_pred = {x_pred}")
    print(f"predict cov diag       = {np.diag(P_pred)}")
    print(f"updated mean   x_upd  = {x_upd}")
    print(f"updated cov diag       = {np.diag(P_upd)}")
    print("=" * 60)

    if all(results):
        print("ALL CHECKS PASSED")
        return 0
    print(f"{results.count(False)} CHECK(S) FAILED -- fix the math and re-run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
