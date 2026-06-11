#!/usr/bin/env python3
# Exercise 2 — Constrained double-integrator MPC (watch the constraints BIND)
#
# Goal: See the entire reason MPC exists. Take the double-integrator MPC from
#       Exercise 1, add HARD velocity and acceleration constraints, and watch the
#       MPC respect them exactly -- saturating at the limit instead of overshooting
#       it -- in precisely the situation where last week's LQR would have VIOLATED
#       them. Then prove it: run the same problem with an unconstrained LQR and
#       show the LQR commands past the limits while the MPC does not.
#
# Estimated time: 45 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#       pip install cvxpy numpy scipy matplotlib
#       python3 exercise-02-constrained-double-integrator-mpc.py
#
#   It runs a large-step regulation task with the MPC (constrained) and the LQR
#   (unconstrained) and reports, for each, the peak velocity and peak acceleration
#   commanded. The MPC must stay within the limits; the LQR will exceed them.
#   It checks prob.status every solve. It exits 0 only when the MPC respected the
#   constraints AND the LQR violated them (proving the constraints did something).
#
# ONE TODO: add the velocity and acceleration constraints to the QP.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The MPC solve status is "optimal" on every step (feasible throughout).
#   [ ] The MPC's peak |velocity| <= V_MAX and peak |accel| <= A_MAX (respected).
#   [ ] The unconstrained LQR's peak |velocity| or |accel| EXCEEDS a limit (violated).
#   [ ] The program prints "CONSTRAINTS BIND" and exits 0.
#
# Expected output is at the bottom of the file.

import sys

import numpy as np
import cvxpy as cp
from scipy.linalg import solve_discrete_are

try:
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:
    HAVE_PLT = False

DT = 0.1
A = np.array([[1.0, DT], [0.0, 1.0]])
B = np.array([[0.5 * DT**2], [DT]])
N = 25
Q = np.diag([10.0, 1.0])
R = np.array([[0.1]])
X_REF = np.array([2.0, 0.0])     # a LARGE step -> the unconstrained LQR wants to floor it
V_MAX = 0.8                       # hard velocity limit (m/s)
A_MAX = 1.0                       # hard acceleration limit (m/s^2)

P_TERM = solve_discrete_are(A, B, Q, R)
K_LQR = np.linalg.inv(R + B.T @ P_TERM @ B) @ (B.T @ P_TERM @ A)


def solve_mpc(x0):
    x = cp.Variable((2, N + 1))
    u = cp.Variable((1, N))
    cost = 0
    cons = [x[:, 0] == x0]
    for k in range(N):
        cost += cp.quad_form(x[:, k] - X_REF, Q) + cp.quad_form(u[:, k], R)
        cons += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]

        # TODO 1: add the HARD constraints that LQR cannot express.
        #   velocity:     cons += [cp.abs(x[1, k]) <= V_MAX]
        #   acceleration: cons += [cp.abs(u[:, k]) <= A_MAX]

    cost += cp.quad_form(x[:, N] - X_REF, P_TERM)
    prob = cp.Problem(cp.Minimize(cost), cons)
    prob.solve(solver=cp.OSQP, warm_start=True)
    return (u[:, 0].value, prob.status)


def run_mpc():
    x = np.array([0.0, 0.0])
    pos, vel, acc, status_ok = [], [], [], True
    for _ in range(60):
        u0, status = solve_mpc(x)
        if status != "optimal" or u0 is None:
            status_ok = False
            break
        a = float(u0)
        acc.append(a)
        x = A @ x + B @ np.array([a])
        pos.append(x[0]); vel.append(x[1])
    return np.array(pos), np.array(vel), np.array(acc), status_ok


def run_lqr():
    """The unconstrained LQR for comparison -- it does NOT know about the limits."""
    x = np.array([0.0, 0.0])
    pos, vel, acc = [], [], []
    for _ in range(60):
        a = float(-K_LQR @ (x - X_REF))    # NO saturation -- the honest LQR command
        acc.append(a)
        x = A @ x + B @ np.array([a])
        pos.append(x[0]); vel.append(x[1])
    return np.array(pos), np.array(vel), np.array(acc)


def main():
    print(f"Double-integrator regulation to p={X_REF[0]} m, "
          f"hard limits |v|<={V_MAX}, |a|<={A_MAX}")

    p_m, v_m, a_m, ok = run_mpc()
    if not ok:
        print("MPC infeasible -- did you make the constraints too tight? (or a bug)")
        sys.exit(1)
    p_l, v_l, a_l = run_lqr()

    mpc_peak_v, mpc_peak_a = np.max(np.abs(v_m)), np.max(np.abs(a_m))
    lqr_peak_v, lqr_peak_a = np.max(np.abs(v_l)), np.max(np.abs(a_l))

    print(f"  MPC  peak |v|={mpc_peak_v:.3f}  peak |a|={mpc_peak_a:.3f}  "
          f"(limits {V_MAX}, {A_MAX})")
    print(f"  LQR  peak |v|={lqr_peak_v:.3f}  peak |a|={lqr_peak_a:.3f}  "
          f"(IGNORES the limits)")

    mpc_respects = mpc_peak_v <= V_MAX + 1e-3 and mpc_peak_a <= A_MAX + 1e-3
    lqr_violates = lqr_peak_v > V_MAX + 1e-3 or lqr_peak_a > A_MAX + 1e-3

    if mpc_respects and lqr_violates:
        print("CONSTRAINTS BIND: the MPC stayed within the hard limits exactly where "
              "the LQR blew past them. That is the whole reason MPC exists.")
        code = 0
    else:
        msgs = []
        if not mpc_respects:
            msgs.append("MPC exceeded a limit (did you add TODO 1?)")
        if not lqr_violates:
            msgs.append("LQR didn't exceed a limit -- make X_REF larger so it wants to")
        print("CHECK FAILED: " + "; ".join(msgs))
        code = 1

    if HAVE_PLT:
        t = np.arange(len(v_m)) * DT
        fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
        ax[0].plot(t, v_m, label="MPC velocity")
        ax[0].plot(t[:len(v_l)], v_l, "--", label="LQR velocity (unconstrained)")
        ax[0].axhline(V_MAX, color="r", ls=":", label="v limit")
        ax[0].set_ylabel("velocity (m/s)"); ax[0].legend(); ax[0].grid(True)
        ax[1].plot(t, a_m, label="MPC accel")
        ax[1].plot(t[:len(a_l)], a_l, "--", label="LQR accel (unconstrained)")
        ax[1].axhline(A_MAX, color="r", ls=":"); ax[1].axhline(-A_MAX, color="r", ls=":")
        ax[1].set_ylabel("accel (m/s^2)"); ax[1].set_xlabel("time (s)")
        ax[1].legend(); ax[1].grid(True)
        fig.suptitle("MPC respects hard limits; LQR violates them")
        fig.tight_layout(); fig.savefig("constraints_bind.png", dpi=110)
        print("saved constraints_bind.png")

    sys.exit(code)


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (after filling in TODO 1)
# -----------------------------------------------------------------------------
#
# Double-integrator regulation to p=2.0 m, hard limits |v|<=0.8, |a|<=1.0
#   MPC  peak |v|=0.800  peak |a|=1.000  (limits 0.8, 1.0)   <- pinned AT the limits
#   LQR  peak |v|=1.__   peak |a|=2.__   (IGNORES the limits) <- blows past them
# CONSTRAINTS BIND: the MPC stayed within the hard limits exactly where the LQR ...
# saved constraints_bind.png
#
# Expected output (BEFORE TODO 1)
# -----------------------------------------------------------------------------
#
# The MPC peak |v|/|a| also exceed the limits (it's just an LQR with extra steps),
# and "CHECK FAILED: MPC exceeded a limit". The lesson: the two cp.abs(...) <= limit
# lines are the entire difference between LQR and MPC. Without them, MPC has no
# more power than LQR. With them, it respects physics LQR cannot express.
# -----------------------------------------------------------------------------
