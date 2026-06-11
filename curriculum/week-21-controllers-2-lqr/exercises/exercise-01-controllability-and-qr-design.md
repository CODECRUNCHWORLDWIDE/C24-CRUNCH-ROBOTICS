# Exercise 1 — Controllability and Q/R Design

**Goal:** Build the diff-drive path-tracking state-space model by hand, test its controllability (and watch the test correctly *fail* at zero speed, which is real physics), and design the `Q`/`R` cost matrices with Bryson's rule. You will produce the four ingredients — `A`, `B`, `Q`, `R` — that Exercise 2 feeds to the Riccati solver. No solving yet; this is the modeling and cost-design half of LQR.

**Estimated time:** 45 minutes. Guided.

---

## The model

We control a diff-drive robot tracking a path. From Lecture 1 §2.2, the linearized **error dynamics** are:

```
state x = [ e_y ]   cross-track error (lateral distance from the path, meters)
          [ e_θ ]   heading error (angle between robot heading and path tangent, rad)

input u = [ δω ]    yaw-rate correction (rad/s)

       d/dt [ e_y ]   [ 0   v_ref ] [ e_y ]   [ 0 ]
            [ e_θ ] = [ 0    0    ] [ e_θ ] + [ 1 ] · δω
```

So `A = [[0, v_ref], [0, 0]]` and `B = [[0], [1]]`, with `v_ref` the reference forward speed.

---

## Step 1 — Build A and B, and read them physically

Save this as `lqr_model.py` and fill in the model:

```python
#!/usr/bin/env python3
"""Build and analyze the diff-drive path-tracking state-space model."""
import numpy as np


def diff_drive_error_AB(v_ref):
    """Linearized error dynamics. Returns (A, B)."""
    A = np.array([[0.0, v_ref],
                  [0.0, 0.0]])
    B = np.array([[0.0],
                  [1.0]])
    return A, B


if __name__ == "__main__":
    A, B = diff_drive_error_AB(v_ref=0.5)
    print("A =\n", A)
    print("B =\n", B)
    # Eigenvalues of A: the OPEN-LOOP modes. Both are 0 here (a double integrator-
    # like chain) -> marginally stable, drifts forever without control. That's why
    # you need a controller: cross-track error never self-corrects.
    print("open-loop eigenvalues of A:", np.linalg.eigvals(A))
```

Read the physics in the matrix: the `v_ref` in `A[0,1]` says "if you're pointed off-axis (`e_θ ≠ 0`) and moving forward at `v_ref`, your cross-track error grows at rate `v_ref·e_θ`." The `1` in `B[1,0]` says "your yaw-rate correction directly changes your heading error." That's the whole robot, linearized.

---

## Step 2 — Test controllability, and break it on purpose

Add the controllability test:

```python
def controllability_matrix(A, B):
    n = A.shape[0]
    blocks = [B]
    for _ in range(1, n):
        blocks.append(A @ blocks[-1])
    return np.hstack(blocks)


def is_controllable(A, B):
    Cm = controllability_matrix(A, B)
    return np.linalg.matrix_rank(Cm) == A.shape[0]
```

Now run it at two speeds:

```python
for v in (0.5, 0.0):
    A, B = diff_drive_error_AB(v)
    Cm = controllability_matrix(A, B)
    print(f"v_ref={v}:  ctrb rank={np.linalg.matrix_rank(Cm)}  "
          f"controllable={is_controllable(A, B)}")
```

You should see:

```
v_ref=0.5:  ctrb rank=2  controllable=True
v_ref=0.0:  ctrb rank=1  controllable=False
```

**The `v_ref = 0` failure is not a bug — it is physics.** A diff-drive robot cannot correct cross-track (lateral) error while standing still; the only way to reduce sideways error is to drive forward while turning. LQR *encodes* that: at zero speed the problem is genuinely uncontrollable, and the rank test tells you so. If you tried to solve LQR at `v_ref = 0` the Riccati solver would fail or return nonsense — correctly, because no controller can do the impossible. Internalize this: the controllability check is a *physical* statement about your robot, not a numerical formality.

---

## Step 3 — Design Q and R with Bryson's rule

Now the cost. Decide what "bad" means for each quantity, then apply Bryson's rule (`Q_ii = 1/x_i,max²`, `R_jj = 1/u_j,max²`):

```python
# TODO 1: choose your tolerances and build Q, R with Bryson's rule.
#   - How much cross-track error is "bad"? (e.g. 0.10 m)
#   - How much heading error is "bad"?     (e.g. 0.20 rad ~ 11 deg)
#   - How much yaw-rate correction is "a lot"? (e.g. 1.0 rad/s)
e_y_max = 0.10
e_theta_max = 0.20
u_max = 1.0

Q = np.diag([1.0 / e_y_max**2, 1.0 / e_theta_max**2])
R = np.array([[1.0 / u_max**2]])
print("Q =\n", Q)        # [[100, 0], [0, 25]]
print("R =\n", R)        # [[1.0]]
```

The units lesson: cross-track error is in meters and heading error is in radians — you *cannot* put `1`s on the diagonal and have the cost mean anything, because a 1 m error and a 1 rad error are not comparable. Bryson's rule normalizes each by its own "bad" value so the terms add up apples to apples.

---

## Step 4 — Sweep the cost and predict the effect

You won't solve until Exercise 2, but reason about it now. Answer these in a comment block in `lqr_model.py`:

- If you **double** `Q[0,0]` (care twice as much about cross-track error), will the resulting controller be more or less aggressive? (More.)
- If you **double** `R` (care twice as much about gentle steering), more or less aggressive? (Less.)
- If you **scale both `Q` and `R` by 10**, what happens to the gain `K`? (Nothing — only the ratio matters.)
- At `v_ref = 1.5` instead of `0.5`, `A` changes. Will the same `Q`/`R` give the same `K`? (No — the dynamics changed; this is *why* gain scheduling exists.)

---

## Acceptance criteria

You can mark this exercise done when:

- [ ] `lqr_model.py` builds `A`, `B` for `v_ref = 0.5` and prints the open-loop eigenvalues (both ~0).
- [ ] The controllability test returns `True` at `v_ref = 0.5` and `False` at `v_ref = 0.0`.
- [ ] You can explain *in one sentence* why zero speed is uncontrollable (a diff-drive robot can't fix lateral error without moving forward).
- [ ] `Q` and `R` are built with Bryson's rule and you can justify each tolerance.
- [ ] The four Step-4 predictions are answered correctly in a comment.

---

## Stretch

- Add a **third state** — velocity error `e_v` — so `x = [e_y, e_θ, e_v]` and `u = [δω, δv]` (two inputs). Build the `3×3` `A`, `3×2` `B`, and re-test controllability. This is the model the mini-project can use for full pose-and-speed tracking.
- Compute the **controllability Gramian** (`scipy.linalg.solve_continuous_lyapunov` on `A W + W Aᵀ = −BBᵀ` for a stable `A`, or the finite-horizon integral) and look at its eigenvalues — the small ones are the "hard to control" directions. This is the quantitative version of the rank test.
- Use `python-control`'s `ctrb` and confirm it gives the same rank as your hand-rolled controllability matrix.

---

When this feels comfortable, move to [Exercise 2 — Solve and simulate LQR](exercise-02-solve-and-simulate-lqr.py).
