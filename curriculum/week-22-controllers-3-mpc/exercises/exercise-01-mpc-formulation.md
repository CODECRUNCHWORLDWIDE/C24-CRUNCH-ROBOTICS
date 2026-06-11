# Exercise 1 — MPC Formulation (and the LQR Equivalence Check)

**Goal:** Formulate a double-integrator MPC — first on paper, then in `cvxpy` — and verify the single most important MPC correctness fact: with **no active constraints**, a long horizon, and the LQR terminal cost, the MPC's first input is *identical* to last week's LQR command. If they match, your MPC machinery is correct and you can add constraints with confidence. If they don't, you have a bug, and you've found it before the constraints hid it.

**Estimated time:** 45 minutes. Guided.

---

## The plant

The double integrator — position and velocity, with acceleration as the input. It's the simplest plant that's still interesting, and it's the textbook MPC example:

```
state x = [ p ]   position
          [ v ]   velocity
input u = [ a ]   acceleration

discrete (step dt):  x_{k+1} = A x_k + B u_k
   A = [ 1  dt ]     B = [ 0.5·dt² ]
       [ 0  1  ]         [   dt    ]
```

The goal: drive the position to a reference `p_ref` and the velocity to 0.

---

## Step 1 — Write the QP on paper

Before any code, write down the full MPC QP for this plant (Lecture 1 §2.5). On paper or in a comment, state:

- The **decision variables**: `x₀…x_N` (the `N+1` predicted states) and `u₀…u_{N−1}` (the `N` inputs).
- The **equality constraints**: `x₀ = x_measured`, and `x_{k+1} = A x_k + B u_k` for each `k`.
- The **objective**: `Σ (x_k − x_ref)ᵀ Q (x_k − x_ref) + u_kᵀ R u_k + (x_N − x_ref)ᵀ P (x_N − x_ref)`.
- (No inequality constraints yet — this is the unconstrained case for the LQR check.)

You should be able to write this from memory by the end of the week. Writing it now, by hand, is how it sticks.

---

## Step 2 — Build it in `cvxpy`

Save this as `mpc_formulation.py` and complete the marked section:

```python
#!/usr/bin/env python3
"""Double-integrator MPC, and the unconstrained-equals-LQR correctness check."""
import numpy as np
import cvxpy as cp
from scipy.linalg import solve_discrete_are

dt = 0.1
A = np.array([[1.0, dt], [0.0, 1.0]])
B = np.array([[0.5 * dt**2], [dt]])
n, m = 2, 1

Q = np.diag([10.0, 1.0])
R = np.array([[0.1]])
x_ref = np.array([1.0, 0.0])
N = 30                      # long horizon, so the finite cutoff barely matters

# The LQR terminal cost P is the discrete-ARE solution — the infinite tail.
P_term = solve_discrete_are(A, B, Q, R)
# The LQR gain we must match in the unconstrained case.
K_lqr = np.linalg.inv(R + B.T @ P_term @ B) @ (B.T @ P_term @ A)


def solve_mpc(x0):
    x = cp.Variable((n, N + 1))
    u = cp.Variable((m, N))
    cost = 0
    constraints = [x[:, 0] == x0]
    for k in range(N):
        cost += cp.quad_form(x[:, k] - x_ref, Q) + cp.quad_form(u[:, k], R)
        constraints += [x[:, k + 1] == A @ x[:, k] + B @ u[:, k]]
        # NOTE: no inequality constraints here -> should reduce to LQR.

    # TODO 1: add the terminal cost (x_N - x_ref)^T P_term (x_N - x_ref) to `cost`.
    #   cost += cp.quad_form(x[:, N] - x_ref, P_term)

    prob = cp.Problem(cp.Minimize(cost), constraints)
    prob.solve(solver=cp.OSQP, warm_start=True)
    return u[:, 0].value, prob.status


if __name__ == "__main__":
    x0 = np.array([0.0, 0.0])
    u0_mpc, status = solve_mpc(x0)
    # The LQR command for the SAME state and reference: u = -K (x - x_ref).
    u0_lqr = float(-K_lqr @ (x0 - x_ref))

    print(f"solve status: {status}")
    print(f"MPC first input u0 : {float(u0_mpc):.5f}")
    print(f"LQR command   u0 : {u0_lqr:.5f}")
    match = abs(float(u0_mpc) - u0_lqr) < 1e-3
    print("MATCH (MPC == LQR when unconstrained)" if match
          else "MISMATCH -- you have a bug (sign? terminal cost? discretization?)")
```

```bash
python3 mpc_formulation.py
```

---

## Step 3 — Confirm the equivalence

You should see the MPC's first input match the LQR command to three decimals:

```
solve status: optimal
MPC first input u0 : 0.31623
LQR command   u0 : 0.31623
MATCH (MPC == LQR when unconstrained)
```

**This is the load-bearing check of the whole week.** It works because (Lecture 1 §5) an unconstrained MPC with a long horizon and the LQR terminal cost *is* the LQR — same problem, finite vs. infinite, reconciled by the terminal cost. If yours doesn't match: did you add the terminal cost (TODO 1)? Is the discretization (`solve_discrete_are`, not continuous) consistent? Is the sign of the LQR command right (`u = −K(x − x_ref)`)? Debug it here, where you have a closed-form answer to compare against.

---

## Step 4 — Break the equivalence on purpose

Now make the horizon *short* (`N = 2`) and re-run. The match degrades — the finite-horizon cutoff now matters and the terminal cost is doing heavy lifting. Then drop the terminal cost entirely (comment out TODO 1) with a short horizon and watch the MPC become noticeably more myopic than the LQR. This shows you *why* the terminal cost exists: it's what lets a short-horizon MPC still behave well, by accounting for the future beyond the horizon.

Write a one-line comment recording what happened at `N=2` with and without the terminal cost.

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] You wrote the MPC QP for the double integrator on paper / in a comment (variables, equality constraints, objective).
- [ ] `mpc_formulation.py` prints `MATCH` — the unconstrained MPC's first input equals the LQR command to within `1e-3`.
- [ ] You can explain *why* they match (unconstrained + long horizon + LQR terminal cost = LQR).
- [ ] You observed (Step 4) that a short horizon without the terminal cost makes the MPC myopic, and you can say why the terminal cost fixes it.

---

## Stretch

- Verify the equivalence holds across several initial states `x0`, not just `[0,0]` — the gain is the same everywhere in the unconstrained region, which is the LQR property.
- Add a single inequality constraint (`|u| ≤ 0.2`) that *binds* for a large initial error, and confirm the MPC now *differs* from the LQR (the LQR would command past 0.2; the MPC saturates at it). This is the preview of Exercise 2.
- Time the `cvxpy` solve with `time.perf_counter` and note how much of it is canonicalization overhead (Lecture 2 §3.1) — this is your first taste of why `cvxpy` is for learning, not the real-time loop.

---

When this feels comfortable, move to [Exercise 2 — Constrained double-integrator MPC](exercise-02-constrained-double-integrator-mpc.py).
