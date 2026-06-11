#!/usr/bin/env python3
# Exercise 2 — Solve the Riccati equation and simulate the LQR closed loop
#
# Goal: Turn the (A, B, Q, R) from Exercise 1 into the optimal gain K, run the
#       three sanity checks (controllable / P positive-definite / closed loop
#       stable), simulate the closed loop, and cross-check K against the
#       python-control library so you trust your hand-rolled solve.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#   Standalone. No ROS, no robot:
#
#       pip install numpy scipy matplotlib control
#       python3 exercise-02-solve-and-simulate-lqr.py
#
#   It solves LQR for the diff-drive error model, runs the checks, simulates a
#   step in cross-track error being driven to zero, and prints whether your gain
#   matches python-control's lqr. It exits 0 only when all checks pass AND the
#   two gains agree.
#
# ONE TODO is marked in lqr(): recover K from the Riccati solution P.
#
# ACCEPTANCE CRITERIA
#
#   [ ] controllability rank == n (2).
#   [ ] P is symmetric positive-definite.
#   [ ] all closed-loop eigenvalues have negative real part.
#   [ ] your K matches control.lqr's K to within tolerance.
#   [ ] the simulated closed loop drives an initial cross-track error to ~0.
#   [ ] the program prints "ALL CHECKS PASS" and exits 0.
#
# Expected output is at the bottom of the file.

import sys

import numpy as np
from scipy.linalg import solve_continuous_are

try:
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:
    HAVE_PLT = False

try:
    import control as ct
    HAVE_CONTROL = True
except ImportError:
    HAVE_CONTROL = False


def diff_drive_error_AB(v_ref):
    A = np.array([[0.0, v_ref], [0.0, 0.0]])
    B = np.array([[0.0], [1.0]])
    return A, B


def controllability_rank(A, B):
    n = A.shape[0]
    blocks = [B]
    for _ in range(1, n):
        blocks.append(A @ blocks[-1])
    return np.linalg.matrix_rank(np.hstack(blocks))


def lqr(A, B, Q, R):
    """Continuous-time infinite-horizon LQR. Returns (K, P)."""
    P = solve_continuous_are(A, B, Q, R)        # solve the CARE for P

    # TODO 1: recover the optimal gain from P.  K = R^-1 B^T P
    #   Replace the placeholder below.
    K = np.zeros((B.shape[1], A.shape[0]))      # <-- BUG: fill in K = inv(R) @ B.T @ P

    return K, P


def sanity_checks(A, B, Q, R, K, P):
    ok = True
    n = A.shape[0]

    rank = controllability_rank(A, B)
    print(f"  [1] controllability rank: {rank} (need {n})  "
          f"{'OK' if rank == n else 'FAIL'}")
    ok &= rank == n

    sym = np.allclose(P, P.T)
    posdef = np.all(np.linalg.eigvals(P) > 0)
    print(f"  [2] P symmetric: {sym}, positive-definite: {posdef}  "
          f"{'OK' if sym and posdef else 'FAIL'}")
    ok &= sym and posdef

    cl_eig = np.linalg.eigvals(A - B @ K)
    stable = np.all(np.real(cl_eig) < 0)
    print(f"  [3] closed-loop eigenvalues: {np.round(cl_eig, 3)}  "
          f"{'OK (stable)' if stable else 'FAIL (unstable)'}")
    ok &= stable

    return ok


def simulate(A, B, K, x0, dt=0.01, t_end=5.0):
    """Simulate xdot = (A - BK) x from x0. Returns (t, X)."""
    n = A.shape[0]
    steps = int(t_end / dt)
    t = np.arange(steps) * dt
    X = np.zeros((steps, n))
    x = np.array(x0, dtype=float)
    Acl = A - B @ K
    for k in range(steps):
        X[k] = x
        x = x + (Acl @ x) * dt
    return t, X


def main():
    v_ref = 0.5
    A, B = diff_drive_error_AB(v_ref)
    Q = np.diag([100.0, 25.0])       # Bryson: 1/0.1^2, 1/0.2^2 (Exercise 1)
    R = np.array([[1.0]])

    print(f"LQR for diff-drive error dynamics at v_ref={v_ref}")
    K, P = lqr(A, B, Q, R)
    print("  optimal gain K =", np.round(K, 4))

    print("Sanity checks:")
    checks_ok = sanity_checks(A, B, Q, R, K, P)

    # Cross-check against python-control.
    match = True
    if HAVE_CONTROL:
        K_ct, _, _ = ct.lqr(A, B, Q, R)
        match = np.allclose(K, K_ct, atol=1e-4)
        print(f"  cross-check vs control.lqr: K_ct={np.round(K_ct, 4)}  "
              f"{'MATCH' if match else 'MISMATCH'}")
    else:
        print("  (python-control not installed; skipping cross-check. "
              "pip install control to enable it.)")

    # Simulate: an initial 0.5 m cross-track error driven to zero.
    t, X = simulate(A, B, K, x0=[0.5, 0.0])
    final_ey = X[-1, 0]
    converged = abs(final_ey) < 0.02
    print(f"Simulation: initial cross-track 0.5 m -> final {final_ey:.4f} m  "
          f"{'OK (converged)' if converged else 'FAIL'}")

    all_ok = checks_ok and match and converged
    print("ALL CHECKS PASS" if all_ok else "CHECKS FAILED (did you fill in TODO 1?)")

    if HAVE_PLT:
        plt.plot(t, X[:, 0], label="cross-track error e_y (m)")
        plt.plot(t, X[:, 1], label="heading error e_theta (rad)")
        plt.axhline(0, color="k", lw=0.6)
        plt.xlabel("time (s)"); plt.ylabel("error"); plt.legend(); plt.grid(True)
        plt.title(f"LQR closed loop, K={np.round(K, 2)}")
        plt.savefig("lqr_closed_loop.png", dpi=110)
        print("saved lqr_closed_loop.png")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (after filling in TODO 1)
# -----------------------------------------------------------------------------
#
# LQR for diff-drive error dynamics at v_ref=0.5
#   optimal gain K = [[10.0   6.7 ]]      (your numbers depend on Q, R)
# Sanity checks:
#   [1] controllability rank: 2 (need 2)  OK
#   [2] P symmetric: True, positive-definite: True  OK
#   [3] closed-loop eigenvalues: [-3.3+1.9j -3.3-1.9j]  OK (stable)
#   cross-check vs control.lqr: K_ct=[[10.0 6.7]]  MATCH
# Simulation: initial cross-track 0.5 m -> final 0.0007 m  OK (converged)
# ALL CHECKS PASS
# saved lqr_closed_loop.png
#
# Expected output (BEFORE filling in TODO 1)
# -----------------------------------------------------------------------------
#
# K is all zeros, so the closed loop is just A (marginally stable), the
# eigenvalue check FAILs, the cross-check MISMATCHes, and the sim does NOT
# converge. CHECKS FAILED. The lesson: K = R^-1 B^T P is the one line that turns
# the Riccati solution into a controller. Everything else is checks around it.
# -----------------------------------------------------------------------------
