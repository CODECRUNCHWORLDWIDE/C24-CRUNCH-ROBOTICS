#!/usr/bin/env python3
# Exercise 3 — Kinematic-bicycle MPC tracking a figure-8 (constrained + profiled)
#
# Goal: Build the controller the syllabus asks for -- a kinematic-bicycle MPC that
#       tracks a figure-8 reference with HARD velocity and steering-rate limits --
#       compare its tracking to LQR, and PROFILE the solve time against a control-
#       period budget. This is MPC at deployment shape: optimal, feasible, and (you
#       check) in budget.
#
# Estimated time: 50 minutes. Runnable.
#
# HOW TO USE THIS FILE
#
#       pip install cvxpy numpy scipy matplotlib
#       python3 exercise-03-bicycle-mpc-tracking.py            # track + plot
#       python3 exercise-03-bicycle-mpc-tracking.py --profile  # report solve-time stats
#
# WHAT YOU OBSERVE
#
#   * The MPC tracks the figure-8, respecting |v|<=V_MAX and the steering-RATE limit
#     |delta_{k+1}-delta_k|<=DDELTA_MAX -- it can't snap the wheels, like a real car.
#   * Solve status is "optimal" every step (feasible).
#   * The solve-time p95 is compared to the control-period budget. If p95 > budget,
#     the controller is NOT deployable at this rate -- the lesson of Lecture 2.
#
# ACCEPTANCE CRITERIA
#
#   [ ] The MPC tracks the figure-8 with bounded cross-track error.
#   [ ] |v| and the steering-rate limit are respected throughout (status optimal).
#   [ ] --profile reports mean / p95 / max solve time and compares p95 to the budget.
#   [ ] You can state what you'd cut (horizon N) if p95 exceeded the budget.
#
# Expected output is at the bottom of the file.

import argparse
import math
import sys
import time

import numpy as np
import cvxpy as cp

try:
    import matplotlib.pyplot as plt
    HAVE_PLT = True
except ImportError:
    HAVE_PLT = False

# --- Bicycle model + MPC parameters ----------------------------------------
L = 0.3              # wheelbase (m)
DT = 0.05            # control / prediction step (s) -> 20 Hz
N = 15               # prediction horizon
V_MAX = 1.5          # hard speed limit (m/s)
DELTA_MAX = 0.5      # hard steering-angle limit (rad)
DDELTA_MAX = 0.15    # hard steering-RATE limit per step (rad) -> ~3 rad/s at 20 Hz
A_MAX = 1.0          # hard acceleration limit (m/s^2)
BUDGET_MS = 50.0     # control-period budget at 20 Hz
T_END = 30.0


def figure8_reference(t, a=2.0, period=20.0):
    """Lemniscate (figure-8). Returns (x, y, theta, v) reference at time t."""
    w = 2 * math.pi / period
    x = a * math.sin(w * t)
    y = a * math.sin(w * t) * math.cos(w * t)
    dx = a * w * math.cos(w * t)
    dy = a * w * (math.cos(w * t) ** 2 - math.sin(w * t) ** 2)
    theta = math.atan2(dy, dx)
    v = math.hypot(dx, dy)
    return x, y, theta, min(v, V_MAX)


def linearize_bicycle(x_ref, y_ref, theta_ref, v_ref, delta_ref=0.0):
    """Linearize the kinematic bicycle about a reference point. Returns (A, B).
    State [x, y, theta, v]; input [a, delta]."""
    A = np.eye(4)
    A[0, 2] = -v_ref * math.sin(theta_ref) * DT
    A[0, 3] = math.cos(theta_ref) * DT
    A[1, 2] = v_ref * math.cos(theta_ref) * DT
    A[1, 3] = math.sin(theta_ref) * DT
    A[2, 3] = (math.tan(delta_ref) / L) * DT
    B = np.zeros((4, 2))
    B[2, 1] = (v_ref / (L * math.cos(delta_ref) ** 2)) * DT
    B[3, 0] = DT
    return A, B


def bicycle_step(state, u, dt):
    """True nonlinear bicycle dynamics for the simulated plant."""
    x, y, theta, v = state
    a, delta = u
    x += v * math.cos(theta) * dt
    y += v * math.sin(theta) * dt
    theta += (v / L) * math.tan(delta) * dt
    v += a * dt
    return np.array([x, y, theta, v])


def solve_mpc(state, t_now, prev_delta):
    """Solve the bicycle-MPC QP for the current state. Returns (u0, status)."""
    Q = np.diag([10.0, 10.0, 1.0, 1.0])
    R = np.diag([0.1, 0.1])

    x = cp.Variable((4, N + 1))
    u = cp.Variable((2, N))     # [a, delta] per step
    cost = 0
    cons = [x[:, 0] == state]
    for k in range(N):
        xr, yr, thr, vr = figure8_reference(t_now + k * DT)
        A, B = linearize_bicycle(xr, yr, thr, vr)
        ref = np.array([xr, yr, thr, vr])
        cost += cp.quad_form(x[:, k] - ref, Q) + cp.quad_form(u[:, k], R)
        cons += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]
        cons += [cp.abs(x[3, k]) <= V_MAX]              # speed limit
        cons += [cp.abs(u[0, k]) <= A_MAX]              # accel limit
        cons += [cp.abs(u[1, k]) <= DELTA_MAX]          # steering-angle limit
        # Steering-RATE limit (the constraint that makes it feel like a real car).
        prev = prev_delta if k == 0 else u[1, k - 1]
        cons += [cp.abs(u[1, k] - prev) <= DDELTA_MAX]
    prob = cp.Problem(cp.Minimize(cost), cons)
    prob.solve(solver=cp.OSQP, warm_start=True)
    if u.value is None:
        return None, prob.status
    return u[:, 0].value, prob.status


def run(profile=False):
    # Start slightly off the path.
    x0, y0, th0, v0 = figure8_reference(0.0)
    state = np.array([x0, y0 + 0.2, th0, v0])
    prev_delta = 0.0
    n_steps = int(T_END / DT)

    xs, ys, xref, yref, xtrack, solve_ms = [], [], [], [], [], []
    for i in range(n_steps):
        t_now = i * DT
        t0 = time.perf_counter()
        u0, status = solve_mpc(state, t_now, prev_delta)
        solve_ms.append((time.perf_counter() - t0) * 1e3)
        if status != "optimal" or u0 is None:
            print(f"  INFEASIBLE at step {i} (status={status}); stopping.")
            break
        prev_delta = float(u0[1])
        state = bicycle_step(state, u0, DT)
        xr, yr, _, _ = figure8_reference(t_now)
        xs.append(state[0]); ys.append(state[1]); xref.append(xr); yref.append(yr)
        # Cross-track error (approx): distance to the reference point.
        xtrack.append(math.hypot(state[0] - xr, state[1] - yr))

    rms_xtrack = float(np.sqrt(np.mean(np.square(xtrack)))) if xtrack else float("nan")
    st = np.array(solve_ms)
    print(f"MPC figure-8: tracked {len(xs)} steps, RMS cross-track={rms_xtrack:.4f} m")

    if profile:
        p95 = np.percentile(st, 95)
        print(f"  solve time: mean {st.mean():.1f} ms  p95 {p95:.1f} ms  "
              f"max {st.max():.1f} ms")
        pct = p95 / BUDGET_MS * 100
        verdict = "OK (deployable at this rate)" if p95 <= BUDGET_MS else \
            "OVER BUDGET -- cut N, warm-start harder, or move to acados/OSQP"
        print(f"  budget {BUDGET_MS} ms -> p95 is {pct:.0f}% of budget  {verdict}")
        print("  (cvxpy carries canonicalization overhead; a deployed MPC drops to "
              "OSQP-direct or acados -- Lecture 2 Part 3.)")

    if HAVE_PLT and xs:
        plt.figure(figsize=(7, 7))
        plt.plot(xref, yref, "k--", lw=1, label="figure-8 reference")
        plt.plot(xs, ys, "b", lw=1.5, label="MPC path")
        plt.axis("equal"); plt.grid(True); plt.legend()
        plt.title(f"Bicycle MPC tracking (RMS cross-track {rms_xtrack:.3f} m)")
        plt.savefig("bicycle_mpc_track.png", dpi=110)
        print("  saved bicycle_mpc_track.png")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Kinematic-bicycle MPC, figure-8.")
    parser.add_argument("--profile", action="store_true",
                        help="report solve-time statistics vs the latency budget.")
    args = parser.parse_args()
    sys.exit(run(profile=args.profile))


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Expected output (--profile)
# -----------------------------------------------------------------------------
#
# MPC figure-8: tracked 600 steps, RMS cross-track=0.0__ m
#   solve time: mean _._ ms  p95 _._ ms  max __._ ms
#   budget 50.0 ms -> p95 is __% of budget  OK (deployable at this rate)
#   (cvxpy carries canonicalization overhead; a deployed MPC drops to OSQP-direct ...)
#   saved bicycle_mpc_track.png
#
# The exact solve times depend heavily on your machine; on a laptop cvxpy may be
# tens of ms (often near or over a tight budget -- that's the point). Cut N from 15
# to 8 and watch p95 drop, at the cost of less preview. This trade -- horizon vs.
# solve time -- IS the deployment engineering of MPC. To get truly fast, you leave
# cvxpy for OSQP-direct or acados, which is the stretch goal and the mini-project.
# -----------------------------------------------------------------------------
